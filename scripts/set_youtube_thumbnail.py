#!/usr/bin/env python3
"""Set a custom Shorts thumbnail after YouTube finishes processing the upload."""
import os
import time
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
POLL_SECONDS = 15
MAX_POLLS = 40  # Up to 10 minutes for YouTube processing.


def main():
    video_id = os.environ.get("VIDEO_ID", "").strip()
    thumbnail_path = Path(os.environ.get("THUMBNAIL_PATH", "output/thumbnail.jpg"))
    required = ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"]
    missing = [name for name in required if not os.environ.get(name)]

    if not video_id or not thumbnail_path.is_file() or thumbnail_path.stat().st_size == 0 or missing:
        print("THUMBNAIL_STATUS=SKIPPED reason=missing_video_image_or_credentials")
        return 0

    try:
        credentials = Credentials(
            token=None,
            refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
            scopes=SCOPES,
        )
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)

        processing_status = ""
        for attempt in range(1, MAX_POLLS + 1):
            response = youtube.videos().list(
                part="processingDetails", id=video_id
            ).execute()
            items = response.get("items") or []
            if not items:
                print("THUMBNAIL_STATUS=FAILED reason=uploaded_video_not_found")
                return 0
            processing_status = (items[0].get("processingDetails") or {}).get("processingStatus", "")
            print(f"YOUTUBE_PROCESSING_STATUS={processing_status or 'pending'}")
            if processing_status == "succeeded":
                break
            if processing_status == "failed":
                print("THUMBNAIL_STATUS=FAILED reason=youtube_video_processing_failed")
                return 0
            if attempt < MAX_POLLS:
                time.sleep(POLL_SECONDS)
        else:
            print("THUMBNAIL_STATUS=FAILED reason=processing_timeout")
            return 0

        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(
                str(thumbnail_path), mimetype="image/jpeg", resumable=False
            ),
        ).execute()
        print("THUMBNAIL_STATUS=SUCCESS")
        print(f"THUMBNAIL_VIDEO_ID={video_id}")
        return 0
    except RefreshError:
        print("THUMBNAIL_STATUS=FAILED reason=oauth_refresh_failed")
        return 0
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", "unknown")
        print(f"THUMBNAIL_STATUS=FAILED reason=youtube_api_http_{status}")
        return 0
    except Exception as exc:
        print(f"THUMBNAIL_STATUS=FAILED reason={type(exc).__name__}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
