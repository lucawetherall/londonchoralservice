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
of Payee runs. New bank details, and details that differ from the ones already
trusted for that singer (same email or same name), raise a warning to ring
before paying. A payment settles one invoice once: its feed item id is stored,
and a payment that fits several singers, or predates the invoice, is only
reported for a check by hand.
"""

import argparse
import datetime
import email
import html
import io
import re
import sys
import urllib.error
from email import policy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

STORE = lm.PRIVATE / "singer-invoices.csv"
COLUMNS = ["message_id", "received", "singer_name", "singer_email", "invoice_ref", "amount_gbp",
           "bank_fp", "bank_last4", "payee", "bank_changed", "paid_on", "paid_amount", "paid_ref", "notes"]
NEW_PAYEE = "NEW: add as a payee in the Starling app"
NEW_DETAILS = "NEW BANK DETAILS: confirm them by phone on a number you already hold before adding the payee"
LOOKBACK = datetime.timedelta(days=14)  # a payment up to 14 days before an invoice arrived is reported, not applied
INVOICING_DOMAINS = ("intuit.com", "quickbooks.com", "xero.com", "freeagent.com", "zohoinvoice.com", "zoho.com",
                     "sumup.com", "paypal.com", "stripe.com", "invoice2go.com", "wave.com", "waveapps.com")
TRADE_WORDS = {"music", "singer", "soprano", "alto", "tenor", "bass", "baritone", "mezzo", "organist", "ltd", "limited"}

AMOUNT = r"(\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d{2})?)"
MONEY = r"(?:(?:£|GBP)\s*" + AMOUNT + r"|(\d{1,3}(?:,\d{3})+\.\d{2}|\d+\.\d{2}))(?![\d.,]?\d)"
LABELS = [  # highest rank first; the first match of the best label present wins
    r"(?<![a-z])(?:amount|balance|total)\s+(?:due|payable)\b",
    r"(?<![a-z\-])(?<!sub )(?:grand\s+)?total\b(?!\s*\(?\s*(?:vat|tax|paid|hours|of|ex|excl\w*|net)\b)",
]
LABELS = [re.compile(lab + r"[^£\d\n]{0,15}?" + MONEY, re.I) for lab in LABELS]
POUNDS = re.compile(r"£\s*" + AMOUNT)
REF = re.compile(r"(?:invoice|inv)\s*(?:no\.?|number|#|ref(?:erence)?)?\s*[:#\-]?\s*([A-Z]{0,5}[-/]?\d[\w\-/]{0,15})", re.I)
SORT = re.compile(r"(?<![a-z])(?:sort[\s\-]*code|s/c)\W{0,5}(\d{2})\W?(\d{2})\W?(\d{2})(?!\d)", re.I)
ACCOUNT = re.compile(r"(?<![a-z])(?:account|acc|a/c)(?![a-z])(?:\s*(?:no|number|num|#))?\.?\W{0,5}"
                     r"(\d{7,8}|\d{4} \d{3,4})(?![ ]?\d)", re.I)
TABLE = re.compile(r"(?<![a-z])sort[\s\-]*code\b[^\n]*\n[ \t]*(\d{2})[-. ]?(\d{2})[-. ]?(\d{2})[ \t]+(\d{7,8})(?!\d)", re.I)
IBAN = re.compile(r"\bGB\d{2} ?[A-Z]{4}(?: ?\d){14}(?!\d)")
NOT_OURS = re.compile(r"\b(?:customer|client|your|reference)\b", re.I)  # a label like "Customer account no."


def _iban_ok(iban):
    s = iban[4:] + iban[:4]
    return int("".join(str(int(c, 36)) for c in s)) % 97 == 1


def extract_amount(text):
    for label in LABELS:
        m = label.search(text)
        if m:
            return lm.money(m.group(1) or m.group(2))
    return max((lm.money(x) for x in POUNDS.findall(text)), default=0.0)


def extract_bank(text):
    """(sort code, account number), or blanks when absent or ambiguous."""
    line = lambda pos: text.count("\n", 0, pos)  # noqa: E731
    sorts = [("".join(m.groups()), line(m.start())) for m in SORT.finditer(text)]
    accs = [(re.sub(r"\s", "", m.group(1)), line(m.start())) for m in ACCOUNT.finditer(text)
            if not NOT_OURS.search(text[max(0, m.start() - 12):m.start()])]
    for m in TABLE.finditer(text):
        sorts.append(("".join(m.groups()[:3]), line(m.start(4))))
        accs.append((m.group(4), line(m.start(4))))
    for m in IBAN.finditer(text):
        iban = re.sub(r"\s", "", m.group(0)).upper()
        if _iban_ok(iban):
            sorts.append((iban[8:14], line(m.start())))
            accs.append((iban[14:22], line(m.start())))
    if len({s for s, _ in sorts}) > 1:
        return "", ""
    sort = sorts[0][0] if sorts else ""
    if sorts and accs:  # the account number nearest (in lines) to the sort code; a tie is ambiguous
        dist = {}
        for a, ln in accs:
            d = min(abs(ln - s_ln) for _, s_ln in sorts)
            dist[a] = min(d, dist.get(a, d))
        best = min(dist.values())
        near = [a for a, d in dist.items() if d == best]
    else:
        near = list({a for a, _ in accs})
    return sort, near[0] if len(near) == 1 else ""


def clean_ref(ref, sort_code, account):
    digits = re.sub(r"\D", "", ref)
    if re.fullmatch(r"\d{8}", ref) or (digits and digits in (sort_code, account)):
        return ""
    return ref


def extract(text):
    text = re.sub(r"[^\S\n]", " ", text)  # non-breaking and other odd spaces
    ref = REF.search(text)
    sort, acc = extract_bank(text)
    return {"amount": round(extract_amount(text), 2), "invoice_ref": clean_ref(ref.group(1) if ref else "", sort, acc),
            "sort_code": sort, "account_number": acc}


def normalise_name(name):
    """'Fenwick, Ben (tenor)' / 'Ben Fenwick Music via QuickBooks' -> 'ben fenwick'."""
    n = re.sub(r"\s+via\s.*$", "", (name or "").lower())
    n = re.sub(r"\([^)]*\)", " ", n)
    parts = []
    for part in n.split(","):
        words = re.findall(r"[^\W\d_]+", part)
        while words and words[-1] in TRADE_WORDS:
            words.pop()
        if words:
            parts.append(words)
    if len(parts) == 2:
        parts.reverse()
    return " ".join(w for p in parts for w in p)


def surname(name):
    parts = normalise_name(name).split()
    return parts[-1] if parts else ""


def name_in(name, text):
    """Whole-word match of a name token (3+ letters) in text."""
    return len(name) >= 3 and re.search(rf"\b{re.escape(name)}\b", (text or "").lower()) is not None


def same_email(a, b):
    a, b = (a or "").lower(), (b or "").lower()
    domain = a.rpartition("@")[2]
    return bool(a) and a == b and not any(domain == d or domain.endswith("." + d) for d in INVOICING_DOMAINS)


def singer_history(rows, sender_email, sender_name):
    key = normalise_name(sender_name)
    return [r for r in rows if same_email(r.get("singer_email"), sender_email)
            or (key and normalise_name(r.get("singer_name")) == key)]


def received_date(r):
    try:
        return datetime.date.fromisoformat((r.get("received") or "")[:10])
    except ValueError:
        return None


def assess_new(inv, sender_email, sender_name, history, payee_fps, payee_names):
    """Payee status and warnings for a new invoice. history = all stored rows; payee_fps None = no Starling token."""
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    mine = [r for r in singer_history(history, sender_email, sender_name) if r.get("bank_fp")]
    trusted = sorted((r for r in mine if r.get("paid_on") or r.get("bank_changed") != "yes"),
                     key=lambda r: r.get("received") or "")
    trusted_fps = {r["bank_fp"] for r in trusted}
    warnings, changed = [], False
    if fp and trusted_fps and fp not in trusted_fps:
        changed = True
        warnings.append(f"BANK DETAILS CHANGED since their last invoice (was ••••{trusted[-1].get('bank_last4', '')}, "
                        f"now ••••{lm.last4(inv['account_number'])}): ring them before paying")
    if payee_fps is None:
        payee = "unknown (no Starling token)"
    elif fp and fp in payee_fps:
        payee = f"existing: {payee_fps[fp]}"
    else:
        sn = surname(sender_name)
        by_name = [n for n in payee_names if name_in(sn, n)]
        if by_name and fp:
            payee = f"name matches payee {by_name[0]} but with different bank details"
            changed = True
            warnings.append(f"Starling payee '{by_name[0]}' has different bank details from this invoice: ring them before paying")
        elif by_name:
            payee = f"probably existing: {by_name[0]} (no bank details on the invoice)"
        else:
            payee = NEW_PAYEE
    if fp and fp not in trusted_fps and not (payee_fps and fp in payee_fps):
        warnings.append(NEW_DETAILS)
    if not fp:
        warnings.append("no bank details found on the invoice")
        if trusted:
            warnings.append("no bank details on the invoice: compare them with "
                            f"••••{trusted[-1].get('bank_last4', '')} before paying")
    return {"bank_fp": fp or "", "bank_last4": lm.last4(inv["account_number"]) if fp else "",
            "payee": payee, "bank_changed": "yes" if changed else "no", "warnings": warnings}


def item_uid(it):
    return it.get("feedItemUid") or "|".join(str(x) for x in (
        it.get("transactionTime"), (it.get("amount") or {}).get("minorUnits"), it.get("counterPartyName")))


def payer_names(r):
    names = {surname(r.get("singer_name"))}
    if (r.get("payee") or "").startswith("existing: "):
        names.add(surname(r["payee"][len("existing: "):]))
    return {n for n in names if len(n) >= 3}


def match_paid(unpaid, out_items, report=None):
    """{message_id: (date, amount, feed item uid)} for OUT payments that settle an unpaid invoice.

    Payments are taken oldest first and each settles at most one invoice (a singer's oldest first).
    A payment that fits invoices from different singers, or that predates the invoice, is only
    added to `report`."""
    report = [] if report is None else report
    open_ = sorted((r for r in unpaid if received_date(r)), key=lambda r: r["received"])
    hits = {}
    for it in sorted(out_items, key=lambda i: i.get("transactionTime") or ""):
        paid = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = lm.local_date(it.get("transactionTime"))
        who = it.get("counterPartyName") or ""
        fits = [r for r in open_ if r["message_id"] not in hits and abs(paid - lm.money(r["amount_gbp"])) < 0.01
                and when >= (received_date(r) - LOOKBACK).isoformat() and any(name_in(n, who) for n in payer_names(r))]
        on_time = [r for r in fits if when >= r["received"][:10]]
        pool = on_time or fits
        if not pool:
            continue
        if len({normalise_name(r.get("singer_name")) or r["message_id"] for r in pool}) > 1:
            report.append(f"AMBIGUOUS £{paid:,.2f} on {when}: check by hand")
        elif on_time:
            hits[pool[0]["message_id"]] = (when, paid, item_uid(it))
        else:
            report.append(f"POSSIBLY ALREADY PAID {pool[0]['message_id']}: {first_name(pool[0]['singer_name'])} "
                          f"£{paid:,.2f} on {when} (before the invoice arrived): check by hand")
    return hits


def summary(rows, today):
    unpaid = [r for r in rows if not r.get("paid_on")]
    ages = [(today - d).days for d in map(received_date, unpaid) if d]
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
        text = body.get_content()
        if body.get_content_type() == "text/html":
            text = re.sub(r"<[^>]+>", " ", html.unescape(text))
        out.append(("email body", text))
    return out


def read_invoice(path):
    found = {"amount": 0.0, "invoice_ref": "", "sort_code": "", "account_number": "", "warnings": []}
    for label, text in message_texts(path):
        if label != "email body" and not text.strip():
            found["warnings"].append(f"could not read {label} (encrypted or damaged): check it by hand")
        e = extract(text)
        if not found["amount"] and e["amount"]:
            found["amount"] = e["amount"]
        if not found["invoice_ref"] and e["invoice_ref"]:
            found["invoice_ref"] = e["invoice_ref"]
        if not found["sort_code"] and e["sort_code"] and e["account_number"]:
            found.update(sort_code=e["sort_code"], account_number=e["account_number"])
    found["invoice_ref"] = clean_ref(found["invoice_ref"], found["sort_code"], found["account_number"])
    if not found["amount"]:
        found["warnings"].append("amount not found: check the invoice by hand")
    return found


def first_name(name):
    return ((name or "").split() or ["?"])[0]


def iso_date(value):
    """argparse type: YYYY-MM-DD or a longer ISO timestamp -> YYYY-MM-DD (Europe/London)."""
    try:
        if len(value) == 10:
            return datetime.date.fromisoformat(value).isoformat()
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return lm.local_date(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not an ISO date: {value!r}") from None


def note(r, text):
    r["notes"] = (r["notes"] + "; " if r.get("notes") else "") + text


def cmd_scan(args, client):
    rows = lm.read_csv(STORE)
    if any(r["message_id"] == args.message_id for r in rows):
        print(f"already recorded: {args.message_id}")
        return
    inv = read_invoice(args.file)
    payees = client.payees() if client else None
    fps = lm.payee_fingerprints(payees) if payees is not None else None
    names = [p.get("payeeName", "") for p in payees] if payees is not None else []
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    for r in singer_history(rows, args.sender_email, args.sender_name):  # scanned out of order: flag the newer one
        if (fp and r.get("bank_fp") and r["bank_fp"] != fp and not r.get("paid_on")
                and r.get("bank_changed") != "yes" and (r.get("received") or "") > args.received):
            r["bank_changed"] = "yes"
            w = (f"BANK DETAILS CHANGED: ••••{r.get('bank_last4', '')} differs from an older invoice "
                 f"(••••{lm.last4(inv['account_number'])}): ring them before paying")
            note(r, w)
            print(f"   ! {r['message_id']}: {w}")
    a = assess_new(inv, args.sender_email, args.sender_name, rows, fps, names)
    rows.append({"message_id": args.message_id, "received": args.received, "singer_name": args.sender_name,
                 "singer_email": args.sender_email.lower(), "invoice_ref": inv["invoice_ref"],
                 "amount_gbp": f"{inv['amount']:.2f}", "bank_fp": a["bank_fp"], "bank_last4": a["bank_last4"],
                 "payee": a["payee"], "bank_changed": a["bank_changed"], "paid_on": "", "paid_amount": "",
                 "paid_ref": "", "notes": "; ".join(inv["warnings"] + a["warnings"])})
    lm.write_csv(STORE, rows, COLUMNS)
    print(f"{first_name(args.sender_name)}: £{inv['amount']:,.2f} (ref {inv['invoice_ref'] or '?'}) · payee {a['payee']}"
          + (f" · bank ••••{a['bank_last4']}" if a["bank_last4"] else ""))
    for w in inv["warnings"] + a["warnings"]:
        print(f"   ! {w}")


def cmd_paid(args, client):
    rows = lm.read_csv(STORE)
    unpaid = [r for r in rows if not r.get("paid_on")]
    for r in unpaid:
        if not received_date(r):
            print(f"skipped {r['message_id']}: received date {r.get('received')!r} is not YYYY-MM-DD")
    unpaid = [r for r in unpaid if received_date(r)]
    if not unpaid:
        print("No unpaid singer invoices.")
        return
    if not client:
        print("No Starling token; paid check skipped.")
        return
    today = datetime.date.today()
    since = min(received_date(r) for r in unpaid) - LOOKBACK
    used = {r["paid_ref"] for r in rows if r.get("paid_ref")}
    legacy = {(r["paid_on"], round(lm.money(r.get("paid_amount")), 2))  # paid before paid_ref was stored
              for r in rows if r.get("paid_on") and not r.get("paid_ref")}
    items = [it for it in client.feed(since, today + datetime.timedelta(days=1), "OUT")
             if item_uid(it) not in used and (lm.local_date(it.get("transactionTime")),
                                              round((it.get("amount") or {}).get("minorUnits", 0) / 100, 2)) not in legacy]
    report = []
    hits = match_paid(unpaid, items, report)
    for line in report:
        print(line)
    for r in rows:
        if r["message_id"] in hits:
            when, amount, uid = hits[r["message_id"]]
            print(f"NEWLY PAID {r['message_id']}: {first_name(r['singer_name'])} £{amount:,.2f} on {when}")
            if args.apply:
                r["paid_on"], r["paid_amount"], r["paid_ref"] = when, f"{amount:.2f}", uid
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
            note(r, f"paid reply drafted {datetime.date.today()}")
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
    s.add_argument("--received", required=True, type=iso_date)
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
    try:
        {"scan": cmd_scan, "paid": cmd_paid, "status": cmd_status, "thanked": cmd_thanked}[args.cmd](args, client)
    except (lm.StarlingError, urllib.error.URLError, TimeoutError, ConnectionError) as e:  # type name only
        print(f"Starling unavailable ({type(e).__name__}); {args.cmd} skipped")


if __name__ == "__main__":
    main()
