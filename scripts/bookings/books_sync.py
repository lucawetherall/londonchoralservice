#!/usr/bin/env python3
"""The local Books cache and the Books guard's view of Books, from one read-only pass over Zoho Books.

    .venv/bin/python scripts/bookings/books_sync.py

It reads Zoho Books (organization_id 941014440) through lcs_mcp, which allows only the read tools on the Books
guard's READ_ALLOW list (ZohoBooks_list_invoices on zoho-books-invoices, ZohoBooks_list_bills on zoho-books), and
writes ~/lcs-private/books-cache.json: each invoice's number, status, date, due date, total, balance and the
customer's first name only; each bill's number, the vendor's first name, status, total, balance and date (best
effort: the free Books plan has no bills, so a failed bill read gives "bills_read": false and no bills); the
totals (receivables, overdue, unpaid bills) and generated_at. check_payments.py (unsent and open invoices),
singer_invoices.py (paid --books-due) and the private dashboard (books_cache.py) read it.

From the same read it writes ~/lcs-private/books-guard.json: each invoice's invoice_id, customer_id, number,
status, total and balance, no names, which the Books guard (.claude/hooks/zoho_books_guard.py) checks invoice
updates and client payments against (owner hands-off, 14 Oct 2026). The guard refuses a snapshot more than an
hour old, so the daily pass runs this first.

On any failure it prints the error's type name only (a message could carry a client's details or a server's URL),
keeps the last files and exits 1; a scheduled run notes it and carries on. Both files are written atomically (a
temp file in the same folder, then os.replace) at mode 600, in folders made mode 700. LCS_PRIVATE_DIR moves the
private tree (the tests use a temp dir).
"""

import datetime
import json
import math
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_mcp  # noqa: E402

ORG = "941014440"
INVOICE_SERVER, BILL_SERVER = "zoho-books-invoices", "zoho-books"
PER_PAGE, MAX_PAGES = 200, 25
LONDON = ZoneInfo("Europe/London")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HONORIFICS = {"dr", "mr", "mrs", "ms", "miss", "mx", "prof", "rev", "revd", "the"}
NOT_OPEN_INVOICE = {"draft", "void", "paid"}
NOT_OPEN_BILL = {"void", "paid"}
RECORD_ID = re.compile(r"[0-9]{9,20}")


def private_dir():
    """Read at call time, so the tests (and a moved private tree) never touch ~/lcs-private."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))


def cache_path():
    return private_dir() / "books-cache.json"


def guard_path():
    return private_dir() / "books-guard.json"


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
    """(records, has more pages) from one Books list reply. ValueError when it isn't the expected shape. Since
    30 Oct 2026 the Books server wraps its reply as {"data": {…}, "headers": …, "status": "success"}; the bare
    reply is still read."""
    data = json.loads(text)
    if isinstance(data, dict) and key not in data and isinstance(data.get("data"), dict):
        if data.get("status") not in (None, "success"):
            raise ValueError("the reply's status isn't success")
        data = data["data"]
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


def guard_row(r):
    """One invoice as the Books guard sees it (books-guard.json): ids, number, status and balance; no names."""
    ids = {k: str(r.get(k) or "").strip() for k in ("invoice_id", "customer_id")}
    if not all(RECORD_ID.fullmatch(v) for v in ids.values()):
        return None
    return dict(ids, number=short(r.get("invoice_number"), 30), status=short(r.get("status"), 20).lower(),
                balance=gbp(r.get("balance")), total=gbp(r.get("total")))


def guard_snapshot(records, when):
    """The Books guard's view of Books (owner hands-off, 14 Oct 2026), kept apart from books-cache.json, which
    carries no record ids. The guard can't call Books itself, so it checks invoice updates and client payments
    against this: the invoice's customer, status and balance."""
    return {"generated_at": when, "invoices": [g for g in (guard_row(r) for r in records) if g]}


def books_snapshot(call, now=None, guard_out=None):
    """The books-cache.json payload, from `call(server, tool, arguments) -> text` (lcs_mcp.call_tool, or a fake).
    With `guard_out` (a dict), it is filled with the guard's snapshot from the same read."""
    records = list_all(call, INVOICE_SERVER, "ZohoBooks_list_invoices", "invoices")
    invoices = [invoice_row(r) for r in records]
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
    if guard_out is not None:
        guard_out.update(guard_snapshot(records, when))
    return {"generated_at": when, "invoices": invoices, "bills": bills, "bills_read": bills_read,
            "totals": totals(invoices, bills)}


def sync(call=None, now=None):
    try:
        guard = {}
        snap = books_snapshot(call or lcs_mcp.call_tool, now, guard)
        write_private_json(cache_path(), snap)
        write_private_json(guard_path(), guard)
    except Exception as e:  # the type name only: a message could carry a client's details or a server's URL
        print(f"books: not updated ({type(e).__name__}); the last cache is kept")
        return 1
    t = snap["totals"]
    bills = (f"{len(snap['bills'])} bills" if snap["bills_read"] else "no bills (not on this Books plan)")
    print(f"books: {len(snap['invoices'])} invoices, {bills} cached; receivables "
          f"£{t['receivables']:,.2f}, overdue £{t['overdue']:,.2f}"
          + (f", unpaid bills £{t['unpaid_bills']:,.2f}" if snap["bills_read"] else ""))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print("usage: books_sync.py (no arguments; caches Books invoices, bills and totals, read-only)")
        return 0 if argv in (["-h"], ["--help"]) else 2
    return sync()


if __name__ == "__main__":
    sys.exit(main())
