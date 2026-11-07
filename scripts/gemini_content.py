#!/usr/bin/env python3
"""Gemini 3.8 Flash grounded research and English Shorts writing."""
import difflib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.8-flash"


def normalize_topic(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def matches_used_topic(candidate, used_topics):
    key = normalize_topic(candidate)
    return bool(key) and any(
        old and difflib.SequenceMatcher(None, key, normalize_topic(old)).ratio() >= 0.88
        for old in used_topics
    )


def parse_object(raw):
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(raw or "").strip(), flags=re.I)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def extract_text(data):
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no completion candidates")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    chunks = [p.get("text", "") for p in parts if isinstance(p, dict)]
    result = "\n".join(x for x in chunks if x).strip()
    if not result:
        raise ValueError("Gemini returned empty text")
    return result


def extract_grounded_sources(response_data):
    """Only accept URLs explicitly returned in Gemini grounding metadata."""
    candidates = response_data.get("candidates") or []
    if not candidates:
        return []
    metadata = candidates[0].get("groundingMetadata") or {}
    sources, seen = [], set()
    for chunk in metadata.get("groundingChunks") or []:
        web = chunk.get("web") if isinstance(chunk, dict) else None
        if not isinstance(web, dict):
            continue
        url = str(web.get("uri") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or url in seen:
            continue
        seen.add(url)
        title = str(web.get("title") or "").strip()
        sources.append({
            "title": title[:200] or "Google Search result",
            "url": url,
            "publisher": title[:120] or parsed.netloc[:120],
            "supports": [],
        })
    return sources


def validate_sources(raw_sources):
    if not isinstance(raw_sources, list):
        raise ValueError("Research did not return a sources list")
    sources, seen = [], set()
    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or url in seen:
            continue
        seen.add(url)
        sources.append({
            "title": str(item.get("title") or "Web source")[:200],
            "url": url,
            "publisher": str(item.get("publisher") or parsed.netloc)[:120],
            "supports": [str(x).strip()[:400] for x in (item.get("supports") or [])
                         if str(x).strip()][:8],
        })
    if len(sources) < 2:
        raise ValueError("Research must be grounded by at least two distinct HTTPS source URLs")
    return sources


def gemini_generate(api_key, model, prompt, *, google_search=False, json_mode=False,
                    max_tokens=3000, stage="request"):
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens},
    }
    if google_search:
        payload["tools"] = [{"google_search": {}}]
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    url = f"{API_BASE}/{model}:generateContent"
    response = None
    for attempt in range(1, 4):
        response = requests.post(
            url, headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload, timeout=(20, 240),
        )
        transient = response.status_code in (429, 500, 502, 503, 504)
        if attempt == 3 or not transient:
            break
        body = response.text.lower()
        # Retry only short-lived rate limits; daily quota exhaustion is not transient.
        if response.status_code == 429 and any(
            marker in body for marker in ("per day", "daily limit", "per_day")
        ):
            break
        wait = min(30, attempt * 5)
        print(f"GEMINI_RETRY stage={stage} attempt={attempt}/3 http={response.status_code}",
              file=sys.stderr, flush=True)
        time.sleep(wait)
    if not response.ok:
        try:
            error = response.json().get("error") or {}
            message = str(error.get("message") or response.reason)
            status = str(error.get("status") or "unknown")
        except (ValueError, AttributeError):
            message, status = response.reason, "unknown"
        # Do not print request headers or the API key.
        raise RuntimeError(
            f"Gemini API stage={stage} HTTP {response.status_code} status={status}: "
            f"{message[:800]}"
        )
    data = response.json()
    return extract_text(data), data


def build_research_prompt(channel, topic, seed, used_topics):
    candidate = (
        f"Editorial lead to investigate independently: {topic}\nSeed text: {seed}\n"
        if topic and seed else "Find ONE genuinely fresh, well-documented story.\n"
    )
    focus = (
        "historical mysteries, discoveries, ancient civilizations, overlooked events, or documented turning points"
        if channel == "history" else
        "company history, business strategy, product decisions, market shifts, or documented entrepreneurial lessons"
    )
    return f"""You are a cautious documentary fact researcher. Research ONE English YouTube Shorts story.
Channel: {channel}. Focus: {focus}
{candidate}
Do not reuse or lightly retitle any used topic: {json.dumps(used_topics, ensure_ascii=False)}
Use Google Search grounding. Search for the subject and verify key claims against the returned evidence.
Prefer primary sources, official filings, reputable museums, universities, archives, and established journalism.
Do not invent facts, dates, quotes, URLs, publishers, or sources. Do not treat a search-result title alone as proof.
Return one compact JSON object only with:
topic (string), verified_facts (array of at least 3 specific supported factual claims),
uncertain_or_disputed (array), research_status ("verified" only when evidence supports the facts,
otherwise "not_verified"), image_searches (4-6 short distinct visual searches).
Do not include a sources array; source URLs must come only from API grounding metadata.
If the returned evidence does not support at least 3 specific facts, set research_status to not_verified."""


def build_writer_prompt(channel, topic, facts, uncertainty, sources):
    compact_sources = [
        {"title": s["title"][:120], "url": s["url"], "publisher": s["publisher"][:80]}
        for s in sources[:3]
    ]
    return f"""Create an accurate English YouTube Short for {channel}.
Topic: {topic}
Use only these verified facts. Add no unsupported dates, numbers, quotes, dialogue, or details.
Qualify disputed points. Facts: {json.dumps(facts[:5], ensure_ascii=False)}
Disputed: {json.dumps(uncertainty[:3], ensure_ascii=False)}
Grounded evidence: {json.dumps(compact_sources, ensure_ascii=False)}
Return JSON with title (under 65 characters), narration (65-120 spoken words),
comment_question (8-16 words ending with ?), and image_searches
(6-8 distinct visual scenes in narration order). Keep every scene relevant to the verified story."""


def export_env(values):
    path = os.getenv("GITHUB_ENV")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            delimiter = "GEMINI_" + uuid.uuid4().hex + "_END"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()
    fallback = os.getenv("STORY_FALLBACK_AVAILABLE", "true").strip().lower() == "true"
    used_topics = json.loads(os.getenv("USED_STORY_TOPICS", "[]"))
    if not isinstance(used_topics, list):
        raise ValueError("USED_STORY_TOPICS must be a JSON list")
    channel = os.getenv("CHANNEL_NAME", "history").strip().lower()
    topic = os.getenv("STORY_TOPIC", "").strip()
    seed = os.getenv("VIDEO_SCRIPT", "").strip()
    if channel not in ("business", "history"):
        raise ValueError("CHANNEL_NAME must be business or history")
    if fallback and (not topic or not seed):
        raise ValueError("Reviewed fallback was marked available but its story is missing")
    if not api_key:
        if fallback:
            print("GEMINI_STATUS=SKIPPED_MISSING_SECRET; unused reviewed fallback retained")
            return
        raise RuntimeError("No unused reviewed fallback remains and GEMINI_API_KEY is unavailable")

    print("GEMINI_STAGE=research", flush=True)
    research_raw, research_response = gemini_generate(
        api_key, model, build_research_prompt(channel, topic, seed, used_topics),
        google_search=True, max_tokens=2200, stage="research",
    )
    research = parse_object(research_raw)
    researched_topic = research.get("topic")
    if not isinstance(researched_topic, str) or not researched_topic.strip():
        raise ValueError("Research stage did not return a topic")
    if matches_used_topic(researched_topic, used_topics):
        raise ValueError("Research stage selected a previously used topic")
    facts = research.get("verified_facts")
    if not isinstance(facts, list):
        raise ValueError("Research stage did not return factual claims")
    facts = [str(x).strip() for x in facts if isinstance(x, str) and x.strip()]
    if len(facts) < 3 or research.get("research_status") != "verified":
        raise ValueError("Fresh story research was not verified; refusing to use it")
    sources = validate_sources(extract_grounded_sources(research_response))
    uncertainty = research.get("uncertain_or_disputed", [])
    if not isinstance(uncertainty, list):
        uncertainty = []

    print("GEMINI_STAGE=writing", flush=True)
    writer_raw, writer_response = gemini_generate(
        api_key, model,
        build_writer_prompt(channel, researched_topic, facts, uncertainty, sources),
        json_mode=True, max_tokens=1200, stage="writing",
    )
    result = parse_object(writer_raw)
    narration, title = result.get("narration"), result.get("title")
    images = result.get("image_searches")
    comment_question = result.get("comment_question")
    words = len(re.findall(r"\b[\w’'-]+\b", narration)) if isinstance(narration, str) else 0
    if not isinstance(narration, str) or not 65 <= words <= 120:
        raise ValueError(f"Generated narration word count outside 65-120: {words}")
    if not isinstance(title, str) or not title.strip() or len(title) > 80:
        raise ValueError("Generated title missing or too long")
    if matches_used_topic(title, used_topics):
        raise ValueError("Writer returned a previously used topic")
    if not isinstance(images, list):
        raise ValueError("Writer did not return image searches")
    clean_images = [str(x).strip() for x in images if str(x).strip()][:8]
    if len(clean_images) < 4 or len(set(x.lower() for x in clean_images)) < 4:
        raise ValueError("Need at least four distinct non-empty scene image searches")

    Path("output").mkdir(exist_ok=True)
    usage = research_response.get("usageMetadata") or {}
    writer_usage = writer_response.get("usageMetadata") or {}
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "google_gemini",
        "channel": channel,
        "topic": title,
        "research_status": "verified",
        "facts": facts,
        "uncertain_or_disputed": uncertainty,
        "sources": sources,
        "model": model,
        "research_usage": usage,
        "writer_usage": writer_usage,
        "total_tokens": int(usage.get("totalTokenCount", 0) or 0)
                        + int(writer_usage.get("totalTokenCount", 0) or 0),
        "narration_words": words,
    }
    Path("output/ai_content_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not isinstance(comment_question, str):
        comment_question = ""
    comment_question = " ".join(comment_question.split()).strip()
    if not (8 <= len(comment_question.split()) <= 20) or not comment_question.endswith("?"):
        comment_question = (
            f"What do you think really happened in {title.strip()}?"
            if channel == "history" else
            f"Would you have made the same decision in {title.strip()}?"
        )
    export_env({
        "STORY_TOPIC": title.strip(),
        "VIDEO_SCRIPT": narration.strip(),
        "CTA_COMMENT_QUESTION": comment_question,
        "IMAGE_SEARCHES": ";".join(clean_images),
    })
    print("GEMINI_STATUS=SUCCESS")
    print("GEMINI_MODEL=" + model)
    print("GEMINI_RESEARCH_SOURCES=" + str(len(sources)))
    print("GEMINI_NARRATION_WORDS=" + str(words))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fallback = os.getenv("STORY_FALLBACK_AVAILABLE", "true").strip().lower() == "true"
        print(f"GEMINI_WARNING={type(exc).__name__}: {exc}", file=sys.stderr)
        if fallback:
            print("GEMINI_STATUS=FALLBACK_TO_UNUSED_REVIEWED_LOCAL_STORY")
        else:
            print("GEMINI_STATUS=FAILED_NO_SAFE_FALLBACK; refusing to publish", file=sys.stderr)
            raise SystemExit(1)
