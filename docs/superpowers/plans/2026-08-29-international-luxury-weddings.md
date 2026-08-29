# International and Destination Wedding Engagements — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Load `build-and-verify` and `new-page` before starting; their constraints go into every phase brief. Load `writing-site-copy` **and** `stop-slop` before drafting or auditing any visible text.

**Goal:** Send qualified international and destination wedding enquiries to `/private-events.html`, which currently receives in-copy links from exactly two pages. Four workstreams: one music-guide (A), one planners-and-venues page (B), eighteen guide cross-links (C), and a four-country destinations section (D). Metric: cost per qualified enquiry, per page.

**Architecture:** The private register's stylesheet and footer move into partials so six pages share one source of truth; the existing partial-expansion pass makes this work with **no change to `build.sh`**. Four new destination pages plus two other new pages, each carrying the register's scoped styles by include. No nav change, so the diff is ~25 files, not ~130.

**Tech Stack:** Static HTML + the existing `build.sh` pipeline (partial expansion, CSS inlining, `generate_llms_full.py`, `validate_jsonld.py`, `validate_competitor_claims.py`, `validate_house_claims.py`), Web3Forms + gtag on the client, Chromium/Playwright for visual review. No framework, no CI.

**Spec:** [docs/superpowers/specs/2026-08-29-international-luxury-weddings-design.md](../specs/2026-08-29-international-luxury-weddings-design.md)

---

## Read this before starting

- **The Pass A defence now lives in a partial and protects six pages, not one.** `partials/private-register.css.html` opens its `<style>` block with a comment line; that comment is the only thing stopping build.sh Pass A (build.sh:84–96) replacing the whole register with the site bundle. No page in the register may ever contain a `style.css` link. The idempotency check in Phase 6 is the tripwire.
- **Partial expansion runs before Pass A** (build.sh:27–63 vs 75–112). That ordering is what makes the partial approach work; do not reorder the passes.
- **Sequencing is not optional.** `generate_llms_full.py` walks `sitemap.xml` `<loc>` entries and **fails the build** on a sitemap entry whose file is not on disk. Page files first, sitemap second, build third.
- **New directory, new globs.** `validate_jsonld.py` (lines 10–14) and `validate_house_claims.py` (the `FILES` tuple) both enumerate directories explicitly. `destinations/` is not in either. Add it to both, or the new pages ship unvalidated.
- **House-claims traps.** Voicings as words (Eight / Twelve / Sixteen / Twenty-four), never digits; no "roster"; "luxury hotels" never "five-star"; no VAT wording; no "over 150"; "elite" banned in this register.
- **The doorway-page test is a ship gate, not advice.** ≥60% unique body copy per destination page, country-specific answers rather than synonyms. Three good destinations beat four templated ones — drop one rather than pad it.
- **Claim nothing we have not done.** No invented venues, clients or case studies. Capability and process only.

---

## Phase 1: Extract the private register into partials

The riskiest step, done first and alone so its diff is readable.

- [ ] **Step 1:** Create `partials/private-register.css.html` containing `private-events.html` lines 64–609 verbatim — the `<style>` block, **comment line first**, with the comment rewritten to say it now serves the whole private register and name this spec.
- [ ] **Step 2:** Create `partials/private-footer.html` from the hub's `<footer class="pe-footer">` block.
- [ ] **Step 3:** Replace both blocks in `private-events.html` with `@include-start` / `@include-end` marker pairs.
- [ ] **Step 4:** `./build.sh`, then inspect `git diff private-events.html`. **Expected: the include markers appear around otherwise byte-identical content.** Any other change means the extraction was not faithful — fix it here, before five more pages depend on it.
- [ ] **Step 5:** Pre-flight greps: no `style.css` reference in `private-events.html`; the comment line is the first inner line of the materialised `<style>`.

## Phase 2: Copy pack

Load `writing-site-copy` + `stop-slop`. Draft every visible string to a scratchpad file before any HTML exists. Python-count every meta description (141–161 chars).

- [ ] **Step 1:** Destination research pack — per country: rite and running order, sung language(s), building types and what they do to the voicing, travel and permit facts (A1, Schengen 90/180, ETIAS, per-country practice) with a **checked date** for anything time-sensitive. Anything uncertain is written as "ask us", never guessed.
- [ ] **Step 2:** Draft the four destination pages, the destinations index, `/planners-and-venues.html`, and `music-guides/destination-wedding-choir.html`.
- [ ] **Step 3:** Draft the eighteen guide cross-link sentences — **each written for the guide it sits in**, not one sentence eighteen times. Model: weddings.html:2404.
- [ ] **Step 4:** Draft titles, meta descriptions, OG/Twitter text, form microcopy, JSON-LD description strings, llms.txt lines.
- [ ] **Step 5:** Run the doorway test on the drafts: ≥60% unique body copy per destination page. Self-audit the whole pack against both skills and the banned-claims list.

## Phase 3: The private-register pages

Build order: index before country pages, so cross-links land on files that exist.

- [ ] **Step 1:** `destinations/index.html` — head per the `new-page` checklist, `theme-color` `#FAF6EE`, the two register partials by include, a bespoke header carrying a visible breadcrumb (Private Events › Destinations), four country cards, and the enquiry form with hidden `source_page`.
- [ ] **Step 2:** `destinations/italy.html`, `france.html`, `ireland.html`, `scotland.html` from the Phase 2 pack. Each: visible breadcrumb, country-specific body, enquiry form with its own `source_page`, budget bands **labelled as pounds sterling**.
- [ ] **Step 3:** `planners-and-venues.html` — same register, "Enquiring as" defaulting to planner, no voicing selector.
- [ ] **Step 4:** JSON-LD per page: `Service` (with `areaServed` as a `Country` node, `provider` → the existing `#organization`) + `FAQPage` (text verbatim from the rendered copy) + `BreadcrumbList` on the destination pages. No `AggregateRating`, no `Review`.
- [ ] **Step 5:** Confirm `js/private-events.js` is referenced and that element IDs match (`pe-enquiry`, `pe-form-success`, `ensemble-size`, `enquiring-as`, `date-flexible`, `hear`). **The JS itself is not edited** — it is already null-guarded for the optional voicing selector (js/private-events.js:56–64).

## Phase 4: The guide and the cross-links

- [ ] **Step 1:** `music-guides/destination-wedding-choir.html` via the `new-page` clone-an-exemplar workflow from an existing wedding guide. LCS register — normal nav/footer partials, site bundle, `weddings` category.
- [ ] **Step 2:** Register it in `music-guides/index.html` under the `data-category="weddings"` section, and in the related-guides blocks of two or three closely related wedding guides.
- [ ] **Step 3:** Add the eighteen per-guide cross-link sentences to the wedding guides' closing CTA or `related-guides` blocks. **Wedding guides only** — no funeral or Christmas guide.

## Phase 5: Wiring and validators — strict order

- [ ] **Step 1:** `validate_jsonld.py` — add `glob.glob('destinations/*.html')` to the `files` tuple.
- [ ] **Step 2:** `validate_house_claims.py` — add `glob.glob('destinations/*.html')` to `FILES`.
- [ ] **Step 3:** `sitemap.xml` — entries for all seven new pages (lastmod 2026-08-29), **only now that the files exist**; refresh `lastmod` on every page whose copy changed.
- [ ] **Step 4:** `llms.txt` — one line per new page in house format.
- [ ] **Step 5:** `private-events.html` — link the destinations index from the "Where do you travel?" answer, and `/planners-and-venues.html` from the planners-and-venues section.
- [ ] **Step 6:** `MANUAL-ACTIONS-REQUIRED.md` — a dated §14 with the owner actions listed at the foot of this plan.

## Phase 6: Build + idempotency

- [ ] **Step 1:** `./build.sh` — all four validators green.
- [ ] **Step 2:** Check the diff shape: **~25 files, no nav-marker hunks anywhere.** A ~130-file diff means something touched `partials/nav.html` or `css/` — stop and investigate.
- [ ] **Step 3:** `./build.sh` a second time. `git diff` across all six private-register pages must be **empty**. A non-empty diff means Pass A ate the register or Pass B inlined the site bundle — fix the page, never the build.
- [ ] **Step 4:** Grep the register for `style.css`: must return nothing.

## Phase 7: Five-lens review

Each lens run separately; every finding verified before fixing, then Phase 6 re-run.

- [ ] **D1 Build safety** — partial extraction fidelity, Pass A comment intact in the partial, no `style.css` in the register, idempotency, `css/` untouched.
- [ ] **D2 Copy/slop audit** — a fresh pass with `stop-slop` + `writing-site-copy` over every rendered string plus meta/JSON-LD/llms.txt: AI tells, house-rule breaches, banned claims, UK English. **Includes the doorway test** and a check that no page claims an engagement we have not performed.
- [ ] **D3 Accessibility + design** — WCAG 2.1 AA against the register's computed contrast table (no candle/limestone/naveStone as text; cassockRed focus rings), real labels, breadcrumb semantics, reduced-motion completeness.
- [ ] **D4 SEO/head/schema** — head block row-by-row against the `new-page` checklist; JSON-LD against the spec; sitemap/llms.txt wiring; canonical/hreflang/OG consistency; **no internal link from any `for-*.html` or `compare/` page into the register**.
- [ ] **D5 Visual + functional** — local server + Chromium at 390×844 and 1440×900. Drive each new form end to end: validation, honeypot, the under-five-seconds rejection, hCaptcha guard, inline success, `source_page` present in the payload, and no site-bundle styles leaking into the register.

## Phase 8: Graph refresh and commit

- [ ] **Step 1:** `/graphify --update`; commit `graphify-out/` alongside the content change.
- [ ] **Step 2:** Commit per house style (`feat(destinations): …`, `copy(music-guides): …`), push to `claude/intl-luxury-wedding-bookings-h2xiwg`, open a draft PR, subscribe to PR activity.

---

## Expected diff shapes

| Change | Expected shape |
|---|---|
| Phase 1 extraction + rebuild | `private-events.html`: include markers around **byte-identical** content. Nothing else. |
| Full change + rebuild | ~25 files. Seven new pages, eighteen guide edits, `music-guides/index.html`, `sitemap.xml`, `llms.txt`, two validators, `private-events.html`. |
| Second `./build.sh` | Empty diff across all six private-register pages (idempotency). |
| `llms-full.txt` | Regenerated — seven new sections; never hand-edited. |
| `css/style.css`, `css/*` | **Untouched.** The register lives in its partial and must never enter the site bundle. |
| `partials/nav.html` | **Untouched.** A nav diff here means the plan was not followed. |

## Outstanding owner actions (record in MANUAL-ACTIONS-REQUIRED.md §14)

1. **Confirm the destination capability claim** before launch: Italy, France, Ireland and Scotland are named because the hub's own FAQ already names them. Adding Spain, Greece or the Gulf needs the owner's confirmation first.
2. **Verify the travel and permit facts** in the destination pages against current guidance, and set the visible checked date. Re-check quarterly alongside the `compare/` pricing check.
3. **Google Ads:** a dedicated conversion action per destination page, and paid search on destination terms — the hub already carries a reserved H1 variant for wedding-targeted paid traffic (private-events.html:711–716).
4. **Photography or video from an actual overseas engagement.** The highest-value asset for this audience and the one thing here that cannot be written.
5. **Planner-network and luxury-directory outreach**, and wedding-press placement — now that there are pages to point at.
6. **Optional:** a one-page planner PDF built from `/planners-and-venues.html` in the LCS house-document style.

## Done when

- `./build.sh` exits 0 twice in a row with an empty diff across the private register between runs.
- All four validators green, with `destinations/` inside their globs; no banned claim survives a grep.
- The diff is ~25 files with no nav-marker hunks and no `css/` changes.
- Every destination page passes the doorway test, and no page claims an engagement we have not performed.
- All five review lenses report clean.
- `graphify-out/` is committed alongside the content change.
