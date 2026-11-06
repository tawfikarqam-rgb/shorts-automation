#!/usr/bin/env python3
"""Groq browser-search research and accurate Shorts writing."""
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

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"


def normalize_topic(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).split())


def matches_used_topic(candidate, used_topics):
    key = normalize_topic(candidate)
    return bool(key) and any(
        old and difflib.SequenceMatcher(None, key, normalize_topic(old)).ratio() >= 0.88
        for old in used_topics
    )


def parse_object(raw):
    raw = re.sub(r"^\x60\x60\x60(?:json)?\s*|\s*\x60\x60\x60$", "", str(raw or "").strip(), flags=re.I)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def extract_message(data):
    choices = data.get("choices") or []
    if not choices:
        raise ValueError("Groq returned no completion choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Groq returned empty message content")
    return content.strip()



def extract_annotation_sources(response_data):
    """Extract URLs Groq explicitly cites for browser-search results."""
    choices = response_data.get("choices") or []
    if not choices:
        return []
    message = choices[0].get("message") or {}
    annotations = message.get("annotations") or []
    sources = []
    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        citation = annotation.get("url_citation") or annotation.get("citation") or {}
        if not isinstance(citation, dict):
            continue
        url = str(citation.get("url") or "").strip()
        title = str(citation.get("title") or "").strip()
        if url:
            sources.append({
                "title": title or "Groq browser-search citation",
                "url": url,
                "publisher": urlparse(url).netloc,
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
        title = str(item.get("title") or "").strip()
        publisher = str(item.get("publisher") or parsed.netloc).strip()
        supports = item.get("supports") or []
        if not isinstance(supports, list):
            supports = []
        seen.add(url)
        sources.append({
            "title": title[:200] or "Web source",
            "url": url,
            "publisher": publisher[:120],
            "supports": [str(x).strip()[:400] for x in supports if str(x).strip()][:8],
        })
    if len(sources) < 2:
        raise ValueError("Research must provide at least two distinct HTTPS source URLs")
    return sources


def groq_generate(api_key, model, messages, browser_search=False, max_tokens=3000, json_mode=False, stage="request"):
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": max_tokens,
    }
    if browser_search:
        payload["tools"] = [{"type": "browser_search"}]
        payload["tool_choice"] = "required"
        payload["reasoning_effort"] = "low"
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = None
    # Retry transient 5xx errors and short-lived TPM (tokens/minute) limits only.
    # Never retry daily token quotas (TPD), authentication, or malformed requests.
    for attempt in range(1, 4):
        response = requests.post(
            API_URL, headers=headers, json=payload, timeout=(20, 240)
        )
        body_lower = response.text.lower()
        transient_server_error = response.status_code in (500, 502, 503, 504)
        temporary_tpm_limit = (
            response.status_code == 429
            and "tokens per minute" in body_lower
            and "tokens per day" not in body_lower
        )
        if attempt == 3 or not (transient_server_error or temporary_tpm_limit):
            break
        if temporary_tpm_limit:
            wait_match = re.search(r"try again in ([0-9]+(?:\.[0-9]+)?)s", body_lower)
            wait_seconds = min(60.0, max(1.0, float(wait_match.group(1)))) if wait_match else 10.0
        else:
            wait_seconds = attempt * 5
        print(
            f"GROQ_RETRY stage={stage} attempt={attempt}/3 "
            f"http={response.status_code}; retrying after {wait_seconds:g}s",
            file=sys.stderr,
        )
        time.sleep(wait_seconds)
    if not response.ok:
        detail = response.text[:1200].replace(api_key, "[REDACTED]")
        request_id = response.headers.get("x-groq-request-id", "unavailable")
        raise RuntimeError(
            f"Groq API stage={stage} HTTP {response.status_code} "
            f"request_id={request_id}: {detail}"
        )
    data = response.json()
    return extract_message(data), data


def export_env(values):
    path = os.getenv("GITHUB_ENV")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            delimiter = "GROQ_" + uuid.uuid4().hex + "_END"
            handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def build_research_prompt(channel, topic, seed, used_topics):
    candidate = (
        f"Review this unused editorial lead, but independently verify every claim.\nLead title: {topic}\nLead text: {seed}\n"
        if topic and seed else "Find ONE genuinely fresh, well-documented story.\n"
    )
    focus = (
        "historical mysteries, discoveries, ancient civilizations, overlooked events, or documented turning points"
        if channel == "history" else
        "company history, business strategy, product decisions, market shifts, or documented entrepreneurial lessons"
    )
    return f"""You are a cautious documentary fact researcher. Research one English YouTube Shorts story.
Channel: {channel}. Focus: {focus}
{candidate}
Do not reuse or lightly retitle any used topic: {json.dumps(used_topics, ensure_ascii=False)}
You MUST use browser search. Prefer primary sources, official filings, reputable museums,
universities, archives, and established journalism. Do not invent URLs or sources.
Return one JSON object only, with keys:
topic (string), verified_facts (array of at least 3 specific factual claims),
uncertain_or_disputed (array), research_status ("verified" only if sources support the facts,
otherwise "not_verified"), sources (array of objects with title, exact https URL, publisher,
and supports array mapping claims to that source), image_searches (4-8 distinct visual searches).
Include at least two different real HTTPS source URLs actually encountered during browser search.
Never fabricate a URL. If you cannot supply two distinct sources and three supported facts,
set research_status to not_verified. Do not claim verification merely because a page appeared in search."""


def build_writer_prompt(channel, topic, facts, uncertainty, sources, used_topics):
    return f"""Write an accurate, compelling English YouTube Short for channel {channel}.
Topic: {topic}. Use ONLY these verified facts and do not add unsupported dates, numbers,
dialogue, quotes, or details. Qualify disputed points. Avoid these used topics:
{json.dumps(used_topics, ensure_ascii=False)}
Facts: {json.dumps(facts, ensure_ascii=False)}
Uncertainty: {json.dumps(uncertainty, ensure_ascii=False)}
Sources: {json.dumps(sources, ensure_ascii=False)}
Return JSON only: title (under 65 characters), narration (65-120 spoken words),
comment_question (8-16 words, ending in ?), image_searches (6-8 distinct scene searches
in narration order). Make visual beats diverse and specific, but factually relevant."""


def main():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip()
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
            print("GROQ_STATUS=SKIPPED_MISSING_SECRET; unused reviewed fallback retained")
            return
        raise RuntimeError("No unused reviewed fallback remains and GROQ_API_KEY is unavailable")

    print("GROQ_STAGE=research", flush=True)
    research_raw, research_response = groq_generate(
        api_key, model,
        [{"role": "user", "content": build_research_prompt(channel, topic, seed, used_topics)}],
        browser_search=True, max_tokens=3000, stage="research",
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
    if len(facts) < 3:
        raise ValueError("Research stage returned fewer than three factual claims")
    if research.get("research_status") != "verified":
        raise ValueError("Fresh story research was not verified; refusing to use it")
    reported_sources = research.get("sources")
    if not isinstance(reported_sources, list):
        reported_sources = []
    # Prefer explicit model-returned source metadata, and supplement it with
    # URLs Groq itself attached as browser-search citation annotations.
    reported_sources = reported_sources + extract_annotation_sources(research_response)
    sources = validate_sources(reported_sources)
    print(
        "GROQ_RESEARCH_SOURCE_COUNTS="
        f"model:{len(research.get('sources') or [])},"
        f"citations:{len(extract_annotation_sources(research_response))},"
        f"validated:{len(sources)}",
        flush=True,
    )
    uncertainty = research.get("uncertain_or_disputed", [])
    if not isinstance(uncertainty, list):
        uncertainty = []

    print("GROQ_STAGE=writing", flush=True)
    writer_raw, writer_response = groq_generate(
        api_key, model,
        [{"role": "user", "content": build_writer_prompt(
            channel, researched_topic, facts, uncertainty, sources, used_topics
        )}],
        max_tokens=1800, json_mode=True, stage="writing",
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
    research_usage = research_response.get("usage") or {}
    writer_usage = writer_response.get("usage") or {}
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "groq",
        "channel": channel,
        "topic": title,
        "research_status": "verified",
        "facts": facts,
        "uncertain_or_disputed": uncertainty,
        "sources": sources,
        "model": model,
        "research_usage": research_usage,
        "writer_usage": writer_usage,
        "total_tokens": int(research_usage.get("total_tokens", 0) or 0)
                        + int(writer_usage.get("total_tokens", 0) or 0),
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
    print("GROQ_STATUS=SUCCESS")
    print("GROQ_MODEL=" + model)
    print("GROQ_RESEARCH_SOURCES=" + str(len(sources)))
    print("GROQ_NARRATION_WORDS=" + str(words))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fallback = os.getenv("STORY_FALLBACK_AVAILABLE", "true").strip().lower() == "true"
        print(f"GROQ_WARNING={type(exc).__name__}: {exc}", file=sys.stderr)
        if fallback:
            print("GROQ_STATUS=FALLBACK_TO_UNUSED_REVIEWED_LOCAL_STORY")
        else:
            print("GROQ_STATUS=FAILED_NO_SAFE_FALLBACK; refusing to publish", file=sys.stderr)
            raise SystemExit(1)
