#!/usr/bin/env python3
"""
Test script to verify multiple concurrent pipeline executions work correctly.

This script runs multiple image generation pipelines simultaneously and
verifies that they all complete successfully without interfering with each other.
"""

import sys
import os
from pathlib import Path
import threading
import time
from datetime import datetime

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

import loader
import runner

# Test prompts for concurrent generation
TEST_PROMPTS = [
    "a serene mountain landscape at sunset",
    "a futuristic city with flying cars",
    "a cozy coffee shop on a rainy day",
    "a majestic dragon flying over a castle",
    "an underwater scene with colorful coral reefs"
]

results = {}
results_lock = threading.Lock()
active_count = 0
active_count_lock = threading.Lock()


def generate_image(prompt_id, prompt):
    """Run the pipeline directly and track the result"""
    global active_count
    start_time = time.time()
    request_id = f"test-{prompt_id}"

    try:
        with active_count_lock:
            active_count += 1
            current_active = active_count

        print(f"[Thread {prompt_id}] Starting pipeline: {prompt[:40]}...")
        print(f"[Thread {prompt_id}] Active pipelines: {current_active}")

        # Load pipeline
        agents = loader.load_pipeline()

        # Initialize context
        context = {
            "original_prompt": prompt,
            "aspect_ratio": "1:1",
            "request_id": request_id
        }

        # Run all agents in sequence
        for agent in agents:
            print(f"[Thread {prompt_id}] Running agent: {agent.display_name}")
            context = runner.run_agent(agent, context)

        # Check if image was generated
        generated_image = context.get("image")
        generated_video = context.get("video_path")
        duration = time.time() - start_time

        # Create outputs directory if it doesn't exist
        output_dir = Path(__file__).parent / "test_outputs"
        output_dir.mkdir(exist_ok=True)

        # Generate base filename with timestamp and prompt ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = prompt[:30].replace(" ", "_").replace("/", "-")
        base_filename = f"{timestamp}_test{prompt_id}_{safe_prompt}"

        # Save the generated image
        image_path = None
        if generated_image:
            image_filename = f"{base_filename}.png"
            image_path = output_dir / image_filename
            generated_image.save(image_path)
            print(f"[Thread {prompt_id}] Saved image to: {image_path}")

        # Save the generated video
        video_path = None
        if generated_video and isinstance(generated_video, bytes):
            video_filename = f"{base_filename}.mp4"
            video_path = output_dir / video_filename
            with open(video_path, 'wb') as f:
                f.write(generated_video)
            print(f"[Thread {prompt_id}] Saved video to: {video_path} ({len(generated_video)} bytes)")

        with results_lock:
            if generated_image or generated_video:
                results[prompt_id] = {
                    "success": True,
                    "duration": duration,
                    "request_id": request_id,
                    "prompt": prompt,
                    "image_size": generated_image.size if generated_image else None,
                    "image_mode": generated_image.mode if generated_image else None,
                    "image_path": str(image_path) if image_path else None,
                    "video_path": str(video_path) if video_path else None,
                    "video_size": len(generated_video) if generated_video else None
                }
                outputs = []
                if generated_image:
                    outputs.append(f"Image: {generated_image.size} {generated_image.mode}")
                if generated_video:
                    outputs.append(f"Video: {len(generated_video)} bytes")
                print(f"[Thread {prompt_id}] ✓ SUCCESS in {duration:.2f}s - {', '.join(outputs)}")
            else:
                results[prompt_id] = {
                    "success": False,
                    "duration": duration,
                    "error": "No image or video generated",
                    "prompt": prompt
                }
                print(f"[Thread {prompt_id}] ✗ FAILED in {duration:.2f}s: No image or video generated")

    except Exception as e:
        duration = time.time() - start_time
        with results_lock:
            results[prompt_id] = {
                "success": False,
                "duration": duration,
                "error": str(e),
                "prompt": prompt
            }
        print(f"[Thread {prompt_id}] ✗ EXCEPTION in {duration:.2f}s: {e}")
        import traceback
        traceback.print_exc()
    finally:
        with active_count_lock:
            active_count -= 1


def check_environment():
    """Check if environment is properly configured"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("✗ GOOGLE_API_KEY not found in environment")
            print("  Please set it in your .env file")
            return False

        print("✓ GOOGLE_API_KEY found")

        # Try to load pipeline
        agents = loader.load_pipeline()
        print(f"✓ Pipeline loaded with {len(agents)} agents")

        return True
    except Exception as e:
        print(f"✗ Environment check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 80)
    print("CONCURRENT PIPELINE EXECUTION TEST")
    print("=" * 80)

    # Check environment
    print("\nChecking environment...")
    if not check_environment():
        print("\n✗ Environment not configured properly")
        return

    print("\n✓ Environment ready")

    # Launch concurrent pipelines
    num_requests = len(TEST_PROMPTS)
    print(f"\nLaunching {num_requests} concurrent pipeline executions...")
    print("-" * 80)

    threads = []
    start_time = time.time()

    for i, prompt in enumerate(TEST_PROMPTS):
        thread = threading.Thread(target=generate_image, args=(i, prompt))
        threads.append(thread)
        thread.start()
        time.sleep(0.2)  # Small delay to stagger requests slightly

    # Monitor active count while pipelines are running
    print("\nMonitoring active pipelines...")
    last_check = time.time()
    while any(t.is_alive() for t in threads):
        if time.time() - last_check > 3:
            with active_count_lock:
                print(f"  Active pipelines: {active_count}")
            last_check = time.time()
        time.sleep(1)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    total_duration = time.time() - start_time

    # Print results summary
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    successful = sum(1 for r in results.values() if r["success"])
    failed = num_requests - successful

    print(f"\nTotal pipelines: {num_requests}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total time: {total_duration:.2f}s")
    print(f"Average time per pipeline: {total_duration / num_requests:.2f}s")

    if successful > 0:
        avg_duration = sum(r["duration"] for r in results.values() if r["success"]) / successful
        print(f"Average successful pipeline duration: {avg_duration:.2f}s")

        # Calculate speedup from parallelization
        total_sequential = sum(r["duration"] for r in results.values() if r["success"])
        speedup = total_sequential / total_duration
        print(f"Parallelization speedup: {speedup:.2f}x")

    print("\nDetailed Results:")
    print("-" * 80)
    for prompt_id in sorted(results.keys()):
        result = results[prompt_id]
        status = "✓" if result["success"] else "✗"
        print(f"{status} Pipeline {prompt_id}: {result['prompt'][:40]}...")
        print(f"  Duration: {result['duration']:.2f}s")
        if result["success"]:
            print(f"  Request ID: {result['request_id']}")
            if result.get('image_size'):
                print(f"  Image: {result['image_size']} {result['image_mode']}")
                print(f"  Image saved to: {result['image_path']}")
            if result.get('video_path'):
                print(f"  Video: {result['video_size']} bytes")
                print(f"  Video saved to: {result['video_path']}")
        else:
            print(f"  Error: {result.get('error', 'Unknown error')[:100]}")

    # Show where outputs are saved
    if successful > 0:
        output_dir = Path(__file__).parent / "test_outputs"
        print("\n" + "=" * 80)
        print(f"OUTPUT LOCATION")
        print("=" * 80)
        print(f"\nAll generated outputs saved to: {output_dir}")

        # Count images and videos
        total_images = sum(1 for r in results.values() if r.get("success") and r.get("image_path"))
        total_videos = sum(1 for r in results.values() if r.get("success") and r.get("video_path"))

        print(f"Total images: {total_images}")
        print(f"Total videos: {total_videos}")

        # List all saved files
        print("\nSaved files:")
        for prompt_id in sorted(results.keys()):
            result = results[prompt_id]
            if result["success"]:
                if result.get('image_path'):
                    filename = Path(result['image_path']).name
                    print(f"  - {filename}")
                if result.get('video_path'):
                    filename = Path(result['video_path']).name
                    print(f"  - {filename}")
                print(f"    Prompt: {result['prompt']}")

    print("\n" + "=" * 80)
    if failed == 0:
        print("✓ ALL TESTS PASSED - Concurrent pipelines working correctly!")
    else:
        print(f"✗ SOME TESTS FAILED - {failed}/{num_requests} pipelines failed")
    print("=" * 80)


if __name__ == "__main__":
    main()
