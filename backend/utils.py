"""Utility functions for image and video processing."""
from PIL import Image
from typing import List
import subprocess
import os


def split_storyboard_grid(storyboard_image: Image.Image, rows: int = 2, cols: int = 3) -> List[Image.Image]:
    """
    Split a storyboard grid image into individual panels.

    Args:
        storyboard_image: PIL Image containing the storyboard grid
        rows: Number of rows in the grid (default: 2)
        cols: Number of columns in the grid (default: 3)

    Returns:
        List of PIL Images, one for each panel (ordered left-to-right, top-to-bottom)
    """
    width, height = storyboard_image.size
    panel_width = width // cols
    panel_height = height // rows

    panels = []
    for row in range(rows):
        for col in range(cols):
            left = col * panel_width
            top = row * panel_height
            right = left + panel_width
            bottom = top + panel_height

            panel = storyboard_image.crop((left, top, right, bottom))
            panels.append(panel)

    print(f"Split {width}x{height} storyboard into {len(panels)} panels of {panel_width}x{panel_height}")
    return panels


def concatenate_videos(video_paths: List[str], output_path: str) -> str:
    """
    Concatenate multiple video files into a single video using ffmpeg.

    Args:
        video_paths: List of paths to video files to concatenate
        output_path: Path where the concatenated video should be saved

    Returns:
        Path to the concatenated video file
    """
    if not video_paths:
        raise ValueError("No video paths provided for concatenation")

    # Verify all input videos exist
    missing_videos = [p for p in video_paths if not os.path.exists(p)]
    if missing_videos:
        raise FileNotFoundError(f"Missing video files: {missing_videos}")

    print(f"\nConcatenating {len(video_paths)} videos:")
    for i, path in enumerate(video_paths, 1):
        size = os.path.getsize(path)
        print(f"  {i}. {os.path.basename(path)} ({size:,} bytes)")

    # Create a temporary file list for ffmpeg
    concat_list_path = output_path + ".concat_list.txt"

    try:
        # Write the list of files to concatenate
        with open(concat_list_path, 'w') as f:
            for path in video_paths:
                # Use absolute paths and escape special characters
                abs_path = os.path.abspath(path)
                f.write(f"file '{abs_path}'\n")

        # Run ffmpeg to concatenate
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list_path,
            '-c', 'copy',
            '-y',  # Overwrite output file if it exists
            output_path
        ]

        print(f"\nRunning ffmpeg concatenation...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        final_size = os.path.getsize(output_path)
        print(f"✓ Successfully concatenated videos to {output_path} ({final_size:,} bytes)")

        return output_path

    except subprocess.CalledProcessError as e:
        print(f"✗ Error concatenating videos:")
        print(f"  stdout: {e.stdout}")
        print(f"  stderr: {e.stderr}")
        raise
    finally:
        # Clean up the temporary concat list file
        if os.path.exists(concat_list_path):
            os.remove(concat_list_path)


def save_asset(asset, path: str, asset_type: str = "auto"):
    """
    Save an asset (image, video bytes, or text) to disk.

    Args:
        asset: The asset to save (PIL.Image, bytes, or str)
        path: Path where the asset should be saved
        asset_type: Type of asset ('image', 'video', 'text', or 'auto' to detect)
    """
    # Ensure directory exists
    dir_path = os.path.dirname(path)
    if dir_path:  # Only create if there's a directory component
        os.makedirs(dir_path, exist_ok=True)

    if asset_type == "auto":
        if isinstance(asset, Image.Image):
            asset_type = "image"
        elif isinstance(asset, bytes):
            asset_type = "video"
        elif isinstance(asset, str):
            asset_type = "text"
        else:
            raise ValueError(f"Cannot auto-detect asset type for {type(asset)}")

    try:
        if asset_type == "image":
            asset.save(path)
            print(f"✓ Saved image to {path}")
        elif asset_type == "video":
            with open(path, 'wb') as f:
                f.write(asset)
            print(f"✓ Saved video to {path} ({len(asset):,} bytes)")
        elif asset_type == "text":
            with open(path, 'w') as f:
                f.write(asset)
            print(f"✓ Saved text to {path} ({len(asset)} chars)")
        else:
            raise ValueError(f"Unknown asset type: {asset_type}")

        # Verify file was created
        if not os.path.exists(path):
            raise IOError(f"File was not created: {path}")

        return path
    except Exception as e:
        print(f"✗ ERROR saving asset to {path}: {e}")
        raise
