#!/usr/bin/env python3
"""Read-only views of the state log, ~/lcs-private/events.jsonl (lcs_events; structured-state design, 29 Sep 2026).

    .venv/bin/python scripts/bookings/events.py verify
        lines, skipped lines, whether the chain is whole ("broken at line N"), when it was last written; then
        each fact whose claimed note clause is missing from its row ("fact without its note: …", the crash window)
        and each notes-checked hash no clause matches; exits 1 on any of these, a skipped line, a broken chain or
        an unreadable log
    .venv/bin/python scripts/bookings/events.py show booking 2111
    .venv/bin/python scripts/bookings/events.py show singer_invoice <message id>
        the facts recorded for one booking or invoice, one line each: eid, on, kind, fields, who and src,
        "(retracted)" where undone. Never notes, names or anything from the CSVs.

    .venv/bin/python scripts/bookings/events.py migrate
        the one-off migration's dry run (lcs_migrate): the facts the ledger's and the singer store's notes imply,
        family by family where the log has none yet, written as a report to <private>/events-migration-<date>.txt
        (mode 600: refs, message ids, kinds, dates, amounts, rule names and flags; never note text) with its totals
        and sha256 printed. Writes nothing else.
    .venv/bin/python scripts/bookings/events.py migrate --apply --expect <sha256> --owner
        the Command Centre only, after the owner's passkey (its one-time nonce on a pipe, lcs_owner): re-runs the dry
        run under the ledger's and the store's locks, refuses a different hash (something changed since) or any
        difference compare --proposed finds, then appends the events (src migration, derived eids) and prints
        "N new events". A second apply adds nothing: "0 new events".
    .venv/bin/python scripts/bookings/events.py compare [--proposed]
        every ledger and store row read from its notes alone and events first (with the log, or with the dry run's
        proposed events added), one line per family that reads differently; "no difference" and exit 0, else exit 1.

verify, show, migrate (without --apply) and compare only read (the dry run writes its report). The retract and
notes-checked commands come in a later change.
"""

import argparse
import datetime
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lcs_events  # noqa: E402
import lcs_money as lm  # noqa: E402
import lcs_owner  # noqa: E402


def cmd_verify(args):
    events, stats = lcs_events.read()
    problem = lcs_events.log_problem(stats)
    if stats.get("unreadable"):
        print(problem)
        return 1
    if not stats["lines"] and not stats["skipped"]:
        print("no state log yet")
        return 0
    chain = "chain whole" if stats["chain_ok"] else f"chain broken at line {stats['broken_at']}"
    print(f"state log: {stats['lines']} lines, {stats['skipped']} skipped, {chain}, "
          f"last written {stats['last_at'] or 'never'}")
    notes = note_problems(events)
    for line in notes:
        print(line)
    return 1 if problem or notes else 0


def note_problems(events):
    """Lines for each fact whose claimed note clause is missing from its row's notes (the crash window: the fact
    decides, the human record is missing) and each live notes-checked hash that no clause of its row matches. A fact
    withdrawn as write-failed never had a note, so it isn't listed. Ids, kinds, dates and hashes only."""
    ledger, store, _, _ = rows()
    notes = {("booking", (r.get("booking_ref") or "").strip()): r.get("notes") or "" for r in ledger}
    notes.update({("singer_invoice", (r.get("message_id") or "").strip()): r.get("notes") or "" for r in store})
    out = []
    for (subject, id_), es in lcs_events.index(events, lm.today()).items():
        have = {lcs_events.note_hash(c.strip()) for c in notes.get((subject, id_), "").split(";") if c.strip()}
        for e in es:
            if e["retracted"] == "write-failed":
                continue
            if e.get("note") and e["note"] not in have:
                out.append(f"fact without its note: {subject} {id_} {e['kind']} on {e['on']} [{e['eid']}]")
            if e["kind"] == "notes-checked" and not e["retracted"]:
                out += [f"notes-checked hash no clause matches: {subject} {id_} {h}" for h in e["fields"]["clauses"]
                        if h not in have]
    return out


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


SHA_RE = re.compile(r"[0-9a-f]{64}")


def rows():
    """(ledger rows, singer store rows, the ledger's path, the store's path), read without a lock."""
    import lcs_migrate
    ledger, store = lcs_migrate.cp.LEDGER, lcs_migrate.si.STORE
    return lm.read_csv(ledger), lm.read_csv(store), ledger, store


def write_report(text, today):
    """<private>/events-migration-<date>.txt, mode 600, replaced atomically (never through a symlink)."""
    path = lcs_events.log_path().parent / f"events-migration-{today.isoformat()}.txt"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path


def cmd_migrate(args):
    import lcs_migrate
    today = lm.today()
    if args.apply:
        return apply_migration(args, today)
    if args.expect or args.owner:
        raise SystemExit("--expect and --owner go with --apply only; nothing written")
    ledger, store, _, _ = rows()
    plan = lcs_migrate.plan(ledger, store, today, lcs_events.read()[0])
    path = write_report(plan["report"], today)
    print(f"events migration dry run for {today.isoformat()}: {lcs_migrate.totals(plan)}")
    if plan["future"]:
        print(f"dated after today: {'; '.join(plan['future'])}: correct those notes before the apply")
    print(f"report: {path}")
    print(f"sha256: {plan['sha256']}")
    return 0


def apply_migration(args, today):
    """The owner's apply: the nonce, the folder, the same dry run (hash), no compare difference; then the events."""
    import lcs_migrate
    if not args.owner:
        raise SystemExit("--apply needs --owner (the Command Centre's passkey action); nothing written")
    if not args.expect or not SHA_RE.fullmatch(args.expect):
        raise SystemExit("--apply needs --expect with the dry run's sha256 (64 hex); nothing written")
    _, _, ledger_path, store_path = rows()
    where = lcs_owner.owner_folder_problem([ledger_path, store_path, lcs_events.log_path()])
    if where:
        raise SystemExit(f"--owner {where}; nothing written")
    if not lcs_owner.owner_confirmed():
        raise SystemExit("--owner needs the Command Centre's one-time owner nonce (the owner's passkey approval); "
                         "nothing written")
    # the CSVs' locks, ledger first, so neither changes between the hash check and the last append; the log's own
    # lock is taken inside each append (lock order: the CSVs', then the log's)
    with lm.ledger_lock(ledger_path), lm.ledger_lock(store_path):
        ledger, store = lm.read_csv(ledger_path), lm.read_csv(store_path)
        log = lcs_events.read()[0]
        plan = lcs_migrate.plan(ledger, store, today, log)
        if not hashlib.sha256(plan["report"].encode("utf-8")).hexdigest() == args.expect:
            raise SystemExit("the ledger, the singer store or the log changed since the dry run: run it again; "
                             "nothing written")
        if plan["future"]:
            raise SystemExit(f"dated after today, so not yet a fact: {'; '.join(plan['future'])}: correct those notes "
                             "first; nothing written")
        events = lcs_migrate.proposed_events(plan["proposals"])
        diffs = lcs_migrate.compare(ledger, store, today, log + events)
        if diffs:
            raise SystemExit(f"compare --proposed finds {len(diffs)} difference(s): run it and settle them first; "
                             "nothing written")
        written = []
        try:
            for p in plan["proposals"]:
                lcs_events.append(p["subject"], p["id"], p["kind"], p["fields"], p["by"], on=p["on"], note=p["note"],
                                  src="migration", eid=p["eid"])
                written.append(p)
        except (OSError, ValueError) as e:
            # never leave a family half-migrated: withdraw this run's lines (write-failed, by their own writer, in
            # the same run), so the next dry run proposes them again and the log reads as if nothing was written
            undone = True
            for p in reversed(written):
                try:
                    lcs_events.append(p["subject"], p["id"], "retract", {"target": p["eid"], "why": "write-failed"},
                                      p["by"])
                except (OSError, ValueError):
                    undone = False
            # a write-failed retract counts only within RUN_SECONDS of its target: check each really undid it
            lcs_events.clear_cache()
            now = {e["eid"]: e["retracted"] for es in lcs_events.index(lcs_events.read()[0], today).values() for e in es}
            undone = undone and all(now.get(p["eid"]) == "write-failed" for p in written)
            if undone:
                raise SystemExit(f"the migration stopped ({type(e).__name__}); what it wrote was withdrawn: run it "
                                 "again; nothing written") from None
            raise SystemExit(f"the migration stopped ({type(e).__name__}) part way and couldn't withdraw it: run "
                             "events.py verify and compare before anything else") from None
    print(f"{len(plan['proposals'])} new events")
    return 0


UNDONE = "earlier entry undone {d} (owner)"  # no kind's words in it, so the notes read no fact from it


def undo_columns(r, kind):
    """A singer store row's columns put back when its fact is undone (a booking's state is all in its notes)."""
    if kind == "withdrawn":
        r["withdrawn"] = ""
    elif kind == "bank-confirmed":
        r["bank_confirmed"] = ""
    elif kind == "settled" and r.get("paid_verified") == "no" and not r.get("paid_ref"):
        r["paid_on"] = r["paid_amount"] = r["paid_verified"] = ""


def cmd_retract(args):
    """The owner's undo (the Command Centre's "Undo a recorded fact", after the passkey): retract {target, why:
    mistake}, by owner, claiming "earlier entry undone D (owner)" appended to the row's notes, both under the row's
    CSV lock; a singer invoice's columns go back (undo_columns). The fact stays in the log as history, its clause
    set aside, so the subject reads as if it had never been recorded."""
    import lcs_migrate
    cp, si = lcs_migrate.cp, lcs_migrate.si
    if not lcs_events.HEX16.fullmatch(args.eid or ""):
        raise SystemExit("not a recorded fact's id (16 hex); nothing written")
    if not args.owner:
        raise SystemExit("retract runs from the Command Centre only (--owner, the owner's passkey); nothing written")
    today = lm.today()
    events, _ = lcs_events.read()
    target = next((e for es in lcs_events.index(events, today).values() for e in es if e["eid"] == args.eid), None)
    if target is None or target["kind"] == "retract" or target["retracted"]:
        raise SystemExit("no live recorded fact with that id (unknown, already undone, or an undo itself); "
                         "nothing written")
    subject, id_ = target["subject"], target["id"]
    path, cols, key = ((cp.LEDGER, None, "booking_ref") if subject == "booking"
                       else (si.STORE, si.COLUMNS, "message_id"))
    where = lcs_owner.owner_folder_problem([path, lcs_events.log_path()])
    if where:
        raise SystemExit(f"--owner {where}; nothing written")
    if not lcs_owner.owner_confirmed():
        raise SystemExit("--owner needs the Command Centre's one-time owner nonce (the owner's passkey approval); "
                         "nothing written")
    clause = UNDONE.format(d=today.isoformat())
    with lcs_events.recording(path, cols) as t:
        r = next((x for x in t.rows if (x.get(key) or "").strip() == id_), None)
        if r is None:
            raise SystemExit(f"no {subject.replace('_', ' ')} {id_}; nothing written")
        r["notes"] = (f"{r['notes']}; " if (r.get("notes") or "").strip() else "") + clause
        if subject == "singer_invoice":
            undo_columns(r, target["kind"])
        if not lcs_events.record(t, subject, id_, "retract", {"target": args.eid, "why": "mistake"}, "owner", clause):
            raise SystemExit("the state log isn't recording facts (no migration applied); nothing written")
    print(f"{subject} {id_}: {target['kind']} of {target['on']} undone")
    return 0


def cmd_compare(args):
    import lcs_migrate
    today = lm.today()
    ledger, store, _, _ = rows()
    events = list(lcs_events.read()[0])
    if args.proposed:
        events += lcs_migrate.proposed_events(lcs_migrate.plan(ledger, store, today, events)["proposals"])
    diffs = lcs_migrate.compare(ledger, store, today, events)
    for line in diffs:
        print(line)
    if not diffs:
        print("no difference")
    return 1 if diffs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="The state log: verify, show, migrate, compare.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    p = sub.add_parser("show")
    p.add_argument("subject", choices=lcs_events.SUBJECTS)
    p.add_argument("id")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("migrate")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--expect", metavar="SHA256")
    p.add_argument("--owner", action="store_true", help="the Command Centre only: needs its one-time nonce on stdin")
    p.set_defaults(fn=cmd_migrate)
    p = sub.add_parser("retract")
    p.add_argument("eid")
    p.add_argument("--owner", action="store_true", help="the Command Centre only: needs its one-time nonce on stdin")
    p.set_defaults(fn=cmd_retract)
    p = sub.add_parser("compare")
    p.add_argument("--proposed", action="store_true", help="add the migration dry run's proposed events")
    p.set_defaults(fn=cmd_compare)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
