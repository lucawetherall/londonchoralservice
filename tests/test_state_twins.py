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
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_payments as cp  # noqa: E402
import lcs_events as ev  # noqa: E402
import lcs_money as lm  # noqa: E402
import singer_invoices as si  # noqa: E402
import state_cases  # noqa: E402
from state_cases import BOOKING_CASES, SINGER_CASES, T, seen  # noqa: E402

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


def test_a_cancellation_whose_ledger_write_failed_but_landed_is_still_cancelled():
    """The review's repro: the drafter's `cancelled` fact, a write-failed retract in the same run, and the note in
    the ledger after all. The note is read: cancelled, never a deposit reminder."""
    note = "cancelled 2026-09-10 by client email"
    clauses = [("PENDING: invoiced", None, False),
               (note, [f("cancelled", "2026-09-10"), f("retract", "2026-09-10", why="write-failed")], True)]
    r, facts = held_row(clauses, 1150, "2026-09-01", "2026-12-12")
    a = cp.assess(r, [], T, facts=facts)
    assert cp.is_cancelled(r, facts=facts) and a["state"] == "CANCELLED" and a["action"] == "none", a
    assert cp.held(r, T, facts=facts) == []
    r, facts = held_row(clauses[:1] + [("", clauses[1][1], False)], 1150, "2026-09-01", "2026-12-12")
    r["notes"] = "PENDING: invoiced"  # the note never landed: nothing happened
    assert cp.assess(r, [], T, facts=facts)["state"] == "DEPOSIT_OVERDUE"


def test_a_script_write_failed_retract_never_reopens_an_owner_close():
    clauses = [("short by fees £12.40 accepted 2026-09-27 (owner)",
                [f("fees-accepted", "2026-09-27", "owner", amount="12.40"),
                 f("retract", "2026-09-27", "script", why="write-failed")], True)]
    r, facts = held_row(clauses, 950, "2026-08-24", "2026-10-10")
    assert cp.closed_on(r, T, facts=facts) == datetime.date(2026, 9, 27) and not cp.open_rows([r], T, facts={REF: facts})


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


# --- Task 6: the pipeline's reviews-due and done-due, and the Ads upload ----------------------------------------

def pipeline_views(r, today, facts):
    import pipeline
    enquiry = {c: "" for c in pipeline.COLUMNS} | {"enquiry_id": "t-1", "status": "confirmed", "booking_ref": REF}
    r = dict(r, occasion="wedding")
    return {"reviews": [d["booking_ref"] for d in pipeline.reviews_due([r], today, facts={REF: facts})],
            "done": [d["booking_ref"] for d in pipeline.done_due([enquiry], [r], today, facts={REF: facts})]}


REVIEW_CASES = [  # (name, event date, clauses): the review window is 3 to 14 days after the event
    ("closed, not yet asked", "2026-09-21",
     [seen("2026-09-04"), ("paid in full 2026-09-20", f("paid-in-full", "2026-09-20", basis="bank"))]),
    ("closed and asked", "2026-09-21",
     [seen("2026-09-04"), ("paid in full 2026-09-20", f("paid-in-full", "2026-09-20", basis="bank")),
      ("review request drafted 2026-09-25", f("review-drafted", "2026-09-25"))]),
    ("closed, review skipped for a planner", "2026-09-21",
     [("paid in full 2026-09-20 (owner)", f("paid-in-full", "2026-09-20", "owner", basis="owner")),
      ("review request skipped 2026-09-25 (planner)", f("review-skipped", "2026-09-25", reason="planner"))]),
    ("closed but cancelled", "2026-09-21",
     [("paid in full 2026-09-20", f("paid-in-full", "2026-09-20", basis="bank")),
      ("cancelled 2026-09-22 by client email", f("cancelled", "2026-09-22"))]),
    ("not closed", "2026-09-21", [seen("2026-09-04")]),
]


def test_reviews_due_and_done_due_read_the_same_three_ways():
    for name, event, clauses in REVIEW_CASES:
        case = (name, 1150, "2026-09-02", event, clauses, [], T)
        got = {label: pipeline_views(r, T, facts) for label, r, facts in three_ways(case)}
        assert got["events"] == got["notes"] and got["both"] == got["notes"], (name, got)
    assert pipeline_views(three_ways(("x", 1150, "2026-09-02", "2026-09-21", REVIEW_CASES[0][2], [], T))[1][1], T,
                          ev.booking_facts(REF, T, events=build_events(REF, REVIEW_CASES[0][2], False))) == \
        {"reviews": [REF], "done": [REF]}


def test_a_fee_closed_booking_is_review_due_before_apply_writes_paid_in_full():
    """Bug 3: reviews-due and done-due read the close through closed_on, so an accepted fee closes for them too."""
    notes = "deposit seen 2026-08-26 (Starling); short by fees £12.40 accepted 2026-09-20 (owner)"
    r = row(950, "2026-08-24", "2026-09-21", notes)
    assert pipeline_views(r, T, ev.booking_facts(REF, T, events=[])) == {"reviews": [REF], "done": [REF]}


def test_a_held_booking_is_neither_review_due_nor_done_due_nor_uploaded():
    import upload_bookings
    clauses = [("paid in full 2026-09-20", f("paid-in-full", "2026-09-20", basis="bank"), True),
               ("cancelled 20 Sep", f("cancelled", "2026-09-20"), True),
               ("reinstated 25 Sep", None, False)]
    r, facts = held_row(clauses, 1150, "2026-09-02", "2026-09-21")
    ok, okf = held_row([c for c in clauses[:1]], 1150, "2026-09-02", "2026-09-21")
    assert pipeline_views(ok, T, okf) == {"reviews": [REF], "done": [REF]}
    assert cp.held(r, T, facts=facts) == ["cancellation"]
    assert pipeline_views(r, T, facts) == {"reviews": [], "done": []}
    extra = dict(invoice_date="2026-09-02", enquiry_date="2026-09-01", gclid="Cj0KCQjwTESTCLICKID",
                 consent="granted", uploaded_at="")
    ready, skipped = upload_bookings.select_ready([dict(ok, **extra)], facts={REF: okf})
    assert [x[0]["booking_ref"] for x in ready] == [REF] and skipped == [], (ready, skipped)
    ready, skipped = upload_bookings.select_ready([dict(r, **extra)], facts={REF: facts})
    assert ready == [] and skipped == [(REF, "held: notes and recorded facts disagree")], skipped


# --- Task 7: singer invoices -------------------------------------------------------------------------------------

REPLACED = {"bank-warning": ("bank_changed", "no"), "bank-confirmed": ("bank_confirmed", ""), "withdrawn": ("withdrawn", "")}


def singer_rows(invoices, mode):
    """(store rows, {message id: Facts}) for one reading: "notes", "events" or "both"."""
    rows, facts = [], {}
    for spec in invoices:
        fp = lm.bank_fingerprint(*spec["acct"]) if spec["acct"] else None
        r = {k: v for k, v in spec.items() if k not in ("acct", "clauses")}
        r.update(bank_fp=fp or "", bank_last4=spec["acct"][1][-4:] if fp else "")
        clauses = []
        for text, fs in spec["clauses"]:
            filled = [(k, {**fl, "fp8": fp[:8] if fp else ""} if fl.get("fp8") == "*" else fl, on, by)
                      for k, fl, on, by in facts_list(fs)]
            clauses.append((text, filled or None))
        with_text = [t for t, fs in clauses if t is not None]
        neutral = [t for t, fs in clauses if t is not None and fs is None]
        r["notes"] = "; ".join(neutral if mode == "events" else with_text)
        if mode == "events":
            for _, fs in clauses:
                for k, *_ in facts_list(fs):
                    if k in REPLACED:
                        r[REPLACED[k][0]] = REPLACED[k][1]
        events = [] if mode == "notes" else build_events(r["message_id"], [(t or "", fs, t is not None and mode == "both")
                                                                            for t, fs in clauses], False, "singer_invoice")
        facts[r["message_id"]] = ev.invoice_facts(r["message_id"], T, events=events)
        rows.append(r)
    return rows, facts


def code_of(w):
    return si.warning_code(w) or w


def singer_reading(rows, facts, today):
    out = {}
    for r in rows:
        out[r["message_id"]] = {
            "ring_first": si.ring_first(r, facts=facts), "ring_first_in": si.ring_first_in(rows, r, facts=facts),
            "trusted": si.is_trusted(r, facts=facts), "account_trusted": si.account_trusted(rows, r, facts=facts),
            "trust_label": si.trust_label(rows, r, facts=facts), "withdrawn": si.is_withdrawn(r, facts=facts),
            "open": si.is_open(r, facts=facts), "changed": si.bank_changed(r, facts=facts),
            "warnings": sorted(code_of(w) for w in si.live_warnings(rows, r, facts=facts)),
            "bill": si.stored_bill(rows, r, facts=facts), "held": si.held(rows, r, facts=facts)}
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        si.print_books_due(rows, today=today, facts=facts)
    out["summary"] = si.summary(rows, today, facts=facts)
    out["books_due"] = printed.getvalue()
    return out


def test_every_singer_case_reads_the_same_three_ways():
    for name, invoices, today in SINGER_CASES:
        got = {mode: singer_reading(*singer_rows(invoices, mode), today) for mode in ("notes", "events", "both")}
        assert all(v["held"] == [] for x in got.values() for k, v in x.items() if k not in ("summary", "books_due")), \
            (name, got)
        assert got["events"] == got["notes"], (name, got["notes"], got["events"])
        assert got["both"] == got["notes"], (name, got["notes"], got["both"])


def test_the_singer_cases_say_what_their_names_say():
    got = {name: singer_reading(*singer_rows(invoices, "events"), today) for name, invoices, today in SINGER_CASES}
    assert got["two invoices to a changed account, neither confirmed"]["summary"]["bank_changed"] == 2
    ok = got["a confirmation clears every alarm on every invoice to that account (50f2429d)"]
    assert not ok["a"]["ring_first_in"] and not ok["b"]["ring_first_in"] and ok["b"]["trust_label"] == "confirmed by phone"
    assert ok["b"]["warnings"] == ["amount not found: check the invoice by hand"] and ok["a"]["bill"] == "yes"
    assert ok["b"]["bill"] == "no (amount not found)", ok["b"]  # the bank alarm is cleared; the missing amount isn't
    assert got["a verified payment trusts the account on the next invoice"]["b"]["trust_label"] == "paid to verifiably"
    assert got["a different account for the same singer is still flagged"]["b"]["ring_first_in"]
    void = got["a rescan to new details voids the confirmation"]["a"]
    assert void["ring_first_in"] and void["trust_label"] == "" and void["bill"] == "no (bank warning)", void
    assert got["no bank details on the invoice"]["a"]["warnings"] == ["no-details"]
    assert got["withdrawn"]["a"]["withdrawn"] and not got["withdrawn"]["a"]["open"]
    assert got["withdrawn"]["summary"]["unpaid"] == 1
    settled = got["settled by hand is paid, never trusted"]["a"]
    assert not settled["open"] and not settled["trusted"]
    assert "THANKS DUE" not in got["a verified payment thanked"]["books_due"]
    assert "THANKS DUE a:" in got["a verified payment not yet thanked"]["books_due"]


def singer_held_rows(clauses, cols=None, acct=state_cases.BEN):
    """One invoice "a" with these (text, facts, claimed) clauses, read events first."""
    fp = lm.bank_fingerprint(*acct)
    r = dict(state_cases.inv("a", "2026-09-01", **(cols or {})), bank_fp=fp, bank_last4=acct[1][-4:])
    del r["acct"], r["clauses"]
    filled = [(t, [(k, {**fl, "fp8": fp[:8]} if fl.get("fp8") == "*" else fl, on, by) for k, fl, on, by in facts_list(fs)]
               or None, c) for t, fs, c in clauses]
    r["notes"] = "; ".join(t for t, _, _ in filled)
    return [r], {"a": ev.invoice_facts("a", T, events=build_events("a", filled, True, "singer_invoice"))}


SINGER_HOLDS = [
    ("bank warnings", [("rescanned 2026-09-14", state_cases.warn("2026-09-14"), True),
                       (state_cases.CHANGED, None, False)]),
    ("withdrawal", [("withdrawn 2026-09-15 (not-ours)", f("withdrawn", "2026-09-15", reason="not-ours"), True),
                    ("earlier entry undone 2026-09-16 (owner)", UNDO, True),
                    ("withdrawn 2026-09-17 (duplicate)", None, False)]),
    ("settlement", [("settled by hand", f("settled", "2026-09-15", "owner", amount="100.00"), True),
                    ("earlier entry undone 2026-09-21 (owner)", UNDO, True), ("settled by hand again", None, False)]),
]


def test_an_unclaimed_singer_note_that_contradicts_a_family_holds_the_invoice():
    for family, clauses in SINGER_HOLDS:
        rows, facts = singer_held_rows(clauses)
        r = rows[0]
        assert si.held(rows, r, facts=facts) == [family], (family, si.held(rows, r, facts=facts))
        assert si.ring_first_in(rows, r, facts=facts) and si.ring_first(r, facts=facts), family
        assert si.stored_bill(rows, r, facts=facts) == "no (held)", family


def test_a_trusted_account_never_holds_on_a_bank_alarm():
    rows, facts = singer_held_rows(SINGER_HOLDS[0][1] + [(state_cases.CONFIRMED[0], state_cases.CONFIRMED[1], True)])
    assert si.held(rows, rows[0], facts=facts) == [] and not si.ring_first_in(rows, rows[0], facts=facts)


def test_claimed_or_checked_singer_notes_never_hold():
    for family, clauses in SINGER_HOLDS:
        rows, facts = singer_held_rows([c for c in clauses if c[2]])
        assert si.held(rows, rows[0], facts=facts) == [], family
        loose = [ev.note_hash(t) for t, _, c in clauses if not c]
        rows, facts = singer_held_rows(clauses + [("notes checked 2026-09-28 (owner)",
                                                   f("notes-checked", "2026-09-28", "owner", clauses=loose), True)])
        assert si.held(rows, rows[0], facts=facts) == [], family


def test_the_trust_history_only_names_rows_on_the_same_account():
    """trust_label checks names only among invoices to the same fingerprint (only they can vouch), so a page over
    the whole store stays linear in the rows it compares by name."""
    rows = []
    for s in range(30):
        for i in range(10):
            rows.append({"message_id": f"m{s}x{i}", "received": "2026-09-01", "singer_name": f"Singer{s} Surname{s}",
                         "singer_email": f"s{s}@example.org", "bank_fp": f"{s:016x}", "notes": "", "paid_on": "",
                         "paid_verified": "yes" if i == 0 else "", "bank_confirmed": ""})
    calls, real = [], si.normalise_name
    si.normalise_name = lambda n: calls.append(n) or real(n)
    try:
        labels = {si.trust_label(rows, r, facts={}) for r in rows}
    finally:
        si.normalise_name = real
    assert labels == {"paid to verifiably"}
    assert len(calls) <= 3 * 10 * len(rows), len(calls)  # the same-account group, not the whole store, per row


def test_with_no_log_the_singer_readers_are_todays():
    ev.clear_cache()
    for name, invoices, today in SINGER_CASES:
        rows, facts = singer_rows(invoices, "notes")
        assert singer_reading(rows, None, today) == singer_reading(rows, facts, today), name


# --- held bookings on Today and the Monday line (review item 4) ------------------------------------------------

class P:
    def __init__(self, value):
        self.value, self.error, self.ok = value, None, True


def held_assessments():
    """A held booking that reads BALANCE_DUE with a fee-sized gap, one that reads DEPOSIT_OVERDUE, and the same two
    unheld: [held balance, held deposit, balance, deposit]."""
    base =[("cancelled 20 Sep", [f("cancelled", "2026-09-20"), f("reinstated", "2026-09-21", "owner")], True)]
    paid = [("2026-09-01", 1137.60, "reference")]  # £12.40 short of £1,150
    out = []
    for ref, clauses, pay, event in (("H1", base + [("cancelled again 22 Sep", None, False)], paid, "2026-10-01"),
                                     ("H2", base + [("cancelled again 22 Sep", None, False)], [], "2026-12-12"),
                                     ("B1", base, paid, "2026-10-01"), ("D1", base, [], "2026-12-12")):
        r, facts = held_row(clauses, 1150, "2026-08-20", event)
        out.append(dict(cp.assess(dict(r, booking_ref=ref), pay, T, facts=facts), ref=ref))
    assert [a["state"] for a in out] == ["BALANCE_DUE", "DEPOSIT_OVERDUE", "BALANCE_DUE", "DEPOSIT_OVERDUE"]
    assert [bool(a.get("held")) for a in out] == [True, True, False, False], out
    return out


def test_a_held_booking_is_never_chased_or_offered_as_a_fee_on_today():
    sys.path.insert(0, ROOT)
    from command_centre import models
    import money_report as mr
    got = held_assessments()
    assert models.fee_shortfall(got[0], True) is None and models.fee_shortfall(got[2], True) is not None
    hand = [{"ref": a["ref"], "state": a["state"], "label": mr.hand_check_label(a)} for a in got if mr.needs_hand_check(a, T)]
    rows, _ = models.needs_you({"bank": P({"assessments": got, "bank_checked": True}), "hand": P(hand)})
    kinds = {r["kind"]: r for r in rows}
    assert [r["item"]["ref"] for r in rows if r["kind"] == "hand"] == ["H1", "H2"], rows
    assert kinds["deposits"]["refs"] == ["D1"] and "balances" not in kinds, rows  # B1 is asked about as a fee
    assert [r["item"]["ref"] for r in rows if r["kind"] == "fee"] == ["B1"], rows
    assert models.hand_reason(got[0], True) == "notes and recorded facts disagree: cancellation"


def test_the_monday_overdue_and_balances_lines_skip_held_bookings():
    import money_report as mr
    got = held_assessments()
    lines = mr.summary_lines(got, [], {"unpaid": 0, "unpaid_total": 0, "oldest_days": 0, "bank_changed": 0}, T)
    assert lines[1] == "deposits overdue: 1 (D1)", lines[1]
    assert lines[2].startswith("balances due in the next 7 days: 1, £12.40 (B1)"), lines[2]
    assert lines[3].startswith("needs a hand check: 2 (H1 notes and recorded facts disagree"), lines[3]


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
        import lcs_owner
        saved = lcs_owner._PROVEN, os.environ.pop("LCS_BOOKINGS_CSV")
        lcs_owner._PROVEN = True  # as the Command Centre's owner run
        try:
            ev.append("booking", "1506", "retract", {"target": eid, "why": "mistake"}, "owner", on="2026-09-21",
                      note=ev.note_hash("earlier entry undone 2026-09-21 (owner)"))
        finally:
            lcs_owner._PROVEN, os.environ["LCS_BOOKINGS_CSV"] = saved
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
