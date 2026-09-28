#!/usr/bin/env python3
"""The private enquiry pipeline for London Choral Service: one row per enquiry in
~/lcs-private/enquiries.csv (LCS_PRIVATE_DIR overrides the folder), mode 600.
The enquiry assistant (handover Appendix E) keeps it up to date; the Monday
report and the dashboard import summary_dict().

    .venv/bin/python scripts/bookings/pipeline.py add '<json object>'   (or: add - , the JSON on stdin)
        a new enquiry; refuses a duplicate enquiry_id or an unknown field.
        Defaults: status new, followups 0, last_contact = first_seen
    .venv/bin/python scripts/bookings/pipeline.py quoted <enquiry_id> <package> <gbp> <YYYY-MM-DD>
        Luca's reply quoted a package: status quoted, follow-up clock restarts. Refuses a date
        before last_contact, or a quote already noted for that date
    .venv/bin/python scripts/bookings/pipeline.py contact <enquiry_id> <YYYY-MM-DD>
        the client replied: last_contact moves on, followups back to 0. Refuses a date before last_contact
    .venv/bin/python scripts/bookings/pipeline.py event <enquiry_id> <YYYY-MM-DD>
        sets the event date
    .venv/bin/python scripts/bookings/pipeline.py status <enquiry_id> <status> [booking_ref]
        new, quoted, confirmed (needs booking_ref), deposit_paid, done, lost, cancelled.
        A confirmed, deposit_paid or done enquiry never goes back to new or quoted
    .venv/bin/python scripts/bookings/pipeline.py followups-due [--today YYYY-MM-DD]
        JSON [{enquiry_id, kind}], kind first | second | mark_lost
    .venv/bin/python scripts/bookings/pipeline.py followed <enquiry_id> <1|2> <YYYY-MM-DD>
        a follow-up draft was saved
    .venv/bin/python scripts/bookings/pipeline.py reviews-due [--today YYYY-MM-DD]
        JSON [{booking_ref, event_date}] from the bookings ledger
    .venv/bin/python scripts/bookings/pipeline.py reviewed <booking_ref> <YYYY-MM-DD>
        appends "review request drafted <date>" to that ledger row's notes
    .venv/bin/python scripts/bookings/pipeline.py review-skipped <booking_ref> <reason word>
        appends "review request skipped <today> (<reason>)" to that ledger row's notes, so
        reviews-due stops listing it (a planner, an unresolved problem); the reason is one
        lower-case word, never a name
    .venv/bin/python scripts/bookings/pipeline.py thread <booking_ref>
        prints the enquiry_id (the Zoho thread id) booked under that ref, or "no thread"
    .venv/bin/python scripts/bookings/pipeline.py done-due [--today YYYY-MM-DD]
        JSON [{enquiry_id, booking_ref}]: booked enquiries whose ledger row is paid in full
        with the event past, not cancelled and not yet done (funerals included)
    .venv/bin/python scripts/bookings/pipeline.py summary [--since YYYY-MM-DD]
        JSON counts by status and source, conversion and median days to quote

Follow-ups (status quoted, no booking_ref), each counted from last_contact, which
`quoted`, `contact` and `followed` move: the first 5 days after the quote, the second
10 days after the first, then mark_lost 10 days after the second. An event date that
is today or past gives mark_lost at once and never a follow-up. A funeral (or an
enquiry with no occasion) is never chased: it gets mark_lost once the event has
passed, or nothing if there is no event date. reviews-due never lists a funeral
booking, or one whose ledger occasion is blank. `quoted` also notes
"quoted YYYY-MM-DD", which gives the days-to-quote figure.

Output shows enquiry ids, booking refs, dates and counts only: never names,
emails or notes. enquiries.csv has no name or email column, and `add` refuses one.
"""

import argparse
import datetime
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402
import check_payments as cp  # noqa: E402

ENQUIRIES = lm.PRIVATE / "enquiries.csv"
COLUMNS = ["enquiry_id", "first_seen", "source", "occasion", "event_date", "package", "quoted_gbp", "status",
           "last_contact", "booking_ref", "gclid", "followups", "notes"]
SOURCES = {"web form", "email", "whatsapp", "phone", "referral"}
STATUSES = {"new", "quoted", "confirmed", "deposit_paid", "done", "lost", "cancelled"}
STATUS_ORDER = ["new", "quoted", "confirmed", "deposit_paid", "done", "lost", "cancelled"]
BOOKED = {"confirmed", "deposit_paid", "done"}
DATE_FIELDS = ("first_seen", "event_date", "last_contact")
FIRST_AFTER, SECOND_AFTER, LOST_AFTER = 5, 10, 10  # days since last_contact (the quote, then each chase)
REVIEW_FROM, REVIEW_UNTIL = 3, 14  # days after the event
QUOTED_NOTE = re.compile(r"\bquoted (\d{4}-\d{2}-\d{2})\b")
REVIEW_NOTE = re.compile(r"review request (drafted|skipped)", re.I)
REASON_RE = re.compile(r"^[a-z][a-z-]{0,19}$")
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
FUNERAL = re.compile(r"\b(funeral|memorial|requiem|burial|interment|committal|cremation|thanksgiving"
                     r"|celebration of life)\b", re.I)
OCCASIONS = ("wedding", "funeral", "christmas", "corporate", "private event", "other")
GCLID_RE = re.compile(r"^((gbraid|wbraid):)?[A-Za-z0-9_-]{10,200}$")
MAX_LEN = {"notes": 300, "gclid": 207}  # characters; gclid is then held to GCLID_RE
MAX_OTHER = 80  # every other field
MAX_GBP = 100000


# --- small helpers -------------------------------------------------------------------------------

def to_date(s):
    """A strict YYYY-MM-DD string (or a date or datetime) -> date, else None."""
    if isinstance(s, datetime.datetime):
        return s.date()
    if isinstance(s, datetime.date):
        return s
    s = (s or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def iso(s, field):
    d = to_date(s)
    if d is None:
        raise SystemExit(f"{field} must be a date as YYYY-MM-DD")
    return d.isoformat()


def gbp(s):
    v = lm.parse_gbp(s)
    if v is None:  # unreadable, nan or inf
        raise SystemExit("quoted_gbp must be an amount in pounds, such as 1150")
    if not v > 0 or round(v, 2) == 0:
        raise SystemExit("quoted_gbp must be more than zero")
    if v > MAX_GBP:
        raise SystemExit(f"quoted_gbp must be at most {MAX_GBP}")
    v = round(v, 2)
    return str(int(v)) if v == int(v) else f"{v:.2f}"


def ident(s, field):
    s = str(s).strip()
    if not ID_RE.fullmatch(s):
        raise SystemExit(f"{field} must be 1-64 letters, digits or . _ : -")
    return s


def add_note(notes, text):
    return (f"{notes}; " if (notes or "").strip() else "") + text


def is_funeral_or_unknown(occasion):
    occasion = (occasion or "").strip()
    return not occasion or bool(FUNERAL.search(occasion))


def status_of(r):
    return (r.get("status") or "").strip().lower()


def followups_of(r):
    try:
        n = int(r.get("followups") or 0)
    except ValueError:
        return None
    return n if n in (0, 1, 2) else None


# --- pure functions ------------------------------------------------------------------------------

def followups_due(rows, today):
    """[{enquiry_id, kind}] for quoted enquiries whose follow-up (or loss) falls due by today.
    Never a booked one (a booking_ref), and never a chase for a funeral or an unknown occasion."""
    today = to_date(today)
    out = []
    for r in rows:
        if status_of(r) != "quoted" or (r.get("booking_ref") or "").strip():
            continue
        event = to_date(r.get("event_date"))
        if event and event <= today:  # nothing to chase on or after the day: close it
            out.append({"enquiry_id": r["enquiry_id"], "kind": "mark_lost"})
            continue
        if is_funeral_or_unknown(r.get("occasion")):
            continue
        last = to_date(r.get("last_contact")) or to_date(r.get("first_seen"))
        n = followups_of(r)
        if last is None or n is None:
            continue
        quiet = (today - last).days
        kind = {0: ("first", FIRST_AFTER), 1: ("second", SECOND_AFTER), 2: ("mark_lost", LOST_AFTER)}[n]
        if quiet >= kind[1]:
            out.append({"enquiry_id": r["enquiry_id"], "kind": kind[0]})
    return out


def reviews_due(ledger_rows, today):
    """[{booking_ref, event_date}] for paid-in-full, uncancelled bookings 3 to 14 days after the event,
    with no review request drafted yet. Never a funeral, or a booking whose occasion is blank."""
    today = to_date(today)
    out = []
    for r in ledger_rows:
        event = to_date(r.get("event_date"))
        notes = r.get("notes") or ""
        if not r.get("booking_ref") or event is None or is_funeral_or_unknown(r.get("occasion")):
            continue
        if not REVIEW_FROM <= (today - event).days <= REVIEW_UNTIL:
            continue
        if not cp.FULL_NOTE.search(notes) or cp.is_cancelled(r) or REVIEW_NOTE.search(notes):
            continue
        out.append({"booking_ref": r["booking_ref"], "event_date": event.isoformat()})
    return out


def done_due(rows, ledger_rows, today):
    """[{enquiry_id, booking_ref}] for enquiries with a booking_ref, not yet done, lost or cancelled, whose
    ledger row is paid in full ("paid in full YYYY-MM-DD"), not cancelled, with the event before today."""
    today = to_date(today)
    ledger = {(r.get("booking_ref") or "").strip(): r for r in ledger_rows if (r.get("booking_ref") or "").strip()}
    out = []
    for r in rows:
        ref = (r.get("booking_ref") or "").strip()
        if not ref or status_of(r) in ("done", "lost", "cancelled") or ref not in ledger:
            continue
        b = ledger[ref]
        event = to_date(b.get("event_date")) or to_date(r.get("event_date"))
        if event is None or event >= today:
            continue
        if not cp.FULL_NOTE.search(b.get("notes") or "") or cp.is_cancelled(b):
            continue
        out.append({"enquiry_id": r["enquiry_id"], "booking_ref": ref})
    return out


def summary_dict(rows, since=None):
    """Pipeline figures for enquiries first seen on or after `since` (a date, a YYYY-MM-DD string or None).

    quoted: enquiries that got a quote (status quoted, a quoted_gbp or a "quoted" note), whatever happened next.
    confirmed: enquiries that became a booking (confirmed, deposit_paid, done, or cancelled with a booking_ref).
    conversion_rate: confirmed / enquiries, 3 decimal places (None with no enquiries).
    median_days_to_quote: first_seen to the first "quoted YYYY-MM-DD" note (None when there are none); a
    negative figure (a mistyped date) is left out. Statuses are counted whatever their case."""
    since = to_date(since) if since else None
    picked = [r for r in rows if since is None or (to_date(r.get("first_seen")) or datetime.date.min) >= since]
    by_status = {s: 0 for s in STATUS_ORDER}
    by_source = {}
    quoted = confirmed = 0
    waits = []
    for r in picked:
        status = status_of(r)
        if status in by_status:
            by_status[status] += 1
        source = (r.get("source") or "").strip() or "unknown"
        by_source[source] = by_source.get(source, 0) + 1
        notes = r.get("notes") or ""
        quote_days = [d for d in (to_date(m) for m in QUOTED_NOTE.findall(notes)) if d]
        if (r.get("quoted_gbp") or "").strip() or quote_days or status in BOOKED or status == "quoted":
            quoted += 1
        if status in BOOKED or (status == "cancelled" and (r.get("booking_ref") or "").strip()):
            confirmed += 1
        seen = to_date(r.get("first_seen"))
        if seen and quote_days and (min(quote_days) - seen).days >= 0:
            waits.append((min(quote_days) - seen).days)
    n = len(picked)
    median = statistics.median(waits) if waits else None
    return {
        "by_status": by_status,
        "enquiries": n,
        "quoted": quoted,
        "confirmed": confirmed,
        "conversion_rate": round(confirmed / n, 3) if n else None,
        "by_source": by_source,
        "median_days_to_quote": median,
    }


# --- file access ---------------------------------------------------------------------------------

def change(enquiry_id, fn):
    """Read-modify-write one enquiry under enquiries.csv's own lock. fn(row) edits the row in place."""
    # lm.locked_rows is not re-entrant: never nest it, or call another writer of this file inside it.
    with lm.locked_rows(ENQUIRIES, COLUMNS) as t:
        for r in t.rows:
            if r.get("enquiry_id") == enquiry_id:
                fn(r)
                break
        else:
            raise SystemExit(f"no enquiry {enquiry_id}")


def clean_row(data):
    if not isinstance(data, dict):
        raise SystemExit("add needs one JSON object")
    unknown = sorted(set(data) - set(COLUMNS))
    if unknown:
        raise SystemExit(f"unknown field(s): {', '.join(unknown)}; nothing written")
    row = {c: "" for c in COLUMNS}
    for k, v in data.items():
        v = "" if v is None else str(v)
        if "\n" in v or "\r" in v:
            raise SystemExit(f"{k} must be a single line")
        v = v.strip()
        limit = MAX_LEN.get(k, MAX_OTHER)
        if len(v) > limit:
            raise SystemExit(f"{k} is too long (at most {limit} characters); nothing written")
        row[k] = v
    row["enquiry_id"] = ident(row["enquiry_id"], "enquiry_id")
    row["first_seen"] = iso(row["first_seen"], "first_seen")
    if row["source"] not in SOURCES:
        raise SystemExit(f"source must be one of: {', '.join(sorted(SOURCES))}")
    row["occasion"] = row["occasion"].lower()
    if row["occasion"] not in OCCASIONS:
        raise SystemExit(f"occasion must be one of: {', '.join(OCCASIONS)}")
    if row["gclid"] and not GCLID_RE.fullmatch(row["gclid"]):
        raise SystemExit("gclid must be a click id (letters, digits, _ or -, 10-200 of them), "
                         "optionally after gbraid: or wbraid:")
    row["status"] = row["status"] or "new"
    if row["status"] not in STATUSES:
        raise SystemExit(f"status must be one of: {', '.join(STATUS_ORDER)}")
    if row["event_date"]:
        row["event_date"] = iso(row["event_date"], "event_date")
    row["last_contact"] = iso(row["last_contact"], "last_contact") if row["last_contact"] else row["first_seen"]
    row["followups"] = row["followups"] or "0"
    if row["followups"] not in ("0", "1", "2"):
        raise SystemExit("followups must be 0, 1 or 2")
    if row["quoted_gbp"]:
        row["quoted_gbp"] = gbp(row["quoted_gbp"])
    if row["booking_ref"]:
        row["booking_ref"] = ident(row["booking_ref"], "booking_ref")
    if row["status"] == "confirmed" and not row["booking_ref"]:
        raise SystemExit("status confirmed needs a booking_ref")
    return row


# --- commands ------------------------------------------------------------------------------------

def cmd_add(args):
    text = sys.stdin.read() if args.json == "-" else args.json
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise SystemExit("add needs one JSON object")
    row = clean_row(data)
    with lm.locked_rows(ENQUIRIES, COLUMNS) as t:
        if any(r.get("enquiry_id") == row["enquiry_id"] for r in t.rows):
            raise SystemExit(f"duplicate enquiry_id {row['enquiry_id']}; nothing written")
        t.rows.append(row)
    print(f"enquiry {row['enquiry_id']}: added")


def cmd_quoted(args):
    when, amount = iso(args.date, "date"), gbp(args.gbp)
    package = args.package.strip()
    if not package or "\n" in package or ";" in package or len(package) > 80:
        raise SystemExit("package must be one line, at most 80 characters, with no ';'")

    def edit(r):
        if r.get("status") in BOOKED or r.get("status") == "cancelled":
            raise SystemExit(f"enquiry {r['enquiry_id']} is {r['status']}; not re-quoted")
        not_before_last_contact(r, when)
        if when in QUOTED_NOTE.findall(r.get("notes") or ""):
            raise SystemExit(f"enquiry {r['enquiry_id']} already has a quote on {when}; nothing changed")
        r.update(status="quoted", package=package, quoted_gbp=amount, last_contact=when, followups="0")
        r["notes"] = add_note(r.get("notes"), f"quoted {when}")
    change(args.enquiry_id, edit)
    print(f"enquiry {args.enquiry_id}: quoted")


def not_before_last_contact(r, when):
    """An old message, or a quote seen again on a later run, must never restart the follow-up clock."""
    last = to_date(r.get("last_contact"))
    if last and to_date(when) < last:
        raise SystemExit(f"enquiry {r['enquiry_id']}: {when} is before the last contact; nothing changed")


def cmd_contact(args):
    when = iso(args.date, "date")

    def edit(r):
        not_before_last_contact(r, when)
        r["last_contact"] = when
        r["followups"] = "0"
    change(args.enquiry_id, edit)
    print(f"enquiry {args.enquiry_id}: contact {when}, follow-ups reset")


def cmd_event(args):
    when = iso(args.date, "date")

    def edit(r):
        r["event_date"] = when
    change(args.enquiry_id, edit)
    print(f"enquiry {args.enquiry_id}: event {when}")


def cmd_status(args):
    if args.status not in STATUSES:
        raise SystemExit(f"status must be one of: {', '.join(STATUS_ORDER)}")
    ref = ident(args.booking_ref, "booking_ref") if args.booking_ref else ""

    def edit(r):
        if status_of(r) in BOOKED and args.status in ("new", "quoted"):
            raise SystemExit(f"enquiry {r['enquiry_id']} is {status_of(r)}; not moved back to {args.status}")
        if ref:
            r["booking_ref"] = ref
        if args.status == "confirmed" and not r.get("booking_ref"):
            raise SystemExit("status confirmed needs a booking_ref")
        r["status"] = args.status
    change(args.enquiry_id, edit)
    print(f"enquiry {args.enquiry_id}: {args.status}" + (f" ({ref})" if ref else ""))


def cmd_followed(args):
    n, when = int(args.number), iso(args.date, "date")

    def edit(r):
        if r.get("status") != "quoted":
            raise SystemExit(f"enquiry {r['enquiry_id']} is {r.get('status') or 'blank'}, not quoted")
        if followups_of(r) != n - 1:
            raise SystemExit(f"enquiry {r['enquiry_id']} already has {r.get('followups')} follow-up(s); "
                             f"follow-up {n} not recorded")
        r.update(followups=str(n), last_contact=when)
    change(args.enquiry_id, edit)
    print(f"enquiry {args.enquiry_id}: follow-up {n} on {when}")


def cmd_reviewed(args):
    when = iso(args.date, "date")
    note_review(args.booking_ref, f"review request drafted {when}")


def cmd_review_skipped(args):
    reason = args.reason.strip()
    if not REASON_RE.fullmatch(reason):
        raise SystemExit("the reason must be one lower-case word, such as planner or unresolved")
    note_review(args.booking_ref, f"review request skipped {lm.today().isoformat()} ({reason})")


def cmd_thread(args):
    ref = args.booking_ref.strip()
    ids = [r["enquiry_id"] for r in lm.read_csv(ENQUIRIES) if (r.get("booking_ref") or "").strip() == ref]
    print("\n".join(ids) if ids else "no thread")


def note_review(booking_ref, text):
    """Append a review note to one ledger row, under the ledger lock; refuses a second one."""
    ledger = lm.LEDGER
    if not ledger.exists():
        raise SystemExit("no bookings ledger")
    # The same lock as check_payments and assistant_io; not re-entrant, so nothing else writes inside it.
    # locked_rows refuses a row wider than the header (a rewrite would drop its extra fields).
    with lm.locked_rows(ledger) as t:
        for r in t.rows:
            if r.get("booking_ref") == booking_ref:
                if REVIEW_NOTE.search(r.get("notes") or ""):
                    raise SystemExit(f"{booking_ref}: review request already drafted or skipped; nothing written")
                r["notes"] = add_note(r.get("notes"), text)
                break
        else:
            raise SystemExit(f"no booking {booking_ref}")
    print(f"{booking_ref}: {text}")


def today_arg(args):
    return to_date(args.today) if args.today else lm.today()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Private enquiry pipeline (see the module docstring).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("json")
    p = sub.add_parser("quoted")
    for a in ("enquiry_id", "package", "gbp", "date"):
        p.add_argument(a)
    p = sub.add_parser("contact")
    p.add_argument("enquiry_id")
    p.add_argument("date")
    p = sub.add_parser("event")
    p.add_argument("enquiry_id")
    p.add_argument("date")
    p = sub.add_parser("status")
    p.add_argument("enquiry_id")
    p.add_argument("status")
    p.add_argument("booking_ref", nargs="?")
    p = sub.add_parser("followed")
    p.add_argument("enquiry_id")
    p.add_argument("number", choices=["1", "2"])
    p.add_argument("date")
    for name in ("followups-due", "reviews-due", "done-due"):
        p = sub.add_parser(name)
        p.add_argument("--today", type=lambda s: iso(s, "--today"))
    p = sub.add_parser("reviewed")
    p.add_argument("booking_ref")
    p.add_argument("date")
    p = sub.add_parser("review-skipped")
    p.add_argument("booking_ref")
    p.add_argument("reason")
    p = sub.add_parser("thread")
    p.add_argument("booking_ref")
    p = sub.add_parser("summary")
    p.add_argument("--since", type=lambda s: iso(s, "--since"))
    args = ap.parse_args(argv)

    if args.cmd == "add":
        cmd_add(args)
    elif args.cmd == "quoted":
        cmd_quoted(args)
    elif args.cmd == "contact":
        cmd_contact(args)
    elif args.cmd == "event":
        cmd_event(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "followed":
        cmd_followed(args)
    elif args.cmd == "followups-due":
        print(json.dumps(followups_due(lm.read_csv(ENQUIRIES), today_arg(args))))
    elif args.cmd == "reviews-due":
        print(json.dumps(reviews_due(lm.read_csv(lm.LEDGER), today_arg(args))))
    elif args.cmd == "done-due":
        print(json.dumps(done_due(lm.read_csv(ENQUIRIES), lm.read_csv(lm.LEDGER), today_arg(args))))
    elif args.cmd == "reviewed":
        cmd_reviewed(args)
    elif args.cmd == "review-skipped":
        cmd_review_skipped(args)
    elif args.cmd == "thread":
        cmd_thread(args)
    elif args.cmd == "summary":
        print(json.dumps(summary_dict(lm.read_csv(ENQUIRIES), args.since)))


if __name__ == "__main__":
    main()
