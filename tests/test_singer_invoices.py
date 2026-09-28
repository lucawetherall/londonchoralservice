#!/usr/bin/env python3
"""Tests for scripts/bookings/singer_invoices.py. Stdlib only. Uses a temp private dir."""
import datetime, os, sys, tempfile

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_money as lm
import singer_invoices as si

LABELLED = """INVOICE
Invoice No: 1020
Date: 25/09/2026
To: Alma Consort Ltd
Funeral 21 September   £100.00
Total due £100.00
Account name: B Fenwick
Sort code: 12-34-56
Account number: 12345678
"""
TERSE = """Invoice INV-0107
Wedding 19 Sep     £150
Travel             £50
Subtotal £200.00
TOTAL £200.00
Sort Code 123456 Acc No 8765 4321
"""
NO_BANK = """Invoice 20260309-001
Balance due: £1,129.15
Thanks!"""


def test_extract_labelled_invoice():
    assert si.extract(LABELLED) == {"amount": 100.0, "invoice_ref": "1020", "sort_code": "123456", "account_number": "12345678"}


def test_extract_terse_invoice():
    e = si.extract(TERSE)
    assert (e["amount"], e["invoice_ref"], e["sort_code"], e["account_number"]) == (200.0, "INV-0107", "123456", "87654321")


def test_extract_without_bank_details():
    e = si.extract(NO_BANK)
    assert (e["amount"], e["invoice_ref"], e["sort_code"], e["account_number"]) == (1129.15, "20260309-001", "", "")


def test_extract_falls_back_to_largest_pound_figure():
    assert si.extract("Fee £80\nTravel £20\nPlease pay £100")["amount"] == 100.0


def inv(sort="123456", acc="12345678", amount=100.0):
    return {"amount": amount, "invoice_ref": "1", "sort_code": sort, "account_number": acc}


def test_new_singer_needs_a_payee():
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], {}, [])
    assert a["payee"] == "NEW: add as a payee in the Starling app" and a["bank_changed"] == "no"
    assert a["bank_last4"] == "5678" and "12345678" not in str(a)


def test_existing_payee_by_fingerprint():
    fps = {lm.bank_fingerprint("123456", "12345678"): "Ben W"}
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben W"])["payee"] == "existing: Ben W"


def test_changed_bank_details_warn():
    history = [{"singer_email": "b@x.com", "bank_fp": lm.bank_fingerprint("123456", "11112222"), "bank_last4": "2222"}]
    a = si.assess_new(inv(), "B@X.com", "Ben Fenwick", history, {}, [])
    assert a["bank_changed"] == "yes" and any("BANK DETAILS CHANGED" in w and "••••2222" in w for w in a["warnings"])


def test_payee_name_with_different_details_warns():
    fps = {lm.bank_fingerprint("123456", "99990000"): "Ben Fenwick"}
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben Fenwick"])
    assert a["bank_changed"] == "yes" and "different bank details" in a["payee"]


def test_no_bank_details_and_no_token():
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", [], None, [])
    assert a["payee"] == "unknown (no Starling token)" and "no bank details found on the invoice" in a["warnings"]


def out(amount, when, who):
    return {"direction": "OUT", "amount": {"minorUnits": int(round(amount * 100))},
            "transactionTime": when + "T10:00:00Z", "counterPartyName": who}


def unpaid(mid, name, amount, received, payee="NEW: add as a payee in the Starling app"):
    return {"message_id": mid, "singer_name": name, "amount_gbp": f"{amount:.2f}", "received": received,
            "payee": payee, "paid_on": "", "bank_changed": "no"}


def test_match_paid_by_amount_and_surname():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19")]
    assert si.match_paid(rows, [out(200, "2026-09-19", "LAURA PENHALLOW")]) == {"m1": ("2026-09-19", 200.0)}


def test_match_paid_uses_payee_name():
    rows = [unpaid("m1", "Maddy Kessell", 160, "2026-09-01", payee="existing: M M Kessell")]
    assert si.match_paid(rows, [out(160, "2026-09-02", "M M KESSELL")]) == {"m1": ("2026-09-02", 160.0)}


def test_match_paid_rejects_wrong_amount_early_date_and_double_use():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19"), unpaid("m2", "Laura Penhallow", 200, "2026-09-20")]
    assert si.match_paid(rows, [out(150, "2026-09-21", "LAURA PENHALLOW")]) == {}
    assert si.match_paid(rows[:1], [out(200, "2026-09-10", "LAURA PENHALLOW")]) == {}
    assert si.match_paid(rows, [out(200, "2026-09-21", "LAURA PENHALLOW")]) == {"m1": ("2026-09-21", 200.0)}


def test_summary_counts():
    rows = [dict(unpaid("m1", "A B", 100, "2026-09-20"), bank_changed="yes"),
            dict(unpaid("m2", "C D", 50, "2026-09-26")),
            dict(unpaid("m3", "E F", 70, "2026-09-01"), paid_on="2026-09-02")]
    assert si.summary(rows, datetime.date(2026, 9, 28)) == {"unpaid": 2, "unpaid_total": 150.0, "oldest_days": 8, "bank_changed": 1}


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
