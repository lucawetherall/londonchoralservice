#!/usr/bin/env python3
"""Append one event for the Command Centre's push notifications.

    .venv/bin/python scripts/reports/cc_event.py <kind> '<short text>'

Kinds: enquiry, deposit, bank-change, guard-denied, run-failed, monday-ready, hand-check.

The line goes to ~/lcs-private/command-centre/events.jsonl (LCS_PRIVATE_DIR moves it; the file is mode 600 in
a mode-700 folder, appended under an flock) as {"at", "kind", "text"}. The app watches that file and pushes a
notification with a title for the kind and this text. First names only: emails, links and runs of six or more
digits (phone numbers, account numbers, message ids) are removed here, and the app removes every known client
and singer surname again before it pushes. The text is cut to 80 characters.

It writes nothing else, reads nothing private and needs no network, so the scheduled prompts may run it
unattended (it is on the .claude/settings.json allowlist).
"""
import datetime
import fcntl
import json
import os
import re
import sys
from pathlib import Path

KINDS = ("enquiry", "deposit", "bank-change", "guard-denied", "run-failed", "monday-ready", "hand-check")
TEXT_MAX = 80
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL_RE = re.compile(r"(?i)\b(?:https?|ftp)://\S+|\bwww\.\S+")
PHONE_RE = re.compile(r"(?:\+44\s?\(?0?\)?\s?|\b0)\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b")  # a UK number with spaces or dashes
DIGITS_RE = re.compile(r"\d{6,}")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]+")


def clean_text(text, most=TEXT_MAX):
    """One line, no email, link, phone number or long digit run, at most `most` characters."""
    text = CONTROL_RE.sub(" ", str(text))
    for rx in (EMAIL_RE, URL_RE, PHONE_RE, DIGITS_RE):
        text = rx.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;:-")
    if len(text) > most:
        text = text[:most - 1].rstrip() + "…"
    return text


def events_path():
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "events.jsonl"


def append(kind, text, now=None):
    """Append one event; returns the dict written. ValueError for an unknown kind or empty text."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind (one of: {', '.join(KINDS)})")
    text = clean_text(text)
    if not text:
        raise ValueError("the text is empty once cleaned")
    at = (now or datetime.datetime.now(datetime.timezone.utc)).isoformat(timespec="seconds")
    event = {"at": at, "kind": kind, "text": text}
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        print(f"usage: cc_event.py <kind> '<short text>'  (kinds: {', '.join(KINDS)})", file=sys.stderr)
        return 2
    try:
        event = append(argv[0], " ".join(argv[1:]))
    except (ValueError, OSError) as e:
        print(f"cc_event: {e if isinstance(e, ValueError) else type(e).__name__}", file=sys.stderr)
        return 1
    print(f"event recorded: {event['kind']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
