# Weekly marketing review improvements, 31 October 2026

> **For agentic workers:** one PR per task, in the order given, each with its tests in `tests/run_ci_tests.py`. The Monday run stays unattended and read-only on Google Ads, GA4, Search Console, Books and the site; every change it makes to the account still goes through `scripts/ads/` with validate-only first and a row in `logs/ads-changes.md`. Tasks 1 to 6 need no owner decision. Tasks 7 to 10 wait for the decisions in section 2. Nothing in this plan lands on main between Sunday evening and the Monday 09:00 run.

**Goal:** make the Monday review answer the owner's question ("is the marketing working, and what should change?") in a form he acts on, and stop proposals from vanishing.

**Architecture:** the report script (`scripts/reports/weekly_review.py`) keeps gathering everything read-only into one saved text file; the four sub-agents keep reading only their sections. The changes add a short computed "this week in brief" section at the top of the report, a private record of what was proposed and decided, a lint pass over the reply before it is sent, and a tighter reply format. Rules move out of agent prose and into code wherever a test can hold them.

**Tech stack:** Python 3 in the repo's `.venv` (google-ads, PyYAML), the existing `tests/` style (plain asserts, run by `tests/run_ci_tests.py`), the scheduled-task prompt in `~/.claude/scheduled-tasks/christmas-carol-campaign-review/SKILL.md` (mirrored in Appendix A of `docs/HANDOVER-2026-09-27-ads-analytics.md`).

No client names, addresses or ledger money figures appear in this file.

---

## 1. What the last five Mondays show

The report itself is in good shape: 14 sections, each guarded so one failure no longer kills the rest, a live settings snapshot (1b) that diffs against the previous week, GoatCounter for cookie-free totals, Core Web Vitals, the enquiry grading in 9b, CI tests on every PR. The GoatCounter failure of 26 Oct is fixed (one retry, HTTP code in the failure line). The problems are in what the review measures and in what happens to its answer.

1. **The reply is a menu, and the owner does not want a menu.** The 26 Oct reply ran to about 2,000 words and 18 numbered proposals. The owner approved three (the negatives), then wrote "do whatever you think is best" and later "do whatever you think will be best for sales / conversions / leads". Items 4 to 18 were done only because he followed up by hand in that session. The format asks him to adjudicate when the house rule since 14 Oct is "decide, don't ask", except for Ads budgets, bids, pauses and copy.

2. **The business numbers are buried.** Headlines open with spend, clicks and Ads conversions. Enquiries this week, quotes sent, bookings confirmed, pounds booked and pounds received sit in the Bookings block halfway down, and only as this week's figures with no trend. Ads conversions are a known-bad measure here (about 70% of visitors decline cookies): the report says so, then leads with them anyway.

3. **Attribution says the ads earn nothing, and it cannot know.** Season to 26 Oct: 15 enquiries and 6 bookings, all "unattributed"; every campaign shows A 0, B 0. Seven enquiries carry grade C (an ad click in the matching campaign that day or the day before), which "never counts". But the Christmas campaign clicked on 6 of the 7 days, so a C there is almost certain by coincidence, while a C on the wedding campaign (clicks on 2 of 7 days) is a real signal. The report prints the grade without the base rate, so the owner cannot weigh it.

4. **Proposals vanish.** Nothing records what was proposed, what the owner approved, what was done, or what was dropped. Each Monday starts from zero. Section 1 lists logged Ads changes, and 1b diffs the account, but a site-copy or growth proposal left unanswered is never seen again.

5. **The web section argues from noise.** The web agent is told to ignore queries under 10 impressions, then proposed three page fixes for queries with 2 impressions each ("choir to hire", "how much does a choir cost", "choir wedding"). Section 6's "money queries" list is a regex on funeral/wedding/carol/choir, so 23 of its 40 lines on 26 Oct were Nine Lessons and Carols service-sheet queries: informational traffic to one guide, not hiring intent. The hiring-intent classifier already exists in `economics.shortlist` and runs only monthly.

6. **Agents misstate facts the repo holds.** On 26 Oct the growth agent assumed three of four Christmas ads carried traffic (all clicks went through one ad; now fixed by `clicks30` in section 4) and quoted the soloist at the old price. Nothing checks a reply's prices against `pricing.html` or scans it for names and emails before it reaches the owner.

7. **Small noise.** Section 11 lists a removed campaign at £0 every week. The reply asks "did any WhatsApp enquiry become a booking?" even in weeks with no open WhatsApp enquiry. Section 13 says "runs on the first Monday" on the other three.

8. **Untested since 26 Oct.** The 1b snapshot diff, the logged-changes block, the spend guard with the retired value check, and the GoatCounter retry have not yet run on a Monday. Tests cover `enquiry_sources`, `goatcounter`, `cwv`, `money_report`, the archive and the proposals flag; not `snapshot_diff_lines`, `previous_snapshot`, `logged_changes` or `quiet_summary`.

## 2. Owner decisions (one reply covers all five)

| # | Decision | Recommendation |
|---|----------|----------------|
| D1 | **Standing approvals.** Let the Monday run apply these without asking, each still validate-only first, logged, and listed in the reply under "Done this morning": (a) negatives for NOT A BUYER search terms that block none of the week's HIRING terms; (b) dismissing Google recommendations of a type the owner has already ruled out (campaign budget, search partners, Maximise conversions or clicks, lead form asset, dynamic image extension, broad match, AI Max); (c) the dated MANUAL-ACTIONS archive line; (d) a sitemap resubmission when section 7 says STALE; (e) the `llms.txt` "content last updated" date. Budgets, bids, pauses, keyword status, ad copy and site copy still wait for approval. | Yes to all five. Each is a class the owner has approved every time it came up (negatives on 5, 12, 16, 19, 25 and 26 Oct; the nine dismissals on 26 Oct). |
| D2 | **Pre-validated change scripts.** Let the unattended run write its proposal scripts under `~/lcs-private/proposals/<date>/` (outside the repo) and run each validate-only, so the reply shows the exact validated current → new lines and approval means running the same script with `--apply`. The run still changes nothing in the account. | Yes. It removes the "write the script after the owner replies" step that stretched the 26 Oct session into the next day, and the owner sees what Google would accept. |
| D3 | **Grade C stays uncounted** but is printed with its base rate (Task 3), so the owner can read a wedding C as a signal and a Christmas C as noise. | Keep the rule; add the base rate. |
| D4 | **Reply length.** Cap the reply at about 700 words: a brief, a decisions list, and one line per area where nothing needs attention. The full agent results go to a private file (Task 1). | Yes. |
| D5 | **The WhatsApp question** is asked only when the pipeline holds an open WhatsApp enquiry from the last 28 days. | Yes. |

## 3. Tasks

### Task 1: a private record of the review and its proposals

The reply is saved beside the report, and every proposal gets an id, so next Monday can say what is still open.

**Files**
- Create: `scripts/reports/review_log.py`
- Modify: `scripts/reports/weekly_review.py` (new section 0b, see below), `scripts/reports/report_sections.py` (no change needed: it splits on `== <id>.` headings)
- Modify: `.claude/agents/lcs-review-bookings.md` (nothing), the dispatcher prompt (Task 10 carries the prompt edits; this task adds the commands)
- Test: `tests/test_review_log.py`, added to `tests/run_ci_tests.py`

**Design**
- `~/lcs-private/reports/<date>-review.md` (mode 600): the dispatcher's full reply plus each agent's RESULT block, written by the dispatcher with the Write tool (a private path, not a repo file).
- `~/lcs-private/review-proposals.jsonl` (mode 600), one JSON object per line: `{"id": "2026-10-26-04", "date": "2026-10-26", "kind": "site|ads|manual|growth|upload|budget", "text": "music-guides/hiring-a-choir.html → …", "status": "open|approved|done|dropped", "decided": "2026-10-26", "note": "PR #392"}`. No names, emails or amounts from the ledger: proposals name pages, campaigns and figures only.
- Commands, all under the ledger lock from `lcs_money`:
  - `review_log.py propose <date> '<json list of {kind, text}>'` prints the ids it assigned (`<date>-NN`).
  - `review_log.py decide <id>[,<id>…] approved|dropped [--note TEXT]`
  - `review_log.py done <id> --note TEXT`
  - `review_log.py open [--before <date>]` prints open proposals, oldest first, as `<id> · <kind> · <text>`.
- Section 0b in the report, "Since last Monday": the open proposals from `review_log.py open --before <today>`; Ads changes logged since the previous saved report (reuse `logged_changes_lines`, which section 1 already prints, so print only a count here and point at section 1); PRs merged since the previous report that touched `*.html` (`git -C <repo> log --merges --since <prev report date> --format=%s`, hardened as `hardened_git()` does). The dispatcher's reply opens with it (Task 10).

**Steps**
1. Write `tests/test_review_log.py` first: `propose` assigns `<date>-01`, `-02`; `decide` on an unknown id fails with exit 2; `open` lists only status open; a second `propose` on the same date continues numbering; the file is created with mode 600 under a `LCS_PRIVATE_DIR` temp dir (the pattern `tests/test_pipeline.py` uses).
2. Implement `review_log.py` with `lcs_money.PRIVATE`, `lcs_money.today()` and the ledger lock; refuse any text containing an `@` or a UK phone pattern (`\b0\d{4}\s?\d{6}\b`), so a proposal line can never carry contact details.
3. Add section 0b to `run_sections` before section 1, guarded like the others: `run_section("0b", "Since last Monday", since_last_monday_section, today)`. Its "open proposals" lines are never problems for `quiet_summary` (prefix them `open `, and add that prefix to the exclusion tuple).
4. Add both files to `tests/run_ci_tests.py`. Run `.venv/bin/python tests/run_ci_tests.py` and `.venv/bin/python scripts/reports/weekly_review.py` (no `--save-report`; section 0b prints "no open proposals" on a fresh machine).
5. Add the three `review_log.py` forms to the dispatcher's SHELL COMMANDS and to the `Bash(...)` allow list in `.claude/settings.json`; `tests/test_prompt_allowlist.py` must still pass.

### Task 2: "this week in brief", computed, at the top of the report

The business figures lead, with trend, so the reply's first five lines come from code rather than from an agent's reading.

**Files**
- Create: `scripts/reports/brief.py` (pure functions over rows already loaded elsewhere: the pipeline sheet, the ledger, `ads-summary.json`, GoatCounter's week, section 6's totals)
- Modify: `scripts/reports/weekly_review.py` (new section 0, printed first; it runs after the sections it draws on, so compute it last and print it with a heading the archive moves to the top, or simplest: gather the week's figures into a dict as each section runs and print section 0 at the end under the heading `== 0. This week in brief` and let `report_sections.py 0` serve it; order in the file does not matter to the agents)
- Modify: `scripts/reports/economics.py` (`ads-summary.json` already holds 8 full weeks of spend and clicks; add enquiries and bookings per week to the same file from the pipeline sheet and ledger)
- Test: `tests/test_brief.py`

**Lines section 0 prints** (one each, "this week · the week before · 8-week average"):
- enquiries, by occasion and by source (from the pipeline sheet, first_seen in the 7 days)
- quotes sent (pipeline "quoted" notes dated in the week) and median hours from first_seen to the first quote
- bookings confirmed and £ booked (ledger rows with invoice_date in the week; count and total only)
- £ received from clients (section 10 already has it)
- ad spend and clicks (section 1), with "no campaign over its cap" or the campaign that is
- page views from every visitor (section 5c) and organic clicks (section 6)
- one alarm line: any "SECTION FAILED", STOP GUARD, STALE, NOT INDEXED, CONFIG ERROR or a conversion-action !CHECK from the sections above, or "nothing alarming"

**Steps**
1. Tests first, with small fixture rows: a week with 3 enquiries (2 web form, 1 email), 2 quotes, 1 booking, expected lines verbatim; an empty week prints zeros, never "–" in the brief.
2. Implement `brief.py` as pure functions; `weekly_review.py` collects the figures into one dict (`WEEK = {}`) as sections run and calls `brief.lines(WEEK)` at the end.
3. Extend `economics.ads_summary()` with `enquiries` and `bookings` per week; `tests/test_economics.py` gets a case.
4. `dashboard.py` reads the two new keys if present (it already reads `ads-summary.json`); no change to its layout.
5. Dispatcher: SHELL COMMANDS gains `report_sections.py 0`, and the reply's first block is section 0 verbatim (Task 10).

### Task 3: grade C with its base rate

**Files**
- Modify: `scripts/reports/enquiry_sources.py` (`grade`, `line`, `counts_lines`), `scripts/reports/weekly_review.py` (`enquiries_section` passes click days)
- Test: `tests/test_enquiry_sources.py`

**Steps**
1. Tests: a C enquiry on a campaign that clicked on 24 of 28 days prints `C <campaign> (clicks on 24 of 28 days: a coincidence is likely)`; on 3 of 28 days, `(clicks on 3 of 28 days: worth a look)`; the threshold is 50%. The by-campaign block prints `C 4 (clicked 24/28 days)`.
2. `ClickDays.clicked_days(start)` already exists in `weekly_review.py`; pass the per-campaign day count into `grade_rows` as `click_days={campaign_key: n}` and into `counts_lines`.
3. The ads agent's step 7 and the bookings agent's step 9 copy the new wording as printed; no agent rule changes.

### Task 4: hiring-intent queries weekly, from code

**Files**
- Modify: `scripts/reports/weekly_review.py` (`gsc_section`), `scripts/reports/economics.py` (expose the intent classifier `shortlist` uses as `is_hiring_query(q)` if it is not already a function)
- Modify: `.claude/agents/lcs-review-web.md` (step 4 reads the new block only; step 2's "ignore under 10 impressions" becomes unnecessary because the script applies it)
- Test: `tests/test_economics.py` (classifier cases: "hire a choir" yes, "choir for funeral" yes, "nine lessons and carols order of service" no, "funeral singers near me" no, since singular singer searches are never targeted)

**Steps**
1. In `gsc_section`, replace the single "money queries" list with two: `-- hiring-intent queries (10+ impressions this week), by impressions` (the classifier, any position; mark `[page one]` under 10 and `[8–20]` in that band) and `-- informational money queries, top 10` (the old regex minus the hiring ones). Keep the "top 15 queries" and "top 15 pages" blocks.
2. Web agent step 4: "Each line in the hiring-intent block marked [8–20]: one fix each", and drop its own threshold wording. Step 2 reads the informational block for moves of more than 3 positions.
3. Section 13 stays monthly (it reads 28 days with the page's h2s); on other Mondays print nothing but its heading and the next date, as now.

### Task 5: a lint pass over the reply

**Files**
- Create: `scripts/reports/review_lint.py`
- Test: `tests/test_review_lint.py`

**Checks** (input: the saved `<date>-review.md`; output: one line per finding, exit 1 when any):
- an email address, a UK phone number, or a surname from the ledger's `client_name` column (read under `LCS_PRIVATE_DIR`, compared case-insensitively, never printed: the finding says "a client name on line N")
- a `£` figure between £250 and £5,000 in a line under the headings Ad copy, GBP posts, Landing page or Proposed changes that is not a price on `pricing.html` or `christmas-pricing.html` (parse both pages' price grids the way `validate_house_claims.py` reads copy), with the combo figures from CLAUDE.md allowed (£275 soloist, £250 organist added, £550, £1,400 Small Choir plus organist)
- the roster-size and London-cathedral patterns from `validate_house_claims.py` (import its regexes rather than copying them)
- a numbered proposal line that lacks ` → ` or ` — ` (the "resource → field: current → new — reason" form)
- the word "singer" in a proposed negative or keyword line when singular and not "carol singers" or "funeral singers" (the targeting rule)
- more than 900 words between the first line and the final question (D4)

**Steps**
1. Tests with a fixture reply: each check has a positive and a negative case.
2. Implement; the dispatcher runs `review_lint.py ~/lcs-private/reports/<date>-review.md` after writing the file and before replying, fixes what it names, saves again, and reruns until clean (at most twice; then reply with the findings at the top). Add the command to SHELL COMMANDS and the allow list.

### Task 6: small noise

**Files**
- Modify: `scripts/reports/economics.py` (section 11: omit a campaign with no spend, clicks, enquiries and bookings in the season; print "campaigns with nothing this season: <names>" once instead)
- Modify: `scripts/bookings/pipeline.py` (`summary_dict` gains `open_whatsapp`: enquiries with source whatsapp, status new or quoted, first_seen in the last 28 days), `.claude/agents/lcs-review-bookings.md` step 8 (prints "open WhatsApp enquiries: n"), the dispatcher's final question (asks the WhatsApp question only when n > 0; D5)
- Modify: `scripts/reports/weekly_review.py` `shortlist_section` (on a non-first Monday print nothing after the heading but `next: <date>`), and `quiet_summary` (section 13's "runs on the first Monday" line is not a problem already; keep)
- Tests: `tests/test_economics.py`, `tests/test_pipeline.py`

### Task 7: standing approvals (after D1)

**Files**
- Create: `scripts/ads/standing_approvals.py`: reads `data/standing-approvals.yml` (the five classes, each with its rule in words and the script it uses: `add_negatives` modelled on the latest `scripts/ads/add_negatives_*.py`, `dismiss_recommendations_*.py` per type, `scripts/gsc/submit_sitemap.py`, the archive line, the `llms.txt` date) and, given the ads agent's NEGATIVES line and the week's HIRING terms, writes a dated `scripts/ads/add_negatives_<date>.py` in a worktree, validates it (`negative_match.py` proves it blocks no HIRING term), applies it with `--apply`, logs it, commits and opens the PR; the dispatcher merges it once the check passes, as it does for approved changes today.
- Modify: the dispatcher prompt step 4 (a new step 3b "standing approvals", run before the reply; its results go under "Done this morning" in the reply, each with its log row); CLAUDE.md's Google Ads bullet ("Every change runs first with validate_only … apply it only after my explicit approval" gains "except the standing approvals in `data/standing-approvals.yml`, owner decision <date>"); Appendix A.
- Test: `tests/test_standing_approvals.py`: a NOT A BUYER term whose proposed negative would also block a HIRING term is refused; a recommendation type not in the list is never dismissed; the file's five classes are exactly those D1 names.

The run keeps "no git commands" for everything else: this task gives it one scripted path (`standing_approvals.py` does the git work itself, in a worktree it removes afterwards), so the prompt's allow list grows by one command.

### Task 8: pre-validated proposal scripts (after D2)

**Files**
- Create: `scripts/ads/propose.py`: takes the ads agent's PROPOSED ADS CHANGES items (a JSON list, each `{"kind": "negative|budget|status|bid|headlines", "campaign": …, …}`), writes one script per item under `~/lcs-private/proposals/<date>/NN-<kind>.py` from the existing templates (`set_budget.py`, `set_campaign_status.py`, the latest `*_bid_*.py` and `*headlines_*.py`), runs each validate-only and prints its current → new lines. `set_budget.py`'s cap check stays inside the script, so a proposal above `budget_cap.py` fails validation here, before the owner sees it.
- Modify: the dispatcher prompt (step 3c: run `propose.py` on the ads items; the reply quotes each validated block; after approval, `propose.py --apply <id>` copies the script into a dated `scripts/ads/` file in a worktree, applies it, logs, commits, PRs); the allow list.
- Test: `tests/test_propose.py` with the Ads client stubbed (`tests/test_weekly_proposals.py` shows the pattern): a budget above the cap is refused at validation; a headline over 30 characters is refused before any API call.

### Task 9: tests for what landed on 26 Oct

**Files**
- Create: `tests/test_weekly_review_snapshot.py`: `snapshot_block` splits a report at `-- snapshot`; `previous_snapshot` picks the newest earlier report in a temp reports dir and ignores today's; `snapshot_diff_lines` prints `- set …` then `+ set …` for a changed bid and nothing for an unchanged block; `logged_changes` keeps rows since the baseline and the last `LOG_DAYS` days; `quiet_summary` lists a `SECTION 5c FAILED` line as a problem and never a `set ` line that contains the word "error".
- Add to `tests/run_ci_tests.py`.

### Task 10: the reply, rewritten

**Files**
- Modify: `~/.claude/scheduled-tasks/christmas-carol-campaign-review/SKILL.md` through the scheduled-tasks tool (copy it to `~/lcs-private/backups/` first), Appendix A of `docs/HANDOVER-2026-09-27-ads-analytics.md` (the same text), the weekly-review bullet in `CLAUDE.md`, `.claude/settings.json` (allow list), `tests/test_prompt_allowlist.py` (must pass)

**Reply format** (D4; the sub-agents' RESULT formats do not change):
1. **Brief**: section 0 verbatim (Task 2), then section 0b's open-proposal count and the PRs merged since last Monday (Task 1).
2. **Done this morning** (Task 7, when it applies): one line per standing approval applied, with its log row.
3. **Decisions**: the numbered proposals, each "resource → field: current → new — reason", with its validated block where Task 8 applies. Proposal ids from `review_log.py propose` in brackets so the owner can answer by id.
4. **Where nothing needs attention, one line**: "Tracking: fine (Submit lead form last seen <date>)", "Coverage: fine", "Money: nothing overdue", "Hand checks: none". The full agent blocks go to the saved review file, not the reply.
5. **Watch**: at most three lines on what next Monday should show (the Christmas bid test to 9 Nov, a page changed this week and its GoatCounter taps, a conversion action not seen for a month).
6. **One question**: approve by id (all, some, none), plus the WhatsApp question only when Task 6's count is above zero.

**Steps**
1. Rewrite the prompt's EACH RUN and REPLY FORMAT sections; keep SAFETY and the stop rule on auth errors as they are; add the new SHELL COMMANDS (`report_sections.py 0`, `review_log.py …`, `review_lint.py …`, and Tasks 7 and 8's commands once decided).
2. Step 4 (after the owner answers) gains: `review_log.py decide` for each id, and `review_log.py done` when a PR merges.
3. Dry run: `run_scheduled_task` on a weekday after Task 1 to 6 are merged, against that day's report; read the saved review file; check it against D4's cap and the lint.

### Task 11: docs

Appendix A gets the new prompt verbatim and a dated note; `CLAUDE.md`'s weekly-review bullet mentions section 0, the review file, the proposals record and (after D1) the standing approvals; `docs/ROADMAP.md` gets one item per task not yet done, in its style, so a later session can pick them up.

## 4. Order and timing

- **Before Monday 2 Nov:** nothing. The 1b snapshot, the GoatCounter retry, the retired value check and the growth agent's first run all get their first Monday as they are, so a failure is attributable.
- **Week of 2 Nov:** Tasks 3, 4, 6 and 9 (small, no decision needed), then Task 1 and Task 2; merged by Friday 6 Nov so 9 Nov runs with section 0 and the proposals record.
- **After the owner's reply on D1 to D5:** Tasks 5 and 10 (the lint needs the saved review file that Task 10's prompt writes; land them together), then 7 and 8.
- **16 Nov:** first Monday on the full set. Compare the reply's length and the number of decisions with 26 Oct's.

## 5. Verification

- `.venv/bin/python tests/run_ci_tests.py` green on every PR (the pull-request check runs it).
- `.venv/bin/python scripts/reports/weekly_review.py` on a weekday prints sections 0 and 0b and changes nothing (`git status` clean; `logs/ads-changes.md` unchanged).
- `.venv/bin/python scripts/reports/report_sections.py 0 0b` prints both.
- A dry run of the scheduled task on a weekday produces `~/lcs-private/reports/<date>-review.md`, `review_lint.py` passes on it, and the reply is under the word cap.
- On 9 Nov and 16 Nov: `review_log.py open` shows the previous week's undecided items at the top of the reply; the owner answers by id; `decide` and `done` rows appear in the record.
