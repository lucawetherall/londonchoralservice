# Singer invoices: several invoices in one email

**Date:** 2026-10-02
**Status:** Approved for implementation. The owner asked whether the enquiry assistant needed updating after paying two invoices that a singer had sent in one email, and replied "make fixes" to the proposal below.

## Problem

`scripts/bookings/singer_invoices.py` keeps one row per email, keyed by the Zoho message id. `read_invoice` reads every PDF, .docx and the body, but takes the amount and reference from the first source that has one. Three real emails show what goes wrong:

1. **Two invoices in one email (1 Oct 2026).** Two PDFs, each saying "invoice", for the same amount and two different events and no reference numbers. Only the first was recorded. The second payment went unmatched: no bank-details check, no "Paid!" thanks, and the per-event margin and the Monday figures miss the cost.
2. **Two numbered invoices in one email (28 Aug 2026).** Two PDFs with their own invoice numbers and different amounts. It was sent before the tracker started, but it would have hit the same problem.
3. **An expense receipt sent with an invoice (Mar 2026).** A taxi receipt PDF came first, and its text also says "invoice". Today the tracker would record the receipt's figure as the invoice and save the receipt as the invoice PDF. The real invoice already includes that taxi fare as a line item.

## Design

### Which attachments are invoices

An invoice that is wrongly split costs more than one that is missed. A phantom row can be paid, so the first invoice is chosen as before, and a further one has to clear a high bar. Only attachments with readable text and an amount (`extract`) count. `classify_documents` sorts them into three groups.

**Receipts** are part of an invoice, not invoices of their own. An attachment is a receipt when:
- its file name says "receipt"; or
- it carries no bank details and its amount is a line on a larger document (a taxi receipt the invoice already includes).

**The first invoice** is the first other attachment with an amount whose file name doesn't say statement, terms or remittance. That is exactly what the tracker always took, except that a receipt no longer wins (problem 3).

**A further invoice** must:
- not be a copy of an invoice already taken. A copy has the same amount and the same reference, the same text, or the same file stem as .pdf and .docx; the PDF is kept.
- have "invoice" in its file name, or an invoice heading (a line starting "Invoice" or "Tax invoice");
- and have "invoice" in its file name, a reference of its own, or bank details of its own.

With three or more invoices, one whose amount is the others' total is a statement.

Every other attachment with an amount (terms, statements, a fee note beside a taxi invoice) is **doubtful**. It is never recorded; the first invoice gets the warning "<file> (£x) may be another invoice: check it by hand". A receipt not named as one gets "read as a receipt included in the invoice: check by hand if it is an invoice of its own".

`split_sources` returns one source list per invoice:
- **One invoice:** all the sources, the invoice first and receipts last.
- **Several:** each invoice's document first, then the attachments with no amount (a bank-details sheet), then the body. Bank details may come from the extras or the body, but each invoice's reference and dates come from its own document alone, so the body can't give two invoices one booking link. The existing logic is renamed `read_sources`.

Each invoice's warnings start with "invoice k of n in this email (<file name>)". `rescan` and `pdf` find a part again by that file name, so a later change to the rules can't swap two rows.

Checked against real mail before release:
- the two-invoice email of 1 Oct reads as two invoices, each with its own event date;
- the 28 Aug email reads as its two numbered invoices;
- the March email reads as the invoice's own total, not the taxi fare;
- seven single-invoice emails already in the tracker read exactly as recorded: amount, reference and bank details.

### Ids

- The first invoice keeps the email's message id.
- The k-th (k ≥ 2) is `<message id>-<k>`.
- `email_id(id)` gives back the message id. It only splits an all-digit id with a numeric suffix, which is how Zoho message ids look.

The state log (`ID_RE`) and the Command Centre (`MESSAGE_ID_RE`, `invoice_key`) already accept `-` and treat the id as opaque, so neither changes. Only what talks to Zoho or names files uses `email_id`: fetching (`rescan`, `pdf`), the PDF file, and the clerk's reply.

- **Bill number:** `bill_number` gives a part `SI-<last 5 digits of the email id><letter>` (B for the second invoice, C for the third) when the singer's own reference is unusable. That keeps the digit run at 5 for the Books guard.
- **PDF:** each invoice's own PDF is saved as `<id>.pdf`, so the second invoice is `<message id>-2.pdf`. The `-` is kept in the file name, so `123-2` can never collide with an email `1232`. A single-invoice email saves its invoice document, not the first PDF it finds.

### Commands

- **`scan`:**
  - records every invoice in the email under one lock, assessing each against the rows before it, so a second invoice with different bank details raises BANK DETAILS CHANGED as usual;
  - prints one block per invoice, each headed `invoice k of n: <id>` when there are several;
  - refuses a part id (`<id>-2`): scan the email's id;
  - on an already-recorded email, reprints every recorded invoice of that email.
- **`more <message id> [--fetch | file]`** (new): records any further invoices in an email recorded with only its first, before this change. It never touches the first invoice's row, and refuses if the email's first invoice no longer has the recorded amount. The clerk doesn't run it.
- **`rescan <id>`** and **`pdf <id>`**: fetch `email_id(id)` and use invoice k of that email.
- **`paid`:**
  - Matching is unchanged: invoices oldest first, and one payment settles one invoice, so two equal invoices from one singer take one payment each.
  - A hit for an invoice in a multi-invoice email prints `PAID <id>: … (invoice k of n in this email: thanked together once all are paid)` instead of `NEWLY PAID`. The enquiry assistant passes only NEWLY PAID and THANKS DUE lines to the clerk, so one email never gets two "Paid!" drafts from one run. The PAID line never contains either of those tokens.
  - An email whose other invoices are all withdrawn has one live invoice, and takes the ordinary NEWLY PAID route.
- **THANKS DUE:**
  - For a multi-invoice email it is one line, under the message id, and only when every invoice not withdrawn is paid to verified details;
  - the most recently paid of them must have been paid in the last 7 days and carry the "thanks due" mark;
  - none of them may already be thanked.
  - The amount is the total. This run's PAID hits are not skipped, so with `--apply` the same run can list it.
- **A part matched by name only, or settled by hand:** the email gets no THANKS DUE. Its PAID line says "check before thanking", as for a single invoice, and Luca thanks by hand.
- **`thanked <id>`:** under one lock, notes the reply on the given invoice and every other paid invoice in its email, with one fact per invoice.
- **Enquiry assistant prompt (Appendix E step 3, and the live task):** a PAID line without "check before thanking" is only a note.

### The clerk (`.claude/agents/lcs-singer-clerk.md`)

- A scan can print several blocks: treat each as an invoice of its own and use its id for `link`, `rescan` and `withdrawn`.
- An id `<message id>-<k>` is invoice k in that email: find or reply to the email by the part before `-`.
- A THANKS DUE line for an email with several invoices gets one "Paid!" draft, then `thanked <id as given>`.

## Out of scope

- Splitting a payment that covers two invoices in one transfer: today it is reported, not matched, and that doesn't change.
- Emails recorded before this change other than the 1 Oct one. `more` handles them if they turn up; the 28 Aug email predates the tracker.

## Testing

New tests in `tests/test_singer_invoices.py` use synthetic invoices (no real names or numbers):
- `split_sources` on two invoices; on a receipt plus an invoice; on a .pdf and .docx copy; on an invoice plus a bank-details sheet; on an invoice in the body only;
- `scan` recording two rows with their own links and PDFs;
- `more` adding the second row to an email recorded with one;
- `rescan` and `pdf` on a part id;
- `paid` printing PAID lines and one THANKS DUE when both are paid, none while one is unpaid;
- `thanked` marking both;
- `bill_number` for part ids;
- a part id refused by `scan`.

All existing tests still pass.
