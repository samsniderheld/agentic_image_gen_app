import google.generativeai as genai
from models.base import PipelineAgent
from models.pipeline_context import PipelineContext
from config import Config

class PlannerAgent(PipelineAgent):
    @property
    def name(self) -> str:
        return "planner"

    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel("gemini-3.1-pro-preview")

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system_prompt = """You are a creative planner for image generation. Your job is to expand terse user prompts into detailed, specific generation briefs.

Include:
- Subject: What is the main focus?
- Action: What is happening?
- Setting: Where is this taking place?
- Mood: What emotional tone should the image convey?
- Lighting style: What kind of lighting (natural, dramatic, soft, etc.)?
- Color palette: What colors dominate the scene?

Return ONLY the enriched prompt as a single paragraph. No preamble, no explanations, just the enhanced prompt."""

        user_message = f"Original prompt: {ctx.original_prompt}\n\nExpand this into a detailed generation brief."

        response = self.model.generate_content(f"{system_prompt}\n\n{user_message}")
        ctx.enriched_prompt = response.text.strip()

        return ctx
