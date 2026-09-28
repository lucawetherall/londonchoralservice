#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY (see lcs_money.StarlingReadOnly).

    .venv/bin/python scripts/bookings/check_payments.py                  # report
    .venv/bin/python scripts/bookings/check_payments.py --apply          # also update ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --apply --json   # machine-readable, for the assistant
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111 [--kind deposit|balance|receipt]
    .venv/bin/python scripts/bookings/check_payments.py --selftest       # token, account and permissions

Matching: an incoming payment belongs to a booking when its reference contains
the invoice number; failing that, when its amount is the deposit or full fee and
the payer's name contains the client's surname; failing that, when its amount is
exactly the deposit or fee of one open booking and of no other, inside that
booking's invoice-to-event window.

States (assess): PAID_IN_FULL, DEPOSIT_SEEN, BALANCE_DUE (from 3 days before the
event), AWAITING_DEPOSIT (first 7 days), DEPOSIT_OVERDUE (future events only),
NOTED_PAID (ledger notes say paid), PAST_UNMATCHED / PAST_PART_PAID (past
events: reported, never chased). Output shows invoice numbers and amounts only.
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


def money(row):
    return lm.money(row.get("value_gbp"))


def window(r, today):
    start = datetime.date.fromisoformat(r["invoice_date"][:10]) - datetime.timedelta(days=3)
    end = (datetime.date.fromisoformat(r["event_date"][:10]) if r.get("event_date") else today) + datetime.timedelta(days=14)
    return start, end


def match(rows, items, today):
    """booking_ref -> list of (date, amount, how)."""
    found = {r["booking_ref"]: [] for r in rows}
    for it in items:
        amount = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = (it.get("transactionTime") or "")[:10]
        ref_text = re.sub(r"[^A-Z0-9]", " ", (it.get("reference") or "").upper())
        payer = (it.get("counterPartyName") or "").lower()
        hit = None
        for r in rows:
            ref = r["booking_ref"].upper()
            if re.search(rf"(?:^|\s)(?:INV\s*)?{re.escape(ref)}(?:\s|$)", ref_text) or f"INV{ref}" in ref_text.replace(" ", ""):
                hit = (r["booking_ref"], "reference")
                break
        if not hit:
            for r in rows:
                surname = (r.get("client_name") or "").strip().split(" ")[-1].lower()
                v = money(r)
                if surname and len(surname) > 2 and surname in payer and any(abs(amount - x) < 0.01 for x in (v, v / 2)):
                    hit = (r["booking_ref"], "name and amount")
                    break
        if not hit and when:
            day = datetime.date.fromisoformat(when)
            fits = [r for r in rows if any(abs(amount - x) < 0.01 for x in (money(r), money(r) / 2))
                    and window(r, today)[0] <= day <= window(r, today)[1]]
            same_value = [r for r in rows if abs(money(r) - money(fits[0])) < 0.01] if len(fits) == 1 else []
            if len(fits) == 1 and len(same_value) == 1:
                hit = (fits[0]["booking_ref"], "amount only")
        if hit:
            found[hit[0]].append((when, amount, hit[1]))
    return found


def assess(r, paid, today):
    value, notes = money(r), r.get("notes") or ""
    total = round(sum(a for _, a, _ in paid), 2)
    first = min((d for d, _, _ in paid), default=None)
    deposit_due = datetime.date.fromisoformat(r["invoice_date"][:10]) + datetime.timedelta(days=7)
    event = datetime.date.fromisoformat(r["event_date"][:10]) if r.get("event_date") else None
    pending = notes.upper().startswith("PENDING")
    manual = bool(re.search(r"\b(paid|deposit seen)\b", notes, re.I)) and not pending
    upcoming = event is None or event >= today
    if value > 0 and total + 0.01 >= value:
        state = "PAID_IN_FULL"
    elif not upcoming:
        state = "PAST_PART_PAID" if paid else ("NOTED_PAID" if manual else "PAST_UNMATCHED")
    elif not paid:
        state = ("NOTED_PAID" if manual else "DEPOSIT_OVERDUE") if today > deposit_due else "AWAITING_DEPOSIT"
    elif event and today >= event - datetime.timedelta(days=3):
        state = "BALANCE_DUE"
    else:
        state = "DEPOSIT_SEEN"
    return {
        "ref": r["booking_ref"], "state": state, "received": total, "value": value,
        "balance": round(max(value - total, 0), 2), "first": first, "how": paid[0][2] if paid else "",
        "event_date": event.isoformat() if event else None, "deposit_due": deposit_due.isoformat(),
        "reminded": {"deposit": bool(re.search(r"(?<!balance )reminder drafted", notes)),
                     "balance": "balance reminder drafted" in notes,
                     "receipt": "receipt drafted" in notes},
        "just_received": bool(paid) and pending,
    }


def describe(a):
    line = f"{a['ref']}: £{a['received']:,.2f} of £{a['value']:,.2f} received"
    if a["first"]:
        line += f" (first {a['first']}, matched by {a['how']})"
    return line + {
        "PAID_IN_FULL": " · PAID IN FULL",
        "DEPOSIT_SEEN": "",
        "AWAITING_DEPOSIT": " · awaiting deposit (not yet due)",
        "BALANCE_DUE": f" · BALANCE £{a['balance']:,.2f} DUE" + (" (reminder already drafted)" if a["reminded"]["balance"] else ""),
        "DEPOSIT_OVERDUE": f" · DEPOSIT OVERDUE since {a['deposit_due']}" + (" (reminder already drafted)" if a["reminded"]["deposit"] else ""),
        "NOTED_PAID": " · no matching payment in the bank feed, but the ledger notes say it was paid (check by hand)",
        "PAST_UNMATCHED": " · event has passed; no matching payment in the bank feed (check by hand; never chase automatically)",
        "PAST_PART_PAID": " · event has passed; part paid (check by hand; never chase automatically)",
    }[a["state"]]


def updated_notes(notes, a, paid):
    new = notes
    if paid and new.upper().startswith("PENDING"):
        rest = new.split(";", 1)[1].strip() if ";" in new else ""
        new = f"deposit seen {a['first']} (Starling)" + (f"; {rest}" if rest else "")
    if a["state"] == "PAID_IN_FULL" and not re.search(r"paid in full \d{4}-\d{2}-\d{2}", new):
        new += f"; paid in full {max(d for d, _, _ in paid)}"
    return new


def open_rows(rows):
    return [r for r in rows if not (r.get("notes") or "").upper().startswith("CANCELLED")
            and not re.search(r"paid in full \d{4}-\d{2}-\d{2}", r.get("notes") or "")]


def collect(client, rows, today):
    """[(row, paid, assessment)] for every open booking."""
    rows = open_rows(rows)
    if not rows:
        return []
    since = min(datetime.date.fromisoformat(r["invoice_date"][:10]) for r in rows) - datetime.timedelta(days=3)
    found = match(rows, client.feed(since, today + datetime.timedelta(days=1), "IN"), today)
    return [(r, found[r["booking_ref"]], assess(r, found[r["booking_ref"]], today)) for r in rows]


def received_since(client, rows, since, today):
    """[(booking_ref, date, amount)] for client payments since a date (any non-cancelled booking)."""
    live = [r for r in rows if not (r.get("notes") or "").upper().startswith("CANCELLED")]
    if not live:
        return []
    found = match(live, client.feed(since, today + datetime.timedelta(days=1), "IN"), today)
    return [(ref, d, a) for ref, hits in found.items() for d, a, _ in hits if d >= since.isoformat()]


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
                r["notes"] = (r.get("notes") or "") + f"; {MARK_TEXT[args.kind]} {today}"
                break
        else:
            raise SystemExit(f"no booking {args.reminded}")
        lm.write_csv(LEDGER, rows, cols)
        print(f"{args.reminded}: {MARK_TEXT[args.kind]} noted")
        return

    tok = lm.keychain_token()
    if not tok:
        print(f"No Starling token in the Keychain (service {lm.KEYCHAIN_SERVICE}); payment check skipped.")
        return
    client = lm.StarlingReadOnly(tok)
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
