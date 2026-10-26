
import asyncio
import os
import subprocess
from pathlib import Path

import edge_tts

CHANNEL = os.environ["CHANNEL_ID"]
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

STORIES = {
    "secrets-mysteries": {
        "title": "The Lost Colony of Roanoke",
        "voice": "en-US-AndrewNeural",
        "script": (
            "In 1587, more than one hundred English settlers arrived "
            "on Roanoke Island. Then their colony mysteriously vanished. "
            "When a relief expedition returned, the settlement was empty. "
            "The word Croatoan had been carved into a post. "
            "What happened to the colonists remains uncertain. "
            "Disease, relocation, and conflict are among the theories. "
            "But no single explanation has been proven. "
            "Would you have joined an expedition to find them?"
        ),
    },
    "money-power-stories": {
        "title": "How Blockbuster Lost Its Crown",
        "voice": "en-US-AndrewNeural",
        "script": (
            "Blockbuster once dominated movie rentals, with stores "
            "around the world. Then home entertainment began to change. "
            "Netflix offered a different way to rent movies, "
            "and later moved into streaming. Blockbuster struggled "
            "with debt, competition, and a changing business model. "
            "In 2010, the company filed for bankruptcy protection. "
            "The lesson is not that one competitor caused everything. "
            "It is that a famous brand can still fail to adapt."
        ),
    },
}


def run(command):
    subprocess.run(command, check=True)


def probe_duration(path):
    result = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ], text=True)
    return float(result.strip())


async def make_voice(text, destination, voice):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    voices = [voice, "en-US-EmmaNeural", "en-US-AriaNeural"]
    last_error = None

    for selected_voice in voices:
        try:
            if destination.exists():
                destination.unlink()

            await asyncio.wait_for(
                edge_tts.Communicate(
                    text=text,
                    voice=selected_voice,
                ).save(str(destination)),
                timeout=90,
            )

            if destination.exists() and destination.stat().st_size > 1000:
                print(f"AUDIO_OK voice={selected_voice}")
                return

            raise RuntimeError("Audio file missing or too small")

        except Exception as exc:
            last_error = exc
            print(
                f"AUDIO_ATTEMPT_FAILED voice={selected_voice} "
                f"error={type(exc).__name__}: {exc}"
            )
            await asyncio.sleep(2)

    raise RuntimeError(f"Audio generation failed: {last_error}")


def make_srt(text, destination, total_seconds):
    words = text.split()
    chunks = [
        " ".join(words[i:i + 7])
        for i in range(0, len(words), 7)
    ]
    total_words = sum(len(chunk.split()) for chunk in chunks)
    cursor = 0.0
    lines = []

    def stamp(seconds):
        millis = int(seconds * 1000)
        hours, millis = divmod(millis, 3_600_000)
        minutes, millis = divmod(millis, 60_000)
        seconds, millis = divmod(millis, 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

    for index, chunk in enumerate(chunks, start=1):
        duration = total_seconds * len(chunk.split()) / total_words
        start = cursor
        cursor += duration
        lines.append(
            f"{index}\n{stamp(start)} --> {stamp(cursor)}\n{chunk}\n"
        )

    destination.write_text("\n".join(lines), encoding="utf-8")


def main():
    if CHANNEL not in STORIES:
        raise ValueError(f"Unknown CHANNEL_ID: {CHANNEL}")

    story = STORIES[CHANNEL]
    scenes = sorted(
        path for path in OUTPUT.glob("scene_*")
        if path.is_file()
        and path.suffix.lower() in {".mp4", ".mov", ".webm", ".avi"}
    )

    if not scenes:
        raise FileNotFoundError(
            "No scene_XX video files found. Run generate_video.py first."
        )

    print(f"CHANNEL={CHANNEL}")
    print(f"STORY={story['title']}")
    print(f"SCENE_COUNT={len(scenes)}")

    audio = OUTPUT / "narration.mp3"
    subtitles = OUTPUT / "captions.srt"
    final_video = OUTPUT / "final_short.mp4"

    asyncio.run(make_voice(story["script"], audio, story["voice"]))
    duration = probe_duration(audio)
    make_srt(story["script"], subtitles, duration)

    # Normalize each scene to the same vertical format and frame rate.
    normalized = []

    for index, scene in enumerate(scenes, start=1):
        normalized_path = OUTPUT / f"normalized_{index:02d}.mp4"

        run([
            "ffmpeg", "-y", "-i", str(scene),
            "-an",
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,fps=30,setsar=1",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "25",
            "-pix_fmt", "yuv420p",
            "-t", "4",
            str(normalized_path),
        ])

        if not normalized_path.exists() or normalized_path.stat().st_size == 0:
            raise RuntimeError(f"Failed to normalize {scene}")

        normalized.append(normalized_path)

    # Concatenate the distinct clips. The combined sequence is looped
    # only if needed to cover narration; scene order remains varied.
    concat_file = OUTPUT / "scene_list.txt"
    concat_file.write_text(
        "".join(f"file '{path.resolve()}'\n" for path in normalized),
        encoding="utf-8",
    )

    base_video = OUTPUT / "combined_scenes.mp4"

    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(base_video),
    ])

    video_duration = probe_duration(base_video)

    if video_duration < duration:
        # Repeat the entire sequence, not an individual scene.
        run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(base_video),
            "-i", str(audio),
            "-t", f"{duration:.3f}",
            "-vf",
            "subtitles=output/captions.srt:"
            "force_style='FontName=DejaVu Sans,FontSize=18,"
            "Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=180'",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(final_video),
        ])
    else:
        run([
            "ffmpeg", "-y",
            "-i", str(base_video),
            "-i", str(audio),
            "-t", f"{duration:.3f}",
            "-vf",
            "subtitles=output/captions.srt:"
            "force_style='FontName=DejaVu Sans,FontSize=18,"
            "Bold=1,Outline=2,Shadow=1,Alignment=2,MarginV=180'",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(final_video),
        ])

    if not final_video.exists() or final_video.stat().st_size < 10_000:
        raise RuntimeError("Final video missing or unexpectedly small")

    run([
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "csv=p=0",
        str(final_video),
    ])

    print(f"FINAL_VIDEO={final_video}")
    print(f"FINAL_SIZE={final_video.stat().st_size}")
    print(f"FINAL_DURATION={probe_duration(final_video):.2f}")


if __name__ == "__main__":
    main()
