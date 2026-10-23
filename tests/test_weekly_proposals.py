#!/usr/bin/env python3
"""Tests for weekly_review --write-proposals: section 12's PROPOSE lines as Command Centre proposals. Stdlib only,
a temp private dir, a fake Ads query and a fake git runner (one test reads this repo's own origin/main with real
git, locally). .venv/bin/python tests/test_weekly_proposals.py"""
import contextlib, datetime, io, json, os, stat, subprocess, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
sys.path.insert(0, ROOT)
import weekly_review as wr

BLOB, COMMIT = "a" * 40, "b" * 40
PDIR = Path(TMP) / "command-centre" / "proposals"
NOW = datetime.datetime(2026, 10, 5, 9, 5, tzinfo=datetime.timezone(datetime.timedelta(hours=1)))
MON = datetime.date(2026, 10, 5)


class FakeGit:
    def __init__(self, blob=BLOB, commit=COMMIT, code=0):
        self.calls, self.blob, self.commit, self.code = [], blob, commit, code

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        spec = argv[-1]
        out = self.blob if ":" in spec else self.commit
        return subprocess.CompletedProcess(argv, self.code, out + "\n", "")


def item(cid="24295921372", cur=4.0, new=5.0, name="Christmas carol singers – events 2026", window="carols"):
    return {"kind": "propose", "campaign": name, "campaign_id": cid, "current": cur, "proposed": new, "window": window,
            "text": "x"}


def clear():
    if PDIR.exists():
        for p in PDIR.iterdir():
            p.unlink()


def written():
    return {p.stem: json.loads(p.read_text()) for p in sorted(PDIR.glob("*.json"))}


def test_writes_a_proposal_the_app_accepts():
    clear()
    git = FakeGit()
    lines = wr.write_proposals([item(), {"kind": "note", "text": "n"}], MON, git_runner=git, now=NOW)
    assert lines == ["proposal written: budget-24295921372-500-20261005"], lines
    p = written()["budget-24295921372-500-20261005"]
    assert p == {"id": "budget-24295921372-500-20261005", "kind": "ads",
                 "title": "Budget: Christmas carol singers – events 2026 £4.00 → £5.00/day",
                 "summary": p["summary"], "script_path": "scripts/ads/set_budget.py",
                 "created": "2026-10-05T09:05:00+01:00", "commit": COMMIT, "script_blob": BLOB,
                 "args": ["24295921372", "5.00"]}, p
    assert "window carols" in p["summary"] and "never above £8/day" in p["summary"]
    f = PDIR / "budget-24295921372-500-20261005.json"
    assert stat.S_IMODE(f.stat().st_mode) == 0o600 and stat.S_IMODE(PDIR.stat().st_mode) == 0o700
    assert stat.S_IMODE(PDIR.parent.stat().st_mode) == 0o700
    from command_centre import actions
    got = actions.load_proposal("budget-24295921372-500-20261005")
    assert got["args"] == ["24295921372", "5.00"] and got["blob"] == BLOB and got["commit"] == COMMIT
    specs = [argv[-1] for argv, _ in git.calls]
    assert specs == ["origin/main:scripts/ads/set_budget.py", "origin/main^{commit}"], specs
    for argv, kw in git.calls:
        assert "core.hooksPath=/dev/null" in argv and "--no-replace-objects" in argv and kw["shell"] is False
        assert kw["env"]["GIT_CONFIG_GLOBAL"] == "/dev/null" and kw["env"]["GIT_CONFIG_NOSYSTEM"] == "1"
        assert not any(k.startswith("GIT_") and k not in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM",
                       "GIT_TERMINAL_PROMPT", "GIT_NO_REPLACE_OBJECTS") for k in kw["env"])


def test_never_twice_while_waiting_but_again_after_it_was_applied():
    clear()
    wr.write_proposals([item()], MON, git_runner=FakeGit(), now=NOW)
    again = wr.write_proposals([item()], MON + datetime.timedelta(days=7), git_runner=FakeGit(), now=NOW)
    assert again == ["proposal already waiting: budget-24295921372-500-20261005"], again
    other_blob = wr.write_proposals([item()], MON, git_runner=FakeGit(blob="c" * 40), now=NOW)
    assert other_blob == ["proposal written: budget-24295921372-500-20261005-2"], other_blob
    (PDIR / "budget-24295921372-500-20261005.applied").write_text("{}")
    later = wr.write_proposals([item()], MON, git_runner=FakeGit(), now=NOW)
    assert later == ["proposal written: budget-24295921372-500-20261005-3"], later


def test_a_new_amount_supersedes_the_older_waiting_proposal_for_the_same_campaign():
    """A repeated Monday review that proposes a new amount for a campaign already waiting must not leave the old
    amount sitting in the Command Centre's list too: the older one is marked superseded_by and hidden there."""
    clear()
    first_lines = wr.write_proposals([item(new=5.0)], MON, git_runner=FakeGit(), now=NOW)
    first = "budget-24295921372-500-20261005"
    assert first_lines == [f"proposal written: {first}"], first_lines
    second_lines = wr.write_proposals([item(new=4.0)], MON, git_runner=FakeGit(), now=NOW)
    second = "budget-24295921372-400-20261005"
    assert second_lines == [f"proposal written: {second}"], second_lines
    data = written()
    assert data[first]["superseded_by"] == second, data[first]
    assert "superseded_by" not in data[second], data[second]
    # a different campaign is never touched, and an already-superseded proposal keeps its original superseded_by
    wr.write_proposals([item(cid="1", new=3.0)], MON, git_runner=FakeGit(), now=NOW)
    wr.write_proposals([item(cid="1", new=2.0)], MON, git_runner=FakeGit(), now=NOW)
    assert written()[first]["superseded_by"] == second
    from command_centre import actions
    listed = {p["id"] for p in actions.list_proposals()}
    assert second in listed and first not in listed


def test_never_above_five_pounds_and_needs_a_campaign_id():
    clear()
    lines = wr.write_proposals([item(cid="1", new=5.01), item(cid="1", new=6), item(cid="1", new=0),
                                item(new=8.01), item(cid=None), item(cid="12a")], MON,
                               git_runner=FakeGit(), now=NOW)
    assert lines == ["not written (Christmas carol singers – events 2026): £5.01/day is outside £0–£5",
                     "not written (Christmas carol singers – events 2026): £6.00/day is outside £0–£5",
                     "not written (Christmas carol singers – events 2026): £0.00/day is outside £0–£5",
                     "not written (Christmas carol singers – events 2026): £8.01/day is outside £0–£8",
                     "not written (Christmas carol singers – events 2026): no campaign id",
                     "not written (Christmas carol singers – events 2026): no campaign id"], lines
    assert not written()


def test_a_long_campaign_name_keeps_the_title_under_120():
    clear()
    wr.write_proposals([item(name="W" * 200, cid="1", cur=3.0, new=4.5)], MON, git_runner=FakeGit(), now=NOW)
    p = written()["budget-1-450-20261005"]
    assert len(p["title"]) <= 120 and p["title"].endswith("£3.00 → £4.50/day") and p["args"] == ["1", "4.50"]


def test_git_failure_writes_nothing():
    clear()
    for git in (FakeGit(code=128), FakeGit(blob="not-a-sha")):
        try:
            wr.write_proposals([item()], MON, git_runner=git, now=NOW)
            raise AssertionError("no error")
        except RuntimeError:
            pass
    assert not written()
    assert wr.write_proposals([{"kind": "note", "text": "n"}], MON, git_runner=FakeGit(code=1)) == \
        ["no budget proposals to write"]


def row(cid, name, status, pounds):
    return NS(campaign=NS(id=int(cid), name=name, status=NS(name=status)),
              campaign_budget=NS(amount_micros=int(pounds * 1_000_000)))


def run_section(write, git):
    rows = [row("24295921372", "Christmas carol singers – events 2026", "ENABLED", 4.0),
            row("23739971001", "wedding-leads", "ENABLED", 4.0),
            row("23735776277", "funeral expert campaign", "PAUSED", 2.0)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        wr.budget_section(lambda q: rows, MON, write=write, git_runner=git, now=NOW)
    return buf.getvalue()


def test_section_12_writes_only_with_the_flag():
    clear()
    out = run_section(False, FakeGit())
    assert "PROPOSE: Christmas carol singers – events 2026 £4.00 → £8.00/day (window carols)" in out, out
    assert "proposal" not in out.split("(window carols)")[1] and not written()
    out = run_section(True, FakeGit())
    assert "   proposal written: budget-24295921372-800-20261005" in out.splitlines(), out
    assert list(written()) == ["budget-24295921372-800-20261005"]
    out = run_section(True, FakeGit(code=1))
    assert "   Command Centre proposals not written: RuntimeError" in out.splitlines(), out


def test_real_git_pins_this_repo():
    probe = subprocess.run(["git", "-C", ROOT, "rev-parse", "--verify", "--quiet", "origin/main"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        print("   (skipped: no origin/main here)")
        return
    blob, commit = wr.git_pins()
    assert commit == probe.stdout.strip()
    assert blob == subprocess.run(["git", "-C", ROOT, "rev-parse", "origin/main:scripts/ads/set_budget.py"],
                                  capture_output=True, text=True).stdout.strip()


def test_flag_is_parsed():
    saved = (wr.run_sections, sys.argv)
    seen = {}
    wr.run_sections = lambda args: seen.update(vars(args))
    try:
        sys.argv = ["weekly_review.py", "--write-proposals"]
        wr.main()
    finally:
        wr.run_sections, sys.argv = saved
    assert seen["write_proposals"] is True and seen["save_report"] is False


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
            N(campaign=N(id=24295921372, name=XMAS), metrics=N(cost_micros=150_000_000, clicks=60, conversions=0.0))]


def test_spend_guard_fires_with_no_conversion_and_no_a_or_b_enquiry():
    mon = datetime.date(2026, 10, 26)
    day = datetime.date(2026, 10, 22)
    lines = wr.spend_guard_lines(guard_rows, mon, graded(enq("christmas", day), clicks={(day, "christmas")}))
    assert lines[0] == ("spend guard wedding-leads: £95.00, 20 clicks, 0 Ads conversions in 28 days · enquiries A 0 · "
                        "B 0 · C 0 — STOP GUARD: propose pausing (never deleting) until the owner decides"), lines
    assert lines[1] == ("spend guard funeral expert campaign: £120.00, 25 clicks, 2 Ads conversions in 28 days · "
                        "enquiries A 0 · B 0 · C 0"), lines
    assert lines[2].endswith("under 15 clicks, too few to judge; watch next week"), lines
    assert lines[3] == "spend guard small: £30.00, 6 clicks, 0 Ads conversions in 28 days · enquiries A 0 · B 0 · C 0"
    # a C enquiry never holds the guard
    assert lines[4].startswith(f"spend guard {XMAS}: £150.00, 60 clicks, 0 Ads conversions in 28 days · enquiries "
                               "A 0 · B 0 · C 1 — STOP GUARD"), lines
    assert lines[5].startswith("stop rule: £80+ in 28 days with no Ads conversion and no A or B enquiry"), lines


def test_spend_guard_is_held_by_an_a_or_b_enquiry_for_that_campaign_only():
    mon = datetime.date(2026, 10, 26)
    day = datetime.date(2026, 10, 22)
    for row in (enq("christmas", day, "ad visit: christmas"), enq("corporate", day, "ad visit: home (christmas-carol-singers-2026)"),
                enq("christmas", day, gclid="Cj0KCQjwTestClickId123")):
        lines = wr.spend_guard_lines(guard_rows, mon, graded(row, found={"Cj0KCQjwTestClickId123": XMAS}))
        assert lines[4].endswith("— held: an A or B enquiry came from this campaign, so no pause"), lines
        assert "STOP GUARD" not in lines[4]
        assert "STOP GUARD" in lines[0], lines  # the wedding campaign still has none of its own
    # outside the 28 days it no longer holds
    lines = wr.spend_guard_lines(guard_rows, mon, graded(enq("christmas", datetime.date(2026, 9, 28), "ad visit: christmas")))
    assert "STOP GUARD" in lines[4], lines
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
