from config import Config
from models.base import ImageGenerator, ImageCritic, PipelineAgent
from models.generators.gemini import GeminiGenerator
from models.critics.gemini import GeminiCritic

# Import YAML loader for configuration-driven agents
from models.yaml_loader import build_pipeline_from_yaml

# Legacy agent imports (kept for backwards compatibility)
# from agents.generator_agent import GeneratorAgent
# from agents.critic_agent import CriticAgent
# from agents.planner_agent import PlannerAgent
# from agents.art_director_agent import ArtDirectorAgent
# from agents.dop_agent import DopAgent

_GENERATORS: dict[str, type[ImageGenerator]] = {
    "gemini": GeminiGenerator,
    # "openai": OpenAIGenerator,  # add future backends here
}

_CRITICS: dict[str, type[ImageCritic]] = {
    "gemini": GeminiCritic,
    # "openai": OpenAICritic,
}

# Pipeline agent registry - now loaded from YAML
# _AGENTS: dict[str, type[PipelineAgent]] = {
#     "generator":    GeneratorAgent,
#     "critic":       CriticAgent,
#     "planner":      PlannerAgent,
#     "art_director": ArtDirectorAgent,
#     "dop":          DopAgent,
# }

def get_generator() -> ImageGenerator:
    key = Config.GENERATOR_BACKEND
    if key not in _GENERATORS:
        raise ValueError(f"Unknown generator backend: '{key}'. Choose from: {list(_GENERATORS)}")
    # Instantiate with config
    if key == "gemini":
        return GeminiGenerator(
            api_key=Config.GOOGLE_API_KEY,
            model_name="gemini-3-pro-image-preview"
        )
    raise NotImplementedError(f"Backend '{key}' not fully configured")

def get_critic() -> ImageCritic:
    key = Config.CRITIC_BACKEND
    if key not in _CRITICS:
        raise ValueError(f"Unknown critic backend: '{key}'. Choose from: {list(_CRITICS)}")
    # Instantiate with config
    if key == "gemini":
        return GeminiCritic(
            api_key=Config.GOOGLE_API_KEY,
            model_name="gemini-3.1-pro-preview"
        )
    raise NotImplementedError(f"Backend '{key}' not fully configured")


def build_pipeline() -> list[PipelineAgent]:
    """
    Build pipeline from YAML configuration.
    Loads agents from config/pipeline.yaml and agents/*.yaml files.
    """
    return build_pipeline_from_yaml()
