from abc import ABC, abstractmethod
from PIL import Image
from typing import Optional, List

class ImageGenerator(ABC):
    """Abstract base class for image generation backends."""

    @abstractmethod
    def generate(self, prompt: str, aspect_ratio: str = "1:1", input_images: Optional[List[Image.Image]] = None) -> Image.Image:
        """Generate an image from a text prompt. Returns a PIL Image."""
        ...

    @abstractmethod
    def inpaint(self, image: Image.Image, mask: Image.Image, prompt: str, aspect_ratio: str = "1:1") -> Image.Image:
        """Apply fixes to an image using inpainting. Returns a PIL Image."""
        ...


class ImageCritic(ABC):
    """Abstract base class for image critique backends."""

    @abstractmethod
    def critique(self, image: Image.Image, prompt: str, input_images: Optional[List[Image.Image]] = None) -> dict:
        """
        Critique a generated image against the original prompt.
        Returns a CritiqueResult as a dict.
        """
        ...

    @abstractmethod
    def infer_composition_prompt(self, images: List[Image.Image]) -> str:
        """
        Analyze images and suggest a composition prompt.
        Returns a string prompt.
        """
        ...
