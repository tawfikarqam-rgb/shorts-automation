#!/usr/bin/env python3
"""Optional two-model OxionAI research and script generation stage."""
import json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

BASE = os.getenv("OXIONAI_BASE_URL", "https://www.oxionai.com/v1").rstrip("/")
RESEARCH_MODEL = os.getenv("OXIONAI_RESEARCH_MODEL", "gemini-3.7-flash")
WRITER_MODEL = os.getenv("OXIONAI_WRITER_MODEL", "deepseek-v4-flash-0731")


def completion(key, model, messages, max_tokens):
    response = requests.post(
        BASE + "/chat/completions",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.35,
              "max_tokens": max_tokens, "response_format": {"type": "json_object"}},
        timeout=(15, 120),
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"].get("content")
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Empty model response: " + model)
    usage = data.get("usage") or {}
    return content.strip(), {
        "model": data.get("model", model),
        "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
        "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def parse_object(raw):
    raw = re.sub(r"^\x60\x60\x60(?:json)?\s*|\s*\x60\x60\x60$", "", raw.strip(), flags=re.I)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def export_env(values):
    path = os.getenv("GITHUB_ENV")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        for key, value in values.items():
            delimiter = "OXION_" + str(abs(hash((key, value)))) + "_END"
            f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def main():
    research_key = os.getenv("OXIONAI_RESEARCH_API_KEY", "").strip()
    writer_key = os.getenv("OXIONAI_WRITER_API_KEY", "").strip()
    if not research_key or not writer_key:
        print("OXIONAI_STATUS=SKIPPED_MISSING_SECRETS; reviewed local story retained")
        return
    channel = os.getenv("CHANNEL_NAME", "history").strip().lower()
    topic = os.getenv("STORY_TOPIC", "").strip()
    seed = os.getenv("VIDEO_SCRIPT", "").strip()
    if channel not in ("business", "history") or not topic or not seed:
        raise ValueError("Missing selected story context")

    research_prompt = f"""Research this candidate for an English YouTube Shorts documentary.
Channel: {channel}
Topic: {topic}
Existing reviewed editorial seed (lead only, not proof):
{seed}

Use your native live web-search capability if available. Do not invent URLs or citations.
Prefer primary sources, official filings, reputable museums, universities, archives and
established journalism. Distinguish facts from disputed interpretations. If live sources
cannot be retrieved, mark research_status not_verified.
Return JSON only:
{{"topic":"accurate title","verified_facts":["3-6 concise sourced facts"],
"uncertain_or_disputed":["claims to avoid or qualify"],
"sources":[{{"title":"source title","url":"https://...","publisher":"...","supports":["claim"]}}],
"research_status":"verified|partially_verified|not_verified",
"image_searches":["3-4 visual queries"]}}
Only list sources actually consulted."""

    research_raw, research_usage = completion(
        research_key, RESEARCH_MODEL,
        [{"role":"system","content":"Cautious fact-checking researcher. Never fabricate sources."},
         {"role":"user","content":research_prompt}], 1800)
    research = parse_object(research_raw)
    facts = research.get("verified_facts")
    sources = research.get("sources")
    valid_sources = [s for s in (sources if isinstance(sources, list) else [])
                     if isinstance(s, dict) and isinstance(s.get("url"), str)
                     and s["url"].startswith("https://") and s.get("title")]
    status = research.get("research_status", "not_verified")
    if not isinstance(facts, list) or len(facts) < 2 or len(valid_sources) < 2 or status == "not_verified":
        print("OXIONAI_STATUS=RESEARCH_NOT_VERIFIED; reviewed local story retained")
        return

    writer_prompt = f"""Write a compelling but accurate English YouTube Short for {channel}.
Topic: {research.get("topic") or topic}
Target 75-105 spoken words. Structure: immediate hook, clear progression, satisfying payoff.
Use ONLY the supplied facts. No invented details, dialogue, numbers or unsupported claims.
Qualify uncertainty. Return JSON only:
{{"title":"accurate title under 65 characters","narration":"65-120 spoken words",
"image_searches":["6-8 distinct, specific visual searches in narration order"]}}
For image_searches, plan different visual beats across the whole narration, not synonyms
for the same subject. Mix relevant people, places, products, archival objects, settings,
and close-up details when supported by the facts. Every query must match a distinct
moment or detail in the narration; avoid generic stock-photo phrases and repeated angles.
FACTS: {json.dumps(facts, ensure_ascii=False)}
UNCERTAINTY: {json.dumps(research.get("uncertain_or_disputed", []), ensure_ascii=False)}
SOURCES: {json.dumps(valid_sources, ensure_ascii=False)}"""

    writer_raw, writer_usage = completion(
        writer_key, WRITER_MODEL,
        [{"role":"system","content":"Precise documentary Shorts writer. Accuracy outranks drama."},
         {"role":"user","content":writer_prompt}], 1200)
    result = parse_object(writer_raw)
    narration = result.get("narration")
    title = result.get("title")
    images = result.get("image_searches")
    words = len(re.findall(r"\b[\w’'-]+\b", narration)) if isinstance(narration, str) else 0
    if not isinstance(narration, str) or not 65 <= words <= 120:
        raise ValueError("Generated narration word count outside 65-120: " + str(words))
    if not isinstance(title, str) or not title.strip() or len(title) > 80:
        raise ValueError("Generated title missing or too long")
    if not isinstance(images, list) or len(images) < 6:
        raise ValueError("Need at least six distinct ordered scene image searches")

    Path("output").mkdir(exist_ok=True)
    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel, "topic": title, "research_status": status,
        "facts": facts, "uncertain_or_disputed": research.get("uncertain_or_disputed", []),
        "sources": valid_sources,
        "models": {"research": research_usage, "writer": writer_usage},
        "total_tokens": research_usage["total_tokens"] + writer_usage["total_tokens"],
        "narration_words": words,
    }
    Path("output/ai_content_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    export_env({"STORY_TOPIC": title.strip(), "VIDEO_SCRIPT": narration.strip(),
                "IMAGE_SEARCHES": ";".join(str(x).strip() for x in images[:8] if str(x).strip())})
    print("OXIONAI_STATUS=SUCCESS")
    print("OXIONAI_RESEARCH_MODEL=" + research_usage["model"])
    print("OXIONAI_WRITER_MODEL=" + writer_usage["model"])
    print("OXIONAI_RESEARCH_TOKENS=" + str(research_usage["total_tokens"]))
    print("OXIONAI_WRITER_TOKENS=" + str(writer_usage["total_tokens"]))
    print("OXIONAI_TOTAL_TOKENS=" + str(audit["total_tokens"]))
    print("OXIONAI_RESEARCH_STATUS=" + status)
    print("OXIONAI_NARRATION_WORDS=" + str(words))
    print("OXIONAI_SOURCES=" + str(len(valid_sources)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Fail open to the pre-reviewed static story; never block the existing video pipeline.
        print(f"OXIONAI_WARNING={type(exc).__name__}: {exc}", file=sys.stderr)
        print("OXIONAI_STATUS=FALLBACK_TO_REVIEWED_LOCAL_STORY")
