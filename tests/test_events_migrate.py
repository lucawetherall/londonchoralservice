#!/usr/bin/env python3
"""Tests for the one-off state-log migration and the notes/events compare (scripts/bookings/lcs_migrate.py and
events.py migrate / compare; structured-state design, "Migration"). Every test uses a temp LCS_PRIVATE_DIR, never
~/lcs-private. Stdlib only: .venv/bin/python tests/test_events_migrate.py"""
import ast, csv, datetime, hashlib, os, re, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.chmod(_HOME, 0o700)
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ.pop("LCS_BOOKINGS_CSV", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_payments as cp  # noqa: E402
import lcs_events as ev  # noqa: E402
import lcs_migrate as mig  # noqa: E402
import lcs_money as lm  # noqa: E402
import lcs_owner  # noqa: E402
import singer_invoices as si  # noqa: E402
from state_cases import BOOKING_CASES, SINGER_CASES, T  # noqa: E402

PY, SCRIPT = sys.executable, os.path.join(ROOT, "scripts", "bookings", "events.py")
NONCE = "ab" * 32
LEDGER_COLS = ["booking_ref", "client_name", "value_gbp", "invoice_date", "event_date", "occasion", "notes"]


def booking(ref, notes, value=1150, invoice="2026-09-01", event="2026-12-12"):
    return {"booking_ref": ref, "client_name": "Ann Smith", "value_gbp": str(value), "invoice_date": invoice,
            "event_date": event, "occasion": "wedding", "notes": notes}


def case_rows():
    """A ledger row per booking case (each clause's text as the notes) and a store row per singer case invoice."""
    ledger = []
    for n, (name, value, invoice, event, clauses, paid, today) in enumerate(BOOKING_CASES):
        ledger.append(booking(f"C{n}", "; ".join(t for t, _ in clauses), value, invoice, event))
    store = []
    for n, (name, invoices, today) in enumerate(SINGER_CASES):
        for inv in invoices:
            row = {k: v for k, v in inv.items() if k not in ("acct", "clauses")}
            fp = lm.bank_fingerprint(*inv["acct"]) if inv["acct"] else None
            row.update(message_id=f"s{n}{inv['message_id']}", bank_fp=fp or "",
                       bank_last4=inv["acct"][1][-4:] if inv["acct"] else "",
                       singer_email=f"singer{n}@example.com",
                       notes="; ".join(t for t, _ in inv["clauses"] if t is not None))
            store.append(row)
    return ledger, store


def harvested_notes():
    """Every short string literal in the note-driven test files: each is read as a whole notes field. Most say
    nothing (refs, amounts); the rest are the phrases the pattern readers were built against."""
    out = []
    for name in ("test_check_payments.py", "test_cancel_contract.py", "test_pipeline.py", "state_cases.py"):
        tree = ast.parse(open(os.path.join(ROOT, "tests", name), encoding="utf-8").read())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str) and 3 <= len(node.value) <= 200
                    and "\n" not in node.value and re.search(r"[a-z]", node.value) and node.value not in out):
                out.append(node.value)
    return out


def facts_map(events, subject, today):
    idx = ev.index(events, today)
    return {i: ev.Facts(subject, es) for (s, i), es in idx.items() if s == subject}


def by_clause(proposals):
    out = {}
    for p in proposals:
        out.setdefault(p["note"], []).append((p["kind"], p["fields"]))
    return out


# --- what the migration proposes ----------------------------------------------------------------------------------

def test_each_booking_case_migrates_to_the_facts_its_clauses_are_worth():
    for n, (name, value, invoice, event, clauses, paid, today) in enumerate(BOOKING_CASES):
        r = booking(f"C{n}", "; ".join(t for t, _ in clauses), value, invoice, event)
        got = by_clause(mig.booking_proposals(r, today, ev.Facts("booking"))[0])
        for text, facts in clauses:
            want = sorted((k, fl) for k, fl, _, _ in ([] if facts is None else facts if isinstance(facts, list) else [facts]))
            assert sorted(got.get(ev.note_hash(text), [])) == want, (name, text, got.get(ev.note_hash(text)), want)


def test_each_singer_case_migrates_to_the_facts_its_clauses_are_worth():
    ledger, store = case_rows()
    for n, (name, invoices, today) in enumerate(SINGER_CASES):
        for inv in invoices:
            r = next(s for s in store if s["message_id"] == f"s{n}{inv['message_id']}")
            got = by_clause(mig.invoice_proposals(r, today, ev.Facts("singer_invoice"))[0])
            for text, fact in inv["clauses"]:
                if text is None:
                    continue
                want = [] if fact is None else [(fact[0], dict(fact[1], fp8=r["bank_fp"][:8]) if fact[1].get("fp8") == "*"
                                                  else fact[1])]
                assert got.get(ev.note_hash(text), []) == want, (name, text, got.get(ev.note_hash(text)), want)


def test_dated_clauses_keep_their_dates_and_undated_ones_are_flagged():
    r = booking("2111", "deposit seen 2026-09-04 (Starling); Cancelled 20 Sep; reinstated 2026-09-15; "
                        "paid in full 2026-09-10", invoice="2026-09-02")
    props, flags = mig.booking_proposals(r, T, ev.Facts("booking"))
    got = [(p["kind"], p["on"], p["flags"]) for p in props]
    assert got[0] == ("deposit-seen", "2026-09-04", []), got
    assert got[1] == ("cancelled", "2026-09-04", ["undated"]), got  # the fact before it in the same notes
    assert got[2] == ("reinstated", "2026-09-15", []), got
    assert got[3] == ("paid-in-full", "2026-09-10", ["out of order", "writer unknown"]), got  # its own date kept
    r = booking("2112", "Cancelled 20 Sep", invoice="2026-09-02")
    assert [(p["on"], p["flags"]) for p in mig.booking_proposals(r, T, ev.Facts("booking"))[0]] == \
        [("2026-09-02", ["undated"])]  # nothing before it: the invoice date


def test_a_cancellation_dated_before_the_fact_it_follows_is_raised_so_the_order_holds():
    r = booking("2111", "cancelled 2026-09-20; reinstated 2026-09-10")  # typed out of order: reinstated is the later
    props = mig.booking_proposals(r, T, ev.Facts("booking"))[0]
    assert [(p["kind"], p["on"], p["flags"]) for p in props] == [
        ("cancelled", "2026-09-20", []), ("reinstated", "2026-09-20", ["out of order"])], props
    facts = ev.booking_facts("2111", T, events=mig.proposed_events(props))
    assert cp.is_cancelled(r, facts=ev.Facts("booking")) is False and facts.cancelled is False


def test_future_dated_facts_are_left_out_and_reported():
    r = booking("2111", "short by fees £12.40 accepted 2026-12-01 (owner); deposit kept 2026-12-01")
    props, flags = mig.booking_proposals(r, T, ev.Facts("booking"))
    assert props == [], props
    assert all("dated after today" in f for f in flags) and len(flags) == 2, flags


def test_paid_in_full_basis_follows_its_writer():
    props = mig.booking_proposals(booking("2111", "paid in full 2026-09-20 (owner)"), T, ev.Facts("booking"))[0]
    assert [(p["kind"], p["fields"], p["by"], p["flags"]) for p in props] == [
        ("paid-in-full", {"basis": "owner"}, "owner", [])], props
    props = mig.booking_proposals(booking("2111", "paid in full 2026-09-20"), T, ev.Facts("booking"))[0]
    assert [(p["fields"], p["by"], p["flags"]) for p in props] == [({"basis": "bank"}, "script", ["writer unknown"])]


def test_owner_kinds_are_the_owners_and_the_rest_the_scripts():
    notes = ("cancelled 2026-09-15; deposit kept 2026-09-16; refunded 2026-09-17; payment checked 2026-09-18; "
             "reinstated 2026-09-19; balance to be paid in cash; reminder drafted 2026-09-20")
    props = mig.booking_proposals(booking("2111", notes), T, ev.Facts("booking"))[0]
    assert {p["kind"]: p["by"] for p in props} == {
        "cancelled": "script", "deposit-kept": "owner", "refunded": "owner", "payment-checked": "owner",
        "reinstated": "owner", "arranged": "script", "reminder-drafted": "script"}, props


def test_derived_eids_follow_the_spec_and_a_repeated_clause_is_one_fact():
    props = mig.booking_proposals(booking("2111", "receipt drafted; receipt drafted"), T, ev.Facts("booking"))[0]
    assert len(props) == 1, props
    p = props[0]
    want = hashlib.sha256(f"migration|booking|2111|{p['kind']}|{p['on']}|{p['note']}".encode()).hexdigest()[:16]
    assert p["eid"] == want


def test_a_family_already_recorded_is_skipped():
    ev.clear_cache()
    have = ev.booking_facts("2111", T, events=[ev.validate({
        "v": 1, "eid": "a" * 16, "prev": "", "at": "2026-09-20T10:00:00Z", "on": "2026-09-20", "subject": "booking",
        "id": "2111", "kind": "cancelled", "fields": {}, "by": "script", "src": "live"})])
    props = mig.booking_proposals(booking("2111", "cancelled 2026-09-15; reinstated 2026-09-19; paid in full 2026-09-20"),
                                  T, have)[0]
    assert [p["kind"] for p in props] == ["paid-in-full"], props


def test_a_bad_ref_or_message_id_is_reported_not_migrated():
    props, flags = mig.booking_proposals(booking("ann@example.com", "cancelled 2026-09-15"), T, ev.Facts("booking"))
    assert props == [] and flags and "ann" not in " ".join(flags), flags
    r = {"message_id": "<a@b>", "received": "2026-09-01", "bank_fp": "", "notes": "withdrawn 2026-09-15 (not-ours)",
         "withdrawn": "2026-09-15"}
    props, flags = mig.invoice_proposals(r, T, ev.Facts("singer_invoice"))
    assert props == [] and flags and "@" not in " ".join(flags), flags


# --- compare -------------------------------------------------------------------------------------------------------

def test_compare_finds_no_difference_on_every_case_and_every_note_in_the_tests():
    ledger, store = case_rows()
    for n, notes in enumerate(harvested_notes()):
        for value, invoice, event in ((1150, "2026-09-01", "2026-12-12"), (650, "2026-08-22", "2026-09-30")):
            ledger.append(booking(f"H{n}x{value}", notes, value, invoice, event))
    plan = mig.plan(ledger, store, T, [])
    assert len(plan["proposals"]) > 150, len(plan["proposals"])
    diffs = mig.compare(ledger, store, T, mig.proposed_events(plan["proposals"]))
    assert diffs == [], "\n".join(diffs[:40])


def test_compare_names_a_family_that_reads_differently():
    r = booking("2111", "cancelled 2026-09-15")
    reinstated = ev.validate({"v": 1, "eid": "b" * 16, "prev": "", "at": "2026-09-20T10:00:00Z", "on": "2026-09-20",
                              "subject": "booking", "id": "2111", "kind": "reinstated", "fields": {}, "by": "owner",
                              "src": "live"})
    diffs = mig.compare([r], [], T, [reinstated])
    assert any(d.startswith("booking 2111 cancellation: True → False") for d in diffs), diffs
    assert all("cancelled 2026" not in d for d in diffs), "no note text"


def test_the_proposed_events_are_valid_log_lines():
    ledger, store = case_rows()
    events = mig.proposed_events(mig.plan(ledger, store, T, [])["proposals"])
    for e in events:
        ev.dumps(ev.validate(e, write=True))
        assert e["src"] == "migration" and e["note"], e


# --- the command line ------------------------------------------------------------------------------------------------

def fresh(ledger=None, store=None):
    d = tempfile.mkdtemp()
    os.chmod(d, 0o700)
    for name, rows, cols in (("bookings.csv", ledger, LEDGER_COLS), ("singer-invoices.csv", store, si.COLUMNS)):
        if rows is not None:
            with open(os.path.join(d, name), "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
    return d


def run(d, *args, stdin_text=None, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "LCS_BOOKINGS_CSV"}
    env["LCS_PRIVATE_DIR"] = d
    env.update(env_extra or {})
    kw = {"input": stdin_text} if stdin_text is not None else {"stdin": subprocess.DEVNULL}
    p = subprocess.run([PY, SCRIPT, *args], env=env, capture_output=True, text=True, timeout=60, **kw)
    return p.returncode, p.stdout + p.stderr


def nonce_file(d):
    cc = os.path.join(d, "command-centre")
    os.makedirs(cc, mode=0o700, exist_ok=True)
    fd = os.open(os.path.join(cc, "owner-nonce"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(hashlib.sha256(NONCE.encode()).hexdigest())


def sha_of(out):
    m = re.search(r"^sha256: ([0-9a-f]{64})$", out, re.M)
    assert m, out
    return m.group(1)


def listing(d):
    return sorted(os.path.relpath(os.path.join(a, f), d) for a, _, fs in os.walk(d) for f in fs)


def sample():
    ledger = [booking("2111", "deposit seen 2026-09-04 (Starling); Cancelled 20 Sep"),
              booking("2112", "PENDING: invoiced; rest will be paid by the father"),
              booking("2113", "paid in full 2026-09-20 (owner); review request drafted 2026-09-25")]
    fp = lm.bank_fingerprint("123456", "11112222")
    store = [{"message_id": "1759000000000000001", "received": "2026-09-01", "singer_name": "Ben Fenwick",
              "singer_email": "ben@example.com", "amount_gbp": "100.00", "bank_fp": fp, "bank_last4": "2222",
              "bank_changed": "yes", "bank_confirmed": "yes", "paid_on": "", "withdrawn": "",
              "notes": "BANK DETAILS CHANGED since their last invoice (was ••••9999, now ••••2222): ring them before "
                       "paying; bank details confirmed by phone 2026-09-12"}]
    return ledger, store


def test_the_dry_run_writes_only_its_report():
    ledger, store = sample()
    d = fresh(ledger, store)
    before = listing(d)
    code, out = run(d, "migrate")
    assert code == 0, out
    today = lm.today().isoformat()
    report = os.path.join(d, f"events-migration-{today}.txt")
    assert listing(d) == sorted(before + [f"events-migration-{today}.txt"]), listing(d)
    assert os.stat(report).st_mode & 0o777 == 0o600
    text = open(report, encoding="utf-8").read()
    assert hashlib.sha256(text.encode()).hexdigest() == sha_of(out)
    assert "booking 2111 cancelled" in text and "singer_invoice 1759000000000000001 bank-confirmed" in text, text
    for secret in ("Ann", "Smith", "Ben", "father", "Cancelled 20 Sep", "ring them", "••••", "example.com"):
        assert secret not in text and secret not in out, secret
    assert re.search(r"^totals: \d+ events", text, re.M), text


def test_apply_needs_the_nonce_and_the_dry_runs_hash():
    ledger, store = sample()
    d = fresh(ledger, store)
    code, out = run(d, "migrate")
    sha = sha_of(out)
    code, out = run(d, "migrate", "--apply", "--expect", sha, "--owner")  # no nonce
    assert code != 0 and "nothing written" in out and not os.path.exists(os.path.join(d, "events.jsonl")), out
    code, out = run(d, "migrate", "--apply", "--expect", sha)  # no --owner
    assert code != 0 and not os.path.exists(os.path.join(d, "events.jsonl")), out
    nonce_file(d)
    code, out = run(d, "migrate", "--apply", "--expect", "0" * 64, "--owner", stdin_text=NONCE + "\n")
    assert code != 0 and "changed since" in out and not os.path.exists(os.path.join(d, "events.jsonl")), out
    nonce_file(d)
    code, out = run(d, "migrate", "--apply", "--expect", sha, "--owner", stdin_text=NONCE + "\n",
                    env_extra={"LCS_BOOKINGS_CSV": os.path.join(d, "bookings.csv")})
    assert code != 0 and "LCS_BOOKINGS_CSV" in out and not os.path.exists(os.path.join(d, "events.jsonl")), out


def test_apply_writes_the_events_once_and_a_second_apply_adds_nothing():
    ledger, store = sample()
    d = fresh(ledger, store)
    code, out = run(d, "migrate")
    total = int(re.search(r"(\d+) events proposed", out).group(1))
    nonce_file(d)
    code, out = run(d, "migrate", "--apply", "--expect", sha_of(out), "--owner", stdin_text=NONCE + "\n")
    assert code == 0 and f"{total} new events" in out, out
    log = os.path.join(d, "events.jsonl")
    first = open(log, "rb").read()
    assert os.stat(log).st_mode & 0o777 == 0o600 and first.count(b"\n") == total, total
    assert b'"src":"migration"' in first and b"Ann" not in first and b"Ben" not in first
    code, out = run(d, "verify")
    assert code == 0 and "chain whole" in out, out
    code, out = run(d, "compare")
    assert code == 0 and "no difference" in out, out
    code, out = run(d, "migrate")
    assert "0 events proposed" in out, out
    nonce_file(d)
    code, out = run(d, "migrate", "--apply", "--expect", sha_of(out), "--owner", stdin_text=NONCE + "\n")
    assert code == 0 and "0 new events" in out, out
    assert open(log, "rb").read() == first


def test_renaming_the_log_gives_the_notes_reading_back():
    ledger, store = sample()
    d = fresh(ledger, store)
    code, out = run(d, "migrate")
    nonce_file(d)
    run(d, "migrate", "--apply", "--expect", sha_of(out), "--owner", stdin_text=NONCE + "\n")
    saved = os.environ["LCS_PRIVATE_DIR"]
    os.environ["LCS_PRIVATE_DIR"] = d
    try:
        ev.clear_cache()
        with_log = ev.booking_facts("2111", T)
        assert with_log.has("cancellation") and with_log.cancelled
        os.rename(os.path.join(d, "events.jsonl"), os.path.join(d, "events.jsonl.old"))
        ev.clear_cache()
        assert not ev.booking_facts("2111", T).families
        assert cp.is_cancelled(ledger[0])  # the notes say the same
    finally:
        os.environ["LCS_PRIVATE_DIR"] = saved
        ev.clear_cache()


def in_home(ledger, store):
    """The sample ledger and store in this process's private folder (cp.LEDGER, si.STORE), with no log."""
    for name, rows, cols in (("bookings.csv", ledger, LEDGER_COLS), ("singer-invoices.csv", store, si.COLUMNS)):
        with open(os.path.join(_HOME, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
    for name in ("events.jsonl", "events.jsonl.lock"):
        if os.path.exists(os.path.join(_HOME, name)):
            os.remove(os.path.join(_HOME, name))
    ev.clear_cache()


def main_out(argv):
    import contextlib, io
    import events
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = events.main(argv)
    except SystemExit as e:
        return str(e), buf.getvalue()
    ev.clear_cache()
    return code, buf.getvalue()


def test_a_migration_that_stops_part_way_withdraws_what_it_wrote_and_runs_again():
    in_home(*sample())
    _, out = main_out(["migrate"])
    total = int(re.search(r"(\d+) events proposed", out).group(1))
    real_write, calls = ev._write, []

    def failing(fd, data):
        calls.append(1)
        if len(calls) == 3:
            raise OSError("disk full")
        return real_write(fd, data)
    saved = (lcs_owner.owner_confirmed, lcs_owner._PROVEN)
    lcs_owner.owner_confirmed, lcs_owner._PROVEN = (lambda *a: True), True
    try:
        ev._write = failing
        msg, _ = main_out(["migrate", "--apply", "--expect", sha_of(out), "--owner"])
        ev._write = real_write
        assert "withdrawn" in msg and "nothing written" in msg and "run it again" in msg, msg
        events, stats = ev.read()
        assert [e["kind"] for e in events] == [events[0]["kind"], events[1]["kind"], "retract", "retract"], events
        assert not ev.migration_applied()
        _, out = main_out(["migrate"])
        assert f"{total} events proposed" in out, out
        code, out2 = main_out(["migrate", "--apply", "--expect", sha_of(out), "--owner"])
        assert code == 0 and f"{total} new events" in out2, (code, out2)
    finally:
        ev._write = real_write
        lcs_owner.owner_confirmed, lcs_owner._PROVEN = saved
    events, stats = ev.read()
    assert stats["skipped"] == 0 and stats["chain_ok"] and len(events) == 4 + total, stats
    assert ev.migration_applied()
    ledger, store = lm.read_csv(cp.LEDGER), lm.read_csv(si.STORE)
    assert mig.compare(ledger, store, lm.today(), events) == []


def test_a_fact_dated_after_today_stops_the_apply_naming_its_row():
    """A clause dated after today can't become a fact yet (the readers ignore it until that day, then the notes and
    the facts would disagree): the apply refuses, naming the ref, kind and date, until the note is corrected."""
    ledger, store = sample()
    ledger.append(booking("2114", "short by fees £12.40 accepted 2027-01-05 (owner)"))
    plan = mig.plan(ledger, store, T, [])
    assert plan["future"] == ["booking 2114 fees-accepted (2027-01-05)"], plan["future"]
    d = fresh(ledger, store)
    code, out = run(d, "migrate")
    assert "dated after today: booking 2114 fees-accepted (2027-01-05)" in out, out
    nonce_file(d)
    code, out = run(d, "migrate", "--apply", "--expect", sha_of(out), "--owner", stdin_text=NONCE + "\n")
    assert code != 0 and "booking 2114 fees-accepted (2027-01-05)" in out and "nothing written" in out, out
    assert not os.path.exists(os.path.join(d, "events.jsonl"))


def test_compare_proposed_and_compare_exit_1_on_a_difference():
    ledger, store = sample()
    d = fresh(ledger, store)
    code, out = run(d, "compare", "--proposed")
    assert code == 0 and "no difference" in out, out
    saved = os.environ["LCS_PRIVATE_DIR"]
    os.environ["LCS_PRIVATE_DIR"] = d
    try:
        ev.clear_cache()
        lcs_owner._PROVEN = True
        ev.append("booking", "2111", "reinstated", {}, "owner", on="2026-09-25")
    finally:
        lcs_owner._PROVEN = False
        os.environ["LCS_PRIVATE_DIR"] = saved
        ev.clear_cache()
    code, out = run(d, "compare")
    assert code == 1 and "booking 2111 cancellation" in out, out


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:  # an error is a failure too
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
