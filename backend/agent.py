from factory import ModelFactory
from pipeline.composer import crop_region, create_mask, recomposite, annotate_bboxes
from schemas import GenerationRequest, CritiqueResult, RegionalFix
from pathlib import Path
from PIL import Image
from typing import List

def step_generate(request: GenerationRequest, out_dir: Path, input_images: List[Image.Image] = None) -> Image.Image:
    # Generate image with optional input images for composition
    image = ModelFactory.get_generator().generate(
        request.prompt,
        request.aspect_ratio,
        input_images=input_images
    )
    image.save(out_dir / "00_initial.png")

    # Save input images for reference if provided
    if input_images and len(input_images) > 0:
        for idx, inp_img in enumerate(input_images):
            inp_img.save(out_dir / f"input_{idx}.png")

    return image

def step_critique(image: Image.Image, prompt: str, out_dir: Path, input_images: List[Image.Image] = None) -> CritiqueResult:
    # Critique with awareness of input images
    result = ModelFactory.get_critic().critique(image, prompt, input_images=input_images)
    annotate_bboxes(image, result.fixes_required).save(out_dir / "01_annotated.png")
    return result

def step_apply_fix(image: Image.Image, fix: RegionalFix, out_dir: Path, idx: int) -> Image.Image:
    mask = create_mask(image.size, fix.bbox)
    patch = crop_region(ModelFactory.get_generator().inpaint(image, mask, fix.fix_prompt), fix.bbox)
    crop_region(image, fix.bbox).save(out_dir / f"fix_{idx}_original.png")
    patch.save(out_dir / f"fix_{idx}_patch.png")
    return patch

def step_accept_fix(image: Image.Image, patch: Image.Image, fix: RegionalFix, out_dir: Path, idx: int) -> Image.Image:
    result = recomposite(image, patch, fix.bbox)
    result.save(out_dir / f"fix_{idx}_composited.png")
    return result
