from PIL import Image, ImageDraw, ImageFont
from schemas import RegionalFix
from typing import List

SEVERITY_COLORS = {"high": "red", "medium": "orange", "low": "yellow"}

def crop_region(image: Image.Image, bbox: tuple) -> Image.Image:
    return image.crop(bbox)

def create_mask(size: tuple, bbox: tuple) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(bbox, fill=255)
    return mask

def recomposite(base: Image.Image, patch: Image.Image, bbox: tuple) -> Image.Image:
    result = base.copy()
    patch_resized = patch.resize((bbox[2] - bbox[0], bbox[3] - bbox[1]))
    result.paste(patch_resized, (bbox[0], bbox[1]))
    return result

def annotate_bboxes(image: Image.Image, fixes: List[RegionalFix]) -> Image.Image:
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    for fix in fixes:
        color = SEVERITY_COLORS[fix.severity]
        draw.rectangle(fix.bbox, outline=color, width=3)
        draw.text((fix.bbox[0] + 4, fix.bbox[1] + 4), fix.region_id, fill=color)
    return annotated
