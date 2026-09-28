#!/usr/bin/env python3
"""Track invoices from singers and organists (money OUT), READ-ONLY against
Starling. Records live in ~/lcs-private/singer-invoices.csv (mode 600).

    singer_invoices.py scan --fetch --message-id ID --received YYYY-MM-DD --sender-email E --sender-name 'N'
    singer_invoices.py scan <saved message> --message-id ID …   # the same, from a saved getOriginalMessage result
    singer_invoices.py rescan <message id> [--fetch | <saved message>]  # re-read an UNPAID invoice

scan and rescan end with two lines for the Books bill: "bill: yes" or "bill: no (<reason>)" (bank warning,
amount not found or zero amount) and "bill_number: <x>" (the singer's ref, or SI- plus the last 5 digits of
the message id when the ref has a digit run over 5 digits). On a message already recorded, scan prints
"already recorded: <id>", then the stored line, its warnings and the bill lines, so a crashed run can resume.
They also print "linked: <booking ref>" or "link: none": an invoice is linked to a ledger booking automatically
when its text mentions a date (with or without the year) and exactly one ledger booking has that event date; a
rescan keeps a link already made.
    singer_invoices.py link <message id> <booking ref>  # link it by hand (the ref must be in the ledger): a label
        for the per-event margin, never money
    singer_invoices.py margins             # per booking: client fee, linked singer costs, margin and margin %
    singer_invoices.py paid [--apply]      # match OUT payments; prints NEWLY PAID <message id>
    singer_invoices.py status              # unpaid invoices and totals
    singer_invoices.py thanked <message id>  # note that the "Paid!" reply was drafted
    singer_invoices.py confirm <message id>  # the owner rang the singer: trust these bank details
    singer_invoices.py confirm <message id> --expect-fp <bank_fp, all 16 hex>  # the Command Centre's form:
        refused unless the recorded details are still the ones the owner approved
    singer_invoices.py settled <message id> YYYY-MM-DD  # the owner paid it outside the feed's reach: mark it paid
    singer_invoices.py pdf <message id> [--fetch | <saved message>]  # save the invoice PDF for the Books bill
        (scan saves it too and ends with "pdf: <path>" or "pdf: none")
    singer_invoices.py withdrawn <message id> <reason word>  # sent to us by mistake (another organisation's
        booking): out of unpaid, status, summary, paid matching, the dashboard, the money line and bills

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
one side lacks bank details does the name decide (name_match: surname, allowing
double-barrelled and run-together forms, and first name, initial or common
nickname; an exact surname beats a looser one), and never when the payment's
own details are trusted for another singer or held on a Starling payee under
another name (reported as PAYMENT TO ANOTHER SINGER'S ACCOUNT). A payment settles one invoice once: its feed item id is stored, and
a payment that fits several singers, or predates the invoice, is only reported. A
name-only match prints "(matched by name, check before thanking)": the assistant
drafts "Paid!" only for a match on the bank details. `settled` is the owner's own
command; it marks the invoice paid (paid_verified=no) and never trusts its details.

Invoices are read from PDF and .docx attachments and the email body (.doc files
are flagged to check by hand). With --fetch the script fetches the raw email
itself, read-only, through lcs_mcp (ZohoMail_getOriginalMessage only).
"""

import argparse
import datetime
import email
import hmac
import html
import io
import os
import re
import sys
import urllib.error
import xml.etree.ElementTree as ET
import zipfile
import zlib
from email import policy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_mcp  # noqa: E402
import lcs_money as lm  # noqa: E402

STORE = lm.PRIVATE / "singer-invoices.csv"
PDF_DIR = lm.PRIVATE / "singer-invoices"  # <message id>.pdf, mode 600: attached to the Books bill
MAX_PDF_BYTES = 10 * 1024 * 1024
COLUMNS = ["message_id", "received", "singer_name", "singer_email", "invoice_ref", "amount_gbp", "bank_fp", "bank_last4",
           "payee", "bank_changed", "bank_confirmed", "paid_on", "paid_amount", "paid_ref", "paid_verified", "notes",
           "withdrawn", "booking_ref"]  # withdrawn: the date `withdrawn` was run; booking_ref: the ledger booking
# this invoice is for (a label for the per-event margin, never money). Both last, so an older store just gains them.
REASON_RE = re.compile(r"^[a-z][a-z-]{0,19}$")  # one lower-case word, such as not-ours
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
TOKEN = r"([A-Z]{0,5}[-/]?\d[\w\-/.]{0,15})"
REF_TIERS = [  # (pattern, how it's labelled); the first acceptable token of the best tier wins
    # "Invoice No: 018", "Invoice Number 1020", "Invoice #37", "Inv ref: LW-042" (value may sit on the next line)
    (re.compile(r"(?<![a-z])inv(?:oice)?\.?[ \t]*(?:(?:no|number|num|ref|reference)(?![a-z])\.?|#)"
                r"[ \t]*[:#.\-]?[ \t]*\n?[ \t]*" + TOKEN, re.I), "explicit"),
    (re.compile(r"(?<![a-z0-9])(INV[-/#]?\d[\w\-/]{0,15})", re.I), "labelled"),  # "INV-0107"
    (re.compile(r"(?<![a-z])invoice[ \t]*[:#\-]?[ \t]*" + TOKEN, re.I), "labelled"),  # "Invoice 1020" on one line
    (re.compile(r"(?<![a-z])invoice\s*[:#\-]?\s*" + TOKEN, re.I), "loose"),  # "INVOICE" then a number further down
]
# "TOTAL<tab><tab>100": a bare figure (six digits at most) ending a total line, taken only when the invoice names
# GBP or £ somewhere, and only when it has no £ figures at all or equals one of them or their sum
BARE_TOTAL = re.compile(r"^[ \t]*(?:grand[ \t]+)?total(?:[ \t]+(?:due|payable))?[ \t]*[:=]?[ \t]*[ \t]"
                        r"(\d{1,3}(?:,\d{3})?|\d{1,6})(?:\.\d{2})?[ \t]*$", re.I | re.M)
CURRENCY = re.compile(r"£|\bGBP\b")
ORDINAL = re.compile(r"\d{1,2}(?:st|nd|rd|th)(?![a-z])", re.I)
DATE_LIKE = re.compile(r"\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?|\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2}")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCX_MAX_PART = 5 << 20  # bytes of one XML part, uncompressed; a bigger part is skipped
DOCX_MAX_TOTAL = 15 << 20  # bytes read from one .docx in all, uncompressed
DOCX_MAX_EXTRA_PARTS = 10  # header and footer parts read
DOCX_MAX_TEXT = 1 << 20  # characters of text kept
DOCX_MAX_DEPTH = 200  # nesting of blocks (content controls, tables in tables …)
UNREADABLE = "too large or malformed"
SORT = re.compile(r"(?<![a-z])(?:sort[\s\-]*code|s/c)\W{0,5}(\d{2})\W?(\d{2})\W?(\d{2})(?!\d)", re.I)
ACCOUNT = re.compile(r"(?<![a-z])(?:account|acct|acc|a/c)(?![a-z])\.?(?:\s*(?:no|number|num|#)\.?)?\W{0,5}"
                     r"(\d{7,8}|\d{4} \d{3,4})(?![ ]?\d)", re.I)
TABLE = re.compile(r"(?<![a-z])sort[\s\-]*code\b[^\n]*\n[ \t]*(\d{2})[-. ]?(\d{2})[-. ]?(\d{2})[ \t]+(\d{7,8})(?!\d)", re.I)
IBAN = re.compile(r"\bGB\d{2} ?[A-Z]{4}(?: ?\d){14}(?!\d)")
NOT_OURS = re.compile(r"\b(?:customer|client|your|reference)\b", re.I)  # a label like "Customer account no."
NICKNAMES = {"ben": {"benjamin", "benedict"}, "jess": {"jessica", "jessie"}, "tom": {"thomas"}, "will": {"william"},
             "kate": {"katherine", "catherine"}, "liz": {"elizabeth"}, "alex": {"alexander", "alexandra"},
             "sam": {"samuel", "samantha"}, "joe": {"joseph"}, "dan": {"daniel"}, "rob": {"robert"},
             "nick": {"nicholas"}, "chris": {"christopher", "christine"}}


def _iban_ok(iban):
    s = iban[4:] + iban[:4]
    return int("".join(str(int(c, 36)) for c in s)) % 97 == 1


def extract_amount(text):
    for label in LABELS:
        m = label.search(text)
        if m:
            return lm.money(m.group(1) or m.group(2))
    pounds = [lm.money(x) for x in POUNDS.findall(text)]
    for m in (BARE_TOTAL.finditer(text) if CURRENCY.search(text) else ()):
        bare = lm.money(m.group(1))  # "Total 3" (hours), "Total due 30" (days), "Total 2026": never a £ figure
        if not pounds or any(abs(bare - p) < 0.005 for p in pounds + [sum(pounds)]):
            return bare
    return max(pounds, default=0.0)


def bank_candidates(text):
    """([(sort code, line)], [(account number, line)]) for every sort code and account number in the text."""
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
    return sorts, accs


def extract_bank(text):
    """(sort code, account number), or blanks when absent or ambiguous."""
    sorts, accs = bank_candidates(text)
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


def acceptable_ref(token, label):
    """The token as a ref, or "" for a date or an ordinal ("27th", "21/09", "2026-09-21", "21.9.26"), for anything
    under three characters unless explicitly labelled ("Invoice #37" yes, "Invoice 12" no), and for a short plain
    number with no label at all (a loose "122")."""
    tok = token.rstrip(".-/")
    if not tok or ORDINAL.match(tok) or DATE_LIKE.fullmatch(tok):
        return ""
    if len(tok) < 3 and label != "explicit":
        return ""
    if label == "loose" and not re.search(r"[A-Za-z]", tok) and len(re.sub(r"\D", "", tok)) < 5:
        return ""
    return tok


def extract_ref(text):
    for pattern, label in REF_TIERS:
        for m in pattern.finditer(text):
            tok = acceptable_ref(m.group(1), label)
            if tok:
                return tok
    return ""


def clean_ref(ref, sort_code, account):
    digits = re.sub(r"\D", "", ref)
    if re.fullmatch(r"\d{8}", ref) or (digits and (digits in (sort_code, account)
                                                  or any(n and n in digits for n in (sort_code, account)))):
        return ""
    return ref


def extract(text):
    text = re.sub(r"[^\S\n]", " ", text)  # non-breaking and other odd spaces
    sort, acc = extract_bank(text)
    ref = clean_ref(extract_ref(text), sort, acc)
    sorts, accs = bank_candidates(text)  # even when too ambiguous to keep, a bank number is never the ref
    for n in {x for x, _ in sorts} | {x for x, _ in accs}:
        ref = clean_ref(ref, n, "")
    return {"amount": round(extract_amount(text), 2), "invoice_ref": ref, "sort_code": sort, "account_number": acc}


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


def compact(word):
    return re.sub(r"[\s\-'’]", "", word)


def first_names_agree(a, b):
    """Equal; an initial; a prefix of 3+ letters (ben/benjamin, jess/jessie); or a NICKNAMES pair."""
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if len(short) == 1 or len(short) >= 3:
        if long_.startswith(short):
            return True
    return b in NICKNAMES.get(a, ()) or a in NICKNAMES.get(b, ())


def _surname_level(x, y):
    """x, y: name words, first name first. 2: the surnames are equal once spaces, hyphens and apostrophes go;
    1: a hyphenated part (4+ letters) of one is the other's surname ("harrow-fenwick" / "fenwick"), or one's
    last two words run together are the other's surname ("fairleigh brook" / "fairleighbrook"); 0: neither."""
    sx, sy = compact(x[-1]), compact(y[-1])
    if len(sx) < 2 or len(sy) < 2:
        return 0
    if sx == sy:
        return 2
    for a, b in ((x, y), (y, x)):
        if any(len(p) >= 4 and p == compact(b[-1]) for p in a[-1].split("-")):
            return 1
        if len(a) >= 3 and compact(a[-2] + a[-1]) == compact(b[-1]):
            return 1
    return 0


def name_match(a, b):
    """How well two names agree: 2 (same surname), 1 (surnames agree loosely: see _surname_level), 0 (not the
    same person). The first names must agree too (first_names_agree). Either name (never both at once) may
    be written 'SURNAME F…', as bank feeds do. A name of fewer than two words never agrees.

    Decided: "Anna Smith" and "Anna Smith-Jones" agree (level 1), as a surname gains or loses a part on
    marriage; where both are open, the exact name (level 2) wins and a tie stays ambiguous."""
    wa, wb = normalise_name(a).split(), normalise_name(b).split()
    if len(wa) < 2 or len(wb) < 2:
        return 0
    best = 0
    for x, y in ((wa, wb), ([wa[1], wa[0]], wb), (wa, [wb[1], wb[0]])):
        if first_names_agree(x[0], y[0]):
            best = max(best, _surname_level(x, y))
    return best


def names_equivalent(a, b):
    return name_match(a, b) > 0


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


def payees_named(sender_name, payee_names, history):
    """(payee names that name this singer, ambiguous?). Only the best-agreeing names count (name_match); it is
    ambiguous when two different payees fit equally well, or when the payee's name fits another singer with
    an unpaid invoice (whose name doesn't fit this one) as well as it fits this singer."""
    levels = {n: name_match(sender_name, n) for n in dict.fromkeys(payee_names)}
    top = max(levels.values(), default=0)
    named = [n for n, lvl in levels.items() if top and lvl == top]
    others = {r.get("singer_name") for r in history if is_open(r) and r.get("singer_name")
              and not names_equivalent(r["singer_name"], sender_name)}
    ambiguous = len(named) > 1 or any(name_match(o, n) >= top for n in named for o in others)
    return named, ambiguous


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
    named, ambiguous = payees_named(sender_name, payee_names if payee_fps is not None else [], history)
    warnings, changed = [], False
    if fp and fp not in trusted:
        # compare with the trusted details, else with any earlier details on record (unconfirmed, but still theirs)
        before = trusted_rows or [r for r in known if r["bank_fp"] != fp]
        if before:
            changed = True
            old4 = before[-1].get("bank_last4", "")
            warnings.append(f"BANK DETAILS CHANGED since their last invoice (was ••••{old4}, "
                            f"now ••••{now}): ring them before paying{same_last4_note(old4, now)}")
        elif named and not ambiguous:
            changed = True
            was = (payee_last4 or {}).get(named[0], "")
            warnings.append(f"BANK DETAILS CHANGED: Starling payee '{first_name(named[0])}' has different bank details "
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
    elif ambiguous:
        payee = f"ambiguous: {', '.join(named)} (the name fits more than one payee or singer): check by hand"
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
    details, the amount and the name decide (name_match: the best-agreeing singers only), unless the singer's name is a single word or the
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
        if any(not names_equivalent(n, r.get("singer_name")) for n in trusted_names_by_fp.get(ifp, set())):
            return True
        payee_name = (payee_fps or {}).get(ifp)
        return bool(payee_name) and not names_equivalent(r.get("singer_name"), payee_name)

    def level(r, who):
        return max(name_match(n, who) for n in payer_names(r))

    open_ = sorted((r for r in unpaid if received_date(r)), key=lambda r: r["received"])
    hits, no_id, too_short = {}, 0, []
    for it in sorted(out_items, key=lambda i: i.get("transactionTime") or ""):
        if not it.get("feedItemUid"):
            no_id += 1
            continue
        paid = (it.get("amount") or {}).get("minorUnits", 0) / 100
        when = lm.local_date(it.get("transactionTime"))
        who, ifp = it.get("counterPartyName") or "", lm.feed_item_fingerprint(it)
        fits, verified, wrong_bank, blocked = [], [], [], []
        for r in open_:
            if (r["message_id"] in hits or abs(paid - lm.money(r["amount_gbp"])) >= 0.01
                    or when < (received_date(r) - LOOKBACK).isoformat()):
                continue
            if ifp and r.get("bank_fp"):
                if ifp == r["bank_fp"]:
                    verified.append(r)
                elif level(r, who):
                    wrong_bank.append(r)
            elif len(normalise_name(r.get("singer_name")).split()) < 2:
                if r["message_id"] not in too_short:
                    too_short.append(r["message_id"])
            elif ifp and fp_belongs_to_someone_else(r, ifp):
                # this payment's own fingerprint is already someone else's: a name match alone won't do
                if level(r, who):
                    blocked.append(r)
            elif level(r, who):
                fits.append((level(r, who), r))
        top = max((lvl for lvl, _ in fits), default=0)
        pool = verified or [r for lvl, r in fits if lvl == top]  # an exact name beats a looser one
        on_time = [r for r in pool if when >= r["received"][:10]]
        pool = on_time or pool
        if not pool:
            if wrong_bank:
                wr = wrong_bank[0]
                item_last4 = lm.last4(it.get("counterPartySubEntitySubIdentifier"))
                report.append(f"PAID TO DIFFERENT BANK DETAILS £{paid:,.2f} on {when} to ••••{item_last4} fits "
                              f"{wr['message_id']} ({first_name(wr.get('singer_name'))}, "
                              f"invoice ••••{wr.get('bank_last4', '')}): check by hand")
            if blocked:
                br = blocked[0]
                item_last4 = lm.last4(it.get("counterPartySubEntitySubIdentifier"))
                report.append(f"PAYMENT TO ANOTHER SINGER'S ACCOUNT £{paid:,.2f} on {when} ••••{item_last4} not matched to "
                              f"{br['message_id']} ({first_name(br.get('singer_name'))}): check by hand")
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


def is_withdrawn(r):
    return bool((r.get("withdrawn") or "").strip())


def is_open(r):
    """Unpaid and not withdrawn: the invoices that are still ours to pay."""
    return not r.get("paid_on") and not is_withdrawn(r)


def summary(rows, today):
    unpaid = [r for r in rows if is_open(r)]
    ages = [(today - d).days for d in map(received_date, unpaid) if d]
    return {"unpaid": len(unpaid), "unpaid_total": round(sum(lm.money(r["amount_gbp"]) for r in unpaid), 2),
            "oldest_days": max(ages, default=0), "bank_changed": sum(1 for r in unpaid if ring_first(r))}


def ring_first(r):
    return r.get("bank_changed") == "yes" and r.get("bank_confirmed") != "yes"


def _docx_runs(el):
    """Text of a paragraph: w:t runs, w:tab as a tab, w:br/w:cr as a line break."""
    bits = []
    for node in el.iter():
        if node.tag == W + "t":
            bits.append(node.text or "")
        elif node.tag == W + "tab":
            bits.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            bits.append("\n")
    return "".join(bits)


class _TooDeep(Exception):
    pass


def _docx_block(el, depth=0):
    """Paragraphs on their own lines; a table row on one line, its cells separated by tabs (a cell's own
    paragraphs joined by spaces), so "Total | £150.00" reads "Total\t£150.00". Nesting past DOCX_MAX_DEPTH
    raises _TooDeep."""
    if depth > DOCX_MAX_DEPTH:
        raise _TooDeep
    lines = []
    for child in el:
        if child.tag == W + "p":
            lines.append(_docx_runs(child))
        elif child.tag == W + "tbl":
            for tr in child.findall(W + "tr"):
                cells = [re.sub(r"[ \t]*\n[ \t]*", " ", _docx_block(tc, depth + 1)).strip()
                         for tc in tr.findall(W + "tc")]
                lines.append("\t".join(cells))
        else:  # body, content controls, custom XML, headers …
            inner = _docx_block(child, depth + 1)
            if inner:
                lines.append(inner)
    return "\n".join(lines)


def _part_order(name):
    m = re.fullmatch(r"word/(header|footer)(\d*)\.xml", name)
    return (m.group(1), int(m.group(2) or 0))


def docx_read(data):
    """(text, too_large) for a .docx, with the standard library only: word/document.xml, then up to
    DOCX_MAX_EXTRA_PARTS headers and footers. A part over DOCX_MAX_PART, or past DOCX_MAX_TOTAL read in all,
    or nested past DOCX_MAX_DEPTH, is skipped, and the text is cut at DOCX_MAX_TEXT: each sets too_large.
    ("", False) when the file isn't a readable .docx (damaged, or encrypted, which makes it an OLE file)."""
    problem, texts = False, []
    try:
        with zipfile.ZipFile(io.BytesIO(data or b"")) as z:
            infos = {i.filename: i for i in z.infolist()}
            extra = sorted((n for n in infos if re.fullmatch(r"word/(?:header|footer)\d*\.xml", n)), key=_part_order)
            problem = len(extra) > DOCX_MAX_EXTRA_PARTS
            budget = DOCX_MAX_TOTAL
            for n in [n for n in ["word/document.xml"] if n in infos] + extra[:DOCX_MAX_EXTRA_PARTS]:
                cap = min(DOCX_MAX_PART, budget)
                if infos[n].file_size > cap:
                    problem = True
                    continue
                with z.open(infos[n]) as f:
                    xml = f.read(cap + 1)
                if len(xml) > cap:  # the zip understated the size
                    problem = True
                    continue
                budget -= len(xml)
                try:
                    texts.append(_docx_block(ET.fromstring(xml)))
                except (_TooDeep, RecursionError):
                    problem = True
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError, ValueError, EOFError, NotImplementedError,
            zlib.error):
        return "", False
    text = "\n".join(texts)
    if len(text) > DOCX_MAX_TEXT:
        text, problem = text[:DOCX_MAX_TEXT], True
    return text, problem


def docx_text(data):
    """Just the text of docx_read: "" when unreadable."""
    return docx_read(data)[0]


def message_texts(path=None, raw=None):
    """[(label, text, problem)] for every PDF and .docx attachment in a message, then its body. A .doc attachment
    gives (name, None, None): it can't be read here. problem is UNREADABLE for a .docx over the size limits
    (docx_read), else None. `raw` is the MIME text itself (a fetched message); else `path` is a saved
    getOriginalMessage result or an .eml."""
    from invoice_text import raw_message
    from pypdf import PdfReader
    msg = email.message_from_string(raw if raw is not None else raw_message(path), policy=policy.default)
    out = []
    for part in msg.walk():
        name = part.get_filename() or ""
        low, ctype = name.lower(), part.get_content_type()
        if low.endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(part.get_payload(decode=True) or b""))
                out.append((name, "\n".join(p.extract_text() or "" for p in reader.pages), None))
            except Exception:
                out.append((name, "", None))
        elif low.endswith(".docx") or (not low and ctype == DOCX_TYPE):
            text, too_large = docx_read(part.get_payload(decode=True))
            out.append((name or "attachment.docx", text, UNREADABLE if too_large else None))
        elif low.endswith(".doc") or (not low and ctype == "application/msword"):
            out.append((name or "attachment.doc", None, None))
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is not None:
        try:
            text = body.get_content()
        except (LookupError, UnicodeError):  # an unknown or wrong charset: read it as latin-1
            text = (body.get_payload(decode=True) or b"").decode("latin-1")
        if body.get_content_type() == "text/html":
            text = re.sub(r"<[^>]+>", " ", html.unescape(text))
        out.append(("email body", text, None))
    return out


def mentions_bank(text):
    """Does the text give bank details of any kind (even ones extract_bank can't settle on)?"""
    text = re.sub(r"[^\S\n]", " ", text)
    return bool(SORT.search(text) or TABLE.search(text) or any(_iban_ok(re.sub(r"\s", "", m.group(0)).upper())
                                                            for m in IBAN.finditer(text))
                or any(not NOT_OURS.search(text[max(0, m.start() - 12):m.start()]) for m in ACCOUNT.finditer(text)))


MONTHS = {m: i + 1 for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                          "nov", "dec"))}
MONTH_WORD = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?"
              r"|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?")
YEAR = r"((?:19|20)\d{2})"
DATE_FORMS = [  # (pattern, the groups' order: y m d, with m a number or a month word)
    (re.compile(r"(?<!\d)" + YEAR + r"-(\d{1,2})-(\d{1,2})(?!\d)"), "ymd"),
    (re.compile(r"(?<![\d/.\-])(\d{1,2})[/.\-](\d{1,2})[/.\-]((?:19|20)?\d{2})(?![\d/.\-]?\d)"), "dmy"),
    (re.compile(r"(?<![\w])(\d{1,2})(?:st|nd|rd|th)?(?:\s+of)?\s+" + MONTH_WORD + r"(?![a-z])(?:,?\s+" + YEAR
                + r"(?!\d))?", re.I), "dMy"),
    (re.compile(r"(?<![a-z])" + MONTH_WORD + r"(?![a-z])\s+(\d{1,2})(?:st|nd|rd|th)?(?!\d)(?:,?\s+" + YEAR
                + r"(?!\d))?", re.I), "Mdy"),
]


def mentioned_dates(text):
    """Dates the text mentions, as (year or None, month, day): 2026-11-21, 21/11/2026, 21.11.26, 21 November
    (2026), 21st Nov, November 21(, 2026). Impossible dates are dropped; the order is first seen."""
    out = []
    for pattern, order in DATE_FORMS:
        for m in pattern.finditer(text or ""):
            g = m.groups()
            if order == "ymd":
                y, mo, d = g
            elif order == "dmy":
                d, mo, y = g
                y = y if len(y) == 4 else "20" + y
            elif order == "dMy":
                d, mo, y = g
            else:
                mo, d, y = g
            month = int(mo) if mo.isdigit() else MONTHS[mo[:3].lower()]
            year = int(y) if y else None
            try:
                datetime.date(year or 2000, month, int(d))  # 2000: a leap year, so 29 February without a year passes
            except ValueError:
                continue
            key = (year, month, int(d))
            if key not in out:
                out.append(key)
    return out


YEARLESS_WINDOW = 200  # days: a date without a year matches an event this close to the invoice's received date


def link_candidates(dates, ledger_rows, received=None):
    """Booking refs whose event date is one of `dates` ((year or None, month, day)). A date without a year matches
    an event on that day and month within YEARLESS_WINDOW days of `received` (any year when that is unknown)."""
    try:
        got = datetime.date.fromisoformat(str(received or "")[:10])
    except ValueError:
        got = None
    refs = []
    for r in ledger_rows:
        ref = (r.get("booking_ref") or "").strip()
        try:
            event = datetime.date.fromisoformat((r.get("event_date") or "").strip())
        except ValueError:
            continue
        for y, m, d in dates:
            if (m, d) != (event.month, event.day):
                continue
            if (y is not None and y == event.year) or (
                    y is None and (got is None or abs((event - got).days) <= YEARLESS_WINDOW)):
                if ref and ref not in refs:
                    refs.append(ref)
    return refs


def auto_link(dates, ledger_rows, received=None):
    """The one booking ref the invoice's dates point to, or "" when none or more than one do."""
    refs = link_candidates(dates, ledger_rows, received)
    return refs[0] if len(refs) == 1 else ""


def print_link(ref):
    print(f"linked: {ref}" if ref else "link: none")


def read_invoice(path=None, raw=None):
    """Amount, ref and bank details from every PDF and .docx and the body (`raw`: the MIME text itself). Bank details come from the first PDF that
    has both numbers (else the first source that does); when sources give different details, or one gives
    unclear details while another is clear, `sources_disagree` is set and DIFFER is warned."""
    found = {"amount": 0.0, "invoice_ref": "", "sort_code": "", "account_number": "", "warnings": [],
             "sources_disagree": False, "dates": []}
    details, unclear = [], False  # details: (is a pdf, sort code, account number)
    for label, text, problem in message_texts(path, raw=raw):
        if text is None:
            found["warnings"].append(f"could not read {label} (.doc): check by hand")
            continue
        found["dates"] += [d for d in mentioned_dates(text) if d not in found["dates"]]
        if problem:
            found["warnings"].append(f"could not read {label} ({problem}): check it by hand")
        elif label != "email body" and not text.strip():
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


def save_pdf(raw, message_id):
    """The message's first PDF attachment, written to PDF_DIR/<message id>.pdf (mode 600, folder 700) so the
    Books bill can carry it. Returns the path, or None when there is no readable PDF under MAX_PDF_BYTES."""
    safe = re.sub(r"[^0-9A-Za-z]", "", message_id or "")
    if not safe:
        return None
    msg = email.message_from_string(raw, policy=policy.default)
    for part in msg.walk():
        if not (part.get_filename() or "").lower().endswith(".pdf"):
            continue
        data = part.get_payload(decode=True) or b""
        if not data.startswith(b"%PDF") or len(data) > MAX_PDF_BYTES:
            continue
        PDF_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = PDF_DIR / f"{safe}.pdf"
        tmp = PDF_DIR / f".{safe}.pdf.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return path
    return None


def load_raw(args):
    """The MIME text: fetched (--fetch) or from a saved getOriginalMessage result or .eml."""
    if getattr(args, "fetch", False):
        return fetch_raw(args.message_id)
    from invoice_text import raw_message
    return raw_message(args.file)


def fetch_raw(message_id):
    """Raw MIME of the invoice email, fetched read-only (ZohoMail_getOriginalMessage through lcs_mcp)."""
    from invoice_text import fetch_message
    return fetch_message(message_id)


def payee_info(client):
    """(fingerprint -> payee name, or None without a token; payee names; payee name -> last four digits)."""
    payees = client.payees() if client else None
    fps = lm.payee_fingerprints(payees) if payees is not None else None
    names = [p.get("payeeName", "") for p in payees] if payees is not None else []
    payee_last4 = {}  # payee name -> last four digits of its first UK account
    for p in payees or []:
        uk = [a for a in p.get("accounts", []) if lm.bank_fingerprint(a.get("bankIdentifier"), a.get("accountIdentifier"))]
        if uk:
            payee_last4.setdefault(p.get("payeeName", ""), lm.last4(uk[0].get("accountIdentifier")))
    return fps, names, payee_last4


def assess_invoice(inv, history, message_id, received, sender_email, sender_name, payees):
    """The change and payee checks for one invoice against `history` (the other stored rows). A newer unpaid
    invoice from the same singer with different details (scanned out of order) is flagged, mutating its row.
    Returns (assess_new result, bank_changed "yes"/"no", lines to print for the flagged rows)."""
    fps, names, payee_last4 = payees
    fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"])
    flagged = []
    for r in singer_history(history, sender_email, sender_name):
        if (fp and r.get("bank_fp") and r["bank_fp"] != fp and is_open(r)
                and r.get("bank_changed") != "yes" and (r.get("received") or "") > received):
            r["bank_changed"] = "yes"
            new4 = lm.last4(inv["account_number"])
            w = (f"BANK DETAILS CHANGED: ••••{r.get('bank_last4', '')} differs from an older invoice "
                 f"(••••{new4}): ring them before paying{same_last4_note(r.get('bank_last4', ''), new4)}")
            note(r, w)
            flagged.append(f"   ! {r['message_id']}: {w}")
    a = assess_new(inv, sender_email, sender_name, history, fps, names, payee_last4, message_id)
    changed = "yes" if a["bank_changed"] == "yes" or inv.get("sources_disagree") else "no"
    return a, changed, flagged


def payee_status(payee):
    """What is printed for a stored payee value: whether Starling already knows the singer, never the payee's
    name (the full value stays in the CSV only). Used for every printed line and the dashboard."""
    payee = payee or ""
    for prefix, label in (("existing: ", "existing payee"),
                          ("name matches payee ", "matches an existing payee, different bank details"),
                          ("probably existing: ", "probably an existing payee (no bank details on the invoice)"),
                          ("ambiguous: ", "ambiguous: the name fits more than one payee or singer: check by hand")):
        if payee.startswith(prefix):
            return label
    return payee


def print_result(name, inv, a):
    print(f"{first_name(name)}: £{inv['amount']:,.2f} (ref {inv['invoice_ref'] or '?'}) · payee {payee_status(a['payee'])}"
          + (f" · bank ••••{a['bank_last4']}" if a["bank_last4"] else ""))
    for w in inv["warnings"] + a["warnings"]:
        print(f"   ! {w}")


BILL_RUN = re.compile(r"\d(?:[ ./_\-]?\d)*")  # digits joined by single separators: one run
MAX_BILL_RUN = 5  # the Books guard reads a longer run as a possible bank number


def bill_number(ref, message_id):
    """The Books bill_number: the singer's own ref if no digit run in it is longer than 5 digits,
    else "SI-" plus the last 5 digits of the Zoho message id."""
    ref = (ref or "").strip()
    if ref and ref != "?" and all(sum(c.isdigit() for c in m.group()) <= MAX_BILL_RUN for m in BILL_RUN.finditer(ref)):
        return ref
    digits = re.sub(r"\D", "", message_id or "")
    return "SI-" + (digits[-5:] if digits else re.sub(r"[^A-Za-z0-9]", "", message_id or "")[-5:])


def bill_verdict(warnings, amount, bank_confirmed=False):
    """"yes", or "no (<reason>)": a bank-details alarm (upper-case BANK DETAILS: new, changed, differing
    or not yet verified; unless the owner has confirmed them by phone), no amount, or a zero amount."""
    if not bank_confirmed and any("BANK DETAILS" in w for w in warnings):
        return "no (bank warning)"
    if any(w.startswith("amount not found") for w in warnings):
        return "no (amount not found)"
    if not amount or round(amount, 2) <= 0:
        return "no (zero amount)"
    return "yes"


def print_bill(warnings, amount, ref, message_id, bank_confirmed=False):
    print(f"bill: {bill_verdict(warnings, amount, bank_confirmed)}")
    print(f"bill_number: {bill_number(ref, message_id)}")


def print_stored(r):
    """A recorded invoice as scan printed it (from the store), then its bill lines: a crashed run can resume."""
    warnings = [n for n in (r.get("notes") or "").split("; ")
                if n and not n.startswith(KEEP_NOTES)]
    amount = lm.money(r.get("amount_gbp"))
    print(f"{first_name(r.get('singer_name'))}: £{amount:,.2f} (ref {r.get('invoice_ref') or '?'}) · payee {payee_status(r.get('payee'))}"
          + (f" · bank ••••{r['bank_last4']}" if r.get("bank_last4") else ""))
    for w in warnings:
        print(f"   ! {w}")
    print_link((r.get("booking_ref") or "").strip())
    if is_withdrawn(r):
        print("bill: no (withdrawn)")
        print(f"bill_number: {bill_number(r.get('invoice_ref'), r['message_id'])}")
        return
    print_bill(warnings, amount, r.get("invoice_ref"), r["message_id"], r.get("bank_confirmed") == "yes")


def already_recorded(rows, message_id):
    row = next((r for r in rows if r["message_id"] == message_id), None)
    if row is not None:
        print(f"already recorded: {message_id}")
        print_stored(row)
        saved = PDF_DIR / f"{re.sub(r'[^0-9A-Za-z]', '', message_id)}.pdf"
        print(f"pdf: {saved if saved.is_file() else 'none'}")
    return row is not None


def load_invoice(args):
    return read_invoice(None, raw=fetch_raw(args.message_id)) if getattr(args, "fetch", False) else read_invoice(args.file)


def cmd_pdf(args, client=None):
    """Save the invoice PDF of a recorded invoice and print "pdf: <path>" (or "pdf: none")."""
    if not any(r["message_id"] == args.message_id for r in lm.read_csv(STORE)):
        raise SystemExit(f"no invoice {args.message_id}")
    path = save_pdf(load_raw(args), args.message_id)
    print(f"pdf: {path or 'none'}")


def cmd_scan(args, client):
    if already_recorded(lm.read_csv(STORE), args.message_id):
        return
    raw = load_raw(args)
    inv = read_invoice(None, raw=raw)
    payees = payee_info(client)
    link = auto_link(inv.get("dates") or [], lm.read_csv(lm.LEDGER), args.received)
    with lm.locked_rows(STORE, COLUMNS) as t:  # after the fetch: never hold the lock over the network
        rows = t.rows  # read again: a fetch can take a while
        if already_recorded(rows, args.message_id):
            return
        a, changed, flagged = assess_invoice(inv, rows, args.message_id, args.received, args.sender_email,
                                             args.sender_name, payees)
        rows.append({"message_id": args.message_id, "received": args.received, "singer_name": args.sender_name,
                     "singer_email": args.sender_email.lower(), "invoice_ref": inv["invoice_ref"],
                     "amount_gbp": f"{inv['amount']:.2f}", "bank_fp": a["bank_fp"], "bank_last4": a["bank_last4"],
                     "payee": a["payee"], "bank_changed": changed, "bank_confirmed": "", "paid_on": "",
                     "paid_amount": "", "paid_ref": "", "paid_verified": "",
                     "notes": "; ".join(inv["warnings"] + a["warnings"]), "booking_ref": link})
    for line in flagged:
        print(line)
    print_result(args.sender_name, inv, a)
    print_link(link)
    print_bill(inv["warnings"] + a["warnings"], inv["amount"], inv["invoice_ref"], args.message_id)
    print(f"pdf: {save_pdf(raw, args.message_id) or 'none'}")


KEEP_NOTES = ("bank details confirmed by phone", "paid reply drafted", "settled by hand", "rescanned", "withdrawn")


def rescan_changes(old, new):
    """Lines "   <field>: old → new" for each changed field; bank details as ••••last4 only."""
    def bank(r):
        return f"••••{r.get('bank_last4')}" if r.get("bank_fp") else "none"
    lines = []
    for label, show in (("amount", lambda r: f"£{lm.money(r.get('amount_gbp')):,.2f}"),
                        ("ref", lambda r: r.get("invoice_ref") or "?"), ("bank details", bank),
                        ("payee", lambda r: payee_status(r.get("payee")) or "?"),
                        ("bank changed", lambda r: r.get("bank_changed") or "no"),
                        ("bank confirmed", lambda r: r.get("bank_confirmed") or "no")):
        if label == "bank details" and old.get("bank_fp") != new.get("bank_fp") and bank(old) == bank(new):
            lines.append(f"   bank details: {bank(old)} → {bank(new)} (different sort code or account)")
        elif show(old) != show(new):
            lines.append(f"   {label}: {show(old)} → {show(new)}")
    return lines or ["   nothing changed"]


def cmd_rescan(args, client):
    """Re-read an UNPAID invoice (fetched, or from a saved file) and redo its amount, ref and bank details with
    the same change and payee checks as scan. A paid invoice is refused. A rescan never makes the record worse:
    an amount or ref it can't find keeps the old one, and when bank details were recorded but none are found
    now, nothing at all is changed. A phone confirmation survives only when the bank details are unchanged.
    Prints old → new for each changed field."""
    def find(rows):
        row = next((r for r in rows if r["message_id"] == args.message_id), None)
        if row is None:
            raise SystemExit(f"no invoice {args.message_id}")
        if row.get("paid_on"):
            raise SystemExit(f"{args.message_id}: already paid on {row['paid_on']}; not rescanned")
        if is_withdrawn(row):
            raise SystemExit(f"{args.message_id}: withdrawn on {row['withdrawn']}; not rescanned")
        return row

    first = find(lm.read_csv(STORE))
    inv = load_invoice(args)
    payees = payee_info(client)
    guess = auto_link(inv.get("dates") or [], lm.read_csv(lm.LEDGER), first.get("received"))
    with lm.locked_rows(STORE, COLUMNS) as t:  # after the fetch: never hold the lock over the network
        rows = t.rows  # read again: a fetch can take a while
        row = find(rows)
        link = (row.get("booking_ref") or "").strip() or guess  # a link already made (by hand, too) is kept
        fp = lm.bank_fingerprint(inv["sort_code"], inv["account_number"]) or ""
        if row.get("bank_fp") and not fp:
            print("no bank details found on rescan; nothing changed")  # the link too: run `link` by hand
            return
        if not inv["amount"] and lm.money(row.get("amount_gbp")):
            inv = dict(inv, amount=lm.money(row["amount_gbp"]),
                       warnings=[w for w in inv["warnings"] if not w.startswith("amount not found")])
        if not inv["invoice_ref"] and row.get("invoice_ref"):
            inv = dict(inv, invoice_ref=row["invoice_ref"])
        old = dict(row)
        still_confirmed = bool(fp) and row.get("bank_confirmed") == "yes" and fp == row.get("bank_fp")
        others = [r for r in rows if r is not row]
        # the row as first recorded counts as history when its confirmation still holds (same details, trusted) or
        # when it carried other details (a change, warned about like any other)
        history = others + ([old] if still_confirmed or (fp and row.get("bank_fp") and fp != row["bank_fp"]) else [])
        a, changed, flagged = assess_invoice(inv, history, row["message_id"], row.get("received") or "",
                                             row.get("singer_email") or "", row.get("singer_name") or "", payees)
        kept = [n for n in (row.get("notes") or "").split("; ") if n.startswith(KEEP_NOTES)]
        if fp and fp == row.get("bank_fp") and row.get("bank_changed") == "yes":
            # the same details again: a change flagged earlier (against details no longer in view) still stands
            changed = "yes"
            kept += [n for n in row["notes"].split("; ") if n.startswith(("BANK DETAILS CHANGED", DIFFER))
                     and n not in inv["warnings"] + a["warnings"] + kept]
        if not still_confirmed:
            row["bank_confirmed"] = ""
            kept = [n for n in kept if not n.startswith("bank details confirmed by phone")]
        row.update(invoice_ref=inv["invoice_ref"], amount_gbp=f"{inv['amount']:.2f}", bank_fp=a["bank_fp"],
                   bank_last4=a["bank_last4"], payee=a["payee"], bank_changed=changed,
                   notes="; ".join(inv["warnings"] + a["warnings"] + kept + [f"rescanned {lm.today()}"]),
                   booking_ref=link)
    for line in flagged:
        print(line)
    print_result(row.get("singer_name"), inv, a)
    print_link(link)
    print_bill(inv["warnings"] + a["warnings"], inv["amount"], inv["invoice_ref"], row["message_id"],
               row.get("bank_confirmed") == "yes")
    for line in rescan_changes(old, row):
        print(line)


def cmd_paid(args, client):
    rows = lm.read_csv(STORE)
    unpaid = [r for r in rows if is_open(r)]
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
    today = lm.today()
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
                  + (" (bank details match)" if verified else " (matched by name, check before thanking)"))
    if not hits:
        print("No new payments to singers matched.")
    elif args.apply:
        # after every Starling call: lock, re-read, and mark only invoices still unpaid, with feed items unused
        with lm.locked_rows(STORE, COLUMNS) as t:
            used_now = {r["paid_ref"] for r in t.rows if r.get("paid_ref")}
            for r in t.rows:
                if r["message_id"] in hits and is_open(r) and hits[r["message_id"]][2] not in used_now:
                    when, amount, uid, verified = hits[r["message_id"]]
                    r["paid_on"], r["paid_amount"], r["paid_ref"] = when, f"{amount:.2f}", uid
                    r["paid_verified"] = "yes" if verified else "no"
        print("Singer invoice store updated.")


def cmd_status(args, client=None):
    rows = lm.read_csv(STORE)
    today = lm.today()
    for r in rows:
        if is_open(r):
            print(f"{r['received']} {first_name(r['singer_name'])} £{lm.money(r['amount_gbp']):,.2f} "
                  f"(ref {r['invoice_ref'] or '?'}) · payee {payee_status(r['payee'])}"
                  + (" · BANK DETAILS CHANGED: ring before paying" if ring_first(r)
                     else " · changed bank details confirmed by phone" if r["bank_changed"] == "yes" else ""))
    s = summary(rows, today)
    print(f"{s['unpaid']} unpaid, £{s['unpaid_total']:,.2f}, oldest {s['oldest_days']} days"
          + (f", {s['bank_changed']} with changed bank details" if s["bank_changed"] else ""))


def update_invoice(message_id, fn):
    """Read-modify-write one stored invoice under the store's lock (lm.locked_rows). fn(row) edits it in
    place and may raise SystemExit to refuse, which writes nothing."""
    with lm.locked_rows(STORE, COLUMNS) as t:
        for r in t.rows:
            if r["message_id"] == message_id:
                fn(r)
                return r
        raise SystemExit(f"no invoice {message_id}")


def cmd_thanked(args, client=None):
    update_invoice(args.message_id, lambda r: note(r, f"paid reply drafted {lm.today()}"))
    print(f"{args.message_id}: paid reply noted")


FP_RE = re.compile(r"^[0-9a-f]{16}$")


def cmd_confirm(args, client=None):
    """The owner rang the singer on a number already held: trust this invoice's bank details. With --expect-fp
    (the Command Centre passes the whole 16-character fingerprint its passkey summary showed), refuses unless the
    recorded fingerprint is still exactly that, so a rescan between approval and run confirms nothing."""
    expect = getattr(args, "expect_fp", None)
    if expect is not None and not FP_RE.fullmatch(expect):
        raise SystemExit(f"{args.message_id}: --expect-fp takes all 16 lower-case hex characters; nothing confirmed")

    def edit(r):
        if not r.get("bank_fp"):
            raise SystemExit(f"{args.message_id}: no bank details recorded, nothing to confirm")
        if expect is not None and not hmac.compare_digest(r["bank_fp"], expect):
            raise SystemExit(f"{args.message_id}: the bank details changed since you approved them; nothing confirmed")
        r["bank_confirmed"] = "yes"
        note(r, f"bank details confirmed by phone {lm.today()}")
    r = update_invoice(args.message_id, edit)
    print(f"{args.message_id}: bank details confirmed")
    print(f"   trusted from now on: the account ending ••••{r.get('bank_last4', '')}")


def cmd_settled(args, client=None):
    """The owner's hand command: an invoice paid outside the feed's reach. Marks it paid for its own amount,
    unverified; never trusts its bank details (bank_confirmed is left alone)."""
    day = strict_date(args.date)
    if day > lm.today().isoformat():  # a typo'd year never marks a payment that hasn't happened
        raise SystemExit(f"{args.message_id}: {day} is after today; settle it on the day it was paid")

    def edit(r):
        if r.get("paid_on"):
            raise SystemExit(f"{args.message_id}: already paid on {r['paid_on']}")
        if is_withdrawn(r):
            raise SystemExit(f"{args.message_id}: withdrawn on {r['withdrawn']}; not settled")
        r["paid_on"], r["paid_amount"], r["paid_verified"] = day, f"{lm.money(r['amount_gbp']):.2f}", "no"
        note(r, "settled by hand")
    update_invoice(args.message_id, edit)
    print(f"{args.message_id}: settled by hand")


def cmd_withdrawn(args, client=None):
    """An invoice sent to us by mistake (another organisation's booking): mark it withdrawn today, with a
    one-word reason in the notes. Refuses a paid or already withdrawn invoice."""
    reason = (args.reason or "").strip()
    if not REASON_RE.fullmatch(reason):
        raise SystemExit("the reason must be one lower-case word, such as not-ours")

    def edit(r):
        if r.get("paid_on"):
            raise SystemExit(f"{args.message_id}: already paid on {r['paid_on']}; not withdrawn")
        if is_withdrawn(r):
            raise SystemExit(f"{args.message_id}: already withdrawn on {r['withdrawn']}")
        today = lm.today().isoformat()
        r["withdrawn"] = today
        note(r, f"withdrawn {today} ({reason})")
    update_invoice(args.message_id, edit)
    print(f"{args.message_id}: withdrawn ({reason})")


BOOKING_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,19}$")


def cmd_link(args, client=None):
    """Link an invoice to a ledger booking by hand: a label for the per-event margin, never money. The ref must be
    a booking_ref in the ledger; the invoice must be in the store. Relinking prints the old ref."""
    ref = (args.booking_ref or "").strip()
    if not BOOKING_REF_RE.fullmatch(ref):
        raise SystemExit(f"not a booking ref: {args.booking_ref!r}; nothing linked")
    if ref not in {(r.get("booking_ref") or "").strip() for r in lm.read_csv(lm.LEDGER)}:
        raise SystemExit(f"{ref} isn't in the bookings ledger; nothing linked")
    before = {}

    def edit(r):
        before["ref"] = (r.get("booking_ref") or "").strip()
        r["booking_ref"] = ref
    update_invoice(args.message_id, edit)
    was = before.get("ref")
    print(f"{args.message_id}: linked to {ref}" + (f" (was {was})" if was and was != ref else ""))


def margins(ledger_rows, singer_rows):
    """Per booking in the ledger, by event date: {ref, event_date, fee, costs, invoices, margin, margin_pct,
    cancelled}. costs is the sum of the linked singer invoices' amounts (withdrawn ones left out); margin_pct is
    None when the fee is 0. Pure: no I/O."""
    import check_payments  # the one cancelled rule every ledger reader uses
    costs, counts = {}, {}
    for s in singer_rows:
        ref = (s.get("booking_ref") or "").strip()
        if ref and not is_withdrawn(s):
            costs[ref] = costs.get(ref, 0.0) + lm.money(s.get("amount_gbp"))
            counts[ref] = counts.get(ref, 0) + 1
    out = []
    for r in ledger_rows:
        ref = (r.get("booking_ref") or "").strip()
        if not ref:
            continue
        fee = round(lm.money(r.get("value_gbp")), 2)
        cost = round(costs.get(ref, 0.0), 2)
        margin = round(fee - cost, 2)
        out.append({"ref": ref, "event_date": (r.get("event_date") or "").strip(), "fee": fee, "costs": cost,
                    "invoices": counts.get(ref, 0), "margin": margin,
                    "margin_pct": round(100 * margin / fee, 1) if fee else None,
                    "cancelled": check_payments.is_cancelled(r)})
    out.sort(key=lambda m: (m["event_date"] or "9999-99-99", m["ref"]))
    return out


def cmd_margins(args=None, client=None):
    items = margins(lm.read_csv(lm.LEDGER), lm.read_csv(STORE))
    if not items:
        print("No bookings in the ledger.")
        return
    for m in items:
        pct = f"{m['margin_pct']:.1f}%" if m["margin_pct"] is not None else "–"
        print(f"{m['ref']} {m['event_date'] or '?'}: fee £{m['fee']:,.2f} · singers £{m['costs']:,.2f} "
              f"({m['invoices']} invoice{'s' if m['invoices'] != 1 else ''}) · margin £{m['margin']:,.2f} ({pct})"
              + (" · cancelled" if m["cancelled"] else ""))
    unlinked = [s for s in lm.read_csv(STORE) if not (s.get("booking_ref") or "").strip() and not is_withdrawn(s)]
    if unlinked:
        print(f"{len(unlinked)} singer invoice{'s' if len(unlinked) != 1 else ''} not linked to a booking "
              f"(£{sum(lm.money(s.get('amount_gbp')) for s in unlinked):,.2f})")


def strict_date(value):
    """YYYY-MM-DD only; anything else is refused (SystemExit), so a typo never marks a wrong day."""
    try:
        if len(value) == 10:
            return datetime.date.fromisoformat(value).isoformat()
    except ValueError:
        pass
    raise SystemExit(f"not a YYYY-MM-DD date: {value!r}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("file", nargs="?", help="a saved getOriginalMessage result or .eml (not with --fetch)")
    s.add_argument("--fetch", action="store_true", help="fetch the raw email itself, read-only")
    s.add_argument("--message-id", required=True)
    s.add_argument("--received", required=True, type=iso_date)
    s.add_argument("--sender-email", required=True)
    s.add_argument("--sender-name", required=True)
    r = sub.add_parser("rescan")
    r.add_argument("message_id")
    r.add_argument("file", nargs="?", help="a saved getOriginalMessage result or .eml (not with --fetch)")
    r.add_argument("--fetch", action="store_true", help="fetch the raw email itself, read-only")
    p = sub.add_parser("paid")
    p.add_argument("--apply", action="store_true")
    sub.add_parser("status")
    t = sub.add_parser("thanked")
    t.add_argument("message_id")
    c = sub.add_parser("confirm")
    c.add_argument("message_id")
    c.add_argument("--expect-fp", metavar="FINGERPRINT", help="refuse unless bank_fp is exactly this (16 hex)")
    st = sub.add_parser("settled")
    st.add_argument("message_id")
    st.add_argument("date")
    pd = sub.add_parser("pdf")
    pd.add_argument("message_id")
    pd.add_argument("file", nargs="?", help="a saved getOriginalMessage result or .eml (not with --fetch)")
    pd.add_argument("--fetch", action="store_true", help="fetch the raw email itself, read-only")
    w = sub.add_parser("withdrawn")
    w.add_argument("message_id")
    w.add_argument("reason")
    lk = sub.add_parser("link")
    lk.add_argument("message_id")
    lk.add_argument("booking_ref")
    sub.add_parser("margins")
    args = ap.parse_args()
    if args.cmd in ("scan", "rescan", "pdf") and bool(args.fetch) == bool(args.file):
        ap.error(f"{args.cmd}: give either --fetch or a saved file")
    tok = lm.keychain_token() if args.cmd in ("scan", "rescan", "paid") else None
    client = lm.StarlingReadOnly(tok) if tok else None
    try:
        {"scan": cmd_scan, "rescan": cmd_rescan, "paid": cmd_paid, "status": cmd_status, "thanked": cmd_thanked,
         "confirm": cmd_confirm, "settled": cmd_settled, "withdrawn": cmd_withdrawn, "pdf": cmd_pdf,
         "link": cmd_link, "margins": cmd_margins}[args.cmd](args, client)
    except (lm.StarlingError, urllib.error.URLError, TimeoutError, ConnectionError) as e:  # type name only
        print(f"Starling unavailable ({type(e).__name__}); {args.cmd} skipped")
    except lcs_mcp.McpError as e:  # names the server only, never its command or URL
        raise SystemExit(f"could not fetch {args.message_id}: {e}; {args.cmd} skipped") from None


if __name__ == "__main__":
    main()
