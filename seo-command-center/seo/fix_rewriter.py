"""
fix_rewriter.py — title rewriting via Ollama.

Provides `rewrite_titles(rows, issues, model)` which calls Ollama to generate
SEO-friendly titles for pages with missing, too-long, or too-short titles.
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
import sys
from urllib.parse import urlparse

from .detector import _int, is_html, is_200, indexable

OLLAMA_BASE = "http://localhost:11434/api/generate"

OLLAMA_CALLS_COUNT = 0


def _call_ollama(prompt: str, model: str = "qwen3.5:9b") -> str | None:
    """Call Ollama and return the generated text, or None on failure."""
    global OLLAMA_CALLS_COUNT
    OLLAMA_CALLS_COUNT += 1
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_BASE, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception:
        return None


def rewrite_titles(
    rows: list[dict],
    issues: list[dict],
    model: str = "qwen3.5:9b",
) -> list[dict]:
    """
    Rewrite titles for pages flagged with missing_title, title_too_long, or title_too_short.

    For each page:
      1. Call Ollama at http://localhost:11434/api/generate
      2. If response > 60 chars, retry with stricter prompt
      3. If still > 60, truncate to 60

    Returns a list of `{url, old, new}` dicts for successfully rewritten titles.
    If Ollama is not running, returns an empty list.
    """
    results: list[dict] = []

    # Gather rows by URL for quick lookup
    by_url: dict[str, dict] = {r["Address"]: r for r in rows}

    # Collect pages that need rewriting
    pages_to_fix: list[tuple[str, str, str | None, str | None]] = []  # (url, old_title, meta_desc, h1)
    for issue in issues:
        if issue["type"] not in ("missing_title", "title_too_long", "title_too_short"):
            continue
        for url in issue["affected_urls"]:
            row = by_url.get(url, {})
            old = row.get("Title 1", "") or ""
            meta = row.get("Meta Description 1", "") or ""
            h1 = row.get("H1-1", "") or ""
            pages_to_fix.append((url, old, meta, h1))

    for url, old, meta, h1 in pages_to_fix:
        if not old:  # missing_title -> prompt without old title
            prompt = (
                f"Write a concise SEO title for a page at URL: {url}\n"
                "Current title: (none)\nH1: {h1}\nRespond with ONLY the title text, nothing else.\n"
                "Max 60 characters."
            ).format(h1=h1)
        elif len(old) > 60:  # title_too_long -> use old as context
            prompt = (
                f"Write a concise SEO title for a page at URL: {url}\n"
                f"Current title: {old}\nMeta Description: {meta}\nH1: {h1}\n"
                "Respond with ONLY the title text, nothing else.\nMax 60 characters."
            )
        else:  # title_too_short -> use old as context
            prompt = (
                f"Write a concise SEO title for a page at URL: {url}\n"
                f"Current title: {old}\nMeta Description: {meta}\nH1: {h1}\n"
                "Respond with ONLY the title text, nothing else.\nMax 60 characters."
            )

        # First attempt
        response = _call_ollama(prompt.format(h1=h1, meta=meta, old=old, url=url), model=model)
        if response is None:
            return []  # Ollama not running

        # Validate length
        new = response
        if len(new) > 60:
            # Retry with stricter prompt
            strict_prompt = (
                f"Shorter title (max 60 chars):\n"
                f"URL: {url}\nCurrent title: {old}\nMeta Description: {meta}\nH1: {h1}\n"
                "Respond with ONLY the title text, nothing else."
            )
            response = _call_ollama(strict_prompt.format(h1=h1, meta=meta, old=old, url=url), model=model)
            if response is None:
                return []
            new = response
            if len(new) > 60:
                new = new[:60]

        results.append({"url": url, "old": old, "new": new})

    return results


def rewrite_metas(
    rows: list[dict],
    issues: list[dict],
    model: str = "qwen3.5:9b",
) -> list[dict]:
    """
    Rewrite meta descriptions for pages flagged with missing_meta_description or meta_description_too_long.

    For each page:
      1. Call Ollama at http://localhost:11434/api/generate
      2. If response > 155 chars, retry with stricter prompt
      3. If still > 155, truncate to 155

    Returns a list of `{url, old, new}` dicts for successfully rewritten meta descriptions.
    If Ollama is not running, returns an empty list.
    """
    results: list[dict] = []

    # Gather rows by URL for quick lookup
    by_url: dict[str, dict] = {r["Address"]: r for r in rows}

    # Collect pages that need rewriting
    pages_to_fix: list[tuple[str, str, str | None, str | None]] = []  # (url, old_meta, title, h1)
    for issue in issues:
        if issue["type"] not in ("missing_meta_description", "meta_description_too_long"):
            continue
        for url in issue["affected_urls"]:
            row = by_url.get(url, {})
            old = row.get("Meta Description 1", "") or ""
            title = row.get("Title 1", "") or ""
            h1 = row.get("H1-1", "") or ""
            pages_to_fix.append((url, old, title, h1))

    for url, old, title, h1 in pages_to_fix:
        if not old:  # missing_meta_description -> prompt without old meta
            prompt = (
                f"Write a concise SEO meta description for a page at URL: {url}\n"
                f"Page title: {title}\nH1: {h1}\nRespond with ONLY the meta description text, nothing else.\n"
                "Max 155 characters."
            ).format(h1=h1, title=title, url=url)
        elif len(old) > 155:  # meta_description_too_long -> use old as context
            prompt = (
                f"Write a concise SEO meta description for a page at URL: {url}\n"
                f"Current meta: {old}\nPage title: {title}\nH1: {h1}\n"
                "Respond with ONLY the meta description text, nothing else.\nMax 155 characters."
            )
        else:
            prompt = (
                f"Write a concise SEO meta description for a page at URL: {url}\n"
                f"Current meta: {old}\nPage title: {title}\nH1: {h1}\n"
                "Respond with ONLY the meta description text, nothing else.\nMax 155 characters."
            )

        # First attempt
        response = _call_ollama(prompt, model=model)
        if response is None:
            return []  # Ollama not running

        # Validate length
        new = response
        if len(new) > 155:
            # Retry with stricter prompt
            strict_prompt = (
                f"Shorter meta description (max 155 chars):\n"
                f"URL: {url}\nCurrent meta: {old}\nPage title: {title}\nH1: {h1}\n"
                "Respond with ONLY the meta description text, nothing else."
            )
            response = _call_ollama(strict_prompt, model=model)
            if response is None:
                return []
            new = response
            if len(new) > 155:
                new = new[:155]

        results.append({"url": url, "old": old, "new": new})

    return results


def build_redirect_map(rows: list[dict], issues: list[dict]) -> list[dict]:
    """
    Build a redirect map for broken links (4xx).

    For each broken URL (4xx), find the closest live (200, indexable) URL by
    comparing path prefixes (split by '/', count matching segments). If no match,
    pick the homepage.

    Returns a list of `{from, to, reason}` dicts.
    """
    results: list[dict] = []

    # Gather rows by URL for quick lookup
    by_url: dict[str, dict] = {r["Address"]: r for r in rows}

    # Collect broken links (4xx)
    broken_urls = [r["Address"] for r in rows if 400 <= _int(r.get("Status Code", 0)) <= 499]

    # Collect live (200, indexable) URLs
    live_urls: list[str] = []
    for r in rows:
        if is_html(r) and is_200(r) and indexable(r):
            live_urls.append(r["Address"])

    # Add homepage if available
    homepage = None
    for url in live_urls:
        parsed = urlparse(url)
        if parsed.path in ("", "/") or "/index" in parsed.path or "/home" in parsed.path:
            homepage = url
            break
    if not homepage and live_urls:
        homepage = live_urls[0]

    for broken_url in broken_urls:
        # Try to find closest live URL by path prefix matching
        broken_path = broken_url.split("?")[0]  # strip query params
        best_match: str | None = None
        best_score: int = -1

        for live_url in live_urls:
            live_path = live_url.split("?")[0]
            # Split paths into segments
            broken_parts = broken_path.split("/")
            live_parts = live_url.split("/")

            # Score by common prefix segments
            score = 0
            for i, bp in enumerate(broken_parts):
                if i >= len(live_parts):
                    break
                if bp == live_parts[i] or bp == "":
                    score += 1
                else:
                    break

            # Bonus for homepage
            if live_url == homepage:
                score += 10

            if score > best_score:
                best_score = score
                best_match = live_url

        # If still no good match, use homepage
        if best_match is None and homepage:
            best_match = homepage

        results.append({
            "from": broken_url,
            "to": best_match or "/",
            "reason": "404 -> closest live page",
        })

    return results


if __name__ == "__main__":
    import os
    from seo.detector import load_rows, detect

    export_dir = "../sample-export" if len(sys.argv) > 1 else "../sample-export"
    rows = load_rows(export_dir)
    issues = detect(rows)

    # Test meta rewrites on first 2 pages
    meta_issues = [
        i for i in issues
        if i["type"] in ("missing_meta_description", "meta_description_too_long")
    ][:2]

    print(f"Testing meta rewrites on {len(meta_issues)} issue types:")
    for iss in meta_issues:
        print(f"  {iss['type']}: {iss['count']} URLs")

    meta_fixes = rewrite_metas(rows, issues)
    print(f"\nGenerated {len(meta_fixes)} meta rewrites.")
    for f in meta_fixes[:5]:
        print(f"  {f['url'][:50]}...")
        print(f"    old: {f['old'][:80]}")
        print(f"    new: {f['new'][:80]}")

    # Print redirect map for broken links
    print("\n--- Redirect Map for Broken Links ---")
    redirect_map = build_redirect_map(rows, issues)
    print(f"Found {len(redirect_map)} broken links, here are the first 10 redirect targets:")
    for r in redirect_map[:10]:
        print(f"  {r['from']} -> {r['to']}")
