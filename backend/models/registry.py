from config import Config
from models.base import ImageGenerator, ImageCritic
from models.generators.gemini import GeminiGenerator
from models.critics.gemini import GeminiCritic

_GENERATORS: dict[str, type[ImageGenerator]] = {
    "gemini": GeminiGenerator,
    # "openai": OpenAIGenerator,  # add future backends here
}

_CRITICS: dict[str, type[ImageCritic]] = {
    "gemini": GeminiCritic,
    # "openai": OpenAICritic,
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
