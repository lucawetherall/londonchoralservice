# Private Events Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Load `build-and-verify` and `new-page` before starting; their constraints go into every phase brief. Load `writing-site-copy` **and** `stop-slop` before drafting or auditing any visible text.

**Goal:** Ship `/private-events.html` — a fully insulated, light-parchment page converting very high-value private and international enquiries for Alma Consort, with a voicing selector, an application-style form with budget bands, and no prices anywhere. Metric: cost per qualified enquiry.

**Architecture:** One hand-authored page carrying its own scoped `<style>` block (first inner line a comment, so `build.sh` Pass A never mistakes it for the generated bundle — see the spec's Pass A defence), no site nav/footer partials, one new JS file (`js/private-events.js`), and wiring edits in a strict order so the sitemap never references a file that does not exist. The nav partial edit rebuilds every page on the site; that diff shape is expected and checked, not feared.

**Tech Stack:** Static HTML + the existing `build.sh` pipeline (CSS inlining, partial expansion, `generate_llms_full.py`, `validate_jsonld.py`, `validate_competitor_claims.py`, `validate_house_claims.py`), Web3Forms + gtag on the client, Chromium/Playwright for visual review. No framework, no CI.

**Spec:** [docs/superpowers/specs/2026-08-26-private-events-design.md](../specs/2026-08-26-private-events-design.md)

---

## Read this before starting

- **The Pass A defence is load-bearing.** The page's `<style>` block starts with a comment line; the page never links `style.css`. Deleting that comment is the most expensive mistake available here — the next build replaces the entire hand-authored stylesheet with the site bundle. The idempotency check in Phase 5 is the tripwire.
- **Sequencing is not optional.** `generate_llms_full.py` walks `sitemap.xml` `<loc>` entries, and a sitemap entry without the file on disk **fails the build**. The page file must exist before the sitemap edit; the sitemap edit before the first build.
- **House-claims traps.** Voicings as words (Eight / Twelve / Sixteen / Twenty-four), never digits; no "roster"; "luxury hotels" never "five-star"; no VAT wording; no "over 150". The validator enforces these — write to pass it, do not negotiate with it.
- **Video IDs** may only come from `data/seo-fix-discovered-urls.yml`. A voicing with a `null` entry renders no player; that is the designed launch state.

---

## Phase 1: Copy pack

Load `writing-site-copy` + `stop-slop`, then draft every visible string before any HTML exists: all seven sections, hero variants, title, meta description (141–161 chars, counted with python), OG/Twitter text, form labels, options and microcopy, success and error messages, the four voicing prose notes, the llms.txt line, JSON-LD description strings, the nav label, and the two in-copy link sentences for `weddings.html` and `about.html`.

- [ ] **Step 1:** Draft the pack to a scratchpad file; python-count the meta description.
- [ ] **Step 2:** Self-audit against both skills and the banned-claims list before handing off.

## Phase 2: JavaScript

- [ ] **Step 1:** Write `js/private-events.js` per the spec — config head (`VOICING_VIDEOS` all `null` at launch; `ADS_CONVERSION` set to the site's existing generic Contact label so tracking works from day one), reduced-motion-gated fades, voicing selector (radios → aria-live note + form sync + click-to-load `youtube-nocookie` embed), UTM/gclid capture, conditional fields, and the submit handler (honeypot → timing check → Web3Forms fetch → inline confirmation + gtag conversion; no redirect).

## Phase 3: Page assembly

- [ ] **Step 1:** Assemble `private-events.html`: head in `new-page` checklist order, theme-color `#FAF6EE`, the scoped light-register CSS **with the Pass A comment as the first inner line of `<style>`**, bespoke header/footer, the seven sections with the Phase 1 copy verbatim, and the JSON-LD graph (Service + PerformingGroup → existing `#organization`; no BreadcrumbList, no AggregateRating/Review).
- [ ] **Step 2:** Pre-flight greps before any build: no `style.css` reference in the page; the comment line directly after `<style>`.

## Phase 4: Wiring — strict order

- [ ] **Step 1:** `sitemap.xml` — add the entry (lastmod 2026-08-26, monthly, 0.7) **only now that the page file exists**.
- [ ] **Step 2:** `llms.txt` — one line under `## Main Pages` in house format.
- [ ] **Step 3:** `partials/nav.html` — the discreet Services-dropdown item. This is the edit that rebuilds the whole site.
- [ ] **Step 4:** `weddings.html` + `about.html` — one in-copy link each (never from `compare/` or `for-*` pages); refresh both pages' sitemap `lastmod`.
- [ ] **Step 5:** `MANUAL-ACTIONS-REQUIRED.md` — dated section listing the owner actions (see foot of this plan).

## Phase 5: Build + idempotency

- [ ] **Step 1:** `./build.sh` — all four validators green.
- [ ] **Step 2:** Check the diff shape: **~130 built pages changed, nav-marker hunks only**. Spot-check two or three; any change outside the nav include markers means stop and investigate.
- [ ] **Step 3:** Run `./build.sh` a second time; `git diff private-events.html` must be **empty**. A non-empty diff means Pass A ate the stylesheet or Pass B inlined the bundle — fix the page, never the build.

## Phase 6: Five-lens review

Parallel reviewers, each with one lens; every finding verified before fixing, then Phase 5 re-run.

- [ ] **D1 Code review** — JS correctness (FormData/disabled-field exclusion, timing check, gtag queueing, IntersectionObserver, radio semantics), HTML validity, build-pipeline safety.
- [ ] **D2 Copy/slop audit** — fresh agent loads `stop-slop` + `writing-site-copy`, adversarially audits every rendered string plus meta/JSON-LD/llms.txt for AI tells, house-rule breaches, banned claims, UK English.
- [ ] **D3 Accessibility + design** — WCAG 2.1 AA against the spec's computed contrast table (no candle/limestone/naveStone text on light fields, cassockRed focus rings, real labels, radiogroup keyboard behaviour, aria-live note, reduced-motion completeness), plus type-scale and measure fidelity.
- [ ] **D4 SEO/head/schema** — head block row-by-row against the `new-page` checklist, JSON-LD against the graph spec, sitemap/llms.txt/nav wiring, canonical/hreflang/OG consistency.
- [ ] **D5 Visual** — local server + Chromium: 390×844 and 1440×900 screenshots (hero, voicing, form) plus a reduced-motion pass; drive the page end to end — arrow-key radios, selector→select sync, Company reveal, date-flexible behaviour, under-5-seconds rejection, inline success, no dead play buttons, no site-bundle styles leaking in.

## Phase 7: Graph refresh and commit

- [ ] **Step 1:** `/graphify --update`; commit `graphify-out/` alongside the content change.
- [ ] **Step 2:** Commit per house style (`feat(private-events): …`), push, open a draft PR, subscribe to PR activity. Send final screenshots to the owner.

---

## Expected diff shapes

| Change | Expected shape |
|---|---|
| `partials/nav.html` edit + rebuild | ~130 built pages, hunks confined to the nav include-marker region only |
| Second `./build.sh` | `git diff private-events.html` empty (idempotency) |
| `llms-full.txt` | Regenerated — one new page section; never hand-edited |
| `css/style.css`, `css/*` | **Untouched.** This page's styles are scoped in its own `<style>` block and must never enter the site bundle |

## Outstanding owner actions (recorded in MANUAL-ACTIONS-REQUIRED.md)

1. **Google Ads:** create a dedicated "Private events enquiry" conversion action and paste its `send_to` label over `PE.ADS_CONVERSION` in `js/private-events.js`; until then the existing generic Contact label fires, so tracking works from day one but is not segmented. Map the page's GA4 conversion event in the Ads UI.
2. **Photography** for the hero and section imagery; the page ships typographic-only until supplied.
3. **Fuller venue list** (15+); the launch list is seeded from the vetted `about.html` credentials, with an HTML comment slot marking where the additions go.
4. **Voicing video mapping:** one YouTube ID per voicing in `PE.VOICING_VIDEOS`. IDs must exist in `data/seo-fix-discovered-urls.yml` first — add new videos there with verified dates before wiring them in.
5. **Verify https://www.almaconsort.com** renders well as the link target (unreachable from the build environment), and add a reciprocal link from it back to `/private-events.html`.
6. **Optional:** a bespoke 1200×630 OG image; the shared site image is used until then.

## Done when

- `./build.sh` exits 0 twice in a row with an empty `git diff private-events.html` between runs.
- All four validators green; no banned claim survives a grep.
- The nav diff is confined to include-marker regions across ~130 files.
- All five review lenses report clean.
- `graphify-out/` is committed alongside the content change.
