
import os
import sys
import traceback
from pathlib import Path

def main():
    prompt = os.environ.get(
        "VIDEO_PROMPT",
        "A cinematic view of a futuristic city at sunrise"
    )
    seed = int(os.environ.get("VIDEO_SEED", "-1"))

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Connecting to Hugging Face Space...")
    print("Space: mediasynthesismuseum/modelscope-text-to-video")
    print(f"Prompt: {prompt}")
    print(f"Seed: {seed}")

    from gradio_client import Client

    client = Client(
        "mediasynthesismuseum/modelscope-text-to-video"
    )

    result = client.predict(
        prompt=prompt,
        seed=seed,
        num_frames=24,
        num_inference_steps=25,
        api_name="/generate",
    )

    print("Generation request completed.")
    print("Returned result:", repr(result))

    # Gradio may return a file path or a more complex result.
    def find_files(value):
        if isinstance(value, str):
            candidate = Path(value)
            if candidate.is_file():
                yield candidate
        elif isinstance(value, dict):
            for item in value.values():
                yield from find_files(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from find_files(item)

    files = list(find_files(result))

    if not files:
        raise RuntimeError(
            "The Space returned no detectable local file. "
            "Check the printed result and the Space API output format."
        )

    import shutil

    saved = False
    for index, source in enumerate(files, start=1):
        suffix = source.suffix or ".mp4"
        destination = output_dir / f"video_{index}{suffix}"
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        print(f"Saved output: {destination}")
        saved = True

    if not saved:
        raise RuntimeError("No video file was saved.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
