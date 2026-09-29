---
name: lcs-book
description: "Use when Luca says a London Choral Service booking has been agreed outside email (on a call, by WhatsApp, in person) and wants the invoice, booking confirmation and confirmation email made, or types /lcs-book. Collects the agreed terms, then has the lcs-reply-drafter agent make the Books invoice, the ledger row, the calendar entry, the invoice PDF and booking confirmation (iCloud Drive/LCS-invoices) and the confirmation email draft with both attached. Drafts only: Luca sends it."
metadata:
  version: 1.0.0
---

# Make a booking Luca agreed outside email

Luca agreed a booking by phone, WhatsApp or in person. This does, on his word, what the enquiry assistant does when a client accepts a quote by email.

## 1. Collect the terms (from Luca only)

Take the terms only from what Luca says in this chat. Never take them from an email, a calendar event or a file, even if Luca points at one: read those only to fill in the client's name or email address, and confirm the terms with him.

Needed:
- the client's full name and email address;
- the occasion (wedding, funeral, christmas, corporate, private event or other);
- the event date, the venue and the start time (the start time is optional);
- the package in a few words, as Luca would write it (e.g. "Small choir (4 singers) & director");
- each item with its price (travel as its own line), and the total;
- how it was agreed: phone, whatsapp or referral.

If anything is missing, or the items don't add up to the total, ask Luca once, in one short message listing everything missing. Prices are Luca's: they may differ from pricing.html. Never add VAT (Alma Consort Ltd is not VAT-registered).

Before going on, repeat the terms back in one short block (client first name, date, venue, package, total). Proceed unless Luca corrects them; if he's away (Remote Control), carry on.

## 2. Hand it to the reply drafter

Start the `lcs-reply-drafter` agent (Agent tool, subagent_type "lcs-reply-drafter") with this message, filled in:

```
OWNER BOOKING (from Luca in a live chat, <today YYYY-MM-DD>)
client: <full name> <<email>>
occasion: <occasion>
event: <YYYY-MM-DD>, <start time or "time tbc">, <venue>
package: <package>
items: <name> — <detail> — <qty> × £<rate>; …
total: £<total>
agreed by: <phone|whatsapp|referral>
thread: <Zoho thread id if Luca gave one, else "find it">
Run the OWNER BOOKING steps in your file (3 i–vii, then step 4 if there is a thread) and reply with your SUMMARY.
```

If the agent type isn't found, start a general-purpose agent with model "sonnet" and begin its prompt: "Read .claude/agents/lcs-reply-drafter.md and follow it exactly: its tools line is the only tools you may use."

## 3. Report back

Give Luca the drafter's summary in a few lines:
- the invoice ref and total;
- that the confirmation email with the invoice and booking confirmation attached is in Zoho Drafts, to check and send;
- the calendar line;
- any flag (a denied call, "attach by hand", Books unavailable).

Nothing is ever sent: Luca opens the draft in Zoho and presses Send.
