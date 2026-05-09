# SEO audit fixes — design

**Date**: 2026-05-08
**Author**: Luca Wetherall (with Claude)
**Source audit**: [SEO-AUDIT-2026-05-08.md](../../../SEO-AUDIT-2026-05-08.md)
**Branch**: `claude/recursing-johnson-cfffdc` (worktree)

## Goal

Address every actionable finding in the 2026-05-08 SEO audit (sections 1–13, 55 findings across 13 themes). Items requiring user action or non-GitHub-Pages infrastructure are documented in a new top-level `MANUAL-ACTIONS-REQUIRED.md` rather than skipped silently. Single comprehensive PR.

## Decisions locked (from brainstorm)

| Decision | Choice |
|---|---|
| New-page builds | All except a Reviews page: `/for-event-managers.html`, 3 buyer's-guide editorial pages, `/areas/index.html` expansion |
| External URL handling | Web-search publicly discoverable; clearly-marked TODO comments for the rest |
| Testimonial geography mismatch | Leave as-is (skip §4 finding 1) |
| PR strategy | Single comprehensive PR |

## Out of scope (documented, not implemented)

These appear in `MANUAL-ACTIONS-REQUIRED.md`:

- GBP listing claim, primary/secondary category audit, replacement of `share.google` shortener with canonical Maps URL (the URL itself can be discovered if user provides the place; but verifying GBP existence is a manual step).
- Third-party UK directory citation building (Bark, Hitched, Bridebook, FuneralGuide).
- Post-event review-request workflow (audit's #4 priority — operational, ongoing).
- GSC, GA4, CrUX credential provisioning + the queries enumerated in audit §9.
- Fastly VCL changes: security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), HSTS preload + `includeSubDomains` + `max-age=63072000`, extensionless URL → `.html` 301, `Cache-Control: max-age=3600`.
- Per-page OG image generation infrastructure (audit §6 — strategic, 1-day setup + ongoing).
- IndexNow protocol for Bing.
- CSS extraction refactor (audit §13.3.3 — explicitly marked optional).

## Architecture context

- Static site, GitHub Pages on Fastly. Single-language (`en-gb` + `x-default`).
- Build pipeline (`build.sh`): inlines `partials/nav.html` and `partials/footer.html` between `@include-start`/`@include-end` markers; concatenates `css/{tokens,base,layout,components,pages}.css` into `css/style.css`; inlines that into every HTML's `<style>` block; runs `validate_jsonld.py` to assert every `<script type="application/ld+json">` parses.
- 99 indexable HTML pages: 12 pillars, 53 area pages (33 London boroughs under `areas/london/` + 20 cities under `areas/`), 34 music guides under `music-guides/`.
- Schema lives as inline JSON-LD `<script>` blocks in each HTML. `LocalBusiness` carries the canonical `@id: https://londonchoralservice.com/#organization`.
- `partials/nav.html` is the source of truth for global navigation (gets inlined into every HTML at build).

## Work streams (mapped to subagent phases)

The audit has roughly 50 in-scope findings touching every layer of the site. Sequential phases avoid file-edit conflicts; parallelism happens within Phase 6 (new pages — fully independent files).

### Phase 1 — Discovery & manual-actions doc

**Single subagent. Sequential first.**

Tasks:
1. Web-search for publicly discoverable URLs:
   - Companies House: `Alma Consort Ltd` (https://find-and-update.company-information.service.gov.uk/).
   - Oxford faculty page for Luca Wetherall (music.ox.ac.uk).
   - Public LinkedIn for Luca Wetherall (if discoverable; expect `/in/lucawetherall` per audit hint).
   - LinkedIn company page for "London Choral Service" or "Alma Consort" (may not exist — leave TODO).
   - YouTube channel URL for The London Choral Service.
   - Actual `uploadDate` and `duration` (ISO 8601 `PT…`) for the 4 VideoObject blocks (1 on `pricing.html`, 3 on `listen.html`) by reading the YouTube video IDs out of those pages and looking them up.
   - Canonical Google Maps place URL (search GBP listing for "The London Choral Service"; if no clear match, leave TODO with note that the share.google shortener is the only signal in repo).
2. Compile a static lookup table of latitude/longitude centroids for all 53 area pages (33 London boroughs + 20 cities) at 5 dp precision. Borough centroid sources: Wikipedia infobox coordinates or council records. City centroid sources: city/town hall.
3. Emit `data/seo-fix-discovered-urls.yml` with all discovered URLs, geo coords, and clearly-marked `TODO` lines for what couldn't be discovered.
4. Write `MANUAL-ACTIONS-REQUIRED.md` at repo root covering every out-of-scope item above with verification steps (e.g. for GBP: `Open GBP dashboard → Verify "Choir" or "Music Service" is primary category → Add Wedding Service + Funeral Service as secondary → Replace share.google sameAs with canonical Maps place URL`).

Inputs to downstream phases: the YAML file. Phase 2 reads it; phases that don't need URLs ignore it.

### Phase 2 — Schema sweep

**Single subagent. Touches all 99 HTML files (JSON-LD blocks).**

Reads `data/seo-fix-discovered-urls.yml`. For URLs marked TODO, emits HTML comments adjacent to the schema property, e.g. `<!-- TODO: replace with canonical Maps place URL -->`.

Changes:

1. **AggregateRating sweep (CRITICAL)**: Remove `aggregateRating` and `review` properties from the `LocalBusiness` block on **97 of 99** indexable pages. Keep only on `index.html`. Also `about.html`. The 97 pages must reference `LocalBusiness` by `@id` only.
2. **`ratingCount` → `reviewCount`** on `weddings.html` and `funerals.html` Service-level AggregateRating.
3. **`AggregateOffer.priceValidUntil`**: add `"priceValidUntil": "2026-12-31"` to `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`.
4. **HowTo schema removal** on 9 guides: memorial-service-planning, funeral-music-guide, wedding-ceremony-music, funeral-choir-guide, hiring-a-choir, corporate-carol-service, office-carol-service-planning, wedding-choir-guide, choosing-wedding-hymns.
5. **`Article.image`** added to all 33 music guides:
   ```json
   "image": {
     "@type": "ImageObject",
     "url": "https://londonchoralservice.com/assets/og-image.png",
     "width": 1200,
     "height": 630
   }
   ```
6. **`Article.wordCount` + `speakable`** on all 33 guides:
   ```json
   "wordCount": <auto-calculated>,
   "speakable": {
     "@type": "SpeakableSpecification",
     "cssSelector": [".lede", ".guide-body p:first-of-type"]
   }
   ```
   `wordCount` calculated by stripping HTML, counting whitespace-separated tokens in the article body.
7. **`services.html`**: add `"name": "Live Music for Ceremonies"` to the Service node; convert inline `provider` LocalBusiness object to `@id` reference.
8. **`Service.provider.@id`** on 53 area pages:
   ```json
   "provider": {
     "@type": "LocalBusiness",
     "@id": "https://londonchoralservice.com/#organization"
   }
   ```
9. **`openingHoursSpecification`** replaces legacy `openingHours` string on `index.html` and `contact.html`:
   ```json
   "openingHoursSpecification": [{
     "@type": "OpeningHoursSpecification",
     "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
     "opens": "09:00",
     "closes": "18:00"
   }]
   ```
10. **Root LocalBusiness extras** on `index.html`:
    - `"legalName": "Alma Consort Ltd"`
    - `"address.addressRegion": "Greater London"`
    - `"address.postalCode"`: registered office postal code (from Phase 1 Companies House lookup); TODO if not found.
11. **`@type` array extension** on `about.html` and `listen.html`: add `"PerformingGroup"` and `"MusicGroup"` to LocalBusiness. (Homepage already has them.)
12. **`Person` schema** on `about.html` for Luca Wetherall: add
    ```json
    "alumniOf": {"@type": "Organization", "name": "University of Oxford"},
    "worksFor": {"@id": "https://londonchoralservice.com/#organization"},
    "sameAs": [<discovered URLs from Phase 1; TODO comments otherwise>]
    ```
13. **`Organization.sameAs`** on `index.html`: replace `share.google/...` with canonical Maps URL if discovered (else TODO comment); add Companies House URL, YouTube channel URL, LinkedIn (TODO if not discovered).
14. **VideoObject** (1 on `pricing.html`, 3 on `listen.html`): replace placeholder `uploadDate: "2025-01-01"` with discovered actual dates; add `duration` in ISO 8601. TODO comments where Phase 1 couldn't resolve.
15. **`dateModified`** on Service schema on 6 commercial pillars: weddings, funerals, corporate, christmas, services, pricing. Value: `"2026-05-08"`.
16. **`geo` coordinates** on each area page's Service block — 5 dp centroids per the lookup table from `data/seo-fix-discovered-urls.yml` (compiled in Phase 1).

Verification: post-edit, run `python3 validate_jsonld.py`; `./build.sh`; programmatic count of `aggregateRating` occurrences should be exactly 2 (index + about) — assert with grep.

### Phase 3 — Title / meta / H1 sweep

**Single subagent. Touches all 99 HTML files.**

Changes:

1. **Title-tag template fix**: drop the `— London Choral Service` brand suffix on the 53 area pages and the 34 music guides; recompute lengths. Pillars retain brand suffix where they fit ≤60 chars; otherwise short-suffix to `| LCS`.
   - Area-page pattern post-fix: `Funeral and wedding choirs in [City]` (~40 chars).
   - Music-guide pattern post-fix: keep existing per-guide title minus the brand tail.
2. **Area-page H1**: change every area page's H1 from `Funeral singers and choirs in [City]` to `Funeral and wedding choirs in [City]`.
3. **Meta-description trim**: every page's meta description ≤160 chars. Where the description is over the cap, truncate at a sentence/clause boundary so the lead is preserved. The audit names 63 pages; the subagent verifies and trims any it finds.
4. **Sitemap typo**: `popular-wedding-organ-music.html` lastmod `2026-03-06` → `2026-05-06`.
5. **`robots.txt`**: append:
   ```
   Disallow: /*?utm_
   Disallow: /*?gclid=
   Disallow: /*?fbclid=
   Disallow: /*?msclkid=
   ```
6. **`llms.txt`**: under `## Music Guides`, add the 21 currently-missing guide entries (full list from audit §6). Add `> Content last updated: May 2026. 34 music guides available.` directly under the existing blockquote description.

Verification: programmatic title-length scan (`<title>[^<]+</title>`) — every result ≤60 chars; meta-description scan — every result ≤160 chars; `validate_jsonld.py` (no schema changes but build must succeed).

### Phase 4 — Content fixes

**Single subagent. Scattered file touches.**

Changes:

1. **Author byline** under H1 on all 33 individual music guides (the hub `music-guides/index.html` is excluded — not an Article):
   ```html
   <p class="guide-meta">By Luca Wetherall, Artistic Director &amp; Tutor in Music, University of Oxford</p>
   ```
   Inserted directly after the existing `<h1>` (or after the existing `.guide-meta` published-date line, whichever is first under H1). The 3 new buyer's-guide pages built in Phase 6 also receive this byline as part of their template.

2. **Last-updated visible date** on commercial pillars (weddings, funerals, corporate, christmas, services, pricing): `<p class="guide-meta">Last updated: May 2026</p>` directly under H1.

3. **Price-summary paragraph** on `weddings.html` and `funerals.html` immediately above the existing `.price-cards` div, mirroring the corporate.html FAQ pattern:
   - Weddings example: *"A small choir of four singers starts from £1,150; a quintet £1,400; a sextet £1,600; full choirs from £2,000. All ensemble sizes include preparation, travel within London, and the music director."*
   - Funerals: same numbers, framed for the grief context.

4. **Funerals.html humanist paragraph**: insert one paragraph + 2-link cluster pointing to existing guides:
   - Link 1: [non-religious-funeral-music.html](music-guides/non-religious-funeral-music.html)
   - Link 2: [celebration-of-life-music.html](music-guides/celebration-of-life-music.html)

5. **Inline area-page links** on `weddings.html` and `funerals.html`: a single sentence in "How it works" / "What we provide" naming 3 areas with links — `[London](areas/london.html)`, `[Oxford](areas/oxford.html)`, `[Manchester](areas/manchester.html)`.

6. **Resource list of guide links** on `for-funeral-directors.html` and `for-wedding-planners.html`: a "Useful resources for families" / "Useful resources for couples" section with 3–4 guide links.

7. **`contact.html` opening + FAQ + FAQPage schema**:
   - One-paragraph opening summary above "By email" stating who the contact is for, expected response time, what to include in an enquiry.
   - 2–3-question FAQ (e.g. *"How quickly do you reply?"*, *"What information should I include?"*, *"Can I phone instead?"*).
   - FAQPage JSON-LD block matching the visible FAQ.

8. **Cancellation/replacement-cover statement** on `funerals.html` and `for-funeral-directors.html`:
   *"In the event of illness, we always have a replacement musician available from our roster of over 150 singers."*

9. **Richmond → London hub body-link**: in `areas/london/richmond.html`, demote the buried "nearby boroughs" line and add an in-body sentence linking to `areas/london.html`.

10. **`pricing.html` → `areas/london.html` link**: add one sentence in "What happens next" — *"For funerals in London, there are no travel costs."* — with the area link.

11. **Funeral-hymns contradiction**: on both `popular-funeral-hymns.html` (visible body + FAQPage answer) and `abide-with-me.html` (visible body + any "most-requested" claim), standardise the claim:
    > "Abide With Me and The Lord's My Shepherd are the two most-requested funeral hymns in the UK. Abide With Me is the most-commonly-chosen as a closing hymn; The Lord's My Shepherd is the most widely known."

12. **"Ensembles for every occasion" boilerplate replacement** on 26 borough pages: replace the shared paragraph beginning *"Not every occasion calls for the same size of ensemble…"* with borough-specific guidance written from venues already named on each page. The subagent reads each of the 26 pages, identifies the named venues (e.g. Westminster Abbey on westminster.html), and produces a 100–150 word paragraph keyed to those venues. Must be unique per borough — no two boroughs receive the same paragraph.

Verification: link-integrity grep (no broken `href=` to nonexistent files); `validate_jsonld.py`; `./build.sh`.

### Phase 5 — Nav + link graph

**Single subagent. Touches `partials/nav.html` + most HTML files for cross-links.**

Changes:

1. **`partials/nav.html` restructure**: top-level commercial pillars become first-class. Final structure:
   ```
   Home | About | Services | Weddings | Funerals | Corporate | Christmas | Listen | Music Guides ▾ | Pricing | Contact
   ```
   `Music Guides` retains a dropdown linking to category-filter URLs and "Browse all". The 4 commercial-pillar items are direct page links (no dropdown). On mobile, all become flat list items.

   The existing CSS uses a 768px hamburger toggle threshold (`@media (max-width: 767px)`); above that the flat list renders horizontally. With 11 top-level items the flat layout will likely wrap or overflow at narrow desktops (~768–999 px). If post-build inspection at 768, 1024, and 1280 px shows wrapping or overflow, group the 4 commercial pillars under an "Occasions ▾" dropdown sibling to "Music Guides" — but try the flat layout first.

2. **`corporate.html` cross-links** (audit §7 finding 1): add inline body-content links from:
   - `music-guides/corporate-carol-service.html`
   - `music-guides/office-carol-service-planning.html`
   - `music-guides/company-christmas-party-entertainment.html`
   - `christmas.html`

3. **"Related guides" component** on every music guide: a templated 3-link section near the bottom — relevant pillar + B2B page + 2–3 sibling guides. The subagent encodes a small per-guide mapping of "relevant siblings" and inserts the markup. Pillar/B2B routing is by topic:
   - Wedding-music guides → `weddings.html` + `for-wedding-planners.html`
   - Funeral-music guides → `funerals.html` + `for-funeral-directors.html`
   - Christmas/corporate guides → `christmas.html` + `corporate.html` (and the new `for-event-managers.html`)
   - General/hub guides → `services.html`

4. **Borough adjacency expansion**: each London-borough page links 4–6 adjacent boroughs (extend the existing `nearby boroughs` block where it has fewer than 4). Adjacency lookup encoded as a static mapping in the subagent prompt.

5. **Crematorium-music ↔ borough cross-links**: add a "Crematoria we serve in London" section on `music-guides/crematorium-music.html` linking to borough pages by named venue (Golders Green → Barnet, West London → Hounslow, South Essex → Havering, Honor Oak → Southwark, Hither Green → Lewisham, Eltham → Greenwich, plus any others surfaced from grep). Reciprocal: each named borough page gets one body-link back to the guide.

Verification: every internal `href` resolves to an existing file (programmatic check); nav passes through all 99 pages after `./build.sh` (since nav is a partial, this is automatic); inbound-link counts confirmed by a Python grep script (corporate.html should show ≥6 inbound after this phase, including nav).

### Phase 6 — New pages

**5 parallel subagents — fully independent files.**

Each subagent receives:
- The "house style" sample (a real existing page closest in structure)
- The required JSON-LD shape
- The internal-linking obligations (which existing pages must link to it; which existing pages it must link out to)
- House-style copy guidance: humanistic-writing skill principles (no AI tells), academic-proofreader voice for the editorial/buyer's-guide pages.

#### 6.1 — `/for-event-managers.html`

Mirrors `/for-wedding-planners.html` structure. Sections:
- H1 + lede targeted at corporate event managers
- "How we work with event managers" (lead times, formats, briefing process, public-liability evidence)
- "What your delegates / clients receive"
- "Booking & invoicing" (PO process, late invoicing, terms)
- "Useful resources for event managers" (3–4 guide links)
- FAQ (5 questions) + FAQPage JSON-LD
- CTA → contact form
- Service JSON-LD with `@type: ProfessionalService`

Word count target: 900–1,200 (matches the other two B2B pages).

Internal-linking obligations:
- Linked from: nav (added in Phase 5), `corporate.html`, the 3 corporate-themed guides (corporate-carol-service, office-carol-service-planning, company-christmas-party-entertainment), and footer.
- Links out: `corporate.html`, `christmas.html`, the 3 corporate guides, `pricing.html`, `contact.html`.

#### 6.2, 6.3, 6.4 — Buyer's-guide editorial pages

Three editorial pages targeting directory-locked queries (audit §10):

- **`/music-guides/best-wedding-choirs-london.html`** — informational pre-purchase intent.
- **`/music-guides/best-christmas-carol-singers.html`** — same shape, Christmas vertical.
- **`/music-guides/best-funeral-singers-london.html`** — same shape, funeral vertical.

Common shape (per audit §10 recommendation):
- H1 + visible byline (`<p class="guide-meta">By Luca Wetherall, Artistic Director &amp; Tutor in Music, University of Oxford</p>`) + published-date line
- Lede paragraph
- "What to look for" (4–5 paragraphs of qualifying criteria)
- "Ensemble size guidance"
- "Price ranges across the market" (general, not just LCS — credibility)
- "4–6 questions to ask any provider"
- "How LCS approaches this" (single section, restrained, with internal CTA — not the lead)
- "Related guides" component (added in Phase 5 for existing guides; the buyer's-guide pages include it on first emission)
- FAQPage JSON-LD
- Article JSON-LD with author + publisher + image + wordCount + speakable + dateModified

Word count target: 1,800–2,200 (matches existing high-value music guides).

Internal-linking obligations:
- Linked from: corresponding pillar (`weddings.html` / `christmas.html` / `funerals.html`), `music-guides/index.html`, "Related guides" components on adjacent guides.
- Links out: corresponding pillar, B2B page (for-wedding-planners / for-event-managers / for-funeral-directors), 2–3 thematic sibling guides.

#### 6.5 — `/areas/index.html` expansion

Existing page is 670 words, list-of-links shape. Expand to 1,000–1,200 words with:
- New 400–600-word editorial introduction explaining how the service works geographically — London-borough coverage, lead times for distant cities, travel-cost logic, the relationship between the borough cluster and outer cities.
- 4-question FAQ + FAQPage JSON-LD: e.g. *"How quickly can you arrange singers in Manchester?"*, *"Do you charge travel for outer cities?"*, *"Can you cover venues outside the listed cities?"*, *"How do you choose musicians per location?"*.
- Existing list-of-area-links retained.

#### Sitemap + llms.txt registration

After Phase 6 completes, the main session adds the **4 new pages** (`for-event-managers.html` + 3 buyer's-guides; `/areas/index.html` is an expansion, already listed) to:
- `sitemap.xml` — 4 new entries with `<lastmod>2026-05-08</lastmod>` and `<changefreq>` / `<priority>` matching existing patterns (B2B page priority 0.7; buyer's guides 0.6).
- `llms.txt` — `for-event-managers.html` under `## Main Pages`; the 3 buyer's-guides under `## Music Guides`.

### Phase 7 — Performance + tech polish

**Single subagent.**

Changes:

1. **Font preload**: confirmed filenames are `cormorant-garamond.woff2`, `cormorant-garamond-italic.woff2`, `source-serif-4.woff2`, `source-serif-4-italic.woff2`. Preload the two non-italic faces (italic is rarely above-the-fold on this site):
   ```html
   <link rel="preload" href="/fonts/cormorant-garamond.woff2" as="font" type="font/woff2" crossorigin>
   <link rel="preload" href="/fonts/source-serif-4.woff2" as="font" type="font/woff2" crossorigin>
   ```
   The preload links must appear in `<head>` of every page. Since `partials/nav.html` is in `<body>`, the preload tags must go directly into each HTML file's `<head>` (or a new `partials/head-extras.html` consumed by an `@include-start`/`@include-end` block placed inside `<head>`). Choose the new partial route — it's the cleaner pattern given the existing partial system, and the build script already supports `@include` markers anywhere in a file.

2. **Image `width` and `height`** on every `<img>` and `<picture>` element. YouTube facade thumbs (`maxresdefault.jpg`) are 1280×720. Other images: read intrinsic dimensions from `assets/` at edit time.

3. **NAP phone E.164 standardisation**:
   - Schema: every phone field uses `+447356042468`.
   - Visible HTML: `07356 042468` retained as the human-readable form.
   - `llms.txt`: `07356 042468` retained.

Verification: programmatic check that every `<img>` has both `width` and `height`; every JSON-LD `telephone` field is `+447356042468`; `./build.sh`; `validate_jsonld.py`.

### Phase 8 — Verification

**Sequential, run in main session — no subagent.**

1. `./build.sh` — must succeed.
2. `python3 validate_jsonld.py` — must succeed.
3. Programmatic checks (Python script `scripts/audit-fix-checks.py` written for this purpose, then deleted before commit):
   - Every page's `<title>` ≤60 chars.
   - Every page's `<meta name="description">` ≤160 chars.
   - `aggregateRating` JSON occurrences = exactly 2 (index.html + about.html).
   - `HowTo` JSON occurrences = 0.
   - `priceValidUntil` present on the 4 service pages.
   - `Article.image` present on all 33 + 3-new = 36 music-guides Article schemas.
   - Every internal `href` resolves to a file that exists (no 404s within the repo).
   - sitemap.xml entries match indexable pages on disk (existing build invariant; reconfirmed).
   - llms.txt contains all 34 guides + 5 new pages.
4. Visual smoke check: open `index.html`, `weddings.html`, `areas/london.html`, `music-guides/abide-with-me.html`, and one of the new buyer's-guide pages directly in a browser (the site is static — no server needed). Confirm nav renders, no obvious layout regressions, no console errors. Test at 768, 1024, and 1280 px viewport widths to validate the nav restructure.
5. Commit on the feature branch in logical batches — one commit per phase — so the diff stays reviewable. Open the PR with a structured summary referencing audit findings by section.

## Cross-cutting concerns

### House style and writing voice

All net-new prose (Phase 4, Phase 6) must avoid AI writing tells. Subagents in those phases invoke `anthropic-skills:stop-slop` (or `humanistic-writing` where the deeper humanisation pass is appropriate) before final emission. The audit's existing high-quality content (the music guides) is the calibration — match its register: factual, specific, named entities, no hedging, no marketing tells.

### Subagent context discipline

Each subagent receives:
- A self-contained task brief.
- The relevant section of this design doc (Phase X) verbatim.
- Concrete file paths + line ranges (not "find the file that does X").
- The verification command to run before reporting back.

Subagents do NOT receive the whole audit — only the findings their phase addresses.

### Failure handling

If a subagent reports a verification failure or returns an incomplete result:
1. Main session inspects the failure, re-scopes if narrow.
2. If broad, the main session does the work directly rather than re-spawning.
3. Phase is not marked complete in the todo list until verification passes.

### Commit cadence

One commit per phase, on the existing worktree branch `claude/recursing-johnson-cfffdc`. Commits are made after the phase's verification passes — not before. Final commit opens the PR.

## Acceptance criteria

- All §1–12 + §13 in-scope findings either implemented in code or documented in `MANUAL-ACTIONS-REQUIRED.md`.
- `./build.sh` exits 0; `python3 validate_jsonld.py` exits 0.
- Every Phase 8 programmatic check passes.
- Single PR opened against `main` from the feature branch with a structured summary mapping commits to audit sections.

## Verification URLs (for the user post-merge)

After merge, the user runs (manual, browser):
- [Rich Results Test — homepage](https://search.google.com/test/rich-results?url=https://londonchoralservice.com/)
- [Rich Results Test — a music guide that previously had AggregateRating](https://search.google.com/test/rich-results?url=https://londonchoralservice.com/music-guides/abide-with-me.html) — should report no review-snippet eligibility errors.
- [Rich Results Test — services.html](https://search.google.com/test/rich-results?url=https://londonchoralservice.com/services.html) — Service.name now present.
- [PageSpeed Insights — homepage](https://pagespeed.web.dev/analysis?url=https://londonchoralservice.com/) — confirm CWV pass.

## Appendices

### A. File-touch budget (rough)

| Phase | Files touched | Net new files | Verification |
|---|---|---|---|
| 1 | 0 (creates 1 yml + 1 md) | 2 | n/a |
| 2 | ~99 HTML | 0 | validate_jsonld.py |
| 3 | ~99 HTML + sitemap.xml + robots.txt + llms.txt | 0 | title/meta length scan |
| 4 | ~50 HTML (scattered) | 0 | link integrity |
| 5 | partials/nav.html + ~80 HTML | 0 | inbound-link count |
| 6 | sitemap.xml + llms.txt | 5 HTML | build + jsonld |
| 7 | partials/nav.html + ~30 HTML (img-bearing) | 0 | img-attr scan |
| 8 | 0 | 0 (deletes scratch script) | full sweep |

### B. Findings → phase mapping

| Audit finding (severity) | Phase |
|---|---|
| §1 MEDIUM extension-less duplication | Out of scope (manual doc) |
| §1 MEDIUM security headers | Out of scope (manual doc) |
| §1 LOW HSTS / Cache-Control | Out of scope (manual doc) |
| §2 HIGH title truncation | Phase 3 |
| §2 HIGH funeral-leaning H1 | Phase 3 |
| §2 MEDIUM meta-description length | Phase 3 |
| §3 CRITICAL AggregateRating sitewide | Phase 2 |
| §3 CRITICAL ratingCount/reviewCount | Phase 2 |
| §3 HIGH HowTo deprecation | Phase 2 |
| §3 HIGH Article.image | Phase 2 |
| §3 HIGH services.html Service.name | Phase 2 |
| §3 HIGH priceValidUntil | Phase 2 |
| §3 MEDIUM VideoObject duration/uploadDate | Phase 1 (lookup) + Phase 2 (write) |
| §3 MEDIUM MusicGroup expansion | Phase 2 |
| §3 MEDIUM FAQPage retention | No-op (decision: keep, document intent — covered by spec note) |
| §3 MEDIUM openingHours format | Phase 2 |
| §3 MEDIUM legalName | Phase 2 |
| §3 MEDIUM Service.provider.@id | Phase 2 |
| §3 LOW address fields | Phase 2 |
| §3 LOW Person properties | Phase 2 |
| §3 LOW Organization.sameAs | Phase 1 (lookup) + Phase 2 (write) |
| §4 HIGH recycled testimonials | Skip (decision) |
| §4 HIGH Ensembles boilerplate | Phase 4 |
| §4 HIGH funeral-hymns contradiction | Phase 4 |
| §4 MEDIUM cannibalisation triplets | No-op (audit verdict: no merge needed) |
| §4 MEDIUM extractable price answer | Phase 4 |
| §4 MEDIUM areas/index thinness | Phase 6.5 |
| §4 MEDIUM last-updated date | Phase 4 |
| §5 CRITICAL review volume | Out of scope (manual doc) |
| §5 CRITICAL GBP sameAs | Phase 1 (discover/TODO) + Phase 2 (write) |
| §5 HIGH NAP phone format | Phase 7 |
| §5 MEDIUM area geo coords | Phase 2 |
| §5 MEDIUM for-event-managers missing | Phase 6.1 |
| §5 MEDIUM citations audit | Out of scope (manual doc) |
| §6 HIGH llms.txt 21 missing guides | Phase 3 |
| §6 HIGH Person sameAs | Phase 1 + Phase 2 |
| §6 MEDIUM wordCount/speakable | Phase 2 |
| §6 MEDIUM llms.txt freshness | Phase 3 |
| §6 MEDIUM single OG image | Out of scope (manual doc) |
| §7 CRITICAL corporate.html link starvation | Phase 5 |
| §7 CRITICAL global nav omission | Phase 5 |
| §7 HIGH B2B page link starvation | Phase 5 |
| §7 MEDIUM guide cluster cross-linking | Phase 5 |
| §7 MEDIUM borough adjacency | Phase 5 |
| §7 MEDIUM crematorium ↔ boroughs | Phase 5 |
| §8 LOW performance | Out of scope (CrUX dependency) |
| §9 GSC/GA4/CrUX | Out of scope (manual doc) |
| §10 directory-locked queries | Phase 6.2/6.3/6.4 |
| §10 persona issues | Resolved by Phase 4 + Phase 6.1 + Phase 6.2/3/4 |
| §11 sitemap typo | Phase 3 |
| §11 stale lastmods | No-op (defensible — audit notes this) |
| §11 IndexNow | Out of scope (manual doc) |
| §13.1.1 extension-less twins | Out of scope (manual doc) |
| §13.1.2/3 HSTS / security headers | Out of scope (manual doc) |
| §13.1.4 robots.txt utm disallow | Phase 3 |
| §13.1.5 Cache-Control | Out of scope (manual doc) |
| §13.1.6 IndexNow | Out of scope (manual doc) |
| §13.2.1 author byline | Phase 4 |
| §13.2.2 funerals humanist gap | Phase 4 |
| §13.2.3 weddings/funerals area links | Phase 4 |
| §13.2.4 for-funeral-directors guide links | Phase 4 |
| §13.2.5 contact opening + FAQ | Phase 4 |
| §13.2.6 testimonial date format | Skip (decision: testimonials untouched) |
| §13.2.7 cancellation policy | Phase 4 |
| §13.2.8 Richmond hub link | Phase 4 |
| §13.2.9 pricing → London link | Phase 4 |
| §13.2.10 VideoObject placeholder | Phase 1 + Phase 2 |
| §13.3.1 font preload | Phase 7 |
| §13.3.2 image width/height | Phase 7 |
| §13.3.3 inline CSS | Out of scope (audit-marked optional) |
| §13.3.4 LCP image preload | Out of scope (no LCP image; audit notes) |
| §13.4 GSC/GA4/CrUX | Out of scope (manual doc) |
