#!/usr/bin/env python3
"""Tests for scripts/bookings/check_payments.py. Stdlib only."""
import contextlib, csv, datetime, io, json, os, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private, even for the in-process imports (review M15)
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(_HOME, "bookings.csv")

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


def test_just_received_lasts_fourteen_days_until_a_receipt_is_drafted():
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
    got = {r["booking_ref"]: (paid, a) for r, paid, a in cp.collect(client, rows, T)}
    assert sorted(got) == ["2401", "2410"]
    paid, a = got["2410"]
    assert paid == [] and a["state"] in ("DEPOSIT_OVERDUE", "AWAITING_DEPOSIT") and a["just_received"] is False
    # the payment after "paid in full" goes to the hand check on 2401, never to "received"
    assert got["2401"][1]["state"] == "PAYMENT_AFTER_CLOSE" and got["2401"][1]["just_received"] is False
    assert client.calls and all(c[2] == "IN" for c in client.calls)
    assert cp.received_since(client, rows, datetime.date(2026, 9, 21), T) == []


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
    assert p.returncode == 0 and notes == f"PENDING: invoiced; reminder drafted {cp.lm.today()}", notes


def test_cli_reminded_balance_kind():
    p, notes = run_cli("deposit seen 2026-08-26 (Starling)", "--reminded", "2111", "--kind", "balance")
    assert p.returncode == 0 and notes.endswith(f"; balance reminder drafted {cp.lm.today()}"), notes


def test_cli_reminded_unknown_ref_fails():
    p, notes = run_cli("PENDING: invoiced", "--reminded", "9999")
    assert p.returncode != 0 and notes == "PENDING: invoiced"


def test_cli_note_is_appended():
    p, notes = run_cli("PENDING: invoiced", "--note", "2111", "paid per client email 2026-09-28")
    assert p.returncode == 0 and notes == "PENDING: invoiced; paid per client email 2026-09-28", notes
    assert p.stdout.strip() == "2111: note added"


def test_cli_note_on_empty_notes_has_no_leading_separator():
    p, notes = run_cli("", "--note", "2111", "cancelled 2026-09-28")
    assert p.returncode == 0 and notes == "cancelled 2026-09-28", notes


def test_cli_note_unknown_ref_fails():
    p, notes = run_cli("PENDING: invoiced", "--note", "9999", "paid 5 Sep")
    assert p.returncode != 0 and notes == "PENDING: invoiced"


def test_cli_note_rejects_a_semicolon():
    p, notes = run_cli("PENDING: invoiced", "--note", "2111", "paid; per client email")
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
            if str(path).endswith("events.jsonl"):  # the state log's own lock, taken inside the ledger's
                yield
                return
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
        run_main_with(OSError("x"), "--apply")  # Starling down: --apply never took the lock (M9)
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
    assert seen == ["held"], seen


class LockCheckingClient(FakeClient):
    """A feed that records whether the ledger lock is free while Starling is being read."""

    def __init__(self, items, path):
        super().__init__(items)
        self.path, self.lock_free = path, []

    def feed(self, since, until, direction):
        import fcntl
        fd = os.open(str(self.path) + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lock_free.append(True)
            except BlockingIOError:
                self.lock_free.append(False)
        finally:
            os.close(fd)
        return super().feed(since, until, direction)


def test_apply_reads_starling_before_taking_the_lock_and_merges_a_concurrent_edit():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    cols = list(row("a", 1, "", "").keys())
    cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced"),
                           row("0512", 650, "2026-09-01", "2026-12-05", "PENDING: invoiced", name="Bo Jones")], cols)
    client = LockCheckingClient([pay(325, "2026-09-24", "INV 2111")], path)
    stale = cp.lm.read_csv(path)
    # another writer notes 0512 after this run read the ledger, before it writes
    cp.lm.write_csv(path, [stale[0], dict(stale[1], notes="PENDING: invoiced; reminder drafted 2026-09-28")], cols)
    args = type("A", (), {"apply": True, "json": True, "selftest": False})()
    saved = cp.LEDGER
    cp.LEDGER = path
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cp.run(args, client, stale, T)
    finally:
        cp.LEDGER = saved
    assert client.lock_free and all(client.lock_free), client.lock_free
    after = {r["booking_ref"]: r["notes"] for r in cp.lm.read_csv(path)}
    assert after["2111"] == "deposit seen 2026-09-24 (Starling); invoiced", after
    assert after["0512"] == "PENDING: invoiced; reminder drafted 2026-09-28", after  # the other writer's edit is kept


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
        assert all(a["state"] == "CHECK_PAYMENT" and a["just_received"] is False for a in states), (ref, states)


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
            row("3005", 450, "2026-09-21", "2026-10-06", "PENDING: invoiced", name="T Brackenwold & Sons")]
    assert _states(rows, [pay(450, "2026-09-24", "INV 3001", "J H KENYON & SONS")]) == {"3001": "PAID_IN_FULL", "3005": "AWAITING_DEPOSIT"}
    assert cp.surnames({"client_name": "T Brackenwold & Sons Ltd."}) == ["Brackenwold"]
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
    # ("balance to be paid in cash on the day" and "will pay balance in cash" are ARRANGED since round 5)
    for n in ("deposit of £575 paid 5 Sep", "£575 paid 5 Sep", "deposit (£575) paid by bank transfer", "deposit paid by card",
              "balance not paid in full"):
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
    cols = ["booking_ref", "value_gbp", "invoice_date", "event_date", "notes", "client_name", "occasion"]
    cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING")], cols)
    seen = []
    real, spy = _lock_spy(seen)
    saved = (aio.LEDGER, sys.argv, cp.lm.ledger_lock)
    aio.LEDGER, sys.argv, cp.lm.ledger_lock = cp.Path(path), ["assistant_io.py", "ledger-add", json.dumps({"booking_ref": "0512", "occasion": "wedding"})], spy
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


# --- round 4: an unconfirmed balance payment stops a balance chase -----------------------------

QUIET = {"unpaid": 0, "unpaid_total": 0.0, "oldest_days": 0, "bank_changed": 0}
R3009 = row("3009", 1150, "2026-08-01", "2026-09-30", "deposit seen 2026-08-05 (Starling)", name="Ian Lamb")


def test_an_unconfirmed_balance_payment_stops_a_balance_chase():
    import money_report as mr
    for who, ref in (("MRS P QUILLAN", "WEDDING BALANCE"), ("P QUILLAN", "")):
        feed = [pay(575, "2026-08-05", "LCS3009", "I LAMB"), pay(575, "2026-09-26", ref, who)]
        found = cp.match([R3009], feed, T)
        a = cp.assess(R3009, found["3009"], T)
        assert a["state"] == "CHECK_PAYMENT" and a["just_received"] is False and a["received"] == 575.0, a
        assert "possible balance payment £575.00 on 2026-09-26 (unconfirmed): confirm by hand" in cp.describe(a), cp.describe(a)
        lines = mr.summary_lines([a], [], QUIET, T)
        assert lines[2] == "balances due in the next 7 days: 0, £0.00" and lines[3].startswith("needs a hand check: 1 (3009 "), lines


def test_which_unconfirmed_payments_stop_a_balance_chase():
    dep = ("2026-08-05", 575.0, "reference")
    # dated on or after the first confident payment: any amount
    assert cp.assess(R3009, [dep, ("2026-09-20", 100.0, "amount only")], T)["state"] == "CHECK_PAYMENT"
    assert cp.assess(R3009, [dep, ("2026-08-05", 575.0, "amount only, several bookings")], T)["state"] == "CHECK_PAYMENT"
    # before the deposit but the size of the balance
    assert cp.assess(R3009, [dep, ("2026-08-01", 575.0, "amount only")], T)["state"] == "CHECK_PAYMENT"
    # before the deposit and another size: still chased
    assert cp.assess(R3009, [dep, ("2026-08-01", 100.0, "amount only")], T)["state"] == "BALANCE_DUE"
    # far from the event: not DEPOSIT_SEEN either
    far = row("3009", 1150, "2026-08-01", "2026-12-30", "deposit seen 2026-08-05 (Starling)", name="Ian Lamb")
    assert cp.assess(far, [dep, ("2026-09-26", 575.0, "amount only")], T)["state"] == "CHECK_PAYMENT"
    assert cp.assess(far, [dep], T)["state"] == "DEPOSIT_SEEN"


# --- round 4: the owner's notes win -----------------------------------------------------------

def test_a_paid_note_after_a_loose_negation_counts():
    for n in ("no chase needed - paid 5 Sep", "Nothing to chase: paid cash 5 Sep", "not a problem: paid 5 Sep",
              "No issues - paid by bank transfer", "not banked yet but received in cash", "no longer pending: paid",
              "said he would ring but paid 5 Sep", "asked about the invoice: paid 5 Sep"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", n), [], T)
        assert a["state"] == "NOTED_PAID", (n, a["state"])


def test_a_rest_of_fee_note_counts_as_full_even_with_an_amount():
    paid = [("2026-09-05", 575.0, "reference")]
    for n in ("no chase: balance paid in cash", "balance of £575 paid", "£1,150 paid in total", "£575 balance paid 20 Sep",
              "remaining £575 paid in cash", "balance: £575 paid by cheque 20 Sep", "deposit and balance paid in cash",
              "total of £1,150 received"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling); " + n), paid, T)
        assert a["state"] == "NOTED_PAID", (n, a["state"])
    for n in ("deposit paid in full", "deposit of £575 paid in full", "deposit received and balance invoiced",
              "paid deposit and balance invoiced 20 Sep", "balance due 30 Sep", "no balance paid yet", "balance not yet received"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling); " + n), paid, T)
        assert a["state"] == "BALANCE_DUE", (n, a["state"])


# --- round 4: payments on cancelled or closed bookings reach the hand check -------------------

E2E_ROWS = [row("0510", 1150, "2026-09-01", "2026-12-05", "Cancelled 20 Sep", name="Eve King"),
            row("1506", 1150, "2026-06-01", "2026-10-15", "deposit seen 2026-06-03 (Starling); paid in full 2026-09-15", name="Fay Hill"),
            row("0710", 1150, "2026-09-01", "2026-12-07", "CANCELLED 2026-09-10; no deposit", name="Gil Ray"),
            row("2111", 1150, "2026-09-10", "2027-06-12", "PENDING: invoiced", name="Ann Smith")]
E2E_FEED = [pay(575, "2026-09-27", "INV 0510", "E KING"), pay(575, "2026-09-26", "WEDDING", "FAY HILL"),
            pay(575, "2026-09-14", "INV 1506 balance", "FAY HILL"), pay(575, "2026-09-24", "INV 2111", "A SMITH")]


def test_payments_on_cancelled_or_closed_bookings_reach_the_hand_check():
    import money_report as mr
    client = FakeClient(E2E_FEED)
    got = {r["booking_ref"]: a for r, _, a in cp.collect(client, E2E_ROWS, T)}
    assert sorted(got) == ["0510", "1506", "2111"], sorted(got)  # 0710: cancelled, nothing paid: out of everything
    assert got["0510"]["state"] == "PAYMENT_ON_CANCELLED" and got["1506"]["state"] == "PAYMENT_AFTER_CLOSE"
    for ref in ("0510", "1506"):
        a = got[ref]
        assert a["just_received"] is False, a
        assert "check by hand" in cp.describe(a), cp.describe(a)
    assert "£575.00 on 2026-09-27" in cp.describe(got["0510"]) and "£575.00 on 2026-09-26" in cp.describe(got["1506"])
    assert "2026-09-14" not in cp.describe(got["1506"]).split(" · ", 1)[1]  # the balance that closed it is not the stray
    rec = cp.received_since(client, E2E_ROWS, T - datetime.timedelta(days=21), T)
    assert sorted(rec) == [("1506", "2026-09-14", 575.0), ("2111", "2026-09-24", 575.0)], rec
    lines = mr.summary_lines(list(got.values()), rec, QUIET, T)
    assert lines[3] == "needs a hand check: 2 (0510 payment on a cancelled booking; 1506 payment after paid in full)", lines
    assert "0510" not in lines[2] and "1506" not in lines[2]


def test_apply_never_rewrites_a_cancelled_or_closed_row():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    rows = [dict(r, notes="PENDING; " + r["notes"]) if r["booking_ref"] in ("0510", "1506") else dict(r) for r in E2E_ROWS]
    cols = list(rows[0].keys())
    cp.lm.write_csv(path, rows, cols)
    saved = cp.LEDGER
    cp.LEDGER = path
    args = type("A", (), {"apply": True, "json": True, "selftest": False})()
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            cp.run(args, FakeClient(E2E_FEED), cp.lm.read_csv(path), T)
    finally:
        cp.LEDGER = saved
    after = {r["booking_ref"]: r["notes"] for r in cp.lm.read_csv(path)}
    assert after["0510"] == rows[0]["notes"] and after["1506"] == rows[1]["notes"], after
    assert after["2111"].startswith("deposit seen 2026-09-24 (Starling)"), after
    states = {a["ref"]: a["state"] for a in json.loads(out.getvalue())}
    assert states["0510"] == "PAYMENT_ON_CANCELLED" and states["1506"] == "PAYMENT_AFTER_CLOSE", states


def test_a_cancelled_booking_payment_counts_only_inside_its_window():
    r = row("0510", 1150, "2026-09-01", "2026-12-05", "Cancelled 20 Sep", name="Eve King")
    assert cp.assess(r, [("2026-09-27", 575.0, "reference")], T)["state"] == "PAYMENT_ON_CANCELLED"
    assert cp.assess(r, [("2026-06-01", 575.0, "reference")], T)["state"] == "CANCELLED"
    assert cp.assess(r, [], T)["state"] == "CANCELLED"


def test_maybe_cancelling_is_still_tracked():
    for n in ("may be cancelling", "might be cancelling", "possibly cancelling", "could be cancelling", "thinking of cancelling",
              "client may be cancelling", "not cancelling"):
        assert not cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", n)), n
    for n in ("client cancelling", "cancelled", "Cancellation confirmed", "cancellation received 20 Sep", "CANCELLED 2026-09-10;"):
        assert cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", n)), n
    got = cp.collect(FakeClient([]), [row("X", 500, "2026-09-01", "2026-10-30", "PENDING; may be cancelling")], T)
    assert [a["state"] for _, _, a in got] == ["DEPOSIT_OVERDUE"]


# --- round 4: rewrites keep the ledger's own header -------------------------------------------

def _ragged_ledger(stray=True):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "bookings.csv")
    header = "booking_ref,value_gbp,invoice_date,event_date,notes,client_name,uploaded_at,extra_col"
    with open(path, "w", newline="") as f:
        f.write(header + "\n2111,650,2026-08-22,2026-11-21,PENDING,Ann Smith,,x" + (",stray" if stray else "") + "\n"
                "0512,650,2026-09-01,2026-12-05,PENDING,Bo Jones,,y\n")
    return path, header


def test_every_ledger_writer_refuses_a_row_wider_than_the_header():
    import assistant_io as aio
    path, _ = _ragged_ledger()
    before = open(path).read()
    attempts = [("check_payments", ["check_payments.py", "--reminded", "0512"], cp.main),
                ("check_payments", ["check_payments.py", "--note", "0512", "paid per client email 2026-09-28"], cp.main),
                ("assistant_io", ["assistant_io.py", "ledger-add", json.dumps({"booking_ref": "0612", "occasion": "wedding"})], aio.main)]
    for name, argv, fn in attempts:
        saved = (sys.argv, cp.LEDGER, aio.LEDGER)
        sys.argv, cp.LEDGER, aio.LEDGER = argv, path, cp.Path(path)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                fn()
            raise AssertionError(f"{name} {argv[1]} wrote a ragged ledger")
        except SystemExit as e:
            assert "more fields than its header" in str(e), (name, e)
        finally:
            sys.argv, cp.LEDGER, aio.LEDGER = saved
        assert open(path).read() == before, name


def test_reminded_keeps_the_ledger_header():
    path, header = _ragged_ledger(stray=False)
    saved = (sys.argv, cp.LEDGER)
    sys.argv, cp.LEDGER = ["check_payments.py", "--reminded", "0512"], path
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cp.main()
    finally:
        sys.argv, cp.LEDGER = saved
    lines = open(path).read().splitlines()
    assert lines[0] == header, lines[0]
    assert cp.lm.read_csv(path)[1]["notes"].startswith("PENDING; reminder drafted")


def test_stamp_uploaded_keeps_the_ledger_header():
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
        import upload_bookings as ub
    except ImportError:
        return
    path, header = _ragged_ledger(stray=False)
    saved = ub.LEDGER
    ub.LEDGER = cp.Path(path)
    try:
        ub.stamp_uploaded({"0512"}, "2026-09-28 10:00")
    finally:
        ub.LEDGER = saved
    got = open(path).read().splitlines()[0].split(",")
    want = header.split(",")
    assert got[:len(want)] == want and None not in got and "" not in got, got
    assert {r["booking_ref"]: r["uploaded_at"] for r in cp.lm.read_csv(path)} == {"2111": "", "0512": "2026-09-28 10:00"}


def test_assistant_paths_follow_the_private_dir():
    d = tempfile.mkdtemp()
    code = ("import sys; sys.path.insert(0, %r); import assistant_io as a; print(a.STATE); print(a.INVOICES); print(a.LEDGER)"
            % os.path.join(ROOT, "scripts", "bookings"))
    env = {k: v for k, v in os.environ.items() if k != "LCS_BOOKINGS_CSV"}
    env["LCS_PRIVATE_DIR"] = d
    p = subprocess.run([PY, "-c", code], env=env, capture_output=True, text=True)
    assert p.stdout.split() == [os.path.join(d, "assistant-state.json"), os.path.join(d, "invoices"),
                                os.path.join(d, "bookings.csv")], (p.stdout, p.stderr[-300:])


# --- round 5: resumed cancellations -------------------------------------------------------------

def test_a_resumed_or_conditional_cancellation_is_not_cancelled():
    for n in ("cancellation requested, then withdrawn", "rain date if cancelled",
              "Cancellation requested 20 Sep; going ahead after all", "cancelled 20 Sep, reinstated 25 Sep",
              "if it is cancelled the deposit is kept"):
        assert not cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", n)), n
    for n in ("cancelled 5 Oct", "cancelled then rebooked", "rebooked for 2027; cancelled 5 Oct", "cancelled, not going ahead", "client cancelled after all",
              "cancellation requested, may be withdrawn", "Cancelled; deposit withdrawn from escrow"):
        assert cp.is_cancelled(row("X", 500, "2026-09-01", "2026-10-30", n)), n


def test_a_resumed_booking_is_chased_again():
    r = row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced; cancellation requested, then withdrawn")
    assert cp.open_rows([r]) == [r] and cp.assess(r, [], T)["state"] == "DEPOSIT_OVERDUE"


# --- round 5: silencing a payment on a cancelled booking --------------------------------------

def test_a_kept_deposit_note_silences_earlier_payments_on_a_cancelled_booking():
    import money_report as mr
    paid = [("2026-08-05", 575.0, "reference")]
    for n in ("Cancelled 15 Sep; deposit kept 2026-09-15", "cancelled; refunded 2026-09-20", "Cancelled; payment checked 2026-09-28",
              "cancelled; Deposit Kept 2026-08-05"):
        r = row("4003", 1150, "2026-08-01", "2027-04-01", n, name="Gus Pardew")
        a = cp.assess(r, paid, T)
        assert a["state"] == "CANCELLED" and a["hand_check_payments"] == [], (n, a["state"])
        got = cp.collect(FakeClient([pay(575, "2026-08-05", "INV4003", "G PARDEW")]), [r], T)
        assert got == [], (n, got)
        assert mr.summary_lines([a for _, _, a in got], [], QUIET, T)[3] == "needs a hand check: 0"


def test_a_payment_after_the_kept_deposit_note_still_reaches_the_hand_check():
    r = row("4003", 1150, "2026-08-01", "2027-04-01", "Cancelled 15 Sep; deposit kept 2026-09-15", name="Gus Pardew")
    paid = [("2026-08-05", 575.0, "reference"), ("2026-09-20", 575.0, "reference")]
    a = cp.assess(r, paid, T)
    assert a["state"] == "PAYMENT_ON_CANCELLED" and a["hand_check_payments"] == [["2026-09-20", 575.0]], a
    assert "2026-08-05" not in cp.describe(a).split(" · ", 1)[1]
    got = cp.collect(FakeClient([pay(575, "2026-08-05", "INV4003", "G PARDEW"), pay(575, "2026-09-20", "INV4003", "G PARDEW")]), [r], T)
    assert [a["state"] for _, _, a in got] == ["PAYMENT_ON_CANCELLED"]
    # without a date the note silences nothing
    r2 = row("4003", 1150, "2026-08-01", "2027-04-01", "Cancelled 15 Sep, deposit kept", name="Gus Pardew")
    assert cp.assess(r2, paid[:1], T)["state"] == "PAYMENT_ON_CANCELLED"


# --- round 5: a balance arranged in cash or by cheque on the day -------------------------------

ARRANGED_NOTES = ("balance to be paid in cash", "will pay balance in cash", "balance payable in cash on the day",
                  "rest will be paid in cash", "cheque on the day", "balance to be paid in cash on the day",
                  "rest will be paid in cash on the day", "balance in cash on the day", "balance will be paid by cheque")


def test_an_arranged_cash_balance_is_never_chased_or_thanked():
    dep = [("2026-09-20", 575.0, "reference")]
    for n in ARRANGED_NOTES:
        for event in ("2026-09-30", "2026-12-12", "2026-09-20"):
            a = cp.assess(row("2111", 1150, "2026-09-01", event, "deposit seen 2026-09-20 (Starling); " + n), dep, T)
            assert a["state"] == "ARRANGED" and a["just_received"] is False, (n, event, a["state"])
    # with nothing in the bank and no note of a deposit, the deposit is still what is owed
    for n in ARRANGED_NOTES:
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-12-12", "PENDING: invoiced; " + n), [], T)
        assert a["state"] == "ARRANGED", (n, a["state"])
    # a note of the whole fee paid still wins, and a negated arrangement is chased as before
    a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30",
                      "deposit seen 2026-09-20 (Starling); balance to be paid in cash on the day; balance paid in cash 29 Sep"), dep, T)
    assert a["state"] == "NOTED_PAID", a["state"]
    for n in ("won't pay cash on the day", "not paying cheque on the day"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-20 (Starling); " + n), dep, T)
        assert a["state"] == "BALANCE_DUE", (n, a["state"])


def test_an_arranged_balance_reaches_the_hand_check_only_near_or_after_the_event():
    import money_report as mr
    dep = [("2026-09-20", 575.0, "reference")]
    note = "deposit seen 2026-09-20 (Starling); rest will be paid in cash on the day"
    near = cp.assess(row("0510", 1150, "2026-09-01", "2026-10-05", note), dep, T)
    past = cp.assess(row("2009", 1150, "2026-09-01", "2026-09-20", note), dep, T)
    far = cp.assess(row("1212", 1150, "2026-09-01", "2026-12-12", note), dep, T)
    assert [a["state"] for a in (near, past, far)] == ["ARRANGED"] * 3
    lines = mr.summary_lines([near, past, far], [], QUIET, T)
    assert lines[2] == "balances due in the next 7 days: 0, £0.00", lines[2]
    assert lines[3] == ("needs a hand check: 2 (0510 balance arranged (cash/cheque on the day); "
                        "2009 balance arranged (cash/cheque on the day))"), lines[3]
    assert "never chase" in cp.describe(near)
    # nothing in the bank and no deposit noted: on the hand check every week
    bare = cp.assess(row("1313", 1150, "2026-09-01", "2026-12-12", "PENDING: invoiced; cheque on the day"), [], T)
    assert mr.summary_lines([bare], [], QUIET, T)[3].startswith("needs a hand check: 1 (1313 balance arranged"), bare


# --- round 5: split or odd-amount payments from the client ------------------------------------

def test_split_payments_from_the_client_are_a_hand_check_not_an_overdue_deposit():
    r = row("4009", 1150, "2026-09-01", "2027-01-09", "PENDING: invoiced", name="Kit Farrow")
    found = cp.match([r], [pay(300, "2026-09-10", "", "K FARROW"), pay(275, "2026-09-11", "", "K FARROW")], T)
    assert found["4009"] == [("2026-09-10", 300.0, "name only, amount differs"),
                             ("2026-09-11", 275.0, "name only, amount differs")], found
    a = cp.assess(r, found["4009"], T)
    assert a["state"] == "CHECK_PAYMENT" and a["received"] == 0 and a["just_received"] is False, a
    assert "matched by name only, amount differs: confirm by hand" in cp.describe(a)
    # a name that fits no open booking, or falls outside the window, is still nobody's
    assert cp.match([r], [pay(300, "2026-09-10", "", "J BLOGGS")], T)["4009"] == []
    assert cp.match([r], [pay(300, "2026-03-10", "", "K FARROW")], T)["4009"] == []
    # a whole-word surname only
    assert cp.match([r], [pay(300, "2026-09-10", "", "K FARROWE")], T)["4009"] == []
    # never on a closed booking; on a cancelled one it is the cancelled client's payment, a hand check
    assert cp.match([dict(r, notes="paid in full 2026-09-05")], [pay(300, "2026-09-10", "", "K FARROW")], T)["4009"] == []
    gone = dict(r, notes="cancelled 5 Sep")
    found = cp.match([gone], [pay(300, "2026-09-10", "", "K FARROW")], T)
    assert found["4009"] == [("2026-09-10", 300.0, "name, cancelled booking")], found
    assert cp.assess(gone, found["4009"], T)["state"] == "PAYMENT_ON_CANCELLED"


def test_an_odd_amount_after_the_deposit_is_a_possible_balance():
    r = row("4009", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling)", name="Kit Farrow")
    found = cp.match([r], [pay(575, "2026-09-05", "INV4009", "K FARROW"), pay(500, "2026-09-26", "", "K FARROW")], T)
    a = cp.assess(r, found["4009"], T)
    assert a["state"] == "CHECK_PAYMENT" and a["possible_balance"] == [["2026-09-26", 500.0]], a


# --- round 5: tidy notes ----------------------------------------------------------------------

def test_updated_notes_drop_a_leftover_deposit_not_yet_seen():
    paid = [("2026-09-22", 575.0, "reference")]
    for before, after in (
            ("PENDING: invoiced by enquiry assistant, deposit not yet seen",
             "deposit seen 2026-09-22 (Starling); invoiced by enquiry assistant"),
            ("PENDING; deposit not yet seen; from quote", "deposit seen 2026-09-22 (Starling); from quote"),
            ("PENDING: deposit not yet seen in the bank", "deposit seen 2026-09-22 (Starling)")):
        r = row("4001", 1150, "2026-09-10", "2027-05-01", before)
        a = cp.assess(r, paid, T)
        assert cp.updated_notes(r["notes"], a, paid) == after, (before, cp.updated_notes(r["notes"], a, paid))


# --- round 6: only an explicit reversal undoes a cancellation ---------------------------------

STAYS_CANCELLED = (
    "Cancelled 1 Sep; rebooked with another choir", "cancelled - went with another choir after all",
    "cancelled; wedding going ahead without music", "cancelled, going ahead at another venue with their organist",
    "cancelled; they rebooked elsewhere", "cancelled; complaint withdrawn", "cancelled; offer withdrawn",
    "cancellation requested; client says funeral going ahead elsewhere", "cancelled 2026-09-01; church booking withdrawn",
    "cancelled; reinstated with a different choir", "cancelled; going ahead after all with another choir",
    "cancelled; will get back on Monday about the refund")
RESUMED_NOTES = ("cancellation requested, then withdrawn", "cancelled 2 Sep; reinstated 5 Sep", "cancelled but back on",
                 "going ahead after all", "cancelled 20 Sep; cancellation withdrawn 22 Sep",
                 "cancellation request withdrawn", "Cancelled 1 Sep; going ahead after all")


def test_only_an_explicit_reversal_undoes_a_cancellation():
    import money_report as mr
    dep = [("2026-07-04", 575.0, "reference")]
    for n in STAYS_CANCELLED:
        r = row("4009", 1150, "2026-07-01", "2026-10-01", "deposit seen 2026-07-04 (Starling); " + n, name="Kit Farrow")
        assert cp.is_cancelled(r), n
        a = cp.assess(r, dep, T)  # a live row would be BALANCE_DUE: a chase
        assert a["state"] == "PAYMENT_ON_CANCELLED" and a["just_received"] is False and mr.needs_hand_check(a, T), (n, a["state"])
    for n in RESUMED_NOTES:
        r = row("4009", 1150, "2026-07-01", "2026-10-01", "deposit seen 2026-07-04 (Starling); " + n, name="Kit Farrow")
        assert not cp.is_cancelled(r), n
        assert cp.assess(r, dep, T)["state"] == "BALANCE_DUE", n


def test_collect_never_chases_a_booking_cancelled_for_another_choir():
    rows = [row("0110", 1150, "2026-07-01", "2026-10-01",
                "deposit seen 2026-07-04 (Starling); cancelled 2026-09-01, deposit kept; wedding going ahead without music"),
            row("0112", 1150, "2026-09-01", "2027-01-12",
                "PENDING: invoiced by enquiry assistant, deposit not yet seen; cancelled 2026-09-10, rebooked with another choir",
                name="Bob Jones")]
    got = {r["booking_ref"]: a for r, _, a in cp.collect(FakeClient([pay(575, "2026-07-04", "0110", "A SMITH")]), rows, T)}
    assert set(got) == {"0110"} and got["0110"]["state"] == "PAYMENT_ON_CANCELLED", {k: a["state"] for k, a in got.items()}
    assert not any(a["state"] in ("DEPOSIT_OVERDUE", "BALANCE_DUE") or a["just_received"] for a in got.values())


# --- round 6: paid or negated cash notes are not an arranged balance -------------------------

def test_a_paid_cash_note_is_noted_paid_not_arranged():
    dep = [("2026-07-04", 575.0, "reference")]
    for n in ("balance paid in cash on the day", "paid in full in cash on the day", "balance received in cash on the day",
              "balance paid by cheque on the day 2026-10-01"):
        assert cp.arranged_notes(n)[0] is False, n
        for event in ("2026-10-01", "2026-09-20"):
            a = cp.assess(row("4009", 1150, "2026-07-01", event, "deposit seen 2026-07-04 (Starling); " + n), dep, T)
            assert a["state"] == "NOTED_PAID", (n, event, a["state"])
    for n in ("balance to be paid in cash on the day", "deposit paid and balance to be paid in cash on the day",
              "rest will be paid by cheque"):
        a = cp.assess(row("4009", 1150, "2026-07-01", "2026-10-01", "deposit seen 2026-07-04 (Starling); " + n), dep, T)
        assert a["state"] == "ARRANGED", (n, a["state"])


def test_a_negated_or_refused_cash_note_is_chased_normally():
    dep = [("2026-07-04", 575.0, "reference")]
    for n in ("asked about paying cash on the day; told bank transfer only", "balance due by transfer not cash",
              "refused to pay cash", "was going to pay cash but will transfer", "balance payable by BACS only no cash",
              "balance due; cash on the day not accepted", "never pays cash", "nothing in cash on the day",
              "won't pay by cheque on the day", "will pay by cheque instead"):
        assert cp.arranged_notes(n)[0] is False, n
        a = cp.assess(row("4009", 1150, "2026-07-01", "2026-10-01", "deposit seen 2026-07-04 (Starling); " + n), dep, T)
        assert a["state"] == "BALANCE_DUE", (n, a["state"])
    for n in ("asked about paying cash on the day, said no", "deposit due by transfer not cash"):
        a = cp.assess(row("4010", 1150, "2026-09-01", "2027-01-09", "PENDING: deposit not yet seen; " + n), [], T)
        assert a["state"] == "DEPOSIT_OVERDUE", (n, a["state"])


# --- round 6: a cancelled client's unreferenced payment stays with the cancelled booking -----

def test_a_cancelled_clients_unreferenced_payment_is_never_linked_to_a_live_booking():
    import money_report as mr
    rows = [row("6001", 1150, "2026-09-05", "2027-03-01", "Cancellation requested 20 Sep", name="Gwen Hall"),
            row("6002", 1150, "2026-09-10", "2027-02-01", "PENDING: invoiced", name="Pat Lee")]
    feed = [pay(575, "2026-09-26", "", "G HALL")]
    found = cp.match(rows, feed, T)
    assert found == {"6001": [("2026-09-26", 575.0, "name, cancelled booking")], "6002": []}, found
    got = {r["booking_ref"]: a for r, _, a in cp.collect(FakeClient(feed), rows, T)}
    assert got["6001"]["state"] == "PAYMENT_ON_CANCELLED" and mr.needs_hand_check(got["6001"], T), got["6001"]
    assert got["6002"]["state"] == "DEPOSIT_OVERDUE" and got["6002"]["unconfirmed"] == [], got["6002"]
    # the same client with a live booking too (a fee the payment doesn't fit): the live one is never chased
    # as if nothing came in
    rows.append(row("6003", 900, "2026-09-12", "2027-04-01", "PENDING: invoiced", name="Gwen Hall"))
    found = cp.match(rows, feed, T)
    assert [k for k, v in found.items() if v] == ["6001", "6003"], found
    a = cp.assess(rows[2], found["6003"], T)
    assert a["state"] == "CHECK_PAYMENT" and a["just_received"] is False, a


# --- round 6: silencing notes -----------------------------------------------------------------

def test_only_a_payment_check_note_silences_and_never_a_future_one():
    paid = [("2026-08-05", 575.0, "reference")]
    for n, state in (("Cancelled 15 Sep; venue availability checked 2026-09-20", "PAYMENT_ON_CANCELLED"),
                     ("Cancelled 15 Sep; payment checked 2026-09-20", "CANCELLED"),
                     ("Cancelled 15 Sep; refund checked 2026-09-20", "CANCELLED"),
                     ("Cancelled 15 Sep; deposit checked 2026-09-20", "CANCELLED"),
                     ("Cancelled 15 Sep; refund not checked 2026-09-20", "PAYMENT_ON_CANCELLED"),
                     ("Cancelled 15 Sep; deposit kept 2026-12-20", "PAYMENT_ON_CANCELLED"),
                     ("Cancelled 15 Sep; payment checked 2026-09-29", "PAYMENT_ON_CANCELLED"),
                     ("Cancelled 15 Sep; refunded 2026-09-28", "CANCELLED")):
        a = cp.assess(row("4003", 1150, "2026-08-01", "2027-04-01", n, name="Gus Pardew"), paid, T)
        assert a["state"] == state, (n, a["state"])


# --- action: what the assistant does with each booking ---------------------------------------------

def test_action_receipt_for_a_fresh_confident_payment():
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), [("2026-09-27", 325.0, "reference")], T)
    assert (a["state"], a["just_received"], a["action"]) == ("DEPOSIT_SEEN", True, "receipt"), a
    done = cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "receipt drafted 2026-09-27"),
                     [("2026-09-27", 325.0, "reference")], T)
    assert done["action"] == "none", done


def test_action_deposit_reminder_only_once():
    a = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: invoiced"), [], T)
    assert (a["state"], a["action"]) == ("DEPOSIT_OVERDUE", "deposit_reminder"), a
    b = cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "PENDING: x; reminder drafted 2026-09-20"), [], T)
    assert b["action"] == "none", b


def test_action_balance_reminder_only_once():
    paid = [("2026-08-26", 325.0, "reference")]
    a = cp.assess(row("X", 650, "2026-08-22", "2026-10-01", "deposit seen x"), paid, T)
    assert (a["state"], a["action"]) == ("BALANCE_DUE", "balance_reminder"), a
    b = cp.assess(row("X", 650, "2026-08-22", "2026-10-01", "deposit seen x; balance reminder drafted 2026-09-28"), paid, T)
    assert b["action"] == "none", b


def test_action_hand_check_states():
    assert cp.assess(row("2509", 3225, "2026-09-12", "2026-09-21"), [], T)["action"] == "hand_check"  # PAST_UNMATCHED
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep"), [], T)["action"] == "hand_check"  # NOTED_PAID
    assert cp.assess(row("X", 0, "2026-09-01", "2026-10-30"), [], T)["action"] == "hand_check"  # CHECK_VALUE
    maybe = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), [("2026-09-27", 650.0, "amount only")], T)
    assert (maybe["state"], maybe["action"]) == ("CHECK_PAYMENT", "hand_check"), maybe
    for state in cp.HAND_CHECK_STATES:
        assert cp.action_for({"state": state, "just_received": False, "reminded": {}, "event_date": None}, T) == "hand_check"


def test_action_arranged_is_a_hand_check_only_within_a_week():
    near = {"state": "ARRANGED", "just_received": False, "reminded": {}, "event_date": "2026-10-05"}
    far = dict(near, event_date="2026-10-06")
    assert cp.action_for(near, T) == "hand_check" and cp.action_for(far, T) == "none"


def test_action_none_for_quiet_states():
    for state in ("AWAITING_DEPOSIT", "DEPOSIT_SEEN", "PAID_IN_FULL", "CANCELLED"):
        assert cp.action_for({"state": state, "just_received": False, "reminded": {"deposit": False, "balance": False},
                              "event_date": "2026-11-21"}, T) == "none", state


def test_every_assessment_carries_an_action():
    a = cp.assess(row("X", 500, "2026-09-25", "2026-10-30", "PENDING: invoiced"), [], T)
    assert a["action"] in cp.ACTIONS and a["action"] == "none"


# --- review I5: --note never writes the phrases the scripts or the owner rely on -------------

def test_note_refuses_the_reserved_phrases():
    for text in ("paid in full 2026-09-28", "deposit seen 2026-09-28 (Starling)", "reminder drafted 2026-09-28",
                 "balance reminder drafted", "receipt drafted 2026-09-28", "deposit kept 2026-09-28",
                 "refunded 2026-09-28", "payment checked 2026-09-28", "reinstated 2026-09-28",
                 "cancellation withdrawn", "going ahead after all", "back on", "review request drafted 2026-09-28",
                 "review request skipped 2026-09-28 (planner)", "PENDING: invoiced", "pending deposit",
                 "short by fees £12.40 accepted 2026-09-28", "Short by fees £5 accepted 2026-09-28 by phone"):
        p, notes = run_cli("deposit seen 2026-08-26 (Starling)", "--note", "2111", text)
        assert p.returncode != 0 and notes == "deposit seen 2026-08-26 (Starling)", (text, p.returncode, notes)
        assert "by hand" in p.stderr, (text, p.stderr)


def test_note_still_takes_the_prompts_phrases():
    for text in ("cancelled 2026-09-28 by client email", "paid per client email 2026-09-28"):
        p, notes = run_cli("PENDING: invoiced", "--note", "2111", text)
        assert p.returncode == 0 and notes == "PENDING: invoiced; " + text, (text, p.stderr, notes)


# ---------------------------------------------------------------- --owner (the Command Centre's hand-check resolutions)
# check_payments.py --note REF TEXT --owner writes an owner-only phrase only with the app's one-time nonce: sha256(nonce)
# in <private>/command-centre/owner-nonce (a regular file, this user's, mode 600, under 60 seconds old) and the nonce
# itself on stdin, which must be a pipe. See docs/superpowers/plans/2026-09-28-command-centre.md, Task 3.1.

import hashlib, time  # noqa: E402

NONCE = "ab" * 32


def owner_ledger(notes="PENDING: invoiced"):
    d = tempfile.mkdtemp()
    seed_migration(d)  # the writers record facts once the migration is applied (the owner facts' tests read them)
    path = os.path.join(d, "bookings.csv")
    cols = ["booking_ref", "value_gbp", "invoice_date", "event_date", "notes", "client_name"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row("2111", 650, "2026-08-22", "2026-11-21", notes))
    return d, path


def nonce_file(d, content=None, mode=0o600, age=0):
    cc = os.path.join(d, "command-centre")
    os.makedirs(cc, mode=0o700, exist_ok=True)
    path = os.path.join(cc, "owner-nonce")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(hashlib.sha256(NONCE.encode()).hexdigest() if content is None else content)
    os.chmod(path, mode)
    if age:
        t = time.time() - age
        os.utime(path, (t, t))
    return path


def run_owner(d, path, args, stdin_text=None, stdin=None, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "LCS_BOOKINGS_CSV"}  # the ledger is <d>/bookings.csv
    env["LCS_PRIVATE_DIR"] = d
    env.update(env_extra or {})
    kw = {"input": stdin_text} if stdin_text is not None else {"stdin": stdin if stdin is not None else subprocess.DEVNULL}
    p = subprocess.run([PY, SCRIPT, *args], env=env, capture_output=True, text=True, timeout=30, **kw)
    with open(path, newline="") as f:
        return p, list(csv.DictReader(f))[0]["notes"]


OWNER_ARGS = ["--note", "2111", "paid in full 2026-09-28", "--owner"]


def test_owner_note_with_the_nonce_over_a_pipe_is_written_once():
    d, path = owner_ledger()
    nf = nonce_file(d)
    p, notes = run_owner(d, path, OWNER_ARGS, stdin_text=NONCE + "\n")
    assert p.returncode == 0, p.stderr
    assert notes == "PENDING: invoiced; paid in full 2026-09-28 (owner)", notes
    assert not os.path.exists(nf), "the nonce file is single use"
    assert cp.closed_on({"notes": notes}) == datetime.date(2026, 9, 28)
    p, notes2 = run_owner(d, path, OWNER_ARGS, stdin_text=NONCE + "\n")  # replay: the file is gone
    assert p.returncode != 0 and notes2 == notes


def test_owner_note_is_refused_without_the_nonce():
    """Every way an allowlisted command could try it: no file, no pipe, the wrong nonce, the file's own contents."""
    cases = []
    d, path = owner_ledger()
    cases.append(("no nonce file", d, path, {"stdin_text": NONCE + "\n"}))
    d, path = owner_ledger()
    nonce_file(d)
    cases.append(("stdin /dev/null", d, path, {}))
    d, path = owner_ledger()
    nonce_file(d)
    cases.append(("wrong nonce", d, path, {"stdin_text": "cd" * 32 + "\n"}))
    d, path = owner_ledger()
    nonce_file(d)
    cases.append(("empty pipe", d, path, {"stdin_text": ""}))
    d, path = owner_ledger()
    nonce_file(d)
    cases.append(("the hash itself over the pipe", d, path,
                  {"stdin_text": hashlib.sha256(NONCE.encode()).hexdigest() + "\n"}))
    d, path = owner_ledger()
    nonce_file(d, age=120)
    cases.append(("stale file", d, path, {"stdin_text": NONCE + "\n"}))
    d, path = owner_ledger()
    nonce_file(d, mode=0o644)
    cases.append(("group-readable file", d, path, {"stdin_text": NONCE + "\n"}))
    for label, d, path, kw in cases:
        p, notes = run_owner(d, path, OWNER_ARGS, **kw)
        assert p.returncode != 0, label
        assert notes == "PENDING: invoiced", (label, notes)
        assert "nothing written" in (p.stderr + p.stdout), (label, p.stderr)


def test_owner_note_refuses_a_redirected_file_even_the_nonce_file():
    d, path = owner_ledger()
    nf = nonce_file(d)
    other = os.path.join(d, "nonce.txt")  # a regular file holding the real nonce is still not a pipe
    with open(other, "w") as f:
        f.write(NONCE + "\n")
    for src in (nf, other):
        with open(src) as f:
            p, notes = run_owner(d, path, OWNER_ARGS, stdin=f)
        assert p.returncode != 0 and notes == "PENDING: invoiced", (src, p.stderr)


def test_owner_note_refuses_a_symlinked_nonce_file():
    d, path = owner_ledger()
    real = nonce_file(tempfile.mkdtemp())
    cc = os.path.join(d, "command-centre")
    os.makedirs(cc, mode=0o700, exist_ok=True)
    os.symlink(real, os.path.join(cc, "owner-nonce"))
    p, notes = run_owner(d, path, OWNER_ARGS, stdin_text=NONCE + "\n")
    assert p.returncode != 0 and notes == "PENDING: invoiced", p.stderr
    assert os.path.exists(real)


def test_the_allowlisted_forms_with_owner_are_refused_without_the_nonce():
    """`--note *` and `--reminded *` on the allowlist also match these; the script refuses them."""
    for args in (["--note", "2111", "refunded 2026-09-28", "--owner"],
                 ["--reminded", "2111", "--note", "2111", "deposit kept 2026-09-28", "--owner"],
                 ["--owner", "--note", "2111", "reinstated 2026-09-28"]):
        d, path = owner_ledger()
        p, notes = run_owner(d, path, args)
        assert p.returncode != 0 and notes == "PENDING: invoiced", (args, p.stderr)


def test_owner_needs_note():
    d, path = owner_ledger()
    nonce_file(d)
    p, notes = run_owner(d, path, ["--owner"], stdin_text=NONCE + "\n")
    assert p.returncode != 0 and notes == "PENDING: invoiced"


def test_without_owner_the_owner_phrases_are_still_refused():
    for text in ("paid in full 2026-09-28", "deposit kept 2026-09-28", "refunded 2026-09-28", "reinstated 2026-09-28",
                 "payment checked 2026-09-28"):
        d, path = owner_ledger()
        nonce_file(d)  # even with a valid nonce waiting, no --owner means the normal rules
        p, notes = run_owner(d, path, ["--note", "2111", text], stdin_text=NONCE + "\n")
        assert p.returncode != 0 and notes == "PENDING: invoiced", text


def test_owner_note_refuses_a_ledger_outside_the_nonce_folder():
    """The nonce proves the app asked; the ledger must be the one beside it. LCS_BOOKINGS_CSV is refused outright,
    even pointing at the same file, and the nonce is left unburnt."""
    d, path = owner_ledger()
    nf = nonce_file(d)
    p, notes = run_owner(d, path, OWNER_ARGS, stdin_text=NONCE + "\n", env_extra={"LCS_BOOKINGS_CSV": path})
    assert p.returncode != 0 and "LCS_BOOKINGS_CSV" in p.stderr and notes == "PENDING: invoiced", p.stderr
    assert os.path.exists(nf)
    other, other_path = owner_ledger()
    p, _ = run_owner(d, path, OWNER_ARGS, stdin_text=NONCE + "\n", env_extra={"LCS_BOOKINGS_CSV": other_path})
    with open(other_path, newline="") as f:
        assert p.returncode != 0 and list(csv.DictReader(f))[0]["notes"] == "PENDING: invoiced"
    # in-process: a ledger in another folder than the nonce's private dir
    saved = cp.LEDGER
    try:
        cp.LEDGER = other_path
        assert "same private folder" in cp.owner_ledger_problem({})
        cp.LEDGER = os.path.join(os.environ["LCS_PRIVATE_DIR"], "bookings.csv")
        assert cp.owner_ledger_problem({}) is None
        assert "LCS_BOOKINGS_CSV" in cp.owner_ledger_problem({"LCS_BOOKINGS_CSV": "x"})
    finally:
        cp.LEDGER = saved


def test_owner_note_keeps_the_single_line_rules():
    for text in ("paid; in full", "x" * 121, "paid\nin full", "PENDING again"):
        d, path = owner_ledger()
        nonce_file(d)
        p, notes = run_owner(d, path, ["--note", "2111", text, "--owner"], stdin_text=NONCE + "\n")
        assert p.returncode != 0 and notes == "PENDING: invoiced", text


# --- round 7: a future-tense payment note is arranged, never paid (R16) -----------------------

def test_a_future_tense_rest_note_is_arranged_not_paid():
    dep = [("2026-09-20", 575.0, "reference")]
    for n in ("rest will be paid by the father", "balance will be paid by her parents",
              "remainder to be paid by the church", "will pay the balance next week",
              "is paying the rest", "are paying the remainder", "going to pay the balance"):
        for event in ("2026-09-30", "2026-12-12", "2026-09-20"):
            a = cp.assess(row("2111", 1150, "2026-09-01", event, "deposit seen 2026-09-20 (Starling); " + n), dep, T)
            assert a["state"] == "ARRANGED" and a["just_received"] is False, (n, event, a["state"])
        # with nothing in the bank and no note of a deposit, the deposit is still what is owed
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-12-12", "PENDING: invoiced; " + n), [], T)
        assert a["state"] == "ARRANGED", (n, a["state"])


def test_a_future_tense_note_with_no_rest_word_is_chased_normally():
    # future tense but no mention of the balance/rest/remainder: neither ARRANGED nor NOTED_PAID
    for n in ("will be paid by Friday", "to be paid next week", "client will pay soon",
              "is paying next week", "going to pay on the day", "deposit to be paid by 5 Oct"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-12-12", "PENDING: invoiced; " + n), [], T)
        assert a["state"] == "DEPOSIT_OVERDUE", (n, a["state"])


def test_a_past_tense_rest_note_still_counts_as_paid():
    dep = [("2026-09-05", 575.0, "reference")]
    for n in ("rest paid by the father 5 Sep", "balance paid by parents"):
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling); " + n), dep, T)
        assert a["state"] == "NOTED_PAID", (n, a["state"])
    # the existing ARRANGED (cash/cheque) and NOTED_PAID cases must still hold
    for n in ARRANGED_NOTES:
        a = cp.assess(row("2111", 1150, "2026-09-01", "2026-09-30", "deposit seen 2026-09-05 (Starling); " + n), dep, T)
        assert a["state"] == "ARRANGED", (n, a["state"])
    assert cp.assess(row("X", 500, "2026-09-01", "2026-10-30", "paid 14 Sep"), [], T)["state"] == "NOTED_PAID"



def test_record_in_books_lists_only_confident_payments_in_settled_states():
    sure = [("2026-09-27", 325.0, "reference")]
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), sure + [("2026-09-28", 100.0, "amount only")], T)
    assert a["state"] == "CHECK_PAYMENT" and a["record_in_books"] == [], a  # an unconfirmed payment: owner checks
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), sure, T)
    assert a["state"] == "DEPOSIT_SEEN" and a["record_in_books"] == [["2026-09-27", 325.0, 0.0]], a
    both = [("2026-09-28", 325.0, "name and amount"), ("2026-09-21", 325.0, "reference")]
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), both, T)
    assert a["state"] == "PAID_IN_FULL" and a["record_in_books"] == [["2026-09-21", 325.0, 0.0], ["2026-09-28", 325.0, 0.0]]
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), both + [("2026-09-28", 50.0, "reference")], T)
    assert a["record_in_books"] == [], a  # more than the booking's value: owner checks
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "cancelled 27 Sep"), sure, T)
    assert a["record_in_books"] == [], a
    a = cp.assess(row("X", 650, "2026-09-20", "2026-11-21"), [("2026-09-27", 325.0, "amount only")], T)
    assert a["record_in_books"] == [], a


# ---------------------------------------------------------------- a shortfall accepted as transfer fees (owner, 28 Sep 2026)

FEE_ROW = ("2408", 950, "2026-08-24", "2026-10-10")
FEE_PAID = [("2026-08-26", 475.0, "reference"), ("2026-09-25", 462.6, "reference")]  # £937.60: £12.40 short


def fee_row(notes):
    return row(*FEE_ROW, notes)


def test_fee_short_booking_without_a_note_is_chased_as_now():
    a = cp.assess(fee_row("deposit seen 2026-08-26 (Starling)"), FEE_PAID, datetime.date(2026, 10, 8))
    assert a["state"] == "BALANCE_DUE" and a["balance"] == 12.4 and a["fees"] == 0.0, a
    assert a["action"] == "balance_reminder"


def test_accepted_fee_reads_paid_in_full():
    a = cp.assess(fee_row("deposit seen 2026-08-26 (Starling); short by fees £12.40 accepted 2026-09-27 (owner)"),
                  FEE_PAID, datetime.date(2026, 10, 8))
    assert a["state"] == "PAID_IN_FULL" and a["balance"] == 0 and a["fees"] == 12.4, a
    assert a["action"] != "balance_reminder" and a["fees_on"] == "2026-09-27"
    assert a["record_in_books"] == [["2026-08-26", 475.0, 0.0], ["2026-09-25", 462.6, 12.4]], a
    json.dumps(a)  # the --json output
    assert "PAID IN FULL (£12.40 short by fees, accepted)" in cp.describe(a), cp.describe(a)


def test_fee_note_above_the_cap_or_in_the_future_is_ignored():
    for n in ("short by fees £40.01 accepted 2026-09-27", "short by fees £45 accepted 2026-09-27",
              "short by fees £12.40 accepted 2026-09-29", "short by fees £0 accepted 2026-09-27"):
        r = fee_row("deposit seen 2026-08-26 (Starling); " + n + " (owner)")
        a = cp.assess(r, FEE_PAID, T)
        assert a["state"] == "DEPOSIT_SEEN" and a["fees"] == 0.0 and a["balance"] == 12.4, (n, a)
        assert cp.fees_accepted(r, T) == 0.0 and cp.closed_on(r, T) is None and cp.open_rows([r], T) == [r], n
    r = fee_row("short by fees £40 accepted 2026-09-27 (owner)")  # at the cap
    assert cp.fees_accepted(r, T) == 40.0 and cp.closed_on(r, T) == datetime.date(2026, 9, 27)


def test_the_latest_counting_fee_note_wins():
    r = fee_row("short by fees £5 accepted 2026-09-20 (owner); short by fees £12.40 accepted 2026-09-27 (owner); "
                "short by fees £45 accepted 2026-09-28")
    assert cp.fees_accepted(r, T) == 12.4
    assert cp.assess(r, FEE_PAID, T)["state"] == "PAID_IN_FULL"
    r = fee_row("short by fees £5 accepted 2026-09-27 (owner)")  # not enough to close the gap
    a = cp.assess(r, FEE_PAID, datetime.date(2026, 10, 8))
    assert a["state"] == "BALANCE_DUE" and a["fees"] == 0.0 and a["record_in_books"][-1][2] == 0.0, a


def test_fee_note_never_pays_a_booking_with_nothing_confident():
    r = row("X", 20, "2026-09-01", "2026-10-30", "short by fees £20 accepted 2026-09-27 (owner)")
    assert cp.assess(r, [], T)["state"] != "PAID_IN_FULL"
    assert cp.assess(r, [("2026-09-02", 20.0, "amount only")], T)["state"] != "PAID_IN_FULL"


def test_more_fee_than_needed_only_uses_the_gap():
    paid = FEE_PAID + [("2026-09-26", 10.0, "reference")]  # the client later sent £10 of the £12.40
    a = cp.assess(fee_row("short by fees £12.40 accepted 2026-09-27 (owner)"), paid, T)
    assert a["state"] == "PAID_IN_FULL" and a["fees"] == 2.4 and a["record_in_books"][-1] == ["2026-09-26", 10.0, 2.4], a


def test_fee_close_is_reported_once_then_closed_like_paid_in_full():
    notes = "deposit seen 2026-08-26 (Starling); short by fees £12.40 accepted 2026-09-27 (owner)"
    r = fee_row(notes)
    feed = [pay(475, "2026-08-26", "INV 2408"), pay(462.6, "2026-09-25", "INV 2408")]
    assert cp.open_rows([r], T) == [] and cp.fee_pending(r, T) and cp.closed_on(r, T) == datetime.date(2026, 9, 27)
    client = FakeClient(feed)
    got = cp.collect(client, [r], T)
    assert [(x["booking_ref"], a["state"]) for x, _, a in got] == [("2408", "PAID_IN_FULL")], got
    assert min(c[0] for c in client.calls) <= datetime.date(2026, 8, 21)  # the feed reaches back to the deposit
    _, paid, a = got[0]
    assert a["record_in_books"][-1] == ["2026-09-25", 462.6, 12.4] and a["action"] != "balance_reminder"
    new = cp.updated_notes(notes, a, paid)
    assert new == notes + "; paid in full 2026-09-27", new  # the same close date: never an earlier one
    closed = fee_row(new)
    assert cp.closed_on(closed, T) == datetime.date(2026, 9, 27) and not cp.fee_pending(closed, T)
    assert cp.collect(FakeClient(feed), [closed], T) == []  # closed: off the list
    # both payments count as received; none after the close
    since = cp.received_since(FakeClient(feed), [closed], datetime.date(2026, 9, 21), T)
    assert since == [("2408", "2026-09-25", 462.6)], since


def test_fee_close_keeps_later_payments_flagged():
    notes = "deposit seen 2026-08-26 (Starling); short by fees £12.40 accepted 2026-09-26 (owner)"
    feed = [pay(475, "2026-08-26", "INV 2408"), pay(462.6, "2026-09-25", "INV 2408"), pay(12.4, "2026-09-27", "INV 2408")]
    for n in (notes, notes + "; paid in full 2026-09-26"):
        got = cp.collect(FakeClient(feed), [fee_row(n)], T)
        assert [a["state"] for _, _, a in got] == ["PAYMENT_AFTER_CLOSE"], (n, got)
        a = got[0][2]
        assert a["hand_check_payments"] == [["2026-09-27", 12.4]] and a["record_in_books"] == [], a
        assert cp.updated_notes(n, a, got[0][1]) == n  # never rewritten
        assert cp.received_since(FakeClient(feed), [fee_row(n)], datetime.date(2026, 9, 21), T) == \
            [("2408", "2026-09-25", 462.6)]


def test_fee_note_is_written_only_with_the_owner_nonce():
    fee = "short by fees £12.40 accepted 2026-09-28"
    d, path = owner_ledger()
    p, notes = run_owner(d, path, ["--note", "2111", fee])
    assert p.returncode != 0 and notes == "PENDING: invoiced", (p.stderr, notes)
    p, notes = run_owner(d, path, ["--note", "2111", fee, "--owner"])  # no nonce
    assert p.returncode != 0 and notes == "PENDING: invoiced", (p.stderr, notes)
    nonce_file(d)
    p, notes = run_owner(d, path, ["--note", "2111", fee, "--owner"], stdin_text=NONCE + "\n")
    assert p.returncode == 0 and notes == f"PENDING: invoiced; {fee} (owner)", (p.stderr, notes)
    assert cp.fees_accepted({"notes": notes}, datetime.date(2026, 9, 28)) == 12.4


# ---------------------------------------------------------------- the writers record facts (structured state, PR 4)

import lcs_events as ev  # noqa: E402

TODAY = cp.lm.today()
TD = TODAY.isoformat()


def log_of(d):
    """The live lines of <d>/events.jsonl (the migration's seed line left out)."""
    path = os.path.join(d, "events.jsonl")
    lines = [json.loads(x) for x in open(path).read().splitlines()] if os.path.exists(path) else []
    return [e for e in lines if e["src"] == "live"]


def seed_migration(d):
    """<d>/events.jsonl holding one migration line: the writers record facts only once the migration is applied."""
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    obj = {"v": 1, "eid": "00000000000000aa", "prev": "", "at": now, "on": "2026-01-01", "subject": "booking",
           "id": "0000", "kind": "deposit-seen", "fields": {}, "by": "script", "src": "migration"}
    fd = os.open(os.path.join(d, "events.jsonl"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.write(fd, (ev.dumps(ev.validate(obj)) + "\n").encode())
    os.close(fd)


def run_fact(notes, *args, migrated=True):
    """check_payments.py with the ledger and the log in one temp private folder: (process, notes, live log lines)."""
    d = tempfile.mkdtemp()
    os.chmod(d, 0o700)
    if migrated:
        seed_migration(d)
    path = os.path.join(d, "bookings.csv")
    cols = ["booking_ref", "value_gbp", "invoice_date", "event_date", "notes", "client_name"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row("2111", 650, "2026-08-22", "2026-11-21", notes))
    env = dict(os.environ, LCS_BOOKINGS_CSV=path, LCS_PRIVATE_DIR=d)
    p = subprocess.run([PY, SCRIPT, *args], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    with open(path, newline="") as f:
        return p, list(csv.DictReader(f))[0]["notes"], log_of(d)


SCRIPT_FACTS = [  # (args after the ref, the clause written, kind, fields)
    (["cancelled"], f"cancelled {TD} by client email", "cancelled", {}),
    (["noted-paid", "--scope", "part"], f"paid per client email {TD}", "noted-paid", {"scope": "part"}),
    (["noted-paid", "--scope", "full"], f"balance paid per client email {TD}", "noted-paid", {"scope": "full"}),
    (["arranged", "--method", "cash"], f"balance payable in cash on the day (arranged {TD})", "arranged", {"method": "cash"}),
    (["arranged", "--method", "cheque"], f"balance payable by cheque on the day (arranged {TD})", "arranged",
     {"method": "cheque"}),
    (["arranged", "--method", "third-party"], f"balance to be paid by another payer (arranged {TD})", "arranged",
     {"method": "third-party"}),
]


def test_fact_writes_todays_phrase_and_its_event_claiming_it():
    for extra, clause, kind, fields in SCRIPT_FACTS:
        p, notes, log = run_fact("PENDING: invoiced", "--fact", "2111", *extra)
        assert p.returncode == 0 and f"2111: {kind} recorded" in p.stdout, (extra, p.stderr)
        assert notes == f"PENDING: invoiced; {clause}", (extra, notes)
        assert len(log) == 1, log
        e = log[0]
        assert (e["kind"], e["fields"], e["by"], e["on"], e["src"]) == (kind, fields, "script", TD, "live"), e
        assert e["note"] == ev.note_hash(clause), e


def test_each_fact_phrase_reads_as_its_fact_from_the_notes_alone():
    """With the log renamed away, the note says the same thing (the pattern readers' fallback)."""
    for extra, clause, kind, fields in SCRIPT_FACTS:
        said = cp.assertions(clause, 650.0, TODAY)
        family = {"cancelled": "cancellation", "noted-paid": "noted paid", "arranged": "arrangement"}[kind]
        want = {"cancelled": True, "arranged": True, "noted-paid": fields.get("scope")}[kind]
        assert said[family] == want, (clause, said)
        assert [f for f, v in said.items() if v is not None] == [family], (clause, said)
    for kind, fields, want in (("paid-in-full", {"basis": "owner"}, "close"), ("fees-accepted", {"amount": "12.40"}, "close"),
                               ("reinstated", {}, "cancellation"), ("deposit-kept", {}, "cancel settlement"),
                               ("refunded", {}, "cancel settlement"), ("payment-checked", {}, "cancel settlement")):
        clause = cp.fact_phrase(kind, fields, TODAY, "owner")
        said = cp.assertions(clause, 650.0, TODAY)
        assert said[want] is not None and said[want] is not False or kind == "reinstated", (clause, said)
        assert clause.endswith(" (owner)"), clause
    assert cp.assertions(cp.fact_phrase("reinstated", {}, TODAY, "owner"), 650.0, TODAY)["cancellation"] is False


def test_fact_refuses_the_owner_kinds_and_bad_input_and_writes_nothing():
    future = (TODAY + datetime.timedelta(days=1)).isoformat()
    old = (TODAY - datetime.timedelta(days=731)).isoformat()
    for args in (["--fact", "2111", "refunded"], ["--fact", "2111", "paid-in-full"],
                 ["--fact", "2111", "fees-accepted", "--amount", "12.40"], ["--fact", "2111", "reinstated"],
                 ["--fact", "2111", "deposit-seen"], ["--fact", "2111", "reminder-drafted"], ["--fact", "2111", "retract"],
                 ["--fact", "2111", "discount-agreed"], ["--fact", "2111", "sacked"],
                 ["--fact", "2111", "arranged"], ["--fact", "2111", "arranged", "--method", "card"],
                 ["--fact", "2111", "noted-paid"], ["--fact", "2111", "noted-paid", "--scope", "all"],
                 ["--fact", "2111", "cancelled", "--method", "cash"], ["--fact", "2111", "cancelled", "--amount", "5"],
                 ["--fact", "2111", "cancelled", "--on", future], ["--fact", "2111", "cancelled", "--on", old],
                 ["--fact", "2111", "cancelled", "--on", "28/09/2026"], ["--fact", "2111", "cancelled", "--on", "2026-02-30"],
                 ["--fact", "9999", "cancelled"], ["--fact", "ann@example.com", "cancelled"], ["--fact", "21 11", "cancelled"],
                 ["--fact", "2111", "cancelled", "--note", "2111", "x"],
                 ["--fact", "2111", "cancelled", "--reminded", "2111"], ["--kind", "balance", "--fact", "2111", "cancelled"]):
        p, notes, log = run_fact("PENDING: invoiced", *args)
        assert p.returncode != 0 and notes == "PENDING: invoiced" and log == [], (args, p.stderr)
    p, notes, log = run_fact("PENDING: invoiced", "--fact", "2111", "cancelled", "--on", "2026-09-10")
    assert p.returncode == 0 and notes == "PENDING: invoiced; cancelled 2026-09-10 by client email" and log[0]["on"] == "2026-09-10"


def run_facts(*commands, owner=()):
    """Several check_payments.py runs against one migrated private folder (commands whose index is in `owner` run
    with the nonce): ([(returncode, stderr)], notes, live log lines)."""
    d, path = owner_ledger()
    out = []
    for n, args in enumerate(commands):
        if n in owner:
            nonce_file(d)
            p, _ = run_owner(d, path, [*args, "--owner"], stdin_text=NONCE + "\n")
        else:
            p, _ = run_owner(d, path, list(args))
        out.append((p.returncode, p.stderr))
    with open(path, newline="") as f:
        return out, list(csv.DictReader(f))[0]["notes"], log_of(d)


def test_the_script_may_not_backdate_a_fact_before_its_familys_latest():
    earlier = (TODAY - datetime.timedelta(days=5)).isoformat()
    runs, notes, log = run_facts(["--fact", "2111", "cancelled"], ["--fact", "2111", "cancelled", "--on", earlier])
    assert runs[0][0] == 0 and runs[1][0] != 0 and "earlier than" in runs[1][1], runs
    assert len(log) == 1 and notes.count("cancelled") == 1, (notes, log)
    runs, notes, log = run_facts(["--fact", "2111", "cancelled"], ["--fact", "2111", "reinstated", "--on", earlier],
                                 owner=(1,))
    assert [c for c, _ in runs] == [0, 0], runs  # the owner may: the booking is then held for him to settle
    runs, notes, log = run_facts(["--fact", "2111", "noted-paid", "--scope", "part"],
                                 ["--fact", "2111", "cancelled", "--on", earlier])  # another family: fine
    assert [c for c, _ in runs] == [0, 0], runs


def test_owner_facts_need_the_nonce_and_write_owner_phrases():
    cases = [(["paid-in-full"], f"paid in full {TD} (owner)", "paid-in-full", {"basis": "owner"}),
             (["fees-accepted", "--amount", "12.4"], f"short by fees £12.40 accepted {TD} (owner)", "fees-accepted",
              {"amount": "12.40"}),
             (["reinstated"], f"reinstated {TD} (owner)", "reinstated", {}),
             (["deposit-kept"], f"deposit kept {TD} (owner)", "deposit-kept", {}),
             (["refunded"], f"refunded {TD} (owner)", "refunded", {}),
             (["payment-checked"], f"payment checked {TD} (owner)", "payment-checked", {}),
             (["cancelled"], f"cancelled {TD} (owner)", "cancelled", {}),
             (["arranged", "--method", "cash"], f"balance payable in cash on the day (arranged {TD}) (owner)", "arranged",
              {"method": "cash"})]
    for extra, clause, kind, fields in cases:
        d, path = owner_ledger()
        args = ["--fact", "2111", *extra, "--owner"]
        p, notes = run_owner(d, path, args)  # no nonce
        assert p.returncode != 0 and notes == "PENDING: invoiced" and log_of(d) == [], (extra, p.stderr)
        assert "nothing written" in p.stderr, p.stderr
        nonce_file(d)
        p, notes = run_owner(d, path, args, stdin_text=NONCE + "\n")
        assert p.returncode == 0 and notes == f"PENDING: invoiced; {clause}", (extra, p.stderr, notes)
        (e,) = log_of(d)
        assert (e["kind"], e["fields"], e["by"], e["note"]) == (kind, fields, "owner", ev.note_hash(clause)), e
    d, path = owner_ledger()
    nf = nonce_file(d)
    p, notes = run_owner(d, path, ["--fact", "2111", "refunded", "--owner"], stdin_text=NONCE + "\n",
                         env_extra={"LCS_BOOKINGS_CSV": path})
    assert p.returncode != 0 and "LCS_BOOKINGS_CSV" in p.stderr and log_of(d) == [] and os.path.exists(nf)
    for amount in ("40.01", "0", "12.345", "abc"):
        d, path = owner_ledger()
        nonce_file(d)
        p, notes = run_owner(d, path, ["--fact", "2111", "fees-accepted", "--amount", amount, "--owner"],
                             stdin_text=NONCE + "\n")
        assert p.returncode != 0 and notes == "PENDING: invoiced" and log_of(d) == [], amount


def test_before_the_migration_the_writers_write_their_notes_exactly_as_before():
    for args, clause in ((["--fact", "2111", "cancelled"], f"cancelled {TD} by client email"),
                         (["--reminded", "2111"], f"reminder drafted {TD}")):
        p, notes, log = run_fact("PENDING: invoiced", *args, migrated=False)
        assert p.returncode == 0 and notes == f"PENDING: invoiced; {clause}" and log == [], (args, p.stderr)


def test_reminded_records_its_marker():
    for kind, clause, what in ((None, f"reminder drafted {TD}", "deposit"), ("balance", f"balance reminder drafted {TD}", "balance"),
                               ("receipt", f"receipt drafted {TD}", "receipt")):
        p, notes, log = run_fact("PENDING: invoiced", "--reminded", "2111", *(["--kind", kind] if kind else []))
        assert p.returncode == 0 and notes == f"PENDING: invoiced; {clause}", p.stderr
        assert [(e["kind"], e["fields"], e["by"], e["note"]) for e in log] == [
            ("reminder-drafted", {"what": what}, "script", ev.note_hash(clause))], log


def in_private(fn):
    """Run fn with this process's private folder (LCS_PRIVATE_DIR) a fresh temp dir, the migration applied; returns
    (dir, fn's value)."""
    d = tempfile.mkdtemp()
    os.chmod(d, 0o700)
    seed_migration(d)
    saved = os.environ["LCS_PRIVATE_DIR"]
    os.environ["LCS_PRIVATE_DIR"] = d
    ev.clear_cache()
    try:
        return d, fn(d)
    finally:
        os.environ["LCS_PRIVATE_DIR"] = saved
        ev.clear_cache()


def test_apply_records_deposit_seen_and_paid_in_full_where_it_writes_them():
    def go(d):
        path = os.path.join(d, "bookings.csv")
        rows = [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced"),
                row("0512", 650, "2026-08-22", "2026-11-21", "deposit seen 2026-08-26 (Starling)", name="Bo Jones"),
                row("0513", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced", name="Cy Kerr")]
        cp.lm.write_csv(path, rows, list(rows[0].keys()))
        paid = {"2111": [("2026-08-26", 325.0, "reference")],
                "0512": [("2026-08-26", 325.0, "reference"), ("2026-09-20", 325.0, "reference")],
                "0513": [("2026-08-26", 325.0, "amount only")]}
        results = [(r, paid[r["booking_ref"]], cp.assess(r, paid[r["booking_ref"]], T)) for r in rows]
        saved = cp.LEDGER
        cp.LEDGER = path
        try:
            assert cp.apply_notes(results, T)
        finally:
            cp.LEDGER = saved
        return {r["booking_ref"]: r["notes"] for r in cp.lm.read_csv(path)}
    d, notes = in_private(go)
    assert notes["2111"] == "deposit seen 2026-08-26 (Starling); invoiced" and notes["0513"] == "PENDING: invoiced", notes
    assert notes["0512"] == "deposit seen 2026-08-26 (Starling); paid in full 2026-09-20", notes
    got = [(e["id"], e["kind"], e["fields"], e["on"], e["by"], e["note"]) for e in log_of(d)]
    assert got == [("2111", "deposit-seen", {}, "2026-08-26", "script", ev.note_hash("deposit seen 2026-08-26 (Starling)")),
                   ("0512", "paid-in-full", {"basis": "bank"}, "2026-09-20", "script",
                    ev.note_hash("paid in full 2026-09-20"))], got


def test_apply_still_writes_the_note_of_a_ref_the_log_cant_take():
    """A legacy ref the state log's id pattern refuses (a space, a slash) keeps today's behaviour: the note, no fact,
    and the other rows' facts are still recorded."""
    def go(d):
        path = os.path.join(d, "bookings.csv")
        rows = [row("21 11", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced"),
                row("0512", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced", name="Bo Jones")]
        cp.lm.write_csv(path, rows, list(rows[0].keys()))
        paid = [("2026-08-26", 325.0, "reference")]
        saved = cp.LEDGER
        cp.LEDGER = path
        try:
            cp.apply_notes([(r, paid, cp.assess(r, paid, T)) for r in rows], T)
        finally:
            cp.LEDGER = saved
        return [r["notes"] for r in cp.lm.read_csv(path)]
    d, notes = in_private(go)
    assert notes == ["deposit seen 2026-08-26 (Starling); invoiced"] * 2, notes
    assert [(e["id"], e["kind"]) for e in log_of(d)] == [("0512", "deposit-seen")]


def test_a_ledger_write_that_fails_after_the_fact_withdraws_it():
    def go(d):
        path = os.path.join(d, "bookings.csv")
        cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced")],
                        list(row("a", 1, "", "").keys()))
        saved, real = (sys.argv, cp.LEDGER), cp.lm.write_csv
        sys.argv, cp.LEDGER = ["check_payments.py", "--fact", "2111", "cancelled"], path

        def broken(*a, **k):
            raise OSError("disk full")
        cp.lm.write_csv = broken
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                cp.main()
            return "not refused", None
        except SystemExit as e:
            return str(e), cp.lm.read_csv(path)[0]["notes"]
        finally:
            sys.argv, cp.LEDGER = saved
            cp.lm.write_csv = real
    d, (msg, notes) = in_private(go)
    assert "nothing written" in msg and "withdrawn" in msg and notes == "PENDING: invoiced", (msg, notes)
    assert [(e["kind"], e["fields"].get("why")) for e in log_of(d)] == [("cancelled", None), ("retract", "write-failed")]


def test_note_keeps_its_text_and_records_the_fact_it_states_until_the_refusal_is_switched_on():
    """Until the prompts use --fact (plan, Task 18), the assistant's fact-shaped --note lines still work, and record
    the fact they state claiming the note, so a later fact in that family never holds the booking."""
    assert cp.NOTE_REFUSES_FACTS is False
    for text, facts in (("cancelled 2026-09-28 by client email", [("cancelled", {})]),
                        ("paid per client email 2026-09-28", [("noted-paid", {"scope": "part"})]),
                        ("balance to be paid in cash", [("arranged", {"method": "cash"})]),
                        ("4 singers, London", [])):
        p, notes, log = run_fact("PENDING: invoiced", "--note", "2111", text)
        assert p.returncode == 0 and notes == "PENDING: invoiced; " + text and p.stdout.strip() == "2111: note added", \
            (text, p.stderr)
        assert [(e["kind"], e["fields"]) for e in log] == facts, (text, log)
        assert all(e["by"] == "script" and e["on"] == TD and e["note"] == ev.note_hash(text) for e in log), log
        p, notes, log = run_fact("PENDING: invoiced", "--note", "2111", text, migrated=False)
        assert p.returncode == 0 and notes == "PENDING: invoiced; " + text and log == [], (text, p.stderr)


def test_a_noted_cancellation_then_the_owners_reinstatement_reads_reinstated_and_is_never_held():
    def go(d):
        path = os.path.join(d, "bookings.csv")
        cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced")],
                        list(row("a", 1, "", "").keys()))
        saved = (sys.argv, cp.LEDGER, cp.lcs_owner.owner_confirmed, cp.lcs_owner._PROVEN,
                 os.environ.pop("LCS_BOOKINGS_CSV"))
        try:
            cp.LEDGER = path
            for argv in (["--note", "2111", "cancelled 2026-09-20 by client email"],
                         ["--fact", "2111", "reinstated", "--owner"]):
                cp.lcs_owner.owner_confirmed, cp.lcs_owner._PROVEN = (lambda *a: True), "--owner" in argv
                sys.argv = ["check_payments.py", *argv]
                with contextlib.redirect_stdout(io.StringIO()):
                    cp.main()
        finally:
            (sys.argv, cp.LEDGER, cp.lcs_owner.owner_confirmed, cp.lcs_owner._PROVEN,
             os.environ["LCS_BOOKINGS_CSV"]) = saved
        ev.clear_cache()
        r = cp.lm.read_csv(path)[0]
        return r, cp.is_cancelled(r), cp.held(r, TODAY), cp.notes_cancelled(r["notes"])
    _, (r, cancelled, held, by_notes) = in_private(go)
    assert (cancelled, held, by_notes) == (False, [], False), (r["notes"], cancelled, held)


def test_note_refuses_fact_shaped_text_once_switched_on():
    want = {"cancelled 2026-09-28 by client email": "--fact 2111 cancelled",
            "client cancelling": "--fact 2111 cancelled",
            "paid per client email 2026-09-28": "--fact 2111 noted-paid --scope part",
            "balance paid per client email 2026-09-28": "--fact 2111 noted-paid --scope full",
            "balance to be paid in cash": "--fact 2111 arranged --method cash|cheque|third-party"}
    for text, form in want.items():
        assert cp.fact_shaped(text) and form in cp.note_refusal("2111", text), (text, cp.note_refusal("2111", text))
    for text in ("4 singers, London", "client asked about parking", "may be cancelling", "no payment received",
                 "deposit not yet seen"):
        assert cp.fact_shaped(text) is None and cp.note_refusal("2111", text) is None, text

    def go(d):
        path = os.path.join(d, "bookings.csv")
        cp.lm.write_csv(path, [row("2111", 650, "2026-08-22", "2026-11-21", "PENDING: invoiced")],
                        list(row("a", 1, "", "").keys()))
        saved = (sys.argv, cp.LEDGER, cp.NOTE_REFUSES_FACTS)
        out = []
        try:
            cp.LEDGER, cp.NOTE_REFUSES_FACTS = path, True
            for text in ("cancelled 2026-09-28 by client email", "4 singers, London"):
                sys.argv = ["check_payments.py", "--note", "2111", text]
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        cp.main()
                    out.append("written")
                except SystemExit as e:
                    out.append(str(e))
        finally:
            sys.argv, cp.LEDGER, cp.NOTE_REFUSES_FACTS = saved
        return out, cp.lm.read_csv(path)[0]["notes"]
    _, (out, notes) = in_private(go)
    assert out[0] == "record it with --fact 2111 cancelled; nothing written" and out[1] == "written", out
    assert notes == "PENDING: invoiced; 4 singers, London", notes


def clear_log():
    """No state log in this process's private folder: the in-process writers append to it, and a later test's
    booking with the same ref would read those facts."""
    for name in ("events.jsonl", "events.jsonl.lock"):
        if os.path.exists(os.path.join(_HOME, name)):
            os.remove(os.path.join(_HOME, name))
    ev.clear_cache()


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            clear_log()
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
