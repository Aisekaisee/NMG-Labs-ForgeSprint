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

OLLAMA_BASE = "http://localhost:11434/api/generate"


def _call_ollama(prompt: str) -> str | None:
    """Call Ollama and return the generated text, or None on failure."""
    payload = json.dumps({"model": "qwen3.5:9b", "prompt": prompt, "stream": False}).encode("utf-8")
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
        response = _call_ollama(prompt.format(h1=h1, meta=meta, old=old, url=url))
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
            response = _call_ollama(strict_prompt.format(h1=h1, meta=meta, old=old, url=url))
            if response is None:
                return []
            new = response
            if len(new) > 60:
                new = new[:60]

        results.append({"url": url, "old": old, "new": new})

    return results


if __name__ == "__main__":
    import os
    from seo.detector import load_rows, detect

    export_dir = "../sample-export" if len(sys.argv) > 1 else "../sample-export"
    rows = load_rows(export_dir)
    issues = detect(rows)

    # Get first 3 broken titles (missing or long/short)
    broken_issues = [
        i for i in issues
        if i["type"] in ("missing_title", "title_too_long", "title_too_short")
    ][:3]

    print(f"Testing on {len(broken_issues)} issue types:")
    for iss in broken_issues:
        print(f"  {iss['type']}: {iss['count']} URLs")

    fixes = rewrite_titles(rows, issues)
    print(f"\nGenerated {len(fixes)} title rewrites.")
    for f in fixes[:5]:
        print(f"  {f['url'][:50]}...")
        print(f"    old: {f['old'][:60]}")
        print(f"    new: {f['new'][:60]}")
