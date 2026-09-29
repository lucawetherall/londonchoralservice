#!/usr/bin/env python3
"""Twin tests for the structured-state readers: each case in tests/state_cases.py read from its notes alone, from
its recorded facts alone and from both must give the same reading, and an unclaimed note that contradicts the
recorded facts holds the booking or invoice (structured-state design, "Precedence when events and notes
disagree"). Every test uses a temp LCS_PRIVATE_DIR, never ~/lcs-private.
Stdlib only: .venv/bin/python tests/test_state_twins.py"""
import datetime, hashlib, os, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(_HOME, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_payments as cp  # noqa: E402
import lcs_events as ev  # noqa: E402
from state_cases import BOOKING_CASES, T  # noqa: E402

REF = "2111"


def facts_list(facts):
    return [] if facts is None else facts if isinstance(facts, list) else [facts]


def build_events(ref, clauses, claim, subject="booking"):
    """Validated events for each clause's facts, in clause order; with claim, each carries its clause's note hash.
    A retract with no target undoes the fact just before it."""
    out = []
    for text, facts, *flag in clauses:
        for kind, fields, on, by in facts_list(facts):
            fields = dict(fields)
            if kind == "retract" and "target" not in fields:
                fields["target"] = out[-1]["eid"]
            obj = {"v": 1, "eid": hashlib.sha256(f"{ref}|{text}|{kind}|{len(out)}".encode()).hexdigest()[:16],
                   "prev": "", "at": f"{on}T12:00:00Z", "on": on, "subject": subject, "id": ref, "kind": kind,
                   "fields": fields, "by": by, "src": "live"}
            if (flag[0] if flag else claim):
                obj["note"] = ev.note_hash(text)
            out.append(ev.validate(obj))
    return out


def row(value, invoice, event, notes, ref=REF, name="Ann Smith"):
    return {"booking_ref": ref, "value_gbp": str(value), "invoice_date": invoice, "event_date": event, "notes": notes,
            "client_name": name}


def three_ways(case):
    """[(label, row, Facts)] for a case: notes only, facts only, both."""
    name, value, invoice, event, clauses, paid, today = case
    notes = "; ".join(t for t, _ in clauses)
    neutral = "; ".join(t for t, facts in clauses if facts is None)
    return [("notes", row(value, invoice, event, notes), ev.booking_facts(REF, today, events=[])),
            ("events", row(value, invoice, event, neutral), ev.booking_facts(REF, today, events=build_events(REF, clauses, False))),
            ("both", row(value, invoice, event, notes), ev.booking_facts(REF, today, events=build_events(REF, clauses, True)))]


def reading(r, paid, today, facts):
    return {"assess": cp.assess(r, paid, today, facts=facts), "cancelled": cp.is_cancelled(r, facts=facts),
            "closed_on": cp.closed_on(r, today, facts=facts), "fee_notes": cp.fee_notes(r, today, facts=facts),
            "fees_accepted": cp.fees_accepted(r, today, facts=facts), "fee_pending": cp.fee_pending(r, today, facts=facts),
            "settled_on": cp.cancel_settled_on(r, today, facts=facts),
            "open": [x["booking_ref"] for x in cp.open_rows([r], today, facts=facts)],
            "held": cp.held(r, today, facts=facts)}


def test_every_booking_case_reads_the_same_three_ways():
    for case in BOOKING_CASES:
        name, paid, today = case[0], case[5], case[6]
        got = {label: reading(r, paid, today, facts) for label, r, facts in three_ways(case)}
        assert got["notes"]["held"] == [] and got["events"]["held"] == [] and got["both"]["held"] == [], (name, got)
        assert got["events"] == got["notes"], (name, got["notes"], got["events"])
        assert got["both"] == got["notes"], (name, got["notes"], got["both"])


def test_the_cases_reach_every_family_and_many_states():
    kinds = {k for c in BOOKING_CASES for _, facts in c[4] for k, *_ in facts_list(facts)}
    assert kinds >= {"paid-in-full", "fees-accepted", "noted-paid", "arranged", "cancelled", "reinstated", "deposit-kept",
                     "refunded", "payment-checked", "deposit-seen", "reminder-drafted", "review-drafted"}, kinds
    states = {reading(r, c[5], c[6], facts)["assess"]["state"] for c in BOOKING_CASES for label, r, facts in three_ways(c)
              if label == "notes"}
    assert states >= {"CANCELLED", "PAYMENT_ON_CANCELLED", "PAYMENT_AFTER_CLOSE", "PAID_IN_FULL", "ARRANGED",
                      "NOTED_PAID", "BALANCE_DUE", "DEPOSIT_OVERDUE", "CHECK_PAYMENT", "DEPOSIT_SEEN"}, states


def test_with_no_facts_the_readers_are_todays():
    """facts=None and no log: the readers fall back to the notes, exactly as before (rule 1)."""
    ev.clear_cache()
    assert not os.path.exists(os.path.join(_HOME, "events.jsonl"))
    for case in BOOKING_CASES:
        _, r, facts = three_ways(case)[0]
        assert reading(r, case[5], case[6], None) == reading(r, case[5], case[6], facts), case[0]


# --- disagreement holds a booking --------------------------------------------------------------------------------

def f(kind, on, by="script", **fields):
    return (kind, fields, on, by)


UNDO = f("retract", "2026-09-21", "owner", why="mistake")

# (family held, clauses as (text, facts, claimed), the fact that agrees with the loose clause); every case's
# facts give its family events, and its last clause is the loose one
HOLDS = [
    ("cancellation", [("cancelled 20 Sep", f("cancelled", "2026-09-20"), True), ("reinstated 25 Sep", None, False)],
     f("reinstated", "2026-09-25", "owner")),
    ("cancellation", [("cancelled 20 Sep", f("cancelled", "2026-09-20"), True),
                      ("reinstated 25 Sep", f("reinstated", "2026-09-25", "owner"), True),
                      ("cancelled again 26 Sep", None, False)], f("cancelled", "2026-09-26")),
    ("close", [("short by fees £5 accepted 2026-09-20 (owner)", f("fees-accepted", "2026-09-20", "owner", amount="5.00"), True),
               ("earlier entry undone 2026-09-21 (owner)", UNDO, True), ("paid in full 2026-09-22", None, False)],
     f("paid-in-full", "2026-09-22", basis="bank")),
    ("cancel settlement", [("cancelled", f("cancelled", "2026-09-15"), True),
                           ("deposit kept 2026-09-15", f("deposit-kept", "2026-09-15", "owner"), True),
                           ("earlier entry undone 2026-09-21 (owner)", UNDO, True), ("refunded 2026-09-20", None, False)],
     f("refunded", "2026-09-20", "owner")),
    ("arrangement", [("balance to be paid in cash", f("arranged", "2026-09-20", method="cash"), True),
                     ("earlier entry undone 2026-09-21 (owner)", UNDO, True), ("cheque on the day", None, False)],
     f("arranged", "2026-09-22", method="cheque")),
    ("noted paid", [("deposit received", f("noted-paid", "2026-09-05", scope="part"), True),
                    ("balance paid in cash", None, False)], f("noted-paid", "2026-09-22", scope="full")),
    ("noted paid", [("paid per client email 2026-09-20", f("noted-paid", "2026-09-20", scope="full"), True),
                    ("earlier entry undone 2026-09-21 (owner)", UNDO, True), ("client paid 5 Sep", None, False)],
     f("noted-paid", "2026-09-22", scope="full")),
]


def held_row(clauses, value=1150, invoice="2026-09-01", event="2026-12-12", today=T):
    r = row(value, invoice, event, "; ".join(t for t, _, _ in clauses))
    return r, ev.booking_facts(REF, today, events=build_events(REF, clauses, True))


def test_an_unclaimed_note_that_contradicts_a_family_holds_the_booking():
    for family, clauses, _ in HOLDS:
        r, facts = held_row(clauses)
        assert cp.held(r, T, facts=facts) == [family], (family, clauses, cp.held(r, T, facts=facts))
        a = cp.assess(r, [], T, facts=facts)
        assert a["held"] == [family] and a["action"] == "hand_check" and a["record_in_books"] == [], (family, a)
        assert f"notes and recorded facts disagree: {family}" in cp.describe(a), cp.describe(a)


def test_the_loose_clause_recorded_as_a_fact_releases_it():
    for family, clauses, agree in HOLDS:
        text = clauses[-1][0]
        r, facts = held_row(clauses[:-1] + [(text, agree, True)])
        assert cp.held(r, T, facts=facts) == [], (family, text)


def test_notes_checked_releases_a_held_booking():
    for family, clauses, _ in HOLDS:
        loose = [ev.note_hash(t) for t, facts, claimed in clauses if not claimed]
        r, facts = held_row(clauses + [("notes checked 2026-09-28 (owner)",
                                        f("notes-checked", "2026-09-28", "owner", clauses=loose), True)])
        assert cp.held(r, T, facts=facts) == [], family


def test_markers_and_families_without_facts_never_hold():
    r, facts = held_row([("deposit seen 2026-09-05 (Starling)", f("deposit-seen", "2026-09-05"), True),
                         ("reminder drafted 2026-09-20", None, False), ("cancelled 20 Sep", None, False),
                         ("balance to be paid in cash", None, False)])
    assert cp.held(r, T, facts=facts) == []
    assert cp.is_cancelled(r, facts=facts), "a family with no facts is read from the notes"
    assert cp.assess(r, [], T, facts=facts)["reminded"]["deposit"], "markers are a union"


def test_a_held_booking_gets_no_receipt_and_no_books_line():
    clauses = [("deposit seen 2026-09-27 (Starling)", f("deposit-seen", "2026-09-27"), True),
               ("deposit received", f("noted-paid", "2026-09-27", scope="part"), True)]
    paid = [("2026-09-27", 325.0, "reference")]
    r, facts = held_row(clauses, 650, "2026-09-20", "2026-11-21")
    a = cp.assess(r, paid, T, facts=facts)
    assert "held" not in a and a["action"] == "receipt" and a["record_in_books"] == [["2026-09-27", 325.0, 0.0]], a
    r, facts = held_row(clauses + [("balance paid in cash", None, False)], 650, "2026-09-20", "2026-11-21")
    a = cp.assess(r, paid, T, facts=facts)
    assert a["held"] == ["noted paid"] and a["action"] == "hand_check" and a["just_received"] is False, a
    assert a["record_in_books"] == [], a


def test_the_monday_money_line_lists_a_held_booking_as_a_hand_check():
    import money_report as mr
    family, clauses, _ = HOLDS[0]
    r, facts = held_row(clauses, event="2026-12-12")
    a = cp.assess(r, [], T, facts=facts)
    assert a["state"] == "CANCELLED" and mr.needs_hand_check(a, T), a
    assert mr.hand_check_label(a) == "notes and recorded facts disagree: cancellation", mr.hand_check_label(a)
    assert mr.summary_lines([a], [], {"unpaid": 0, "unpaid_total": 0, "oldest_days": 0, "bank_changed": 0}, T)[3] == \
        "needs a hand check: 1 (2111 notes and recorded facts disagree: cancellation)"


class FakeClient:
    def __init__(self, items):
        self.items = items

    def feed(self, since, until, direction):
        return [i for i in self.items if i.get("direction") == direction]


def fresh_log():
    d = tempfile.mkdtemp()
    os.chmod(d, 0o700)
    os.environ["LCS_PRIVATE_DIR"] = d
    ev.clear_cache()
    return d


def test_collect_reports_a_held_closed_or_cancelled_booking_from_the_log():
    fresh_log()
    try:
        closed = row(1150, "2026-06-01", "2026-10-15", "paid in full 2026-09-15; balance to be paid in cash; "
                     "earlier entry undone 2026-09-21 (owner); cheque on the day", ref="1506")
        cancelled = row(1150, "2026-09-01", "2026-12-05", "cancelled 20 Sep; reinstated 25 Sep", ref="0510")
        quiet = row(1150, "2026-09-01", "2026-12-06", "cancelled 20 Sep", ref="0511")
        before = cp.collect(FakeClient([]), [closed, cancelled, quiet], T)  # no log: 0510 reads reinstated, so open
        assert [(r["booking_ref"], "held" in a) for r, _, a in before] == [("0510", False)], before
        ev.append("booking", "1506", "paid-in-full", {"basis": "bank"}, "script", on="2026-09-15",
                  note=ev.note_hash("paid in full 2026-09-15"))
        eid = ev.append("booking", "1506", "arranged", {"method": "cash"}, "script", on="2026-09-15",
                        note=ev.note_hash("balance to be paid in cash"))
        ev.append("booking", "1506", "retract", {"target": eid, "why": "mistake"}, "owner", on="2026-09-21",
                  note=ev.note_hash("earlier entry undone 2026-09-21 (owner)"))
        ev.append("booking", "0510", "cancelled", {}, "script", on="2026-09-20", note=ev.note_hash("cancelled 20 Sep"))
        ev.append("booking", "0511", "cancelled", {}, "script", on="2026-09-20", note=ev.note_hash("cancelled 20 Sep"))
        got = {r["booking_ref"]: a for r, _, a in cp.collect(FakeClient([]), [closed, cancelled, quiet], T)}
        assert sorted(got) == ["0510", "1506"], got
        assert got["1506"]["held"] == ["arrangement"] and got["0510"]["held"] == ["cancellation"], got
        assert all(a["action"] == "hand_check" for a in got.values())
        assert cp.is_cancelled(cancelled) and not cp.open_rows([closed, cancelled, quiet], T)
    finally:
        os.environ["LCS_PRIVATE_DIR"] = _HOME
        ev.clear_cache()


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
            except Exception as e:  # an error is a failure too
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
