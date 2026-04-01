from models.base import PipelineAgent
from models.pipeline_context import PipelineContext

class CriticAgent(PipelineAgent):
    @property
    def name(self) -> str:
        return "critic"

    def __init__(self):
        self._backend = None

    def _get_backend(self):
        """Lazy-load backend to avoid circular imports."""
        if self._backend is None:
            from models.registry import get_critic
            self._backend = get_critic()
        return self._backend

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.image is None:
            raise RuntimeError("CriticAgent requires an image; generator must run first.")

        backend = self._get_backend()
        result = backend.critique(ctx.image, ctx.original_prompt)
        ctx.critiques.append({"agent": self.name, **result})

        return ctx
