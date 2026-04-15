from loader import AgentConfig
import providers
import asyncio
from concurrent.futures import ThreadPoolExecutor

PROVIDER_DISPATCH = {
    "llm_agent": ("get_llm_provider", "call_llm"),
    "generator_agent": ("get_image_provider", "generate_image"),
    "critic_agent": ("get_critic_provider", "critique_image"),
    "video_agent": ("get_video_provider", "generate_video"),
}

# Thread pool for running sync provider calls in parallel
_executor = ThreadPoolExecutor(max_workers=10)

def run_agent(config: AgentConfig, context: dict) -> dict:
    """Synchronous wrapper for backward compatibility"""
    return asyncio.run(run_agent_async(config, context))

async def run_agent_async(config: AgentConfig, context: dict) -> dict:
    """Async version that can be run in parallel"""
    if config.type not in PROVIDER_DISPATCH:
        raise ValueError(f"Unknown agent type: {config.type}")
    getter_name, _ = PROVIDER_DISPATCH[config.type]
    provider = getattr(providers, getter_name)(config.model_provider)
    inputs = _resolve_inputs(config, context)

    # Run provider call in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _call_provider, config, provider, inputs)

    context = _set_outputs(config, context, result)
    return context

async def run_agents_parallel(agents: list, context: dict) -> dict:
    """Run multiple agents in parallel where possible"""
    # For now, run sequentially but with async support
    # Future enhancement: detect independent agents and run them in parallel
    for agent in agents:
        context = await run_agent_async(agent, context)
    return context

def _resolve_inputs(config: AgentConfig, context: dict) -> dict:
    out = {}
    for spec in config.inputs:
        print(f"DEBUG: Resolving input '{spec['name']}' from source '{spec['source']}'")
        v = context.get(spec["source"])
        print(f"DEBUG: Got value from context: {v is not None} (type: {type(v).__name__ if v is not None else 'None'})")

        if v is None and spec.get("fallback"):
            v = context.get(spec["fallback"])
            print(f"DEBUG: Used fallback, got: {v is not None}")

        if v is None and not spec.get("optional", False):
            v = spec.get("default")
            print(f"DEBUG: Used default: {v}")

        if spec.get("combine_with") and v is not None:
            sep = spec.get("separator", "\n\n")
            parts = [v] + [context[k] for k in spec["combine_with"] if context.get(k)]
            v = sep.join(parts)
            print(f"DEBUG: Combined with other fields")

        # Apply template if specified
        if spec.get("template") and v is not None:
            template = spec["template"]
            # Build template context from current value and combined fields
            template_vars = {spec["source"]: v}
            if spec.get("combine_with"):
                for key in spec["combine_with"]:
                    template_vars[key] = context.get(key, "")
            v = template.format(**template_vars)
            print(f"DEBUG: Applied template")

        out[spec["name"]] = v
        print(f"DEBUG: Final value for '{spec['name']}': {v is not None}")

    print(f"DEBUG: Resolved inputs keys: {list(out.keys())}")
    return out

def _call_provider(config: AgentConfig, provider, inputs: dict):
    if config.type == "llm_agent":
        # LLMs receive a system instruction + collapsed user message + model params.
        # Extract input_images separately if present
        input_images = inputs.pop('input_images', None)

        # All remaining data inputs are joined into the user message
        user_message = "\n\n".join(str(v) for v in inputs.values() if v is not None and v != '')

        # Check if agent has structured output schema
        response_schema = None
        if hasattr(config, 'response_schema'):
            response_schema = config.response_schema

        return provider.call_llm(
            config.instruction, user_message,
            config.model_name, config.temperature, config.max_tokens,
            input_images=input_images,
            response_schema=response_schema
        )
    elif config.type == "generator_agent":
        # generator_agent: add model_name to inputs
        print(f"DEBUG: Generator inputs: {list(inputs.keys())}")
        if 'input_images' in inputs:
            print(f"DEBUG: input_images value: {inputs['input_images']}")
        _, func_name = PROVIDER_DISPATCH[config.type]
        return getattr(provider, func_name)(model_name=config.model_name, **inputs)
    elif config.type == "video_agent":
        # video_agent: add model_name to inputs
        print(f"DEBUG: Video agent inputs: {list(inputs.keys())}")
        _, func_name = PROVIDER_DISPATCH[config.type]
        return getattr(provider, func_name)(model_name=config.model_name, **inputs)
    else:
        # critic_agent: YAML input names match provider kwarg names.
        _, func_name = PROVIDER_DISPATCH[config.type]
        return getattr(provider, func_name)(**inputs)

def _set_outputs(config: AgentConfig, context: dict, result) -> dict:
    """Set outputs in context without saving to disk - app.py handles saving"""
    for spec in config.outputs:
        context[spec["target"]] = result
    return context
