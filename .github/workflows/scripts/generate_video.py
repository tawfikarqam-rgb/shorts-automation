
import os
import shutil
import requests
from pathlib import Path
from urllib.parse import urlparse
from gradio_client import Client

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

PROMPT = os.environ.get(
    "VIDEO_PROMPT",
    "A tiny orange kitten exploring a futuristic neon city"
)
SEED = int(os.environ.get("VIDEO_SEED", "-1"))


def save_result(value, depth=0):
    """Find a generated video in common Gradio result formats."""
    if depth > 6 or value is None:
        return None

    if isinstance(value, (list, tuple)):
        for item in value:
            saved = save_result(item, depth + 1)
            if saved:
                return saved
        return None

    if isinstance(value, dict):
        for key in ("video", "path", "url", "name", "data"):
            if key in value:
                saved = save_result(value[key], depth + 1)
                if saved:
                    return saved
        for item in value.values():
            saved = save_result(item, depth + 1)
            if saved:
                return saved
        return None

    if not isinstance(value, str):
        return None

    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if not parsed.path.lower().endswith(
            (".mp4", ".webm", ".mov", ".m4v")
        ):
            return None

        response = requests.get(value, timeout=120)
        response.raise_for_status()

        target = OUTPUT_DIR / "generated.mp4"
        target.write_bytes(response.content)

        if target.stat().st_size > 0:
            return target
        return None

    path = Path(value)
    if path.is_file() and path.suffix.lower() in (
        ".mp4", ".webm", ".mov", ".m4v"
    ):
        target = OUTPUT_DIR / ("generated" + path.suffix.lower())
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
        return target

    return None


def main():
    print("Connecting to public Hugging Face Space...")
    client = Client("mediasynthesismuseum/modelscope-text-to-video")

    print("Submitting generation request...")
    result = client.predict(
        prompt=PROMPT,
        seed=SEED,
        num_frames=24,
        num_inference_steps=25,
        api_name="/generate",
    )

    print("Returned result type:", type(result).__name__)
    print("Returned result:", repr(result)[:3000])

    saved = save_result(result)
    if not saved:
        raise RuntimeError(
            "Generation returned no downloadable video file. "
            "Inspect the result above and the Space API output schema."
        )

    print("VIDEO_SAVED:", saved)
    print("VIDEO_BYTES:", saved.stat().st_size)


if __name__ == "__main__":
    main()
