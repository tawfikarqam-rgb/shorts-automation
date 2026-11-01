#!/usr/bin/env python3
"""Append a short spoken and on-screen CTA outro to a rendered YouTube Short."""
import asyncio
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import edge_tts

VOICE = os.getenv("CTA_VOICE", "en-US-AndrewNeural")
CHANNEL = os.getenv("CHANNEL_NAME", "business").strip().lower()
QUESTION = " ".join(os.getenv("CTA_COMMENT_QUESTION", "").split()).strip()
LABELS = {
    "business": "MONEY & POWER STORIES",
    "history": "SECRETS & MYSTERIES",
}


def run(args):
    subprocess.run(args, check=True)


def duration(path):
    value = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ], text=True).strip()
    return float(value)


async def make_voice(text, path):
    last_error = None
    for voice in (VOICE, "en-US-EmmaNeural", "en-US-AriaNeural"):
        try:
            if path.exists():
                path.unlink()
            await asyncio.wait_for(
                edge_tts.Communicate(text=text, voice=voice).save(str(path)),
                timeout=90,
            )
            if path.is_file() and path.stat().st_size > 1000:
                print(f"CTA_AUDIO_OK voice={voice}")
                return
            raise RuntimeError("CTA audio missing or too small")
        except Exception as exc:
            last_error = exc
            print(f"CTA_TTS_RETRY voice={voice} error={type(exc).__name__}: {exc}")
    raise RuntimeError(f"Could not generate CTA narration: {last_error}")


def main():
    if len(sys.argv) > 1:
        video = Path(sys.argv[1]).resolve()
    else:
        video = Path("../output/final_short.mp4").resolve()
    if CHANNEL not in LABELS:
        raise ValueError(f"Unsupported channel: {CHANNEL}")
    if not video.is_file() or video.stat().st_size == 0:
        raise FileNotFoundError(f"Rendered Short not found: {video}")
    question = QUESTION or (
        "What do you think really happened in this story?"
        if CHANNEL == "history" else
        "Would you have made the same decision?"
    )

    # Keep the displayed question concise and readable on a phone.
    question = question[:150].rstrip()
    spoken = f"Like and subscribe for more. Tell us in the comments: {question}"
    work = video.parent
    frame = work / "cta_last_frame.jpg"
    audio = work / "cta_voice.mp3"
    textfile = work / "cta_overlay.txt"
    rendered = work / "final_short_with_cta.mp4"
    backup = work / "final_short_before_cta.mp4"

    try:
        asyncio.run(make_voice(spoken, audio))
        audio_duration = duration(audio)
        outro_duration = max(4.5, audio_duration + 0.35)
        if outro_duration > 8:
            raise ValueError(f"CTA audio is too long ({audio_duration:.2f}s); keep it under 7.65s")

        run([
            "ffmpeg", "-y", "-sseof", "-0.15", "-i", str(video),
            "-frames:v", "1", "-q:v", "2", str(frame),
        ])
        if not frame.is_file() or frame.stat().st_size < 1000:
            raise RuntimeError("Could not extract the final frame for the CTA card")

        overlay = "\n".join([
            LABELS[CHANNEL],
            "",
            "LIKE  •  SUBSCRIBE",
            "COMMENT BELOW",
            "",
            *textwrap.wrap(question, width=24),
        ])
        textfile.write_text(overlay, encoding="utf-8")

        # Use textfile rather than inline drawtext text to avoid filter escaping bugs.
        drawtext = (
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":textfile={textfile.resolve()}"
            ":fontcolor=white:fontsize=h*0.036"
            ":x=(w-text_w)/2:y=(h-text_h)/2"
            ":line_spacing=20:box=1:boxcolor=black@0.68:boxborderw=48"
        )
        graph = (
            "[0:v]setpts=PTS-STARTPTS,fps=30,setsar=1,format=yuv420p[v0];"
            f"[1:v]fps=30,{drawtext},fade=t=in:st=0:d=0.25,"
            "setsar=1,format=yuv420p[v1];"
            "[0:a]aresample=48000,aformat=sample_fmts=fltp:"
            "channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];"
            "[2:a]aresample=48000,aformat=sample_fmts=fltp:"
            f"channel_layouts=stereo,afade=t=out:st={max(0.0, audio_duration - 0.25):.3f}:d=0.25,"
            "asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
        )
        run([
            "ffmpeg", "-y",
            "-i", str(video),
            "-loop", "1", "-framerate", "30", "-t", f"{outro_duration:.3f}",
            "-i", str(frame),
            "-i", str(audio),
            "-filter_complex", graph,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(rendered),
        ])
        if not rendered.is_file() or rendered.stat().st_size < 500_000:
            raise RuntimeError("CTA-extended video is missing or unexpectedly small")

        # Replace only after the complete output has been rendered successfully.
        video.replace(backup)
        rendered.replace(video)
        backup.unlink()
        print(f"CTA_OUTRO=SUCCESS")
        print(f"CTA_QUESTION={question}")
        print(f"CTA_DURATION={outro_duration:.2f}")
        print(f"FINAL_VIDEO={video}")
    finally:
        # Restore the original if the final rename failed after moving it.
        if backup.exists() and not video.exists():
            backup.replace(video)
        for temporary in (frame, audio, textfile, rendered):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        if backup.exists() and video.exists():
            backup.unlink()


if __name__ == "__main__":
    main()
