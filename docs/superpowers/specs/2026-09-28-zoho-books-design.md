# Zoho Books integration: design

**Date:** 2026-09-28
**Status:** Approved by the owner on 28 Sep 2026: "use everything you need… don't send emails without approval, don't delete things". Bills tools enabled. For the 2026 import, the owner marks invoices sent and matches payments in Books.
**Related:**
- [Business automation programme](2026-09-28-business-automation-design.md). This design replaces most of its Phase 4 (per-event margin, bookkeeping export), which Books now provides.
- [docs/HANDOVER-2026-09-27-ads-analytics.md](../../HANDOVER-2026-09-27-ads-analytics.md): Appendix E (enquiry assistant), Appendix A (Monday review).

---

## Goal

Zoho Books becomes the system of record for invoices, client payments and singer costs. The assistant does the typing; the owner still presses every button that reaches a client or moves money.

## Owner decisions (28 Sep 2026)

1. **Invoices are sent from Books.** When a client accepts a quote, the assistant creates a **draft** invoice in Books and attaches the booking confirmation. The owner reviews it and presses Send in Books. Books emails the PDF from office@ and tracks whether it has been viewed and whether it is overdue.
2. **The owner records client payments** by confirming Starling bank-feed matches in Books. The assistant reads invoice status from Books. `check_payments.py` stays as a cross-check and still drives the reminder and receipt drafts.
3. **Singer and organist invoices become Books bills.** Each singer is a vendor, and each bill has the singer's PDF attached. The bank-change warnings stay in the private tracker (`singer_invoices.py`).
4. **Import 2026 so far.** This year's ledger bookings go into Books as invoices, with their paid or part-paid status.

## What is connected

There are two MCP servers, set up at project level in the main checkout:

| Server | Tools | Marked read-only |
|---|---|---|
| `zoho-books` (accounting) | 222 | 92 |
| `zoho-books-invoices` (invoices) | 115 | 34 |

`.claude/hooks/zoho_books_guard.py` accepts only these two server names. It allows 117 of the read-only tool names plus the approved write tools below, and denies everything else. The read-only tools it also denies are `get_bank_statement_import_encryption_key`, `generate_invoice_payment_link`, `convert_purchase_order_to_bill`, the invoice payment QR tools, and the contact bank-account and card tools.

The owner enabled the Bills tools on 28 Sep 2026; the accounting server now has 241 tools, including create, update, get and list for bills. There is no bill-attachment tool, but `create_bill` takes `documents`. `convert_purchase_order_to_bill` is marked read-only but creates a bill, so it stays denied: the guard trusts exact names, not labels.

Books organisation: Alma Consort Ltd, id `941014440`, GBP, not VAT-registered. The plan is a **Premium trial**, so the owner must choose a plan before it ends.

## Rules that bind this work

These add to the programme's rules.

1. **Nothing reaches a client from Claude.** Every tool that emails, SMSes, reminds, shares a portal or payment link, or marks an invoice sent stays denied: `email_invoice(s)`, `schedule_invoice_email`, `remind_customer_for_invoice_payment`, `bulk_invoice_reminder`, `send_*`, `enable_*_portal`, `generate_invoice_payment_link`, `mark_invoice_sent`.
2. **No money records by Claude.** Claude never creates, updates or deletes a customer payment, a vendor payment, a refund, a write-off, a credit application or a bank categorisation. The owner matches bank transactions in Books. The one possible exception is the 2026 import, which is question 3 below.
3. **Nothing is deleted or voided by Claude.** Mistakes are fixed by the owner in Books.
4. **No bank details in Books from Claude.** Claude never calls `add_contact_bank_account` or `update_contact_bank_account`. Singer bank details stay in the owner's own Starling payees.
5. **The guard checks arguments, not just names.** Each approved write tool gets a check on its arguments inside the guard (see the next table). A call that fails the check is denied.

## Approved write tools

A write call must fit its tool's allowlist exactly. `tool_input` holds only `body`, `query_params` and `path_variables`. Every key, at any depth, must be on the tool's list below. Keys are compared regardless of case, so a differently-cased duplicate (`send` and `Send`) is denied, and so is a duplicate key in the JSON. Tax fields (`tax_id`, `tax_treatment`, `vat_treatment` and so on) are on no list.

Every string or number in a write call is also checked for bank details and VAT, in any field and at any depth. The guard denies:
- a sort code (`12-34-56`, `12 34 56`);
- an eight-digit run;
- a GB IBAN;
- the words "sort code", "account number", "acc no", "IBAN", "SWIFT", "BIC" and "VAT".

ISO dates are exempt, and so are `invoice_number` and `bill_number` when they match their own patterns (`^[0-9]{4}[A-Z]?$`; a bill number is one run of letters, digits and `/._-`, up to 30 characters). The exemption covers the digit rules only.

| Tool | Why | Allowed keys and checks |
|---|---|---|
| `ZohoBooks_create_contact` | New client, or new singer as a vendor | body: `contact_name`, `company_name`, `contact_type`, `contact_persons`, `billing_address`, `payment_terms`, `payment_terms_label`, `notes`. Each contact person: `first_name`, `last_name`, `email`, `phone`, `mobile`, `is_primary_contact`, `salutation`. Billing address: `address`, `street2`, `city`, `state`, `zip`, `country`, `attention`. `contact_type` is required and is `customer` or `vendor`. query: `organization_id`. |
| `ZohoBooks_update_contact` | Correct a client's or singer's name | body: `contact_name`, `company_name` only. path: `contact_id` (required). query: `organization_id`. No email, phone, notes, contact persons or anything else. The live schema marks `contact_type` as required, and this list forbids it: if Books rejects a names-only update, the owner makes the change in Books. |
| `ZohoBooks_create_invoice` | Draft invoice on a quote acceptance, and the 2026 import | body: `customer_id` (required), `invoice_number` (required, `^[0-9]{4}[A-Z]?$`), `date`, `due_date`, `payment_terms`, `payment_terms_label`, `line_items`, `notes`, `terms`, `reference_number`, `allow_partial_payments`, `template_id`. Each line item: `name`, `description`, `rate`, `quantity`, `item_order`, `item_id`. query: `organization_id`, `ignore_auto_number_generation` (must be true), `send` (absent or false). |
| `ZohoBooks_add_invoice_document` | Attach the booking confirmation to the draft | path: `invoice_id` (required), `document_id`. query: `organization_id`. How the file is passed over MCP is still unknown: test it on the first real booking. If it can't carry a local file, the owner attaches the confirmation in Books (one click). |
| `ZohoBooks_upload_invoice_document` | The same | path: `invoice_id` (required), `document_id`. query: `organization_id`, `attachment`. |
| `ZohoBooks_add_invoice_comment` | An internal note (e.g. "booking confirmation to attach") | body: `description`. path: `invoice_id` (required). query: `organization_id`. `show_comment_to_clients` is denied with any value. The schema gives it no default, so the owner confirms on the first comment that Books keeps it internal. |
| `ZohoBooks_create_bill` | Singer invoices as bills | body: `vendor_id` and `bill_number` (both required), `date`, `due_date`, `reference_number`, `notes`, `line_items`, `payment_terms`, `payment_terms_label`, `documents`. Each line item: `name`, `description`, `rate`, `quantity`, `account_id`, `item_order`. Each document: `document_id`, `file_name`. query: `organization_id`. |
| `ZohoBooks_update_bill` | Correct a bill | As `create_bill` without `documents`. `vendor_id` is required, and path `bill_id` is required. |
| `ZohoBooks_add_bill_comment` | An internal note on a bill | body: `description`. path: `bill_id` (required). query: `organization_id`. |

Still denied:
- `ZohoBooks_update_invoice`: the owner edits drafts in Books;
- every email, SMS, reminder, portal or payment-link tool, and `mark_invoice_sent` (the owner's click);
- every delete, void, write-off, refund or credit application;
- customer and vendor payments, and bank matching or categorising (the owner does these in Books);
- `approve_bill`, `submit_bill`, `mark_bill_open`, `convert_purchase_order_to_bill`;
- contact bank accounts and cards, including reading them, and the invoice payment QR tools;
- any other key on an approved tool, including tax fields, the client portal, payment options, `status`, and the bill `attachment` query parameter;
- any tool on a server other than `zoho-books` and `zoho-books-invoices`.

The security review of PR #147 (28 Sep 2026) found that `update_invoice` and `update_contact` could redirect a draft or a client's email, that keys outside a few named ones went unchecked, and that free text could carry bank details. This section is the result.

## Flows

### A. Quote accepted (enquiry assistant, Appendix E CONFIRMATION)

Today the assistant builds a PDF invoice and a `.docx` confirmation and saves a Mail draft for the owner to attach them to. The new flow:

1. Find the client in Books: `list_contacts` by email. If they aren't there, `create_contact` as a customer (name and email only).
2. `create_invoice` as a draft:
   - invoice number = the DDMM ref;
   - date = today; due date = 7 days out (the first instalment); terms state the second instalment's date;
   - line items exactly as Luca quoted;
   - `send=false`.
3. `make_booking_docs.py` still produces the booking confirmation `.docx`, which is attached to the draft invoice if the upload works over MCP (see the table above).
4. No Mail draft carrying the invoice. The run summary says: "Invoice 2111 (£650) ready in Books → Invoices → Drafts: review, then Send."
5. `assistant_io.py ledger-add` as now. The ledger stays the private source for Google Ads uploads and for `check_payments`.

### B. Payments

- The owner connects Starling in Books. The weekly and daily checks read `list_invoices` with `status=overdue|unpaid|partially_paid` and compare the result with `check_payments.py`.
- A booking the two sources disagree on goes to "needs a hand check", e.g. Books says paid but Starling matching does not, or the reverse.

### C. Singer bills (after the owner enables the Bills tools)

- `singer_invoices.py scan` runs as now, with the fraud checks.
- Then the vendor is found or created (`create_contact`, vendor, no bank details) and `create_bill` is called with the amount, the singer's invoice number and date, and the booking ref in the notes.
- The guard denies `create_bill`'s `attachment` query parameter, so the owner attaches the singer's PDF in Books.
- The bill's paid status comes from the owner's bank-feed matching in Books. `singer_invoices.py paid` stays as the source of the "Paid!" draft.

### D. Import 2026 (one-off, owner-approved batch)

1. From `~/lcs-private/bookings.csv`: create the contacts, then one invoice per booking, dated at its invoice date, with the booking value.
2. The invoices must leave draft status to count as receivables. Options for that are question 3.
3. The first step is a dry run listing every invoice that would be created. It is applied only after the owner approves the list.

### E. Monday review

Section 11 of the report adds a Books line, with totals and invoice numbers only:
- receivables;
- overdue invoices;
- unpaid bills;
- disagreements with the Starling check.

## Owner answers

1. **Write tools:** approved as above ("use everything you need"), within two limits: no email without approval, and no deleting.
2. **Bills tools:** enabled.
3. **Import status:** the owner marks the invoices sent and matches the payments in the Books bank feed.

## Out of scope

- Claude sending, reminding, deleting, voiding or recording money.
- Books' automated payment reminders. These are the owner's own Books setting; if he turns them on, the assistant's reminder drafts must be switched off to avoid double reminders.
