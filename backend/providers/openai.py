# Set model.provider: openai in any agent YAML to route through this module.
# Requires OPENAI_API_KEY in .env
from PIL import Image

def call_llm(instruction, user_message, model_name, temperature, max_tokens, input_images=None) -> str:
    raise NotImplementedError("OpenAI LLM not yet implemented")

def generate_image(prompt, aspect_ratio, model_name, input_images=None) -> Image.Image:
    raise NotImplementedError("OpenAI image generation not yet implemented")

def inpaint_image(image, fix_prompts, aspect_ratio, model_name) -> Image.Image:
    raise NotImplementedError("OpenAI inpainting not yet implemented")

def infer_composition_prompt(images) -> str:
    raise NotImplementedError("OpenAI composition prompt not yet implemented")

def critique_image(image, original_prompt) -> dict:
    raise NotImplementedError("OpenAI critique not yet implemented")
