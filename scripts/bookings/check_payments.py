#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY (see lcs_money.StarlingReadOnly).

    .venv/bin/python scripts/bookings/check_payments.py                  # report
    .venv/bin/python scripts/bookings/check_payments.py --apply          # also update ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --apply --json   # machine-readable, for the assistant
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111 [--kind deposit|balance|receipt]
    .venv/bin/python scripts/bookings/check_payments.py --selftest       # token, account and permissions

Matching (against every ledger row, closed ones too, so a payment is never
credited to the wrong booking): an incoming payment belongs to a booking when a
word of its reference is the invoice number ("INV2111", "INV 2111" and "2111"
all name 2111; "24081" does not name 2408). A reference that names any booking
is final. Failing that, when its amount is the deposit or full fee, the payer's
name contains the client's surname as a whole word, and it falls inside that
booking's invoice-to-event window. Failing that, when its amount is exactly the
deposit or fee of one open booking and of no other, inside that booking's
window: an "amount only" match, which is unconfirmed and never counts as paid.

States (assess): PAID_IN_FULL, DEPOSIT_SEEN, BALANCE_DUE (from 3 days before the
event), AWAITING_DEPOSIT (first 7 days), DEPOSIT_OVERDUE (future events only),
NOTED_PAID (ledger notes say paid), PAST_UNMATCHED / PAST_PART_PAID (past
events), CHECK_PAYMENT (only an unconfirmed amount-only match), CHECK_VALUE (no
readable booking value), CANCELLED. Only DEPOSIT_OVERDUE and BALANCE_DUE are
ever chased. Output shows invoice numbers and amounts only.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

LEDGER = lm.LEDGER
MARK_TEXT = {"deposit": "reminder drafted", "balance": "balance reminder drafted", "receipt": "receipt drafted"}
CONFIDENT = ("reference", "name and amount")
PAID_NOTE = re.compile(r"\b(balance (paid|received|settled)|paid in full|fully paid|paid by (cash|cheque|card|bank transfer)"
                       r"|paid (in )?cash)\b", re.I)
AUTO_NOTE = re.compile(r"deposit seen \d{4}-\d{2}-\d{2} \(Starling\)", re.I)
FULL_NOTE = re.compile(r"paid in full \d{4}-\d{2}-\d{2}", re.I)


def money(row):
    return lm.money(row.get("value_gbp"))


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


def ref_tokens(text):
    """Reference words, uppercased, with any INV prefix stripped ("INV2111" -> "2111"; "INV" alone dropped)."""
    toks = (t[3:] if t.startswith("INV") else t for t in re.split(r"[^A-Z0-9]+", (text or "").upper()))
    return {t for t in toks if t}


def fits_amount(amount, r):
    v = money(r)
    return v > 0 and any(abs(amount - x) < 0.01 for x in (v, v / 2))


def is_cancelled(r):
    return bool(re.search(r"\bcancel", r.get("notes") or "", re.I))


def is_pending(notes):
    return notes.lstrip().upper().startswith("PENDING")


def match(rows, items, today):
    """booking_ref -> list of (date, amount, how). Give it every ledger row, closed ones too; a payment
    whose reference names several bookings, or fits several by name, goes to each of them unconfirmed."""
    found = {r["booking_ref"]: [] for r in rows}
    by_ref = {}
    for r in rows:
        key = r["booking_ref"].strip().upper()
        by_ref.setdefault(key[3:] if key.startswith("INV") else key, set()).add(r["booking_ref"])
    live = open_rows(rows)
    for it in items:
        amount = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = lm.local_date(it.get("transactionTime"))
        payer = it.get("counterPartyName") or ""
        named = sorted(set().union(*(by_ref[t] for t in ref_tokens(it.get("reference")) if t in by_ref)))
        if named:
            refs, how = named, "reference" if len(named) == 1 else "reference naming several bookings"
        else:
            refs = [r["booking_ref"] for r in rows if not is_cancelled(r) and fits_amount(amount, r) and in_window(r, when, today)
                    and len(s := (r.get("client_name") or "").strip().split(" ")[-1]) > 2
                    and re.search(rf"\b{re.escape(s)}\b", payer, re.I)]
            how = "name and amount" if len(refs) == 1 else "name and amount, several bookings"
        if not refs:
            fits = [r for r in live if fits_amount(amount, r) and in_window(r, when, today)]
            same_value = [r for r in live if abs(money(r) - money(fits[0])) < 0.01] if len(fits) == 1 else []
            refs, how = ([fits[0]["booking_ref"]], "amount only") if len(same_value) == 1 else ([], "")
        for ref in refs:
            found[ref].append((when, amount, how))
    return found


def assess(r, paid, today):
    value, notes = money(r), r.get("notes") or ""
    sure = [p for p in paid if p[2] in CONFIDENT]
    maybe = [p for p in paid if p[2] not in CONFIDENT]
    total = round(sum(a for _, a, _ in sure), 2)
    first = min((d for d, _, _ in sure), default=None)
    deposit_due = datetime.date.fromisoformat(r["invoice_date"][:10]) + datetime.timedelta(days=7)
    event = date_or_none(r.get("event_date"))
    pending = is_pending(notes)
    after_pending = (notes.split(";", 1)[1] if ";" in notes else "") if pending else notes
    manual = bool(re.search(r"\b(paid|deposit seen)\b", after_pending, re.I))
    noted_full = bool(PAID_NOTE.search(AUTO_NOTE.sub("", notes)))
    upcoming = event is None or event >= today
    if is_cancelled(r):
        state = "CANCELLED"
    elif value <= 0:
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
    elif manual:
        state = "NOTED_PAID"
    elif not upcoming:
        state = "PAST_UNMATCHED"
    elif maybe:
        state = "CHECK_PAYMENT"
    else:
        state = "DEPOSIT_OVERDUE" if today > deposit_due else "AWAITING_DEPOSIT"
    return {
        "ref": r["booking_ref"], "state": state, "received": total, "value": value,
        "balance": round(max(value - total, 0), 2), "first": first,
        "how": sure[0][2] if sure else (maybe[0][2] if state == "CHECK_PAYMENT" else ""),
        "unconfirmed": [[d, a] for d, a, _ in maybe],
        "event_date": event.isoformat() if event else None, "deposit_due": deposit_due.isoformat(),
        "reminded": {"deposit": bool(re.search(r"(?<!balance )reminder drafted", notes, re.I)),
                     "balance": bool(re.search(r"balance reminder drafted", notes, re.I)),
                     "receipt": bool(re.search(r"receipt drafted", notes, re.I))},
        "just_received": bool(sure) and pending and state != "CANCELLED",
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
        "CHECK_VALUE": " · booking value missing or unreadable in the ledger (check by hand)",
        "CANCELLED": " · cancelled",
    }[a["state"]]


def updated_notes(notes, a, paid):
    """Ledger notes after this run; only confident matches (reference, name and amount) change them."""
    sure = [p for p in paid if p[2] in CONFIDENT]
    new = notes
    if sure and is_pending(new):
        rest = new.split(";", 1)[1].strip() if ";" in new else ""
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
    found = match(rows, client.feed(since, today + datetime.timedelta(days=1), "IN"), today)
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
    rows = lm.read_csv(LEDGER)
    cols = list(rows[0].keys()) if rows else []

    if args.reminded:
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
        run(args, client, rows, cols, today)
    except lm.StarlingError as e:
        raise SystemExit(str(e))


def run(args, client, rows, cols, today):
    if args.selftest:
        try:
            scopes = sorted(client.get("/api/v2/identity/token").get("scopes", []))
        except Exception as e:  # identity endpoint unavailable: still test the account call
            scopes = [f"(could not read scopes: {type(e).__name__})"]
        acct = client.account()
        print("Starling token works; account found (uid ends …" + acct["accountUid"][-4:] + ").")
        print("Token permissions: " + ", ".join(scopes))
        risky = [x for x in scopes if not x.startswith("(") and not x.endswith(":read")]
        if risky:
            print("WARNING: this token can do more than read: " + ", ".join(risky)
                  + ". Revoke it in the Starling developer portal and create one with only account-list:read and transaction:read.")
        return

    results = collect(client, rows, today)
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
