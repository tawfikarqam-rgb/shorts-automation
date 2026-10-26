
import os
import sys
import shutil
import traceback
from pathlib import Path

from gradio_client import Client

OUTPUT = Path("output")
OUTPUT.mkdir(parents=True, exist_ok=True)

CHANNEL = os.environ.get("CHANNEL_ID", "secrets-mysteries")
SEED = int(os.environ.get("VIDEO_SEED", "-1"))

SCENES = {
    "secrets-mysteries": [
        (
            "Wide cinematic establishing shot of Roanoke Island "
            "in 1587, wooden English colonial settlement beside "
            "the Atlantic coast, sailing ships offshore, historically "
            "inspired documentary realism, overcast dramatic sky, "
            "vertical composition, no text, no logos"
        ),
        (
            "Close cinematic view of an English sailing ship "
            "approaching a remote island in the late 16th century, "
            "rough Atlantic waves, weathered wooden ship, historical "
            "documentary realism, vertical composition, no text, no logos"
        ),
        (
            "Abandoned 16th century English colonial settlement, "
            "empty wooden huts, overgrown paths, mist moving through "
            "the trees, mysterious historical documentary atmosphere, "
            "vertical composition, no text, no logos"
        ),
        (
            "Close-up of an old weathered wooden post in a deserted "
            "colonial settlement, mysterious carved marks, shallow "
            "depth of field, dramatic natural light, historical "
            "documentary style, vertical composition, no text, no logos"
        ),
    ],
    "money-power-stories": [
        (
            "Busy 1990s American Blockbuster video rental store, "
            "customers browsing shelves of VHS movie cases, "
            "recognizable blue and yellow retail design without "
            "readable text, realistic business documentary, "
            "vertical composition, no logos"
        ),
        (
            "Rows of VHS tapes and movie rental shelves inside "
            "a large 1990s video rental store, warm fluorescent "
            "lighting, nostalgic business documentary photography, "
            "vertical composition, no readable text, no logos"
        ),
        (
            "Person watching movies at home on an early laptop, "
            "DVD rental envelope on a table, early 2000s technology, "
            "cinematic business history documentary, vertical "
            "composition, no readable text, no logos"
        ),
        (
            "Nearly empty video rental store with bare shelves, "
            "boxes and closing inventory, subdued cinematic lighting, "
            "symbolizing the decline of a retail business, realistic "
            "documentary photography, vertical composition, no logos"
        ),
    ],
}

def find_video_files(value):
    if isinstance(value, str):
        path = Path(value)
        if path.is_file() and path.suffix.lower() in {
            ".mp4", ".mov", ".webm", ".avi"
        }:
            yield path

    elif isinstance(value, dict):
        for item in value.values():
            yield from find_video_files(item)

    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from find_video_files(item)


def main():
    if CHANNEL not in SCENES:
        raise ValueError(f"Unknown channel: {CHANNEL}")

    # Remove stale scene files so previous runs cannot be mixed in.
    for old_file in OUTPUT.glob("scene_*"):
        if old_file.is_file():
            old_file.unlink()

    print("Connecting to Hugging Face Space...")
    print("Space: mediasynthesismuseum/modelscope-text-to-video")
    print(f"Channel: {CHANNEL}")

    client = Client(
        "mediasynthesismuseum/modelscope-text-to-video"
    )

    prompts = SCENES[CHANNEL]

    for index, prompt in enumerate(prompts, start=1):
        scene_seed = -1 if SEED < 0 else SEED + index

        print(f"\nGenerating scene {index}/{len(prompts)}")
        print(f"Prompt: {prompt}")
        print(f"Seed: {scene_seed}")

        result = client.predict(
            prompt=prompt,
            seed=scene_seed,
            num_frames=24,
            num_inference_steps=25,
            api_name="/generate",
        )

        files = list(find_video_files(result))

        if not files:
            raise RuntimeError(
                f"No video file returned for scene {index}. "
                f"Result: {result!r}"
            )

        source = files[0]
        destination = OUTPUT / f"scene_{index:02d}{source.suffix.lower()}"

        shutil.copy2(source, destination)

        if not destination.exists() or destination.stat().st_size == 0:
            raise RuntimeError(f"Scene file is empty: {destination}")

        print(
            f"SCENE_OK={destination} "
            f"SIZE={destination.stat().st_size}"
        )

    print(f"SCENES_GENERATED={len(prompts)}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
