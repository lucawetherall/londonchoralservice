#!/usr/bin/env python3
"""Tests for scripts/bookings/check_payments.py. Stdlib only."""
import contextlib, csv, datetime, io, os, subprocess, sys, tempfile

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


def test_amount_only_needs_a_unique_amount():
    one = [row("A", 1150, "2026-09-01", "2026-10-10", name="X Y")]
    two = one + [row("B", 1150, "2026-09-02", "2026-10-11", name="P Q")]
    payment = [pay(1150, "2026-09-05", "wedding")]
    assert cp.match(one, payment, T)["A"][0][2] == "amount only"
    assert cp.match(two, payment, T) == {"A": [], "B": []}


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


def test_just_received_only_from_pending():
    paid = [("2026-09-27", 325.0, "reference")]
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "PENDING: invoiced"), paid, T)["just_received"] is True
    assert cp.assess(row("X", 650, "2026-09-20", "2026-11-21", "deposit seen 2026-09-27 (Starling)"), paid, T)["just_received"] is False


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
    for ref in ("INV2111", "inv-2111 deposit", "2111", "Invoice INV 2111"):
        assert cp.match(rows, [pay(325, "2026-08-26", ref)], T)["2111"][0][2] == "reference", ref


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
    assert [(r["booking_ref"], a["state"], a["just_received"]) for r, _, a in got] == [("2111", "DEPOSIT_SEEN", True)]


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
