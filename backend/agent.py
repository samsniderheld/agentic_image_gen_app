import asyncio
from google.adk.runners import InMemoryRunner
from google.genai import types
from agent_loader import load_agent
import state
from models.registry import build_pipeline
from models.pipeline_context import PipelineContext
from typing import List

APP_NAME = "image_gen_app"
USER_ID  = "local_user"

# Simple direct tool calling for now (can switch to full ADK later)
USE_DIRECT_TOOLS = True

# Build pipeline once at module load (singleton)
_pipeline = None

def get_pipeline():
    """Get or build the pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
        print(f"🔧 Pipeline built: {[agent.name for agent in _pipeline]}")
    return _pipeline


def run_pre_generation(ctx: PipelineContext, message_callback=None) -> PipelineContext:
    """Run all agents that appear before 'generator' in the pipeline."""
    pipeline = get_pipeline()

    # Map agent names to friendly labels
    agent_labels = {
        "planner": "Planning and expanding prompt",
        "art_director": "Defining visual style",
        "dop": "Setting up shot specifications"
    }

    for agent in pipeline:
        if agent.name == "generator":
            break

        label = agent_labels.get(agent.name, f"Running {agent.name}")
        print(f"🤖 Running pre-generation agent: {agent.name}")

        if message_callback:
            message_callback({"role": "agent", "type": "thinking", "content": f"{label}..."})

        ctx = agent.run(ctx)
    return ctx


def run_generator(ctx: PipelineContext, message_callback=None) -> PipelineContext:
    """Run the generator agent."""
    pipeline = get_pipeline()
    for agent in pipeline:
        if agent.name == "generator":
            print(f"🤖 Running generator agent: {agent.name}")

            if message_callback:
                message_callback({"role": "agent", "type": "thinking", "content": "Generating image..."})

            return agent.run(ctx)
    raise RuntimeError("No 'generator' agent found in pipeline.")


def run_post_generation(ctx: PipelineContext, message_callback=None) -> PipelineContext:
    """Run all agents that appear after 'generator' in the pipeline."""
    pipeline = get_pipeline()
    after_generator = False

    # Map agent names to friendly labels
    agent_labels = {
        "critic": "Running vision critique"
    }

    for agent in pipeline:
        if agent.name == "generator":
            after_generator = True
            continue
        if after_generator:
            label = agent_labels.get(agent.name, f"Running {agent.name}")
            print(f"🤖 Running post-generation agent: {agent.name}")

            if message_callback:
                message_callback({"role": "agent", "type": "thinking", "content": f"{label}..."})

            ctx = agent.run(ctx)
    return ctx


# Legacy ADK-based functions (kept for backward compatibility with existing tools)
def run_adk_segment(agent_yaml: str, input_message: str, state_in: dict, state_out_keys: list):
    """
    Synchronously run an ADK agent.
    - agent_yaml:     filename in agents/ without .yaml
    - input_message:  user turn text sent to agent
    - state_in:       keys seeded into session.state before run
    - state_out_keys: keys read back into state.pipeline after run
    """
    if USE_DIRECT_TOOLS:
        # Simplified direct tool calling
        _run_direct(agent_yaml, state_in, state_out_keys)
    else:
        try:
            asyncio.run(_run(agent_yaml, input_message, state_in, state_out_keys))
        except Exception as e:
            print(f"❌ ADK agent error: {e}")
            import traceback
            traceback.print_exc()
            raise

def _run_direct(agent_yaml: str, state_in: dict, state_out_keys: list):
    """Direct tool calling without ADK complexity."""
    from pipeline.tools import TOOL_REGISTRY

    print(f"🔧 Direct tool call: {agent_yaml}")

    # Mock tool context
    class MockToolContext:
        class Actions:
            escalate = False
        actions = Actions()

    tool_context = MockToolContext()

    if agent_yaml == "generation_agent":
        result = TOOL_REGISTRY["generate_image"](
            prompt=state_in["prompt"],
            aspect_ratio=state_in["aspect_ratio"],
            tool_context=tool_context
        )
        for key in state_out_keys:
            if key in result:
                state.pipeline[key] = result[key]
                print(f"   ✅ Set {key}: {result[key]}")

    elif agent_yaml == "critique_agent":
        result = TOOL_REGISTRY["critique_image"](
            image_path=state_in["image_path"],
            prompt=state_in["prompt"],
            tool_context=tool_context
        )
        # critique_image returns the full critique dict, store it under the expected key
        if "critique_json" in state_out_keys:
            state.pipeline["critique_json"] = result
            print(f"   ✅ Set critique_json")

    elif agent_yaml == "fix_loop":
        if not state_in.get("fixes_exhausted", False):
            result = TOOL_REGISTRY["apply_fix"](
                image_path=state_in["image_path"],
                fix_json=state_in["current_fix"],
                fix_index=state_in["fix_index"],
                tool_context=tool_context
            )
            for key in state_out_keys:
                if key in result:
                    state.pipeline[key] = result[key]
                    print(f"   ✅ Set {key}: {result[key]}")
        else:
            TOOL_REGISTRY["exit_loop"](tool_context=tool_context)

async def _run(agent_yaml, input_message, state_in, state_out_keys):
    print(f"🤖 Running ADK agent: {agent_yaml}")
    print(f"   Input: {input_message}")
    print(f"   State in: {state_in}")

    agent   = load_agent(agent_yaml)
    print(f"   Agent loaded: {agent.name}")

    runner  = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, state=state_in
    )
    print(f"   Session created: {session.id}")

    content = types.Content(role="user", parts=[types.Part(text=input_message)])

    print(f"   Running agent...")
    async for event in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=content):
        print(f"   📨 Event: {event}")

    final = await runner.session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session.id
    )
    print(f"   Final state keys: {list(final.state.keys())}")

    for key in state_out_keys:
        if key in final.state:
            state.pipeline[key] = final.state[key]
            print(f"   ✅ Copied {key}: {final.state[key]}")
        else:
            print(f"   ⚠️  Missing expected key: {key}")
