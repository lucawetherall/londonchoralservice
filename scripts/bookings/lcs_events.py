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
import json
import re
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
