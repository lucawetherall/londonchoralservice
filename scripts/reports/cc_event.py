#!/usr/bin/env python3
"""Append one event for the Command Centre's push notifications. A kind plus validated fields, never free text:

    .venv/bin/python scripts/reports/cc_event.py enquiry --first <Name> --occasion <occasion> --date <YYYY-MM-DD|tbc>
    .venv/bin/python scripts/reports/cc_event.py deposit --first <Name> --ref <ref>
    .venv/bin/python scripts/reports/cc_event.py hand-check --ref <ref> --state <state>
    .venv/bin/python scripts/reports/cc_event.py bank-change --first <Name>
    .venv/bin/python scripts/reports/cc_event.py guard-denied --agent <reply-drafter|singer-clerk|daily-pass|monday>
    .venv/bin/python scripts/reports/cc_event.py run-failed
    .venv/bin/python scripts/reports/cc_event.py monday-ready

- A first name is one capitalised word: ^[A-Z][a-z'’-]{1,20}$ (no surname, email, number or sentence fits).
- A booking ref is ^[A-Z0-9-]{3,20}$.
- An occasion is one of OCCASIONS, a hand-check state one of STATES (check_payments.py's hand-check states), an
  agent one of AGENTS, a date YYYY-MM-DD or "tbc".

The line goes to ~/lcs-private/command-centre/events.jsonl (LCS_PRIVATE_DIR moves it; the file is mode 600 in a
mode-700 folder, appended under an flock) as {"at", "kind", "fields"}. The app validates the fields again when it
reads the line and builds the notification from a fixed template per kind (command_centre/push.py), so nothing a
prompt or an email says can reach the lock screen except a first name, a ref, a date and words from fixed lists.

It writes nothing else, reads nothing private and needs no network, so the scheduled prompts may run it
unattended (it is on the .claude/settings.json allowlist).
"""
import argparse
import datetime
import fcntl
import json
import os
import re
import sys
from pathlib import Path

FIRST_RE = re.compile(r"^[A-Z][a-z'’-]{1,20}$")
REF_RE = re.compile(r"^[A-Z0-9-]{3,20}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OCCASIONS = ("wedding", "funeral", "christmas", "corporate", "private-event", "other")
STATES = ("CHECK_PAYMENT", "CHECK_VALUE", "NOTED_PAID", "PAST_UNMATCHED", "PAST_PART_PAID", "PAYMENT_ON_CANCELLED",
          "PAYMENT_AFTER_CLOSE", "ARRANGED")
AGENTS = ("reply-drafter", "singer-clerk", "daily-pass", "monday")
# kind -> the fields it takes (all required); nothing else is accepted
KINDS = {
    "enquiry": ("first", "occasion", "date"),
    "deposit": ("first", "ref"),
    "hand-check": ("ref", "state"),
    "bank-change": ("first",),
    "guard-denied": ("agent",),
    "run-failed": (),
    "monday-ready": (),
}


def _first(v):
    if not FIRST_RE.fullmatch(v):
        raise ValueError("--first must be one capitalised first name (letters, ' or -, 2 to 21 characters)")
    return v


def _ref(v):
    if not REF_RE.fullmatch(v):
        raise ValueError("--ref must be 3 to 20 capital letters, digits or -")
    return v


def _occasion(v):
    v = v.strip().lower().replace(" ", "-")
    if v not in OCCASIONS:
        raise ValueError(f"--occasion must be one of: {', '.join(OCCASIONS)}")
    return v


def _date(v):
    if v == "tbc":
        return v
    if not DATE_RE.fullmatch(v):
        raise ValueError("--date must be YYYY-MM-DD or tbc")
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        raise ValueError("--date must be YYYY-MM-DD or tbc") from None
    return v


def _state(v):
    if v not in STATES:
        raise ValueError(f"--state must be one of: {', '.join(STATES)}")
    return v


def _agent(v):
    if v not in AGENTS:
        raise ValueError(f"--agent must be one of: {', '.join(AGENTS)}")
    return v


CHECKS = {"first": _first, "ref": _ref, "occasion": _occasion, "date": _date, "state": _state, "agent": _agent}


def validate(kind, fields):
    """The fields for `kind`, checked (exactly the kind's fields, each a string that passes its check), or
    ValueError. The app calls this again on every line it reads."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind (one of: {', '.join(KINDS)})")
    fields = {} if fields is None else fields
    if not isinstance(fields, dict) or set(fields) != set(KINDS[kind]):
        raise ValueError(f"{kind} takes exactly: {', '.join('--' + f for f in KINDS[kind]) or 'no fields'}")
    out = {}
    for name in KINDS[kind]:
        value = fields[name]
        if not isinstance(value, str):
            raise ValueError(f"--{name} must be text")
        out[name] = CHECKS[name](value)
    return out


def events_path():
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "events.jsonl"


def append(kind, fields=None, now=None):
    """Append one event; returns the dict written. ValueError for an unknown kind or a field that fails."""
    fields = validate(kind, fields)
    at = (now or datetime.datetime.now(datetime.timezone.utc)).isoformat(timespec="seconds")
    event = {"at": at, "kind": kind, "fields": fields}
    path = events_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    return event


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # a usage error exits 2 without echoing the arguments back
        self.print_usage(sys.stderr)
        print(f"cc_event: {message.split(':')[0]}", file=sys.stderr)
        sys.exit(2)


def parser():
    ap = _Parser(prog="cc_event.py", description="Append one Command Centre push event (fixed templates).")
    sub = ap.add_subparsers(dest="kind", required=True, parser_class=_Parser)
    for kind, names in KINDS.items():
        p = sub.add_parser(kind)
        for name in names:
            p.add_argument(f"--{name}", required=True)
    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = parser().parse_args(argv)
    fields = {name: getattr(args, name) for name in KINDS[args.kind]}
    try:
        event = append(args.kind, fields)
    except (ValueError, OSError) as e:
        print(f"cc_event: {e if isinstance(e, ValueError) else type(e).__name__}", file=sys.stderr)
        return 1
    print(f"event recorded: {event['kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
