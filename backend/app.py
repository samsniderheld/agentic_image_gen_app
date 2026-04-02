from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import state
import loader
import runner
from PIL import Image
import base64
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="../frontend/dist")
CORS(app)

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")

@app.route("/api/action", methods=["POST"])
def action():
    data = request.json
    action_type = data.get("action")

    try:
        if action_type == "generate":
            return handle_generate(data)
        elif action_type == "review":
            return handle_review(data)
        elif action_type == "critique":
            return handle_critique()
        elif action_type == "apply_fixes":
            return handle_apply_fixes(data)
        elif action_type == "accept_fix":
            return handle_accept_fix(data)
        else:
            return jsonify({"error": f"Unknown action: {action_type}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def handle_generate(data):
    """Start a new pipeline run"""
    state.reset()

    # Load pipeline
    state.pipeline["agents"] = loader.load_pipeline()
    state.pipeline["hitl_config"] = loader.build_hitl_config(state.pipeline["agents"])

    # Initialize context with user inputs
    state.pipeline["context"]["original_prompt"] = data.get("prompt", "")
    state.pipeline["context"]["aspect_ratio"] = data.get("aspect_ratio", "1:1")

    # Handle uploaded images
    if data.get("images"):
        input_images = []
        for img_b64 in data["images"]:
            img_data = base64.b64decode(img_b64.split(",")[1] if "," in img_b64 else img_b64)
            input_images.append(Image.open(io.BytesIO(img_data)))
        state.pipeline["context"]["input_images"] = input_images

    # Add user message
    state.pipeline["messages"].append({
        "type": "text",
        "role": "user",
        "text": data.get("prompt", "")
    })

    # Start pipeline
    return advance_pipeline()

def handle_review(data):
    """Handle HITL review decisions"""
    decision = data.get("decision")
    current_agent = state.pipeline["agents"][state.pipeline["current_agent_index"]]

    if decision == "approve":
        # Add approval message
        hitl = state.pipeline["hitl_config"][current_agent.name]
        state.pipeline["messages"].append({
            "type": "text",
            "role": "agent",
            "text": hitl["approval_message"]
        })

        # Advance to next agent
        state.pipeline["current_agent_index"] += 1
        return advance_pipeline()

    elif decision == "feedback":
        # Add feedback to context and re-run current agent
        feedback = data.get("feedback", "")
        hitl = state.pipeline["hitl_config"][current_agent.name]
        feedback_target = hitl.get("feedback_target")

        if feedback_target:
            current_value = state.pipeline["context"].get(feedback_target, "")
            state.pipeline["context"][feedback_target] = f"{current_value}\n\nFeedback: {feedback}"

        # Add user feedback message
        state.pipeline["messages"].append({
            "type": "text",
            "role": "user",
            "text": feedback
        })

        # Add thinking message
        state.pipeline["messages"].append({
            "type": "thinking",
            "text": hitl["thinking_revise"]
        })

        # Re-run current agent
        state.pipeline["context"] = runner.run_agent(current_agent, state.pipeline["context"])

        # Add output message
        output_field = hitl["output_field"]
        output_value = state.pipeline["context"].get(output_field)
        state.pipeline["messages"].append({
            "type": "text",
            "role": "agent",
            "text": output_value
        })

        # Add options again
        state.pipeline["messages"].append({
            "type": "options",
            "options": [
                {"label": hitl["approve_label"], "value": "approve"},
                {"label": "Provide Feedback", "value": "feedback"},
                {"label": "Start Over", "value": "reject"}
            ],
            "showFeedback": False
        })

        return jsonify({"messages": state.pipeline["messages"]})

    elif decision == "reject":
        state.reset()
        state.pipeline["stage"] = "idle"
        state.pipeline["messages"].append({
            "type": "text",
            "role": "agent",
            "text": "Starting over. What would you like to create?"
        })
        return jsonify({"messages": state.pipeline["messages"]})

def advance_pipeline():
    """Run agents until we hit a HITL gate or finish"""
    while state.pipeline["current_agent_index"] < len(state.pipeline["agents"]):
        current_agent = state.pipeline["agents"][state.pipeline["current_agent_index"]]

        # Add thinking message
        hitl = current_agent.hitl
        if hitl.get("enabled"):
            thinking_msg = hitl.get("thinking_message", f"Running {current_agent.display_name}...")
            state.pipeline["messages"].append({
                "type": "thinking",
                "text": thinking_msg
            })

        # Run agent
        state.pipeline["context"] = runner.run_agent(current_agent, state.pipeline["context"])

        # Check if this is a HITL agent
        if hitl.get("enabled"):
            # Set review stage
            state.pipeline["stage"] = hitl.get("review_stage", f"awaiting_{current_agent.name}_review")

            # Add output message
            hitl_config = state.pipeline["hitl_config"][current_agent.name]
            output_field = hitl_config["output_field"]
            output_value = state.pipeline["context"].get(output_field)

            state.pipeline["messages"].append({
                "type": "text",
                "role": "agent",
                "text": output_value
            })

            # Add options
            state.pipeline["messages"].append({
                "type": "options",
                "options": [
                    {"label": hitl_config["approve_label"], "value": "approve"},
                    {"label": "Provide Feedback", "value": "feedback"},
                    {"label": "Start Over", "value": "reject"}
                ],
                "showFeedback": False
            })

            return jsonify({"messages": state.pipeline["messages"]})

        # If not HITL, continue to next agent
        state.pipeline["current_agent_index"] += 1

    # Pipeline finished - we should have an image
    if "image_path" in state.pipeline["context"]:
        img_path = state.pipeline["context"]["image_path"]
        state.pipeline["original_image_path"] = img_path
        state.pipeline["current_image_path"] = img_path
        state.pipeline["stage"] = "awaiting_initial_review"

        # Add image message
        state.pipeline["messages"].append({
            "type": "image",
            "src": f"/outputs/{os.path.basename(img_path)}",
            "caption": "Generated image"
        })

        # Add options
        state.pipeline["messages"].append({
            "type": "options",
            "options": [
                {"label": "Send to Critique", "value": "critique"},
                {"label": "Start Over", "value": "reject"}
            ],
            "showFeedback": False
        })

    return jsonify({"messages": state.pipeline["messages"]})

def handle_critique():
    """Run the critic agent"""
    state.pipeline["stage"] = "running_critique"

    # Add thinking message
    state.pipeline["messages"].append({
        "type": "thinking",
        "text": "Analyzing image..."
    })

    # Find critic agent in pipeline
    critic_agent = next((a for a in state.pipeline["agents"] if a.type == "critic_agent"), None)
    if not critic_agent:
        return jsonify({"error": "No critic agent found in pipeline"}), 400

    # Run critique
    state.pipeline["context"] = runner.run_agent(critic_agent, state.pipeline["context"])
    critique = state.pipeline["context"]["critique"]
    state.pipeline["critique"] = critique

    # Add critique message
    state.pipeline["messages"].append({
        "type": "critique",
        "score": int(critique["overall_score"] * 100),
        "assessment": critique["overall_assessment"],
        "pass": critique["pass_threshold_met"]
    })

    # If passed, show final image
    if critique["pass_threshold_met"]:
        state.pipeline["stage"] = "done"
        state.pipeline["messages"].append({
            "type": "final",
            "src": f"/outputs/{os.path.basename(state.pipeline['current_image_path'])}"
        })
    else:
        # Show fix checklist
        state.pipeline["stage"] = "awaiting_fix_review"
        state.pipeline["messages"].append({
            "type": "image",
            "src": f"/outputs/{os.path.basename(state.pipeline['current_image_path'])}",
            "caption": "Current image"
        })
        state.pipeline["messages"].append({
            "type": "checklist",
            "fixes": critique["fixes_required"],
            "allowCustom": True,
            "allowRecritique": True
        })

    return jsonify({"messages": state.pipeline["messages"]})

def handle_apply_fixes(data):
    """Apply selected fixes via inpainting"""
    approved_fix_ids = data.get("approved_fix_ids", [])
    custom_fixes = data.get("custom_fixes", [])

    # Build fix prompts
    fix_prompts = []
    for fix in state.pipeline["critique"]["fixes_required"]:
        if fix["fix_id"] in approved_fix_ids:
            fix_prompts.append(fix["fix_prompt"])
    fix_prompts.extend(custom_fixes)

    if not fix_prompts:
        return jsonify({"error": "No fixes selected"}), 400

    # Add thinking message
    state.pipeline["messages"].append({
        "type": "thinking",
        "text": "Applying fixes..."
    })

    # Apply fixes
    current_image = Image.open(state.pipeline["current_image_path"])
    aspect_ratio = state.pipeline["context"]["aspect_ratio"]
    provider_name = state.pipeline["agents"][0].model_provider  # Use first agent's provider

    fixed_image, fixed_path = runner.apply_fixes(current_image, fix_prompts, aspect_ratio, provider_name)
    state.pipeline["current_image_path"] = fixed_path

    # Add comparison message
    state.pipeline["stage"] = "awaiting_fixes_review"
    state.pipeline["messages"].append({
        "type": "comparison",
        "before": f"/outputs/{os.path.basename(state.pipeline['original_image_path'])}",
        "after": f"/outputs/{os.path.basename(fixed_path)}",
        "beforeLabel": "Original",
        "afterLabel": "With fixes"
    })

    # Add options
    state.pipeline["messages"].append({
        "type": "options",
        "options": [
            {"label": "Accept", "value": "accept"},
            {"label": "Reject", "value": "reject"},
            {"label": "Re-critique", "value": "recritique"}
        ],
        "showFeedback": False
    })

    return jsonify({"messages": state.pipeline["messages"]})

def handle_accept_fix(data):
    """Handle acceptance/rejection of fixes"""
    decision = data.get("decision", "accept")

    if decision == "accept":
        state.pipeline["stage"] = "done"
        state.pipeline["messages"].append({
            "type": "final",
            "src": f"/outputs/{os.path.basename(state.pipeline['current_image_path'])}"
        })
    elif decision == "reject":
        # Revert to original image
        state.pipeline["current_image_path"] = state.pipeline["original_image_path"]
        state.pipeline["stage"] = "awaiting_fix_review"

        # Show original image again with fix checklist
        state.pipeline["messages"].append({
            "type": "image",
            "src": f"/outputs/{os.path.basename(state.pipeline['current_image_path'])}",
            "caption": "Original image"
        })
        state.pipeline["messages"].append({
            "type": "checklist",
            "fixes": state.pipeline["critique"]["fixes_required"],
            "allowCustom": True,
            "allowRecritique": True
        })
    elif decision == "recritique":
        # Run critique on the fixed image
        state.pipeline["context"]["image"] = Image.open(state.pipeline["current_image_path"])
        return handle_critique()

    return jsonify({"messages": state.pipeline["messages"]})

@app.route("/outputs/<path:filename>")
def serve_output(filename):
    return send_from_directory(OUTPUTS_DIR, filename)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(debug=True, port=8000)
