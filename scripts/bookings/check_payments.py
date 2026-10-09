#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY (see lcs_money.StarlingReadOnly).

    .venv/bin/python scripts/bookings/check_payments.py                  # report
    .venv/bin/python scripts/bookings/check_payments.py --apply          # also update ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --apply --json   # machine-readable, for the assistant;
        each item's "action" is receipt | deposit_reminder | balance_reminder | hand_check | none (action_for),
        and "record_in_books" lists its confident payments [[date, amount, bank charges]] for the Books invoice
        (BOOKS_STATES; the bank charges are 0.0 except on the last payment of a booking closed by an accepted fee)
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111 [--kind deposit|balance|receipt]
        (also records reminder-drafted in the state log; --apply records deposit-seen and paid-in-full, basis bank,
        where it writes those notes)
    .venv/bin/python scripts/bookings/check_payments.py --fact 2111 cancelled [--on YYYY-MM-DD]
    … --fact 2111 noted-paid --scope part|full   … --fact 2111 arranged --method cash|cheque|third-party
        records the fact in the state log (lcs_events; structured-state design) and appends its phrase to the
        notes (fact_phrase: "cancelled D by client email", "paid per client email D", "balance paid per client
        email D", "balance payable in cash on the day (arranged D)" …), both under the ledger lock. --on defaults
        to today (never after it, at most 730 days back). The owner's kinds (paid-in-full, fees-accepted --amount
        X, reinstated, deposit-kept, refunded, payment-checked) need --owner and the Command Centre's nonce, and
        write "… (owner)"
    .venv/bin/python scripts/bookings/check_payments.py --note 2111 "4 singers, London"
        (free text only: one line, at most 120 characters, no ';'; refuses the scripts' own phrases and the owner's
        hand-written ones: paid in full, short by fees … accepted, deposit seen … (Starling), reminder/receipt drafted, deposit kept, refunded,
        payment checked, reinstated and the like, review request …, and anything starting PENDING. It also refuses
        text that states a cancellation, an arrangement or a payment the client reported (NOTE_REFUSES_FACTS, owner
        decision 29 Sep 2026), naming the --fact form to use instead: "record it with --fact 2111 cancelled;
        nothing written")
    … --note 2111 "paid in full 2026-09-28" --owner
        (the Command Centre only, after the owner's passkey: allows the owner's phrases and records "(owner)";
        refused unless stdin is a pipe carrying the app's one-time nonce, see owner_confirmed)
    .venv/bin/python scripts/bookings/check_payments.py --selftest       # token, account and permissions

Matching (against every ledger row, closed ones too, so a payment is never
credited to the wrong booking): an incoming payment belongs to a booking when its
reference names the invoice number ("INV2111", "INV 2111", "INV-2111",
"LCS2111", "INV2111DEPOSIT" and "2111" all name 2111; "24081" does not name
2408). A letter names a suffixed ref only as the reference's last token ("INV
1212 A") or a glued one-letter tail ("1212A", "INV1212A"); "1212 A SMITH" and
"INV1212BAL" name 1212. A reference that names any booking is final, but it is
only CONFIDENT when nothing contradicts it: "1212" when 1212A also exists names
them all, and the payer's surname may pick one (else all are unconfirmed); and
the payer's surname contradicts it only when it fits another open booking whose
window and fee or half-fee fit the payment, while the named client's surname is
absent from the payer's name (then both are unconfirmed). Parents and funeral
directors paying under another name are normal. Surnames are the last real word
of each party ("Ann Smith & Tom Jones": Smith or Jones; "T Brackenwold & Sons": Brackenwold).
Failing a reference, when its amount is the deposit or full fee, the payer's name
contains the client's surname as a whole word, and it falls inside that
booking's invoice-to-event window. Failing that, when its amount is the deposit
or fee of open bookings inside their window: an "amount only" match, on each
booking it fits, which is unconfirmed and never counts as paid. Failing that too,
when the payer's name has an open booking's surname as a whole word inside its
window (a split or odd amount: £300 then £275 from "K FARROW"): "name only, amount
differs", on each such booking, also unconfirmed. A payment with no reference from a
cancelled booking's client (surname, inside its window) is "name, cancelled booking"
before any amount-only match, so it never lands on another client's live booking.

States (assess): PAID_IN_FULL (the confident payments cover the booking's value, or fall short of it by no more
than a shortfall the owner accepted as transfer fees: "short by fees £12.40 accepted YYYY-MM-DD", at most FEE_CAP
(£40) and dated no later than today, written only through the Command Centre with --owner; "fees" is the part of
it used, "balance" is then 0, and the fee rides on the last payment in "record_in_books" as Books' bank charges.
That note closes the booking like "paid in full YYYY-MM-DD": collect() reports it once more, as PAID_IN_FULL,
and --apply then adds "paid in full" dated the later of the last payment and the fee note), DEPOSIT_SEEN, BALANCE_DUE (from 3 days before the
event), AWAITING_DEPOSIT (until the deposit falls due: 7 days after the invoice,
or 3 days before a short-notice event, never the invoice day), DEPOSIT_OVERDUE
(future events only), AWAITING_INVOICE_SENT (instead of either of those two while the booking's Zoho Books invoice
is still a draft, so the client hasn't been sent it: never chased, action none; on the Monday hand check once the
deposit would have been due. Read from the Command Centre's local Books cache, unsent_invoices; no cache, no
change),NOTED_PAID (the owner's notes say paid, or an earlier run's
"deposit seen … (Starling)" with nothing in the feed now; negated or future
phrases such as "not yet seen", "no payment received", "to be paid" or "asked if
paid" don't count, but "no chase needed - paid 5 Sep" does. With a deposit in the
bank only a note of the whole fee counts: "balance of £575 paid" or "£1,150 paid
in total" do, "£575 paid 5 Sep" or "deposit paid in full" are the deposit. It
stays on the Monday hand check until the notes say "paid in full YYYY-MM-DD"),
PAST_UNMATCHED / PAST_PART_PAID (past events), CHECK_PAYMENT (only an unconfirmed
match, which outranks a stale auto note; or a confident deposit plus an
unconfirmed payment dated on or after it, or the size of the balance, which may
be the balance paid by someone else), CHECK_VALUE (no readable booking value,
invoice date or event date), CANCELLED ("cancelled", "cancellation confirmed",
"received" or "requested", unless "if" or "unless" comes just before it ("rain date if
cancelled"), or "cancelling" unless "may", "might", "thinking of" and the like come
just before it; only a later explicit reversal undoes it: "reinstated",
"cancellation (request) withdrawn" ("cancellation requested, then withdrawn"),
"going ahead after all" or "back on", unless negated or doubtful ("may be
reinstated") or followed within three words by with, elsewhere, another, without
or different ("going ahead after all with another choir"); bare "rebooked",
"withdrawn" or "going ahead" never undo it. The row then drops out of everything),
PAYMENT_ON_CANCELLED (a payment inside a cancelled booking's window; once the owner
has dealt with it, "deposit kept YYYY-MM-DD", "refunded YYYY-MM-DD" or "payment
(refund, deposit) checked YYYY-MM-DD" in the notes limits this to payments dated
after that day, so with none the row drops off the hand check; a date after today
silences nothing), PAYMENT_AFTER_CLOSE (a payment dated
after a "paid in full YYYY-MM-DD" or counting "short by fees … accepted YYYY-MM-DD" note; received_since leaves it out) and ARRANGED
(the notes say the balance will come in cash or by cheque: "balance to be paid in
cash", "will pay balance in cash", "balance payable in cash on the day", "rest will
be paid in cash", "cheque on the day"; or a future-tense note of the balance/rest/
remainder with no cash or cheque mentioned at all: "rest will be paid by the father",
"balance will be paid by her parents", "remainder to be paid by the church", "is
paying the rest", "going to pay the balance" — a future-tense phrase never reads as
paid, whatever the wording, and with no mention of the balance/rest/remainder it is
chased normally instead; not when the clause has a paid word ("balance
paid in cash on the day" is NOTED_PAID, and so is a past-tense "rest paid by the
father 5 Sep") or a negation, refusal or doubt anywhere in
it ("told bank transfer only", "by transfer not cash", "going to pay cash but will
transfer"), and a note of the whole fee paid still wins. Never chased or thanked; on the Monday
hand check from 7 days before the event, or every week when no deposit is in the bank
or the notes. A possible balance payment in the bank makes it CHECK_PAYMENT instead).
Only DEPOSIT_OVERDUE and BALANCE_DUE are ever chased (never AWAITING_INVOICE_SENT); just_received (a confident
payment in the last 14 days with no receipt drafted, only in PAID_IN_FULL,
DEPOSIT_SEEN, BALANCE_DUE or NOTED_PAID) asks for a thank-you, and short_notice
(event within 10 days of the invoice) asks for the full fee rather than a deposit.
Every CHECK_*, PAST_*, NOTED_PAID and PAYMENT_* state is on the Monday money line's
"needs a hand check" (money_report.py), and ARRANGED as above; --apply never rewrites
the notes of a cancelled or closed row, and drops a "deposit not yet seen" clause when
it writes "deposit seen … (Starling)". Output shows invoice numbers and amounts only.
"""

import argparse
import datetime
import json
import math
import os
import re
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_events  # noqa: E402
import lcs_money as lm  # noqa: E402
import lcs_owner  # noqa: E402

LEDGER = lm.LEDGER
MARK_TEXT = {"deposit": "reminder drafted", "balance": "balance reminder drafted", "receipt": "receipt drafted"}
CONFIDENT = ("reference", "name and amount")
RECEIPT_DAYS = 14
SHORT_NOTICE_DAYS = 10
# The most a booking may be short by transfer fees and still read paid in full, once the owner accepts it
# ("short by fees £12.40 accepted 2026-09-28", written only through the Command Centre; owner decision, 28 Sep 2026).
FEE_CAP = lm.FEE_CAP  # £40, owner decision, 29 Sep 2026; defined in lcs_money so the state log's schema shares it
# A thank-you is only ever drafted in these states; notes are never rewritten in the others.
RECEIPT_STATES = {"PAID_IN_FULL", "DEPOSIT_SEEN", "BALANCE_DUE", "NOTED_PAID"}
# States whose confident payments the assistant records against the Books invoice (owner decision, 28 Sep 2026).
# Every CHECK_*, PAST_*, NOTED_PAID, PAYMENT_* and CANCELLED state stays with the owner.
BOOKS_STATES = {"PAID_IN_FULL", "DEPOSIT_SEEN", "BALANCE_DUE", "ARRANGED"}
NEVER_WRITTEN = {"CANCELLED", "PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE"}
# URLError and HTTPError are OSErrors too; a non-JSON 200 body (an outage page) is a JSONDecodeError
STARLING_DOWN = (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError)
# The script's own notes, removed before reading the owner's hand-written ones.
AUTO_NOTE = re.compile(r"deposit seen \d{4}-\d{2}-\d{2} \(Starling\)", re.I)
MARK_NOTE = re.compile(r"\b(balance )?reminder drafted( \d{4}-\d{2}-\d{2})?|\breceipt drafted( \d{4}-\d{2}-\d{2})?", re.I)
FULL_NOTE = re.compile(r"paid in full \d{4}-\d{2}-\d{2}", re.I)
# The owner's acceptance of a shortfall lost to transfer fees: it closes the booking like "paid in full" (fee_notes)
FEES_NOTE = re.compile(r"short by fees £(\d+(?:\.\d{1,2})?) accepted (\d{4}-\d{2}-\d{2})", re.I)
NOT_YET_SEEN = re.compile(r"\s*[,;]?\s*\bdeposit not yet seen\b[^;,]*", re.I)  # dropped once the deposit is seen
# Negated, conditional or future phrases, removed before looking for a paid word. A bare negation only
# reaches a paid word across a few listed filler words ("no payment received", "not yet been paid"), so
# "no chase needed - paid 5 Sep" or "not a problem: paid" keep their "paid"; the other gaps never cross
# ";", ".", ",", ":", " - ", a dash or "but" ("said he'd ring but paid 5 Sep" is paid).
def _gap(n=""):
    return r"(?:(?!\bbut\b|\s-\s|[;.,:\u2013\u2014]).)" + (f"{{0,{n}}}" if n else "*")


NOT_PAID = re.compile(
    r"\bdeposit not yet seen\b"
    r"|(\b(not|un)|n't)\s*(yet\s+)?(been\s+)?(paid|received|seen|settled)\b"
    r"|\b(not|never|no|nothing)\s+((yet|been|the|a|any|deposit|balance|payment|money|funds|anything)\s+){0,3}"
    r"(paid|received|seen|settled|in)\b"
    r"|\bto be (paid|received|settled)\b" + _gap()
    + r"|\bif\b" + _gap(15) + r"\bpaid\b"
    r"|\b(asked|says|said)\b" + _gap(20) + r"\bpaid\b"
    r"|\bwill\s+(be\s+|have\s+)?(pay|paid)\b" + _gap()
    + r"|\b(deposit|balance|payment)\s+in\s+by\b", re.I)  # "deposit in by Friday please" is a deadline
# "deposit seen <date>;" is what the enquiry assistant writes by hand (handover Appendix E)
PAID_WORD = re.compile(r"\b(paid|received|settled)\b|\bdeposit\s+(seen|in)\b", re.I)
# With a confident deposit in the bank, only a note of the WHOLE fee stops a balance chase.
_DATE = r"\d{1,2}(st|nd|rd|th)?\s+[a-z]{3,9}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}"
FULL_PAID = re.compile(
    r"\bbalance\s+(paid|received|settled)\b|\bpaid\s+in\s+full\b|\bfully\s+paid\b"
    r"|(?<!deposit )\bpaid\s+(on\s+)?(" + _DATE + r")\b|(?<!deposit )\bpaid\s+the\s+balance\b"
    r"|\bsettled\s+in\s+cash\b|\bbalance\s+in\s+cash\b"
    r"|(?<!deposit )\bpaid\s+(by\s+|in\s+)?(cash|cheque|card|bank\s+transfer)\b", re.I)
# A full-payment phrase in a clause that starts with "deposit", or carries a £ amount below the booking
# value with no word for the rest of the fee, is about the deposit: "£575 paid 5 Sep" never stops a balance chase.
# A word for the rest of the fee next to a paid word is the whole fee, whatever the amount ("balance of £575 paid",
# "£1,150 paid in total"); in a clause starting "deposit" only balance/rest/remainder count ("deposit paid in full"
# is the deposit).
CLAUSE = re.compile(r";|\.(?!\d)|,(?!\d)")
REST_WORD = re.compile(r"\b(balance|rest|remainder|remaining|in full|fully|final|in total|total)\b", re.I)
REST_PAID = re.compile(
    r"\b(balance|rest|remainder|remaining|total)\b(?:(?!\bdeposit\b).){0,30}?\b(paid|received|settled)\b"
    r"|\b(paid|received|settled)\b(?:(?!\bdeposit\b).){0,30}?\b(in\s+full|in\s+total|the\s+(balance|rest|remainder))\b", re.I)
OTHER_PART = re.compile(r"\b(balance|rest|remainder|remaining)\b", re.I)
POUNDS = re.compile(r"£\s*(\d[\d,]*(?:\.\d+)?)")
# Not surnames: the last real word of each party is ("T Brackenwold & Sons" is Brackenwold).
GENERIC = {"son", "sons", "ltd", "limited", "funeral", "funerals", "director", "directors", "church", "parish", "and",
           "co", "plc", "llp", "mr", "mrs", "ms", "miss", "dr", "rev", "revd"}
PREFIX = r"(INVOICE|INV|LCS)"
REF_TOKEN = re.compile(r"(?:" + PREFIX + r"\s*[-#:]?\s*(?=\d))?([A-Z0-9]+)")


def money(row):
    return lm.money(row.get("value_gbp"))  # 0.0 when unreadable, "nan" and "inf" included


def date_or_none(s):
    try:
        return datetime.date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def window(r, today):
    start = date_or_none(r.get("invoice_date"))
    if not start:
        return None
    end = date_or_none(r.get("event_date")) or today
    return start - datetime.timedelta(days=3), end + datetime.timedelta(days=14)


def in_window(r, when, today):
    w, day = window(r, today), date_or_none(when)
    return bool(w and day and w[0] <= day <= w[1])


def norm_ref(ref):
    key = (ref or "").strip().upper()
    return key[3:] if key.startswith("INV") else key


def named_keys(text, known):
    """Known refs a payment reference names. A single letter names a suffixed ref only when it is the
    reference's LAST token ("INV 1212 A") or the whole glued tail ("1212A", "INV1212A"); "2111 A SMITH"
    and "INV2111BAL" name 2111 (and so every 2111 sibling). "24081" never names 2408."""
    toks = [(bool(m.group(1)), m.group(2)) for m in REF_TOKEN.finditer((text or "").upper())]
    out = set()
    for i, (prefixed, t) in enumerate(toks):
        m = re.fullmatch(r"(\d+)([A-Z]*)", t)
        if not m:
            continue
        digits, letters = m.groups()
        last_letter = (not letters and i == len(toks) - 2 and not toks[i + 1][0]
                       and re.fullmatch(r"[A-Z]", toks[i + 1][1]))
        cands = [digits + toks[i + 1][1]] if last_letter else []
        cands.append(t)
        if prefixed and letters and len(digits) == 4:
            cands.append(digits)  # "INV2111DEPOSIT", "INV2111A" when there is no 2111A
        hit = next((c for c in cands if c in known), None)
        if hit:
            out.add(hit)
    return out


def surnames(r):
    """The last real word of each party in the client name ("Ann Smith & Tom Jones" -> Smith, Jones),
    skipping generic words ("& Sons", "Ltd", "Funeral Directors") and anything under three letters."""
    out = []
    for party in re.split(r"&|\band\b|\+|/", r.get("client_name") or "", flags=re.I):
        words = [w for w in re.findall(r"[^\W\d_][\w'’-]*", party) if w.lower().strip("'’-") not in GENERIC]
        if words and len(words[-1]) > 2 and words[-1] not in out:
            out.append(words[-1])
    return out


def payer_is(r, payer):
    return any(re.search(rf"\b{re.escape(s)}\b", payer or "", re.I) for s in surnames(r))


def fits_amount(amount, r):
    v = money(r)
    return v > 0 and any(abs(amount - x) < 0.01 for x in (v, v / 2))


CANCEL_WORD = re.compile(r"(?<!not )\b(cancell?ed|cancellation (confirmed|received|requested))\b", re.I)
CANCELLING = re.compile(r"\bcancell?ing\b", re.I)
# "cancelling" is a cancellation unless one of these comes within the three words before it
MAYBE_WORDS = {"may", "might", "considering", "thinking", "about", "of", "not", "possibly", "could"}
# "cancelled" is not a cancellation with one of these within the three words before it ("rain date if cancelled")
IF_WORDS = {"if", "unless"}
# Only an explicit reversal undoes the cancellation: "reinstated", "cancellation (request) withdrawn" ("cancellation
# requested, then withdrawn"), "going ahead after all", "back on". Bare "rebooked", "withdrawn", "going ahead" or
# "after all" never do: "rebooked with another choir", "complaint withdrawn", "going ahead without music".
RESUMED = re.compile(
    r"\breinstated\b|\bcancellation(?:\s+request(?:ed)?)?[\s,;]+(?:(?:then|now|since|later|was|is|has|had|been)\s+)*withdrawn\b"
    r"|\bgoing\s+ahead\s+after\s+all\b|\bback\s+on\b", re.I)
# ...unless it is negated or doubtful ("not going ahead after all", "may be reinstated")
DOUBT_WORDS = MAYBE_WORDS | IF_WORDS | {"no", "never", "longer", "perhaps", "maybe", "hope", "hoping", "unlikely"}
# ...or another choir, venue or plan follows within three words ("reinstated with another choir")
ELSEWHERE_WORDS = {"with", "elsewhere", "another", "without", "different"}
# "get back on Monday" is a reply, not the booking
CALL_WORDS = {"get", "gets", "got", "getting", "come", "comes", "came", "coming", "call", "ring", "phone", "reply",
              "respond", "write", "email", "report", "text"}


def words_before(notes, pos, n=3):
    """The last n words before pos in the same clause ("not sure; client cancelling" -> ["client"])."""
    clause = re.split(r"[;.,:]", notes[:pos])[-1]
    return re.findall(r"[a-z'’]+", clause.lower())[-n:]


def facts_for(r, today=None, facts=None):
    """The recorded facts (lcs_events.Facts) for one ledger row: `facts` itself when it is a Facts (tests pass one),
    facts[ref] when it is a mapping, else the state log's (lcs_events.booking_facts, cached per process). A row with
    no ref, or no log, has none, and every family is then read from the notes as before (structured-state design,
    precedence rule 1)."""
    if isinstance(facts, lcs_events.Facts):
        return facts
    ref = (r.get("booking_ref") or "").strip()
    if facts is not None:
        return facts.get(ref) or lcs_events.Facts("booking")
    if not ref:
        return lcs_events.Facts("booking")
    return lcs_events.booking_facts(ref, today or lm.today())


def counting_cancels(notes):
    """Where each counting cancellation phrase starts, in text order ("rain date if cancelled" doesn't count)."""
    out = [m.start() for m in CANCEL_WORD.finditer(notes) if not IF_WORDS & set(words_before(notes, m.start()))]
    out += [m.start() for m in CANCELLING.finditer(notes) if not MAYBE_WORDS & set(words_before(notes, m.start()))]
    return sorted(out)


def last_cancel(notes):
    """Where the notes' latest counting cancellation phrase starts, or -1."""
    return max(counting_cancels(notes), default=-1)


def counting_resumes(notes, start=0):
    """Where each explicit, undoubted reversal ("reinstated", "going ahead after all") at or after start begins."""
    out = []
    for m in RESUMED.finditer(notes, start):
        before = words_before(notes, m.start(), 4)
        if DOUBT_WORDS & set(before) or any(w.endswith(("n't", "n’t")) for w in before):
            continue
        if m.group(0).lower().startswith("back") and before[-1:] and before[-1] in CALL_WORDS:
            continue
        after = re.findall(r"[a-z'’]+", notes[m.end():].lower())[:3]
        if ELSEWHERE_WORDS & set(after):
            continue
        out.append(m.start())
    return out


def resumed_after(notes, start):
    """True when an explicit, undoubted reversal ("reinstated", "going ahead after all") comes at or after start."""
    return bool(counting_resumes(notes, start))


def notes_cancelled(notes):
    """True when the notes' latest cancellation is not undone by a later resumed phrase."""
    last = last_cancel(notes)
    return last >= 0 and not resumed_after(notes, last)


def is_cancelled(r, facts=None):
    """The cancellation family: the recorded cancelled / reinstated facts when there are any, else the notes."""
    f = facts_for(r, None, facts)
    return f.cancelled if f.has("cancellation") else notes_cancelled(r.get("notes") or "")


# "deposit kept 2026-09-15", "refunded 2026-09-20", "payment checked 2026-09-28" on a cancelled row: payments up to
# that date have been dealt with; only a later one is a hand check. A note dated after today silences nothing.
SETTLED_NOTE = re.compile(
    r"(?<!not )\b(?:deposit kept|refunded|(?:payment|refund|deposit) checked)\s+(\d{4}-\d{2}-\d{2})\b", re.I)


# The pipeline's own note on a ledger row (pipeline.py reviewed / review-skipped).
REVIEW_NOTE = re.compile(r"review request (drafted|skipped)", re.I)
# Phrases --note never writes: the scripts' own notes, and the ones the owner writes by hand in the ledger
# (paid in full, short by fees, deposit kept / refunded / checked, reinstated), which close, settle or reopen a booking.
RESERVED_NOTES = (FULL_NOTE, FEES_NOTE, AUTO_NOTE, MARK_NOTE, SETTLED_NOTE, RESUMED, REVIEW_NOTE)


def reserved_note(text):
    """True when --note must refuse this text: a reserved phrase, or anything starting with PENDING."""
    return is_pending(text) or any(p.search(text) for p in RESERVED_NOTES)


# --- --fact: a fact recorded in the state log with today's phrase as its note (structured-state design) ---------

# The kinds --fact records. The script may record the first three (the assistant, from a client's own message); the
# rest are the owner's, with --owner and the Command Centre's nonce. Markers have their own writers (--reminded,
# --apply, pipeline.py reviewed / review-skipped); retract and notes-checked are events.py's.
FACT_KINDS = ("cancelled", "noted-paid", "arranged", "paid-in-full", "fees-accepted", "reinstated", "deposit-kept",
              "refunded", "payment-checked")
OWNER_FACTS = {"paid-in-full", "fees-accepted", "reinstated", "deposit-kept", "refunded", "payment-checked"}
FACT_FIELDS = {"noted-paid": ("scope", ("part", "full")), "arranged": ("method", ("cash", "cheque", "third-party")),
               "fees-accepted": ("amount", None)}
FACT_BACK_DAYS = 730
# The phrase each kind writes (the one the pattern readers read, so the notes say the same fact): {d} the date
PHRASES = {"paid-in-full": "paid in full {d}", "fees-accepted": "short by fees £{amount} accepted {d}",
           "cancelled": "cancelled {d}", "reinstated": "reinstated {d}", "deposit-kept": "deposit kept {d}",
           "refunded": "refunded {d}", "payment-checked": "payment checked {d}",
           ("noted-paid", "part"): "paid per client email {d}", ("noted-paid", "full"): "balance paid per client email {d}",
           ("arranged", "cash"): "balance payable in cash on the day (arranged {d})",
           ("arranged", "cheque"): "balance payable by cheque on the day (arranged {d})",
           ("arranged", "third-party"): "balance to be paid by another payer (arranged {d})"}
AMOUNT_ARG = re.compile(r"\d{1,5}(?:\.\d{1,2})?")
# question 3 (owner decision, 29 Sep 2026): --note refuses fact-shaped text, naming the --fact form, now that the
# prompts use --fact (plan, Task 18); not the owner's --note. False would let the assistant's fact-shaped notes
# through again, each recorded with the facts it states (note_facts), as in the interim.
NOTE_REFUSES_FACTS = True


def fact_phrase(kind, fields, day, by):
    """The note --fact writes for a fact: today's phrase (PHRASES), "cancelled D by client email" for the script's
    cancellation, and " (owner)" after the owner's."""
    key = next(((kind, v) for v in fields.values() if (kind, v) in PHRASES), kind)
    text = PHRASES[key].format(d=day.isoformat(), amount=fields.get("amount", ""))
    if kind == "cancelled" and by == "script":
        text += " by client email"
    return text + (" (owner)" if by == "owner" else "")


def fact_shaped(text):
    """The --fact form a note's text asserts ("cancelled", "noted-paid --scope part", …), or None: the
    cancellation, arrangement and noted-paid families, read with today's patterns (assertions)."""
    said = assertions(text, math.inf, lm.today())
    if said["cancellation"] is not None:
        return "cancelled" if said["cancellation"] else "reinstated"
    if said["arrangement"]:
        return "arranged --method cash|cheque|third-party"
    if said["noted paid"]:
        return f"noted-paid --scope {said['noted paid']}"
    return None


def note_facts(text, row, by, today):
    """The facts a --note's text states in the families --fact records (cancellation, arrangement, noted paid), read
    with today's patterns against the row's value, each dated today: [(kind, fields, by, day)]. --note records them
    claiming its note, so a later fact in the same family never finds this clause unclaimed and holds the booking:
    the owner's --note (the assistant's fact-shaped text is refused while NOTE_REFUSES_FACTS is on). Reinstated only
    for the owner (--note refuses it otherwise)."""
    said = assertions(text, money(row), today)
    out = []
    if said["cancellation"] is True:
        out.append(("cancelled", {}, by, today))
    elif said["cancellation"] is False and by == "owner":
        out.append(("reinstated", {}, by, today))
    if said["arrangement"]:
        low = text.lower()
        where = {w: low.find(w) for w in ("cash", "cheque") if w in low}
        out.append(("arranged", {"method": min(where, key=where.get) if where else "third-party"}, by, today))
    if said["noted paid"]:
        out.append(("noted-paid", {"scope": said["noted paid"]}, by, today))
    return out


def note_refusal(ref, text):
    """--note's refusal of fact-shaped text (once NOTE_REFUSES_FACTS is on), or None."""
    form = fact_shaped(text)
    return f"record it with --fact {ref} {form}; nothing written" if form else None


def fact_input(args, today):
    """(kind, fields, by, day) for --fact from the parsed arguments, or SystemExit naming what is wrong."""
    ref, kind = args.fact
    if not lcs_events.loggable("booking", ref):
        raise SystemExit("--fact needs a booking ref of letters, digits and '-' (the state log's); nothing written")
    if kind not in FACT_KINDS:
        raise SystemExit(f"--fact records one of: {', '.join(FACT_KINDS)}; nothing written")
    by = "owner" if args.owner else "script"
    if kind in OWNER_FACTS and by != "owner":
        raise SystemExit(f"{kind} is the owner's: the Command Centre records it with --owner; nothing written")
    given = {k: getattr(args, k) for k in ("scope", "method", "amount") if getattr(args, k) is not None}
    want = FACT_FIELDS.get(kind)
    if set(given) != ({want[0]} if want else set()):
        need = f"--{want[0]} and nothing else" if want else "no --scope, --method or --amount"
        raise SystemExit(f"--fact {kind} takes {need}; nothing written")
    fields = {"basis": "owner"} if kind == "paid-in-full" else {}
    if want and want[1] is not None:
        if given[want[0]] not in want[1]:
            raise SystemExit(f"--{want[0]} is one of: {', '.join(want[1])}; nothing written")
        fields[want[0]] = given[want[0]]
    elif want:  # fees-accepted: a plain amount, more than £0 and at most FEE_CAP
        amount = given["amount"]
        if not AMOUNT_ARG.fullmatch(amount) or not 0 < float(amount) <= FEE_CAP:
            raise SystemExit(f"--amount must be a plain amount more than £0 and at most £{FEE_CAP:.2f}; nothing written")
        fields["amount"] = f"{float(amount):.2f}"
    day = today
    if args.on is not None:
        day = date_or_none(args.on) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.on) else None
        if day is None or day > today or day < today - datetime.timedelta(days=FACT_BACK_DAYS):
            raise SystemExit(f"--on must be a real date YYYY-MM-DD, not after today and at most {FACT_BACK_DAYS} days "
                             "back; nothing written")
    return kind, fields, by, day


def cancel_settled_on(r, today, facts=None):
    """The cancel-settlement family: the latest deposit kept / refunded / payment checked date up to today."""
    f = facts_for(r, today, facts)
    if f.has("cancel settlement"):
        return f.settled_on
    days = [date_or_none(m.group(1)) for m in SETTLED_NOTE.finditer(r.get("notes") or "")]
    return max((d for d in days if d and d <= today), default=None)


def fee_notes(r, today=None, facts=None):
    """[(date, amount)] of the owner's "short by fees £X accepted YYYY-MM-DD" notes that count, in note order: more
    than £0 and at most FEE_CAP, dated no later than today (default lm.today()). The others are ignored. With
    recorded close facts, the live fees-accepted facts instead (the schema holds them to the cap; later days are
    left out)."""
    today = today or lm.today()
    f = facts_for(r, today, facts)
    if f.has("close"):
        return f.fees
    out = []
    for m in FEES_NOTE.finditer(r.get("notes") or ""):
        day, amount = date_or_none(m.group(2)), float(m.group(1))
        if day and day <= today and 0 < amount <= FEE_CAP:
            out.append((day, amount))
    return out


def fees_accepted(r, today, facts=None):
    """The amount of the latest fee note that counts (fee_notes; by date, then the last written), or 0.0."""
    notes = fee_notes(r, today, facts)
    return max(enumerate(notes), key=lambda n: (n[1][0], n[0]))[1][1] if notes else 0.0


def fee_pending(r, today=None, facts=None):
    """A booking closed by a fee note that no run has marked "paid in full" yet: collect() still reports it once, so
    the daily pass records the last payment and the fee in Books, and --apply then writes the "paid in full" note."""
    f = facts_for(r, today, facts)
    full = f.paid_full_on if f.has("close") else FULL_NOTE.search(r.get("notes") or "")
    return not is_cancelled(r, f) and not full and bool(fee_notes(r, today, f))


def closed_on(r, today=None, facts=None):
    """The close family: the latest "paid in full YYYY-MM-DD" or counting "short by fees £X accepted YYYY-MM-DD"
    date (from the recorded facts when there are any, else the notes), or None: the booking is closed from then."""
    f = facts_for(r, today, facts)
    if f.has("close"):
        return f.closed_on
    days = [date_or_none(m.group(0)[-10:]) for m in FULL_NOTE.finditer(r.get("notes") or "")]
    days += [d for d, _ in fee_notes(r, today, f)]
    return max((d for d in days if d), default=None)


def is_closed(r, today=None, facts=None):
    """Closed for chasing: a close fact, or else "paid in full YYYY-MM-DD" anywhere or a counting fee note."""
    f = facts_for(r, today, facts)
    if f.has("close"):
        return f.closed_on is not None
    return bool(FULL_NOTE.search(r.get("notes") or "") or fee_notes(r, today, f))


def is_pending(notes):
    return notes.lstrip().upper().startswith("PENDING")


def by_reference(keys, by_key, payer, amount, rows, when, today):
    """(booking refs, how) for a payment whose reference names these ledger keys. The payer's surname
    contradicts the reference only when it fits another OPEN booking whose window and fee (or half-fee)
    fit the payment too, and the named client's own surname isn't in the payer's name; a parent or
    funeral director paying under another name is otherwise normal."""
    named = []
    for k in sorted(keys):
        group = list(by_key[k])
        if k[-1:].isdigit():  # "1212" when 1212A, 1212B also exist: which one?
            group += [r for kk, rs in by_key.items() if len(kk) == len(k) + 1 and kk.startswith(k) and kk[-1].isalpha()
                      for r in rs]
        if len(group) > 1:
            who = [r for r in group if payer_is(r, payer)]
            group = who if len(who) == 1 else group
        named += [r for r in group if r not in named]
    refs = sorted({r["booking_ref"] for r in named})
    if len(refs) > 1:
        return refs, "reference naming several bookings"
    others = sorted({r["booking_ref"] for r in open_rows(rows, today) if r["booking_ref"] != refs[0] and payer_is(r, payer)
                     and in_window(r, when, today) and fits_amount(amount, r)})
    if others and not any(payer_is(r, payer) for r in named):
        return refs + others, "reference, but the payer's name fits another booking"
    return refs, "reference"


def match(rows, items, today):
    """booking_ref -> list of (date, amount, how). Give it every ledger row, closed ones too. Anything
    uncertain (a reference or amount that fits several bookings, a name that contradicts the
    reference) goes to each booking it might belong to, unconfirmed."""
    found = {r["booking_ref"]: [] for r in rows}
    by_key = {}
    for r in rows:
        by_key.setdefault(norm_ref(r["booking_ref"]), []).append(r)
    live = open_rows(rows, today)
    for it in items:
        amount = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = lm.local_date(it.get("transactionTime"))
        payer = it.get("counterPartyName") or ""
        keys = named_keys(it.get("reference"), by_key)
        if keys:
            refs, how = by_reference(keys, by_key, payer, amount, rows, when, today)
        else:
            refs = [r["booking_ref"] for r in rows if not is_cancelled(r) and fits_amount(amount, r)
                    and in_window(r, when, today) and payer_is(r, payer)]
            how = "name and amount" if len(refs) == 1 else "name and amount, several bookings"
            if not refs:  # a cancelled client paying without a reference: never an amount-only match on a live row
                refs = [r["booking_ref"] for r in rows if is_cancelled(r) and in_window(r, when, today) and payer_is(r, payer)]
                if refs:  # the same client's live booking gets it too, unconfirmed, so it is never chased meanwhile
                    refs += [r["booking_ref"] for r in live if in_window(r, when, today) and payer_is(r, payer)]
                how = "name, cancelled booking"
        if not refs:
            refs = [r["booking_ref"] for r in live if fits_amount(amount, r) and in_window(r, when, today)]
            how = "amount only" if len(refs) == 1 else "amount only, several bookings"
        if not refs:  # a split or odd amount from the client ("K FARROW" £300 then £275): unconfirmed, a hand check
            refs = [r["booking_ref"] for r in live if in_window(r, when, today) and payer_is(r, payer)]
            how = "name only, amount differs"
        for ref in dict.fromkeys(refs):
            found[ref].append((when, amount, how))
    return found


def hand_notes(notes):
    """The owner's own words: the script's auto notes and negated phrases ("not yet seen", "unpaid") removed."""
    return NOT_PAID.sub(" ~ ", MARK_NOTE.sub(" ", AUTO_NOTE.sub(" ", notes or "")))  # "~" keeps "balance to be paid in cash" apart


# A balance the client will pay in cash or by cheque, on the day or later ("balance to be paid in cash", "will pay
# balance in cash", "balance payable in cash on the day", "rest will be paid in cash", "cheque on the day").
# Also a future-tense note of the balance/rest/remainder with no cash/cheque mentioned at all ("rest will be paid
# by the father", "balance will be paid by her parents", "remainder to be paid by the church", "is paying the
# rest", "going to pay the balance"): this is still an arrangement, not a payment, whoever ends up paying it
# (R16). A future-tense phrase with no balance/rest/remainder mention ("will be paid by Friday") is neither
# NOTED_PAID nor ARRANGED: it is just chased normally.
FUTURE_PAY = r"(?:will\s+be\s+paid|to\s+be\s+paid|will\s+pay|is\s+paying|are\s+paying|going\s+to\s+pay)"
REST_WORDS = r"(?:balance|rest|remainder|remaining)"
ARRANGED_NOTE = re.compile(
    r"\b(?:to be|will be|payable|due)\b(?:(?![;.,]).){0,20}?\b(?:cash|cheque)\b"
    r"|\b(?:will|to|going to)\s+(?:pay|bring)\b(?:(?![;.,]).){0,25}?\b(?:cash|cheque)\b"
    r"|\b(?:cash|cheque)\s+on\s+the\s+day\b"
    r"|\b" + REST_WORDS + r"\b(?:(?![;.,]).){0,30}?\b" + FUTURE_PAY + r"\b"
    r"|\b" + FUTURE_PAY + r"\b(?:(?![;.,]).){0,30}?\b" + REST_WORDS + r"\b", re.I)
NEGATION = {"not", "no", "never", "longer", "wont", "cant"}
# A clause with a paid word ("balance paid in cash on the day" is a note of payment, not an arrangement; "to be
# paid" and "will be paid" still arrange), or with a negation, refusal or doubt anywhere in it ("told bank transfer
# only", "by transfer not cash", "was going to pay cash but will transfer"), never arranges a balance.
ARRANGED_PAID = re.compile(r"(?<!\bbe )(?<!\bdeposit )\b(paid|received|settled)\b", re.I)  # "deposit paid and ..." is the deposit
NOT_ARRANGED = re.compile(r"\b(not|never|no|nothing|won['’]?t|refus\w*|told|asked|about|instead|only|but)\b", re.I)


def arranged_notes(notes):
    """(True when a clause arranges a cash or cheque balance, the notes without those clauses). A negated,
    refused or already paid arrangement ("won't pay cash on the day", "balance paid in cash") doesn't count and
    stays in the notes."""
    base = MARK_NOTE.sub(" ", AUTO_NOTE.sub(" ", notes or ""))
    keep, found = [], False
    for clause in CLAUSE.split(base):
        hit = False
        if ARRANGED_PAID.search(clause) or NOT_ARRANGED.search(clause):
            keep.append(clause)
            continue
        for m in ARRANGED_NOTE.finditer(clause):
            before = words_before(clause, m.start(), 4)
            if not (NEGATION & set(before) or any(w.endswith(("n't", "n’t")) for w in before)):
                hit = True
        found = found or hit
        if not hit:
            keep.append(clause)
    return found, ("; ".join(keep) if found else notes or "")


def full_paid(own, value):
    """True when the owner's words record the whole fee as paid, not just the deposit."""
    for clause in CLAUSE.split(own):
        rest_paid = REST_PAID.search(clause)
        if clause.strip().lower().startswith("deposit"):
            # "deposit and balance paid in cash" is the whole fee; "deposit paid in full" is the deposit
            if rest_paid and OTHER_PART.search(rest_paid.group(0)):
                return True
            continue
        if rest_paid:
            return True
        if not FULL_PAID.search(clause):
            continue
        if not REST_WORD.search(clause) and any(lm.money(x) + 0.01 < value for x in POUNDS.findall(clause)):
            continue
        return True
    return False


def deposit_due_date(invoice, event):
    if not invoice:
        return None
    due = invoice + datetime.timedelta(days=7)
    if event:
        due = max(invoice + datetime.timedelta(days=1), min(due, event - datetime.timedelta(days=3)))
    return due


def books_cache():
    """The Command Centre's Books cache (cc_sync.py books); LCS_PRIVATE_DIR is read at call time."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "cache" / "books.json"


def unsent_invoices(path=None):
    """Booking refs whose Zoho Books invoice is still a draft, so the client hasn't been sent it (the daily pass
    marks an invoice sent only once Luca's email carrying it is in Sent). Read from the local cache, no network
    call. An invoice only moves on from draft, so a stale cache can hold a reminder back a day, never send one
    early. A missing or unreadable cache gives an empty set: every booking is then assessed as before."""
    try:
        data = json.loads(Path(path or books_cache()).read_text())
        return {str(i["number"]).strip() for i in data["invoices"]
                if str(i.get("status", "")).lower() == "draft" and str(i.get("number", "")).strip()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return set()


def noted_facts(f):
    """(noted part, noted full) from the recorded facts: the noted-paid facts, and a recorded "paid in full" close,
    which the notes' own "paid in full YYYY-MM-DD" says too (its "paid" is a paid word)."""
    full = bool(f.has("close") and f.paid_full_on)
    return f.noted_part or full, f.noted_full or full


def note_readings(r, today=None, facts=None):
    """assess's reading of the arrangement, noted paid and marker families for one row: {arranged, noted_hand,
    noted_full, noted_auto, reminded}. A family with recorded facts is read from them; markers are a union. The notes
    are read without the clauses the owner set aside (an undone fact's, lcs_events.set_aside): an undone marker
    un-marks."""
    f = facts_for(r, today, facts)
    value, notes = money(r), lcs_events.set_aside(r.get("notes"), f)
    arranged, rest = arranged_notes(notes)  # "rest will be paid in cash" is not a note of payment
    if f.has("arrangement"):
        arranged = f.arranged
    own = hand_notes(rest)
    noted_hand = bool(PAID_WORD.search(own))
    noted_full = full_paid(own, value)
    if f.has("noted paid"):
        noted_hand, noted_full = f.noted_part, f.noted_full
    if f.has("close") and f.paid_full_on:  # a recorded "paid in full" reads as the notes' own phrase does: paid
        noted_hand = noted_full = True
    marked = f.reminded  # markers are a union: a recorded reminder or receipt counts as the note does
    return {"arranged": arranged, "noted_hand": noted_hand, "noted_full": noted_full,
            # the script saw a deposit on an earlier run (union)
            "noted_auto": bool(AUTO_NOTE.search(notes)) or f.deposit_seen,
            "reminded": {"deposit": bool(re.search(r"(?<!balance )reminder drafted", notes, re.I)) or marked["deposit"],
                         "balance": bool(re.search(r"balance reminder drafted", notes, re.I)) or marked["balance"],
                         "receipt": bool(re.search(r"receipt drafted", notes, re.I)) or marked["receipt"]}}


def assess(r, paid, today, facts=None, unsent=None):
    """`unsent`: the refs whose Books invoice hasn't been sent yet (None reads unsent_invoices())."""
    value = money(r)
    f = facts_for(r, today, facts)
    sure = [p for p in paid if p[2] in CONFIDENT]
    maybe = [p for p in paid if p[2] not in CONFIDENT]
    total = round(sum(a for _, a, _ in sure), 2)
    first = min((d for d, _, _ in sure), default=None)
    invoice = date_or_none(r.get("invoice_date"))
    event_raw = (r.get("event_date") or "").strip()
    event = date_or_none(event_raw)
    deposit_due = deposit_due_date(invoice, event)
    read = note_readings(r, today, f)
    arranged, noted_hand, noted_full, noted_auto = (read[k] for k in ("arranged", "noted_hand", "noted_full",
                                                                       "noted_auto"))
    upcoming = event is None or event >= today
    close = closed_on(r, today, f)
    fees = fees_accepted(r, today, f)  # a shortfall the owner accepted as transfer fees ("short by fees £X accepted …")
    fee_day = max((d for d, _ in fee_notes(r, today, f)), default=None)
    # an unconfirmed payment after the first confident one, or the size of what is left, may be the balance
    possible_balance = [p for p in maybe if first and (p[0] >= first or abs(p[1] - (value - total)) < 0.01)]
    flagged = []  # payments on a cancelled or closed booking: never chased or thanked, always a hand check
    if is_cancelled(r, f):
        settled = cancel_settled_on(r, today, f)  # "deposit kept YYYY-MM-DD": payments up to then are dealt with
        flagged = [p for p in paid if in_window(r, p[0], today) and not (settled and p[0] <= settled.isoformat())]
        state = "PAYMENT_ON_CANCELLED" if flagged else "CANCELLED"
    elif close and any(d > close.isoformat() for d, _, _ in paid):
        flagged = [p for p in paid if p[0] > close.isoformat()]
        state = "PAYMENT_AFTER_CLOSE"
    elif not (math.isfinite(value) and value > 0) or invoice is None or (event_raw and event is None):
        state = "CHECK_VALUE"
    elif sure and total + fees + 0.01 >= value:  # a fee note never pays a booking with nothing confident in the bank
        state = "PAID_IN_FULL"
    elif sure:
        if noted_full:
            state = "NOTED_PAID"
        elif arranged and not (upcoming and possible_balance):  # a possible balance in the bank is checked now
            state = "ARRANGED"
        elif not upcoming:
            state = "PAST_PART_PAID"
        elif possible_balance:
            state = "CHECK_PAYMENT"
        elif event and today >= event - datetime.timedelta(days=3):
            state = "BALANCE_DUE"
        else:
            state = "DEPOSIT_SEEN"
    elif arranged and not noted_full and not maybe:
        state = "ARRANGED"
    elif noted_hand or (noted_auto and not maybe):
        state = "NOTED_PAID"
    elif noted_auto:  # an unconfirmed payment now outranks a stale "deposit seen … (Starling)"
        state = "CHECK_PAYMENT"
    elif not upcoming:
        state = "PAST_UNMATCHED"
    elif maybe:
        state = "CHECK_PAYMENT"
    else:
        state = "DEPOSIT_OVERDUE" if today > deposit_due else "AWAITING_DEPOSIT"
        if r["booking_ref"] in (unsent_invoices() if unsent is None else unsent):
            state = "AWAITING_INVOICE_SENT"  # the client has no invoice yet: nothing to chase
    reminded = read["reminded"]
    hold = held(r, today, f)  # notes and recorded facts disagree: the owner resolves it, nothing acts meanwhile
    # the part of the accepted fee that closes the gap: only in PAID_IN_FULL, never more than what is still owed
    fees_used = round(min(fees, max(value - total, 0)), 2) if state == "PAID_IN_FULL" else 0.0
    books = [[d, a, 0.0] for d, a, _ in sorted(sure)]  # [date, amount, bank charges]
    if books and fees_used:
        books[-1][2] = fees_used  # the fee goes on the last confident payment, as Books' bank charges
    first_day = date_or_none(first)
    just_received = bool(first_day and datetime.timedelta(0) <= today - first_day <= datetime.timedelta(days=RECEIPT_DAYS)
                       and not reminded["receipt"] and upcoming and state in RECEIPT_STATES and not hold)
    out = {
        "ref": r["booking_ref"], "state": state, "received": total, "value": value,
        "balance": round(max(value - total - fees_used, 0), 2), "first": first,
        "last": max((d for d, _, _ in sure), default=None),
        # the accepted fee that makes it PAID_IN_FULL (0.0 otherwise), and the date of the latest counting fee note
        "fees": fees_used, "fees_on": fee_day.isoformat() if fees_used and fee_day else None,
        "how": sure[0][2] if sure else (maybe[0][2] if state == "CHECK_PAYMENT" else ""),
        "unconfirmed": [[d, a] for d, a, _ in maybe],
        "possible_balance": [[d, a] for d, a, _ in possible_balance],
        "hand_check_payments": [[d, a] for d, a, _ in flagged],
        # an arranged balance with no deposit in the bank or the notes: on the Monday hand check every week
        "arranged_no_deposit": state == "ARRANGED" and not (sure or noted_hand or noted_auto),
        "event_date": event.isoformat() if event else None,
        "deposit_due": deposit_due.isoformat() if deposit_due else None,
        "short_notice": bool(invoice and event and (event - invoice).days <= SHORT_NOTICE_DAYS),
        "reminded": reminded,
        "just_received": just_received,  # draft a thank-you (action "receipt"); the one key for it
        # confident payments to record against the Books invoice: [[date, amount, bank charges]], oldest first,
        # the bank charges 0.0 except on the last one when an accepted fee closes the booking ("fees"); empty
        # unless the state is settled enough and the confident payments don't exceed the booking's value
        "record_in_books": books if state in BOOKS_STATES and total <= value + 0.01 and not hold else [],
    }
    if state == "AWAITING_INVOICE_SENT":  # only then, so every other assessment is exactly as before
        out["deposit_late"] = today > deposit_due  # the Monday hand check lists it from then on
    out["action"] = action_for(out, today)
    if hold:  # only when held, so an assessment with no recorded facts is exactly as before
        out["held"], out["action"] = hold, "hand_check"
    return out


ACTIONS = ("receipt", "deposit_reminder", "balance_reminder", "hand_check", "none")
HAND_CHECK_STATES = {"CHECK_PAYMENT", "CHECK_VALUE", "NOTED_PAID", "PAST_UNMATCHED", "PAST_PART_PAID",
                     "PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE"}
ARRANGED_CHECK_DAYS = 7


def action_for(a, today):
    """What the enquiry assistant does with one assessed booking (handover Appendix E, step 5a):
    receipt (a thank-you for a fresh confident payment), deposit_reminder or balance_reminder (once each),
    hand_check (listed under "Money to check by hand") or none."""
    reminded = a.get("reminded") or {}
    if a.get("just_received"):
        return "receipt"
    if a["state"] == "DEPOSIT_OVERDUE" and not reminded.get("deposit"):
        return "deposit_reminder"
    if a["state"] == "BALANCE_DUE" and not reminded.get("balance"):
        return "balance_reminder"
    if a["state"] in HAND_CHECK_STATES:
        return "hand_check"
    event = date_or_none(a.get("event_date"))
    if a["state"] == "ARRANGED" and event and (event - today).days <= ARRANGED_CHECK_DAYS:
        return "hand_check"  # so Luca remembers to collect the cash or cheque
    return "none"


def describe(a):
    line = describe_state(a)
    if a.get("held"):
        line += f" · notes and recorded facts disagree: {', '.join(a['held'])} (check by hand)"
    return line


def describe_state(a):
    line = f"{a['ref']}: £{a['received']:,.2f} of £{a['value']:,.2f} received"
    if a["first"]:
        line += f" (first {a['first']}, matched by {a['how']})"
    def listed(key):
        return ", ".join(f"£{x:,.2f} on {d}" for d, x in a.get(key) or [])
    maybe, flagged = listed("unconfirmed"), listed("hand_check_payments")
    if a["state"] == "CHECK_PAYMENT" and a["received"] and a.get("possible_balance"):
        return line + f" · possible balance payment {listed('possible_balance')} (unconfirmed): confirm by hand"
    return line + {
        "PAID_IN_FULL": " · PAID IN FULL" + (f" (£{a['fees']:,.2f} short by fees, accepted)" if a.get("fees") else ""),
        "DEPOSIT_SEEN": "",
        "AWAITING_DEPOSIT": " · awaiting deposit (not yet due)",
        "AWAITING_INVOICE_SENT": " · invoice still a draft in Books, not yet sent to the client (never chased)"
                                 + (f"; the deposit would have been due {a['deposit_due']}" if a.get("deposit_late") else ""),
        "BALANCE_DUE": f" · BALANCE £{a['balance']:,.2f} DUE" + (" (reminder already drafted)" if a["reminded"]["balance"] else ""),
        "DEPOSIT_OVERDUE": f" · DEPOSIT OVERDUE since {a['deposit_due']}" + (" (reminder already drafted)" if a["reminded"]["deposit"] else ""),
        "NOTED_PAID": (" · part paid in the bank feed; the ledger notes say the rest was paid" if a["received"]
                       else " · no matching payment in the bank feed, but the ledger notes say it was paid")
                      + " (check by hand, then add \"paid in full YYYY-MM-DD\" to the notes)",
        "PAST_UNMATCHED": " · event has passed; no matching payment in the bank feed (check by hand; never chase automatically)",
        "PAST_PART_PAID": " · event has passed; part paid (check by hand; never chase automatically)",
        "ARRANGED": " · balance arranged in cash or by cheque (never chase or thank; check by hand on the day)"
                    + ("; no deposit in the bank or the notes" if a.get("arranged_no_deposit") else ""),
        "CHECK_PAYMENT": f" · possible payment {maybe} matched by {a['how']}: confirm by hand",
        "CHECK_VALUE": (" · booking value missing or unreadable in the ledger (check by hand)" if a["value"] <= 0
                        else " · invoice or event date missing or unreadable in the ledger (check by hand)"),
        "CANCELLED": " · cancelled",
        "PAYMENT_ON_CANCELLED": f" · payment on a cancelled booking: {flagged} (check by hand: refund or keep; never chase or thank)",
        "PAYMENT_AFTER_CLOSE": f" · payment after paid in full: {flagged} (check by hand; never chase or thank)",
    }[a["state"]]


def updated_notes(notes, a, paid):
    """Ledger notes after this run; only confident matches (reference, name and amount) change them."""
    if a["state"] in NEVER_WRITTEN:  # cancelled or closed rows are never rewritten
        return notes
    sure = [p for p in paid if p[2] in CONFIDENT]
    new = notes
    if sure and is_pending(new):
        rest = new.split(";", 1)[1].strip() if ";" in new else re.sub(r"^\s*PENDING[\s:,-]*", "", new, flags=re.I).strip()
        rest = re.sub(r"^[\s,;]+", "", NOT_YET_SEEN.sub("", rest))  # the deposit has now been seen
        new = f"deposit seen {a['first']} (Starling)" + (f"; {rest}" if rest else "")
    if a["state"] == "PAID_IN_FULL" and sure and not FULL_NOTE.search(new):
        # closed by an accepted fee: dated the later of the last payment and the fee note, so the two notes agree
        # and the booking's close date (closed_on) doesn't move
        day = max([d for d, _, _ in sure] + ([a["fees_on"]] if a.get("fees") and a.get("fees_on") else []))
        new = (f"{new}; " if new.strip() else "") + f"paid in full {day}"
    return new


def open_rows(rows, today=None, facts=None):
    """Rows neither cancelled nor closed ("paid in full YYYY-MM-DD", or a counting "short by fees" note, or their
    recorded facts). `facts`: None (the log), or a mapping ref -> lcs_events.Facts."""
    out = []
    for r in rows:
        f = facts_for(r, today, facts)
        if not is_cancelled(r, f) and not is_closed(r, today, f):
            out.append(r)
    return out


# --- recorded facts against the notes (structured-state design, precedence rules 2 and 4) ------------------------

def clauses(notes):
    """The notes' clauses as the writers append them ("; " between clauses), stripped, empty ones dropped."""
    return [c.strip() for c in (notes or "").split(";") if c.strip()]


def unclaimed(notes, claims):
    """The notes' clauses that no recorded fact claims (lcs_events.note_hash), rejoined: hand edits and legacy
    text."""
    return "; ".join(c for c in clauses(notes) if lcs_events.note_hash(c) not in claims)


def assertions(text, value, today):
    """What this note text asserts, per family, read with today's patterns (or None where it says nothing):
    cancellation True (cancelled) or False (reinstated); close, cancel settlement and arrangement True;
    noted paid "part" or "full". Markers assert nothing: they are a union."""
    last = last_cancel(text)
    cancel = (not resumed_after(text, last)) if last >= 0 else (False if resumed_after(text, 0) else None)
    bare = {"notes": text}  # no booking_ref: read from the text alone
    arranged, rest = arranged_notes(text)
    own = hand_notes(rest)
    noted = "full" if full_paid(own, value) else "part" if PAID_WORD.search(own) else None
    return {"cancellation": cancel,
            "close": True if FULL_NOTE.search(text) or fee_notes(bare, today) else None,
            "cancel settlement": True if cancel_settled_on(bare, today) else None,
            "arrangement": True if arranged else None,
            "noted paid": noted}


HELD_FAMILIES = ("cancellation", "close", "cancel settlement", "arrangement", "noted paid")
FAMILY_OF = {k: fam for fam, kinds in lcs_events.FAMILIES["booking"].items() for k in kinds}


def family_readings(r, today, f):
    """Per family, (its reading from the notes alone, its reading from the recorded facts), whole: the cancellation;
    the close date and every counting fee (date, amount); the cancel-settlement date; the arrangement; noted paid
    (part, full). The notes are read without the clauses the owner set aside: those a fact he withdrew as a mistake
    claims, and those a live notes-checked confirms (the recorded facts are right there)."""
    none = lcs_events.Facts("booking")
    bare = dict(r, notes=lcs_events.set_aside(r.get("notes"), f))
    read = note_readings(bare, today, none)
    return {"cancellation": (is_cancelled(bare, none), f.cancelled),
            "close": ((closed_on(bare, today, none), sorted(fee_notes(bare, today, none))), (f.closed_on, sorted(f.fees))),
            "cancel settlement": (cancel_settled_on(bare, today, none), f.settled_on),
            "arrangement": (read["arranged"], f.arranged),
            "noted paid": ((read["noted_hand"], read["noted_full"]), noted_facts(f))}


def held(r, today=None, facts=None):
    """The families whose recorded facts the notes contradict, in a fixed order ([] when none): the booking is then
    held for the owner (a hand check, no reminder, receipt, Books line, review or upload). A family with facts is
    checked when the notes speak to it outside the facts: an unclaimed clause asserts something in it, or a clause
    one of its live facts claims is gone from the notes (deleted by hand); it is held when its whole reading from the
    notes then differs from the facts' (a hand-typed later fee, a refund after a kept deposit, a deleted
    cancellation). The cancellation family is held too when its latest fact by date and its latest written differ
    (a backdated cancellation written after a later reinstatement): the order the notes were written in no longer
    says the same thing as the dates."""
    today = today or lm.today()
    f = facts_for(r, today, facts)
    if not f.families - {"markers"}:
        return []
    said = assertions(unclaimed(r.get("notes"), f.claims), money(r), today)
    present = {lcs_events.note_hash(c) for c in clauses(r.get("notes"))}
    gone = {FAMILY_OF[e["kind"]] for e in f.live if e.get("note") and e["note"] not in present
            and FAMILY_OF.get(e["kind"]) in HELD_FAMILIES}
    order = f.of("cancelled", "reinstated")
    backdated = bool(order) and order[-1]["kind"] != ("cancelled" if f.cancelled else "reinstated")
    readings = None
    out = []
    for fam in HELD_FAMILIES:
        if not f.has(fam):
            continue
        if fam == "cancellation" and backdated:
            out.append(fam)
            continue
        if said[fam] is None and fam not in gone:
            continue
        readings = readings or family_readings(r, today, f)
        notes_say, facts_say = readings[fam]
        if notes_say != facts_say:
            out.append(fam)
    return out


def _day_words(d):
    return f"{d.day} {d:%b %Y}"


def reading_words(family, value):
    """One family's reading (family_readings' shape) in fixed words for the owner's pages: never note text."""
    if family == "cancellation":
        return "cancelled" if value else "not cancelled"
    if family == "close":
        closed, fees = value
        if not closed:
            return "open"
        return f"closed on {_day_words(closed)}" + "".join(f", £{x:,.2f} fees accepted on {_day_words(d)}"
                                                           for d, x in fees)
    if family == "cancel settlement":
        return f"settled on {_day_words(value)}" if value else "not settled"
    if family == "arrangement":
        return "balance arranged" if value else "nothing arranged"
    part, full = value  # noted paid
    return "noted paid in full" if full else "noted part paid" if part else "nothing noted paid"


def held_readings(r, today=None, facts=None):
    """held()'s families, each with both readings side by side for the owner: [{family, notes, facts, clauses}], the
    readings in fixed words (reading_words) and `clauses` the note hashes of the loose (unclaimed, not set aside)
    clauses that speak to that family, the ones "The recorded facts are right" (events.py notes-checked) claims. A
    family held only because a claimed clause was deleted by hand has no clause to confirm: [] (undo the fact, or
    record what the notes now say). [] when the booking isn't held."""
    today = today or lm.today()
    f = facts_for(r, today, facts)
    families = held(r, today, f)
    if not families:
        return []
    readings, value = family_readings(r, today, f), money(r)
    loose = [c for c in clauses(lcs_events.set_aside(r.get("notes"), f)) if lcs_events.note_hash(c) not in f.claims]
    out = []
    for fam in families:
        notes_say, facts_say = readings[fam]
        out.append({"family": fam, "notes": reading_words(fam, notes_say), "facts": reading_words(fam, facts_say),
                    "clauses": [lcs_events.note_hash(c) for c in loose
                                if assertions(c, value, today)[fam] is not None]})
    return out


def collect(client, rows, today):
    """[(row, paid, assessment)] in ledger order for every open booking, and for every cancelled or closed
    ("paid in full YYYY-MM-DD", "short by fees … accepted YYYY-MM-DD") booking with a payment that needs a hand
    check: on a cancelled booking, any payment inside its window; on a closed one, any payment dated after the
    close. A booking closed by a fee note and not yet marked "paid in full" (fee_pending) is reported too while it
    reads PAID_IN_FULL, so the daily pass records its fee in Books and --apply marks it. A cancelled or closed
    booking whose notes and recorded facts disagree (held) is reported too, as a hand check. Payments are matched
    against every row."""
    live = open_rows(rows, today)
    pending = [r for r in rows if fee_pending(r, today)]
    starts = [d - datetime.timedelta(days=3) for d in (date_or_none(r.get("invoice_date")) for r in live + pending) if d]
    for r in rows:
        w = window(r, today)
        if is_cancelled(r) and w and w[1] >= today:  # a booking still ahead: its deposit may be in the bank
            starts.append(w[0])
        elif not is_cancelled(r) and closed_on(r, today):  # a stray payment after the close lands now, not years ago
            starts.append(max(closed_on(r, today), today - datetime.timedelta(days=31)))
    shut_held = [r for r in rows if r not in live and held(r, today)]
    if not starts:  # nothing with a readable invoice date: no feed to read, but still report each open (or held) row
        return [(r, [], assess(r, [], today)) for r in rows if r in live or r in shut_held]
    found = match(rows, client.feed(min(starts), today + datetime.timedelta(days=1), "IN"), today)
    out = []
    for r in rows:
        paid = found[r["booking_ref"]]
        if r in live or r in shut_held or (paid and (is_cancelled(r) or closed_on(r, today))):
            a = assess(r, paid, today)
            if (r in live or r in shut_held or a["state"] in ("PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE")
                    or (r in pending and a["state"] == "PAID_IN_FULL")):
                out.append((r, paid, a))
    return out


def received_since(client, rows, since, today):
    """[(booking_ref, date, amount)] for confident client payments since a date (any non-cancelled booking).
    A payment on a closed booking dated after its "paid in full" (or accepted fee) date is left out: collect()
    puts it on the hand check instead."""
    live = {r["booking_ref"]: closed_on(r, today) for r in rows if not is_cancelled(r)}
    if not live:
        return []
    # the feed filters by UTC time: start a day early so 00:00-01:00 BST on `since` is included
    found = match(rows, client.feed(since - datetime.timedelta(days=1), today + datetime.timedelta(days=1), "IN"), today)
    return [(ref, d, a) for ref, hits in found.items() if ref in live
            for d, a, how in hits if how in CONFIDENT and d >= since.isoformat()
            and not (live[ref] and d > live[ref].isoformat())]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reminded", metavar="REF")
    ap.add_argument("--kind", choices=sorted(MARK_TEXT))
    ap.add_argument("--note", nargs=2, metavar=("REF", "TEXT"))
    ap.add_argument("--fact", nargs=2, metavar=("REF", "KIND"))
    ap.add_argument("--on", metavar="YYYY-MM-DD")
    ap.add_argument("--amount")
    ap.add_argument("--method")
    ap.add_argument("--scope")
    ap.add_argument("--owner", action="store_true", help="the Command Centre only: needs its one-time nonce on stdin")
    args = ap.parse_args()
    today = lm.today()

    # lm.locked_rows holds lm.ledger_lock, an flock on a fresh descriptor: NOT re-entrant. Never nest it, or
    # call another ledger writer while holding it, in one process: the second acquire deadlocks.
    if args.owner and not (args.note or args.fact):
        raise SystemExit("--owner goes with --note or --fact only; nothing written")
    if not args.fact and any(getattr(args, k) is not None for k in ("on", "amount", "method", "scope")):
        raise SystemExit("--on, --amount, --method and --scope go with --fact only; nothing written")
    if args.fact:
        if args.note or args.reminded or args.kind or args.apply or args.json or args.selftest:
            raise SystemExit("--fact goes on its own (with --on, --amount, --method, --scope, --owner); nothing written")
        ref = args.fact[0]
        kind, fields, by, day = fact_input(args, today)
        if by == "owner":
            where = lcs_owner.owner_folder_problem([LEDGER, lcs_events.log_path()])
            if where:
                raise SystemExit(f"--owner {where}; nothing written")
            if not owner_confirmed():
                raise SystemExit("--owner needs the Command Centre's one-time owner nonce (the owner's passkey "
                                 "approval); nothing written")
        append_note(ref, fact_phrase(kind, fields, day, by), [(kind, fields, by, day)])
        lcs_events.clear_cache()  # read the log afresh: was the fact recorded, or only its note?
        print(f"{ref}: {kind} recorded" if lcs_events.migration_applied()
              else f"{ref}: {kind} noted; facts start after the migration")
        return
    if args.note:
        ref, text = args.note
        by_note = "owner" if args.owner else "script"
        if "\n" in text or "\r" in text or len(text) > 120 or ";" in text:
            raise SystemExit("note text must be a single line, at most 120 characters, with no ';'")
        if args.owner:
            if is_pending(text):
                raise SystemExit("a note never starts with PENDING; nothing written")
            where = owner_ledger_problem()
            if where:
                raise SystemExit(f"--owner {where}; nothing written")
            if not owner_confirmed():
                raise SystemExit("--owner needs the Command Centre's one-time owner nonce (the owner's passkey "
                                 "approval); nothing written")
            text = f"{text} (owner)"
        elif reserved_note(text):
            raise SystemExit("that phrase is the scripts' own or the owner's (he writes it in the ledger by hand); "
                             "nothing written")
        elif NOTE_REFUSES_FACTS and note_refusal(ref, text):
            # the assistant records a cancellation, an arrangement or a client's "paid" with --fact (question 3);
            # the owner's --note (the Command Centre's nonce) is his own record and is not refused
            raise SystemExit(note_refusal(ref, text))
        # the facts a note states are recorded with it, claiming it (note_facts), so it never holds the booking: the
        # owner's own phrases, or (NOTE_REFUSES_FACTS off) the assistant's; a refused text never gets here
        append_note(ref, text, lambda row: note_facts(text, row, by_note, today))
        print(f"{ref}: note added")
        return

    if args.reminded:
        kind = args.kind or "deposit"
        append_note(args.reminded, f"{MARK_TEXT[kind]} {today}", [("reminder-drafted", {"what": kind}, "script", today)])
        print(f"{args.reminded}: {MARK_TEXT[kind]} noted")
        return
    if args.kind:
        raise SystemExit("--kind goes with --reminded only; nothing written")

    tok = lm.keychain_token()
    if not tok:
        msg = f"No Starling token in the Keychain (service {lm.KEYCHAIN_SERVICE}); payment check skipped."
        if args.json:
            print("[]")
        print(msg, file=sys.stderr if args.json else sys.stdout)
        return
    client = lm.StarlingReadOnly(tok)
    try:
        run(args, client, lm.read_csv(LEDGER), today)  # --apply takes the lock only after the Starling calls
    except lm.StarlingError as e:
        raise SystemExit(str(e))


# The owner barrier lives in lcs_owner (shared with the singer store and the state log); kept here under the old
# names, so the Command Centre and the tests need no change.
OWNER_NONCE_TTL = lcs_owner.OWNER_NONCE_TTL
owner_nonce_path = lcs_owner.owner_nonce_path


def owner_ledger_problem(environ=None):
    """None when an --owner note would land in the ledger beside the nonce, else the reason (lcs_owner.
    owner_folder_problem for LEDGER, read at call time)."""
    return lcs_owner.owner_folder_problem([LEDGER], environ)


def owner_confirmed(stdin_fd=0):
    """True only when the Command Centre ran this --owner note after the owner's passkey approval (lcs_owner.
    owner_confirmed: the one-time nonce over a pipe, burnt on a match)."""
    return lcs_owner.owner_confirmed(stdin_fd)


def append_note(ref, text, facts=None):
    """Append "; <text>" to one booking's notes, under the ledger lock. `facts`: [(kind, fields, by, day)], or a
    function of the row giving them, each recorded in the state log claiming that clause, under the same lock
    (lcs_events.recording: if the ledger isn't written after all, the facts are withdrawn)."""
    with lcs_events.recording(LEDGER) as t:
        for r in t.rows:
            if r["booking_ref"] == ref:
                notes = r.get("notes") or ""
                r["notes"] = (f"{notes}; " if notes.strip() else "") + text
                todo = facts(r) if callable(facts) else facts or ()
                have = facts_for(r, lm.today()) if todo else None
                for kind, fields, by, day in todo:
                    fam = FAMILY_OF[kind]
                    latest = max((lcs_events._date(e["on"]) for e in have.live if FAMILY_OF.get(e["kind"]) == fam),
                                 default=None)
                    if by == "script" and latest and day < latest:
                        raise SystemExit(f"{ref}: {day} is earlier than the booking's latest recorded {fam} fact "
                                         f"({latest}): only the owner may backdate one; nothing written")
                    lcs_events.record(t, "booking", ref, kind, fields, by, text, on=day)
                break
        else:
            raise SystemExit(f"no booking {ref}")


def starling_unavailable(args, e):
    """One line, type name (and HTTP status) only, since the message could carry bank data; nothing is written."""
    if args.json:
        print("[]")
    code = f" {e.code}" if isinstance(e, urllib.error.HTTPError) else ""
    print(f"Starling unavailable ({type(e).__name__}{code})", file=sys.stderr)


def run(args, client, rows, today):
    """Report (and with --apply, note) payments. All Starling calls happen first, on `rows` read without the
    lock; --apply then takes the lock, re-reads the ledger, and reassesses each booking from its fresh row
    (the same payments, no network) before writing, so an edit made meanwhile is kept."""
    if args.selftest:
        try:
            scopes = sorted(client.get("/api/v2/identity/token").get("scopes", []))
        except Exception as e:  # identity endpoint unavailable: still test the account call
            scopes = [f"(could not read scopes: {type(e).__name__})"]
        try:
            acct = client.account()
        except STARLING_DOWN as e:
            return starling_unavailable(args, e)
        print("Starling token works; account found (uid ends …" + acct["accountUid"][-4:] + ").")
        print("Token permissions: " + ", ".join(scopes))
        risky = [x for x in scopes if not x.startswith("(") and not x.endswith(":read")]
        if risky:
            print("Note: this token can do more than read: " + ", ".join(risky)
                  + ". The owner chose to keep it (CLAUDE.md, Payments); these scripts only ever send GET requests.")
        return

    try:
        results = collect(client, rows, today)
    except STARLING_DOWN as e:
        return starling_unavailable(args, e)
    if not results:
        print("[]" if args.json else "No open bookings to check.")
        return
    for _, _, a in results:
        if not args.json:
            print(describe(a))
    if args.json:
        print(json.dumps([a for _, _, a in results]))
    if args.apply and apply_notes(results, today) and not args.json:
        print("Ledger notes updated.")


def apply_notes(results, today):
    """Write updated_notes for each assessed booking under the lock, from the ledger as it is now, recording in the
    state log the facts its new clauses state: "deposit seen D (Starling)" (deposit-seen) and "paid in full D"
    (paid-in-full, basis bank: PAID_IN_FULL from confident payments is the only way updated_notes writes it). True
    if anything changed."""
    paid_by_ref = {r["booking_ref"]: paid for r, paid, _ in results}
    changed = False
    with lcs_events.recording(LEDGER) as t:
        for r in t.rows:
            if r.get("booking_ref") not in paid_by_ref:
                continue
            paid = paid_by_ref[r["booking_ref"]]
            notes = r.get("notes") or ""
            new = updated_notes(notes, assess(r, paid, today), paid)
            if new != notes:
                r["notes"], changed = new, True
                # (a ref the log can't take gets its note as before and no fact: record() skips it)
                for clause in [c for c in clauses(new) if c not in clauses(notes)]:
                    if AUTO_NOTE.fullmatch(clause):
                        lcs_events.record(t, "booking", r["booking_ref"], "deposit-seen", {}, "script", clause,
                                          on=clause[len("deposit seen "):][:10])
                    elif FULL_NOTE.fullmatch(clause):
                        lcs_events.record(t, "booking", r["booking_ref"], "paid-in-full", {"basis": "bank"}, "script",
                                          clause, on=clause[-10:])
    return changed


if __name__ == "__main__":
    main()
