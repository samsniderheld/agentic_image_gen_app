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

# Agent configuration: defines output fields, labels, and next agent
# Load AGENT_CONFIG from YAML files
from models.yaml_loader import build_agent_config_dict
AGENT_CONFIG = build_agent_config_dict()

# Legacy hardcoded config (kept for reference, can be removed)
# AGENT_CONFIG = {
#     "planner": {
#         "output_field": "enriched_prompt",
#         "output_label": "Enriched prompt",
#         "thinking_revise": "Revising enriched prompt based on your feedback...",
#         "approval_message": "Approved enriched prompt.",
#         "next_agent": "art_director",
#         "next_stage": "awaiting_art_director_review",
#         "next_label": "Continue to style",
#         "feedback_to_field": "original_prompt",
#     },
#     "art_director": {
#         "output_field": "style_brief",
#         "output_label": "Style brief",
#         "thinking_revise": "Revising style brief based on your feedback...",
#         "approval_message": "Approved style brief.",
#         "next_agent": "dop",
#         "next_stage": "awaiting_dop_review",
#         "next_label": "Continue to shot setup",
#         "feedback_to_field": "enriched_prompt",
#     },
#     "dop": {
#         "output_field": "shot_brief",
#         "output_label": "Shot brief",
#         "thinking_revise": "Revising shot brief based on your feedback...",
#         "approval_message": "Approved shot setup. Generating image...",
#         "next_agent": "generator",
#         "next_stage": "awaiting_initial_review",
#         "next_label": "Generate image",
#         "feedback_to_field": "style_brief",
#     },
# }

@app.post("/api/review/agent")
def review_agent():
    """Generic agent review handler - works for any pipeline agent."""
    from models.pipeline_context import PipelineContext
    from agent import get_pipeline, run_generator

    agent_name = request.json["agent"]
    decision = request.json["decision"]
    feedback = request.json.get("feedback")

    if agent_name not in AGENT_CONFIG:
        return jsonify({"error": f"Unknown agent: {agent_name}"}), 400

    agent_config = AGENT_CONFIG[agent_name]
    ctx = state.pipeline.get("pipeline_context")
    if not ctx:
        return jsonify({"error": "No pipeline context found"}), 400

    # Handle reject - start over
    if decision == "reject":
        state.push_message({"role": "user", "type": "text", "content": "Start over."})
        state.reset()
        return jsonify({"stage": "idle", "messages": state.pipeline["messages"][-1:]})

    # Handle feedback - re-run agent with feedback
    if decision == "feedback":
        state.push_message({"role": "user", "type": "text", "content": f"Feedback: {feedback}"})
        state.push_message({"role": "agent", "type": "thinking", "content": agent_config["thinking_revise"]})

        # Inject feedback into appropriate field
        feedback_field = agent_config["feedback_to_field"]
        current_value = getattr(ctx, feedback_field)
        setattr(ctx, feedback_field, f"{current_value}\n\nUser feedback: {feedback}")

        # Re-run the agent
        pipeline = get_pipeline()
        agent = next((a for a in pipeline if a.name == agent_name), None)
        if agent:
            ctx = agent.run(ctx)

        state.pipeline["pipeline_context"] = ctx

        # Show revised output
        output_value = getattr(ctx, agent_config["output_field"])
        state.push_message({"role": "agent", "type": "text",
            "content": f"**Revised {agent_config['output_label'].lower()}:**\n\n{output_value}"})

        # Show same options again
        current_stage = f"awaiting_{agent_name}_review"
        state.push_message({"role": "agent", "type": "options",
            "prompt": "Does this look better?",
            "options": [
                {"label": f"✓ Approve - {agent_config['next_label']}", "value": "approve"},
                {"label": "✎ Give more feedback", "value": "feedback"},
                {"label": "✕ Start over", "value": "reject"}
            ]})
        return jsonify({"stage": current_stage, "messages": state.pipeline["messages"][-3:]})

    # Handle approve - run next agent
    state.push_message({"role": "user", "type": "text", "content": agent_config["approval_message"]})

    next_agent_name = agent_config["next_agent"]

    # Special case: if next is generator, generate image
    if next_agent_name == "generator":
        state.push_message({"role": "agent", "type": "thinking", "content": "Generating image..."})
        ctx = run_generator(ctx)

        # Save generated image
        from config import config as app_config
        path = str(app_config.OUTPUT_DIR / "00_initial.png")
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

        state.pipeline["stage"] = agent_config["next_stage"]
        return jsonify({"stage": state.pipeline["stage"], "messages": state.pipeline["messages"][-5:]})

    # Otherwise, run next agent in pipeline
    pipeline = get_pipeline()
    next_agent = next((a for a in pipeline if a.name == next_agent_name), None)
    if next_agent:
        # Get thinking message from next agent config
        next_config = AGENT_CONFIG.get(next_agent_name, {})
        thinking = next_config.get("thinking_revise", f"Running {next_agent_name}...")
        thinking = thinking.replace("Revising", "Defining").replace(" based on your feedback", "")
        state.push_message({"role": "agent", "type": "thinking", "content": thinking})
        ctx = next_agent.run(ctx)

    state.pipeline["pipeline_context"] = ctx

    # Show output from next agent
    next_config = AGENT_CONFIG[next_agent_name]
    output_value = getattr(ctx, next_config["output_field"])
    state.push_message({"role": "agent", "type": "text",
        "content": f"**{next_config['output_label']}:**\n\n{output_value}"})

    # Show options for next review
    state.push_message({"role": "agent", "type": "options",
        "prompt": f"Does this {next_config['output_label'].lower()} work?",
        "options": [
            {"label": f"✓ Approve - {next_config['next_label']}", "value": "approve"},
            {"label": "✎ Give feedback", "value": "feedback"},
            {"label": "✕ Start over", "value": "reject"}
        ]})

    state.pipeline["stage"] = agent_config["next_stage"]
    return jsonify({"stage": state.pipeline["stage"], "messages": state.pipeline["messages"][-4:]})

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
