#!/usr/bin/env python3
"""Tests for scripts/bookings/money_report.py. Stdlib only."""
import datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import money_report as mr

T = datetime.date(2026, 9, 28)


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
        "singer invoices unpaid: 2, £150.00, oldest 8 days · BANK DETAILS CHANGED on 1: ring before paying",
    ]


def test_quiet_week():
    singer = {"unpaid": 0, "unpaid_total": 0.0, "oldest_days": 0, "bank_changed": 0}
    assert mr.summary_lines([], [], singer, T) == [
        "received from clients, last 7 days: £0.00 (0 payments)",
        "deposits overdue: 0",
        "balances due in the next 7 days: 0, £0.00",
        "singer invoices unpaid: 0, £0.00, oldest 0 days",
    ]


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
