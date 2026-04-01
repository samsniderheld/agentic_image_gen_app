from models.base import PipelineAgent
from models.pipeline_context import PipelineContext

class GeneratorAgent(PipelineAgent):
    @property
    def name(self) -> str:
        return "generator"

    def __init__(self):
        self._backend = None

    def _get_backend(self):
        """Lazy-load backend to avoid circular imports."""
        if self._backend is None:
            from models.registry import get_generator
            self._backend = get_generator()
        return self._backend

    def run(self, ctx: PipelineContext) -> PipelineContext:
        # Assemble final prompt from all enrichment stages
        parts = [ctx.enriched_prompt or ctx.original_prompt]
        if ctx.style_brief:
            parts.append(ctx.style_brief)
        if ctx.shot_brief:
            parts.append(ctx.shot_brief)
        final_prompt = "\n\n".join(parts)

        # Generate the image
        backend = self._get_backend()
        ctx.image = backend.generate(final_prompt, ctx.aspect_ratio)

        # Store the final prompt used in metadata
        ctx.metadata["final_generation_prompt"] = final_prompt

        return ctx
