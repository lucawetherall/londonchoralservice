# Value, Bespoke Care & On-Page SEO — Design Spec

**Date:** 2026-08-18
**Status:** Approved design (brainstorm complete) → ready for implementation plan
**Scope:** Two phases, delivered in order. Phase 1 (conversion) first, Phase 2 (on-page SEO) second.

## Problem / goal

The site is SEO-mature — the obvious audit wins are done (canonical/hreflang/OG, schema, complete sitemap, `llms.txt`, deep music-guide + area-page content, multi-channel enquiry). The next tier of improvement is not fixing basics; it is **conversion**, plus a short list of **genuine on-page SEO gaps**.

The owner's own thesis, adopted as the spine of this work:

1. **Make the price feel like better value** — the value is real but buried in prose; nothing packages it where a skim-reader sees it.
2. **Show the bespoke care each client gets** — the personal, hand-held service is described in paragraphs, never dramatised as a visible sequence.

Both traffic and conversion matter roughly equally to the owner, across **all four service lines** (funerals, weddings, corporate, Christmas). The work is therefore **site-wide and systemic** (shared components lifting every funnel), not a single-service campaign.

## Constraint that shapes everything: no usable analytics

The owner has no usable GA4 / Search Console / enquiry data to hand. Consequences:

- We **cannot** run rigorous CRO experiments; changes must be **best-practice-driven**, high-confidence, and grounded in how people buy emotional, personal services.
- A **lightweight measurement baseline** (GA4 conversion events) is a strongly recommended fast-follow so this work can eventually be judged. It is **out of scope here** (see W3, below) to keep this spec focused, but it should be the next spec.

## Positioning steer (from the owner)

- **Handpicked, elite, matched per engagement** — deliberately **not** the big-roster pitch competitors use. A headcount claim ("150+ musicians") is off-message and must not be used as a trust signal.
- Led by **Artistic Director Luca Wetherall (Tutor in Music, University of Oxford)**, who consults on music choices and handpicks the team.
- This positioning is **already consistent with existing structured data**: `about.html`'s `Person` node describes Luca as "Tutor in Music at the University of Oxford. Handpicks every singer and instrumentalist for The London Choral Service." Making these credentials *visible* (Phase 1) reinforces authority signals that until now lived only in the markup.

## Current state — what already exists (do NOT rebuild)

Verified during the brainstorm:

- **Enquiry mechanism:** multi-channel and working — Web3Forms contact form (hCaptcha + honeypot), phone, WhatsApp. No new mechanism needed.
- **Pricing:** flat, all-in, "no hidden fees" FAQ already on `pricing.html`; value cues already in prose (e.g. "Most families spend more on flowers than on the singer who carries the whole service").
- **E-E-A-T / entity:** `Person` schema for Luca in `about.html`; author `Person` schema **and** visible bylines ("By Luca Wetherall, Artistic Director & Tutor in Music, University of Oxford") on the music guides. **This is done — no entity rebuild.**
- **FAQ schema:** present on `corporate.html`, `christmas.html`, `pricing.html`, `services.html`.
- **Content + technical:** ~48 music guides, 20 city + 33 borough area pages, hand-maintained `sitemap.xml` + `llms.txt` (151 lines), disciplined meta/canonical/hreflang/OG.

## Solution overview

**Phase 1 (W1) — a "value + bespoke care" component system.** Two reusable components deployed across the money pages, built to fit the partials/`build.sh` pipeline. Plus a small policy-safe conversion add (testimonial quotes).

**Phase 2 (W2) — close the verified on-page SEO gaps.** FAQ schema hole on the two biggest money pages, a consolidated FAQ hub, an internal-linking audit, and per-service social images.

**A decision, recorded:** ratings/reviews handled the **policy-safe** way — **no `AggregateRating` schema**.

---

## Phase 1 (W1): Value & bespoke-care components

Two components only. (Earlier candidates — a value-anchor callout and a "trust band" — were cut during design.) Copy below is final and stop-slop-clean; it is the source text for implementation. Re-run the `writing-site-copy` skill on any further edits.

### Component A — Value block: "Included with every booking"

Turns a price into a package. Every line is already true on the site; the component's job is to make them visible at a glance, led by the two differentiators.

**Heading:** Included with every booking
**Sub:** One flat price, and a team chosen for your occasion.

**List:**
1. A one-to-one music consultation with our Artistic Director, Luca Wetherall (Tutor in Music, University of Oxford), who plans your repertoire with you.
2. A handpicked ensemble, matched to your occasion. We choose every singer for you, never send whoever is free from a rota.
3. All rehearsals, preparation, and sheet music.
4. **[per-service coordination line — see table]**
5. A written quote, confirmed before you commit. No hidden fees.

**Price line:** [per-page lead price], all in. Travel within Greater London included.

**Per-service variants** (item 4 + price line). Prices are cited from `pricing.html`, the single source of truth:

| Page | Item 4 (coordination) | Price line lead |
|---|---|---|
| `funerals.html` | We coordinate with your venue and funeral director. | From £250 for a solo singer |
| `weddings.html` | We coordinate with your venue, celebrant, and wedding planner. | From £1,150 for a small choir of four |
| `corporate.html` | We coordinate with your venue and event organiser. | From £1,150 for a small choir of four |
| `christmas.html` | We coordinate with your venue or office. | From £1,150 for a small choir of four |
| `services.html` | We coordinate with your venue, funeral director, or wedding planner. | From £250 for a soloist |
| `pricing.html` | We coordinate with your venue, funeral director, or wedding planner. | *(omit — the price table is adjacent)* |

### Component B — Care strip: "We take the whole thing off your hands"

A four-step sequence that dramatises the hand-held service. Identical on every page → implemented as a single partial (one source of truth).

**Heading:** We take the whole thing off your hands
**Sub:** From your first message to the last note.

| Step | Heading | Detail |
|---|---|---|
| 1 | You get in touch | A message, a call, or WhatsApp. Just the date and the occasion. |
| 2 | We plan the music | Luca chooses the voices and repertoire with you. |
| 3 | We do the rest | Rehearsals, sheet music, and coordination with your venue. |
| 4 | You just listen | We arrive early, set up quietly, and sing. |

### Placement map

| Page | Value block (A) | Care strip (B) |
|---|---|---|
| `pricing.html` | ✅ beside the price tables | ✅ **absorbs** the prose "What happens next" section (same intent, now visual). Preserve its specific facts as adjacent copy — same-day confirmation for funerals, and no travel costs within London — don't drop them |
| `funerals.html` | ✅ | ✅ |
| `weddings.html` | ✅ | ✅ |
| `corporate.html` | ✅ | ✅ |
| `christmas.html` | ✅ | ✅ |
| `services.html` | ✅ | ✅ |
| `index.html` | ➖ (homepage kept lighter) | ✅ between "Who we are" and "What families tell us" |

### Testimonial quotes on money pages (policy-safe conversion add)

From the ratings decision: distribute **real, existing** testimonial pull-quotes onto the money pages that lack one, reusing the existing `.pull-quote` pattern. One quote per page, not a wall. **Only quotes already on the site** (e.g. Pamela/Richmond, Tony/Battersea on `pricing.html`; Margaret/Dulwich on area pages) or new ones the owner supplies — never invented. This is content, not schema.

### Build mechanics (fits the existing pipeline)

Load the **build-and-verify** skill before starting.

1. **Component CSS** → add `.included-list` and `.care-steps` (+ responsive rules) to `css/components.css`. Run `./build.sh` to inline site-wide. Never hand-edit generated `<style>` blocks or `css/style.css`.
2. **Care strip (B)** → new `partials/care-strip.html` with `@include-start`/`@include-end` markers; placed on the 7 pages via the standard include, expanded by `build.sh`. Never hand-edit content between include markers.
3. **Value block (A)** → per-page HTML using the shared classes, with the per-service copy above. (Per-page rather than a partial because item 4 and the price line vary by service; the *reused* parts are the CSS pattern and the copy template.)
4. **Testimonial quotes** → per-page `.pull-quote` blocks, existing quotes only.
5. Run `./build.sh` (expect the ~106-file inlining diff); update `<lastmod>` in `sitemap.xml` for every edited page.
6. All copy passes `writing-site-copy`. No new schema in Phase 1. No rating/review markup anywhere.

---

## Phase 2 (W2): On-page SEO gaps

Verified gaps only — no busywork, no re-doing done work.

### W2a — Close the FAQPage-schema hole (highest-value, lowest-risk)

`funerals.html` and `weddings.html` — the two biggest money pages — have **no `FAQPage` schema**, while corporate/Christmas/pricing/services do. Add a visible FAQ section (3–8 Q&A) + matching `FAQPage` JSON-LD to both, following the pattern already used on the other money pages.

- Questions must be user-visible (Google requirement) and the visible text must match the schema answer text exactly.
- **Dedupe site-wide** (per R10 discipline): no question string may appear in two pages' `FAQPage` schema. Verify with the R10 script.

### W2b — FAQ hub (`/faq.html`)

Does not exist. A consolidated hub aggregating the best long-tail questions, linked from the footer. Use the **new-page** skill.

- **Dedupe against per-page FAQs** — do not emit the same Q&A `FAQPage` schema on both the hub and a service page (splits the rich-result signal). The hub either curates *different* questions or carries no `FAQPage` schema on overlapping ones.
- Update `sitemap.xml` (new `<url>` + lastmod) and `llms.txt`.

### W2c — Internal-linking audit → money pages

Audit whether the ~48-guide content layer funnels commercial-anchor inbound links into the service / pricing / area pages; add contextual links where thin. Judgement-based, low risk. Prior internal-linking work exists (PR #79) — **audit before adding**, don't re-link what's already linked.

### W2d — Per-service OG / social images  `[BLOCKED-ON-HUMAN]`

All ~106 pages share one generic `assets/og-image.png`. Per-service images (funerals, weddings, corporate, Christmas + major hubs) would lift social CTR. **Image assets are human-supplied**; the wiring (`og:image` / `twitter:image` per page + correct dimensions) is agent work once assets land in `assets/`. Ships when the owner provides images.

---

## Ratings & reviews — decision (recorded)

**No `AggregateRating` / `Review` / star-rating schema.** Confirmed with the owner during this brainstorm; consistent with `CLAUDE.md` and roadmap R1.

Rationale: a business marking up its own rating about itself is self-serving markup — Google ignores it (no stars) and it risks a "spammy structured markup" manual action against the site's *other* rich results. The legitimate paths to stars are third-party: **Google Business Profile** reviews (stars in Maps/local pack from Google's own data) and/or a third-party review platform (Trustpilot/Reviews.io) that emits its own schema. Both require genuine collected reviews.

**Chosen approach:** policy-safe. Add visible testimonial quotes for conversion now (W1); pursue real GBP reviews as a **human task** (track in `MANUAL-ACTIONS-REQUIRED.md`). A third-party review platform is a possible separate future project, not in this spec.

## Success criteria

No analytics baseline exists, so criteria are output- and validation-based, with an outcome check deferred until measurement (W3) lands:

- **Phase 1:** value block live on 6 pages (correct per-service copy + prices matching `pricing.html`); care strip partial live on 7 pages; `pricing.html` "What happens next" prose absorbed into the care strip without losing its specific facts (same-day funeral confirmation; no London travel cost) and without duplicating the sequence; one real testimonial quote on each money page; `./build.sh` green; JSON-LD still validates (`python3 validate_jsonld.py`); no rating/review schema introduced; all copy passes `writing-site-copy`.
- **Phase 2:** `funerals.html` + `weddings.html` carry valid `FAQPage` schema with visible, matching Q&A; every `FAQPage` question string is unique site-wide (R10 script → "unique"); `/faq.html` live, footer-linked, in `sitemap.xml` + `llms.txt`, with no duplicate FAQ schema; internal-link audit completed with gaps filled.
- **Deferred outcome check (post-W3):** once GA4 conversion events exist, watch enquiry rate from money-page and guide traffic.

## Out of scope

- **W3 — measurement baseline** (GA4 conversion events on form submit + WhatsApp/tel clicks; read Search Console once). **Strongly recommended as the next spec** so this work can be judged, but not part of this one.
- **AggregateRating / any rating or review schema** (decided against — see above).
- Third-party review-platform integration (possible future project).
- New JavaScript, new enquiry mechanisms, email capture/newsletter, paid ads, CSS-framework or site redesign.
- Cookie consent / Consent Mode (roadmap R4, separate SPEC-FIRST item).
- Net-new commercial content / new area pages (coverage is already deep; not the marginal win).

## Open decisions / to confirm at review

- **Luca's title wording** — spec uses "Artistic Director" + "Tutor in Music, University of Oxford", matching the existing guide bylines and `about.html` schema. Confirm this is the exact form to use.
- **"UK-wide / cathedral tradition" style claims** were dropped from the components (they lived only in the cut trust band); no unverifiable claim is introduced. Confirm nothing further needs a proof source.
- **Homepage** deliberately receives only the care strip, not the value block, to keep it light. Confirm that's the desired split.
