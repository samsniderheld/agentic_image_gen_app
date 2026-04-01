from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from config import config
import state, agent
from schemas import GenerationRequest, Fix
import json
from pathlib import Path

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app)

OUT = config.OUTPUT_DIR
OUT.mkdir(exist_ok=True)

# Path to frontend build directory
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# ── Status ──────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    return jsonify({"stage": state.pipeline["stage"]})

# ── Generate ─────────────────────────────────────────────────────

@app.post("/api/generate")
def generate():
    import base64
    import io
    from PIL import Image
    from models.pipeline_context import PipelineContext
    from agent import run_pre_generation, run_generator

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

    state.pipeline.update(request=req.model_dump(), stage="running_planner", input_images=input_images, aspect_ratio=req.aspect_ratio)

    # Use new pipeline system with HITL gates
    ctx = PipelineContext(
        original_prompt=req.prompt,
        aspect_ratio=req.aspect_ratio
    )

    # Import and run just the planner agent
    from agent import get_pipeline
    pipeline = get_pipeline()

    # Find and run planner
    planner = next((a for a in pipeline if a.name == "planner"), None)
    if planner:
        state.push_message({"role": "agent", "type": "thinking",
            "content": "Planning and expanding prompt..."})
        ctx = planner.run(ctx)

    # Store context for next steps
    state.pipeline["pipeline_context"] = ctx

    # Show enriched prompt to user for review
    if ctx.enriched_prompt:
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Enriched prompt:**\n\n{ctx.enriched_prompt}"})

    # Ask for approval or feedback
    state.push_message({"role": "agent", "type": "options",
        "prompt": "Does this enriched prompt look good?",
        "options": [
            {"label": "✓ Approve - Continue to style", "value": "approve"},
            {"label": "✎ Give feedback", "value": "feedback"},
            {"label": "✕ Start over", "value": "reject"}
        ]})

    state.pipeline["stage"] = "awaiting_planner_review"
    return jsonify({"stage": state.pipeline["stage"],
                    "messages": state.pipeline["messages"]})

# ── Initial Review (HITL Gate 1) ──────────────────────────────────

@app.post("/api/review/initial")
def review_initial():
    decision   = request.json["decision"]
    new_prompt = request.json.get("new_prompt")

    if decision == "reject":
        state.push_message({"role": "user", "type": "text", "content": "Start over."})
        state.push_message({"role": "agent", "type": "text",
            "content": "No problem. What would you like to generate?"})
        state.reset()
        return jsonify({"stage": "idle", "messages": state.pipeline["messages"][-2:]})

    if decision == "edit":
        state.push_message({"role": "user", "type": "text", "content": "Edit the prompt."})
        state.push_message({"role": "agent", "type": "text",
            "content": "Sure! What would you like to change?"})
        state.push_message({"role": "agent", "type": "input_request",
            "placeholder": "Enter your updated prompt...", "action": "resubmit_prompt"})
        state.pipeline["stage"] = "awaiting_edit"
        return jsonify({"stage": "awaiting_edit",
                        "messages": state.pipeline["messages"][-3:]})

    # accept → run critique
    return run_critique(is_recritique=False)

# ── Pipeline Agent Reviews (HITL Gates) ───────────────────────────

@app.post("/api/review/planner")
def review_planner():
    """Review planner output and continue to art director."""
    from models.pipeline_context import PipelineContext
    from agent import get_pipeline

    decision = request.json["decision"]
    feedback = request.json.get("feedback")

    ctx = state.pipeline.get("pipeline_context")
    if not ctx:
        return jsonify({"error": "No pipeline context found"}), 400

    if decision == "reject":
        state.push_message({"role": "user", "type": "text", "content": "Start over."})
        state.reset()
        return jsonify({"stage": "idle", "messages": state.pipeline["messages"][-1:]})

    if decision == "feedback":
        state.push_message({"role": "user", "type": "text", "content": f"Feedback: {feedback}"})
        # Re-run planner with feedback
        state.push_message({"role": "agent", "type": "thinking", "content": "Revising enriched prompt based on your feedback..."})

        # Add feedback to the original prompt
        ctx.original_prompt = f"{ctx.original_prompt}\n\nUser feedback: {feedback}"

        pipeline = get_pipeline()
        planner = next((a for a in pipeline if a.name == "planner"), None)
        if planner:
            ctx = planner.run(ctx)

        state.pipeline["pipeline_context"] = ctx
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Revised enriched prompt:**\n\n{ctx.enriched_prompt}"})
        state.push_message({"role": "agent", "type": "options",
            "prompt": "Does this look better?",
            "options": [
                {"label": "✓ Approve - Continue to style", "value": "approve"},
                {"label": "✎ Give more feedback", "value": "feedback"},
                {"label": "✕ Start over", "value": "reject"}
            ]})
        return jsonify({"stage": "awaiting_planner_review", "messages": state.pipeline["messages"][-3:]})

    # approve → continue to art director
    state.push_message({"role": "user", "type": "text", "content": "Approved enriched prompt."})

    pipeline = get_pipeline()
    art_director = next((a for a in pipeline if a.name == "art_director"), None)
    if art_director:
        state.push_message({"role": "agent", "type": "thinking", "content": "Defining visual style..."})
        ctx = art_director.run(ctx)

    state.pipeline["pipeline_context"] = ctx

    if ctx.style_brief:
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Style brief:**\n\n{ctx.style_brief}"})

    state.push_message({"role": "agent", "type": "options",
        "prompt": "Does this visual style work?",
        "options": [
            {"label": "✓ Approve - Continue to shot setup", "value": "approve"},
            {"label": "✎ Give feedback", "value": "feedback"},
            {"label": "✕ Start over", "value": "reject"}
        ]})

    state.pipeline["stage"] = "awaiting_art_director_review"
    return jsonify({"stage": state.pipeline["stage"], "messages": state.pipeline["messages"][-4:]})


@app.post("/api/review/art_director")
def review_art_director():
    """Review art director output and continue to DOP."""
    from models.pipeline_context import PipelineContext
    from agent import get_pipeline

    decision = request.json["decision"]
    feedback = request.json.get("feedback")

    ctx = state.pipeline.get("pipeline_context")
    if not ctx:
        return jsonify({"error": "No pipeline context found"}), 400

    if decision == "reject":
        state.push_message({"role": "user", "type": "text", "content": "Start over."})
        state.reset()
        return jsonify({"stage": "idle", "messages": state.pipeline["messages"][-1:]})

    if decision == "feedback":
        state.push_message({"role": "user", "type": "text", "content": f"Feedback: {feedback}"})
        state.push_message({"role": "agent", "type": "thinking", "content": "Revising style brief based on your feedback..."})

        # Temporarily store feedback in metadata
        ctx.metadata["art_director_feedback"] = feedback

        pipeline = get_pipeline()
        art_director = next((a for a in pipeline if a.name == "art_director"), None)
        if art_director:
            # Modify enriched prompt with feedback for art director
            original_enriched = ctx.enriched_prompt
            ctx.enriched_prompt = f"{ctx.enriched_prompt}\n\nStyle feedback: {feedback}"
            ctx = art_director.run(ctx)
            ctx.enriched_prompt = original_enriched  # Restore

        state.pipeline["pipeline_context"] = ctx
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Revised style brief:**\n\n{ctx.style_brief}"})
        state.push_message({"role": "agent", "type": "options",
            "prompt": "Does this look better?",
            "options": [
                {"label": "✓ Approve - Continue to shot setup", "value": "approve"},
                {"label": "✎ Give more feedback", "value": "feedback"},
                {"label": "✕ Start over", "value": "reject"}
            ]})
        return jsonify({"stage": "awaiting_art_director_review", "messages": state.pipeline["messages"][-3:]})

    # approve → continue to DOP
    state.push_message({"role": "user", "type": "text", "content": "Approved style brief."})

    pipeline = get_pipeline()
    dop = next((a for a in pipeline if a.name == "dop"), None)
    if dop:
        state.push_message({"role": "agent", "type": "thinking", "content": "Setting up shot specifications..."})
        ctx = dop.run(ctx)

    state.pipeline["pipeline_context"] = ctx

    if ctx.shot_brief:
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Shot brief:**\n\n{ctx.shot_brief}"})

    state.push_message({"role": "agent", "type": "options",
        "prompt": "Does this shot setup work?",
        "options": [
            {"label": "✓ Approve - Generate image", "value": "approve"},
            {"label": "✎ Give feedback", "value": "feedback"},
            {"label": "✕ Start over", "value": "reject"}
        ]})

    state.pipeline["stage"] = "awaiting_dop_review"
    return jsonify({"stage": state.pipeline["stage"], "messages": state.pipeline["messages"][-4:]})


@app.post("/api/review/dop")
def review_dop():
    """Review DOP output and generate image."""
    from models.pipeline_context import PipelineContext
    from agent import get_pipeline, run_generator

    decision = request.json["decision"]
    feedback = request.json.get("feedback")

    ctx = state.pipeline.get("pipeline_context")
    if not ctx:
        return jsonify({"error": "No pipeline context found"}), 400

    if decision == "reject":
        state.push_message({"role": "user", "type": "text", "content": "Start over."})
        state.reset()
        return jsonify({"stage": "idle", "messages": state.pipeline["messages"][-1:]})

    if decision == "feedback":
        state.push_message({"role": "user", "type": "text", "content": f"Feedback: {feedback}"})
        state.push_message({"role": "agent", "type": "thinking", "content": "Revising shot brief based on your feedback..."})

        # Store feedback in metadata
        ctx.metadata["dop_feedback"] = feedback

        pipeline = get_pipeline()
        dop = next((a for a in pipeline if a.name == "dop"), None)
        if dop:
            # Add feedback context
            if ctx.style_brief:
                ctx.style_brief = f"{ctx.style_brief}\n\nShot feedback: {feedback}"
            ctx = dop.run(ctx)

        state.pipeline["pipeline_context"] = ctx
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Revised shot brief:**\n\n{ctx.shot_brief}"})
        state.push_message({"role": "agent", "type": "options",
            "prompt": "Does this look better?",
            "options": [
                {"label": "✓ Approve - Generate image", "value": "approve"},
                {"label": "✎ Give more feedback", "value": "feedback"},
                {"label": "✕ Start over", "value": "reject"}
            ]})
        return jsonify({"stage": "awaiting_dop_review", "messages": state.pipeline["messages"][-3:]})

    # approve → generate image
    state.push_message({"role": "user", "type": "text", "content": "Approved shot setup. Generating image..."})
    state.push_message({"role": "agent", "type": "thinking", "content": "Generating image..."})

    # Run generator
    ctx = run_generator(ctx)

    # Save generated image
    path = str(config.OUTPUT_DIR / "00_initial.png")
    ctx.image.save(path)
    state.pipeline["current_image_path"] = path
    state.pipeline["original_image_path"] = path

    state.push_message({"role": "agent", "type": "text",
        "content": "Done! Here's your generated image:"})
    state.push_message({"role": "agent", "type": "image",
        "url": "/outputs/00_initial.png", "caption": ""})
    state.push_message({"role": "agent", "type": "options",
        "prompt": "What would you like to do?",
        "options": [
            {"label": "✓ Looks good — critique it", "value": "accept"},
            {"label": "✕ Start over", "value": "reject"}
        ]})

    state.pipeline["stage"] = "awaiting_initial_review"
    return jsonify({"stage": state.pipeline["stage"], "messages": state.pipeline["messages"][-5:]})

# ── Critique (Unified endpoint for initial + re-critique) ─────────

@app.post("/api/critique")
def critique():
    """Run critique on current image. Handles both initial critique and re-critique."""
    is_recritique = request.json.get("is_recritique", False)
    return run_critique(is_recritique)

def run_critique(is_recritique=False):
    """Internal function to run critique logic."""
    import os
    from PIL import Image
    from models.pipeline_context import PipelineContext
    from agent import run_post_generation

    # Always use current_image_path - it's the single source of truth
    current_image_path = state.pipeline.get("current_image_path")

    if not current_image_path:
        return jsonify({"error": "No image to critique"}), 400

    # Determine display URL from the current path
    filename = os.path.basename(current_image_path)
    display_url = f"/outputs/{filename}"

    # User message
    if is_recritique:
        state.push_message({"role": "user", "type": "text", "content": "Run critique again."})
    else:
        state.push_message({"role": "user", "type": "text", "content": "Looks good, critique it."})

    # Show the current image being critiqued (for re-critique, show which version)
    if is_recritique:
        state.push_message({"role": "agent", "type": "image",
            "url": display_url, "caption": "Current image"})

    # Use new pipeline system for critique
    ctx = PipelineContext(
        original_prompt=state.pipeline["request"]["prompt"],
        aspect_ratio=state.pipeline.get("aspect_ratio", "1:1"),
        image=Image.open(current_image_path)
    )

    # Run post-generation agents (includes critic) with chat feedback
    ctx = run_post_generation(ctx, message_callback=state.push_message)

    # Extract critique from context
    if ctx.critiques:
        critique = ctx.critiques[0]  # Get the first (and only) critique
        state.pipeline["critique_json"] = critique
        state.pipeline["critique"] = critique
    else:
        return jsonify({"error": "No critique generated"}), 500

    # Save a copy of the critiqued image as annotated (for display in chat)
    # Note: We removed bbox annotations, so this is just the same image
    annotated_path = str(config.OUTPUT_DIR / "01_annotated.png")
    ctx.image.save(annotated_path)

    passed = critique["pass_threshold_met"]

    # Push critique result
    state.push_message({"role": "agent", "type": "critique",
        "score":      critique["overall_score"],
        "assessment": critique["overall_assessment"],
        "passed":     passed})

    # Show annotated image (same as generated, but shown for context)
    state.push_message({"role": "agent", "type": "image",
        "url": "/outputs/01_annotated.png", "caption": "Issues annotated"})

    # Show checklist with fixes
    if critique["fixes_required"]:
        prompt_text = "Select which fixes to apply (or skip all to finalize):"
    else:
        prompt_text = "No issues found! You can finalize the image:"

    state.push_message({"role": "agent", "type": "checklist",
        "prompt": prompt_text,
        "items": [{"id":       f["fix_id"],
                    "label":    f["issue_description"],
                    "severity": f["severity"],
                    "checked":  f["severity"] in ("high", "medium")}
                  for f in critique["fixes_required"]],
        "action": "apply_fixes",
        "allowRecritique": True})

    state.pipeline["stage"] = "awaiting_fix_review"

    new_msgs = state.pipeline["messages"][-10:]
    return jsonify({"stage": state.pipeline["stage"],
                    "critique": critique,
                    "messages": new_msgs})

# ── Fix Review (HITL Gate 2) ──────────────────────────────────────

@app.post("/api/review/fixes")
def review_fixes():
    approved_ids = request.json["approved_fix_ids"]
    custom_fixes_data = request.json.get("custom_fixes", [])

    # Get AI-detected fixes that were selected
    approved = [f for f in state.pipeline["critique"]["fixes_required"]
                if f["fix_id"] in approved_ids]

    # Add custom fixes to the approved list
    for custom in custom_fixes_data:
        if custom["id"] in approved_ids:
            # Create a fix object that matches the expected structure
            approved.append({
                "fix_id": custom["id"],
                "severity": custom.get("severity", "medium"),
                "issue_description": "Custom user-requested change",
                "fix_prompt": custom["label"]
            })

    state.push_message({"role": "user", "type": "text",
        "content": f"{len(approved)} fix(es) selected."})

    if not approved:
        from PIL import Image
        Image.open(state.pipeline["current_image_path"]).save(OUT / "final.png")
        state.push_message({"role": "agent", "type": "text",
            "content": "No fixes selected. Here's your final image:"})
        state.push_message({"role": "agent", "type": "final",
            "url": "/outputs/final.png", "caption": "Your image is ready."})
        state.pipeline["stage"] = "done"
        return jsonify({"stage": "done", "messages": state.pipeline["messages"][-3:]})

    # Apply all fixes at once
    state.push_message({"role": "agent", "type": "thinking",
        "content": f"Applying {len(approved)} fix(es) to the image..."})

    from pipeline.tools import TOOL_REGISTRY

    # Mock tool context
    class MockToolContext:
        class Actions:
            escalate = False
        actions = Actions()

    result = TOOL_REGISTRY["apply_all_fixes"](
        image_path=state.pipeline["current_image_path"],
        fixes_json=json.dumps(approved),
        tool_context=MockToolContext()
    )

    # Update current_image_path to the fixed version
    state.pipeline["current_image_path"] = result["fixed_image_path"]

    # Show before/after comparison (use original vs current)
    import os
    state.push_message({"role": "agent", "type": "comparison",
        "leftUrl":  f"/outputs/{os.path.basename(state.pipeline['original_image_path'])}",
        "rightUrl": f"/outputs/{os.path.basename(state.pipeline['current_image_path'])}",
        "caption":  f"Applied {len(approved)} fix(es)"})

    # Offer to accept or reject
    state.push_message({"role": "agent", "type": "options",
        "prompt": "Accept these changes?",
        "options": [
            {"label": "✓ Accept & Finalize", "value": "accept_all_fixes"},
            {"label": "✕ Reject & Keep Original",  "value": "reject_all_fixes"},
            {"label": "🔄 Run Critique Again", "value": "recritique"}
        ]})

    state.pipeline["stage"] = "awaiting_fixes_review"
    return jsonify({"stage": "awaiting_fixes_review",
                    "messages": state.pipeline["messages"][-4:]})

# ── Fixes Accept/Reject ───────────────────────────────────────────

@app.post("/api/fix/accept")
def accept_fix():
    accepted = request.json["accepted"]
    from PIL import Image

    if accepted:
        # Use the current image (with fixes) as final
        current_image = Image.open(state.pipeline["current_image_path"])
        current_image.save(OUT / "final.png")
        state.push_message({"role": "agent", "type": "text",
            "content": "All fixes accepted! Here's your final image:"})
    else:
        # Revert to original image and update current_image_path
        original_image = Image.open(state.pipeline["original_image_path"])
        original_image.save(OUT / "final.png")
        state.pipeline["current_image_path"] = state.pipeline["original_image_path"]
        state.push_message({"role": "agent", "type": "text",
            "content": "Fixes rejected. Keeping the original image:"})

    state.push_message({"role": "agent", "type": "final",
        "url": "/outputs/final.png", "caption": "Your image is ready."})
    state.pipeline["stage"] = "done"
    return jsonify({"stage": "done", "messages": state.pipeline["messages"][-2:]})

# ── Static ────────────────────────────────────────────────────────

@app.get("/outputs/<filename>")
def serve_output(filename):
    return send_from_directory(OUT, filename)

# ── Serve React Frontend ──────────────────────────────────────────

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
