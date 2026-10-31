#!/usr/bin/env python3
"""Tests for weekly_review's section 12 (budget rules, the Christmas value check and the spend guard), 9b and 11.
Stdlib only, a temp private dir and a fake Ads query. .venv/bin/python tests/test_weekly_proposals.py"""
import contextlib, datetime, io, os, stat, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
sys.path.insert(0, ROOT)
import weekly_review as wr

MON = datetime.date(2026, 10, 5)


def row(cid, name, status, pounds):
    return NS(campaign=NS(id=int(cid), name=name, status=NS(name=status)),
              campaign_budget=NS(amount_micros=int(pounds * 1_000_000)))


def test_section_12_prints_propose_lines_and_writes_nothing():
    rows = [row("24295921372", "Christmas carol singers – events 2026", "ENABLED", 4.0),
            row("23739971001", "wedding-leads", "ENABLED", 4.0),
            row("23735776277", "funeral expert campaign", "PAUSED", 2.0)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        wr.budget_section(lambda q: rows, MON)
    out = buf.getvalue()
    # the carols window is £5 a day since 26 Oct 2026 (data/budget-windows.yml); the fake campaign sits at £4
    assert "PROPOSE: Christmas carol singers – events 2026 £4.00 → £5.00/day (window carols)" in out, out
    assert "written" not in out and not (Path(TMP) / "command-centre").exists(), out


def test_the_proposals_flag_is_gone():
    saved = (wr.run_sections, sys.argv, sys.stderr)
    seen = {}
    wr.run_sections = lambda args: seen.update(vars(args))
    try:
        sys.argv, sys.stderr = ["weekly_review.py"], io.StringIO()
        wr.main()
        assert "write_proposals" not in seen and seen["save_report"] is False, seen
        sys.argv = ["weekly_review.py", "--write-proposals"]
        try:
            wr.main()
            raise AssertionError("--write-proposals still accepted")
        except SystemExit as e:
            assert e.code == 2
    finally:
        wr.run_sections, sys.argv, sys.stderr = saved


import enquiry_sources as es  # noqa: E402

N = NS
XMAS = "Christmas carol singers – events 2026"


def enq(occasion, first_seen, notes="", gclid=""):
    """A synthetic enquiries.csv row (no names: the sheet has none)."""
    return {"enquiry_id": "t", "first_seen": str(first_seen), "source": "web form", "occasion": occasion,
            "notes": notes, "gclid": gclid, "booking_ref": "", "status": "new"}


def graded(*rows, clicks=None, found=None):
    return es.grade_rows(list(rows), (lambda g, d: (found or {}).get(g)), clicks)


def xmas_rows(costs, conversions=0.0):
    return lambda query: [N(metrics=N(cost_micros=int(c * 1e6), conversions=conversions if i == 0 else 0.0))
                          for i, c in enumerate(costs)]


def test_christmas_value_check_flags_extra_spend_past_sixty_pounds():
    lines = wr.value_check_lines(xmas_rows([8, 8, 2]), datetime.date(2026, 10, 5), graded())
    assert lines[0] == ("Christmas value check: £18.00 spent since 28 Sep, £6.00 of it above the £5/day level · 0 Ads "
                        "conversions · enquiries from Christmas ads: A 0 · B 0 (C 0, never counts)"), lines
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2), graded())
    assert lines[0].endswith("— PAST £60 with no A or B enquiry from Christmas ads and no Ads conversion: back to £5"), \
        lines
    assert "(checked from" not in lines[0]
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 10, 26), graded())
    assert lines[0].endswith("back to £5 (checked from 02 Nov)"), lines
    assert "C never counts" in lines[1] and lines[1].startswith("stop rule:"), lines
    assert wr.value_check_lines(xmas_rows([8]), datetime.date(2026, 9, 27)) == []


def test_christmas_rule_counts_a_and_b_only():
    day = datetime.date(2026, 10, 22)
    c_only = graded(enq("christmas", day, "heard: Searching on Google"), enq("corporate", day),
                    clicks={(day, "christmas")})
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2), c_only)
    assert "enquiries from Christmas ads: A 0 · B 0 (C 2, never counts)" in lines[0], lines
    assert "PAST £60 with no A or B enquiry" in lines[0], lines
    for row in (enq("christmas", day, "ad visit: christmas"),                                   # B by page
                enq("christmas", day, "ad visit: pricing (christmas-carol-singers-2026)"),        # B by campaign
                enq("christmas", day, gclid="Cj0KCQjwTestClickId123")):                          # A by click
        lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2),
                                     graded(row, found={"Cj0KCQjwTestClickId123": XMAS}))
        assert "over £60, but the campaign brought 1 A/B enquiries: keep £8 on this test" in lines[0], lines
        assert "PAST £" not in lines[0]
    # a B that names no campaign (pricing page, or "A Google ad") and a wedding ad visit are not Christmas's
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2),
                                 graded(enq("christmas", day, "ad visit: pricing"),
                                        enq("christmas", day, "heard: A Google ad"),
                                        enq("wedding", day, "ad visit: weddings")))
    assert "A 0 · B 0 (C 0" in lines[0] and "PAST £60" in lines[0], lines
    # an Ads conversion (a WhatsApp or email contact) still counts as the owner's rule says
    lines = wr.value_check_lines(xmas_rows([8] * 21, conversions=1.0), datetime.date(2026, 11, 2), graded())
    assert "brought 1 Ads conversions: keep £8" in lines[0], lines
    # not graded: the rule can't be settled by the report
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2), None)
    assert "enquiries not graded this week" in lines[0] and "unless the pipeline shows an A or B enquiry" in lines[0]
    # an enquiry before 28 Sep doesn't count
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2),
                                 graded(enq("christmas", datetime.date(2026, 9, 20), "ad visit: christmas")))
    assert "A 0 · B 0" in lines[0], lines


def guard_rows(query):
    return [N(campaign=N(id=23739971001, name="wedding-leads"), metrics=N(cost_micros=95_000_000, clicks=20, conversions=0.0)),
            N(campaign=N(id=23735776277, name="funeral expert campaign"), metrics=N(cost_micros=120_000_000, clicks=25, conversions=2.0)),
            N(campaign=N(id=3, name="quiet"), metrics=N(cost_micros=85_000_000, clicks=9, conversions=0.0)),
            N(campaign=N(id=4, name="small"), metrics=N(cost_micros=30_000_000, clicks=6, conversions=0.0)),
            N(campaign=N(id=24295921372, name=XMAS), campaign_budget=N(amount_micros=8_000_000),
              metrics=N(cost_micros=150_000_000, clicks=60, conversions=0.0))]


def test_spend_guard_judges_christmas_like_the_others_once_its_budget_is_back_at_five_pounds():
    # 26 Oct 2026: the owner took the Christmas budget from £8 to £5; the dated exception in budget_cap.py stays
    # until 13 Dec, but a campaign not spending above £5/day is not "inside" it, so the guard applies
    def rows(query):
        return [N(campaign=N(id=24295921372, name=XMAS), campaign_budget=N(amount_micros=5_000_000),
                  metrics=N(cost_micros=136_000_000, clicks=41, conversions=0.0))]
    lines = wr.spend_guard_lines(rows, datetime.date(2026, 11, 2), graded())
    assert lines[0].endswith("— STOP GUARD: propose pausing (never deleting) until the owner decides"), lines
    assert "deferred" not in lines[0], lines


def test_christmas_value_check_is_retired_once_the_budget_is_five_pounds():
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2), graded(), budget_gbp=5.0)
    assert lines[0].endswith("— budget already £5/day (owner, 26 Oct 2026): the £8 rule is retired, nothing to propose"), \
        lines
    assert "back to £5" not in lines[0] and lines[1].startswith("stop rule: retired"), lines
    # at £8 the rule still runs
    lines = wr.value_check_lines(xmas_rows([8] * 21), datetime.date(2026, 11, 2), graded(), budget_gbp=8.0)
    assert lines[0].endswith("back to £5"), lines


def test_spend_guard_fires_with_no_a_or_b_enquiry_even_with_ads_conversions():
    mon = datetime.date(2026, 10, 26)
    day = datetime.date(2026, 10, 22)
    lines = wr.spend_guard_lines(guard_rows, mon, graded(enq("christmas", day), clicks={(day, "christmas")}))
    assert lines[0] == ("spend guard wedding-leads: £95.00, 20 clicks, 0 Ads conversions in 28 days · enquiries A 0 · "
                        "B 0 · C 0 — STOP GUARD: propose pausing (never deleting) until the owner decides"), lines
    # owner decision 26 Oct 2026: two click-conversions (WhatsApp or email taps) no longer hold a campaign open
    assert lines[1] == ("spend guard funeral expert campaign: £120.00, 25 clicks, 2 Ads conversions in 28 days · "
                        "enquiries A 0 · B 0 · C 0 — STOP GUARD: propose pausing (never deleting) until the owner "
                        "decides"), lines
    assert lines[2].endswith("under 15 clicks, too few to judge; watch next week"), lines
    assert lines[3] == "spend guard small: £30.00, 6 clicks, 0 Ads conversions in 28 days · enquiries A 0 · B 0 · C 0"
    # a C enquiry never holds the guard; inside its dated £8 exception the Christmas campaign is left to its own
    # stop rule (section 12's value check) instead of a pause proposal
    assert lines[4] == (f"spend guard {XMAS}: £150.00, 60 clicks, 0 Ads conversions in 28 days · enquiries "
                        "A 0 · B 0 · C 1 — deferred: inside its dated budget exception, judged by its own stop rule "
                        "(the value check in section 12), not paused here"), lines
    assert lines[5].startswith("stop rule: £80+ in 28 days with no A or B enquiry → propose pausing"), lines
    assert "no Ads conversion and" not in lines[5], lines


def test_spend_guard_an_a_or_b_enquiry_holds_a_campaign_with_ads_conversions():
    mon = datetime.date(2026, 10, 26)
    lines = wr.spend_guard_lines(guard_rows, mon, graded(enq("funeral", datetime.date(2026, 10, 22),
                                                             "ad visit: funerals")))
    assert lines[1].endswith("— held: an A or B enquiry came from this campaign, so no pause"), lines


def test_spend_guard_is_held_by_an_a_or_b_enquiry_for_that_campaign_only():
    mon = datetime.date(2026, 10, 26)
    day = datetime.date(2026, 10, 22)
    for row in (enq("christmas", day, "ad visit: christmas"), enq("corporate", day, "ad visit: home (christmas-carol-singers-2026)"),
                enq("christmas", day, gclid="Cj0KCQjwTestClickId123")):
        lines = wr.spend_guard_lines(guard_rows, mon, graded(row, found={"Cj0KCQjwTestClickId123": XMAS}))
        assert lines[4].endswith("— held: an A or B enquiry came from this campaign, so no pause"), lines
        assert "STOP GUARD" not in lines[4]
        assert "STOP GUARD" in lines[0], lines  # the wedding campaign still has none of its own
    # outside the 28 days it no longer holds (the dated exception then defers it; after the exception ends,
    # 13 Dec 2026, the guard fires as for any campaign)
    lines = wr.spend_guard_lines(guard_rows, mon, graded(enq("christmas", datetime.date(2026, 9, 28), "ad visit: christmas")))
    assert "deferred: inside its dated budget exception" in lines[4], lines
    lines = wr.spend_guard_lines(guard_rows, datetime.date(2026, 12, 14), graded(enq("wedding", datetime.date(2026, 9, 28))))
    assert "STOP GUARD" in lines[4] and "deferred" not in lines[4], lines
    # an ad enquiry that names no campaign doesn't hold it but is flagged beside the pause
    lines = wr.spend_guard_lines(guard_rows, mon, graded(enq("wedding", day, "heard: A Google ad")))
    assert lines[0].endswith("(1 ad enquiries in these 28 days name no campaign: check them first)"), lines
    # not graded: the guard still fires, with a caveat
    lines = wr.spend_guard_lines(guard_rows, mon, None)
    assert "enquiries not graded" in lines[0] and lines[0].endswith(
        "(enquiries not graded this week: check the pipeline first)"), lines


class FakeClicksAds:
    """The GAQL runner for sections 9b and 11: ad clicks per campaign per day, click_view by date, season spend."""
    def __init__(self, daily, click_view, spend=()):
        self.daily, self.click_view, self.spend, self.queries = daily, click_view, spend, []

    def __call__(self, query):
        self.queries.append(query)
        if "FROM click_view" in query:
            day = query.split("segments.date = '")[1][:10]
            return [N(click_view=N(gclid=g), campaign=N(name=c)) for g, c in self.click_view.get(day, {}).items()]
        if "metrics.clicks > 0" in query:
            return [N(campaign=N(id=cid, name=name), segments=N(date=d), metrics=N(clicks=1)) for d, cid, name in self.daily]
        if "metrics.cost_micros, metrics.clicks FROM campaign" in query:
            return [N(campaign=N(id=cid, name=name), metrics=N(cost_micros=int(c * 1e6), clicks=k))
                    for cid, name, c, k in self.spend]
        return []


def write_rows(path, columns, rows):
    import csv
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


ENQ_COLS = ["enquiry_id", "first_seen", "source", "occasion", "event_date", "package", "quoted_gbp", "status",
            "last_contact", "booking_ref", "gclid", "followups", "notes"]


def test_section_9b_grades_the_week_from_the_sheet_and_the_days_clicks():
    mon = datetime.date(2026, 10, 26)
    path = Path(TMP) / "enquiries-9b.csv"
    write_rows(path, ENQ_COLS, [
        enq("christmas", "2026-10-22", "6 singers at Some Venue; heard: Searching on Google"),
        enq("christmas", "2026-10-22", "4-6 singers, Some Town"),
        enq("wedding", "2026-10-20", "ad visit: weddings (wedding-leads)"),
        enq("funeral", "2026-10-21", gclid="Cj0KCQjwTestClickId777"),
        enq("corporate", "2026-10-02", "ad visit: christmas-pricing")])
    ads = FakeClicksAds(daily=[("2026-10-21", 24295921372, XMAS)],
                        click_view={"2026-10-21": {"Cj0KCQjwTestClickId777": "funeral expert campaign"}})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        got = wr.enquiries_section(wr.AdClicks(ads, mon), mon, path)
    text = buf.getvalue()
    assert len(got) == 5, got
    assert "   2026-10-22 · christmas · web form · C Christmas carol singers – events 2026 (only a Christmas carol " \
           "singers – events 2026 ad click that day or the day before, cookies declined?; never counts) · heard: " \
           "Searching on Google" in text.splitlines(), text
    assert "   2026-10-21 · funeral · web form · A funeral expert campaign (click reference (gclid, its click's " \
           "campaign))" in text.splitlines(), text
    assert "   2026-10-20 · wedding · web form · B wedding-leads (ad visit: weddings (wedding-leads))" in text, text
    assert "2026-10-02" not in text.split("-- by campaign")[0], "the week starts 7 days back"
    assert "   Christmas carol singers – events 2026: A 0 · B 1 · C 2" in text.splitlines(), text
    assert "   funeral expert campaign: A 1 · B 0 · C 0" in text.splitlines(), text
    for word in ("Venue", "Town", "singers,"):
        assert word not in text, word


def test_section_11_credits_a_booking_by_its_enquirys_grade_when_the_ledger_has_no_click_reference():
    import economics as ec
    mon = datetime.date(2026, 10, 26)
    write_rows(ec.lcs_money.LEDGER, ["booking_ref", "invoice_date", "event_date", "occasion", "value_gbp", "gclid",
                                     "enquiry_date", "notes"],
               [{"booking_ref": "0112", "invoice_date": "2026-10-20", "occasion": "christmas", "value_gbp": "1150",
                 "gclid": "", "enquiry_date": "2026-10-15", "notes": ""},
                {"booking_ref": "0512", "invoice_date": "2026-10-21", "occasion": "christmas", "value_gbp": "1350",
                 "gclid": "Cj0KCQjwTestClickId888", "enquiry_date": "2026-10-16", "notes": ""},
                {"booking_ref": "0612", "invoice_date": "2026-10-21", "occasion": "christmas", "value_gbp": "900",
                 "gclid": "", "enquiry_date": "2026-10-16", "notes": ""}])
    rows = [dict(enq("christmas", "2026-10-15", "ad visit: christmas"), booking_ref="0112"),
            dict(enq("christmas", "2026-10-16"), booking_ref="0612"),
            enq("wedding", "2026-10-18", "heard: A Google ad")]
    ads = FakeClicksAds(daily=[], click_view={"2026-10-16": {"Cj0KCQjwTestClickId888": XMAS}},
                        spend=[(24295921372, XMAS, 120.0, 40), (23739971001, "wedding-leads", 30.0, 9)])
    g = graded(*rows)
    bookings, enquiries = wr.season_attribution(wr.AdClicks(ads, mon), mon, datetime.date(2026, 9, 1), g,
                                                {"christmas": XMAS, "wedding": "wedding-leads"})
    assert bookings == [(XMAS, 1150.0, "B"), (XMAS, 1350.0, "click"), (None, 900.0, None)], bookings
    assert enquiries == [(XMAS, "B"), (None, None), (None, None)], enquiries
    lines = ec.cost_lines(ec.cost_table({XMAS: (120_000_000, 40), "wedding-leads": (30_000_000, 9)}, bookings, enquiries))
    assert lines[0] == (f"{XMAS}: spend £120.00 · clicks 40 · enquiries 1 (A 0 · B 1) · bookings 2 (1 by their "
                        "enquiry's grade, no click reference) · booked £2,500.00 · per enquiry £120.00 · per booking "
                        "£60.00"), lines[0]
    assert lines[-2] == "unattributed: enquiries 2 · bookings 1 · booked £900.00", lines
    # the whole section, with the shared click lookups and its private cache
    write_rows(Path(TMP) / "enquiries.csv", ENQ_COLS, rows)
    buf = io.StringIO()
    clicks = wr.AdClicks(ads, mon)
    with contextlib.redirect_stdout(buf):
        wr.cost_section(ads, mon, clicks, g)
    text = buf.getvalue()
    assert "bookings 2 (1 by their enquiry's grade, no click reference)" in text and "failed" not in text, text
    assert stat.S_IMODE(os.stat(Path(TMP) / "gclid-campaigns.json").st_mode) == 0o600


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
