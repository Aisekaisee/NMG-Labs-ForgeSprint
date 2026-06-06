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
- **Prompt:** ❯ Create `seo/fix_rewriter.py` with a function `rewrite_titles(rows, issues, model="qwen3.5:9b")` that:
  1. Finds all pages flagged with `missing_title`, `title_too_long`, or `title_too_short` in the `issues` list
  2. For each page, calls Ollama at `http://localhost:11434/api/generate` via `urllib.request`:
     - JSON body: `{"model": model, "prompt": "Write a concise SEO title for a page at URL: {url}\nCurrent title: {old_title}\nH1: {h1}\nRespond with ONLY the title text, nothing
  else.\nMax 60 characters."}`
  3. Validates the response length in Python:
     - If `len(response.strip()) > 60`, re-ask once with a stricter prompt: "Shorter title (max 60 chars):"
     - If still over 60 after retry, truncate to 60 chars
  4. Returns a list: `[{"url": "...", "old": "...", "new": "..."}]`
  5. If Ollama is not running (connection refused), return an empty list so the pipeline doesn't crash
  Use only standard library (`urllib.request`, `json`). Add a `__main__` block that tests it on the first 3 broken titles from `../sample-export`.
- **For:** Fixing the missing_title, title_too_long, or title_too_short in the fix_writer.py
- **Revised?** NO

4. 
- **Prompt:**  Extend `seo/fix_rewriter.py` with two more functions:
  1. `rewrite_metas(rows, issues, model="qwen3.5:9b")`:
     - Finds pages flagged with `missing_meta_description` or `meta_description_too_long`
     - Same Ollama pattern as titles, but prompt asks for meta description (max 155 chars)
     - Validate `len(response.strip()) <= 155`, retry once if over, truncate if still over
     - Returns `[{"url": "...", "old": "...", "new": "..."}]`
  2. `build_redirect_map(rows, issues)` — no model needed, pure Python:
     - Finds all URLs flagged as `broken_link` (4xx)
     - Builds a list of all live (200, indexable) URLs
     - For each broken URL, find the closest live URL by common path prefix (split by `/`, count matching segments). If no match, pick the homepage.
     - Returns `[{"from": "...", "to": "...", "reason": "404 -> closest live page"}]`
  Keep the existing `rewrite_titles` function unchanged. Add a `__main__` block that tests meta rewrites on 2 pages and prints the redirect map for broken links.
- **For:** 
- **Revised?** 

5. 
- **Prompt:**  Wire the fixer into the pipeline. Make these minimal edits:
  1. In `mcp/server.py`:
     - Import the new functions from `seo.fix_rewriter`
     - Add `seo_fix()` function that calls `rewrite_titles()`, `rewrite_metas()`, and `build_redirect_map()` using `RUN["rows"]` and `RUN["issues"]`
     - Store results in `RUN["fixes"] = {"titles": [...], "redirect_map": [...]}`
     - Update `RUN["model_calls"]` to count actual Ollama calls made
     - Emit `_emit("fixes", RUN["fixes"])` for the dashboard
  2. In `run.py`:
     - After `server.seo_detect()`, call `server.seo_fix()` before `server.seo_recommend()`
     - Remove the hardcoded `RUN["model_calls"] = 0` — let the fixer set it
  3. Run end-to-end: `python run.py sample-export/`
  4. Check `outputs/report.json` has a non-empty `fixes` block
- **For:** Added the fix_writer.py in the mcp/server.py
- **Revised?** 

6. 
- **Prompt:** Improve `_render_html()` in `mcp/server.py` to make `outputs/report.html` genuinely client-ready:
  - Add a professional header with site name, crawl date, and summary counts
  - Group issues by severity (High → Medium → Low) with clear visual hierarchy
  - Add a "Fixes" section showing the title rewrites and redirect map in tables
  - Make recommendations specific and actionable (not generic)
  - Add basic CSS styling that looks professional in a browser and in a forwarded email
  - Keep it a single self-contained HTML file with inline CSS (no external dependencies)
- **For:** Improving the html rendered output for better readability and understanding
- **Revised?** 
