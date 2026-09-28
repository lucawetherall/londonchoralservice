#!/usr/bin/env python3
"""Tests for scripts/bookings/check_payments.py. Stdlib only."""
import datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import check_payments as cp

T = datetime.date(2026, 9, 28)


def row(ref, value, invoice, event, notes="", name="Ann Smith"):
    return {"booking_ref": ref, "value_gbp": str(value), "invoice_date": invoice, "event_date": event,
            "notes": notes, "client_name": name}


def pay(amount, when, ref="", who="Someone"):
    return {"direction": "IN", "amount": {"minorUnits": int(round(amount * 100))},
            "transactionTime": when + "T10:00:00Z", "reference": ref, "counterPartyName": who}


def test_match_by_reference():
    found = cp.match([row("2111", 650, "2026-08-22", "2026-11-21")], [pay(325, "2026-08-26", "INV 2111")], T)
    assert found["2111"] == [("2026-08-26", 325.0, "reference")]


def test_match_by_surname_and_deposit():
    found = cp.match([row("0810", 375, "2026-09-22", "2026-10-08")], [pay(187.5, "2026-09-24", "deposit", "MRS A SMITH")], T)
    assert found["0810"][0][2] == "name and amount"


def test_amount_only_needs_a_unique_amount():
    one = [row("A", 1150, "2026-09-01", "2026-10-10", name="X Y")]
    two = one + [row("B", 1150, "2026-09-02", "2026-10-11", name="P Q")]
    payment = [pay(1150, "2026-09-05", "wedding")]
    assert cp.match(one, payment, T)["A"][0][2] == "amount only"
    assert cp.match(two, payment, T) == {"A": [], "B": []}


def test_past_event_is_never_overdue():
    assert cp.assess(row("2509", 3225, "2026-09-12", "2026-09-21"), [], T)["state"] == "PAST_UNMATCHED"


def test_noted_paid_is_not_chased():
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep"), [], T)["state"] == "NOTED_PAID"


def test_deposit_overdue_for_future_event():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced"), [], T)
    assert a["state"] == "DEPOSIT_OVERDUE" and a["deposit_due"] == "2026-09-08"


def test_awaiting_deposit_inside_seven_days():
    assert cp.assess(row("X", 500, "2026-09-25", "2026-10-30", "PENDING: invoiced"), [], T)["state"] == "AWAITING_DEPOSIT"


def test_balance_due_from_three_days_before():
    paid = [("2026-08-26", 325.0, "reference")]
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-10-01"), paid, T)["state"] == "BALANCE_DUE"
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-11-21"), paid, T)["state"] == "DEPOSIT_SEEN"


def test_paid_in_full():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    a = cp.assess(row("2111", 650, "2026-08-22", "2026-11-21"), paid, T)
    assert a["state"] == "PAID_IN_FULL" and a["balance"] == 0


def test_just_received_only_from_pending():
    paid = [("2026-09-27", 325.0, "reference")]
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "PENDING: invoiced"), paid, T)["just_received"] is True
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "deposit seen 2026-09-27 (Starling)"), paid, T)["just_received"] is False


def test_reminder_marks_are_distinct():
    a = cp.assess(row("X", 650, "2026-08-22", "2026-10-01", "deposit seen x; balance reminder drafted 2026-09-28"),
                  [("2026-08-26", 325.0, "reference")], T)
    assert a["reminded"] == {"deposit": False, "balance": True, "receipt": False}
    b = cp.assess(row("X", 650, "2026-09-01", "2026-10-30", "PENDING: x; reminder drafted 2026-09-20"), [], T)
    assert b["reminded"]["deposit"] is True and b["reminded"]["balance"] is False


def test_updated_notes_clears_pending_and_marks_full():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    r = row("X", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced; from quote")
    a = cp.assess(r, paid, T)
    assert cp.updated_notes(r["notes"], a, paid) == "deposit seen 2026-08-26 (Starling); from quote; paid in full 2026-09-20"


def test_describe_never_names_the_client():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced", name="Secret Person"), [], T)
    assert "Secret" not in cp.describe(a) and "DEPOSIT OVERDUE since 2026-09-08" in cp.describe(a)


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
