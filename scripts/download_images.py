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


def save_image(url, title, license_name, attribution, landing_url, provider):
    if not url or url in seen or len(downloaded) >= 4:
        return False
    seen.add(url)
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
            "source_url": landing_url, "provider": provider
        })
        print(f"Downloaded ({provider}): {title} [{license_name}]")
        return True
    except Exception as exc:
        print(f"Image download failed for {title}: {exc}")
        return False


# Primary: Openverse. Retry transient network errors and 429/5xx responses.
for term in SEARCHES:
    if len(downloaded) >= 4:
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
    for item in results:
        if len(downloaded) >= 4:
            break
        if item.get("license") not in {"cc0", "pdm", "by", "by-sa"}:
            continue
        save_image(
            item.get("url") or item.get("thumbnail"), item.get("title", term),
            f'{item.get("license", "").upper()} {item.get("license_version", "")}'.strip(),
            item.get("attribution", ""), item.get("foreign_landing_url", ""),
            f'Openverse/{item.get("provider", "unknown")}'
        )
    time.sleep(0.5)

# Fallback: broaden Commons searches without relaxing the public-domain/CC0 rule.
if len(downloaded) < 2:
    print("Openverse returned fewer than 2 usable images; trying Wikimedia Commons with retries.")
    commons_terms = []
    for term in SEARCHES:
        commons_terms.append(term)
        words = [w for w in re.findall(r"[A-Za-z0-9]+", term) if len(w) >= 4]
        if len(words) >= 2:
            commons_terms.append(" ".join(words[:2]))
        if words:
            commons_terms.append(words[0])
    # Preserve order while removing duplicate terms.
    commons_terms = list(dict.fromkeys(commons_terms))

    for term in commons_terms:
        if len(downloaded) >= 4:
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
        query_tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", term) if len(t) >= 4}
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = meta.get("LicenseShortName", {}).get("value", "")
            normalized = license_name.lower()
            if not ("public domain" in normalized or normalized.strip() == "cc0" or "cc0" in normalized):
                continue
            title = page.get("title", "")
            title_tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9]+", title) if len(t) >= 4}
            overlap = len(query_tokens & title_tokens)
            candidates.append((overlap, page))

        candidates.sort(key=lambda pair: pair[0], reverse=True)
        for _, page in candidates:
            if len(downloaded) >= 4:
                break
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            save_image(
                info.get("thumburl") or info.get("url"), page.get("title", term),
                meta.get("LicenseShortName", {}).get("value", "Public domain"),
                meta.get("Artist", {}).get("value", ""),
                "https://commons.wikimedia.org/wiki/" + page.get("title", "").replace(" ", "_"),
                "Wikimedia Commons"
            )
        time.sleep(0.4)

if len(downloaded) < 2:
    raise SystemExit(
        f"Could not find at least 2 usable openly licensed images; found {len(downloaded)}. "
        "Openverse and Wikimedia Commons were retried; see logs above."
    )

(OUT / "image_manifest.json").write_text(json.dumps(downloaded, indent=2), encoding="utf-8")
(OUT / "image_sources.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Downloaded {len(downloaded)} openly licensed images.")
print(f"Image source and attribution manifest: {OUT / 'image_sources.json'}")
