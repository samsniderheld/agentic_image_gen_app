#!/usr/bin/env python3
"""
Extended pipeline script with parallel agent execution and asset saving.

This pipeline implements the following flow:
1. Image load (from user input)
2. Planner (single output)
3. Art Director (single output)
4. Script Writer (single output - 6 shots)
5. Storyboard Artist (single output - 3x2 grid image)
6. Split storyboard into 6 panels
7. Run 6 parallel instances of: DOP -> Image Gen -> Video Gen
8. Concatenate all 6 videos into final output

All assets are saved at each step to outputs/extended/

Usage:
    python run_pipeline_extended.py --prompt "your prompt here"
    python run_pipeline_extended.py --prompt "your prompt here" --image /path/to/image.jpg
    python run_pipeline_extended.py --preset landscape_scene
"""

import argparse
import sys
import os
from pathlib import Path
import yaml
import asyncio
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import loader
import runner
from utils import split_storyboard_grid, concatenate_videos, save_asset
from PIL import Image
import requests
from io import BytesIO


def setup_output_dir(base_dir="outputs/extended"):
    """Create timestamped output directory for this run."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(base_dir) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


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


async def run_shot_pipeline(shot_num, shot_panel, script_text, context, output_dir):
    """
    Run the complete pipeline for a single shot: DOP -> Image Gen -> Video Gen.

    Args:
        shot_num: Shot number (1-6)
        shot_panel: PIL Image of the storyboard panel
        script_text: The script text for this shot
        context: Shared context dict
        output_dir: Directory to save outputs

    Returns:
        Path to the generated video file
    """
    print(f"\n{'='*80}")
    print(f"Processing Shot {shot_num}/6")
    print(f"{'='*80}")

    # Create shot-specific context
    shot_context = context.copy()

    # Add storyboard panel to input_images for reference
    panel_images = [shot_panel]
    if "input_images" in context:
        panel_images.extend(context["input_images"])
    shot_context["input_images"] = panel_images

    # Update enriched_prompt with shot-specific script
    shot_context["enriched_prompt"] = f"{context.get('enriched_prompt', context['original_prompt'])}\n\nShot description: {script_text}"

    # Save storyboard panel
    panel_path = output_dir / f"shot_{shot_num:02d}_panel.png"
    save_asset(shot_panel, str(panel_path))

    # Load agents for this shot
    dop_agent = loader.load_agent("dop")
    generator_agent = loader.load_agent("generator")
    veo_agent = loader.load_agent("veo_generator")

    # Run DOP
    print(f"\n[Shot {shot_num}] Running DOP...")
    print(f"  Script: {script_text}")
    shot_context = await runner.run_agent_async(dop_agent, shot_context)
    shot_brief_path = output_dir / f"shot_{shot_num:02d}_brief.txt"
    save_asset(shot_context["shot_brief"], str(shot_brief_path))
    print(f"  → Shot brief: {shot_context['shot_brief'][:100]}...")

    # Run Image Generator
    print(f"\n[Shot {shot_num}] Running Image Generator...")
    shot_context = await runner.run_agent_async(generator_agent, shot_context)
    image_path = output_dir / f"shot_{shot_num:02d}_image.png"
    save_asset(shot_context["image"], str(image_path))
    print(f"  → Generated image: {shot_context['image'].size}")

    # Run Video Generator
    print(f"\n[Shot {shot_num}] Running Video Generator...")
    shot_context = await runner.run_agent_async(veo_agent, shot_context)

    # Debug: Check what we got back
    video_data = shot_context.get("video_path")
    print(f"  → Video data type: {type(video_data)}")
    if isinstance(video_data, bytes):
        print(f"  → Video data size: {len(video_data):,} bytes")
    else:
        print(f"  → WARNING: Expected bytes, got {type(video_data)}")

    video_path = output_dir / f"shot_{shot_num:02d}_video.mp4"
    saved_path = save_asset(video_data, str(video_path))
    print(f"  → Video saved to: {saved_path}")

    print(f"\n[Shot {shot_num}] Complete!")
    return str(video_path)


async def run_extended_pipeline(prompt, image_urls=None, aspect_ratio="9:16", output_dir=None):
    """Run the extended agentic image generation pipeline with parallel execution."""

    if output_dir is None:
        output_dir = setup_output_dir()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nOutput directory: {output_dir}")
    print("="*80)

    # Initialize context
    context = {
        "original_prompt": prompt,
        "aspect_ratio": aspect_ratio
    }

    # Load reference images if provided
    if image_urls:
        input_images = []
        for idx, image_url in enumerate(image_urls):
            try:
                input_image = load_image_from_url(image_url)
                input_images.append(input_image)
                print(f"Loaded reference image {idx+1}/{len(image_urls)}: {input_image.size}")
                # Save reference image
                save_asset(input_image, str(output_dir / f"input_image_{idx+1}.png"))
            except Exception as e:
                print(f"Warning: Failed to load image from {image_url}: {e}")

        if input_images:
            context["input_images"] = input_images
            print(f"Total reference images loaded: {len(input_images)}")

    # Phase 1: Sequential single-output agents
    print(f"\n{'='*80}")
    print("PHASE 1: Planning and Storyboarding")
    print(f"{'='*80}")

    # Load and run initial agents
    planner = loader.load_agent("planner")
    art_director = loader.load_agent("art_director")
    script_writer = loader.load_agent("script")
    storyboard_artist = loader.load_agent("storyboard")

    # Run Planner
    print(f"\n[1/4] Running Planner...")
    context = await runner.run_agent_async(planner, context)
    save_asset(context["enriched_prompt"], str(output_dir / "01_enriched_prompt.txt"))
    print(f"  → Enriched prompt: {context['enriched_prompt'][:150]}...")

    # Run Art Director
    print(f"\n[2/4] Running Art Director...")
    context = await runner.run_agent_async(art_director, context)
    save_asset(context["style_brief"], str(output_dir / "02_style_brief.txt"))
    print(f"  → Style brief: {context['style_brief'][:150]}...")

    # Run Script Writer
    print(f"\n[3/4] Running Script Writer...")
    context = await runner.run_agent_async(script_writer, context)
    save_asset(context["script"], str(output_dir / "03_script.txt"))
    print(f"  → Script (6 shots):\n{context['script']}")

    # Run Storyboard Artist
    print(f"\n[4/4] Running Storyboard Artist...")
    context = await runner.run_agent_async(storyboard_artist, context)
    save_asset(context["storyboard_image"], str(output_dir / "04_storyboard_grid.png"))
    print(f"  → Storyboard: {context['storyboard_image'].size}")

    # Phase 2: Split storyboard into panels
    print(f"\n{'='*80}")
    print("PHASE 2: Processing Storyboard")
    print(f"{'='*80}")

    storyboard_panels = split_storyboard_grid(context["storyboard_image"], rows=2, cols=3)
    print(f"Split storyboard into {len(storyboard_panels)} panels")

    # Parse script into individual shots
    script_lines = context["script"].strip().split('\n')
    shot_scripts = []
    for line in script_lines:
        if line.strip().startswith("Shot"):
            shot_scripts.append(line.strip())

    # Ensure we have exactly 6 shots
    while len(shot_scripts) < 6:
        shot_scripts.append(f"Shot {len(shot_scripts)+1}: [Generated from prompt]")

    # Phase 3: Parallel execution of 6 shot pipelines
    print(f"\n{'='*80}")
    print("PHASE 3: Generating 6 Shots in Parallel")
    print(f"{'='*80}")

    # Create tasks for all 6 shots
    shot_tasks = []
    for i in range(6):
        task = run_shot_pipeline(
            shot_num=i+1,
            shot_panel=storyboard_panels[i],
            script_text=shot_scripts[i],
            context=context,
            output_dir=output_dir
        )
        shot_tasks.append(task)

    # Run all shots in parallel
    video_paths = await asyncio.gather(*shot_tasks)

    # Phase 4: Concatenate videos
    print(f"\n{'='*80}")
    print("PHASE 4: Concatenating Videos")
    print(f"{'='*80}")

    final_video_path = str(output_dir / "final_video.mp4")
    concatenate_videos(video_paths, final_video_path)

    print(f"\n{'='*80}")
    print("PIPELINE COMPLETE!")
    print(f"{'='*80}")
    print(f"\nFinal video saved to: {final_video_path}")
    print(f"All assets saved to: {output_dir}")

    # Try to open the final video
    try:
        import subprocess
        subprocess.run(['open', final_video_path], check=False)
        print(f"Opening final video...")
    except Exception as e:
        print(f"Video saved (could not auto-open: {e})")

    return {
        "output_dir": str(output_dir),
        "final_video": final_video_path,
        "video_paths": video_paths,
        "context": context
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run the extended agentic pipeline with parallel execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--config", type=str, help="Path to YAML config file")
    parser.add_argument("--preset", type=str, help="Preset name from config file")
    parser.add_argument("--prompt", type=str, help="The prompt describing what to generate")
    parser.add_argument("--image", type=str, help="Reference image URL or local path")
    parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="9:16",
        choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
        help="Aspect ratio for generation (default: 9:16)"
    )
    parser.add_argument("--output-dir", type=str, help="Custom output directory")

    args = parser.parse_args()

    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        # Check for API key
        if not os.getenv("GOOGLE_API_KEY"):
            print("Error: GOOGLE_API_KEY not found in environment")
            sys.exit(1)

        # Load preset from config if specified
        prompt = args.prompt
        image_urls = [args.image] if args.image else []
        aspect_ratio = args.aspect_ratio
        output_dir = args.output_dir

        if args.preset:
            config_path = args.config or "pipeline_config.yaml"
            config = load_config(config_path)

            if not config:
                print(f"Error: Config file not found: {config_path}")
                sys.exit(1)

            if "presets" not in config or args.preset not in config["presets"]:
                print(f"Error: Preset '{args.preset}' not found in {config_path}")
                sys.exit(1)

            preset = config["presets"][args.preset]
            print(f"Loading preset: {args.preset}")

            prompt = preset.get("prompt", prompt)
            preset_images = preset.get("images", [])
            if preset_images:
                image_urls = preset_images[:3]

        # Validate prompt
        if not prompt:
            print("Error: --prompt is required (or use --preset)")
            sys.exit(1)

        # Run the extended pipeline
        result = asyncio.run(run_extended_pipeline(
            prompt=prompt,
            image_urls=image_urls if image_urls else None,
            aspect_ratio=aspect_ratio,
            output_dir=output_dir
        ))

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
