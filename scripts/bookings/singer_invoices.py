#!/usr/bin/env python3
"""Track invoices from singers and organists (money OUT), READ-ONLY against
Starling. Records live in ~/lcs-private/singer-invoices.csv (mode 600).

    singer_invoices.py scan <saved message> --message-id ID --received YYYY-MM-DD --sender-email E --sender-name 'N'
    singer_invoices.py paid [--apply]      # match OUT payments; prints NEWLY PAID <message id>
    singer_invoices.py status              # unpaid invoices and totals
    singer_invoices.py thanked <message id>  # note that the "Paid!" reply was drafted

Bank details are stored as a fingerprint plus the last four digits, and only
"••••1234" is ever printed. This script never creates payees or payments: a new
singer is flagged for the owner to add in the Starling app, where Confirmation
of Payee runs. Changed bank details raise a warning to ring before paying.
"""

import argparse
import datetime
import email
import io
import re
import sys
from email import policy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

STORE = lm.PRIVATE / "singer-invoices.csv"
COLUMNS = ["message_id", "received", "singer_name", "singer_email", "invoice_ref", "amount_gbp",
           "bank_fp", "bank_last4", "payee", "bank_changed", "paid_on", "paid_amount", "notes"]
NEW_PAYEE = "NEW: add as a payee in the Starling app"

AMOUNT = r"(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d{2})?)"
SORT = re.compile(r"sort[\s\-]*code\W{0,5}(\d{2})\W?(\d{2})\W?(\d{2})(?!\d)", re.I)
ACCOUNT = re.compile(r"(?:account|acc|a/c)[\s\.]*(?:no|number|num|#)?\.?\W{0,5}(\d(?:\s?\d){7})(?!\d)", re.I)
TOTAL = re.compile(r"(?<![A-Za-z])(?:total\s+due|amount\s+due|balance\s+due|total\s+amount|grand\s+total|total)\b"
                   r"[^£\d\n]{0,15}£?\s*" + AMOUNT, re.I)
POUNDS = re.compile(r"£\s*" + AMOUNT)
REF = re.compile(r"(?:invoice|inv)\s*(?:no\.?|number|#|ref(?:erence)?)?\s*[:#\-]?\s*([A-Z]{0,5}[-/]?\d[\w\-/]{0,15})", re.I)


def extract(text):
    sort, acc, ref = SORT.search(text), ACCOUNT.search(text), REF.search(text)
    totals = TOTAL.findall(text)
    amount = lm.money(totals[-1]) if totals else max((lm.money(x) for x in POUNDS.findall(text)), default=0.0)
    return {"amount": round(amount, 2), "invoice_ref": ref.group(1) if ref else "",
            "sort_code": "".join(sort.groups()) if sort else "",
            "account_number": re.sub(r"\s", "", acc.group(1)) if acc else ""}


def surname(name):
    parts = re.findall(r"[a-z]+", (name or "").lower())
    return parts[-1] if parts else ""


def assess_new(inv, sender_email, sender_name, history, payee_fps, payee_names):
    """Payee status and warnings for a new invoice. payee_fps None = no Starling token."""
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    previous = [r for r in history if r.get("singer_email", "").lower() == sender_email.lower() and r.get("bank_fp")]
    warnings, changed = [], False
    if fp and previous and previous[-1]["bank_fp"] != fp:
        changed = True
        warnings.append(f"BANK DETAILS CHANGED since their last invoice (was ••••{previous[-1]['bank_last4']}, "
                        f"now ••••{lm.last4(inv['account_number'])}): ring them before paying")
    if payee_fps is None:
        payee = "unknown (no Starling token)"
    elif fp and fp in payee_fps:
        payee = f"existing: {payee_fps[fp]}"
    else:
        sn = surname(sender_name)
        by_name = [n for n in payee_names if sn and sn in n.lower()]
        if by_name and fp:
            payee = f"name matches payee {by_name[0]} but with different bank details"
            changed = True
            warnings.append(f"Starling payee '{by_name[0]}' has different bank details from this invoice: ring them before paying")
        elif by_name:
            payee = f"probably existing: {by_name[0]} (no bank details on the invoice)"
        else:
            payee = NEW_PAYEE
    if not fp:
        warnings.append("no bank details found on the invoice")
    return {"bank_fp": fp or "", "bank_last4": lm.last4(inv["account_number"]) if fp else "",
            "payee": payee, "bank_changed": "yes" if changed else "no", "warnings": warnings}


def match_paid(unpaid, out_items):
    """{message_id: (date, amount)} for OUT payments that settle an unpaid invoice (each payment used once)."""
    hits, used = {}, set()
    for r in sorted(unpaid, key=lambda r: r["received"]):
        amount = lm.money(r["amount_gbp"])
        names = {surname(r["singer_name"])}
        if r["payee"].startswith("existing: "):
            names.add(surname(r["payee"][len("existing: "):]))
        names.discard("")
        for i, it in enumerate(out_items):
            if i in used:
                continue
            paid = (it.get("amount") or {}).get("minorUnits", 0) / 100
            when = (it.get("transactionTime") or "")[:10]
            who = (it.get("counterPartyName") or "").lower()
            if abs(paid - amount) < 0.01 and when >= r["received"][:10] and any(n in who for n in names):
                hits[r["message_id"]] = (when, paid)
                used.add(i)
                break
    return hits


def summary(rows, today):
    unpaid = [r for r in rows if not r.get("paid_on")]
    ages = [(today - datetime.date.fromisoformat(r["received"][:10])).days for r in unpaid]
    return {"unpaid": len(unpaid), "unpaid_total": round(sum(lm.money(r["amount_gbp"]) for r in unpaid), 2),
            "oldest_days": max(ages, default=0), "bank_changed": sum(1 for r in unpaid if r.get("bank_changed") == "yes")}


def message_texts(path):
    """[(label, text)] for every PDF attachment in a saved message, then its body."""
    from invoice_text import raw_message
    from pypdf import PdfReader
    msg = email.message_from_string(raw_message(path), policy=policy.default)
    out = []
    for part in msg.walk():
        name = part.get_filename() or ""
        if name.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(part.get_payload(decode=True) or b""))
                out.append((name, "\n".join(p.extract_text() or "" for p in reader.pages)))
            except Exception:
                out.append((name, ""))
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is not None:
        out.append(("email body", re.sub(r"<[^>]+>", " ", body.get_content())))
    return out


def read_invoice(path):
    found = {"amount": 0.0, "invoice_ref": "", "sort_code": "", "account_number": ""}
    for _, text in message_texts(path):
        e = extract(text)
        if not found["amount"] and e["amount"]:
            found.update(amount=e["amount"], invoice_ref=e["invoice_ref"])
        if not found["sort_code"] and e["sort_code"] and e["account_number"]:
            found.update(sort_code=e["sort_code"], account_number=e["account_number"])
    return found


def first_name(name):
    return (name or "?").split()[0]


def cmd_scan(args, client):
    rows = lm.read_csv(STORE)
    if any(r["message_id"] == args.message_id for r in rows):
        print(f"already recorded: {args.message_id}")
        return
    inv = read_invoice(args.file)
    payees = client.payees() if client else None
    fps = lm.payee_fingerprints(payees) if payees is not None else None
    names = [p.get("payeeName", "") for p in payees] if payees is not None else []
    a = assess_new(inv, args.sender_email, args.sender_name, rows, fps, names)
    rows.append({"message_id": args.message_id, "received": args.received, "singer_name": args.sender_name,
                 "singer_email": args.sender_email.lower(), "invoice_ref": inv["invoice_ref"],
                 "amount_gbp": f"{inv['amount']:.2f}", "bank_fp": a["bank_fp"], "bank_last4": a["bank_last4"],
                 "payee": a["payee"], "bank_changed": a["bank_changed"], "paid_on": "", "paid_amount": "",
                 "notes": "; ".join(a["warnings"])})
    lm.write_csv(STORE, rows, COLUMNS)
    print(f"{first_name(args.sender_name)}: £{inv['amount']:,.2f} (ref {inv['invoice_ref'] or '?'}) · payee {a['payee']}"
          + (f" · bank ••••{a['bank_last4']}" if a["bank_last4"] else ""))
    for w in a["warnings"]:
        print(f"   ! {w}")


def cmd_paid(args, client):
    rows = lm.read_csv(STORE)
    unpaid = [r for r in rows if not r["paid_on"]]
    if not unpaid:
        print("No unpaid singer invoices.")
        return
    if not client:
        print("No Starling token; paid check skipped.")
        return
    today = datetime.date.today()
    since = min(datetime.date.fromisoformat(r["received"][:10]) for r in unpaid) - datetime.timedelta(days=1)
    hits = match_paid(unpaid, client.feed(since, today + datetime.timedelta(days=1), "OUT"))
    for r in rows:
        if r["message_id"] in hits:
            when, amount = hits[r["message_id"]]
            print(f"NEWLY PAID {r['message_id']}: {first_name(r['singer_name'])} £{amount:,.2f} on {when}")
            if args.apply:
                r["paid_on"], r["paid_amount"] = when, f"{amount:.2f}"
    if not hits:
        print("No new payments to singers matched.")
    elif args.apply:
        lm.write_csv(STORE, rows, COLUMNS)
        print("Singer invoice store updated.")


def cmd_status(args, client=None):
    rows = lm.read_csv(STORE)
    today = datetime.date.today()
    for r in rows:
        if not r["paid_on"]:
            print(f"{r['received']} {first_name(r['singer_name'])} £{lm.money(r['amount_gbp']):,.2f} "
                  f"(ref {r['invoice_ref'] or '?'}) · payee {r['payee']}"
                  + (" · BANK DETAILS CHANGED: ring before paying" if r["bank_changed"] == "yes" else ""))
    s = summary(rows, today)
    print(f"{s['unpaid']} unpaid, £{s['unpaid_total']:,.2f}, oldest {s['oldest_days']} days"
          + (f", {s['bank_changed']} with changed bank details" if s["bank_changed"] else ""))


def cmd_thanked(args, client=None):
    rows = lm.read_csv(STORE)
    for r in rows:
        if r["message_id"] == args.message_id:
            r["notes"] = (r["notes"] + "; " if r["notes"] else "") + f"paid reply drafted {datetime.date.today()}"
            lm.write_csv(STORE, rows, COLUMNS)
            print(f"{args.message_id}: paid reply noted")
            return
    raise SystemExit(f"no invoice {args.message_id}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("file")
    s.add_argument("--message-id", required=True)
    s.add_argument("--received", required=True)
    s.add_argument("--sender-email", required=True)
    s.add_argument("--sender-name", required=True)
    p = sub.add_parser("paid")
    p.add_argument("--apply", action="store_true")
    sub.add_parser("status")
    t = sub.add_parser("thanked")
    t.add_argument("message_id")
    args = ap.parse_args()
    tok = lm.keychain_token() if args.cmd in ("scan", "paid") else None
    client = lm.StarlingReadOnly(tok) if tok else None
    {"scan": cmd_scan, "paid": cmd_paid, "status": cmd_status, "thanked": cmd_thanked}[args.cmd](args, client)


if __name__ == "__main__":
    main()
