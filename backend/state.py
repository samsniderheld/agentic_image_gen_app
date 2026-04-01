from PIL import Image

pipeline = {
    "stage":               "idle",
    "request":             None,
    "current_image_path":  None,   # Path to current image (always the latest version)
    "original_image_path": None,   # Path to original generated image (for comparison)
    "input_images":        [],     # List[PIL.Image] - input images for composition
    "aspect_ratio":        "1:1",  # Store aspect ratio for consistent generation
    "critique":            None,
    "messages":            [],     # chat message dicts appended by routes

    # Pipeline context for HITL workflow
    "pipeline_context":    None,   # PipelineContext object stored between agent runs
}

def reset():
    pipeline.update({
        "stage": "idle", "request": None,
        "current_image_path": None, "original_image_path": None,
        "input_images": [], "aspect_ratio": "1:1", "critique": None,
        "messages": [], "pipeline_context": None,
    })

def push_message(msg: dict):
    pipeline["messages"].append(msg)
