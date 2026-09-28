#!/usr/bin/env python3
"""Cross-script contract: a cancellation written with `check_payments.py --note <ref> "cancelled …"` (appended to
the notes, never a prefix) must count as cancelled everywhere that reads the ledger: the Google Ads upload, the
Monday report's section 9, section 11 (economics), the pipeline's reviews-due and done-due, and the dashboard.
Each check is run before the note too, so a test can't pass because the row was never eligible.
Stdlib only: .venv/bin/python tests/test_cancel_contract.py"""
import csv, datetime, os, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
LEDGER = os.path.join(_HOME, "bookings.csv")
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = LEDGER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("bookings", "reports", "ads"):
    sys.path.insert(0, os.path.join(ROOT, "scripts", sub))
import dashboard  # noqa: E402
import economics  # noqa: E402
import lcs_money as lm  # noqa: E402
import pipeline  # noqa: E402
import upload_bookings  # noqa: E402
import weekly_review  # noqa: E402

PY = sys.executable
T = datetime.date(2026, 9, 28)
COLS = upload_bookings.COLUMNS
PAST, FUTURE = "2109", "2111"  # an event 7 days ago (paid in full), and one ahead
NOTE = "cancelled 2026-09-28 by client email"


def ledger_rows():
    base = dict(invoice_date="2026-09-02", client_name="Rowan Ashby", client_email="rowan@example.com",
                occasion="wedding", ensemble="Small Choir", value_gbp="1150", enquiry_date="2026-09-01",
                source="web form", gclid="Cj0KCQjwTESTCLICKID", consent="granted", uploaded_at="")
    past = dict(base, booking_ref=PAST, event_date="2026-09-21",
                notes="deposit seen 2026-09-04 (Starling); paid in full 2026-09-20")
    future = dict(base, booking_ref=FUTURE, event_date="2026-11-21", notes="deposit seen 2026-09-04 (Starling)")
    return [past, future]


def fresh():
    for name in os.listdir(_HOME):
        os.remove(os.path.join(_HOME, name))
    with open(LEDGER, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(ledger_rows())
    enq = [{c: "" for c in pipeline.COLUMNS} | {"enquiry_id": "t-" + ref, "first_seen": "2026-09-01", "source": "web form",
                                                  "occasion": "wedding", "status": "confirmed", "booking_ref": ref,
                                                  "followups": "0", "last_contact": "2026-09-02"} for ref in (PAST, FUTURE)]
    with open(os.path.join(_HOME, "enquiries.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pipeline.COLUMNS)
        w.writeheader()
        w.writerows(enq)


def note_cancelled(ref):
    p = subprocess.run([PY, os.path.join(ROOT, "scripts", "bookings", "check_payments.py"), "--note", ref, NOTE],
                       capture_output=True, text=True, cwd=ROOT,
                       env=dict(os.environ, LCS_PRIVATE_DIR=_HOME, LCS_BOOKINGS_CSV=LEDGER))
    assert p.returncode == 0, p.stderr
    notes = {r["booking_ref"]: r["notes"] for r in lm.read_csv(LEDGER)}
    assert notes[ref].endswith("; " + NOTE), notes  # appended, not a prefix: the case the rule must handle


def views():
    """What each consumer makes of the ledger right now: the set of refs it treats as live."""
    rows = lm.read_csv(LEDGER)
    enq = lm.read_csv(os.path.join(_HOME, "enquiries.csv"))
    ready, _ = upload_bookings.select_ready(rows)
    counts = weekly_review.ledger_counts(rows)
    assessments, _, _ = dashboard.payments(None, rows, T)
    return {
        "upload": {r["booking_ref"] for r, _, _ in ready},
        "section 9 ready": counts["ready"],
        "section 9 bookings": counts["bookings"],
        "section 9 total": counts["total"],
        "economics": {r["booking_ref"] for r in economics.season_bookings(rows, datetime.date(2026, 9, 1))},
        "reviews-due": {d["booking_ref"] for d in pipeline.reviews_due(rows, T)},
        "done-due": {d["booking_ref"] for d in pipeline.done_due(enq, rows, T)},
        "dashboard upcoming": {u["ref"] for u in dashboard.upcoming(rows, assessments, False, T)},
        "dashboard payments": {a["ref"] for a in assessments},
    }


def test_before_the_note_every_consumer_sees_both_bookings():
    fresh()
    v = views()
    assert v["upload"] == {PAST, FUTURE}, v
    assert v["section 9 ready"] == 2 and v["section 9 bookings"] == 2 and v["section 9 total"] == 2300.0, v
    assert v["economics"] == {PAST, FUTURE}, v
    assert v["reviews-due"] == {PAST} and v["done-due"] == {PAST}, v
    assert v["dashboard upcoming"] == {FUTURE} and v["dashboard payments"] == {FUTURE}, v


def test_a_note_cancelled_booking_drops_out_everywhere():
    fresh()
    note_cancelled(PAST)
    note_cancelled(FUTURE)
    v = views()
    assert v["upload"] == set(), v
    assert v["section 9 ready"] == 0 and v["section 9 bookings"] == 0 and v["section 9 total"] == 0.0, v
    assert v["economics"] == set(), v
    assert v["reviews-due"] == set() and v["done-due"] == set(), v
    assert v["dashboard upcoming"] == set() and v["dashboard payments"] == set(), v


def test_section_9_counts_the_cancelled_separately():
    fresh()
    note_cancelled(FUTURE)
    counts = weekly_review.ledger_counts(lm.read_csv(LEDGER))
    assert counts["cancelled"] == 1 and counts["bookings"] == 1 and counts["total"] == 1150.0, counts
    assert counts["ready"] == 1, counts


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
