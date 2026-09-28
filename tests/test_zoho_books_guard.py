#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_books_guard.py (PreToolUse). Stdlib only."""
import importlib.util, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, ".claude", "hooks", "zoho_books_guard.py")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

SERVERS = ("zoho-books", "zoho-books-invoices")


NON_READ_ONLY = [ "ZohoBooks_add_bank_reconciliation_attachment", "ZohoBooks_add_contact_address", "ZohoBooks_add_contact_attachment", "ZohoBooks_add_contact_bank_account", "ZohoBooks_add_contact_card", "ZohoBooks_add_contact_comment", "ZohoBooks_add_contact_tax_info", "ZohoBooks_add_invoice_comment", "ZohoBooks_add_invoice_digital_signature", "ZohoBooks_add_invoice_document", "ZohoBooks_add_invoice_online_payment_bank_account", "ZohoBooks_apply_credits_to_invoice", "ZohoBooks_apply_invoice_substatus", "ZohoBooks_apply_pricebook_to_invoice", "ZohoBooks_approve_contact_bank_account", "ZohoBooks_approve_invoice", "ZohoBooks_approve_invoices", "ZohoBooks_assign_contact_owner", "ZohoBooks_assign_owner_to_contacts", "ZohoBooks_bulk_invoice_reminder", "ZohoBooks_bulk_mark_item_masters_active", "ZohoBooks_bulk_mark_item_masters_inactive", "ZohoBooks_bulk_mark_item_variants_active", "ZohoBooks_bulk_mark_item_variants_inactive", "ZohoBooks_bulk_update_bank_account_rules", "ZohoBooks_cancel_einvoice_invoice", "ZohoBooks_cancel_invoice", "ZohoBooks_cancel_invoice_einvoice", "ZohoBooks_cancel_invoices_einvoice", "ZohoBooks_cancel_scheduled_invoice_email", "ZohoBooks_cancel_write_off_invoice", "ZohoBooks_categorize_as_credit_note_refunds", "ZohoBooks_categorize_as_vendor_credit_refunds", "ZohoBooks_categorize_as_vendor_payment_refund", "ZohoBooks_categorize_bank_transaction", "ZohoBooks_categorize_bank_transaction_as_customer_payment", "ZohoBooks_categorize_bank_transaction_as_expense", "ZohoBooks_categorize_bank_transaction_as_payment_refund", "ZohoBooks_categorize_bank_transaction_as_vendor_payment", "ZohoBooks_create_bank_account", "ZohoBooks_create_bank_account_match_filter", "ZohoBooks_create_bank_account_rule", "ZohoBooks_create_bank_reconciliation", "ZohoBooks_create_bank_transaction", "ZohoBooks_create_contact", "ZohoBooks_create_contact_person", "ZohoBooks_create_customer_payment", "ZohoBooks_create_customer_payment_refund", "ZohoBooks_create_employee", "ZohoBooks_create_expense", "ZohoBooks_create_invoice", "ZohoBooks_create_invoice_asynchronous_online_payment", "ZohoBooks_create_invoice_from_salesorder", "ZohoBooks_create_invoice_synchronous_online_payment", "ZohoBooks_create_invoices_from_estimates", "ZohoBooks_create_invoices_from_projects", "ZohoBooks_create_item", "ZohoBooks_create_item_master", "ZohoBooks_create_item_variant", "ZohoBooks_create_pricebook", "ZohoBooks_create_recurring_bill", "ZohoBooks_create_tax", "ZohoBooks_create_tax_authority", "ZohoBooks_create_tax_exemption", "ZohoBooks_create_tax_group", "ZohoBooks_decline_contact_bank_account", "ZohoBooks_delete_invoice", "ZohoBooks_delete_invoice_applied_credit", "ZohoBooks_delete_invoice_comment", "ZohoBooks_delete_invoice_document", "ZohoBooks_delete_invoice_einvoice_status", "ZohoBooks_delete_invoice_expense_receipt", "ZohoBooks_delete_invoice_line_item", "ZohoBooks_delete_invoice_payment", "ZohoBooks_delete_invoice_substatus", "ZohoBooks_delete_invoices", "ZohoBooks_delete_recurring_bill", "ZohoBooks_disable_contact_payment_reminder", "ZohoBooks_disable_contact_person_sms", "ZohoBooks_disable_contact_portal", "ZohoBooks_disable_invoice_payment_reminder", "ZohoBooks_email_contact", "ZohoBooks_email_contact_statement", "ZohoBooks_email_invoice", "ZohoBooks_email_invoices", "ZohoBooks_enable_contact_payment_reminder", "ZohoBooks_enable_contact_person_sms", "ZohoBooks_enable_contact_portal", "ZohoBooks_enable_invoice_payment_reminder", "ZohoBooks_exclude_bank_transaction", "ZohoBooks_fetch_invoice_einvoice", "ZohoBooks_finalize_invoice_approval", "ZohoBooks_force_pay_invoice", "ZohoBooks_generate_invoice_payment_link", "ZohoBooks_get_bank_statement_import_encryption_key", "ZohoBooks_import_bank_statements", "ZohoBooks_invite_contact_person_to_portal", "ZohoBooks_mail_invoice_pdf", "ZohoBooks_map_invoice_with_salesorder", "ZohoBooks_mark_bank_account_active", "ZohoBooks_mark_bank_account_inactive", "ZohoBooks_mark_contact_active", "ZohoBooks_mark_contact_address_as_billing", "ZohoBooks_mark_contact_address_as_shipping", "ZohoBooks_mark_contact_inactive", "ZohoBooks_mark_contact_person_primary", "ZohoBooks_mark_contacts_for_1099_tracking", "ZohoBooks_mark_invoice_draft", "ZohoBooks_mark_invoice_einvoice_cancelled", "ZohoBooks_mark_invoice_einvoice_pushed", "ZohoBooks_mark_invoice_ready_to_push", "ZohoBooks_mark_invoice_sent", "ZohoBooks_mark_invoice_void", "ZohoBooks_mark_invoices_sent", "ZohoBooks_mark_invoices_shipped", "ZohoBooks_mark_item_active", "ZohoBooks_mark_item_inactive", "ZohoBooks_mark_item_master_as_active", "ZohoBooks_mark_item_master_as_inactive", "ZohoBooks_mark_item_variant_as_active", "ZohoBooks_mark_item_variant_as_inactive", "ZohoBooks_mark_pricebook_active", "ZohoBooks_mark_pricebook_inactive", "ZohoBooks_match_bank_transaction", "ZohoBooks_merge_contact", "ZohoBooks_move_item_variant", "ZohoBooks_preview_invoice_coupons", "ZohoBooks_push_invoice_einvoice", "ZohoBooks_push_invoices_einvoice", "ZohoBooks_recall_invoice_einvoice_status", "ZohoBooks_reject_invoice", "ZohoBooks_remind_customer_for_invoice_payment", "ZohoBooks_reorder_bank_account_rules", "ZohoBooks_resend_contact_person_portal_invite", "ZohoBooks_restore_bank_transaction", "ZohoBooks_restore_contact_documents", "ZohoBooks_resume_recurring_bill", "ZohoBooks_save_bank_reconciliation_draft", "ZohoBooks_schedule_invoice_email", "ZohoBooks_send_contact_client_review_email", "ZohoBooks_send_contact_payment_method_email", "ZohoBooks_send_contact_sms", "ZohoBooks_send_contact_vendor_statement_email", "ZohoBooks_send_contacts_sms", "ZohoBooks_send_invoice_dunning_notifications", "ZohoBooks_send_invoice_retry_sms", "ZohoBooks_send_invoice_sms", "ZohoBooks_send_invoice_via_snail_mail", "ZohoBooks_skip_suggested_bank_account_rule", "ZohoBooks_stop_recurring_bill", "ZohoBooks_submit_invoice", "ZohoBooks_submit_invoices", "ZohoBooks_track_contact_1099", "ZohoBooks_uncategorize_bank_transaction", "ZohoBooks_ungroup_item_variants", "ZohoBooks_unmap_invoices_from_salesorders", "ZohoBooks_unmatch_bank_transaction", "ZohoBooks_unship_invoices", "ZohoBooks_untrack_contact_1099", "ZohoBooks_update_bank_account", "ZohoBooks_update_bank_account_match_filter", "ZohoBooks_update_bank_account_preferences", "ZohoBooks_update_bank_account_rule", "ZohoBooks_update_bank_reconciliation", "ZohoBooks_update_bank_transaction", "ZohoBooks_update_contact", "ZohoBooks_update_contact_address", "ZohoBooks_update_contact_bank_account", "ZohoBooks_update_contact_card", "ZohoBooks_update_contact_document", "ZohoBooks_update_contact_person", "ZohoBooks_update_contact_tags", "ZohoBooks_update_contact_tax_info", "ZohoBooks_update_contact_trn_status", "ZohoBooks_update_contact_using_custom_field", "ZohoBooks_update_custom_fields_in_customer_payment", "ZohoBooks_update_custom_fields_in_invoice", "ZohoBooks_update_custom_fields_in_item", "ZohoBooks_update_customer_payment", "ZohoBooks_update_customer_payment_refund", "ZohoBooks_update_customer_payment_using_custom_field", "ZohoBooks_update_expense", "ZohoBooks_update_expense_using_custom_field", "ZohoBooks_update_invoice", "ZohoBooks_update_invoice_advanced_tracking_details", "ZohoBooks_update_invoice_billing_address", "ZohoBooks_update_invoice_cfdi_status", "ZohoBooks_update_invoice_comment", "ZohoBooks_update_invoice_einvoice_payment_status", "ZohoBooks_update_invoice_metadata", "ZohoBooks_update_invoice_shipping_address", "ZohoBooks_update_invoice_template", "ZohoBooks_update_invoice_using_custom_field", "ZohoBooks_update_item", "ZohoBooks_update_item_master", "ZohoBooks_update_item_using_custom_field", "ZohoBooks_update_item_variant", "ZohoBooks_update_pricebook", "ZohoBooks_update_recurring_bill", "ZohoBooks_update_recurring_bill_using_custom_field", "ZohoBooks_update_tax", "ZohoBooks_update_tax_authority", "ZohoBooks_update_tax_exemption", "ZohoBooks_update_tax_group", "ZohoBooks_upload_invoice_digital_signature", "ZohoBooks_upload_invoice_document", "ZohoBooks_verify_contact_address_by_id", "ZohoBooks_verify_contact_bank_account", "ZohoBooks_verify_contact_einvoice", "ZohoBooks_void_invoices", "ZohoBooks_write_off_invoice", "ZohoBooks_write_off_invoices" ]


def raw(stdin):
    """Run the guard on raw stdin; its decision ("allow" when it prints nothing)."""
    p = subprocess.run([sys.executable, GUARD], input=stdin, capture_output=True, text=True)
    assert p.returncode == 0, (p.returncode, p.stderr)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"] if p.stdout.strip() else "allow"


def decide(server, tool, tool_input=None):
    return raw(json.dumps({"tool_name": f"mcp__{server}__{tool}", "tool_input": tool_input or {}}))


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
    assert decide("zoho-books", "ZohoBooks_list_bank_transactions") == "allow"


def test_send_and_write_tools_are_denied():
    for name in ("ZohoBooks_email_invoice", "ZohoBooks_email_invoices", "ZohoBooks_schedule_invoice_email",
                 "ZohoBooks_delete_invoice",
                 "ZohoBooks_mark_invoice_void", "ZohoBooks_mark_invoice_sent", "ZohoBooks_write_off_invoice",
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
               "ZohoBooks_list_contact_cards", "ZohoBooks_get_contact_card_count"}
    assert not removed & guard_module().READ_ALLOW
    for server in SERVERS:
        for name in removed:
            assert decide(server, name) == "deny", (server, name)


# --- owner-approved writes, checked by argument --------------------------------------

APPROVED_WRITES = {
    "ZohoBooks_create_contact", "ZohoBooks_update_contact",
    "ZohoBooks_create_invoice",
    "ZohoBooks_add_invoice_document", "ZohoBooks_upload_invoice_document",
    "ZohoBooks_add_invoice_comment",
    "ZohoBooks_create_bill", "ZohoBooks_update_bill", "ZohoBooks_add_bill_comment",
}
ORG = {"organization_id": "941014440"}


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
                            "account_id": "460000000033333", "item_order": 1}]}
    return {
        "ZohoBooks_create_contact": {"body": contact, "query_params": ORG},
        "ZohoBooks_update_contact": {"body": {"contact_name": "A Client", "company_name": "A Client Ltd"},
                                     "query_params": ORG, "path_variables": {"contact_id": "333"}},
        "ZohoBooks_create_invoice": {"body": invoice,
                                     "query_params": dict(ORG, ignore_auto_number_generation=True, send=False)},
        "ZohoBooks_add_invoice_document": {"query_params": ORG,
                                           "path_variables": {"invoice_id": "444", "document_id": "555"}},
        "ZohoBooks_upload_invoice_document": {"query_params": dict(ORG, attachment="/tmp/Booking Confirmation.docx"),
                                              "path_variables": {"invoice_id": "444", "document_id": "555"}},
        "ZohoBooks_add_invoice_comment": {"body": {"description": "Booking confirmation to attach"},
                                          "query_params": ORG, "path_variables": {"invoice_id": "444"}},
        "ZohoBooks_create_bill": {"body": dict(bill, documents=[{"document_id": "777", "file_name": "S-17.pdf"}]),
                                  "query_params": ORG},
        "ZohoBooks_update_bill": {"body": bill, "query_params": ORG, "path_variables": {"bill_id": "666"}},
        "ZohoBooks_add_bill_comment": {"body": {"description": "Booking 2111"}, "query_params": ORG,
                                       "path_variables": {"bill_id": "666"}},
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
            ("ZohoBooks_update_bill", {"body": {"vendor_id": "1"}, "query_params": ORG,
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
                     ("notes", "x"), ("contact_type", "vendor"), ("billing_address", {"city": "London"}),
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


def test_keys_are_compared_case_insensitively():
    I, C = "ZohoBooks_create_invoice", "ZohoBooks_create_contact"
    # a differently-cased duplicate of an allowed key is denied, whatever the values
    assert denied(I, with_(I, "query_params", Send=False))  # send=False is already there
    assert denied(I, with_(I, "query_params", SEND="false"))
    assert denied(I, with_(I, "body", Customer_ID="1"))
    assert denied(C, with_(C, "body", Contact_Name="B"))
    # a differently-cased key on its own is read as the allowed key and checked as such
    ti = with_(I, "query_params", send=None, Send=True)
    assert denied(I, ti)
    ti = with_(I, "query_params", send=None, SEND="true")
    assert denied(I, ti)
    assert denied(I, with_(I, "body", Send=True))  # body never takes send
    assert denied(C, with_(C, "body", contact_type=None, Contact_Type="employee"))
    assert decide("zoho-books", I, with_(I, "query_params", send=None, Send=False)) == "allow"


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


def test_bill_update_needs_bill_id_and_vendor_id():
    U = "ZohoBooks_update_bill"
    assert denied(U, with_(U, "path_variables", bill_id=None))
    assert denied(U, with_(U, "body", vendor_id=None))
    assert denied(U, {"body": {"notes": "x"}, "query_params": ORG, "path_variables": {"bill_id": "1"}})


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


def test_bank_details_and_vat_are_denied_in_any_text():
    I, C, B = "ZohoBooks_create_invoice", "ZohoBooks_create_contact", "ZohoBooks_create_bill"
    for text in BANK_TEXT + VAT_TEXT:
        assert denied(I, with_(I, "body", notes=text)), text
        assert denied(I, with_(I, "body", terms=text)), text
        assert denied(I, with_(I, "body", line_items=[{"name": "Choir", "description": text, "rate": 1}])), text
        assert denied(C, with_(C, "body", contact_name=text)), text
        assert denied(C, with_(C, "body", contact_persons=[{"first_name": text}])), text
        assert denied(C, with_(C, "body", billing_address={"address": text})), text
        assert denied(B, with_(B, "body", notes=text)), text
        assert denied("ZohoBooks_add_bill_comment",
                      with_("ZohoBooks_add_bill_comment", "body", description=text)), text
        assert denied("ZohoBooks_add_invoice_comment",
                      with_("ZohoBooks_add_invoice_comment", "body", description=text)), text
        assert denied("ZohoBooks_update_contact", with_("ZohoBooks_update_contact", "body", company_name=text)), text
        assert denied("ZohoBooks_upload_invoice_document",
                      with_("ZohoBooks_upload_invoice_document", "query_params", attachment=f"/tmp/{text}.pdf")), text
    # a number is scanned as well as a string
    assert denied(I, with_(I, "body", line_items=[{"name": "Choir", "rate": 12345678}]))


def test_ordinary_text_passes_the_bank_check():
    I = "ZohoBooks_create_invoice"
    for text in ("Wedding at St Bride's, 21 Nov 2026, 14:00", "Dates: 2026-11-21 and 2026-12-05",
                 "Invoice 2111, ref 2111B", "Tel 020 7946 0958", "Mobile 07700 900123", "Music for 150 guests",
                 "Arabic and Bicester", "Private vatican tour"):
        assert decide("zoho-books", I, with_(I, "body", notes=text)) == "allow", text


def test_invoice_and_bill_numbers_are_exempt_from_the_digit_rule_only_when_they_match():
    B = "ZohoBooks_create_bill"
    for ok in ("20260928", "INV-12345678", "12-34-56"):
        assert decide("zoho-books", B, with_(B, "body", bill_number=ok)) == "allow", ok
    for bad in ("Acc 12345678 please", "sort code 12-34-56", "VAT 1", "GB29 NWBK 1"):
        assert denied(B, with_(B, "body", bill_number=bad)), bad
    # the exemption is for the field itself: the same digits elsewhere are still denied
    assert denied(B, with_(B, "body", reference_number="20260928"))


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
    for name in ("ZohoBooks_email_invoice", "ZohoBooks_mark_invoice_sent", "ZohoBooks_delete_invoice",
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
    # both servers are pre-approved so scheduled tasks don't stall; the guard decides what runs
    for server in SERVERS:
        assert f"mcp__{server}" in cfg["permissions"]["allow"], server


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
