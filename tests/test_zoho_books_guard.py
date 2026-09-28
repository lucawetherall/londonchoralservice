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
                 "ZohoBooks_create_invoice", "ZohoBooks_update_invoice", "ZohoBooks_delete_invoice",
                 "ZohoBooks_mark_invoice_void", "ZohoBooks_mark_invoice_sent", "ZohoBooks_write_off_invoice",
                 "ZohoBooks_remind_customer_for_invoice_payment", "ZohoBooks_create_customer_payment",
                 "ZohoBooks_fetch_invoice_einvoice", "ZohoBooks_generate_invoice_payment_link",
                 "ZohoBooks_get_bank_statement_import_encryption_key", "ZohoBooks_add_contact_bank_account",
                 "ZohoBooks_categorize_bank_transaction", "ZohoBooks_send_contact_sms", "unknown_tool"):
        assert decide("zoho-books-invoices", name) == "deny", name


def test_every_non_read_only_tool_seen_on_28_sep_is_denied():
    # The write tools both servers listed on 28 Sep 2026 (tools/list without readOnlyHint).
    for name in NON_READ_ONLY:
        assert decide("zoho-books", name) == "deny", name


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
