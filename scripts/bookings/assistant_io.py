#!/usr/bin/env python3
"""Small, allowlisted helpers for the "Enquiry assistant" scheduled task, so an
unattended run needs no ad-hoc shell commands (which would stop on permission
prompts). Private data stays in ~/lcs-private/; this file holds none.

    .venv/bin/python scripts/bookings/assistant_io.py state
        start a run: print the time now, last_checked and the handled message ids
        (creates the file, 24 h back) and remember when this run started
    .venv/bin/python scripts/bookings/assistant_io.py done [messageId ...]
        mark messages handled and move last_checked to when this run started
    .venv/bin/python scripts/bookings/assistant_io.py style
        print the private email style guide (~/lcs-private/email-style.md)
    .venv/bin/python scripts/bookings/assistant_io.py refs
        print invoice refs already used (ledger and ~/lcs-private/invoices/)
    .venv/bin/python scripts/bookings/assistant_io.py ledger-add '<json object>'
        append one booking row (columns as in the ledger header); refuses duplicates
"""

import csv
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_money as lm  # noqa: E402

PRIVATE = Path.home() / "lcs-private"
STATE = PRIVATE / "assistant-state.json"
STYLE = PRIVATE / "email-style.md"
LEDGER = lm.LEDGER  # $LCS_BOOKINGS_CSV, else bookings.csv in $LCS_PRIVATE_DIR (default ~/lcs-private)
INVOICES = PRIVATE / "invoices"


def private_write(path, text):
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    path.write_text(text)
    os.chmod(path, 0o600)


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    state = {"last_checked": since.isoformat(timespec="seconds"), "handled": []}
    private_write(STATE, json.dumps(state, indent=1))
    return state


def main():
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "state":
        s = load_state()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        s["run_started"] = now
        private_write(STATE, json.dumps(s, indent=1))
        print(json.dumps({"now": now, "last_checked": s["last_checked"], "handled": s["handled"][-500:]}))
    elif cmd == "done":
        s = load_state()
        started = s.pop("run_started", None) or datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        s["handled"] = (s["handled"] + [m for m in args if m not in s["handled"]])[-500:]
        s["last_checked"] = started
        private_write(STATE, json.dumps(s, indent=1))
        print(f"state saved: last_checked {started}, {len(args)} message(s) marked")
    elif cmd == "style":
        print(STYLE.read_text() if STYLE.exists() else "(no style guide at ~/lcs-private/email-style.md)")
    elif cmd == "refs":
        refs = set()
        if LEDGER.exists():
            refs |= {r["booking_ref"] for r in csv.DictReader(open(LEDGER, newline=""))}
        if INVOICES.exists():
            refs |= {p.name.split(" - ")[0] for p in INVOICES.iterdir() if p.is_dir()}
        print(" ".join(sorted(refs)) or "(none)")
    elif cmd == "ledger-add":
        row = json.loads(args[0])
        if not LEDGER.exists():
            raise SystemExit("no ledger yet: run scripts/ads/upload_bookings.py once to create it")
        # The same lock as check_payments and upload_bookings, around the whole read-check-append.
        # lm.ledger_lock is not re-entrant: never nest it or call another ledger writer inside it.
        with lm.ledger_lock(LEDGER):
            with open(LEDGER, newline="") as f:
                reader = csv.DictReader(f)
                cols, rows = reader.fieldnames, list(reader)
            unknown = set(row) - set(cols)
            if unknown:
                raise SystemExit(f"unknown columns: {', '.join(sorted(unknown))}")
            if not row.get("booking_ref") or any(r["booking_ref"] == row["booking_ref"] for r in rows):
                raise SystemExit("missing or duplicate booking_ref; nothing written")
            with open(LEDGER, "a", newline="") as f:
                csv.DictWriter(f, fieldnames=cols).writerow({c: row.get(c, "") for c in cols})
            os.chmod(LEDGER, 0o600)
        print(f"ledger: added {row['booking_ref']}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
