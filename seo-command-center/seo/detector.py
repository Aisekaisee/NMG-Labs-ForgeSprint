"""
detector.py — deterministic SEO issue detection from a Screaming Frog internal_all.csv.

STARTER IMPLEMENTATION. It already detects several issues so the pipeline runs end to
end. Your job in the Sprint is to COMPLETE the rulebook (see rulebook.md): add the
missing detectors, handle edge cases, and improve accuracy against the hidden export.

Standard library only (csv). Detection is plain Python on purpose — the model is for
judgment (rewriting titles, choosing redirect targets), not for counting rows.
"""

from __future__ import annotations
import csv
import os
from collections import defaultdict


def load_rows(export_dir: str) -> list[dict]:
    path = os.path.join(export_dir, "internal_all.csv")
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _int(v, default=0):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


def _float(v, default=0.0):
    try:
        return float(str(v).strip())
    except Exception:
        return default


def is_html(r):  return "text/html" in (r.get("Content Type", "") or "").lower()
def is_200(r):   return _int(r.get("Status Code")) == 200
def indexable(r): return (r.get("Indexability", "") or "").strip().lower() == "indexable"


def detect(rows: list[dict]) -> list[dict]:
    """Return a list of issue dicts: {type, severity, affected_urls, count, explanation}.
    STARTER set — extend to the full rulebook for a high score."""
    issues = []

    def add(t, sev, urls, explanation):
        urls = sorted(set(urls))
        if urls:
            issues.append({"type": t, "severity": sev, "affected_urls": urls,
                           "count": len(urls), "explanation": explanation})

    html = [r for r in rows if is_html(r)]
    idx200 = [r for r in html if is_200(r) and indexable(r)]

    # --- Titles ---
    add("missing_title", "High",
        [r["Address"] for r in idx200 if not (r.get("Title 1", "") or "").strip()],
        "Indexable pages with no title tag.")

    # duplicate titles (indexable only)
    by_title = defaultdict(list)
    for r in idx200:
        t = (r.get("Title 1", "") or "").strip()
        if t:
            by_title[t].append(r["Address"])
    dup_t = [u for urls in by_title.values() if len(urls) > 1 for u in urls]
    add("duplicate_title", "High", dup_t, "Pages sharing an identical title.")

    add("title_too_long", "Medium",
        [r["Address"] for r in idx200
         if _int(r.get("Title 1 Pixel Width")) > 561 or _int(r.get("Title 1 Length")) > 60],
        "Titles likely truncated in search results.")

    # --- Response codes ---
    add("broken_link", "High",
        [r["Address"] for r in rows if 400 <= _int(r.get("Status Code")) <= 499],
        "URLs returning a client error (4xx).")
    add("server_error", "High",
        [r["Address"] for r in rows if 500 <= _int(r.get("Status Code")) <= 599],
        "URLs returning a server error (5xx).")
    add("redirect", "Medium",
        [r["Address"] for r in rows if 300 <= _int(r.get("Status Code")) <= 399],
        "URLs that redirect (3xx).")

    # --- Orphan pages ---
    add("orphan_page", "Medium",
        [r["Address"] for r in idx200 if _int(r.get("Inlinks")) == 0],
        "Indexable pages with zero internal links in.")

    # ----------------------------------------------------------------------- #
    # Title length checks (indexable 200 pages)
    add("title_too_short", "Low",
        [r["Address"] for r in idx200
         if 0 < _int(r.get("Title 1 Length", 0)) < 30],
        "Titles with less than 30 characters.")

    # ----------------------------------------------------------------------- #
    # Meta description checks (indexable 200 pages)
    add("missing_meta_description", "Medium",
        [r["Address"] for r in idx200 if not (r.get("Meta Description 1", "") or "").strip()],
        "Indexable pages with no meta description tag.")

    # duplicate meta descriptions (ignore empty values)
    by_meta_desc = defaultdict(list)
    for r in idx200:
        md = (r.get("Meta Description 1", "") or "").strip()
        if md:
            by_meta_desc[md].append(r["Address"])
    dup_md = [u for urls in by_meta_desc.values() if len(urls) > 1 for u in urls]
    add("duplicate_meta_description", "Medium", dup_md, "Pages sharing an identical meta description.")

    add("meta_description_too_long", "Low",
        [r["Address"] for r in idx200
         if _int(r.get("Meta Description 1 Length", 0)) > 155],
        "Meta descriptions likely truncated in search results.")

    # ----------------------------------------------------------------------- #
    # H1 checks (all 200 HTML pages, not just indexable)
    h1_200 = [r for r in rows if is_html(r) and is_200(r)]
    add("missing_h1", "Medium",
        [r["Address"] for r in h1_200 if not (r.get("H1-1", "") or "").strip()],
        "200 pages with no H1 heading.")

    # ----------------------------------------------------------------------- #
    # Duplicate H1 checks (indexable 200 pages)
    by_h1 = defaultdict(list)
    for r in idx200:
        h1 = (r.get("H1-1", "") or "").strip()
        if h1:
            by_h1[h1].append(r["Address"])
    dup_h1 = [u for urls in by_h1.values() if len(urls) > 1 for u in urls]
    add("duplicate_h1", "Low", dup_h1, "Pages sharing an identical H1 heading.")

    # ----------------------------------------------------------------------- #
    # Response time and content checks
    add("slow_page", "Low",
        [r["Address"] for r in rows if _float(r.get("Response Time", 0)) > 1.0],
        "Pages taking longer than 1 second to load.")

    add("thin_content", "Low",
        [r["Address"] for r in idx200 if _int(r.get("Word Count", 0)) < 200],
        "Pages with less than 200 words of content.")

    add("non_indexable_but_linked", "Medium",
        [r["Address"] for r in rows
         if "Non-Indexable" in (r.get("Indexability", "") or "").strip()
         and _int(r.get("Inlinks", 0)) > 0],
        "Non-indexable pages that have internal links pointing to them.")

    # ----------------------------------------------------------------------- #
    # redirect_chain: a redirect whose target is itself a redirecting URL
    redirects = [r for r in rows if 300 <= _int(r.get("Status Code", 0)) <= 399]
    redirect_map = {r.get("Address", ""): r.get("Redirect URL", "") for r in redirects}
    redirect_targets = {r.get("Redirect URL", "") for r in redirects}
    chain_urls = [t for t in redirect_targets if t in redirect_map]
    add("redirect_chain", "High", chain_urls, "Redirects that lead to other redirects (redirect chains).")

    return issues


def summarize(issues: list[dict]) -> dict:
    by_sev = defaultdict(int)
    for i in issues:
        by_sev[i["severity"]] += 1
    return {"total_issues": len(issues),
            "by_severity": {"High": by_sev["High"], "Medium": by_sev["Medium"], "Low": by_sev["Low"]}}


if __name__ == "__main__":
    import sys, json
    d = sys.argv[1] if len(sys.argv) > 1 else "../sample-export"
    rows = load_rows(d)
    iss = detect(rows)
    print(f"Loaded {len(rows)} rows, detected {len(iss)} issue types.")
    print(json.dumps(summarize(iss), indent=2))
    for i in iss:
        print(f"  [{i['severity']:<6}] {i['type']:<24} x{i['count']}")
