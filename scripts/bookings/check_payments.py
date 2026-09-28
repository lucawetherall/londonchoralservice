#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY (see lcs_money.StarlingReadOnly).

    .venv/bin/python scripts/bookings/check_payments.py                  # report
    .venv/bin/python scripts/bookings/check_payments.py --apply          # also update ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --apply --json   # machine-readable, for the assistant
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111 [--kind deposit|balance|receipt]
    .venv/bin/python scripts/bookings/check_payments.py --selftest       # token, account and permissions

Matching (against every ledger row, closed ones too, so a payment is never
credited to the wrong booking): an incoming payment belongs to a booking when its
reference names the invoice number ("INV2111", "INV 2111", "INV-2111",
"LCS2111", "INV2111DEPOSIT" and "2111" all name 2111; "24081" does not name
2408; "INV 1212 A" and "1212A" name 1212A). A reference that names any booking
is final, but it is only CONFIDENT when nothing contradicts it: a bare "1212"
when 1212A also exists needs the payer's surname to pick one, and a payer whose
surname fits another booking and not the named one leaves it unconfirmed on
both. Failing a reference, when its amount is the deposit or full fee, the
payer's name contains the client's surname as a whole word, and it falls inside
that booking's invoice-to-event window. Failing that, when its amount is the
deposit or fee of open bookings inside their window: an "amount only" match, on
each booking it fits, which is unconfirmed and never counts as paid.

States (assess): PAID_IN_FULL, DEPOSIT_SEEN, BALANCE_DUE (from 3 days before the
event), AWAITING_DEPOSIT (until the deposit falls due: 7 days after the invoice,
or 3 days before a short-notice event, never the invoice day), DEPOSIT_OVERDUE
(future events only), NOTED_PAID (ledger notes say paid), PAST_UNMATCHED /
PAST_PART_PAID (past events), CHECK_PAYMENT (only an unconfirmed match),
CHECK_VALUE (no readable booking value, invoice date or event date), CANCELLED.
Only DEPOSIT_OVERDUE and BALANCE_DUE are ever chased; just_received (a confident
payment in the last 14 days with no receipt drafted) asks for a thank-you, and
short_notice (event within 10 days of the invoice) asks for the full fee rather
than a deposit. Output shows invoice numbers and amounts only.
"""

import argparse
import datetime
import contextlib
import json
import math
import re
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

LEDGER = lm.LEDGER
MARK_TEXT = {"deposit": "reminder drafted", "balance": "balance reminder drafted", "receipt": "receipt drafted"}
CONFIDENT = ("reference", "name and amount")
RECEIPT_DAYS = 14
SHORT_NOTICE_DAYS = 10
STARLING_DOWN = (urllib.error.URLError, TimeoutError, OSError)  # URLError and HTTPError are OSErrors too
# The script's own notes, removed before reading the owner's hand-written ones.
AUTO_NOTE = re.compile(r"deposit seen \d{4}-\d{2}-\d{2} \(Starling\)", re.I)
MARK_NOTE = re.compile(r"\b(balance )?reminder drafted( \d{4}-\d{2}-\d{2})?|\breceipt drafted( \d{4}-\d{2}-\d{2})?", re.I)
FULL_NOTE = re.compile(r"paid in full \d{4}-\d{2}-\d{2}", re.I)
NOT_PAID = re.compile(r"(\b(not|un)|n't)\s*(yet\s+)?(been\s+)?(paid|received|seen|settled)\b", re.I)
# "deposit seen <date>;" is what the enquiry assistant writes by hand (handover Appendix E)
PAID_WORD = re.compile(r"\b(paid|received|settled)\b|\bdeposit\s+(seen|in)\b", re.I)
# With a confident deposit in the bank, only a note of the WHOLE fee stops a balance chase.
_DATE = r"\d{1,2}(st|nd|rd|th)?\s+[a-z]{3,9}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}"
FULL_PAID = re.compile(
    r"\bbalance\s+(paid|received|settled)\b|\bpaid\s+in\s+full\b|\bfully\s+paid\b"
    r"|(?<!deposit )\bpaid\s+(on\s+)?(" + _DATE + r")\b|(?<!deposit )\bpaid\s+the\s+balance\b"
    r"|\bsettled\s+in\s+cash\b|\bbalance\s+in\s+cash\b"
    r"|(?<!deposit )\bpaid\s+(by\s+|in\s+)?(cash|cheque|card|bank\s+transfer)\b", re.I)
PREFIX = r"(INVOICE|INV|LCS)"
REF_TOKEN = re.compile(r"(?:" + PREFIX + r"\s*[-#:]?\s*(?=\d))?([A-Z0-9]+)")


def money(row):
    v = lm.money(row.get("value_gbp"))
    return v if math.isfinite(v) else 0.0  # "nan"/"inf" are unreadable, not a price


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
    """Known refs a payment reference names. "INV 1212 A" or "1212A" name 1212A when it exists; glued
    forms ("INV2111DEPOSIT", "LCS2111") try the longest known candidate first; "24081" never names 2408."""
    toks = [(bool(m.group(1)), m.group(2)) for m in REF_TOKEN.finditer((text or "").upper())]
    out = set()
    for i, (prefixed, t) in enumerate(toks):
        m = re.fullmatch(r"(\d+)([A-Z]*)", t)
        if not m:
            continue
        digits, letters = m.groups()
        nxt = toks[i + 1] if i + 1 < len(toks) else (True, "")
        cands = [digits + nxt[1]] if not letters and not nxt[0] and re.fullmatch(r"[A-Z]", nxt[1]) else []
        cands.append(t)
        if prefixed and letters and len(digits) == 4:
            cands += [digits + letters[0], digits]
        hit = next((c for c in cands if c in known), None)
        if hit:
            out.add(hit)
    return out


def surname(r):
    s = (r.get("client_name") or "").strip().split(" ")[-1]
    return s if len(s) > 2 else ""


def payer_is(r, payer):
    s = surname(r)
    return bool(s and re.search(rf"\b{re.escape(s)}\b", payer or "", re.I))


def fits_amount(amount, r):
    v = money(r)
    return v > 0 and any(abs(amount - x) < 0.01 for x in (v, v / 2))


def is_cancelled(r):
    return bool(re.search(r"(?<!not )\b(cancell?ed|cancellation (confirmed|received))\b", r.get("notes") or "", re.I))


def is_pending(notes):
    return notes.lstrip().upper().startswith("PENDING")


def by_reference(keys, by_key, payer, rows, when, today):
    """(booking refs, how) for a payment whose reference names these ledger keys."""
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
    others = sorted({r["booking_ref"] for r in rows if r["booking_ref"] != refs[0] and payer_is(r, payer)
                     and in_window(r, when, today)})
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
            refs, how = by_reference(keys, by_key, payer, rows, when, today)
        else:
            refs = [r["booking_ref"] for r in rows if not is_cancelled(r) and fits_amount(amount, r)
                    and in_window(r, when, today) and payer_is(r, payer)]
            how = "name and amount" if len(refs) == 1 else "name and amount, several bookings"
        if not refs:
            refs = [r["booking_ref"] for r in live if fits_amount(amount, r) and in_window(r, when, today)]
            how = "amount only" if len(refs) == 1 else "amount only, several bookings"
        for ref in dict.fromkeys(refs):
            found[ref].append((when, amount, how))
    return found


def hand_notes(notes):
    """The owner's own words: the script's auto notes and negated phrases ("not yet seen", "unpaid") removed."""
    return NOT_PAID.sub(" ", MARK_NOTE.sub(" ", AUTO_NOTE.sub(" ", notes or "")))


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
    own = hand_notes(notes)
    noted_any = bool(PAID_WORD.search(own) or AUTO_NOTE.search(notes))  # the script saw a deposit before
    noted_full = bool(FULL_PAID.search(own))
    upcoming = event is None or event >= today
    if is_cancelled(r):
        state = "CANCELLED"
    elif not (math.isfinite(value) and value > 0) or invoice is None or (event_raw and event is None):
        state = "CHECK_VALUE"
    elif total + 0.01 >= value:
        state = "PAID_IN_FULL"
    elif sure:
        if noted_full:
            state = "NOTED_PAID"
        elif not upcoming:
            state = "PAST_PART_PAID"
        elif event and today >= event - datetime.timedelta(days=3):
            state = "BALANCE_DUE"
        else:
            state = "DEPOSIT_SEEN"
    elif noted_any:
        state = "NOTED_PAID"
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
    receipt_due = bool(first_day and datetime.timedelta(0) <= today - first_day <= datetime.timedelta(days=RECEIPT_DAYS)
                       and not reminded["receipt"] and upcoming
                       and state != "CANCELLED" and not state.startswith(("PAST_", "CHECK_")))
    return {
        "ref": r["booking_ref"], "state": state, "received": total, "value": value,
        "balance": round(max(value - total, 0), 2), "first": first,
        "how": sure[0][2] if sure else (maybe[0][2] if state == "CHECK_PAYMENT" else ""),
        "unconfirmed": [[d, a] for d, a, _ in maybe],
        "event_date": event.isoformat() if event else None,
        "deposit_due": deposit_due.isoformat() if deposit_due else None,
        "short_notice": bool(invoice and event and (event - invoice).days <= SHORT_NOTICE_DAYS),
        "reminded": reminded,
        "receipt_due": receipt_due,
        "just_received": receipt_due,  # old name, same meaning: draft a thank-you
    }


def describe(a):
    line = f"{a['ref']}: £{a['received']:,.2f} of £{a['value']:,.2f} received"
    if a["first"]:
        line += f" (first {a['first']}, matched by {a['how']})"
    maybe = ", ".join(f"£{x:,.2f} on {d}" for d, x in a["unconfirmed"])
    return line + {
        "PAID_IN_FULL": " · PAID IN FULL",
        "DEPOSIT_SEEN": "",
        "AWAITING_DEPOSIT": " · awaiting deposit (not yet due)",
        "BALANCE_DUE": f" · BALANCE £{a['balance']:,.2f} DUE" + (" (reminder already drafted)" if a["reminded"]["balance"] else ""),
        "DEPOSIT_OVERDUE": f" · DEPOSIT OVERDUE since {a['deposit_due']}" + (" (reminder already drafted)" if a["reminded"]["deposit"] else ""),
        "NOTED_PAID": (" · part paid in the bank feed; the ledger notes say the rest was paid (check by hand)" if a["received"]
                       else " · no matching payment in the bank feed, but the ledger notes say it was paid (check by hand)"),
        "PAST_UNMATCHED": " · event has passed; no matching payment in the bank feed (check by hand; never chase automatically)",
        "PAST_PART_PAID": " · event has passed; part paid (check by hand; never chase automatically)",
        "CHECK_PAYMENT": f" · possible payment {maybe} matched by {a['how']}: confirm by hand",
        "CHECK_VALUE": (" · booking value missing or unreadable in the ledger (check by hand)" if a["value"] <= 0
                        else " · invoice or event date missing or unreadable in the ledger (check by hand)"),
        "CANCELLED": " · cancelled",
    }[a["state"]]


def updated_notes(notes, a, paid):
    """Ledger notes after this run; only confident matches (reference, name and amount) change them."""
    sure = [p for p in paid if p[2] in CONFIDENT]
    new = notes
    if sure and is_pending(new):
        rest = new.split(";", 1)[1].strip() if ";" in new else re.sub(r"^\s*PENDING[\s:,-]*", "", new, flags=re.I).strip()
        new = f"deposit seen {a['first']} (Starling)" + (f"; {rest}" if rest else "")
    if a["state"] == "PAID_IN_FULL" and sure and not FULL_NOTE.search(new):
        new = (f"{new}; " if new.strip() else "") + f"paid in full {max(d for d, _, _ in sure)}"
    return new


def open_rows(rows):
    return [r for r in rows if not is_cancelled(r) and not FULL_NOTE.search(r.get("notes") or "")]


def collect(client, rows, today):
    """[(row, paid, assessment)] for every open booking; payments are matched against every row."""
    live = open_rows(rows)
    starts = [d for d in (date_or_none(r.get("invoice_date")) for r in live) if d]
    if not live or not starts:
        return []
    found = match(rows, client.feed(min(starts) - datetime.timedelta(days=3), today + datetime.timedelta(days=1), "IN"), today)
    return [(r, found[r["booking_ref"]], assess(r, found[r["booking_ref"]], today)) for r in live]


def received_since(client, rows, since, today):
    """[(booking_ref, date, amount)] for confident client payments since a date (any non-cancelled booking)."""
    live = {r["booking_ref"] for r in rows if not is_cancelled(r)}
    if not live:
        return []
    # the feed filters by UTC time: start a day early so 00:00-01:00 BST on `since` is included
    found = match(rows, client.feed(since - datetime.timedelta(days=1), today + datetime.timedelta(days=1), "IN"), today)
    return [(ref, d, a) for ref, hits in found.items() if ref in live
            for d, a, how in hits if how in CONFIDENT and d >= since.isoformat()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reminded", metavar="REF")
    ap.add_argument("--kind", choices=sorted(MARK_TEXT), default="deposit")
    args = ap.parse_args()
    today = datetime.date.today()

    if args.reminded:
        with lm.ledger_lock(LEDGER):
            rows = lm.read_csv(LEDGER)
            cols = list(rows[0].keys()) if rows else []
            for r in rows:
                if r["booking_ref"] == args.reminded:
                    r["notes"] = (f"{r['notes']}; " if (r.get("notes") or "").strip() else "") + f"{MARK_TEXT[args.kind]} {today}"
                    break
            else:
                raise SystemExit(f"no booking {args.reminded}")
            lm.write_csv(LEDGER, rows, cols)
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
        with lm.ledger_lock(LEDGER) if args.apply else contextlib.nullcontext():
            rows = lm.read_csv(LEDGER)
            run(args, client, rows, list(rows[0].keys()) if rows else [], today)
    except lm.StarlingError as e:
        raise SystemExit(str(e))


def starling_unavailable(args, e):
    """One line, type name only (the message could carry bank data); nothing is written."""
    if args.json:
        print("[]")
    print(f"Starling unavailable ({type(e).__name__})", file=sys.stderr)


def run(args, client, rows, cols, today):
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
            print("WARNING: this token can do more than read: " + ", ".join(risky)
                  + ". Revoke it in the Starling developer portal and create one with only account-list:read and transaction:read.")
        return

    try:
        results = collect(client, rows, today)
    except STARLING_DOWN as e:
        return starling_unavailable(args, e)
    if not results:
        print("[]" if args.json else "No open bookings to check.")
        return
    changed = False
    for r, paid, a in results:
        if not args.json:
            print(describe(a))
        if args.apply:
            new = updated_notes(r.get("notes") or "", a, paid)
            if new != (r.get("notes") or ""):
                r["notes"], changed = new, True
    if args.json:
        print(json.dumps([a for _, _, a in results]))
    if args.apply and changed:
        lm.write_csv(LEDGER, rows, cols)
        if not args.json:
            print("Ledger notes updated.")


if __name__ == "__main__":
    main()
