#!/usr/bin/env python3
"""Cache writers for the Command Centre: Zoho Books receivables and bills, and the diary.

    .venv/bin/python scripts/reports/cc_sync.py books
    .venv/bin/python scripts/reports/cc_sync.py calendar-put '<one-line JSON list of events>'
    .venv/bin/python scripts/reports/cc_sync.py calendar-put --file <path inside ~/lcs-private>
    <JSON on stdin> | .venv/bin/python scripts/reports/cc_sync.py calendar-put
    .venv/bin/python scripts/reports/cc_sync.py drafts-put '<one-line JSON object, or a list of them>'
    .venv/bin/python scripts/reports/cc_sync.py drafts-sync '<one-line JSON list from the Zoho Drafts folder>'

books reads Zoho Books (organization_id 941014440) through lcs_mcp, which allows only the read tools on the Books
guard's READ_ALLOW list (ZohoBooks_list_invoices on zoho-books-invoices, ZohoBooks_list_bills on zoho-books), and
writes ~/lcs-private/command-centre/cache/books.json: each invoice's number, status, date, due date, total, balance
and the customer's first name only; each bill's number, the vendor's first name, status, total, balance and date
(best effort: the free Books plan has no bills, so a failed bill read gives "bills_read": false and no bills);
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

drafts-put records the drafts the scheduled assistant saved in Zoho Mail, for the Command Centre's drafts inbox:
one JSON object or a list of at most 50, each exactly {thread_id, kind, first_name, subject, created}: a thread id
of 1 to 40 letters and digits, a kind from DRAFT_KINDS, one capitalised first name (cc_event.py's rule), a subject
of at most 80 characters with no control character, and the created date as YYYY-MM-DD. Anything else refuses the
whole input and writes nothing. The drafts are merged into ~/lcs-private/command-centre/cache/drafts.json (a new
one with the same thread and kind replaces the old), newest first, at most 500 kept, under an flock. The owner's
sent/discarded marks live elsewhere (drafts-marks.json, written by the app), so a re-recorded draft keeps its mark.
Each entry written by drafts-put is tagged source "assistant": the assistant knows what kind of draft it saved.

drafts-sync records the daily pass's read-only listing of the whole Zoho Drafts folder (ZohoMail_listEmails,
already on the mail guard's read allowlist), for drafts saved by hand and to drop ones no longer there (sent or
deleted in Zoho, where drafts-put alone would leave a stale row forever). One JSON list of at most 200, each
exactly {thread_id, subject, date, to_first_name}: the same thread id and subject rules as drafts-put, date as
YYYY-MM-DD, and to_first_name one capitalised first name. Anything else refuses the whole input and writes
nothing. It REPLACES ~/lcs-private/command-centre/cache/drafts.json with one row per listed thread: when a
thread was already recorded by drafts-put (source "assistant"), its kind is kept and the row's source stays
"assistant"; a thread the assistant never recorded gets kind "other" and source "zoho" ("saved by you" on the
Drafts page). A thread that no longer appears in the listing drops out, whichever source last wrote it.

All caches are written atomically (a temp file in the same folder, then os.replace) at mode 600, in folders made
mode 700. LCS_PRIVATE_DIR moves the private tree (the tests use a temp dir).
"""

import argparse
import datetime
import fcntl
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
DRAFT_KINDS = ("reply", "confirmation", "holding", "follow-up", "deposit-reminder", "balance-reminder", "receipt",
               "review", "paid-thanks", "other")
DRAFT_KEYS = {"thread_id", "kind", "first_name", "subject", "created"}
DRAFTS_PER_CALL, DRAFTS_KEPT, DRAFT_SUBJECT_MAX = 50, 500, 80
THREAD_RE = re.compile(r"^[A-Za-z0-9]{1,40}$")
FIRST_RE = re.compile(r"^[A-Z][a-z'’-]{1,20}$")  # cc_event.py's first-name rule
ZOHO_DRAFT_KEYS = {"thread_id", "subject", "date", "to_first_name"}
ZOHO_SYNC_MAX = 200  # a Drafts folder listing in one call


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
    # Bills are best effort: the free Books plan (from 29 Sep 2026) has none, so a failed read leaves them
    # out ("bills_read": false) instead of losing the invoices; singer costs live in singer-invoices.csv.
    try:
        bills = [bill_row(r) for r in list_all(call, BILL_SERVER, "ZohoBooks_list_bills", "bills")]
        bills_read = True
    except Exception:  # noqa: BLE001  the invoices still count
        bills, bills_read = [], False
    invoices.sort(key=lambda i: (i["date"], i["number"]), reverse=True)
    bills.sort(key=lambda b: (b["date"], b["number"]), reverse=True)
    when = (now or datetime.datetime.now(LONDON)).isoformat(timespec="seconds")
    return {"generated_at": when, "invoices": invoices, "bills": bills, "bills_read": bills_read,
            "totals": totals(invoices, bills)}


def cmd_books(call=None, now=None):
    try:
        snap = books_snapshot(call or lcs_mcp.call_tool, now)
        write_private_json(cache_dir() / "books.json", snap)
    except Exception as e:  # the type name only: a message could carry a client's details or a server's URL
        print(f"books: not updated ({type(e).__name__}); the last cache is kept")
        return 0
    t = snap["totals"]
    bills = (f"{len(snap['bills'])} bills" if snap["bills_read"] else "no bills (not on this Books plan)")
    print(f"books: {len(snap['invoices'])} invoices, {bills} cached; receivables "
          f"£{t['receivables']:,.2f}, overdue £{t['overdue']:,.2f}"
          + (f", unpaid bills £{t['unpaid_bills']:,.2f}" if snap["bills_read"] else ""))
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


# ---------------------------------------------------------------- drafts


def validate_drafts(value):
    """The checked draft list, or Refused naming the first problem."""
    items = value if isinstance(value, list) else [value]
    if not items:
        raise Refused("no drafts given")
    if len(items) > DRAFTS_PER_CALL:
        raise Refused(f"more than {DRAFTS_PER_CALL} drafts")
    out = []
    for i, d in enumerate(items):
        where = f"draft {i}"
        if not isinstance(d, dict) or set(d) != DRAFT_KEYS:
            raise Refused(f"{where} must have exactly thread_id, kind, first_name, subject and created")
        if not isinstance(d["thread_id"], str) or not THREAD_RE.fullmatch(d["thread_id"]):
            raise Refused(f"{where} thread_id must be 1 to 40 letters and digits")
        if d["kind"] not in DRAFT_KINDS:
            raise Refused(f"{where} kind must be one of {', '.join(DRAFT_KINDS)}")
        if not isinstance(d["first_name"], str) or not FIRST_RE.fullmatch(d["first_name"]):
            raise Refused(f"{where} first_name must be one capitalised first name")
        subject = _text(d["subject"], DRAFT_SUBJECT_MAX, f"{where} subject", blank_ok=False)
        if not isinstance(d["created"], str) or not DATE_RE.fullmatch(d["created"]):
            raise Refused(f"{where} created must be YYYY-MM-DD")
        try:
            datetime.date.fromisoformat(d["created"])
        except ValueError:
            raise Refused(f"{where} created is not a real date") from None
        out.append({"thread_id": d["thread_id"], "kind": d["kind"], "first_name": d["first_name"],
                    "subject": subject, "created": d["created"], "source": "assistant"})
    return out


def merge_drafts(old, new):
    """`new` over `old` (the same thread and kind replaces), newest first, at most DRAFTS_KEPT."""
    by = {}
    for d in (old if isinstance(old, list) else []):
        if isinstance(d, dict) and isinstance(d.get("thread_id"), str) and isinstance(d.get("kind"), str):
            by[(d["thread_id"], d["kind"])] = d
    for d in new:
        by[(d["thread_id"], d["kind"])] = d
    return sorted(by.values(), key=lambda d: (str(d.get("created", "")), d["thread_id"], d["kind"]),
                  reverse=True)[:DRAFTS_KEPT]


def validate_zoho_drafts(value):
    """The checked Zoho Drafts listing, or Refused naming the first problem. Each row: {thread_id, subject, date,
    to_first_name}, the same rules as validate_drafts bar kind (Zoho's own listing carries no kind)."""
    if not isinstance(value, list):
        raise Refused("the drafts input must be a JSON list")
    if len(value) > ZOHO_SYNC_MAX:
        raise Refused(f"more than {ZOHO_SYNC_MAX} drafts")
    out = []
    for i, d in enumerate(value):
        where = f"draft {i}"
        if not isinstance(d, dict) or set(d) != ZOHO_DRAFT_KEYS:
            raise Refused(f"{where} must have exactly thread_id, subject, date and to_first_name")
        if not isinstance(d["thread_id"], str) or not THREAD_RE.fullmatch(d["thread_id"]):
            raise Refused(f"{where} thread_id must be 1 to 40 letters and digits")
        subject = _text(d["subject"], DRAFT_SUBJECT_MAX, f"{where} subject", blank_ok=False)
        if not isinstance(d["date"], str) or not DATE_RE.fullmatch(d["date"]):
            raise Refused(f"{where} date must be YYYY-MM-DD")
        try:
            datetime.date.fromisoformat(d["date"])
        except ValueError:
            raise Refused(f"{where} date is not a real date") from None
        if not isinstance(d["to_first_name"], str) or not FIRST_RE.fullmatch(d["to_first_name"]):
            raise Refused(f"{where} to_first_name must be one capitalised first name")
        out.append({"thread_id": d["thread_id"], "subject": subject, "date": d["date"],
                    "to_first_name": d["to_first_name"]})
    return out


def sync_drafts(old, rows):
    """The full replacement drafts.json from a live Zoho Drafts listing (`rows`, validate_zoho_drafts's output):
    one entry per listed thread, newest first. A thread drafts-put already recorded (source "assistant") keeps
    its kind and source; any other thread gets kind "other" and source "zoho" ("saved by you" on the page). A
    thread no longer listed (sent or deleted in Zoho) is dropped, whichever source last wrote it. Pure: no I/O."""
    kind_by_thread = {}
    for d in (old if isinstance(old, list) else []):
        if isinstance(d, dict) and d.get("source", "assistant") == "assistant" and isinstance(d.get("thread_id"), str) \
                and isinstance(d.get("kind"), str):
            prev = kind_by_thread.get(d["thread_id"])
            if prev is None or str(d.get("created", "")) >= prev[1]:
                kind_by_thread[d["thread_id"]] = (d["kind"], str(d.get("created", "")))
    out = []
    for row in rows:
        known = kind_by_thread.get(row["thread_id"])
        out.append({"thread_id": row["thread_id"], "kind": known[0] if known else "other",
                    "first_name": row["to_first_name"], "subject": row["subject"], "created": row["date"],
                    "source": "assistant" if known else "zoho"})
    return sorted(out, key=lambda d: (d["created"], d["thread_id"], d["kind"]), reverse=True)[:DRAFTS_KEPT]


def make_private_dirs(path):
    """The folders above `path`, each made mode 700 if missing."""
    missing = []
    d = Path(path).parent
    while not d.exists():
        missing.append(d)
        d = d.parent
    for d in reversed(missing):
        d.mkdir(mode=0o700, exist_ok=True)


def cmd_drafts_put(text):
    try:
        raw = text.encode("utf-8")
        if len(raw) > MAX_INPUT:
            raise Refused(f"the drafts input is over {MAX_INPUT} bytes")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise Refused("the drafts input isn't valid JSON") from None
        new = validate_drafts(value)
    except Refused as e:
        print(f"drafts: refused ({e}); nothing written")
        return 2
    path = cache_dir() / "drafts.json"
    lock = cache_dir() / ".drafts.lock"
    make_private_dirs(lock)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)  # one writer at a time: the read, merge and write happen under it
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except (FileNotFoundError, ValueError):
            old = []
        merged = merge_drafts(old, new)
        write_private_json(path, merged)
    finally:
        os.close(fd)
    print(f"drafts: {len(new)} recorded, {len(merged)} in the inbox")
    return 0


def cmd_drafts_sync(text):
    try:
        raw = text.encode("utf-8")
        if len(raw) > MAX_INPUT:
            raise Refused(f"the drafts input is over {MAX_INPUT} bytes")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise Refused("the drafts input isn't valid JSON") from None
        rows = validate_zoho_drafts(value)
    except Refused as e:
        print(f"drafts-sync: refused ({e}); nothing written")
        return 2
    path = cache_dir() / "drafts.json"
    lock = cache_dir() / ".drafts.lock"
    make_private_dirs(lock)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)  # one writer at a time, the same lock drafts-put uses
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except (FileNotFoundError, ValueError):
            old = []
        synced = sync_drafts(old, rows)
        write_private_json(path, synced)
    finally:
        os.close(fd)
    by_you = sum(1 for d in synced if d["source"] == "zoho")
    print(f"drafts-sync: {len(synced)} drafts synced ({by_you} saved by you)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Command Centre cache writers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("books", help="cache Books invoices, bills and totals (read-only)")
    c = sub.add_parser("calendar-put", help="cache the diary from a JSON list (argument, --file or stdin)")
    c.add_argument("json", nargs="?", help="the JSON list itself, as one argument")
    c.add_argument("--file", help="a JSON file inside ~/lcs-private")
    d = sub.add_parser("drafts-put", help="record drafts saved in Zoho Mail (one JSON object or a list)")
    d.add_argument("json", help="the JSON itself, as one argument")
    s = sub.add_parser("drafts-sync", help="replace the Zoho-sourced drafts from a live Drafts folder listing")
    s.add_argument("json", help="the JSON list itself, as one argument")
    args = ap.parse_args(argv)
    if args.cmd == "books":
        return cmd_books()
    if args.cmd == "drafts-put":
        return cmd_drafts_put(args.json)
    if args.cmd == "drafts-sync":
        return cmd_drafts_sync(args.json)
    if args.json is not None and args.file is not None:
        ap.error("calendar-put: give the JSON or --file, not both")
    return cmd_calendar_put(args.json, args.file)


if __name__ == "__main__":
    sys.exit(main())
