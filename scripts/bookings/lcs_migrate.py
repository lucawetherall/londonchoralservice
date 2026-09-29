#!/usr/bin/env python3
"""The one-off migration of the ledger's and the singer store's notes into the state log, and the compare that
checks it (structured-state design, "Migration"; plan, Task 9). events.py runs both; the Command Centre's "Apply
the events migration" action builds its summary from plan() and compare() here.

- booking_proposals / invoice_proposals: for one row, the facts its notes (and, for a singer invoice, its columns)
  imply, read clause by clause with the same pattern readers check_payments and singer_invoices use, and the
  things left out (a date after today, a date that isn't one, an id that can't go in the log). A family that
  already has recorded facts for the subject is skipped, so a rerun, or a run after live writes, never
  contradicts a recorded fact.
- Dates: a phrase that carries its own date (paid in full, short by fees, deposit kept …, deposit seen) keeps it;
  any other fact takes the first ISO date in its clause, else the date of the fact before it in the same notes, else
  the invoice (received) date, flagged "undated". A date earlier than the fact before it is flagged "out of order";
  only in the cancellation family, whose reading follows the order, is it raised to the one before, so the log
  keeps the notes' order there. Other families read the latest date, so raising one would change the reading.
- plan(): every row's proposals, a report (refs, message ids, kinds, dates, amounts, rule names and flags only: never
  note text, names or bank details) and its sha256. The owner's apply re-runs it and refuses a different hash.
- compare(): every row read from its notes alone and events first (with the given events), and each family whose
  reading differs, as "subject id family: notes → events" (no note text: warnings as their codes).

Nothing here writes: events.py writes the report and appends the events.
"""

import datetime
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_payments as cp  # noqa: E402
import lcs_events  # noqa: E402
import lcs_money as lm  # noqa: E402
import singer_invoices as si  # noqa: E402

ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RULES = {"paid-in-full": "B5", "fees-accepted": "B6", "noted-paid": "B7/B8", "cancelled": "B9", "reinstated": "B10",
         "deposit-kept": "B11", "refunded": "B11", "payment-checked": "B11", "arranged": "B12", "deposit-seen": "B2",
         "reminder-drafted": "B4", "review-drafted": "B13", "review-skipped": "B13", "bank-warning": "S1-S4",
         "bank-confirmed": "S7", "settled": "S8", "withdrawn": "S9", "paid-reply-drafted": "S10"}
FAMILY = {k: fam for subject in lcs_events.FAMILIES.values() for fam, kinds in subject.items() for k in kinds}
SETTLED_KIND = (("deposit kept", "deposit-kept"), ("refunded", "refunded"))  # else payment-checked
WITHDRAWN_REASONS = ("not-ours", "duplicate", "sent-in-error")
WITHDRAWN_NOTE = re.compile(r"^withdrawn (\d{4}-\d{2}-\d{2}) \(([a-z][a-z-]*)\)")


def _date(text):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def first_iso(text):
    """The first real ISO date in the text, or None."""
    for m in ISO.finditer(text or ""):
        d = _date(m.group(1))
        if d:
            return d
    return None


def spans(notes):
    """[(start, end, clause)] for the notes' ";" clauses, stripped (check_payments.clauses, with positions)."""
    out, pos = [], 0
    for part in (notes or "").split(";"):
        text = part.strip()
        if text:
            start = pos + part.index(text)
            out.append((start, start + len(text), text))
        pos += len(part) + 1
    return out


def clause_at(parts, pos):
    return next((c for s, e, c in parts if s <= pos < e), None)


def derived_eid(subject, id, kind, on, claim):
    return hashlib.sha256(f"migration|{subject}|{id}|{kind}|{on}|{claim or ''}".encode()).hexdigest()[:16]


def unused_eid(eid, taken):
    """The derived eid, or, when the log already holds it (a line an earlier run wrote and withdrew as write-failed:
    a repeated eid would be skipped as a duplicate), the first of sha256(eid + "|n")[:16], n = 2, 3 … it doesn't."""
    out, n = eid, 1
    while out in taken:
        n += 1
        out = hashlib.sha256(f"{eid}|{n}".encode()).hexdigest()[:16]
    return out


def _proposal(pos, kind, fields, by, clause, own_date=None, flags=()):
    return {"pos": pos, "kind": kind, "fields": fields, "by": by, "clause": clause, "own": own_date,
            "flags": list(flags)}


def _dated(subject, id, found, fallback, today):
    """found: proposals with pos, clause and own date. Sorts them by position, gives each its `on` (the rules in the
    module docstring), its note claim and derived eid; drops a repeat (the same eid). Returns the finished list."""
    out, prev, last_cancel, seen = [], None, None, set()
    for p in sorted(found, key=lambda p: (p["pos"], p.get("tie", 0))):
        day = p["own"] or first_iso(p["clause"])
        flags = list(p["flags"])
        if day is None:
            day, flags = prev or fallback, ["undated"] + flags
        elif prev and day < prev:
            flags = ["out of order"] + flags
        if FAMILY[p["kind"]] == "cancellation":
            if last_cancel and day < last_cancel:
                day = last_cancel
                if "out of order" not in flags:
                    flags = ["out of order"] + flags
            last_cancel = day
        prev = day
        note = lcs_events.note_hash(p["clause"]) if p["clause"] else None
        eid = derived_eid(subject, id, p["kind"], day.isoformat(), note)
        if eid in seen:
            continue
        seen.add(eid)
        out.append({"subject": subject, "id": id, "kind": p["kind"], "fields": p["fields"], "by": p["by"],
                    "on": day.isoformat(), "note": note, "rule": RULES[p["kind"]], "flags": flags, "eid": eid})
    return out


def _fallback(day, today):
    return day if day and day <= today else today


# --- bookings ------------------------------------------------------------------------------------------------------

def booking_proposals(r, today, have):
    """([proposal], [left-out line]) for one ledger row. `have`: its recorded facts (lcs_events.Facts)."""
    ref = (r.get("booking_ref") or "").strip()
    if not lcs_events.ID_RE["booking"].fullmatch(ref):
        return [], ["left out: a ledger row whose booking ref can't go in the log [id]"]
    notes, value = r.get("notes") or "", cp.money(r)
    parts, found, left = spans(notes), [], []

    def skip(kind):
        return have.has(FAMILY[kind])

    def out_of_reach(kind, day):
        if day is None:
            left.append(f"left out: booking {ref} {kind} [{RULES[kind]}]: its date isn't a real date")
            return True
        if day > today:
            left.append(f"left out: booking {ref} {kind} [{RULES[kind]}]: dated after today ({day})")
            return True
        return False

    # cancellation (B9, B10): every counting phrase in text order, so the last one decides as notes_cancelled does
    if not skip("cancelled"):
        for pos in cp.counting_cancels(notes):
            found.append(dict(_proposal(pos, "cancelled", {}, "script", clause_at(parts, pos)), tie=0))
        for pos in cp.counting_resumes(notes):
            found.append(dict(_proposal(pos, "reinstated", {}, "owner", clause_at(parts, pos)), tie=1))
    # close (B5, B6)
    if not skip("paid-in-full"):
        for m in cp.FULL_NOTE.finditer(notes):
            day, clause = _date(m.group(0)[-10:]), clause_at(parts, m.start())
            if out_of_reach("paid-in-full", day):
                continue
            owner = (clause or "").rstrip().endswith("(owner)")
            found.append(_proposal(m.start(), "paid-in-full", {"basis": "owner" if owner else "bank"},
                                   "owner" if owner else "script", clause, day, () if owner else ["writer unknown"]))
        for m in cp.FEES_NOTE.finditer(notes):
            day, amount = _date(m.group(2)), float(m.group(1))
            if not 0 < amount <= cp.FEE_CAP:
                continue  # fee_notes ignores it too
            if out_of_reach("fees-accepted", day):
                continue
            found.append(_proposal(m.start(), "fees-accepted", {"amount": f"{amount:.2f}"}, "owner",
                                   clause_at(parts, m.start()), day))
    # cancel settlement (B11)
    if not skip("deposit-kept"):
        for m in cp.SETTLED_NOTE.finditer(notes):
            day = _date(m.group(1))
            said = m.group(0).lower()
            kind = next((k for words, k in SETTLED_KIND if said.startswith(words)), "payment-checked")
            if out_of_reach(kind, day):
                continue
            found.append(_proposal(m.start(), kind, {}, "owner", clause_at(parts, m.start()), day))
    for start, _, clause in parts:
        # deposit seen and reminders (markers B2, B4, B13)
        if not skip("deposit-seen"):
            for m in cp.AUTO_NOTE.finditer(clause):
                day = first_iso(m.group(0))
                if day and day <= today:
                    found.append(_proposal(start + m.start(), "deposit-seen", {}, "script", clause, day))
            for rx, what in ((r"(?<!balance )reminder drafted", "deposit"), (r"balance reminder drafted", "balance"),
                             (r"receipt drafted", "receipt")):
                m = re.search(rx, clause, re.I)
                if m:
                    found.append(_proposal(start + m.start(), "reminder-drafted", {"what": what}, "script", clause))
            m = cp.REVIEW_NOTE.search(clause)
            if m and m.group(1).lower() == "drafted":
                found.append(_proposal(start + m.start(), "review-drafted", {}, "script", clause))
            elif m:
                reason = re.search(r"\((planner|unresolved)\)", clause)
                if reason:
                    found.append(_proposal(start + m.start(), "review-skipped", {"reason": reason.group(1)}, "script",
                                           clause))
                else:
                    left.append(f"left out: booking {ref} review-skipped [B13]: a reason the log doesn't take")
        # arrangement (B12) and noted paid (B7, B8), read per clause exactly as assess reads the whole notes
        arranged, rest = cp.arranged_notes(clause)
        if arranged and not skip("arranged"):
            low = clause.lower()
            where = {w: low.find(w) for w in ("cash", "cheque") if w in low}
            method = min(where, key=where.get) if where else "third-party"
            found.append(_proposal(start, "arranged", {"method": method}, "script", clause))
        if not skip("noted-paid"):
            own = cp.hand_notes(cp.FULL_NOTE.sub(" ", rest))  # a "paid in full" close says paid by itself
            if cp.PAID_WORD.search(own):
                scope = "full" if cp.full_paid(own, value) else "part"
                found.append(_proposal(start, "noted-paid", {"scope": scope}, "script", clause))
    fallback = _fallback(cp.date_or_none(r.get("invoice_date")), today)
    return _dated("booking", ref, found, fallback, today), left


# --- singer invoices -----------------------------------------------------------------------------------------------

def invoice_proposals(r, today, have):
    """([proposal], [left-out line]) for one singer store row. `have`: its recorded facts."""
    mid = (r.get("message_id") or "").strip()
    if not lcs_events.ID_RE["singer_invoice"].fullmatch(mid):
        return [], ["left out: a singer invoice whose message id can't go in the log [id]"]
    parts = spans(r.get("notes") or "")
    fp = r.get("bank_fp") or ""
    fp8 = fp[:8]
    received = _fallback(si.received_date(r), today)
    found, left = [], []
    if not have.has("bank warnings"):
        coded = [(s, c, si.warning_code(c)) for s, _, c in parts if si.warning_code(c)]
        codes = list(dict.fromkeys(code for _, _, code in coded))
        flags = []
        if r.get("bank_changed") == "yes" and not set(codes) & si.RING_CODES:
            codes.append("changed")
            flags.append("changed from the column only")
        if codes and not lcs_events.FP8_RE.fullmatch(fp8):
            left.append(f"left out: singer_invoice {mid} bank-warning [S1-S4]: a bank fingerprint the log can't take")
        elif codes:
            pos, clause = (coded[0][0], coded[0][1]) if coded else (0, None)
            found.append(_proposal(pos, "bank-warning", {"fp8": fp8, "codes": codes}, "script", clause, received, flags))
    if r.get("bank_confirmed") == "yes" and not have.has("bank trust"):
        hit = next(((s, c) for s, _, c in parts if c.startswith("bank details confirmed by phone")), (0, None))
        if len(fp8) == 8 and lcs_events.FP8_RE.fullmatch(fp8):
            found.append(_proposal(hit[0], "bank-confirmed", {"fp8": fp8}, "owner", hit[1]))
        else:
            left.append(f"left out: singer_invoice {mid} bank-confirmed [S7]: no bank details recorded")
    settle = next(((s, c) for s, _, c in parts if c.startswith("settled by hand")), None)
    if settle and r.get("paid_on") and not have.has("settlement"):
        day, amount = _date((r.get("paid_on") or "")[:10]), lm.parse_gbp(r.get("paid_amount") or r.get("amount_gbp"))
        if day is None or day > today or not amount or round(amount, 2) <= 0 or amount >= 100000:
            left.append(f"left out: singer_invoice {mid} settled [S8]: no usable date or amount")
        else:
            found.append(_proposal(settle[0], "settled", {"amount": f"{amount:.2f}"}, "owner", settle[1], day))
    if (r.get("withdrawn") or "").strip() and not have.has("withdrawal"):
        day = _date((r.get("withdrawn") or "").strip()[:10])
        hit = next(((s, c, WITHDRAWN_NOTE.match(c)) for s, _, c in parts if WITHDRAWN_NOTE.match(c)), (len(r.get("notes") or ""), None, None))
        word = hit[2].group(2) if hit[2] else ""
        if day is None:
            left.append(f"left out: singer_invoice {mid} withdrawn [S9]: its date isn't a real date")
        elif day > today:
            left.append(f"left out: singer_invoice {mid} withdrawn [S9]: dated after today ({day})")
        else:
            found.append(_proposal(hit[0], "withdrawn", {"reason": word if word in WITHDRAWN_REASONS else "other"},
                                   "script", hit[1], day))
    if not have.has("markers"):
        for s, _, c in parts:
            if c.startswith("paid reply drafted"):
                found.append(_proposal(s, "paid-reply-drafted", {}, "script", c))
    return _dated("singer_invoice", mid, found, received, today), left


# --- the plan and its report ---------------------------------------------------------------------------------------

def describe(p):
    fields = " ".join(f"{k}={','.join(v) if isinstance(v, list) else v}" for k, v in sorted(p["fields"].items()))
    line = (f"{p['subject']} {p['id']} {p['kind']}" + (f" {fields}" if fields else "")
            + f" on {p['on']} by {p['by']} [{p['rule']}] eid {p['eid']}")
    return line + (f" ({', '.join(p['flags'])})" if p["flags"] else "")


def plan(ledger_rows, store_rows, today, events):
    """{"proposals", "left", "report", "sha256"} for the whole ledger and store against the log's `events`."""
    idx = lcs_events.index(events, today)
    proposals, left, seen, taken = [], [], set(), {e["eid"] for e in events}
    for subject, rows, propose, key in (("booking", ledger_rows, booking_proposals, "booking_ref"),
                                        ("singer_invoice", store_rows, invoice_proposals, "message_id")):
        for r in rows:
            have = lcs_events.Facts(subject, idx.get((subject, (r.get(key) or "").strip()), []))
            got, out = propose(r, today, have)
            left += out
            for p in got:
                if p["eid"] in seen:  # the same fact twice (a duplicated ledger row): once
                    continue
                seen.add(p["eid"])
                p["eid"] = unused_eid(p["eid"], taken)
                try:
                    lcs_events.dumps(lcs_events.validate(_event(p, _now()), write=True))
                except ValueError as e:
                    left.append(f"left out: {p['subject']} {p['id']} {p['kind']} [{p['rule']}]: {e}")
                    continue
                taken.add(p["eid"])
                proposals.append(p)
    report = render(proposals, left, today, len(ledger_rows), len(store_rows), len(events))
    return {"proposals": proposals, "left": left, "report": report, "future": future_lines(left),
            "sha256": hashlib.sha256(report.encode("utf-8")).hexdigest()}


FUTURE = re.compile(r"^left out: (\S+ \S+ \S+) \[[^\]]*\]: dated after today \((\d{4}-\d{2}-\d{2})\)$")


def future_lines(left):
    """"<subject> <id> <kind> (<date>)" for each fact left out as dated after today: the apply refuses while any is
    left (the readers would read the note on that day, and the facts would then disagree with it)."""
    return [f"{m.group(1)} ({m.group(2)})" for m in map(FUTURE.match, left) if m]


def flag_counts(proposals):
    out = {}
    for p in proposals:
        for f in p["flags"]:
            out[f] = out.get(f, 0) + 1
    return out


def totals(plan_):
    """One line: the events proposed, by subject, and the flags."""
    ps = plan_["proposals"]
    b = sum(p["subject"] == "booking" for p in ps)
    flags = ", ".join(f"{k} {v}" for k, v in sorted(flag_counts(ps).items())) or "none"
    return (f"{len(ps)} events proposed (bookings {b}, singer invoices {len(ps) - b}); flags: {flags}; "
            f"left out {len(plan_['left'])}")


def render(proposals, left, today, n_ledger, n_store, n_events):
    lines = [f"state log migration: dry run for {today.isoformat()}",
             f"ledger rows {n_ledger}, singer invoices {n_store}, lines already in the log {n_events}", ""]
    lines += [describe(p) for p in proposals]
    lines += [""] + left if left else []
    t = totals({"proposals": proposals, "left": left})
    lines += ["", "totals: " + t.replace(" proposed", "", 1)]
    return "\n".join(lines) + "\n"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def _event(p, now):
    obj = {"v": 1, "eid": p["eid"], "prev": "", "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "on": p["on"],
           "subject": p["subject"], "id": p["id"], "kind": p["kind"], "fields": p["fields"], "by": p["by"],
           "src": "migration"}
    if p["note"]:
        obj["note"] = p["note"]
    return obj


def proposed_events(proposals, now=None):
    """The proposals as validated log lines (prev left "": they are read, not chained), for compare --proposed."""
    now = now or _now()
    return [lcs_events.validate(_event(p, now)) for p in proposals]


# --- compare -------------------------------------------------------------------------------------------------------

def booking_readings(r, today, facts):
    f = cp.facts_for(r, today, facts)
    n = cp.note_readings(r, today, f)
    return {"cancellation": cp.is_cancelled(r, f),
            "close": (cp.closed_on(r, today, f), cp.fee_notes(r, today, f), cp.fee_pending(r, today, f),
                      cp.is_closed(r, today, f)),
            "cancel settlement": cp.cancel_settled_on(r, today, f),
            "arrangement": n["arranged"],
            "noted paid": (n["noted_hand"], n["noted_full"]),
            "markers": (n["noted_auto"], n["reminded"], bool(cp.REVIEW_NOTE.search(r.get("notes") or "")) or f.review),
            "held": cp.held(r, today, f)}


def warning_codes(texts):
    return sorted(si.warning_code(t) or "note" for t in texts)


def invoice_readings(rows, r, facts):
    f = si.facts_for(r, facts)
    return {"withdrawal": si.is_withdrawn(r, f), "open": si.is_open(r, f),
            "bank trust": (si.confirmed(r, f), si.trust_label(rows, r, facts)),
            "bank warnings": (si.bank_changed(r, f), si.ring_first_in(rows, r, facts),
                              warning_codes(si.live_warnings(rows, r, facts))),
            "bill": si.stored_bill(rows, r, facts),
            "markers": "paid reply drafted" in (r.get("notes") or "") or f.thanked,
            "held": si.held(rows, r, facts)}


def shown(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return "(" + ", ".join(shown(v) for v in value) + ")"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k} {shown(v)}" for k, v in value.items()) + "}"
    return str(value)


def compare(ledger_rows, store_rows, today, events):
    """["subject id family: notes → events"] for every family whose reading from the notes alone differs from its
    reading events first (with `events`). [] when nothing differs."""
    idx = lcs_events.index(events, today)
    books = {i: lcs_events.Facts("booking", es) for (s, i), es in idx.items() if s == "booking"}
    invoices = {i: lcs_events.Facts("singer_invoice", es) for (s, i), es in idx.items() if s == "singer_invoice"}
    out = []
    for r in ledger_rows:
        ref = (r.get("booking_ref") or "").strip()
        a, b = booking_readings(r, today, {}), booking_readings(r, today, books)
        out += [f"booking {ref} {fam}: {shown(a[fam])} → {shown(b[fam])}" for fam in a if a[fam] != b[fam]]
    for r in store_rows:
        mid = (r.get("message_id") or "").strip()
        a, b = invoice_readings(store_rows, r, {}), invoice_readings(store_rows, r, invoices)
        out += [f"singer_invoice {mid} {fam}: {shown(a[fam])} → {shown(b[fam])}" for fam in a if a[fam] != b[fam]]
    return out
