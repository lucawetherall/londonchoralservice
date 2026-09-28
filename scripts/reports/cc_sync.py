#!/usr/bin/env python3
"""Cache writers for the Command Centre: Zoho Books receivables and bills, and the diary.

    .venv/bin/python scripts/reports/cc_sync.py books
    .venv/bin/python scripts/reports/cc_sync.py calendar-put '<one-line JSON list of events>'
    .venv/bin/python scripts/reports/cc_sync.py calendar-put --file <path inside ~/lcs-private>
    <JSON on stdin> | .venv/bin/python scripts/reports/cc_sync.py calendar-put

books reads Zoho Books (organization_id 941014440) through lcs_mcp, which allows only the read tools on the Books
guard's READ_ALLOW list (ZohoBooks_list_invoices on zoho-books-invoices, ZohoBooks_list_bills on zoho-books), and
writes ~/lcs-private/command-centre/cache/books.json: each invoice's number, status, date, due date, total, balance
and the customer's first name only; each bill's number, the vendor's first name, status, total, balance and date;
the totals (receivables, overdue, unpaid bills) and generated_at. On any failure it prints the error's type name
only, keeps the last cache and exits 0, so a scheduled run carries on.

calendar-put takes the diary from the scheduled assistant (Python can't reach the claude.ai Google Calendar
connector): a JSON list of {start, end, summary, calendar}, at most 500 events, start and end ISO dates (all-day,
end exclusive) or ISO datetimes with an offset, summary at most 120 characters, calendar at most 40. Anything else
refuses the whole input and writes nothing. It writes ~/lcs-private/command-centre/cache/calendar.json, the file
command_centre/sources.calendar_cache() reads. The scheduled prompt passes the JSON as one single-quoted argument
(the same shape as assistant_io.py ledger-add): a heredoc or a pipe isn't a plain allowlisted command, and Claude's
Write tool is denied in ~/lcs-private/command-centre/, so --file (any regular file inside ~/lcs-private, never
through a symlink) and stdin are there for hand use.

Both caches are written atomically (a temp file in the same folder, then os.replace) at mode 600, in folders made
mode 700. LCS_PRIVATE_DIR moves the private tree (the tests use a temp dir).
"""

import argparse
import datetime
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "bookings"))
import lcs_mcp  # noqa: E402

ORG = "941014440"
INVOICE_SERVER, BILL_SERVER = "zoho-books-invoices", "zoho-books"
PER_PAGE, MAX_PAGES = 200, 25
LONDON = ZoneInfo("Europe/London")
MAX_EVENTS = 500
MAX_INPUT = 1 << 20  # bytes of calendar JSON
SUMMARY_MAX, CALENDAR_MAX = 120, 40
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})$")
HONORIFICS = {"dr", "mr", "mrs", "ms", "miss", "mx", "prof", "rev", "revd", "the"}
NOT_OPEN_INVOICE = {"draft", "void", "paid"}
NOT_OPEN_BILL = {"void", "paid"}


def private_dir():
    """Read at call time, so the tests (and a moved private tree) never touch ~/lcs-private."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))


def cache_dir():
    return private_dir() / "command-centre" / "cache"


def write_private_json(path, value):
    """`value` as JSON at `path`, mode 600, atomically; the folders are made mode 700 if missing."""
    path = Path(path)
    missing = []
    d = path.parent
    while not d.exists():
        missing.append(d)
        d = d.parent
    for d in reversed(missing):  # every folder made here is mode 700, not only the last one
        d.mkdir(mode=0o700, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------- Books


def first_name(name):
    """The first word of a name that isn't an honorific, title-cased and at most 30 characters; "" if none."""
    for word in re.findall(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", str(name or "")):
        if word.lower().strip(".") not in HONORIFICS:
            return word[:30]
    return ""


def gbp(value):
    """A finite amount rounded to pence, or 0.0."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(x, 2) if math.isfinite(x) else 0.0


def iso_or_blank(value):
    s = str(value or "")[:10]
    try:
        return datetime.date.fromisoformat(s).isoformat() if DATE_RE.fullmatch(s) else ""
    except ValueError:
        return ""


def short(value, most):
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value or "")).strip()[:most]


def parse_page(text, key):
    """(records, has more pages) from one Books list reply. ValueError when it isn't the expected shape."""
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get(key), list):
        raise ValueError(f"no {key} list in the reply")
    more = bool((data.get("page_context") or {}).get("has_more_page"))
    return [r for r in data[key] if isinstance(r, dict)], more


def list_all(call, server, tool, key):
    """Every record of one Books list tool, page by page (at most MAX_PAGES)."""
    out = []
    for page in range(1, MAX_PAGES + 1):
        text = call(server, tool, {"query_params": {"organization_id": ORG, "page": page, "per_page": PER_PAGE}})
        records, more = parse_page(text, key)
        out += records
        if not more:
            return out
    raise ValueError(f"more than {MAX_PAGES} pages of {key}")


def invoice_row(r):
    return {"number": short(r.get("invoice_number"), 30), "status": short(r.get("status"), 20).lower(),
            "date": iso_or_blank(r.get("date")), "due_date": iso_or_blank(r.get("due_date")),
            "total": gbp(r.get("total")), "balance": gbp(r.get("balance")),
            "customer": first_name(r.get("customer_name"))}


def bill_row(r):
    return {"number": short(r.get("bill_number"), 30), "vendor": first_name(r.get("vendor_name")),
            "status": short(r.get("status"), 20).lower(), "total": gbp(r.get("total")),
            "balance": gbp(r.get("balance")), "date": iso_or_blank(r.get("date"))}


def totals(invoices, bills):
    open_inv = [i for i in invoices if i["status"] not in NOT_OPEN_INVOICE and i["balance"] > 0]
    overdue = [i for i in open_inv if i["status"] == "overdue"]
    unpaid = [b for b in bills if b["status"] not in NOT_OPEN_BILL and b["balance"] > 0]
    return {"receivables": round(sum(i["balance"] for i in open_inv), 2), "receivables_count": len(open_inv),
            "overdue": round(sum(i["balance"] for i in overdue), 2), "overdue_count": len(overdue),
            "unpaid_bills": round(sum(b["balance"] for b in unpaid), 2), "unpaid_bills_count": len(unpaid)}


def books_snapshot(call, now=None):
    """The books.json payload, from `call(server, tool, arguments) -> text` (lcs_mcp.call_tool, or a fake)."""
    invoices = [invoice_row(r) for r in list_all(call, INVOICE_SERVER, "ZohoBooks_list_invoices", "invoices")]
    bills = [bill_row(r) for r in list_all(call, BILL_SERVER, "ZohoBooks_list_bills", "bills")]
    invoices.sort(key=lambda i: (i["date"], i["number"]), reverse=True)
    bills.sort(key=lambda b: (b["date"], b["number"]), reverse=True)
    when = (now or datetime.datetime.now(LONDON)).isoformat(timespec="seconds")
    return {"generated_at": when, "invoices": invoices, "bills": bills, "totals": totals(invoices, bills)}


def cmd_books(call=None, now=None):
    try:
        snap = books_snapshot(call or lcs_mcp.call_tool, now)
        write_private_json(cache_dir() / "books.json", snap)
    except Exception as e:  # the type name only: a message could carry a client's details or a server's URL
        print(f"books: not updated ({type(e).__name__}); the last cache is kept")
        return 0
    t = snap["totals"]
    print(f"books: {len(snap['invoices'])} invoices, {len(snap['bills'])} bills cached; receivables "
          f"£{t['receivables']:,.2f}, overdue £{t['overdue']:,.2f}, unpaid bills £{t['unpaid_bills']:,.2f}")
    return 0


# ---------------------------------------------------------------- calendar


class Refused(ValueError):
    """Calendar input that breaks a rule; nothing is written."""


def _when(value, where):
    """(kind, comparable value) for an ISO date or an ISO datetime with an offset."""
    if not isinstance(value, str):
        raise Refused(f"{where} must be a string")
    try:
        if DATE_RE.fullmatch(value):
            d = datetime.date.fromisoformat(value)
            return "date", datetime.datetime.combine(d, datetime.time(), LONDON)
        if DATETIME_RE.fullmatch(value):
            dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                return "datetime", dt
    except ValueError:
        pass
    raise Refused(f"{where} must be an ISO date (YYYY-MM-DD) or an ISO datetime with an offset")


def _text(value, most, where, blank_ok):
    if not isinstance(value, str):
        raise Refused(f"{where} must be a string")
    if re.search(r"[\x00-\x1f\x7f  ]", value):
        raise Refused(f"{where} has a control character")
    if len(value) > most:
        raise Refused(f"{where} is over {most} characters")
    if not blank_ok and not value.strip():
        raise Refused(f"{where} is blank")
    return value.strip()


def validate_events(value):
    """The checked event list, or Refused naming the first problem."""
    if not isinstance(value, list):
        raise Refused("the calendar input must be a JSON list")
    if len(value) > MAX_EVENTS:
        raise Refused(f"more than {MAX_EVENTS} events")
    out = []
    for i, e in enumerate(value):
        where = f"event {i}"
        if not isinstance(e, dict) or set(e) != {"start", "end", "summary", "calendar"}:
            raise Refused(f"{where} must have exactly start, end, summary and calendar")
        k1, start = _when(e["start"], f"{where} start")
        k2, end = _when(e["end"], f"{where} end")
        if k1 != k2:
            raise Refused(f"{where}: start and end must both be dates or both be datetimes")
        if end < start:
            raise Refused(f"{where} ends before it starts")
        out.append({"start": e["start"], "end": e["end"],
                    "summary": _text(e["summary"], SUMMARY_MAX, f"{where} summary", blank_ok=True),
                    "calendar": _text(e["calendar"], CALENDAR_MAX, f"{where} calendar", blank_ok=False)})
    out.sort(key=lambda e: (_when(e["start"], "")[1], e["calendar"], e["summary"]))
    return out


def read_input_file(path):
    """A regular file inside the private folder, never through a symlink, at most MAX_INPUT bytes."""
    root = os.path.realpath(private_dir())
    real = os.path.realpath(os.path.expanduser(path))
    if os.path.commonpath([root, real]) != root or real == root:
        raise Refused("--file must be inside the private folder (~/lcs-private)")
    try:
        st = os.lstat(os.path.expanduser(path))
    except OSError:
        raise Refused("--file must be a readable plain file (not a symlink)") from None
    if stat.S_ISLNK(st.st_mode):
        raise Refused("--file must be a readable plain file (not a symlink)")
    if not stat.S_ISREG(st.st_mode):
        raise Refused("--file must be a plain file")  # checked before opening: a FIFO must never block this
    try:
        fd = os.open(os.path.expanduser(path), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        raise Refused("--file must be a readable plain file (not a symlink)") from None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Refused("--file must be a plain file")
        raw = os.read(fd, MAX_INPUT + 1)
    finally:
        os.close(fd)
    return raw


def cmd_calendar_put(text=None, file=None, stdin=None):
    try:
        if file is not None:
            raw = read_input_file(file)
        elif text is not None:
            raw = text.encode("utf-8")
        else:
            raw = (stdin or sys.stdin.buffer).read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise Refused(f"the calendar input is over {MAX_INPUT} bytes")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise Refused("the calendar input isn't valid JSON") from None
        events = validate_events(value)
    except Refused as e:
        print(f"calendar: refused ({e}); nothing written")
        return 2
    write_private_json(cache_dir() / "calendar.json", events)
    print(f"calendar: {len(events)} events cached")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Command Centre cache writers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("books", help="cache Books invoices, bills and totals (read-only)")
    c = sub.add_parser("calendar-put", help="cache the diary from a JSON list (argument, --file or stdin)")
    c.add_argument("json", nargs="?", help="the JSON list itself, as one argument")
    c.add_argument("--file", help="a JSON file inside ~/lcs-private")
    args = ap.parse_args(argv)
    if args.cmd == "books":
        return cmd_books()
    if args.json is not None and args.file is not None:
        ap.error("calendar-put: give the JSON or --file, not both")
    return cmd_calendar_put(args.json, args.file)


if __name__ == "__main__":
    sys.exit(main())
