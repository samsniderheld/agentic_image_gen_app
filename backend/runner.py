from loader import AgentConfig
import providers
import os

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

PROVIDER_DISPATCH = {
    "llm_agent": ("get_llm_provider", "call_llm"),
    "generator_agent": ("get_image_provider", "generate_image"),
    "critic_agent": ("get_critic_provider", "critique_image"),
}

def run_agent(config: AgentConfig, context: dict) -> dict:
    if config.type not in PROVIDER_DISPATCH:
        raise ValueError(f"Unknown agent type: {config.type}")
    getter_name, _ = PROVIDER_DISPATCH[config.type]
    provider = getattr(providers, getter_name)(config.model_provider)
    inputs = _resolve_inputs(config, context)
    result = _call_provider(config, provider, inputs)
    context = _set_outputs(config, context, result)
    return context

def _resolve_inputs(config: AgentConfig, context: dict) -> dict:
    out = {}
    for spec in config.inputs:
        v = context.get(spec["source"])
        if v is None and spec.get("fallback"):
            v = context.get(spec["fallback"])
        if v is None and not spec.get("optional", False):
            v = spec.get("default")
        if spec.get("combine_with") and v is not None:
            sep = spec.get("separator", "\n\n")
            parts = [v] + [context[k] for k in spec["combine_with"] if context.get(k)]
            v = sep.join(parts)
        out[spec["name"]] = v
    return out

def _call_provider(config: AgentConfig, provider, inputs: dict):
    if config.type == "llm_agent":
        # LLMs receive a system instruction + collapsed user message + model params.
        # All data inputs are joined into the user message.
        user_message = "\n\n".join(str(v) for v in inputs.values() if v is not None)
        return provider.call_llm(
            config.instruction, user_message,
            config.model_name, config.temperature, config.max_tokens,
        )
    elif config.type == "generator_agent":
        # generator_agent: add model_name to inputs
        _, func_name = PROVIDER_DISPATCH[config.type]
        return getattr(provider, func_name)(model_name=config.model_name, **inputs)
    else:
        # critic_agent: YAML input names match provider kwarg names.
        _, func_name = PROVIDER_DISPATCH[config.type]
        return getattr(provider, func_name)(**inputs)

def _set_outputs(config: AgentConfig, context: dict, result) -> dict:
    for spec in config.outputs:
        context[spec["target"]] = result
        if spec.get("save_to_disk") and result is not None:
            path = os.path.join(OUTPUTS_DIR, os.path.basename(spec["save_to_disk"]))
            os.makedirs(OUTPUTS_DIR, exist_ok=True)
            result.save(path)
            context[spec["target"] + "_path"] = path
    return context

def apply_fixes(image, fix_prompts: list, aspect_ratio: str, provider_name: str, model_name: str):
    """Inpainting helper used by the image generation pipeline."""
    provider = providers.get_image_provider(provider_name)
    fixed = provider.inpaint_image(image, fix_prompts, aspect_ratio, model_name)
    path = os.path.join(OUTPUTS_DIR, "fixes_applied.png")
    fixed.save(path)
    return fixed, path
