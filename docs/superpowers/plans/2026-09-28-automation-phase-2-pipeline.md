# Automation Phase 2 (Pipeline) Implementation Plan

> **For agentic workers:** the code (Tasks 1–2) is built and tested on `claude/phase-2-pipeline`. Task 3 is the wiring step: it edits files other agents also touch, so it runs separately, after this branch merges. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track every enquiry from first message to booking or loss:
- a private pipeline sheet;
- quote follow-ups 5 days after the quote and 10 days after the first chase, then "lost" 10 days after the second;
- one review request after each paid event (never after a funeral);
- a diary check before drafting;
- a cancellation log.

**Architecture:** One script, `scripts/bookings/pipeline.py`, owns `~/lcs-private/enquiries.csv`. It reuses `lcs_money` (`PRIVATE`, `LEDGER`, `read_csv`, atomic mode-600 `write_csv`, `ledger_lock`) and `check_payments` (`is_cancelled`, `FULL_NOTE`, `header`). The enquiry assistant (handover Appendix E) calls it. The Monday report and the Phase 5 dashboard import the pure `summary_dict(rows, since)`. The diary check and cancellations need no new code: they use the Google Calendar connector (read-only) and `check_payments.py --note`.

**Tech Stack:** Python 3 stdlib in the repo's `.venv`. Tests are stdlib scripts: `.venv/bin/python tests/test_pipeline.py`.

**Spec:** [docs/superpowers/specs/2026-09-28-business-automation-design.md](../specs/2026-09-28-business-automation-design.md), Phase 2, features 6–10.

---

## Read this before starting

- **No names in the pipeline.** `enquiries.csv` has no name, email or venue column, and `add` refuses any field it doesn't know. The Zoho thread id is the key. Output is ids, refs, dates and counts only.
- **Two locks, never nested.** Enquiry writes hold `ledger_lock(enquiries.csv)`. `reviewed` holds `ledger_lock(LEDGER)`, the same lock `check_payments` and `assistant_io` use. The lock is not re-entrant, so no command takes both.
- **Drafts only.** Follow-ups and review requests are Zoho drafts that Luca sends. A command runs only after its draft is saved (`followed`, `reviewed`), so a failed draft is retried next day. Nothing is ever sent twice.

## File structure

| File | Responsibility |
|---|---|
| Create `scripts/bookings/pipeline.py` | The enquiry sheet: `add`, `quoted`, `contact`, `event`, `status`, `followups-due`, `followed`, `reviews-due`, `reviewed`, `done-due`, `summary`; pure `followups_due`, `reviews_due`, `done_due`, `summary_dict` |
| Create `tests/test_pipeline.py` | 45 tests: timing edges and the full chase timeline, past events, no restart from an old message or a re-run quote, funerals and booked clients never chased, review filters, done-due, ledger columns and mode, refusals and field limits, summary numbers, no names in output |
| Modify (Task 3) `docs/HANDOVER-2026-09-27-ads-analytics.md` | Appendix E steps below |
| Modify (Task 3) `.claude/settings.json` | Allowlist below |
| Modify (Task 3) `CLAUDE.md` | One bullet in "Email and invoices" |

---

### Task 1: `pipeline.py` (done)

`enquiries.csv` columns: `enquiry_id, first_seen, source, occasion, event_date, package, quoted_gbp, status, last_contact, booking_ref, gclid, followups, notes`. The spec's data model lacked `gclid` and `followups`. Phase 3 needs `gclid` for cost per booking, and `followups` counts the drafts.

| Command | Behaviour |
|---|---|
| `add '<json>'` or `add -` | The JSON as an argument, or on stdin with `-` (so notes with apostrophes are safe). Validates everything: an id of 1–64 characters from `[A-Za-z0-9._:-]`; strict ISO dates; source one of web form, email, whatsapp, phone, referral; occasion one of wedding, funeral, christmas, corporate, private event, other; gclid matching `^((gbraid\|wbraid):)?[A-Za-z0-9_-]{10,200}$`; a known status; followups 0–2; single-line values; notes at most 300 characters and other fields at most 80 (the error names the field, never the value); `confirmed` needs a `booking_ref`. Defaults: status new, followups 0, last_contact = first_seen. Refuses a duplicate id or an unknown field, and writes nothing then |
| `quoted <id> <package> <gbp> <date>` | Status quoted, package, £ (normalised: `£1,150` → `1150`; more than 0 and at most 100,000), last_contact = date, followups back to 0, and a `quoted YYYY-MM-DD` note (used for days-to-quote). Refuses a confirmed, deposit_paid, done or cancelled enquiry, a date before last_contact, and a quote already noted for that date ("…is before the last contact; nothing changed"), so a re-run never restarts the chase. A lost one can be re-quoted with a new date |
| `contact <id> <date>` | The client replied: followups back to 0, last_contact = date. Refuses a date before last_contact ("…is before the last contact; nothing changed"), so an old message read late never restarts the chase |
| `event <id> <date>` | Sets event_date |
| `status <id> <status> [ref]` | Any valid status; `confirmed` needs a ref, given now or already stored. A confirmed, deposit_paid or done enquiry never moves back to new or quoted |
| `followups-due [--today]` | Quoted rows with no booking_ref, measured from last_contact (or first_seen), which `quoted`, `contact` and `followed` move: `first` at ≥5 days with 0 follow-ups (5 days after the quote), `second` at ≥10 with 1 (10 days after the first), `mark_lost` at ≥10 with 2 (10 days after the second). Quote on 1 Sep → first 6 Sep → second 16 Sep → mark_lost 26 Sep. If the event date is today or past, the kind is `mark_lost` and nothing is chased. An unknown event date still follows up. A funeral occasion (`FUNERAL`: funeral, memorial, requiem, burial, interment, committal, cremation, thanksgiving, celebration of life) or a blank one is never chased: `mark_lost` once the event has passed, nothing if there is no event date |
| `followed <id> <1\|2> <date>` | Needs status quoted and exactly n−1 follow-ups so far, so a repeat is refused |
| `reviews-due [--today]` | Ledger rows with an event 3–14 days ago (inclusive), `paid in full YYYY-MM-DD` in the notes, not `is_cancelled`, no `review request drafted`, and an occasion that is neither blank nor a funeral (`FUNERAL`) |
| `reviewed <ref> <date>` | Appends `; review request drafted <date>` under the ledger lock and keeps the ledger's own header order (`check_payments.header`), mode 600. Refuses an unknown ref, one already marked, or a ledger with any row wider than its header (it writes nothing then) |
| `done-due [--today]` | `[{enquiry_id, booking_ref}]`: pipeline rows with a booking_ref, not done, lost or cancelled, whose ledger row has `paid in full YYYY-MM-DD`, is not `is_cancelled`, and has an event before today. Funerals included |
| `summary [--since]` | `{by_status (all seven, zeros included), enquiries, quoted, confirmed, conversion_rate, by_source, median_days_to_quote}`, filtered on first_seen |

`summary_dict` definitions:
- **quoted:** status quoted, a `quoted_gbp`, a `quoted` note or a booked status.
- **confirmed:** confirmed, deposit_paid or done, or cancelled with a `booking_ref` (booked, then cancelled).
- **conversion_rate:** confirmed ÷ enquiries, to 3 decimals, or `null` with no enquiries.
- **median_days_to_quote:** first_seen to the first `quoted` note; a negative figure (a mistyped date) is left out.
- Statuses are counted whatever their case.

### Task 2: Tests (done)

```bash
PY=~/Documents/GitHub/londonchoralservice/.venv/bin/python
$PY tests/test_pipeline.py        # 45 PASS, 0 failure(s)
$PY tests/test_check_payments.py  # unchanged, 0 failure(s)
```

---

### Task 3: Wire the assistant (the later wiring step)

- [ ] **Step 1: Allowlist.** Add to `permissions.allow` in `.claude/settings.json` (`check_payments.py --note *` is already there):

```json
"Bash(.venv/bin/python scripts/bookings/pipeline.py *)",
"mcp__caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1__list_calendars",
"mcp__caefd5da-81a5-4eb0-993a-dfeaa5b9d7c1__list_events"
```

The two calendar tools are the claude.ai Google Calendar connector on this machine. Check the id with `ToolSearch "calendar list_events"` on a new machine. Never allow its create, update, delete or respond tools.

- [ ] **Step 2: Appendix E, TOOLS.** Add after the `singer_invoices.py thanked` line:

```text
  .venv/bin/python scripts/bookings/check_payments.py --note <invoice ref> "cancelled <YYYY-MM-DD> by client email"
  .venv/bin/python scripts/bookings/pipeline.py add - <<'JSON'   (one JSON object on stdin; or add '<one-line JSON object>')
  .venv/bin/python scripts/bookings/pipeline.py quoted <threadId> '<package>' <total £> <YYYY-MM-DD>
  .venv/bin/python scripts/bookings/pipeline.py contact <threadId> <YYYY-MM-DD>
  .venv/bin/python scripts/bookings/pipeline.py event <threadId> <YYYY-MM-DD>
  .venv/bin/python scripts/bookings/pipeline.py status <threadId> <new|quoted|confirmed|deposit_paid|done|lost|cancelled> [invoice ref]
  .venv/bin/python scripts/bookings/pipeline.py followups-due
  .venv/bin/python scripts/bookings/pipeline.py followed <threadId> <1|2> <YYYY-MM-DD>
  .venv/bin/python scripts/bookings/pipeline.py reviews-due
  .venv/bin/python scripts/bookings/pipeline.py reviewed <invoice ref> <YYYY-MM-DD>
  .venv/bin/python scripts/bookings/pipeline.py done-due
- Google Calendar, read-only: the connector's list_calendars and list_events only. Never create, update, delete or respond to an event.
```

- [ ] **Step 3: Appendix E, SET-UP.** Add a bullet:

```text
- The pipeline (~/lcs-private/enquiries.csv) keys every enquiry by its Zoho threadId. Put no names, emails, phone numbers or venues in it: in a pipeline "notes" value write only short facts such as "4 singers, London".
```

- [ ] **Step 4: Appendix E, step 3.** Insert as the first bullet of step 3, before "NEW ENQUIRY":

```text
   - Diary check: before drafting a reply to a NEW ENQUIRY, or any message that names a new date, read Luca's Google Calendar for that date. Once per run, list_calendars to find the calendars named "Personal", "Work" and "Alma Consort". Then list_events on each for the whole day (Europe/London). Note any event that day in your summary under the draft: "Diary: <time>–<time> <calendar>" for each one, or "Diary: clear", or "Diary: not checked" if the calendar can't be read or the date is unclear. Never mention the diary, a clash or availability in the draft.
```

Replace the CHANGE or CANCELLATION bullet with:

```text
   - CHANGE or CANCELLATION: a short, kind acknowledgement. Don't state refund terms beyond "the terms in your booking confirmation"; flag it for Luca. When the client plainly cancels a booked event (not "might", "thinking of" or a question), also run `check_payments.py --note <invoice ref> "cancelled <date of their message> by client email"` and `pipeline.py status <threadId> cancelled`. In the summary, list the ref, the event date and the days of notice, with "deposit retained under the terms; balance depends on notice, Luca to decide". Never promise or start a refund.
```

- [ ] **Step 5: Appendix E, new step 3a** (after step 3, before "Ad click reference"):

```text
3a. Pipeline, for every message you classified in step 2 (threadId = the Zoho thread id):
   - NEW ENQUIRY: `pipeline.py add '{"enquiry_id": "<threadId>", "first_seen": "<date of their first message>", "source": "<web form|email|whatsapp|phone|referral>", "occasion": "<wedding|funeral|christmas|corporate|private event|other>", "event_date": "<YYYY-MM-DD, or leave the key out>", "gclid": "<from step 4, or leave the key out>"}'`. If it says duplicate, run `contact` instead.
   - FOLLOW-UP, or any other client message on a thread already in the pipeline: `pipeline.py contact <threadId> <date of their message>`. If the reply says they have booked someone else or no longer need us, also run `pipeline.py status <threadId> lost` and draft nothing more than a gracious one-line reply.
   - CONFIRMATION, after the documents are made: `pipeline.py status <threadId> confirmed <invoice ref>`.
   - Quotes: in the Sent folder, find Luca's replies from office@ since last_checked. For each one that states a package and a total price, run `pipeline.py quoted <threadId> '<package as he wrote it>' <total £> <date sent>`. Record only what Luca sent, never a draft. If the thread isn't in the pipeline yet, `add` it first from the client's first message.
   - Event date: when a message or Luca's quote gives the event date, run `pipeline.py event <id> <date>`.
   - Within a thread, run `contact` and `quoted` in date order, oldest first. If either says "is before the last contact; nothing changed", that message is already counted: move on.
   If a pipeline command says "no enquiry" for a thread that began before 28 Sep 2026, ignore it: older threads aren't in the pipeline.
```

- [ ] **Step 6: Appendix E, step 6** (first run of the day). Add after 6b:

```text
   c. Follow-ups: run `pipeline.py followups-due`. For each item, read the whole thread first. If the client has written since Luca's last message, run `pipeline.py contact <id> <date of their message>` and draft nothing. If Luca has already chased by hand, run `pipeline.py followed <id> <n> <date he sent it>` and draft nothing. Draft nothing, flag it, and run `pipeline.py status <id> confirmed <ref>` if the thread shows an acceptance, an invoice or a booking confirmation. Also draft nothing if a follow-up draft for this thread is already in Drafts (run `followed` instead). Otherwise:
      - first: a light check-in in the thread, two or three sentences in Luca's style, asking whether they've had a chance to think about it and offering to answer any questions. Then `pipeline.py followed <id> 1 <today>`.
      - second: a last friendly note, just as short. Luca won't chase again, and the door stays open if plans change. Then `pipeline.py followed <id> 2 <today>`.
      - mark_lost: draft nothing; run `pipeline.py status <id> lost`.
      Never offer a discount, a new price or a hold on the date, and never say the date is free.
   d. Review requests: run `pipeline.py reviews-due` (it never lists a funeral, or a booking with no occasion). For each booking ref, find the client's thread (search for the invoice ref) and read it. If anything went wrong or is unresolved, draft nothing and flag it. If the thread shows the correspondent is a wedding planner or venue rather than the couple, draft nothing and flag it. Otherwise draft a short thank-you in the thread in Luca's style: thanks for having us, a line about the day if the thread gives one, and one sentence asking whether they'd leave a Google review, with the link from `gbp_canonical_maps_url` in data/seo-fix-discovered-urls.yml (Read tool). Never offer anything in return for a review, and never ask only for a good one. Then run `pipeline.py reviewed <ref> <today>`.
   e. When 6a drafts a receipt for a deposit, also run `pipeline.py status <threadId> deposit_paid` for that thread (ignore "no enquiry").
   f. Done: run `pipeline.py done-due`. For each item, run `pipeline.py status <enquiry_id> done`. This covers every paid-in-full booking whose event has passed, funerals included; draft nothing.
```

- [ ] **Step 7: Appendix E, notification and FINAL SUMMARY.** The PushNotification count includes follow-up and review drafts. Add to FINAL SUMMARY, after "Invoices made":

```text
- Pipeline: follow-ups drafted (thread ids and first or second), enquiries marked lost, review requests drafted (refs), cancellations logged (ref, event date, days of notice).
```

Also, under "Drafts saved", each line now ends with its Diary note.

- [ ] **Step 8: Appendix A (optional, Monday).** In the bookings line, add: `the pipeline since 1 Sep: .venv/bin/python scripts/bookings/pipeline.py summary --since <season start>, as "<n> enquiries, <q> quoted, <c> booked (<rate>%), median <d> days to quote"`. Phase 3 replaces this with cost per booking.

- [ ] **Step 9: CLAUDE.md.** In "Email and invoices", add:

```text
- **Enquiry pipeline:** `scripts/bookings/pipeline.py` keeps `~/lcs-private/enquiries.csv` (keyed by Zoho thread id, no names): status new → quoted → confirmed → deposit_paid → done, or lost/cancelled. The assistant drafts quote follow-ups 5 days after the quote and 10 days after the first, then marks the enquiry lost 10 days after the second. It never chases a funeral enquiry or a booked client. It drafts one review request 3–14 days after a paid-in-full event, never after a funeral. It checks Google Calendar read-only before drafting, and flags a clash only in its summary.
```

- [ ] **Step 10:** Paste the updated Appendix E into the `enquiry-assistant` scheduled task, then run the Phase 1 plan's Task 7 Step 8 check (`## Appendix E True`).

## Open points for the owner

- **Review link.** `gbp_canonical_maps_url` opens the Maps listing, so the client still has to find "Write a review". The Business Profile's "Ask for reviews" short link goes straight to the form. To switch to it, add that link as `gbp_review_url` to `data/seo-fix-discovered-urls.yml` and change step 6d.
- **Funerals.** Closed. Owner default: never ask; enforced in code. `reviews-due` skips a funeral (or blank) occasion, and `followups-due` never chases a funeral enquiry.
- **Older threads.** Enquiries from before the wiring aren't in the pipeline. Their follow-ups stay with Luca unless he wants them back-filled.
