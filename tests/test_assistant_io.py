#!/usr/bin/env python3
"""Tests for scripts/bookings/assistant_io.py. Stdlib only: .venv/bin/python tests/test_assistant_io.py"""
import csv, datetime, json, os, shutil, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(_HOME, "bookings.csv")
os.environ["LCS_INVOICES_DIR"] = os.path.join(_HOME, "LCS-invoices")  # never the real iCloud folder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import assistant_io as aio  # noqa: E402
import check_payments as cp  # noqa: E402

PY, SCRIPT = sys.executable, os.path.join(ROOT, "scripts", "bookings", "assistant_io.py")
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]


def run(*args):
    p = subprocess.run([PY, SCRIPT, *args], capture_output=True, text=True, cwd=ROOT,
                       env=dict(os.environ, LCS_PRIVATE_DIR=_HOME, LCS_BOOKINGS_CSV=os.path.join(_HOME, "bookings.csv")))
    return p.returncode, p.stdout, p.stderr


def fresh(refs=(), folders=(), icloud=()):
    for name in os.listdir(_HOME):
        path = os.path.join(_HOME, name)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    with open(os.path.join(_HOME, "bookings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        for ref in refs:
            w.writerow({c: "" for c in LEDGER_COLS} | {"booking_ref": ref})
    for name in folders:
        os.makedirs(os.path.join(_HOME, "invoices", name))
    for name in icloud:
        os.makedirs(os.path.join(_HOME, "LCS-invoices", name))


# --- state / daily-done -------------------------------------------------------------------------

def test_state_reports_daily_due_until_daily_done_then_not():
    fresh()
    code, out, _ = run("state")
    assert code == 0 and json.loads(out)["daily_due"] is True, out
    code, out, _ = run("daily-done")
    assert code == 0 and "daily pass done" in out, out
    code, out, _ = run("state")
    assert json.loads(out)["daily_due"] is False, out
    # `done` keeps the daily record
    run("done", "m1")
    assert json.loads(run("state")[1])["daily_due"] is False


def test_daily_due_follows_the_london_date_not_utc():
    # 23:30 UTC on 28 Sep is 00:30 on 29 Sep in London (BST): a new London day
    late = datetime.datetime(2026, 9, 28, 23, 30, tzinfo=datetime.timezone.utc)
    assert aio.london_today(late) == datetime.date(2026, 9, 29)
    assert aio.daily_due({"daily_done": "2026-09-28"}, late) is True
    assert aio.daily_due({"daily_done": "2026-09-29"}, late) is False
    # 09:07 UTC and 07:07 UTC on the same BST day are one London day: the daily pass runs once
    assert aio.london_today(datetime.datetime(2026, 9, 28, 7, 7, tzinfo=datetime.timezone.utc)) == \
        aio.london_today(datetime.datetime(2026, 9, 28, 9, 7, tzinfo=datetime.timezone.utc))
    assert aio.daily_due({}, late) is True


# --- next-ref ------------------------------------------------------------------------------------

def test_next_ref_takes_the_first_free_suffix_and_the_checker_due_dates():
    fresh(refs=["211126"], folders=["211126A - Smith"])
    code, out, err = run("next-ref", "2026-11-21", "--taken", "211126B")
    assert code == 0, err
    got = json.loads(out)
    assert got["ref"] == "211126C", got
    today = aio.london_today()
    assert got["instalment_1_due"] == cp.deposit_due_date(today, datetime.date(2026, 11, 21)).isoformat()
    assert got["instalment_2_due"] == "2026-11-19"


def test_next_ref_counts_the_icloud_invoice_folders_too():
    fresh(refs=["211126"], folders=["211126A - Smith"], icloud=["211126B - Jones"])
    code, out, err = run("next-ref", "2026-11-21")
    assert code == 0, err
    assert json.loads(out)["ref"] == "211126C", out


def test_next_ref_with_nothing_taken_is_plain_ddmmyy():
    fresh()
    assert json.loads(run("next-ref", "2027-06-05")[1])["ref"] == "050627"


def test_next_ref_older_ddmm_refs_never_block_a_new_ddmmyy_one():
    # owner decision, 14 Oct 2026: 2111 and 2111A (older bookings) keep their refs; events on 21 Nov 2026
    # and 21 Nov 2027 get 211126 and 211127, so a year never repeats a ref
    fresh(refs=["2111", "2111A"], folders=["2111B - Smith"])
    code, out, err = run("next-ref", "2026-11-21", "--taken", "2111C,211127")
    assert code == 0, err
    assert json.loads(out)["ref"] == "211126", out
    assert json.loads(run("next-ref", "2027-11-21", "--taken", "211127")[1])["ref"] == "211127A"


def test_next_ref_pure_function_and_short_notice():
    today = datetime.date(2026, 11, 10)
    got = aio.next_ref(datetime.date(2026, 11, 14), {"141126", "141126A", "1411"}, today)
    assert got["ref"] == "141126B"
    assert got["instalment_1_due"] == "2026-11-11"  # 3 days before the event, never the invoice day
    assert got["instalment_2_due"] == "2026-11-12"
    assert got["short_notice"] is True
    far = aio.next_ref(datetime.date(2027, 6, 5), set(), today)
    assert far["ref"] == "050627"
    assert far["instalment_1_due"] == "2026-11-17" and far["short_notice"] is False


def test_ref_re_takes_both_forms_and_nothing_else():
    for ok in ("2111", "2111A", "211126", "211126A", "0506", "050627"):
        assert aio.REF_RE.fullmatch(ok), ok
    for bad in ("211", "21112", "2111267", "211126AB", "2111a", "21/11/26", "21-11-26", "", "211126 "):
        assert not aio.REF_RE.fullmatch(bad), bad


def test_next_ref_refuses_a_bad_or_past_date():
    fresh()
    assert run("next-ref", "21/11/2026")[0] != 0
    assert run("next-ref", "2020-01-01")[0] != 0
    assert run("next-ref", "2026-11-21", "--taken", "21 11")[0] != 0
    assert run("next-ref", "2026-11-21", "--taken", "21112")[0] != 0  # five digits
    assert run("next-ref", "2026-11-21", "--taken", "2111267")[0] != 0  # seven digits
    assert run("next-ref", "2026-11-21", "--taken", "21/11/26")[0] != 0


# --- prices --------------------------------------------------------------------------------------

def test_prices_prints_compact_price_tables():
    code, out, err = run("prices")
    assert code == 0, err
    assert "Small Choir" in out and "£1,150" in out and "£" in out, out
    assert "pricing.html" in out and "christmas-pricing.html" in out
    assert len(out.encode()) < 4000, len(out.encode())
    assert "<" not in out and "&pound;" not in out


# --- ledger-add ----------------------------------------------------------------------------------

def test_ledger_add_requires_a_known_occasion():
    fresh()
    code, _, err = run("ledger-add", json.dumps({"booking_ref": "2111", "occasion": "Wedding reception"}))
    assert code != 0 and "occasion" in err, err
    code, _, err = run("ledger-add", json.dumps({"booking_ref": "2111"}))
    assert code != 0 and "occasion" in err, err
    code, out, err = run("ledger-add", json.dumps({"booking_ref": "2111", "occasion": "private event"}))
    assert code == 0 and "added 2111" in out, err
    code, _, err = run("ledger-add", json.dumps({"booking_ref": "2111", "occasion": "wedding"}))
    assert code != 0 and "duplicate" in err


# --- review I9 / M2: ledger-add, state and done ---------------------------------------------------

def test_ledger_add_appends_one_row_atomically_at_mode_600():
    fresh(refs=["0110"])
    ledger = os.path.join(_HOME, "bookings.csv")
    os.chmod(ledger, 0o644)
    code, out, err = run("ledger-add", json.dumps({"booking_ref": "2111", "occasion": "wedding", "value_gbp": 1150,
                                                   "notes": "PENDING: invoiced by enquiry assistant"}))
    assert code == 0 and out.strip() == "ledger: added 2111", (out, err)
    with open(ledger, newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["booking_ref"] for r in rows] == ["0110", "2111"] and rows[1]["value_gbp"] == "1150", rows
    assert oct(os.stat(ledger).st_mode & 0o777) == "0o600"
    assert sorted(n for n in os.listdir(_HOME) if n.startswith(".")) == [], os.listdir(_HOME)  # no temp file left


def test_ledger_add_refuses_duplicates_unknown_columns_bad_json_and_no_ledger():
    fresh(refs=["2111"])
    ledger = os.path.join(_HOME, "bookings.csv")
    before = open(ledger).read()
    for args, why in ((json.dumps({"booking_ref": "2111", "occasion": "wedding"}), "duplicate"),
                      (json.dumps({"booking_ref": "2112", "occasion": "wedding", "phone": "x"}), "unknown columns"),
                      (json.dumps({"occasion": "wedding"}), "missing"),
                      ("{not json", "one JSON object"),
                      (json.dumps(["2112"]), "one JSON object")):
        code, _, err = run("ledger-add", args)
        assert code != 0 and why in err, (args, err)
    assert open(ledger).read() == before
    os.remove(ledger)
    code, _, err = run("ledger-add", json.dumps({"booking_ref": "2112", "occasion": "wedding"}))
    assert code != 0 and "no ledger yet" in err, err


def test_ledger_add_records_the_facts_its_notes_state_once_the_migration_is_applied():
    import lcs_events as ev
    notes = "PENDING: invoiced by enquiry assistant; deposit seen 2026-09-20; balance to be paid in cash"
    row = {"booking_ref": "2111", "occasion": "wedding", "value_gbp": 1150, "invoice_date": "2026-09-01",
           "event_date": "2026-12-12", "notes": notes}
    fresh(refs=["0110"])
    code, out, err = run("ledger-add", json.dumps(row))
    assert code == 0 and not os.path.exists(os.path.join(_HOME, "events.jsonl")), err  # before: the notes alone
    fresh(refs=["0110"])
    ev.clear_cache()
    ev.append("booking", "0000", "deposit-seen", {}, "script", on="2026-01-01", src="migration", eid="00000000000000aa")
    code, out, err = run("ledger-add", json.dumps(row))
    assert code == 0 and out.strip() == "ledger: added 2111", (out, err)
    ev.clear_cache()
    got = [(e["kind"], e["fields"], e["by"], e["note"]) for e in ev.read()[0] if e["src"] == "live"]
    assert got == [("noted-paid", {"scope": "part"}, "script", ev.note_hash("deposit seen 2026-09-20")),
                   ("arranged", {"method": "cash"}, "script", ev.note_hash("balance to be paid in cash"))], got
    r = next(x for x in cp.lm.read_csv(os.path.join(_HOME, "bookings.csv")) if x["booking_ref"] == "2111")
    assert cp.held(r) == [] and cp.assess(r, [], datetime.date(2026, 9, 28))["state"] == "ARRANGED"
    fresh()
    ev.clear_cache()


def test_ledger_add_skips_a_fact_dated_after_today_and_still_adds_the_row():
    import lcs_events as ev
    for i, notes in enumerate(("cancelled 2027-01-05 by client email", "paid per client email 2027-01-05",
                               "balance to be paid in cash (arranged 2027-01-05)")):
        fresh(refs=["0110"])
        ev.clear_cache()
        ev.append("booking", "0000", "deposit-seen", {}, "script", on="2026-01-01", src="migration", eid="00000000000000aa")
        row = {"booking_ref": f"22{i:02d}", "occasion": "wedding", "value_gbp": 1150, "invoice_date": "2026-09-01",
               "event_date": "2027-02-12", "notes": notes}
        code, out, err = run("ledger-add", json.dumps(row))
        assert code == 0 and out.strip() == f"ledger: added 22{i:02d}", (notes, out, err)
        ev.clear_cache()
        assert [e for e in ev.read()[0] if e["src"] == "live"] == [], notes
        r = next(x for x in cp.lm.read_csv(os.path.join(_HOME, "bookings.csv")) if x["booking_ref"] == f"22{i:02d}")
        assert r["notes"] == notes
    fresh()
    ev.clear_cache()


def test_state_file_is_private_and_done_moves_last_checked_to_the_run_start():
    fresh()
    state = json.loads(run("state")[1])
    path = os.path.join(_HOME, "assistant-state.json")
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    started = state["now"]
    code, out, _ = run("done", "m1", "m2")
    assert code == 0 and f"last_checked {started}" in out, out
    saved = json.load(open(path))
    assert saved["last_checked"] == started and saved["handled"] == ["m1", "m2"] and "run_started" not in saved, saved
    assert json.loads(run("state")[1])["handled"] == ["m1", "m2"]


def test_zoho_down_books_one_retry_until_a_done_clears_it():
    fresh()
    before = json.loads(run("state")[1])
    code, out, _ = run("zoho-down")
    assert code == 0 and out.startswith("retry: yes "), out
    at = datetime.datetime.fromisoformat(out.split()[2])
    assert at.utcoffset() is not None
    lead = at - datetime.datetime.now(datetime.timezone.utc)
    assert datetime.timedelta(minutes=9) < lead <= datetime.timedelta(minutes=10), lead
    # the failed run moved nothing: the retry looks back as far as this run would have
    assert json.loads(run("state")[1])["last_checked"] == before["last_checked"]
    # the retry run fails too: no second retry, no loop
    code, out, _ = run("zoho-down")
    assert code == 0 and out.startswith("retry: no"), out
    # a run that reaches `done` clears it, so the next outage gets its own retry
    run("done")
    assert run("zoho-down")[1].startswith("retry: yes ")


def test_zoho_retry_window_lapses_after_three_hours():
    now = datetime.datetime(2026, 10, 22, 13, 15, tzinfo=datetime.timezone.utc)
    booked = {"retry_booked_at": (now - datetime.timedelta(hours=2)).isoformat()}
    assert aio.zoho_retry(booked, now) == (False, None)
    booked = {"retry_booked_at": (now - datetime.timedelta(hours=3, minutes=1)).isoformat()}
    retry, at = aio.zoho_retry(booked, now)
    assert retry and at == "2026-10-22T14:25:00+01:00", at  # BST


# --- run log (assistant-runs.jsonl) ---------------------------------------------------------------

RUNS = os.path.join(_HOME, "assistant-runs.jsonl")


def run_log():
    with open(RUNS) as f:
        return [json.loads(line) for line in f if line.strip()]


def test_run_log_records_state_done_zoho_down_and_daily_done_at_mode_600():
    fresh()
    started = json.loads(run("state")[1])["now"]
    assert oct(os.stat(RUNS).st_mode & 0o777) == "0o600"
    run("zoho-down")
    run("zoho-down")  # the retry is refused, the failure is still logged
    run("daily-done")
    code, out, _ = run("done", "m1", "m2")
    assert code == 0, out
    log = run_log()
    assert [sorted(e) for e in log] == [["start"], ["zoho_down"], ["zoho_down"], ["daily"], ["done", "marked"]], log
    assert log[0]["start"] == started
    assert log[3]["daily"] == aio.london_today().isoformat()
    assert log[4]["marked"] == 2
    for e in (log[1]["zoho_down"], log[4]["done"]):  # the state file's own format: UTC, to the second
        t = datetime.datetime.fromisoformat(e)
        assert t.utcoffset() == datetime.timedelta(0) and t.microsecond == 0 and len(e) == len(started), e
    run("done")
    assert run_log()[-1]["marked"] == 0


def unwritable_logs():
    """Run-log paths an append must survive: a directory, a read-only file and a symlink (never followed)."""
    def as_dir():
        os.mkdir(RUNS)

    def read_only():
        with open(RUNS, "w") as f:
            f.write('{"start": "2026-10-30T08:07:00+00:00"}\n')
        os.chmod(RUNS, 0o400)

    def symlink():
        target = os.path.join(_HOME, "elsewhere.jsonl")
        open(target, "w").close()
        os.symlink(target, RUNS)
    return as_dir, read_only, symlink


def test_a_run_log_that_cannot_be_written_changes_no_output_or_exit_code():
    fresh()
    good = {cmd: run(*cmd) for cmd in (("state",), ("zoho-down",), ("daily-done",), ("done", "m1"))}
    for breaker in unwritable_logs():
        fresh()
        breaker()
        for cmd, (code, out, err) in good.items():
            got = run(*cmd)
            assert got[0] == code and got[2] == err == "", (breaker.__name__, cmd, got)
            if cmd == ("state",):
                a, b = json.loads(got[1]), json.loads(out)
                assert set(a) == set(b) and a["daily_due"] == b["daily_due"], (breaker.__name__, got)
                assert got[1].count("\n") == out.count("\n")
            else:
                assert got[1].split()[:2] == out.split()[:2], (breaker.__name__, cmd, got)
        if breaker.__name__ == "symlink":
            assert os.path.getsize(os.path.join(_HOME, "elsewhere.jsonl")) == 0  # nothing written through it
        if breaker.__name__ == "read_only":
            os.chmod(RUNS, 0o600)


def test_run_log_prunes_lines_older_than_60_days_once_it_is_long():
    fresh()
    now = datetime.datetime(2026, 10, 31, 9, 7, tzinfo=datetime.timezone.utc)
    old = (now - datetime.timedelta(days=61)).isoformat(timespec="seconds")
    recent = (now - datetime.timedelta(days=59)).isoformat(timespec="seconds")
    with open(RUNS, "w") as f:
        for _ in range(3):
            f.write(json.dumps({"start": old}) + "\n")
        f.write(json.dumps({"daily": "2026-08-30"}) + "\n")  # 62 days: dropped
        f.write(json.dumps({"daily": "2026-09-02"}) + "\n")  # 59 days: kept
        f.write("not json\n")  # an unreadable line goes
        f.write(json.dumps({"done": recent, "marked": 1}) + "\n")
    saved = aio.RUN_LOG_MAX_LINES
    aio.RUN_LOG_MAX_LINES = 5
    try:
        aio.log_run({"start": now.isoformat(timespec="seconds")}, now)
    finally:
        aio.RUN_LOG_MAX_LINES = saved
    assert run_log() == [{"daily": "2026-09-02"}, {"done": recent, "marked": 1},
                         {"start": now.isoformat(timespec="seconds")}], run_log()
    assert oct(os.stat(RUNS).st_mode & 0o777) == "0o600"
    # below the line limit nothing is rewritten: old lines stay until the file is long
    with open(RUNS, "a") as f:
        f.write(json.dumps({"start": old}) + "\n")
    aio.log_run({"daily": "2026-10-31"}, now)
    assert len(run_log()) == 5, run_log()


# --- books-queue ---------------------------------------------------------------------------------

def queued(ref="2111", **over):
    rec = {"ref": ref, "reason": "trial expired",
           "contact_email": "client@example.com",
           "contact": {"contact_name": "Test Client", "contact_type": "customer"},
           "invoice": {"invoice_number": ref, "date": "2026-10-14", "due_date": "2026-10-21",
                       "line_items": [{"name": "Small choir (4 singers)", "rate": 1150, "quantity": 1}],
                       "notes": "First instalment £575.00 due 21 October 2026."}}
    rec.update(over)
    return json.dumps(rec)


def test_books_queue_add_list_done_round_trip_at_mode_600():
    fresh()
    code, out, _ = run("books-queue", "list")
    assert code == 0 and json.loads(out) == [], out
    code, out, _ = run("books-queue", "add", queued())
    assert code == 0 and "2111 queued" in out, out
    path = os.path.join(_HOME, "books-queue.jsonl")
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    rows = json.loads(run("books-queue", "list")[1])
    assert [r["ref"] for r in rows] == ["2111"] and rows[0]["invoice"]["line_items"][0]["rate"] == 1150, rows
    assert rows[0]["contact_email"] == "client@example.com" and rows[0]["queued"], rows
    code, out, _ = run("books-queue", "add", queued())  # a rerun of the same booking
    assert code == 0 and "already queued" in out, out
    run("books-queue", "add", queued("2111A"))
    assert [r["ref"] for r in json.loads(run("books-queue", "list")[1])] == ["2111", "2111A"]
    code, out, _ = run("books-queue", "done", "2111")
    assert code == 0 and "2111 done" in out, out
    assert [r["ref"] for r in json.loads(run("books-queue", "list")[1])] == ["2111A"]
    code, _, err = run("books-queue", "done", "2111")
    assert code != 0 and "not queued" in err, err
    # the done record stays in the file (a trail), and the ref can be queued again later
    assert len(open(path).read().splitlines()) == 2
    code, out, _ = run("books-queue", "add", queued())
    assert code == 0 and "2111 queued" in out, out


def test_books_queue_add_refuses_bad_records():
    fresh()
    bad = [
        "not json",
        json.dumps([1]),
        queued(extra="x"),
        queued(ref="21-11"),
        queued(ref="21112"),
        queued(ref="2111267"),
        queued(contact_email="nobody"),
        queued(contact={"contact_type": "customer"}),
        queued(invoice={"invoice_number": "9999", "line_items": [{"rate": 1}]}),
        queued(invoice={"invoice_number": "2111", "send": True, "line_items": [{"rate": 1}]}),
        queued(invoice={"invoice_number": "2111", "customer_id": "1", "line_items": [{"rate": 1}]}),
        queued(invoice={"invoice_number": "2111", "line_items": []}),
        queued(invoice={"invoice_number": "2111", "line_items": [{"name": "no rate"}]}),
    ]
    for arg in bad:
        code, _, err = run("books-queue", "add", arg)
        assert code != 0, arg
    assert not os.path.exists(os.path.join(_HOME, "books-queue.jsonl"))
    for args in (("books-queue",), ("books-queue", "list", "x"), ("books-queue", "done"), ("books-queue", "zap")):
        code, _, err = run(*args)
        assert code != 0 and "usage" in err, (args, err)


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
