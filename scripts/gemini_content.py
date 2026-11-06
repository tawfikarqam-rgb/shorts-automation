#!/usr/bin/env python3
"""Gemini-powered, Google-Search-grounded story research and Shorts writing."""
import difflib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.8-flash"


def normalize_topic(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def matches_used_topic(candidate, used_topics):
    candidate_key = normalize_topic(candidate)
    if not candidate_key:
        return False
    for old_topic in used_topics:
        old_key = normalize_topic(old_topic)
        if old_key and difflib.SequenceMatcher(None, candidate_key, old_key).ratio() >= 0.88:
            return True
    return False


def parse_object(raw):
    raw = re.sub(r"^\x60\x60\x60(?:json)?\s*|\s*\x60\x60\x60$", "", raw.strip(), flags=re.I)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def extract_text(response_data):
    candidates = response_data.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidate")
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not content.strip():
        reason = candidates[0].get("finishReason", "unknown")
        raise ValueError("Gemini returned empty content (finishReason=" + str(reason) + ")")
    return content.strip()


def grounding_sources(response_data):
    candidates = response_data.get("candidates") or []
    metadata = candidates[0].get("groundingMetadata") or {} if candidates else {}
    chunks = metadata.get("groundingChunks") or []
    sources = []
    seen = set()
    for chunk in chunks:
        web = chunk.get("web") if isinstance(chunk, dict) else None
        if not isinstance(web, dict):
            continue
        url = web.get("uri")
        title = web.get("title")
        if isinstance(url, str) and url.startswith("https://") and url not in seen:
            seen.add(url)
            sources.append({
                "title": str(title or "Web source").strip(),
                "url": url,
                "publisher": str(title or "").strip(),
                "supports": [],
            })
    return sources, metadata


def validate_grounding(response_data):
    sources, metadata = grounding_sources(response_data)
    queries = metadata.get("webSearchQueries") or []
    supports = metadata.get("groundingSupports") or []
    if len(sources) < 2:
        raise ValueError("Google Search grounding returned fewer than two distinct HTTPS sources")
    if not queries:
        raise ValueError("Gemini did not return Google Search grounding queries")
    if not supports:
        raise ValueError("Gemini did not return claim-to-source grounding supports")
    return sources, metadata


def gemini_generate(api_key, model, prompt, use_google_search=False, max_output_tokens=4096):
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    url = f"{API_BASE}/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.25,
            "responseMimeType": "application/json",
            "maxOutputTokens": max_output_tokens,
        },
    }
    if use_google_search:
        payload["tools"] = [{"google_search": {}}]
    response = requests.post(
        url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=(20, 180),
    )
    if not response.ok:
        # Do not print request headers or any credential material.
        detail = response.text[:1200].replace(api_key, "[REDACTED]")
        raise RuntimeError(f"Gemini API HTTP {response.status_code}: {detail}")
    data = response.json()
    return extract_text(data), data


def export_env(values):
    path = os.getenv("GITHUB_ENV")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            delimiter = "GEMINI_" + uuid.uuid4().hex + "_END"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def build_research_prompt(channel, topic, seed, used_topics):
    if topic and seed:
        candidate_context = (
            "Review this unused editorial candidate, but do not assume its claims are true.\n"
            f"Candidate title: {topic}\nEditorial seed (lead only, not proof):\n{seed}\n"
        )
    else:
        candidate_context = "Find ONE genuinely fresh story that has not appeared in the used-topic list.\n"
    focus = (
        "historical mysteries, discoveries, ancient civilizations, overlooked events, or documented turning points"
        if channel == "history" else
        "company history, business strategy, product decisions, market shifts, or documented entrepreneurial lessons"
    )
    return f"""Act as a cautious documentary researcher. Research one English YouTube Shorts story.
Channel: {channel}
Editorial focus: {focus}
{candidate_context}
Previously used topics to avoid completely:
{json.dumps(used_topics, ensure_ascii=False)}
Use Google Search to consult multiple reliable sources. Prefer primary sources, official filings,
reputable museums, universities, archives, and established journalism. Do not invent URLs,
citations, dates, quotations, or facts. Distinguish established facts from disputed interpretations.
Choose a genuinely different subject, not a synonym or a lightly retitled version of a used story.
Return JSON only with this schema:
{{"topic":"accurate concise title","verified_facts":["at least 3 concise factual claims"],
"uncertain_or_disputed":["claims to avoid or qualify"],
"research_status":"verified|partially_verified|not_verified",
"image_searches":["4-8 distinct visual searches in story order"]}}
Only call a claim verified when the search evidence supports it. If evidence is insufficient,
set research_status to not_verified. The application will attach the actual Google grounding
sources separately; do not fabricate a sources array."""


def build_writer_prompt(channel, topic, facts, uncertainty, sources, used_topics):
    return f"""Write a compelling but accurate English YouTube Short for the {channel} channel.
Topic: {topic}
Target 75-105 spoken words. Structure: immediate hook, clear progression, satisfying payoff.
Use ONLY the supplied verified facts. Do not add invented details, dialogue, numbers, dates,
or unsupported claims. Qualify uncertainty. Avoid every previously used topic:
{json.dumps(used_topics, ensure_ascii=False)}
Return JSON only:
{{"title":"accurate title under 65 characters","narration":"65-120 spoken words",
"comment_question":"one natural story-specific question, 8-16 words",
"image_searches":["6-8 distinct, specific visual searches in narration order"]}}
Plan different visual beats across the narration, not synonyms for one subject. Mix relevant
people, places, objects, archival details, and settings only when supported by the facts.
FACTS: {json.dumps(facts, ensure_ascii=False)}
UNCERTAINTY: {json.dumps(uncertainty, ensure_ascii=False)}
GROUNDING SOURCES: {json.dumps(sources, ensure_ascii=False)}"""


def main():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()
    fallback_available = os.getenv("STORY_FALLBACK_AVAILABLE", "true").strip().lower() == "true"
    try:
        used_topics = json.loads(os.getenv("USED_STORY_TOPICS", "[]"))
    except json.JSONDecodeError as exc:
        raise ValueError("USED_STORY_TOPICS is not valid JSON") from exc
    if not isinstance(used_topics, list):
        raise ValueError("USED_STORY_TOPICS must be a JSON list")

    channel = os.getenv("CHANNEL_NAME", "history").strip().lower()
    topic = os.getenv("STORY_TOPIC", "").strip()
    seed = os.getenv("VIDEO_SCRIPT", "").strip()
    if channel not in ("business", "history"):
        raise ValueError("CHANNEL_NAME must be business or history")
    if fallback_available and (not topic or not seed):
        raise ValueError("Reviewed fallback was marked available but its story is missing")
    if not api_key:
        if fallback_available:
            print("GEMINI_STATUS=SKIPPED_MISSING_SECRET; unused reviewed fallback retained")
            return
        raise RuntimeError("No unused reviewed fallback remains and GEMINI_API_KEY is unavailable")

    research_raw, research_response = gemini_generate(
        api_key, model, build_research_prompt(channel, topic, seed, used_topics),
        use_google_search=True, max_output_tokens=3000,
    )
    research = parse_object(research_raw)
    researched_topic = research.get("topic")
    if not isinstance(researched_topic, str) or not researched_topic.strip():
        raise ValueError("Research stage did not return a topic")
    if matches_used_topic(researched_topic, used_topics):
        raise ValueError("Research stage selected a previously used topic")
    facts = research.get("verified_facts")
    status = research.get("research_status", "not_verified")
    sources, grounding = validate_grounding(research_response)
    if not isinstance(facts, list) or len([x for x in facts if isinstance(x, str) and x.strip()]) < 3:
        raise ValueError("Research stage returned fewer than three factual claims")
    if status != "verified":
        raise ValueError("Fresh story research was not marked verified; refusing to use it")
    facts = [x.strip() for x in facts if isinstance(x, str) and x.strip()]
    uncertainty = research.get("uncertain_or_disputed", [])
    if not isinstance(uncertainty, list):
        uncertainty = []

    writer_raw, writer_response = gemini_generate(
        api_key, model,
        build_writer_prompt(channel, researched_topic, facts, uncertainty, sources, used_topics),
        use_google_search=False, max_output_tokens=1800,
    )
    result = parse_object(writer_raw)
    narration = result.get("narration")
    title = result.get("title")
    images = result.get("image_searches")
    comment_question = result.get("comment_question")
    words = len(re.findall(r"\b[\w’'-]+\b", narration)) if isinstance(narration, str) else 0
    if not isinstance(narration, str) or not 65 <= words <= 120:
        raise ValueError("Generated narration word count outside 65-120: " + str(words))
    if not isinstance(title, str) or not title.strip() or len(title) > 80:
        raise ValueError("Generated title missing or too long")
    if matches_used_topic(title, used_topics):
        raise ValueError("Writer returned a previously used topic")
    if not isinstance(images, list) or len(images) < 4:
        raise ValueError("Need at least four distinct ordered scene image searches")
    clean_images = [str(item).strip() for item in images[:8] if str(item).strip()]
    if len(clean_images) < 4:
        raise ValueError("Need at least four non-empty image searches")

    Path("output").mkdir(exist_ok=True)
    usage = (research_response.get("usageMetadata") or {})
    writer_usage = (writer_response.get("usageMetadata") or {})
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel,
        "topic": title,
        "research_status": status,
        "facts": facts,
        "uncertain_or_disputed": uncertainty,
        "sources": sources,
        "google_search_queries": grounding.get("webSearchQueries", []),
        "grounding_support_count": len(grounding.get("groundingSupports") or []),
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
    print("GEMINI_GROUNDING_SUPPORTS=" + str(len(grounding.get("groundingSupports") or [])))
    print("GEMINI_NARRATION_WORDS=" + str(words))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fallback_available = os.getenv("STORY_FALLBACK_AVAILABLE", "true").strip().lower() == "true"
        print(f"GEMINI_WARNING={type(exc).__name__}: {exc}", file=sys.stderr)
        if fallback_available:
            print("GEMINI_STATUS=FALLBACK_TO_UNUSED_REVIEWED_LOCAL_STORY")
        else:
            print("GEMINI_STATUS=FAILED_NO_SAFE_FALLBACK; refusing to publish", file=sys.stderr)
            raise SystemExit(1)
