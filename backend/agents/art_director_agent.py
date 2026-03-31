import google.generativeai as genai
from models.base import PipelineAgent
from models.pipeline_context import PipelineContext
from config import Config

class ArtDirectorAgent(PipelineAgent):
    @property
    def name(self) -> str:
        return "art_director"

    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel("gemini-3.1-pro-preview")

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system_prompt = """You are an experienced art director. Your job is to define the visual style for an image generation.

From the prompt provided, define:
- Medium: Is this an oil painting, photograph, digital illustration, 3D render, watercolor, etc.?
- Color grading: What is the color treatment (warm, cool, desaturated, vibrant, etc.)?
- Texture: What surface qualities should be present?
- Art movement or style references: Any specific artistic styles or movements that apply?

Return ONLY a terse brief as one short paragraph. No preamble."""

        input_prompt = ctx.enriched_prompt or ctx.original_prompt
        user_message = f"Prompt: {input_prompt}\n\nDefine the visual style."

        response = self.model.generate_content(f"{system_prompt}\n\n{user_message}")
        ctx.style_brief = response.text.strip()

        return ctx
