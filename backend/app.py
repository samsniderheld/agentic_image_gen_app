from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import loader
import runner
import providers
from PIL import Image
import base64
import io
import os
import uuid
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="../frontend/dist")
CORS(app)

# Track active requests for monitoring
active_requests = {}
active_requests_lock = threading.Lock()

@app.route("/api/generate_image", methods=["POST"])
def generate_image():
    """
    Generate an image from a prompt and optional reference images.

    Request body:
    {
        "prompt": "your prompt here",
        "aspect_ratio": "1:1",  // optional, defaults to "1:1"
        "images": ["base64_image_data", ...]  // optional reference images
    }

    Response:
    {
        "image_url": "/outputs/filename.png",
        "context": { ... }  // full pipeline context for debugging
    }
    """
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]

    with active_requests_lock:
        active_requests[request_id] = {
            "type": "image_generation",
            "start_time": datetime.now(),
            "thread_id": threading.get_ident()
        }

    try:
        data = request.json
        prompt = data.get("prompt", "")
        aspect_ratio = data.get("aspect_ratio", "1:1")
        image_data_list = data.get("images", [])

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        print(f"[Request {request_id}] Starting image generation")
        print(f"[Request {request_id}] Active requests: {len(active_requests)}")

        # Load pipeline
        agents = loader.load_pipeline()

        # Initialize context
        context = {
            "original_prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "request_id": request_id
        }

        # Process reference images if provided
        if image_data_list:
            input_images = []
            for img_b64 in image_data_list:
                img_data = base64.b64decode(img_b64.split(",")[1] if "," in img_b64 else img_b64)
                img = Image.open(io.BytesIO(img_data))
                input_images.append(img)
            context["input_images"] = input_images
            print(f"[Request {request_id}] Loaded {len(input_images)} reference images")

        # Run all agents in sequence
        for agent in agents:
            print(f"[Request {request_id}] Running agent: {agent.display_name}")
            context = runner.run_agent(agent, context)

        # Extract generated image from context
        generated_image = context.get("image")
        if not generated_image:
            return jsonify({"error": "Pipeline did not produce an image"}), 500

        # Convert image to base64
        img_buffer = io.BytesIO()
        generated_image.save(img_buffer, format="PNG")
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        img_data_url = f"data:image/png;base64,{img_base64}"
        print(f"[Request {request_id}] Generated image: {generated_image.size} {generated_image.mode}")

        # Return base64 image
        return jsonify({
            "image_data": img_data_url,
            "request_id": request_id,
            "context": {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                       for k, v in context.items()}
        })

    except Exception as e:
        print(f"[Request {request_id}] ERROR in generate_image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "request_id": request_id}), 500
    finally:
        with active_requests_lock:
            if request_id in active_requests:
                duration = (datetime.now() - active_requests[request_id]["start_time"]).total_seconds()
                print(f"[Request {request_id}] Completed in {duration:.2f}s")
                del active_requests[request_id]


@app.route("/api/generate_video", methods=["POST"])
def generate_video():
    """
    Generate a video from an image.

    Request body:
    {
        "image_url": "/outputs/filename.png",
        "prompt": "your prompt here",
        "aspect_ratio": "9:16",  // optional, defaults to "9:16"
        "duration_seconds": 8,  // optional, defaults to 8
        "resolution": "1080p"  // optional, defaults to "1080p"
    }

    Response:
    {
        "video_url": "/outputs/filename.mp4"
    }
    """
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]

    with active_requests_lock:
        active_requests[request_id] = {
            "type": "video_generation",
            "start_time": datetime.now(),
            "thread_id": threading.get_ident()
        }

    try:
        data = request.json
        image_url = data.get("image_url", "")
        prompt = data.get("prompt", "")
        aspect_ratio = data.get("aspect_ratio", "9:16")
        duration_seconds = data.get("duration_seconds", 8)
        resolution = data.get("resolution", "1080p")

        if not image_url:
            return jsonify({"error": "image_data is required"}), 400

        print(f"[Request {request_id}] Starting video generation")
        print(f"[Request {request_id}] Active requests: {len(active_requests)}")

        # Decode base64 image
        if image_url.startswith("data:image"):
            # Extract base64 data from data URL
            img_data = image_url.split(",")[1] if "," in image_url else image_url
            img_bytes = base64.b64decode(img_data)
            image = Image.open(io.BytesIO(img_bytes))
            print(f"[Request {request_id}] Loaded image from base64: {image.size} {image.mode}")
        else:
            return jsonify({"error": "Invalid image_data format"}), 400

        # Get video provider and generate video
        video_provider = providers.get_video_provider("gemini")
        video_bytes = video_provider(
            image=image,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            duration_seconds=duration_seconds,
            resolution=resolution,
            model_name="veo-3.1-generate-preview"
        )

        print(f"[Request {request_id}] Video generated: {len(video_bytes)} bytes")

        # Convert video to base64
        video_base64 = base64.b64encode(video_bytes).decode('utf-8')
        video_data_url = f"data:video/mp4;base64,{video_base64}"
        print(f"[Request {request_id}] Video encoded to base64")

        # Return base64 video
        return jsonify({
            "video_data": video_data_url,
            "request_id": request_id
        })

    except Exception as e:
        print(f"[Request {request_id}] ERROR in generate_video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "request_id": request_id}), 500
    finally:
        with active_requests_lock:
            if request_id in active_requests:
                duration = (datetime.now() - active_requests[request_id]["start_time"]).total_seconds()
                print(f"[Request {request_id}] Completed in {duration:.2f}s")
                del active_requests[request_id]


@app.route("/api/status", methods=["GET"])
def get_status():
    """Get status of active requests"""
    with active_requests_lock:
        return jsonify({
            "active_requests": len(active_requests),
            "requests": [
                {
                    "request_id": req_id,
                    "type": req_info["type"],
                    "duration": (datetime.now() - req_info["start_time"]).total_seconds(),
                    "thread_id": req_info["thread_id"]
                }
                for req_id, req_info in active_requests.items()
            ]
        })


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve the React frontend"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    # Enable threaded mode to handle multiple concurrent requests
    # Each request will run in its own thread
    print("Starting Flask server with multi-threading enabled...")
    print("Max concurrent requests: Limited by system resources")
    app.run(debug=True, port=8000, threaded=True)
