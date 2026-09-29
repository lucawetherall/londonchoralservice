#!/usr/bin/env python3
"""Read-only views of the state log, ~/lcs-private/events.jsonl (lcs_events; structured-state design, 29 Sep 2026).

    .venv/bin/python scripts/bookings/events.py verify
        lines, skipped lines, whether the chain is whole ("broken at line N"), when it was last written;
        exits 1 on a skipped line, a broken chain or an unreadable log
    .venv/bin/python scripts/bookings/events.py show booking 2111
    .venv/bin/python scripts/bookings/events.py show singer_invoice <message id>
        the facts recorded for one booking or invoice, one line each: eid, on, kind, fields, who and src,
        "(retracted)" where undone. Never notes, names or anything from the CSVs.

Both only read. The migration, compare, retract and notes-checked commands come in later changes.
"""

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_events  # noqa: E402
import lcs_money as lm  # noqa: E402


def cmd_verify(args):
    events, stats = lcs_events.read()
    if stats.get("unreadable"):
        print("state log unreadable: it must be a regular file of this user's, mode 600 (read as absent)")
        return 1
    if not stats["lines"] and not stats["skipped"]:
        print("no state log yet")
        return 0
    chain = "chain whole" if stats["chain_ok"] else f"chain broken at line {stats['broken_at']}"
    print(f"state log: {stats['lines']} lines, {stats['skipped']} skipped, {chain}, "
          f"last written {stats['last_at'] or 'never'}")
    return 1 if stats["skipped"] or not stats["chain_ok"] else 0


def describe(e, today):
    fields = " ".join(f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in sorted(e["fields"].items()))
    line = f"{e['on']} {e['kind']}" + (f" {fields}" if fields else "") + f" by {e['by']} ({e['src']}) [{e['eid']}]"
    if e.get("retracted"):
        line += " (retracted)"
    if e["on"] > today.isoformat():
        line += " (dated after today: not read yet)"
    return line


def cmd_show(args):
    if not lcs_events.ID_RE[args.subject].fullmatch(args.id):
        raise SystemExit("not a booking ref or message id; nothing shown")
    events, _ = lcs_events.read()
    facts = lcs_events.index(events, datetime.date.max).get((args.subject, args.id), [])
    if not facts:
        print("no recorded facts")
        return 0
    today = lm.today()
    # every fact is listed, future-dated ones too, but only a retract dated up to today undoes its target
    now = {e["eid"]: e["retracted"] for e in lcs_events.index(events, today).get((args.subject, args.id), [])}
    for e in facts:
        print(describe(dict(e, retracted=now.get(e["eid"], False)), today))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only views of the state log.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    p = sub.add_parser("show")
    p.add_argument("subject", choices=lcs_events.SUBJECTS)
    p.add_argument("id")
    p.set_defaults(fn=cmd_show)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
