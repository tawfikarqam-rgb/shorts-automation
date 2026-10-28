#!/usr/bin/env python3
"""Upload a generated channel Short to YouTube with channel-specific metadata."""
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "business").strip().lower()
IS_HISTORY = CHANNEL_NAME == "history"
CHANNEL_LABEL = "History Shorts" if IS_HISTORY else "Money & Business Stories"


def main() -> None:
    video_path = Path(os.environ.get("VIDEO_PATH", "output/final_short.mp4"))
    if not video_path.is_file() or video_path.stat().st_size == 0:
        raise SystemExit(f"UPLOAD_FAILED: video file missing or empty: {video_path}")

    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("UPLOAD_FAILED: missing GitHub Actions secrets: " + ", ".join(missing))

    title = os.environ.get("VIDEO_TITLE", CHANNEL_LABEL).strip()
    if not title:
        title = CHANNEL_LABEL
    title = title[:100]

    topic = os.environ.get("STORY_TOPIC", "").strip()
    if IS_HISTORY:
        description_lines = [
            "History's mysteries, turning points, and remarkable stories explained in short videos.",
            "",
            "Discover historical events, ancient civilizations, scientific mysteries, and the people who shaped our world.",
            "",
            "What do you think about this story? Share your take in the comments.",
            "Subscribe for more history stories and mysteries.",
            "",
            "#History #HistoricalFacts #Shorts",
        ]
    else:
        description_lines = [
            "Short business stories, explained clearly.",
            "",
            "We break down business decisions, company stories, money concepts, and lessons entrepreneurs can learn.",
            "",
            "What do you think about this story? Share your take in the comments.",
            "Subscribe to Money & Business Stories for more short business explainers.",
            "",
            "#Business #Entrepreneurship #Shorts",
        ]
    if topic:
        description_lines.insert(1, f"Today's topic: {topic}.")
    description = "\n".join(description_lines)

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": (
                ["history", "historical facts", "ancient history", "history mysteries", "historical events", "civilizations", "shorts"]
                if IS_HISTORY else
                ["business", "business stories", "entrepreneurship", "business strategy", "money explained", "financial literacy", "company history", "business lessons", "small business", "economics", "shorts"]
            ),
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            chunksize=8 * 1024 * 1024,
            resumable=True,
        ),
        notifySubscribers=False,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status is not None:
            print(f"UPLOAD_PROGRESS={int(status.progress() * 100)}%")

    video_id = response.get("id")
    if not video_id:
        raise SystemExit("UPLOAD_FAILED: YouTube response did not include a video ID.")

    returned_privacy = (response.get("status") or {}).get("privacyStatus")
    if returned_privacy and returned_privacy != "public":
        raise SystemExit(
            f"UPLOAD_WARNING: video {video_id} returned privacyStatus={returned_privacy!r}"
        )

    print("PUBLIC_YOUTUBE_UPLOAD=SUCCESS")
    print(f"VIDEO_ID={video_id}")
    print(f"VIDEO_URL=https://youtube.com/shorts/{video_id}")
    print(f"STUDIO_URL=https://studio.youtube.com/video/{video_id}/edit")
    print(f"PRIVACY_STATUS={returned_privacy or 'public requested; verify in Studio'}")


if __name__ == "__main__":
    main()
