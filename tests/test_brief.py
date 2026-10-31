#!/usr/bin/env python3
"""Tests for scripts/reports/brief.py and section 0 of the Monday report ("This week in brief").
Stdlib only, synthetic rows in a temp private dir, no network. .venv/bin/python tests/test_brief.py"""
import contextlib, csv, datetime, io, os, sys, tempfile

TMP = tempfile.mkdtemp(prefix="lcs-brief-test-")
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import brief  # noqa: E402
import economics as ec  # noqa: E402

D = datetime.date
MON = D(2026, 11, 2)
WEEKS = ec.full_weeks(MON, 8)  # the last is 26 Oct to 1 Nov


def enq(first_seen, occasion="wedding", source="web form", notes=""):
    return {"enquiry_id": first_seen, "first_seen": first_seen, "occasion": occasion, "source": source,
            "notes": notes, "status": "new"}


ENQUIRIES = [
    enq("2026-10-26", "wedding", "web form", "quoted 2026-10-27"),
    enq("2026-10-28", "wedding", "web form", "ad visit: weddings; quoted 2026-10-28"),
    enq("2026-10-31", "funeral", "email"),
    enq("2026-10-20", "christmas", "whatsapp", "quoted 2026-10-21"),
]
LEDGER = [
    {"booking_ref": "121226", "invoice_date": "2026-10-29", "client_name": "Jane Example",
     "client_email": "jane@example.com", "value_gbp": "1150", "notes": ""},
    {"booking_ref": "131226", "invoice_date": "2026-10-30", "client_name": "John Example", "value_gbp": "900",
     "notes": "cancelled 2026-10-31"},
]
ADS = [{"week_start": w.isoformat(), "spend_gbp": 20.0, "clicks": 8, "conversions": 0.0} for w in WEEKS[:-2]] + \
      [{"week_start": WEEKS[-2].isoformat(), "spend_gbp": 25.0, "clicks": 10, "conversions": 0.0},
       {"week_start": WEEKS[-1].isoformat(), "spend_gbp": 35.0, "clicks": 14, "conversions": 1.0}]


def test_a_fixture_week_gives_the_expected_lines():
    data = brief.collect(ENQUIRIES, LEDGER, WEEKS)
    data.update(ads=ADS, pageviews=(420, 380), organic=(15, 12, D(2026, 10, 24), D(2026, 10, 30)),
                alarms=["SECTION 5c FAILED: GoatCounterError (HTTP 429)"])
    got = brief.lines(data)
    assert got == [
        "== 0. This week in brief (week 2026-10-26 to 2026-11-01; then the week before, then the average of the "
        "last 8 full weeks)",
        "   enquiries 3 · week before 1 · 8-week average 0.5 · this week by occasion: wedding 2, funeral 1 · by "
        "source: web form 2, email 1",
        "   quotes sent 2 · week before 1 · 8-week average 0.4 · median 0.5 days from first contact to quote",
        "   bookings 1 (£1,150) · week before 0 (£0) · 8-week average 0.1 (£144) (by invoice date, cancelled left out)",
        "   ad spend £35.00 (14 clicks) · week before £25.00 (10 clicks) · 8-week average £22.50 (9.0 clicks)",
        "   page views, every visitor (GoatCounter, the last 7 days) 420 · the 7 days before 380",
        "   organic clicks (Search Console, 2026-10-24 to 2026-10-30) 15 · week before 12",
        "   alarms: 1 (the sections above give the detail)",
        "   alarm: SECTION 5c FAILED: GoatCounterError (HTTP 429)",
    ], "\n".join(got)
    text = "\n".join(got)
    for secret in ("Jane", "John", "example.com", "ad visit"):
        assert secret not in text, secret


def test_an_empty_week_prints_zeros_never_dashes():
    data = brief.collect([], [], WEEKS)
    data.update(ads=ec.week_buckets([], MON, 8), pageviews=(0, None), organic=(0, 0, D(2026, 10, 24),
                                                                              D(2026, 10, 30)), alarms=[])
    got = brief.lines(data)
    assert got[1:] == [
        "   enquiries 0 · week before 0 · 8-week average 0.0",
        "   quotes sent 0 · week before 0 · 8-week average 0.0",
        "   bookings 0 (£0) · week before 0 (£0) · 8-week average 0.0 (£0) (by invoice date, cancelled left out)",
        "   ad spend £0.00 (0 clicks) · week before £0.00 (0 clicks) · 8-week average £0.00 (0.0 clicks)",
        "   page views, every visitor (GoatCounter, the last 7 days) 0 · the 7 days before not counted yet",
        "   organic clicks (Search Console, 2026-10-24 to 2026-10-30) 0 · week before 0",
        "   alarms: nothing alarming",
    ], "\n".join(got)
    assert "–" not in "\n".join(got) and " - " not in "\n".join(got)


def test_a_failed_section_prints_not_read():
    data = brief.collect(None, [], WEEKS)
    data.update(ads=None, pageviews=None, organic=None, alarms=[])
    got = brief.lines(data)
    assert "   enquiries: no pipeline sheet yet" in got, got
    assert "   ad spend: not read (section 11 has no figures)" in got, got
    assert "   page views (GoatCounter): not read (section 5c has no figures)" in got, got
    assert "   organic clicks (Search Console): not read (section 6 has no figures)" in got, got
    assert not any(l.startswith("   quotes") for l in got), got


def test_the_alarm_list_is_capped():
    data = brief.collect([], [], WEEKS)
    data.update(alarms=[f"SECTION {n} FAILED: KeyError" for n in range(20)])
    got = brief.lines(data)
    assert got[-1] == "   and 8 more" and sum(l.startswith("   alarm: ") for l in got) == brief.MAX_ALARMS, got


def _write(path, rows):
    cols = sorted({k for r in rows for k in r})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def test_section_0_reads_the_sheets_the_weeks_figures_and_the_alarms_printed_before_it():
    sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
    import weekly_review as wr
    _write(os.path.join(TMP, "enquiries.csv"), ENQUIRIES)
    _write(os.environ["LCS_BOOKINGS_CSV"], LEDGER)
    wr.WEEK.clear()
    wr.WEEK.update(ads_weeks=ADS, pageviews=(420, 380))
    printed = ("== 1. Campaigns\n   log 2026-10-19 · ad 1 · final URL · error page → x\n"
               "== 0b. Since last Monday\n   open 2026-10-26-01 · site · fix the error page\n"
               "== 6. Search Console\n   SECTION 6 FAILED: RefreshError\n"
               "== 7. Search Console coverage\n   /sitemap.xml · …  !STALE: resubmit\n")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.brief_section(MON, printed)
    lines = out.getvalue().splitlines()
    assert lines[1].startswith("== 0. This week in brief"), lines
    assert "   enquiries 3 · week before 1" in "\n".join(lines)
    assert "   organic clicks (Search Console): not read (section 6 has no figures)" in lines
    assert lines[-3:] == ["   alarms: 2 (the sections above give the detail)",
                          "   alarm: SECTION 6 FAILED: RefreshError", "   alarm: /sitemap.xml · …  !STALE: resubmit"], lines
    assert "Jane" not in out.getvalue() and "example.com" not in out.getvalue()


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
