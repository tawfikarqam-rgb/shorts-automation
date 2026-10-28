#!/usr/bin/env python3
"""Fail the pipeline before upload when a rendered Short is technically invalid."""
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "output/final_short.mp4")
    if not path.is_file():
        raise SystemExit(f"VALIDATION_FAILED: file not found: {path}")

    size = path.stat().st_size
    if size < 500_000:
        raise SystemExit(f"VALIDATION_FAILED: file is suspiciously small ({size} bytes)")

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,width,height,codec_name",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(result.stdout)
    streams = metadata.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if video is None:
        raise SystemExit("VALIDATION_FAILED: no video stream")
    if audio is None:
        raise SystemExit("VALIDATION_FAILED: no audio stream; narration may be missing")

    width, height = video.get("width"), video.get("height")
    if not width or not height or width < 720 or height < 1280:
        raise SystemExit(f"VALIDATION_FAILED: resolution too low: {width}x{height}")
    if abs((width / height) - (9 / 16)) > 0.015:
        raise SystemExit(f"VALIDATION_FAILED: expected vertical 9:16 video, got {width}x{height}")

    duration = float(metadata.get("format", {}).get("duration", 0))
    if not 10 <= duration <= 180:
        raise SystemExit(f"VALIDATION_FAILED: duration {duration:.2f}s is outside 10-180 seconds")

    print("VIDEO_VALIDATION=PASS")
    print(f"VIDEO_RESOLUTION={width}x{height}")
    print(f"VIDEO_DURATION_SECONDS={duration:.2f}")
    print(f"VIDEO_CODEC={video.get('codec_name', 'unknown')}")
    print(f"AUDIO_CODEC={audio.get('codec_name', 'unknown')}")
    print(f"VIDEO_FILE_SIZE_BYTES={size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
