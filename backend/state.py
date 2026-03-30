from PIL import Image

pipeline = {
    "stage":               "idle",
    "request":             None,
    "current_image":       None,   # PIL.Image — never serialized
    "critique":            None,
    "approved_fixes":      [],
    "pending_fix_index":   0,
    "last_patch":          None,   # PIL.Image
    "messages":            [],     # chat message dicts appended by routes
}

def reset():
    pipeline.update({
        "stage": "idle", "request": None, "current_image": None,
        "critique": None, "approved_fixes": [], "pending_fix_index": 0,
        "last_patch": None, "messages": [],
    })

def push_message(msg: dict):
    pipeline["messages"].append(msg)
