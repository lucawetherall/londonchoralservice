#!/usr/bin/env python3
"""Small, allowlisted helpers for the "Enquiry assistant" scheduled task, so an
unattended run needs no ad-hoc shell commands (which would stop on permission
prompts). Private data stays in ~/lcs-private/; this file holds none.

    .venv/bin/python scripts/bookings/assistant_io.py state
        start a run: print the time now, last_checked, the handled message ids and
        daily_due (true once per Europe/London date, until `daily-done`); creates the
        file (24 h back) and remembers when this run started
    .venv/bin/python scripts/bookings/assistant_io.py daily-done
        record today's (Europe/London) daily pass as done
    .venv/bin/python scripts/bookings/assistant_io.py done [messageId ...]
        mark messages handled and move last_checked to when this run started
    .venv/bin/python scripts/bookings/assistant_io.py zoho-down
        Zoho failed to connect at the start of this run: print "retry: yes <fireAt>" (Europe/London,
        ten minutes from now) the first time, so the run books one retry run in a fresh session, and
        "retry: no" while a retry booked in the last 3 hours hasn't been followed by a `done`
    state, done, zoho-down and daily-done each also append one JSON line to ~/lcs-private/assistant-runs.jsonl
    ({"start": <run_started>}, {"done": <now>, "marked": n}, {"zoho_down": <now>}, {"daily": "YYYY-MM-DD"}; UTC,
    to the second, as last_checked), for the Monday review's count of runs; best effort, never changing the output
    .venv/bin/python scripts/bookings/assistant_io.py style
        print the private email style guide (~/lcs-private/email-style.md)
    .venv/bin/python scripts/bookings/assistant_io.py prices
        print only the price tables of pricing.html and christmas-pricing.html, as short text
    .venv/bin/python scripts/bookings/assistant_io.py refs
        print invoice refs already used (ledger, iCloud Drive/LCS-invoices and the older ~/lcs-private/invoices/)
    .venv/bin/python scripts/bookings/assistant_io.py next-ref <YYYY-MM-DD event date> [--taken 211126,211126A]
        JSON {ref, instalment_1_due, instalment_2_due, short_notice}: the event's DDMMYY plus the first
        free suffix (refs from the ledger, the invoices folder and --taken; owner decision, 14 Oct 2026:
        older bookings keep their four-digit DDMM ref, which --taken also takes), the first instalment due
        by check_payments.deposit_due_date (the rule the payment checker uses) and the balance due
        two days (48 hours) before the event (terms 4(c))
    .venv/bin/python scripts/bookings/assistant_io.py ledger-add '<json object>'
        append one booking row (columns as in the ledger header); refuses duplicates and an
        occasion that isn't wedding, funeral, christmas, corporate, private event or other
    .venv/bin/python scripts/bookings/assistant_io.py books-queue add '<json object>'
        queue a Books record the drafter couldn't make (Books unavailable: plan, sign-in or tools):
        {ref, reason, contact_email, contact: <create_contact body>, invoice: <create_invoice body
        without customer_id>}, kept in ~/lcs-private/books-queue.jsonl (mode 600); a ref already
        queued is left as it was
    .venv/bin/python scripts/bookings/assistant_io.py books-queue list
        JSON list of the queued records not yet done, oldest first
    .venv/bin/python scripts/bookings/assistant_io.py books-queue done <ref>
        mark a queued record done once its Books invoice exists
"""

import datetime
import html
import html.parser
import json
import os
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402
import check_payments as cp  # noqa: E402

PRIVATE = lm.PRIVATE  # $LCS_PRIVATE_DIR (default ~/lcs-private), like the ledger
STATE = PRIVATE / "assistant-state.json"
BOOKS_QUEUE = PRIVATE / "books-queue.jsonl"  # Books records owed while Books can't take them
STYLE = PRIVATE / "email-style.md"
LEDGER = lm.LEDGER  # $LCS_BOOKINGS_CSV, else bookings.csv in $LCS_PRIVATE_DIR (default ~/lcs-private)
INVOICES = PRIVATE / "invoices"  # before 29 Sep 2026
ICLOUD_INVOICES = Path(os.environ.get("LCS_INVOICES_DIR", lm.ICLOUD_INVOICES))  # make_booking_docs.py writes here
REPO = Path(__file__).resolve().parents[2]
PRICE_PAGES = ("pricing.html", "christmas-pricing.html")
OCCASIONS = ("wedding", "funeral", "christmas", "corporate", "private event", "other")
# A booking ref: the event's DDMMYY (211126), or before 14 Oct 2026 its DDMM (2111), each with an optional
# capital letter for another booking that day (211126A, 2111A). Older refs keep their four digits.
REF_RE = re.compile(r"(?:[0-9]{6}|[0-9]{4})[A-Z]?")


def private_write(path, text):
    """Atomic write at mode 600: a temp file in the same folder, then os.replace."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    state = {"last_checked": since.isoformat(timespec="seconds"), "handled": []}
    private_write(STATE, json.dumps(state, indent=1))
    return state


london_today = lm.today  # today's Europe/London date (`now`: an aware datetime, default the current time)


def daily_due(state, now=None):
    """True until the daily pass is recorded for this Europe/London date."""
    return state.get("daily_done") != london_today(now).isoformat()


# --- run log -------------------------------------------------------------------------------------
# One JSON line per state, done, zoho-down and daily-done in RUN_LOG, so the Monday review can count runs started,
# finished, stopped early and Zoho-down, and find gaps (plan 2026-10-31, task 12). Best effort: a log that can't be
# written (a directory, a read-only file, a symlink, a full disk) never changes what a command prints or its exit code.

RUN_LOG = PRIVATE / "assistant-runs.jsonl"
RUN_LOG_DAYS = 60  # lines older than this go when the file is rewritten
RUN_LOG_MAX_LINES = 2000  # about 19 lines a day: the file is pruned only once it passes this


def run_log_time(entry):
    """An entry's time (aware datetime) from its start, done, zoho_down or daily value, else None."""
    for key in ("start", "done", "zoho_down", "daily"):
        value = entry.get(key) if isinstance(entry, dict) else None
        if isinstance(value, str):
            try:
                t = datetime.datetime.fromisoformat(value)
            except ValueError:
                return None
            return t if t.tzinfo else t.replace(tzinfo=lm.LONDON)
    return None


def log_run(entry, now=None):
    """Append `entry` to RUN_LOG (mode 600 on create, never through a symlink); once the file passes
    RUN_LOG_MAX_LINES, rewrite it without the lines older than RUN_LOG_DAYS (and any unreadable one)."""
    try:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        line = json.dumps(entry) + "\n"
        with lm.ledger_lock(RUN_LOG):
            fd = os.open(RUN_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "a") as f:
                f.write(line)
            lines = RUN_LOG.read_text().splitlines()
            if len(lines) > RUN_LOG_MAX_LINES:
                cutoff = now - datetime.timedelta(days=RUN_LOG_DAYS)
                kept = []
                for text in lines:
                    try:
                        t = run_log_time(json.loads(text))
                    except ValueError:
                        t = None
                    if t is not None and t >= cutoff:
                        kept.append(text + "\n")
                private_write(RUN_LOG, "".join(kept))
    except Exception:  # noqa: BLE001 - the log is a nicety; the run's own output and exit code come first
        pass


def utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


RETRY_AFTER = datetime.timedelta(minutes=10)
RETRY_WINDOW = datetime.timedelta(hours=3)


def zoho_retry(state, now):
    """(book a retry?, its fireAt). Zoho outages seen so far (22 Oct 2026: all three servers refused
    for a moment) clear within minutes, and a fresh session reconnects; one retry per outage, so a
    lasting failure falls back to the regular runs and the 4-hour alert instead of looping."""
    booked = state.get("retry_booked_at")
    if booked and now - datetime.datetime.fromisoformat(booked) < RETRY_WINDOW:
        return False, None
    return True, (now + RETRY_AFTER).astimezone(lm.LONDON).isoformat(timespec="seconds")


# --- invoice refs --------------------------------------------------------------------------------

def taken_refs():
    refs = {(r.get("booking_ref") or "").strip() for r in lm.read_csv(LEDGER)}
    for folder in (INVOICES, ICLOUD_INVOICES):
        if folder.exists():
            refs |= {p.name.split(" - ")[0].strip() for p in folder.iterdir() if p.is_dir()}
    return {r for r in refs if r}


def next_ref(event, taken, today):
    """{ref, instalment_1_due, instalment_2_due, short_notice} for an event on `event` (dates)."""
    base = event.strftime("%d%m%y")  # DDMMYY (owner decision, 14 Oct 2026): a DDMM ref repeats every year
    ref = next((base + s for s in [""] + list(string.ascii_uppercase) if base + s not in taken), None)
    if ref is None:
        raise SystemExit(f"every ref from {base} to {base}Z is taken")
    return {"ref": ref,
            "instalment_1_due": cp.deposit_due_date(today, event).isoformat(),
            "instalment_2_due": (event - datetime.timedelta(days=2)).isoformat(),  # 48 hours before (terms 4(c))
            "short_notice": (event - today).days <= cp.SHORT_NOTICE_DAYS}


def cmd_next_ref(args):
    if not args or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args[0]):
        raise SystemExit("usage: next-ref <YYYY-MM-DD event date> [--taken 211126,211126A]")
    try:
        event = datetime.date.fromisoformat(args[0])
    except ValueError:
        raise SystemExit("the event date must be a real date as YYYY-MM-DD")
    extra = set()
    rest = args[1:]
    if rest:
        if len(rest) != 2 or rest[0] != "--taken":
            raise SystemExit("usage: next-ref <YYYY-MM-DD event date> [--taken 211126,211126A]")
        extra = {t.strip() for t in rest[1].split(",") if t.strip()}
        bad = [t for t in extra if not REF_RE.fullmatch(t)]
        if bad:
            raise SystemExit("--taken takes invoice refs such as 211126, 211126A or an older 2111, comma-separated")
    today = london_today()
    if event < today:
        raise SystemExit("the event date is in the past")
    print(json.dumps(next_ref(event, taken_refs() | extra, today)))


# --- prices --------------------------------------------------------------------------------------

class PriceParser(html.parser.HTMLParser):
    """Collects, inside <main>: each pricing table's rows (name, sub, price, sentences with £ in the
    detail) under the h2 before it, list items with a £ figure, and sentences about a premium."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth_main = 0
        self.stack = []  # open tags inside main, with their class
        self.h2 = ""
        self.buf = None  # (kind, text parts) being collected
        self.blocks = []  # (heading, [lines])
        self.row = None
        self.cell = None
        self.extras = []  # li lines with £
        self.notes = []  # premium sentences
        self.rows = []  # [{table, heading, name, sub, price, detail}]: the same rows, structured (the quote calculator)

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if tag == "main":
            self.depth_main += 1
            return
        if not self.depth_main:
            return
        if tag in ("h2", "li", "p") and self.cell is None:
            self.buf = (tag, [])
        elif tag == "table" and "pricing-table" in cls:
            self.blocks.append((self.h2, []))
        elif tag == "tr" and self.blocks:
            self.row = {"name": [], "sub": [], "detail": [], "price": []}
        elif tag == "td" and self.row is not None:
            self.cell = ("name" if "pricing-name" in cls else "detail" if "pricing-detail" in cls
                         else "price" if "pricing-price" in cls else None)
        elif tag == "span" and "pricing-sub" in cls and self.cell == "name":
            self.cell = "sub"

    def handle_endtag(self, tag):
        if tag == "main":
            self.depth_main -= 1
            return
        if not self.depth_main:
            return
        if tag == "span" and self.cell == "sub":
            self.cell = "name"
        elif tag == "td":
            self.cell = None
        elif tag == "tr" and self.row is not None:
            r = {k: squash("".join(v)) for k, v in self.row.items()}
            if r["name"] and r["price"]:
                line = r["name"] + (f" ({r['sub']})" if r["sub"] else "") + " — " + r["price"]
                self.blocks[-1][1].append(line)
                self.rows.append(dict(r, table=len(self.blocks) - 1, heading=self.blocks[-1][0]))
                for s in sentences(r["detail"]):
                    if "£" in s:
                        self.blocks[-1][1].append("    · " + s)
            self.row = None
        elif self.buf and tag == self.buf[0]:
            text = squash("".join(self.buf[1]))
            if tag == "h2":
                self.h2 = text
            elif tag == "li" and "£" in text:
                self.extras.append(text)
            elif tag == "p":
                self.notes += [s for s in sentences(text) if re.search(r"\bpremium\b", s, re.I)]
            self.buf = None

    def handle_data(self, data):
        if not self.depth_main:
            return
        if self.row is not None and self.cell:
            self.row[self.cell].append(data)
        elif self.buf is not None:
            self.buf[1].append(data)


def squash(text):
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]


def price_text(page):
    p = PriceParser()
    p.feed((REPO / page).read_text(encoding="utf-8"))
    out = [f"== {page}"]
    for heading, lines in p.blocks:
        out.append(heading or "Prices")
        out += ["  " + line for line in lines]
    if p.extras:
        out.append("Combinations and examples")
        out += ["  " + x for x in dict.fromkeys(p.extras)]
    if p.notes:
        out.append("Premiums")
        out += ["  " + x for x in list(dict.fromkeys(p.notes))[:2]]
    return "\n".join(out)


# --- ledger --------------------------------------------------------------------------------------

def ledger_add(row):
    if not isinstance(row, dict):
        raise SystemExit("ledger-add needs one JSON object")
    if (row.get("occasion") or "") not in OCCASIONS:
        raise SystemExit(f"occasion must be one of: {', '.join(OCCASIONS)}; nothing written")
    if not LEDGER.exists():
        raise SystemExit("no ledger yet: run scripts/ads/upload_bookings.py once to create it")
    # The same lock as check_payments and upload_bookings, around the whole read-check-write; the file is
    # rewritten atomically at mode 600. lm.locked_rows is not re-entrant: never nest it or call another
    # ledger writer inside it.
    # Once the events migration is applied, the facts the new row's notes state (read clause by clause as the
    # migration reads them; the script's kinds only) are recorded too, claiming their clauses, under the same lock.
    with cp.lcs_events.recording(LEDGER) as t:
        unknown = set(row) - set(t.columns)
        if unknown:
            raise SystemExit(f"unknown columns: {', '.join(sorted(unknown))}")
        if not row.get("booking_ref") or any(r["booking_ref"] == row["booking_ref"] for r in t.rows):
            raise SystemExit("missing or duplicate booking_ref; nothing written")
        new = {c: "" if row.get(c) is None else str(row.get(c)) for c in t.columns}
        t.rows.append(new)
        if (new.get("notes") or "").strip() and cp.lcs_events.migration_applied():
            import lcs_migrate
            by_hash = {cp.lcs_events.note_hash(c): c for c in cp.clauses(new["notes"])}
            for p in lcs_migrate.booking_proposals(new, lm.today(), cp.lcs_events.Facts("booking"))[0]:
                # a fact dated after today isn't recorded (plan() leaves it out too): the row and its note still are
                if p["by"] == "script" and p["on"] <= lm.today().isoformat():
                    cp.lcs_events.record(t, "booking", p["id"], p["kind"], p["fields"], "script",
                                         by_hash.get(p["note"]), on=p["on"])
    print(f"ledger: added {row['booking_ref']}")


# --- Books queue ---------------------------------------------------------------------------------
# When Books refuses writes (an expired trial, a lapsed sign-in, the tools missing), the drafter stores here the exact
# contact and invoice bodies it meant to send, and the daily pass replays them once Books works again, so nobody has
# to add an invoice to Books by hand.

QUEUE_KEYS = {"ref", "reason", "contact_email", "contact", "invoice"}


def read_queue():
    if not BOOKS_QUEUE.exists():
        return []
    return [json.loads(line) for line in BOOKS_QUEUE.read_text().splitlines() if line.strip()]


def write_queue(rows):
    private_write(BOOKS_QUEUE, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))


def queue_add(rec, today=None):
    if not isinstance(rec, dict):
        raise SystemExit("books-queue add needs one JSON object")
    unknown = set(rec) - QUEUE_KEYS
    if unknown:
        raise SystemExit(f"unknown keys: {', '.join(sorted(unknown))}; nothing written")
    ref = rec.get("ref")
    if not (isinstance(ref, str) and REF_RE.fullmatch(ref)):
        raise SystemExit("ref must be a booking ref such as 211126 or 211126A (older: 2111); nothing written")
    email = rec.get("contact_email")
    if not (isinstance(email, str) and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
        raise SystemExit("contact_email must be the client's email address; nothing written")
    contact, inv = rec.get("contact"), rec.get("invoice")
    if not (isinstance(contact, dict) and contact.get("contact_name")):
        raise SystemExit("contact must be the create_contact body, with contact_name; nothing written")
    if not isinstance(inv, dict) or inv.get("invoice_number") != ref:
        raise SystemExit("invoice must be the create_invoice body, with invoice_number equal to ref; nothing written")
    if "send" in inv or "customer_id" in inv:
        raise SystemExit("leave send and customer_id out of the invoice body (the replay finds the contact); "
                         "nothing written")
    items = inv.get("line_items")
    if not (isinstance(items, list) and items and all(isinstance(i, dict) and "rate" in i for i in items)):
        raise SystemExit("invoice.line_items must list each item with its rate; nothing written")
    with lm.ledger_lock(BOOKS_QUEUE):  # the drafter and the daily pass run in parallel: no lost update
        rows = read_queue()
        if any(r["ref"] == ref and not r.get("done") for r in rows):
            print(f"books-queue: {ref} already queued")
            return
        rows.append({"ref": ref, "queued": (today or london_today()).isoformat(),
                     "reason": str(rec.get("reason") or ""), "contact_email": email, "contact": contact, "invoice": inv})
        write_queue(rows)
    print(f"books-queue: {ref} queued")


def queue_done(ref, today=None):
    with lm.ledger_lock(BOOKS_QUEUE):
        rows = read_queue()
        hit = [r for r in rows if r["ref"] == ref and not r.get("done")]
        if not hit:
            raise SystemExit(f"books-queue: {ref} is not queued")
        for r in hit:
            r["done"] = (today or london_today()).isoformat()
        write_queue(rows)
    print(f"books-queue: {ref} done")


def cmd_books_queue(args):
    sub = args[0] if args else ""
    if sub == "add" and len(args) == 2:
        try:
            rec = json.loads(args[1])
        except json.JSONDecodeError:
            raise SystemExit("books-queue add needs one JSON object")
        queue_add(rec)
    elif sub == "list" and len(args) == 1:
        print(json.dumps([r for r in read_queue() if not r.get("done")], ensure_ascii=False))
    elif sub == "done" and len(args) == 2:
        queue_done(args[1])
    else:
        raise SystemExit("usage: books-queue add '<json>' | books-queue list | books-queue done <ref>")


def main():
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "state":
        s = load_state()
        now = datetime.datetime.now(datetime.timezone.utc)
        s["run_started"] = now.isoformat(timespec="seconds")
        private_write(STATE, json.dumps(s, indent=1))
        print(json.dumps({"now": s["run_started"], "last_checked": s["last_checked"],
                          "daily_due": daily_due(s, now), "handled": s["handled"][-500:]}))
        log_run({"start": s["run_started"]})
    elif cmd == "daily-done":
        s = load_state()
        s["daily_done"] = london_today().isoformat()
        private_write(STATE, json.dumps(s, indent=1))
        print(f"daily pass done for {s['daily_done']}")
        log_run({"daily": s["daily_done"]})
    elif cmd == "done":
        s = load_state()
        started = s.pop("run_started", None) or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        s["handled"] = (s["handled"] + [m for m in args if m not in s["handled"]])[-500:]
        s["last_checked"] = started
        s.pop("retry_booked_at", None)
        private_write(STATE, json.dumps(s, indent=1))
        print(f"state saved: last_checked {started}, {len(args)} message(s) marked")
        log_run({"done": utc_now_iso(), "marked": len(args)})
    elif cmd == "zoho-down":
        s = load_state()
        now = datetime.datetime.now(datetime.timezone.utc)
        retry, at = zoho_retry(s, now)
        if retry:
            s["retry_booked_at"] = now.isoformat(timespec="seconds")
            private_write(STATE, json.dumps(s, indent=1))
            print(f"retry: yes {at}")
        else:
            print(f"retry: no (a retry was booked at {s['retry_booked_at']})")
        log_run({"zoho_down": now.isoformat(timespec="seconds")}, now)
    elif cmd == "style":
        print(STYLE.read_text() if STYLE.exists() else "(no style guide at ~/lcs-private/email-style.md)")
    elif cmd == "prices":
        print("\n\n".join(price_text(page) for page in PRICE_PAGES))
    elif cmd == "refs":
        print(" ".join(sorted(taken_refs())) or "(none)")
    elif cmd == "next-ref":
        cmd_next_ref(args)
    elif cmd == "ledger-add":
        try:
            row = json.loads(args[0]) if args else None
        except json.JSONDecodeError:
            raise SystemExit("ledger-add needs one JSON object")
        ledger_add(row)
    elif cmd == "books-queue":
        cmd_books_queue(args)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
