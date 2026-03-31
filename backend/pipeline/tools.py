from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from models.registry import get_generator, get_critic
from schemas import Fix
from config import config
from PIL import Image
import json
import state

def generate_image(prompt: str, aspect_ratio: str, tool_context: ToolContext) -> dict:
    """Generate full image. Saves to outputs/00_initial.png."""
    image = get_generator().generate(prompt, aspect_ratio)
    path = str(config.OUTPUT_DIR / "00_initial.png")
    image.save(path)
    return {"image_path": path}

def critique_image(image_path: str, prompt: str, tool_context: ToolContext) -> dict:
    """Critique image against prompt. Returns CritiqueResult as dict."""
    image = Image.open(image_path)
    result = get_critic().critique(image, prompt)

    # Just save a copy of the image for display (no annotations needed)
    image.save(str(config.OUTPUT_DIR / "01_annotated.png"))

    # result is already a dict from the ABC implementation
    return result

def apply_all_fixes(image_path: str, fixes_json: str, tool_context: ToolContext) -> dict:
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

def exit_loop(tool_context: ToolContext) -> dict:
    """Signal LoopAgent to stop. Call when all fixes are exhausted."""
    tool_context.actions.escalate = True
    return {}

TOOL_REGISTRY = {
    "generate_image": generate_image,
    "critique_image": critique_image,
    "apply_all_fixes": apply_all_fixes,
    "exit_loop":      exit_loop,
}

def get_tool(name: str) -> FunctionTool:
    return FunctionTool(TOOL_REGISTRY[name])
