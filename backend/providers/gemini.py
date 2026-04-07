from google import genai
from google.genai import types
from PIL import Image
import os, io, json

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

    image_bytes = response.candidates[0].content.parts[0].inline_data.data
    return Image.open(io.BytesIO(image_bytes))

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
