# Structured state for bookings and singer invoices: design

**Date:** 2026-09-29
**Status:** Approved by the owner, 29 Sep 2026: yes to all three questions at the end.
**Related:**
- [Business automation programme](2026-09-28-business-automation-design.md): its "Notes conventions" are the rules this design moves into structured records.
- [Command Centre](2026-09-28-command-centre-design.md): the owner nonce, the action registry, backups, and the push feed (a different file, see below).
- [Zoho Books design](2026-09-28-zoho-books-design.md): fee shortfalls and `record_in_books`.
- Plan: [2026-09-29-structured-state](../plans/2026-09-29-structured-state.md).
- Code: `scripts/bookings/check_payments.py`, `singer_invoices.py`, `pipeline.py`, `lcs_money.py`; `command_centre/actions.py`, `models.py`.

---

## Problem

The state of a booking and of a singer invoice lives in free-text `notes` columns, read back by regular expressions. `check_payments.py` alone has 21 patterns and six word lists for this, and each new fact needs a new phrase, a new pattern, a new entry in `RESERVED_NOTES` and a new Command Centre choice. Three recent bugs came from it:

1. **Warnings survived a confirmation** (fixed in `50f2429d`). A phone confirmation left the old CHANGED and NOT YET VERIFIED clauses in the notes, and trust was per row, so the Singers card stayed red and the Books bill stayed blocked.
2. **A fee shortfall had no way in** (fixed in `6078f968`) until a new reserved phrase, "short by fees £X accepted YYYY-MM-DD", was added and taught to every reader.
3. **A booking's close is read from phrases, in two ways.** `check_payments.closed_on` counts "paid in full YYYY-MM-DD" or a counting fee note; `pipeline.reviews_due` and `done_due` search for `FULL_NOTE` only. A booking closed by an accepted fee is closed for chasing but not for reviews until a later `--apply` adds "paid in full".

## Goals

1. Each fact about a booking or a singer invoice is one structured, validated line in an append-only log, with its date and who recorded it.
2. Nothing changes on day one. Readers read the log first and fall back to today's pattern readers for anything the log doesn't cover.
3. The notes stay the human record: every writer still writes its note, in the same words, under the same lock.
4. Owner facts keep the owner barrier (the Command Centre's one-time nonce after a passkey tap).
5. No names, emails or bank numbers in the log.
6. A new kind of fact is a new line in a schema table, not a new pattern.

## Non-goals

- Replacing the CSVs. `bookings.csv`, `singer-invoices.csv` and `enquiries.csv` keep every column and stay the source for names, amounts, dates and payment matches.
- Changing any payment rule. `check_payments.assess` keeps its state order line for line; only its inputs come from the log.
- Structured columns that already work: `paid_on`, `paid_amount`, `paid_ref`, `paid_verified` and `booking_ref` in the singer store.
- The `PENDING` prefix (the Google Ads upload gate) and the enquiry sheet's `quoted YYYY-MM-DD` notes. Both stay as they are.
- Non-bank scan warnings ("amount not found", "could not read …") stay in the singer notes, where `bill_verdict` reads them.
- Editing or deleting a recorded fact. A mistake is withdrawn with a `retract` line.
- Anything reaching Books, Starling, Zoho Mail or the push feed.

## The note-driven rules today, and their events

Every rule that reads or writes `notes` to decide something, and the event that replaces it. "Union" and "events first" are defined under [Reading](#reading-events-first).

### Bookings (`check_payments.py` unless named)

| # | Rule and code | Written by | What it decides | Event |
|---|---|---|---|---|
| B1 | `is_pending`: notes start `PENDING` | `assistant_io.py ledger-add` | Held back from the Ads upload until the deposit is seen; `--apply` replaces it | None: stays a prefix. `--apply` also writes `deposit-seen` |
| B2 | `AUTO_NOTE` "deposit seen YYYY-MM-DD (Starling)" | `--apply` | `noted_auto`: NOTED_PAID with nothing in the feed, CHECK_PAYMENT with an unconfirmed payment; removed before reading the owner's words | `deposit-seen` (union) |
| B3 | `NOT_YET_SEEN` "deposit not yet seen" | assistant, by hand | Dropped when the deposit is seen; a negation for B7 | None (note hygiene) |
| B4 | `MARK_NOTE` and `assess`'s `reminded`: "reminder drafted", "balance reminder drafted", "receipt drafted" | `--reminded REF --kind` | One deposit and one balance reminder, one receipt; `just_received` | `reminder-drafted {what}` (union) |
| B5 | `FULL_NOTE` "paid in full YYYY-MM-DD" | `--apply` (the bank covers it); the owner in the Command Centre or by hand | Closes: `open_rows`, `closed_on`, PAYMENT_AFTER_CLOSE, `received_since`, `fee_pending`; CLOSED in the Command Centre and the dashboard | `paid-in-full {basis}` |
| B6 | `FEES_NOTE` "short by fees £X accepted YYYY-MM-DD", at most £40 (`FEE_CAP`; owner decision, 29 Sep 2026: was £25), not after today: `fee_notes`, `fees_accepted`, `fee_pending` | The owner, `--note … --owner` | PAID_IN_FULL with `balance` 0; the fee as Books bank charges on the last payment; closes like B5 | `fees-accepted {amount}` |
| B7 | `NOT_PAID`, `PAID_WORD`, `hand_notes` → `noted_hand` | The Monday review (`--note "paid per client email D"`), the assistant's handwritten "deposit seen D", the owner by hand | NOTED_PAID (a hand check) when nothing confident is in the bank | `noted-paid {scope: part}` |
| B8 | `FULL_PAID`, `REST_PAID`, `CLAUSE`, `REST_WORD`, `OTHER_PART`, `POUNDS`, `full_paid` → `noted_full` | The same | With a deposit in the bank, only a note of the whole fee stops the balance chase | `noted-paid {scope: full}` |
| B9 | `CANCEL_WORD`, `CANCELLING`, `IF_WORDS`, `MAYBE_WORDS` in `is_cancelled` | The reply drafter (`--note "cancelled D by client email"`), the Monday review (`--note "cancelled D"`), the owner | The row drops out of chasing, uploads, reviews and counts; "name, cancelled booking" matching; PAYMENT_ON_CANCELLED | `cancelled` |
| B10 | `RESUMED`, `DOUBT_WORDS`, `ELSEWHERE_WORDS`, `CALL_WORDS` in `is_cancelled` | The owner only (reserved) | Undoes B9 | `reinstated` |
| B11 | `SETTLED_NOTE` "deposit kept / refunded / payment, refund or deposit checked YYYY-MM-DD": `cancel_settled_on` | The owner only (reserved) | On a cancelled booking, payments up to that day leave the hand check | `deposit-kept`, `refunded`, `payment-checked` |
| B12 | `ARRANGED_NOTE`, `ARRANGED_PAID`, `NOT_ARRANGED`, `NEGATION`, `arranged_notes` | The assistant, the owner | ARRANGED (never chased or thanked; a hand check from 7 days before), `arranged_no_deposit`; the clause is removed before B7 | `arranged {method}` |
| B13 | `REVIEW_NOTE` "review request drafted / skipped" | `pipeline.py reviewed`, `review-skipped` | `reviews_due` stops listing it; the Command Centre tags the clause | `review-drafted`, `review-skipped {reason}` (union) |
| B14 | `RESERVED_NOTES`, `reserved_note` | — | `--note` refuses B2, B4–B6, B10, B11, B13 and `PENDING` without `--owner` | Carries over as "who may write which kind" |
| B15 | " (owner)" appended by `--owner` | `--note … --owner` | Nothing (a human record) | `by: owner` |
| B16 | `pipeline.reviews_due`, `done_due` read `FULL_NOTE` directly | — | Bug 3 above | Both read the close through one function, `closed_on` |

### Singer invoices (`singer_invoices.py`)

| # | Rule and code | Written by | What it decides | Event |
|---|---|---|---|---|
| S1 | "BANK DETAILS CHANGED" (three forms: since the last invoice, against a Starling payee, against an older invoice scanned out of order) and the column `bank_changed=yes` | `scan`, `rescan` (`assess_new`, `assess_invoice`) | `ring_first`, `ring_first_in`, the summary count, `status`, the red card and Today panel, `bill: no (bank warning)` | `bank-warning {codes: [changed]}` |
| S2 | `DIFFER` and `bank_changed=yes` | `scan`, `rescan` | The same | code `differ` |
| S3 | `NEW_DETAILS`, `NOT_YET_VERIFIED` | `scan`, `rescan` | The same (both contain "BANK DETAILS") | codes `new`, `not-yet-verified` |
| S4 | "no bank details found on the invoice", "no bank details on the invoice: compare …" | `scan`, `rescan` | Shown by `live_warnings`; not a bill block | code `no-details` |
| S5 | `TRUSTED_DIFFER` | `scan`, `rescan` | Nothing (information) | None |
| S6 | `BANK_ALARMS`, `KEEP_NOTES`, `live_warnings` | — | Which clauses still show; alarms hidden once the account is trusted | Derived from S1–S4 and S7 |
| S7 | "bank details confirmed by phone D" and `bank_confirmed=yes`; `rescan` clears both when the details change | `confirm` (the owner) | `is_trusted`, `trust_label`, `account_trusted`, bill verdict | `bank-confirmed {fp8}` |
| S8 | "settled by hand" with `paid_verified=no` | `settled` (the owner) | Paid, never trusted | `settled {amount}` |
| S9 | Column `withdrawn` and "withdrawn D (reason)" | `withdrawn` | `is_withdrawn`, `is_open`: out of unpaid, status, the money line, bills | `withdrawn {reason}` |
| S10 | "paid reply drafted D", read as a substring by `print_books_due` | `thanked` | THANKS DUE stops | `paid-reply-drafted` (union) |
| S11 | "rescanned D" | `rescan` | Nothing | None: the rescan's own `bank-warning` line records it |
| S12 | In `assess_new`, "A, B, B": the last invoice's `bank_changed=yes` while it is open | — | No second CHANGED flag | Reads the derived changed flag |

### Command Centre

| # | Rule | Event |
|---|---|---|
| C1 | `HAND_CHOICES` maps each choice to a phrase for `--note … --owner` | Each choice maps to a kind, passed as `--fact` (below) |
| C2 | `models.ledger_timeline` splits the notes on ";" and tags `REVIEW_NOTE` clauses | Timeline items come from events; clauses an event claims are not shown twice |

## The event log

`~/lcs-private/events.jsonl` (`LCS_PRIVATE_DIR` moves it), mode 600 in the mode-700 private folder. Not to be confused with `~/lcs-private/command-centre/events.jsonl`, the Command Centre's push feed written by `cc_event.py`: the code calls this one the state log and that one the push feed, and neither reads the other.

One JSON object per line, UTF-8, keys sorted, no spaces, ending `\n`, at most 1,024 bytes. The owner's outline (`at`, `subject`, `id`, `kind`, `fields`, `by`) plus six keys the readers need:

| Key | Value |
|---|---|
| `v` | `1` |
| `eid` | 16 lower-case hex: random for a live write; `sha256("migration|" + subject + "|" + id + "|" + kind + "|" + on + "|" + claim)[:16]` for the migration, so a rerun adds nothing |
| `prev` | The first 16 hex of the sha256 of the previous line's bytes, `""` on the first line: the audit log's chain, so a deleted or edited line shows |
| `at` | When it was written, UTC, `YYYY-MM-DDTHH:MM:SSZ` |
| `on` | The business day the fact belongs to, `YYYY-MM-DD`, Europe/London; never after the London date of `at` |
| `subject` | `booking` or `singer_invoice` |
| `id` | A booking ref, `^[A-Za-z0-9][A-Za-z0-9-]{0,19}$`, in the ledger when written; or a singer invoice's message id, `^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$` (no `@`, so never an email address), in the store when written |
| `kind` | One of the kinds below, for that subject |
| `fields` | Exactly the kind's keys, each in its form below; an unknown or missing key refuses the line |
| `by` | `owner` or `script` |
| `src` | `live` or `migration` |
| `note` | Optional: the first 12 hex of the sha256 of the note clause written with it (the clause as appended, UTF-8). The event "claims" that clause |

Every value is a date, an amount, an id, a hash or a word from a fixed list. No field takes free text, so no name, email or bank number can reach the log. Amounts are strings `^\d{1,5}\.\d{2}$`, more than 0. `fp8` is the first 8 hex of the 16-hex keyed bank fingerprint (not a bank number; the confirm action already shows the whole fingerprint), or `""`.

### Kinds

The note phrase is the one written today, so the pattern readers read the same fact. `D` is `on`.

**Bookings**

| Kind | Fields | By | Written by | Note phrase |
|---|---|---|---|---|
| `paid-in-full` | `basis`: `bank` or `owner` | script (`bank`, from `--apply` only), owner (`owner`) | `--apply`; Command Centre "paid in full" | "paid in full D"; "paid in full D (owner)" |
| `fees-accepted` | `amount`: at most `40.00` (`FEE_CAP`, owner decision 29 Sep 2026; checked when written, so a later lower cap never reopens a booking) | owner | Command Centre "short by transfer fees" | "short by fees £X accepted D (owner)" |
| `noted-paid` | `scope`: `part` or `full` | script, owner | `--fact` (the Monday review, from the client's own message) | "paid per client email D" (the Monday review's phrase today); "balance paid per client email D" |
| `arranged` | `method`: `cash`, `cheque` or `third-party` | script, owner | `--fact`; Command Centre | "balance payable in cash on the day (arranged D)", "… by cheque …", "balance to be paid by another payer (arranged D)" |
| `cancelled` | none | script, owner | The reply drafter (`--fact`); Command Centre | "cancelled D by client email"; "cancelled D (owner)" |
| `reinstated` | none | owner | Command Centre | "reinstated D (owner)" |
| `deposit-kept`, `refunded`, `payment-checked` | none | owner | Command Centre | "deposit kept D (owner)" and so on |
| `deposit-seen` | none | script | `--apply` | "deposit seen D (Starling)" |
| `reminder-drafted` | `what`: `deposit`, `balance` or `receipt` | script | `--reminded` | "reminder drafted D", "balance reminder drafted D", "receipt drafted D" |
| `review-drafted` | none | script | `pipeline.py reviewed` | "review request drafted D" |
| `review-skipped` | `reason`: `planner` or `unresolved` | script | `pipeline.py review-skipped` | "review request skipped D (reason)" |
| Reserved for the later PR: `payment-confirmed`, `discount-agreed`, `goodwill-reduction`, `overpayment-refunded` | see [Later](#later-pr-how-each-feature-uses-events) | owner | Command Centre | The writer refuses them until that PR |

**Singer invoices**

| Kind | Fields | By | Written by | Note phrase |
|---|---|---|---|---|
| `bank-warning` | `fp8`; `codes`: a list, possibly empty, from `changed`, `differ`, `new`, `not-yet-verified`, `no-details` | script | Every `scan` and `rescan` (an empty list records a clean scan), and the out-of-order CHANGED flag on another invoice | The existing warning texts |
| `bank-confirmed` | `fp8` (must be the invoice's current `bank_fp[:8]` when written) | owner | Command Centre "confirm bank details" | "bank details confirmed by phone D" |
| `settled` | `amount` | owner | Command Centre "mark paid" | "settled by hand" |
| `withdrawn` | `reason`: `not-ours`, `duplicate`, `sent-in-error` or `other` (any other one-word reason the CLI takes is recorded as `other`; the note keeps the word) | script, owner | `withdrawn` | "withdrawn D (word)" |
| `paid-reply-drafted` | none | script | `thanked` | "paid reply drafted D" |

**Both subjects**

| Kind | Fields | By | Written by | Note phrase |
|---|---|---|---|---|
| `retract` | `target`: an `eid` of the same subject and id; `why`: `mistake` or `write-failed` | owner (`mistake`); the target's own writer, in the same run (`write-failed`) | Command Centre "undo"; the library | "earlier entry undone D (owner)" (no kind name in it, so the fallback reads no fact from it) |
| `notes-checked` | `clauses`: 1 to 20 note hashes (12 hex) | owner | Command Centre, on a held booking or invoice | "notes checked D (owner)" |

A retracted event is skipped by every reader. A `retract` can't be retracted: record the fact again.

## Reading: events first

A small library, `scripts/bookings/lcs_events.py`, reads the log once per process (cached on the file's inode, size and mtime), validates every line, skips and counts bad ones (a line that doesn't parse, fails the schema, is over 1,024 bytes, or is a last line without `\n`, which is a write in progress), drops retracted events and events dated after today, and indexes the rest by `(subject, id)`.

### Families

Kinds group into families. A family decides one question.

| Subject | Family | Kinds | How the events decide it |
|---|---|---|---|
| booking | close | `paid-in-full`, `fees-accepted` (later also `discount-agreed`, `goodwill-reduction`, `overpayment-refunded`) | `closed_on` = the latest `on`; `fees_accepted` = the latest `fees-accepted` amount, as `fee_notes` does now |
| booking | cancellation | `cancelled`, `reinstated` | The later of the two by `(on, file order)` |
| booking | cancel settlement | `deposit-kept`, `refunded`, `payment-checked` | `cancel_settled_on` = the latest `on` |
| booking | arrangement | `arranged` | Arranged, with the method |
| booking | noted paid | `noted-paid` | `noted_hand` for any; `noted_full` for `full` |
| booking | markers | `deposit-seen`, `reminder-drafted`, `review-drafted`, `review-skipped` | Union: set if either the events or the notes say so |
| singer_invoice | bank warnings | `bank-warning` | The latest line's codes, only while its `fp8` is the invoice's current `bank_fp[:8]` |
| singer_invoice | bank trust | `bank-confirmed` | Confirmed while its `fp8` is the invoice's current `bank_fp[:8]` (a rescan to other details voids it, as clearing `bank_confirmed` does today) |
| singer_invoice | settlement | `settled` | Settled by hand |
| singer_invoice | withdrawal | `withdrawn` | Withdrawn on `on` |
| singer_invoice | markers | `paid-reply-drafted` | Union |

The existing functions stay the only way in, so every script and page that uses them changes with them: `check_payments.is_cancelled`, `closed_on`, `fee_notes`, `fees_accepted`, `fee_pending`, `cancel_settled_on`, `open_rows` and `assess`'s inputs (`arranged`, `noted_hand`, `noted_full`, `noted_auto`, `reminded`); `pipeline.reviews_due` and `done_due` (through `closed_on`, which fixes bug 3); `singer_invoices.is_trusted`, `trust_label`, `account_trusted`, `ring_first`, `ring_first_in`, `live_warnings`, `is_withdrawn`, `is_open`, `bill_verdict`'s inputs and `print_books_due`. Each takes an optional `facts` argument (tests pass it; callers omit it and get the log). `upload_bookings.py`, `weekly_review.py`, `economics.py`, `dashboard.py` and the Command Centre need no change of their own beyond the "held" rule below.

### Precedence when events and notes disagree

1. **A family with no events for this subject** is read from the notes, exactly as today. Before the migration, that is every family of every row, so nothing changes on day one.
2. **A family with events** (ones retracted by mistake count: they are history, and keep their note claims) is read from the events. A fact undone by a write-failed retract (its own writer, in the same run) never happened: it counts for nothing and claims no note, so a note that landed after all is read or held as usual. The notes are then read only for disagreement (rule 4).
3. **Markers are a union.** A reminder, receipt, review, deposit-seen or "Paid!" marker counts if either side has it. A marker only stops a repeat, so the union can never cause a chase.
4. **Disagreement holds the subject.** The notes' *unclaimed* clauses (clauses no event claims by its `note` hash, so hand edits and legacy text) are read with today's patterns, per family, as an assertion or nothing: "cancelled" or "reinstated"; "closed"; "settled"; "arranged"; "paid (part or full)"; for a singer invoice, "a bank alarm". When a family has events and its unclaimed clauses assert something the events don't say, the booking or invoice is **held**:
   - a held booking's `action` is `hand_check` with the reason "notes and recorded facts disagree: <family>"; it gets no reminder, receipt, `record_in_books` entry, review request, `done-due` line or Ads upload until the owner resolves it;
   - a held singer invoice shows "ring before paying" and `bill: no (held)`.
   The owner resolves it in the Command Centre either way: record the notes' reading as an event, or confirm the recorded facts, which writes `notes-checked` claiming those clauses.
5. **An event without its note** (the crash window below) is read like any other event; `events.py verify` lists it.

The patterns stay in the code as the fallback and the disagreement reader. They are never deleted in this work.

## Writing

### Lock and order

- The log has its own lock, `lcs_money.ledger_lock(events.jsonl)` (an flock on `events.jsonl.lock`, mode 600), taken only inside `lcs_events.append()`, which calls nothing else. Lock order is always the CSV's lock (`locked_rows(LEDGER)` or `locked_rows(STORE)`) first, then the log's. Neither lock is re-entrant; no writer takes a CSV lock while holding the log's.
- A writer, inside `locked_rows`:
  1. validates and edits the row (the note, and any column) in memory;
  2. appends the event: one `os.write` of the whole line to a descriptor opened `O_WRONLY | O_APPEND | O_CREAT | O_NOFOLLOW`, mode 600, then `fsync`; the file must be a regular file owned by this user with no group or other bits, else it refuses and nothing is written;
  3. leaves the block, so `locked_rows` writes the CSV atomically (`write_csv`, `os.replace`).
- If step 2 fails, the block raises and `locked_rows` writes nothing: neither changed.
- If step 3 fails, the writer appends `retract {target, why: write-failed}` under the same lock and reports the failure. If that fails too, it reports "fact recorded, note not written: run events.py verify". The event decides either way (precedence rule 5), and the missing note is only the human record.
- Readers take no lock. A line is one `write` to an append-only file; a reader ignores a last line without `\n`.

### Writers

| Command | Event | Change |
|---|---|---|
| `check_payments.py --fact REF KIND [--on D] [--amount X] [--method M] [--scope S] [--owner]` | Any booking kind the caller may write | New. Builds the note phrase itself from the kind (the table above), so no caller passes a phrase. `--on` defaults to today; a date after today, or more than 730 days back, is refused |
| `check_payments.py --reminded REF --kind K` | `reminder-drafted` | Adds the event |
| `check_payments.py --apply` | `deposit-seen`, `paid-in-full {basis: bank}` | Adds the events in `apply_notes`, only where `updated_notes` changes the notes |
| `check_payments.py --note REF TEXT` | None | Unchanged: free text only. In the last rollout step it refuses text whose pattern reading asserts a family that has a `--fact` kind, naming the `--fact` form (question 3) |
| `pipeline.py reviewed`, `review-skipped` | `review-drafted`, `review-skipped` | Adds the event |
| `singer_invoices.py scan`, `rescan` | `bank-warning` (and one for an older invoice flagged out of order) | Adds the event |
| `singer_invoices.py confirm --expect-fp FP --owner` | `bank-confirmed` | Adds the event; needs the nonce (question 2) |
| `singer_invoices.py settled ID D --owner` | `settled` | The same |
| `singer_invoices.py withdrawn ID REASON [--owner]` | `withdrawn` | Adds the event; `by: owner` only with the nonce |
| `singer_invoices.py thanked` | `paid-reply-drafted` | Adds the event |
| `events.py retract EID --owner`, `events.py notes-checked SUBJECT ID HASH… --owner` | `retract`, `notes-checked` | New, Command Centre only |
| `events.py migrate [--apply --expect SHA --owner]` | Migration events | New (below) |

`events.py` also has `verify` (schema, chain, events without their note, notes-checked hashes that no longer match a clause) and `show SUBJECT ID` (the facts for one booking or invoice: kinds, dates, amounts, who; never notes). Both are read-only.

### Who may write which kind

| Kind | `by: script` | `by: owner` |
|---|---|---|
| `cancelled`, `arranged`, `noted-paid` | Yes (the assistant, from a client's own message) | Yes |
| `paid-in-full` | Only `basis: bank`, only from `--apply` when `assess` says PAID_IN_FULL from confident payments | `basis: owner` |
| `fees-accepted`, `reinstated`, `deposit-kept`, `refunded`, `payment-checked`, `notes-checked`, `retract {why: mistake}` | No | Yes |
| `deposit-seen`, `reminder-drafted`, `review-drafted`, `review-skipped`, `bank-warning`, `paid-reply-drafted` | Yes | No (nothing for the owner to record) |
| `bank-confirmed`, `settled` | No | Yes |
| `withdrawn` | Yes (it is on Claude's allowlist today) | Yes |

`by: owner` is written only when the process proved it: `--owner` plus the Command Centre's one-time nonce, exactly as `check_payments.py --note --owner` does now. `owner_confirmed` and `owner_ledger_problem` move from `check_payments.py` into a shared `scripts/bookings/lcs_owner.py`, and the folder check covers the log too: with `--owner`, `LCS_BOOKINGS_CSV` is refused and the ledger, the singer store and the log must all sit in the nonce's private folder. An owner kind without the nonce is refused and nothing is written.

## Migration

A one-off, owner-approved step, run after the readers ship and before the writers do, so the log starts with the legacy facts.

1. **Dry run.** `events.py migrate` reads the ledger and the singer store and, for each row, runs the pattern readers clause by clause and lists the events they imply: subject, id, kind, `on`, fields, which rule fired, and flags. It writes nothing but the report, `~/lcs-private/events-migration-<date>.txt` (mode 600), and prints its sha256. It prints refs, kinds, dates, amounts and rule names only, never note text.
2. **Dates.** An event takes the first ISO date in its clause. An undated clause takes the `on` of the fact before it in the same notes, or the invoice date (the received date for a singer invoice), and is flagged "undated". A date earlier than the fact before it is raised to that one, so the log's order is the notes' order, and flagged "out of order". Dates after today are left out, as the readers ignore them now.
3. **Families already recorded are skipped.** The migration writes a family for a subject only when that family has no events for it, so a rerun, or a run after live writes, never contradicts a recorded fact.
4. **Compare.** `events.py compare` reads every row twice, once from the notes only and once events first, and prints each ref and family whose reading differs (none should). It runs on the dry run's proposed events before the apply, and on the log after it.
5. **Apply.** In the Command Centre, "Apply the events migration" shows the report's totals, its flags and its hash; after the owner's passkey it runs `events.py migrate --apply --expect <sha256> --owner` with the nonce. The script re-runs the dry run and refuses if the hash differs (the ledger changed since). Events carry `src: migration`, derived `eid`s, `note` claims for the clauses they came from, and `by: owner` for the owner-only kinds (only the owner could have written those phrases: `--note` refuses them without `--owner`), `by: script` for the rest. "Paid in full D" is `basis: owner, by: owner` when the clause ends "(owner)", else `basis: bank, by: script`, flagged "writer unknown" (the owner may have typed it): the reading is the same either way.
6. **Idempotent.** A second apply writes nothing and says "0 new events".
7. **Reversible.** Rename or delete `events.jsonl` and every reader falls back to the notes, as today. That is a full rollback until the writers ship, and still one afterwards for everything but retractions, `notes-checked` claims and owner corrections of a misread note, because every writer keeps writing its note. Once the later PR adds kinds with no pattern (a discount, a confirmed payment), deleting the file is no longer a rollback: restore it from the backup instead.

## Security

- **The file.** Mode 600, in the mode-700 private folder; the lock file mode 600. Writers open it `O_NOFOLLOW` and refuse a symlink, another owner or any group or other bit. Readers open it `O_NOFOLLOW` too; an unreadable log reads as absent (today's behaviour) and shows red on the Health page.
- **No personal data.** The schema has no free-text field; the validator refuses any unknown key and any value outside its pattern, on write and on read. A `note` hash is 48 bits of a sha256 of one clause. Bank details appear only as `fp8`.
- **Owner facts** need the nonce (above). No allowlisted command can write an owner kind or a `retract {why: mistake}`.
- **Claude's permissions** (`.claude/settings.json`):
  - allow: `check_payments.py --fact *` (owner kinds are still refused without the nonce, as `--note *` is today), `scripts/bookings/events.py verify`, `events.py show *`, `events.py migrate` and `events.py compare` (both read-only);
  - deny: `Write(~/lcs-private/events.jsonl)`, `Edit(~/lcs-private/events.jsonl)`, `Write(~/lcs-private/events.jsonl.lock)`, `Bash(*events.py migrate*--apply*)`, `Bash(*events.py retract*)`, `Bash(*events.py notes-checked*)`, and (question 2) `Bash(*singer_invoices.py confirm*)`, `Bash(*singer_invoices.py settled*)`, as `Write(~/lcs-private/command-centre/**)` is denied now.
  - Residual risk, as in the Command Centre design: a process running as the owner outside Claude's tools, or a command the owner approves at a prompt, can still write the file.
- **Backups.** The nightly `cc_backup.py` archive already covers `~/lcs-private` (only caches, runs, the mirror and the backups folder are left out), so the log and its lock are in it. Restore `bookings.csv`, `singer-invoices.csv` and `events.jsonl` from the same night: a mismatched pair shows up as held bookings, not wrong chases.
- **The repo.** New code is under `scripts/`, which `stage_site.py` keeps private. `.gitignore` gains `events*.jsonl` beside `bookings*.csv`.

## Command Centre

- **Reads.** The booking timeline shows each event as an item with its `on` date, fixed words per kind and who recorded it ("you", "the assistant", "migrated"); note clauses an event claims aren't shown again, and unclaimed clauses show as notes. The singer card shows how an account is trusted ("confirmed by phone on D"). Held bookings and invoices appear on Today with the hand checks, with both readings side by side. Health gains a line: lines, last written, chain whole or broken at line N, lines skipped.
- **Actions.** "Resolve hand check" passes `--fact <kind>` instead of a phrase. Singer confirm and settle pass `--owner` with the nonce (withdraw too). New: "Undo a recorded fact" (`retract`), "The recorded facts are right" (`notes-checked`) and "Apply the events migration". Each has a server-built summary, a passkey tap and an audit line, as every action does.
- The app never writes the log itself: it runs the scripts, as for the ledger.

## Later PR: how each feature uses events

- **Confirm a payment.** `payment-confirmed {item, amount}` (owner): `item` is the Starling feed item's uid. `match` treats that feed item as a confident payment for this booking (`how: owner`), so a CHECK_PAYMENT resolves without a note.
- **More shortfall reasons.** `discount-agreed {amount}` and `goodwill-reduction {amount}` lower what is due; `overpayment-refunded {amount}` lowers what was received. They join the close family: the booking reads PAID_IN_FULL when confident payments plus accepted reductions reach its value. Books handling is decided in that PR.
- **Singer pay list.** Open invoices sorted by trust from the bank-trust and bank-warning families: "ready to pay" or "ring first".
- **Sync strip with retry.** Reads the caches' own stamps; it needs no events. Each row may show the last fact recorded (`at`).
- **Alerts on silence.** Sync-stale reads cache stamps. Books-disagree pushes when the close family says closed and Books shows a balance, or the reverse, using `at` for "since when".
- **Enquiry ageing.** Reads `enquiries.csv`; it stops ageing an enquiry whose booking has a `cancelled` or close event.
- **Marketing panels.** Cost per booking already goes through `is_cancelled` and `closed_on`, so it follows the events with no change.

## Testing

- **Every existing test keeps passing unchanged.** Each uses a temp `LCS_PRIVATE_DIR` with no log, so every family falls back to the notes (rule 1).
- **Twin cases.** Each note-driven case in `test_check_payments.py`, `test_singer_invoices.py`, `test_pipeline.py` and `test_cancel_contract.py` gets a twin in a shared table (`tests/state_cases.py`): the same row with neutral notes and the equivalent events. `tests/test_state_twins.py` runs each case three ways (notes only, events only, both agreeing) and asserts the same assessment, state, action, `record_in_books`, warnings and bill verdict.
- **Disagreement.** For each family, an unclaimed clause that contradicts the events holds the subject: `hand_check`, no reminder, no Books line, no review, no upload; `notes-checked` releases it; a claimed clause never holds.
- **The library** (`tests/test_lcs_events.py`): every kind's fields, bad values, unknown keys, `@` in an id, digit runs in a word field, over-long lines, a partial last line, two processes appending at once (every line intact, the chain whole), a symlink or group-readable file refused, future `on` ignored, retract.
- **Writers:** each writes its note and its event under the lock; a CSV write that fails after the append leaves a `write-failed` retract; owner kinds refused without the nonce and with `LCS_BOOKINGS_CSV`.
- **Migration:** a dry run writes nothing but its report; apply twice gives the same file; `compare` finds no difference on a ledger built from every note in the existing tests; renaming the file restores the notes' reading.
- **Command Centre:** timelines, the held panel, the new argv for each action, and the new actions' refusals.

## Rollout

Each step is its own pull request, reviewed and merged before the next.

1. **Library.** `lcs_events.py`, `lcs_owner.py`, `events.py verify` and `show`. No reader uses them yet.
2. **Readers.** The facade functions read events first; `reviews_due` and `done_due` go through `closed_on`; the twin and disagreement tests. With no log, nothing changes.
3. **Migration.** `events.py migrate` and `compare`, and the Command Centre action. The owner reads the dry run and applies it; `compare` then shows no difference.
4. **Writers.** Every writer above, the settings allow and deny rules, and the singer commands' `--owner`.
5. **Command Centre.** Timelines, the held panel, Health, and the undo and notes-checked actions.
6. **Prompts.** The reply drafter and the Monday review (handover Appendix A, step e) use `--fact` for cancellations, arrangements and "the client says they have paid"; `--note` then refuses fact-shaped text. CLAUDE.md, the handover's Appendix E and the business-automation spec's notes conventions point here.

## Owner decisions (29 Sep 2026)

The owner answered yes to each question below: hold on disagreement; singer confirm and settle from the Command Centre only; `--note` refuses fact-shaped text.

1. **Hold on disagreement.** Once a booking has recorded facts in a family, a phrase typed into the ledger by hand no longer acts by itself: the booking is held for you to confirm in the Command Centre. *Recommendation:* yes. The alternative (the recorded facts win silently) would ignore your hand edits without telling you.
2. **Singer confirm and settle from the Command Centre only.** They would need the nonce, so `singer_invoices.py confirm` in a terminal stops working (CLAUDE.md now says you run it by hand after ringing the singer), and Claude is denied both commands. *Recommendation:* yes. The Command Centre action already binds the whole fingerprint; if the app is down, setting `bank_confirmed` to yes in the CSV still works through the fallback while that invoice has no `bank-confirmed` event.
3. **`--note` refuses fact-shaped text** once the prompts use `--fact` (step 6), so a cancellation or a "client says paid" can't be recorded only as free text. *Recommendation:* yes, with the refusal naming the `--fact` form, so the assistant corrects itself in the same run.
