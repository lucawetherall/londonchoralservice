#!/usr/bin/env python3
"""PreToolUse guard for the Zoho Books MCP servers (matcher mcp__zoho-books.*).

\1It allows only the exact tool names in READ_ALLOW (the tools the servers
mark read-only) and WRITE_ALLOW (tools the owner has approved by name); every
other tool, including any the servers add later, is denied. Claude never sends, deletes or voids an invoice
through these servers: that stays the owner's job in Zoho Books until they
approve specific write tools by name below. This holds whatever tools the
Zoho Books MCP console exposes, and it fails closed: any error denies the
call.
"""
import json
import sys

# Exact names of the tools the Zoho Books servers mark read-only (tools/list,
# readOnlyHint), taken on 28 Sep 2026, minus get_bank_statement_import_encryption_key
# and generate_invoice_payment_link. Unknown or new tools are denied.
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

# Add exact tool names here only after the owner approves them (see
# docs/superpowers/specs/*zoho-books*).
WRITE_ALLOW = set()


def decide(tool, tool_input):
    name = tool.split("__")[-1]
    if name in READ_ALLOW or name in WRITE_ALLOW:
        return None  # allowed; normal permission rules apply
    return (f"Zoho Books guard: {name} isn't allowed. Claude has read-only access to "
            "Zoho Books until the owner approves specific write tools.")


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
