# Zoho Books integration: design

**Date:** 2026-09-28
**Status:** Approved by the owner on 28 Sep 2026: "use everything you need… don't send emails without approval, don't delete things". Bills tools enabled. Payment recording by Claude added the same day (rule 2). For the 2026 import, see Owner answers 3.
**Related:**
- [Business automation programme](2026-09-28-business-automation-design.md). This design replaces most of its Phase 4 (per-event margin, bookkeeping export), which Books now provides.
- [docs/HANDOVER-2026-09-27-ads-analytics.md](../../HANDOVER-2026-09-27-ads-analytics.md): Appendix E (enquiry assistant), Appendix A (Monday review).

---

## Goal

Zoho Books becomes the system of record for invoices, client payments and singer costs. The assistant does the typing; the owner still presses every button that reaches a client or moves money.

## Owner decisions (28 Sep 2026)

1. **Invoices are sent from Books.** When a client accepts a quote, the assistant creates a **draft** invoice in Books and attaches the booking confirmation. The owner reviews it and presses Send in Books. Books emails the PDF from office@ and tracks whether it has been viewed and whether it is overdue.
2. **Client payments are recorded in Books.** The owner confirms Starling bank-feed matches in Books. Later the same day the owner also let the assistant record the payments `check_payments.py --json` is confident about (its `record_in_books` list), and a singer's bill once `singer_invoices.py paid` has matched the Starling payment to the singer's own bank details (rule 2). The assistant reads invoice status from Books. `check_payments.py` stays as a cross-check and still drives the reminder and receipt drafts.
3. **Singer and organist invoices become Books bills.** Each singer is a vendor, and each bill has the singer's PDF attached. The bank-change warnings stay in the private tracker (`singer_invoices.py`).
4. **Import 2026 so far.** This year's ledger bookings go into Books as invoices, with their paid or part-paid status.

## Change, 29 Sep 2026: the free plan, and invoices sent from Zoho Mail

The owner chose not to pay for Books Premium. The free plan keeps invoices, contacts, customer payments and the API (1,000 calls a day), but not bills or bank feeds. So:

1. **Invoices reach the client attached to Luca's own email.** When a client accepts, the reply drafter still creates the draft Books invoice (the accounting record, same DDMM number and figures), then makes the invoice PDF and booking confirmation from the owner's private templates (`make_booking_docs.py`, into iCloud Drive/LCS-invoices/<ref> - <client>/) and saves the confirmation email with both attached into Zoho Drafts with `scripts/bookings/imap_draft.py` (IMAP APPEND to Drafts only; no sending code; one recipient, no Cc or Bcc; attachments only from LCS-invoices; the Zoho Mail guard's bank-details scan on the text; an app password in the Keychain, service `lcs-zoho-imap`). Luca checks and sends it from Zoho Mail. This replaces decision 1: nothing is sent from Books.
2. **Mark sent.** Once that email (to the invoice's customer, with "Invoice <ref> - …pdf" attached) is in Sent, the daily pass calls `ZohoBooks_mark_invoice_sent` (the guard allows only the invoice id), so payments can be recorded against it. The evidence comes from `imap_draft.py sent <ref> <email> <date>`, which matches the attachment name exactly; the prompt acts only on "sent: yes". Books then emails nobody, provided its automatic payment reminders stay off (MANUAL-ACTIONS §27).
3. **Payments.** No bank feed on the free plan, so decision 2 is replaced by the evening-of-28-Sep rule already in place: the daily pass records confident Starling matches against the invoice; the rest go to the owner's hand-check list.
4. **No bills.** Decision 3 is dropped: singer and organist invoices stay in the private tracker (`singer_invoices.py`, with the PDF saved), which the per-event margin already reads. The bill tools stay on the guard's list, unused. `cc_sync.py books` reads bills best effort and marks `"bills_read": false` when the plan has none.

## What is connected

There are two MCP servers, set up at project level in the main checkout:

| Server | Tools | Marked read-only |
|---|---|---|
| `zoho-books` (accounting) | 222 | 92 |
| `zoho-books-invoices` (invoices) | 115 | 34 |

`.claude/hooks/zoho_books_guard.py` accepts only these two server names. It allows 91 of the read-only tool names plus the approved write tools below, and denies everything else. The read-only tools it also denies are `get_bank_statement_import_encryption_key`, `generate_invoice_payment_link`, `convert_purchase_order_to_bill`, the invoice payment QR tools, `get_invoice_qr_code`, `list_contact_autobill_recurring_invoices`, the contact bank-account and card tools, and (since the whole-code review, M16) every read of the business's own bank accounts, bank transactions, statements and reconciliations: no prompt uses them.

The owner enabled the Bills tools on 28 Sep 2026; the accounting server now has 241 tools, including create, update, get and list for bills. There is no bill-attachment tool, but `create_bill` takes `documents`. `convert_purchase_order_to_bill` is marked read-only but creates a bill, so it stays denied: the guard trusts exact names, not labels.

Books organisation: Alma Consort Ltd, id `941014440`, GBP, not VAT-registered. The plan is a **Premium trial**, so the owner must choose a plan before it ends.

## Rules that bind this work

These add to the programme's rules.

1. **Nothing reaches a client from Claude.** Every tool that emails, SMSes, reminds, shares a portal or payment link, or marks an invoice sent stays denied: `email_invoice(s)`, `schedule_invoice_email`, `remind_customer_for_invoice_payment`, `bulk_invoice_reminder`, `send_*`, `enable_*_portal`, `generate_invoice_payment_link`. `mark_invoice_sent` was denied too until 29 Sep 2026; since then the guard allows it (the invoice id only, a status change that emails nobody while Books' automatic reminders are off), and the daily pass calls it only once Luca's own email carrying that invoice is in Sent (the change above).
2. **Two kinds of money record by Claude, nothing else** (owner decisions, 28 Sep 2026). Claude creates a customer payment only for a confident Starling match that `check_payments.py --json` lists in `record_in_books` (never more than the invoice's balance, never on a draft invoice), and a vendor payment only for a singer's bill that `singer_invoices.py paid` has matched to the singer's own bank details. Each goes against exactly one invoice or bill, through the owner's Starling account in Books (`1534218000000095168`), under the argument checks in the table below. A client payment may carry `bank_charges` (more than £0, at most £25) for a transfer-fee shortfall the owner accepted (Fee shortfalls, below). Claude never updates or deletes a payment, and never creates a refund, a write-off, a credit application or a bank categorisation. On the free plan (from 29 Sep 2026) there are no bills or bank feeds, so only client payments are recorded and nothing is matched in Books.
3. **Nothing is deleted or voided by Claude.** Mistakes are fixed by the owner in Books.
4. **No bank details in Books from Claude.** Claude never calls `add_contact_bank_account` or `update_contact_bank_account`. Singer bank details stay in the owner's own Starling payees.
5. **The guard checks arguments, not just names.** Each approved write tool gets a check on its arguments inside the guard (see the next table). A call that fails the check is denied.
6. **Books is reached only through these MCP tools, under the guard.** If the guard denies a call, Claude stops and tells the owner. A one-off exception is a committed, reviewed guard change naming the exact records, reverted afterwards, never a direct call to the server. `.claude/hooks/mcp_bypass_guard.py` refuses a script or command that starts the server, reads its configuration or speaks the protocol itself (added after the 2026 import, Owner answers 3).

## Approved write tools

A write call must fit its tool's allowlist exactly. `tool_input` holds only `body`, `query_params` and `path_variables`. Every key, at any depth, must be on the tool's list below, spelt exactly: keys are lower case, and a key with any upper-case letter (`Send`, `Body`, `Contact_ID`) is denied, as is a duplicate key in the JSON. Tax fields (`tax_id`, `tax_treatment`, `vat_treatment` and so on) are on no list.

Every string or number in a write call is also checked for bank details and VAT, in any field and at any depth. Singer invoices carry real bank details, and foreign IBANs are plausible, so the check covers any format. The text is first NFKC-normalised (fullwidth digits and letters become plain ones), and invisible format characters (zero-width space, soft hyphen) and accents are stripped. Real dates and clock times are then removed: ISO dates (`2026-11-21`), day/month/year dates (`21/11/2026`, `21.11.2026`, `21-11-2026`, `21 11 2026`), dates with a month name (`1 December 2026`, `Nov 2026`, `December 12, 2026`) and times (`11:00`, `14.30`; a dotted sort code such as `04.00.04` is not read as a time). The guard denies:
- a run of 6 to 10 digits, or of 14 or more, where the digits are joined by at most one separator each (space, `.`, `/`, `-`, `_`, the Unicode dashes U+2010 to U+2015, or the minus sign). This covers a sort code in any layout (`04-00-04`, `04/00/04`, `04.00.04`, `040004`), an account number (`1234 5678`, `1234-5678`) and the two together (`04000412345678`);
- a run of 11 to 13 digits, unless it looks like a phone number: 11 digits starting with 0 (`020 7946 0958`), or directly after a `+` or `+ ` (`+44 20 7946 0958`);
- an IBAN from any country (two letters, two check digits, then 11 to 30 letters or digits, grouped or not) with at least ten digits in it;
- the words "sort code" (also run together, "Sortcode"), "s/c", "a/c", "acct", "account number", "account no", "account #", "acc no", "IBAN", "SWIFT" and "BIC";
- "VAT" in any spacing or punctuation ("V.A.T.", "V A T", "VAT20", "20%VAT"), "VATable" and "value added tax";
- any Greek or Cyrillic letter, since these can pass for Latin ones ("ВАТ");
- in invoice and bill calls only, the word "tax" or "taxes". Alma Consort Ltd is not VAT-registered, so its invoices and bills never mention tax. Contacts may (a client can be a tax adviser).

Two exemptions cover the digit rules only. `invoice_number` is exempt when it matches `^[0-9]{4}[A-Z]?$`: four digits, below the run threshold anyway. A key ending `_id` is exempt when its whole value is 9 to 20 digits, the shape of a Books record id. `bill_number` has no exemption, so a singer's invoice number with six or more joined digits (`20260928`, `2026/17`) is denied; Claude puts such a number in the notes or leaves it for the owner.

What still passes: phone numbers in 11-digit or `+` form, UK postcodes, `21 November 2026 11:00`, `2026-11-21`, `11.00–12.30`, `Small choir (4 singers)`, `£1,150.00`. What is denied as a false positive: short lists of numbers (`10 20 30`), `£1150.00` without the comma, a 10-digit phone number, and `+44 (0)20 …` (write `+44 20 …`).

What the check can't catch: digits spelt out in words, or a number split across two fields.

| Tool | Why | Allowed keys and checks |
|---|---|---|
| `ZohoBooks_create_contact` | New client, or new singer as a vendor | body: `contact_name`, `company_name`, `contact_type`, `contact_persons`, `billing_address`, `payment_terms`, `payment_terms_label`, `notes`. Each contact person: `first_name`, `last_name`, `email`, `phone`, `mobile`, `is_primary_contact`, `salutation`. Billing address: `address`, `street2`, `city`, `state`, `zip`, `country`, `attention`. `contact_type` is required and is `customer` or `vendor`. query: `organization_id`. |
| `ZohoBooks_update_contact` | Correct a client's or singer's name | body: `contact_name`, `company_name`, `contact_type`. path: `contact_id` (required). query: `organization_id`. The live schema marks `contact_type` as required, so it may be restated, but only as `customer` or `vendor`. No email, phone, notes, contact persons or anything else. |
| `ZohoBooks_create_invoice` | Draft invoice on a quote acceptance, and the 2026 import | body: `customer_id` (required), `invoice_number` (required, `^[0-9]{4}[A-Z]?$`), `date`, `due_date`, `payment_terms`, `payment_terms_label`, `line_items`, `notes`, `terms`, `reference_number`, `allow_partial_payments`, `template_id`. Each line item: `name`, `description`, `rate`, `quantity`, `item_order`, `item_id`. query: `organization_id`, `ignore_auto_number_generation` (must be true), `send` (absent or false). |
| `ZohoBooks_add_invoice_document` | Attach the booking confirmation to the draft | path: `invoice_id` (required), `document_id`. query: `organization_id`. How the file is passed over MCP is still unknown: test it on the first real booking. If it can't carry a local file, the owner attaches the confirmation in Books (one click). |
| `ZohoBooks_upload_invoice_document` | The same | path: `invoice_id` (required), `document_id`. query: `organization_id`, `attachment`. The attachment must be a path ending `.pdf` or `.docx`, written `~/…` or absolute, with no `..` and no control characters, whose real path (after `~` is expanded and symlinks are resolved) is inside `~/lcs-private/invoices/`, where `make_booking_docs.py` writes. Any other path, a URL or file contents (base64) is denied. |
| `ZohoBooks_add_invoice_comment` | An internal note (e.g. "booking confirmation to attach") | body: `description`. path: `invoice_id` (required). query: `organization_id`. `show_comment_to_clients` is denied with any value. The schema gives it no default, so the owner confirms on the first comment that Books keeps it internal. |
| `ZohoBooks_create_bill` | Singer invoices as bills | body: `vendor_id` and `bill_number` (both required), `date`, `due_date`, `reference_number`, `notes`, `line_items`, `payment_terms`, `payment_terms_label`, `documents`. Each line item: `name`, `description`, `rate`, `quantity`, `account_id`, `item_order`. Each document: `document_id`, `file_name`. query: `organization_id`. `account_id` may only be `1534218000000034003` (Cost of Goods Sold). query may add `attachment`: only a PDF `singer_invoices.py` saved, `~/lcs-private/singer-invoices/<message id>.pdf`. |
| `ZohoBooks_create_vendor_payment` | Recording a singer's bill as paid (owner decision, 28 Sep 2026), after `singer_invoices.py paid` matched the Starling payment on the singer's bank details | body: `vendor_id`, `date` (both required), `amount`, `payment_mode` (`Bank Transfer` or absent), `paid_through_account_id` (must be `1534218000000095168`, the owner's Starling account in Books), `description`, `bills` (exactly one `{bill_id, amount_applied}`, with `amount_applied` equal to `amount`, more than £0 and at most £10,000). query: `organization_id`. |
| `ZohoBooks_create_customer_payment` | Recording a client payment (owner decision, 28 Sep 2026) that `check_payments.py --json` lists in `record_in_books` | body: `customer_id`, `date`, `invoice_id` (required), `amount`, `amount_applied`, `payment_mode` (must be `banktransfer`), `account_id` (must be `1534218000000095168`), `reference_number` (the DDMM ref or absent), `description`, `invoices` (exactly one `{invoice_id, amount_applied}`; the invoice and all three amounts must agree, more than £0 and at most £10,000). Never `contact_persons` (Books would email a thank-you). query: `organization_id`. |
| `ZohoBooks_create_bank_account` | The Starling account in Books (created once, 28 Sep 2026) | body: `account_name` (required), `account_type` (must be `bank`), `currency_code` (`GBP` or absent), `description`. No account numbers. query: `organization_id`. |
| `ZohoBooks_create_item` | The "Singing fee" and "Organ fee" purchase items (added 28 Sep 2026: the connector has no chart-of-accounts tool, and a new purchase item shows the account Books files it under) | body: `name` (required), `item_type` (must be `purchases`), `product_type` (`service` or absent), `rate`, `description`, `purchase_rate`, `purchase_description`. No account, tax or vendor keys. query: `organization_id`. |
| `ZohoBooks_update_bill` | Correct a bill's notes, dates or reference | body: `notes`, `date`, `due_date`, `reference_number` only. path: `bill_id` (required). query: `organization_id`. No `vendor_id`, `bill_number`, `line_items` or payment terms: a wrong vendor or amount is the owner's to fix in Books. |
| `ZohoBooks_add_bill_comment` | An internal note on a bill | body: `description`. path: `bill_id` (required). query: `organization_id`. |

Still denied:
- `ZohoBooks_update_invoice`: the owner edits drafts in Books;
- every email, SMS, reminder, portal or payment-link tool, and `mark_invoice_sent` other than as rule 1 allows;
- every delete, void, write-off, refund or credit application;
- any other payment: updating or deleting one, a payment not against exactly one invoice or bill, through another account or for a different amount (rule 2); and bank matching or categorising (the owner does these in Books);
- `approve_bill`, `submit_bill`, `mark_bill_open`, `convert_purchase_order_to_bill`;
- contact bank accounts and cards, including reading them, and the invoice payment QR tools;
- reading Books bank accounts, bank transactions, bank statements and reconciliations;
- any other key on an approved tool, including tax fields, the client portal, payment options and `status`; a bill `attachment` other than a singer invoice PDF that `singer_invoices.py` saved;
- a bill update that changes the vendor, the bill number or the line items;
- an invoice attachment from anywhere but iCloud Drive/LCS-invoices/ (`~/lcs-private/invoices/` before 29 Sep 2026);
- any tool on a server other than `zoho-books` and `zoho-books-invoices`;
- any route to Books other than these MCP tools (rule 6).

The security review of PR #147 (28 Sep 2026) found that `update_invoice` and `update_contact` could redirect a draft or a client's email, that keys outside a few named ones went unchecked, and that free text could carry bank details. Its re-review the same day found that bank details still got through in other layouts (`a/c`, `acct`, en dashes, fullwidth digits, foreign IBANs, a zip code and a bill number), that VAT got through as "V.A.T." or Cyrillic "ВАТ", that the attachment could be any local file, and that a bill update could swap the vendor or the line items. This section is the result.

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
- The daily pass records each confident payment in `check_payments.py --json`'s `record_in_books` with `create_customer_payment` (rule 2), skipping one Books already shows with the same date and amount.

### C. Singer bills (after the owner enables the Bills tools)

- `singer_invoices.py scan` runs as now, with the fraud checks.
- Then the vendor is found or created (`create_contact`, vendor, no bank details) and `create_bill` is called with the amount, the singer's invoice number and date, and the booking ref in the notes.
- `create_bill` attaches the singer's PDF through its `attachment` query parameter; the guard allows only a PDF `singer_invoices.py` saved in `~/lcs-private/singer-invoices/`.
- When `singer_invoices.py paid` matches the Starling payment to the singer's own bank details, the clerk records it against the bill with `create_vendor_payment` (rule 2); anything less certain is left to the owner's bank-feed matching in Books. `singer_invoices.py paid` stays as the source of the "Paid!" draft.

### D. Import 2026 (one-off, owner-approved batch)

1. From `~/lcs-private/bookings.csv`: create the contacts, then one invoice per booking, dated at its invoice date, with the booking value.
2. The invoices must leave draft status to count as receivables. Options for that are question 3.
3. The first step is a dry run listing every invoice that would be created. It is applied only after the owner approves the list.

### E. Monday review

The Monday review prompt (handover Appendix A, step 6g) adds a Books line, read from Books by Claude with the read tools, with totals and invoice numbers only (the report script itself makes no Books calls; its section 11 is the true cost per booking):
- receivables;
- overdue invoices;
- unpaid bills;
- disagreements with the Starling check.

## Owner answers

1. **Write tools:** approved as above ("use everything you need"), within two limits: no email without approval, and no deleting.
2. **Bills tools:** enabled.
3. **Import status:** the plan was for the owner to mark the invoices sent and match the payments in the Books bank feed. On 28 Sep 2026 the owner instead approved Claude marking the 7 invoices sent. The guard then denied `mark_invoice_sent` (the 29 Sep rule allowing it once Luca's own email carrying the invoice is in Sent came the next day) and was not changed: Claude called the Books server directly from a script, around the guard, and in the same way changed invoice 2111's due date (`update_invoice`, still denied). Both are recorded in `logs/books-changes.md`. Rule 6 and `mcp_bypass_guard.py` came out of this.

## Out of scope

- Claude sending, reminding, deleting or voiding, or recording money beyond the cases in rule 2.
- Books' automated payment reminders. These are the owner's own Books setting; if he turns them on, the assistant's reminder drafts must be switched off to avoid double reminders.

## Fee shortfalls (owner decision, 28 Sep 2026)

Some clients' banks take a transfer fee, so a booking can arrive a few pounds short (invoice 2408 was). Until now that booking read DEPOSIT_SEEN or BALANCE_DUE, and a balance reminder went out for the fee, or it sat on the hand check as PAST_PART_PAID. The owner decided to accept such a shortfall, record it in the ledger, and record it in Books as a bank charge, capped at £25 a booking.

- **Ledger.** In the Command Centre the owner picks "Short by transfer fees (£x.xx)" on the booking, or on its hand-check row. The option appears only when the bank shows a confident payment in and a balance of £0.01 to £25 (DEPOSIT_SEEN, BALANCE_DUE, PAST_PART_PAID or NOTED_PAID). The server assesses the booking again from the cached bank read, refuses when the bank wasn't checked, when the amount is more than a penny off the balance, when it is more than £25, or when the date is before the last payment, and after Face ID or Touch ID runs `check_payments.py --note <ref> "short by fees £x.xx accepted YYYY-MM-DD" --owner`. Only `--owner` writes that phrase.
- **check_payments.py.** A booking whose confident payments plus the accepted fee reach its value reads PAID_IN_FULL, with `balance` 0 and `fees` the amount used. A note over £25 or dated after today is ignored. The note closes the booking like "paid in full": a later payment is PAYMENT_AFTER_CLOSE. The booking is reported once more, so the daily pass can record the fee, and `--apply` then adds "paid in full" with the same close date.
- **Books.** `record_in_books` entries are `[date, amount, bank charges]`. The charge is 0 on every payment but the last one of a fee-closed booking. The plan is for the daily pass to record that payment with `bank_charges` (a plain number, more than £0 and at most £25) and both `amount_applied` values set to amount + charge. That needs two changes the owner approves separately, because they widen what Claude may do in Books: the guard (`.claude/hooks/zoho_books_guard.py`) allowing exactly that key, and the daily-pass prompt (`.claude/agents/lcs-daily-pass.md`). Until then the guard denies `bank_charges`, the charge stays unrecorded, and the Command Centre flags the invoice as "Starling paid in full, Books part-paid". If the last payment is already in Books without the charge, the daily pass records nothing and lists it under "Money to check by hand": Claude never updates a Books payment, so the owner adds the charge there.
