from google import genai
from google.genai import types
from PIL import Image
import os, io, json, time

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    return _client

# LLM role
def call_llm(instruction, user_message, model_name, temperature, max_tokens, input_images=None) -> str:
    config = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens)

    # Build content with system instruction and user message
    full_prompt = f"{instruction}\n\n{user_message}"

    if input_images and len(input_images) > 0:
        # Include images in the request for multimodal understanding
        print(f"DEBUG call_llm: Including {len(input_images)} images in LLM request")
        content_parts = []

        # Add images first
        for i, img in enumerate(input_images):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            print(f"DEBUG call_llm: Adding image {i+1}: {img.size} {img.mode}")
            content_parts.append(types.Part.from_bytes(
                data=buf.getvalue(),
                mime_type="image/png"
            ))

        # Add text prompt after images
        content_parts.append(types.Part.from_text(text=full_prompt))

        r = _get_client().models.generate_content(
            model=model_name,
            contents=content_parts,
            config=config,
        )
    else:
        # Text-only request
        r = _get_client().models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=config,
        )

    return r.text.strip()

# Image generation role
def generate_image(prompt, aspect_ratio, model_name, input_images=None) -> Image.Image:
    print(f"DEBUG generate_image called:")
    print(f"  prompt: {prompt[:100]}...")
    print(f"  aspect_ratio: {aspect_ratio}")
    print(f"  model_name: {model_name}")
    print(f"  input_images: {input_images}")
    print(f"  input_images type: {type(input_images)}")
    if input_images:
        print(f"  input_images length: {len(input_images)}")

    config = types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
        ),
    )

    if input_images and len(input_images) > 0:
        # Build content with input images + prompt
        print(f"DEBUG: Using {len(input_images)} reference images")
        content_parts = [prompt]
        for i, img in enumerate(input_images):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            print(f"DEBUG: Adding reference image {i+1}: {img.size} {img.mode}")
            # Create a Part with inline image data
            content_parts.append(types.Part.from_bytes(
                data=buf.getvalue(),
                mime_type="image/png"
            ))

        print(f"DEBUG: Sending to Gemini with {len(content_parts)} parts (1 text + {len(input_images)} images)")
        response = _get_client().models.generate_content(
            model=model_name,
            contents=content_parts,
            config=config,
        )
    else:
        # Text-only prompt
        print("DEBUG: Sending text-only prompt to Gemini")
        response = _get_client().models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

    # Extract image from response using proper method
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            image_bytes = part.inline_data.data
            generated_image = Image.open(io.BytesIO(image_bytes))
            print('Successfully extracted image from Gemini response')
            return generated_image

    raise ValueError("No image found in Gemini response")

def inpaint_image(image, fix_prompts, aspect_ratio, model_name) -> Image.Image:
    prompt = "Fix the following issues:\n" + "\n".join(f"- {p}" for p in fix_prompts)
    return generate_image(prompt, aspect_ratio, model_name, input_images=[image])

def infer_composition_prompt(images) -> str:
    parts = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        parts.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"))
    parts.append(types.Part.from_text(
        text="Analyze these images and suggest a composition prompt for combining them."))
    return _get_client().models.generate_content(
        model="gemini-3.1-pro-preview", contents=parts
    ).text.strip()

# Vision critic role
def critique_image(image, original_prompt) -> dict:
    buf = io.BytesIO()
    image.save(buf, format="PNG")

    system = (
        "You are an expert image critic. Analyze the image against the original prompt. "
        "Return JSON: overall_score (float 0-1), overall_assessment (str), "
        "fixes_required (array of {fix_id, severity: low|medium|high, "
        "issue_description, fix_prompt}), pass_threshold_met (bool, true if score >= 0.9)."
    )

    r = _get_client().models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=[
            types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"),
            types.Part.from_text(text=f"Original prompt: {original_prompt}\n\nCritique this image."),
        ],
        config=types.GenerateContentConfig(
            system_instruction=system, response_mime_type="application/json"),
    )
    return json.loads(r.text)

# Video generation role
def generate_video(image, prompt, aspect_ratio="9:16", duration_seconds=8, resolution="1080p", model_name="veo-3.1-generate-preview"):
    """
    Generate a video from an image using Veo.
    Returns raw video bytes.
    """
    # Veo only supports 16:9 and 9:16 aspect ratios
    # Map other aspect ratios to supported ones
    aspect_ratio_map = {
        "1:1": "9:16",  # Square -> Portrait
        "4:3": "16:9",  # Classic -> Landscape
        "3:4": "9:16",  # Classic portrait -> Portrait
        "16:9": "16:9",
        "9:16": "9:16",
    }

    original_aspect = aspect_ratio
    aspect_ratio = aspect_ratio_map.get(aspect_ratio, "9:16")

    if original_aspect != aspect_ratio:
        print(f"Note: Converted aspect ratio from {original_aspect} to {aspect_ratio} (Veo only supports 16:9 and 9:16)")

    print(f"DEBUG generate_video called:")
    print(f"  prompt: {prompt[:100]}...")
    print(f"  aspect_ratio: {aspect_ratio}")
    print(f"  duration_seconds: {duration_seconds}")
    print(f"  resolution: {resolution}")
    print(f"  model_name: {model_name}")
    print(f"  image: {image.size} {image.mode}")

    # Get client with v1beta API version for video generation
    video_client = genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    # Save image to temporary file for upload
    temp_image_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "temp_video_input.png")
    temp_image_path = os.path.abspath(temp_image_path)
    os.makedirs(os.path.dirname(temp_image_path), exist_ok=True)
    image.save(temp_image_path)

    # Configure video generation
    video_config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        number_of_videos=1,
        duration_seconds=duration_seconds,
        resolution=resolution,
    )

    # Start video generation
    print("DEBUG: Starting video generation...")
    # operation = video_client.models.generate_videos(
    #     model=model_name,
    #     source=types.VideoGenerationSource(
    #         prompt=prompt,
    #         image=types.Image(
    #             gcs_uri=uploaded_file.uri,
    #             mime_type="image/png"
    #         ),
    #     ),
    #     config=video_config,
    # )

    operation = video_client.models.generate_videos(
        model=model_name,
        prompt=prompt,
        image=types.Image.from_file(location=temp_image_path),
        config=video_config,
    )

    # Poll for completion
    print("DEBUG: Waiting for video generation to complete...")
    poll_count = 0
    while not operation.done:
        poll_count += 1
        print(f"DEBUG: Video generation in progress... (poll #{poll_count})")
        time.sleep(10)
        operation = video_client.operations.get(operation)

    print("DEBUG: Video generation completed!")

    # Get result
    result = operation.result
    if not result:
        raise ValueError("Error occurred while generating video - no result returned")

    generated_videos = result.generated_videos
    if not generated_videos:
        raise ValueError("No videos were generated")

    print(f"DEBUG: Generated {len(generated_videos)} video(s)")

    # Download video bytes from URI
    generated_video = generated_videos[0]
    video_uri = generated_video.video.uri
    print(f"DEBUG: Video URI: {video_uri}")

    # Download the video using the client - returns bytes directly
    video_bytes = video_client.files.download(file=generated_video.video)
    print(f"DEBUG: Downloaded video bytes: {len(video_bytes)} bytes")

    # Clean up temp image
    if os.path.exists(temp_image_path):
        os.remove(temp_image_path)

    return video_bytes
