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
    .venv/bin/python scripts/bookings/assistant_io.py style
        print the private email style guide (~/lcs-private/email-style.md)
    .venv/bin/python scripts/bookings/assistant_io.py prices
        print only the price tables of pricing.html and christmas-pricing.html, as short text
    .venv/bin/python scripts/bookings/assistant_io.py refs
        print invoice refs already used (ledger, iCloud Drive/LCS-invoices and the older ~/lcs-private/invoices/)
    .venv/bin/python scripts/bookings/assistant_io.py next-ref <YYYY-MM-DD event date> [--taken 2111,2111A]
        JSON {ref, instalment_1_due, instalment_2_due, short_notice}: the event's DDMM plus the first
        free suffix (refs from the ledger, the invoices folder and --taken), the first instalment due
        by check_payments.deposit_due_date (the rule the payment checker uses) and the balance due
        the day before the event
    .venv/bin/python scripts/bookings/assistant_io.py ledger-add '<json object>'
        append one booking row (columns as in the ledger header); refuses duplicates and an
        occasion that isn't wedding, funeral, christmas, corporate, private event or other
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
STYLE = PRIVATE / "email-style.md"
LEDGER = lm.LEDGER  # $LCS_BOOKINGS_CSV, else bookings.csv in $LCS_PRIVATE_DIR (default ~/lcs-private)
INVOICES = PRIVATE / "invoices"  # before 29 Sep 2026
ICLOUD_INVOICES = Path(os.environ.get("LCS_INVOICES_DIR", lm.ICLOUD_INVOICES))  # make_booking_docs.py writes here
REPO = Path(__file__).resolve().parents[2]
PRICE_PAGES = ("pricing.html", "christmas-pricing.html")
OCCASIONS = ("wedding", "funeral", "christmas", "corporate", "private event", "other")
REF_RE = re.compile(r"[0-9]{4}[A-Z]?")


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


# --- invoice refs --------------------------------------------------------------------------------

def taken_refs():
    refs = {(r.get("booking_ref") or "").strip() for r in lm.read_csv(LEDGER)}
    for folder in (INVOICES, ICLOUD_INVOICES):
        if folder.exists():
            refs |= {p.name.split(" - ")[0].strip() for p in folder.iterdir() if p.is_dir()}
    return {r for r in refs if r}


def next_ref(event, taken, today):
    """{ref, instalment_1_due, instalment_2_due, short_notice} for an event on `event` (dates)."""
    base = event.strftime("%d%m")
    ref = next((base + s for s in [""] + list(string.ascii_uppercase) if base + s not in taken), None)
    if ref is None:
        raise SystemExit(f"every ref from {base} to {base}Z is taken")
    return {"ref": ref,
            "instalment_1_due": cp.deposit_due_date(today, event).isoformat(),
            "instalment_2_due": (event - datetime.timedelta(days=1)).isoformat(),
            "short_notice": (event - today).days <= cp.SHORT_NOTICE_DAYS}


def cmd_next_ref(args):
    if not args or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args[0]):
        raise SystemExit("usage: next-ref <YYYY-MM-DD event date> [--taken 2111,2111A]")
    try:
        event = datetime.date.fromisoformat(args[0])
    except ValueError:
        raise SystemExit("the event date must be a real date as YYYY-MM-DD")
    extra = set()
    rest = args[1:]
    if rest:
        if len(rest) != 2 or rest[0] != "--taken":
            raise SystemExit("usage: next-ref <YYYY-MM-DD event date> [--taken 2111,2111A]")
        extra = {t.strip() for t in rest[1].split(",") if t.strip()}
        bad = [t for t in extra if not REF_RE.fullmatch(t)]
        if bad:
            raise SystemExit("--taken takes invoice refs such as 2111 or 2111A, comma-separated")
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
    with lm.locked_rows(LEDGER) as t:
        unknown = set(row) - set(t.columns)
        if unknown:
            raise SystemExit(f"unknown columns: {', '.join(sorted(unknown))}")
        if not row.get("booking_ref") or any(r["booking_ref"] == row["booking_ref"] for r in t.rows):
            raise SystemExit("missing or duplicate booking_ref; nothing written")
        t.rows.append({c: "" if row.get(c) is None else str(row.get(c)) for c in t.columns})
    print(f"ledger: added {row['booking_ref']}")


def main():
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "state":
        s = load_state()
        now = datetime.datetime.now(datetime.timezone.utc)
        s["run_started"] = now.isoformat(timespec="seconds")
        private_write(STATE, json.dumps(s, indent=1))
        print(json.dumps({"now": s["run_started"], "last_checked": s["last_checked"],
                          "daily_due": daily_due(s, now), "handled": s["handled"][-500:]}))
    elif cmd == "daily-done":
        s = load_state()
        s["daily_done"] = london_today().isoformat()
        private_write(STATE, json.dumps(s, indent=1))
        print(f"daily pass done for {s['daily_done']}")
    elif cmd == "done":
        s = load_state()
        started = s.pop("run_started", None) or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        s["handled"] = (s["handled"] + [m for m in args if m not in s["handled"]])[-500:]
        s["last_checked"] = started
        private_write(STATE, json.dumps(s, indent=1))
        print(f"state saved: last_checked {started}, {len(args)} message(s) marked")
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
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
