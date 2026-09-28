#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_books_guard.py (PreToolUse). Stdlib only."""
import importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "zoho_books_guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

SERVERS = ("zoho-books", "zoho-books-invoices")


NON_READ_ONLY = [ "ZohoBooks_add_bank_reconciliation_attachment", "ZohoBooks_add_contact_address", "ZohoBooks_add_contact_attachment", "ZohoBooks_add_contact_bank_account", "ZohoBooks_add_contact_card", "ZohoBooks_add_contact_comment", "ZohoBooks_add_contact_tax_info", "ZohoBooks_add_invoice_comment", "ZohoBooks_add_invoice_digital_signature", "ZohoBooks_add_invoice_document", "ZohoBooks_add_invoice_online_payment_bank_account", "ZohoBooks_apply_credits_to_invoice", "ZohoBooks_apply_invoice_substatus", "ZohoBooks_apply_pricebook_to_invoice", "ZohoBooks_approve_contact_bank_account", "ZohoBooks_approve_invoice", "ZohoBooks_approve_invoices", "ZohoBooks_assign_contact_owner", "ZohoBooks_assign_owner_to_contacts", "ZohoBooks_bulk_invoice_reminder", "ZohoBooks_bulk_mark_item_masters_active", "ZohoBooks_bulk_mark_item_masters_inactive", "ZohoBooks_bulk_mark_item_variants_active", "ZohoBooks_bulk_mark_item_variants_inactive", "ZohoBooks_bulk_update_bank_account_rules", "ZohoBooks_cancel_einvoice_invoice", "ZohoBooks_cancel_invoice", "ZohoBooks_cancel_invoice_einvoice", "ZohoBooks_cancel_invoices_einvoice", "ZohoBooks_cancel_scheduled_invoice_email", "ZohoBooks_cancel_write_off_invoice", "ZohoBooks_categorize_as_credit_note_refunds", "ZohoBooks_categorize_as_vendor_credit_refunds", "ZohoBooks_categorize_as_vendor_payment_refund", "ZohoBooks_categorize_bank_transaction", "ZohoBooks_categorize_bank_transaction_as_customer_payment", "ZohoBooks_categorize_bank_transaction_as_expense", "ZohoBooks_categorize_bank_transaction_as_payment_refund", "ZohoBooks_categorize_bank_transaction_as_vendor_payment", "ZohoBooks_create_bank_account", "ZohoBooks_create_bank_account_match_filter", "ZohoBooks_create_bank_account_rule", "ZohoBooks_create_bank_reconciliation", "ZohoBooks_create_bank_transaction", "ZohoBooks_create_contact", "ZohoBooks_create_contact_person", "ZohoBooks_create_customer_payment", "ZohoBooks_create_customer_payment_refund", "ZohoBooks_create_employee", "ZohoBooks_create_expense", "ZohoBooks_create_invoice", "ZohoBooks_create_invoice_asynchronous_online_payment", "ZohoBooks_create_invoice_from_salesorder", "ZohoBooks_create_invoice_synchronous_online_payment", "ZohoBooks_create_invoices_from_estimates", "ZohoBooks_create_invoices_from_projects", "ZohoBooks_create_item", "ZohoBooks_create_item_master", "ZohoBooks_create_item_variant", "ZohoBooks_create_pricebook", "ZohoBooks_create_recurring_bill", "ZohoBooks_create_tax", "ZohoBooks_create_tax_authority", "ZohoBooks_create_tax_exemption", "ZohoBooks_create_tax_group", "ZohoBooks_decline_contact_bank_account", "ZohoBooks_delete_invoice", "ZohoBooks_delete_invoice_applied_credit", "ZohoBooks_delete_invoice_comment", "ZohoBooks_delete_invoice_document", "ZohoBooks_delete_invoice_einvoice_status", "ZohoBooks_delete_invoice_expense_receipt", "ZohoBooks_delete_invoice_line_item", "ZohoBooks_delete_invoice_payment", "ZohoBooks_delete_invoice_substatus", "ZohoBooks_delete_invoices", "ZohoBooks_delete_recurring_bill", "ZohoBooks_disable_contact_payment_reminder", "ZohoBooks_disable_contact_person_sms", "ZohoBooks_disable_contact_portal", "ZohoBooks_disable_invoice_payment_reminder", "ZohoBooks_email_contact", "ZohoBooks_email_contact_statement", "ZohoBooks_email_invoice", "ZohoBooks_email_invoices", "ZohoBooks_enable_contact_payment_reminder", "ZohoBooks_enable_contact_person_sms", "ZohoBooks_enable_contact_portal", "ZohoBooks_enable_invoice_payment_reminder", "ZohoBooks_exclude_bank_transaction", "ZohoBooks_fetch_invoice_einvoice", "ZohoBooks_finalize_invoice_approval", "ZohoBooks_force_pay_invoice", "ZohoBooks_generate_invoice_payment_link", "ZohoBooks_get_bank_statement_import_encryption_key", "ZohoBooks_import_bank_statements", "ZohoBooks_invite_contact_person_to_portal", "ZohoBooks_mail_invoice_pdf", "ZohoBooks_map_invoice_with_salesorder", "ZohoBooks_mark_bank_account_active", "ZohoBooks_mark_bank_account_inactive", "ZohoBooks_mark_contact_active", "ZohoBooks_mark_contact_address_as_billing", "ZohoBooks_mark_contact_address_as_shipping", "ZohoBooks_mark_contact_inactive", "ZohoBooks_mark_contact_person_primary", "ZohoBooks_mark_contacts_for_1099_tracking", "ZohoBooks_mark_invoice_draft", "ZohoBooks_mark_invoice_einvoice_cancelled", "ZohoBooks_mark_invoice_einvoice_pushed", "ZohoBooks_mark_invoice_ready_to_push", "ZohoBooks_mark_invoice_sent", "ZohoBooks_mark_invoice_void", "ZohoBooks_mark_invoices_sent", "ZohoBooks_mark_invoices_shipped", "ZohoBooks_mark_item_active", "ZohoBooks_mark_item_inactive", "ZohoBooks_mark_item_master_as_active", "ZohoBooks_mark_item_master_as_inactive", "ZohoBooks_mark_item_variant_as_active", "ZohoBooks_mark_item_variant_as_inactive", "ZohoBooks_mark_pricebook_active", "ZohoBooks_mark_pricebook_inactive", "ZohoBooks_match_bank_transaction", "ZohoBooks_merge_contact", "ZohoBooks_move_item_variant", "ZohoBooks_preview_invoice_coupons", "ZohoBooks_push_invoice_einvoice", "ZohoBooks_push_invoices_einvoice", "ZohoBooks_recall_invoice_einvoice_status", "ZohoBooks_reject_invoice", "ZohoBooks_remind_customer_for_invoice_payment", "ZohoBooks_reorder_bank_account_rules", "ZohoBooks_resend_contact_person_portal_invite", "ZohoBooks_restore_bank_transaction", "ZohoBooks_restore_contact_documents", "ZohoBooks_resume_recurring_bill", "ZohoBooks_save_bank_reconciliation_draft", "ZohoBooks_schedule_invoice_email", "ZohoBooks_send_contact_client_review_email", "ZohoBooks_send_contact_payment_method_email", "ZohoBooks_send_contact_sms", "ZohoBooks_send_contact_vendor_statement_email", "ZohoBooks_send_contacts_sms", "ZohoBooks_send_invoice_dunning_notifications", "ZohoBooks_send_invoice_retry_sms", "ZohoBooks_send_invoice_sms", "ZohoBooks_send_invoice_via_snail_mail", "ZohoBooks_skip_suggested_bank_account_rule", "ZohoBooks_stop_recurring_bill", "ZohoBooks_submit_invoice", "ZohoBooks_submit_invoices", "ZohoBooks_track_contact_1099", "ZohoBooks_uncategorize_bank_transaction", "ZohoBooks_ungroup_item_variants", "ZohoBooks_unmap_invoices_from_salesorders", "ZohoBooks_unmatch_bank_transaction", "ZohoBooks_unship_invoices", "ZohoBooks_untrack_contact_1099", "ZohoBooks_update_bank_account", "ZohoBooks_update_bank_account_match_filter", "ZohoBooks_update_bank_account_preferences", "ZohoBooks_update_bank_account_rule", "ZohoBooks_update_bank_reconciliation", "ZohoBooks_update_bank_transaction", "ZohoBooks_update_contact", "ZohoBooks_update_contact_address", "ZohoBooks_update_contact_bank_account", "ZohoBooks_update_contact_card", "ZohoBooks_update_contact_document", "ZohoBooks_update_contact_person", "ZohoBooks_update_contact_tags", "ZohoBooks_update_contact_tax_info", "ZohoBooks_update_contact_trn_status", "ZohoBooks_update_contact_using_custom_field", "ZohoBooks_update_custom_fields_in_customer_payment", "ZohoBooks_update_custom_fields_in_invoice", "ZohoBooks_update_custom_fields_in_item", "ZohoBooks_update_customer_payment", "ZohoBooks_update_customer_payment_refund", "ZohoBooks_update_customer_payment_using_custom_field", "ZohoBooks_update_expense", "ZohoBooks_update_expense_using_custom_field", "ZohoBooks_update_invoice", "ZohoBooks_update_invoice_advanced_tracking_details", "ZohoBooks_update_invoice_billing_address", "ZohoBooks_update_invoice_cfdi_status", "ZohoBooks_update_invoice_comment", "ZohoBooks_update_invoice_einvoice_payment_status", "ZohoBooks_update_invoice_metadata", "ZohoBooks_update_invoice_shipping_address", "ZohoBooks_update_invoice_template", "ZohoBooks_update_invoice_using_custom_field", "ZohoBooks_update_item", "ZohoBooks_update_item_master", "ZohoBooks_update_item_using_custom_field", "ZohoBooks_update_item_variant", "ZohoBooks_update_pricebook", "ZohoBooks_update_recurring_bill", "ZohoBooks_update_recurring_bill_using_custom_field", "ZohoBooks_update_tax", "ZohoBooks_update_tax_authority", "ZohoBooks_update_tax_exemption", "ZohoBooks_update_tax_group", "ZohoBooks_upload_invoice_digital_signature", "ZohoBooks_upload_invoice_document", "ZohoBooks_verify_contact_address_by_id", "ZohoBooks_verify_contact_bank_account", "ZohoBooks_verify_contact_einvoice", "ZohoBooks_void_invoices", "ZohoBooks_write_off_invoice", "ZohoBooks_write_off_invoices" ]


def raw(stdin, env=None):
    """Run the guard on raw stdin; its decision ("allow" when it prints nothing)."""
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True, env=env)
    assert p.returncode == 0, (p.returncode, p.stderr)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def decide(server, tool, tool_input=None, env=None):
    return raw(json.dumps({"tool_name": f"mcp__{server}__{tool}", "tool_input": tool_input or {}}), env)


def guard_module():
    spec = importlib.util.spec_from_file_location("zoho_books_guard", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hook_command():
    """The zoho-books guard command exactly as .claude/settings.json runs it."""
    with open(SETTINGS) as f:
        cfg = json.load(f)
    cmds = [h["command"] for entry in cfg["hooks"]["PreToolUse"] if entry["matcher"] == "mcp__zoho-books.*"
            for h in entry["hooks"]]
    assert len(cmds) == 1, cmds
    return cmds[0]


def test_read_only_tools_are_allowed_on_both_servers():
    for server in ("zoho-books", "zoho-books-invoices"):
        for name in ("ZohoBooks_list_invoices", "ZohoBooks_get_invoice", "ZohoBooks_list_contacts"):
            assert decide(server, name) == "allow", (server, name)
    assert decide("zoho-books", "ZohoBooks_list_bills") == "allow"


def test_bank_account_and_transaction_reads_are_denied():
    assert not [n for n in guard_module().READ_ALLOW if "bank_" in n]
    for server in SERVERS:
        for name in ("ZohoBooks_list_bank_transactions", "ZohoBooks_get_bank_transaction", "ZohoBooks_get_bank_account",
                     "ZohoBooks_list_bank_accounts", "ZohoBooks_get_matching_bank_transactions",
                     "ZohoBooks_list_bank_account_statements", "ZohoBooks_get_bank_reconciliation"):
            assert decide(server, name) == "deny", (server, name)
    for name in ("ZohoBooks_list_invoices", "ZohoBooks_get_invoice", "ZohoBooks_list_bills", "ZohoBooks_get_bill",
                 "ZohoBooks_list_contacts", "ZohoBooks_get_contact", "ZohoBooks_list_vendors"):
        assert name in guard_module().READ_ALLOW, name


def test_send_and_write_tools_are_denied():
    for name in ("ZohoBooks_email_invoice", "ZohoBooks_email_invoices", "ZohoBooks_schedule_invoice_email",
                 "ZohoBooks_delete_invoice",
                 "ZohoBooks_mark_invoice_void", "ZohoBooks_write_off_invoice",
                 "ZohoBooks_remind_customer_for_invoice_payment", "ZohoBooks_create_customer_payment",
                 "ZohoBooks_fetch_invoice_einvoice", "ZohoBooks_generate_invoice_payment_link",
                 "ZohoBooks_get_bank_statement_import_encryption_key", "ZohoBooks_add_contact_bank_account",
                 "ZohoBooks_categorize_bank_transaction", "ZohoBooks_send_contact_sms", "unknown_tool"):
        assert decide("zoho-books-invoices", name) == "deny", name


def test_every_non_read_only_tool_seen_on_28_sep_is_denied():
    # The write tools both servers listed on 28 Sep 2026 (tools/list without readOnlyHint),
    # except the ones the owner approved (checked by argument in the tests below).
    assert APPROVED_WRITES & set(NON_READ_ONLY)  # the exclusion is doing something
    assert "ZohoBooks_update_invoice" in NON_READ_ONLY  # ...and no longer covers invoice updates
    for name in NON_READ_ONLY:
        if name in APPROVED_WRITES:
            continue
        assert decide("zoho-books", name) == "deny", name


def test_payment_qr_and_contact_bank_or_card_reads_are_denied():
    removed = {"ZohoBooks_get_invoice_payment_qr", "ZohoBooks_get_invoice_payment_qr_status",
               "ZohoBooks_get_contact_bank_account", "ZohoBooks_list_contact_bank_accounts",
               "ZohoBooks_list_all_contact_bank_accounts", "ZohoBooks_get_contact_card",
               "ZohoBooks_list_contact_cards", "ZohoBooks_get_contact_card_count",
               "ZohoBooks_list_contact_autobill_recurring_invoices", "ZohoBooks_get_invoice_qr_code"}
    assert not removed & guard_module().READ_ALLOW
    for server in SERVERS:
        for name in removed:
            assert decide(server, name) == "deny", (server, name)


# --- owner-approved writes, checked by argument --------------------------------------

APPROVED_WRITES = {
    "ZohoBooks_create_contact", "ZohoBooks_update_contact",
    "ZohoBooks_create_invoice",
    "ZohoBooks_add_invoice_document", "ZohoBooks_upload_invoice_document",
    "ZohoBooks_add_invoice_comment", "ZohoBooks_mark_invoice_sent",
    "ZohoBooks_create_bill", "ZohoBooks_update_bill", "ZohoBooks_add_bill_comment",
    "ZohoBooks_create_item", "ZohoBooks_create_bank_account", "ZohoBooks_create_vendor_payment",
    "ZohoBooks_create_customer_payment",
}
STARLING = "1534218000000095168"
ORG = {"organization_id": "941014440"}
CONFIRMATION = "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/2111 - A Client/Booking Confirmation - A Client - 21 Nov 2026.docx"


def good_inputs():
    """One well-formed call per approved write tool."""
    contact = {"contact_name": "A Client", "company_name": "A Client Ltd", "contact_type": "customer",
               "contact_persons": [{"salutation": "Ms", "first_name": "A", "last_name": "Client",
                                    "email": "a@example.com", "phone": "020 7946 0958",
                                    "mobile": "07700 900123", "is_primary_contact": True}],
               "billing_address": {"attention": "A Client", "address": "1 High Street", "street2": "Flat 2",
                                   "city": "London", "state": "Greater London", "zip": "SW1A 1AA",
                                   "country": "United Kingdom"},
               "payment_terms": 7, "payment_terms_label": "Net 7", "notes": "Wedding enquiry, ref 2111"}
    invoice = {"customer_id": "460000000026049", "invoice_number": "2111", "date": "2026-09-28",
               "due_date": "2026-10-05", "payment_terms": 7, "payment_terms_label": "Net 7",
               "reference_number": "2111", "allow_partial_payments": True, "template_id": "460000000011111",
               "line_items": [{"item_id": "460000000099999", "name": "Small Choir",
                               "description": "Wedding, 21 Nov 2026", "rate": 1150, "quantity": 1,
                               "item_order": 1}],
               "notes": "Thank you for booking.", "terms": "Second instalment due 2026-10-21."}
    bill = {"vendor_id": "460000000022222", "bill_number": "S-17", "date": "2026-09-28",
            "due_date": "2026-10-12", "reference_number": "2111", "notes": "Booking 2111",
            "payment_terms": 14, "payment_terms_label": "Net 14",
            "line_items": [{"name": "Wedding, 2111", "description": "Tenor", "rate": 180, "quantity": 1,
                            "account_id": "1534218000000034003", "item_order": 1}]}
    return {
        "ZohoBooks_create_contact": {"body": contact, "query_params": ORG},
        "ZohoBooks_update_contact": {"body": {"contact_name": "A Client", "company_name": "A Client Ltd"},
                                     "query_params": ORG, "path_variables": {"contact_id": "333"}},
        "ZohoBooks_create_invoice": {"body": invoice,
                                     "query_params": dict(ORG, ignore_auto_number_generation=True, send=False)},
        "ZohoBooks_add_invoice_document": {"query_params": ORG,
                                           "path_variables": {"invoice_id": "444", "document_id": "555"}},
        "ZohoBooks_upload_invoice_document": {"query_params": dict(ORG, attachment=CONFIRMATION),
                                              "path_variables": {"invoice_id": "444", "document_id": "555"}},
        "ZohoBooks_mark_invoice_sent": {"query_params": ORG, "path_variables": {"invoice_id": "444"}},
        "ZohoBooks_add_invoice_comment": {"body": {"description": "Booking confirmation to attach"},
                                          "query_params": ORG, "path_variables": {"invoice_id": "444"}},
        "ZohoBooks_create_bill": {"body": dict(bill, documents=[{"document_id": "777", "file_name": "S-17.pdf"}]),
                                  "query_params": ORG},
        "ZohoBooks_update_bill": {"body": {"notes": "Booking 2111", "reference_number": "2111", "date": "2026-09-28",
                                           "due_date": "2026-10-12"},
                                  "query_params": ORG, "path_variables": {"bill_id": "666"}},
        "ZohoBooks_add_bill_comment": {"body": {"description": "Booking 2111"}, "query_params": ORG,
                                       "path_variables": {"bill_id": "666"}},
        "ZohoBooks_create_vendor_payment": {"body": {"vendor_id": "1534218000000100001", "amount": 100,
                                                     "date": "2026-09-28", "payment_mode": "Bank Transfer",
                                                     "paid_through_account_id": STARLING,
                                                     "description": "Starling transfer",
                                                     "bills": [{"bill_id": "1534218000000102002",
                                                                "amount_applied": 100}]},
                                            "query_params": ORG},
        "ZohoBooks_create_customer_payment": {"body": {"customer_id": "1534218000000100010", "date": "2026-09-27",
                                                       "amount": 575, "amount_applied": 575,
                                                       "invoice_id": "1534218000000100020",
                                                       "payment_mode": "banktransfer", "account_id": STARLING,
                                                       "reference_number": "2111",
                                                       "description": "Starling transfer, reference 2111",
                                                       "invoices": [{"invoice_id": "1534218000000100020",
                                                                     "amount_applied": 575}]},
                                              "query_params": ORG},
        "ZohoBooks_create_bank_account": {"body": {"account_name": "Starling Business", "account_type": "bank",
                                                   "currency_code": "GBP", "description": "Business account"},
                                          "query_params": ORG},
        "ZohoBooks_create_item": {"body": {"name": "Singing fee", "rate": 0, "description": "Singer's fee",
                                           "item_type": "purchases", "product_type": "service",
                                           "purchase_rate": "0", "purchase_description": "Singer's fee"},
                                  "query_params": ORG},
    }


def with_(tool, section, **changes):
    """The good input for `tool`, with keys in one section changed (None deletes the key)."""
    ti = json.loads(json.dumps(good_inputs()[tool]))
    sec = ti.setdefault(section, {})
    for k, v in changes.items():
        if v is None:
            sec.pop(k, None)
        else:
            sec[k] = v
    return ti


def denied(tool, ti, server="zoho-books"):
    return decide(server, tool, ti) == "deny"


def test_approved_writes_with_good_arguments_are_allowed_on_both_servers():
    assert set(good_inputs()) == APPROVED_WRITES
    assert set(guard_module().WRITE_TOOLS) == APPROVED_WRITES
    for server in SERVERS:
        for name, ti in good_inputs().items():
            assert decide(server, name, ti) == "allow", (server, name)


def test_minimal_good_calls_are_allowed():
    for tool, ti in (
            ("ZohoBooks_create_contact", {"body": {"contact_name": "A", "contact_type": "vendor"}, "query_params": ORG}),
            ("ZohoBooks_create_invoice", {"body": {"customer_id": "1", "invoice_number": "2111B"},
                                          "query_params": dict(ORG, ignore_auto_number_generation="true")}),
            ("ZohoBooks_create_bill", {"body": {"vendor_id": "1", "bill_number": "S1", "line_items": [{"rate": 100}]},
                                       "query_params": ORG}),
            ("ZohoBooks_update_bill", {"body": {"notes": "Booking 2111"}, "query_params": ORG,
                                       "path_variables": {"bill_id": "1"}}),
            ("ZohoBooks_add_invoice_document", {"path_variables": {"invoice_id": "1"}})):
        assert decide("zoho-books", tool, ti) == "allow", tool


# --- H1: no invoice updates ----------------------------------------------------------

def test_update_invoice_is_denied_even_with_good_arguments():
    ti = {"body": good_inputs()["ZohoBooks_create_invoice"]["body"], "query_params": ORG,
          "path_variables": {"invoice_id": "444"}}
    for server in SERVERS:
        assert decide(server, "ZohoBooks_update_invoice", ti) == "deny", server
        assert decide(server, "ZohoBooks_update_invoice", {}) == "deny", server


# --- H2: contact updates change names only -------------------------------------------

def test_update_contact_may_only_change_names():
    T = "ZohoBooks_update_contact"
    assert decide("zoho-books", T, with_(T, "body", company_name=None)) == "allow"
    for key, val in (("contact_persons", [{"contact_person_id": "1", "email": "attacker@evil.test"}]),
                     ("contact_persons", [{"first_name": "A"}]),
                     ("email", "attacker@evil.test"), ("phone", "020 7946 0958"), ("mobile", "07700 900123"),
                     ("notes", "x"), ("billing_address", {"city": "London"}),
                     ("payment_terms", 7), ("is_portal_enabled", False), ("custom_fields", [])):
        assert denied(T, with_(T, "body", **{key: val})), key


def test_update_contact_needs_contact_id_in_path():
    T = "ZohoBooks_update_contact"
    assert denied(T, with_(T, "path_variables", contact_id=None))
    assert denied(T, with_(T, "path_variables", contact_id=""))
    ti = with_(T, "path_variables", contact_id=None)
    ti["query_params"]["contact_id"] = "333"
    assert denied(T, ti)
    assert denied(T, with_(T, "path_variables", enable_portal="true"))


# --- H3: strict allowlists -----------------------------------------------------------

def test_tool_input_top_level_keys_are_restricted():
    T = "ZohoBooks_create_invoice"
    for extra in ({"send": True}, {"Body": {"send": True}}, {"attachment": "x"}, {"BODY": {}}):
        ti = dict(good_inputs()[T], **extra)
        assert denied(T, ti), extra


def test_unlisted_keys_are_denied_in_every_section():
    cases = {
        "ZohoBooks_create_contact": [
            ("body", "is_portal_enabled", False), ("body", "credit_limit", 500), ("body", "iban", "x"),
            ("body", "account_number", "1"), ("body", "ach", {"routing_number": "1"}),
            ("body", "custom_fields", [{"label": "Payee", "value": "x"}]), ("body", "settings", {"Portal": {"on": True}}),
            ("body", "payment_reminder_enabled", True), ("body", "default_templates", {"invoice_email_template_id": "1"}),
            ("body", "opening_balances", []), ("body", "contact_number", "1"), ("body", "currency_id", "1"),
            ("body", "shipping_address", {"city": "x"}),
            ("query_params", "send", False), ("path_variables", "contact_id", "1")],
        "ZohoBooks_create_invoice": [
            ("body", "send", False), ("body", "status", "sent"), ("body", "payments", [{"amount": "650"}]),
            ("body", "batch_payments", [{"amount": "650"}]), ("body", "batchPayments", [{"amount": "650"}]),
            ("body", "payment_options", {"payment_gateways": []}), ("body", "custom_body", "x"),
            ("body", "custom_subject", "x"), ("body", "recurring_invoice_id", "5"),
            ("body", "invoiced_estimate_id", "5"), ("body", "contact_persons", ["1"]),
            ("body", "ignore_auto_number_generation", True), ("body", "JSONString", "{}"),
            ("body", "discount", 10), ("body", "adjustment", 1),
            ("query_params", "is_quick_create", True), ("query_params", "batch_payments", True),
            ("query_params", "invoice_number", "INV-999"), ("query_params", "JSONString", "{}"),
            ("query_params", "payment_options", "{}"), ("path_variables", "send", "true"),
            ("path_variables", "invoice_id", "1")],
        "ZohoBooks_add_invoice_document": [
            ("query_params", "attachment", "/tmp/x.pdf"), ("query_params", "doc", "x"),
            ("body", "send", False), ("path_variables", "x", "1")],
        "ZohoBooks_upload_invoice_document": [
            ("query_params", "doc", "x"), ("body", "document_id", "1"), ("path_variables", "x", "1")],
        "ZohoBooks_add_invoice_comment": [
            ("body", "payment_expected_date", "2026-10-01"), ("query_params", "show_comment_to_clients", False),
            ("path_variables", "show_comment_to_clients", "false")],
        "ZohoBooks_create_bill": [
            ("body", "paid_through_account_id", "3"), ("body", "is_paid", True), ("body", "vendor_credits", []),
            ("body", "apply_vendor_credits", True), ("body", "Payment_Made", 1), ("body", "status", "paid"),
            ("body", "approvers", [{"approver_id": "1"}]), ("body", "purchaseorder_ids", ["9"]),
            ("body", "recurring_bill_id", "4"), ("body", "terms", "x"), ("body", "custom_fields", []),
            ("query_params", "attachment", "/etc/passwd"), ("query_params", "approvers", "[1]"),
            ("path_variables", "bill_id", "1")],
        "ZohoBooks_update_bill": [
            ("body", "documents", [{"document_id": "1"}]), ("body", "is_paid", True),
            ("body", "vendor_id", "460000000022222"), ("body", "line_items", []),
            ("body", "line_items", [{"name": "x", "rate": 1}]), ("body", "bill_number", "S-18"),
            ("body", "payment_terms", 14), ("body", "payment_terms_label", "Net 14"),
            ("query_params", "attachment", "x"), ("path_variables", "vendor_id", "1")],
        "ZohoBooks_add_bill_comment": [
            ("body", "show_comment_to_clients", True), ("body", "send", True), ("query_params", "send", True),
            ("path_variables", "invoice_id", "1")],
    }
    for tool, rows in cases.items():
        for section, key, val in rows:
            for server in SERVERS:
                assert denied(tool, with_(tool, section, **{key: val}), server), (server, tool, section, key)


def test_unlisted_nested_keys_are_denied():
    C, I, B = "ZohoBooks_create_contact", "ZohoBooks_create_invoice", "ZohoBooks_create_bill"
    for person in ({"first_name": "A", "enable_portal": True}, {"first_name": "A", "contact_person_id": "1"},
                   {"communication_preference": {"is_sms_enabled": True, "is_whatsapp_enabled": True}},
                   {"first_name": "A", "skype": "x"}, {"first_name": "A", "bank_sort_code": "x"}):
        assert denied(C, with_(C, "body", contact_persons=[person])), person
    for addr in ({"city": "London", "phone": "1"}, {"city": "London", "fax": "1"}, {"state_code": "LDN"}):
        assert denied(C, with_(C, "body", billing_address=addr)), addr
    for item in ({"name": "x", "rate": 1, "tax_id": "77"}, {"name": "x", "bill_id": "1"},
                 {"name": "x", "discount": 5}, {"name": "x", "account_id": "1"}, {"name": "x", "tags": []}):
        assert denied(I, with_(I, "body", line_items=[item])), item
    for item in ({"rate": 1, "customer_id": "7", "is_billable": True}, {"rate": 1, "approvers": [1]},
                 {"rate": 1, "item_id": "1"}, {"rate": 1, "tax_id": "1"}, {"rate": 1, "purchaseorder_item_id": "1"}):
        assert denied(B, with_(B, "body", line_items=[item])), item
    assert denied(B, with_(B, "body", documents=[{"document_id": "1", "url": "http://x"}]))


def test_values_must_have_the_listed_shape():
    C, I, B = "ZohoBooks_create_contact", "ZohoBooks_create_invoice", "ZohoBooks_create_bill"
    assert denied(I, with_(I, "body", customer_id={"x": 1}))
    assert denied(I, with_(I, "body", notes=["x"]))
    assert denied(I, with_(I, "body", line_items={"name": "x"}))
    assert denied(I, with_(I, "body", line_items=["x"]))
    assert denied(C, with_(C, "body", billing_address="1 High Street"))
    assert denied(C, with_(C, "body", contact_persons={"first_name": "A"}))
    assert denied(B, with_(B, "body", documents=["777"]))


def test_keys_must_be_exactly_lower_case():
    I, C, U = "ZohoBooks_create_invoice", "ZohoBooks_create_contact", "ZohoBooks_update_contact"
    # an upper-case letter anywhere in a key is denied, whatever the value and at any depth
    assert denied(I, with_(I, "query_params", send=None, Send=False))
    assert denied(I, with_(I, "query_params", Send=False))  # beside send=False
    assert denied(I, with_(I, "query_params", send=None, SEND="false"))
    assert denied(I, with_(I, "query_params", ignore_auto_number_generation=None,
                           IGNORE_AUTO_NUMBER_GENERATION=True))
    assert denied(I, with_(I, "body", customer_id=None, Customer_ID="1"))
    assert denied(I, with_(I, "body", Send=True))
    assert denied(I, with_(I, "body", line_items=[{"Name": "Choir", "rate": 1}]))
    assert denied(C, with_(C, "body", contact_type=None, Contact_Type="vendor"))
    assert denied(C, with_(C, "body", billing_address={"City": "London"}))
    assert denied(U, with_(U, "path_variables", contact_id=None, Contact_ID="333"))
    ti = good_inputs()[U]
    assert denied(U, {"Body": ti["body"], "query_params": ORG, "path_variables": ti["path_variables"]})
    assert denied(U, {"body": ti["body"], "query_params": ORG, "PATH_VARIABLES": ti["path_variables"]})
    # a Kelvin sign lower-cases to k; it is still not the key "k"
    assert denied(I, with_(I, "body", line_items=[{"name": "x", "ran\u212a": 1}]))


def test_duplicate_json_keys_are_denied():
    tool = "mcp__zoho-books-invoices__ZohoBooks_create_invoice"
    base = ('{"tool_name":"%s","tool_input":{"body":{"customer_id":"1","invoice_number":"2111"},'
            '"query_params":{"organization_id":"1","ignore_auto_number_generation":true,%s}}}')
    assert raw(base % (tool, '"send":false')) == "allow"
    assert raw(base % (tool, '"send":true,"send":false')) == "deny"
    assert raw(base % (tool, '"send":false,"send":false')) == "deny"


def test_contact_type_is_required_and_customer_or_vendor():
    C = "ZohoBooks_create_contact"
    for v in (None, "employee", "Customer", "", True, ["customer"]):
        assert denied(C, with_(C, "body", contact_type=v)), v
    assert decide("zoho-books", C, with_(C, "body", contact_type="vendor")) == "allow"


def test_invoice_send_must_be_absent_or_false():
    I = "ZohoBooks_create_invoice"
    for v in (True, "true", "True", "TRUE", "1", 1, 0, 0.0, 1.0, "yes", " false", "", []):
        assert denied(I, with_(I, "query_params", send=v), "zoho-books-invoices"), v
    for v in (False, "false", None):
        ti = with_(I, "query_params", send=v)
        assert decide("zoho-books-invoices", I, ti) == "allow", v


def test_invoice_needs_ignore_auto_number_generation_true_in_query():
    I = "ZohoBooks_create_invoice"
    for v in (None, False, "false", "0", 1, "1", "yes"):
        assert denied(I, with_(I, "query_params", ignore_auto_number_generation=v)), v
    assert decide("zoho-books", I, with_(I, "query_params", ignore_auto_number_generation="true")) == "allow"


def test_invoice_number_must_be_a_ddmm_ref():
    I = "ZohoBooks_create_invoice"
    for bad in ("INV-2111", "211", "21111", "2111b", "2111AB", "2111\n", 2111, "٢١١١", None, ""):
        assert denied(I, with_(I, "body", invoice_number=bad)), bad
    assert decide("zoho-books", I, with_(I, "body", invoice_number="2111B")) == "allow"


def test_invoice_needs_customer_id():
    I = "ZohoBooks_create_invoice"
    for v in (None, "", " "):
        assert denied(I, with_(I, "body", customer_id=v)), v


def test_invoice_documents_need_invoice_id():
    for tool in ("ZohoBooks_add_invoice_document", "ZohoBooks_upload_invoice_document"):
        assert denied(tool, with_(tool, "path_variables", invoice_id=None)), tool
        ti = with_(tool, "path_variables", invoice_id=None)
        ti["query_params"]["invoice_id"] = "444"
        assert denied(tool, ti), tool


def test_invoice_comment_is_internal_and_needs_invoice_id():
    T = "ZohoBooks_add_invoice_comment"
    # show_comment_to_clients is denied whatever its value: only its absence is allowed
    for v in (True, False, "true", "false", "yes", 0):
        assert denied(T, with_(T, "body", show_comment_to_clients=v), "zoho-books-invoices"), v
    assert denied(T, with_(T, "path_variables", invoice_id=None))
    assert denied(T, {"body": {"description": "x"}})


def test_bill_create_needs_vendor_and_bill_number():
    B = "ZohoBooks_create_bill"
    for key in ("vendor_id", "bill_number"):
        for v in (None, ""):
            assert denied(B, with_(B, "body", **{key: v})), (key, v)


def test_bill_update_needs_bill_id_and_changes_notes_dates_and_reference_only():
    U = "ZohoBooks_update_bill"
    assert denied(U, with_(U, "path_variables", bill_id=None))
    assert set(guard_module().WRITE_TOOLS[U][0]) == {"notes", "due_date", "date", "reference_number"}
    for body in ({"notes": "x"}, {"due_date": "2026-10-12"}, {"date": "2026-09-28"}, {"reference_number": "2111"}):
        ti = {"body": body, "query_params": ORG, "path_variables": {"bill_id": "1"}}
        assert decide("zoho-books", U, ti) == "allow", body
    for key, val in (("vendor_id", "1"), ("line_items", []), ("line_items", [{"rate": 1}]), ("bill_number", "S-1"),
                     ("payment_terms", 7), ("documents", []), ("account_id", "1")):
        assert denied(U, with_(U, "body", **{key: val})), key


def test_bill_attachment_is_only_a_saved_singer_pdf():
    B = "ZohoBooks_create_bill"
    home = tempfile.mkdtemp()
    os.makedirs(os.path.join(home, "lcs-private", "singer-invoices"))
    os.makedirs(os.path.join(home, "lcs-private", "invoices"))
    env = dict(os.environ, HOME=home)
    ok = "~/lcs-private/singer-invoices/1790614912727141700.pdf"
    def run(att):
        return decide("zoho-books", B, with_(B, "query_params", attachment=att), env=env)
    assert run(ok) == "allow"
    assert run(os.path.join(home, "lcs-private", "singer-invoices", "1790614912727141700.pdf")) == "allow"
    for bad in ("~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/2111.pdf", "~/lcs-private/singer-invoices/x.docx",
                "~/lcs-private/singer-invoices/../invoices/a.pdf", "~/lcs-private/singer-invoices/a b.pdf",
                "~/lcs-private/singer-invoices/sub/a.pdf", "https://example.com/a.pdf", "~/Desktop/a.pdf"):
        assert run(bad) == "deny", bad
    # the long digit run is exempt only as that file name, never in bill text
    assert decide("zoho-books", B, with_(B, "body", notes="1790614912727141700"), env=env) == "deny"


def test_bill_lines_may_only_use_the_singer_fees_account():
    B = "ZohoBooks_create_bill"
    line = {"name": "Singing fee", "rate": 100, "quantity": 1}
    assert not denied(B, with_(B, "body", line_items=[line]))
    assert not denied(B, with_(B, "body", line_items=[dict(line, account_id="1534218000000034003")]))
    assert denied(B, with_(B, "body", line_items=[dict(line, account_id="1534218000000000373")]))


def test_vendor_payment_is_one_bill_in_full_through_starling():
    V = "ZohoBooks_create_vendor_payment"
    bill = {"bill_id": "1534218000000102002", "amount_applied": 100}
    assert denied(V, with_(V, "body", paid_through_account_id="1534218000000117002"))
    assert denied(V, with_(V, "body", paid_through_account_id=None))
    assert denied(V, with_(V, "body", payment_mode="Cash"))
    assert not denied(V, with_(V, "body", payment_mode=None))
    assert denied(V, with_(V, "body", amount=90))
    assert denied(V, with_(V, "body", amount=0, bills=[dict(bill, amount_applied=0)]))
    assert denied(V, with_(V, "body", amount=20000, bills=[dict(bill, amount_applied=20000)]))
    assert denied(V, with_(V, "body", amount="100"))
    assert denied(V, with_(V, "body", bills=[]))
    assert denied(V, with_(V, "body", bills=[bill, bill]))
    assert denied(V, with_(V, "body", vendor_id=None))
    for key in ("reference_number", "check_details", "exchange_rate", "location_id"):
        assert denied(V, with_(V, "body", **{key: "x"})), key
    assert denied(V, with_(V, "body", description="Paid to sort code 12-34-56"))
    for tool in ("ZohoBooks_email_vendor_payment", "ZohoBooks_create_customer_payment_refund",
                 "ZohoBooks_write_off_invoice", "ZohoBooks_apply_credits_to_invoice"):
        assert decide("zoho-books", tool, {"query_params": ORG}) == "deny", tool


def test_customer_payment_is_one_invoice_through_starling_with_no_thank_you_email():
    C = "ZohoBooks_create_customer_payment"
    inv = {"invoice_id": "1534218000000100020", "amount_applied": 575}
    assert denied(C, with_(C, "body", account_id="1534218000000117002"))
    assert denied(C, with_(C, "body", payment_mode="cash"))
    assert denied(C, with_(C, "body", amount=600))
    assert denied(C, with_(C, "body", amount_applied=500))
    assert denied(C, with_(C, "body", invoices=[dict(inv, amount_applied=500)]))
    assert denied(C, with_(C, "body", invoices=[dict(inv, invoice_id="999999999")]))
    assert denied(C, with_(C, "body", invoices=[inv, inv]))
    assert denied(C, with_(C, "body", amount=0, amount_applied=0, invoices=[dict(inv, amount_applied=0)]))
    assert denied(C, with_(C, "body", reference_number="INV 2111 Smith"))
    assert not denied(C, with_(C, "body", reference_number=None))
    for key in ("contact_persons", "bank_charges", "exchange_rate", "retainerinvoice_id", "custom_fields", "tags"):
        assert denied(C, with_(C, "body", **{key: "1"})), key
    assert denied(C, with_(C, "body", description="Paid from 12-34-56 12345678"))


def test_customer_payment_may_carry_the_owners_accepted_fee_as_bank_charges():
    """A shortfall the owner accepted as transfer fees (at most £25): amount is the money received, and the
    invoice is credited with amount + bank_charges."""
    C = "ZohoBooks_create_customer_payment"
    inv = {"invoice_id": "1534218000000100020"}

    def pay(amount, charges, applied=None, line=None):
        applied = round(amount + charges, 2) if applied is None else applied
        return with_(C, "body", amount=amount, bank_charges=charges, amount_applied=applied,
                     description="Starling transfer, matched to invoice 2111 (£12.40 bank charges accepted by the owner)",
                     invoices=[dict(inv, amount_applied=applied if line is None else line)])
    assert not denied(C, pay(462.6, 12.4))  # 475.00 applied
    assert not denied(C, pay(550, 25))  # at the cap
    assert not denied(C, pay(574.99, 0.01))
    assert denied(C, pay(549.99, 25.01))  # over the cap
    assert denied(C, pay(575, 0, applied=575))  # a charge of nothing is left out, never 0
    assert denied(C, pay(575, -5, applied=570))
    assert denied(C, with_(C, "body", bank_charges="12.40", amount=562.6, amount_applied=575,
                           invoices=[dict(inv, amount_applied=575)]))  # a string
    assert denied(C, with_(C, "body", bank_charges=True, amount=574, amount_applied=575,
                           invoices=[dict(inv, amount_applied=575)]))  # a bool
    assert denied(C, pay(462.6, 12.4, applied=462.6, line=462.6))  # the charge not applied to the invoice
    assert denied(C, pay(462.6, 12.4, applied=475, line=462.6))  # the two amount_applied disagree
    assert denied(C, pay(462.6, 12.4, applied=462.6, line=475))
    assert denied(C, pay(462.6, 12.4, applied=480, line=480))  # more than amount + charges
    assert denied(C, with_(C, "body", bank_charges=[12.4]))
    # without bank_charges, all three amounts must still be equal
    assert not denied(C, with_(C, "body"))
    assert denied(C, with_(C, "body", amount=562.6))
    assert denied(C, with_(C, "body", amount=562.6, amount_applied=575, invoices=[dict(inv, amount_applied=575)]))


def test_bank_account_is_a_named_gbp_bank_with_no_numbers():
    A = "ZohoBooks_create_bank_account"
    assert denied(A, with_(A, "body", account_type="credit_card"))
    assert denied(A, with_(A, "body", currency_code="EUR"))
    assert denied(A, with_(A, "body", account_name=None))
    for key in ("account_number", "routing_number", "account_code", "bank_name", "is_primary_account"):
        assert denied(A, with_(A, "body", **{key: "12345678"})), key
    assert denied(A, with_(A, "body", description="Sort code 12-34-56"))


def test_item_create_is_a_purchase_service_with_no_account_or_tax_keys():
    T = "ZohoBooks_create_item"
    assert denied(T, with_(T, "body", item_type=None))
    for bad in ("sales", "sales_and_purchases", "inventory"):
        assert denied(T, with_(T, "body", item_type=bad)), bad
    assert denied(T, with_(T, "body", product_type="goods"))
    assert not denied(T, with_(T, "body", product_type=None))
    assert denied(T, with_(T, "body", name=None))
    for key in ("account_id", "purchase_account_id", "inventory_account_id", "tax_id", "vendor_id", "sku"):
        assert denied(T, with_(T, "body", **{key: "460000000033333"})), key


def test_bill_comment_needs_bill_id():
    assert denied("ZohoBooks_add_bill_comment", with_("ZohoBooks_add_bill_comment", "path_variables", bill_id=None))
    assert denied("ZohoBooks_add_bill_comment", {"body": {"description": "x"}})


def test_malformed_sections_are_denied():
    assert denied("ZohoBooks_create_contact", {"body": ["not", "a", "dict"], "query_params": ORG})
    assert denied("ZohoBooks_create_invoice", {"body": "x", "query_params": ORG})
    assert denied("ZohoBooks_create_invoice", dict(good_inputs()["ZohoBooks_create_invoice"], query_params="send=true"))
    assert denied("ZohoBooks_add_invoice_comment",
                  dict(good_inputs()["ZohoBooks_add_invoice_comment"], path_variables=["444"]))
    assert raw(json.dumps({"tool_name": "mcp__zoho-books__ZohoBooks_add_bill_comment",
                           "tool_input": "not an object"})) == "deny"
    assert raw(json.dumps({"tool_name": "mcp__zoho-books__ZohoBooks_create_invoice", "tool_input": [1]})) == "deny"
    assert raw(json.dumps({"tool_name": "mcp__zoho-books__ZohoBooks_create_invoice", "tool_input": None})) == "deny"


# --- M1: no bank details and no VAT in any text --------------------------------------

BANK_TEXT = ("Pay to 12-34-56", "sort code 04 00 04", "Account 12345678", "Sort Code: 040004",
             "account number 1234", "Acc no 1234", "IBAN please", "GB29 NWBK 6016 1331 9268 19",
             "GB29NWBK60161331926819", "SWIFT: NWBKGB2L", "BIC NWBKGB2L", "our bic is x")
VAT_TEXT = ("Plus VAT", "VAT at 20%", "vat included", "Not VAT-registered", "(VAT)")
# The PR #147 re-review (28 Sep 2026): each of these got through the first scanner.
REVIEW_BANK_TEXT = (
    "Pay to 040004 a/c 1234 5678", "04/00/04 acct 1234 5678", "Account: 1234 5678", "Acct # 1234-5678",
    "Please transfer: 04\u201300\u201304, 1234\u20135678", "Ref 04000412345678", "Sortcode040004",
    "IBAN-free: DE89 3704 0044 0532 0130 00", "FR76 3000 6000 0112 3456 7890 189", "fr7630006000011234567890189",
    "GB 29 NWBK 6016 1331 9268 19", "gb29 nwbk 6016 1331 9268 19", "Pay to 04.00.04 12345678",
    "Payee s/c 04-00-04", "a/c 1", "acct no 1", "account no. 1", "Account # 1", "acc. no. 1",
    "\uff10\uff14-\uff10\uff10-\uff10\uff14",  # fullwidth 04-00-04
    "04\u200b00\u200b04", "1234\u00ad5678", "Bank: Monzo 04-00-04", "account 12 34 56 78",
    "code guichet 04 00 04 num\u00e9ro de compte 1234-5678", "12345678 999", "Pay 04000412345678901",
    "04.00.04", "04.00.04 12.34.56.78", "Nov 2026 040004", "21 Nov 2026 1234 5678", "11:00 040004",
)
REVIEW_VAT_TEXT = ("Plus Value Added Tax at 20%", "value-added tax", "V.A.T. included", "VAT20", "20%VAT", "incl.VAT",
                   "vat-inclusive", "V A T", "v. a. t.", "VATable", "V\u200bAT",
                   "\u0412\u0410\u0422 included")  # Cyrillic ВАТ
TAX_TEXT = ("Tax (20%) included", "plus tax", "Taxes included", "tax20", "20%tax", "TAX")
LOOKALIKE_TEXT = ("\u0455ort code", "Choir \u03bf", "\u0410 Client")  # Cyrillic dze, Greek omicron, Cyrillic A


def test_bank_details_and_vat_are_denied_in_any_text():
    I, C, B = "ZohoBooks_create_invoice", "ZohoBooks_create_contact", "ZohoBooks_create_bill"
    U = "ZohoBooks_upload_invoice_document"
    for text in BANK_TEXT + VAT_TEXT + REVIEW_BANK_TEXT + REVIEW_VAT_TEXT + LOOKALIKE_TEXT:
        assert denied(I, with_(I, "body", notes=text)), text
        assert denied(I, with_(I, "body", terms=text)), text
        assert denied(I, with_(I, "body", line_items=[{"name": "Choir", "description": text, "rate": 1}])), text
        assert denied(C, with_(C, "body", contact_name=text)), text
        assert denied(C, with_(C, "body", contact_persons=[{"first_name": text}])), text
        assert denied(C, with_(C, "body", billing_address={"address": text})), text
        assert denied(B, with_(B, "body", notes=text)), text
        assert denied(B, with_(B, "body", bill_number=text)), text
        assert denied("ZohoBooks_update_bill", with_("ZohoBooks_update_bill", "body", notes=text)), text
        assert denied("ZohoBooks_add_bill_comment",
                      with_("ZohoBooks_add_bill_comment", "body", description=text)), text
        assert denied("ZohoBooks_add_invoice_comment",
                      with_("ZohoBooks_add_invoice_comment", "body", description=text)), text
        assert denied("ZohoBooks_update_contact", with_("ZohoBooks_update_contact", "body", company_name=text)), text
        assert denied(U, with_(U, "query_params", attachment=f"~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/{text}.pdf")), text
    # a number is scanned as well as a string
    assert denied(I, with_(I, "body", line_items=[{"name": "Choir", "rate": 12345678}]))
    assert denied(I, with_(I, "body", line_items=[{"name": "Choir", "rate": 40000412345678}]))


def test_bank_digits_are_denied_in_address_fields():
    C = "ZohoBooks_create_contact"
    assert denied(C, with_(C, "body", billing_address={"zip": "040004"}))
    assert denied(C, with_(C, "body", billing_address={"street2": "1234 5678"}))
    assert denied(C, with_(C, "body", billing_address={"zip": "040004", "street2": "1234 5678"}))
    assert denied(C, with_(C, "body", contact_persons=[{"phone": "1234 5678"}]))


def test_tax_is_denied_in_invoice_and_bill_text_only():
    I, B, C = "ZohoBooks_create_invoice", "ZohoBooks_create_bill", "ZohoBooks_create_contact"
    for text in TAX_TEXT:
        assert denied(I, with_(I, "body", notes=text)), text
        assert denied(I, with_(I, "body", line_items=[{"name": text, "rate": 1}])), text
        assert denied(B, with_(B, "body", notes=text)), text
        assert denied("ZohoBooks_update_bill", with_("ZohoBooks_update_bill", "body", notes=text)), text
        assert denied("ZohoBooks_add_invoice_comment",
                      with_("ZohoBooks_add_invoice_comment", "body", description=text)), text
        assert denied("ZohoBooks_add_bill_comment", with_("ZohoBooks_add_bill_comment", "body", description=text)), text
    # a client may be a tax adviser; "tax" inside a word is fine everywhere
    assert decide("zoho-books", C, with_(C, "body", company_name="Smith Tax Advisers Ltd")) == "allow"
    for text in ("Taxi from the station", "Syntax of the order of service"):
        assert decide("zoho-books", I, with_(I, "body", notes=text)) == "allow", text


ORDINARY_TEXT = ("Wedding at St Bride's, 21 Nov 2026, 14:00", "Dates: 2026-11-21 and 2026-12-05",
                 "Invoice 2111, ref 2111B", "Tel 020 7946 0958", "Mobile 07700 900123", "Music for 150 guests",
                 "Arabic and Bicester", "Private vatican tour", "+44 20 7946 0958", "+44 7700 900123",
                 "21 November 2026", "2026-11-21", "Small choir (4 singers)", "\u00a31,150.00",
                 "Total \u00a312,500 for 2 services", "SW1A 1AA", "EC4Y 8AU", "W1K 7TN",
                 "Wedding on 21 November 2026 at St Mary's, Oxford OX1 4AH", "Service on 21/11/2026 at 11:00",
                 "Service on 21.11.2026", "Rehearsal 5 11 2026", "Café Rouge, Zoë Brontë", "Accountant: J Smith",
                 "Account manager: Ann", "Access code for the vestry: 4321",
                 "Tuesday 1 December 2026 11:00 \u2013 12:30", "Wedding, 21 Nov 2026 14:00", "21 November 2026 11am",
                 "December 12, 2026 2pm", "Service 11.00\u201312.30", "2026-11-21 14:00", "21/11/2026 14.30")


def test_ordinary_text_passes_the_bank_check():
    I = "ZohoBooks_create_invoice"
    for text in ORDINARY_TEXT:
        assert decide("zoho-books", I, with_(I, "body", notes=text)) == "allow", text
    for text in ("Tel +442079460958", "+44 20 7946 0958", "+ 44 20 7946 0958", "+12125550123"):
        assert decide("zoho-books", I, with_(I, "body", notes=text)) == "allow", text
    for text in ("Tel 442079460958", "+x 44 20 7946 0958", "12125550123", "+  44 20 7946 0958"):
        assert denied(I, with_(I, "body", notes=text)), text
    C = "ZohoBooks_create_contact"
    assert decide("zoho-books", C, with_(C, "body", contact_persons=[{"phone": "020 7946 0958",
                                                                       "mobile": "+44 7700 900123"}])) == "allow"


def test_long_text_is_scanned_quickly():
    # a slow scan could run past the hook's 10-second timeout; this must stay well under it
    import time
    I = "ZohoBooks_create_invoice"
    for text in ("+12345678901 " * 80000, "a " * 500000, "+ " * 500000 + "1"):
        start = time.time()
        assert decide("zoho-books", I, with_(I, "body", notes=text)) == "allow"
        assert time.time() - start < 3, text[:20]


def test_record_ids_are_exempt_from_the_digit_rule_only_as_whole_digit_ids():
    I, B = "ZohoBooks_create_invoice", "ZohoBooks_create_bill"
    for v in ("460000000026049", "123456789", "12345678901234567890"):
        assert decide("zoho-books", I, with_(I, "body", customer_id=v)) == "allow", v
    for v in ("12345678", "123456789012345678901", "04-00-04", "a12345678901", "0400 0412345678"):
        assert denied(I, with_(I, "body", customer_id=v)), v
    # the same digits outside an _id field are denied
    for key in ("notes", "reference_number", "terms"):
        assert denied(I, with_(I, "body", **{key: "460000000026049"})), key
    assert denied(B, with_(B, "body", line_items=[{"rate": 1, "description": "460000000033333"}]))


def test_only_the_invoice_number_is_exempt_from_the_digit_rule():
    B, I = "ZohoBooks_create_bill", "ZohoBooks_create_invoice"
    assert decide("zoho-books", I, with_(I, "body", invoice_number="2111B")) == "allow"
    # bill_number has no exemption: a singer's invoice number carrying bank digits is denied
    for bad in ("20260928", "12-34-56", "SC040004-AC12345678", "04-00-04", "Acc 12345678 please",
                "sort code 12-34-56", "VAT 1", "GB29 NWBK 6016 1331 9268 19"):
        assert denied(B, with_(B, "body", bill_number=bad)), bad
    for ok in ("S-17", "INV-017", "LW 42"):
        assert decide("zoho-books", B, with_(B, "body", bill_number=ok)) == "allow", ok
    assert denied(B, with_(B, "body", reference_number="20260928"))


# --- mark sent: the invoice id only, nothing else ---------------------------------------

def test_mark_invoice_sent_takes_only_the_invoice_id():
    M = "ZohoBooks_mark_invoice_sent"
    assert decide("zoho-books-invoices", M, {"query_params": ORG, "path_variables": {"invoice_id": "444"}}) == "allow"
    for bad in ({"query_params": ORG},
                {"query_params": ORG, "path_variables": {"invoice_id": ""}},
                {"query_params": dict(ORG, send=True), "path_variables": {"invoice_id": "444"}},
                {"query_params": dict(ORG, send_email=True), "path_variables": {"invoice_id": "444"}},
                {"query_params": ORG, "path_variables": {"invoice_id": "444"}, "body": {"to_mail_ids": ["a@b.com"]}},
                {"query_params": ORG, "path_variables": {"invoice_id": "444", "contact_id": "1"}}):
        assert decide("zoho-books-invoices", M, bad) == "deny", bad


# --- attachments come only from the private invoices folder ---------------------------

def test_attachment_must_be_a_pdf_or_docx_in_the_private_invoices_folder():
    U = "ZohoBooks_upload_invoice_document"
    home = os.path.expanduser("~")
    for ok in (CONFIRMATION, "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/2111 - A Client/Invoice 2111 - A Client.pdf",
               os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs", "LCS-invoices", "Invoice 2111 - A Client.pdf")):
        assert decide("zoho-books-invoices", U, with_(U, "query_params", attachment=ok)) == "allow", ok
    for bad in ("/tmp/Booking Confirmation.docx", "/Users/luca/.config/lcs/google-ads.yaml",
                "~/.config/gcloud/application_default_credentials.json", "~/lcs-private/bookings.csv",
                "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/../bookings.csv", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/../invoices/a.pdf",
                "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a/../../x.pdf", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoicesX/a.pdf", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices",
                "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a.txt", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a.pdf.exe",
                "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a.PDF", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a.pdf\n", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a\u0000.pdf",
                "Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a.pdf", "~root/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/a.pdf", "~/lcs-private/invoices/a.pdf", "~/.ssh/id_ed25519",
                "../../etc/passwd", "https://evil.test/a.pdf", "file:///Users/luca/lcs-private/invoices/a.pdf",
                "JVBERi0xLjQKJcfsj6IKNSAwIG9iago8PC9MZW5ndGggNiAwIFI+PgpzdHJlYW0K", "data:application/pdf;base64,JVBERi0=",
                json.dumps({"send": True}), "", 1, True, ["a.pdf"]):
        assert denied(U, with_(U, "query_params", attachment=bad), "zoho-books-invoices"), bad


def test_attachment_path_is_resolved_through_symlinks():
    U = "ZohoBooks_upload_invoice_document"
    home = tempfile.mkdtemp()
    inv = os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs", "LCS-invoices")
    os.makedirs(inv)
    os.symlink("/etc", os.path.join(inv, "etc"))
    open(os.path.join(home, "secret.pdf"), "w").close()
    os.symlink(os.path.join(home, "secret.pdf"), os.path.join(inv, "link.pdf"))
    env = dict(os.environ, HOME=home)
    ok = with_(U, "query_params", attachment="~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/Invoice 2111 - A Client.pdf")
    assert decide("zoho-books-invoices", U, ok, env) == "allow"
    for bad in ("~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/etc/passwd.pdf", "~/Library/Mobile Documents/com~apple~CloudDocs/LCS-invoices/link.pdf"):
        assert denied_env(U, with_(U, "query_params", attachment=bad), env), bad


def denied_env(tool, ti, env):
    return decide("zoho-books-invoices", tool, ti, env) == "deny"


# --- L2: exact server names ----------------------------------------------------------

def test_only_the_two_books_servers_are_accepted():
    ti = good_inputs()["ZohoBooks_create_invoice"]
    for tool in ("mcp__zoho-books-evil__ZohoBooks_create_invoice", "mcp__zoho-books-x__ZohoBooks_list_invoices",
                 "mcp__zoho-mail__ZohoBooks_create_invoice", "zoho-books__ZohoBooks_create_invoice",
                 "ZohoBooks_create_invoice", "mcp__zoho-books__ZohoBooks_create_invoice ",
                 "mcp__zoho-books__zohobooks_create_invoice", "mcp__ZOHO-BOOKS__ZohoBooks_create_invoice",
                 "mcp__zoho-books__x__ZohoBooks_create_invoice", "mcp__zoho-books__", "xmcp__zoho-books__ZohoBooks_list_invoices"):
        assert raw(json.dumps({"tool_name": tool, "tool_input": ti})) == "deny", tool
    for server in SERVERS:
        assert raw(json.dumps({"tool_name": f"mcp__{server}__ZohoBooks_create_invoice", "tool_input": ti})) == "allow"


# --- L3: tax fields ------------------------------------------------------------------

def test_tax_fields_are_denied():
    for tool, section in (("ZohoBooks_create_invoice", "body"), ("ZohoBooks_create_contact", "body"),
                          ("ZohoBooks_create_bill", "body"), ("ZohoBooks_update_bill", "body")):
        for key in ("tax_id", "vat_treatment", "tax_treatment", "tax_exemption_id", "is_inclusive_tax"):
            assert denied(tool, with_(tool, section, **{key: "x"})), (tool, key)
    I = "ZohoBooks_create_invoice"
    assert denied(I, with_(I, "body", line_items=[{"name": "x", "rate": 1, "tax_id": "77"}]))
    assert denied("ZohoBooks_create_bill", with_("ZohoBooks_create_bill", "body",
                                                 line_items=[{"name": "x", "rate": 1, "tax_id": "77"}]))


# --- still denied, and the plumbing --------------------------------------------------

def test_still_denied_tools_from_the_design():
    # A plausible-looking argument set must not unlock any of these.
    ti = good_inputs()["ZohoBooks_create_invoice"]
    for name in ("ZohoBooks_email_invoice", "ZohoBooks_delete_invoice",
                 "ZohoBooks_mark_invoice_void", "ZohoBooks_write_off_invoice", "ZohoBooks_create_customer_payment",
                 "ZohoBooks_match_bank_transaction", "ZohoBooks_categorize_bank_transaction",
                 "ZohoBooks_approve_bill", "ZohoBooks_delete_bill", "ZohoBooks_convert_purchase_order_to_bill",
                 "ZohoBooks_add_contact_bank_account", "ZohoBooks_generate_invoice_payment_link",
                 "ZohoBooks_submit_bill", "ZohoBooks_mark_bill_open", "ZohoBooks_mark_bill_void",
                 "ZohoBooks_delete_bill_payment", "ZohoBooks_apply_credits_to_bill", "ZohoBooks_update_invoice"):
        for server in SERVERS:
            assert decide(server, name, ti) == "deny", (server, name)


def test_new_read_only_bill_tools_are_allowed():
    for name in ("ZohoBooks_get_bill", "ZohoBooks_get_bill_comments", "ZohoBooks_list_bills",
                 "ZohoBooks_list_bill_payments"):
        assert decide("zoho-books", name) == "allow", name


def test_malformed_events_fail_closed():
    assert raw("{not json") == "deny"
    assert raw("") == "deny"
    assert raw(json.dumps({"tool_input": {}})) == "deny"  # missing tool_name
    assert raw(json.dumps({"tool_name": 123, "tool_input": {}})) == "deny"  # not a string
    assert raw(json.dumps(["not", "an", "object"])) == "deny"


def test_settings_hook_blocks_when_the_guard_cannot_run():
    cmd = hook_command()
    assert cmd.endswith("|| exit 2"), cmd
    event = json.dumps({"tool_name": "mcp__zoho-books__ZohoBooks_deleteInvoice", "tool_input": {}})
    run = lambda c, project: subprocess.run(["sh", "-c", c], input=event, capture_output=True, text=True,
                                            env=dict(os.environ, CLAUDE_PROJECT_DIR=project))
    # the real command, from the worktree: the guard runs and denies with exit 0
    ok = run(cmd, ROOT)
    assert ok.returncode == 0 and json.loads(ok.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", ok
    # the same command against a guard path that does not exist: exit 2, which blocks a PreToolUse call
    missing = cmd.replace("zoho_books_guard.py", "zoho_books_guard_missing.py")
    assert missing != cmd
    assert run(missing, ROOT).returncode == 2
    assert run(cmd, tempfile.mkdtemp()).returncode == 2


def test_settings_json_is_valid_and_registers_the_guard():
    with open(SETTINGS) as f:
        cfg = json.load(f)
    assert hook_command() == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/zoho_books_guard.py" || exit 2'
    matchers = [entry["matcher"] for entry in cfg["hooks"]["PreToolUse"]]
    assert "mcp__zoho-mail__.*" in matchers
    assert "mcp__zoho-books.*" in matchers
    # both Zoho guards fail closed: a guard that can't run exits 2, which blocks the call
    cmds = {entry["matcher"]: [h["command"] for h in entry["hooks"]] for entry in cfg["hooks"]["PreToolUse"]}
    for matcher, script in (("mcp__zoho-mail__.*", "zoho_guard.py"), ("mcp__zoho-books.*", "zoho_books_guard.py")):
        assert len(cmds[matcher]) == 1, matcher
        assert script in cmds[matcher][0] and cmds[matcher][0].endswith("|| exit 2"), cmds[matcher]
    # Claude may not read the Starling token or dump the Keychain
    security = sorted(d for d in cfg["permissions"]["deny"] if d.startswith("Bash(security"))
    assert security == ["Bash(security dump-keychain *)", "Bash(security dump-keychain)",
                        "Bash(security find-generic-password *)"], security
    # both servers are pre-approved so scheduled tasks don't stall; the guard decides what runs
    for server in SERVERS:
        assert f"mcp__{server}" in cfg["permissions"]["allow"], server


def test_update_contact_may_restate_contact_type_only_as_customer_or_vendor():
    ok = {"path_variables": {"contact_id": "1"}, "body": {"contact_name": "Ann Smith", "contact_type": "customer"}}
    assert decide("zoho-books-invoices", "ZohoBooks_update_contact", ok) == "allow"
    bad = {"path_variables": {"contact_id": "1"}, "body": {"contact_name": "Ann Smith", "contact_type": "employee"}}
    assert decide("zoho-books-invoices", "ZohoBooks_update_contact", bad) == "deny"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
