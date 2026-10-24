---
name: build-and-verify
description: "REQUIRED before changing any CSS, styles, nav, footer, or partials on this site, before any site-wide/bulk edit across pages, and before committing any HTML change. Also use when the user says 'build', 'rebuild', 'run build.sh', 'verify the site', or when a git diff unexpectedly touches 100+ HTML files. Explains the CSS-inlining/partials build pipeline, which files are generated vs source, expected diff shapes, and the verification checklist."
metadata:
  version: 1.0.0
---

# Build and Verify

This site has no framework and no CI build. `build.sh` is the entire build system, and it **rewrites the HTML files in place**. Misunderstanding it is the most expensive mistake you can make in this repo.

## The two cardinal rules

1. **Never hand-edit the generated CSS block in any page** (from `<!-- @css-start … -->` to `<!-- @css-end -->`). Every page carries its own critical CSS inlined into its `<head>`, plus a non-blocking link to `css/style.css`. That block is generated. Edit the sources — `css/tokens.css`, `css/base.css`, `css/layout.css`, `css/components.css`, `css/pages.css` — then run `./build.sh`. `css/style.css` is also generated (a concatenation of the five sources); never edit it either.
2. **Never hand-edit content between `<!-- @include-start partials/x.html -->` and `<!-- @include-end partials/x.html -->` markers.** The nav, footer, and head-extras appear expanded inside every page, but the source of truth is `partials/nav.html`, `partials/footer.html`, `partials/head-extras.html`. Edit the partial, then run `./build.sh`.

Hand-edits inside either region will be silently overwritten by the next build.

## What build.sh does (7 steps)

1. **CSS concat** — concatenates the five `css/*.css` sources (in the order above) into `css/style.css`.
2. **Partial expansion** — for every HTML file outside `partials/`, replaces the content between each `@include-start`/`@include-end` marker pair with the current content of the named partial. Fails loudly if a referenced partial doesn't exist.
3. **Critical CSS** — `scripts/inline_css.py` replaces each page's block between `<!-- @css-start … -->` and `<!-- @css-end -->` with the rules that can style that page's first screen (13–20 KB; the bundle is 61 KB), then `<link rel="preload" href="/css/style.css?v=<hash>" as="style" onload="…this.rel='stylesheet'">` and a `<noscript>` stylesheet fallback. The browser caches the bundle after the first page; `?v=` changes with the bundle. The first screen is worked out from the page itself: its body without the footer, `<main>` cut after three top-level sections, plus the classes `js/consent.js` and `js/nav.js` add. A rule is kept when every class, id and element its selector names (outside `:not()`) appears there. Pages without the site bundle (the `destinations/` register pages) are left alone. `python3 scripts/inline_css.py --report` lists each page's critical size. **After a CSS or first-screen markup change, check the first screen is unchanged with only the critical CSS**: in a preview, disable the `style.css` link and compare (see Verification checklist).
4. **Sitemap and dates** — `scripts/generate_sitemap.py` rewrites `sitemap.xml` and `data/page-dates.json` (lastmod moves only when body content changes); `scripts/sync_dates.py` sets `dateModified`, `article:modified_time` and the visible Published/Updated line on every Article page from that date.
5. **llms-full.txt** — `scripts/generate_llms_full.py` dumps the visible text of every sitemap page.
6. **Validation** — runs `python3 validate_jsonld.py`, which checks that every `application/ld+json` block in every HTML file parses as JSON. Build fails if any block is invalid.
7. **Deploy allowlist** — `scripts/stage_site.py` checks that every file is either published (`PUBLIC`) or internal (`PRIVATE`), that every sitemap URL and everything the pages reference (links, scripts, fonts, images, icons, form redirects) will be served, and that no internal link is broken. A failure names the file: add the new directory, asset type or root file to `PUBLIC` (an internal file type to `PRIVATE`), or fix the link.

There is no build step in CI — **the built output is what you commit**, which is why `./build.sh` must run before committing any css/ or partials/ change. On each push to `main`, `.github/workflows/deploy-pages.yml` deploys only the files `scripts/stage_site.py` publishes, unchanged; the rest of the repo is not served.

## When to rebuild

| You changed… | Rebuild? |
|---|---|
| Page body copy, meta tags, JSON-LD in one page | Not required (harmless if you do) |
| Anything in `css/` | **Mandatory** |
| Anything in `partials/` | **Mandatory** |
| Added a new page | **Mandatory** (expands its markers, inlines its critical CSS) |
| First-screen markup (a hero, the first sections) | **Mandatory**: its critical CSS depends on the classes it uses |
| `llms.txt`, `robots.txt`, docs | No |
| Body copy on any page | Recommended: the build refreshes `sitemap.xml` lastmod and article dates from content (`scripts/generate_sitemap.py`, `scripts/sync_dates.py`) |

## Expected diff shapes (anti-panic guide)

- **Content edit on one page** → `git diff --stat` shows 1 file.
- **CSS source edit + rebuild** → up to ~145 HTML files change (every page's `?v=` hash moves; the critical rules only where the edited rules apply), plus `css/style.css` and the source you edited. Every HTML change must be confined to the `@css-start`/`@css-end` block. Spot-check three pages from different sections: `git diff -- index.html areas/london/camden.html music-guides/index.html`.
- **Partial edit + rebuild** → ~165 HTML files change, confined to the marker regions for that partial. Spot-check the same way.
- **A rebuild with no source changes** → clean tree. `./build.sh && git diff --stat` producing no output is the standard sanity check that the pipeline is healthy.

If a rebuild changes anything *outside* the generated CSS block or a marker region, stop and investigate before committing — something upstream is wrong.

## Verification checklist

Run before committing:

1. `./build.sh` exits 0 (it prints counts for CSS bytes, partials populated, files inlined, and ends with the JSON-LD result).
2. If you only edited JSON-LD, `python3 validate_jsonld.py` alone is enough.
3. `git diff --stat` matches the expected shape above; spot-check representative pages.
4. Preview locally: `python3 -m http.server 8000` from the repo root, then check the affected pages at `http://localhost:8000/…` (nav, footer, and styles render; no raw marker comments visible).
   After a CSS change or new first-screen markup, compare each affected page at 1280 and 375 px with and without the bundle: snapshot every element in the first viewport (rect, colour, background, font size, display), set `document.querySelector('link[href^="/css/style.css"]').disabled = true`, snapshot again; the two must match, with the cookie sheet showing and without. A difference means a first-screen rule is missing from the critical CSS (or a script class needs adding to `FIRST_SCREEN_JS` in `scripts/inline_css.py`).
5. For copy changes, the writing-site-copy skill's checks apply before this checklist.

## Site-wide sweeps (things NOT in partials)

The GA4/Google Ads snippet is now `partials/analytics.html` (since 2026-09-04): edit the partial and rebuild. Most other head meta structure is still duplicated per page; changing it means editing ~165 files. Rules:

- Never sweep by hand. Write a small Python script (or careful `sed`) that targets the same file set as `validate_jsonld.py`: `*.html`, `areas/*.html`, `areas/**/*.html`, `music-guides/*.html`.
- Verify with counts: `grep -rl 'PATTERN' --include='*.html' . | wc -l` before and after — the numbers must be equal (or exactly what you intended).
- Run the full verification checklist afterwards; the diff shape should be "~165 files, one small identical change each".
