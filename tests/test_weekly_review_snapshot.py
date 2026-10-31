#!/usr/bin/env python3
"""Tests for the Monday report's own plumbing in scripts/reports/weekly_review.py: the 1b snapshot, the change log,
--quiet's problem lines, the --out dry run, section 0b (since last Monday), section 6's query blocks, section 9c
(the enquiry assistant's run log) and section 13's off-week line. Stdlib only, a temp private dir, no network.

    .venv/bin/python tests/test_weekly_review_snapshot.py
"""
import contextlib, datetime, io, json, os, subprocess, sys, tempfile, types

TMP = tempfile.mkdtemp(prefix="lcs-wr-snapshot-test-")
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import weekly_review as wr  # noqa: E402
import report_sections as rs  # noqa: E402
import review_log  # noqa: E402

D = datetime.date
REPORTS = os.path.join(TMP, "reports")


def reset():
    for d, _, files in os.walk(TMP, topdown=False):
        for f in files:
            os.remove(os.path.join(d, f))
        if d != TMP:
            os.rmdir(d)


@contextlib.contextmanager
def patched(obj, name, value):
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def snap_report(lines):
    return ("== 1. Campaigns\nx\n\n== 1b. Account settings (live) and changes since the last report\n"
            "-- snapshot (read-only; enabled items, one line per item, sorted; no metrics)\n"
            + "".join(f"   {l}\n" for l in lines)
            + "-- changed since 2026-10-12 (that report's 1b; + now, - then)\n   + set a diff line\n"
            "\n== 2. Search terms\n   set not a snapshot line\n")


# ---------- the 1b snapshot ----------

def test_snapshot_block_stops_at_the_next_dash_or_section_line():
    text = snap_report(["set a", "set b"])
    assert wr.snapshot_block(text) == ["set a", "set b"]  # not the diff's "+ set …", not section 2's "set …"
    only = "-- snapshot (x)\n   set a\n== 2. Search terms\n   set b\n"
    assert wr.snapshot_block(only) == ["set a"]
    assert wr.snapshot_block("== 1b. x\n   SECTION 1b FAILED: KeyError\n") is None
    assert wr.snapshot_block("") is None and wr.snapshot_block(None) is None


def test_previous_snapshot_takes_the_newest_earlier_report_and_ignores_reviews():
    reset()
    write(os.path.join(REPORTS, "2026-10-12.txt"), snap_report(["set twelfth"]))
    write(os.path.join(REPORTS, "2026-10-19.txt"), snap_report(["set nineteenth"]))
    write(os.path.join(REPORTS, "2026-10-22.txt"), "== 1b. Account settings\n   SECTION 1b FAILED: RefreshError\n")
    write(os.path.join(REPORTS, "2026-10-26.txt"), snap_report(["set today"]))
    write(os.path.join(REPORTS, "reviews", "2026-10-25.txt"), snap_report(["set a review, not a report"]))
    write(os.path.join(REPORTS, "reviews", "2026-10-25.md"), "## Decisions\n1. x → y\n")
    write(os.path.join(REPORTS, "notes.txt"), snap_report(["set not dated"]))
    assert wr.previous_snapshot(D(2026, 10, 26)) == (D(2026, 10, 19), ["set nineteenth"])  # skips today's and 22nd
    assert wr.previous_snapshot(D(2026, 10, 19)) == (D(2026, 10, 12), ["set twelfth"])
    assert wr.previous_snapshot(D(2026, 10, 12)) == (None, None)
    assert wr.previous_report_date(D(2026, 10, 26)) == D(2026, 10, 22)  # 0b counts from any report, 1b or not


def test_snapshot_diff_prints_the_old_line_then_the_new_and_no_change():
    old = ['set "X" keyword "funeral choir" EXACT in "G" · bid £3.50', 'set "X" campaign ENABLED · budget £5.00/day']
    new = ['set "X" keyword "funeral choir" EXACT in "G" · bid £4.00', 'set "X" campaign ENABLED · budget £5.00/day']
    got = wr.snapshot_diff_lines(new, D(2026, 10, 19), old)
    assert got == ["-- changed since 2026-10-19 (that report's 1b; + now, - then)",
                   '   - set "X" keyword "funeral choir" EXACT in "G" · bid £3.50',
                   '   + set "X" keyword "funeral choir" EXACT in "G" · bid £4.00'], got
    assert wr.snapshot_diff_lines(new, D(2026, 10, 19), list(new))[-1] == "   no change since 2026-10-19"


# ---------- the change log ----------

LOG = ("| Date | Resource | Field | Current → New | Reason | Script |\n|---|---|---|---|---|---|\n"
       "| 2026-10-25 10:00 | kw a | max CPC | £3 → £4 | r | s |\n"
       "| 2026-10-20 09:00 | ad 1 | final URL | x → y | r | s |\n"
       "| 2026-10-01 09:00 | budget | amount | £4 → £5 | r | s |\n"
       "| 2026-09-01 09:00 | old | budget | £1 → £2 | r | s |\n")


def test_logged_changes_keeps_rows_since_the_baseline_and_the_last_log_days():
    today = D(2026, 10, 26)
    rows = wr.logged_changes(LOG, today, days=wr.LOG_DAYS, baseline=D(2026, 10, 19))
    assert [r[0] for r in rows] == ["2026-10-25 10:00", "2026-10-20 09:00"], rows  # the last 21 days
    rows = wr.logged_changes(LOG, today, days=wr.LOG_DAYS, baseline=D(2026, 9, 30))
    assert [r[0] for r in rows] == ["2026-10-25 10:00", "2026-10-20 09:00", "2026-10-01 09:00"], rows  # baseline
    rows = wr.logged_changes(LOG, today, days=wr.LOG_DAYS, baseline=D(2026, 8, 31))
    assert rows[-1][0] == "2026-09-01 09:00", rows  # an older baseline reaches further back
    rows = wr.logged_changes(LOG, today, days=3, baseline=D(2026, 10, 24))
    assert [r[0] for r in rows] == ["2026-10-25 10:00"], rows
    assert wr.change_log_count(LOG, D(2026, 10, 20)) == 2


# ---------- --quiet's problem lines ----------

def test_quiet_lists_a_failed_section_but_not_set_or_open_lines_holding_error():
    reset()
    path = os.path.join(REPORTS, "2026-10-26.txt")
    write(path, "== 0b. Since last Monday\n"
                "   open 2026-10-19-02 · site · fix the error page on /contact.html\n"
                "   merged #419 fix(review): GoatCounter failed lines\n"
                "\n== 1b. Account settings\n   set \"X\" sitelink \"Error-free\" ENABLED\n"
                "   + set \"X\" keyword \"denied\" EXACT\n"
                "\n== 5c. Visits from every visitor\n   SECTION 5c FAILED: GoatCounterError (HTTP 429)\n"
                "\n== 0. This week in brief\n   alarm: SECTION 5c FAILED: GoatCounterError (HTTP 429)\n")
    problems = [l for l in wr.quiet_summary(path).splitlines() if l.startswith("problem")]
    assert problems == ["problem: SECTION 5c FAILED: GoatCounterError (HTTP 429)"], problems


# ---------- Task 0: the dry-run path ----------

def test_out_writes_there_and_never_to_the_reports_folder():
    reset()
    out_path = os.path.join(TMP, "scratch", "dry.txt")
    seen = []

    def fake(args):
        seen.append(wr.previous_snapshot(D(2026, 10, 26)))
        print("== 1. Campaigns\nline\n== 0. This week in brief\n   alarms: nothing alarming")
    write(os.path.join(REPORTS, "2026-10-19.txt"), snap_report(["set nineteenth"]))
    with patched(wr, "run_sections", fake), patched(wr.lm, "today", lambda *a, **k: D(2026, 10, 26)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            wr.main(["--save-report", "--quiet", "--out", out_path])
    assert os.path.exists(out_path)
    assert sorted(os.listdir(REPORTS)) == ["2026-10-19.txt"], os.listdir(REPORTS)  # no 2026-10-26.txt
    assert seen == [(D(2026, 10, 19), ["set nineteenth"])]  # 1b still compares with the real folder
    assert f"report saved: {out_path}" in buf.getvalue() and "sections: 1 0" in buf.getvalue(), buf.getvalue()
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            wr.main(["--out", out_path])
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("--out without --save-report should be refused")


def test_report_sections_file_serves_sections_from_it():
    reset()
    path = os.path.join(TMP, "scratch", "dry.txt")
    write(path, "== 0b. Since last Monday\n   since x\n\n== 1. Campaigns\nc\n\n== 0. This week in brief\n   b\n")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert rs.main(["--file", path, "0", "0b"]) == 0
    assert out.getvalue() == "== 0. This week in brief\n   b\n\n== 0b. Since last Monday\n   since x\n\n", out.getvalue()
    with contextlib.redirect_stderr(io.StringIO()):
        assert rs.main(["--file", os.path.join(TMP, "missing.txt"), "0"]) == 2
        try:
            rs.main(["--file", path, "--date", "2026-10-26", "0"])
        except SystemExit as e:
            assert e.code == 2
        else:
            raise AssertionError("--file and --date together should be refused")


# ---------- section 0b ----------

class FakeGit:
    def __init__(self, stdout="", code=0):
        self.stdout, self.code, self.calls = stdout, code, []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if "show" in cmd:
            return types.SimpleNamespace(returncode=1, stdout="")
        return types.SimpleNamespace(returncode=self.code, stdout=self.stdout)


def test_section_0b_lists_due_watch_items_open_proposals_changes_and_merged_prs():
    reset()
    write(os.path.join(REPORTS, "2026-10-26.txt"), "== 1. x\n")
    review = ("## Decisions\n\n1. [site] /weddings.html → title: a → b — an error-page fix\n2. [ads] x → y: 1 → 2\n"
              "\n## Watch\n\n- funeral clicks after the bid change (due 2026-11-02)\n- later thing (due 2026-11-16)\n")
    write(os.path.join(TMP, "2026-10-26.md"), review)
    review_log.record(os.path.join(TMP, "2026-10-26.md"))
    git = FakeGit("feat(review): reply lint and the run log (#421)\x1fbody\x1e"
                  "chore: a commit pushed straight to main\x1f\x1e"
                  "Merge pull request #419 from x/y\x1ffeat(review): section 0\n\nbody\x1e"
                  "Merge pull request #418 from x/z\x1ffix(books): read wrapped replies\x1e"
                  "Merge pull request #417 from lucawetherall/claude/some-branch\x1f\x1e")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.since_last_section(D(2026, 11, 2), runner=git)
    lines = out.getvalue().splitlines()
    assert lines[:3] == ["== 0b. Since last Monday", "   since 2026-10-26 (the previous saved report)",
                         "-- due to check this week"], lines
    assert lines[3] == "   open 2026-10-26-03 · watch · due 2026-11-02 · funeral clicks after the bid change", lines
    i = lines.index("-- open proposals, oldest first")
    assert lines[i + 1] == "   open 2026-10-26-01 · site · /weddings.html → title: a → b — an error-page fix", lines
    assert lines[i + 2] == "   open 2026-10-26-02 · ads · x → y: 1 → 2"
    assert "   1 watch item not due yet" in lines, lines
    assert any(l.startswith("-- Ads changes logged in logs/ads-changes.md since 2026-10-26: ") for l in lines), lines
    assert lines[-4:] == ["   merged #421 feat(review): reply lint and the run log",
                          "   merged #419 feat(review): section 0", "   merged #418 fix(books): read wrapped replies",
                          "   merged #417 (branch claude/some-branch)"], lines
    log_cmd = [c for c in git.calls if "log" in c][0]
    assert "--first-parent" in log_cmd and "--since=2026-10-26" in log_cmd and "origin/main" in log_cmd, log_cmd
    path = os.path.join(TMP, "q.txt")
    write(path, out.getvalue())
    assert "problems: none" in wr.quiet_summary(path)  # "error-page" in a proposal is not a problem


def test_section_0b_with_no_record_no_earlier_report_and_no_origin():
    reset()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.since_last_section(D(2026, 11, 2), runner=FakeGit(code=128))
    lines = out.getvalue().splitlines()
    assert lines[1] == "   since 2026-10-26 (no earlier report saved: 7 days)", lines
    assert "   (none: no review recorded yet)" in lines and "   not read (git has no origin/main here)" in lines, lines
    assert not os.path.exists(review_log.STORE)  # 0b only reads


def test_section_0b_applies_expiry_in_memory_only():
    reset()
    write(os.path.join(TMP, "2026-09-21.md"), "## Decisions\n\n1. old → x: a → b\n")
    review_log.record(os.path.join(TMP, "2026-09-21.md"))
    before = open(review_log.STORE, encoding="utf-8").read()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.since_last_section(D(2026, 11, 2), runner=FakeGit())
    assert "2026-09-21-01" not in out.getvalue()  # 42 days old: expired
    assert open(review_log.STORE, encoding="utf-8").read() == before


# ---------- section 6: hiring searches and the other money queries ----------

def test_section_6_splits_hiring_searches_from_other_money_queries():
    now = {"funeral choir hire": {"impressions": 40, "position": 12.0, "clicks": 1},
           "wedding choir london": {"impressions": 25, "position": 5.0, "clicks": 2},
           "carol singers for hire": {"impressions": 11, "position": 31.0, "clicks": 0},
           "choir for funeral": {"impressions": 9, "position": 9.0, "clicks": 0},  # under 10 impressions
           "nine lessons and carols order of service": {"impressions": 90, "position": 4.0, "clicks": 3},
           "funeral singer": {"impressions": 30, "position": 15.0, "clicks": 0}}
    before = {"wedding hymns": {"impressions": 5, "position": 20.0, "clicks": 0}}
    hiring, other = wr.money_query_blocks(now, before)
    assert hiring == ["funeral choir hire", "wedding choir london", "carol singers for hire"], hiring
    assert other[:2] == ["nine lessons and carols order of service", "funeral singer"], other
    assert "funeral choir hire" not in other and "wedding hymns" in other
    assert [wr.rank_band(p) for p in (5.0, 7.9, 8.0, 20.0, 20.1)] == ["page one", "page one", "8–20", "8–20", "deep"]
    many = {f"funeral music {i}": {"impressions": i, "position": 3.0, "clicks": 0} for i in range(30)}
    assert len(wr.money_query_blocks(many, {})[1]) == wr.OTHER_MONEY_TOP


def test_section_6_prints_the_bands_and_hands_section_0_its_clicks():
    class Resp:
        def __init__(self, rows):
            self.ok, self._rows = True, rows

        def json(self):
            return {"rows": self._rows}

    class Session:
        def post(self, url, json):
            dims = json["dimensions"]
            if dims == []:
                return Resp([{"clicks": 7, "impressions": 300, "ctr": 0.02, "position": 11.0}])
            if dims == ["query"]:
                return Resp([{"keys": ["funeral choir hire"], "clicks": 1, "impressions": 40, "position": 12.0},
                             {"keys": ["funeral hymns"], "clicks": 0, "impressions": 20, "position": 6.0}])
            return Resp([])
    wr.WEEK.clear()
    out = io.StringIO()
    with patched(wr.lm, "today", lambda *a, **k: D(2026, 11, 2)), contextlib.redirect_stdout(out):
        wr.gsc_section(Session())
    text = out.getvalue()
    assert "-- hiring searches (economics.hiring_intent, 10+ impressions this week), by impressions" in text, text
    assert any(l.startswith("   funeral choir hire") and l.endswith("[8–20]") for l in text.splitlines()), text
    other = text.split("-- other money queries")[1]
    assert "funeral hymns" in other and "funeral choir hire" not in other.split("-- top 15")[0], text
    assert wr.WEEK["organic"] == (7, 7, D(2026, 10, 24), D(2026, 10, 30)), wr.WEEK


# ---------- section 13 off the first Monday ----------

def test_section_13_off_the_first_monday_prints_one_next_line():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        wr.shortlist_section(None, D(2026, 10, 26), force=False)
    assert out.getvalue().splitlines() == ["", "== 13. Search Console shortlist (hiring intent, positions 8–20)",
                                           "   next: 2026-11-02"], out.getvalue()


# ---------- section 9c: the enquiry assistant's run log ----------

def runs(days, skip=(), early=(), zoho=(), daily=True):
    """A run log for `days` (dates): a start and a done at each slot, except the (date, hour) pairs in skip
    (no run), early (a start only) and zoho (a start then zoho_down)."""
    out = []
    for d in days:
        for h in range(6, 23, 2):
            if (d, h) in skip:
                continue
            t = datetime.datetime.combine(d, datetime.time(h, 7), tzinfo=wr.lm.LONDON)
            out.append({"start": t.isoformat()})
            if (d, h) in early:
                continue
            if (d, h) in zoho:
                out.append({"zoho_down": (t + datetime.timedelta(minutes=1)).isoformat()})
                continue
            out.append({"done": (t + datetime.timedelta(minutes=4)).isoformat(), "marked": 1})
        if daily:
            out.append({"daily": d.isoformat()})
    return out


WEEK9C = [D(2026, 10, 26) + datetime.timedelta(days=i) for i in range(7)]  # Mon 26 Oct to Sun 1 Nov


def test_9c_a_clean_week():
    w = wr.assistant_week(runs(WEEK9C), D(2026, 11, 2))
    assert (w["started"], w["expected"], w["finished"], w["early"], w["zoho_down"]) == (63, 63, 63, 0, 0), w
    assert w["daily_days"] == 7 and w["days"] == 7 and not w["partial"]
    assert abs(w["gap_hours"] - 2.0) < 1e-9, w["gap_hours"]
    lines = wr.assistant_lines(w)
    assert lines[0] == "   runs started 63 of 63 expected (9 a day, every two hours 06:07–22:07)", lines
    assert lines[1] == "   finished 63 · stopped early (no done and no Zoho-down line) 0 · Zoho down 0", lines
    assert "STALE" not in "\n".join(lines) and lines[-1] == "   daily pass ran on 7 of 7 days", lines


def test_9c_counts_early_stops_zoho_and_a_long_gap():
    d = WEEK9C
    skip = {(d[1], h) for h in range(6, 23, 2)} | {(d[2], 6), (d[2], 8)}  # Tue gone and Wed's first two
    w = wr.assistant_week(runs(d, skip=skip, early={(d[3], 10)}, zoho={(d[4], 12), (d[4], 14)}), D(2026, 11, 2))
    assert w["started"] == 63 - 11 and w["early"] == 1 and w["zoho_down"] == 2 and w["finished"] == 63 - 14, w
    # Mon 22:07 to Wed 10:07, inside 06:00–22:00: Tue's 16 h and Wed's 4h07
    assert abs(w["gap_hours"] - (16 + 4 + 7 / 60)) < 1e-6, w["gap_hours"]
    lines = wr.assistant_lines(w)
    gap = [l for l in lines if "longest gap" in l][0]
    assert "(Mon 26 Oct 22:07 to Wed 28 Oct 10:07)" in gap and "STALE ASSISTANT" in gap, gap
    path = os.path.join(TMP, "q9c.txt")
    write(path, "== 9c. Enquiry assistant\n" + "\n".join(lines) + "\n")
    assert any("STALE ASSISTANT" in l for l in wr.quiet_summary(path).splitlines() if l.startswith("problem:"))


def test_9c_before_a_full_week_says_when_the_log_started():
    w = wr.assistant_week(runs(WEEK9C[4:]), D(2026, 11, 2))  # from Fri 30 Oct
    assert w["partial"] and w["expected"] == 27 and w["started"] == 27 and w["days"] == 3, w
    assert w["gap_hours"] < 2.01, w["gap_hours"]  # the days before the log are not a gap
    lines = wr.assistant_lines(w)
    assert lines[0] == "   log started 2026-10-30 06:07: the figures cover from then, not a full week", lines
    assert lines[-1] == "   daily pass ran on 3 of 3 days", lines


def test_9c_section_reads_the_file_and_says_so_when_missing():
    reset()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert wr.assistant_section(D(2026, 11, 2)) is None
    assert out.getvalue().splitlines()[-1] == "   no run log yet (assistant_io.py writes it from 2026-11-02)", out.getvalue()
    path = os.path.join(TMP, "assistant-runs.jsonl")
    entries = runs(WEEK9C)
    # UTC and Z timestamps are read as the same moments
    entries[0] = {"start": datetime.datetime.fromisoformat(entries[0]["start"]).astimezone(datetime.timezone.utc)
                  .isoformat().replace("+00:00", "Z")}
    write(path, "\n".join(json.dumps(e) for e in entries) + "\nnot json\n")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        w = wr.assistant_section(D(2026, 11, 2))
    text = out.getvalue()
    assert w["started"] == 63 and "   1 unreadable line skipped" in text.splitlines(), text
    assert text.splitlines()[1] == "== 9c. Enquiry assistant, last 7 days (2026-10-26 to 2026-11-01)", text


def test_in_run_hours_counts_only_0600_to_2200_london():
    t = lambda d, h, m=0: datetime.datetime.combine(d, datetime.time(h, m), tzinfo=wr.lm.LONDON)
    assert wr.in_run_hours(t(D(2026, 10, 26), 22, 7), t(D(2026, 10, 27), 6, 7)) * 60 == 7
    assert wr.in_run_hours(t(D(2026, 10, 26), 8), t(D(2026, 10, 26), 10)) == 2
    # the clocks went back on 25 Oct 2026: still 16 run hours that day
    assert wr.in_run_hours(t(D(2026, 10, 25), 0), t(D(2026, 10, 26), 0)) == 16


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
