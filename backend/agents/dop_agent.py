import google.generativeai as genai
from models.base import PipelineAgent
from models.pipeline_context import PipelineContext
from config import Config

class DopAgent(PipelineAgent):
    @property
    def name(self) -> str:
        return "dop"

    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel("gemini-3.1-pro-preview")

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system_prompt = """You are a director of photography (DOP). Your job is to define the technical shot specifications for an image.

From the prompt and style brief provided, define:
- Camera angle: Eye-level, low angle, high angle, bird's eye, worm's eye, etc.
- Focal length feel: Wide angle, normal, telephoto compression
- Depth of field: Shallow (bokeh background), deep (everything sharp), etc.
- Lighting setup: Key light direction, fill light, practical lights, shadows
- Composition notes: Rule of thirds, centered, symmetrical, leading lines, etc.

Return ONLY a terse brief as one short paragraph. No preamble."""

        input_prompt = ctx.enriched_prompt or ctx.original_prompt
        style_context = f"\nStyle brief: {ctx.style_brief}" if ctx.style_brief else ""
        user_message = f"Prompt: {input_prompt}{style_context}\n\nDefine the shot specifications."

        response = self.model.generate_content(f"{system_prompt}\n\n{user_message}")
        ctx.shot_brief = response.text.strip()

        return ctx
