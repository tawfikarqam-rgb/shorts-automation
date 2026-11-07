#!/usr/bin/env python3
"""Read-only Gemini API smoke test. Does not create or publish content."""
import os
import sys
from urllib.parse import urlparse

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()


def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_SMOKE_STATUS=FAILED")
        print("GEMINI_SMOKE_REASON=MISSING_SECRET")
        return 1

    if not MODEL or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in MODEL):
        print("GEMINI_SMOKE_STATUS=FAILED")
        print("GEMINI_SMOKE_REASON=INVALID_MODEL_CONFIGURATION")
        return 1

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": (
                    "Use Google Search to find the official Google AI for Developers "
                    "Gemini API models documentation. State the page's subject in one "
                    "short sentence. Do not guess if you cannot find it."
                )
            }],
        }],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 128},
    }

    try:
        response = requests.post(
            f"{API_BASE}/{MODEL}:generateContent",
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(15, 90),
        )
    except requests.RequestException as exc:
        print("GEMINI_SMOKE_STATUS=FAILED")
        print(f"GEMINI_SMOKE_REASON=NETWORK_{type(exc).__name__}")
        return 1

    if not response.ok:
        # Never print response bodies, request headers, or credential material.
        print("GEMINI_SMOKE_STATUS=FAILED")
        print(f"GEMINI_SMOKE_HTTP_STATUS={response.status_code}")
        try:
            error_status = str((response.json().get("error") or {}).get("status") or "UNKNOWN")
        except (ValueError, AttributeError):
            error_status = "UNKNOWN"
        safe_status = "".join(c for c in error_status if c.isalnum() or c in "_-")[:60]
        print(f"GEMINI_SMOKE_API_ERROR={safe_status or 'UNKNOWN'}")
        return 1

    try:
        data = response.json()
    except ValueError:
        print("GEMINI_SMOKE_STATUS=FAILED")
        print("GEMINI_SMOKE_REASON=INVALID_JSON_RESPONSE")
        return 1

    candidates = data.get("candidates") or []
    if not candidates:
        print("GEMINI_SMOKE_STATUS=FAILED")
        print("GEMINI_SMOKE_REASON=NO_CANDIDATES")
        return 1

    parts = (candidates[0].get("content") or {}).get("parts") or []
    if not any(isinstance(part, dict) and str(part.get("text") or "").strip() for part in parts):
        print("GEMINI_SMOKE_STATUS=FAILED")
        print("GEMINI_SMOKE_REASON=EMPTY_MODEL_RESPONSE")
        return 1

    metadata = candidates[0].get("groundingMetadata") or {}
    urls = set()
    for chunk in metadata.get("groundingChunks") or []:
        web = chunk.get("web") if isinstance(chunk, dict) else None
        if not isinstance(web, dict):
            continue
        url = str(web.get("uri") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc:
            urls.add(url)

    if not urls:
        print("GEMINI_SMOKE_STATUS=FAILED")
        print("GEMINI_SMOKE_REASON=NO_GOOGLE_SEARCH_GROUNDING_SOURCES")
        return 1

    print("GEMINI_SMOKE_STATUS=SUCCESS")
    print(f"GEMINI_SMOKE_MODEL={MODEL}")
    print(f"GEMINI_SMOKE_GROUNDING_SOURCES={len(urls)}")
    print("GEMINI_SMOKE_CONTENT=RECEIVED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
