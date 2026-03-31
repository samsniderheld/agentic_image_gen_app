import google.generativeai as genai
from PIL import Image
from schemas import CritiqueResult
import io, base64, json
from typing import List, Optional

from models.base import ImageCritic


class GeminiCritic(ImageCritic):
    """Gemini-based image critique backend."""

    def __init__(self, api_key: str, model_name: str):
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model_name)

    def infer_composition_prompt(self, images: List[Image.Image]) -> str:
        """
        Analyze images and suggest a composition prompt focusing on:
        - Combining elements from multiple images
        - Face composition/swapping
        - Style blending
        - Object/scene compositing
        """
        content_parts = []

        # Add all input images
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_data = base64.b64encode(buf.getvalue()).decode()
            content_parts.append({"mime_type": "image/png", "data": img_data})

        # Ask for composition-focused prompt
        prompt = """Analyze these images and suggest a composition prompt that combines their elements.

Focus on:
- If faces are present: face composition, expression transfer, or portrait blending
- Object composition: placing elements from one image into another
- Style transfer: applying the aesthetic of one image to another
- Scene merging: blending backgrounds, lighting, or atmospheres
- Element extraction: taking specific subjects and compositing them together

Return ONLY a clear, actionable composition prompt (1-2 sentences) that describes how to combine these images, nothing else."""

        content_parts.append(prompt)

        response = self.client.generate_content(content_parts)
        return response.text.strip()

    def critique(self, image: Image.Image, prompt: str, input_images: Optional[List[Image.Image]] = None) -> dict:
        """
        Critique a generated image against the original prompt.
        Returns a CritiqueResult as a dict.
        """
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_data = base64.b64encode(buf.getvalue()).decode()

        # Build the critique prompt based on whether input images were used
        if input_images and len(input_images) > 0:
            num_inputs = len(input_images)
            critique_prompt = f"""Analyze this generated image against the original prompt: '{prompt}'.
This image was created by combining {num_inputs} input image(s).

Evaluate:
1. How well the prompt is fulfilled
2. How well each input image is integrated (seamlessness, consistency, natural blending)
3. Any visual issues or artifacts
4. Does this image look AI generated
5. Do the faces match the input images
6. Do the products look real

Return ONLY valid JSON — no markdown, no explanation:
{{
  "overall_score": <float 0.0-1.0>,
  "overall_assessment": <string>,
  "fixes_required": [
    {{
      "fix_id": <string e.g. "fix_0">,
      "severity": <"low"|"medium"|"high">,
      "issue_description": <string>,
      "fix_prompt": <string describing the DESIRED result for the entire image>
    }}
  ],
  "pass_threshold_met": <true if score >= 0.8>,
  "image_integrations": [
    {{
      "image_index": <int 0 to {num_inputs-1}>,
      "integration_score": <float 0.0-1.0>,
      "integration_notes": <string describing how well this input image was integrated>
    }}
  ]
}}
Each fix applies to the ENTIRE image, not regions.
Only include fixes for genuine issues. Return an empty array if none.
Provide integration_score for each of the {num_inputs} input images."""
        else:
            critique_prompt = f"""Analyze this image against the original prompt: '{prompt}'.
Return ONLY valid JSON — no markdown, no explanation:
{{
  "overall_score": <float 0.0-1.0>,
  "overall_assessment": <string>,
  "fixes_required": [
    {{
      "fix_id": <string e.g. "fix_0">,
      "severity": <"low"|"medium"|"high">,
      "issue_description": <string>,
      "fix_prompt": <string describing the DESIRED result for the entire image>
    }}
  ],
  "pass_threshold_met": <true if score >= 0.8>,
  "image_integrations": []
}}
Each fix applies to the ENTIRE image, not regions.
Only include fixes for genuine issues. Return an empty array if none."""

        # Build content with generated image and optionally input images for reference
        content_parts = []

        # Add input images if provided (for reference in critique)
        if input_images and len(input_images) > 0:
            for idx, input_img in enumerate(input_images):
                buf_input = io.BytesIO()
                input_img.save(buf_input, format="PNG")
                input_data = base64.b64encode(buf_input.getvalue()).decode()
                content_parts.append({"mime_type": "image/png", "data": input_data})

        # Add the generated image to critique
        content_parts.append({"mime_type": "image/png", "data": image_data})
        content_parts.append(critique_prompt)

        response = self.client.generate_content(content_parts)
        raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()

        # Return CritiqueResult as dict (compatible with ABC)
        result = CritiqueResult(**json.loads(raw))
        return result.model_dump()
