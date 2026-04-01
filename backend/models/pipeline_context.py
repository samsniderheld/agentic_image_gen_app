from dataclasses import dataclass, field
from PIL import Image

@dataclass
class PipelineContext:
    # Set by the user at the start of a run
    original_prompt: str
    aspect_ratio: str = "1:1"
    seed: int | None = None

    # Populated by pre-generation agents
    enriched_prompt: str | None = None      # planner output
    style_brief: str | None = None          # art director output
    shot_brief: str | None = None           # DOP output

    # Populated by the generator agent
    image: Image.Image | None = None

    # Populated by post-generation agents
    critiques: list[dict] = field(default_factory=list)  # each critic/reviewer appends here

    # Catch-all for any agent to store arbitrary metadata
    metadata: dict = field(default_factory=dict)
