
import asyncio
import os
import subprocess
import textwrap
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



async def make_voice(text, destination, voice):
    import asyncio
    import edge_tts

    voices = [
        voice,
        "en-US-EmmaNeural",
        "en-US-AriaNeural",
    ]

    last_error = None

    for attempt in range(3):
        selected_voice = voices[attempt]

        try:
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)

            if destination.exists():
                destination.unlink()

            communicator = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
            )

            await asyncio.wait_for(
                communicator.save(str(destination)),
                timeout=90,
            )

            if not destination.exists() or destination.stat().st_size < 1000:
                raise RuntimeError("Audio file is missing or too small")

            print(f"AUDIO_OK voice={selected_voice}")
            return

        except Exception as exc:
            last_error = exc
            print(
                f"AUDIO_ATTEMPT_FAILED "
                f"attempt={attempt + 1} "
                f"voice={selected_voice} "
                f"error={type(exc).__name__}: {exc}"
            )

            await asyncio.sleep(2 * (attempt + 1))

    raise RuntimeError(
        f"Audio generation failed after 3 attempts: {last_error}"
    )



def make_srt(text, destination, total_seconds):
    words = text.split()
    chunks = [
        " ".join(words[i:i + 7])
        for i in range(0, len(words), 7)
    ]
    total_words = sum(len(c.split()) for c in chunks)
    cursor = 0.0
    lines = []

    for index, chunk in enumerate(chunks, start=1):
        duration = total_seconds * len(chunk.split()) / total_words
        start = cursor
        end = cursor + duration
        cursor = end

        def stamp(seconds):
            millis = int(seconds * 1000)
            hours, millis = divmod(millis, 3_600_000)
            minutes, millis = divmod(millis, 60_000)
            seconds, millis = divmod(millis, 1000)
            return (
                f"{hours:02}:{minutes:02}:"
                f"{seconds:02},{millis:03}"
            )

        lines.append(
            f"{index}\n{stamp(start)} --> {stamp(end)}\n{chunk}\n"
        )

    destination.write_text("\n".join(lines), encoding="utf-8")


def main():
    if CHANNEL not in STORIES:
        raise ValueError(f"Unknown CHANNEL_ID: {CHANNEL}")

    story = STORIES[CHANNEL]
    source = next(
        (
            p for p in OUTPUT.glob("*")
            if p.is_file()
            and p.suffix.lower() in {".mp4", ".mov", ".webm"}
            and p.name != "final_short.mp4"
        ),
        None,
    )

    if source is None:
        raise FileNotFoundError("No generated source video found in output/")

    audio = OUTPUT / "narration.mp3"
    subtitles = OUTPUT / "captions.srt"
    final_video = OUTPUT / "final_short.mp4"

    print(f"CHANNEL={CHANNEL}")
    print(f"STORY={story['title']}")
    asyncio.run(make_voice(
        story["script"], audio, story["voice"]
    ))

    probe = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio),
    ], text=True)
    duration = float(probe.strip())

    make_srt(story["script"], subtitles, duration)

    # Loop the generated scene to match narration duration.
    run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(source),
        "-i", str(audio),
        "-t", f"{duration:.3f}",
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
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

    print(f"FINAL_VIDEO={final_video}")
    print(f"FINAL_SIZE={final_video.stat().st_size}")
    print(f"FINAL_DURATION={duration:.2f}")


if __name__ == "__main__":
    main()
