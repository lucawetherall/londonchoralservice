"""Twin cases for the structured-state readers (tests/test_state_twins.py): the note-driven cases of
test_check_payments.py, test_cancel_contract.py, test_pipeline.py and test_singer_invoices.py, each as its note
clauses, with the recorded fact each clause is worth (None for neutral text: "PENDING: invoiced", "from quote").

A singer case (SINGER_CASES) is (name, invoices, today): each invoice a dict of its store columns plus "acct" (sort
code, account number, or None) and "clauses" as above; a fact's fp8 of "*" is filled with the invoice's own
bank_fp[:8], and a clause text of None is a fact with no note (a rescan dropped it). The facts-only reading also
clears the columns a fact replaces: bank_changed (bank-warning), bank_confirmed (bank-confirmed), withdrawn.

A booking case is (name, value, invoice date, event date, clauses, paid, today) with clauses
[(text, fact or None)] and fact (kind, fields, on, by). The twin test reads each case three ways: the notes
alone (no facts), the facts alone (neutral clauses only), and both (each fact claiming its clause), and asserts
the same assessment. A clause may carry several facts ("cancellation requested, then withdrawn": cancelled, then
reinstated); a fact may stand for a whole clause that also holds neutral words, as the migration claims it.
"""
import datetime

T = datetime.date(2026, 9, 28)
D8 = datetime.date(2026, 10, 8)
DEP_0826 = [("2026-08-26", 325.0, "reference")]
DEP_0905 = [("2026-09-05", 575.0, "reference")]
DEP_0920 = [("2026-09-20", 575.0, "reference")]
DEP_0704 = [("2026-07-04", 575.0, "reference")]
FEE_PAID = [("2026-08-26", 475.0, "reference"), ("2026-09-25", 462.6, "reference")]  # £937.60 of £950


def f(kind, on, by="script", **fields):
    return (kind, fields, on, by)


def seen(day):
    return (f"deposit seen {day} (Starling)", f("deposit-seen", day))


PENDING = ("PENDING: invoiced", None)

BOOKING_CASES = [
    # --- cancellation (B9, B10) ---------------------------------------------------------------------------------
    ("cancelled anywhere in the notes", 500, "2026-09-01", "2026-10-30",
     [PENDING, ("Cancelled 20 Sep", f("cancelled", "2026-09-20"))], [], T),
    ("a payment inside a cancelled booking's window", 1150, "2026-09-01", "2026-12-05",
     [("Cancelled 20 Sep", f("cancelled", "2026-09-20"))], [("2026-09-27", 575.0, "reference")], T),
    ("a cancelled booking's old payment outside its window", 1150, "2026-09-01", "2026-12-05",
     [("Cancelled 20 Sep", f("cancelled", "2026-09-20"))], [("2026-06-01", 575.0, "reference")], T),
    ("cancelled, then reinstated by the owner", 1150, "2026-07-01", "2026-10-01",
     [seen("2026-07-04"), ("cancelled 20 Sep", f("cancelled", "2026-09-20")),
      ("reinstated 25 Sep", f("reinstated", "2026-09-25", "owner"))], DEP_0704, T),
    ("a cancellation request withdrawn in one clause", 500, "2026-09-01", "2026-10-30",
     [PENDING, ("cancellation requested, then withdrawn", [f("cancelled", "2026-09-20"),
                                                           f("reinstated", "2026-09-21", "owner")])], [], T),
    ("cancelled for another choir stays cancelled", 1150, "2026-09-01", "2027-01-12",
     [("PENDING: invoiced by enquiry assistant, deposit not yet seen", None),
      ("cancelled 2026-09-10, rebooked with another choir", f("cancelled", "2026-09-10"))], [], T),
    ("cancelled by client email (the reply drafter's phrase)", 1150, "2026-09-02", "2026-11-21",
     [seen("2026-09-04"), ("cancelled 2026-09-28 by client email", f("cancelled", "2026-09-28"))],
     [("2026-09-04", 575.0, "reference")], T),
    ("a maybe-cancelling note is chased as before", 500, "2026-09-01", "2026-10-30",
     [PENDING, ("may be cancelling", None)], [], T),
    # --- cancel settlement (B11) ----------------------------------------------------------------------------------
    ("a kept deposit silences the earlier payment", 1150, "2026-08-01", "2027-04-01",
     [("Cancelled 15 Sep", f("cancelled", "2026-09-15")),
      ("deposit kept 2026-09-15", f("deposit-kept", "2026-09-15", "owner"))], [("2026-08-05", 575.0, "reference")], T),
    ("a payment after the kept deposit still reaches the hand check", 1150, "2026-08-01", "2027-04-01",
     [("Cancelled 15 Sep", f("cancelled", "2026-09-15")),
      ("deposit kept 2026-09-15", f("deposit-kept", "2026-09-15", "owner"))],
     [("2026-08-05", 575.0, "reference"), ("2026-09-20", 575.0, "reference")], T),
    ("refunded", 1150, "2026-08-01", "2027-04-01",
     [("cancelled", f("cancelled", "2026-09-15")), ("refunded 2026-09-20", f("refunded", "2026-09-20", "owner"))],
     [("2026-08-05", 575.0, "reference")], T),
    ("payment checked", 1150, "2026-08-01", "2027-04-01",
     [("Cancelled 15 Sep", f("cancelled", "2026-09-15")),
      ("payment checked 2026-09-20", f("payment-checked", "2026-09-20", "owner"))], [("2026-08-05", 575.0, "reference")], T),
    # --- close (B5, B6) --------------------------------------------------------------------------------------------
    ("a payment after paid in full", 1150, "2026-06-01", "2026-10-15",
     [seen("2026-06-03"), ("paid in full 2026-09-15", f("paid-in-full", "2026-09-15", basis="bank"))],
     [("2026-06-03", 575.0, "reference"), ("2026-09-14", 575.0, "reference"), ("2026-09-26", 575.0, "name and amount")], T),
    ("paid in full by the owner with nothing in the bank", 650, "2026-08-22", "2026-11-21",
     [PENDING, ("paid in full 2026-09-28 (owner)", f("paid-in-full", "2026-09-28", "owner", basis="owner"))], [], T),
    ("closed before the event, balance in the bank", 650, "2026-08-22", "2026-11-21",
     [seen("2026-08-26"), ("paid in full 2026-09-20", f("paid-in-full", "2026-09-20", basis="bank"))],
     [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")], T),
    ("an accepted fee reads paid in full", 950, "2026-08-24", "2026-10-10",
     [seen("2026-08-26"), ("short by fees £12.40 accepted 2026-09-27 (owner)",
                           f("fees-accepted", "2026-09-27", "owner", amount="12.40"))], FEE_PAID, D8),
    ("the latest counting fee wins", 950, "2026-08-24", "2026-10-10",
     [("short by fees £5 accepted 2026-09-20 (owner)", f("fees-accepted", "2026-09-20", "owner", amount="5.00")),
      ("short by fees £12.40 accepted 2026-09-27 (owner)", f("fees-accepted", "2026-09-27", "owner", amount="12.40"))],
     FEE_PAID, T),
    ("a fee too small to close the gap", 950, "2026-08-24", "2026-10-10",
     [("short by fees £5 accepted 2026-09-27 (owner)", f("fees-accepted", "2026-09-27", "owner", amount="5.00"))],
     FEE_PAID, D8),
    ("a fee close keeps a later payment flagged", 950, "2026-08-24", "2026-10-10",
     [seen("2026-08-26"), ("short by fees £12.40 accepted 2026-09-26 (owner)",
                           f("fees-accepted", "2026-09-26", "owner", amount="12.40")),
      ("paid in full 2026-09-26", f("paid-in-full", "2026-09-26", basis="bank"))],
     FEE_PAID + [("2026-09-27", 12.4, "reference")], T),
    # --- arrangement (B12) -----------------------------------------------------------------------------------------
    ("a cash balance arranged", 1150, "2026-09-01", "2026-12-12",
     [seen("2026-09-20"), ("balance to be paid in cash", f("arranged", "2026-09-20", method="cash"))], DEP_0920, T),
    ("a cheque on the day with nothing in the bank", 1150, "2026-09-01", "2026-12-12",
     [PENDING, ("cheque on the day", f("arranged", "2026-09-02", method="cheque"))], [], T),
    ("an arranged balance a week away is a hand check", 1150, "2026-09-01", "2026-10-05",
     [seen("2026-09-20"), ("rest will be paid in cash on the day", f("arranged", "2026-09-20", method="cash"))],
     DEP_0920, T),
    ("the rest paid by another payer", 1150, "2026-09-01", "2026-09-30",
     [seen("2026-09-05"), ("rest will be paid by the father", f("arranged", "2026-09-05", method="third-party"))],
     DEP_0905, T),
    ("an arrangement then the whole fee noted", 1150, "2026-09-01", "2026-09-30",
     [seen("2026-09-20"), ("balance to be paid in cash on the day", f("arranged", "2026-09-20", method="cash")),
      ("balance paid in cash 28 Sep", f("noted-paid", "2026-09-28", scope="full"))], DEP_0920, T),
    # --- noted paid (B7, B8) ---------------------------------------------------------------------------------------
    ("paid 14 Sep", 500, "2026-09-01", "2026-10-30", [("paid 14 Sep", f("noted-paid", "2026-09-14", scope="full"))], [], T),
    ("paid by cash behind a PENDING", 500, "2026-09-01", "2026-10-30",
     [PENDING, ("client paid by cash 5 Sep", f("noted-paid", "2026-09-05", scope="full"))], [], T),
    ("a deposit note only", 500, "2026-09-01", "2026-10-30",
     [("Deposit in 5 Sep (cash)", f("noted-paid", "2026-09-05", scope="part"))], [], T),
    ("a deposit note never stops a balance chase", 650, "2026-08-22", "2026-09-30",
     [seen("2026-08-26"), ("deposit received", f("noted-paid", "2026-08-26", scope="part"))], DEP_0826, T),
    ("the balance paid at the rehearsal", 650, "2026-08-22", "2026-10-01",
     [seen("2026-08-26"), ("balance paid by cash at the rehearsal", f("noted-paid", "2026-09-26", scope="full"))],
     DEP_0826, T),
    ("paid per client email (the Monday review's phrase)", 1150, "2026-09-01", "2026-12-12",
     [PENDING, ("paid per client email 2026-09-27", f("noted-paid", "2026-09-27", scope="full"))], [], T),
    ("a negated paid note is chased", 1150, "2026-09-01", "2026-12-12", [PENDING, ("no payment received", None)], [], T),
    # --- markers (B2, B4) ------------------------------------------------------------------------------------------
    ("a stale auto note with nothing in the feed", 1150, "2026-09-01", "2026-12-12", [seen("2026-09-05")], [], T),
    ("an unconfirmed match beats a stale auto note", 1150, "2026-09-01", "2026-12-12", [seen("2026-09-05")],
     [("2026-09-05", 575.0, "amount only")], T),
    ("a receipt drafted stops the thank-you", 650, "2026-09-20", "2026-11-21",
     [seen("2026-09-27"), ("receipt drafted 2026-09-28", f("reminder-drafted", "2026-09-28", what="receipt"))],
     [("2026-09-27", 325.0, "reference")], T),
    ("a fresh payment asks for a thank-you", 650, "2026-09-20", "2026-11-21", [seen("2026-09-27")],
     [("2026-09-27", 325.0, "reference")], T),
    ("a deposit reminder drafted once", 500, "2026-09-01", "2026-10-30",
     [PENDING, ("reminder drafted 2026-09-20", f("reminder-drafted", "2026-09-20", what="deposit"))], [], T),
    ("a balance reminder drafted once", 650, "2026-08-22", "2026-10-01",
     [seen("2026-08-26"), ("balance reminder drafted 2026-09-28", f("reminder-drafted", "2026-09-28", what="balance"))],
     DEP_0826, T),
    ("both reminders and a receipt", 500, "2026-09-01", "2026-10-30",
     [PENDING, ("Reminder drafted 2026-09-20", f("reminder-drafted", "2026-09-20", what="deposit")),
      ("Receipt drafted", f("reminder-drafted", "2026-09-21", what="receipt"))], [], T),
    ("a review drafted after the close", 1150, "2026-09-02", "2026-09-21",
     [seen("2026-09-04"), ("paid in full 2026-09-20", f("paid-in-full", "2026-09-20", basis="bank")),
      ("review request drafted 2026-09-25", f("review-drafted", "2026-09-25"))],
     [("2026-09-04", 575.0, "reference"), ("2026-09-20", 575.0, "reference")], T),
]

# --- singer invoices (S1–S12) -----------------------------------------------------------------------------------

BEN = ("123456", "11112222")
OTHER = ("654321", "99998888")
CHANGED = "BANK DETAILS CHANGED since their last invoice (was ••••9999, now ••••2222): ring them before paying"
DIFFER = "BANK DETAILS DIFFER between the attachment and the email: ring them before paying"
NEW = ("NEW BANK DETAILS: confirm them by phone on a number you already hold before adding the payee, "
       "then run singer_invoices.py confirm a")
NYV = "BANK DETAILS NOT YET VERIFIED (seen on an earlier invoice): confirm by phone, then run singer_invoices.py confirm b"
NO_DETAILS = "no bank details found on the invoice"


def warn(on, *codes):
    return f("bank-warning", on, fp8="*", codes=list(codes))


def inv(mid, received, acct=BEN, clauses=(), **cols):
    base = {"message_id": mid, "received": received, "singer_name": "Ben Fenwick", "singer_email": "ben@example.com",
            "invoice_ref": "1020", "amount_gbp": "100.00", "payee": "", "bank_changed": "no", "bank_confirmed": "",
            "paid_on": "", "paid_amount": "", "paid_ref": "", "paid_verified": "", "withdrawn": "", "booking_ref": ""}
    return dict(base, acct=acct, clauses=list(clauses), **cols)


CONFIRMED = ("bank details confirmed by phone 2026-09-12", f("bank-confirmed", "2026-09-12", "owner", fp8="*"))

SINGER_CASES = [
    ("two invoices to a changed account, neither confirmed",
     [inv("a", "2026-09-01", clauses=[(CHANGED, warn("2026-09-01", "changed"))], bank_changed="yes"),
      inv("b", "2026-09-10", clauses=[(CHANGED, warn("2026-09-10", "changed"))], bank_changed="yes")], T),
    ("a confirmation clears every alarm on every invoice to that account (50f2429d)",
     [inv("a", "2026-09-01", clauses=[(CHANGED, warn("2026-09-01", "changed")), CONFIRMED], bank_changed="yes",
          bank_confirmed="yes"),
      inv("b", "2026-09-10", clauses=[(CHANGED, warn("2026-09-10", "changed")),
                                      ("amount not found: check the invoice by hand", None)], bank_changed="yes")], T),
    ("a verified payment trusts the account on the next invoice",
     [inv("a", "2026-09-01", clauses=[(CHANGED, warn("2026-09-01", "changed"))], bank_changed="yes",
          paid_on="2026-09-05", paid_verified="yes"),
      inv("b", "2026-09-10", clauses=[(CHANGED, warn("2026-09-10", "changed"))], bank_changed="yes")], T),
    ("a different account for the same singer is still flagged",
     [inv("a", "2026-09-01", clauses=[CONFIRMED], bank_confirmed="yes"),
      inv("b", "2026-09-10", OTHER, clauses=[(CHANGED, warn("2026-09-10", "changed"))], bank_changed="yes")], T),
    ("a rescan to new details voids the confirmation",
     [inv("a", "2026-09-01", OTHER, clauses=[
         (None, f("bank-confirmed", "2026-09-12", "owner", fp8="0123abcd")),
         (CHANGED, warn("2026-09-14", "changed")), ("rescanned 2026-09-14", None)], bank_changed="yes")], T),
    ("details that differ between attachment and email",
     [inv("a", "2026-09-01", clauses=[(DIFFER, warn("2026-09-01", "differ", "new")), (NEW, None)],
          bank_changed="yes")], T),
    ("new details, not yet verified on a second invoice",
     [inv("a", "2026-09-01", clauses=[(NEW, warn("2026-09-01", "new"))]),
      inv("b", "2026-09-10", clauses=[(NYV, warn("2026-09-10", "not-yet-verified"))])], T),
    ("no bank details on the invoice",
     [inv("a", "2026-09-01", None, clauses=[(NO_DETAILS, warn("2026-09-01", "no-details"))])], T),
    ("a clean scan", [inv("a", "2026-09-01", clauses=[(None, warn("2026-09-01"))])], T),
    ("withdrawn",
     [inv("a", "2026-09-01", clauses=[(NEW, warn("2026-09-01", "new")),
                                      ("withdrawn 2026-09-15 (not-ours)", f("withdrawn", "2026-09-15", reason="not-ours"))],
          withdrawn="2026-09-15"),
      inv("b", "2026-09-10", clauses=[(NYV, warn("2026-09-10", "not-yet-verified"))])], T),
    ("settled by hand is paid, never trusted",
     [inv("a", "2026-09-01", clauses=[(NEW, warn("2026-09-01", "new")),
                                      ("settled by hand", f("settled", "2026-09-20", "owner", amount="100.00"))],
          paid_on="2026-09-20", paid_amount="100.00", paid_verified="no")], T),
    ("a verified payment thanked",
     [inv("a", "2026-09-20", clauses=[("thanks due 2026-09-25", None),
                                      ("paid reply drafted 2026-09-26", f("paid-reply-drafted", "2026-09-26"))],
          paid_on="2026-09-25", paid_amount="100.00", paid_verified="yes")], T),
    ("a verified payment not yet thanked",
     [inv("a", "2026-09-20", clauses=[("thanks due 2026-09-25", None)], paid_on="2026-09-25", paid_amount="100.00",
          paid_verified="yes")], T),
]
