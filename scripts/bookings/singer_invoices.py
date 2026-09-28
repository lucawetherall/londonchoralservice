#!/usr/bin/env python3
"""Track invoices from singers and organists (money OUT), READ-ONLY against
Starling. Records live in ~/lcs-private/singer-invoices.csv (mode 600).

    singer_invoices.py scan <saved message> --message-id ID --received YYYY-MM-DD --sender-email E --sender-name 'N'
    singer_invoices.py paid [--apply]      # match OUT payments; prints NEWLY PAID <message id>
    singer_invoices.py status              # unpaid invoices and totals
    singer_invoices.py thanked <message id>  # note that the "Paid!" reply was drafted
    singer_invoices.py confirm <message id>  # the owner rang the singer: trust these bank details

Bank details are stored as a keyed fingerprint (lcs_money.bank_fingerprint) plus
the last four digits, and only "••••1234" is ever printed. This script never
creates payees or payments: a new singer is flagged for the owner to add in the
Starling app, where Confirmation of Payee runs. Details are trusted only once
paid to verifiably, confirmed by phone, or held on a Starling payee. New details,
details that differ from the trusted ones for that singer (same email or same
name), and details that differ between the attachment and the email all raise a
warning to ring before paying. A payment is matched by the bank's own evidence
where it can: a feed item carrying the recipient's sort code and account number
settles only the invoice with the same fingerprint (paid_verified=yes). Only when
one side lacks bank details does the name decide (surname and first name or
initial). A payment settles one invoice once: its feed item id is stored, and a
payment that fits several singers, or predates the invoice, is only reported.
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
COLUMNS = ["message_id", "received", "singer_name", "singer_email", "invoice_ref", "amount_gbp", "bank_fp", "bank_last4",
           "payee", "bank_changed", "bank_confirmed", "paid_on", "paid_amount", "paid_ref", "paid_verified", "notes"]
NEW_PAYEE = "NEW: add as a payee in the Starling app"
NEW_DETAILS = "NEW BANK DETAILS: confirm them by phone on a number you already hold before adding the payee"
NOT_YET_VERIFIED = "BANK DETAILS NOT YET VERIFIED (seen on an earlier invoice): confirm by phone"
LOOKBACK = datetime.timedelta(days=14)  # a payment up to 14 days before an invoice arrived is reported, not applied
INVOICING_DOMAINS = ("intuit.com", "quickbooks.com", "xero.com", "freeagent.com", "zohoinvoice.com", "zoho.com",
                     "sumup.com", "paypal.com", "stripe.com", "invoice2go.com", "wave.com", "waveapps.com")
TRADE_WORDS = {"music", "singer", "soprano", "alto", "tenor", "bass", "baritone", "mezzo", "organist", "ltd", "limited"}
HONORIFICS = {"dr", "mr", "mrs", "ms", "miss", "mx", "prof", "rev", "revd"}
WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")  # a hyphenated name is one word: "smith-jones"
DIFFER = "BANK DETAILS DIFFER between the attachment and the email: ring them before paying"

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
ACCOUNT = re.compile(r"(?<![a-z])(?:account|acct|acc|a/c)(?![a-z])\.?(?:\s*(?:no|number|num|#)\.?)?\W{0,5}"
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
    if re.fullmatch(r"\d{8}", ref) or (digits and (digits in (sort_code, account)
                                                  or any(n and n in digits for n in (sort_code, account)))):
        return ""
    return ref


def extract(text):
    text = re.sub(r"[^\S\n]", " ", text)  # non-breaking and other odd spaces
    ref = REF.search(text)
    sort, acc = extract_bank(text)
    return {"amount": round(extract_amount(text), 2), "invoice_ref": clean_ref(ref.group(1) if ref else "", sort, acc),
            "sort_code": sort, "account_number": acc}


def words(text):
    """Lower-case name words, leading honorifics dropped; 'SMITH-JONES' stays one word."""
    w = WORD.findall((text or "").lower())
    while len(w) > 1 and w[0] in HONORIFICS:
        w.pop(0)
    return w


def normalise_name(name):
    """'Fenwick, Ben (tenor)' / 'Dr Ben Fenwick Music via QuickBooks' / 'Ben Fenwick, BA Hons' -> 'ben fenwick'."""
    n = re.sub(r"\s+via\s.*$", "", (name or "").lower())
    n = re.sub(r"\([^)]*\)", " ", n)
    head, comma, tail = n.partition(",")
    w, t = words(head), words(tail)
    if comma and len(w) == 1 and len(t) == 1 and t[0] not in TRADE_WORDS:  # "Fenwick, Ben"
        w = t + w
    while len(w) > 2 and w[-1] in TRADE_WORDS:  # "Sarah Singer" keeps her surname
        w.pop()
    return " ".join(w)


def surname(name):
    parts = normalise_name(name).split()
    return parts[-1] if parts else ""


def names_agree(name, who):
    """The counterparty `who` names this person: surname as a whole word, and first name or its initial
    as 'F SURNAME…' or 'SURNAME F…'. A name of fewer than two words never agrees."""
    parts, w = normalise_name(name).split(), words(who)
    if len(parts) < 2 or len(parts[-1]) < 2 or parts[-1] not in w:
        return False
    first, last = parts[0], parts[-1]
    fits = lambda t: t in (first, first[0])  # noqa: E731
    return (w[0] != last and fits(w[0])) or (len(w) > 1 and w[0] == last and fits(w[1]))


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


def is_trusted(r):
    """Details paid to verifiably (the bank's own record matched) or confirmed by phone. A paid mark alone isn't."""
    return bool(r.get("bank_fp")) and (r.get("paid_verified") == "yes" or r.get("bank_confirmed") == "yes")


def same_last4_note(old, new):
    """Extra clause for a CHANGED warning when the old and new last four digits happen to be equal."""
    return " (same last four digits, different sort code or account)" if old and new and old == new else ""


def assess_new(inv, sender_email, sender_name, history, payee_fps, payee_names, payee_last4=None, message_id=""):
    """Payee status and warnings for a new invoice. history = all stored rows; payee_fps None = no Starling token;
    payee_last4 = {payee name: last four digits}; message_id, when given, is named in the NEW/NOT-YET-VERIFIED
    warning as the invoice to run `singer_invoices.py confirm` against once the singer is rung."""
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    now = lm.last4(inv["account_number"])
    by_date = lambda rows: sorted(rows, key=lambda r: r.get("received") or "")  # noqa: E731
    known = by_date(r for r in singer_history(history, sender_email, sender_name) if r.get("bank_fp"))
    trusted_rows = [r for r in known if is_trusted(r)]
    trusted = {r["bank_fp"] for r in trusted_rows} | set(payee_fps or {})
    named = [n for n in (payee_names if payee_fps is not None else []) if names_agree(sender_name, n)]
    warnings, changed = [], False
    if fp and fp not in trusted:
        # compare with the trusted details, else with any earlier details on record (unconfirmed, but still theirs)
        before = trusted_rows or [r for r in known if r["bank_fp"] != fp]
        if before:
            changed = True
            old4 = before[-1].get("bank_last4", "")
            warnings.append(f"BANK DETAILS CHANGED since their last invoice (was ••••{old4}, "
                            f"now ••••{now}): ring them before paying{same_last4_note(old4, now)}")
        elif named:
            changed = True
            was = (payee_last4 or {}).get(named[0], "")
            warnings.append(f"BANK DETAILS CHANGED: Starling payee '{named[0]}' has different bank details "
                            f"(was ••••{was or '?'}, now ••••{now}): ring them before paying{same_last4_note(was, now)}")
        confirm_hint = f", then run singer_invoices.py confirm {message_id}" if message_id else ""
        if fp in {r["bank_fp"] for r in known}:  # seen on an earlier invoice from this singer, just never trusted
            warnings.append(f"{NOT_YET_VERIFIED}{confirm_hint}")
        else:
            warnings.append(NEW_DETAILS + confirm_hint)
    if payee_fps is None:
        payee = "unknown (no Starling token)"
    elif fp and fp in payee_fps:
        payee = f"existing: {payee_fps[fp]}"
    elif named and fp:
        payee = f"name matches payee {named[0]} but with different bank details"
    elif named:
        payee = f"probably existing: {named[0]} (no bank details on the invoice)"
    else:
        payee = NEW_PAYEE
    if not fp:
        warnings.append("no bank details found on the invoice")
        if known:
            last = (trusted_rows or known)[-1]
            warnings.append(f"no bank details on the invoice: compare them with ••••{last.get('bank_last4', '')} before paying")
    return {"bank_fp": fp or "", "bank_last4": now if fp else "",
            "payee": payee, "bank_changed": "yes" if changed else "no", "warnings": warnings}


def payer_names(r):
    """Names a payment to this invoice's singer may carry: theirs, and the Starling payee's matched by fingerprint."""
    names = [r.get("singer_name") or ""]
    if (r.get("payee") or "").startswith("existing: "):
        names.append(r["payee"][len("existing: "):])
    return names


def match_paid(unpaid, out_items, report=None, history=None, payee_fps=None):
    """{message_id: (date, amount, feed item uid, verified)} for OUT payments that settle an unpaid invoice.

    Invoices oldest first, payments oldest first, each payment settles at most one invoice. When both the
    invoice and the payment carry bank details, only equal fingerprints (and amounts) match, and the match
    is verified; a payment to different bank details that would otherwise fit by name is never matched,
    only reported once per feed item as PAID TO DIFFERENT BANK DETAILS. When only the payment carries bank
    details, the amount and the name decide (names_agree), unless the singer's name is a single word or the
    payment's own fingerprint is already known to belong to someone else — trusted (verified or confirmed)
    in a different singer's history, or a Starling payee whose name disagrees with this invoice (`history`
    and `payee_fps` supply that knowledge; a caller that omits them keeps the old name-only behaviour). A
    payment that fits invoices from different singers, or predates the invoice, and a feed item without an
    id, are only added to `report`."""
    report = [] if report is None else report
    history = unpaid if history is None else history
    trusted_names_by_fp = {}
    for r2 in history:
        if is_trusted(r2):
            trusted_names_by_fp.setdefault(r2["bank_fp"], set()).add(normalise_name(r2.get("singer_name")))

    def fp_belongs_to_someone_else(r, ifp):
        others = trusted_names_by_fp.get(ifp, set()) - {normalise_name(r.get("singer_name"))}
        if others:
            return True
        payee_name = (payee_fps or {}).get(ifp)
        return bool(payee_name) and not names_agree(r.get("singer_name"), payee_name)

    open_ = sorted((r for r in unpaid if received_date(r)), key=lambda r: r["received"])
    hits, no_id, too_short = {}, 0, []
    for it in sorted(out_items, key=lambda i: i.get("transactionTime") or ""):
        if not it.get("feedItemUid"):
            no_id += 1
            continue
        paid = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = lm.local_date(it.get("transactionTime"))
        who, ifp = it.get("counterPartyName") or "", lm.feed_item_fingerprint(it)
        fits, verified, wrong_bank = [], [], []
        for r in open_:
            if (r["message_id"] in hits or abs(paid - lm.money(r["amount_gbp"])) >= 0.01
                    or when < (received_date(r) - LOOKBACK).isoformat()):
                continue
            if ifp and r.get("bank_fp"):
                if ifp == r["bank_fp"]:
                    verified.append(r)
                elif any(names_agree(n, who) for n in payer_names(r)):
                    wrong_bank.append(r)
            elif len(normalise_name(r.get("singer_name")).split()) < 2:
                if r["message_id"] not in too_short:
                    too_short.append(r["message_id"])
            elif ifp and fp_belongs_to_someone_else(r, ifp):
                pass  # this payment's own fingerprint is already someone else's: a name match alone won't do
            elif any(names_agree(n, who) for n in payer_names(r)):
                fits.append(r)
        pool = verified or fits
        on_time = [r for r in pool if when >= r["received"][:10]]
        pool = on_time or pool
        if not pool:
            if wrong_bank:
                wr = wrong_bank[0]
                item_last4 = lm.last4(it.get("counterPartySubEntitySubIdentifier"))
                report.append(f"PAID TO DIFFERENT BANK DETAILS £{paid:,.2f} on {when} to ••••{item_last4} fits "
                              f"{wr['message_id']} ({first_name(wr.get('singer_name'))}, "
                              f"invoice ••••{wr.get('bank_last4', '')}): check by hand")
            continue
        if len({normalise_name(r.get("singer_name")) or r["message_id"] for r in pool}) > 1:
            names = ", ".join(f"{r['message_id']} ({first_name(r.get('singer_name'))})" for r in pool)
            report.append(f"AMBIGUOUS £{paid:,.2f} on {when} fits {names}: check by hand")
        elif on_time:
            hits[pool[0]["message_id"]] = (when, paid, it["feedItemUid"], bool(verified))
        else:
            report.append(f"POSSIBLY ALREADY PAID {pool[0]['message_id']}: {first_name(pool[0]['singer_name'])} "
                          f"£{paid:,.2f} on {when} (before the invoice arrived): check by hand")
    if no_id:
        report.append(f"feed item without id skipped{f' ({no_id})' if no_id > 1 else ''}: check by hand")
    report += [f"NAME TOO SHORT {m}: check by hand" for m in too_short if m not in hits]
    return hits


def summary(rows, today):
    unpaid = [r for r in rows if not r.get("paid_on")]
    ages = [(today - d).days for d in map(received_date, unpaid) if d]
    return {"unpaid": len(unpaid), "unpaid_total": round(sum(lm.money(r["amount_gbp"]) for r in unpaid), 2),
            "oldest_days": max(ages, default=0), "bank_changed": sum(1 for r in unpaid if ring_first(r))}


def ring_first(r):
    return r.get("bank_changed") == "yes" and r.get("bank_confirmed") != "yes"


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


def mentions_bank(text):
    """Does the text give bank details of any kind (even ones extract_bank can't settle on)?"""
    text = re.sub(r"[^\S\n]", " ", text)
    return bool(SORT.search(text) or TABLE.search(text) or any(_iban_ok(re.sub(r"\s", "", m.group(0)).upper())
                                                            for m in IBAN.finditer(text))
                or any(not NOT_OURS.search(text[max(0, m.start() - 12):m.start()]) for m in ACCOUNT.finditer(text)))


def read_invoice(path):
    """Amount, ref and bank details from every PDF and the body. Bank details come from the first PDF that
    has both numbers (else the first source that does); when sources give different details, or one gives
    unclear details while another is clear, `sources_disagree` is set and DIFFER is warned."""
    found = {"amount": 0.0, "invoice_ref": "", "sort_code": "", "account_number": "", "warnings": [],
             "sources_disagree": False}
    details, unclear = [], False  # details: (is a pdf, sort code, account number)
    for label, text in message_texts(path):
        if label != "email body" and not text.strip():
            found["warnings"].append(f"could not read {label} (encrypted or damaged): check it by hand")
        e = extract(text)
        if not found["amount"] and e["amount"]:
            found["amount"] = e["amount"]
        if not found["invoice_ref"] and e["invoice_ref"]:
            found["invoice_ref"] = e["invoice_ref"]
        if e["sort_code"] and e["account_number"]:
            details.append((label != "email body", e["sort_code"], e["account_number"]))
        elif mentions_bank(text):
            unclear = True
    if details:
        _, sort, acc = next((d for d in details if d[0]), details[0])
        found.update(sort_code=sort, account_number=acc)
        if unclear or len({lm.bank_fingerprint(s, a) for _, s, a in details}) > 1:
            found["sources_disagree"] = True
            found["warnings"].append(DIFFER)
    for _, s, a in details:
        found["invoice_ref"] = clean_ref(found["invoice_ref"], s, a)
    if not found["amount"]:
        found["warnings"].append("amount not found: check the invoice by hand")
    return found


def first_name(name):
    parts = normalise_name(name).split() or (name or "").split()
    return parts[0].title() if parts else "?"


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
    payee_last4 = {}  # payee name -> last four digits of its first UK account
    for p in payees or []:
        uk = [a for a in p.get("accounts", []) if lm.bank_fingerprint(a.get("bankIdentifier"), a.get("accountIdentifier"))]
        if uk:
            payee_last4.setdefault(p.get("payeeName", ""), lm.last4(uk[0].get("accountIdentifier")))
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    for r in singer_history(rows, args.sender_email, args.sender_name):  # scanned out of order: flag the newer one
        if (fp and r.get("bank_fp") and r["bank_fp"] != fp and not r.get("paid_on")
                and r.get("bank_changed") != "yes" and (r.get("received") or "") > args.received):
            r["bank_changed"] = "yes"
            new4 = lm.last4(inv["account_number"])
            w = (f"BANK DETAILS CHANGED: ••••{r.get('bank_last4', '')} differs from an older invoice "
                 f"(••••{new4}): ring them before paying{same_last4_note(r.get('bank_last4', ''), new4)}")
            note(r, w)
            print(f"   ! {r['message_id']}: {w}")
    a = assess_new(inv, args.sender_email, args.sender_name, rows, fps, names, payee_last4, args.message_id)
    changed = "yes" if a["bank_changed"] == "yes" or inv.get("sources_disagree") else "no"
    rows.append({"message_id": args.message_id, "received": args.received, "singer_name": args.sender_name,
                 "singer_email": args.sender_email.lower(), "invoice_ref": inv["invoice_ref"],
                 "amount_gbp": f"{inv['amount']:.2f}", "bank_fp": a["bank_fp"], "bank_last4": a["bank_last4"],
                 "payee": a["payee"], "bank_changed": changed, "bank_confirmed": "", "paid_on": "", "paid_amount": "",
                 "paid_ref": "", "paid_verified": "", "notes": "; ".join(inv["warnings"] + a["warnings"])})
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
    legacy = {(r["paid_on"], round(lm.money(r.get("paid_amount")), 2), surname(r.get("singer_name")))
              for r in rows if r.get("paid_on") and not r.get("paid_ref")}  # paid before paid_ref was stored

    def settled_before(it):
        key = (lm.local_date(it.get("transactionTime")), round((it.get("amount") or {}).get("minorUnits", 0) / 100, 2))
        return any(key == (d, a) and s and s in words(it.get("counterPartyName")) for d, a, s in legacy)

    items = [it for it in client.feed(since, today + datetime.timedelta(days=1), "OUT")
             if not (it.get("feedItemUid") and it["feedItemUid"] in used) and not settled_before(it)]
    payee_fps = lm.payee_fingerprints(client.payees())  # so a payment's own fp can be recognised as someone else's
    report = []
    hits = match_paid(unpaid, items, report, history=rows, payee_fps=payee_fps)
    for line in report:
        print(line)
    for r in rows:
        if r["message_id"] in hits:
            when, amount, uid, verified = hits[r["message_id"]]
            print(f"NEWLY PAID {r['message_id']}: {first_name(r['singer_name'])} £{amount:,.2f} on {when}"
                  + (" (bank details match)" if verified else " (matched by name)"))
            if args.apply:
                r["paid_on"], r["paid_amount"], r["paid_ref"] = when, f"{amount:.2f}", uid
                r["paid_verified"] = "yes" if verified else "no"
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
                  + (" · BANK DETAILS CHANGED: ring before paying" if ring_first(r)
                     else " · changed bank details confirmed by phone" if r["bank_changed"] == "yes" else ""))
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


def cmd_confirm(args, client=None):
    """The owner rang the singer on a number already held: trust this invoice's bank details."""
    rows = lm.read_csv(STORE)
    for r in rows:
        if r["message_id"] == args.message_id:
            if not r.get("bank_fp"):
                raise SystemExit(f"{args.message_id}: no bank details recorded, nothing to confirm")
            r["bank_confirmed"] = "yes"
            note(r, f"bank details confirmed by phone {datetime.date.today()}")
            lm.write_csv(STORE, rows, COLUMNS)
            print(f"{args.message_id}: bank details confirmed")
            print(f"   trusted from now on: the account ending ••••{r.get('bank_last4', '')}")
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
    c = sub.add_parser("confirm")
    c.add_argument("message_id")
    args = ap.parse_args()
    tok = lm.keychain_token() if args.cmd in ("scan", "paid") else None
    client = lm.StarlingReadOnly(tok) if tok else None
    try:
        {"scan": cmd_scan, "paid": cmd_paid, "status": cmd_status, "thanked": cmd_thanked,
         "confirm": cmd_confirm}[args.cmd](args, client)
    except (lm.StarlingError, urllib.error.URLError, TimeoutError, ConnectionError) as e:  # type name only
        print(f"Starling unavailable ({type(e).__name__}); {args.cmd} skipped")


if __name__ == "__main__":
    main()
