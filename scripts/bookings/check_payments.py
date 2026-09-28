#!/usr/bin/env python3
"""Confirm deposits and balances for London Choral Service bookings against the
Alma Consort Starling account, READ-ONLY.

The owner creates a Starling personal access token with read-only scopes
(account-list:read, transaction:read) and stores it in the macOS Keychain
himself (see the handover); Claude never sees it:
    security add-generic-password -a "$USER" -s lcs-starling-read -w
This script reads it from the Keychain at run time and never prints it.

    .venv/bin/python scripts/bookings/check_payments.py            # report only
    .venv/bin/python scripts/bookings/check_payments.py --apply    # also update the ledger notes
    .venv/bin/python scripts/bookings/check_payments.py --reminded 2111   # note that a reminder was drafted
    .venv/bin/python scripts/bookings/check_payments.py --selftest # token and account check

Matching: an incoming payment belongs to a booking when its reference contains
the invoice number (e.g. "INV 2111", "2111"); failing that, when its amount is
the deposit or the full fee and the payer's name contains the client's surname;
failing that, when its amount is exactly the deposit or the full fee of one open
booking and of no other, inside that booking's invoice-to-event window.
Only bookings still to come are ever reported as overdue: a past event, or a
ledger note saying it was paid, is never chased. Output shows invoice numbers, amounts and dates only: never payer names,
balances or unrelated transactions. --apply turns "PENDING…" notes into
"deposit seen <date> (Starling)" and adds "paid in full <date>" when covered.
"""

import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

API = "https://api.starlingbank.com"
KEYCHAIN_SERVICE = "lcs-starling-read"
LEDGER = Path(os.environ.get("LCS_BOOKINGS_CSV", Path.home() / "lcs-private" / "bookings.csv"))
TODAY = datetime.date.today()


def token():
    r = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def get(path, tok):
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def account(tok):
    accounts = get("/api/v2/accounts", tok).get("accounts", [])
    want = os.environ.get("LCS_STARLING_ACCOUNT_UID")
    for a in accounts:
        if not want or a.get("accountUid") == want:
            return a
    raise SystemExit("No matching Starling account (set LCS_STARLING_ACCOUNT_UID if there are several).")


def incoming(tok, acct, since):
    path = (f"/api/v2/feed/account/{acct['accountUid']}/category/{acct['defaultCategory']}/transactions-between"
            f"?minTransactionTimestamp={since.isoformat()}T00:00:00.000Z"
            f"&maxTransactionTimestamp={(TODAY + datetime.timedelta(days=1)).isoformat()}T00:00:00.000Z")
    items = get(path, tok).get("feedItems", [])
    return [i for i in items if i.get("direction") == "IN" and i.get("status") not in ("DECLINED", "REVERSED", "REFUNDED")]


def money(row):
    try:
        return float((row.get("value_gbp") or "0").replace("£", "").replace(",", ""))
    except ValueError:
        return 0.0


def window(r):
    start = datetime.date.fromisoformat(r["invoice_date"][:10]) - datetime.timedelta(days=3)
    end = (datetime.date.fromisoformat(r["event_date"][:10]) if r.get("event_date") else TODAY) + datetime.timedelta(days=14)
    return start, end


def match(rows, items):
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
                    and window(r)[0] <= day <= window(r)[1]]
            same_value = [r for r in rows if abs(money(r) - money(fits[0])) < 0.01] if len(fits) == 1 else []
            if len(fits) == 1 and len(same_value) == 1:
                hit = (fits[0]["booking_ref"], "amount only")
        if hit:
            found[hit[0]].append((when, amount, hit[1]))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--reminded", metavar="REF")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(LEDGER, newline=""))) if LEDGER.exists() else []
    cols = list(rows[0].keys()) if rows else []

    if args.reminded:
        for r in rows:
            if r["booking_ref"] == args.reminded:
                r["notes"] = (r.get("notes") or "") + f"; reminder drafted {TODAY}"
                break
        else:
            raise SystemExit(f"no booking {args.reminded}")
        with open(LEDGER, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        os.chmod(LEDGER, 0o600)
        print(f"{args.reminded}: reminder noted")
        return

    tok = token()
    if not tok:
        print(f"No Starling token in the Keychain (service {KEYCHAIN_SERVICE}); payment check skipped.")
        return
    if args.selftest:
        try:
            scopes = sorted(get("/api/v2/identity/token", tok).get("scopes", []))
        except Exception as e:  # identity endpoint unavailable: still test the account call
            scopes = [f"(could not read scopes: {type(e).__name__})"]
        acct = account(tok)
        print("Starling token works; account found (uid ends …" + acct["accountUid"][-4:] + ").")
        print("Token permissions: " + ", ".join(scopes))
        risky = [x for x in scopes if not x.startswith("(") and not x.endswith(":read")]
        if risky:
            print("WARNING: this token can do more than read: " + ", ".join(risky)
                  + ". Revoke it in the Starling developer portal and create one with only account-list:read and transaction:read.")
        return
    acct = account(tok)

    open_rows = [r for r in rows if not (r.get("notes") or "").upper().startswith("CANCELLED")
                 and not re.search(r"paid in full \d{4}-\d{2}-\d{2}", r.get("notes") or "")]
    if not open_rows:
        print("No open bookings to check.")
        return
    since = min(datetime.date.fromisoformat(r["invoice_date"][:10]) for r in open_rows) - datetime.timedelta(days=3)
    found = match(open_rows, incoming(tok, acct, since))
    changed = False
    for r in open_rows:
        ref, value, notes = r["booking_ref"], money(r), r.get("notes") or ""
        paid = found[ref]
        total = sum(a for _, a, _ in paid)
        first = min((d for d, _, _ in paid), default=None)
        how = paid[0][2] if paid else ""
        deposit_due = datetime.date.fromisoformat(r["invoice_date"][:10]) + datetime.timedelta(days=7)
        event = datetime.date.fromisoformat(r["event_date"][:10]) if r.get("event_date") else None
        line = f"{ref}: £{total:,.2f} of £{value:,.2f} received"
        if first:
            line += f" (first {first}, matched by {how})"
        manual = re.search(r"\b(paid|deposit seen)\b", notes, re.I) and not notes.upper().startswith("PENDING")
        upcoming = event is None or event >= TODAY
        if total + 0.01 >= value > 0:
            line += " · PAID IN FULL"
        elif not upcoming:
            if not paid:
                line += " · event has passed; no matching payment in the bank feed" + (
                    " (ledger notes say it was paid)" if manual else " (check by hand; never chase automatically)")
        elif not paid and TODAY > deposit_due:
            if manual:
                line += " · no matching payment in the bank feed, but the ledger notes say it was paid (check by hand)"
            else:
                line += f" · DEPOSIT OVERDUE since {deposit_due}" + (" (reminder already drafted)" if "reminder drafted" in notes else "")
        elif paid and event and TODAY >= event - datetime.timedelta(days=1):
            line += f" · BALANCE £{value - total:,.2f} DUE BY {event - datetime.timedelta(days=1)}"
        print(line)
        if args.apply and paid:
            new = notes
            if new.upper().startswith("PENDING"):
                rest = new.split(";", 1)[1].strip() if ";" in new else ""
                new = f"deposit seen {first} (Starling)" + (f"; {rest}" if rest else "")
            if total + 0.01 >= value > 0 and "paid in full" not in new:
                new += f"; paid in full {max(d for d, _, _ in paid)}"
            if new != notes:
                r["notes"], changed = new, True
    if args.apply and changed:
        by_ref = {r["booking_ref"]: r for r in open_rows}
        rows = [by_ref.get(r["booking_ref"], r) for r in rows]
        with open(LEDGER, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        os.chmod(LEDGER, 0o600)
        print("Ledger notes updated.")


if __name__ == "__main__":
    main()
