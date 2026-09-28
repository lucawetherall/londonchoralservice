#!/usr/bin/env python3
"""Tests for scripts/reports/cc_sync.py (the Books and calendar caches) and command_centre/books_cache.py.
Stdlib only, a temp private dir, a fake MCP runner: no server is started. .venv/bin/python tests/test_cc_sync.py"""
import contextlib, datetime, io, json, os, stat, sys, tempfile
from pathlib import Path

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "ledger.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
sys.path.insert(0, ROOT)
import cc_sync
import lcs_mcp

CACHE = Path(TMP) / "command-centre" / "cache"
NOW = datetime.datetime(2026, 9, 28, 9, 30, tzinfo=cc_sync.LONDON)

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


class FakeBooks:
    """Stands in for lcs_mcp.call_tool; checks every call against the real allowlist, like the real one."""
    def __init__(self, invoices=INVOICES, bills=BILLS, per_page=None, fail=None):
        self.calls, self.invoices, self.bills, self.per_page, self.fail = [], invoices, bills, per_page, fail

    def __call__(self, server, tool, arguments):
        self.calls.append((server, tool, arguments))
        assert lcs_mcp.is_allowed(server, tool), (server, tool)
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
    for p in CACHE.glob("*"):
        p.unlink()


# ---------------------------------------------------------------- books


def test_books_cache_shape_and_totals():
    clear()
    fake = FakeBooks()
    code, out = run(cc_sync.cmd_books, fake, NOW)
    assert code == 0 and out.startswith("books: 4 invoices, 3 bills cached"), out
    data = json.loads((CACHE / "books.json").read_text())
    assert data["generated_at"] == "2026-09-28T09:30:00+01:00"
    assert set(data) == {"generated_at", "invoices", "bills", "totals"}
    inv = {i["number"]: i for i in data["invoices"]}
    assert inv["2111"] == {"number": "2111", "status": "sent", "date": "2026-09-20", "due_date": "2026-10-05",
                           "total": 1150.0, "balance": 1150.0, "customer": "Harriet"}, inv["2111"]
    assert data["bills"][0] == {"number": "INV-7", "vendor": "Ben", "status": "open", "total": 180.0,
                                "balance": 180.0, "date": "2026-09-22"}
    assert data["totals"] == {"receivables": 1375.5, "receivables_count": 2, "overdue": 225.5, "overdue_count": 1,
                              "unpaid_bills": 330.0, "unpaid_bills_count": 2}, data["totals"]
    raw = (CACHE / "books.json").read_text()
    for private in ("Example-Smith", "h@example.com", "Fenwick", "invoice_id"):
        assert private not in raw, private
    assert mode(CACHE / "books.json") == 0o600 and mode(CACHE) == 0o700 and mode(CACHE.parent) == 0o700
    assert {(s, t) for s, t, _ in fake.calls} == {("zoho-books-invoices", "ZohoBooks_list_invoices"),
                                                  ("zoho-books", "ZohoBooks_list_bills")}
    assert all(a["query_params"]["organization_id"] == "941014440" for _, _, a in fake.calls)


def test_books_pages_through():
    clear()
    fake = FakeBooks(per_page=1)
    code, out = run(cc_sync.cmd_books, fake, NOW)
    assert code == 0 and "4 invoices, 3 bills" in out, out
    assert len(fake.calls) == 7


def test_books_failure_keeps_the_old_cache_and_prints_the_type_only():
    clear()
    run(cc_sync.cmd_books, FakeBooks(), NOW)
    before = (CACHE / "books.json").read_text()
    for fail in (lcs_mcp.McpError("zoho-books: https://secret.example/abc failed"), TimeoutError("h@example.com")):
        code, out = run(cc_sync.cmd_books, FakeBooks(fail=fail), NOW)
        assert code == 0, code
        assert out.strip() == f"books: not updated ({type(fail).__name__}); the last cache is kept", out
    code, out = run(cc_sync.cmd_books, lambda *a: "not json", NOW)
    assert out.strip() == "books: not updated (JSONDecodeError); the last cache is kept", out
    code, out = run(cc_sync.cmd_books, lambda *a: json.dumps({"code": 0}), NOW)
    assert "(ValueError)" in out and code == 0
    assert (CACHE / "books.json").read_text() == before
    assert [p.name for p in CACHE.iterdir()] == ["books.json"]  # no temp file left behind


def test_books_main_uses_the_real_client_path_without_starting_a_server():
    """cc_sync.py books with no MCP settings at all: lcs_mcp raises, the run still exits 0."""
    clear()
    saved = lcs_mcp.CLAUDE_JSON
    lcs_mcp.CLAUDE_JSON = Path(TMP) / "no-such-claude.json"
    try:
        code, out = run(cc_sync.main, ["books"])
    finally:
        lcs_mcp.CLAUDE_JSON = saved
    assert code == 0 and out.strip() == "books: not updated (McpError); the last cache is kept", out
    assert not (CACHE / "books.json").exists()


def test_first_name():
    assert cc_sync.first_name("Mrs Harriet Example-Smith") == "Harriet"
    assert cc_sync.first_name("Dr. Jo Bloggs") == "Jo"
    assert cc_sync.first_name("") == "" and cc_sync.first_name(None) == ""
    assert cc_sync.first_name("St Mary's Church") == "St"


def test_books_cache_reader():
    from command_centre import books_cache
    clear()
    assert books_cache.books_cache() is None
    run(cc_sync.cmd_books, FakeBooks(), NOW)
    assert books_cache.books_cache()["totals"]["overdue"] == 225.5
    (CACHE / "books.json").write_text("[]")
    try:
        books_cache.books_cache()
        raise AssertionError("no ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------- calendar

EVENTS = [
    {"start": "2026-10-03T14:00:00+01:00", "end": "2026-10-03T16:00:00+01:00", "summary": "Wedding, St Mary’s",
     "calendar": "Work"},
    {"start": "2026-10-01", "end": "2026-10-02", "summary": "Day off", "calendar": "Personal"},
]


def test_calendar_put_writes_the_cache_the_app_reads():
    clear()
    code, out = run(cc_sync.cmd_calendar_put, json.dumps(EVENTS))
    assert code == 0 and out.strip() == "calendar: 2 events cached", out
    data = json.loads((CACHE / "calendar.json").read_text())
    assert [e["summary"] for e in data] == ["Day off", "Wedding, St Mary’s"]  # sorted by start
    assert mode(CACHE / "calendar.json") == 0o600
    from command_centre import sources
    entries, _ = sources.calendar_cache()
    assert entries == data


def test_calendar_put_from_stdin_and_file():
    clear()
    code, out = run(cc_sync.cmd_calendar_put, None, None, io.BytesIO(json.dumps(EVENTS[:1]).encode()))
    assert code == 0 and "1 events cached" in out, out
    src = Path(TMP) / "calendar-in.json"
    src.write_text(json.dumps(EVENTS))
    code, out = run(cc_sync.cmd_calendar_put, None, str(src))
    assert code == 0 and "2 events cached" in out, out
    outside = Path(tempfile.mkdtemp()) / "x.json"
    outside.write_text(json.dumps(EVENTS))
    code, out = run(cc_sync.cmd_calendar_put, None, str(outside))
    assert code == 2 and "inside the private folder" in out, out
    link = Path(TMP) / "link.json"
    link.symlink_to(src)
    code, out = run(cc_sync.cmd_calendar_put, None, str(link))
    assert code == 2 and "not a symlink" in out, out


def refused(value, why):
    clear()
    (CACHE.mkdir(parents=True, exist_ok=True), (CACHE / "calendar.json").write_text("[]"))
    text = value if isinstance(value, str) else json.dumps(value)
    code, out = run(cc_sync.cmd_calendar_put, text)
    assert code == 2 and "nothing written" in out and why in out, (value, out)
    assert (CACHE / "calendar.json").read_text() == "[]"


def test_calendar_put_is_strict():
    ok = EVENTS[0]
    refused("not json", "valid JSON")
    refused({"events": []}, "must be a JSON list")
    refused([ok] * 501, "more than 500")
    refused([dict(ok, summary="x" * 121)], "over 120")
    refused([dict(ok, calendar="c" * 41)], "over 40")
    refused([dict(ok, calendar=" ")], "blank")
    refused([dict(ok, start="3 Oct 2026")], "ISO")
    refused([dict(ok, start="2026-10-03T14:00:00")], "ISO")  # no offset
    refused([dict(ok, start="2026-02-30")], "ISO")
    refused([dict(ok, end="2026-10-04")], "both be dates")
    refused([dict(ok, end="2026-10-03T13:00:00+01:00")], "ends before")
    refused([dict(ok, extra=1)], "exactly start, end, summary and calendar")
    refused([{k: v for k, v in ok.items() if k != "calendar"}], "exactly")
    refused([dict(ok, summary=None)], "must be a string")
    refused([dict(ok, summary="a\nb")], "control character")
    refused("[" + ",".join([json.dumps(ok)] * 20000) + "]", "over")
    clear()
    assert run(cc_sync.cmd_calendar_put, json.dumps([ok] * 500))[0] == 0
    assert run(cc_sync.cmd_calendar_put, json.dumps([dict(ok, summary="x" * 120, start="2026-10-03T13:00:00Z")]))[0] == 0
    assert run(cc_sync.cmd_calendar_put, "[]")[1].strip() == "calendar: 0 events cached"


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
