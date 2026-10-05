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
    fresh(refs=["2111"], folders=["2111A - Smith"])
    code, out, err = run("next-ref", "2026-11-21", "--taken", "2111B")
    assert code == 0, err
    got = json.loads(out)
    assert got["ref"] == "2111C", got
    today = aio.london_today()
    assert got["instalment_1_due"] == cp.deposit_due_date(today, datetime.date(2026, 11, 21)).isoformat()
    assert got["instalment_2_due"] == "2026-11-20"


def test_next_ref_counts_the_icloud_invoice_folders_too():
    fresh(refs=["2111"], folders=["2111A - Smith"], icloud=["2111B - Jones"])
    code, out, err = run("next-ref", "2026-11-21")
    assert code == 0, err
    assert json.loads(out)["ref"] == "2111C", out


def test_next_ref_with_nothing_taken_is_plain_ddmm():
    fresh()
    assert json.loads(run("next-ref", "2027-06-05")[1])["ref"] == "0506"


def test_next_ref_pure_function_and_short_notice():
    today = datetime.date(2026, 11, 10)
    got = aio.next_ref(datetime.date(2026, 11, 14), {"1411", "1411A"}, today)
    assert got["ref"] == "1411B"
    assert got["instalment_1_due"] == "2026-11-11"  # 3 days before the event, never the invoice day
    assert got["instalment_2_due"] == "2026-11-13"
    assert got["short_notice"] is True
    far = aio.next_ref(datetime.date(2027, 6, 5), set(), today)
    assert far["instalment_1_due"] == "2026-11-17" and far["short_notice"] is False


def test_next_ref_refuses_a_bad_or_past_date():
    fresh()
    assert run("next-ref", "21/11/2026")[0] != 0
    assert run("next-ref", "2020-01-01")[0] != 0
    assert run("next-ref", "2026-11-21", "--taken", "21 11")[0] != 0


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
