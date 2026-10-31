#!/usr/bin/env python3
"""Tests for scripts/bookings/books_sync.py (the local Books cache and the Books guard's snapshot) and
scripts/bookings/books_cache.py (its reader). Stdlib only, a temp private dir, a fake Books runner: no server is
started. .venv/bin/python tests/test_books_sync.py"""
import contextlib, datetime, io, json, os, stat, subprocess, sys, tempfile
from pathlib import Path

TMP = tempfile.mkdtemp()
PRIVATE = Path(TMP) / "private"  # made by the first sync, so its folder mode is the script's
os.environ["LCS_PRIVATE_DIR"] = str(PRIVATE)
os.environ["LCS_BOOKINGS_CSV"] = str(PRIVATE / "ledger.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import books_sync  # noqa: E402
import books_cache  # noqa: E402

SCRIPT = Path(ROOT) / "scripts" / "bookings" / "books_sync.py"
CACHE = PRIVATE / "books-cache.json"
GUARD = PRIVATE / "books-guard.json"
NOW = datetime.datetime(2026, 9, 28, 9, 30, tzinfo=books_sync.LONDON)
READS = {("zoho-books-invoices", "ZohoBooks_list_invoices"), ("zoho-books", "ZohoBooks_list_bills")}

INVOICES = [
    {"invoice_number": "2111", "status": "sent", "date": "2026-09-20", "due_date": "2026-10-05", "total": 1150,
     "balance": 1150, "customer_name": "Mrs Harriet Example-Smith", "email": "h@example.com", "invoice_id": "1"},
    {"invoice_number": "2109", "status": "overdue", "date": "2026-09-01", "due_date": "2026-09-10", "total": 450.0,
     "balance": 225.5, "customer_name": "Tom Other", "invoice_id": "2"},
    {"invoice_number": "2201", "status": "draft", "date": "2026-09-27", "due_date": "", "total": 600,
     "balance": 600, "customer_name": "Draft Person"},
    {"invoice_number": "2001", "status": "paid", "date": "2026-08-01", "due_date": "2026-08-10", "total": 800,
     "balance": 0, "customer_name": "Paid Person"},
]
BILLS = [
    {"bill_number": "INV-7", "vendor_name": "Ben Fenwick", "status": "open", "total": 180, "balance": 180,
     "date": "2026-09-22", "due_date": "2026-10-22"},
    {"bill_number": "SI-12345", "vendor_name": "Anna Singer", "status": "overdue", "total": 150, "balance": 150,
     "date": "2026-09-01"},
    {"bill_number": "B3", "vendor_name": "Carl Paid", "status": "paid", "total": 90, "balance": 0, "date": "2026-08-01"},
]


class McpError(Exception):
    """Stands in for the client's own error: only its type name may be printed."""


class FakeBooks:
    """Stands in for the read client's call_tool; only the two Books list tools are ever asked for."""
    def __init__(self, invoices=INVOICES, bills=BILLS, per_page=None, fail=None):
        self.calls, self.invoices, self.bills, self.per_page, self.fail = [], invoices, bills, per_page, fail

    def __call__(self, server, tool, arguments):
        self.calls.append((server, tool, arguments))
        assert (server, tool) in READS, (server, tool)
        if self.fail:
            raise self.fail
        key, rows = ("invoices", self.invoices) if tool == "ZohoBooks_list_invoices" else ("bills", self.bills)
        page = arguments["query_params"]["page"]
        size = self.per_page or len(rows) or 1
        chunk = rows[(page - 1) * size: page * size]
        return json.dumps({"code": 0, key: chunk, "page_context": {"page": page, "has_more_page": page * size < len(rows)}})


def run(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*a, **kw)
    return code, buf.getvalue()


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def clear():
    for p in (PRIVATE.glob("*") if PRIVATE.exists() else []):
        p.unlink()


def test_books_cache_shape_and_totals():
    clear()
    fake = FakeBooks()
    code, out = run(books_sync.sync, fake, NOW)
    assert code == 0 and out.startswith("books: 4 invoices, 3 bills cached"), out
    data = json.loads(CACHE.read_text())
    assert data["generated_at"] == "2026-09-28T09:30:00+01:00"
    assert set(data) == {"generated_at", "invoices", "bills", "bills_read", "totals"} and data["bills_read"] is True
    inv = {i["number"]: i for i in data["invoices"]}
    assert inv["2111"] == {"number": "2111", "status": "sent", "date": "2026-09-20", "due_date": "2026-10-05",
                           "total": 1150.0, "balance": 1150.0, "customer": "Harriet"}, inv["2111"]
    assert data["bills"][0] == {"number": "INV-7", "vendor": "Ben", "status": "open", "total": 180.0,
                                "balance": 180.0, "date": "2026-09-22"}
    assert data["totals"] == {"receivables": 1375.5, "receivables_count": 2, "overdue": 225.5, "overdue_count": 1,
                              "unpaid_bills": 330.0, "unpaid_bills_count": 2}, data["totals"]
    raw = CACHE.read_text()
    for private in ("Example-Smith", "h@example.com", "Fenwick", "invoice_id"):
        assert private not in raw, private
    assert mode(CACHE) == 0o600 and mode(PRIVATE) == 0o700
    assert {(s, t) for s, t, _ in fake.calls} == READS
    assert all(a["query_params"]["organization_id"] == "941014440" for _, _, a in fake.calls)


def test_the_wrapped_reply_is_read():
    """Since 30 Oct 2026 the server wraps its reply as {"data": {…}, "headers": …, "status": "success"}."""
    class Wrapped(FakeBooks):
        def __call__(self, server, tool, arguments):
            inner = json.loads(super().__call__(server, tool, arguments))
            return json.dumps({"data": inner, "headers": {"content-type": "application/json"}, "status": "success"})
    clear()
    code, out = run(books_sync.sync, Wrapped(), NOW)
    assert code == 0 and out.startswith("books: 4 invoices, 3 bills cached"), out
    rows, more = books_sync.parse_page(json.dumps({"data": {"invoices": [{"a": 1}]}, "status": "success"}), "invoices")
    assert rows == [{"a": 1}] and more is False
    for bad in ({"data": {"invoices": []}, "status": "failure"}, {"data": {"code": 57}, "status": "success"}):
        try:
            books_sync.parse_page(json.dumps(bad), "invoices")
        except ValueError:
            continue
        raise AssertionError(bad)


def test_books_also_writes_the_guards_id_snapshot():
    """books-guard.json (owner hands-off, 14 Oct 2026): the ids the Books guard checks updates and payments against,
    beside the cache, never in it, and with no names or emails."""
    clear()
    invoices = [dict(INVOICES[0], invoice_id="1534218000000100020", customer_id="1534218000000100010"),
                dict(INVOICES[1], invoice_id="2", customer_id="1534218000000100011")]  # a short id is left out
    code, _ = run(books_sync.sync, FakeBooks(invoices=invoices), NOW)
    assert code == 0
    data = json.loads(GUARD.read_text())
    assert data == {"generated_at": "2026-09-28T09:30:00+01:00", "invoices": [
        {"invoice_id": "1534218000000100020", "customer_id": "1534218000000100010", "number": "2111",
         "status": "sent", "balance": 1150.0, "total": 1150.0}]}, data
    for private in ("Harriet", "Example-Smith", "h@example.com"):
        assert private not in GUARD.read_text(), private
    assert mode(GUARD) == 0o600
    assert "invoice_id" not in CACHE.read_text()


def test_the_guard_reads_the_snapshot_this_writes():
    """The Books guard's own reader takes the file books_sync writes (path, shape and freshness)."""
    import importlib.util
    clear()
    invoices = [dict(INVOICES[0], invoice_id="1534218000000100020", customer_id="1534218000000100010")]
    run(books_sync.sync, FakeBooks(invoices=invoices), None)  # stamped now: the guard wants it under an hour old
    spec = importlib.util.spec_from_file_location("zbg", os.path.join(ROOT, ".claude", "hooks", "zoho_books_guard.py"))
    zbg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(zbg)
    found = zbg._books_invoice("1534218000000100020")
    assert found["number"] == "2111" and found["status"] == "sent", found


def test_books_without_bills_on_the_free_plan_still_caches_the_invoices():
    clear()
    fake = FakeBooks()

    def call(server, tool, args):
        if tool == "ZohoBooks_list_bills":
            raise McpError("this feature is not available in your plan")
        return fake(server, tool, args)
    code, out = run(books_sync.sync, call, NOW)
    assert code == 0 and out.startswith("books: 4 invoices, no bills (not on this Books plan) cached"), out
    assert "unpaid bills" not in out, out
    data = json.loads(CACHE.read_text())
    assert data["bills_read"] is False and data["bills"] == [] and len(data["invoices"]) == 4
    assert data["totals"]["receivables"] == 1375.5 and data["totals"]["unpaid_bills"] == 0


def test_books_pages_through():
    clear()
    fake = FakeBooks(per_page=1)
    code, out = run(books_sync.sync, fake, NOW)
    assert code == 0 and "4 invoices, 3 bills" in out, out
    assert len(fake.calls) == 7


def test_books_failure_keeps_the_old_cache_and_prints_the_type_only():
    clear()
    run(books_sync.sync, FakeBooks(), NOW)
    before, guard_before = CACHE.read_text(), GUARD.read_text()
    for fail in (McpError("zoho-books: https://secret.example/abc failed"), TimeoutError("h@example.com")):
        code, out = run(books_sync.sync, FakeBooks(fail=fail), NOW)
        assert code == 1, code  # non-zero, so a scheduled run sees the failure
        assert out.strip() == f"books: not updated ({type(fail).__name__}); the last cache is kept", out
    code, out = run(books_sync.sync, lambda *a: "not json", NOW)
    assert code == 1 and out.strip() == "books: not updated (JSONDecodeError); the last cache is kept", out
    code, out = run(books_sync.sync, lambda *a: json.dumps({"code": 0}), NOW)
    assert "(ValueError)" in out and code == 1
    assert CACHE.read_text() == before and GUARD.read_text() == guard_before
    assert sorted(p.name for p in PRIVATE.iterdir()) == ["books-cache.json", "books-guard.json"]  # no temp file left


def test_as_a_subprocess_exits_1_on_failure_without_starting_a_server():
    """With no MCP settings at all the read client raises before starting anything: exit 1, nothing written."""
    clear()
    env = dict(os.environ, LCS_PRIVATE_DIR=str(PRIVATE), LCS_CLAUDE_JSON=str(Path(TMP) / "absent-settings"))
    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env,
                          stdin=subprocess.DEVNULL, timeout=60)
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert proc.stdout.strip() == "books: not updated (McpError); the last cache is kept", proc.stdout
    assert not CACHE.exists() and not GUARD.exists()


def test_main_takes_no_arguments():
    code, out = run(books_sync.main, ["books"])
    assert code == 2 and "no arguments" in out, out
    code, out = run(books_sync.main, ["--help"])
    assert code == 0 and "usage" in out, out


def test_first_name():
    assert books_sync.first_name("Mrs Harriet Example-Smith") == "Harriet"
    assert books_sync.first_name("Dr. Jo Bloggs") == "Jo"
    assert books_sync.first_name("") == "" and books_sync.first_name(None) == ""
    assert books_sync.first_name("St Mary's Church") == "St"


def test_books_cache_reader():
    clear()
    assert books_cache.books_path() == CACHE
    assert books_cache.books_cache() is None
    run(books_sync.sync, FakeBooks(), NOW)
    assert books_cache.books_cache()["totals"]["overdue"] == 225.5
    CACHE.write_text("[]")
    try:
        books_cache.books_cache()
        raise AssertionError("no ValueError")
    except ValueError:
        pass


def test_the_readers_use_the_same_cache():
    """check_payments and singer_invoices read the file books_sync writes."""
    import check_payments as cp
    import singer_invoices as si
    clear()
    run(books_sync.sync, FakeBooks(), NOW)
    assert Path(cp.books_cache()) == CACHE and Path(si.books_cache_path()) == CACHE
    assert cp.unsent_invoices() == {"2201"} and cp.books_open_balances() == {"2111": 1150.0, "2109": 225.5}
    assert [b["number"] for b in si.read_books_bills()] == ["INV-7", "SI-12345", "B3"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
