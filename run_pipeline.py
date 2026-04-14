#!/usr/bin/env python3
"""
CLI script to run the agentic image generation pipeline.

Usage:
    # Manual mode (single reference image)
    python run_pipeline.py --prompt "your prompt here"
    python run_pipeline.py --prompt "your prompt here" --image https://example.com/image.jpg
    python run_pipeline.py --prompt "your prompt here" --image /path/to/local/image.jpg
    python run_pipeline.py --prompt "your prompt here" --output output.png

    # Using presets from config file (can include 1-3 reference images)
    python run_pipeline.py --preset landscape_scene     # No reference images
    python run_pipeline.py --preset styled_portrait     # 1 reference image
    python run_pipeline.py --preset city_night          # 2 reference images
    python run_pipeline.py --preset nature_inspired     # 3 reference images
"""

import argparse
import sys
import os
from pathlib import Path
import yaml

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import loader
import runner
from PIL import Image
import requests
from io import BytesIO


def load_config(config_path="pipeline_config.yaml"):
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        return None

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_image_from_url(url):
    """Load image from URL or local path."""
    if url.startswith(('http://', 'https://')):
        print(f"Downloading image from {url}...")
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    else:
        print(f"Loading image from {url}...")
        return Image.open(url)


def run_pipeline(prompt, image_urls=None, aspect_ratio="1:1", pipeline_name="default", output_path=None):
    """Run the agentic image generation pipeline."""

    # Load pipeline
    print(f"Loading pipeline: {pipeline_name}")
    agents = loader.load_pipeline(pipeline_name)

    # Initialize context
    context = {
        "original_prompt": prompt,
        "aspect_ratio": aspect_ratio
    }

    # Load reference images if provided (supports multiple)
    if image_urls:
        input_images = []
        for idx, image_url in enumerate(image_urls):
            try:
                input_image = load_image_from_url(image_url)
                input_images.append(input_image)
                print(f"Loaded reference image {idx+1}/{len(image_urls)}: {input_image.size} {input_image.mode}")
            except Exception as e:
                print(f"Warning: Failed to load image from {image_url}: {e}")

        if input_images:
            context["input_images"] = input_images
            print(f"Total reference images loaded: {len(input_images)}")
        else:
            print("No reference images loaded, continuing without them")

    # Run through all agents
    print(f"\nStarting pipeline with prompt: '{prompt}'")
    print(f"Aspect ratio: {aspect_ratio}")
    print("-" * 80)

    for idx, agent in enumerate(agents):
        print(f"\n[{idx+1}/{len(agents)}] Running {agent.display_name} ({agent.name})...")

        try:
            context = runner.run_agent(agent, context)

            # Show outputs
            for output in agent.outputs:
                output_name = output["target"]
                if output_name in context:
                    value = context[output_name]

                    # Show text outputs
                    if isinstance(value, str):
                        print(f"  → {output_name}:")
                        # Truncate long outputs
                        if len(value) > 200:
                            print(f"    {value[:200]}...")
                        else:
                            print(f"    {value}")
                    elif output_name == "image":
                        print(f"  → Generated image: {value.size} {value.mode}")

                        # Save and display image immediately
                        save_path = output_path if output_path else "generated_image.png"
                        value.save(save_path)
                        print(f"  → Saved to: {save_path}")

                        # Display the image (macOS)
                        try:
                            import subprocess
                            subprocess.run(['open', save_path], check=False)
                            print(f"  → Opening image...")
                        except Exception as e:
                            print(f"  → Image saved (could not auto-open: {e})")

                    elif output_name == "critique":
                        print(f"  → critique score: {value.get('overall_score', 'N/A')}")
                        print(f"    pass: {value.get('pass_threshold_met', False)}")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            raise

    # Final results
    print("\n" + "=" * 80)
    print("Pipeline completed!")

    if "image" in context:
        generated_image = context["image"]
        print(f"\nFinal image: {generated_image.size} {generated_image.mode}")

    if "video_path" in context:
        # Video generation returns raw bytes, save them
        video_bytes = context.get("video_path")
        if video_bytes and isinstance(video_bytes, bytes):
            video_output_path = "generated_video.mp4"
            with open(video_output_path, 'wb') as f:
                f.write(video_bytes)
            print(f"\nGenerated video saved to: {video_output_path}")
            print(f"Video size: {len(video_bytes)} bytes")

    if "critique" in context:
        critique = context["critique"]
        print(f"\nCritique score: {critique.get('overall_score', 'N/A')}/1.0")
        print(f"Assessment: {critique.get('overall_assessment', 'N/A')}")
        print(f"Passed: {critique.get('pass_threshold_met', False)}")

    print("=" * 80)

    return context


def main():
    parser = argparse.ArgumentParser(
        description="Run the agentic image generation pipeline from CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Manual mode
  python run_pipeline.py --prompt "a serene mountain landscape at sunset"
  python run_pipeline.py --prompt "a futuristic city" --image https://example.com/ref.jpg
  python run_pipeline.py --prompt "cyberpunk portrait" --image ./reference.jpg --aspect-ratio 16:9

  # Using presets from config file
  python run_pipeline.py --config pipeline_config.yaml --preset landscape_scene
  python run_pipeline.py --config pipeline_config.yaml --preset styled_portrait
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to YAML config file (default: pipeline_config.yaml)"
    )

    parser.add_argument(
        "--preset",
        type=str,
        help="Preset name from config file"
    )

    parser.add_argument(
        "--prompt",
        type=str,
        help="The prompt describing what to generate"
    )

    parser.add_argument(
        "--image",
        type=str,
        help="Reference image URL or local path (optional)"
    )

    parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="9:16",
        choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
        help="Aspect ratio for generation (default: 1:1)"
    )

    parser.add_argument(
        "--pipeline",
        type=str,
        default="default",
        help="Pipeline name to run (default: default)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: generated_image.png)"
    )

    args = parser.parse_args()

    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        # Check for API key
        if not os.getenv("GOOGLE_API_KEY"):
            print("Error: GOOGLE_API_KEY not found in environment")
            print("Please set it in your .env file or environment")
            sys.exit(1)

        # Load preset from config if specified
        prompt = args.prompt
        image_urls = [args.image] if args.image else []
        aspect_ratio = args.aspect_ratio
        pipeline_name = args.pipeline
        output_path = args.output

        if args.preset:
            config_path = args.config or "pipeline_config.yaml"
            config = load_config(config_path)

            if not config:
                print(f"Error: Config file not found: {config_path}")
                sys.exit(1)

            if "presets" not in config or args.preset not in config["presets"]:
                print(f"Error: Preset '{args.preset}' not found in {config_path}")
                print(f"Available presets: {', '.join(config.get('presets', {}).keys())}")
                sys.exit(1)

            preset = config["presets"][args.preset]
            print(f"Loading preset: {args.preset}")

            # Override with preset values
            prompt = preset.get("prompt", prompt)
            # Load images array from preset (1-3 images)
            preset_images = preset.get("images", [])
            if preset_images:
                image_urls = preset_images[:3]  # Limit to 3 images max

            print(f"Preset prompt: {prompt}")
            if image_urls:
                print(f"Preset images ({len(image_urls)}):")
                for idx, img in enumerate(image_urls):
                    print(f"  {idx+1}. {img}")

        # Validate that we have a prompt
        if not prompt:
            print("Error: --prompt is required (or use --preset)")
            sys.exit(1)

        # Run pipeline once with all reference images
        run_pipeline(
            prompt=prompt,
            image_urls=image_urls if image_urls else None,
            aspect_ratio=aspect_ratio,
            pipeline_name=pipeline_name,
            output_path=output_path
        )

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
