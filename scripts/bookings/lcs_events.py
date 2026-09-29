#!/usr/bin/env python3
"""The state log: each fact about a booking or a singer invoice as one validated line in an append-only file,
~/lcs-private/events.jsonl (LCS_PRIVATE_DIR moves it), mode 600. Design and rules:
docs/superpowers/specs/2026-09-29-structured-state-design.md.

Not to be confused with ~/lcs-private/command-centre/events.jsonl, the Command Centre's push feed (cc_event.py):
the code calls this one the state log and that one the push feed, and neither reads the other.

One JSON object per line, keys sorted, no spaces, ending "\\n", at most LINE_MAX bytes:
    v 1 · eid 16 hex · prev (the first 16 hex of the sha256 of the previous line's bytes, "" on the first line)
    at (UTC, YYYY-MM-DDTHH:MM:SSZ) · on (the business day, YYYY-MM-DD, never after the London date of at)
    subject booking | singer_invoice · id (a booking ref, or a singer invoice's message id; never an "@")
    kind (KINDS) · fields (exactly the kind's keys) · by owner | script · src live | migration
    note (optional: note_hash of the note clause written with it, which the event "claims")
Every value is a date, an amount, an id, a hash or a word from a fixed list: no field takes free text, so no name,
email or bank number can reach the log. validate() runs on every write and every read.
"""

import datetime
import hashlib
import json
import os
import re
import secrets
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

LINE_MAX = 1024  # bytes of one line, its "\n" included
SUBJECTS = ("booking", "singer_invoice")
BY = ("owner", "script")
SRC = ("live", "migration")
TOP = {"v", "eid", "prev", "at", "on", "subject", "id", "kind", "fields", "by", "src"}  # plus the optional "note"
HEX16 = re.compile(r"[0-9a-f]{16}")
HEX12 = re.compile(r"[0-9a-f]{12}")
AT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
ON_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
ID_RE = {"booking": re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,19}"),  # a ledger booking_ref
         "singer_invoice": re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}")}  # a Zoho message id: no "@", so never an email
AMOUNT_RE = re.compile(r"\d{1,5}\.\d{2}")
FP8_RE = re.compile(r"(?:[0-9a-f]{8})?")  # the first 8 hex of the keyed bank fingerprint, or ""
ITEM_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")  # a Starling feed item uid
CODES = ("changed", "differ", "new", "not-yet-verified", "no-details")  # singer bank-warning codes


# --- field checkers: each returns True for a good value -------------------------------------------------------

def _word(*choices):
    return lambda x: isinstance(x, str) and x in choices


def _amount(cap=None):
    def ok(x):
        return (isinstance(x, str) and bool(AMOUNT_RE.fullmatch(x)) and float(x) > 0
                and (cap is None or float(x) <= cap() + 1e-9))
    return ok


def _pattern(rx):
    return lambda x: isinstance(x, str) and bool(rx.fullmatch(x))


def _fp8_set(x):
    return isinstance(x, str) and len(x) == 8 and bool(FP8_RE.fullmatch(x))


def _codes(x):
    return isinstance(x, list) and len(set(x)) == len(x) and all(isinstance(c, str) and c in CODES for c in x)


def _clauses(x):
    return (isinstance(x, list) and 1 <= len(x) <= 20
            and all(isinstance(c, str) and HEX12.fullmatch(c) for c in x))


_FEE = _amount(lambda: lm.FEE_CAP)
RETRACT = {"target": _pattern(HEX16), "why": _word("mistake", "write-failed")}
CHECKED = {"clauses": _clauses}

# (subject, kind) -> {field: checker}. A new kind of fact is a new line here, not a new pattern.
KINDS = {
    ("booking", "paid-in-full"): {"basis": _word("bank", "owner")},
    ("booking", "fees-accepted"): {"amount": _FEE},
    ("booking", "noted-paid"): {"scope": _word("part", "full")},
    ("booking", "arranged"): {"method": _word("cash", "cheque", "third-party")},
    ("booking", "cancelled"): {},
    ("booking", "reinstated"): {},
    ("booking", "deposit-kept"): {},
    ("booking", "refunded"): {},
    ("booking", "payment-checked"): {},
    ("booking", "deposit-seen"): {},
    ("booking", "reminder-drafted"): {"what": _word("deposit", "balance", "receipt")},
    ("booking", "review-drafted"): {},
    ("booking", "review-skipped"): {"reason": _word("planner", "unresolved")},
    # reserved for the later PR (confirm a payment, more shortfall reasons): validated, but append refuses them
    ("booking", "payment-confirmed"): {"item": _pattern(ITEM_RE), "amount": _amount()},
    ("booking", "discount-agreed"): {"amount": _amount()},
    ("booking", "goodwill-reduction"): {"amount": _amount()},
    ("booking", "overpayment-refunded"): {"amount": _amount()},
    ("booking", "retract"): RETRACT,
    ("booking", "notes-checked"): CHECKED,
    ("singer_invoice", "bank-warning"): {"fp8": _pattern(FP8_RE), "codes": _codes},
    ("singer_invoice", "bank-confirmed"): {"fp8": _fp8_set},
    ("singer_invoice", "settled"): {"amount": _amount()},
    ("singer_invoice", "withdrawn"): {"reason": _word("not-ours", "duplicate", "sent-in-error", "other")},
    ("singer_invoice", "paid-reply-drafted"): {},
    ("singer_invoice", "retract"): RETRACT,
    ("singer_invoice", "notes-checked"): CHECKED,
}
RESERVED = {"payment-confirmed", "discount-agreed", "goodwill-reduction", "overpayment-refunded"}
# Who may write which kind (spec, "Who may write which kind"). paid-in-full is the script's only as basis bank
# (from --apply), the owner's only as basis owner; retract {why: mistake} is the owner's.
OWNER_ONLY = {"fees-accepted", "reinstated", "deposit-kept", "refunded", "payment-checked", "notes-checked",
              "bank-confirmed", "settled"} | RESERVED
SCRIPT_ONLY = {"deposit-seen", "reminder-drafted", "review-drafted", "review-skipped", "bank-warning",
               "paid-reply-drafted"}


def _date(text):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def at_date(at):
    """The Europe/London date of an `at` stamp (YYYY-MM-DDTHH:MM:SSZ), or None when it isn't one."""
    if not isinstance(at, str) or not AT_RE.fullmatch(at):
        return None
    try:
        t = datetime.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None
    return lm.today(t)


def validate(obj):
    """obj when it is a well-formed state-log line, else ValueError with a fixed phrase (never the bad value)."""
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    keys = set(obj)
    if not TOP <= keys or keys - TOP - {"note"}:
        raise ValueError("wrong keys")
    if type(obj["v"]) is not int or obj["v"] != 1:
        raise ValueError("unknown version")
    if not _pattern(HEX16)(obj["eid"]):
        raise ValueError("bad eid")
    if not (obj["prev"] == "" or _pattern(HEX16)(obj["prev"])):
        raise ValueError("bad prev")
    day = at_date(obj["at"])
    if day is None:
        raise ValueError("bad at")
    on = _date(obj["on"]) if isinstance(obj["on"], str) and ON_RE.fullmatch(obj["on"]) else None
    if on is None or on > day:
        raise ValueError("bad on")
    subject, kind = obj["subject"], obj["kind"]
    if subject not in SUBJECTS:
        raise ValueError("bad subject")
    if not _pattern(ID_RE[subject])(obj["id"]):
        raise ValueError("bad id")
    if not isinstance(kind, str) or (subject, kind) not in KINDS:
        raise ValueError("unknown kind")
    fields, schema = obj["fields"], KINDS[(subject, kind)]
    if not isinstance(fields, dict) or set(fields) != set(schema):
        raise ValueError("wrong fields")
    for name, ok in schema.items():
        if not ok(fields[name]):
            raise ValueError(f"bad {name}")
    by = obj["by"]
    if by not in BY or obj["src"] not in SRC:
        raise ValueError("bad by or src")
    if (kind in OWNER_ONLY and by != "owner") or (kind in SCRIPT_ONLY and by != "script"):
        raise ValueError("not a kind this writer may record")
    if kind == "paid-in-full" and fields["basis"] != ("bank" if by == "script" else "owner"):
        raise ValueError("paid-in-full basis doesn't fit its writer")
    if kind == "retract" and fields["why"] == "mistake" and by != "owner":
        raise ValueError("only the owner retracts a mistake")
    if "note" in obj and not _pattern(HEX12)(obj["note"]):
        raise ValueError("bad note")
    return obj


def dumps(obj):
    """One line of the log, without its "\\n": sorted keys, no spaces, ASCII; ValueError over LINE_MAX bytes."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(text.encode()) + 1 > LINE_MAX:
        raise ValueError("line too long")
    return text


def note_hash(clause):
    """The claim an event makes on the note clause written with it: the first 12 hex of the sha256 of the clause
    as appended (UTF-8)."""
    return hashlib.sha256(clause.encode("utf-8")).hexdigest()[:12]


def chain_hash(raw):
    """prev for the line after `raw` (a whole line's bytes, its "\\n" included)."""
    return hashlib.sha256(raw).hexdigest()[:16]


# --- the file ----------------------------------------------------------------------------------------------------

class LogRefused(OSError):
    """The log is not a regular file of this user's with no group or other bits: nothing is read or written."""


def log_path():
    """<LCS_PRIVATE_DIR or ~/lcs-private>/events.jsonl, read at call time."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "events.jsonl"


def _check(st):
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise LogRefused("the state log must be a regular file of this user's, mode 600")


def _last_line(fd, size):
    """(the log's last line as bytes with its "\\n", or b"" for an empty file; True when the file doesn't end with
    "\\n", a write cut short). A cut-short tail counts as the last line: the next append ends it first."""
    buf, pos = b"", size
    while pos > 0:
        step = min(4096, pos)
        pos -= step
        buf = os.pread(fd, step, pos) + buf
        if b"\n" in buf[:-1]:
            break
    if not buf:
        return b"", False
    cut = not buf.endswith(b"\n")
    body = buf if cut else buf[:-1]
    return body[body.rfind(b"\n") + 1:] + b"\n", cut


def append(subject, id, kind, fields, by, on=None, note=None, src="live", eid=None):
    """Validate one fact and append it to the log; returns its eid. `on` (a date or YYYY-MM-DD) defaults to today
    in London. Refuses (ValueError) a bad line or a reserved kind, and (LogRefused, OSError) a log that is a symlink,
    another user's or has any group or other bit; either way nothing is written.

    The log's own lock (lm.ledger_lock on events.jsonl.lock) is taken here and only here, and nothing else is
    called under it. A writer calls this inside its CSV's locked_rows block, never around it (lock order: the
    CSV's, then the log's). One os.write of the whole line to an O_APPEND descriptor, then fsync."""
    if kind in RESERVED:
        raise ValueError("a kind reserved for a later change")
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    on = on.isoformat() if isinstance(on, datetime.date) else (on or lm.today(now).isoformat())
    obj = {"v": 1, "eid": eid or secrets.token_hex(8), "prev": "", "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "on": on, "subject": subject, "id": id, "kind": kind, "fields": fields, "by": by, "src": src}
    if note is not None:
        obj["note"] = note
    dumps(validate(obj))
    path = log_path()
    with lm.ledger_lock(path):
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            st = os.fstat(fd)
            _check(st)
            rfd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                rst = os.fstat(rfd)
                if (rst.st_dev, rst.st_ino) != (st.st_dev, st.st_ino):
                    raise LogRefused("the state log changed while it was opened")
                last, cut = _last_line(rfd, rst.st_size)
            finally:
                os.close(rfd)
            obj["prev"] = chain_hash(last) if last else ""
            data = (b"\n" if cut else b"") + dumps(obj).encode() + b"\n"
            if os.write(fd, data) != len(data):
                raise OSError("short write to the state log")
            os.fsync(fd)
        finally:
            os.close(fd)
    return obj["eid"]


_CACHE = {}


def clear_cache():
    _CACHE.clear()


def read(path=None):
    """(events in file order, stats) with stats = {lines, skipped, chain_ok, broken_at, last_at} (+ unreadable: True
    for a log that is a symlink, another user's, group or other readable, or can't be opened; it reads as absent).
    Lines that don't parse, fail validate(), run over LINE_MAX bytes, repeat an eid, or are a last line without
    "\\n" (a write in progress) are skipped and counted. The chain is checked over every complete line: broken_at
    is the first valid line whose prev doesn't fit the line before it. Cached per process on the file's identity,
    size and mtime; takes no lock. Callers must not modify what it returns."""
    path = Path(path or log_path())
    stats = {"lines": 0, "skipped": 0, "chain_ok": True, "broken_at": None, "last_at": None}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return [], stats
    except OSError:
        return [], dict(stats, unreadable=True)
    try:
        st = os.fstat(fd)
        try:
            _check(st)
        except LogRefused:
            return [], dict(stats, unreadable=True)
        key = (str(path), st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
        if key in _CACHE:
            return _CACHE[key]
        chunks = []
        while True:
            b = os.read(fd, 1 << 20)
            if not b:
                break
            chunks.append(b)
    finally:
        os.close(fd)
    lines = b"".join(chunks).split(b"\n")
    if lines.pop():  # a last line without "\n"
        stats["skipped"] += 1
    events, seen, prev = [], set(), ""
    for n, raw in enumerate(lines, 1):
        whole = raw + b"\n"
        stats["lines"] += 1
        obj = None
        if len(whole) <= LINE_MAX:
            try:
                obj = validate(json.loads(raw.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                obj = None
        if obj is None or obj["eid"] in seen:
            stats["skipped"] += 1
        else:
            if obj["prev"] != prev and stats["chain_ok"]:
                stats["chain_ok"], stats["broken_at"] = False, n
            seen.add(obj["eid"])
            events.append(obj)
            stats["last_at"] = obj["at"]
        prev = chain_hash(whole)
    _CACHE.clear()  # one log per process in practice: keep only the latest reading
    _CACHE[key] = (events, stats)
    return events, stats


def index(events, today):
    """{(subject, id): [events in file order]}, each a copy with "retracted" set when a later retract of the same
    subject and id names it (a retract is never itself retracted). Events whose `on` is after today are left out,
    retracts too. Readers skip retracted events for the reading but count them for "the family has events" and
    keep their note claims."""
    live = [e for e in events if _date(e["on"]) <= today]
    seen, gone = {}, set()
    for e in live:
        if e["kind"] == "retract":
            t = seen.get(e["fields"]["target"])
            if t and t["kind"] != "retract" and (t["subject"], t["id"]) == (e["subject"], e["id"]):
                gone.add(t["eid"])
        seen[e["eid"]] = e
    out = {}
    for e in live:
        out.setdefault((e["subject"], e["id"]), []).append(dict(e, retracted=e["eid"] in gone))
    return out
