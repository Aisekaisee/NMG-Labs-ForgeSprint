# PROMPTS.md — my key prompts log

Keep the handful of prompts that actually moved the build. Not every message — the ones that
mattered: the system/sub-agent prompts, the ones you iterated on, the "this finally worked"
moment. This shows how you direct an AI, which is graded (challenge brief section 08).

Format per entry:
- **Prompt** (paste it)
- **For:** what you were trying to do
- **Revised?** did you have to change it, and why

---

## Example (replace with your own)

- **Prompt:** "Extend seo/detector.py to detect redirect chains: build a map of {Address ->
  Redirect URL} for all 3xx rows, then a chain exists when a Redirect URL is itself a key in
  that map. Add a redirect_chain issue (High). Run python seo/detector.py and show counts."
- **For:** adding the redirect-chain detector
- **Revised?** Yes — first version flagged single redirects as chains; added the "target is
  also a redirecting URL" condition.

---

## My prompts
1. 
- **Prompt:** We are building an SEO Command Center for Forge Sprint 01. The starter bundle is already wired: MCP server, dashboard, plugin manifest, and a partial detector. We run on Claude Code + Ollama (qwen3.5:9b), fully offline.
- **For:** To make it understand the context of the current codebase.
- **Revised?** No

2. 
- **Prompt:** Extend `seo/detector.py` to add these 10 missing issue types. The starter already has 7 implemented (missing_title, duplicate_title, title_too_long, broken_link, server_error,
  redirect, orphan_page). Add:
  1. `title_too_short` — Title 1 Length < 30, not empty, on indexable 200 HTML pages
  2. `missing_meta_description` — Meta Description 1 empty, on indexable 200 HTML pages
  3. `duplicate_meta_description` — Same Meta Description 1 on 2+ indexable 200 HTML pages (ignore empty)
  4. `meta_description_too_long` — Meta Description 1 Length > 155, on indexable 200 HTML pages
  5. `missing_h1` — H1-1 empty, on 200 HTML pages (note: rulebook says "200 page" not "indexable 200")
  6. `duplicate_h1` — Same H1-1 on 2+ indexable 200 HTML pages (ignore empty)
  7. `redirect_chain` — Build a map of {Address → Redirect URL} for all 3xx rows. A chain exists when a Redirect URL is also a key in that map. Flag the ORIGINAL redirecting URL(s) in the chain.
  8. `thin_content` — Word Count < 200 on an indexable HTML page
  9. `non_indexable_but_linked` — Indexability = Non-Indexable AND Inlinks > 0
  10. `slow_page` — Response Time > 1.0 second

  Rules:
  - Use existing helpers: `_int()`, `_float()`, `is_html()`, `is_200()`, `indexable()`
  - Use the existing `add()` helper
  - Every issue needs: type, severity, affected_urls, count, explanation
  - Do NOT change existing 7 detectors
  - Return all issues in a single list from `detect()`
- **For:** Detailed prompt to add all the remaining 10 SEO rules in the detector.py
- **Revised?** NO

3. 
- **Prompt:** 
- **For:** 
- **Revised?** 


4. 
- **Prompt:** 
- **For:** 
- **Revised?** 
