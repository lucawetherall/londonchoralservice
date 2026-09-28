#!/usr/bin/env python3
"""Tests for scripts/bookings/check_payments.py. Stdlib only."""
import contextlib, csv, datetime, io, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import check_payments as cp

PY, SCRIPT = sys.executable, os.path.join(ROOT, "scripts", "bookings", "check_payments.py")

T = datetime.date(2026, 9, 28)


def row(ref, value, invoice, event, notes="", name="Ann Smith"):
    return {"booking_ref": ref, "value_gbp": str(value), "invoice_date": invoice, "event_date": event,
            "notes": notes, "client_name": name}


def pay(amount, when, ref="", who="Someone"):
    return {"direction": "IN", "amount": {"minorUnits": int(round(amount * 100))},
            "transactionTime": when + "T10:00:00Z", "reference": ref, "counterPartyName": who}


def test_match_by_reference():
    found = cp.match([row("2111", 650, "2026-08-22", "2026-11-21")], [pay(325, "2026-08-26", "INV 2111")], T)
    assert found["2111"] == [("2026-08-26", 325.0, "reference")]


def test_match_by_surname_and_deposit():
    found = cp.match([row("0810", 375, "2026-09-22", "2026-10-08")], [pay(187.5, "2026-09-24", "deposit", "MRS A SMITH")], T)
    assert found["0810"][0][2] == "name and amount"


def test_amount_only_fitting_several_bookings_is_unconfirmed_on_each():
    one = [row("A", 1150, "2026-09-01", "2026-10-10", name="X Y")]
    two = one + [row("B", 1150, "2026-09-02", "2026-10-11", name="P Q")]
    payment = [pay(1150, "2026-09-05", "wedding")]
    assert cp.match(one, payment, T)["A"][0][2] == "amount only"
    found = cp.match(two, payment, T)
    assert found["A"] and found["B"], found
    assert all(how not in cp.CONFIDENT for hits in found.values() for _, _, how in hits)
    assert [cp.assess(r, found[r["booking_ref"]], T)["state"] for r in two] == ["CHECK_PAYMENT", "CHECK_PAYMENT"]


def test_past_event_is_never_overdue():
    assert cp.assess(row("2509", 3225, "2026-09-12", "2026-09-21"), [], T)["state"] == "PAST_UNMATCHED"


def test_noted_paid_is_not_chased():
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep"), [], T)["state"] == "NOTED_PAID"


def test_deposit_overdue_for_future_event():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced"), [], T)
    assert a["state"] == "DEPOSIT_OVERDUE" and a["deposit_due"] == "2026-09-08"


def test_awaiting_deposit_inside_seven_days():
    assert cp.assess(row("X", 500, "2026-09-25", "2026-10-30", "PENDING: invoiced"), [], T)["state"] == "AWAITING_DEPOSIT"


def test_balance_due_from_three_days_before():
    paid = [("2026-08-26", 325.0, "reference")]
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-10-01"), paid, T)["state"] == "BALANCE_DUE"
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-11-21"), paid, T)["state"] == "DEPOSIT_SEEN"


def test_paid_in_full():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    a = cp.assess(row("2111", 650, "2026-08-22", "2026-11-21"), paid, T)
    assert a["state"] == "PAID_IN_FULL" and a["balance"] == 0


def test_receipt_due_lasts_fourteen_days_until_a_receipt_is_drafted():
    paid = [("2026-09-27", 325.0, "reference")]
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "PENDING: invoiced"), paid, T)["just_received"] is True
    # a Monday --apply rewrites PENDING; the receipt signal must survive it
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "deposit seen 2026-09-27 (Starling)"), paid, T)["just_received"] is True
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "deposit seen 2026-09-27 (Starling); receipt drafted 2026-09-28"),
                     paid, T)["just_received"] is False
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), [("2026-09-14", 325.0, "reference")], T)["just_received"] is True
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), [("2026-09-13", 325.0, "reference")], T)["just_received"] is False
    # an old first payment, as in the live 2111 row, never asks for a receipt
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-11-21", "deposit seen 2026-08-22 (Starling)"),
                     [("2026-08-22", 325.0, "reference")], T)["just_received"] is False
    # unconfirmed, cancelled or past: never
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), [("2026-09-27", 325.0, "amount only")], T)["just_received"] is False
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "cancelled 27 Sep"), paid, T)["just_received"] is False
    assert cp.assess(row("X", 650, "2026-09-10", "2026-09-26"), [("2026-09-20", 325.0, "reference")], T)["just_received"] is False


def test_reminder_marks_are_distinct():
    a = cp.assess(row("X", 650, "2026-08-22", "2026-10-01", "deposit seen x; balance reminder drafted 2026-09-28"),
                  [("2026-08-26", 325.0, "reference")], T)
    assert a["reminded"] == {"deposit": False, "balance": True, "receipt": False}
    b = cp.assess(row("X", 650, "2026-09-01", "2026-10-30", "PENDING: x; reminder drafted 2026-09-20"), [], T)
    assert b["reminded"]["deposit"] is True and b["reminded"]["balance"] is False


def test_updated_notes_clears_pending_and_marks_full():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    r = row("X", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced; from quote")
    a = cp.assess(r, paid, T)
    assert cp.updated_notes(r["notes"], a, paid) == "deposit seen 2026-08-26 (Starling); from quote; paid in full 2026-09-20"


def test_describe_never_names_the_client():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced", name="Secret Person"), [], T)
    assert "Secret" not in cp.describe(a) and "DEPOSIT OVERDUE since 2026-09-08" in cp.describe(a)


class FakeClient:
    def __init__(self, items):
        self.items, self.calls = items, []

    def feed(self, since, until, direction):
        self.calls.append((since, until, direction))
        return self.items


def test_reference_is_token_exact():
    rows = [row("2408", 650, "2026-08-22", "2026-11-21"), row("24081", 900, "2026-08-22", "2026-11-21")]
    found = cp.match(rows, [pay(325, "2026-08-26", "INV 24081")], T)
    assert found["2408"] == [] and found["24081"] == [("2026-08-26", 325.0, "reference")]
    found = cp.match(rows[:1], [pay(325, "2026-08-26", "INV 24081")], T)
    assert all(how != "reference" for _, _, how in found["2408"])


def test_reference_accepts_inv_prefix_forms():
    rows = [row("2111", 650, "2026-08-22", "2026-11-21")]
    for ref in ("INV2111", "inv-2111 deposit", "2111", "Invoice INV 2111", "INV2111DEPOSIT", "INV2111DEP", "INV-2111",
                "LCS2111", "INVOICE2111", "INV#2111", "inv:2111", "Ref: INV 2111.", "Smith wedding 2111"):
        assert cp.match(rows, [pay(325, "2026-08-26", ref)], T)["2111"] == [("2026-08-26", 325.0, "reference")], ref
    for ref in ("INV24081", "21110", "INV 21112"):
        assert all(how != "reference" for _, _, how in cp.match(rows, [pay(325, "2026-08-26", ref)], T)["2111"]), ref


def test_reference_to_a_closed_booking_never_falls_through():
    rows = [row("2401", 1150, "2026-08-01", "2026-10-10", "paid in full 2026-09-19"),
            row("2410", 1150, "2026-09-10", "2026-11-14", "PENDING: invoiced")]
    found = cp.match(rows, [pay(575, "2026-09-25", "INV 2401 balance", "ANN SMITH")], T)
    assert found["2401"] == [("2026-09-25", 575.0, "reference")] and found["2410"] == []


def test_collect_never_credits_the_wrong_booking():
    rows = [row("2401", 1150, "2026-08-01", "2026-10-10", "paid in full 2026-09-19"),
            row("2410", 1150, "2026-09-10", "2026-11-14", "PENDING: invoiced")]
    client = FakeClient([pay(575, "2026-09-25", "INV 2401 balance")])
    got = cp.collect(client, rows, T)
    assert [r["booking_ref"] for r, _, _ in got] == ["2410"]
    _, paid, a = got[0]
    assert paid == [] and a["state"] in ("DEPOSIT_OVERDUE", "AWAITING_DEPOSIT") and a["just_received"] is False
    assert client.calls and all(c[2] == "IN" for c in client.calls)
    assert cp.received_since(client, rows, datetime.date(2026, 9, 21), T) == [("2401", "2026-09-25", 575.0)]


def test_collect_uses_the_feed_and_assesses_open_rows():
    rows = [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced"),
            row("2000", 500, "2026-08-01", "2026-12-01", "cancelled by client 3 Sep")]
    got = cp.collect(FakeClient([pay(325, "2026-08-26", "INV 2111")]), rows, T)
    assert [(r["booking_ref"], a["state"], a["just_received"]) for r, _, a in got] == [("2111", "DEPOSIT_SEEN", False)]


def test_unrelated_amount_only_payment_needs_a_hand_check():
    r = row("2410", 1150, "2026-09-10", "2026-11-14", "PENDING: invoiced")
    got = cp.collect(FakeClient([pay(575, "2026-09-20", "", "J BLOGGS")]), [r], T)
    _, paid, a = got[0]
    assert a["state"] == "CHECK_PAYMENT" and a["just_received"] is False and a["received"] == 0
    assert a["unconfirmed"] == [["2026-09-20", 575.0]]
    assert "possible payment £575.00 on 2026-09-20 matched by amount only: confirm by hand" in cp.describe(a)
    assert cp.updated_notes(r["notes"], a, paid) == "PENDING: invoiced"
    assert cp.received_since(FakeClient([pay(575, "2026-09-20")]), [r], datetime.date(2026, 9, 1), T) == []


def test_surname_must_be_a_whole_word():
    rows = [row("0810", 375, "2026-09-22", "2026-10-08", name="Jo Lee")]
    found = cp.match(rows, [pay(187.5, "2026-09-24", "deposit", "ASHLEE K")], T)
    assert all(how != "name and amount" for _, _, how in found["0810"])
    assert cp.match(rows, [pay(187.5, "2026-09-24", "deposit", "MR J LEE")], T)["0810"][0][2] == "name and amount"


def test_name_match_needs_the_booking_window():
    rows = [row("0810", 375, "2026-09-22", "2026-10-08")]
    found = cp.match(rows, [pay(187.5, "2026-03-01", "deposit", "MRS A SMITH")], T)
    assert found["0810"] == []


def test_payment_date_is_london_date():
    rows = [row("2111", 650, "2026-08-22", "2026-11-21")]
    item = pay(325, "2026-09-30", "INV 2111")
    item["transactionTime"] = "2026-09-30T23:30:00.000Z"
    assert cp.match(rows, [item], T)["2111"][0][0] == "2026-10-01"


def test_balance_due_respects_a_hand_written_paid_note():
    paid = [("2026-08-26", 325.0, "reference")]
    for note in ("deposit seen 2026-08-26 (Starling); balance paid by cash at the rehearsal",
                 "deposit seen 2026-08-26 (Starling); Fully paid", "paid by cheque 20 Sep"):
        assert cp.assess(row("2111", 650, "2026-08-22", "2026-10-01", note), paid, T)["state"] == "NOTED_PAID", note
    assert cp.assess(row("2111", 650, "2026-08-22", "2026-10-01", "deposit seen 2026-08-26 (Starling)"),
                     paid, T)["state"] == "BALANCE_DUE"


def test_pending_does_not_hide_a_paid_note():
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced; client paid by cash 5 Sep"),
                     [], T)["state"] == "NOTED_PAID"
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced"), [], T)["state"] == "DEPOSIT_OVERDUE"


def test_missing_value_is_never_chased():
    for v in ("", "TBC", "0"):
        a = cp.assess(row("X", v, "2026-09-01", "2026-10-30", "PENDING: invoiced"), [], T)
        assert a["state"] == "CHECK_VALUE", v
        assert "booking value missing or unreadable in the ledger (check by hand)" in cp.describe(a)


def test_cancelled_anywhere_in_notes():
    r = row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced; Cancelled 20 Sep")
    assert cp.is_cancelled(r) and cp.assess(r, [], T)["state"] == "CANCELLED"
    assert cp.describe(cp.assess(r, [], T)).endswith(" · cancelled")
    assert cp.open_rows([r, row("Y", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced")]) == \
        [row("Y", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced")]


def test_reminded_marks_ignore_case():
    a = cp.assess(row("X", 650, "2026-08-22", "2026-10-01", "Balance Reminder Drafted 2026-09-28"),
                  [("2026-08-26", 325.0, "reference")], T)
    assert a["reminded"] == {"deposit": False, "balance": True, "receipt": False}
    b = cp.assess(row("X", 650, "2026-09-01", "2026-10-30", "PENDING: x; Reminder drafted 2026-09-20; Receipt drafted"), [], T)
    assert b["reminded"] == {"deposit": True, "balance": False, "receipt": True}


def test_updated_notes_on_empty_notes():
    paid = [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")]
    a = cp.assess(row("X", 650, "2026-08-22", "2026-11-21", ""), paid, T)
    assert cp.updated_notes("", a, paid) == "paid in full 2026-09-20"


def run_cli(notes, *args):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    cols = ["booking_ref", "value_gbp", "invoice_date", "event_date", "notes", "client_name"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row("2111", 650, "2026-08-22", "2026-11-21", notes))
    env = dict(os.environ, LCS_BOOKINGS_CSV=path, LCS_PRIVATE_DIR=d)
    p = subprocess.run([PY, SCRIPT, *args], env=env, capture_output=True, text=True)
    with open(path, newline="") as f:
        return p, list(csv.DictReader(f))[0]["notes"]


def test_cli_reminded_default_kind():
    p, notes = run_cli("PENDING: invoiced", "--reminded", "2111")
    assert p.returncode == 0 and notes == f"PENDING: invoiced; reminder drafted {datetime.date.today()}", notes


def test_cli_reminded_balance_kind():
    p, notes = run_cli("deposit seen 2026-08-26 (Starling)", "--reminded", "2111", "--kind", "balance")
    assert p.returncode == 0 and notes.endswith(f"; balance reminder drafted {datetime.date.today()}"), notes


def test_cli_reminded_unknown_ref_fails():
    p, notes = run_cli("PENDING: invoiced", "--reminded", "9999")
    assert p.returncode != 0 and notes == "PENDING: invoiced"



def test_json_without_a_token_prints_an_empty_list():
    out, err, saved = io.StringIO(), io.StringIO(), (cp.lm.keychain_token, sys.argv, cp.LEDGER)
    cp.lm.keychain_token, sys.argv = (lambda: None), ["check_payments.py", "--json"]
    cp.LEDGER = os.path.join(tempfile.mkdtemp(), "none.csv")
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cp.main()
    finally:
        cp.lm.keychain_token, sys.argv, cp.LEDGER = saved
    assert out.getvalue() == "[]\n" and "No Starling token" in err.getvalue()


# --- suffix refs ("1212", "1212A") -------------------------------------------------------------

SUFFIX_ROWS = [row("1212", 650, "2026-09-20", "2026-12-12", "PENDING: invoiced", name="Ann Smith"),
               row("1212A", 650, "2026-09-21", "2026-12-12", "PENDING: invoiced", name="Bo Jones")]


def test_spaced_letter_suffix_names_the_suffixed_ref():
    for ref in ("INV 1212 A", "INV1212A", "INV-1212-A", "1212A deposit"):
        found = cp.match(SUFFIX_ROWS, [pay(325, "2026-09-24", ref, "BO JONES")], T)
        assert found["1212A"] == [("2026-09-24", 325.0, "reference")] and found["1212"] == [], (ref, found)


def test_bare_number_with_suffixed_siblings_uses_the_surname():
    found = cp.match(SUFFIX_ROWS, [pay(325, "2026-09-24", "INV 1212", "BO JONES")], T)
    assert found["1212A"] == [("2026-09-24", 325.0, "reference")] and found["1212"] == [], found


def test_bare_number_with_suffixed_siblings_and_no_surname_is_unconfirmed_on_all():
    found = cp.match(SUFFIX_ROWS, [pay(325, "2026-09-24", "1212", "KATE DOE")], T)
    assert found["1212"] and found["1212A"], found
    states = [cp.assess(r, found[r["booking_ref"]], T) for r in SUFFIX_ROWS]
    assert [a["state"] for a in states] == ["CHECK_PAYMENT", "CHECK_PAYMENT"]
    assert all(a["received"] == 0 and a["just_received"] is False for a in states)


def test_reference_to_one_booking_from_another_clients_name_is_unconfirmed():
    rows = [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced", name="Ann Smith"),
            row("0512", 650, "2026-09-20", "2026-12-05", "PENDING: invoiced", name="Bo Jones")]
    found = cp.match(rows, [pay(325, "2026-09-24", "INV 2111", "BO JONES")], T)
    assert found["2111"] and found["0512"], found
    assert all(how not in cp.CONFIDENT for hits in found.values() for _, _, how in hits)
    # the booking's own client (or a stranger) paying by reference stays confident
    assert cp.match(rows, [pay(325, "2026-09-24", "INV 2111", "MRS A SMITH")], T)["2111"][0][2] == "reference"
    assert cp.match(rows, [pay(325, "2026-09-24", "INV 2111", "KATE DOE")], T)["2111"][0][2] == "reference"


# --- paid notes -------------------------------------------------------------------------------

def test_paid_notes_count_whatever_the_wording():
    for note in ("PENDING: invoiced by enquiry assistant, deposit not yet seen. Paid by cash 5 Sep",
                 "PENDING: invoiced by enquiry assistant, deposit not yet seen, client paid 5 Sep",
                 "PENDING; deposit received by bank transfer",
                 "PENDING - settled in cash", "deposit seen 2026-09-05; from quote", "Deposit in 5 Sep (cash)"):
        assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", note), [], T)["state"] == "NOTED_PAID", note
    for note in ("PENDING: invoiced, deposit not yet seen", "PENDING: invoiced; unpaid", "PENDING: not paid yet",
                 "PENDING: invoiced; reminder drafted 2026-09-10"):
        assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", note), [], T)["state"] == "DEPOSIT_OVERDUE", note


def test_part_paid_needs_a_full_payment_note():
    paid = [("2026-08-26", 325.0, "reference")]
    for note in ("deposit seen 2026-08-26 (Starling); paid the balance", "deposit seen 2026-08-26 (Starling); paid 29 Sep",
                 "deposit seen 2026-08-26 (Starling); paid 29 September", "deposit seen 2026-08-26 (Starling); client paid on 2026-09-29",
                 "deposit seen 2026-08-26 (Starling); balance in cash 29 Sep", "deposit seen 2026-08-26 (Starling); settled in cash",
                 "deposit seen 2026-08-26 (Starling); rest paid in cash", "deposit seen 2026-08-26 (Starling); Paid in full (cash)"):
        assert cp.assess(row("2111", 650, "2026-08-22", "2026-09-30", note), paid, T)["state"] == "NOTED_PAID", note
    for note in ("deposit seen 2026-08-26 (Starling); deposit received", "deposit seen 2026-08-26 (Starling); deposit paid 26 Aug",
                 "deposit seen 2026-08-26 (Starling); balance not yet paid", "deposit seen 2026-08-26 (Starling); receipt drafted 2026-08-27"):
        assert cp.assess(row("2111", 650, "2026-08-22", "2026-09-30", note), paid, T)["state"] == "BALANCE_DUE", note


# --- dates and values -------------------------------------------------------------------------

def test_bad_dates_and_values_are_check_value_not_a_crash():
    for inv, ev in (("", "2026-10-30"), ("TBC", "2026-10-30"), (None, "2026-10-30"), ("2026-09-01", "TBC"), ("2026-09-01", "31/10/2026")):
        a = cp.assess(row("X", 500, inv, ev, "PENDING: x"), [], T)
        assert a["state"] == "CHECK_VALUE", (inv, ev, a["state"])
        assert "(check by hand)" in cp.describe(a)
    assert cp.assess(row("X", 500, "2026-09-01", "", "PENDING: x"), [], T)["state"] == "DEPOSIT_OVERDUE"
    for v in ("nan", "inf", "-inf", "NaN"):
        a = cp.assess(row("X", v, "2026-09-01", "2026-10-30", "PENDING: x"), [], T)
        assert a["state"] == "CHECK_VALUE", v
        json.dumps(a, allow_nan=False)


def test_collect_survives_a_row_with_bad_dates():
    rows = [row("X", 500, "", "2026-10-30", "PENDING: x"), row("Y", 500, "2026-09-01", "2026-10-30", "PENDING: x")]
    got = {r["booking_ref"]: a["state"] for r, _, a in cp.collect(FakeClient([]), rows, T)}
    assert got == {"X": "CHECK_VALUE", "Y": "DEPOSIT_OVERDUE"}, got


# --- short notice -----------------------------------------------------------------------------

def test_short_notice_deposit_falls_due_before_the_event():
    r = row("0210", 1150, "2026-09-26", "2026-10-02", "PENDING: invoiced")
    a = cp.assess(r, [], datetime.date(2026, 9, 28))
    assert a["state"] == "AWAITING_DEPOSIT" and a["deposit_due"] == "2026-09-29" and a["short_notice"] is True
    assert cp.assess(r, [], datetime.date(2026, 9, 29))["state"] == "AWAITING_DEPOSIT"
    assert cp.assess(r, [], datetime.date(2026, 9, 30))["state"] == "DEPOSIT_OVERDUE"
    # never due on the invoice day itself
    assert cp.assess(row("X", 500, "2026-09-26", "2026-09-27", "PENDING"), [], datetime.date(2026, 9, 26))["deposit_due"] == "2026-09-27"
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING"), [], T)["short_notice"] is False
    assert cp.assess(row("X", 500, "2026-09-20", "2026-09-30", "PENDING"), [], T)["short_notice"] is True


# --- cancellations ----------------------------------------------------------------------------

def test_cancelled_wording():
    for note in ("Cancelled 20 Sep", "CANCELED", "cancellation confirmed by email", "PENDING; cancellation received"):
        assert cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", note)), note
    for note in ("PENDING: invoiced; cancellation terms explained", "postponed, not cancelled", "cancel policy sent"):
        assert not cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", note)), note


# --- notes, feed window, errors, lock ---------------------------------------------------------

def test_clearing_pending_without_a_semicolon_keeps_the_text():
    paid = [("2026-09-24", 325.0, "reference")]
    for notes, want in (("PENDING: invoiced, from quote", "deposit seen 2026-09-24 (Starling); invoiced, from quote"),
                        ("PENDING - invoiced", "deposit seen 2026-09-24 (Starling); invoiced"),
                        ("PENDING", "deposit seen 2026-09-24 (Starling)")):
        r = row("X", 650, "2026-09-20", "2026-11-21", notes)
        assert cp.updated_notes(notes, cp.assess(r, paid, T), paid) == want, notes


def test_received_since_counts_early_hours_bst_payments():
    rows = [row("2111", 650, "2026-08-22", "2026-11-21")]
    early = pay(325, "2026-09-21", "INV 2111")
    early["transactionTime"] = "2026-09-21T23:30:00Z"  # 00:30 on 22 Sep in London
    before = pay(100, "2026-09-21", "INV 2111")         # 11:00 on 21 Sep in London

    class UtcFeed(FakeClient):
        def feed(self, since, until, direction):
            self.calls.append((since, until, direction))
            lo, hi = since.isoformat() + "T00:00:00", until.isoformat() + "T00:00:00"
            return [i for i in self.items if lo <= i["transactionTime"][:19] < hi]

    c = UtcFeed([early, before])
    assert cp.received_since(c, rows, datetime.date(2026, 9, 22), T) == [("2111", "2026-09-22", 325.0)]
    assert c.calls[0][0] == datetime.date(2026, 9, 21)


class DownClient:
    def __init__(self, exc):
        self.exc = exc

    def feed(self, *a):
        raise self.exc

    def get(self, *a):
        raise self.exc

    def account(self):
        raise self.exc


def run_main_with(exc, *argv):
    import urllib.error
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    cols = ["booking_ref", "value_gbp", "invoice_date", "event_date", "notes", "client_name"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced"))
    before = open(path).read()
    out, err = io.StringIO(), io.StringIO()
    saved = (cp.lm.keychain_token, cp.lm.StarlingReadOnly, sys.argv, cp.LEDGER)
    cp.lm.keychain_token, cp.lm.StarlingReadOnly = (lambda: "tok"), (lambda tok: DownClient(exc))
    sys.argv, cp.LEDGER, code = ["check_payments.py", *argv], path, 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                cp.main()
            except SystemExit as e:
                code = e.code
    finally:
        cp.lm.keychain_token, cp.lm.StarlingReadOnly, sys.argv, cp.LEDGER = saved
    return code, out.getvalue(), err.getvalue(), open(path).read() == before


def test_starling_unavailable_is_one_quiet_line():
    import urllib.error
    for exc in (urllib.error.URLError("down"), urllib.error.HTTPError("u", 503, "x", {}, None), TimeoutError(), OSError("x")):
        code, out, err, unchanged = run_main_with(exc, "--apply", "--json")
        name = type(exc).__name__ + (f" {exc.code}" if isinstance(exc, urllib.error.HTTPError) else "")
        assert code in (0, None) and out == "[]\n" and err == f"Starling unavailable ({name})\n" and unchanged, (name, code, out, err)
        code, out, err, unchanged = run_main_with(exc, "--apply")
        assert code in (0, None) and out == "" and err == f"Starling unavailable ({name})\n" and unchanged, (name, out, err)


def test_apply_and_reminded_hold_the_ledger_lock():
    import fcntl
    seen = []
    real = cp.lm.ledger_lock

    @contextlib.contextmanager
    def spy(path):
        with real(path):
            fd = os.open(str(path) + ".lock", os.O_RDWR)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    seen.append("free")
                except BlockingIOError:
                    seen.append("held")
            finally:
                os.close(fd)
            yield

    cp.lm.ledger_lock = spy
    try:
        run_main_with(OSError("x"), "--apply")
        d = tempfile.mkdtemp()
        path = os.path.join(d, "b.csv")
        cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING")], list(row("a", 1, "", "").keys()))
        saved = (sys.argv, cp.LEDGER)
        sys.argv, cp.LEDGER = ["check_payments.py", "--reminded", "2111"], path
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                cp.main()
        finally:
            sys.argv, cp.LEDGER = saved
    finally:
        cp.lm.ledger_lock = real
    assert seen == ["held", "held"], seen


# --- round 3: letter after the number ---------------------------------------------------------

SIBLINGS = [row("2111", 1150, "2026-09-10", "2026-11-21", "PENDING: invoiced", name="Ann Smith"),
            row("2111A", 1150, "2026-09-12", "2027-11-21", "PENDING: invoiced", name="Cy Brown"),
            row("2111B", 1150, "2026-09-14", "2028-11-21", "PENDING: invoiced", name="Di Green")]


def test_a_letter_mid_reference_never_picks_a_sibling():
    for ref in ("INV 2111 A SMITH", "2111 A SMITH", "INV2111 B SMITH", "INV2111BALANCE", "INV2111BAL", "INV2111ADEPOSIT"):
        found = cp.match(SIBLINGS, [pay(575, "2026-09-24", ref, "MR J DOE")], T)
        for k in ("2111A", "2111B"):
            assert all(how not in cp.CONFIDENT for _, _, how in found[k]), (ref, found)
        states = [cp.assess(r, found[r["booking_ref"]], T) for r in SIBLINGS]
        assert all(a["state"] == "CHECK_PAYMENT" and a["receipt_due"] is False for a in states), (ref, states)


def test_a_final_or_glued_single_letter_names_the_sibling():
    for ref in ("INV 2111 A", "INV2111A", "Ref: INV 2111 A.", "2111A"):
        found = cp.match(SIBLINGS, [pay(575, "2026-09-24", ref, "MR J DOE")], T)
        assert found["2111A"] == [("2026-09-24", 575.0, "reference")] and not found["2111"] and not found["2111B"], (ref, found)


def test_a_mid_reference_letter_with_the_clients_surname_picks_the_number():
    found = cp.match(SIBLINGS, [pay(575, "2026-09-24", "INV 2111 A SMITH", "ANN SMITH")], T)
    assert found["2111"] == [("2026-09-24", 575.0, "reference")] and not found["2111A"] and not found["2111B"], found


# --- round 3: when a payer's surname really contradicts the reference ------------------------

def _states(rows, items):
    f = cp.match(rows, items, T)
    return {r["booking_ref"]: cp.assess(r, f[r["booking_ref"]], T)["state"] for r in rows}


def test_a_parent_paying_under_another_surname_stays_confident():
    base = [row("2111", 1150, "2026-09-10", "2027-06-12", "PENDING: invoiced", name="Ann Smith")]
    jones = [pay(575, "2026-09-24", "INV 2111", "MR R JONES")]
    # another Jones booking whose fee the amount doesn't fit
    assert _states(base + [row("0512", 2400, "2026-09-12", "2026-12-05", "PENDING: invoiced", name="Kate Jones")], jones)["2111"] == "DEPOSIT_SEEN"
    # a closed (paid in full) Jones booking
    assert _states(base + [row("0512", 1150, "2026-08-12", "2026-12-05", "paid in full 2026-09-01", name="Kate Jones")], jones)["2111"] == "DEPOSIT_SEEN"
    # a cancelled Jones booking
    assert _states(base + [row("0512", 1150, "2026-09-12", "2026-12-05", "Cancelled 20 Sep", name="Kate Jones")], jones)["2111"] == "DEPOSIT_SEEN"
    # a Jones booking whose window the payment falls outside
    assert _states(base + [row("0512", 1150, "2026-10-12", "2026-12-05", "PENDING: invoiced", name="Kate Jones")], jones)["2111"] == "DEPOSIT_SEEN"


def test_generic_trailing_words_are_not_surnames():
    rows = [row("3001", 450, "2026-09-20", "2026-10-02", "PENDING: invoiced", name="Mary Brown"),
            row("3005", 450, "2026-09-21", "2026-10-06", "PENDING: invoiced", name="T Cribb & Sons")]
    assert _states(rows, [pay(450, "2026-09-24", "INV 3001", "J H KENYON & SONS")]) == {"3001": "PAID_IN_FULL", "3005": "AWAITING_DEPOSIT"}
    assert cp.surnames({"client_name": "T Cribb & Sons Ltd."}) == ["Cribb"]
    assert cp.surnames({"client_name": "Parish Church"}) == []
    assert cp.surnames({"client_name": "Mr and Mrs Lee"}) == ["Lee"]


def test_either_party_of_a_couple_can_pay():
    rows = [row("2111", 1150, "2026-09-10", "2027-06-12", "PENDING: invoiced", name="Ann Smith & Tom Jones"),
            row("0512", 1150, "2026-09-12", "2026-12-05", "PENDING: invoiced", name="Bo Smith")]
    assert _states(rows, [pay(575, "2026-09-24", "INV 2111", "A SMITH")])["2111"] == "DEPOSIT_SEEN"
    assert _states(rows, [pay(575, "2026-09-24", "INV 2111", "T JONES")])["2111"] == "DEPOSIT_SEEN"
    assert cp.surnames({"client_name": "Ann Smith & Tom Jones"}) == ["Smith", "Jones"]


def test_typo_guard_still_holds():
    rows = [row("2111", 1150, "2026-09-10", "2027-06-12", "PENDING: invoiced", name="Ann Smith"),
            row("0512", 1150, "2026-09-12", "2026-12-05", "PENDING: invoiced", name="Kate Jones")]
    assert _states(rows, [pay(575, "2026-09-24", "INV 2111", "K JONES")]) == {"2111": "CHECK_PAYMENT", "0512": "CHECK_PAYMENT"}


# --- round 3: paid notes ----------------------------------------------------------------------

def test_negated_or_future_paid_notes_are_still_chased():
    for n in ("deposit not yet seen in the bank", "nothing received yet", "no payment received", "deposit to be paid by 5 Oct",
              "deposit in by Friday please", "asked if paid", "never paid", "client says she paid, not seen yet",
              "client will have paid by Friday", "PENDING: invoiced, deposit not yet seen"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-12-12", "PENDING: invoiced; " + n), [], T)
        assert a["state"] == "DEPOSIT_OVERDUE", (n, a["state"])
    # a paid note after a negated phrase still counts
    for n in ("no reminder needed, paid 5 Sep", "deposit not yet seen, client paid 5 Sep", "not in the bank yet; paid by cash 5 Sep"):
        assert cp.assess(row("2111", 1150, "2026-09-01", "2026-12-12", "PENDING: invoiced; " + n), [], T)["state"] == "NOTED_PAID", n


def test_a_deposit_sized_paid_note_never_stops_a_balance_chase():
    paid = [("2026-09-05", 575.0, "reference")]
    for n in ("deposit of £575 paid 5 Sep", "£575 paid 5 Sep", "deposit (£575) paid by bank transfer", "deposit paid by card",
              "balance to be paid in cash on the day", "will pay balance in cash", "balance not paid in full"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling); " + n), paid, T)
        assert a["state"] == "BALANCE_DUE", (n, a["state"])
    for n in ("£1,150 paid 5 Sep", "balance of £575 paid in cash", "£575 paid 5 Sep; balance paid in cash 29 Sep",
              "deposit of £575 paid 5 Sep, balance paid in cash"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling); " + n), paid, T)
        assert a["state"] == "NOTED_PAID", (n, a["state"])


def test_an_unconfirmed_match_beats_a_stale_auto_note():
    r = row("2111", 1150, "2026-09-01", "2026-12-12", "deposit seen 2026-09-05 (Starling)")
    for how in ("reference naming several bookings", "amount only"):
        assert cp.assess(r, [("2026-09-05", 575.0, how)], T)["state"] == "CHECK_PAYMENT", how
    assert cp.assess(r, [], T)["state"] == "NOTED_PAID"


def test_noted_paid_says_how_to_silence_it():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep"), [], T)
    assert "paid in full YYYY-MM-DD" in cp.describe(a)
    assert cp.open_rows([row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep; paid in full 2026-09-14")]) == []


# --- round 3: minors --------------------------------------------------------------------------

def test_cancelling_wording():
    for note in ("client cancelling", "cancellation requested 20 Sep"):
        assert cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", note)), note
    for note in ("not cancelling", "thinking about cancelling", "considering cancelling"):
        assert not cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", note)), note


def test_bad_json_and_http_status_are_starling_unavailable():
    import urllib.error
    code, out, err, unchanged = run_main_with(json.JSONDecodeError("x", "<html>", 0), "--apply", "--json")
    assert code in (0, None) and out == "[]\n" and err == "Starling unavailable (JSONDecodeError)\n" and unchanged, (code, out, err)
    code, out, err, unchanged = run_main_with(urllib.error.HTTPError("u", 401, "x", {}, None), "--apply")
    assert code in (0, None) and out == "" and err == "Starling unavailable (HTTPError 401)\n" and unchanged, (code, out, err)


# --- round 3: every ledger writer takes the lock ----------------------------------------------

def _lock_spy(seen):
    import fcntl
    real = cp.lm.ledger_lock

    @contextlib.contextmanager
    def spy(path):
        with real(path):
            fd = os.open(str(path) + ".lock", os.O_RDWR)
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    seen.append("free")
                except BlockingIOError:
                    seen.append("held")
            finally:
                os.close(fd)
            yield
    return real, spy


def test_assistant_ledger_add_holds_the_lock():
    import assistant_io as aio
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    cols = ["booking_ref", "value_gbp", "invoice_date", "event_date", "notes", "client_name"]
    cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING")], cols)
    seen = []
    real, spy = _lock_spy(seen)
    saved = (aio.LEDGER, sys.argv, cp.lm.ledger_lock)
    aio.LEDGER, sys.argv, cp.lm.ledger_lock = cp.Path(path), ["assistant_io.py", "ledger-add", json.dumps({"booking_ref": "0512"})], spy
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            aio.main()
    finally:
        aio.LEDGER, sys.argv, cp.lm.ledger_lock = saved
    assert seen == ["held"], seen
    assert [r["booking_ref"] for r in cp.lm.read_csv(path)] == ["2111", "0512"]


def test_upload_bookings_stamps_the_ledger_under_the_lock():
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
        import upload_bookings as ub
    except ImportError:  # google-ads not installed: nothing to check here
        return
    assert ub.lm is cp.lm
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    rows = [dict(r, uploaded_at="") for r in (row("2111", 650, "2026-08-22", "2026-11-21"), row("0512", 650, "2026-09-01", "2026-12-05"))]
    cp.lm.write_csv(path, rows, list(rows[0].keys()))
    seen = []
    real, spy = _lock_spy(seen)
    saved = (ub.LEDGER, cp.lm.ledger_lock)
    ub.LEDGER, cp.lm.ledger_lock = cp.Path(path), spy
    try:
        ub.stamp_uploaded({"0512"}, "2026-09-28 10:00")
    finally:
        ub.LEDGER, cp.lm.ledger_lock = saved
    got = {r["booking_ref"]: r["uploaded_at"] for r in cp.lm.read_csv(path)}
    assert seen == ["held"] and got == {"2111": "", "0512": "2026-09-28 10:00"}, (seen, got)
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"


def test_upload_bookings_ledger_follows_the_private_dir():
    d = tempfile.mkdtemp()
    code = ("import sys; sys.path.insert(0, %r); import upload_bookings as ub; print(ub.LEDGER)"
            % os.path.join(ROOT, "scripts", "ads"))
    env = {k: v for k, v in os.environ.items() if k != "LCS_BOOKINGS_CSV"}
    env["LCS_PRIVATE_DIR"] = d
    p = subprocess.run([PY, "-c", code], env=env, capture_output=True, text=True)
    if "No module named 'google" in p.stderr:
        return
    assert p.stdout.strip() == os.path.join(d, "bookings.csv"), (p.stdout, p.stderr[-300:])


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
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
