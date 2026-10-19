#!/usr/bin/env python3
"""PreToolUse guard for the Zoho Books MCP servers (matcher mcp__zoho-books.*).

This hook is the only barrier between unattended Claude runs and the live Books
account. It accepts only `mcp__zoho-books__<name>` and
`mcp__zoho-books-invoices__<name>`, and within those only the exact tool names
in READ_ALLOW (read-only tools) and WRITE_TOOLS (write tools the owner approved
on 28 Sep 2026). Every other tool, including any the servers add later, is
denied.

A write call must fit its tool's allowlist exactly: tool_input holds only
body / query_params / path_variables, and every key at every depth must be on
the tool's list, spelt exactly (lower case; a key with any upper-case letter is
denied, and so is a duplicate key in the JSON). On top of that, no string or
number anywhere in a write call may carry bank details (in any format, any
country), VAT wording or Greek/Cyrillic lookalike letters, and no invoice or bill
text may mention tax. An attachment must be a .pdf or .docx inside
iCloud Drive/LCS-invoices/ (~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices).
Claude never emails, reminds, deletes, voids or writes off anything in Books and never
matches a bank transaction. Since 14 Oct 2026 (owner hands-off: "you have full permissions
to fix all Books issues. i dont ever want to manually edit books") Claude keeps Books
correct: it may correct a draft or sent invoice's dates, payment terms, notes and terms
text, reference number and lines (never the customer, currency, tax fields, or the number
except on a draft, to a DDMM ref), and turn an invoice's payment reminders off (never on).
Invoice updates and client payments are checked against ~/lcs-private/books-guard.json
(cc_sync.py books; at most an hour old) and payments against the ledger. It records only
client payments backed by a Starling payment (one invoice, its own customer, sent and
open, never above its balance, never a "hand check only" booking, with any shortfall the
owner accepted as transfer fees, at most £40, as its bank_charges) and a singer payment
against its bill (unused on the free plan), both through the Starling account, and marks an invoice sent (a status change; Books emails nobody as long as
its automatic payment reminders are off) only once Luca's own email carrying that
invoice is in the Sent folder. Calls that go around this hook (a script starting
the server itself) are refused by mcp_bypass_guard.py. Invoices are created as drafts (`send`
absent or false) and carry the DDMM booking ref as their number. The guard fails closed: any error, or a tool_input
of the wrong shape, denies the call.
Design: docs/superpowers/specs/2026-09-28-zoho-books-design.md
"""
import csv
import datetime
import json
import math
import os
import re
import sys
import unicodedata

SERVERS = {"zoho-books", "zoho-books-invoices"}

# Exact names of the tools the Zoho Books servers mark read-only (tools/list,
# readOnlyHint), taken on 28 Sep 2026 plus the bill tools listed after the owner
# enabled Bills that day. Left out although labelled read-only:
#   get_bank_statement_import_encryption_key, generate_invoice_payment_link and
#   convert_purchase_order_to_bill (it creates a bill);
#   get_invoice_payment_qr and get_invoice_payment_qr_status (payment QR codes);
#   get_contact_bank_account, list_contact_bank_accounts and
#   list_all_contact_bank_accounts (contacts' bank details);
#   get_contact_card, list_contact_cards and get_contact_card_count (stored cards);
#   list_contact_autobill_recurring_invoices (card autobilling) and
#   get_invoice_qr_code (it can carry payment details);
#   every bank account, bank transaction, bank statement and reconciliation read
#   (get_bank_*, list_bank_*, get_matching_bank_transactions and the like): no
#   prompt uses them, and they hold the business's own bank data (review M16).
# Unknown or new tools are denied.
READ_ALLOW = {
    "ZohoBooks_bulk_export_invoices_as_pdf",
    "ZohoBooks_bulk_fetch_pricebooks",
    "ZohoBooks_bulk_print_invoices",
    "ZohoBooks_get_bill",
    "ZohoBooks_get_bill_comments",
    "ZohoBooks_get_contact",
    "ZohoBooks_get_contact_address",
    "ZohoBooks_get_contact_by_reference",
    "ZohoBooks_get_contact_client_review_email",
    "ZohoBooks_get_contact_contact_person",
    "ZohoBooks_get_contact_document",
    "ZohoBooks_get_contact_email_content",
    "ZohoBooks_get_contact_income_and_expense",
    "ZohoBooks_get_contact_inventory_summary",
    "ZohoBooks_get_contact_opening_balances",
    "ZohoBooks_get_contact_payment_method_email",
    "ZohoBooks_get_contact_person",
    "ZohoBooks_get_contact_profit_and_loss",
    "ZohoBooks_get_contact_sms_content",
    "ZohoBooks_get_contact_statement",
    "ZohoBooks_get_contact_statement_mail",
    "ZohoBooks_get_contact_unused_credits",
    "ZohoBooks_get_contact_vendor_statement_email",
    "ZohoBooks_get_contacts_sms_content",
    "ZohoBooks_get_customer_payment",
    "ZohoBooks_get_customer_payment_refund",
    "ZohoBooks_get_employee",
    "ZohoBooks_get_estimate",
    "ZohoBooks_get_expense",
    "ZohoBooks_get_invoice",
    "ZohoBooks_get_invoice_advanced_tracking_details",
    "ZohoBooks_get_invoice_by_reference",
    "ZohoBooks_get_invoice_custom_fields",
    "ZohoBooks_get_invoice_dashboard",
    "ZohoBooks_get_invoice_delivery_notes",
    "ZohoBooks_get_invoice_einvoice",
    "ZohoBooks_get_invoice_email",
    "ZohoBooks_get_invoice_metadata",
    "ZohoBooks_get_invoice_packing_slips",
    "ZohoBooks_get_invoice_signature_template",
    "ZohoBooks_get_invoice_sms",
    "ZohoBooks_get_item",
    "ZohoBooks_get_item_master",
    "ZohoBooks_get_item_variant",
    "ZohoBooks_get_payment_reminder_mail_content_for_invoice",
    "ZohoBooks_get_recurring_bill",
    "ZohoBooks_get_tax",
    "ZohoBooks_get_tax_authority",
    "ZohoBooks_get_tax_exemption",
    "ZohoBooks_get_tax_group",
    "ZohoBooks_get_unused_retainer_payments",
    "ZohoBooks_list_all_contact_persons",
    "ZohoBooks_list_bill_payments",
    "ZohoBooks_list_bills",
    "ZohoBooks_list_contact_addresses",
    "ZohoBooks_list_contact_comments",
    "ZohoBooks_list_contact_credit_note_refunds",
    "ZohoBooks_list_contact_payment_refunds",
    "ZohoBooks_list_contact_persons",
    "ZohoBooks_list_contact_tax_info",
    "ZohoBooks_list_contacts",
    "ZohoBooks_list_customer_payment_refunds",
    "ZohoBooks_list_customer_payments",
    "ZohoBooks_list_customers",
    "ZohoBooks_list_employees",
    "ZohoBooks_list_expense_comments",
    "ZohoBooks_list_expenses",
    "ZohoBooks_list_invoice_comments",
    "ZohoBooks_list_invoice_credits_applied",
    "ZohoBooks_list_invoice_payments",
    "ZohoBooks_list_invoice_templates",
    "ZohoBooks_list_invoices",
    "ZohoBooks_list_invoices_einvoice",
    "ZohoBooks_list_item_details",
    "ZohoBooks_list_item_masters",
    "ZohoBooks_list_item_variants",
    "ZohoBooks_list_items",
    "ZohoBooks_list_organizations",
    "ZohoBooks_list_pricebook_items",
    "ZohoBooks_list_pricebooks",
    "ZohoBooks_list_recurring_bill_history",
    "ZohoBooks_list_recurring_bills",
    "ZohoBooks_list_sales_orders",
    "ZohoBooks_list_tax_authorities",
    "ZohoBooks_list_tax_exemptions",
    "ZohoBooks_list_taxes",
    "ZohoBooks_list_vendor_payments",
    "ZohoBooks_get_vendor_payment",
    "ZohoBooks_list_vendors",
    "ZohoBooks_print_invoice_delivery_note",
    "ZohoBooks_print_invoice_packing_slip",
    "ZohoBooks_verify_contact_address",
}

P = "Zoho Books guard: "


class Deny(Exception):
    """A call that breaks a rule; the message is the reason Claude sees."""


# --- allowlists ----------------------------------------------------------------------
# A spec is VALUE (one string, number, boolean or null: never an object or a list),
# a dict of allowed (lower-case) keys to specs, or a one-element list [item spec].
VALUE = "value"


def obj(*keys, **nested):
    spec = {k: VALUE for k in keys}
    spec.update(nested)
    return spec


ORG_ONLY = obj("organization_id")
NOTHING = obj()
CONTACT_PERSON = obj("first_name", "last_name", "email", "phone", "mobile", "is_primary_contact", "salutation")
BILLING_ADDRESS = obj("address", "street2", "city", "state", "zip", "country", "attention")
INVOICE_LINE = obj("name", "description", "rate", "quantity", "item_order", "item_id")
# An update resends every line with its line_item_id (a line left out is removed); item_id is the schema's required key
INVOICE_UPDATE_LINE = obj("line_item_id", "item_id", "name", "description", "rate", "quantity", "item_order")
BILL_LINE = obj("name", "description", "rate", "quantity", "account_id", "item_order")
BILL_DOCUMENT = obj("document_id", "file_name")  # the keys the create_bill schema lists for documents
BILL_FIELDS = ("vendor_id", "bill_number", "date", "due_date", "reference_number", "notes",
               "payment_terms", "payment_terms_label")
BILL_UPDATE_FIELDS = ("notes", "due_date", "date", "reference_number")  # never the vendor or the amounts

INVOICE_NUMBER = re.compile(r"[0-9]{4}[A-Z]?")  # the DDMM booking ref, e.g. 2111 or 2111B
# where make_booking_docs.py writes (iCloud Drive, since 29 Sep 2026)
INVOICES_DIR = os.path.join("~", "Library", "Mobile Documents", "com~apple~CloudDocs", "LCS-invoices")
SINGER_PDF_DIR = os.path.join("~", "lcs-private", "singer-invoices")  # where singer_invoices.py saves PDFs
SINGER_PDF_NAME = re.compile(r"[0-9A-Za-z]{1,40}\.pdf")  # <Zoho message id>.pdf


def _present(v):
    return (isinstance(v, str) and v.strip() != "") or (isinstance(v, int) and not isinstance(v, bool))


def _need(sec, key, where):
    if not _present(sec.get(key)):
        raise Deny(f"{P}this call needs {where}.{key}.")


def check_create_contact(body, query, path):
    if body.get("contact_type") not in ("customer", "vendor"):
        raise Deny(P + "contact_type must be \"customer\" or \"vendor\".")


def check_update_contact(body, query, path):
    _need(path, "contact_id", "path_variables")
    # Books' schema requires contact_type on update; it may only restate customer or vendor.
    if "contact_type" in body and body["contact_type"] not in ("customer", "vendor"):
        raise Deny(P + "contact_type must be \"customer\" or \"vendor\".")


def check_create_invoice(body, query, path):
    send = query.get("send")
    if not (send is None or send is False or (isinstance(send, str) and send.lower() == "false")):
        raise Deny(P + "invoices are saved as drafts: `send` must be absent or false. The owner sends from Books.")
    auto = query.get("ignore_auto_number_generation")
    if not (auto is True or (isinstance(auto, str) and auto.lower() == "true")):
        raise Deny(P + "set query_params.ignore_auto_number_generation=true so Books keeps the DDMM invoice number.")
    num = body.get("invoice_number")
    if not (isinstance(num, str) and INVOICE_NUMBER.fullmatch(num)):
        raise Deny(P + "invoice_number must be the booking's DDMM ref (e.g. 2111 or 2111B).")
    _need(body, "customer_id", "body")


def check_invoice_document(body, query, path):
    _need(path, "invoice_id", "path_variables")
    if "attachment" in query:
        _check_attachment(query["attachment"])


def _check_attachment(value, folder=INVOICES_DIR, exts=(".pdf", ".docx")):
    """A file the booking scripts wrote: its real path must be inside `folder` (default iCloud Drive/LCS-invoices/)."""
    shown = folder.replace(os.sep, "/") + "/"
    bad = Deny(P + f"query_params.attachment must be a {' or '.join(exts)} file inside {shown} "
               "(a local path, not a URL or file contents).")
    if not (isinstance(value, str) and value.startswith(("~/", "/")) and value.endswith(exts)):
        raise bad
    if ".." in value or any(unicodedata.category(c).startswith("C") for c in value):
        raise bad
    root = os.path.realpath(os.path.expanduser(folder))
    real = os.path.realpath(os.path.expanduser(value))
    if not root.startswith("/") or os.path.commonpath([root, real]) != root or real == root:
        raise bad
    return real


def _singer_pdf(value):
    """True for the path of a PDF singer_invoices.py saved: ~/lcs-private/singer-invoices/<message id>.pdf."""
    try:
        real = _check_attachment(value, SINGER_PDF_DIR, (".pdf",))
    except Deny:
        return False
    return (os.path.dirname(real) == os.path.realpath(os.path.expanduser(SINGER_PDF_DIR))
            and bool(SINGER_PDF_NAME.fullmatch(os.path.basename(real))))


# show_comment_to_clients is not on the list, so it is denied with any value. The live
# schema (28 Sep 2026) describes it only as "Boolean to check if the comment to be shown
# to the clients" and gives no default; leaving it out lets Books apply its own default
# (internal). The owner confirms that on the first comment Claude adds.
# Mark sent (owner decision, 29 Sep 2026, with the move to the free Books plan): the invoice PDF now goes
# out attached to Luca's own email from Zoho Mail, so the Books invoice is only the accounting record.
# Once that email is in the Sent folder the daily pass marks the Books invoice sent, a status change
# only (Books emails nobody while its automatic reminders are off, MANUAL-ACTIONS §27), so payments can be
# recorded against it. Only the invoice id is allowed.
def check_mark_invoice_sent(body, query, path):
    _need(path, "invoice_id", "path_variables")


def check_invoice_comment(body, query, path):
    _need(path, "invoice_id", "path_variables")


# The expense account every singer and organist bill line goes to: "Cost of Goods Sold", the
# account Books gave the "Singing fee" and "Organ fee" purchase items on 28 Sep 2026.
SINGER_FEES_ACCOUNT_ID = "1534218000000034003"


def check_create_bill(body, query, path):
    _need(body, "vendor_id", "body")
    _need(body, "bill_number", "body")
    if "attachment" in query and not _singer_pdf(query["attachment"]):
        raise Deny(P + "a bill's query_params.attachment must be a singer invoice PDF that singer_invoices.py "
                   "saved: ~/lcs-private/singer-invoices/<message id>.pdf.")
    for line in body.get("line_items") or []:
        if isinstance(line, dict) and "account_id" in line and line["account_id"] != SINGER_FEES_ACCOUNT_ID:
            raise Deny(f"{P}bill lines go to Cost of Goods Sold: account_id must be \"{SINGER_FEES_ACCOUNT_ID}\".")


def check_update_bill(body, query, path):
    _need(path, "bill_id", "path_variables")


def check_bill_comment(body, query, path):
    _need(path, "bill_id", "path_variables")


# Purchase items ("Singing fee", "Organ fee") set up the singer bills' expense account: the
# connector has no chart-of-accounts tool, and Books files a purchase item under its default
# expense account, which get_item then shows. No account key is allowed, so Books picks it.
# The Books bank account singer payments are recorded against ("Starling Business"): a name and GBP only,
# never an account number or sort code (those keys aren't allowed, and the bank-details scan still runs).
def check_create_bank_account(body, query, path):
    _need(body, "account_name", "body")
    if body.get("account_type") != "bank":
        raise Deny(P + "account_type must be \"bank\".")
    if body.get("currency_code") not in (None, "GBP"):
        raise Deny(P + "currency_code must be \"GBP\" or absent.")


# Singer bills only (owner decision, 28 Sep 2026): a payment Starling shows was made to the singer's own bank
# details, recorded against that one bill, in full, through the owner's "Starling Business" account in Books.
STARLING_BOOKS_ACCOUNT_ID = "1534218000000095168"  # the owner's Starling Business account in Books


def check_create_vendor_payment(body, query, path):
    for key in ("vendor_id", "date"):
        _need(body, key, "body")
    if not STARLING_BOOKS_ACCOUNT_ID or body.get("paid_through_account_id") != STARLING_BOOKS_ACCOUNT_ID:
        raise Deny(P + "paid_through_account_id must be the Starling Business account in Books"
                   + (f" (\"{STARLING_BOOKS_ACCOUNT_ID}\")." if STARLING_BOOKS_ACCOUNT_ID else ", and it isn't set yet."))
    if body.get("payment_mode") not in (None, "Bank Transfer"):
        raise Deny(P + "payment_mode must be \"Bank Transfer\" or absent.")
    bills = body.get("bills")
    if not (isinstance(bills, list) and len(bills) == 1 and isinstance(bills[0], dict)):
        raise Deny(P + "a payment settles exactly one bill: bills must list one {bill_id, amount_applied}.")
    _need(bills[0], "bill_id", "body.bills[0]")
    amount, applied = body.get("amount"), bills[0].get("amount_applied")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (amount, applied)):
        raise Deny(P + "amount and amount_applied must be plain numbers.")
    if not (0 < amount <= 10000 and round(amount, 2) == round(applied, 2)):
        raise Deny(P + "amount must equal the bill's amount_applied (more than £0, at most £10,000).")


# Client payments (owner decision, 28 Sep 2026, the evening after the singer rule): a payment
# check_payments.py matched confidently (its "record_in_books" list), recorded against that booking's one
# invoice, through the Starling account, never with contact_persons (Books would email a thank-you).
# amount, amount_applied and invoices[0].amount_applied are always equal: Books credits the invoice with
# `amount`. A shortfall the owner accepted as transfer fees (owner decision, 28 Sep 2026: "short by fees £X
# accepted", at most £40 a booking since 29 Sep 2026) rides on the last payment as `bank_charges`, a plain number
# more than £0, at most FEE_CAP and less than amount; Books then deposits amount - bank_charges (the money that
# reached Starling). Books refuses an amount_applied above amount (checked against Books on 29 Sep 2026).
FEE_CAP = 40.00  # check_payments.FEE_CAP


# --- the guard's view of Books and the ledger (owner hands-off, 14 Oct 2026) ------------------------------
# The guard can't call Books (mcp_bypass_guard.py refuses that, rightly), so it checks invoice updates and client
# payments against ~/lcs-private/books-guard.json, which `cc_sync.py books` writes from a read-only list_invoices:
# each invoice's invoice_id, customer_id, number, status, total and balance. It must be at most SNAPSHOT_MAX_AGE
# old; run `cc_sync.py books` first. A payment is also checked against the ledger (~/lcs-private/bookings.csv):
# the invoice's booking must be there, and never one whose notes say "hand check only". A missing, unreadable or
# stale file denies the call (fail closed). LCS_PRIVATE_DIR and LCS_BOOKINGS_CSV move both, as for the scripts.
SNAPSHOT_MAX_AGE = datetime.timedelta(minutes=60)
OPEN_STATUSES = {"sent", "viewed", "overdue", "unpaid", "partially_paid"}  # sent to the client and not yet paid
EDITABLE_STATUSES = OPEN_STATUSES | {"draft"}  # an invoice Claude may correct: never a paid or void one
HAND_ONLY_NOTE = re.compile(r"\bhand check only\b", re.I)  # check_payments.HAND_ONLY_NOTE
ISO_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _private_dir():
    return os.environ.get("LCS_PRIVATE_DIR") or os.path.join(os.path.expanduser("~"), "lcs-private")


def _books_invoice(invoice_id, now=None):
    """The invoice as books-guard.json shows it, or Deny."""
    stale = Deny(P + "the guard checks this against ~/lcs-private/books-guard.json, which is missing, unreadable or "
                 "more than an hour old, or doesn't list this invoice: run `.venv/bin/python scripts/reports/cc_sync.py "
                 "books` and try again.")
    try:
        with open(os.path.join(_private_dir(), "books-guard.json"), encoding="utf-8") as f:
            data = json.load(f)
        when = datetime.datetime.fromisoformat(data["generated_at"])
        now = now or datetime.datetime.now(datetime.timezone.utc)
        if when.tzinfo is None or not (datetime.timedelta(minutes=-5) <= now - when <= SNAPSHOT_MAX_AGE):
            raise stale
        found = [i for i in data["invoices"] if isinstance(i, dict) and i.get("invoice_id") == invoice_id]
    except Deny:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise stale
    if len(found) != 1 or not all(isinstance(found[0].get(k), str) for k in ("customer_id", "number", "status")):
        raise stale
    inv = found[0]
    if not isinstance(inv.get("balance"), (int, float)) or isinstance(inv.get("balance"), bool):
        raise stale
    return inv


# One-off exceptions to the "hand check only" rule (CLAUDE.md, Zoho Books: "a committed, reviewed guard change naming the
# exact records, reverted afterwards"). Each lets exactly one customer payment through:
# - that invoice and customer, and the invoice as books-guard.json shows it (sent, with that total and that balance);
# - that date and that exact amount, no bank charges, and the booking's own ref (or none) as reference_number;
# - only until `until`: it lapses even if the revert is missed.
# The first time one is allowed the guard claims it with a marker under ~/lcs-private/books-guard-one-offs/, so it is
# never allowed twice, even against a snapshot that still shows the invoice unpaid.
# Owner, 19 Oct 2026: record the £2,800 Starling payment of 19 Oct against invoice 2108A. Its bank reference names the
# client and it equals the invoice. 2108A is hand-check only because ref 2108 was also issued to an earlier booking.
ONE_OFF_HAND_CHECK_PAYMENTS = (
    {"invoice_id": "1534218000000393001", "customer_id": "1534218000000392001", "number": "2108A",
     "date": "2026-10-19", "amount": 2800.0, "until": "2026-10-20"},
)


def _one_off_payment(body, inv, today=None):
    """The one of ONE_OFF_HAND_CHECK_PAYMENTS that this payment is exactly, still in date, or None."""
    today = today or datetime.date.today()
    for o in ONE_OFF_HAND_CHECK_PAYMENTS:
        if (body.get("invoice_id") == o["invoice_id"] and body.get("customer_id") == o["customer_id"]
                and inv.get("number") == o["number"] and inv.get("status") == "sent"
                and _plain_number(inv.get("total")) and round(inv["total"], 2) == o["amount"]
                and _plain_number(inv.get("balance")) and round(inv["balance"], 2) == o["amount"]
                and body.get("date") == o["date"] and "bank_charges" not in body
                and _plain_number(body.get("amount")) and body["amount"] == o["amount"]
                and body.get("reference_number") in (None, o["number"])
                and today <= datetime.date.fromisoformat(o["until"])):
            return o
    return None


def _claim_one_off(o):
    """Mark the one-off used (O_EXCL), or Deny when it already is or the marker can't be written (fail closed)."""
    folder = os.path.join(_private_dir(), "books-guard-one-offs")
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        fd = os.open(os.path.join(folder, f"{o['invoice_id']}-{o['date']}"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
    except FileExistsError:
        raise Deny(P + f"the one-off for invoice {o['number']} has been used already: a payment is never recorded twice.")
    except OSError:
        raise Deny(P + "the one-off's use can't be recorded, so no payment is recorded.")


def _ledger_allows_payment(number):
    """Deny unless the ledger has the booking `number` and none of its rows says "hand check only"."""
    path = os.environ.get("LCS_BOOKINGS_CSV") or os.path.join(_private_dir(), "bookings.csv")
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("booking_ref") or "").strip() == number]
    except (OSError, ValueError, csv.Error):
        raise Deny(P + "the ledger (~/lcs-private/bookings.csv) can't be read, so no payment is recorded.")
    if not rows:
        raise Deny(P + f"invoice {number} has no booking in the ledger, so no payment is recorded against it.")
    if any(HAND_ONLY_NOTE.search(r.get("notes") or "") for r in rows):
        raise Deny(P + f"booking {number} says \"hand check only\" in the ledger: its payments are confirmed by hand, "
                   "never recorded by Claude.")


def _plain_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _iso_day(v, where):
    try:
        ok = isinstance(v, str) and ISO_DAY.fullmatch(v) and datetime.date.fromisoformat(v)
    except ValueError:
        ok = False
    if not ok:
        raise Deny(f"{P}{where} must be a date written YYYY-MM-DD.")


# Invoice corrections (owner hands-off, 14 Oct 2026: "you have full permissions to fix all Books issues. i dont
# ever want to manually edit books"): dates and payment terms, notes and terms text, the reference number and the
# lines' description, rate and quantity, on a draft or sent (not paid, not void) invoice. Never the customer
# (customer_id, which the update schema requires, may only restate the invoice's own), never the currency, tax or
# VAT fields, discounts, adjustments, email text or flags (none of those keys is listed), and the invoice number
# only on a draft, to a DDMM ref. Books asks a sent invoice's update for a `reason` (code 110701, 14 Oct 2026): free
# text, scanned like the rest. The text scan below still denies bank details, VAT wording and the word tax.
def check_update_invoice(body, query, path):
    _need(path, "invoice_id", "path_variables")
    # Books removes every line an update leaves out, so each update resends the invoice's lines (get_invoice first,
    # each with its line_item_id); a call without them could empty the invoice.
    if not (isinstance(body.get("line_items"), list) and body["line_items"]):
        raise Deny(P + "an invoice update resends every line from get_invoice (with its line_item_id): Books removes "
                   "a line left out.")
    inv = _books_invoice(path["invoice_id"])
    if inv["status"] not in EDITABLE_STATUSES:
        raise Deny(P + f"invoice {inv['number']} is {inv['status']}: Claude corrects only draft or sent invoices, "
                   "never a paid or void one.")
    if "customer_id" in body and body["customer_id"] != inv["customer_id"]:
        raise Deny(P + "an invoice update never changes the customer: customer_id may only restate the invoice's own.")
    num = body.get("invoice_number")
    if "invoice_number" in body and num != inv["number"]:
        if inv["status"] != "draft":
            raise Deny(P + "the invoice number changes only on a draft invoice.")
        if not (isinstance(num, str) and INVOICE_NUMBER.fullmatch(num)):
            raise Deny(P + "invoice_number must be the booking's DDMM ref (e.g. 2111 or 2111B).")
    auto = query.get("ignore_auto_number_generation")
    if auto is not None and not (isinstance(auto, bool) or (isinstance(auto, str) and auto.lower() in ("true", "false"))):
        raise Deny(P + "ignore_auto_number_generation must be true or false.")
    for key in ("date", "due_date"):
        if key in body:
            _iso_day(body[key], f"body.{key}")
    if "payment_terms" in body and not (isinstance(body["payment_terms"], int) and not isinstance(body["payment_terms"], bool)
                                        and 0 <= body["payment_terms"] <= 400):
        raise Deny(P + "payment_terms must be a whole number of days.")
    for i, line in enumerate(body.get("line_items") or []):
        for key, low in (("rate", 0), ("quantity", 0)):
            if key in line and not (_plain_number(line[key]) and low <= line[key] <= 10000
                                    and (key != "quantity" or line[key] > 0)):
                raise Deny(f"{P}body.line_items[{i}].{key} must be a plain number (rate £0 to £10,000, quantity above 0).")


# Payment reminders off (owner hands-off, 14 Oct 2026): Books' automatic reminders would email the client, so Claude
# turns them off wherever it finds them on. Never on: enable_invoice_payment_reminder and every remind tool stay denied.
def check_disable_reminder(body, query, path):
    _need(path, "invoice_id", "path_variables")


def check_create_customer_payment(body, query, path):
    for key in ("customer_id", "date", "invoice_id"):
        _need(body, key, "body")
    if body.get("account_id") != STARLING_BOOKS_ACCOUNT_ID:
        raise Deny(P + f"account_id must be the Starling Business account in Books (\"{STARLING_BOOKS_ACCOUNT_ID}\").")
    if body.get("payment_mode") != "banktransfer":
        raise Deny(P + "payment_mode must be \"banktransfer\".")
    ref = body.get("reference_number")
    if ref is not None and not (isinstance(ref, str) and INVOICE_NUMBER.fullmatch(ref)):
        raise Deny(P + "reference_number may only be the booking's DDMM ref (e.g. 2111 or 2111B).")
    invoices = body.get("invoices")
    if not (isinstance(invoices, list) and len(invoices) == 1 and isinstance(invoices[0], dict)):
        raise Deny(P + "a payment settles exactly one invoice: invoices must list one {invoice_id, amount_applied}.")
    line = invoices[0]
    amounts = (body.get("amount"), body.get("amount_applied"), line.get("amount_applied"))
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in amounts):
        raise Deny(P + "amount, amount_applied and invoices[0].amount_applied must be plain numbers.")
    charges = 0
    if "bank_charges" in body:
        charges = body["bank_charges"]
        if not (isinstance(charges, (int, float)) and not isinstance(charges, bool)
                and math.isfinite(charges) and 0 < charges <= FEE_CAP):
            raise Deny(P + f"bank_charges must be a plain number, more than £0 and at most £{FEE_CAP:.0f} "
                       "(a shortfall the owner accepted as transfer fees).")
    if line.get("invoice_id") != body.get("invoice_id") or len({round(v, 2) for v in amounts}) != 1:
        raise Deny(P + "invoice_id and every amount must agree: one invoice, the whole payment applied to it "
                   "(amount and both amount_applied values equal; bank_charges, if any, is part of amount).")
    if not (math.isfinite(amounts[0]) and 0 < amounts[0] <= 10000):
        raise Deny(P + "amount must be more than £0 and at most £10,000.")
    if charges and not charges < amounts[0]:
        raise Deny(P + "bank_charges must be less than amount.")
    _iso_day(body["date"], "body.date")
    # Books as the guard last saw it (books-guard.json): the invoice's own customer, sent and still open, never a
    # draft, paid or void one, and never more than its balance; then the ledger: never a "hand check only" booking.
    inv = _books_invoice(body["invoice_id"])
    if body["customer_id"] != inv["customer_id"]:
        raise Deny(P + "customer_id must be the invoice's own customer.")
    if inv["status"] not in OPEN_STATUSES:
        raise Deny(P + f"invoice {inv['number']} is {inv['status']}: a payment is recorded only against a sent invoice "
                   "with a balance (never a draft, paid or void one).")
    if round(amounts[0], 2) > round(inv["balance"], 2):
        raise Deny(P + f"£{amounts[0]:,.2f} is more than invoice {inv['number']}'s balance (£{inv['balance']:,.2f}).")
    one_off = _one_off_payment(body, inv)
    if not one_off:
        _ledger_allows_payment(inv["number"])
    return one_off  # claimed by check_write only once every other check (the bank-details scan too) has passed


def check_create_item(body, query, path):
    _need(body, "name", "body")
    if body.get("item_type") != "purchases":
        raise Deny(P + "item_type must be \"purchases\": items are only for singer and organist bills.")
    if body.get("product_type") not in (None, "service"):
        raise Deny(P + "product_type must be \"service\" or absent.")


# Write tools the owner approved on 28 Sep 2026, as tool name -> (allowed keys of body,
# query_params and path_variables, the check on their values). Any key not listed, at any
# depth, is denied. See the design's "Approved write tools".
WRITE_TOOLS = {
    "ZohoBooks_create_contact": (
        obj("contact_name", "company_name", "contact_type", "payment_terms", "payment_terms_label", "notes",
            contact_persons=[CONTACT_PERSON], billing_address=BILLING_ADDRESS),
        ORG_ONLY, NOTHING, check_create_contact),
    "ZohoBooks_update_contact": (
        obj("contact_name", "company_name", "contact_type"), ORG_ONLY, obj("contact_id"), check_update_contact),
    "ZohoBooks_create_invoice": (
        obj("customer_id", "invoice_number", "date", "due_date", "payment_terms", "payment_terms_label", "notes",
            "terms", "reference_number", "allow_partial_payments", "template_id", line_items=[INVOICE_LINE]),
        obj("organization_id", "ignore_auto_number_generation", "send"), NOTHING, check_create_invoice),
    "ZohoBooks_add_invoice_document": (
        NOTHING, ORG_ONLY, obj("invoice_id", "document_id"), check_invoice_document),
    "ZohoBooks_upload_invoice_document": (
        NOTHING, obj("organization_id", "attachment"), obj("invoice_id", "document_id"), check_invoice_document),
    "ZohoBooks_mark_invoice_sent": (
        NOTHING, ORG_ONLY, obj("invoice_id"), check_mark_invoice_sent),
    "ZohoBooks_add_invoice_comment": (
        obj("description"), ORG_ONLY, obj("invoice_id"), check_invoice_comment),
    "ZohoBooks_create_bill": (
        obj(*BILL_FIELDS, line_items=[BILL_LINE], documents=[BILL_DOCUMENT]), obj("organization_id", "attachment"),
        NOTHING, check_create_bill),
    "ZohoBooks_update_bill": (
        obj(*BILL_UPDATE_FIELDS), ORG_ONLY, obj("bill_id"), check_update_bill),
    "ZohoBooks_add_bill_comment": (
        obj("description"), ORG_ONLY, obj("bill_id"), check_bill_comment),
    "ZohoBooks_create_bank_account": (
        obj("account_name", "account_type", "currency_code", "description"), ORG_ONLY, NOTHING,
        check_create_bank_account),
    "ZohoBooks_create_vendor_payment": (
        obj("vendor_id", "amount", "date", "payment_mode", "paid_through_account_id", "description",
            bills=[obj("bill_id", "amount_applied")]),
        ORG_ONLY, NOTHING, check_create_vendor_payment),
    "ZohoBooks_create_customer_payment": (
        obj("customer_id", "date", "amount", "amount_applied", "bank_charges", "invoice_id", "payment_mode",
            "account_id", "reference_number", "description", invoices=[obj("invoice_id", "amount_applied")]),
        ORG_ONLY, NOTHING, check_create_customer_payment),
    "ZohoBooks_create_item": (
        obj("name", "rate", "description", "item_type", "product_type", "purchase_rate", "purchase_description"),
        ORG_ONLY, NOTHING, check_create_item),
    # owner hands-off, 14 Oct 2026
    "ZohoBooks_update_invoice": (
        obj("customer_id", "invoice_number", "date", "due_date", "payment_terms", "payment_terms_label", "notes",
            "terms", "reference_number", "reason", line_items=[INVOICE_UPDATE_LINE]),
        obj("organization_id", "ignore_auto_number_generation"), obj("invoice_id"), check_update_invoice),
    "ZohoBooks_disable_invoice_payment_reminder": (
        NOTHING, ORG_ONLY, obj("invoice_id"), check_disable_reminder),
}


def _fit(value, spec, where):
    """`value` checked against `spec`; every key must be spelt exactly as listed. Raises Deny."""
    if spec == VALUE:
        if isinstance(value, (dict, list)):
            raise Deny(f"{P}{where} must be a single value, not an object or a list.")
        return value
    if isinstance(spec, list):
        if not isinstance(value, list):
            raise Deny(f"{P}{where} must be a list.")
        return [_fit(v, spec[0], f"{where}[{i}]") for i, v in enumerate(value)]
    if not isinstance(value, dict):
        raise Deny(f"{P}{where} must be an object.")
    for key, v in value.items():
        if not isinstance(key, str) or key != key.lower() or any(c.isupper() for c in key):
            raise Deny(f"{P}{where}.{key} isn't allowed: keys are lower case only.")
        if key not in spec:
            raise Deny(f"{P}{where}.{key} isn't allowed here. Allowed: {', '.join(sorted(spec)) or 'nothing'}.")
        _fit(v, spec[key], f"{where}.{key}")
    return value


# --- no bank details, no VAT, no tax -------------------------------------------------
# Text is NFKC-normalised (fullwidth digits and letters become ASCII) and stripped of
# invisible format characters and accents before it is scanned. Real dates and clock
# times are removed first, so that "2026-11-21", "21/11/2026", "1 December 2026 11:00"
# and "11.00-12.30" don't count as digit runs. The lookarounds keep a dotted sort code
# (04.00.04) from being read as a time.
ISO_DATE = re.compile(r"(?<![0-9])(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])(?![0-9])")
DMY_DATE = re.compile(r"(?<![0-9])(?:0?[1-9]|[12][0-9]|3[01])([ ./-])(?:0?[1-9]|1[0-2])\1(?:19|20)[0-9]{2}(?![0-9])")
MONTH_DATE = re.compile(r"(?<![a-z])(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
                        r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?![a-z])\.?"
                        r"(?:\s+[0-9]{1,2}(?:st|nd|rd|th)?)?,?\s+(?:19|20)[0-9]{2}(?![0-9])", re.I)
CLOCK_TIME = re.compile(r"(?<![0-9.:])(?:[01]?[0-9]|2[0-3])[:.][0-5][0-9](?![0-9.:])")
# Digits joined by single separators (space . / - _ and the Unicode dashes and minus).
DIGIT_RUN = re.compile(r"\d(?:[\s./_\-\u2010-\u2015\u2212]?\d)*")
# A generic IBAN: country code, check digits, 11-30 letters or digits, optionally grouped.
IBAN = re.compile(r"(?<![a-z0-9])[a-z]{2}\s?[0-9]{2}(?:\s?[a-z0-9]){11,30}(?![a-z0-9])", re.I)
BANK_WORDS = re.compile(r"(?<![a-z])(?:sort\W*code|s/c|a/c|acct|acc(?:oun)?t\W*(?:number|no|#)|acc\W*no|iban|swift|bic)"
                        r"(?![a-z])", re.I)
VAT_WORDS = re.compile(r"(?<![a-z])(?:v\W{0,2}a\W{0,2}t(?![a-z])|vatable|value\W*added\W*tax)", re.I)
TAX_WORD = re.compile(r"(?<![a-z])tax(?:es)?(?![a-z])", re.I)  # invoice and bill text only
RECORD_ID = re.compile(r"[0-9]{9,20}")  # a Books record id, in a key ending _id
OWN_PATTERN = {"invoice_number": INVOICE_NUMBER}
BANK_OR_VAT = (P + "{where} looks like bank details or mentions VAT. Claude never puts bank details in Books, "
               "and Alma Consort Ltd is not VAT-registered.")


def _plain(text):
    """NFKC text without format characters (zero-width, soft hyphen) or combining accents."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(c for c in unicodedata.normalize("NFKD", text) if unicodedata.category(c) not in ("Cf", "Mn"))


def _bank_digits(text):
    """True if a run of joined digits could be a sort code, account number or card/IBAN body."""
    for m in DIGIT_RUN.finditer(text):
        run = m.group()
        n = sum(c.isdigit() for c in run)
        if 6 <= n <= 10 or n >= 14:
            return True
        # 11-13 digits pass only as a phone number: 11 digits from 0 (UK), or after "+" (international)
        if 11 <= n <= 13 and not ((n == 11 and run[0] == "0") or _after_plus(text, m.start())):
            return True
    return False


def _after_plus(text, i):
    """True if text[i] follows "+", or "+" and one space."""
    return text[i - 1:i] == "+" or (text[i - 1:i] == " " and text[i - 2:i - 1] == "+")


def strip_dates(text):
    """`text` with real dates and clock times blanked, so they don't count as digit runs."""
    for pattern in (ISO_DATE, DMY_DATE, MONTH_DATE, CLOCK_TIME):
        text = pattern.sub(" ", text)
    return text


def bank_details_in(text):
    """True if plain text carries bank details: a sort-code or account-length digit run, a bank keyword
    (sort code, account number, IBAN, SWIFT, BIC) or an IBAN. Shared with zoho_guard.py (Mail drafts);
    VAT wording and lookalike letters are the Books guard's own extra checks, not part of this."""
    bare = strip_dates(_plain(text))
    return bool(_bank_digits(bare) or BANK_WORDS.search(bare)
                or any(sum(c.isdigit() for c in m.group()) >= 10 for m in IBAN.finditer(bare)))


def _lookalike(text):
    return any(unicodedata.name(c, "").startswith(("GREEK", "CYRILLIC")) for c in text)


def _scan(value, key, where, tax):
    """Deny bank details, VAT, lookalike letters or (if `tax`) the word tax in any value of a write call."""
    if isinstance(value, dict):
        for k, v in value.items():
            _scan(v, k, f"{where}.{k}", tax)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _scan(v, key, f"{where}[{i}]", tax)
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = _plain(str(value))
        own = OWN_PATTERN.get(key)
        exempt = (own is not None and isinstance(value, str) and own.fullmatch(value)) or (
            isinstance(key, str) and key.endswith("_id") and RECORD_ID.fullmatch(text)) or (
            key == "attachment" and _singer_pdf(value))  # the file name is the Zoho message id
        bare = strip_dates(text)
        if ((not exempt and _bank_digits(bare)) or BANK_WORDS.search(bare) or VAT_WORDS.search(bare)
                or _lookalike(text) or any(sum(c.isdigit() for c in m.group()) >= 10 for m in IBAN.finditer(bare))):
            raise Deny(BANK_OR_VAT.format(where=where))
        if tax and TAX_WORD.search(bare):
            raise Deny(f"{P}{where} mentions tax. Alma Consort Ltd is not VAT-registered, so its invoices and "
                       "bills never mention tax.")
    elif value is not None and not isinstance(value, bool):
        raise Deny(f"{P}{where} has an unexpected value.")


def check_write(name, tool_input):
    body_spec, query_spec, path_spec, check = WRITE_TOOLS[name]
    if tool_input is None:
        tool_input = {}
    ti = _fit(tool_input, {"body": body_spec, "query_params": query_spec, "path_variables": path_spec}, "tool_input")
    body, query, path = ti.get("body", {}), ti.get("query_params", {}), ti.get("path_variables", {})
    one_off = check(body, query, path)
    _scan(ti, None, "tool_input", tax="invoice" in name or "bill" in name)
    if one_off:  # last of all, so a call refused for any other reason never uses the one-off up
        _claim_one_off(one_off)


def decide(tool, tool_input):
    parts = tool.split("__")
    if len(parts) != 3 or parts[0] != "mcp" or parts[1] not in SERVERS or not parts[2]:
        return f"{P}{tool!r} is not a tool of the zoho-books or zoho-books-invoices server."
    name = parts[2]
    if name in READ_ALLOW:
        return None  # allowed; normal permission rules apply
    if name in WRITE_TOOLS:
        try:
            check_write(name, tool_input)
        except Deny as e:
            return str(e)
        return None
    return (f"{P}{name} isn't allowed. Claude may read Books, make draft invoices, contacts and bills, correct an "
            "invoice's dates, terms, text and lines, record a client payment and turn reminders off; it never emails, "
            "reminds, deletes, voids, refunds, writes off or matches bank transactions.")


def _no_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def main():
    try:
        event = json.load(sys.stdin, object_pairs_hook=_no_duplicate_keys)
        tool = event.get("tool_name")
        if not isinstance(tool, str) or not tool:
            raise ValueError("missing or invalid tool_name")
        reason = decide(tool, event.get("tool_input"))
    except Exception as e:  # fail closed
        reason = f"Zoho Books guard error ({type(e).__name__}); call blocked."
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
