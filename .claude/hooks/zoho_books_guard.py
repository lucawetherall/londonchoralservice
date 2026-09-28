#!/usr/bin/env python3
"""PreToolUse guard for the Zoho Books MCP servers (matcher mcp__zoho-books.*).

It allows only the exact tool names in READ_ALLOW (the tools the servers mark
read-only) and WRITE_CHECKS (write tools the owner approved on 28 Sep 2026,
each with a check on its arguments); every other tool, including any the
servers add later, is denied. Claude never emails, reminds, deletes, voids,
records a payment or matches a bank transaction in Books: those stay the
owner's job. Invoices are created as drafts only (`send` is never on) and
carry the DDMM booking ref as their number. This holds whatever tools the
Zoho Books MCP console exposes, and it fails closed: any error, or a
tool_input of the wrong shape, denies the call.
Design: docs/superpowers/specs/2026-09-28-zoho-books-design.md
"""
import json
import re
import sys

# Exact names of the tools the Zoho Books servers mark read-only (tools/list,
# readOnlyHint), taken on 28 Sep 2026 plus the bill tools listed after the owner
# enabled Bills that day, minus get_bank_statement_import_encryption_key,
# generate_invoice_payment_link and convert_purchase_order_to_bill (labelled
# read-only, but it creates a bill). Unknown or new tools are denied.
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
    "ZohoBooks_get_contact_bank_account",
    "ZohoBooks_get_contact_by_reference",
    "ZohoBooks_get_contact_card",
    "ZohoBooks_get_contact_card_count",
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
    "ZohoBooks_get_invoice_payment_qr",
    "ZohoBooks_get_invoice_payment_qr_status",
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
    "ZohoBooks_list_all_contact_bank_accounts",
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
    "ZohoBooks_list_contact_bank_accounts",
    "ZohoBooks_list_contact_cards",
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
INVOICE_NUMBER = re.compile(r"\d{4}[A-Z]?")  # the DDMM booking ref, e.g. 2111 or 2111B
OFF = (None, False, 0, "", "false", "False", "0")
BILL_PAYMENT_KEYS_OK = {"payment_terms", "payment_terms_label"}


def _off(v):
    """True when a flag or field is absent, false or empty."""
    if isinstance(v, (list, dict)):
        return not v
    return any(v is o or (type(v) is type(o) and v == o) for o in OFF)


def _on(v):
    """True for an explicit yes: True, 1, "true", "True", "1"."""
    return v is True or (type(v) is int and v == 1) or (isinstance(v, str) and v.strip() in ("true", "True", "1"))


def _present(v):
    return v is not None and not (isinstance(v, str) and not v.strip()) and v != [] and v != {}


def _keys(obj):
    """Every dict key at any depth, with its value."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def _sections(tool_input):
    """(body, query_params, path_variables), each a dict; anything else raises (and so denies)."""
    if tool_input is None:
        tool_input = {}
    if not isinstance(tool_input, dict):
        raise ValueError("tool_input is not an object")
    out = []
    for key in ("body", "query_params", "path_variables"):
        sec = tool_input.get(key)
        if sec is None:
            sec = {}
        if not isinstance(sec, dict):
            raise ValueError(f"{key} is not an object")
        out.append(sec)
    return out


def check_contact(tool_input, create):
    body, query, _ = _sections(tool_input)
    if "contact_type" in body and body["contact_type"] not in ("customer", "vendor"):
        return P + "contact_type must be customer or vendor."
    for sec in (body, query):
        for k, v in _keys(sec):
            lk = k.lower()
            if "portal" in lk and not _off(v):
                return P + "no client portal on contacts (the owner turns it on in Books)."
            if "opening_balance" in lk:
                return P + "no opening_balances on contacts."
            if "bank" in lk or "card" in lk or "credit_limit" in lk:
                return P + f"no bank, card or credit-limit fields on contacts ({k})."
    return None


def check_invoice(tool_input, create):
    body, query, path = _sections(tool_input)
    for where, sec in (("body", body), ("query_params", query)):
        if not _off(sec.get("send")):
            return P + f"invoices are saved as drafts: `send` must be absent or false ({where}). The owner sends from Books."
        if not _off(sec.get("batch_payments")):
            return P + f"no batch_payments on invoices ({where})."
    if create or body.get("invoice_number") is not None:
        num = body.get("invoice_number")
        if not isinstance(num, str) or not INVOICE_NUMBER.fullmatch(num):
            return P + "invoice_number must be the booking's DDMM ref (e.g. 2111 or 2111B)."
    if create and not (_on(query.get("ignore_auto_number_generation"))
                       or _on(body.get("ignore_auto_number_generation"))):
        return P + "set ignore_auto_number_generation=true so Books keeps the DDMM invoice number."
    opts = body.get("payment_options")
    if opts is not None:
        if not isinstance(opts, dict):
            return P + "payment_options must be an object."
        if not _off(opts.get("payment_gateways")):
            return P + "no online payment gateways on invoices."
    if create and not _present(body.get("customer_id")):
        return P + "create_invoice needs customer_id."
    if not create and not _present(path.get("invoice_id")):
        return P + "update_invoice needs invoice_id."
    return None


def check_invoice_document(tool_input, create):
    _, _, path = _sections(tool_input)
    if not _present(path.get("invoice_id")):
        return P + "an invoice document needs invoice_id."
    return None


def check_invoice_comment(tool_input, create):
    body, _, _ = _sections(tool_input)
    if not _off(body.get("show_comment_to_clients")):
        return P + "invoice comments are internal: show_comment_to_clients must be absent or false."
    return None


def check_bill(tool_input, create):
    body, query, _ = _sections(tool_input)
    if create:
        for key in ("vendor_id", "bill_number"):
            if not _present(body.get(key)):
                return P + f"create_bill needs {key}."
    for key in ("approvers", "purchaseorder_ids"):
        if not _off(body.get(key)):
            return P + f"no {key} on bills (the owner approves bills in Books)."
    for sec in (body, query):
        for k, _v in _keys(sec):
            if "payment" in k.lower() and k not in BILL_PAYMENT_KEYS_OK:
                return P + f"no payment fields on bills ({k}); the owner records payments in Books."
    return None


def no_check(tool_input, create):
    _sections(tool_input)  # still fail closed on a malformed shape
    return None


# Write tools the owner approved on 28 Sep 2026, each with its argument check
# (returns None to allow, or the deny reason). See the design's "Approved write tools".
WRITE_CHECKS = {
    "ZohoBooks_create_contact": lambda ti: check_contact(ti, create=True),
    "ZohoBooks_update_contact": lambda ti: check_contact(ti, create=False),
    "ZohoBooks_create_invoice": lambda ti: check_invoice(ti, create=True),
    "ZohoBooks_update_invoice": lambda ti: check_invoice(ti, create=False),
    "ZohoBooks_add_invoice_document": lambda ti: check_invoice_document(ti, create=False),
    "ZohoBooks_upload_invoice_document": lambda ti: check_invoice_document(ti, create=False),
    "ZohoBooks_add_invoice_comment": lambda ti: check_invoice_comment(ti, create=False),
    "ZohoBooks_create_bill": lambda ti: check_bill(ti, create=True),
    "ZohoBooks_update_bill": lambda ti: check_bill(ti, create=False),
    "ZohoBooks_add_bill_comment": lambda ti: no_check(ti, create=False),
}


def decide(tool, tool_input):
    name = tool.split("__")[-1]
    if name in READ_ALLOW:
        return None  # allowed; normal permission rules apply
    check = WRITE_CHECKS.get(name)
    if check is not None:
        return check(tool_input)
    return (f"{P}{name} isn't allowed. Claude may read Books and make drafts, contacts and bills; "
            "it never emails, reminds, deletes, voids, records payments or matches bank transactions.")


def main():
    try:
        event = json.load(sys.stdin)
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
