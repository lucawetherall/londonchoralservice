# Automation Phase 3 (Marketing economics) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Monday report three read-only sections:
- 11, true cost per booking: season spend, enquiries, bookings and £ booked by campaign;
- 12, seasonal budget rules: dated windows turned into budget proposals, never above £5/day;
- 13, a Search Console shortlist: hiring-intent queries at positions 8–20, each with one page and one fix.

**Architecture:** Pure functions go in a new `scripts/reports/economics.py`. `weekly_review.py` makes every Google call (GAQL `search` and Search Console `searchAnalytics.query`, both read-only) and prints the sections. Each new section sits in its own try/except and prints only the exception's type name, so one failure never stops the report. The owner edits the budget windows in `data/budget-windows.yml`. Two private files are written in `~/lcs-private/` (mode 600): `gclid-campaigns.json`, a cache so each gclid is looked up once, and `ads-summary.json` for the Phase 5 dashboard.

**Tech Stack:** Python 3 in the repo's `.venv` (google-ads, google-auth, PyYAML). The tests are a stdlib script with no network access.

**Spec:** [docs/superpowers/specs/2026-09-28-business-automation-design.md](../specs/2026-09-28-business-automation-design.md), Phase 3, features 11–13.

---

## Read this before starting

- **Read-only against Google.** The report never mutates Ads, GA4 or Search Console. A `PROPOSE:` line is a suggestion for the Monday approval question. An approved change goes through `scripts/ads/` as usual: validate_only first, then apply, then log.
- **The £5 cap.** `proposals()` never proposes more than £5/day. A window above £5 prints `CONFIG ERROR: … capped at £5.00`.
- **Targeting.** The shortlist drops "singer" (singular), solo, soloist and vocalist queries, per the 26 Sep targeting decision. "singers" stays in.
- **No names.** Section 11 prints campaign names and totals only. It prints no client names, emails or booking refs.
- **Tests** point `LCS_PRIVATE_DIR` and `LCS_BOOKINGS_CSV` at a temp directory before importing.

## File structure

| File | Responsibility |
|---|---|
| Create `scripts/reports/economics.py` | `attribute`, `season_bookings`, `season_enquiries`, `cost_table`/`cost_lines`, `full_weeks`/`week_buckets`/`ads_summary`, `load_windows`/`in_window`/`proposals`/`proposal_lines`, `hiring_intent`/`main_term`/`shortlist`/`shortlist_lines`/`page_h2s_from`, `is_first_monday`, `gsc_window`, and private JSON read/write |
| Create `data/budget-windows.yml` | `season_start` and the seeded windows (owner-edited proposals) |
| Modify `scripts/reports/weekly_review.py` | `ads_query()` shared runner; sections 11–13; `--gsc-shortlist` |
| Create `tests/test_economics.py` | Attribution and caching, cost maths, week bucketing, proposals, shortlist |

## What was built

### Task 1: Tests first (`tests/test_economics.py`)

- [x] Attribution: `attribute()` walks back from the enquiry date and stops at the first hit. It caches hits and misses, so each gclid is looked up once, and never caches a failed lookup. `gbraid:`/`wbraid:` refs and blank gclids are unattributed without any query. It skips future dates and dates older than click_view's 90 days.
- [x] Bookings in the season: only rows invoiced on or after `season_start`, and not those whose notes match `\bcancell?ed\b`. Enquiries count by `first_seen`.
- [x] Cost maths: per campaign, the unattributed line and the total. A zero divisor gives "–". With no pipeline sheet, the enquiry figures are "–" and never "None".
- [x] Weeks: the last 8 full Monday–Sunday weeks. Empty weeks are filled in, and today's partial week is ignored.
- [x] Budget windows: windows that wrap the new year, the proposals on 28 Sep and 1 Oct, the £5 cap and its config error, bad MM-DD dates, overlapping windows and an enabled campaign in no window. The seed file loads, and none of it goes over £5.
- [x] Shortlist: "singers" is kept and "singer" dropped. Positions run 8–20 inclusive, with at least 20 impressions. Pages are merged per query, and the main page is the one with the most impressions. The three fix rules work, the main term skips generic words and numbers, and h2s are read from the local page with path traversal refused.

Run: `.venv/bin/python tests/test_economics.py`

### Task 2: `economics.py` and `data/budget-windows.yml`

- [x] The pure functions above. `proposals(campaigns, windows, today)` returns error, propose and note items. `proposal_lines()` prints the config errors first, then the `PROPOSE:` lines, then "budgets match the season's windows" when there's nothing to change.
- [x] `shortlist(rows, h2s=None)` takes Search Console rows (keys `[query, page]`). The "today" part of the section lives in `gsc_window(today)`, the last 28 days to 3 days ago, and `is_first_monday(today)`, so the filter itself doesn't depend on the date.
- [x] The seed windows: carols 10-01..12-20 £5; carols-off 12-21..09-30 £1; weddings-peak 01-02..04-30 £5; weddings-base 05-01..01-01 £3; funerals all year £3; `season_start: 2026-09-01`.

### Task 3: Wire into `weekly_review.py`

- [x] **Section 11:**
  - season spend and clicks by campaign;
  - bookings from `lcs_money.LEDGER`, attributed with the `click_view` query one date at a time (memoised per date within a run), with the cache saved even if a lookup fails;
  - enquiries from `~/lcs-private/enquiries.csv` if it exists, otherwise "enquiries: pipeline sheet not set up yet";
  - writes `ads-summary.json`: `{"generated", "weeks": [{week_start, spend_gbp, clicks, conversions}], "season": {start, campaigns, unattributed, total}}`.
- [x] **Section 12:** `campaign_budget.amount_micros` and the status of every campaign that isn't removed. Only ENABLED campaigns get proposals.
- [x] **Section 13:** runs on the first Monday of the month or with `--gsc-shortlist`. It makes one `searchAnalytics.query` call (query × page, 28 days, rowLimit 5000) and reads the h2s from the repo's copy of each page.

### Task 4: Live check (28 Sep 2026)

- [x] `weekly_review.py --gsc-shortlist` ran end to end: sections 1–13, exit 0, no section failed.
- [x] Section 11: £317.83 spent since 1 Sep. The one season booking has no ad click reference, so it's unattributed. There's no pipeline sheet yet.
- [x] Section 12 proposed three changes from the seed windows: funeral £4 → £3, wedding £4 → £3, and Christmas £5 → £1. The Christmas proposal comes from carols-off, which runs to 30 Sep, two days before the carols window. **The owner should check the seed windows before Appendix A is wired**, or the first Monday run will put these three proposals in the approval question.
- [x] Section 13: two queries. "funeral singers near me" → best-funeral-singers-london (no h2 mentions "funeral", so the fix is "add a section"), and "9 lessons and carols readings" → nine-lessons-and-carols (position 9.2, so the fix is "add an internal link").

### Task 5: Wire the Monday review (not done here: the handover doc is being edited elsewhere)

- [ ] Paste the text below into Appendix A of `docs/HANDOVER-2026-09-27-ads-analytics.md` and into the "Weekly marketing review" scheduled task. Allowlist `.venv/bin/python scripts/reports/weekly_review.py --gsc-shortlist` if prompts appear.

**1. In SET-UP, replace the "Sections:" sentence with:**

```text
Sections: 1 campaigns (last 7 days and since 26 Sep 2026), 2 search terms with matched keywords, 3 conversions per action, 4 ads with Google's ad-strength advice, 4b Google's open recommendations, 5 GA4 lead events and channels, 6 Search Console queries and pages, 7 Search Console coverage (sitemap freshness, index status of every ad landing page), 8 tracking wiring (live tags and conversion labels, Ads settings, GA4 key events and links), 9 bookings ledger (counts only), 10 money (totals only), 11 true cost per booking by campaign over the season, 12 seasonal budget proposals from data/budget-windows.yml, 13 Search Console shortlist (first Monday of the month only; the report says when it next runs).
```

**2. Add these steps to EACH RUN, after step 6:**

```text
6g. Marketing economics (section 11): give season spend, enquiries, bookings, £ booked, cost per enquiry and cost per booking for each campaign, plus the unattributed and total lines, exactly as printed ("–" means nothing to divide by). If "pipeline sheet not set up yet" shows, say so in one line. Never add names or booking refs.
6h. Seasonal budgets (section 12): each "PROPOSE: <campaign> £a → £b/day (window <name>)" line becomes one Ads change set in the approval question: campaign budget → amount: £a → £b/day, reason "seasonal window <name> (data/budget-windows.yml)". Write the change as a scripts/ads/ script in the worktree and run it validate-only. Never propose more than £5/day. If the report prints "CONFIG ERROR", report it and propose no change for that window; the owner fixes data/budget-windows.yml. From 5 Oct, step 7's Christmas budget call takes precedence over the carols window for the Christmas campaign.
6i. Search Console shortlist (section 13, first Monday of the month): list each query → page, position, impressions and the suggested fix. Turn each into a proposed page fix in the change list ("<page>: <fix>"). Don't write the copy: a fix is drafted on a branch only after the owner approves, under the writing-site-copy and stop-slop skills, and it never targets singular "singer", solo or soloist searches.
```

**3. In REPLY FORMAT, after the bookings line, add:**

```text
- An economics block: section 11's per-campaign lines, then section 12's proposals (or "budgets match the season's windows"), then, on the first Monday of the month, section 13's shortlist.
```

**4. In REPLY FORMAT, add to the numbered proposed changes:** budget proposals from 6h, as Ads change sets, and page fixes from 6i, as site changes. Both go in the same single approval question.

## Self-review

- **Spec coverage:** feature 11 is Tasks 1–3 (section 11 and `ads-summary.json`), feature 12 is section 12 plus the YAML, and feature 13 is section 13. The spec's step of drafting shortlist fixes as a branch is left to the Monday task after approval (step 6i).
- **Safety:**
  - no mutate call anywhere (`ads_query()` exposes `search` only);
  - the £5 cap is enforced in `proposals()` and tested;
  - private files are mode 600 via `save_json_private`;
  - error lines print type names only.
- **Known gaps:**
  - Enquiries need Phase 2's `enquiries.csv`, with `first_seen` and `gclid` columns.
  - Google keeps `click_view` for only 90 days. A gclid whose enquiry is older than that stays unattributed, and the miss is cached.
