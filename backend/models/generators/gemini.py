from google import genai
from google.genai import types
from PIL import Image
import io
from typing import List, Optional

from models.base import ImageGenerator


class GeminiGenerator(ImageGenerator):
    """Gemini-based image generation backend."""

    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt: str, aspect_ratio: str = "1:1", input_images: Optional[List[Image.Image]] = None) -> Image.Image:
        """Generate an image from a text prompt. Returns a PIL Image."""
        # Call the model requesting image output
        # Pass aspect_ratio via generation_config
        # If input_images provided, include them in the request for composition
        # The response will contain an inline image part
        # Extract the image bytes and return as PIL.Image

        config = types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            ),
        )

        if input_images and len(input_images) > 0:
            # Build content with input images + prompt
            content_parts = [prompt]
            for img in input_images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                # Create a Part with inline image data
                content_parts.append(types.Part.from_bytes(
                    data=buf.getvalue(),
                    mime_type="image/png"
                ))

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=content_parts,
                config=config,
            )
        else:
            # Text-only prompt
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )

        image_bytes = response.candidates[0].content.parts[0].inline_data.data
        return Image.open(io.BytesIO(image_bytes))

    def inpaint(self, image: Image.Image, mask: Image.Image, prompt: str, aspect_ratio: str = "1:1") -> Image.Image:
        """Apply fixes to an image using inpainting. Returns a PIL Image."""
        # Encode base image and mask as PNG bytes
        # Send both to the model with the fix prompt
        # Use the editing/inpainting capability of gemini-3-pro-image-preview
        # Return the resulting PIL.Image

        config = types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,  # Use the stored aspect ratio
            ),
        )

        # Build content with image, mask, and prompt (mirroring generate method pattern)
        content_parts = [prompt]

        # Add base image
        buf_img = io.BytesIO()
        image.save(buf_img, format="PNG")
        content_parts.append(types.Part.from_bytes(
            data=buf_img.getvalue(),
            mime_type="image/png"
        ))

        # Add mask
        buf_mask = io.BytesIO()
        mask.save(buf_mask, format="PNG")
        content_parts.append(types.Part.from_bytes(
            data=buf_mask.getvalue(),
            mime_type="image/png"
        ))

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=content_parts,
            config=config,
        )

        image_bytes = response.candidates[0].content.parts[0].inline_data.data
        return Image.open(io.BytesIO(image_bytes))
