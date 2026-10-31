#!/usr/bin/env python3
"""The Monday review's private memory: what it proposed, what the owner decided, and what it means to check later.

One JSON object per line in ~/lcs-private/review-proposals.jsonl (LCS_PRIVATE_DIR respected; mode 600, written
atomically under lcs_money's file lock):

    {"id": "2026-10-26-04", "date": "2026-10-26", "kind": "site", "text": "…", "status": "open",
     "decided": "", "note": ""}

kind is ads, site, growth, manual, upload, budget or send (the dispatcher's [tag]; an untagged item is "other"), or
"watch" for a thing to check later, which also carries "due": "YYYY-MM-DD". status is open, approved, done,
dropped or expired. The review file itself (~/lcs-private/reports/reviews/<date>.md) is written by the dispatcher.

    review_log.py record <review file> [--date YYYY-MM-DD]
        the numbered items under "## Decisions" (lines "1. …") and the numbered or bulleted lines under "## Watch"
        (each may end "(due YYYY-MM-DD)"; without one it is due the Monday after the review). Ids are <date>-NN
        in order. A line starting with an earlier id ("2026-10-26-04 · …") is that item carried forward, not a new
        one. A rerun for the same date replaces that date's open items; decided ones keep their ids. Refuses the
        whole file (nothing recorded) if an item holds an email address or a UK phone number. The date comes from
        the file name (<date>.md) unless --date.
    review_log.py decide <id>[,<id>…] approved|dropped [--note TEXT]
    review_log.py done <id>[,<id>…] --note TEXT
    review_log.py note <id> TEXT              appends to the item's note (the review's own running notes)
    review_log.py open [--before YYYY-MM-DD]
        open items oldest first, "<id> · <kind> · <text>" or "<id> · watch · due <date> · <text>". First marks
        expired every proposal open more than 28 days and every watch item more than 14 days past its due date.

An unknown id exits 2 and changes nothing. Proposals name pages, campaigns and figures only: never a client's
name, email or phone number.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import lcs_money as lm  # noqa: E402  PRIVATE, ledger_lock, today

STORE = lm.PRIVATE / "review-proposals.jsonl"
KINDS = ("ads", "site", "growth", "manual", "upload", "budget", "send")
STATUSES = ("open", "approved", "done", "dropped", "expired")
OPEN_DAYS, WATCH_GRACE_DAYS = 28, 14
ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}$")
CARRIED = re.compile(r"^\W*(\d{4}-\d{2}-\d{2}-\d{2})\b\W*")
TAG = re.compile(r"\s*\**\[([A-Za-z]+)\]\**\s*")
DUE = re.compile(r"\s*\(due (\d{4}-\d{2}-\d{2})\)\s*$", re.I)
EMAIL = re.compile(r"@")
# A UK number: 0 then 9 or 10 digits, spaced any way (020 7946 0958, 07700 900123, 01632 960123), or +44 for the 0.
PHONE = re.compile(r"(?<![\d£.,])0(?:[ -]?\d){9,10}\b|\+44[ -]?(?:\(0\)[ -]?)?\d(?:[ -]?\d){8,9}\b")
DECISION_LINE = re.compile(r"^\s*\d+\.\s+(.*\S)")
WATCH_LINE = re.compile(r"^\s*(?:\d+\.|[-*•])\s+(.*\S)")


class Refused(SystemExit):
    pass


def has_contact(text):
    return bool(EMAIL.search(text or "") or PHONE.search(text or ""))


def check_clean(text, what):
    if has_contact(text):
        raise Refused(f"refused: {what} holds an email address or a phone number; nothing recorded")


def to_date(s):
    try:
        return datetime.date.fromisoformat(str(s or "")[:10])
    except ValueError:
        return None


def next_monday(day):
    return day + datetime.timedelta(days=7 - day.weekday())


# ---------- the file ----------

def read_items(path=None):
    """The items, oldest first (read-only; a missing file is no items). A line that isn't a JSON object stops
    everything, so a rewrite can never drop it."""
    path = Path(path or STORE)
    if not path.exists():
        return []
    items = []
    for n, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except ValueError:
            obj = None
        if not isinstance(obj, dict) or not ID_RE.match(str(obj.get("id", ""))):
            raise SystemExit(f"{path.name} line {n} is not a review item; nothing changed")
        items.append(obj)
    return sorted(items, key=lambda i: i["id"])


def write_items(items, path=None):
    path = Path(path or STORE)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for i in sorted(items, key=lambda i: i["id"]):
                f.write(json.dumps(i, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# ---------- parsing a review file ----------

def _section(text, name):
    """The lines under "## <name>" up to the next heading of level 1 or 2."""
    out, inside = [], False
    for ln in (text or "").splitlines():
        if re.match(r"^#{1,2}\s", ln):
            inside = bool(re.match(rf"^##\s+{name}\b", ln, re.I))
            continue
        if inside:
            out.append(ln)
    return out


def _kind_and_text(text):
    m = TAG.search(text)
    if m and m.group(1).lower() in KINDS:
        return m.group(1).lower(), (text[:m.start()] + " " + text[m.end():]).strip()
    return "other", text.strip()


def parse_review(text, review_date):
    """([(kind, text, carried id or None)], [(text, due date)]) from a review file's Decisions and Watch."""
    decisions, watch = [], []
    for ln in _section(text, "Decisions"):
        m = DECISION_LINE.match(ln)
        if not m:
            continue
        body = m.group(1)
        c = CARRIED.match(body)
        carried = c.group(1) if c else None
        if c:
            body = body[c.end():]
        kind, body = _kind_and_text(body)
        decisions.append((kind, body, carried))
    for ln in _section(text, "Watch"):
        m = WATCH_LINE.match(ln)
        if not m:
            continue
        body = m.group(1)
        c = CARRIED.match(body)
        if c:  # an earlier watch item restated: it is already recorded
            continue
        d = DUE.search(body)
        due = to_date(d.group(1)) if d else None
        if d:
            body = body[:d.start()]
        watch.append((body.strip(), due or next_monday(review_date)))
    return decisions, watch


# ---------- commands ----------

def record(review_path, review_date=None, store=None):
    """Record a review file's items; returns the printed lines."""
    review_path = Path(review_path)
    day = review_date or to_date(review_path.stem)
    if not day:
        raise SystemExit("no date: name the file <YYYY-MM-DD>.md or pass --date")
    text = review_path.read_text(encoding="utf-8")
    decisions, watch = parse_review(text, day)
    for n, (_, body, carried) in enumerate(decisions, 1):
        if not carried:
            check_clean(body, f"item {n} under Decisions")
    for n, (body, _) in enumerate(watch, 1):
        check_clean(body, f"item {n} under Watch")
    store = Path(store or STORE)
    out = []
    with lm.ledger_lock(store):
        items = read_items(store)
        all_ids = {i["id"] for i in items}
        kept = [i for i in items if not (i["date"] == day.isoformat() and i["status"] == "open")]
        decided_today = {i["text"]: i["id"] for i in kept if i["date"] == day.isoformat()}
        used = {i["id"] for i in kept}
        counter = [0]

        def next_id():
            while True:
                counter[0] += 1
                nid = f"{day.isoformat()}-{counter[0]:02d}"
                if nid not in used:
                    used.add(nid)
                    return nid
        new = []
        for kind, body, carried in decisions:
            if carried and carried in all_ids:
                out.append(f"{carried} (carried) {body}")
                continue
            if carried:
                check_clean(body, "a carried item")
            if body in decided_today:
                out.append(f"{decided_today[body]} (already decided) {body}")
                continue
            nid = next_id()
            new.append({"id": nid, "date": day.isoformat(), "kind": kind, "text": body, "status": "open",
                        "decided": "", "note": ""})
            out.append(f"{nid} {body}")
        for body, due in watch:
            if body in decided_today:
                out.append(f"{decided_today[body]} (already decided) {body}")
                continue
            nid = next_id()
            new.append({"id": nid, "date": day.isoformat(), "kind": "watch", "text": body, "status": "open",
                        "decided": "", "note": "", "due": due.isoformat()})
            out.append(f"{nid} watch, due {due} · {body}")
        write_items(kept + new, store)
    return out or ["no numbered items under ## Decisions or ## Watch"]


def _add_note(item, text):
    item["note"] = "; ".join(x for x in ((item.get("note") or "").strip(), text.strip()) if x)


def expire(items, today):
    """Mark expired, in place, every proposal open more than OPEN_DAYS days and every watch item open more than
    WATCH_GRACE_DAYS days past its due date. Returns how many."""
    n = 0
    for i in items:
        if i.get("status") != "open":
            continue
        if i.get("kind") == "watch":
            due = to_date(i.get("due")) or to_date(i.get("date"))
            late = due and (today - due).days > WATCH_GRACE_DAYS
        else:
            made = to_date(i.get("date"))
            late = made and (today - made).days > OPEN_DAYS
        if late:
            i.update(status="expired", decided=today.isoformat())
            _add_note(i, f"expired {today}")
            n += 1
    return n


def item_line(i):
    if i.get("kind") == "watch":
        return f"{i['id']} · watch · due {i.get('due', '?')} · {i['text']}"
    return f"{i['id']} · {i.get('kind', 'other')} · {i['text']}"


def open_items(items, today, before=None):
    """The open items, oldest first, after expiry (applied to copies: the caller's items are not changed)."""
    copies = [dict(i) for i in items]
    expire(copies, today)
    return [i for i in copies if i.get("status") == "open" and (before is None or i["date"] < before.isoformat())]


def _ids(arg):
    ids = [x.strip() for x in arg.split(",") if x.strip()]
    if not ids:
        raise SystemExit(2)
    return ids


def change(ids, edit, store=None, today=None):
    """Apply edit(item) to each id under the lock; an unknown id exits 2 with nothing changed."""
    store = Path(store or STORE)
    with lm.ledger_lock(store):
        items = read_items(store)
        by = {i["id"]: i for i in items}
        unknown = [x for x in ids if x not in by]
        if unknown:
            print(f"unknown id: {', '.join(unknown)}; nothing changed", file=sys.stderr)
            raise SystemExit(2)
        for x in ids:
            edit(by[x])
        write_items(items, store)


def main(argv=None):
    p = argparse.ArgumentParser(description="The Monday review's record of proposals and watch items (private).")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("file")
    r.add_argument("--date", type=datetime.date.fromisoformat)
    d = sub.add_parser("decide")
    d.add_argument("ids")
    d.add_argument("status", choices=("approved", "dropped"))
    d.add_argument("--note", default="")
    dn = sub.add_parser("done")
    dn.add_argument("ids")
    dn.add_argument("--note", required=True)
    nt = sub.add_parser("note")
    nt.add_argument("id")
    nt.add_argument("text", nargs="+")
    o = sub.add_parser("open")
    o.add_argument("--before", type=datetime.date.fromisoformat)
    for sp in (r, d, dn, nt, o):
        sp.add_argument("--today", type=datetime.date.fromisoformat, help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    today = args.today or lm.today()
    try:
        if args.cmd == "record":
            for ln in record(args.file, args.date):
                print(ln)
        elif args.cmd in ("decide", "done"):
            note = args.note.strip()
            check_clean(note, "the note")
            status = args.status if args.cmd == "decide" else "done"

            def edit(i):
                i["status"] = status
                if args.cmd == "done":
                    i["done"] = today.isoformat()
                if not i.get("decided") or args.cmd == "decide":
                    i["decided"] = today.isoformat()
                if note:
                    _add_note(i, note)
            ids = _ids(args.ids)
            change(ids, edit)
            print(f"{', '.join(ids)}: {status}")
        elif args.cmd == "note":
            text = " ".join(args.text).strip()
            if not text:
                raise SystemExit("an empty note")
            check_clean(text, "the note")
            change([args.id], lambda i: _add_note(i, text))
            print(f"{args.id}: note added")
        elif args.cmd == "open":
            with lm.ledger_lock(STORE):
                items = read_items()
                if expire(items, today):
                    write_items(items)
            shown = [i for i in items if i.get("status") == "open"
                     and (args.before is None or i["date"] < args.before.isoformat())]
            for i in shown:
                print(item_line(i))
            if not shown:
                print("(no open items)")
    except Refused as e:
        print(e.code, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
