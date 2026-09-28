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


def test_christmas_value_check_flags_extra_spend_past_sixty_pounds():
    from types import SimpleNamespace as N
    rows = lambda costs: (lambda query: [N(metrics=N(cost_micros=int(c * 1e6))) for c in costs])
    lines = wr.value_check_lines(rows([8, 8, 2]), datetime.date(2026, 10, 5))
    assert lines[0] == "Christmas value check: £18.00 spent since 28 Sep, £6.00 of it above the £5/day level", lines
    lines = wr.value_check_lines(rows([8] * 21), datetime.date(2026, 11, 2))
    assert "PAST £60: back to £5 unless a real enquiry came from the campaign" in lines[0], lines
    assert "(checked from" not in lines[0]
    assert wr.value_check_lines(rows([8]), datetime.date(2026, 9, 27)) == []


def test_spend_guard_flags_eighty_pounds_with_no_lead_and_enough_clicks():
    from types import SimpleNamespace as N
    def rows(query):
        return [N(campaign=N(id=1, name="wedding-leads"), metrics=N(cost_micros=95_000_000, clicks=20, conversions=0.0)),
                N(campaign=N(id=2, name="funeral expert campaign"), metrics=N(cost_micros=120_000_000, clicks=25, conversions=2.0)),
                N(campaign=N(id=3, name="quiet"), metrics=N(cost_micros=85_000_000, clicks=9, conversions=0.0)),
                N(campaign=N(id=4, name="small"), metrics=N(cost_micros=30_000_000, clicks=6, conversions=0.0))]
    lines = wr.spend_guard_lines(rows, datetime.date(2026, 10, 26))
    assert lines[0] == ("spend guard wedding-leads: £95.00, 20 clicks, 0 leads in 28 days — STOP GUARD: propose "
                        "pausing (never deleting) until the owner decides"), lines
    assert lines[1] == "spend guard funeral expert campaign: £120.00, 25 clicks, 2 leads in 28 days", lines
    assert lines[2].endswith("under 15 clicks, too few to judge; watch next week"), lines
    assert lines[3] == "spend guard small: £30.00, 6 clicks, 0 leads in 28 days", lines
    assert lines[4].startswith("stop rule: £80+ in 28 days with no lead")


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
