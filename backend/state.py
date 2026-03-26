pipeline = {
    "stage": "idle",
    "request": None,
    "current_image": None,     # PIL.Image
    "input_images": [],        # List[PIL.Image] - input images for composition
    "critique": None,
    "approved_fixes": [],
    "pending_fix_index": 0,
    "last_patch": None,        # PIL.Image
}

def reset():
    pipeline.update({
        "stage": "idle", "request": None, "current_image": None,
        "input_images": [], "critique": None, "approved_fixes": [],
        "pending_fix_index": 0, "last_patch": None,
    })
