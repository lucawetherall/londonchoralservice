# International and Destination Wedding Engagements — Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Load `build-and-verify` and `new-page` before starting; their constraints go into every phase brief. Load `writing-site-copy` **and** `stop-slop` before drafting or auditing any visible text.

**Goal:** Send qualified international and destination wedding enquiries to `/private-events.html`, which currently receives in-copy links from exactly two pages. Four workstreams: one music-guide (A), one planners-and-venues page (B), cross-links from every guide in the music-guides weddings category (C), and a `/destinations/` section covering twenty-two countries (D). Metric: cost per qualified enquiry, per page.

**Architecture:** The private register's stylesheet and footer move into partials so twenty-five-plus pages share one source of truth; the existing partial-expansion pass makes this work with **no change to `build.sh`**. Country pages carry their regions as anchored sections; region pages are a later phase on the `areas/london/` precedent. No nav change at any point.

**Tech Stack:** Static HTML + the existing `build.sh` pipeline (partial expansion, CSS inlining, `generate_llms_full.py`, `validate_jsonld.py`, `validate_competitor_claims.py`, `validate_house_claims.py`), Web3Forms + gtag on the client, Chromium/Playwright for visual review. No framework, no CI.

**Spec:** [docs/superpowers/specs/2026-08-29-international-luxury-weddings-design.md](../specs/2026-08-29-international-luxury-weddings-design.md)

---

## Delivery: four shipments, not one

Twenty-five-plus hand-authored pages in one pull request is unreviewable. Ship in this order — Luca's priority order (guide → planners → cross-links → destinations), adjusted so each PR stands alone.

| PR | Contents | Rationale |
|---|---|---|
| **1** | Phase 1 partial extraction · hub copy fixes · `/destinations/index.html` · Workstream A guide · Workstream B planners page · Workstream C's eighteen cross-links | Everything high-yield that needs no country page. The index ships with the country list as its content, so the guide and the cross-links have a live target from day one. |
| **2** | Eleven Europe/short-haul country pages | Shortest travel-and-permit research; highest volume. Mostly rite-spine pages, but Greece and Cyprus straddle — the split is by haul, and each page picks its spine per the spec. |
| **3** | Eleven long-haul country pages | The heavy permit research, the United States especially. Mostly no-building pages, but the US, Mexico and the Caribbean carry rite material — again, haul decides the shipment, the spec decides the spine. |
| **4+** | Region pages, prioritised by market value | Luxury tier first: Lake Como, Amalfi, Tuscany, Côte d'Azur, Ibiza, Mallorca, Santorini. |

Phases 2 onward repeat per shipment. Phase 1 happens once, in PR 1.

---

## Read this before starting

- **The Pass A defence lives in a partial and protects every page in the register.** `partials/private-register.css.html` opens its `<style>` block with a comment line; that comment is the only thing stopping build.sh Pass A (the inlined-CSS restore pass — search `build.sh` for "Pass A") replacing the whole register with the site bundle. No page in the register may ever contain a `style.css` link. The idempotency check in Phase 6 is the tripwire.
- **Partial expansion runs before Pass A** — the include pass sits above the CSS passes in `build.sh`. That ordering is what makes the partial approach work; do not reorder the passes.
- **Sequencing is not optional.** `generate_llms_full.py` walks `sitemap.xml` `<loc>` entries and **fails the build** on a sitemap entry whose file is not on disk. Page files first, sitemap second, build third.
- **New directories, new globs.** `validate_jsonld.py` (its `files` tuple) and `validate_house_claims.py` (its `FILES` tuple) both enumerate directories explicitly. Add **both** `destinations/*.html` and `destinations/**/*.html` in PR 1, so the later region pages are covered without a second edit.
- **House-claims traps.** Voicings as words (Eight / Twelve / Sixteen / Twenty-four), never digits; no "roster"; "luxury hotels" never "five-star"; no VAT wording; no "over 150"; "elite" banned in this register.
- **The doorway-page test is a ship gate, not advice.** ≥60% unique body copy per page, country-specific answers rather than synonyms. Fifteen good destinations beat twenty-two templated ones — drop one rather than pad it.
- **Two page shapes, not one.** The rite spine and the no-building spine are different documents. See the spec; do not force one outline onto both.
- **The long-haul capability is owner-confirmed (2026-08-29)** and recorded in the spec. Do not strip those pages as over-claims. Everything else stays capability-and-process: no invented venues, clients or case studies.
- **Permit facts carry a visible checked date** and anything uncertain is written as "ask us", never guessed.

---

## Phase 1: Extract the private register into partials *(PR 1 only)*

The riskiest step, done first and alone so its diff is readable.

- [ ] **Step 1:** Create `partials/private-register.css.html` containing `private-events.html`'s hand-authored `<style>` block verbatim (the one opening with the Pass A comment — `grep -n 'bespoke scoped styles' private-events.html`), **comment line first**, with the comment rewritten to say it now serves the whole private register and to name this spec.
- [ ] **Step 2:** Create `partials/private-footer.html` from the hub's `<footer class="pe-footer">` block.
- [ ] **Step 3:** Replace both blocks in `private-events.html` with `@include-start` / `@include-end` marker pairs.
- [ ] **Step 4:** `./build.sh`, then inspect `git diff private-events.html`. **Expected: the include markers appear around otherwise byte-identical content.** Any other change means the extraction was not faithful — fix it here, before twenty-four more pages depend on it.
- [ ] **Step 5:** Pre-flight greps: no `style.css` reference in `private-events.html`; the comment line is the first inner line of the materialised `<style>`.

## Phase 1b: Bring the hub up to date *(PR 1 only)*

- [ ] **Step 1:** The hero footprint sentence — anchor `grep -n 'Europe, North America, and the Gulf' private-events.html`.
- [ ] **Step 2:** The "Where do you travel?" answer — anchor `grep -n 'Where do you travel' private-events.html`. **Point it at `/destinations/`; do not list twenty-two countries in an FAQ answer.** Update the matching `FAQPage` JSON-LD text verbatim.
- [ ] **Step 3:** The hub's Service `areaServed` — extend beyond `United Kingdom` plus a generic `International` place.
- [ ] **Step 4:** Extend the hub's budget bands to **Under £5,000 · £5,000–£10,000 · £10,000–£25,000 · £25,000–£50,000 · £50,000+ · Prefer to discuss**, labelled as pounds sterling. **"Under £5,000" stays, and stays first** — that was an explicit owner decision about the bottom band.

## Phase 2: Copy pack *(every PR)*

Load `writing-site-copy` + `stop-slop`. Draft every visible string to a scratchpad file before any HTML exists. Python-count every meta description (141–161 chars).

- [ ] **Step 1:** Research pack for this shipment's countries — rite and running order, sung language(s), building types and what they do to the voicing, permit and travel reality with a **checked date**, and the honest cost drivers. For no-building destinations: outdoor acoustics, heat and humidity, what a consort does at a civil ceremony.
- [ ] **Step 2:** Draft this shipment's pages, choosing the rite spine or the no-building spine per the spec. Greece, Cyprus, the United States and Mexico straddle both — handle the split inside the page.
- [ ] **Step 3 (PR 1):** Draft one cross-link sentence per guide under `data-category="weddings"` in `music-guides/index.html` (eighteen at the time of writing, `jerusalem.html` included — the list is the source of truth, not the number) — **each written for the guide it sits in**, not one sentence eighteen times. Model: the existing hand-off sentence — `grep -n 'private and international engagements' weddings.html`.
- [ ] **Step 4:** Titles, meta descriptions, OG/Twitter text, form microcopy, JSON-LD description strings, llms.txt lines.
- [ ] **Step 5:** Run the doorway test on the drafts: ≥60% unique body copy per page. Self-audit the whole pack against both skills and the banned-claims list.

## Phase 3: The private-register pages *(every PR)*

- [ ] **Step 1 (PR 1):** `destinations/index.html` — head per the `new-page` checklist, `theme-color` `#FAF6EE`, the two register partials by include, a bespoke header with a visible breadcrumb (Private Events › Destinations), the twenty-two countries grouped as in the spec, and the enquiry form with hidden `source_page`.
- [ ] **Step 2:** This shipment's `destinations/<country>.html` pages. Each: visible breadcrumb, country-specific body, **a real anchored section per named region**, enquiry form with its own `source_page`, six budget bands labelled as pounds sterling.
- [ ] **Step 3 (PR 1):** `planners-and-venues.html` — same register, "Enquiring as" defaulting to planner, no voicing selector.
- [ ] **Step 4:** JSON-LD per page: `Service` (with `areaServed` as a `Country` node, `provider` → the existing `#organization`) + `FAQPage` (text verbatim from the rendered copy) + `BreadcrumbList`. No `AggregateRating`, no `Review`.
- [ ] **Step 5:** Every new register page carries the full form scaffold the hub has, or the form silently fails:
  - the **Web3Forms client script** (`https://web3forms.com/client/script.js`) — it is what renders the hCaptcha widget from `<div class="h-captcha" data-captcha="true">`; without it the captcha never appears and Web3Forms rejects the post;
  - the **per-page GA4/Ads gtag snippet** — CLAUDE.md: duplicated per page, *never* a partial. Without it `window.gtag` is undefined and the enquiry conversion never fires, on the programme whose metric is cost per qualified enquiry;
  - **absolute asset paths.** The hub's favicon links are *relative* (`href="assets/favicon.ico"`) — copied into `destinations/` they 404. Convert to `/assets/...` in any head cloned from the hub.
- [ ] **Step 6:** Confirm `js/private-events.js` is referenced and element IDs match (`pe-enquiry`, `pe-form-success`, `ensemble-size`, `enquiring-as`, `date-flexible`, `hear`). **The JS itself is not edited** — already null-guarded for the optional voicing selector (`grep -n 'no mapped video' js/private-events.js` lands in the guarded block).

## Phase 4: The guide and the cross-links *(PR 1 only)*

- [ ] **Step 1:** `music-guides/destination-wedding-choir.html` via the `new-page` clone-an-exemplar workflow from an existing wedding guide. LCS register — normal nav/footer partials, site bundle, `weddings` category.
- [ ] **Step 2:** Register it in `music-guides/index.html` under the `data-category="weddings"` section, and in the related-guides blocks of two or three closely related wedding guides.
- [ ] **Step 3:** Add the per-guide cross-link sentences from Phase 2 — to `/destinations/` where the guide's subject suggests a destination, otherwise `/private-events.html`. **Wedding guides only.**

## Phase 5: Wiring and validators — strict order *(every PR)*

- [ ] **Step 1 (PR 1):** `validate_jsonld.py` — add `glob.glob('destinations/*.html')` and `glob.glob('destinations/**/*.html')` to the `files` tuple.
- [ ] **Step 2 (PR 1):** `validate_house_claims.py` — the same two globs in `FILES`.
- [ ] **Step 3:** `sitemap.xml` — entries for this shipment's pages, **only now that the files exist**; the destinations index uses the trailing-slash form (`https://londonchoralservice.com/destinations/`), matching `areas/` and `music-guides/` — `generate_llms_full.py` resolves trailing-slash URLs to `index.html`. Refresh `lastmod` on every page whose copy changed.
- [ ] **Step 4:** `llms.txt` — a `## Destinations` grouping rather than loose lines under Main Pages: created in PR 1 with its first entries, extended by each later shipment; one line per page in house format.
- [ ] **Step 5 (PR 1):** Link `/destinations/` and `/planners-and-venues.html` from the hub.
- [ ] **Step 6 (PR 1):** `MANUAL-ACTIONS-REQUIRED.md` — a dated §14 with the owner actions at the foot of this plan.

## Phase 6: Build + idempotency *(every PR)*

- [ ] **Step 1:** `./build.sh` — all four validators green.
- [ ] **Step 2:** Check the diff shape against the table below. **No nav-marker hunks anywhere.** A ~130-file diff means something touched `partials/nav.html` or `css/` — stop and investigate.
- [ ] **Step 3:** `./build.sh` a second time. `git diff` across every private-register page must be **empty**. A non-empty diff means Pass A ate the register or Pass B inlined the site bundle — fix the page, never the build.
- [ ] **Step 4:** Grep the register for `style.css`: must return nothing.

## Phase 7: Five-lens review *(every PR)*

Each lens run separately; every finding verified before fixing, then Phase 6 re-run.

- [ ] **D1 Build safety** — partial fidelity, Pass A comment intact, no `style.css` in the register, idempotency, `css/` untouched.
- [ ] **D2 Copy/slop audit** — `stop-slop` + `writing-site-copy` over every rendered string plus meta/JSON-LD/llms.txt. **Per page against a fresh reading, not per batch** — at this page count house-voice drift becomes invisible from inside. Includes the doorway test and a check that no page claims an engagement we have not performed.
- [ ] **D3 Accessibility + design** — WCAG 2.1 AA against the register's computed contrast table (no candle/limestone/naveStone as text; cassockRed focus rings), real labels, breadcrumb semantics, reduced-motion completeness.
- [ ] **D4 SEO/head/schema** — head block row-by-row against the `new-page` checklist; JSON-LD against the spec; sitemap/llms.txt wiring; canonical/hreflang/OG consistency; **no internal link from any `for-*.html` or `compare/` page into the register**.
- [ ] **D5 Visual + functional** — local server + Chromium at 390×844 and 1440×900. Drive each new form end to end: validation, honeypot, the under-five-seconds rejection, hCaptcha guard, inline success, `source_page` present in the payload, the hCaptcha widget actually rendering, `window.gtag` defined at submit time, and no site-bundle styles leaking into the register.

## Phase 8: Graph refresh and commit *(every PR)*

- [ ] **Step 1:** `/graphify --update`; commit `graphify-out/` alongside the content change.
- [ ] **Step 2:** Commit per house style (`feat(destinations): …`, `copy(music-guides): …`), push, open a draft PR, subscribe to PR activity.

---

## Expected diff shapes

| Change | Expected shape |
|---|---|
| Phase 1 extraction + rebuild | `private-events.html`: include markers around **byte-identical** content. Nothing else. |
| PR 1 | ~30 files: index, guide, planners page, the weddings-category guide edits, `music-guides/index.html`, `private-events.html`, two validators, `sitemap.xml`, `llms.txt`, two new partials, `MANUAL-ACTIONS-REQUIRED.md`. Plus the regenerated `llms-full.txt` and the `graphify-out/` refresh, both expected in every shipment. |
| PR 2 and PR 3 | ~14 files each: eleven country pages, `sitemap.xml`, `llms.txt`, `destinations/index.html` — plus the recurring `llms-full.txt` and `graphify-out/` refresh. |
| Second `./build.sh` | Empty diff across every private-register page (idempotency). |
| `llms-full.txt` | Regenerated each time; never hand-edited. |
| `css/style.css`, `css/*` | **Untouched.** The register lives in its partial and must never enter the site bundle. |
| `partials/nav.html` | **Untouched, in every shipment.** A nav diff means the plan was not followed. |

## Outstanding owner actions (record in MANUAL-ACTIONS-REQUIRED.md §14)

1. **Ireland and Scotland regions** — the only two countries in the list with no regions named. Set them before PR 2.
2. **Verify the permit and travel facts** in each shipment against current guidance, and set the visible checked date. Re-check quarterly alongside the `compare/` pricing check.
3. **United States lead times** — if P-visa petitions make US engagements impractical under six months, the US page says so plainly rather than implying a quick booking. Confirm before PR 3.
4. **Google Ads:** a dedicated conversion action for the destinations funnel, and paid search on destination terms — the hub already carries a reserved H1 variant for wedding-targeted paid traffic (`grep -n 'Hero H1 A/B alternatives' private-events.html`).
5. **Photography or video from an actual overseas engagement.** The highest-value asset for this audience and the one thing here that cannot be written.
6. **Planner-network and luxury-directory outreach**, and wedding-press placement — now that there are pages to point at.
7. **Optional:** a one-page planner PDF built from `/planners-and-venues.html` in the LCS house-document style.

## Done when (per shipment)

- `./build.sh` exits 0 twice in a row with an empty diff across the private register between runs.
- All four validators green, with `destinations/` inside their globs; no banned claim survives a grep.
- The diff matches the table above, with no nav-marker hunks and no `css/` changes.
- Every page passes the doorway test, and no page claims an engagement we have not performed.
- All five review lenses report clean.
- `graphify-out/` is committed alongside the content change.
