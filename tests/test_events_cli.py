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


# --- retract: the owner's undo (Command Centre only) ----------------------------------------------------------------

NONCE = "ab" * 32


def nonce_file(d):
    import hashlib
    cc = os.path.join(d, "command-centre")
    os.makedirs(cc, mode=0o700, exist_ok=True)
    fd = os.open(os.path.join(cc, "owner-nonce"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(hashlib.sha256(NONCE.encode()).hexdigest())


def run_owner(*args, nonce=True):
    d = os.environ["LCS_PRIVATE_DIR"]
    if nonce:
        nonce_file(d)
    kw = {"input": NONCE + "\n"} if nonce else {"stdin": subprocess.DEVNULL}
    p = subprocess.run([PY, SCRIPT, *args], capture_output=True, text=True, timeout=30, env=dict(os.environ), **kw)
    return p.returncode, p.stdout + p.stderr


def migrated(d):
    ev.append("booking", "0000", "deposit-seen", {}, "script", on="2026-01-01", src="migration", eid="00000000000000aa")


def ledger_notes(d, ref="2111"):
    import csv
    with open(os.path.join(d, "bookings.csv"), newline="") as f:
        return next(r for r in csv.DictReader(f) if r["booking_ref"] == ref)["notes"]


def test_retract_undoes_a_fact_as_a_mistake_and_notes_it():
    import check_payments as cp
    d = fresh()
    clause = "cancelled 2026-09-20 by client email"
    write_ledger(d, {"2111": f"4 singers; {clause}"})
    migrated(d)
    eid = ev.append("booking", "2111", "cancelled", {}, "script", on="2026-09-20", note=ev.note_hash(clause))
    for args, nonce in ((("retract", eid), True), (("retract", eid, "--owner"), False)):
        code, out = run_owner(*args, nonce=nonce)
        assert code != 0 and "nothing written" in out, out
    code, out = run_owner("retract", eid, "--owner")
    assert code == 0 and out.strip() == "booking 2111: cancelled of 2026-09-20 undone", out
    today = ev.lm.today().isoformat()
    assert ledger_notes(d) == f"4 singers; {clause}; earlier entry undone {today} (owner)"
    ev.clear_cache()
    last = ev.read()[0][-1]
    assert (last["kind"], last["fields"], last["by"], last["note"]) == (
        "retract", {"target": eid, "why": "mistake"}, "owner", ev.note_hash(f"earlier entry undone {today} (owner)"))
    r = {"booking_ref": "2111", "notes": ledger_notes(d), "value_gbp": "650", "invoice_date": "2026-09-01",
         "event_date": "2026-12-12"}
    assert not cp.is_cancelled(r) and cp.held(r) == [], "undone: its clause is set aside, nothing is held"
    for bad in (eid, last["eid"], "0123456789abcdef", "nothex"):  # twice, a retract, unknown, malformed
        code, out = run_owner("retract", bad, "--owner")
        assert code != 0 and "nothing written" in out, (bad, out)


def write_store(d, rows):
    import csv
    import singer_invoices as si
    base = {c: "" for c in si.COLUMNS}
    with open(os.path.join(d, "singer-invoices.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=si.COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(dict(base, **r))


def store_row(d, mid):
    import csv
    with open(os.path.join(d, "singer-invoices.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    return rows, next(r for r in rows if r["message_id"] == mid)


CHANGED = "BANK DETAILS CHANGED since their last invoice (was ••••1111, now ••••5678): ring them before paying"


def test_a_bank_warning_is_never_undone_and_an_undone_one_leaves_the_alarm_to_the_notes():
    import singer_invoices as si
    d = fresh()
    write_ledger(d, {})
    migrated(d)
    write_store(d, [{"message_id": "m2", "received": "2026-09-20", "amount_gbp": "150.00", "bank_fp": "a1b2c3d4e5f60718",
                     "bank_changed": "yes", "notes": CHANGED}])
    eid = ev.append("singer_invoice", "m2", "bank-warning", {"fp8": "a1b2c3d4", "codes": ["changed"]}, "script",
                    note=ev.note_hash(CHANGED))
    code, out = run_owner("retract", eid, "--owner")
    assert code != 0 and "confirm" in out and "nothing written" in out, out
    import sys as _s
    _s.path.insert(0, os.path.join(ROOT))
    from command_centre import models
    assert models.live_facts("singer_invoice", "m2") == []  # never offered
    # an undone warning (by an earlier build, or by hand) leaves the notes and the column to say it: still rung first
    lcs = __import__("lcs_owner")
    saved, lcs._PROVEN = lcs._PROVEN, True
    try:
        ev.append("singer_invoice", "m2", "retract", {"target": eid, "why": "mistake"}, "owner")
    finally:
        lcs._PROVEN = saved
    ev.clear_cache()
    rows, r = store_row(d, "m2")
    assert si.warning_codes(r) is None and si.bank_changed(r) and si.ring_first_in(rows, r)


def marker_case(d, ref, notes, kind, fields, clause):
    write_ledger(d, {ref: f"{notes}; {clause}"})
    return ev.append("booking", ref, kind, fields, "script", note=ev.note_hash(clause))


def test_undoing_a_marker_really_unmarks_it():
    import datetime as dt
    import check_payments as cp
    import pipeline as pl
    today = ev.lm.today()
    td = today.isoformat()
    row = lambda d, ref: {"booking_ref": ref, "notes": ledger_notes(d, ref), "value_gbp": "650",  # noqa: E731
                          "invoice_date": "2026-09-01", "event_date": "2026-12-12", "occasion": "wedding"}
    for kind, fields, clause, read in (
            ("reminder-drafted", {"what": "deposit"}, f"reminder drafted {td}",
             lambda r: cp.note_readings(r, today)["reminded"]["deposit"]),
            ("reminder-drafted", {"what": "balance"}, f"balance reminder drafted {td}",
             lambda r: cp.note_readings(r, today)["reminded"]["balance"]),
            ("reminder-drafted", {"what": "receipt"}, f"receipt drafted {td}",
             lambda r: cp.note_readings(r, today)["reminded"]["receipt"]),
            ("deposit-seen", {}, "deposit seen 2026-09-03 (Starling)", lambda r: cp.note_readings(r, today)["noted_auto"])):
        d = fresh()
        migrated(d)
        eid = marker_case(d, "2111", "4 singers", kind, fields, clause)
        assert read(row(d, "2111")), (kind, clause)
        code, out = run_owner("retract", eid, "--owner")
        assert code == 0, out
        ev.clear_cache()
        assert not read(row(d, "2111")), (kind, clause, "undo must un-mark")
    # the review markers: reviews-due lists the booking again
    event = (today - dt.timedelta(days=5)).isoformat()
    for kind, fields, clause in (("review-drafted", {}, f"review request drafted {td}"),
                                 ("review-skipped", {"reason": "planner"}, f"review request skipped {td} (planner)")):
        d = fresh()
        migrated(d)
        write_ledger(d, {})
        import csv
        with open(os.path.join(d, "bookings.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["booking_ref", "notes", "event_date", "occasion", "value_gbp"])
            w.writeheader()
            w.writerow({"booking_ref": "2111", "notes": f"paid in full {event}; {clause}", "event_date": event,
                        "occasion": "wedding", "value_gbp": "650"})
        lcs = __import__("lcs_owner")
        saved, lcs._PROVEN = lcs._PROVEN, True
        try:
            ev.append("booking", "2111", "paid-in-full", {"basis": "owner"}, "owner", on=event,
                      note=ev.note_hash(f"paid in full {event}"))
        finally:
            lcs._PROVEN = saved
        eid = ev.append("booking", "2111", kind, fields, "script", note=ev.note_hash(clause))
        rows = lambda: ev.lm.read_csv(os.path.join(d, "bookings.csv"))  # noqa: E731
        assert pl.reviews_due(rows(), today) == [], kind
        code, out = run_owner("retract", eid, "--owner")
        assert code == 0, out
        ev.clear_cache()
        assert [x["booking_ref"] for x in pl.reviews_due(rows(), today)] == ["2111"], kind
    # the singer's "Paid!" marker: THANKS DUE again
    import singer_invoices as si
    d = fresh()
    write_ledger(d, {})
    migrated(d)
    write_store(d, [{"message_id": "m5", "received": "2026-09-20", "amount_gbp": "150.00", "paid_on": td,
                     "paid_amount": "150.00", "paid_verified": "yes", "notes": f"thanks due {td}; paid reply drafted {td}"}])
    eid = ev.append("singer_invoice", "m5", "paid-reply-drafted", {}, "script", note=ev.note_hash(f"paid reply drafted {td}"))
    assert si.thanked(store_row(d, "m5")[1])
    code, out = run_owner("retract", eid, "--owner")
    assert code == 0, out
    ev.clear_cache()
    assert not si.thanked(store_row(d, "m5")[1])


def test_after_an_undo_verify_and_compare_report_nothing():
    d = fresh()
    clause = "cancelled 2026-09-20 by client email"
    write_ledger(d, {"2111": f"4 singers; {clause}"})
    write_store(d, [])
    migrated(d)
    eid = ev.append("booking", "2111", "cancelled", {}, "script", on="2026-09-20", note=ev.note_hash(clause))
    assert run_owner("retract", eid, "--owner")[0] == 0
    code, out = run("verify")
    assert code == 0 and "without its note" not in out, out
    code, out = run("compare")
    assert code == 0 and "no difference" in out, out
    write_ledger(d, {"2111": "4 singers"})  # the owner tidies both clauses away by hand
    code, out = run("verify")
    assert code == 0 and "without its note" not in out, out
    code, out = run("compare")
    assert code == 0 and "no difference" in out, out


def test_retract_of_a_singer_fact_puts_its_column_back():
    import csv
    import singer_invoices as si
    d = fresh()
    write_ledger(d, {})
    migrated(d)
    base = {c: "" for c in si.COLUMNS}
    with open(os.path.join(d, "singer-invoices.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=si.COLUMNS)
        w.writeheader()
        w.writerow(dict(base, message_id="m1", received="2026-09-01", amount_gbp="100.00", withdrawn="2026-09-20",
                        notes="withdrawn 2026-09-20 (not-ours)"))
        w.writerow(dict(base, message_id="m2", received="2026-09-01", amount_gbp="100.00", bank_fp="a1b2c3d4e5f60718",
                        bank_confirmed="yes", notes="bank details confirmed by phone 2026-09-21"))
        w.writerow(dict(base, message_id="m3", received="2026-09-01", amount_gbp="100.00", paid_on="2026-09-22",
                        paid_amount="100.00", paid_verified="no", notes="settled by hand"))
    lcs = __import__("lcs_owner")
    saved, lcs._PROVEN = lcs._PROVEN, True
    try:
        eids = [ev.append("singer_invoice", "m1", "withdrawn", {"reason": "not-ours"}, "script", on="2026-09-20",
                          note=ev.note_hash("withdrawn 2026-09-20 (not-ours)")),
                ev.append("singer_invoice", "m2", "bank-confirmed", {"fp8": "a1b2c3d4"}, "owner", on="2026-09-21",
                          note=ev.note_hash("bank details confirmed by phone 2026-09-21")),
                ev.append("singer_invoice", "m3", "settled", {"amount": "100.00"}, "owner", on="2026-09-22",
                          note=ev.note_hash("settled by hand"))]
    finally:
        lcs._PROVEN = saved
    for eid in eids:
        code, out = run_owner("retract", eid, "--owner")
        assert code == 0, out
    with open(os.path.join(d, "singer-invoices.csv"), newline="") as f:
        rows = {r["message_id"]: r for r in csv.DictReader(f)}
    assert rows["m1"]["withdrawn"] == "" and rows["m2"]["bank_confirmed"] == "", rows
    assert (rows["m3"]["paid_on"], rows["m3"]["paid_amount"], rows["m3"]["paid_verified"]) == ("", "", ""), rows["m3"]
    assert all("earlier entry undone" in r["notes"] for r in rows.values())
    ev.clear_cache()
    for r in rows.values():  # the undo line is a record, never a warning, and nothing is held
        assert not any("undone" in w for w in si.live_warnings(list(rows.values()), r)), r["message_id"]
        assert si.held(list(rows.values()), r) == [], r["message_id"]
    assert not si.is_withdrawn(rows["m1"]) and not si.confirmed(rows["m2"]) and si.is_open(rows["m3"])


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
