from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from config import config
import state, agent
from schemas import GenerationRequest, RegionalFix
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
    state.reset()
    req = GenerationRequest(**request.json)
    state.pipeline.update(request=req.model_dump(), stage="generating")

    state.push_message({"role": "agent", "type": "thinking",
        "content": f"Generating with prompt: \"{req.prompt}\" at {req.aspect_ratio}..."})

    agent.run_adk_segment(
        agent_yaml="generation_agent",
        input_message="Generate the image now.",
        state_in={"prompt": req.prompt, "aspect_ratio": req.aspect_ratio},
        state_out_keys=["image_path"]
    )

    state.push_message({"role": "agent", "type": "text",
        "content": "Done! Here's your initial generation:"})
    state.push_message({"role": "agent", "type": "image",
        "url": "/outputs/00_initial.png", "caption": ""})
    state.push_message({"role": "agent", "type": "options",
        "prompt": "What would you like to do?",
        "options": [
            {"label": "✓ Looks good — critique it", "value": "accept"},
            {"label": "✎ Edit my prompt",            "value": "edit"},
            {"label": "✕ Start over",                "value": "reject"}
        ]})

    state.pipeline["stage"] = "awaiting_initial_review"
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

    # accept → critique
    state.push_message({"role": "user", "type": "text", "content": "Looks good, critique it."})
    state.push_message({"role": "agent", "type": "thinking",
        "content": "Running vision critique against the original prompt..."})

    agent.run_adk_segment(
        agent_yaml="critique_agent",
        input_message="Critique the current image.",
        state_in={"image_path": state.pipeline["image_path"],
                  "prompt": state.pipeline["request"]["prompt"]},
        state_out_keys=["critique_json"]
    )

    critique = state.pipeline["critique_json"]
    state.pipeline["critique"] = critique
    passed = critique["pass_threshold_met"]

    state.push_message({"role": "agent", "type": "critique",
        "score":      critique["overall_score"],
        "assessment": critique["overall_assessment"],
        "passed":     passed})
    state.push_message({"role": "agent", "type": "image",
        "url": "/outputs/01_annotated.png", "caption": "Issues annotated"})

    # Always show checklist, even if passed
    if critique["fixes_required"]:
        prompt_text = "Select which fixes to apply (or skip all to finalize):"
    else:
        prompt_text = "No issues found! You can finalize the image:"

    state.push_message({"role": "agent", "type": "checklist",
        "prompt": prompt_text,
        "items": [{"id":       f["region_id"],
                    "label":    f["issue_description"],
                    "severity": f["severity"],
                    "checked":  f["severity"] in ("high", "medium")}
                  for f in critique["fixes_required"]],
        "action": "apply_fixes"})
    state.pipeline["stage"] = "awaiting_fix_review"

    new_msgs = state.pipeline["messages"][-10:]
    return jsonify({"stage": state.pipeline["stage"],
                    "critique": critique,
                    "messages": new_msgs})

# ── Fix Review (HITL Gate 2) ──────────────────────────────────────

@app.post("/api/review/fixes")
def review_fixes():
    approved_ids = request.json["approved_fix_ids"]
    approved = [f for f in state.pipeline["critique"]["fixes_required"]
                if f["region_id"] in approved_ids]

    state.push_message({"role": "user", "type": "text",
        "content": f"{len(approved)} fix(es) selected."})

    if not approved:
        from PIL import Image
        Image.open(state.pipeline["image_path"]).save(OUT / "final.png")
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
        image_path=state.pipeline["image_path"],
        fixes_json=json.dumps(approved),
        tool_context=MockToolContext()
    )

    # Show before/after comparison
    state.push_message({"role": "agent", "type": "comparison",
        "leftUrl":  "/outputs/00_initial.png",
        "rightUrl": "/outputs/fixes_applied.png",
        "caption":  f"Applied {len(approved)} fix(es)"})

    # Offer to accept or reject
    state.push_message({"role": "agent", "type": "options",
        "prompt": "Accept these changes?",
        "options": [
            {"label": "✓ Accept & Finalize", "value": "accept_all_fixes"},
            {"label": "✕ Reject & Keep Original",  "value": "reject_all_fixes"}
        ]})

    state.pipeline["stage"] = "awaiting_fixes_review"
    state.pipeline["fixed_image_path"] = result["fixed_image_path"]
    return jsonify({"stage": "awaiting_fixes_review",
                    "messages": state.pipeline["messages"][-4:]})

# ── Fixes Accept/Reject ───────────────────────────────────────────

@app.post("/api/fix/accept")
def accept_fix():
    accepted = request.json["accepted"]

    if accepted:
        # Use the fixed image as final
        from PIL import Image
        fixed_image = Image.open(state.pipeline["fixed_image_path"])
        fixed_image.save(OUT / "final.png")
        state.push_message({"role": "agent", "type": "text",
            "content": "All fixes accepted! Here's your final image:"})
    else:
        # Keep the original image
        from PIL import Image
        Image.open(state.pipeline["image_path"]).save(OUT / "final.png")
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
