#!/usr/bin/env python3
"""Tests for scripts/ads/upload_bookings.py row selection (select_ready). No network, no Google calls.
Stdlib only: .venv/bin/python tests/test_upload_bookings.py"""
import os, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(_HOME, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
import upload_bookings as ub  # noqa: E402


def row(ref="2111", **kw):
    r = {c: "" for c in ub.COLUMNS}
    r.update(booking_ref=ref, invoice_date="2026-09-20", event_date="2026-11-21", value_gbp="1150",
             enquiry_date="2026-09-10", gclid="Cj0KCQjwTESTCLICKID", consent="granted",
             notes="deposit seen 2026-09-22 (Starling)")
    r.update(kw)
    return r


def refs(rows):
    ready, _ = ub.select_ready(rows)
    return [r["booking_ref"] for r, _, _ in ready]


def reasons(rows):
    return dict(ub.select_ready(rows)[1])


def test_a_confirmed_booking_is_ready_with_its_value_and_time():
    ready, skipped = ub.select_ready([row()])
    assert skipped == [] and len(ready) == 1, (ready, skipped)
    r, value, when = ready[0]
    assert r["booking_ref"] == "2111" and value == 1150.0 and when == "2026-09-20T12:00:00+01:00", ready


def test_a_cancellation_appended_to_the_notes_is_never_uploaded():
    for notes in ("deposit seen 2026-09-22 (Starling); cancelled 2026-10-05 by client email",
                  "PENDING: invoiced; cancelled 2026-10-05 by client email",
                  "CANCELLED by phone", "cancellation confirmed 2026-10-06"):
        rows = [row(notes=notes)]
        assert refs(rows) == [], notes
        assert reasons(rows) == {"2111": "cancelled"}, (notes, reasons(rows))


def test_a_reinstated_booking_is_ready_again():
    assert refs([row(notes="cancelled 2026-10-05 by client email; reinstated 2026-10-07")]) == ["2111"]


def test_a_pending_booking_waits():
    rows = [row(notes="PENDING: invoiced by enquiry assistant, deposit not yet seen")]
    assert refs(rows) == [] and reasons(rows)["2111"].startswith("PENDING"), reasons(rows)


def test_uploaded_rows_are_left_out_silently():
    assert ub.select_ready([row(uploaded_at="2026-09-25 09:00")]) == ([], [])


def test_no_click_reference_or_no_consent_is_skipped():
    assert "no ad click reference" in reasons([row(gclid="")])["2111"]
    assert "consent" in reasons([row(consent="unknown")])["2111"]


def test_unreadable_nan_inf_zero_or_negative_values_are_refused():
    for bad in ("", "abc", "nan", "inf", "-inf", "-50", "0", "£-1,150"):
        rows = [row(value_gbp=bad)]
        assert refs(rows) == [], bad
        assert "value" in reasons(rows)["2111"], (bad, reasons(rows))


def test_a_pound_sign_and_commas_are_read():
    ready, _ = ub.select_ready([row(value_gbp="£1,150.00")])
    assert ready[0][1] == 1150.0


def test_an_unreadable_enquiry_date_is_a_skip_not_a_crash():
    assert "enquiry_date" in reasons([row(enquiry_date="soon")])["2111"], reasons([row(enquiry_date="soon")])


def test_booked_more_than_90_days_after_the_enquiry_is_skipped():
    assert "90 days" in reasons([row(enquiry_date="2026-05-01")])["2111"]


def test_a_missing_invoice_date_is_skipped():
    assert "invoice_date" in reasons([row(invoice_date="")])["2111"]


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
            except Exception as e:  # an error is a failure too
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
