from pydantic import BaseModel
from typing import Optional, Tuple, List, Literal

class GenerationRequest(BaseModel):
    prompt: str = ""  # Can be empty if images are provided for inference
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3"] = "1:1"
    seed: Optional[int] = None
    input_image_paths: List[str] = []  # Paths to input images for composition

class Fix(BaseModel):
    fix_id: str
    severity: Literal["low", "medium", "high"]
    issue_description: str
    fix_prompt: str

class ImageIntegration(BaseModel):
    image_index: int
    integration_score: float               # 0.0 – 1.0
    integration_notes: str

class CritiqueResult(BaseModel):
    overall_score: float                   # 0.0 – 1.0
    overall_assessment: str
    fixes_required: List[Fix]
    pass_threshold_met: bool               # True if score >= 0.8
    image_integrations: List[ImageIntegration] = []  # How well each input image is integrated
