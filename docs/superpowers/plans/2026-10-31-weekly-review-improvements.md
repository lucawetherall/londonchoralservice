# Weekly marketing review improvements, 31 October 2026

> **For agentic workers:** the Monday run stays unattended and read-only on Google Ads, GA4, Search Console, Books and the site. Every account change still goes through `scripts/ads/` with validate-only first and a row in `logs/ads-changes.md`. New tests join `tests/run_ci_tests.py`. Dry runs never write to `~/lcs-private/reports/`: use `--out` (Task 0), because a stray `<date>.txt` there becomes the "previous report" for the next Monday's settings diff and change log.

**Goal:** make the Monday review answer the owner's question ("is the marketing working, and what should change?") in a form he acts on, and stop proposals from vanishing.

**Architecture:** the report script (`scripts/reports/weekly_review.py`) keeps gathering everything read-only into one saved text file, and the four sub-agents keep reading only their own sections. The changes add a computed brief to the report, a private record of what was proposed and decided, a lint pass over the reply before it goes out, and a shorter reply. Rules move out of agent prose and into code wherever a test can hold them.

**Tech stack:** Python 3 in the repo's `.venv`, the existing `tests/` style (plain asserts, run by `tests/run_ci_tests.py`), and the scheduled-task prompt in `~/.claude/scheduled-tasks/christmas-carol-campaign-review/SKILL.md`, mirrored in Appendix A of `docs/HANDOVER-2026-09-27-ads-analytics.md`.

No client names, addresses or ledger money figures appear in this file.

**Revised 31 Oct after a review against the code.** The changes from the first draft:
- Proposals are now recorded by parsing the saved review file, not by passing JSON in a shell argument.
- Quote speed is measured in days, because the pipeline records only quote dates.
- The hiring filter reuses `economics.hiring_intent`.
- The lint matches full client names only.
- Standing approvals became a prompt and data change.
- Pre-validation reuses `set_budget.py` and `set_campaign_status.py`, which already validate by default.
- Dry runs got their own output path.
- The "nothing before 2 Nov" hold was dropped, because the owner asked for the work now. It is replaced by a dry run before anything merges.

---

## 1. What the last five Mondays show

The report itself is in good shape. It has 14 sections, each guarded so that one failure no longer kills the rest. It also has a live settings snapshot (1b) that it compares with the previous week, GoatCounter for cookie-free totals, Core Web Vitals, the enquiry grading in 9b, and CI tests on every PR. The GoatCounter failure of 26 Oct is fixed: the reader retries once, and the failure line carries the HTTP code. The problems are in what the review measures and in what happens to its answer.

1. **The reply is a menu, and the owner does not want a menu.** The 26 Oct reply ran to about 2,000 words and held 18 numbered proposals. The owner approved three of them, the negatives. He then wrote "do whatever you think is best", and later "do whatever you think will be best for sales / conversions / leads". Items 4 to 18 were done only because he followed up by hand in that session.
2. **The business numbers are buried.** The headlines open with spend, clicks and Ads conversions. Enquiries, quotes, bookings and money sit halfway down, with no trend. Ads conversions are a known-bad measure here, because about 70% of visitors decline cookies.
3. **Attribution says the ads earn nothing, and it cannot know.** Season to 26 Oct: 15 enquiries, all of them unattributed, and every campaign shows A 0 and B 0. Seven enquiries carry grade C, which never counts. But the Christmas campaign clicked on 6 of the 7 days, so a C there is almost certainly a coincidence. A C on the wedding campaign, which clicked on 2 of the 7 days, is a real signal. The report prints the grade without that base rate.
4. **Proposals vanish.** Nothing records what was proposed, approved, done or dropped. A site or growth proposal that goes unanswered is never seen again.
5. **The web section argues from noise.** Three page fixes on 26 Oct rested on queries with 2 impressions each. The "money queries" list is a word filter: 23 of its 40 lines were Nine Lessons and Carols service-sheet searches. `economics.hiring_intent` already tells hiring searches apart, but only section 13 uses it, and only once a month.
6. **Agents misstate facts the repo holds.** On 26 Oct the growth agent quoted the soloist at the old price. Nothing checks a reply's prices, or scans it for names and emails, before the owner sees it.
7. **Small noise.**
   - Section 11 lists a removed campaign at £0 every week.
   - The WhatsApp question comes every week.
   - Section 13 prints a placeholder on three Mondays out of four.
8. **Untested.** These have no tests: `snapshot_block`, `previous_snapshot`, `snapshot_diff_lines`, `logged_changes` and `quiet_summary`.

## 2. Owner decisions

| # | Decision | Status |
|---|----------|--------|
| D1 | **Standing approvals.** The Monday run would apply these classes without asking. Each is still validated first, logged, and listed under "Done this morning".<br>(a) Negatives for NOT A BUYER terms that block none of the week's HIRING terms.<br>(b) Dismissing recommendation types the owner has already ruled out: campaign budget, search partners, Maximise conversions or clicks, lead form asset, dynamic image extension, broad match and AI Max.<br>(c) The dated MANUAL-ACTIONS archive line.<br>(d) A sitemap resubmission when section 7 says STALE.<br>(e) The `llms.txt` "content last updated" date.<br>Budgets, bids, pauses, keyword status, ad copy and site copy still wait for approval. | **Approved 31 Oct** ("all decisions approved"). The owner restated that any rise in ad spend needs his approval, so no budget change, up or down, is a standing approval. Built in Task 7. |
| D2 | **Validated budget and pause proposals.** The run runs `set_budget.py` and `set_campaign_status.py` in their default validate-only mode, and quotes the output, so the owner approves exactly what Google accepted. Nothing changes in the account. | Done in Task 8. These are read-only calls, already within "change nothing". |
| D3 | **Grade C** still never counts, but it is printed with its base rate. | Done in Task 3. |
| D4 | **The reply** has a cap of about 700 words. The full agent results go to a private file. | Done in Task 10. |
| D5 | **The WhatsApp question** is asked only while the pipeline holds an open WhatsApp enquiry from the last 28 days. | Done in Task 6. |

## 3. Tasks

### Task 0: a dry-run path

- `weekly_review.py --save-report --out PATH` writes the report to PATH instead of `~/lcs-private/reports/<date>.txt`. Section 1b's `previous_snapshot` still reads the real reports directory.
- `report_sections.py --file PATH` reads that file.
- Tests: `--out` writes there and not to the reports directory (with `LCS_PRIVATE_DIR` set to a temp directory), and `--file` serves sections from it.

### Task 1: a private record of the review and its proposals

**Files:** create `scripts/reports/review_log.py` and `tests/test_review_log.py`. Modify `weekly_review.py` to add section 0b.

**Storage**
- `~/lcs-private/reports/reviews/<date>.md` (mode 600) holds the dispatcher's full reply and each agent's RESULT block. The dispatcher writes it with the Write tool, which is private and outside the repo. It lives in a subfolder so the reports directory holds only report files.
- `~/lcs-private/review-proposals.jsonl` (mode 600) holds one object per proposal: `{"id": "2026-10-26-04", "date", "kind", "text", "status": "open|approved|done|dropped|expired", "decided", "note"}`. `kind` is one of ads, site, growth, manual, upload or budget. The dispatcher tags each item `[ads]`, `[site]` and so on, and an untagged item is `other`.

**Commands** (the file lock from `lcs_money`, mode 600 on create)
- `review_log.py record <review file>`: parses the numbered items under the heading `## Decisions` (lines matching `^\d+\. `), assigns `<date>-NN` in order, and prints `<id> <text>`. Rerunning it on the same date replaces that date's open items. Items already decided keep their ids.
- `review_log.py decide <id>[,<id>…] approved|dropped [--note TEXT]`
- `review_log.py done <id>[,<id>…] --note TEXT`
- `review_log.py open [--before DATE]`: prints open items oldest first, as `<id> · <kind> · <text>`. Any item open for more than 28 days is marked `expired` first, so the list stays short.

**Rules:** `record` refuses an item holding an `@`, or a UK phone number (`\b0\d{3,4}\s?\d{3}\s?\d{3,4}\b`, and the same with `+44`). Proposals name pages, campaigns and figures only.

**Section 0b, "Since last Monday"** (guarded like the other sections):
- the open proposals, each line starting `open `;
- the number of Ads changes logged since the previous report (section 1 lists them);
- the titles of PRs merged on origin/main since the previous report, using `hardened_git()` and `git log origin/main --merges --since <date> --format=%s`.

Add `open ` to `quiet_summary`'s exclusion prefixes.

**Tests:**
- `record` parses a fixture review file and numbers its items from 01.
- A second `record` that day replaces only the open items.
- `decide` on an unknown id exits 2.
- `open` expires an item older than 28 days.
- Contact details are refused.
- The file is created with mode 600.

### Task 2: section 0, "This week in brief"

**Files:** create `scripts/reports/brief.py` (pure functions) and `tests/test_brief.py`. Modify `weekly_review.py` and `economics.py`.

The report prints `== 0. This week in brief` last, after the sections it reads, and `report_sections.py 0` serves it. Each line shows this week, the week before, and the average of the 8 full weeks:
- **enquiries**, with this week's split by occasion and by source, from the pipeline sheet's `first_seen`;
- **quotes sent**, from the pipeline's `quoted YYYY-MM-DD` notes, with the median days from first contact to quote;
- **bookings**, as a count and £ booked, from ledger rows by `invoice_date`, with cancelled bookings left out (`check_payments.is_cancelled`);
- **ad spend and clicks**, from the per-week figures section 11 already builds;
- **page views from every visitor**, from GoatCounter's section 5c result, and **organic clicks**, from section 6's totals; "not read" when a section failed;
- **an alarms line**, the problem lines `quiet_summary` would list (the same `PROBLEM_RE` and exclusions), or "nothing alarming".

The section functions hand their figures back through their return values or a module-level `WEEK` dict. `brief.lines(week)` formats them, and an empty week prints zeros, never "–".

`economics.ads_summary` gains enquiries and bookings for each week, so `~/lcs-private/ads-summary.json` and the dashboard have them too.

**Tests:**
- A fixture week (3 enquiries, 2 quotes, 1 booking) gives the expected lines exactly.
- An empty week prints zeros.
- A failed section prints "not read".

### Task 3: grade C with its base rate

**Files:** `scripts/reports/enquiry_sources.py`, `weekly_review.py` (`enquiry_grades` already has `days`, the set of campaign click days) and `tests/test_enquiry_sources.py`.

- The base rate is the share of the 28 days in which the C's campaign had an ad click on that day or the day before.
- A C line reads `C <campaign> (… ; that campaign clicked on n of 28 days: a coincidence is likely)` when the share is 50% or more, and `(…: worth a look)` below 50%.
- The by-campaign lines read `C 4 (clicked 24/28 days)`.
- Grade C still never counts.

### Task 4: hiring searches every week

**Files:** `weekly_review.py` (`gsc_section`) and `.claude/agents/lcs-review-web.md`.

Section 6's "money queries" block becomes two blocks:
- `-- hiring searches (economics.hiring_intent, 10+ impressions this week), by impressions`, each line ending `[page one]` below position 8, `[8–20]` from 8 to 20, or `[deep]` beyond 20;
- `-- other money queries, top 10 by impressions`: the old word filter, without the hiring ones.

The web agent's step 4 now takes only the `[8–20]` lines, and its own impressions threshold goes. Section 13 still runs monthly.

### Task 5: lint the reply

**Files:** create `scripts/reports/review_lint.py` and `tests/test_review_lint.py`.

The input is the saved review file. The output is one line per finding, with exit 1 when there are any. The checks:
- **contact details:** an email address or a UK phone number, except the business's own number and its office@ and luca@ addresses;
- **client names:** a ledger `client_name`, matched as the whole name, case-insensitive, and never printed. The finding says "a client name on line N";
- **prices:** a £ figure from £250 to £10,000 under Decisions, Ad copy, GBP posts or Landing page that appears nowhere in the visible text of `pricing.html` or `christmas-pricing.html`, or in CLAUDE.md's combination figures (£550, and the Small Choir plus organist at £1,400). Spend and money lines elsewhere are not checked;
- **house rules:** the roster-size and London-cathedral patterns, imported from `validate_house_claims.py`, not copied;
- **proposal form:** a numbered item under Decisions without ` → `;
- **targeting:** a proposed keyword in Decisions holding singular "singer", "soloist", "solo" or "vocalist" (negatives are fine);
- **length:** more than 900 words before the final question.

**Tests:** a positive and a negative fixture for each check.

### Task 6: small noise

- **Section 11** leaves out a campaign with no spend, clicks, enquiries or bookings in the season, and prints `campaigns with nothing this season: <names>` once instead. Tests go in `tests/test_economics.py`.
- **`pipeline.summary_dict`** gains `open_whatsapp`: enquiries with source whatsapp, status new or quoted, first seen in the last 28 days. `pipeline.py summary` prints it. Tests go in `tests/test_pipeline.py`.
- **Section 13**, on any Monday but the first of the month, prints its heading and one line: `next: <date>`.

### Task 7: standing approvals (D1)

**Files:** `data/standing-approvals.yml` (the five classes, each with its rule and its script), the dispatcher prompt (a step that runs the classes before the reply, using the same worktree, script, validate, apply, log and PR flow as approved changes, with negatives checked by `negative_match` against the week's HIRING terms), the Google Ads bullet in CLAUDE.md, and Appendix A.

**Test:** `tests/test_standing_approvals.py` checks that the YAML names exactly the five classes, and that the recommendation types match the ones the owner ruled out on 26 Oct in `logs/ads-changes.md`.

### Task 8: budget and pause proposals, validated

The prompt's step 3 gains a new step. For each PROPOSE budget line and each spend-guard pause, the dispatcher runs the matching command:

```
.venv/bin/python scripts/ads/set_budget.py <id> <£> --reason "<reason>"
.venv/bin/python scripts/ads/set_campaign_status.py <id> paused --reason "<reason>"
```

Both run without `--apply`, which is their validate-only default. The reply quotes the current → new line each one prints. If validation fails, the item stays in the reply with the error, marked "Google refused this as written". Both commands are added to the allow list.

### Task 9: tests for the 26 Oct pieces

Create `tests/test_weekly_review_snapshot.py`, covering:
- `snapshot_block` stops at the next `-- ` or `== ` line;
- `previous_snapshot` takes the newest earlier report, skips today's, skips a report whose 1b failed, and ignores `reviews/`;
- `snapshot_diff_lines` prints `- set …` and then `+ set …` for a changed bid, and "no change" when nothing changed;
- `logged_changes` keeps the rows since the baseline and the rows from the last `LOG_DAYS` days;
- `quiet_summary` lists `SECTION 5c FAILED` as a problem, and does not list a `set ` line or an `open ` line that contains "error".

### Task 10: the reply, rewritten

**Files:**
- the SKILL.md, updated through the scheduled-tasks tool after a backup copy in `~/lcs-private/backups/`;
- Appendix A, with the same text;
- the weekly-review bullet in CLAUDE.md;
- the allow list in `.claude/settings.json`, so that `tests/test_prompt_allowlist.py` passes;
- `.claude/agents/lcs-review-bookings.md` (open WhatsApp count) and `.claude/agents/lcs-review-web.md` (Task 4).

**Reply format** (the sub-agents' RESULT formats are unchanged apart from Tasks 4 and 6):
1. **Brief:** section 0 verbatim, plus section 0b's open proposals and merged PRs.
2. **Done this morning:** only once Task 7 exists.
3. **Decisions** (`## Decisions`): numbered, each tagged and in the form "resource → field: current → new — reason", with Task 8's validated line where one applies. Open items from earlier weeks come first, under their ids.
4. **One line per quiet area:** Tracking, Web, Coverage, Speed, Money, Books, Hand checks, Pipeline. Any area with a finding gets up to three lines.
5. **Watch:** at most three lines.
6. **One question:** approve by number or id (all, some or none). The WhatsApp question is added only when the open WhatsApp count is above zero.

**Steps in the run:** report → agents → cross-checks → Task 8 validations → write the review file → `review_lint.py` (fix and rewrite, at most twice; then put the findings at the top of the reply) → `review_log.py record` → reply. After the owner answers: `decide`, then the existing worktree flow, then `done` once a PR merges.

### Task 12: the enquiry assistant's week, in the Monday report

The owner asked that the review also cover the other routine.

**Why.** Its run history (`list_task_runs`) shows gaps the Monday review never saw:
- 22 to 25 Oct, and 27 to 29 Oct (37 hours), when a run session left open blocked every later run;
- one run on 25 Oct that stopped early because the command safety check kept failing.

The assistant records only `last_checked`, so these left no trace in any report.

**Files:** `scripts/bookings/assistant_io.py`, `tests/test_assistant_io.py`, `weekly_review.py` (new section 9c) and `.claude/agents/lcs-review-bookings.md`.

**What changes**
- `assistant_io.py` appends one line to `~/lcs-private/assistant-runs.jsonl` (mode 600; lines older than 60 days dropped) for each of these:
  - `state`: `{"start": <now>}`
  - `done`: `{"done": <now>, "marked": n}`
  - `zoho-down`: `{"zoho_down": <now>}`
  - `daily-done`: `{"daily": <date>}`
- A failure to append never changes what a command prints or its exit code.
- Section 9c, "Enquiry assistant, last 7 days", reads that file:
  - runs started against the 63 expected (9 a day);
  - runs finished (a `done` after the start, before the next start);
  - runs that stopped early (a start with no `done` or `zoho_down`);
  - Zoho-down runs;
  - the longest gap between starts in London hours 06:00 to 22:00 (`STALE ASSISTANT` when over 4 hours, so `quiet_summary` lists it);
  - days the daily pass ran, out of 7.
  - Before the log has a full week it says "log started <date>".
- The bookings agent copies section 9c into a new ASSISTANT line, and the reply's quiet-area lines include it.

**How the two routines share things** (checked 31 Oct):
- **Ledger and pipeline:** both write `bookings.csv` and `enquiries.csv`, under the same file locks.
- **Timing:** the review starts at 09:03, between the assistant's 08:07 and 10:07 runs (cron `7 6-22/2`).
- **Dashboard:** both regenerate it.
- **Additive changes only:** this plan adds a key to `pipeline.summary_dict` and two keys to `ads-summary.json`, and the dashboard reads only the keys it knows.
- **Prompt allow list:** `tests/test_prompt_allowlist.py` covers Appendix E too, so the assistant's prompt must still pass.
- **Not done here:** the price and name lint (Task 5) could also check the reply drafter's text before it saves a draft. That changes the client-facing routine, so it goes in the roadmap as its own item.

### Task 11: docs

- Appendix A gets the new prompt verbatim and a dated note.
- CLAUDE.md's weekly-review bullet mentions section 0, the review file, the proposals record and the lint.
- `docs/ROADMAP.md` gets an item for linting the reply drafter's text with Task 5's checks before it saves a draft (Task 12).

## 4. Order

1. Tasks 0, 1, 2, 3, 4, 9, Task 6's section 11 and 13 changes, and Task 12's section 9c go on one branch. They all touch `weekly_review.py`, so one worker does them in turn.
2. Task 5, Task 6's pipeline change and Task 12's run log in `assistant_io.py` go on a second branch, in parallel. They touch other files.
3. After both merge, Tasks 8, 10 and 11 follow: the prompt, the agents and the docs.
4. Before the prompt goes live, run a dry run:
   - `weekly_review.py --save-report --quiet --out <scratch>`;
   - `report_sections.py --file <scratch> 0 0b 6 9b 11 13`;
   - `review_lint.py` on a review file written from the 26 Oct reply, which must flag the 2,000 words and the soloist at £250.
5. 2 Nov is the first live run. Check the saved review file and `review_log.py open` afterwards.

## 5. Verification

- `.venv/bin/python tests/run_ci_tests.py` is green on every PR.
- A dry run changes nothing: `git status` stays clean, `logs/ads-changes.md` is untouched, and there is no new file in `~/lcs-private/reports/`.
- On 2 Nov and 9 Nov, the reply is under the word cap, opens with section 0, and lists the previous week's open items by id.
