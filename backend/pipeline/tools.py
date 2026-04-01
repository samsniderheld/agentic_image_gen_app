from models.registry import get_generator
from schemas import Fix
from config import config
from PIL import Image
import json
import state

def apply_all_fixes(image_path: str, fixes_json: str, tool_context=None) -> dict:
    """Apply all fixes to the entire image using inpainting with full mask."""
    image = Image.open(image_path)
    fixes_data = json.loads(fixes_json)

    # Build comprehensive fix prompt
    fix_instructions = []
    for i, fix_data in enumerate(fixes_data):
        fix = Fix(**fix_data)
        severity_label = fix.severity.upper()
        fix_instructions.append(f"Fix {i+1} [{severity_label}]: {fix.fix_prompt}")

    combined_prompt = "Apply these fixes to the image:\n" + "\n".join(fix_instructions)
    combined_prompt += "\n\nReturn the corrected image with all fixes applied."

    # Apply fixes to entire image using inpainting with full mask
    aspect_ratio = state.pipeline.get("aspect_ratio", "1:1")
    fixed_image = get_generator().inpaint(
        image=image,
        mask=Image.new("L", image.size, 255),  # Full mask (edit entire image)
        prompt=combined_prompt,
        aspect_ratio=aspect_ratio
    )

    # Save result
    result_path = str(config.OUTPUT_DIR / "fixes_applied.png")
    fixed_image.save(result_path)

    return {"fixed_image_path": result_path}

# Registry for backwards compatibility
TOOL_REGISTRY = {
    "apply_all_fixes": apply_all_fixes,
}
