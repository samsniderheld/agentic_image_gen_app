from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from factory import ModelFactory
from pipeline.composer import crop_region, create_mask, recomposite
from schemas import RegionalFix
from config import config
from PIL import Image
import json

def generate_image(prompt: str, aspect_ratio: str, tool_context: ToolContext) -> dict:
    """Generate full image. Saves to outputs/00_initial.png."""
    image = ModelFactory.get_generator().generate(prompt, aspect_ratio)
    path = str(config.OUTPUT_DIR / "00_initial.png")
    image.save(path)
    return {"image_path": path}

def critique_image(image_path: str, prompt: str, tool_context: ToolContext) -> dict:
    """Critique image against prompt. Returns CritiqueResult as dict."""
    from pipeline.composer import annotate_bboxes
    from schemas import CritiqueResult

    image = Image.open(image_path)
    result = ModelFactory.get_critic().critique(image, prompt)

    # Save annotated image with bounding boxes
    critique_obj = CritiqueResult(**result.model_dump())
    annotated = annotate_bboxes(image, critique_obj.fixes_required)
    annotated.save(str(config.OUTPUT_DIR / "01_annotated.png"))

    return result.model_dump()

def apply_fix(image_path: str, fix_json: str, fix_index: int, tool_context: ToolContext) -> dict:
    """Inpaint one fix region. Saves original crop + patch. Returns their paths."""
    image = Image.open(image_path)
    fix = RegionalFix(**json.loads(fix_json))
    mask = create_mask(image.size, fix.bbox)
    patched = ModelFactory.get_generator().inpaint(image, mask, fix.fix_prompt)
    patch = crop_region(patched, fix.bbox)
    orig_path  = str(config.OUTPUT_DIR / f"fix_{fix_index}_original.png")
    patch_path = str(config.OUTPUT_DIR / f"fix_{fix_index}_patch.png")
    crop_region(image, fix.bbox).save(orig_path)
    patch.save(patch_path)
    return {"patch_path": patch_path, "original_crop_path": orig_path}

def apply_all_fixes(image_path: str, fixes_json: str, tool_context: ToolContext) -> dict:
    """Apply all fixes at once by sending annotated image to generator with fix instructions."""
    from PIL import ImageDraw

    image = Image.open(image_path)
    fixes_data = json.loads(fixes_json)

    # Create annotated image with all fixes marked
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)

    # Draw all bounding boxes and labels
    SEVERITY_COLORS = {"high": "red", "medium": "orange", "low": "yellow"}
    for i, fix_data in enumerate(fixes_data):
        fix = RegionalFix(**fix_data)
        color = SEVERITY_COLORS[fix.severity]
        draw.rectangle(fix.bbox, outline=color, width=3)
        # Add fix number label
        draw.text((fix.bbox[0] + 4, fix.bbox[1] + 4), f"Fix {i+1}", fill=color)

    # Save annotated image for reference
    annotated_path = str(config.OUTPUT_DIR / "fixes_annotated.png")
    annotated.save(annotated_path)

    # Build comprehensive fix prompt
    fix_instructions = []
    for i, fix_data in enumerate(fixes_data):
        fix = RegionalFix(**fix_data)
        fix_instructions.append(f"Fix {i+1} (marked in {SEVERITY_COLORS[fix.severity]}): {fix.fix_prompt}")

    combined_prompt = "Apply these fixes to the image:\n" + "\n".join(fix_instructions)
    combined_prompt += "\n\nReturn the corrected image with all fixes applied."

    # Send annotated image + original image + fix instructions to generator
    fixed_image = ModelFactory.get_generator().inpaint(
        image=annotated,  # Send annotated version so model can see what to fix
        mask=Image.new("L", image.size, 255),  # Full mask (edit entire image)
        prompt=combined_prompt
    )

    # Save result
    result_path = str(config.OUTPUT_DIR / "fixes_applied.png")
    fixed_image.save(result_path)

    return {
        "fixed_image_path": result_path,
        "annotated_reference_path": annotated_path
    }

def exit_loop(tool_context: ToolContext) -> dict:
    """Signal LoopAgent to stop. Call when all fixes are exhausted."""
    tool_context.actions.escalate = True
    return {}

TOOL_REGISTRY = {
    "generate_image": generate_image,
    "critique_image": critique_image,
    "apply_fix":      apply_fix,
    "apply_all_fixes": apply_all_fixes,
    "exit_loop":      exit_loop,
}

def get_tool(name: str) -> FunctionTool:
    return FunctionTool(TOOL_REGISTRY[name])
