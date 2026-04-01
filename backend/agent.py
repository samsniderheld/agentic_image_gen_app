from models.registry import build_pipeline
from models.pipeline_context import PipelineContext

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
