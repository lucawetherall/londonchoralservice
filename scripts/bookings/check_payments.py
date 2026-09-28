#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY (see lcs_money.StarlingReadOnly).

    .venv/bin/python scripts/bookings/check_payments.py                  # report
    .venv/bin/python scripts/bookings/check_payments.py --apply          # also update ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --apply --json   # machine-readable, for the assistant;
        each item's "action" is receipt | deposit_reminder | balance_reminder | hand_check | none (action_for)
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111 [--kind deposit|balance|receipt]
    .venv/bin/python scripts/bookings/check_payments.py --note 2111 "paid per client email 2026-09-28"
        (one line, at most 120 characters, no ';'; refuses the scripts' own phrases and the owner's hand-written
        ones: paid in full, deposit seen … (Starling), reminder/receipt drafted, deposit kept, refunded,
        payment checked, reinstated and the like, review request …, and anything starting PENDING)
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

States (assess): PAID_IN_FULL, DEPOSIT_SEEN, BALANCE_DUE (from 3 days before the
event), AWAITING_DEPOSIT (until the deposit falls due: 7 days after the invoice,
or 3 days before a short-notice event, never the invoice day), DEPOSIT_OVERDUE
(future events only), NOTED_PAID (the owner's notes say paid, or an earlier run's
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
after a "paid in full YYYY-MM-DD" note; received_since leaves it out) and ARRANGED
(the notes say the balance will come in cash or by cheque: "balance to be paid in
cash", "will pay balance in cash", "balance payable in cash on the day", "rest will
be paid in cash", "cheque on the day"; not when the clause has a paid word ("balance
paid in cash on the day" is NOTED_PAID) or a negation, refusal or doubt anywhere in
it ("told bank transfer only", "by transfer not cash", "going to pay cash but will
transfer"), and a note of the whole fee paid still wins. Never chased or thanked; on the Monday
hand check from 7 days before the event, or every week when no deposit is in the bank
or the notes. A possible balance payment in the bank makes it CHECK_PAYMENT instead).
Only DEPOSIT_OVERDUE and BALANCE_DUE are ever chased; just_received (a confident
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
import hashlib
import hmac
import json
import math
import os
import re
import select
import stat
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

LEDGER = lm.LEDGER
MARK_TEXT = {"deposit": "reminder drafted", "balance": "balance reminder drafted", "receipt": "receipt drafted"}
CONFIDENT = ("reference", "name and amount")
RECEIPT_DAYS = 14
SHORT_NOTICE_DAYS = 10
# A thank-you is only ever drafted in these states; notes are never rewritten in the others.
RECEIPT_STATES = {"PAID_IN_FULL", "DEPOSIT_SEEN", "BALANCE_DUE", "NOTED_PAID"}
NEVER_WRITTEN = {"CANCELLED", "PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE"}
# URLError and HTTPError are OSErrors too; a non-JSON 200 body (an outage page) is a JSONDecodeError
STARLING_DOWN = (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError)
# The script's own notes, removed before reading the owner's hand-written ones.
AUTO_NOTE = re.compile(r"deposit seen \d{4}-\d{2}-\d{2} \(Starling\)", re.I)
MARK_NOTE = re.compile(r"\b(balance )?reminder drafted( \d{4}-\d{2}-\d{2})?|\breceipt drafted( \d{4}-\d{2}-\d{2})?", re.I)
FULL_NOTE = re.compile(r"paid in full \d{4}-\d{2}-\d{2}", re.I)
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
    r"|\bwill\s+(have\s+)?(pay|paid)\b" + _gap()
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


def is_cancelled(r):
    """True when the notes' latest cancellation is not undone by a later resumed phrase."""
    notes = r.get("notes") or ""
    last = -1
    for m in CANCEL_WORD.finditer(notes):
        if not IF_WORDS & set(words_before(notes, m.start())):
            last = m.start()
    for m in CANCELLING.finditer(notes):
        if not MAYBE_WORDS & set(words_before(notes, m.start())):
            last = max(last, m.start())
    if last < 0:
        return False
    for m in RESUMED.finditer(notes, last):
        before = words_before(notes, m.start(), 4)
        if DOUBT_WORDS & set(before) or any(w.endswith(("n't", "n’t")) for w in before):
            continue
        if m.group(0).lower().startswith("back") and before[-1:] and before[-1] in CALL_WORDS:
            continue
        after = re.findall(r"[a-z'’]+", notes[m.end():].lower())[:3]
        if ELSEWHERE_WORDS & set(after):
            continue
        return False
    return True


# "deposit kept 2026-09-15", "refunded 2026-09-20", "payment checked 2026-09-28" on a cancelled row: payments up to
# that date have been dealt with; only a later one is a hand check. A note dated after today silences nothing.
SETTLED_NOTE = re.compile(
    r"(?<!not )\b(?:deposit kept|refunded|(?:payment|refund|deposit) checked)\s+(\d{4}-\d{2}-\d{2})\b", re.I)


# The pipeline's own note on a ledger row (pipeline.py reviewed / review-skipped).
REVIEW_NOTE = re.compile(r"review request (drafted|skipped)", re.I)
# Phrases --note never writes: the scripts' own notes, and the ones the owner writes by hand in the ledger
# (paid in full, deposit kept / refunded / checked, reinstated), which close, settle or reopen a booking.
RESERVED_NOTES = (FULL_NOTE, AUTO_NOTE, MARK_NOTE, SETTLED_NOTE, RESUMED, REVIEW_NOTE)


def reserved_note(text):
    """True when --note must refuse this text: a reserved phrase, or anything starting with PENDING."""
    return is_pending(text) or any(p.search(text) for p in RESERVED_NOTES)


def cancel_settled_on(r, today):
    days = [date_or_none(m.group(1)) for m in SETTLED_NOTE.finditer(r.get("notes") or "")]
    return max((d for d in days if d and d <= today), default=None)


def closed_on(r):
    """The latest "paid in full YYYY-MM-DD" date in the notes, or None: the booking is closed from then."""
    days = [date_or_none(m.group(0)[-10:]) for m in FULL_NOTE.finditer(r.get("notes") or "")]
    return max((d for d in days if d), default=None)


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
    others = sorted({r["booking_ref"] for r in open_rows(rows) if r["booking_ref"] != refs[0] and payer_is(r, payer)
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
    live = open_rows(rows)
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
ARRANGED_NOTE = re.compile(
    r"\b(?:to be|will be|payable|due)\b(?:(?![;.,]).){0,20}?\b(?:cash|cheque)\b"
    r"|\b(?:will|to|going to)\s+(?:pay|bring)\b(?:(?![;.,]).){0,25}?\b(?:cash|cheque)\b"
    r"|\b(?:cash|cheque)\s+on\s+the\s+day\b", re.I)
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


def assess(r, paid, today):
    value, notes = money(r), r.get("notes") or ""
    sure = [p for p in paid if p[2] in CONFIDENT]
    maybe = [p for p in paid if p[2] not in CONFIDENT]
    total = round(sum(a for _, a, _ in sure), 2)
    first = min((d for d, _, _ in sure), default=None)
    invoice = date_or_none(r.get("invoice_date"))
    event_raw = (r.get("event_date") or "").strip()
    event = date_or_none(event_raw)
    deposit_due = deposit_due_date(invoice, event)
    arranged, rest = arranged_notes(notes)  # "rest will be paid in cash" is not a note of payment
    own = hand_notes(rest)
    noted_hand = bool(PAID_WORD.search(own))
    noted_auto = bool(AUTO_NOTE.search(notes))  # the script saw a deposit on an earlier run
    noted_full = full_paid(own, value)
    upcoming = event is None or event >= today
    close = closed_on(r)
    # an unconfirmed payment after the first confident one, or the size of what is left, may be the balance
    possible_balance = [p for p in maybe if first and (p[0] >= first or abs(p[1] - (value - total)) < 0.01)]
    flagged = []  # payments on a cancelled or closed booking: never chased or thanked, always a hand check
    if is_cancelled(r):
        settled = cancel_settled_on(r, today)  # "deposit kept YYYY-MM-DD": payments up to then are dealt with
        flagged = [p for p in paid if in_window(r, p[0], today) and not (settled and p[0] <= settled.isoformat())]
        state = "PAYMENT_ON_CANCELLED" if flagged else "CANCELLED"
    elif close and any(d > close.isoformat() for d, _, _ in paid):
        flagged = [p for p in paid if p[0] > close.isoformat()]
        state = "PAYMENT_AFTER_CLOSE"
    elif not (math.isfinite(value) and value > 0) or invoice is None or (event_raw and event is None):
        state = "CHECK_VALUE"
    elif total + 0.01 >= value:
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
    reminded = {"deposit": bool(re.search(r"(?<!balance )reminder drafted", notes, re.I)),
                "balance": bool(re.search(r"balance reminder drafted", notes, re.I)),
                "receipt": bool(re.search(r"receipt drafted", notes, re.I))}
    first_day = date_or_none(first)
    just_received = bool(first_day and datetime.timedelta(0) <= today - first_day <= datetime.timedelta(days=RECEIPT_DAYS)
                       and not reminded["receipt"] and upcoming and state in RECEIPT_STATES)
    out = {
        "ref": r["booking_ref"], "state": state, "received": total, "value": value,
        "balance": round(max(value - total, 0), 2), "first": first,
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
    }
    out["action"] = action_for(out, today)
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
    line = f"{a['ref']}: £{a['received']:,.2f} of £{a['value']:,.2f} received"
    if a["first"]:
        line += f" (first {a['first']}, matched by {a['how']})"
    def listed(key):
        return ", ".join(f"£{x:,.2f} on {d}" for d, x in a.get(key) or [])
    maybe, flagged = listed("unconfirmed"), listed("hand_check_payments")
    if a["state"] == "CHECK_PAYMENT" and a["received"] and a.get("possible_balance"):
        return line + f" · possible balance payment {listed('possible_balance')} (unconfirmed): confirm by hand"
    return line + {
        "PAID_IN_FULL": " · PAID IN FULL",
        "DEPOSIT_SEEN": "",
        "AWAITING_DEPOSIT": " · awaiting deposit (not yet due)",
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
        new = (f"{new}; " if new.strip() else "") + f"paid in full {max(d for d, _, _ in sure)}"
    return new


def open_rows(rows):
    return [r for r in rows if not is_cancelled(r) and not FULL_NOTE.search(r.get("notes") or "")]


def collect(client, rows, today):
    """[(row, paid, assessment)] in ledger order for every open booking, and for every cancelled or closed
    ("paid in full YYYY-MM-DD") booking with a payment that needs a hand check: on a cancelled booking,
    any payment inside its window; on a closed one, any payment dated after the close. Payments are
    matched against every row."""
    live = open_rows(rows)
    starts = [d - datetime.timedelta(days=3) for d in (date_or_none(r.get("invoice_date")) for r in live) if d]
    for r in rows:
        w = window(r, today)
        if is_cancelled(r) and w and w[1] >= today:  # a booking still ahead: its deposit may be in the bank
            starts.append(w[0])
        elif not is_cancelled(r) and closed_on(r):  # a stray payment after the close lands now, not years ago
            starts.append(max(closed_on(r), today - datetime.timedelta(days=31)))
    if not starts:  # nothing with a readable invoice date: no feed to read, but still report each open row
        return [(r, [], assess(r, [], today)) for r in live]
    found = match(rows, client.feed(min(starts), today + datetime.timedelta(days=1), "IN"), today)
    out = []
    for r in rows:
        paid = found[r["booking_ref"]]
        if r in live or (paid and (is_cancelled(r) or closed_on(r))):
            a = assess(r, paid, today)
            if r in live or a["state"] in ("PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE"):
                out.append((r, paid, a))
    return out


def received_since(client, rows, since, today):
    """[(booking_ref, date, amount)] for confident client payments since a date (any non-cancelled booking).
    A payment on a closed booking dated after its "paid in full" date is left out: collect() puts it on
    the hand check instead."""
    live = {r["booking_ref"]: closed_on(r) for r in rows if not is_cancelled(r)}
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
    ap.add_argument("--kind", choices=sorted(MARK_TEXT), default="deposit")
    ap.add_argument("--note", nargs=2, metavar=("REF", "TEXT"))
    ap.add_argument("--owner", action="store_true", help="the Command Centre only: needs its one-time nonce on stdin")
    args = ap.parse_args()
    today = lm.today()

    # lm.locked_rows holds lm.ledger_lock, an flock on a fresh descriptor: NOT re-entrant. Never nest it, or
    # call another ledger writer while holding it, in one process: the second acquire deadlocks.
    if args.owner and not args.note:
        raise SystemExit("--owner goes with --note only; nothing written")
    if args.note:
        ref, text = args.note
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
        append_note(ref, text)
        print(f"{ref}: note added")
        return

    if args.reminded:
        append_note(args.reminded, f"{MARK_TEXT[args.kind]} {today}")
        print(f"{args.reminded}: {MARK_TEXT[args.kind]} noted")
        return

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


OWNER_NONCE_TTL = 60  # seconds: the Command Centre writes the file moments before it runs this script


def owner_nonce_path():
    """<private dir>/command-centre/owner-nonce (LCS_PRIVATE_DIR read at call time)."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "owner-nonce"


def owner_ledger_problem(environ=None):
    """None when an --owner note would land in the ledger beside the nonce, else the reason. The nonce proves the
    app asked; this proves the note goes to the ledger the app read: LCS_BOOKINGS_CSV must be unset (the app never
    sets it for its subprocesses) and the ledger must sit directly in the nonce's private dir."""
    environ = os.environ if environ is None else environ
    if environ.get("LCS_BOOKINGS_CSV"):
        return "refuses LCS_BOOKINGS_CSV (the ledger must be the one in the private folder)"
    private = owner_nonce_path().parent.parent
    try:
        if Path(LEDGER).resolve().parent != private.resolve():
            return "needs the ledger in the same private folder as the nonce"
    except OSError:
        return "couldn't resolve the ledger's folder"
    return None


def owner_confirmed(stdin_fd=0):
    """True only when the Command Centre ran this --owner note after the owner's passkey approval: stdin is a pipe
    (not a terminal, not a redirected file) whose first line hashes (sha256) to the contents of the one-time nonce
    file, and that file is a regular file (never followed through a symlink), this user's, mode 600 with no group
    or other bits, and under OWNER_NONCE_TTL seconds old. The file is deleted on a match, so a nonce works once.
    The nonce itself lives only in the app's memory and the pipe; the file holds its hash, so redirecting the
    file into stdin fails twice over. No allowlisted command can pipe or write that file (plan, Task 3.1)."""
    try:
        if not stat.S_ISFIFO(os.fstat(stdin_fd).st_mode):
            return False
        path = owner_nonce_path()
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return False
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077
                or not -5 <= time.time() - st.st_mtime <= OWNER_NONCE_TTL or st.st_size > 200):
            return False
        want = os.read(fd, 200).decode("ascii", "replace").strip()
    finally:
        os.close(fd)
    if not re.fullmatch(r"[0-9a-f]{64}", want):
        return False
    ready, _, _ = select.select([stdin_fd], [], [], 2.0)  # an idle, open pipe never hangs the script
    if not ready:
        return False
    line = os.read(stdin_fd, 200).decode("ascii", "replace").split("\n", 1)[0].strip()
    if not re.fullmatch(r"[0-9a-f]{64}", line):
        return False
    if not hmac.compare_digest(hashlib.sha256(line.encode("ascii")).hexdigest(), want):
        return False
    try:
        os.unlink(path)  # single use: burnt before the note is written
    except OSError:
        return False
    return True


def append_note(ref, text):
    """Append "; <text>" to one booking's notes, under the ledger lock."""
    with lm.locked_rows(LEDGER) as t:
        for r in t.rows:
            if r["booking_ref"] == ref:
                notes = r.get("notes") or ""
                r["notes"] = (f"{notes}; " if notes.strip() else "") + text
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
    """Write updated_notes for each assessed booking under the lock, from the ledger as it is now. True if
    anything changed."""
    paid_by_ref = {r["booking_ref"]: paid for r, paid, _ in results}
    changed = False
    with lm.locked_rows(LEDGER) as t:
        for r in t.rows:
            if r.get("booking_ref") not in paid_by_ref:
                continue
            paid = paid_by_ref[r["booking_ref"]]
            notes = r.get("notes") or ""
            new = updated_notes(notes, assess(r, paid, today), paid)
            if new != notes:
                r["notes"], changed = new, True
    return changed


if __name__ == "__main__":
    main()
