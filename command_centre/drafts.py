"""The drafts inbox: the drafts the scheduled assistant saved in Zoho Mail, and the owner's local marks.

cache/drafts.json is written by `scripts/reports/cc_sync.py drafts-put` (the reply drafter, the daily pass and the
singer clerk run it once per saved draft). The marks (sent, discarded, or open again) live in
<private>/command-centre/drafts-marks.json and are written only by the app's draft-mark action (no passkey: it is a
local record and never touches Zoho). A draft is named on the page and in forms by a 12-letter hash of its thread,
kind and date, so no thread id (a long digit run) reaches the page.
"""

import datetime
import hashlib
import json
import re

from . import auth, sources, todo

ZOHO_DRAFTS_URL = "https://mail.zoho.com/zm/#mail/folder/drafts"  # the owner's account is on Zoho's .com data centre
STATES = ("sent", "discarded", "open")
KEY_RE = re.compile(r"^[a-z]{12}$")
FIELDS = ("thread_id", "kind", "first_name", "subject", "created")
KIND_WORDS = {"reply": "reply", "confirmation": "booking confirmation", "holding": "holding reply",
              "follow-up": "quote follow-up", "deposit-reminder": "deposit reminder",
              "balance-reminder": "balance reminder", "receipt": "payment receipt", "review": "review request",
              "paid-thanks": "singer “Paid!”", "other": "other"}


def drafts_path():
    return auth.config_dir() / "cache" / "drafts.json"


def marks_path():
    return auth.config_dir() / "drafts-marks.json"


def draft_key(d):
    digest = hashlib.sha256(("lcs-cc-draft:" + "|".join(str(d.get(k, "")) for k in ("thread_id", "kind", "created")))
                            .encode("utf-8")).digest()
    return "".join(chr(97 + b % 26) for b in digest[:12])


def read_drafts():
    """(drafts, synced at) from the cache, or None: nothing recorded yet. Entries that aren't the expected shape are
    skipped; a file that isn't a list raises ValueError (the panel shows the type)."""
    found = sources.read_json(drafts_path())
    if found is None:
        return None
    value, when = found
    if not isinstance(value, list):
        raise ValueError("drafts.json is not a list")
    out = []
    for d in value:
        if isinstance(d, dict) and all(isinstance(d.get(k), str) for k in FIELDS):
            out.append({k: d[k] for k in FIELDS})
    return out, when


def load_marks():
    try:
        with open(marks_path(), encoding="utf-8") as f:
            marks = json.load(f)
    except FileNotFoundError:
        return {}
    return marks if isinstance(marks, dict) else {}


def set_mark(key, state, when=None):
    """Record one mark, under the config lock (one writer at a time)."""
    when = when or datetime.datetime.now(datetime.timezone.utc)
    with auth.config_lock():
        marks = load_marks()
        marks[key] = {"state": state, "at": when.isoformat(timespec="seconds")}
        todo.write_private_json(marks_path(), marks)


def inbox(found, marks):
    """{"open": [...], "marked": [...], "synced": mtime}: each draft with its key, kind words and mark."""
    drafts, when = found if found else ([], None)
    open_, marked = [], []
    for d in drafts:
        key = draft_key(d)
        m = marks.get(key) if isinstance(marks.get(key), dict) else {}
        state = m.get("state") if m.get("state") in STATES else "open"
        row = {"key": key, "kind": d["kind"], "kind_words": KIND_WORDS.get(d["kind"], d["kind"]),
               "first_name": d["first_name"], "subject": d["subject"], "created": d["created"], "state": state,
               "marked_at": str(m.get("at") or "")[:10]}
        (open_ if state == "open" else marked).append(row)
    order = lambda r: (r["created"], r["key"])  # noqa: E731
    return {"open": sorted(open_, key=order, reverse=True), "marked": sorted(marked, key=order, reverse=True),
            "synced": when}


def find(key):
    """The recorded draft with this key, or None."""
    found = read_drafts()
    return next((d for d in (found[0] if found else []) if draft_key(d) == key), None)
