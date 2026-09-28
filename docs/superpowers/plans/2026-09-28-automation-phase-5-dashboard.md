# Automation Phase 5 (Owner's dashboard) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One private page that shows where the bookings and the money stand, without opening five tabs:
- upcoming events with their payment state;
- the Monday money lines, the hand-check list and unpaid singer invoices;
- the enquiry pipeline, the last 4 weeks' Ads spend and cost per enquiry;
- the bank balance.

**Architecture:** `scripts/reports/dashboard.py` has two halves. `gather(client, today)` reads the private files (and Starling through `lcs_money.StarlingReadOnly`, GET only) into a plain dict. `render(data)` turns that dict into one self-contained HTML page and nothing else, so tests drive it with fake data. It reuses `check_payments.collect`/`assess`/`received_since`, `money_report.summary_lines`/`hand_check_label` and `singer_invoices.summary`/`first_name`/`ring_first`; it adds nothing to `lcs_money`. The page is written atomically to `~/lcs-private/dashboard.html`, mode 600. The Monday review and the enquiry assistant's first run of each day regenerate it.

**Tech Stack:**
- Python 3 stdlib in the repo's `.venv`.
- Starling API v2, GET only (`/api/v2/accounts`, the IN feed, `/api/v2/accounts/{uid}/balance`).
- Tests are stdlib-only scripts in the repo's style: `.venv/bin/python tests/test_dashboard.py`.

**Spec:** [docs/superpowers/specs/2026-09-28-business-automation-design.md](../specs/2026-09-28-business-automation-design.md), Phase 5, feature 16.

---

## Read this before starting

- **The dashboard is a local file only.** Never publish, commit, attach, upload or paste it, and never print its contents in a transcript, PR or summary. The CLI prints one line: `dashboard written: <path>`.
- **No network from the page.** Inline CSS only: no fonts, CDNs, scripts, images or links. A `Content-Security-Policy` meta (`default-src 'none'; style-src 'unsafe-inline'`) blocks anything that slips through, so it works offline.
- **The bank is read-only.** Use the existing `StarlingReadOnly.get`, `account` and `feed`; add no methods to `lcs_money`. `--no-bank` reads neither the Keychain nor Starling.
- **Names and numbers.** Client and singer first names only; bank accounts only as `••••last4` (gather passes the last four digits and render trims whatever it's handed to four).
- **Every section stands alone.** Each is built in `gather` and rendered in `render` inside try/except. A failure shows `couldn't load (<TypeName>)`, never the message (it could carry private data), and the rest of the page still renders. Starling errors (`StarlingError`, `URLError`, `HTTPError`, `TimeoutError`, `OSError`, `JSONDecodeError`) mean "bank not checked", not a failure.
- **Branch and worktree.** Work in a worktree on `claude/phase-5-dashboard` from `origin/main`. Run everything with the main checkout's venv: `PY=~/Documents/GitHub/londonchoralservice/.venv/bin/python`. Tests set `LCS_PRIVATE_DIR` and `LCS_BOOKINGS_CSV` to a temp dir before importing anything.

## File structure

| File | Responsibility |
|---|---|
| Create `scripts/reports/dashboard.py` | `gather()`, `render()`, atomic `write()`, CLI `[--no-bank]` |
| Create `tests/test_dashboard.py` | Tests |
| Modify `.claude/settings.json` | Allowlist the two commands (Task 2) |
| Modify `docs/HANDOVER-2026-09-27-ads-analytics.md` | Appendix A (Monday review) and Appendix E (assistant) steps (Task 2) |
| Modify `CLAUDE.md` | One line in "Email and invoices" (Task 2) |

## Sections and their sources

| # | Heading | Source | Without the source |
|---|---|---|---|
| 1 | Upcoming events | `bookings.csv` rows with event_date ≥ today, not cancelled, soonest first: date, ref, client first name, occasion, ensemble, value £, payment state from `check_payments.collect` (a closed row reads "paid in full (closed)") | No token or Starling down: "bank not checked" plus the notes-only state from `assess(row, [], today)` |
| 2 | Money | `money_report.summary_lines` | Received line reads "bank not checked" |
| 3 | Needs a hand check | assessments in `money_report.HAND_CHECK`: ref, label, value £, received £ | Received reads "not checked" |
| 4 | Singer invoices unpaid | `singer-invoices.csv` rows with no paid_on: received, first name, £, payee status (never the payee's name), `••••last4`, a red badge when `ring_first`, an amber one when the change was confirmed by phone | "No unpaid singer invoices." |
| 5 | Pipeline | `enquiries.csv`: counts by status for the season (from 1 September) and the last 30 days; conversion = confirmed (confirmed, deposit paid, done) / quoted (those plus quoted, or any row with quoted_gbp) | "pipeline sheet not set up yet" |
| 6 | Ads | `ads-summary.json`: the 4 latest weeks' spend and clicks, newest first; with `enquiries.csv`, enquiries whose first_seen falls in each week and spend ÷ enquiries | "run the Monday review to fill this" |
| 7 | Bank balance | `GET /api/v2/accounts/{uid}/balance`: cleared and effective £ | "not checked" |

---

### Task 1: `dashboard.py` and its tests (done in this PR)

- [x] **Step 1: Tests first** (`tests/test_dashboard.py`):
  - `render()` with fake data for every section shows all seven headings and their values;
  - a `<script>` name is escaped;
  - no `http:`/`https:`, `//`, `src=`, `href=`, `url(` or `@import` in the page;
  - a store row holding a full account number yields only `••••` plus the last four, and no 8-digit run appears;
  - missing files give the placeholders;
  - a failing section (in `gather` or in `render`) shows `couldn't load (<TypeName>)` and the rest renders;
  - the file is mode 600 and no temp file is left;
  - `--no-bank` makes no Keychain read and no Starling call (fake client), while the same fake is used without it;
  - Starling errors give "bank not checked" and a "not checked" balance.
- [x] **Step 2: Implement** until `$PY tests/test_dashboard.py` prints `0 failure(s)`.
- [x] **Step 3: Live check** from the main checkout: `$PY <worktree>/scripts/reports/dashboard.py`, then check the mode (`stat -f %Lp` → 600), grep only the `<h2>` headings (all seven), and grep for `https?:|//|src=|href=|url\(|@import` (none). Print nothing else from the file.

### Task 2: Wire it into the scheduled tasks (after the PR is merged)

**Files:**
- Modify: `.claude/settings.json`
- Modify: `docs/HANDOVER-2026-09-27-ads-analytics.md` (Appendix A and Appendix E)
- Modify: `CLAUDE.md`
- Update: scheduled tasks `enquiry-assistant` and `christmas-carol-campaign-review` (via the scheduled-tasks tool, text copied from the appendices)

- [ ] **Step 1: Allowlist.** Add to `permissions.allow`, keeping the existing entries and the `deny` list:

```json
"Bash(.venv/bin/python scripts/reports/dashboard.py)",
"Bash(.venv/bin/python scripts/reports/dashboard.py --no-bank)"
```

- [ ] **Step 2: Appendix E, TOOLS list.** Add:

```text
  .venv/bin/python scripts/reports/dashboard.py
```

- [ ] **Step 3: Appendix E, step 6.** After 6b, add:

```text
   c. Run `.venv/bin/python scripts/reports/dashboard.py` (after 6a and 6b, so it shows the notes they wrote). It prints one line, "dashboard written: <path>". Never open, read, attach or copy the dashboard file. If it fails, note "dashboard failed" with the error's type name only.
```

- [ ] **Step 4: Appendix E, FINAL SUMMARY.** Add after the "Money to check by hand" bullet:

```text
- "dashboard updated" when step 6c ran (first run of the day only).
```

- [ ] **Step 5: Appendix A (Monday).** Append to step 6:

```text
   g. Run `.venv/bin/python scripts/reports/dashboard.py` after 6e, so the page shows this week's notes. It prints one line, "dashboard written: <path>". Never open, read, attach or copy the dashboard file.
```

  In REPLY FORMAT, change the bookings bullet to: `- A bookings line: new bookings recorded (count, total £), uploads ready (count), anything skipped and why, then section 10's money lines and "dashboard updated". No client or singer names.`

- [ ] **Step 6: CLAUDE.md.** In "Email and invoices (Zoho Mail)", add after the Payments bullet:

```text
- **Dashboard:** `scripts/reports/dashboard.py` writes `~/lcs-private/dashboard.html` (mode 600, inline CSS, no external requests) with upcoming events, money, hand checks, unpaid singer invoices, the pipeline, Ads cost per enquiry and the bank balance. The Monday review and the assistant's first run of each day regenerate it. It is a local file only: never publish, commit, attach or print it. `--no-bank` skips Starling.
```

- [ ] **Step 7: Update the scheduled tasks** with the verbatim appendix text, then run the Phase 1 plan's Task 7 Step 8 check. Expected: `## Appendix A True` and `## Appendix E True`.

- [ ] **Step 8: Commit**

```bash
git add .claude/settings.json docs/HANDOVER-2026-09-27-ads-analytics.md CLAUDE.md
git commit -m "docs(automation): regenerate the owner's dashboard from the Monday review and the first assistant run"
```

### Task 3: Watch one real run

- [ ] Run the enquiry assistant once before 09:30 UTC (`run_scheduled_task enquiry-assistant`) and read its transcript. Expected: no permission prompt for `dashboard.py`, the file's mtime updated, mode still 600, and "dashboard updated" in the summary with no dashboard contents quoted.

---

## Self-review (done while writing)

- **Spec coverage:** feature 16's upcoming events with paid status (section 1), deposits and balances due (section 2), singer invoices unpaid (section 4), pipeline by status (section 5), the last 4 weeks' Ads spend and cost per enquiry (section 6), bank balance (section 7); regeneration by the Monday task and the first assistant run (Task 2); local file only (Read this before starting).
- **Consistency:** the hand-check states are `money_report.HAND_CHECK`'s keys, the same list Appendix E step 6a copies under "Money to check by hand". The payment states are `check_payments.assess`'s.
- **Open assumptions:** `enquiries.csv` (Phase 2) and `ads-summary.json` (Phase 3) don't exist yet; the dashboard reads the column names and shape agreed for them and shows a placeholder until they do. "Season" starts on 1 September (`SEASON_START_MONTH`); change it there if the Phase 3 report defines it differently.
