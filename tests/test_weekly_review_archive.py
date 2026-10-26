#!/usr/bin/env python3
"""Tests for the --save-report archiving in scripts/reports/weekly_review.py.

Stdlib only; never touches the real private files or the network. The Ads/GA4/Search
Console/ledger/money sections are network-calling, so this only exercises tee_to and the
--save-report wiring around them (main()'s run_sections is monkeypatched for the wiring test).

    .venv/bin/python tests/test_weekly_review_archive.py
"""
import contextlib
import io
import os
import stat
import sys
import tempfile

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import weekly_review as wr  # noqa: E402

lm = wr.lm


def reset():
    for d, _, files in os.walk(TMP, topdown=False):
        for f in files:
            os.remove(os.path.join(d, f))
        if d != TMP:
            os.rmdir(d)


def test_tee_to_prints_and_writes_the_same_text():
    reset()
    path = os.path.join(TMP, "reports", "2026-09-28.txt")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        with wr.tee_to(path):
            print("== 1. Campaigns")
            print("hello")
    assert out.getvalue() == "== 1. Campaigns\nhello\n"
    with open(path, encoding="utf-8") as f:
        assert f.read() == "== 1. Campaigns\nhello\n"


def test_tee_to_is_mode_600_in_a_mode_700_directory():
    reset()
    path = os.path.join(TMP, "reports", "2026-09-28.txt")
    with contextlib.redirect_stdout(io.StringIO()):
        with wr.tee_to(path):
            print("x")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode) == 0o700


def test_tee_to_writes_atomically_no_leftover_tmp_file():
    reset()
    path = os.path.join(TMP, "reports", "2026-09-28.txt")
    with contextlib.redirect_stdout(io.StringIO()):
        with wr.tee_to(path):
            print("x")
    names = os.listdir(os.path.dirname(path))
    assert names == ["2026-09-28.txt"], names


def test_same_day_rerun_overwrites():
    reset()
    path = os.path.join(TMP, "reports", "2026-09-28.txt")
    with contextlib.redirect_stdout(io.StringIO()):
        with wr.tee_to(path):
            print("first run, long line of text")
        with wr.tee_to(path):
            print("second")
    with open(path, encoding="utf-8") as f:
        assert f.read() == "second\n"


def test_report_path_uses_lcs_money_private_and_todays_london_date():
    reset()
    import datetime
    d = datetime.date(2026, 9, 28)
    got = wr.report_path(d)
    assert str(got) == os.path.join(TMP, "reports", "2026-09-28.txt"), got
    assert got.parent == lm.PRIVATE / "reports"


def test_save_report_flag_archives_and_still_prints(monkeypatch):
    reset()
    printed = []

    def fake_run_sections(args):
        printed.append(args.since)
        print("== fake report body")

    monkeypatch.setattr(wr, "run_sections", fake_run_sections)
    import datetime
    fixed_today = datetime.date(2026, 9, 28)
    monkeypatch.setattr(wr.lm, "today", lambda *a, **k: fixed_today)
    monkeypatch.setattr(sys, "argv", ["weekly_review.py", "--save-report"])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.main()
    assert "== fake report body" in out.getvalue()
    path = wr.report_path(fixed_today)
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        assert f.read() == "== fake report body\n"


def test_without_the_flag_nothing_is_written():
    reset()

    def fake_run_sections(args):
        print("== fake report body")

    orig = wr.run_sections
    wr.run_sections = fake_run_sections
    orig_argv = sys.argv
    try:
        sys.argv = ["weekly_review.py"]
        with contextlib.redirect_stdout(io.StringIO()):
            wr.main()
    finally:
        wr.run_sections = orig
        sys.argv = orig_argv
    assert not os.path.isdir(os.path.join(TMP, "reports"))


REPORT = ("== 1. Campaigns\ncampaign line\n\n== 2. Search terms, last 7 days\nterm line\n\n"
          "== 4b. Google's recommendations\nrec line\n\n== 12. Seasonal budget rules\n"
          "   Christmas value check: £9.00 spent\n   stop rule: back to £5 if …\n"
          "   Command Centre proposals not written: RuntimeError\n")


def test_quiet_saves_the_report_and_prints_only_path_sections_and_problems(monkeypatch):
    reset()
    import datetime
    monkeypatch.setattr(wr, "run_sections", lambda args: print(REPORT, end=""))
    monkeypatch.setattr(wr.lm, "today", lambda *a, **k: datetime.date(2026, 10, 5))
    monkeypatch.setattr(sys, "argv", ["weekly_review.py", "--save-report", "--quiet"])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.main()
    path = wr.report_path(datetime.date(2026, 10, 5))
    with open(path, encoding="utf-8") as f:
        assert f.read() == REPORT
    lines = out.getvalue().splitlines()
    assert lines == [f"report saved: {path}", "sections: 1 2 4b 12",
                     "problem: Command Centre proposals not written: RuntimeError"], lines


def test_quiet_without_save_report_is_refused(monkeypatch):
    reset()
    monkeypatch.setattr(sys, "argv", ["weekly_review.py", "--quiet"])
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            wr.main()
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("--quiet alone should be refused")
    assert not os.path.isdir(os.path.join(TMP, "reports"))


def test_report_sections_prints_only_the_chosen_sections(monkeypatch):
    reset()
    import datetime
    sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
    import report_sections as rs
    monkeypatch.setattr(rs.lm, "today", lambda *a, **k: datetime.date(2026, 10, 5))
    os.makedirs(os.path.join(TMP, "reports"), exist_ok=True)
    with open(os.path.join(TMP, "reports", "2026-10-05.txt"), "w", encoding="utf-8") as f:
        f.write(REPORT)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = rs.main(["2", "4b"])
    assert code == 0
    assert out.getvalue() == ("== 2. Search terms, last 7 days\nterm line\n\n"
                              "== 4b. Google's recommendations\nrec line\n\n"), repr(out.getvalue())
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        assert rs.main(["1", "13"]) == 1
    assert "not in this report: 13" in err.getvalue()
    with contextlib.redirect_stderr(io.StringIO()):
        assert rs.main(["--date", "2026-10-12", "1"]) == 2


# ---------- each section on its own (the 12 Oct report died after its first Ads query) ----------

class RefreshError(Exception):
    """Stands in for google.auth.exceptions.RefreshError (an expired or revoked sign-in)."""


class FakeAdsException(Exception):
    """Shaped like GoogleAdsException: no message, the reason in .failure."""
    def __init__(self, failure):
        super().__init__()
        self.failure = failure


def test_failure_note_names_the_type_and_spots_google_sign_in_errors():
    assert wr.failure_note(ValueError("Some Client, 12 Example Road")) == "ValueError"
    hint = " (looks like a Google auth error: check the sign-in)"
    assert wr.failure_note(RefreshError("invalid_grant: Token has been expired or revoked.")) == "RefreshError" + hint
    assert wr.failure_note(FakeAdsException("errors { error_code { authentication_error: OAUTH_TOKEN_INVALID } }")) \
        == "FakeAdsException" + hint
    assert wr.failure_note(FakeAdsException("errors { error_code { query_error: BAD_FIELD } }")) == "FakeAdsException"
    assert wr.failure_note(PermissionError(13, "Permission denied")) == "PermissionError"  # a local file, not Google
    assert "Example" not in wr.failure_note(RuntimeError("credentials for Some Client at Example Road"))


def test_failure_note_adds_goatcounters_http_code_and_nothing_else():
    import goatcounter
    assert wr.failure_note(goatcounter.GoatCounterError("GoatCounter API answered 429", http_status=429)) \
        == "GoatCounterError (HTTP 429)"
    assert wr.failure_note(goatcounter.GoatCounterError(goatcounter.NO_KEY)) == f"GoatCounterError: {goatcounter.NO_KEY}"
    assert wr.failure_note(goatcounter.GoatCounterError("GoatCounter API not reached (TimeoutError)")) \
        == "GoatCounterError: GoatCounter API not reached (TimeoutError)"
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.run_section("5c", "Visits from every visitor (GoatCounter)",
                       lambda: (_ for _ in ()).throw(goatcounter.GoatCounterError(goatcounter.NO_KEY)))
    assert f"   SECTION 5c FAILED: GoatCounterError: {goatcounter.NO_KEY}" in out.getvalue().splitlines(), out.getvalue()
    e = ValueError("Some Client")
    e.http_status = True  # not a code
    assert wr.failure_note(e) == "ValueError"


def test_run_section_keeps_going_and_adds_the_heading_when_missing():
    def boom_before_heading():
        raise KeyError("x")

    def boom_after_heading():
        print("\n== 6. Search Console, a to b")
        print("   this week clicks 3")
        raise RefreshError("invalid_grant")

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert wr.run_section("5", "GA4, last 7 days", boom_before_heading) is None
        assert wr.run_section("6", "Search Console", boom_after_heading) is None
        assert wr.run_section("9", "Bookings ledger", lambda: print("\n== 9. Bookings ledger") or 42) == 42
    text = out.getvalue()
    assert text == ("\n== 5. GA4, last 7 days\n   SECTION 5 FAILED: KeyError\n"
                    "\n== 6. Search Console, a to b\n   this week clicks 3\n"
                    "   SECTION 6 FAILED: RefreshError (looks like a Google auth error: check the sign-in)\n"
                    "\n== 9. Bookings ledger\n"), repr(text)


def test_lazy_client_is_made_once_and_its_error_repeats():
    made = []

    def make():
        made.append(1)
        raise RefreshError("invalid_grant")
    q = wr._Lazy(make)
    for _ in range(3):
        try:
            q("SELECT campaign.id FROM campaign")
        except RefreshError:
            pass
        else:
            raise AssertionError("should raise")
    assert made == [1]
    ok = wr._Lazy(lambda: (lambda query: ["row"]))
    assert ok("SELECT 1") == ["row"] and ok("SELECT 2") == ["row"]


def test_with_google_signed_out_every_section_still_reports(monkeypatch):
    """Ads and the Google session both fail to sign in: each Google section says SECTION <id> FAILED with the
    auth hint, the ledger and enquiry sections still run (9b grades from the sheet alone), and --quiet's problem
    lines carry the auth wording the dispatcher stops on. No network: the live-page fetches are stubbed."""
    reset()
    import datetime
    import types
    import urllib.request
    today = datetime.date(2026, 10, 26)
    monkeypatch.setattr(wr.lm, "today", lambda *a, **k: today)

    def no_network(*a, **k):
        raise OSError("no network in tests")
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    monkeypatch.setattr(wr.goatcounter, "keychain_token", lambda *a, **k: None)  # no Keychain in tests
    import cwv  # section 5d imports it when it runs; the same module object
    monkeypatch.setattr(cwv, "keychain_key", lambda *a, **k: None)

    def money_down():
        print("\n== 10. Money (totals and invoice numbers only)")
        raise ValueError("ledger row text that must never print")
    monkeypatch.setattr(wr, "money_section", money_down)
    import csv as _csv
    with open(os.path.join(TMP, "enquiries.csv"), "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["enquiry_id", "first_seen", "source", "occasion", "gclid", "notes"])
        w.writeheader()
        w.writerow({"enquiry_id": "t1", "first_seen": "2026-10-22", "source": "web form", "occasion": "christmas",
                    "gclid": "", "notes": "ad visit: christmas; The Example Hall"})

    def signed_out():
        raise RefreshError("invalid_grant: Token has been expired or revoked.")
    q, s = wr._Lazy(signed_out), wr._Lazy(signed_out)
    args = types.SimpleNamespace(since=datetime.date(2026, 9, 26), write_proposals=False, gsc_shortlist=False)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.run_sections(args, q=q, s=s)
    text = out.getvalue()
    heads = __import__("re").findall(r"^== (\w+)\.", text, __import__("re").M)
    assert heads == ["1", "1b", "2", "3", "4", "4b", "5", "5c", "5d", "6", "7", "8", "9", "9b", "10", "11", "12",
                     "13"], heads
    hint = "RefreshError (looks like a Google auth error: check the sign-in)"
    for sid in ("1", "1b", "2", "3", "4", "4b", "5", "6", "7", "8"):
        assert f"   SECTION {sid} FAILED: {hint}" in text.splitlines(), (sid, text)
    assert "   SECTION 10 FAILED: ValueError" in text.splitlines() and "must never print" not in text, text
    assert "2026-10-22 · christmas · web form · B Christmas carol singers – events 2026 (ad visit: christmas)" in text, text
    assert "Example Hall" not in text
    assert f"true cost per booking failed: {hint}" in text and f"seasonal budget rules failed: {hint}" in text, text
    path = os.path.join(TMP, "reports", "2026-10-26.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    summary = wr.quiet_summary(path)
    assert "sections: 1 1b 2 3 4 4b 5 5c 5d 6 7 8 9 9b 10 11 12 13" in summary, summary
    assert f"problem: SECTION 1 FAILED: {hint}" in summary.splitlines(), summary


def test_quiet_lists_failed_sections_but_not_log_rows_held_guards_or_c_grades():
    reset()
    path = os.path.join(TMP, "reports", "2026-10-26.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("== 1. Campaigns\n"
                "   log 2026-10-19 23:16 · campaign X · final URL · error page → christmas.html\n"
                "\n== 1b. Account settings (live) and changes since the last report\n"
                "-- snapshot (read-only)\n"
                "   set \"X\" sitelink \"Error-free booking\" ENABLED · → https://example.org/failed.html\n"
                "-- changed since 2026-10-19 (that report's 1b; + now, - then)\n"
                "   - set \"X\" keyword \"denied\" EXACT in \"Ad group 1\" · bid £3.50\n"
                "   + set \"X\" keyword \"denied\" EXACT in \"Ad group 1\" · bid £4.00\n"
                "\n== 9b. Enquiries by ad source\n"
                "   2026-10-22 · christmas · web form · C Christmas (only a Christmas ad click that day or the day "
                "before, cookies declined?; never counts)\n"
                "\n== 12. Seasonal budget rules\n"
                "   spend guard X: £90.00, 20 clicks, 0 Ads conversions in 28 days · enquiries A 0 · B 1 · C 0 — held: "
                "an A or B enquiry came from this campaign, so no pause\n"
                "   spend guard Y: £90.00, 20 clicks, 0 Ads conversions in 28 days · enquiries A 0 · B 0 · C 0 — STOP "
                "GUARD: propose pausing (never deleting) until the owner decides\n"
                "   stop rule: £80+ in 28 days with no A or B enquiry → propose pausing\n"
                "\n== 13. Search Console shortlist\n   SECTION 13 FAILED: KeyError\n")
    lines = wr.quiet_summary(path).splitlines()
    problems = [l for l in lines if l.startswith("problem:")]
    assert len(problems) == 2, lines
    assert problems[0].startswith("problem: spend guard Y:") and problems[1] == "problem: SECTION 13 FAILED: KeyError"


def test_logged_changes_are_newest_first_merged_and_dated():
    import datetime
    text = ("| Date | Resource | Field | Current → New | Reason | Script |\n|---|---|---|---|---|---|\n"
            "| 2026-10-19 23:42 | kw \"a\" (exact) | max CPC | £2.50 → £3.50 | r | s |\n"
            "| 2026-10-19 23:42 | kw \"b\" (exact) | max CPC | £2.50 → £3.50 | r | s |\n"
            "| 2026-10-19 23:16 | ad 1 | final URL | x → y | r | s |\n"
            "| 2026-09-01 00:00 | old | budget | £1 → £2 | r | s |\n")
    rows = wr.logged_changes(text, datetime.date(2026, 10, 26), days=21, baseline=datetime.date(2026, 10, 23))
    assert rows == [("2026-10-19 23:42", 'kw "a" (exact) (+1 more alike)', "max CPC", "£2.50 → £3.50"),
                    ("2026-10-19 23:16", "ad 1", "final URL", "x → y")], rows
    rows = wr.logged_changes(text, datetime.date(2026, 10, 26), days=21, baseline=datetime.date(2026, 8, 30))
    assert rows[-1] == ("2026-09-01 00:00", "old", "budget", "£1 → £2"), rows


def _ns(**kw):
    import types
    return types.SimpleNamespace(**kw)


def _enum(name):
    return _ns(name=name)


def test_section_3_flags_a_wrong_primary_and_a_missing_one():
    actions = [("Submit lead form", "ENABLED", True), ("Contact", "ENABLED", True),
               ("Call click", "ENABLED", False), ("GA4 import", "HIDDEN", False)]

    def q(query):
        if "FROM conversion_action" in query:
            assert "!= 'REMOVED'" in query, query
            return [_ns(conversion_action=_ns(name=n, status=_enum(s), primary_for_goal=p)) for n, s, p in actions]
        return []
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.conversions_section(q)
    lines = out.getvalue().splitlines()
    by = {l.split("  ")[0]: l for l in lines[1:]}
    assert "!CHECK" not in by["Submit lead form"] and "ENABLED" in by["Submit lead form"], lines
    assert "!CHECK: primary, but not one of the owner's two" in by["Contact"], lines
    assert "!CHECK" not in by["Call click"], lines
    assert "GA4 import" not in out.getvalue(), lines  # hidden and secondary: left out
    assert "!CHECK: not in the account" in by["WhatsApp or email click"], lines


def test_section_4_prints_rsa_counts_and_sitelinks_per_campaign():
    def ad(campaign, n_head, n_desc):
        return _ns(campaign=_ns(name=campaign), ad_group=_ns(name="g", status=_enum("ENABLED")),
                   ad_group_ad=_ns(status=_enum("ENABLED"), ad_strength=_enum("GOOD"), action_items=[],
                                   policy_summary=_ns(approval_status=_enum("APPROVED"),
                                                      review_status=_enum("REVIEWED")),
                                   ad=_ns(id=1, final_urls=["https://londonchoralservice.com/funerals.html"],
                                          responsive_search_ad=_ns(headlines=[0] * n_head,
                                                                   descriptions=[0] * n_desc))))

    def q(query):
        if "FROM ad_group_ad" in query and "metrics.clicks" in query:
            assert "segments.date" in query, query
            return [_ns(ad_group_ad=_ns(ad=_ns(id=1)), metrics=_ns(clicks=c)) for c in (3, 4)]
        if "FROM ad_group_ad" in query:
            assert "responsive_search_ad.headlines" in query and "responsive_search_ad.descriptions" in query
            return [ad("funeral expert campaign", 15, 4), ad("wedding-leads", 9, 3)]
        if "FROM campaign_asset" in query:
            assert "SITELINK" in query and "campaign_asset.status = 'ENABLED'" in query, query
            return [_ns(campaign=_ns(name="funeral expert campaign"))] * 6
        return []
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        landing = wr.ads_section(q)
    text = out.getvalue()
    assert "headlines=15 descriptions=4" in text and "headlines=9 descriptions=3" in text, text
    assert "clicks30=7" in text, text  # summed over the ad's daily rows
    assert "funeral expert campaign" in text and "sitelinks=6" in text, text
    assert [l for l in text.splitlines() if "wedding-leads" in l and "sitelinks=0" in l], text
    assert landing == ["https://londonchoralservice.com/funerals.html"]


# ---------- 1b. live settings and the diff with the previous report ----------

def _e(name):
    from types import SimpleNamespace as N
    return N(name=name)


def fake_settings_ads(budget=5_000_000, bid=3_500_000, sitelink_status="ENABLED"):
    """A GAQL runner for section 1b: one campaign, schedule, two locations, one ad group, keyword, ad, sitelink,
    call asset, account logo and two conversion actions."""
    from types import SimpleNamespace as N

    def q(query):
        if "FROM campaign_criterion" in query:
            sched = lambda d: N(campaign=N(id=1), campaign_criterion=N(
                type_=_e("AD_SCHEDULE"), negative=False, location=N(geo_target_constant=""),
                ad_schedule=N(day_of_week=_e(d), start_hour=7, start_minute=_e("ZERO"), end_hour=22,
                              end_minute=_e("THIRTY"))))
            loc = lambda g, neg=False: N(campaign=N(id=1), campaign_criterion=N(
                type_=_e("LOCATION"), negative=neg, location=N(geo_target_constant=g), ad_schedule=None))
            return [sched(d) for d in ("MONDAY", "TUESDAY", "WEDNESDAY", "FRIDAY")] + \
                [loc("geoTargetConstants/1006886"), loc("geoTargetConstants/20339", True)]
        if "FROM geo_target_constant" in query:
            return [N(geo_target_constant=N(resource_name="geoTargetConstants/1006886", name="London")),
                    N(geo_target_constant=N(resource_name="geoTargetConstants/20339", name="Kent"))]
        if "FROM campaign_asset" in query:
            return [N(campaign=N(id=1), campaign_asset=N(field_type=_e("SITELINK"), status=_e(sitelink_status)),
                      asset=N(id=424863742104, sitelink_asset=N(link_text="Funeral Choir Prices"),
                              final_urls=["https://londonchoralservice.com/pricing.html"])),
                    N(campaign=N(id=1), campaign_asset=N(field_type=_e("CALL"), status=_e("ENABLED")),
                      asset=N(id=348067579141, sitelink_asset=N(link_text=""), final_urls=[]))]
        if "FROM customer_asset" in query:
            return [N(customer_asset=N(field_type=_e("BUSINESS_LOGO"), status=_e("ENABLED")))]
        if "FROM conversion_action" in query:
            return [N(conversion_action=N(name="Submit lead form", status=_e("ENABLED"), primary_for_goal=True)),
                    N(conversion_action=N(name="Contact", status=_e("ENABLED"), primary_for_goal=False))]
        if "FROM ad_group_criterion" in query:
            return [N(campaign=N(id=1), ad_group=N(name="Ad group 1"), ad_group_criterion=N(
                keyword=N(text="funeral choir", match_type=_e("EXACT")), effective_cpc_bid_micros=bid))]
        if "FROM ad_group_ad" in query:
            t = lambda text, pin="UNSPECIFIED": N(text=text, pinned_field=_e(pin))
            return [N(campaign=N(id=1), ad_group=N(name="Ad group 1"), ad_group_ad=N(
                ad_strength=_e("GOOD"), ad=N(id=826000407483, final_urls=["https://londonchoralservice.com/funerals.html"],
                                             responsive_search_ad=N(headlines=[t("Funeral Choir from £1,150", "HEADLINE_2"),
                                                                               t("Funeral Choirs")],
                                                                    descriptions=[t("A choir of four.")]))))]
        if "FROM ad_group" in query:
            return [N(campaign=N(id=1), ad_group=N(name="Ad group 1", status=_e("ENABLED"), cpc_bid_micros=3_000_000))]
        if "FROM campaign" in query:
            return [N(campaign=N(id=1, name="funeral expert campaign", status=_e("ENABLED"),
                                 bidding_strategy_type=_e("MANUAL_CPC"), end_date_time="",
                                 network_settings=N(target_google_search=True, target_search_network=False,
                                                    target_content_network=False),
                                 geo_target_type_setting=N(positive_geo_target_type=_e("PRESENCE"))),
                      campaign_budget=N(amount_micros=budget))]
        raise AssertionError(query)
    return q


def test_section_1b_prints_one_sorted_line_per_item_and_no_metrics():
    lines = wr.account_snapshot_lines(fake_settings_ads())
    assert lines == sorted(lines) and all(l.startswith("set ") for l in lines), lines
    camp = [l for l in lines if " campaign ENABLED" in l]
    assert camp == ['set "funeral expert campaign" [1] campaign ENABLED · budget £5.00/day · MANUAL_CPC · search on, '
                    'partners off, display off · ends never · locations by PRESENCE · schedule Mon–Wed,Fri 07:00–22:30'
                    ' · locations 2: London, excluded Kent'], lines
    assert 'set "funeral expert campaign" keyword "funeral choir" EXACT in "Ad group 1" · bid £3.50' in lines
    assert 'set "funeral expert campaign" ad group "Ad group 1" ENABLED · default CPC £3.00' in lines
    assert ('set "funeral expert campaign" ad 826000407483 in "Ad group 1" · strength GOOD · → '
            'https://londonchoralservice.com/funerals.html · pins: HEADLINE_2 "Funeral Choir from £1,150"') in lines
    assert ('set "funeral expert campaign" sitelink "Funeral Choir Prices" (424863742104) ENABLED · → '
            'https://londonchoralservice.com/pricing.html') in lines
    assert 'set "funeral expert campaign" assets (enabled, not sitelinks) · CALL 1' in lines
    assert "set account assets (enabled, not sitelinks) · BUSINESS_LOGO 1" in lines
    assert 'set account conversion action "Submit lead form" · primary · ENABLED' in lines
    assert 'set account conversion action "Contact" · secondary · ENABLED' in lines
    assert not any("clicks" in l or "impr" in l for l in lines)
    assert wr.schedule_text([]) == "all day"
    assert wr.schedule_text([(d, "07:00", "24:00") for d in wr.WEEKDAYS]) == "Mon–Sun 07:00–24:00"


def _report_with_snapshot(lines, sid_tail="\n== 2. Search terms\nterm\n"):
    return ("== 1. Campaigns\nx\n\n== 1b. Account settings (live) and changes since the last report\n"
            "-- snapshot (read-only; enabled items, one line per item, sorted; no metrics)\n"
            + "".join(f"   {l}\n" for l in lines)
            + "-- changed since 2026-10-12 (that report's 1b; + now, - then)\n   + set old diff line\n" + sid_tail)


def test_section_1b_diffs_against_the_newest_earlier_snapshot():
    import datetime
    reset()
    rdir = os.path.join(TMP, "reports")
    os.makedirs(rdir)
    old = wr.account_snapshot_lines(fake_settings_ads())
    new = wr.account_snapshot_lines(fake_settings_ads(budget=8_000_000, bid=4_000_000, sitelink_status="PAUSED"))
    with open(os.path.join(rdir, "2026-10-12.txt"), "w", encoding="utf-8") as f:
        f.write(_report_with_snapshot(["set very old line"]))
    with open(os.path.join(rdir, "2026-10-19.txt"), "w", encoding="utf-8") as f:
        f.write(_report_with_snapshot(old))
    with open(os.path.join(rdir, "2026-10-22.txt"), "w", encoding="utf-8") as f:  # a rerun whose 1b failed
        f.write("== 1b. Account settings\n   SECTION 1b FAILED: RefreshError\n\n== 2. Search terms\n")
    with open(os.path.join(rdir, "2026-10-26.txt"), "w", encoding="utf-8") as f:  # today's own: never compared
        f.write(_report_with_snapshot(["set today line"]))
    day, prev = wr.previous_snapshot(datetime.date(2026, 10, 26))
    assert day == datetime.date(2026, 10, 19) and prev == old, (day, prev)  # the diff lines were not taken
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.account_settings_section(fake_settings_ads(budget=8_000_000, bid=4_000_000, sitelink_status="PAUSED"),
                                    datetime.date(2026, 10, 26))
    text = out.getvalue()
    tail = text.split("-- changed since ")[1].splitlines()
    assert tail[0].startswith("2026-10-19"), tail
    changes = tail[1:]
    assert len(changes) == 6, changes  # campaign, keyword and sitelink: each - then +
    assert changes[0].startswith('   - set "funeral expert campaign" [1] campaign ENABLED · budget £5.00/day'), changes
    assert changes[1].startswith('   + set "funeral expert campaign" [1] campaign ENABLED · budget £8.00/day'), changes
    assert '   - set "funeral expert campaign" keyword "funeral choir" EXACT in "Ad group 1" · bid £3.50' in changes
    assert '   + set "funeral expert campaign" keyword "funeral choir" EXACT in "Ad group 1" · bid £4.00' in changes
    assert any(l.startswith('   + set "funeral expert campaign" sitelink "Funeral Choir Prices" (424863742104) PAUSED')
               for l in changes)
    # the section's own output round-trips: next week this report is the previous snapshot
    assert wr.snapshot_block(text) == new
    assert wr.snapshot_diff_lines(new, datetime.date(2026, 10, 26), new) == [
        "-- changed since 2026-10-26 (that report's 1b; + now, - then)", "   no change since 2026-10-26"]
    assert wr.snapshot_diff_lines(new, None, None) == ["-- changed since the last report",
                                                       "   no earlier snapshot (first run)"]
    reset()
    assert wr.previous_snapshot(datetime.date(2026, 10, 26)) == (None, None)  # no reports directory at all


def test_report_sections_serves_1b(monkeypatch):
    import datetime
    import report_sections as rs
    reset()
    monkeypatch.setattr(rs.lm, "today", lambda *a, **k: datetime.date(2026, 10, 26))
    os.makedirs(os.path.join(TMP, "reports"))
    with open(os.path.join(TMP, "reports", "2026-10-26.txt"), "w", encoding="utf-8") as f:
        f.write(_report_with_snapshot(["set a", "set b"]))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert rs.main(["1b"]) == 0
    text = out.getvalue()
    assert text.startswith("== 1b. Account settings") and "   set a\n   set b\n" in text and "== 2." not in text, text
    assert "== 1." not in text.replace("== 1b.", "")


def test_a_failing_1b_says_so_with_the_http_code_and_the_rest_runs():
    class ApiError(Exception):
        def __init__(self):
            super().__init__("customer data that must never print")
            self.http_status = 503

    def broken(query):
        raise ApiError()
    import datetime
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert wr.run_section("1b", "Account settings (live) and changes since the last report",
                              wr.account_settings_section, broken, datetime.date(2026, 10, 26)) is None
        wr.run_section("2", "Search terms", lambda: print("\n== 2. Search terms"))
    text = out.getvalue()
    assert "   SECTION 1b FAILED: ApiError (HTTP 503)" in text.splitlines(), text
    assert "must never print" not in text and "== 2. Search terms" in text, text
    assert wr.snapshot_block(text) is None


if __name__ == "__main__":
    import inspect

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                params = inspect.signature(fn).parameters
                if "monkeypatch" in params:
                    class MP:
                        def __init__(self):
                            self._undo = []

                        def setattr(self, obj, name, value):
                            self._undo.append((obj, name, getattr(obj, name)))
                            setattr(obj, name, value)

                        def undo(self):
                            for obj, name, value in reversed(self._undo):
                                setattr(obj, name, value)

                    mp = MP()
                    try:
                        fn(mp)
                    finally:
                        mp.undo()
                else:
                    fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
