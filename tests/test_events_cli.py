#!/usr/bin/env python3
"""Tests for scripts/bookings/events.py (verify, show): read-only views of the state log. Each test runs the
script against a temp LCS_PRIVATE_DIR, never ~/lcs-private. Stdlib only: .venv/bin/python tests/test_events_cli.py"""
import datetime, os, subprocess, sys, tempfile
from zoneinfo import ZoneInfo

os.environ["LCS_PRIVATE_DIR"] = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ.pop("LCS_BOOKINGS_CSV", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_events as ev  # noqa: E402

PY, SCRIPT = sys.executable, os.path.join(ROOT, "scripts", "bookings", "events.py")


def fresh():
    d = tempfile.mkdtemp()
    os.chmod(d, 0o700)
    os.environ["LCS_PRIVATE_DIR"] = d
    ev.clear_cache()
    return d


def run(*args):
    p = subprocess.run([PY, SCRIPT, *args], capture_output=True, text=True, timeout=30, env=dict(os.environ))
    return p.returncode, p.stdout + p.stderr


def test_verify_without_a_log():
    fresh()
    code, out = run("verify")
    assert code == 0 and "no state log yet" in out, out


def test_verify_a_whole_log():
    fresh()
    ev.append("booking", "2111", "deposit-seen", {}, "script", on="2026-09-20")
    ev.append("booking", "2111", "cancelled", {}, "script", on="2026-09-21")
    code, out = run("verify")
    assert code == 0, out
    assert "2 lines" in out and "0 skipped" in out and "chain whole" in out and "last written 20" in out, out


def test_verify_exits_1_on_a_broken_chain_or_a_skipped_line():
    d = fresh()
    for kind in ("deposit-seen", "cancelled", "review-drafted"):
        ev.append("booking", "2111", kind, {}, "script")
    path = os.path.join(d, "events.jsonl")
    lines = open(path, "rb").read().split(b"\n")[:-1]
    with open(path, "wb") as f:
        f.write(lines[0] + b"\n" + lines[2] + b"\n")
    code, out = run("verify")
    assert code == 1 and "broken at line 2" in out, out
    with open(path, "wb") as f:
        f.write(lines[0] + b"\nnot json\n")
    code, out = run("verify")
    assert code == 1 and "1 skipped" in out, out


def test_verify_reports_an_unreadable_log():
    d = fresh()
    ev.append("booking", "2111", "cancelled", {}, "script")
    os.chmod(os.path.join(d, "events.jsonl"), 0o644)
    code, out = run("verify")
    assert code == 1 and "can't be read" in out, out
    os.chmod(os.path.join(d, "events.jsonl"), 0o600)
    os.rename(os.path.join(d, "events.jsonl"), os.path.join(d, "real.jsonl"))
    os.symlink(os.path.join(d, "real.jsonl"), os.path.join(d, "events.jsonl"))
    code, out = run("verify")
    assert code == 1 and "can't be read" in out, out


def test_show_prints_one_line_per_fact_and_never_notes():
    fresh()
    import lcs_owner
    saved, lcs_owner._PROVEN = lcs_owner._PROVEN, True  # as the Command Centre's owner run
    try:
        a = ev.append("booking", "2111", "fees-accepted", {"amount": "12.40"}, "owner", on="2026-09-20",
                      note=ev.note_hash("short by fees £12.40 accepted 2026-09-20 (owner)"))
        ev.append("booking", "2111", "retract", {"target": a, "why": "mistake"}, "owner", on="2026-09-21")
    finally:
        lcs_owner._PROVEN = saved
    ev.append("booking", "2112", "cancelled", {}, "script")
    code, out = run("show", "booking", "2111")
    lines = out.strip().splitlines()
    assert code == 0 and len(lines) == 2, out
    assert lines[0].startswith("2026-09-20 fees-accepted amount=12.40 by owner (live)") and "retracted" in lines[0], out
    assert lines[1].startswith("2026-09-21 retract") and f"target={a}" in lines[1], out
    assert "short by fees" not in out and "2112" not in out


def test_show_a_future_dated_retract_leaves_its_target_standing():
    d = fresh()
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.astimezone(ZoneInfo("Europe/London")).date()
    ahead = now + datetime.timedelta(hours=20)
    base = {"v": 1, "prev": "", "subject": "booking", "id": "2111", "by": "script", "src": "live"}
    target = dict(base, eid="a1b2c3d4e5f60718", at=now.strftime("%Y-%m-%dT%H:%M:%SZ"), on=today.isoformat(),
                  kind="cancelled", fields={})
    undo = dict(base, eid="b1b2c3d4e5f60718", at=ahead.strftime("%Y-%m-%dT%H:%M:%SZ"), by="owner",
                on=ev.at_date(ahead.strftime("%Y-%m-%dT%H:%M:%SZ")).isoformat(), kind="retract",
                fields={"target": target["eid"], "why": "mistake"})
    if undo["on"] == target["on"]:
        return  # late in the London day the retract isn't dated after today: nothing to test right now
    first = ev.dumps(ev.validate(target)) + "\n"
    undo["prev"] = ev.chain_hash(first.encode())
    with open(os.open(os.path.join(d, "events.jsonl"), os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
        f.write(first + ev.dumps(ev.validate(undo)) + "\n")
    code, out = run("show", "booking", "2111")
    lines = out.strip().splitlines()
    assert code == 0 and "retracted" not in lines[0] and "dated after today" in lines[1], out


def test_show_an_unknown_id():
    fresh()
    code, out = run("show", "singer_invoice", "1759123")
    assert code == 0 and out.strip() == "no recorded facts", out


def test_show_refuses_a_bad_subject_or_id():
    fresh()
    for args in (("show", "enquiry", "2111"), ("show", "booking", "ann@example.com"), ("show", "booking", "Ann Smith")):
        code, out = run(*args)
        assert code != 0, (args, out)


def write_ledger(d, notes):
    with open(os.path.join(d, "bookings.csv"), "w") as f:
        f.write("booking_ref,notes\n" + "".join(f"{ref},{n}\n" for ref, n in notes.items()))


def test_verify_lists_facts_whose_note_is_missing_and_stale_notes_checked_hashes():
    import lcs_owner
    d = fresh()
    write_ledger(d, {"2111": "PENDING: invoiced; cancelled 2026-09-20 by client email", "2112": "PENDING"})
    ev.append("booking", "2111", "cancelled", {}, "script", on="2026-09-20",
              note=ev.note_hash("cancelled 2026-09-20 by client email"))
    code, out = run("verify")
    assert code == 0 and "missing" not in out, out
    gone = ev.append("booking", "2112", "cancelled", {}, "script", on="2026-09-21",
                     note=ev.note_hash("cancelled 2026-09-21 by client email"))  # the ledger write never landed
    saved, lcs_owner._PROVEN = lcs_owner._PROVEN, True
    try:
        ev.append("booking", "2111", "notes-checked", {"clauses": [ev.note_hash("PENDING: invoiced"), "0123456789ab"]},
                  "owner", on="2026-09-22")
    finally:
        lcs_owner._PROVEN = saved
    code, out = run("verify")
    assert code == 1, out
    assert f"fact without its note: booking 2112 cancelled on 2026-09-21 [{gone}]" in out, out
    assert "notes-checked hash no clause matches: booking 2111 0123456789ab" in out, out
    assert "PENDING" not in out and "client email" not in out
    ev.append("booking", "2112", "retract", {"target": gone, "why": "write-failed"}, "script")
    code, out = run("verify")
    assert "2112" not in out, "a withdrawn fact never had a note to lose"


def test_the_log_is_never_committed():
    lines = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read().splitlines()
    assert "events*.jsonl" in lines


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
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
