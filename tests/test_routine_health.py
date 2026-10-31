#!/usr/bin/env python3
"""routine_health.py: the watchdog's checks. Stdlib only: .venv/bin/python tests/test_routine_health.py"""
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

_HOME = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = _HOME
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "reports"))
import routine_health as rh  # noqa: E402

LON = rh.lm.LONDON


def at(y, m, d, hh, mm):
    return datetime.datetime(y, m, d, hh, mm, tzinfo=LON)


def log(entries):
    p = Path(tempfile.mkdtemp()) / "assistant-runs.jsonl"
    p.write_text("".join(json.dumps(e) + "\n" for e in entries))
    return p


def iso(t):
    return t.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


def test_no_log_is_a_note_not_an_alert():
    lines = rh.assistant_lines(at(2026, 11, 3, 12, 0), Path(_HOME) / "missing.jsonl")
    assert lines[0].startswith("note:"), lines


def test_a_recent_start_is_ok():
    p = log([{"start": iso(at(2026, 11, 3, 10, 9))}, {"done": iso(at(2026, 11, 3, 10, 10)), "marked": 0}])
    lines = rh.assistant_lines(at(2026, 11, 3, 11, 30), p)
    assert lines == ["ok: enquiry assistant: last run started Tue 03 Nov 10:09"], lines


def test_a_missed_slot_is_an_alert():
    # last start 06:09; the 08:07 and 10:07 slots passed (now 11:00) with no start
    p = log([{"start": iso(at(2026, 11, 3, 6, 9))}, {"done": iso(at(2026, 11, 3, 6, 11)), "marked": 2}])
    lines = rh.assistant_lines(at(2026, 11, 3, 11, 0), p)
    assert lines[0].startswith("ALERT: enquiry assistant: no run has started since Tue 03 Nov 06:09"), lines
    assert "due Tue 03 Nov 10:07" in lines[0], lines


def test_within_grace_is_not_an_alert():
    # 08:07 slot is only 20 minutes old: the 06:09 start still counts
    p = log([{"start": iso(at(2026, 11, 3, 6, 9))}, {"done": iso(at(2026, 11, 3, 6, 11)), "marked": 0}])
    assert rh.assistant_lines(at(2026, 11, 3, 8, 27), p)[0].startswith("ok:")


def test_overnight_is_quiet():
    # last start 22:08; at 05:00 the next slot (06:07) hasn't come
    p = log([{"start": iso(at(2026, 11, 2, 22, 8))}, {"done": iso(at(2026, 11, 2, 22, 9)), "marked": 0}])
    assert rh.assistant_lines(at(2026, 11, 3, 5, 0), p)[0].startswith("ok:")


def test_an_unfinished_run_is_noted():
    p = log([{"start": iso(at(2026, 11, 3, 10, 9))}])
    lines = rh.assistant_lines(at(2026, 11, 3, 11, 30), p)
    assert lines[0].startswith("ok:") and lines[1].startswith("note: enquiry assistant: the run started"), lines


def test_a_zoho_down_run_counts_as_finished():
    p = log([{"start": iso(at(2026, 11, 3, 10, 9))}, {"zoho_down": iso(at(2026, 11, 3, 10, 10))}])
    assert len(rh.assistant_lines(at(2026, 11, 3, 11, 30), p)) == 1


def test_monday_report_missing_is_an_alert_after_eleven():
    d = Path(tempfile.mkdtemp())
    assert rh.review_lines(at(2026, 11, 2, 12, 0), d)[0].startswith("ALERT: Monday review: no report saved for 2026-11-02")
    (d / "2026-11-02.txt").write_text("x")
    assert rh.review_lines(at(2026, 11, 2, 12, 0), d) == ["ok: Monday review: report saved for 2026-11-02"]


def test_monday_morning_looks_at_the_previous_week():
    d = Path(tempfile.mkdtemp())
    (d / "2026-10-26.txt").write_text("x")
    assert rh.review_lines(at(2026, 11, 2, 9, 30), d) == ["ok: Monday review: report saved for 2026-10-26"]
    assert rh.review_lines(at(2026, 10, 31, 20, 0), d) == ["ok: Monday review: report saved for 2026-10-26"]


def test_main_prints_and_exits_zero():
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert rh.main(at(2026, 11, 3, 12, 0)) == 0
    assert buf.getvalue().strip(), buf.getvalue()


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
