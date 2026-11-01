#!/usr/bin/env python3
"""Download relevant openly licensed images with retries and a resilient Commons fallback."""
import json
import os
import re
import time
from pathlib import Path
from html import unescape

import requests

OUT = Path("MoneyPrinterTurbo/storage/local_videos")
OUT.mkdir(parents=True, exist_ok=True)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ShortsAutomation/1.2 (open-license educational video project; contact: repository maintainer)"})
SEARCHES = [q.strip() for q in os.environ.get("IMAGE_SEARCHES", "").split(";") if q.strip()]
downloaded, sources, seen = [], [], set()
seen_titles = set()
MAX_IMAGES = 8
MAX_PER_QUERY = 2
STOP_WORDS = {
    "about", "after", "before", "from", "into", "with", "without",
    "that", "this", "their", "there", "then", "they", "when", "where",
    "what", "why", "how", "the", "and", "for", "was", "were", "are",
    "its", "his", "her", "over", "under", "early", "late", "historic",
    "historical", "vintage", "photo", "photograph", "image", "images"
}


def tokens(value):
    return {
        word.lower() for word in re.findall(r"[A-Za-z0-9]+", str(value or ""))
        if len(word) >= 3 and word.lower() not in STOP_WORDS
    }


def relevance(query, description):
    query_tokens = tokens(query)
    if not query_tokens:
        return 0
    return len(query_tokens & tokens(description))


def minimum_overlap(query):
    return 2 if len(tokens(query)) >= 3 else 1


def request_with_retry(url, *, params=None, timeout=(15, 60), attempts=3):
    last = None
    for attempt in range(attempts):
        try:
            response = SESSION.get(url, params=params, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504):
                response.raise_for_status()
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last = exc
            if attempt + 1 < attempts:
                delay = min(8 * (2 ** attempt), 24)
                print(f"Request attempt {attempt + 1}/{attempts} failed: {exc}; retrying in {delay}s")
                time.sleep(delay)
    raise last


def save_image(url, title, license_name, attribution, landing_url, provider, query=""):
    normalized_title = re.sub(r"[^a-z0-9]+", " ", str(title or "").lower()).strip()
    url_key = str(url or "").split("?", 1)[0]
    if (not url or url_key in seen or len(downloaded) >= MAX_IMAGES
            or (normalized_title and normalized_title in seen_titles)):
        return False
    seen.add(url_key)
    if normalized_title:
        seen_titles.add(normalized_title)
    try:
        response = request_with_retry(url, timeout=(15, 45), attempts=2)
        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            print(f"Skipped non-image response for {title}: {content_type}")
            return False
        ext = ".png" if "png" in content_type else ".webp" if "webp" in content_type else ".jpg"
        path = OUT / f"scene_{len(downloaded) + 1}{ext}"
        path.write_bytes(response.content)
        if path.stat().st_size < 10000:
            path.unlink(missing_ok=True)
            return False
        downloaded.append(str(path.resolve()))
        sources.append({
            "file": str(path), "title": title, "license": license_name,
            "attribution": unescape(attribution or ""),
            "source_url": landing_url, "provider": provider, "matched_query": query
        })
        print(f"Downloaded ({provider}): {title} [{license_name}]")
        return True
    except Exception as exc:
        print(f"Image download failed for {title}: {exc}")
        return False


# Primary: Openverse. Retry transient network errors and 429/5xx responses.
for term in SEARCHES:
    if len(downloaded) >= MAX_IMAGES:
        break
    try:
        response = request_with_retry(
            "https://api.openverse.org/v1/images/",
            params={
                "q": term, "license": "cc0,pdm,by,by-sa",
                "license_type": "commercial", "size": "large",
                "page_size": 30, "mature": "false", "filter_dead": "true"
            },
            timeout=(15, 60), attempts=3
        )
        results = response.json().get("results", [])
    except Exception as exc:
        print(f"Openverse search failed for '{term}' after retries: {exc}")
        continue
    ranked = []
    for item in results:
        if item.get("license") not in {"cc0", "pdm", "by", "by-sa"}:
            continue
        tag_text = " ".join(
            tag.get("name", "") for tag in (item.get("tags") or [])
            if isinstance(tag, dict)
        )
        score = relevance(term, " ".join([
            item.get("title", ""), tag_text, item.get("description", "")
        ]))
        if score >= minimum_overlap(term):
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)

    accepted_for_query = 0
    for _, item in ranked:
        if len(downloaded) >= MAX_IMAGES or accepted_for_query >= MAX_PER_QUERY:
            break
        if save_image(
            item.get("url") or item.get("thumbnail"), item.get("title", term),
            f'{item.get("license", "").upper()} {item.get("license_version", "")}'.strip(),
            item.get("attribution", ""), item.get("foreign_landing_url", ""),
            f'Openverse/{item.get("provider", "unknown")}', query=term
        ):
            accepted_for_query += 1
    time.sleep(0.5)

# Fallback: use the same specific scene queries; never broaden to vague single words.
if len(downloaded) < MAX_IMAGES:
    print(f"Openverse supplied {len(downloaded)} relevant images; topping up with Wikimedia Commons.")
    for term in SEARCHES:
        if len(downloaded) >= MAX_IMAGES:
            break
        try:
            response = request_with_retry(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "format": "json", "generator": "search",
                    "gsrsearch": term, "gsrnamespace": 6, "gsrlimit": 50,
                    "prop": "imageinfo", "iiprop": "url|extmetadata",
                    "iiextmetadatafilter": "LicenseShortName|Artist|ImageDescription",
                    "iiurlwidth": 2000, "maxlag": 5
                },
                timeout=(15, 60), attempts=3
            )
            pages = response.json().get("query", {}).get("pages", {})
        except Exception as exc:
            print(f"Wikimedia search failed for '{term}' after retries: {exc}")
            continue

        candidates = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = meta.get("LicenseShortName", {}).get("value", "")
            normalized = license_name.lower()
            if not ("public domain" in normalized or normalized.strip() == "cc0" or "cc0" in normalized):
                continue
            title = page.get("title", "")
            description = re.sub(
                r"<[^>]+>", " ",
                meta.get("ImageDescription", {}).get("value", "")
            )
            overlap = relevance(term, title + " " + description)
            if overlap >= minimum_overlap(term):
                candidates.append((overlap, page))

        candidates.sort(key=lambda pair: pair[0], reverse=True)
        accepted_for_query = 0
        for _, page in candidates:
            if len(downloaded) >= MAX_IMAGES or accepted_for_query >= MAX_PER_QUERY:
                break
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            if save_image(
                info.get("thumburl") or info.get("url"), page.get("title", term),
                meta.get("LicenseShortName", {}).get("value", "Public domain"),
                meta.get("Artist", {}).get("value", ""),
                "https://commons.wikimedia.org/wiki/" + page.get("title", "").replace(" ", "_"),
                "Wikimedia Commons", query=term
            ):
                accepted_for_query += 1
        time.sleep(0.4)

if len(downloaded) < 2:
    raise SystemExit(
        f"Could not find at least 2 usable openly licensed images; found {len(downloaded)}. "
        "Openverse and Wikimedia Commons were retried; see logs above."
    )

(OUT / "image_manifest.json").write_text(json.dumps(downloaded, indent=2), encoding="utf-8")
(OUT / "image_sources.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Downloaded {len(downloaded)} relevant openly licensed images (target: {MAX_IMAGES}).")
if len(downloaded) < 6:
    print("WARNING: Fewer than 6 distinct scene images were found; visual variety may be limited.")
print(f"Image source and attribution manifest: {OUT / 'image_sources.json'}")
