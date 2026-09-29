# Structured State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Approved, 29 Sep 2026. The owner answered yes to the spec's three questions, so tasks 14, 15 and 18 go ahead as written. PRs 1–4 are merged (#209, #216); PRs 5 and 6 (tasks 16–18) are on `feat/structured-state-final`. Task 11 (the owner applies the migration) is still the owner's. Task 18's agent prompts (`.claude/agents/`) and CLAUDE.md sentences are applied by the owner, since Claude may not edit those files.

**Goal:** Record each fact about a booking or a singer invoice as one validated line in an append-only log, `~/lcs-private/events.jsonl`, and have every reader use it before the notes, without changing any behaviour on the day it ships.

**Architecture:** A library, `scripts/bookings/lcs_events.py`, owns the log: the schema, validated appends under its own flock (always taken inside the CSV's lock, never around it), reads cached per process, and a per-subject index of facts by family. The existing reader functions in `check_payments.py`, `singer_invoices.py` and `pipeline.py` take an optional `facts` argument and read events first, falling back to their patterns per family. The owner barrier moves into a shared `lcs_owner.py`. A CLI, `scripts/bookings/events.py`, verifies, shows, migrates and compares. The Command Centre reads through the same functions and writes only by running the scripts.

**Tech Stack:** Python 3 stdlib in the repo's `.venv`. Tests are stdlib scripts in the repo's style: `.venv/bin/python tests/test_lcs_events.py`.

**Spec:** [docs/superpowers/specs/2026-09-29-structured-state-design.md](../specs/2026-09-29-structured-state-design.md).

---

## Read this before starting

- **Never the real private folder.** Every test sets `LCS_PRIVATE_DIR` (and, where the ledger is involved, `LCS_BOOKINGS_CSV`) to a temp dir before importing, as `tests/test_cancel_contract.py` does. No session reads `~/lcs-private` beyond file names and CSV headers.
- **Nothing changes without a log.** Until Task 11, no `events.jsonl` exists, so every reader falls back to the notes. Each PR's full test run must pass unchanged.
- **Notes are always written.** Every writer that gains an event keeps writing its note, in the same words. Only `--fact` builds a phrase itself, and it builds today's phrase.
- **Lock order.** CSV lock (`lm.locked_rows`) first, the log's lock (`lm.ledger_lock(events.jsonl)`) inside `lcs_events.append()` only. Neither is re-entrant.
- **Event first, then the CSV.** Inside `locked_rows`: edit the row, append the event (fsync), leave the block. A failed CSV write gets a `write-failed` retract.
- **No free text in the log.** Every field is a date, an amount, an id, a hash or a word from a fixed list; the validator runs on write and on read.
- **Owner kinds need the nonce.** Only `lcs_owner.owner_confirmed()` makes `by: owner`.
- **Two files called events.jsonl.** This work's is `~/lcs-private/events.jsonl` (the state log). `~/lcs-private/command-centre/events.jsonl` is the push feed (`cc_event.py`, `push.py`); don't touch it.

## File structure

| File | Responsibility | Task |
|---|---|---|
| Create `scripts/bookings/lcs_owner.py` | `owner_nonce_path`, `owner_confirmed`, `owner_folder_problem` (moved from `check_payments.py`, the folder check widened to the singer store and the log) | 1 |
| Create `scripts/bookings/lcs_events.py` | Schema, `validate`, `append`, `read`, `index`, `Facts`, families, note hashes and claims | 2, 3, 5 |
| Create `scripts/bookings/events.py` | CLI: `verify`, `show`, `migrate`, `compare`, `retract`, `notes-checked` | 4, 9, 17 |
| Modify `scripts/bookings/check_payments.py` | Facade reads events first; held; `--fact`; events from `--reminded` and `--apply` | 5, 12 |
| Modify `scripts/bookings/pipeline.py` | `reviews_due`, `done_due` through `closed_on` and held; events from `reviewed`, `review-skipped` | 6, 13 |
| Modify `scripts/ads/upload_bookings.py` | Skip held bookings | 6 |
| Modify `scripts/bookings/singer_invoices.py` | Facade reads events first; held; events from every writer; `--owner` | 7, 14 |
| Modify `command_centre/actions.py`, `models.py`, `data.py`, templates | New argv, timelines, held panel, Health line, new actions | 10, 15, 16, 17 |
| Modify `.claude/settings.json`, `.gitignore`, `tests/test_prompt_allowlist.py` | Allow and deny rules; `events*.jsonl` | 4, 15 |
| Modify `.claude/agents/lcs-reply-drafter.md`, `CLAUDE.md`, `docs/HANDOVER-2026-09-27-ads-analytics.md` (Appendices A and E), the business-automation spec | `--fact`, pointers to the spec | 18 |
| Create `tests/test_lcs_owner.py`, `test_lcs_events.py`, `test_events_cli.py`, `test_events_migrate.py`, `test_state_twins.py`, `tests/state_cases.py` | As named | 1–13 |

---

## PR 1: the library (nothing reads it yet)

### Task 1: `lcs_owner.py`

**Files:** Create `scripts/bookings/lcs_owner.py`, `tests/test_lcs_owner.py`; modify `scripts/bookings/check_payments.py`.

- [ ] **Step 1:** Move `OWNER_NONCE_TTL`, `owner_nonce_path`, `owner_confirmed` and `owner_ledger_problem` out of `check_payments.py` unchanged; `check_payments` imports them under the same names, so its tests and `command_centre/actions.py` need no change.
- [ ] **Step 2:** Add `owner_folder_problem(paths)`: `None` when `LCS_BOOKINGS_CSV` is unset and every path resolves to a file directly in the nonce's private folder, else a fixed reason. `owner_ledger_problem()` becomes `owner_folder_problem([LEDGER])`.
- [ ] **Tests:** the existing `--owner` cases in `tests/test_check_payments.py`; new: a store or log outside the folder refused, through a symlinked folder refused, `LCS_BOOKINGS_CSV` refused.

**Verify:** `.venv/bin/python tests/test_lcs_owner.py && .venv/bin/python tests/test_check_payments.py && .venv/bin/python tests/test_cc_actions.py`

### Task 2: the schema (`lcs_events.validate`)

**Files:** Create `scripts/bookings/lcs_events.py`, `tests/test_lcs_events.py`.

- [ ] **Step 1:** `KINDS = {(subject, kind): {field: checker}}` for every kind in the spec's tables, with `OWNER_ONLY`, `SCRIPT_ONLY` and `RESERVED` sets (the four later-PR kinds: `append` refuses them).
- [ ] **Step 2:** `validate(obj) -> obj` or `ValueError(<fixed phrase>)`: exactly the top-level keys (`note` optional), `v == 1`, `eid` and `prev` forms, `at` as UTC `Z`, `on` a real date not after `at`'s London date, `id` by subject (`@` refused), exactly the kind's fields, each through its checker (amounts `^\d{1,5}\.\d{2}$` and more than 0, `fees-accepted` at most `check_payments.FEE_CAP`, `fp8` `^([0-9a-f]{8})?$`, `clauses` 1–20 of `^[0-9a-f]{12}$`, words from their lists), `by` and `src` from their lists, `paid-in-full` with `by: script` only as `basis: bank`.
- [ ] **Step 3:** `dumps(obj)`: sorted keys, no spaces, one line, at most 1,024 bytes, else `ValueError`.
- [ ] **Tests:** one passing and at least two failing lines per kind; unknown key at top level and in `fields`; a string where a list goes; `"12.4"`, `"0.00"`, `"40.01"` (over `FEE_CAP`, refused when written) for fees; a name-shaped or email-shaped value in every string field refused; an over-long line.

**Verify:** `.venv/bin/python tests/test_lcs_events.py`

### Task 3: append, read and index

**Files:** Modify `scripts/bookings/lcs_events.py`, `tests/test_lcs_events.py`.

- [ ] **Step 1:** `log_path()` = `<LCS_PRIVATE_DIR or ~/lcs-private>/events.jsonl`, read at call time.
- [ ] **Step 2:** `append(subject, id, kind, fields, by, on=None, note=None, src="live", eid=None)`: build, validate, then under `lm.ledger_lock(log_path())` open `O_WRONLY|O_APPEND|O_CREAT|O_NOFOLLOW` at 0o600, `fstat` (regular, this uid, no group or other bits, else refuse), read the last line for `prev`, one `os.write`, `fsync`. Returns the `eid`. A random `eid` is `secrets.token_hex(8)`.
- [ ] **Step 3:** `read()`: open `O_NOFOLLOW`; skip and count lines that don't parse, fail `validate`, run over 1,024 bytes, or are a last line without `\n`; check the chain; return `(events, stats)` with `stats = {lines, skipped, chain_ok, broken_at, last_at}`. Cache on `(st_ino, st_size, st_mtime_ns)`. A missing file is `([], stats)`; an unreadable one is the same with `stats["unreadable"] = True`.
- [ ] **Step 4:** `index(events, today)`: `{(subject, id): [events in file order]}`, each marked `retracted` when a retract names it, and events with `on` after today left out. Readers skip retracted events for the reading but count them for "the family has events" and keep their note claims (spec, precedence rule 2).
- [ ] **Step 5:** `note_hash(clause)` = sha256 of the UTF-8 clause, first 12 hex.
- [ ] **Tests:** round trip; two processes appending 200 lines each at once (all lines valid, chain whole); a partial last line ignored; a symlinked or group-readable file refused on write and read; a retract hides its target; a future `on` is ignored until that day.

**Verify:** `.venv/bin/python tests/test_lcs_events.py`

### Task 4: `events.py verify` and `show`; repo hygiene

**Files:** Create `scripts/bookings/events.py`, `tests/test_events_cli.py`; modify `.gitignore`.

- [ ] **Step 1:** `verify`: prints lines, skipped, chain whole or "broken at line N", last written; exits 1 on a skipped line or a broken chain. (Events without their note and stale `notes-checked` hashes join it in Task 12.)
- [ ] **Step 2:** `show <booking|singer_invoice> <id>`: one line per event, `on`, kind, fields, `by`, `src`; never notes, names or anything from the CSVs.
- [ ] **Step 3:** `.gitignore`: add `events*.jsonl`.
- [ ] **Tests:** output shape; a broken chain exits 1; `show` for an unknown id prints "no recorded facts".

**Verify:** `.venv/bin/python tests/test_events_cli.py && python3 scripts/stage_site.py`

---

## PR 2: readers, events first (with no log, nothing changes)

### Task 5: booking facts and `check_payments`

**Files:** Modify `scripts/bookings/lcs_events.py`, `scripts/bookings/check_payments.py`; create `tests/state_cases.py`, `tests/test_state_twins.py`.

- [ ] **Step 1:** `lcs_events.booking_facts(ref, today, events=None)` returns a `Facts` with, per family, `has_events` and the reading from the spec's family table (close: `closed_on`, `fees`, `fee_days`; cancellation: `cancelled`; cancel settlement: `settled_on`; arrangement: `arranged`, `method`; noted paid: `part`, `full`; markers: `deposit_seen`, `reminded`, `review`), plus `claims` (the note hashes of every event, retracted ones included).
- [ ] **Step 2:** `check_payments.unclaimed(notes, claims)`: the notes' "; " clauses whose hash isn't claimed, rejoined. `assertions(text, value, today)` returns, per family, what that text asserts with today's patterns, or `None`.
- [ ] **Step 3:** Each facade function gains `facts=None` (default: `booking_facts` from the log): `is_cancelled`, `closed_on`, `fee_notes`, `fees_accepted`, `fee_pending`, `cancel_settled_on`, `open_rows`, and in `assess` the inputs `arranged`, `noted_hand`, `noted_full`, `noted_auto`, `reminded`. A family with events reads the facts; a family without reads the notes as now; markers are a union.
- [ ] **Step 4:** `held(r, facts=None)`: the families whose events disagree with the unclaimed clauses' assertions. In `assess`: when held, `out["held"]` lists them, `action` is `hand_check`, `record_in_books` is `[]`, `just_received` is false; `describe` adds "notes and recorded facts disagree: <family>". `collect` also reports a held closed or cancelled row.
- [ ] **Step 5:** `tests/state_cases.py`: for every note-driven case in `test_check_payments.py` and `test_cancel_contract.py`, a `(name, row, paid, today, events)` twin with neutral notes. `test_state_twins.py` asserts the same `assess` dict (bar `held`) from notes only, events only, and both (the events claiming the notes' clauses); plus, per family, a contradicting unclaimed clause holds it and a claimed one doesn't.
- [ ] **Tests:** the whole existing `tests/test_check_payments.py` unchanged; the twins.

**Verify:** `.venv/bin/python tests/test_check_payments.py && .venv/bin/python tests/test_state_twins.py && .venv/bin/python tests/test_cancel_contract.py`

### Task 6: `pipeline.py` and `upload_bookings.py`

**Files:** Modify `scripts/bookings/pipeline.py`, `scripts/ads/upload_bookings.py`, `tests/state_cases.py`.

- [ ] **Step 1:** `reviews_due` and `done_due` use `cp.closed_on(r)` instead of `cp.FULL_NOTE.search` (a fee-closed booking is closed for reviews too: bug 3), and skip a held row. `reviews_due`'s "already asked" check is the union of the review markers.
- [ ] **Step 2:** `upload_bookings.py` skips a held row with the line "held: notes and recorded facts disagree".
- [ ] **Tests:** the existing `test_pipeline.py` and `test_upload_bookings.py` unchanged; twins for the review markers; a fee-closed booking is review-due before `--apply`; a held booking is neither review-due nor done-due nor uploaded.

**Verify:** `.venv/bin/python tests/test_pipeline.py && .venv/bin/python tests/test_upload_bookings.py && .venv/bin/python tests/test_state_twins.py && .venv/bin/python tests/test_cancel_contract.py`

### Task 7: singer invoice facts

**Files:** Modify `scripts/bookings/lcs_events.py`, `scripts/bookings/singer_invoices.py`, `tests/state_cases.py`.

- [ ] **Step 1:** `invoice_facts(message_id, today, events=None)`: bank warnings (the latest `bank-warning`'s codes and `fp8`), bank trust (`bank-confirmed` `fp8`s), settlement, withdrawal (date, reason), paid-reply marker, claims.
- [ ] **Step 2:** With `facts=None` defaults: `is_trusted` (confirmed = a `bank-confirmed` whose `fp8` is `bank_fp[:8]`, else the column), `trust_label`, `account_trusted`, `ring_first` (codes `changed` or `differ` while `fp8` matches, else the column), `ring_first_in`, `live_warnings` (the codes' texts from the notes' matching clauses, or the codes' fixed words when the clause is gone), `is_withdrawn`, `is_open`, the A, B, B rule in `assess_new`, `print_books_due`'s THANKS DUE (union), `bill_verdict`'s bank input.
- [ ] **Step 3:** Held: an unclaimed bank alarm while the events say none, or an unclaimed "withdrawn" or "settled by hand" the events don't have. A held invoice is `ring_first` and `bill: no (held)`.
- [ ] **Tests:** the whole existing `tests/test_singer_invoices.py` and `test_singer_links.py` unchanged; twins for the confirmation bug in `50f2429d` (a confirmation clears every alarm on every invoice to that account), a rescan to new details voiding a confirmation, withdrawn, settled, thanked.

**Verify:** `.venv/bin/python tests/test_singer_invoices.py && .venv/bin/python tests/test_singer_links.py && .venv/bin/python tests/test_state_twins.py`

### Task 8: the whole suite

**Files:** none new.

- [ ] **Step 1:** Run every test file that imports the bookings scripts: `test_money_report.py`, `test_dashboard.py`, `test_cc_*.py`, `test_lcs_money.py`. Any change in output with no log is a bug in Tasks 5–7.

**Verify:** `for t in tests/test_*.py; do .venv/bin/python "$t" >/dev/null || echo "FAIL $t"; done; ./build.sh`

---

## PR 3: the migration

### Task 9: `events.py migrate` and `compare`

**Files:** Modify `scripts/bookings/events.py`; create `tests/test_events_migrate.py`.

- [ ] **Step 1:** `migrate` (dry run): for each ledger row and store row, walk the notes clause by clause with the pattern readers and propose events per the spec's migration section (dates, undated and out-of-order flags, `paid-in-full` basis and "writer unknown", `by` per kind, `note` claims, derived `eid`s), skipping any family that already has events for that subject. Write the report to `<private>/events-migration-<today>.txt` (mode 600: refs, kinds, dates, amounts, rule names and flags only) and print its totals and sha256.
- [ ] **Step 2:** `compare [--proposed]`: every row read notes-only and events-first (with the log, or with the dry run's proposed events added), printing `ref family notes→events` for each difference; exit 1 on any.
- [ ] **Step 3:** `migrate --apply --expect SHA --owner`: refuses without `lcs_owner.owner_confirmed()` and `owner_folder_problem([LEDGER, STORE, log])`; re-runs the dry run and refuses a different hash; appends the new events in note order; prints "N new events". A second run prints "0 new events".
- [ ] **Step 4:** Cancellation: emit `cancelled` and `reinstated` in text order only where `is_cancelled`'s rules count them, so the final state equals `is_cancelled(notes)`.
- [ ] **Tests:** the dry run writes only its report; `compare --proposed` finds nothing on a ledger and store built from every notes string in `tests/state_cases.py` and the existing test files; apply twice gives the same file; renaming the log gives the notes' reading back; `--apply` refused without the nonce, with a stale hash, with `LCS_BOOKINGS_CSV`.

**Verify:** `.venv/bin/python tests/test_events_migrate.py`

### Task 10: the Command Centre action

**Files:** Modify `command_centre/actions.py`, `command_centre/templates/health.html` (or the Runs and health page's panel); `tests/test_cc_actions.py`.

- [ ] **Step 1:** `MIGRATE_EVENTS`, a `ScriptAction` with `owner_nonce=True`: validation runs `events.py migrate` (dry run) and `compare --proposed`, refuses if compare finds a difference, and shows the totals, flags and hash; argv `["migrate", "--apply", "--expect", sha, "--owner"]`. Offered only while the log has no `src: migration` lines.
- [ ] **Tests:** exact argv; refused while compare differs; refused after a migration; the summary carries no note text.

**Verify:** `.venv/bin/python tests/test_cc_actions.py`

### Task 11: the owner applies it (owner step)

- [ ] **Step 1:** The owner opens Runs and health, reads the migration summary and flags, taps "Apply the events migration" with Face ID or Touch ID.
- [ ] **Step 2:** A session then runs the read-only checks.

**Verify:** `.venv/bin/python scripts/bookings/events.py verify && .venv/bin/python scripts/bookings/events.py compare` (both exit 0, compare prints nothing)

---

## PR 4: writers write events

### Task 12: `check_payments.py`

**Files:** Modify `scripts/bookings/check_payments.py`, `scripts/bookings/events.py`; `tests/test_check_payments.py`.

- [ ] **Step 1:** `--fact REF KIND [--on D] [--amount X] [--method M] [--scope S] [--owner]`: the kind must be a booking kind the caller may write (owner kinds need `--owner`, which needs the nonce and `owner_folder_problem`); `--on` defaults to today, refuses a future date or one more than 730 days back; `fees-accepted` keeps the Command Centre's cap. Inside `locked_rows(LEDGER)`: append the spec's phrase (with " (owner)" for the owner), then `lcs_events.append(..., note=note_hash(phrase))`; on a failed CSV write, the `write-failed` retract.
- [ ] **Step 2:** `--reminded` also appends `reminder-drafted`; `apply_notes` appends `deposit-seen` and `paid-in-full {basis: bank}` where `updated_notes` added those clauses.
- [ ] **Step 3:** `events.py verify` also lists events whose claimed clause is missing from the notes, and `notes-checked` hashes no clause matches.
- [ ] **Tests:** each kind writes its note and its event, claimed; the note reads the same fact with the log renamed; owner kinds refused without the nonce; a CSV write failure leaves a retract and the error message; `--note` unchanged.

**Verify:** `.venv/bin/python tests/test_check_payments.py && .venv/bin/python tests/test_state_twins.py && .venv/bin/python tests/test_events_cli.py`

### Task 13: `pipeline.py`

**Files:** Modify `scripts/bookings/pipeline.py`; `tests/test_pipeline.py`.

- [ ] **Step 1:** `note_review` appends `review-drafted` or `review-skipped {reason}` (reason `planner` or `unresolved`; any other word is refused, as the daily pass uses only these) with the claim, inside its `locked_rows`.
- [ ] **Tests:** each writes both; a second one is still refused.

**Verify:** `.venv/bin/python tests/test_pipeline.py`

### Task 14: `singer_invoices.py`

**Files:** Modify `scripts/bookings/singer_invoices.py`; `tests/test_singer_invoices.py`.

- [ ] **Step 1:** `scan` and `rescan` append `bank-warning {fp8, codes}` for the invoice (empty codes for a clean scan) and one for each older invoice `assess_invoice` flags, each claiming its warning clauses.
- [ ] **Step 2:** `thanked` → `paid-reply-drafted`; `withdrawn` → `withdrawn {reason}` (`by: owner` only with `--owner` and the nonce).
- [ ] **Step 3 (question 2):** `confirm` and `settled` require `--owner` with the nonce and write `bank-confirmed {fp8}` and `settled {amount}`. If the owner keeps the terminal route instead, they write `by: owner` without the nonce and rely on the deny rules in Task 15.
- [ ] **Tests:** every writer writes both; `confirm` refused without the nonce (per question 2) and on a changed fingerprint; the existing cases unchanged apart from the new flag.

**Verify:** `.venv/bin/python tests/test_singer_invoices.py && .venv/bin/python tests/test_state_twins.py`

### Task 15: Command Centre argv and Claude's permissions

**Files:** Modify `command_centre/actions.py`, `.claude/settings.json`; `tests/test_cc_actions.py`, `tests/test_prompt_allowlist.py`.

- [ ] **Step 1:** `HAND_CHOICES` maps each choice to a kind and its fields; `RESOLVE_HAND_CHECK`'s argv becomes `["--fact", ref, kind, "--on", day, …, "--owner"]`. `SINGER_CONFIRM`, `SINGER_SETTLED` (and `SINGER_WITHDRAWN`) gain `owner_nonce=True` and `--owner`.
- [ ] **Step 2:** `.claude/settings.json` allow: `Bash(.venv/bin/python scripts/bookings/check_payments.py --fact *)`, `Bash(.venv/bin/python scripts/bookings/events.py verify)`, `Bash(.venv/bin/python scripts/bookings/events.py show *)`, `Bash(.venv/bin/python scripts/bookings/events.py migrate)`, `Bash(.venv/bin/python scripts/bookings/events.py compare)`. Deny: `Write(~/lcs-private/events.jsonl)`, `Edit(~/lcs-private/events.jsonl)`, `Write(~/lcs-private/events.jsonl.lock)`, `Bash(*events.py migrate*--apply*)`, `Bash(*events.py retract*)`, `Bash(*events.py notes-checked*)`, and per question 2 `Bash(*singer_invoices.py confirm*)`, `Bash(*singer_invoices.py settled*)`.
- [ ] **Tests:** exact argv per choice; `tests/test_prompt_allowlist.py` gains the new allow rules and puts `events.py migrate --apply`, `retract`, `notes-checked` (and per question 2 `singer_invoices.py confirm` and `settled`) in its `NEVER` list; a check that the three `Write`/`Edit` deny rules are present.

**Verify:** `.venv/bin/python tests/test_cc_actions.py && .venv/bin/python tests/test_prompt_allowlist.py`

---

## PR 5: the Command Centre reads events

### Task 16: timelines, trust, held, Health

**Files:** Modify `command_centre/models.py`, `data.py`, `templates/booking.html`, `singers.html`, `today.html`, `health.html`, `macros.html`; `tests/test_cc_pages2.py`, `tests/test_cc_final.py`.

- [ ] **Step 1:** `ledger_timeline` adds one item per event (`on`, fixed words per kind, "you", "the assistant" or "migrated"), and skips note clauses an event claims.
- [ ] **Step 2:** The singer card and directory show the trust source from events ("confirmed by phone on D").
- [ ] **Step 3:** Today lists held bookings and invoices with the hand checks: the family, the notes' reading and the recorded one.
- [ ] **Step 4:** Health shows the log's `stats` (lines, last written, chain, skipped, unreadable).
- [ ] **Tests:** each page with a fixture log; no note text or name leaks beyond what the page already shows; a held row appears once.

**Verify:** `.venv/bin/python tests/test_cc_pages2.py && .venv/bin/python tests/test_cc_final.py`

### Task 17: undo and "the recorded facts are right"

**Files:** Modify `scripts/bookings/events.py`, `command_centre/actions.py`, templates; `tests/test_events_cli.py`, `tests/test_cc_actions.py`.

- [ ] **Step 1:** `events.py retract EID --owner` (the target must exist, be live and not a retract; writes "earlier entry undone D (owner)" to the row's notes and the event, under the CSV lock) and `events.py notes-checked SUBJECT ID HASH… --owner` (each hash must be an unclaimed clause of that row now).
- [ ] **Step 2:** Actions `UNDO_FACT` and `NOTES_CHECKED`, both `owner_nonce=True`, offered on the booking and singer pages and on a held row.
- [ ] **Tests:** argv; refusals (unknown or retracted target, a claimed hash, no nonce); a held booking is released by `notes-checked` and by recording the notes' reading.

**Verify:** `.venv/bin/python tests/test_events_cli.py && .venv/bin/python tests/test_cc_actions.py`

---

## PR 6: prompts and docs

### Task 18: the assistant uses `--fact`; `--note` refuses fact-shaped text

**Files:** Modify `.claude/agents/lcs-reply-drafter.md`, `scripts/bookings/check_payments.py`, `CLAUDE.md`, `docs/HANDOVER-2026-09-27-ads-analytics.md` (Appendix A step e, Appendix E), `docs/superpowers/specs/2026-09-28-business-automation-design.md` (notes conventions); `tests/test_check_payments.py`, `tests/test_prompt_allowlist.py`.

- [ ] **Step 1:** The reply drafter logs a cancellation with `check_payments.py --fact <ref> cancelled --on <YYYY-MM-DD>`. The Monday review (Appendix A, step e) does the same for a cancellation, and records "the client says they have paid" with `--fact <ref> noted-paid --scope part` (or `full` when the client says the whole fee), in place of its two `--note` lines. An arrangement the client states is `--fact <ref> arranged --method cash|cheque|third-party`.
- [ ] **Step 2 (question 3):** `--note` refuses text whose `assertions()` reading names the cancellation, arrangement or noted-paid family, with "record it with --fact <ref> <kind>; nothing written".
- [ ] **Step 3:** CLAUDE.md's Payments and Singer invoices bullets name the state log, `--fact` and the owner-only kinds; the handover and the business-automation spec point to the structured-state spec.
- [ ] **Tests:** each refused phrase names its `--fact` form; free text such as "4 singers, London" still passes; every command the prompts now name is allowed.

**Verify:** `.venv/bin/python tests/test_check_payments.py && .venv/bin/python tests/test_prompt_allowlist.py && ./build.sh`
