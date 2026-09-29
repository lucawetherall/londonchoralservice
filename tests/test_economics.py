#!/usr/bin/env python3
"""Tests for scripts/reports/economics.py (report sections 11-13). Stdlib only, no network."""
import datetime, json, os, stat, sys, tempfile

TMP = tempfile.mkdtemp(prefix="lcs-econ-test-")
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import economics as ec

D = datetime.date
MON = D(2026, 9, 28)  # a Monday


# ---------- attribution ----------

class FakeClicks:
    """Stands in for the click_view GAQL query: date -> {gclid: campaign}. Counts the dates asked for."""

    def __init__(self, by_date):
        self.by_date = by_date
        self.asked = []

    def __call__(self, day):
        self.asked.append(day)
        return self.by_date.get(day, {})


def test_attribution_walks_back_from_the_enquiry_date_and_stops_when_found():
    fake = FakeClicks({D(2026, 9, 20): {"abc": "wedding-leads"}})
    cache = {}
    assert ec.attribute("abc", D(2026, 9, 22), fake, cache, today=MON) == "wedding-leads"
    assert fake.asked == [D(2026, 9, 22), D(2026, 9, 21), D(2026, 9, 20)], fake.asked
    assert cache == {"abc": "wedding-leads"}


def test_attribution_is_cached_so_each_gclid_is_looked_up_once():
    fake = FakeClicks({D(2026, 9, 20): {"abc": "wedding-leads"}})
    cache = {}
    ec.attribute("abc", D(2026, 9, 22), fake, cache, today=MON)
    n = len(fake.asked)
    assert ec.attribute("abc", D(2026, 9, 22), fake, cache, today=MON) == "wedding-leads"
    assert len(fake.asked) == n


def test_attribution_not_found_in_30_days_is_cached_as_unattributed():
    fake = FakeClicks({D(2026, 8, 1): {"old": "wedding-leads"}})  # 52 days before: outside the window
    cache = {}
    assert ec.attribute("old", D(2026, 9, 22), fake, cache, today=MON) is None
    assert len(fake.asked) == 31, len(fake.asked)  # the enquiry date and 30 days back
    assert "old" not in cache and list(cache.values()) == [None], cache  # the miss is keyed on gclid and date
    ec.attribute("old", D(2026, 9, 22), fake, cache, today=MON)
    assert len(fake.asked) == 31


def test_a_click_not_yet_in_click_view_is_not_cached_and_is_found_later():
    # Monday 28 Sep: the 27 Sep click hasn't landed in click_view yet, so the search isn't complete
    cache = {}
    assert ec.attribute("G1", "2026-09-27", FakeClicks({}), cache, today=MON) is None
    assert cache == {}, cache
    assert ec.attribute("G1", "2026-09-28", FakeClicks({}), cache, today=MON) is None
    assert cache == {}, cache  # today isn't settled either
    later = FakeClicks({D(2026, 9, 27): {"G1": "Weddings"}})
    assert ec.attribute("G1", "2026-09-27", later, cache, today=MON + datetime.timedelta(7)) == "Weddings"
    assert cache == {"G1": "Weddings"}


def test_a_settled_miss_two_days_back_is_cached():
    cache = {}
    ec.attribute("G1", "2026-09-26", FakeClicks({}), cache, today=MON)
    assert cache == {"G1@2026-09-26/30": None}, cache


def test_an_unparseable_enquiry_date_returns_none_and_caches_nothing():
    fake = FakeClicks({MON: {"G3": "Weddings"}})
    cache = {}
    for bad in ("28/09/2026", "next week", "2026-13-01"):
        assert ec.attribute("G3", bad, fake, cache, today=MON) is None
    assert cache == {} and fake.asked == []


def test_a_blank_enquiry_date_searches_the_whole_retained_window_then_a_filled_one_still_works():
    click = D(2026, 8, 10)
    fake = FakeClicks({click: {"G2": "Funerals"}})
    cache = {}
    # invoiced 40 days after the click, no enquiry date: the 30-day walk would miss it
    row = {"gclid": "G2", "enquiry_date": "", "invoice_date": "2026-09-19"}
    assert ec.attribute_booking(row, fake, cache, today=MON) == "Funerals"
    assert cache == {"G2": "Funerals"}
    # a miss on the blank-date search doesn't block a later search once enquiry_date is filled
    cache = {}
    none = FakeClicks({})
    assert ec.attribute_booking({"gclid": "G2", "enquiry_date": "", "invoice_date": "2026-09-19"}, none, cache, MON) is None
    assert min(none.asked) == MON - datetime.timedelta(days=ec.CLICK_VIEW_DAYS - 1)
    assert "G2" not in cache
    assert ec.attribute_booking({"gclid": "G2", "enquiry_date": "2026-08-11", "invoice_date": "2026-09-19"},
                                fake, cache, MON) == "Funerals"


def test_an_old_cached_miss_under_the_bare_gclid_is_searched_again():
    cache = {"G4": None}  # written by an earlier version
    assert ec.attribute("G4", "2026-09-20", FakeClicks({D(2026, 9, 19): {"G4": "Weddings"}}), cache, MON) == "Weddings"


def test_a_corrupt_gclid_cache_is_moved_aside_and_a_fresh_one_started():
    d = tempfile.mkdtemp(dir=TMP)
    path = os.path.join(d, "gclid-campaigns.json")
    open(path, "w").write('{"abc": "wedd')
    assert ec.load_gclid_cache(path, MON) == {}
    assert not os.path.exists(path)
    assert open(os.path.join(d, "gclid-campaigns.json.corrupt-2026-09-28")).read() == '{"abc": "wedd'
    open(path, "w").write("[1, 2]")  # valid JSON but not a mapping; the first corrupt copy is kept
    assert ec.load_gclid_cache(path, MON) == {}
    assert sorted(os.listdir(d)) == ["gclid-campaigns.json.corrupt-2026-09-28",
                                     "gclid-campaigns.json.corrupt-2026-09-28-2"], os.listdir(d)
    assert ec.load_gclid_cache(os.path.join(d, "missing.json"), MON) == {}
    ec.save_json_private(path, {"abc": "wedding-leads"})
    assert ec.load_gclid_cache(path, MON) == {"abc": "wedding-leads"}


def test_braid_prefixes_and_blank_gclids_are_unattributed_without_a_lookup():
    fake = FakeClicks({})
    cache = {}
    for ref in ("gbraid:0AAAA", "wbraid:CkQ", "", None, "   "):
        assert ec.attribute(ref, D(2026, 9, 22), fake, cache, today=MON) is None
    assert fake.asked == [] and cache == {}


def test_attribution_skips_future_dates_and_dates_google_no_longer_keeps():
    fake = FakeClicks({})
    ec.attribute("zzz", D(2026, 9, 30), fake, {}, today=MON)  # enquiry date after today (typo)
    assert max(fake.asked) == MON
    fake2 = FakeClicks({})
    ec.attribute("yyy", D(2026, 6, 15), fake2, {}, today=MON)  # more than 90 days ago: nothing to ask
    assert fake2.asked == []


def test_a_failed_lookup_is_not_cached():
    def boom(day):
        raise RuntimeError("quota")
    cache = {}
    try:
        ec.attribute("abc", D(2026, 9, 22), boom, cache, today=MON)
        raise AssertionError("expected the error to propagate")
    except RuntimeError:
        pass
    assert cache == {}


def test_gclid_cache_file_is_private_and_round_trips():
    path = os.path.join(TMP, "gclid-campaigns.json")
    ec.save_json_private(path, {"abc": "wedding-leads", "old": None})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert ec.load_json(path, {}) == {"abc": "wedding-leads", "old": None}
    assert ec.load_json(os.path.join(TMP, "missing.json"), {}) == {}


# ---------- bookings and enquiries in the season ----------

def test_season_bookings_skip_cancelled_and_earlier_invoices():
    rows = [
        {"booking_ref": "1", "invoice_date": "2026-09-05", "value_gbp": "£1,150", "gclid": "abc", "enquiry_date": "2026-09-01", "notes": ""},
        {"booking_ref": "2", "invoice_date": "2026-09-06", "value_gbp": "650", "gclid": "", "enquiry_date": "", "notes": "CANCELLED 2026-09-10"},
        {"booking_ref": "3", "invoice_date": "2026-09-07", "value_gbp": "650", "gclid": "", "enquiry_date": "", "notes": "client cancelled by phone"},
        {"booking_ref": "4", "invoice_date": "2026-08-31", "value_gbp": "650", "gclid": "", "enquiry_date": "", "notes": ""},
        {"booking_ref": "5", "invoice_date": "2026-09-20", "value_gbp": "575", "gclid": "gbraid:x", "enquiry_date": "2026-09-18", "notes": "PENDING: invoiced"},
        {"booking_ref": "6", "invoice_date": "2026-09-21", "value_gbp": "400", "gclid": "", "enquiry_date": "", "notes": "not cancelledish: rescheduled"},
    ]
    got = ec.season_bookings(rows, D(2026, 9, 1))
    assert [r["booking_ref"] for r in got] == ["1", "5", "6"], got


def test_season_bookings_share_check_payments_cancelled_rule():
    def counts(notes):
        return bool(ec.season_bookings([{"invoice_date": "2026-09-10", "notes": notes}], D(2026, 9, 1)))
    assert counts("not cancelled, date moved")
    assert counts("may be cancelling")
    assert not counts("cancellation confirmed 2026-09-20")
    assert not counts("client cancelling")


def test_season_enquiries_use_first_seen():
    rows = [{"first_seen": "2026-09-02T10:00:00", "gclid": "abc"}, {"first_seen": "2026-08-30", "gclid": ""},
            {"first_seen": "", "gclid": ""}]
    got = ec.season_enquiries(rows, D(2026, 9, 1))
    assert len(got) == 1 and got[0]["gclid"] == "abc"


# ---------- cost maths ----------

def test_cost_table_per_campaign_unattributed_and_total():
    spend = {"wedding-leads": (30_000_000, 12), "funeral expert campaign": (0, 0), "Christmas carols": (10_500_000, 7)}
    bookings = [("wedding-leads", 1150.0), ("wedding-leads", 650.0), (None, 575.0)]
    enquiries = ["wedding-leads", "wedding-leads", "wedding-leads", "Christmas carols", None]
    t = ec.cost_table(spend, bookings, enquiries)
    by = {r["campaign"]: r for r in t["campaigns"]}
    w = by["wedding-leads"]
    assert (w["spend_gbp"], w["clicks"], w["enquiries"], w["bookings"], w["booked_gbp"]) == (30.0, 12, 3, 2, 1800.0)
    assert w["cost_per_enquiry"] == 10.0 and w["cost_per_booking"] == 15.0
    f = by["funeral expert campaign"]
    assert f["cost_per_enquiry"] is None and f["cost_per_booking"] is None
    c = by["Christmas carols"]
    assert c["cost_per_enquiry"] == 10.5 and c["cost_per_booking"] is None
    assert t["unattributed"] == {"enquiries": 1, "bookings": 1, "booked_gbp": 575.0}
    tot = t["total"]
    assert (tot["spend_gbp"], tot["clicks"], tot["enquiries"], tot["bookings"], tot["booked_gbp"]) == (40.5, 19, 5, 3, 2375.0)
    assert tot["cost_per_enquiry"] == 8.1 and tot["cost_per_booking"] == 13.5


def test_cost_table_without_the_pipeline_sheet_has_no_enquiry_figures():
    t = ec.cost_table({"wedding-leads": (5_000_000, 2)}, [], None)
    w = t["campaigns"][0]
    assert w["enquiries"] is None and w["cost_per_enquiry"] is None and w["cost_per_booking"] is None
    assert t["total"]["enquiries"] is None
    lines = ec.cost_lines(t)
    assert "–" in lines[0] or "–" in lines[1]
    assert not any("None" in l for l in lines), lines


def test_booking_attributed_to_a_campaign_with_no_spend_row_still_shows():
    t = ec.cost_table({}, [("old campaign", 650.0)], [])
    assert t["campaigns"][0]["campaign"] == "old campaign" and t["campaigns"][0]["spend_gbp"] == 0.0


def test_cost_lines_format_money_and_dashes():
    t = ec.cost_table({"wedding-leads": (30_000_000, 12)}, [("wedding-leads", 1150.0)], ["wedding-leads"])
    lines = ec.cost_lines(t)
    assert lines[0] == ("wedding-leads: spend £30.00 · clicks 12 · enquiries 1 · bookings 1 · booked £1,150.00"
                        " · per enquiry £30.00 · per booking £30.00"), lines[0]
    assert lines[-2] == "unattributed: enquiries 0 · bookings 0 · booked £0.00", lines[-2]
    assert lines[-1].startswith("total: spend £30.00 · clicks 12"), lines[-1]


def test_divide_returns_none_on_zero():
    assert ec.divide(10, 0) is None and ec.divide(0, 0) is None and ec.divide(9, 3) == 3.0
    assert ec.gbp_or_dash(None) == "–" and ec.gbp_or_dash(1234.5) == "£1,234.50"


# ---------- ads-summary weeks ----------

def test_last_full_weeks_are_monday_to_sunday():
    weeks = ec.full_weeks(MON, 8)
    assert weeks[-1] == D(2026, 9, 21) and weeks[0] == D(2026, 8, 3) and len(weeks) == 8
    assert all(w.weekday() == 0 for w in weeks)
    # on a Sunday the current week isn't finished yet
    assert ec.full_weeks(D(2026, 9, 27), 1) == [D(2026, 9, 14)]
    assert ec.full_weeks(D(2026, 9, 29), 1) == [D(2026, 9, 21)]


def test_week_buckets_sum_days_and_fill_empty_weeks():
    daily = [(D(2026, 9, 21), 1_000_000, 2, 0.0), (D(2026, 9, 27), 2_500_000, 3, 1.0),  # same week
             (D(2026, 9, 28), 9_000_000, 9, 9.0),  # today: not a full week, ignored
             (D(2026, 8, 2), 9_000_000, 9, 9.0),   # before the 8 weeks, ignored
             ("2026-08-03", 500_000, 1, 0.5)]      # ISO strings accepted
    got = ec.week_buckets(daily, MON, 8)
    assert len(got) == 8
    assert got[0] == {"week_start": "2026-08-03", "spend_gbp": 0.5, "clicks": 1, "conversions": 0.5}, got[0]
    assert got[-1] == {"week_start": "2026-09-21", "spend_gbp": 3.5, "clicks": 5, "conversions": 1.0}, got[-1]
    assert got[3] == {"week_start": "2026-08-24", "spend_gbp": 0.0, "clicks": 0, "conversions": 0.0}


def test_ads_summary_shape_and_file_mode():
    t = ec.cost_table({"wedding-leads": (5_000_000, 2)}, [], None)
    summary = ec.ads_summary(ec.week_buckets([], MON, 8), t, D(2026, 9, 1), datetime.datetime(2026, 9, 28, 9, 0))
    assert set(summary) == {"generated", "weeks", "season"}
    assert summary["generated"] == "2026-09-28T09:00:00"
    assert summary["season"]["start"] == "2026-09-01"
    assert summary["season"]["campaigns"][0]["campaign"] == "wedding-leads"
    path = os.path.join(TMP, "ads-summary.json")
    ec.save_json_private(path, summary)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert json.load(open(path))["weeks"][0]["week_start"] == "2026-08-03"


# ---------- seasonal budget windows ----------

WINDOWS = [
    {"name": "carols", "campaigns": ["christmas", "carol"], "start": "10-01", "end": "12-20", "daily_gbp": 5},
    {"name": "carols-off", "campaigns": ["christmas", "carol"], "start": "12-21", "end": "09-30", "daily_gbp": 1},
    {"name": "weddings-peak", "campaigns": ["wedding"], "start": "01-02", "end": "04-30", "daily_gbp": 5},
    {"name": "weddings-base", "campaigns": ["wedding"], "start": "05-01", "end": "01-01", "daily_gbp": 3},
    {"name": "funerals", "campaigns": ["funeral"], "start": "01-01", "end": "12-31", "daily_gbp": 3},
]
CAMPAIGNS = [
    {"name": "Christmas carol singers – events 2026", "status": "ENABLED", "budget_gbp": 5.0},
    {"name": "wedding-leads", "status": "ENABLED", "budget_gbp": 3.0},
    {"name": "funeral expert campaign", "status": "ENABLED", "budget_gbp": 2.0},
    {"name": "old test campaign", "status": "PAUSED", "budget_gbp": 1.0},
]


def test_windows_wrap_round_the_new_year():
    assert ec.in_window(D(2026, 12, 25), "12-21", "09-30")
    assert ec.in_window(D(2027, 9, 30), "12-21", "09-30")
    assert not ec.in_window(D(2026, 10, 1), "12-21", "09-30")
    assert ec.in_window(D(2027, 1, 1), "05-01", "01-01") and not ec.in_window(D(2027, 1, 2), "05-01", "01-01")
    assert ec.in_window(D(2026, 12, 20), "10-01", "12-20") and not ec.in_window(D(2026, 12, 21), "10-01", "12-20")


def test_proposals_on_28_september():
    got = ec.proposals(CAMPAIGNS, WINDOWS, MON)
    lines = ec.proposal_lines(got)
    # carols-off (£1) runs to 30 Sep, so the £5 Christmas budget is proposed down; weddings-base £3 matches;
    # funerals £3 vs £2; the paused campaign is left alone.
    assert lines == [
        "PROPOSE: Christmas carol singers – events 2026 £5.00 → £1.00/day (window carols-off)",
        "PROPOSE: funeral expert campaign £2.00 → £3.00/day (window funerals)",
    ], lines


def test_proposals_on_1_october_match():
    cams = [dict(c) for c in CAMPAIGNS]
    cams[2]["budget_gbp"] = 3.0
    got = ec.proposals(cams, WINDOWS, D(2026, 10, 1))
    assert ec.proposal_lines(got) == ["budgets match the season's windows"]


def test_proposals_never_go_above_five_pounds_and_flag_the_window():
    windows = [{"name": "greedy", "campaigns": ["wedding"], "start": "01-01", "end": "12-31", "daily_gbp": 8}]
    got = ec.proposals([{"name": "wedding-leads", "status": "ENABLED", "budget_gbp": 3.0}], windows, MON)
    lines = ec.proposal_lines(got)
    assert "CONFIG ERROR: window greedy asks for £8.00/day, above the £5 cap: capped at £5.00" in lines, lines
    assert "PROPOSE: wedding-leads £3.00 → £5.00/day (window greedy)" in lines, lines
    assert all("£8" not in l for l in lines if l.startswith("PROPOSE")), lines


def test_a_capped_window_that_matches_the_budget_proposes_nothing_but_still_flags():
    windows = [{"name": "greedy", "campaigns": ["wedding"], "start": "01-01", "end": "12-31", "daily_gbp": 6}]
    got = ec.proposals([{"name": "wedding-leads", "status": "ENABLED", "budget_gbp": 5.0}], windows, MON)
    lines = ec.proposal_lines(got)
    assert lines == ["CONFIG ERROR: window greedy asks for £6.00/day, above the £5 cap: capped at £5.00"], lines


def test_config_errors_for_bad_dates_and_overlaps():
    windows = [{"name": "bad", "campaigns": ["wedding"], "start": "13-01", "end": "12-31", "daily_gbp": 3},
               {"name": "a", "campaigns": ["funeral"], "start": "01-01", "end": "12-31", "daily_gbp": 3},
               {"name": "b", "campaigns": ["funeral"], "start": "09-01", "end": "10-31", "daily_gbp": 2}]
    cams = [{"name": "funeral expert campaign", "status": "ENABLED", "budget_gbp": 3.0},
            {"name": "wedding-leads", "status": "ENABLED", "budget_gbp": 3.0}]
    lines = ec.proposal_lines(ec.proposals(cams, windows, MON))
    assert any(l.startswith("CONFIG ERROR: window bad") for l in lines), lines
    assert "CONFIG ERROR: funeral expert campaign is in 2 windows today (a, b): no proposal" in lines, lines
    assert not any(l.startswith("PROPOSE: funeral") for l in lines), lines


def test_non_positive_or_non_finite_daily_budgets_are_config_errors():
    cams = [{"name": "Weddings", "status": "ENABLED", "budget_gbp": 4.0}]
    for bad in (-1, 0, "0", "nan", "inf"):
        w = [{"name": "x", "campaigns": ["wedding"], "start": "01-01", "end": "12-31", "daily_gbp": bad}]
        lines = ec.proposal_lines(ec.proposals(cams, w, MON))
        assert lines[0].startswith("CONFIG ERROR: window x"), (bad, lines)
        assert not any(l.startswith("PROPOSE") for l in lines), (bad, lines)
    w = [{"name": "s", "campaigns": ["wedding"], "start": "01-01", "end": "12-31", "daily_gbp": "4.5"}]
    assert ec.proposal_lines(ec.proposals(cams, w, MON)) == ["PROPOSE: Weddings £4.00 → £4.50/day (window s)"]


def test_blank_campaign_substrings_are_config_errors():
    cams = [{"name": "Weddings", "status": "ENABLED", "budget_gbp": 4.0},
            {"name": "Funerals", "status": "ENABLED", "budget_gbp": 4.0}]
    for subs in ([""], ["  "], ["wedding", ""]):
        w = [{"name": "s", "campaigns": subs, "start": "01-01", "end": "12-31", "daily_gbp": 3}]
        lines = ec.proposal_lines(ec.proposals(cams, w, MON))
        assert lines[0] == "CONFIG ERROR: window s has a blank campaign name: skipped", (subs, lines)
        assert not any(l.startswith("PROPOSE") for l in lines), (subs, lines)


def test_load_windows_keeps_null_campaigns_blank_and_a_bad_season_start_is_none():
    d = tempfile.mkdtemp(dir=TMP)
    for text, want in (("season_start: 2026-13-01\n", None), ("windows: []\n", None),
                       ("season_start: nonsense\n", None), ("season_start: 2026-09-01\n", D(2026, 9, 1))):
        p = os.path.join(d, "w.yml")
        open(p, "w").write(text)
        assert ec.load_windows(p)["season_start"] == want, text
    open(p, "w").write('windows:\n  - {name: s, campaigns: [~], start: "01-01", end: "12-31", daily_gbp: 3}\n')
    assert ec.load_windows(p)["windows"][0]["campaigns"] == [""]


def test_enabled_campaign_with_no_window_is_noted_not_proposed():
    got = ec.proposals([{"name": "brand terms", "status": "ENABLED", "budget_gbp": 2.0}], WINDOWS, MON)
    assert ec.proposal_lines(got) == ["no window covers brand terms today: left as it is",
                                      "budgets match the season's windows"]


def test_seed_file_loads_and_stays_under_the_cap():
    cfg = ec.load_windows(os.path.join(ROOT, "data", "budget-windows.yml"))
    assert cfg["season_start"] == D(2026, 9, 1)
    names = [w["name"] for w in cfg["windows"]]
    assert names == ["carols", "carols-late", "carols-off", "weddings", "funerals"], names
    assert all(w["daily_gbp"] <= 5 for w in cfg["windows"] if w["name"] != "carols")
    cams = [dict(c, id="24295921372") if c["name"].startswith("Christmas") else c for c in CAMPAIGNS]
    for day in (D(2026, 1, 1), D(2026, 1, 2), D(2026, 5, 1), D(2026, 10, 1), D(2026, 12, 21), MON):
        items = ec.proposals(cams, cfg["windows"], day)
        assert not [i for i in items if i["kind"] == "error"], (day, items)


def test_the_christmas_exception_allows_eight_pounds_only_for_its_id_and_dates():
    cfg = ec.load_windows(os.path.join(ROOT, "data", "budget-windows.yml"))
    xmas = {"name": "Christmas carol singers – events 2026", "status": "ENABLED", "budget_gbp": 5.0,
            "id": "24295921372"}
    lines = ec.proposal_lines(ec.proposals([xmas], cfg["windows"], D(2026, 10, 1)))
    assert lines == ["PROPOSE: Christmas carol singers – events 2026 £5.00 → £8.00/day (window carols)"], lines
    lines = ec.proposal_lines(ec.proposals([dict(xmas, budget_gbp=8.0)], cfg["windows"], D(2026, 12, 14)))
    assert lines == ["PROPOSE: Christmas carol singers – events 2026 £8.00 → £5.00/day (window carols-late)"], lines
    # the same name without the id, or the same id after 13 Dec 2026, gets the £5 cap
    for cam, day in ((dict(xmas, id=None), D(2026, 10, 1)), (xmas, D(2027, 10, 1))):
        lines = ec.proposal_lines(ec.proposals([cam], cfg["windows"], day))
        assert lines == ["CONFIG ERROR: window carols asks for £8.00/day, above the £5 cap: capped at £5.00"], lines


# ---------- Search Console shortlist ----------

def row(query, page, impressions, position, clicks=0):
    return {"keys": [query, page], "impressions": impressions, "position": position, "clicks": clicks,
            "ctr": clicks / impressions if impressions else 0}


SITE = "https://londonchoralservice.com"


def test_negative_blocking_follows_googles_match_rules():
    negs = [("singer", "BROAD"), ("albert hall", "PHRASE"), ("carol singers", "EXACT"), ("brass", "BROAD")]
    assert ec.negative_blocking("best singer for wedding", negs) == ("singer", "BROAD")
    assert ec.negative_blocking("wedding singers", negs) is None  # no plurals or close variants
    assert ec.negative_blocking("carols at the royal albert hall", negs) == ("albert hall", "PHRASE")
    assert ec.negative_blocking("hall albert carols", negs) is None  # phrase needs the order
    assert ec.negative_blocking("carol singers", negs) == ("carol singers", "EXACT")
    assert ec.negative_blocking("hire carol singers", negs) is None  # exact needs the whole term
    assert ec.negative_blocking("Brass band music for a funeral", negs) == ("brass", "BROAD")
    assert ec.negative_blocking("st paul's", [("st paul's", "PHRASE")]) == ("st paul's", "PHRASE")
    assert ec.negative_blocking("", negs) is None and ec.negative_blocking(None, []) is None


def test_search_term_flag_follows_the_targeting_rule():
    for term, word in (("wedding singer london", "singer"), ("Funeral SOLOIST", "soloist"), ("solo violin", "solo"),
                       ("female vocalists for hire", "vocalists"), ("carol singer hire", "singer")):
        assert ec.search_term_flag(term) == f"solo-singer search ('{word}'): choirs of four or more only", term
    assert ec.search_term_flag("choir lyrics") == "not a hiring search ('lyrics')"
    assert ec.search_term_flag("join a choir") == "not a hiring search ('join')"
    assert ec.search_term_flag("funeral songs") == "no choir or hiring word"
    for term in ("wedding singers london", "christmas carol singers", "hire a choir", "london choral service",
                 "carols in the city", "funeral quartet"):
        assert ec.search_term_flag(term) is None, term
    assert ec.search_term_flag("") == "no choir or hiring word" and ec.search_term_flag(None) == "no choir or hiring word"


def test_hiring_intent_keeps_singers_and_drops_singer():
    assert ec.hiring_intent("wedding singers london")
    assert not ec.hiring_intent("wedding singer london")
    assert not ec.hiring_intent("carol singer hire")
    assert ec.hiring_intent("hire a choir")
    assert ec.hiring_intent("christmas carol singers")
    assert not ec.hiring_intent("funeral soloist")
    assert not ec.hiring_intent("choir lyrics")
    assert not ec.hiring_intent("free choir music")
    assert not ec.hiring_intent("funeral songs")  # no hiring word at all
    assert not ec.hiring_intent("Solo Vocalist For Wedding")


def test_hiring_intent_uses_whole_words_and_drops_non_hiring_queries():
    for q in ("facebook wedding band", "booklet for funeral", "yorkshire funeral music", "caroline flack funeral",
              "join a choir london", "carol service order of service", "9 lessons and carols readings",
              "nine lessons and carols readings", "choir auditions london", "wedding singer", "singer's fee",
              "funeral soloists", "solo singers for weddings"):
        assert not ec.hiring_intent(q), q
    for q in ("singers for funeral", "carol singers london", "hire a choir for wedding", "book choir wedding",
              "carollers for hire", "christmas carolers singers", "a cappella group hire", "choristers for a wedding",
              "string quartets and choir", "booking a choir"):
        assert ec.hiring_intent(q), q


def test_shortlist_filters_position_impressions_and_intent():
    rows = [row("choir for funeral", f"{SITE}/funerals.html", 100, 9.0),
            row("hire a choir", f"{SITE}/", 50, 15.0),
            row("wedding singer london", f"{SITE}/weddings.html", 500, 10.0),   # singular singer: out
            row("wedding singers london", f"{SITE}/weddings.html", 60, 20.0),   # position 20: in
            row("carol singers", f"{SITE}/christmas.html", 900, 7.9),           # too high: out
            row("church choir hire", f"{SITE}/", 900, 20.1),                   # too low: out
            row("gospel choir hire", f"{SITE}/", 19, 12.0)]                   # 19 impressions: out
    got = ec.shortlist(rows)
    assert [g["query"] for g in got] == ["choir for funeral", "wedding singers london", "hire a choir"], got


def test_shortlist_merges_pages_per_query_and_keeps_top_ten():
    rows = [row("choir hire london", f"{SITE}/services.html", 30, 10.0, 1),
            row("choir hire london", f"{SITE}/", 10, 16.0)]
    rows += [row(f"choir hire {i}", f"{SITE}/", 100 + i, 12.0) for i in range(12)]
    got = ec.shortlist(rows)
    assert len(got) == 10 and got[0]["query"] == "choir hire 11"
    merged = ec.shortlist(rows[:2])[0]
    assert merged["page"] == f"{SITE}/services.html" and merged["impressions"] == 40
    assert abs(merged["position"] - 11.5) < 1e-9 and abs(merged["ctr"] - 0.025) < 1e-9


def test_suggested_fix_rules():
    h2s = {f"{SITE}/funerals.html": ["Music for the funeral", "Prices"],
           f"{SITE}/weddings.html": ["Our wedding packages"],
           f"{SITE}/": ["Why book us"]}
    rows = [row("choir for funeral", f"{SITE}/funerals.html", 100, 9.0),      # h2 has "funeral", 8-12: link
            row("wedding singers london", f"{SITE}/weddings.html", 90, 15.0),  # h2 has "wedding", 15: title/meta
            row("hire a gospel choir", f"{SITE}/", 80, 11.0)]                 # no h2 with "gospel": section
    got = {g["query"]: g["fix"] for g in ec.shortlist(rows, h2s.get)}
    assert got["choir for funeral"] == "add an internal link from a related page with anchor 'choir for funeral'"
    assert got["wedding singers london"] == "strengthen the title/meta for 'wedding singers london'"
    assert got["hire a gospel choir"] == "add a section answering 'hire a gospel choir'"


def test_suggested_fix_strips_one_plural_s_but_not_ss():
    item = {"query": "bass singers", "position": 15.0}
    assert ec.suggested_fix(item, ["Bass and tenor"]) == "strengthen the title/meta for 'bass singers'"
    assert ec.suggested_fix(item, ["Tenors"]) == "add a section answering 'bass singers'"  # "ba" must not match
    item = {"query": "hire a choir for weddings", "position": 15.0}
    assert ec.suggested_fix(item, ["Our wedding packages"]) == "strengthen the title/meta for 'hire a choir for weddings'"


def test_main_term_skips_generic_words():
    assert ec.main_term("choir for funeral london") == "funeral"
    assert ec.main_term("christmas carol singers") == "christmas"
    assert ec.main_term("hire a choir") == "choir"
    assert ec.main_term("9 lessons and carols readings") == "lessons"  # numbers are never the main term


def test_unknown_page_skips_the_h2_rule():
    got = ec.shortlist([row("hire a gospel choir", f"{SITE}/nowhere", 80, 15.0)], lambda page: None)
    assert got[0]["fix"] == "strengthen the title/meta for 'hire a gospel choir'"


def test_shortlist_lines():
    got = ec.shortlist([row("choir for funeral", f"{SITE}/funerals.html", 200, 9.04, 3)])
    lines = ec.shortlist_lines(got)
    assert lines[0] == "choir for funeral → /funerals.html · pos 9.0 · impr 200 · CTR 1.5%", lines[0]
    assert lines[1].startswith("   suggested fix: "), lines[1]
    assert ec.shortlist_lines([]) == ["(no hiring-intent queries at positions 8–20 with 20+ impressions)"]


def test_first_monday_and_window():
    assert ec.is_first_monday(D(2026, 10, 5)) and not ec.is_first_monday(MON) and not ec.is_first_monday(D(2026, 10, 6))
    assert ec.next_first_monday(MON) == D(2026, 10, 5)
    assert ec.next_first_monday(D(2026, 10, 5)) == D(2026, 10, 5)
    assert ec.gsc_window(MON) == (D(2026, 8, 29), D(2026, 9, 25))


def test_page_h2s_reads_local_files():
    root = tempfile.mkdtemp(dir=TMP)
    os.makedirs(os.path.join(root, "areas", "london"))
    open(os.path.join(root, "index.html"), "w").write("<h2 class='x'>Why <em>book</em> us &amp; more</h2><h3>no</h3>")
    open(os.path.join(root, "weddings.html"), "w").write("<h2>Wedding\n music</h2>")
    open(os.path.join(root, "areas", "london", "index.html"), "w").write("<h2>London</h2>")
    h2 = ec.page_h2s_from(root)
    assert h2(f"{SITE}/") == ["Why book us & more"]
    assert h2(f"{SITE}/weddings") == ["Wedding music"]
    assert h2(f"{SITE}/weddings.html?x=1#y") == ["Wedding music"]
    assert h2(f"{SITE}/areas/london/") == ["London"]
    assert h2(f"{SITE}/missing.html") is None
    assert h2(f"{SITE}/../../etc/passwd") is None
    assert h2("https://x/%2e%2e/%2e%2e/etc/passwd") is None and h2("https://x//etc/passwd") is None
    assert h2("file:///etc/passwd") is None and h2("/etc/hosts") is None
    open(os.path.join(root, "notes.py"), "w").write("<h2>not a page</h2>")
    assert h2(f"{SITE}/notes.py") is None  # only .html pages are read


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
