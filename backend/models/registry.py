from config import Config
from models.base import ImageGenerator, ImageCritic, PipelineAgent
from models.generators.gemini import GeminiGenerator
from models.critics.gemini import GeminiCritic
from agents.generator_agent import GeneratorAgent
from agents.critic_agent import CriticAgent
from agents.planner_agent import PlannerAgent
from agents.art_director_agent import ArtDirectorAgent
from agents.dop_agent import DopAgent

_GENERATORS: dict[str, type[ImageGenerator]] = {
    "gemini": GeminiGenerator,
    # "openai": OpenAIGenerator,  # add future backends here
}

_CRITICS: dict[str, type[ImageCritic]] = {
    "gemini": GeminiCritic,
    # "openai": OpenAICritic,
}

# Pipeline agent registry
_AGENTS: dict[str, type[PipelineAgent]] = {
    "generator":    GeneratorAgent,
    "critic":       CriticAgent,
    "planner":      PlannerAgent,
    "art_director": ArtDirectorAgent,
    "dop":          DopAgent,
}

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
    Instantiate agents in the order specified by Config.PIPELINE.
    Raises ValueError for unknown agent names.
    """
    pipeline = []
    for name in Config.PIPELINE:
        name = name.strip()
        if name not in _AGENTS:
            raise ValueError(
                f"Unknown agent '{name}' in PIPELINE. "
                f"Valid options: {list(_AGENTS.keys())}"
            )
        pipeline.append(_AGENTS[name]())
    return pipeline
