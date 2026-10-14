# Cookieless Ad Attribution Implementation Plan

**Status:** Approved, 14 Oct 2026 (owner, live in chat). Built in one session in the worktree `.claude/worktrees/cookieless-ad-attribution`.

**Goal:** Learn which enquiries came from Google Ads when the visitor declined cookies. Two ways: an ad-visit tag taken from the landing URL, and an optional ad-measurement checkbox on every enquiry form that lets a booking go to Google with a hashed email.

**Architecture:** Front end: `partials/analytics.html` (shared helpers), `js/form.js`, `js/private-events.js`, `js/consent.js`, CSS sources, and the form markup on 16 main-site pages, `private-events.html` and the register generator. Back end: `scripts/bookings/pipeline.py` and `scripts/ads/upload_bookings.py`, the weekly report's ledger line, and the agent prompts and docs.

**Spec:** [docs/superpowers/specs/2026-10-14-cookieless-ad-attribution.md](../specs/2026-10-14-cookieless-ad-attribution.md).

---

## Read this before starting

- Load `build-and-verify`, `writing-site-copy` and `stop-slop`. Never hand-edit an inlined `<style>` block or marker regions; edit `css/*.css`, `partials/*` and the generators, then `./build.sh`.
- Destination pages, the destinations hub and `planners-and-venues.html` come from `scripts/build_register_page.py` via the generators: edit the scaffold, rerun the generators, and `tests/test_register_generators.py` must pass.
- Change nothing in Google Ads, GA4, Zoho or `~/lcs-private`. Never run `upload_bookings.py --apply`.

## File structure

| File | Change | Task |
|---|---|---|
| `partials/analytics.html` | `LCS_AD_VISIT`, `lcsAdVisitSlug`, `lcsAdVisit`, `lcsClickIds`; WhatsApp/email tag | 1 |
| `js/form.js`, `js/private-events.js` | `ad_visit`; click IDs with a ticked box | 2 |
| `css/components.css`, `partials/private-register.css.html` | `.form-check` and `.pe-check-label--consent` | 3 |
| 14 `.contact-form` pages, `private-events.html`, `scripts/build_register_page.py` (+ generated pages) | Unticked `ad_measurement` checkbox | 3 |
| `js/consent.js` | Neutral sheet wording on register pages | 4 |
| `privacy.html` | Both features, `#ad-measurement`, date | 4 |
| `scripts/bookings/pipeline.py`, `tests/test_pipeline.py` | `ad_visit` / `ad_measurement` → notes | 5 |
| `scripts/ads/upload_bookings.py`, `tests/test_upload_bookings.py` | `consent` = `form`; email-only events | 6 |
| `scripts/reports/weekly_review.py` | Ledger line: box-ticked count | 6 |
| `tests/test_ad_attribution.py` | New: slug, storage, markup, script contract | 7 |
| `.claude/agents/lcs-reply-drafter.md`, `lcs-review-bookings.md`, handover Appendix A, `CLAUDE.md` | Record and report both | 8 |

### Task 1: Shared helpers in the analytics partial
- [x] `lcsAdVisitSlug(path)`: strip `/`, `.html`, `index`; `''` → `home`; anything outside `[a-z0-9/-]` → `other`.
- [x] `LCS_AD_VISIT` computed once from `location.search`; `lcsAdVisit()` returns it only without `granted` consent.
- [x] `lcsLabelMessage`: with no Ref, append `Ad visit: <slug>` (WhatsApp text and email body).

### Task 2: Form scripts
- [x] `form.js`: after the consented attribution merge, `data.ad_visit = lcsAdVisit()` when set; with `ad_measurement` ticked and no consent, add click IDs from `lcsClickIds()` (URL only).
- [x] `private-events.js`: the same, on the data object after `FormData`.

### Task 3: Checkbox markup and styles
- [x] `.form-check` (main site) and `.pe-check-label--consent` (register) styles; build.
- [x] Insert the checkbox before `.h-captcha` on every form by script (counted: 14 + 1), and in the scaffold; rerun `gen_country_pages.py`, `gen_destinations_index.py`, `gen_planners_page.py`.

### Task 4: Copy
- [x] Privacy paragraphs and the register banner wording (writing-site-copy + stop-slop).

### Tasks 5–6: Scripts and tests
- [x] Pipeline keys, slug check, notes; tests.
- [x] Upload rule, `ec_for_leads` check for email-only events; tests; weekly line.

### Task 7: Contract test
- [x] `tests/test_ad_attribution.py` (node for the slug; static checks for storage and markup).

### Task 8: Prompts and docs
- [x] Drafter steps 2, 3.iv, 4; review-bookings steps 3, 9; Appendix A cross-check; CLAUDE.md one line.

### Verification
- `./build.sh`; `python3 tests/test_stage_site.py`; `.venv/bin/python tests/test_register_generators.py`; the touched tests.
- Browser on `python3 -m http.server`: the four checks in the spec. The form is never submitted to Web3Forms.
