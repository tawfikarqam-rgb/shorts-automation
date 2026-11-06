#!/usr/bin/env python3
"""Fail-closed, per-channel YouTube duplicate guard backed by GitHub Contents API."""
import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def normalize(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def sha256_text(value):
    return hashlib.sha256(normalize(value).encode("utf-8")).hexdigest()


def similarity(left, right):
    a, b = normalize(left), normalize(right)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def find_duplicate(topic, script, video_sha256, ledger):
    topic_key = normalize(topic)
    script_key = normalize(script)

    for old_hash in (entry.get("video_sha256") for entry in ledger.get("entries", [])):
        if video_sha256 and old_hash and video_sha256 == old_hash:
            return "identical final MP4 SHA-256"

    for old_topic in ledger.get("legacy_blocked_topics", []):
        if topic_key and similarity(topic_key, old_topic) >= 0.88:
            return "topic was already used in the legacy story rotation: " + str(old_topic)

    for entry in ledger.get("entries", []):
        old_topic = entry.get("topic", "")
        old_script = entry.get("script", "")
        if topic_key and old_topic and similarity(topic_key, old_topic) >= 0.90:
            return "topic matches a previously reserved/published story: " + old_topic
        if script_key and old_script and similarity(script_key, old_script) >= 0.94:
            return "narration matches a previously reserved/published script"
        old_script_hash = entry.get("script_sha256")
        if script_key and old_script_hash and sha256_text(script) == old_script_hash:
            return "identical narration fingerprint"
    return None


def write_output(name, value):
    path = os.getenv("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def github_headers(token):
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def load_remote_ledger(repo, path, headers, channel):
    import requests

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    response = requests.get(url, headers=headers, params={"ref": os.getenv("GITHUB_REF_NAME", "main")}, timeout=30)
    if response.status_code == 404:
        return {"version": 1, "channel": channel, "legacy_blocked_topics": [], "entries": []}, None
    response.raise_for_status()
    payload = response.json()
    raw = base64.b64decode(payload["content"]).decode("utf-8")
    ledger = json.loads(raw)
    ledger.setdefault("legacy_blocked_topics", [])
    ledger.setdefault("entries", [])
    return ledger, payload["sha"]


def save_remote_ledger(repo, path, headers, ledger, sha, message):
    import requests

    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    content = base64.b64encode(
        (json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    ).decode("ascii")
    payload = {
        "message": message,
        "content": content,
        "branch": os.getenv("GITHUB_REF_NAME", "main"),
    }
    if sha:
        payload["sha"] = sha
    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if response.status_code in (409, 422):
        return False
    response.raise_for_status()
    return True


def reserve():
    channel = os.getenv("CHANNEL_NAME", "").strip().lower()
    if channel not in ("business", "history"):
        raise RuntimeError("CHANNEL_NAME must be business or history")
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not repo or not token:
        raise RuntimeError("GITHUB_REPOSITORY or GITHUB_TOKEN is missing")
    video_path = Path(os.getenv("VIDEO_PATH", "output/final_short.mp4"))
    if not video_path.is_file() or video_path.stat().st_size == 0:
        raise RuntimeError(f"Video file missing or empty: {video_path}")

    topic = os.getenv("STORY_TOPIC", "").strip()
    script = os.getenv("VIDEO_SCRIPT", "").strip()
    seed_topic = os.getenv("STORY_SEED_TOPIC", "").strip()
    if not topic or not script:
        raise RuntimeError("Final story topic/script is missing; refusing YouTube upload")

    video_sha = hashlib.sha256(video_path.read_bytes()).hexdigest()
    script_sha = sha256_text(script)
    topic_key = normalize(topic)
    path = f"state/published/{channel}.json"
    headers = github_headers(token)

    for attempt in range(4):
        ledger, sha = load_remote_ledger(repo, path, headers, channel)
        reason = find_duplicate(topic, script, video_sha, ledger)
        if reason:
            write_output("publish_allowed", "false")
            print("DUPLICATE_BLOCKED=" + reason)
            return False

        entry = {
            "status": "reserved",
            "topic": topic,
            "topic_key": topic_key,
            "script": script,
            "script_sha256": script_sha,
            "video_sha256": video_sha,
            "seed_topic": seed_topic,
            "run_id": os.getenv("GITHUB_RUN_ID", ""),
            "run_number": os.getenv("GITHUB_RUN_NUMBER", ""),
            "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "video_id": None,
        }
        ledger.setdefault("entries", []).append(entry)
        if seed_topic:
            existing = {normalize(x) for x in ledger.setdefault("legacy_blocked_topics", [])}
            if normalize(seed_topic) not in existing:
                ledger["legacy_blocked_topics"].append(seed_topic)

        saved = save_remote_ledger(
            repo, path, headers, ledger, sha,
            f"Reserve {channel} Short before YouTube upload",
        )
        if saved:
            write_output("publish_allowed", "true")
            print("PUBLISH_RESERVATION=CREATED")
            print("VIDEO_SHA256=" + video_sha)
            return True
        print(f"Ledger changed concurrently; retrying reservation ({attempt + 1}/4).")

    raise RuntimeError("Could not safely reserve publication after concurrent ledger updates")


def mark_published(video_id):
    channel = os.getenv("CHANNEL_NAME", "").strip().lower()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if channel not in ("business", "history") or not repo or not token:
        raise RuntimeError("Missing channel or GitHub credentials while finalizing publication")
    video_path = Path(os.getenv("VIDEO_PATH", "output/final_short.mp4"))
    video_sha = hashlib.sha256(video_path.read_bytes()).hexdigest()
    topic_key = normalize(os.getenv("STORY_TOPIC", ""))
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "")
    path = f"state/published/{channel}.json"
    headers = github_headers(token)

    for attempt in range(4):
        ledger, sha = load_remote_ledger(repo, path, headers, channel)
        match = None
        for entry in reversed(ledger.get("entries", [])):
            if (
                entry.get("run_id") == run_id
                and str(entry.get("run_attempt", "")) == str(run_attempt)
                and entry.get("video_sha256") == video_sha
                and entry.get("topic_key") == topic_key
            ):
                match = entry
                break
        if match is None:
            raise RuntimeError("No matching reservation found; leaving publication unconfirmed")
        if match.get("status") == "published" and match.get("video_id") == video_id:
            print("PUBLISH_LEDGER=ALREADY_CONFIRMED")
            return
        match["status"] = "published"
        match["video_id"] = video_id
        match["published_at"] = datetime.now(timezone.utc).isoformat()
        saved = save_remote_ledger(
            repo, path, headers, ledger, sha,
            f"Confirm {channel} YouTube Short {video_id}",
        )
        if saved:
            print("PUBLISH_LEDGER=CONFIRMED")
            return
        print(f"Ledger changed concurrently; retrying confirmation ({attempt + 1}/4).")
    raise RuntimeError("Could not confirm published video in durable ledger")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reserve", action="store_true")
    parser.add_argument("--mark-published", metavar="VIDEO_ID")
    args = parser.parse_args()
    if args.reserve == bool(args.mark_published):
        parser.error("choose exactly one of --reserve or --mark-published")
    if args.reserve:
        reserve()
    else:
        mark_published(args.mark_published)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PUBLISH_GUARD_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
