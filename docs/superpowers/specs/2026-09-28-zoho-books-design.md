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

`.claude/hooks/zoho_books_guard.py` allows exactly the 121 read-only tool names and denies everything else. The two exceptions it also denies are `get_bank_statement_import_encryption_key` and `generate_invoice_payment_link`.

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

| Tool | Why | Argument checks in the guard |
|---|---|---|
| `ZohoBooks_create_contact` (invoices server) | New client, or new singer as a vendor | `contact_type` is `customer` or `vendor`. No portal (`is_portal_enabled` absent or false, and no contact person with `enable_portal`). No `opening_balances`, and no bank or card fields. |
| `ZohoBooks_create_invoice` | Draft invoice on a quote acceptance, and the 2026 import | `send` absent or false, in both the body and `query_params`. `invoice_number` matches `^\d{4}[A-Z]?$` with `ignore_auto_number_generation=true`. No `batch_payments` and no `payment_options.payment_gateways`. `customer_id` present. |
| `ZohoBooks_add_invoice_document` / `ZohoBooks_upload_invoice_document` | Attach the booking confirmation to the draft | `invoice_id` present. How the file is passed over MCP is still unknown: test it on the first real booking. If it can't carry a local file, the owner attaches the confirmation in Books (one click). |
| `ZohoBooks_update_contact` | Correct a client's or singer's name or email | The same checks as `create_contact`. |
| `ZohoBooks_update_invoice` | Fix a draft before the owner sends it | The same body checks as `create_invoice`, and `invoice_id` present. |
| `ZohoBooks_add_invoice_comment` | An internal note (e.g. "booking confirmation to attach") | `show_comment_to_clients` absent or false. |
| `ZohoBooks_create_bill`, `ZohoBooks_update_bill` | Singer invoices as bills | `vendor_id` present; `bill_number` present on create; no `approvers`, `purchaseorder_ids` or payment fields. |
| `ZohoBooks_add_bill_comment` | An internal note on a bill | None. |

Still denied:
- every email, SMS, reminder, portal or payment-link tool, and `mark_invoice_sent` (the owner's click);
- every delete, void, write-off, refund or credit application;
- customer and vendor payments, and bank matching or categorising (the owner does these in Books);
- `approve_bill`, `submit_bill`, `mark_bill_open`, `convert_purchase_order_to_bill`;
- contact bank accounts and cards.

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
- The PDF is attached to the bill if the upload works.
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
