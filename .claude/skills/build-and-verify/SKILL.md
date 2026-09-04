---
name: build-and-verify
description: "REQUIRED before changing any CSS, styles, nav, footer, or partials on this site, before any site-wide/bulk edit across pages, and before committing any HTML change. Also use when the user says 'build', 'rebuild', 'run build.sh', 'verify the site', or when a git diff unexpectedly touches 100+ HTML files. Explains the CSS-inlining/partials build pipeline, which files are generated vs source, expected diff shapes, and the verification checklist."
metadata:
  version: 1.0.0
---

# Build and Verify

This site has no framework and no CI. `build.sh` is the entire build system, and it **rewrites the HTML files in place**. Misunderstanding it is the most expensive mistake you can make in this repo.

## The two cardinal rules

1. **Never hand-edit the inlined `<style>` block in any page.** Every page carries the full site CSS inlined into its `<head>`. That block is generated. Edit the sources — `css/tokens.css`, `css/base.css`, `css/layout.css`, `css/components.css`, `css/pages.css` — then run `./build.sh`. `css/style.css` is also generated (a concatenation of the five sources); never edit it either.
2. **Never hand-edit content between `<!-- @include-start partials/x.html -->` and `<!-- @include-end partials/x.html -->` markers.** The nav, footer, and head-extras appear expanded inside every page, but the source of truth is `partials/nav.html`, `partials/footer.html`, `partials/head-extras.html`. Edit the partial, then run `./build.sh`.

Hand-edits inside either region will be silently overwritten by the next build.

## What build.sh does (6 steps)

1. **CSS concat** — concatenates the five `css/*.css` sources (in the order above) into `css/style.css`.
2. **Partial expansion** — for every HTML file outside `partials/`, replaces the content between each `@include-start`/`@include-end` marker pair with the current content of the named partial. Fails loudly if a referenced partial doesn't exist.
3. **CSS inlining (reversible)** — pass A finds pages whose CSS is already inlined and converts the `<style>` block back to a `<link rel="stylesheet" href="/css/style.css">` tag; pass B re-inlines the fresh `css/style.css` in place of that link tag. Pass A detects the generated block by its signature: a line that is exactly `  <style>` (two-space indent) immediately followed by a line containing `:root {` (the start of tokens.css). **Do not change that indentation or move tokens.css from first position in the concat order** — you would break the detection and the next build would double-inline.
4. **Sitemap and dates** — `scripts/generate_sitemap.py` rewrites `sitemap.xml` and `data/page-dates.json` (lastmod moves only when body content changes); `scripts/sync_dates.py` sets `dateModified`, `article:modified_time` and the visible Published/Updated line on every Article page from that date.
5. **llms-full.txt** — `scripts/generate_llms_full.py` dumps the visible text of every sitemap page.
6. **Validation** — runs `python3 validate_jsonld.py`, which checks that every `application/ld+json` block in every HTML file parses as JSON. Build fails if any block is invalid.

Deployment is GitHub Pages serving the committed files directly. There is no build step in CI — **the built output is what you commit**, which is why `./build.sh` must run before committing any css/ or partials/ change.

## When to rebuild

| You changed… | Rebuild? |
|---|---|
| Page body copy, meta tags, JSON-LD in one page | Not required (harmless if you do) |
| Anything in `css/` | **Mandatory** |
| Anything in `partials/` | **Mandatory** |
| Added a new page | **Mandatory** (expands its markers, inlines CSS) |
| `llms.txt`, `robots.txt`, docs | No |
| Body copy on any page | Recommended: the build refreshes `sitemap.xml` lastmod and article dates from content (`scripts/generate_sitemap.py`, `scripts/sync_dates.py`) |

## Expected diff shapes (anti-panic guide)

- **Content edit on one page** → `git diff --stat` shows 1 file.
- **CSS source edit + rebuild** → ~165 HTML files change, plus `css/style.css` and the source you edited. Every HTML change must be confined to the inlined `<style>` block. Spot-check three pages from different sections: `git diff -- index.html areas/london/camden.html music-guides/index.html`.
- **Partial edit + rebuild** → ~165 HTML files change, confined to the marker regions for that partial. Spot-check the same way.
- **A rebuild with no source changes** → clean tree. `./build.sh && git diff --stat` producing no output is the standard sanity check that the pipeline is healthy.

If a rebuild changes anything *outside* a `<style>` block or marker region, stop and investigate before committing — something upstream is wrong.

## Verification checklist

Run before committing:

1. `./build.sh` exits 0 (it prints counts for CSS bytes, partials populated, files inlined, and ends with the JSON-LD result).
2. If you only edited JSON-LD, `python3 validate_jsonld.py` alone is enough.
3. `git diff --stat` matches the expected shape above; spot-check representative pages.
4. Preview locally: `python3 -m http.server 8000` from the repo root, then check the affected pages at `http://localhost:8000/…` (nav, footer, and styles render; no raw marker comments visible).
5. For copy changes, the writing-site-copy skill's checks apply before this checklist.

## Site-wide sweeps (things NOT in partials)

The GA4/Google Ads snippet is now `partials/analytics.html` (since 2026-09-04): edit the partial and rebuild. Most other head meta structure is still duplicated per page; changing it means editing ~165 files. Rules:

- Never sweep by hand. Write a small Python script (or careful `sed`) that targets the same file set as `validate_jsonld.py`: `*.html`, `areas/*.html`, `areas/**/*.html`, `music-guides/*.html`.
- Verify with counts: `grep -rl 'PATTERN' --include='*.html' . | wc -l` before and after — the numbers must be equal (or exactly what you intended).
- Run the full verification checklist afterwards; the diff shape should be "~165 files, one small identical change each".
