from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from config import config
import state, agent
from schemas import GenerationRequest, RegionalFix
from PIL import Image
import io
import base64
from pathlib import Path

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app)

OUT = config.OUTPUT_DIR
OUT.mkdir(exist_ok=True)

# Path to frontend build directory
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

@app.get("/api/status")
def status():
    return jsonify({"stage": state.pipeline["stage"]})

@app.post("/api/generate")
def generate():
    state.reset()
    data = request.json

    # Handle base64 encoded input images
    input_images = []
    if "input_images" in data and data["input_images"]:
        for img_b64 in data["input_images"]:
            # Decode base64 string to image
            img_data = base64.b64decode(img_b64.split(',')[1] if ',' in img_b64 else img_b64)
            img = Image.open(io.BytesIO(img_data))
            input_images.append(img)

    # Remove input_images from data before creating GenerationRequest
    request_data = {k: v for k, v in data.items() if k != "input_images"}
    req = GenerationRequest(**request_data)

    state.pipeline.update(request=req.model_dump(), stage="generating", input_images=input_images)

    # Step 1: Generate image
    image = agent.step_generate(req, OUT, input_images=input_images)
    state.pipeline.update(current_image=image)

    # Step 2: Automatically run critique (no human intervention)
    result = agent.step_critique(
        image,
        req.prompt,
        OUT,
        input_images=input_images
    )
    state.pipeline.update(critique=result.model_dump(), stage="awaiting_fix_review")

    # Return URLs for input images if any
    input_urls = [f"/outputs/input_{i}.png" for i in range(len(input_images))]

    return jsonify({
        "image_url": "/outputs/00_initial.png",
        "input_image_urls": input_urls,
        "critique": result.model_dump(),
        "annotated_url": "/outputs/01_annotated.png",
        "stage": "awaiting_fix_review"
    })

# Route removed - critique now happens automatically in /api/generate

@app.post("/api/review/fixes")
def review_fixes():
    approved_ids = request.json["approved_fix_ids"]
    # Preserve the original order from fixes_required
    approved = [f for f in state.pipeline["critique"]["fixes_required"]
                if f["region_id"] in approved_ids]

    # Debug: log the order
    print(f"Approved fixes in order: {[f['region_id'] for f in approved]}")

    state.pipeline.update(approved_fixes=approved, pending_fix_index=0)
    if not approved:
        state.pipeline["current_image"].save(OUT / "final.png")
        state.pipeline["stage"] = "done"
        return jsonify({"stage": "done", "final_url": "/outputs/final.png"})
    return _apply_next_fix()

@app.post("/api/fix/accept")
def accept_fix():
    idx = state.pipeline["pending_fix_index"]
    if request.json["accepted"]:
        fix = RegionalFix(**state.pipeline["approved_fixes"][idx])
        state.pipeline["current_image"] = agent.step_accept_fix(
            state.pipeline["current_image"], state.pipeline["last_patch"], fix, OUT, idx)
    state.pipeline["pending_fix_index"] += 1
    if state.pipeline["pending_fix_index"] >= len(state.pipeline["approved_fixes"]):
        state.pipeline["current_image"].save(OUT / "final.png")
        state.pipeline["stage"] = "done"
        return jsonify({"stage": "done", "final_url": "/outputs/final.png"})
    return _apply_next_fix()

def _apply_next_fix():
    idx = state.pipeline["pending_fix_index"]
    fix = RegionalFix(**state.pipeline["approved_fixes"][idx])

    # Debug: log which fix we're applying
    print(f"Applying fix {idx}: {fix.region_id} - {fix.issue_description}")

    patch = agent.step_apply_fix(state.pipeline["current_image"], fix, OUT, idx)
    state.pipeline.update(last_patch=patch, stage="awaiting_patch_review")
    return jsonify({
        "stage": "awaiting_patch_review",
        "fix_index": idx,
        "total_fixes": len(state.pipeline["approved_fixes"]),
        "original_url": f"/outputs/fix_{idx}_original.png",
        "patch_url": f"/outputs/fix_{idx}_patch.png",
        "fix": fix.model_dump(),
    })

@app.get("/outputs/<filename>")
def serve_output(filename):
    return send_from_directory(OUT, filename)

# Serve React frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    # If requesting a file that exists in dist, serve it
    if path and (FRONTEND_DIST / path).exists():
        return send_from_directory(FRONTEND_DIST, path)
    # Otherwise serve index.html (for React Router)
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        return send_file(FRONTEND_DIST / "index.html")
    else:
        return jsonify({
            "error": "Frontend not built",
            "message": "Run 'cd frontend && npm run build' to build the frontend first"
        }), 404

if __name__ == "__main__":
    app.run(debug=True, port=8000, host='0.0.0.0')
