#!/usr/bin/env python3
"""Tests for scripts/bookings/money_report.py. Stdlib only."""
import datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import check_payments as cp
import money_report as mr

T = datetime.date(2026, 9, 28)
QUIET_SINGERS = {"unpaid": 0, "unpaid_total": 0.0, "oldest_days": 0, "bank_changed": 0}


def test_summary_lines():
    assessments = [
        {"ref": "A", "state": "DEPOSIT_OVERDUE", "balance": 500.0, "event_date": "2026-10-30"},
        {"ref": "B", "state": "BALANCE_DUE", "balance": 325.0, "event_date": "2026-10-01"},
        {"ref": "C", "state": "DEPOSIT_SEEN", "balance": 575.0, "event_date": "2026-12-12"},
    ]
    receipts = [("B", "2026-09-25", 325.0), ("C", "2026-09-01", 575.0)]
    singer = {"unpaid": 2, "unpaid_total": 150.0, "oldest_days": 8, "bank_changed": 1}
    assert mr.summary_lines(assessments, receipts, singer, T) == [
        "received from clients, last 7 days: £325.00 (1 payment)",
        "deposits overdue: 1 (A)",
        "balances due in the next 7 days: 1, £325.00 (B)",
        "needs a hand check: 0",
        "singer invoices unpaid: 2, £150.00, oldest 8 days · BANK DETAILS CHANGED on 1 invoice: ring before paying",
    ]


def test_quiet_week():
    assert mr.summary_lines([], [], QUIET_SINGERS, T) == [
        "received from clients, last 7 days: £0.00 (0 payments)",
        "deposits overdue: 0",
        "balances due in the next 7 days: 0, £0.00",
        "needs a hand check: 0",
        "singer invoices unpaid: 0, £0.00",
    ]


def test_last_seven_days_means_today_and_the_six_before():
    receipts = [("X", "2026-09-21", 100.0), ("Y", "2026-09-22", 200.0), ("Z", "2026-09-28", 50.0)]
    assert mr.summary_lines([], receipts, QUIET_SINGERS, T)[0] == "received from clients, last 7 days: £250.00 (2 payments)"


def test_short_notice_unpaid_booking_is_in_the_balances_line():
    r = {"booking_ref": "0210", "value_gbp": "1150", "invoice_date": "2026-09-26", "event_date": "2026-10-02",
         "notes": "PENDING: invoiced", "client_name": "Ann Smith"}
    a = cp.assess(r, [], T)
    assert a["state"] == "AWAITING_DEPOSIT"
    assert mr.summary_lines([a], [], QUIET_SINGERS, T)[2] == \
        "balances due in the next 7 days: 1, £1,150.00 (0210) (includes 1 with no deposit)"


def test_balances_line_takes_every_open_upcoming_state_and_nothing_else():
    def a(ref, state, event, balance=100.0):
        return {"ref": ref, "state": state, "balance": balance, "event_date": event}
    assessments = [
        a("in1", "DEPOSIT_OVERDUE", "2026-10-01"), a("in2", "AWAITING_DEPOSIT", "2026-10-05"),
        a("in3", "DEPOSIT_SEEN", "2026-09-28"), a("in4", "BALANCE_DUE", "2026-09-30"),
        a("far", "DEPOSIT_SEEN", "2026-10-06"), a("gone", "BALANCE_DUE", "2026-09-27"), a("none", "DEPOSIT_SEEN", None),
        a("zero", "DEPOSIT_SEEN", "2026-10-01", 0.0),
        a("x1", "PAID_IN_FULL", "2026-10-01"), a("x2", "NOTED_PAID", "2026-10-01"), a("x3", "CANCELLED", "2026-10-01"),
        a("x4", "CHECK_PAYMENT", "2026-10-01"), a("x5", "CHECK_VALUE", "2026-10-01"),
        a("x6", "PAST_UNMATCHED", "2026-10-01"), a("x7", "PAST_PART_PAID", "2026-10-01"),
    ]
    assert mr.summary_lines(assessments, [], QUIET_SINGERS, T)[2] == \
        "balances due in the next 7 days: 4, £400.00 (in1, in2, in3, in4) (includes 2 with no deposit)"


def test_hand_check_line():
    assessments = [
        {"ref": "2410", "state": "CHECK_PAYMENT", "balance": 1150.0, "event_date": "2026-11-14"},
        {"ref": "0909", "state": "PAST_UNMATCHED", "balance": 650.0, "event_date": "2026-09-09"},
        {"ref": "0101", "state": "DEPOSIT_SEEN", "balance": 325.0, "event_date": "2027-01-01"},
    ]
    assert mr.summary_lines(assessments, [], QUIET_SINGERS, T)[3] == "needs a hand check: 2 (2410 possible payment; 0909 past, unpaid)"
    more = [{"ref": "0808", "state": "PAST_PART_PAID", "balance": 1.0, "event_date": "2026-08-08"},
            {"ref": "1111", "state": "CHECK_VALUE", "balance": 0.0, "event_date": None}]
    assert mr.summary_lines(more, [], QUIET_SINGERS, T)[3] == "needs a hand check: 2 (0808 past, part paid; 1111 unreadable value or date)"


def test_singer_line_wording():
    one = {"unpaid": 1, "unpaid_total": 75.0, "oldest_days": 1, "bank_changed": 2}
    assert mr.summary_lines([], [], one, T)[-1] == \
        "singer invoices unpaid: 1, £75.00, oldest 1 day · BANK DETAILS CHANGED on 2 invoices: ring before paying"


def test_noted_paid_needs_a_hand_check_until_marked_paid_in_full():
    r = {"booking_ref": "0909", "value_gbp": "650", "invoice_date": "2026-09-01", "event_date": "2026-10-30",
         "notes": "PENDING: invoiced; client paid by cash 5 Sep", "client_name": "Ann Smith"}
    a = cp.assess(r, [], T)
    assert a["state"] == "NOTED_PAID"
    assert mr.summary_lines([a], [], QUIET_SINGERS, T)[3] == "needs a hand check: 1 (0909 noted paid, not in bank)"
    r["notes"] += "; paid in full 2026-09-05"
    assert cp.open_rows([r]) == []  # the owner's note takes it off the list


def test_overdue_deposit_in_the_next_week_is_on_both_lines_and_flagged():
    a = [{"ref": "0110", "state": "DEPOSIT_OVERDUE", "balance": 650.0, "event_date": "2026-10-01"},
         {"ref": "0210", "state": "BALANCE_DUE", "balance": 325.0, "event_date": "2026-10-02"}]
    lines = mr.summary_lines(a, [], QUIET_SINGERS, T)
    assert lines[1] == "deposits overdue: 1 (0110)"
    assert lines[2] == "balances due in the next 7 days: 2, £975.00 (0110, 0210) (includes 1 with no deposit)"


def test_noted_paid_label_says_what_is_in_the_bank():
    a = [{"ref": "0909", "state": "NOTED_PAID", "balance": 650.0, "received": 0.0, "event_date": "2026-10-30"},
         {"ref": "1010", "state": "NOTED_PAID", "balance": 575.0, "received": 575.0, "event_date": "2026-10-30"}]
    assert mr.summary_lines(a, [], QUIET_SINGERS, T)[3] == \
        "needs a hand check: 2 (0909 noted paid, not in bank; 1010 noted paid, £575.00 in bank)"


def test_payments_on_cancelled_or_closed_bookings_are_hand_checks_not_balances():
    a = [{"ref": "0510", "state": "PAYMENT_ON_CANCELLED", "balance": 575.0, "received": 575.0, "event_date": "2026-10-01"},
         {"ref": "1506", "state": "PAYMENT_AFTER_CLOSE", "balance": 0.0, "received": 1150.0, "event_date": "2026-10-02"},
         {"ref": "3009", "state": "CHECK_PAYMENT", "balance": 575.0, "received": 575.0, "event_date": "2026-09-30"}]
    lines = mr.summary_lines(a, [], QUIET_SINGERS, T)
    assert lines[2] == "balances due in the next 7 days: 0, £0.00", lines[2]
    assert lines[3] == ("needs a hand check: 3 (0510 payment on a cancelled booking; 1506 payment after paid in full; "
                        "3009 possible balance payment)"), lines[3]


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
