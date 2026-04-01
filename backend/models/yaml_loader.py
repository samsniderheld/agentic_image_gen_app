"""
YAML-based agent configuration loader.
Loads agent configurations from YAML files and creates agent instances.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, List
import google.generativeai as genai
from models.base import PipelineAgent
from models.pipeline_context import PipelineContext
from config import Config

# Avoid circular import - import registry functions lazily when needed

AGENTS_DIR = Path(__file__).parent.parent / "agents"
CONFIG_DIR = Path(__file__).parent.parent / "config"


class YAMLAgentConfig:
    """Represents a loaded agent configuration from YAML."""

    def __init__(self, config_dict: Dict[str, Any]):
        self.config = config_dict
        self.name = config_dict["name"]
        self.display_name = config_dict.get("display_name", self.name.title())
        self.description = config_dict.get("description", "")
        self.agent_type = config_dict.get("type", "llm_agent")

        # Model config
        self.model_config = config_dict.get("model", {})
        self.provider = self.model_config.get("provider", "gemini")
        self.model_name = self.model_config.get("name", "gemini-3.1-pro-preview")
        self.temperature = self.model_config.get("temperature", 0.7)
        self.max_tokens = self.model_config.get("max_tokens", 2048)

        # Instructions
        self.instruction = config_dict.get("instruction", "")

        # I/O config
        self.inputs = config_dict.get("inputs", [])
        self.outputs = config_dict.get("outputs", [])

        # HITL config
        self.hitl = config_dict.get("hitl", {})
        self.hitl_enabled = self.hitl.get("enabled", False)

        # Behaviors
        self.behaviors = config_dict.get("behaviors", {})

    def get_hitl_config(self) -> Dict[str, Any]:
        """Get HITL configuration for AGENT_CONFIG."""
        if not self.hitl_enabled:
            return None

        output_field = None
        output_label = self.hitl.get("output_label", "Output")

        # Extract output field from outputs
        for output in self.outputs:
            if output.get("target", "").startswith("context."):
                output_field = output["target"].replace("context.", "")
                break

        return {
            "output_field": output_field,
            "output_label": output_label,
            "thinking_revise": self.hitl.get("thinking_revise_message", "Revising..."),
            "approval_message": self.hitl.get("approval_message", "Approved."),
            "next_agent": self.hitl.get("next_agent"),
            "next_stage": self.hitl.get("next_stage"),
            "next_label": self.hitl.get("next_label", "Continue"),
            "feedback_to_field": self.hitl.get("feedback_target"),
        }


class ConfigurableAgent(PipelineAgent):
    """A pipeline agent created from YAML configuration."""

    def __init__(self, config: YAMLAgentConfig):
        self.config = config
        self._model = None
        self._backend = None

    @property
    def name(self) -> str:
        return self.config.name

    def _get_model(self):
        """Lazy-load the LLM model."""
        if self._model is None and self.config.provider == "gemini":
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            self._model = genai.GenerativeModel(self.config.model_name)
        return self._model

    def _get_backend(self):
        """Lazy-load the backend (for generator/critic agents)."""
        if self._backend is None:
            # Lazy import to avoid circular dependency
            from models.registry import get_generator, get_critic

            if self.config.agent_type == "generator_agent":
                self._backend = get_generator()
            elif self.config.agent_type == "critic_agent":
                self._backend = get_critic()
        return self._backend

    def _get_input_value(self, input_spec: Dict[str, Any], ctx: PipelineContext) -> Any:
        """Extract input value from context based on input spec."""
        source = input_spec.get("source", "")

        # Extract from context
        if source.startswith("context."):
            field_name = source.replace("context.", "")
            value = getattr(ctx, field_name, None)

            # Try fallback if value is None
            if value is None and "fallback" in input_spec:
                fallback_source = input_spec["fallback"]
                if fallback_source.startswith("context."):
                    fallback_field = fallback_source.replace("context.", "")
                    value = getattr(ctx, fallback_field, None)

            # Use default if still None and not optional
            if value is None and not input_spec.get("optional", False):
                value = input_spec.get("default")

            return value

        return None

    def _set_output_value(self, output_spec: Dict[str, Any], ctx: PipelineContext, value: Any):
        """Set output value in context based on output spec."""
        target = output_spec.get("target", "")

        if target.startswith("context."):
            field_path = target.replace("context.", "")

            # Handle nested paths (e.g., metadata.final_generation_prompt)
            if "." in field_path:
                parts = field_path.split(".")
                obj = getattr(ctx, parts[0])
                for part in parts[1:-1]:
                    obj = obj[part]

                if output_spec.get("append", False):
                    if isinstance(obj, list):
                        obj.append(value)
                    else:
                        obj[parts[-1]] = value
                else:
                    obj[parts[-1]] = value
            else:
                # Direct field
                if output_spec.get("append", False):
                    field_value = getattr(ctx, field_path, [])
                    if isinstance(field_value, list):
                        field_value.append(value)
                    else:
                        setattr(ctx, field_path, value)
                else:
                    setattr(ctx, field_path, value)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        """Execute the agent based on its type and configuration."""

        if self.config.agent_type == "llm_agent":
            return self._run_llm_agent(ctx)
        elif self.config.agent_type == "generator_agent":
            return self._run_generator_agent(ctx)
        elif self.config.agent_type == "critic_agent":
            return self._run_critic_agent(ctx)
        else:
            raise ValueError(f"Unknown agent type: {self.config.agent_type}")

    def _run_llm_agent(self, ctx: PipelineContext) -> PipelineContext:
        """Run an LLM-based agent."""
        # Gather inputs
        inputs = {}
        for input_spec in self.config.inputs:
            input_name = input_spec["name"]
            inputs[input_name] = self._get_input_value(input_spec, ctx)

        # Build prompt from inputs
        # For simple cases, just use the first input
        user_message = ""
        if len(self.config.inputs) == 1:
            input_spec = self.config.inputs[0]
            user_message = f"{input_spec['description']}: {inputs[input_spec['name']]}"
        else:
            # Combine multiple inputs
            parts = []
            for input_spec in self.config.inputs:
                value = inputs[input_spec["name"]]
                if value:
                    parts.append(f"{input_spec['description']}: {value}")
            user_message = "\n\n".join(parts)

        # Execute LLM
        model = self._get_model()
        full_prompt = f"{self.config.instruction}\n\n{user_message}"
        response = model.generate_content(full_prompt)
        result_text = response.text.strip()

        # Set outputs
        for output_spec in self.config.outputs:
            self._set_output_value(output_spec, ctx, result_text)

        return ctx

    def _run_generator_agent(self, ctx: PipelineContext) -> PipelineContext:
        """Run the generator agent."""
        # Gather inputs
        inputs = {}
        for input_spec in self.config.inputs:
            inputs[input_spec["name"]] = self._get_input_value(input_spec, ctx)

        # Combine prompts if configured
        if self.config.behaviors.get("combine_prompts", False):
            parts = []
            separator = self.config.behaviors.get("separator", "\n\n")

            for key in ["enriched_prompt", "style_brief", "shot_brief"]:
                if key in inputs and inputs[key]:
                    parts.append(inputs[key])

            final_prompt = separator.join(parts)
        else:
            final_prompt = inputs.get("enriched_prompt") or inputs.get("original_prompt", "")

        # Generate image
        backend = self._get_backend()
        aspect_ratio = inputs.get("aspect_ratio", "1:1")
        image = backend.generate(final_prompt, aspect_ratio)

        # Set outputs
        for output_spec in self.config.outputs:
            if output_spec["name"] == "image":
                self._set_output_value(output_spec, ctx, image)
            elif output_spec["name"] == "final_generation_prompt":
                self._set_output_value(output_spec, ctx, final_prompt)

        return ctx

    def _run_critic_agent(self, ctx: PipelineContext) -> PipelineContext:
        """Run the critic agent."""
        # Gather inputs
        inputs = {}
        for input_spec in self.config.inputs:
            inputs[input_spec["name"]] = self._get_input_value(input_spec, ctx)

        # Run critique
        backend = self._get_backend()
        result = backend.critique(inputs["image"], inputs["original_prompt"])

        # Set outputs
        for output_spec in self.config.outputs:
            self._set_output_value(output_spec, ctx, result)

        return ctx


def load_agent_config(agent_name: str) -> YAMLAgentConfig:
    """Load agent configuration from YAML file."""
    yaml_path = AGENTS_DIR / f"{agent_name}.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Agent config not found: {yaml_path}")

    with open(yaml_path, 'r') as f:
        config_dict = yaml.safe_load(f)

    return YAMLAgentConfig(config_dict)


def create_agent_from_yaml(agent_name: str) -> ConfigurableAgent:
    """Create an agent instance from its YAML configuration."""
    config = load_agent_config(agent_name)
    return ConfigurableAgent(config)


def load_pipeline_config() -> Dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    pipeline_path = CONFIG_DIR / "pipeline.yaml"

    if not pipeline_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {pipeline_path}")

    with open(pipeline_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def build_pipeline_from_yaml() -> List[PipelineAgent]:
    """Build the agent pipeline from YAML configuration."""
    pipeline_config = load_pipeline_config()

    # Get active pipeline name
    active_name = pipeline_config.get("active_pipeline", "pipeline")

    # Get agent list
    if active_name == "pipeline":
        agent_names = pipeline_config["pipeline"]["agents"]
    else:
        agent_names = pipeline_config["pipelines"][active_name]["agents"]

    # Create agents
    agents = []
    for agent_name in agent_names:
        agent = create_agent_from_yaml(agent_name)
        agents.append(agent)

    return agents


def build_agent_config_dict() -> Dict[str, Dict[str, Any]]:
    """Build AGENT_CONFIG dictionary from YAML files for HITL workflow."""
    pipeline_config = load_pipeline_config()
    active_name = pipeline_config.get("active_pipeline", "pipeline")

    if active_name == "pipeline":
        agent_names = pipeline_config["pipeline"]["agents"]
    else:
        agent_names = pipeline_config["pipelines"][active_name]["agents"]

    agent_config_dict = {}

    for agent_name in agent_names:
        config = load_agent_config(agent_name)
        hitl_config = config.get_hitl_config()

        if hitl_config:
            agent_config_dict[agent_name] = hitl_config

    return agent_config_dict
