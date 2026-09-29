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

import contextlib
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
import lcs_owner  # noqa: E402

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


def _amount():
    return lambda x: isinstance(x, str) and bool(AMOUNT_RE.fullmatch(x)) and float(x) > 0


def _pattern(rx):
    return lambda x: isinstance(x, str) and bool(rx.fullmatch(x))


def _fp8_set(x):
    return isinstance(x, str) and len(x) == 8 and bool(FP8_RE.fullmatch(x))


def _codes(x):
    return isinstance(x, list) and len(set(x)) == len(x) and all(isinstance(c, str) and c in CODES for c in x)


def _clauses(x):
    return (isinstance(x, list) and 1 <= len(x) <= 20
            and all(isinstance(c, str) and HEX12.fullmatch(c) for c in x))


RETRACT = {"target": _pattern(HEX16), "why": _word("mistake", "write-failed")}
CHECKED = {"clauses": _clauses}

# (subject, kind) -> {field: checker}. A new kind of fact is a new line here, not a new pattern.
KINDS = {
    ("booking", "paid-in-full"): {"basis": _word("bank", "owner")},
    ("booking", "fees-accepted"): {"amount": _amount()},  # at most FEE_CAP when written (validate, write=True)
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


AT_AHEAD = datetime.timedelta(days=1)  # an `at` further ahead of now than this is a clock or hand error: refused


def validate(obj, write=False):
    """obj when it is a well-formed state-log line, else ValueError with a fixed phrase (never the bad value).
    write=True (append) also holds a fees-accepted amount to today's FEE_CAP; a reader takes any fee that was
    valid when written, so lowering the cap later never reopens a booking it closed."""
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
    if _at(obj) - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) > AT_AHEAD:
        raise ValueError("at is in the future")
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
    if write and kind == "fees-accepted" and float(fields["amount"]) > lm.FEE_CAP + 1e-9:
        raise ValueError("bad amount")
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


class OwnerRefused(ValueError):
    """An owner fact without the owner's proof in this process: nothing is written."""


def log_path():
    """<LCS_PRIVATE_DIR or ~/lcs-private>/events.jsonl, read at call time."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "events.jsonl"


_write = os.write  # the one write of a line (tests replace it to cut a write short)


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
    in London. Refuses (ValueError) a bad line or a reserved kind; (OwnerRefused) by: owner unless this process
    passed lcs_owner.owner_confirmed() (the Command Centre's one-time nonce) and the log sits in the nonce's private
    folder with no LCS_BOOKINGS_CSV (lcs_owner.owner_folder_problem); and (LogRefused, OSError) a log that is a
    symlink, another user's or has any group or other bit. In each case nothing is written.

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
    dumps(validate(obj, write=True))
    path = log_path()
    if by == "owner" and (not lcs_owner.owner_proven() or lcs_owner.owner_folder_problem([path])):
        raise OwnerRefused("an owner fact needs the Command Centre's owner nonce in this run")
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
            try:
                if _write(fd, data) != len(data):
                    raise OSError("short write to the state log")
                os.fsync(fd)
            except BaseException:
                # a line cut short (even one missing only its "\n") would be revived by the next append: put the
                # file back as it was, under the same lock, then report the failure
                os.ftruncate(fd, rst.st_size)
                raise
        finally:
            os.close(fd)
    return obj["eid"]


# --- writers: a fact and its note under the CSV's lock ---------------------------------------------------------------

def loggable(subject, id):
    """True when `id` can go in the log for this subject (ID_RE)."""
    return isinstance(id, str) and bool(ID_RE[subject].fullmatch(id))


def record(table, subject, id, kind, fields, by, clause, on=None):
    """Inside a writer's recording() block, once the row it edits carries `clause` (the note clause exactly as
    appended, or None for a fact with no note): append the fact claiming that clause, and have locked_rows withdraw
    it (a write-failed retract by the same writer, still under the CSV's lock) should the rows not be written after
    all. Returns the eid. Record a fact only after every refusal the writer makes: a refusal after it withdraws it.
    A legacy id the log can't take (loggable() false: a space, a slash, an "@") records nothing and returns None: no
    fact can ever exist for it, so its readers keep reading its notes and columns, as before."""
    if not loggable(subject, id):
        return None
    try:
        eid = append(subject, id, kind, fields, by, on=on, note=note_hash(clause) if clause else None)
    except (ValueError, OSError):
        table.log_refused = True
        raise

    def undo():
        try:
            append(subject, id, "retract", {"target": eid, "why": "write-failed"}, by)
        except Exception:  # the note is not written and the fact stands: events.py verify lists it
            table.undo_failed = True
    table.if_unwritten.append(undo)
    return eid


@contextlib.contextmanager
def recording(path, columns=None):
    """lm.locked_rows for a writer that records facts (record()): the CSV's lock first, the log's inside each append.
    If the rows are not written after a fact was recorded (the block raised, or the CSV write failed), the facts are
    withdrawn and this ends in SystemExit: "nothing written (<error type>) …", or, when a withdrawal failed too,
    "fact recorded, note not written …: run events.py verify" (the fact decides; the note is the human record).
    A fact the log refuses (a bad value, an owner fact without the owner's proof, an unsafe log file) ends in
    SystemExit too, with nothing written anywhere."""
    table = None
    try:
        with lm.locked_rows(path, columns) as table:
            yield table
    except (ValueError, OSError) as e:
        if table is not None and table.if_unwritten:
            if getattr(table, "undo_failed", False):
                raise SystemExit(f"fact recorded, note not written ({type(e).__name__}): run events.py verify") from None
            raise SystemExit(f"nothing written ({type(e).__name__}): the recorded fact was withdrawn") from None
        if table is not None and getattr(table, "log_refused", False):
            raise SystemExit(f"the state log refused it ({e}); nothing written") from None
        raise


_CACHE = {}


_open = os.open  # opening the log to parse it (tests count the calls)
# the readings of a missing and of an unreadable log: shared, so the index and Facts caches hold across calls
_ABSENT = ([], {"lines": 0, "skipped": 0, "chain_ok": True, "broken_at": None, "last_at": None})
_UNREADABLE = ([], dict(_ABSENT[1], unreadable=True))


def clear_cache():
    _CACHE.clear()
    _INDEXED.clear()


def read(path=None):
    """(events in file order, stats) with stats = {lines, skipped, chain_ok, broken_at, last_at} (+ unreadable: True
    for a log that is a symlink, another user's, group or other readable, or can't be opened; it reads as absent).
    Lines that don't parse, fail validate(), run over LINE_MAX bytes, repeat an eid, or are a last line without
    "\\n" (a write in progress) are skipped and counted. The chain is checked over every complete line: broken_at
    is the first valid line whose prev doesn't fit the line before it. Cached per process on the file's identity,
    size, mtime, mode and owner, checked with one lstat per call, so an unchanged log is never reopened or parsed
    again; takes no lock. Callers must not modify what it returns."""
    path = Path(path or log_path())
    try:
        lst = os.lstat(path)
    except FileNotFoundError:
        return _ABSENT
    except OSError:
        return _UNREADABLE
    key = (str(path), lst.st_dev, lst.st_ino, lst.st_size, lst.st_mtime_ns, lst.st_mode, lst.st_uid)
    if key in _CACHE:
        return _CACHE[key]
    stats = {"lines": 0, "skipped": 0, "chain_ok": True, "broken_at": None, "last_at": None}
    try:
        fd = _open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return _ABSENT
    except OSError:
        return _UNREADABLE
    try:
        st = os.fstat(fd)
        try:
            _check(st)
            if (st.st_dev, st.st_ino) != (lst.st_dev, lst.st_ino):
                raise LogRefused("the state log changed while it was opened")
        except LogRefused:
            return _UNREADABLE
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


RUN_SECONDS = 120  # a write-failed retract comes from its target's own run: written within this long after it


def _at(e):
    return datetime.datetime.strptime(e["at"], "%Y-%m-%dT%H:%M:%SZ")


def retracts(t, e):
    """True when retract `e` undoes `t`: an earlier fact (never a retract) of the same subject and id. A mistake is
    the owner's (validate); a write-failed retract counts only from the target's own writer (the same `by`) in the
    same run (0 to RUN_SECONDS after it), so a script can never undo an owner fact that way."""
    if not t or t["kind"] == "retract" or (t["subject"], t["id"]) != (e["subject"], e["id"]):
        return False
    if e["fields"]["why"] == "mistake":
        return True
    gap = (_at(e) - _at(t)).total_seconds()
    return e["by"] == t["by"] and 0 <= gap <= RUN_SECONDS


UNREADABLE = ("the state log can't be read (it must be a regular file of this user's, mode 600, never a link): "
              "every reader treats it as absent")


def log_problem(stats=None):
    """None when the log is whole (or doesn't exist yet), else one line for the Health page and events.py verify:
    unreadable (which every reader treats as absent, so it must never pass quietly), a broken chain, skipped lines."""
    stats = read()[1] if stats is None else stats
    if stats.get("unreadable"):
        return UNREADABLE
    parts = [f"the state log's chain is broken at line {stats['broken_at']}"] if not stats["chain_ok"] else []
    if stats["skipped"]:
        parts.append(f"{stats['skipped']} line{'' if stats['skipped'] == 1 else 's'} skipped")
    return "; ".join(parts) or None


def index(events, today):
    """{(subject, id): [events in file order]}, each a copy with "retracted" set to the retract's why ("mistake" or
    "write-failed") when a later retract undoes it (retracts()), else False. Events whose `on` is after today are
    left out, retracts too. Readers skip retracted events for the reading. A fact retracted by mistake is history:
    it still counts for "the family has events" and keeps its note claim (precedence rule 2). A fact retracted as
    write-failed never happened: it counts for nothing and claims nothing, so a note that did land is read."""
    live = [e for e in events if _date(e["on"]) <= today]
    seen, gone = {}, {}
    for e in live:
        if e["kind"] == "retract" and retracts(seen.get(e["fields"]["target"]), e):
            gone.setdefault(e["fields"]["target"], e["fields"]["why"])
        seen[e["eid"]] = e
    out = {}
    for e in live:
        out.setdefault((e["subject"], e["id"]), []).append(dict(e, retracted=gone.get(e["eid"], False)))
    return out


# --- facts: what the log says about one booking or invoice, per family -----------------------------------------

# A family decides one question (spec, "Families"). Markers are a union with the notes; every other family, once
# it has events for a subject (retracted ones count: they are history), is read from them and not the notes.
FAMILIES = {
    "booking": {"close": {"paid-in-full", "fees-accepted"}, "cancellation": {"cancelled", "reinstated"},
                "cancel settlement": {"deposit-kept", "refunded", "payment-checked"}, "arrangement": {"arranged"},
                "noted paid": {"noted-paid"},
                "markers": {"deposit-seen", "reminder-drafted", "review-drafted", "review-skipped"}},
    "singer_invoice": {"bank warnings": {"bank-warning"}, "bank trust": {"bank-confirmed"}, "settlement": {"settled"},
                       "withdrawal": {"withdrawn"}, "markers": {"paid-reply-drafted"}},
}


class Facts:
    """The recorded facts for one booking or singer invoice (its index() list), read per family. Nothing here
    reads notes: check_payments and singer_invoices decide, per family, between these and the notes.

    families: the families with events (retracted by mistake included: history); claims: the note hashes of those
    events plus the clauses a live notes-checked confirmed. A fact retracted as write-failed is in neither."""

    def __init__(self, subject, events=()):
        self.subject, self.events = subject, list(events)
        self.live = [e for e in self.events if not e.get("retracted")]
        kept = [e for e in self.events if e.get("retracted") != "write-failed"]
        self.families = {fam for e in kept for fam, kinds in FAMILIES[subject].items() if e["kind"] in kinds}
        self.claims = ({e["note"] for e in kept if e.get("note")}
                       | {c for e in self.live if e["kind"] == "notes-checked" for c in e["fields"]["clauses"]})

    def has(self, family):
        return family in self.families

    def of(self, *kinds):
        """Live events of these kinds, in file order."""
        return [e for e in self.live if e["kind"] in kinds]

    def _latest_on(self, *kinds):
        return max((_date(e["on"]) for e in self.of(*kinds)), default=None)

    # --- bookings
    @property
    def closed_on(self):
        return self._latest_on("paid-in-full", "fees-accepted")

    @property
    def paid_full_on(self):
        return self._latest_on("paid-in-full")

    @property
    def fees(self):
        """[(date, amount)] of the live fees-accepted facts, in file order (fee_notes' shape)."""
        return [(_date(e["on"]), float(e["fields"]["amount"])) for e in self.of("fees-accepted")]

    @property
    def cancelled(self):
        """The later of cancelled and reinstated by (on, file order); False with neither live."""
        last = max(enumerate(self.of("cancelled", "reinstated")), key=lambda x: (x[1]["on"], x[0]), default=None)
        return bool(last and last[1]["kind"] == "cancelled")

    @property
    def settled_on(self):
        return self._latest_on("deposit-kept", "refunded", "payment-checked")

    @property
    def arranged(self):
        return bool(self.of("arranged"))

    @property
    def noted_part(self):
        return bool(self.of("noted-paid"))

    @property
    def noted_full(self):
        return any(e["fields"]["scope"] == "full" for e in self.of("noted-paid"))

    @property
    def deposit_seen(self):
        return bool(self.of("deposit-seen"))

    @property
    def reminded(self):
        return {w: any(e["fields"]["what"] == w for e in self.of("reminder-drafted")) for w in ("deposit", "balance", "receipt")}

    @property
    def review(self):
        return bool(self.of("review-drafted", "review-skipped"))

    # --- singer invoices
    @property
    def warning(self):
        """The latest live bank-warning's (fp8, codes), or None."""
        w = self.of("bank-warning")
        return (w[-1]["fields"]["fp8"], list(w[-1]["fields"]["codes"])) if w else None

    @property
    def confirmed_fp8s(self):
        return {e["fields"]["fp8"] for e in self.of("bank-confirmed")}

    @property
    def settled(self):
        return bool(self.of("settled"))

    @property
    def withdrawn_on(self):
        return self._latest_on("withdrawn")

    @property
    def thanked(self):
        return bool(self.of("paid-reply-drafted"))


_INDEXED = {}


def _indexed(today):
    """(index(read()) for today, its Facts cache), both kept while the log is unchanged (read() then returns the
    same list), so a reader asking row by row never rebuilds either."""
    events, _ = read()
    if _INDEXED.get("events") is not events or _INDEXED.get("today") != today:
        _INDEXED.update(events=events, today=today, index=index(events, today), facts={})
    return _INDEXED["index"], _INDEXED["facts"]


def facts(subject, id, today, events=None):
    """Facts for one subject: from `events` (a list of validated events, as tests pass) or else the log (cached per
    log snapshot and day; callers must not modify what they get)."""
    if events is not None:
        return Facts(subject, index(events, today).get((subject, id), []))
    idx, made = _indexed(today)
    if (subject, id) not in made:
        made[(subject, id)] = Facts(subject, idx.get((subject, id), []))
    return made[(subject, id)]


def booking_facts(ref, today, events=None):
    return facts("booking", ref, today, events)


def invoice_facts(message_id, today, events=None):
    return facts("singer_invoice", message_id, today, events)
