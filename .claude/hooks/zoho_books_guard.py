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
Claude never emails, reminds, deletes, voids or writes off anything in Books, never
matches a bank transaction and never updates an invoice. It records only the
payments the owner approved (a confident client payment against its invoice, with any
shortfall the owner accepted as transfer fees, at most £25, as its bank_charges; and a
singer payment against its bill, unused on the free plan, both through the Starling
account), and marks an invoice sent (a status change; Books emails nobody as long as
its automatic payment reminders are off) only once Luca's own email carrying that
invoice is in the Sent folder. Calls that go around this hook (a script starting
the server itself) are refused by mcp_bypass_guard.py. Invoices are created as drafts (`send`
absent or false) and carry the DDMM booking ref as their number. The guard fails closed: any error, or a tool_input
of the wrong shape, denies the call.
Design: docs/superpowers/specs/2026-09-28-zoho-books-design.md
"""
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
# Client payments stay the owner's: Books' customer-payment tools are still denied.
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
# `amount` is the money received. A shortfall the owner accepted as transfer fees (owner decision, 28 Sep 2026:
# "short by fees £X accepted", at most £25 a booking) rides on the last payment as `bank_charges`, a plain
# number more than £0 and at most FEE_CAP; the invoice is then credited with amount + bank_charges, so both
# amount_applied values must equal that sum. Without bank_charges all three amounts are equal.
FEE_CAP = 25.00  # check_payments.FEE_CAP


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
    applied = round(amounts[0] + charges, 2)
    if line.get("invoice_id") != body.get("invoice_id") or {round(v, 2) for v in amounts[1:]} != {applied}:
        raise Deny(P + "invoice_id and every amount must agree: one invoice, the whole payment applied to it "
                   "(both amount_applied values equal amount, plus bank_charges when there are any).")
    if not (math.isfinite(amounts[0]) and 0 < amounts[0] <= 10000):
        raise Deny(P + "amount must be more than £0 and at most £10,000.")


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
    check(body, query, path)
    _scan(ti, None, "tool_input", tax="invoice" in name or "bill" in name)


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
    if name == "ZohoBooks_update_invoice":
        return P + "Claude doesn't update invoices. The owner edits drafts in Books."
    return (f"{P}{name} isn't allowed. Claude may read Books and make draft invoices, contacts and bills; "
            "it never emails, reminds, deletes, voids, refunds, writes off or matches bank transactions.")


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
