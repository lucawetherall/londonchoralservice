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
the tool's list (compared case-insensitively; a differently-cased duplicate is
denied, and so is a duplicate key in the JSON). On top of that, no string or
number anywhere in a write call may carry bank details or the word "VAT".
Claude never emails, reminds, deletes, voids, records a payment or matches a
bank transaction in Books, and never updates an invoice: those stay the owner's
job. Invoices are created as drafts (`send` absent or false) and carry the DDMM
booking ref as their number. The guard fails closed: any error, or a tool_input
of the wrong shape, denies the call.
Design: docs/superpowers/specs/2026-09-28-zoho-books-design.md
"""
import json
import re
import sys

SERVERS = {"zoho-books", "zoho-books-invoices"}

# Exact names of the tools the Zoho Books servers mark read-only (tools/list,
# readOnlyHint), taken on 28 Sep 2026 plus the bill tools listed after the owner
# enabled Bills that day. Left out although labelled read-only:
#   get_bank_statement_import_encryption_key, generate_invoice_payment_link and
#   convert_purchase_order_to_bill (it creates a bill);
#   get_invoice_payment_qr and get_invoice_payment_qr_status (payment QR codes);
#   get_contact_bank_account, list_contact_bank_accounts and
#   list_all_contact_bank_accounts (contacts' bank details);
#   get_contact_card, list_contact_cards and get_contact_card_count (stored cards).
# Unknown or new tools are denied.
READ_ALLOW = {
    "ZohoBooks_bulk_export_invoices_as_pdf",
    "ZohoBooks_bulk_fetch_pricebooks",
    "ZohoBooks_bulk_print_invoices",
    "ZohoBooks_get_bank_account",
    "ZohoBooks_get_bank_account_balance",
    "ZohoBooks_get_bank_account_balances",
    "ZohoBooks_get_bank_account_insights",
    "ZohoBooks_get_bank_account_overview",
    "ZohoBooks_get_bank_account_preferences",
    "ZohoBooks_get_bank_account_rule",
    "ZohoBooks_get_bank_account_statement_summary",
    "ZohoBooks_get_bank_accounts_overview",
    "ZohoBooks_get_bank_reconciliation",
    "ZohoBooks_get_bank_reconciliation_document",
    "ZohoBooks_get_bank_transaction",
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
    "ZohoBooks_get_invoice_qr_code",
    "ZohoBooks_get_invoice_signature_template",
    "ZohoBooks_get_invoice_sms",
    "ZohoBooks_get_item",
    "ZohoBooks_get_item_master",
    "ZohoBooks_get_item_variant",
    "ZohoBooks_get_last_imported_bank_statement",
    "ZohoBooks_get_matching_bank_transactions",
    "ZohoBooks_get_payment_reminder_mail_content_for_invoice",
    "ZohoBooks_get_recurring_bill",
    "ZohoBooks_get_tax",
    "ZohoBooks_get_tax_authority",
    "ZohoBooks_get_tax_exemption",
    "ZohoBooks_get_tax_group",
    "ZohoBooks_get_unused_retainer_payments",
    "ZohoBooks_list_all_contact_persons",
    "ZohoBooks_list_bank_account_balances",
    "ZohoBooks_list_bank_account_match_filters",
    "ZohoBooks_list_bank_account_rules",
    "ZohoBooks_list_bank_account_statements",
    "ZohoBooks_list_bank_account_subaccounts",
    "ZohoBooks_list_bank_account_transactions",
    "ZohoBooks_list_bank_accounts",
    "ZohoBooks_list_bank_reconciliations",
    "ZohoBooks_list_bank_transactions",
    "ZohoBooks_list_bill_payments",
    "ZohoBooks_list_bills",
    "ZohoBooks_list_contact_addresses",
    "ZohoBooks_list_contact_autobill_recurring_invoices",
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
    "ZohoBooks_list_unreviewed_bank_statements",
    "ZohoBooks_list_vendor_payments",
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

INVOICE_NUMBER = re.compile(r"[0-9]{4}[A-Z]?")  # the DDMM booking ref, e.g. 2111 or 2111B
BILL_NUMBER = re.compile(r"[A-Za-z0-9][A-Za-z0-9/._-]{0,29}")  # a singer's own invoice number, e.g. S-17


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


# show_comment_to_clients is not on the list, so it is denied with any value. The live
# schema (28 Sep 2026) describes it only as "Boolean to check if the comment to be shown
# to the clients" and gives no default; leaving it out lets Books apply its own default
# (internal). The owner confirms that on the first comment Claude adds.
def check_invoice_comment(body, query, path):
    _need(path, "invoice_id", "path_variables")


def check_create_bill(body, query, path):
    _need(body, "vendor_id", "body")
    _need(body, "bill_number", "body")


def check_update_bill(body, query, path):
    _need(path, "bill_id", "path_variables")
    _need(body, "vendor_id", "body")


def check_bill_comment(body, query, path):
    _need(path, "bill_id", "path_variables")


# Write tools the owner approved on 28 Sep 2026, as tool name -> (allowed keys of body,
# query_params and path_variables, the check on their values). Any key not listed, at any
# depth, is denied. See the design's "Approved write tools".
WRITE_TOOLS = {
    "ZohoBooks_create_contact": (
        obj("contact_name", "company_name", "contact_type", "payment_terms", "payment_terms_label", "notes",
            contact_persons=[CONTACT_PERSON], billing_address=BILLING_ADDRESS),
        ORG_ONLY, NOTHING, check_create_contact),
    "ZohoBooks_update_contact": (
        obj("contact_name", "company_name"), ORG_ONLY, obj("contact_id"), check_update_contact),
    "ZohoBooks_create_invoice": (
        obj("customer_id", "invoice_number", "date", "due_date", "payment_terms", "payment_terms_label", "notes",
            "terms", "reference_number", "allow_partial_payments", "template_id", line_items=[INVOICE_LINE]),
        obj("organization_id", "ignore_auto_number_generation", "send"), NOTHING, check_create_invoice),
    "ZohoBooks_add_invoice_document": (
        NOTHING, ORG_ONLY, obj("invoice_id", "document_id"), check_invoice_document),
    "ZohoBooks_upload_invoice_document": (
        NOTHING, obj("organization_id", "attachment"), obj("invoice_id", "document_id"), check_invoice_document),
    "ZohoBooks_add_invoice_comment": (
        obj("description"), ORG_ONLY, obj("invoice_id"), check_invoice_comment),
    "ZohoBooks_create_bill": (
        obj(*BILL_FIELDS, line_items=[BILL_LINE], documents=[BILL_DOCUMENT]), ORG_ONLY, NOTHING, check_create_bill),
    "ZohoBooks_update_bill": (
        obj(*BILL_FIELDS, line_items=[BILL_LINE]), ORG_ONLY, obj("bill_id"), check_update_bill),
    "ZohoBooks_add_bill_comment": (
        obj("description"), ORG_ONLY, obj("bill_id"), check_bill_comment),
}


def _fit(value, spec, where):
    """`value` checked against `spec`, with every dict key lower-cased; raises Deny."""
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
    out = {}
    for key, v in value.items():
        low = str(key).lower()
        if low in out:
            raise Deny(f"{P}{where} has {key!r} twice (keys are compared regardless of case).")
        if low not in spec:
            raise Deny(f"{P}{where}.{key} isn't allowed here. Allowed: {', '.join(sorted(spec)) or 'nothing'}.")
        out[low] = _fit(v, spec[low], f"{where}.{key}")
    return out


# --- no bank details, no VAT ---------------------------------------------------------
ISO_DATE = re.compile(r"(?<![0-9-])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9-])")
DIGIT_RULES = (re.compile(r"\b\d{2}[- ]\d{2}[- ]\d{2}\b"),  # a sort code
               re.compile(r"(?<!\d)\d{8}(?!\d)"))  # an account number
TEXT_RULES = (re.compile(r"GB\d{2}\s?[A-Z]{4}", re.I),  # a GB IBAN
              re.compile(r"\b(?:sort[\s-]*code|account[\s-]*(?:number|no)|acc[\s.]*no|a/c[\s.]*no|iban|swift|bic)\b",
                         re.I),
              re.compile(r"\bvat\b", re.I))  # Alma Consort Ltd is not VAT-registered
OWN_PATTERN = {"invoice_number": INVOICE_NUMBER, "bill_number": BILL_NUMBER}


def _scan(value, key, where):
    """Deny bank details or VAT in any string or number of a write call."""
    if isinstance(value, dict):
        for k, v in value.items():
            _scan(v, k, f"{where}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _scan(v, key, f"{where}[{i}]")
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        text = str(value)
        rules = TEXT_RULES
        own = OWN_PATTERN.get(key)
        if not (own and isinstance(value, str) and own.fullmatch(value)):
            rules = DIGIT_RULES + rules
        bare = ISO_DATE.sub(" ", text)
        for rule in rules:
            if rule.search(bare):
                raise Deny(f"{P}{where} looks like bank details or mentions VAT. Claude never puts bank details "
                           "in Books, and Alma Consort Ltd is not VAT-registered.")
    elif value is not None and not isinstance(value, bool):
        raise Deny(f"{P}{where} has an unexpected value.")


def check_write(name, tool_input):
    body_spec, query_spec, path_spec, check = WRITE_TOOLS[name]
    if tool_input is None:
        tool_input = {}
    ti = _fit(tool_input, {"body": body_spec, "query_params": query_spec, "path_variables": path_spec}, "tool_input")
    body, query, path = ti.get("body", {}), ti.get("query_params", {}), ti.get("path_variables", {})
    check(body, query, path)
    _scan(ti, None, "tool_input")


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
            "it never emails, reminds, deletes, voids, records payments or matches bank transactions.")


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
