# YouTube Shorts automation — analytics setup

## Current publishing path
The existing MoneyPrinterTurbo generation and YouTube upload steps remain unchanged.
Analytics collection is an optional, non-blocking post-upload step. It never controls
whether a video is uploaded.

## Enable read-only analytics (one-time Google OAuth action)
Create a separate refresh token for each channel's Google account with this scope:

\`https://www.googleapis.com/auth/yt-analytics.readonly\`

Keep the existing upload refresh tokens unchanged. Add these GitHub Actions secrets:

- Business channel: \`YOUTUBE_ANALYTICS_REFRESH_TOKEN\`
- History channel: \`HISTORY_YOUTUBE_ANALYTICS_REFRESH_TOKEN\`

The existing client ID and client secret are reused for the matching channel:
- Business: \`YOUTUBE_CLIENT_ID\`, \`YOUTUBE_CLIENT_SECRET\`
- History: \`HISTORY_YOUTUBE_CLIENT_ID\`, \`HISTORY_YOUTUBE_CLIENT_SECRET\`

Enable the YouTube Analytics API in the same Google Cloud project. Do not paste tokens
into issues, workflow files, commits, or chat.

## Data collected
The collector requests a rolling 28-day channel report, ending yesterday, grouped by
video. It records views, engaged views, average view duration, average percentage viewed,
likes, comments, shares, and subscribers gained. Snapshots are appended to channel JSONL
files and retained in GitHub Actions cache/artifacts.

YouTube Analytics data is delayed. Do not interpret same-day absence as zero performance.
The first dataset is descriptive only; automated topic/script adaptation must wait until
there are enough observations. In particular, avoid making decisions from videos with
very small view counts.

## Run tests locally
\`python -m unittest discover -s tests -v\`
