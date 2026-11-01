#!/usr/bin/env python3
"""Tests for scripts/ads/upload_enquiries.py row selection (select_ready) and its events. No network, no Google
calls. Stdlib only: .venv/bin/python tests/test_upload_enquiries.py"""
import datetime, os, sys, tempfile
from zoneinfo import ZoneInfo

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(_HOME, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
import upload_enquiries as ue  # noqa: E402

LONDON = ZoneInfo("Europe/London")
TODAY = datetime.date(2026, 11, 2)
NOW = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=LONDON)


def row(eid="19a2b3c4d5e6f7", **kw):
    r = {c: "" for c in ue.pipeline.COLUMNS}
    r.update(enquiry_id=eid, first_seen="2026-10-28", source="whatsapp", occasion="christmas", status="new",
             gclid="Cj0KCQjwTESTCLICKID", followups="0")
    r.update(kw)
    return r


def select(rows):
    return ue.select_ready(rows, today=TODAY, now=NOW)


def ids(rows):
    return [r["enquiry_id"] for r, _ in select(rows)[0]]


def reasons(rows):
    return dict(select(rows)[1])


def test_an_enquiry_with_a_click_reference_is_ready_at_the_end_of_its_day():
    ready, skipped = select([row()])
    assert skipped == [] and len(ready) == 1, (ready, skipped)
    r, when = ready[0]
    assert when == "2026-10-28T23:59:00+00:00", when  # GMT by then
    e = ue.event(r, when)
    assert e == {"eventTimestamp": when, "transactionId": "19a2b3c4d5e6f7", "eventSource": "OTHER",
                 "adIdentifiers": {"gclid": "Cj0KCQjwTESTCLICKID"}}, e


def test_every_channel_counts_and_braids_keep_their_kind():
    rows = [row("a", source="web form"), row("b", source="email"), row("c", source="phone"),
            row("d", gclid="gbraid:0AAAAAoXyz_12345"), row("e", gclid="wbraid:CkEKCQjw1234567")]
    ready = select(rows)[0]
    assert [r["enquiry_id"] for r, _ in ready] == ["a", "b", "c", "d", "e"]
    assert ue.event(*ready[3])["adIdentifiers"] == {"gbraid": "0AAAAAoXyz_12345"}
    assert ue.event(*ready[4])["adIdentifiers"] == {"wbraid": "CkEKCQjw1234567"}


def test_an_enquiry_first_seen_today_goes_a_minute_before_now():
    _, when = select([row(first_seen="2026-11-02")])[0][0]
    assert when == "2026-11-02T08:59:00+00:00", when


def test_ad_visits_and_enquiries_not_from_an_ad_never_go_and_are_not_listed():
    rows = [row("v", gclid="", notes="ad visit: pricing (wedding-leads)"),
            row("h", gclid="", notes="heard: A Google ad"), row("n", gclid="")]
    assert select(rows) == ([], [])


def test_an_unresolved_ref_note_is_listed_with_its_reason():
    assert "not resolved" in reasons([row(gclid="", notes="ref: AB12")])["19a2b3c4d5e6f7"]


def test_uploaded_rows_are_left_out_silently():
    assert select([row(ads_uploaded_at="2026-11-01 09:00")]) == ([], [])


def test_outside_the_window_or_before_consent_was_recorded_is_skipped():
    assert "90 days" in reasons([row(first_seen="2026-08-01")])["19a2b3c4d5e6f7"]
    assert "27 Sep" in reasons([row(first_seen="2026-09-26")])["19a2b3c4d5e6f7"]
    assert ids([row(first_seen="2026-09-27")]) == ["19a2b3c4d5e6f7"]
    assert "first_seen" in reasons([row(first_seen="")])["19a2b3c4d5e6f7"]


def test_a_ticked_box_without_a_click_never_goes_and_no_email_ever_does():
    # the box promises nothing is sent for an enquiry that doesn't become a booking (privacy.html)
    r = row(gclid="", source="web form", notes="ad measurement: yes")
    assert select([r]) == ([], [])
    ready = select([row(source="web form", notes="ad measurement: yes")])[0]
    e = ue.event(*ready[0])
    assert set(e) == {"eventTimestamp", "transactionId", "eventSource", "adIdentifiers"}, e


def test_stamping_marks_only_the_uploaded_rows():
    lm, pl = ue.lm, ue.pipeline
    lm.write_csv(pl.ENQUIRIES, [row("a"), row("b"), row("c", ads_uploaded_at="2026-10-01 09:00")], pl.COLUMNS)
    ue.stamp_uploaded({"a", "c"}, "2026-11-02 09:00")
    got = {r["enquiry_id"]: r["ads_uploaded_at"] for r in lm.read_csv(pl.ENQUIRIES)}
    assert got == {"a": "2026-11-02 09:00", "b": "", "c": "2026-10-01 09:00"}, got


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
