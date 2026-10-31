#!/usr/bin/env python3
"""Collect channel-level YouTube Analytics snapshots without affecting publishing."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"
METRICS = "views,engagedViews,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=("business", "history"), required=True)
    parser.add_argument("--output-dir", default="analytics_data")
    parser.add_argument("--days", type=int, default=28)
    args = parser.parse_args()

    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_ANALYTICS_REFRESH_TOKEN")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        print("ANALYTICS_SKIPPED=missing_" + ",".join(missing))
        return 0

    if not 7 <= args.days <= 90:
        raise SystemExit("--days must be between 7 and 90")

    credentials = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_ANALYTICS_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=[ANALYTICS_SCOPE],
    )

    # YouTube Analytics reports are delayed; end yesterday to avoid partial-day comparisons.
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=args.days - 1)
    youtube_analytics = build("youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False)
    response = youtube_analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics=METRICS,
        dimensions="video",
        sort="-views",
        maxResults=200,
    ).execute()

    headers = [h.get("name") for h in response.get("columnHeaders", [])]
    rows = response.get("rows", [])
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{args.channel}.jsonl"
    collected_at = datetime.now(timezone.utc).isoformat()

    count = 0
    with output.open("a", encoding="utf-8") as handle:
        for row in rows:
            record = dict(zip(headers, row))
            record.update({
                "channel": args.channel,
                "window_start": start_date.isoformat(),
                "window_end": end_date.isoformat(),
                "collected_at": collected_at,
                "sample_window_days": args.days,
            })
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"ANALYTICS_COLLECTION=SUCCESS")
    print(f"ANALYTICS_CHANNEL={args.channel}")
    print(f"ANALYTICS_WINDOW={start_date.isoformat()}..{end_date.isoformat()}")
    print(f"ANALYTICS_VIDEO_ROWS={count}")
    print(f"ANALYTICS_FILE={output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Analytics is deliberately non-blocking: a missing scope, disabled API,
        # or temporary API failure must never cancel a successfully generated upload.
        print(f"ANALYTICS_WARNING={type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(0)
