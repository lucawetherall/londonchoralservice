#!/usr/bin/env python3
"""Tests for .claude/hooks/zoho_books_guard.py (PreToolUse). Stdlib only."""
import json, os, subprocess, sys, tempfile

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
    for name in NON_READ_ONLY:
        if name in APPROVED_WRITES:
            continue
        assert decide("zoho-books", name) == "deny", name


# --- owner-approved writes, checked by argument --------------------------------------

APPROVED_WRITES = {
    "ZohoBooks_create_contact", "ZohoBooks_update_contact",
    "ZohoBooks_create_invoice", "ZohoBooks_update_invoice",
    "ZohoBooks_add_invoice_document", "ZohoBooks_upload_invoice_document",
    "ZohoBooks_add_invoice_comment",
    "ZohoBooks_create_bill", "ZohoBooks_update_bill", "ZohoBooks_add_bill_comment",
}
ORG = {"organization_id": "941014440"}


def good_inputs():
    """One well-formed call per approved write tool."""
    contact = {"contact_name": "A Client", "contact_type": "customer",
               "contact_persons": [{"first_name": "A", "email": "a@example.com"}]}
    invoice = {"customer_id": "111", "invoice_number": "2111",
               "line_items": [{"name": "Small Choir", "rate": 1150, "quantity": 1}]}
    bill = {"vendor_id": "222", "bill_number": "S-17", "date": "2026-09-28",
            "payment_terms": 14, "payment_terms_label": "Net 14",
            "line_items": [{"name": "Wedding, 2111", "rate": 180, "quantity": 1}]}
    return {
        "ZohoBooks_create_contact": {"body": contact, "query_params": ORG},
        "ZohoBooks_update_contact": {"body": dict(contact, contact_type="vendor"), "query_params": ORG,
                                     "path_variables": {"contact_id": "333"}},
        "ZohoBooks_create_invoice": {"body": dict(invoice, send=False),
                                     "query_params": dict(ORG, ignore_auto_number_generation=True, send="false")},
        "ZohoBooks_update_invoice": {"body": invoice, "query_params": ORG, "path_variables": {"invoice_id": "444"}},
        "ZohoBooks_add_invoice_document": {"query_params": ORG,
                                           "path_variables": {"invoice_id": "444", "document_id": "555"}},
        "ZohoBooks_upload_invoice_document": {"query_params": ORG,
                                              "path_variables": {"invoice_id": "444", "document_id": "555"}},
        "ZohoBooks_add_invoice_comment": {"body": {"description": "Booking confirmation to attach",
                                                   "show_comment_to_clients": False},
                                          "query_params": ORG, "path_variables": {"invoice_id": "444"}},
        "ZohoBooks_create_bill": {"body": bill, "query_params": ORG},
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


def test_approved_writes_with_good_arguments_are_allowed_on_both_servers():
    assert set(good_inputs()) == APPROVED_WRITES
    for server in SERVERS:
        for name, ti in good_inputs().items():
            assert decide(server, name, ti) == "allow", (server, name)


def test_invoice_with_invoice_number_suffix_and_string_flags_is_allowed():
    ti = with_("ZohoBooks_create_invoice", "body", invoice_number="2111B", send=None)
    ti["query_params"]["ignore_auto_number_generation"] = "true"
    assert decide("zoho-books-invoices", "ZohoBooks_create_invoice", ti) == "allow"
    ti = with_("ZohoBooks_create_invoice", "query_params", ignore_auto_number_generation=None)
    ti["body"]["ignore_auto_number_generation"] = True
    assert decide("zoho-books-invoices", "ZohoBooks_create_invoice", ti) == "allow"


def test_invoice_send_true_in_body_is_denied():
    for v in (True, "true", "True", "1", 1):
        assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                      with_("ZohoBooks_create_invoice", "body", send=v)) == "deny", v
    assert decide("zoho-books-invoices", "ZohoBooks_update_invoice",
                  with_("ZohoBooks_update_invoice", "body", send=True)) == "deny"


def test_invoice_send_true_in_query_params_is_denied():
    for v in ("true", "True", "1", True, "yes"):
        assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                      with_("ZohoBooks_create_invoice", "query_params", send=v)) == "deny", v
    assert decide("zoho-books-invoices", "ZohoBooks_update_invoice",
                  with_("ZohoBooks_update_invoice", "query_params", send="true")) == "deny"


def test_invoice_number_must_be_a_ddmm_ref():
    for bad in ("INV-2111", "211", "21111", "2111b", "2111AB", "2111\n", 2111):
        assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                      with_("ZohoBooks_create_invoice", "body", invoice_number=bad)) == "deny", bad
    assert decide("zoho-books-invoices", "ZohoBooks_update_invoice",
                  with_("ZohoBooks_update_invoice", "body", invoice_number="INV-2111")) == "deny"
    # required on create, optional on update
    assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                  with_("ZohoBooks_create_invoice", "body", invoice_number=None)) == "deny"
    assert decide("zoho-books-invoices", "ZohoBooks_update_invoice",
                  with_("ZohoBooks_update_invoice", "body", invoice_number=None)) == "allow"


def test_invoice_create_needs_ignore_auto_number_generation():
    for v in (None, False, "false", "0"):
        assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                      with_("ZohoBooks_create_invoice", "query_params", ignore_auto_number_generation=v)) == "deny", v


def test_invoice_missing_customer_id_is_denied():
    for v in (None, ""):
        assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                      with_("ZohoBooks_create_invoice", "body", customer_id=v)) == "deny", v


def test_invoice_update_needs_invoice_id():
    assert decide("zoho-books-invoices", "ZohoBooks_update_invoice",
                  with_("ZohoBooks_update_invoice", "path_variables", invoice_id=None)) == "deny"


def test_invoice_batch_payments_are_denied():
    assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                  with_("ZohoBooks_create_invoice", "body", batch_payments=[{"payment_mode": "cash"}])) == "deny"
    assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                  with_("ZohoBooks_create_invoice", "query_params", batch_payments=True)) == "deny"


def test_invoice_payment_gateway_is_denied():
    gw = {"payment_gateways": [{"gateway_name": "stripe", "configured": True}]}
    for tool in ("ZohoBooks_create_invoice", "ZohoBooks_update_invoice"):
        assert decide("zoho-books-invoices", tool, with_(tool, "body", payment_options=gw)) == "deny", tool
    # an empty gateway list is harmless
    assert decide("zoho-books-invoices", "ZohoBooks_create_invoice",
                  with_("ZohoBooks_create_invoice", "body", payment_options={"payment_gateways": []})) == "allow"


def test_contact_portal_is_denied():
    for tool in ("ZohoBooks_create_contact", "ZohoBooks_update_contact"):
        assert decide("zoho-books", tool, with_(tool, "body", is_portal_enabled=True)) == "deny", tool
        assert decide("zoho-books", tool, with_(tool, "body", is_portal_enabled="true")) == "deny", tool
        persons = [{"first_name": "A", "email": "a@example.com", "enable_portal": True}]
        assert decide("zoho-books", tool, with_(tool, "body", contact_persons=persons)) == "deny", tool
    assert decide("zoho-books", "ZohoBooks_create_contact",
                  with_("ZohoBooks_create_contact", "body", is_portal_enabled=False)) == "allow"


def test_contact_bank_card_credit_and_opening_balance_fields_are_denied():
    for tool in ("ZohoBooks_create_contact", "ZohoBooks_update_contact"):
        for key, val in (("bank_account_number", "12345678"), ("bank_accounts", [{"account_number": "1"}]),
                         ("card_number", "4111"), ("credit_limit", 500),
                         ("opening_balances", [{"opening_balance_amount": 100}])):
            assert decide("zoho-books", tool, with_(tool, "body", **{key: val})) == "deny", (tool, key)
        nested = [{"first_name": "A", "bank_sort_code": "00-00-00"}]
        assert decide("zoho-books", tool, with_(tool, "body", contact_persons=nested)) == "deny", tool


def test_contact_type_must_be_customer_or_vendor():
    for tool in ("ZohoBooks_create_contact", "ZohoBooks_update_contact"):
        assert decide("zoho-books", tool, with_(tool, "body", contact_type="employee")) == "deny", tool


def test_contact_body_must_be_an_object():
    assert decide("zoho-books", "ZohoBooks_create_contact",
                  {"body": ["not", "a", "dict"], "query_params": ORG}) == "deny"
    assert decide("zoho-books", "ZohoBooks_create_invoice", {"body": "x", "query_params": ORG}) == "deny"
    assert decide("zoho-books", "ZohoBooks_create_invoice",
                  dict(good_inputs()["ZohoBooks_create_invoice"], query_params="send=true")) == "deny"
    assert decide("zoho-books", "ZohoBooks_update_invoice",
                  dict(good_inputs()["ZohoBooks_update_invoice"], path_variables=["444"])) == "deny"
    assert raw(json.dumps({"tool_name": "mcp__zoho-books__ZohoBooks_add_bill_comment",
                           "tool_input": "not an object"})) == "deny"


def test_invoice_documents_need_invoice_id():
    for tool in ("ZohoBooks_add_invoice_document", "ZohoBooks_upload_invoice_document"):
        assert decide("zoho-books-invoices", tool,
                      with_(tool, "path_variables", invoice_id=None)) == "deny", tool


def test_invoice_comment_shown_to_client_is_denied():
    for v in (True, "true", "1"):
        assert decide("zoho-books-invoices", "ZohoBooks_add_invoice_comment",
                      with_("ZohoBooks_add_invoice_comment", "body", show_comment_to_clients=v)) == "deny", v


def test_bill_approvers_and_purchase_orders_are_denied():
    for tool in ("ZohoBooks_create_bill", "ZohoBooks_update_bill"):
        assert decide("zoho-books", tool,
                      with_(tool, "body", approvers=[{"approver_id": "1", "order": 1}])) == "deny", tool
        assert decide("zoho-books", tool, with_(tool, "body", purchaseorder_ids=["9"])) == "deny", tool


def test_bill_payment_fields_are_denied():
    for tool in ("ZohoBooks_create_bill", "ZohoBooks_update_bill"):
        for key, val in (("payment_made", 180), ("payments", [{"amount": 180}]), ("vendor_payment_id", "1")):
            assert decide("zoho-books", tool, with_(tool, "body", **{key: val})) == "deny", (tool, key)
        items = [{"name": "Wedding", "rate": 180, "payment_account_id": "7"}]
        assert decide("zoho-books", tool, with_(tool, "body", line_items=items)) == "deny", tool


def test_bill_create_needs_vendor_and_bill_number():
    for key in ("vendor_id", "bill_number"):
        assert decide("zoho-books", "ZohoBooks_create_bill",
                      with_("ZohoBooks_create_bill", "body", **{key: None})) == "deny", key


def test_still_denied_tools_from_the_design():
    # A plausible-looking argument set must not unlock any of these.
    ti = good_inputs()["ZohoBooks_update_invoice"]
    for name in ("ZohoBooks_email_invoice", "ZohoBooks_mark_invoice_sent", "ZohoBooks_delete_invoice",
                 "ZohoBooks_mark_invoice_void", "ZohoBooks_write_off_invoice", "ZohoBooks_create_customer_payment",
                 "ZohoBooks_match_bank_transaction", "ZohoBooks_categorize_bank_transaction",
                 "ZohoBooks_approve_bill", "ZohoBooks_delete_bill", "ZohoBooks_convert_purchase_order_to_bill",
                 "ZohoBooks_add_contact_bank_account", "ZohoBooks_generate_invoice_payment_link",
                 "ZohoBooks_submit_bill", "ZohoBooks_mark_bill_open", "ZohoBooks_mark_bill_void",
                 "ZohoBooks_delete_bill_payment", "ZohoBooks_apply_credits_to_bill"):
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
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
