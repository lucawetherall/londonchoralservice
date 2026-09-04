---
name: new-page
description: "Use when creating any new page on this site: a new city/area page, a London borough page, a music-guide article, a service page, or a B2B landing page. Also when the user says 'add a page for <place>', 'new article', 'new guide', 'new landing page'. Provides the clone-an-exemplar workflow, the required head block and JSON-LD per page type, and the sitemap/llms.txt/internal-linking wiring checklist."
metadata:
  version: 1.0.0
---

# Creating a New Page

Every page on this site is a standalone HTML file carrying ~60 lines of head boilerplate, an inlined CSS block, expanded partials, and page-type-specific JSON-LD. **Never write a page from scratch.**

## Method: clone the nearest exemplar

1. Pick the **most recently added** page of the same type (check `git log --diff-filter=A --name-only`). Fallback exemplars:
   - City/area page → `areas/manchester.html`
   - London borough page → `areas/london/camden.html`
   - Music guide article → any recent `music-guides/*.html` (e.g. `music-guides/wedding-pop-songs-choir.html`)
   - Service page → `weddings.html` or `christmas.html`
   - B2B landing page → `for-event-managers.html`
2. Copy it to the new path. URL conventions: lowercase, hyphenated, `.html` extension, matching the directory of its type (`areas/`, `areas/london/`, `music-guides/`, or root).
3. Change what varies; keep the invariants verbatim (next section).
4. Work through the wiring checklist, then run `./build.sh` (see the build-and-verify skill).

## What to change vs what to keep

**Keep verbatim** (invariant across the site):
- The `partials/analytics.html` include markers (GA4/Google Ads + Consent Mode); the build expands them.
- The `@include-start`/`@include-end` marker pairs and everything between them — stale expanded content from the cloned page is fine; `./build.sh` re-expands it.
- The inlined `<style>` block — again, the build refreshes it.
- `theme-color`, `robots`, `dns-prefetch` lines, favicon links, `og:image` path.

**Change for the new page** (full element-by-element list in `references/head-checklist.md`):
- `<title>`, meta description (**141–161 characters** — check with `python3 -c "print(len('...'))"`)
- `canonical` + both `hreflang` links, all `og:*` and `twitter:*` URL/title/description fields
- All JSON-LD blocks — see `references/jsonld-by-page-type.md` for what each page type must carry
- The entire `<body>` content between the nav and footer markers
- `<h1>` (exactly one per page)

## Wiring checklist

A page that exists but isn't wired in is invisible. All of these, every time:

- [ ] `sitemap.xml`: nothing to do by hand. `./build.sh` adds the page with today's `lastmod` (`scripts/generate_sitemap.py`); check the new `<url>` appears. Guides and compare pages also get their visible date line and `dateModified` from the build.
- [ ] `llms.txt`: add the page under the appropriate section.
- [ ] Internal links from hub pages — see `references/internal-linking.md` for which hubs must link to each page type.
- [ ] Run `./build.sh` — must exit 0 (this also validates your JSON-LD).
- [ ] Diff check per the build-and-verify skill: the new file plus the exact wiring files you touched, nothing else unexpected.
- [ ] Preview at `python3 -m http.server 8000`: nav/footer render, no raw `@include` content missing, page reads correctly on a ~375px viewport.

## Copy quality gate

Before writing any body copy, load the **writing-site-copy** skill — it carries the house anti-slop rules. For a full editing pass on a drafted page, use the generic **copy-editing** skill afterwards. Do not invent facts: prices come from `pricing.html`, venue/place claims must be real and checkable, and unresolved schema values come from `data/seo-fix-discovered-urls.yml` — never fabricated.
