#!/usr/bin/env python3
"""Upload one generated Short as PRIVATE for an explicit manual test only."""
import os
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    video_path = Path(os.environ.get("VIDEO_PATH", "output/final_short.mp4"))
    if not video_path.is_file() or video_path.stat().st_size == 0:
        raise SystemExit(f"Video file missing or empty: {video_path}")

    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit("Missing GitHub Actions secrets: " + ", ".join(missing))

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)

    title = os.environ.get("VIDEO_TITLE", "Money & Business Stories").strip()
    description = (
        "Automatically generated Short from Money & Business Stories. "
        "This video is uploaded as a private test."
    )
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True),
        notifySubscribers=False,
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response.get("id")
    if not video_id:
        raise SystemExit("Upload response did not include a video ID.")
    print("Private YouTube test upload succeeded.")
    print(f"Video ID: {video_id}")
    print(f"Studio URL: https://studio.youtube.com/video/{video_id}/edit")
    print("Privacy status requested: private")

if __name__ == "__main__":
    main()
