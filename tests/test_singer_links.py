#!/usr/bin/env python3
"""Singer invoices linked to ledger bookings, and the per-event margin (roadmap R18): singer_invoices.py link,
the auto-link at scan and rescan, margins() and `margins`. Stdlib only, temp private dir and ledger, no network
(the fetch is faked). .venv/bin/python tests/test_singer_links.py"""
import contextlib, csv, io, os, sys, tempfile
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "ledger.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_money as lm
import singer_invoices as si

assert str(lm.LEDGER).startswith(TMP) and str(si.STORE).startswith(TMP)

LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "value_gbp", "notes"]
BANK = "\nSort code 12-34-56\nAccount number 12345678"
ARGS = ["--received", "2026-09-25", "--sender-email", "ben@example.com", "--sender-name", "Ben Fenwick"]


def ledger(rows):
    with open(lm.LEDGER, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in LEDGER_COLS})


def booking(ref, event, value="1150", notes=""):
    return {"booking_ref": ref, "invoice_date": "2026-09-01", "event_date": event, "client_name": "A Client",
            "value_gbp": value, "notes": notes}


def fresh():
    for p in (si.STORE, lm.LEDGER):
        if Path(p).exists():
            Path(p).unlink()


def raw_mime(body):
    return f"From: Ben Fenwick <ben@example.com>\nSubject: Invoice\nContent-Type: text/plain; charset=utf-8\n\n{body}"


@contextlib.contextmanager
def fake_fetch(texts):
    saved = si.fetch_raw
    si.fetch_raw = lambda mid: texts[mid]
    try:
        yield
    finally:
        si.fetch_raw = saved


def run_main(argv):
    saved = (lm.keychain_token, sys.argv)
    lm.keychain_token = lambda: None  # no Starling in tests
    buf = io.StringIO()
    try:
        sys.argv = ["singer_invoices.py", *argv]
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            try:
                si.main()
            except SystemExit as e:
                if e.code not in (None, 0):
                    buf.write(f"EXIT {e.code}\n")
    finally:
        lm.keychain_token, sys.argv = saved
    return buf.getvalue()


def scan(mid, body):
    with fake_fetch({mid: raw_mime(body)}):
        return run_main(["scan", "--fetch", "--message-id", mid, *ARGS])


def stored(mid):
    return next(r for r in lm.read_csv(si.STORE) if r["message_id"] == mid)


# ---------------------------------------------------------------- dates


def test_mentioned_dates_shapes():
    got = si.mentioned_dates("Funeral 21 September £100\nDate: 25/09/2026\nWedding 2026-11-21, "
                             "Sat 3rd Oct 2026, December 5, 2026, 7.12.26, 31/02/2026, sort 12-34-56")
    assert got == [(2026, 11, 21), (2026, 9, 25), (2026, 12, 7), (None, 9, 21), (2026, 10, 3), (2026, 12, 5)], got


def test_auto_link_needs_exactly_one_booking():
    rows = [booking("2109", "2026-09-21"), booking("2111", "2026-11-21"), booking("2111A", "2026-11-21")]
    assert si.auto_link([(None, 9, 21)], rows, "2026-09-25") == "2109"
    assert si.auto_link([(2026, 9, 21)], rows) == "2109"
    assert si.auto_link([(2026, 11, 21)], rows) == ""  # two bookings that day
    assert si.auto_link([(2026, 9, 21), (2026, 11, 21)], rows) == ""  # dates point to three bookings
    assert si.auto_link([(2025, 9, 21)], rows) == ""  # wrong year
    assert si.auto_link([(None, 9, 21)], rows, "2027-09-25") == ""  # a year-less date far from the event
    assert si.auto_link([], rows) == ""


# ---------------------------------------------------------------- scan, rescan, link


def test_scan_links_when_one_booking_has_the_date():
    fresh()
    ledger([booking("2109", "2026-09-21"), booking("2111", "2026-11-21")])
    out = scan("301", "Invoice No: 7\nFuneral 21 September\nTotal £100.00" + BANK)
    assert "linked: 2109" in out.splitlines(), out
    lines = out.splitlines()
    assert lines.index("linked: 2109") < min(i for i, l in enumerate(lines) if l.startswith("bill:")), out
    assert stored("301")["booking_ref"] == "2109"
    again = scan("301", "whatever")  # already recorded: the stored link is reprinted
    assert "linked: 2109" in again.splitlines(), again


def test_scan_without_a_unique_date_prints_link_none():
    fresh()
    ledger([booking("2111", "2026-11-21"), booking("2111A", "2026-11-21")])
    out = scan("302", "Invoice No: 8\nWedding 21 November 2026\nTotal £100.00" + BANK)
    assert "link: none" in out.splitlines(), out
    assert stored("302")["booking_ref"] == ""


def test_rescan_links_but_keeps_a_link_already_made():
    fresh()
    ledger([booking("2109", "2026-09-21"), booking("2111", "2026-11-21")])
    scan("303", "Invoice No: 9\nTotal £100.00" + BANK)
    assert stored("303")["booking_ref"] == ""
    with fake_fetch({"303": raw_mime("Invoice No: 9\nWedding 21/11/2026\nTotal £100.00" + BANK)}):
        out = run_main(["rescan", "303", "--fetch"])
    assert "linked: 2111" in out.splitlines(), out
    assert run_main(["link", "303", "2109"]).strip() == "303: linked to 2109 (was 2111)"
    with fake_fetch({"303": raw_mime("Invoice No: 9\nWedding 21/11/2026\nTotal £100.00" + BANK)}):
        out = run_main(["rescan", "303", "--fetch"])
    assert "linked: 2109" in out.splitlines() and stored("303")["booking_ref"] == "2109", out


def test_link_refuses_an_unknown_ref_or_invoice():
    fresh()
    ledger([booking("2109", "2026-09-21")])
    scan("304", "Invoice No: 10\nTotal £100.00" + BANK)
    before = si.STORE.read_text()
    assert "isn't in the bookings ledger" in run_main(["link", "304", "2110"])
    assert "EXIT 2" in run_main(["link", "304", "-x"])  # argparse: never taken as a ref
    assert "not a booking ref" in run_main(["link", "304", "a b"])
    assert "no invoice 999" in run_main(["link", "999", "2109"])
    assert si.STORE.read_text() == before
    assert run_main(["link", "304", "2109"]).strip() == "304: linked to 2109"
    assert stored("304")["booking_ref"] == "2109"
    assert os.stat(si.STORE).st_mode & 0o777 == 0o600


def test_an_old_store_gains_the_column():
    fresh()
    ledger([booking("2109", "2026-09-21")])
    old = [c for c in si.COLUMNS if c != "booking_ref"]
    with open(si.STORE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old)
        w.writeheader()
        w.writerow({c: "" for c in old} | {"message_id": "305", "amount_gbp": "90.00", "received": "2026-09-20"})
    assert run_main(["link", "305", "2109"]).strip() == "305: linked to 2109"
    assert stored("305")["booking_ref"] == "2109" and stored("305")["amount_gbp"] == "90.00"


# ---------------------------------------------------------------- margins


def test_margins_pure():
    ledger_rows = [booking("2111", "2026-11-21", "1150"), booking("2109", "2026-09-21", "450"),
                   booking("2201", "2026-12-01", "0"), booking("2202", "2026-12-02", "575", "cancelled 2026-10-01")]
    singer_rows = [{"booking_ref": "2111", "amount_gbp": "180.00", "withdrawn": ""},
                   {"booking_ref": "2111", "amount_gbp": "200.50", "withdrawn": ""},
                   {"booking_ref": "2111", "amount_gbp": "999.00", "withdrawn": "2026-10-02"},
                   {"booking_ref": "", "amount_gbp": "50.00", "withdrawn": ""}]
    got = {m["ref"]: m for m in si.margins(ledger_rows, singer_rows)}
    assert [m["ref"] for m in si.margins(ledger_rows, singer_rows)] == ["2109", "2111", "2201", "2202"]
    m = got["2111"]
    assert (m["fee"], m["costs"], m["invoices"], m["margin"], m["margin_pct"]) == (1150.0, 380.5, 2, 769.5, 66.9), m
    assert got["2109"]["costs"] == 0 and got["2109"]["margin_pct"] == 100.0
    assert got["2201"]["margin_pct"] is None
    assert got["2202"]["cancelled"] is True and got["2111"]["cancelled"] is False


def test_margins_command():
    fresh()
    ledger([booking("2111", "2026-11-21", "1150")])
    scan("306", "Invoice No: 11\nWedding 21 November 2026\nTotal £180.00" + BANK)
    scan("307", "Invoice No: 12\nTotal £40.00" + BANK)
    out = run_main(["margins"])
    assert "2111 2026-11-21: fee £1,150.00 · singers £180.00 (1 invoice) · margin £970.00 (84.3%)" in out, out
    assert "1 singer invoice not linked to a booking (£40.00)" in out, out
    assert "Ben" not in out and "12345678" not in out


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
