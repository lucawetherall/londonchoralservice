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
