#!/usr/bin/env python3
"""Tests for scripts/bookings/singer_invoices.py. Stdlib only. Uses a temp private dir."""
import argparse, base64, contextlib, datetime, io, os, sys, tempfile

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_money as lm
import singer_invoices as si

LABELLED = """INVOICE
Invoice No: 1020
Date: 25/09/2026
To: Alma Consort Ltd
Funeral 21 September   £100.00
Total due £100.00
Account name: B Fenwick
Sort code: 12-34-56
Account number: 12345678
"""
TERSE = """Invoice INV-0107
Wedding 19 Sep     £150
Travel             £50
Subtotal £200.00
TOTAL £200.00
Sort Code 123456 Acc No 8765 4321
"""
NO_BANK = """Invoice 20260309-001
Balance due: £1,129.15
Thanks!"""


def test_extract_labelled_invoice():
    assert si.extract(LABELLED) == {"amount": 100.0, "invoice_ref": "1020", "sort_code": "123456", "account_number": "12345678"}


def test_extract_terse_invoice():
    e = si.extract(TERSE)
    assert (e["amount"], e["invoice_ref"], e["sort_code"], e["account_number"]) == (200.0, "INV-0107", "123456", "87654321")


def test_extract_without_bank_details():
    e = si.extract(NO_BANK)
    assert (e["amount"], e["invoice_ref"], e["sort_code"], e["account_number"]) == (1129.15, "20260309-001", "", "")


def test_extract_falls_back_to_largest_pound_figure():
    assert si.extract("Fee £80\nTravel £20\nPlease pay £100")["amount"] == 100.0


def inv(sort="123456", acc="12345678", amount=100.0):
    return {"amount": amount, "invoice_ref": "1", "sort_code": sort, "account_number": acc}


def test_new_singer_needs_a_payee():
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], {}, [])
    assert a["payee"] == "NEW: add as a payee in the Starling app" and a["bank_changed"] == "no"
    assert a["bank_last4"] == "5678" and "12345678" not in str(a)


def test_existing_payee_by_fingerprint():
    fps = {lm.bank_fingerprint("123456", "12345678"): "Ben W"}
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben W"])["payee"] == "existing: Ben W"


def test_changed_bank_details_warn():
    history = [{"singer_email": "b@x.com", "bank_fp": lm.bank_fingerprint("123456", "11112222"), "bank_last4": "2222"}]
    a = si.assess_new(inv(), "B@X.com", "Ben Fenwick", history, {}, [])
    assert a["bank_changed"] == "yes" and any("BANK DETAILS CHANGED" in w and "••••2222" in w for w in a["warnings"])


def test_payee_name_with_different_details_warns():
    fps = {lm.bank_fingerprint("123456", "99990000"): "Ben Fenwick"}
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben Fenwick"])
    assert a["bank_changed"] == "yes" and "different bank details" in a["payee"]


def test_no_bank_details_and_no_token():
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", [], None, [])
    assert a["payee"] == "unknown (no Starling token)" and "no bank details found on the invoice" in a["warnings"]


def out(amount, when, who, uid=None, at="T10:00:00Z"):
    item = {"direction": "OUT", "amount": {"minorUnits": int(round(amount * 100))},
            "transactionTime": when + at, "counterPartyName": who}
    if uid:
        item["feedItemUid"] = uid
    return item


def unpaid(mid, name, amount, received, payee="NEW: add as a payee in the Starling app"):
    return {"message_id": mid, "singer_name": name, "amount_gbp": f"{amount:.2f}", "received": received,
            "payee": payee, "paid_on": "", "bank_changed": "no"}


def test_match_paid_by_amount_and_surname():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19")]
    assert si.match_paid(rows, [out(200, "2026-09-19", "LAURA PENHALLOW", "p1")]) == {"m1": ("2026-09-19", 200.0, "p1", False)}


def test_match_paid_uses_payee_name():
    rows = [unpaid("m1", "Maddy Kessell", 160, "2026-09-01", payee="existing: M M Kessell")]
    assert si.match_paid(rows, [out(160, "2026-09-02", "M M KESSELL", "p1")]) == {"m1": ("2026-09-02", 160.0, "p1", False)}


def test_match_paid_rejects_wrong_amount_early_date_and_double_use():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19"), unpaid("m2", "Laura Penhallow", 200, "2026-09-20")]
    assert si.match_paid(rows, [out(150, "2026-09-21", "LAURA PENHALLOW", "p0")]) == {}
    assert si.match_paid(rows[:1], [out(200, "2026-09-10", "LAURA PENHALLOW", "p0")]) == {}
    assert si.match_paid(rows, [out(200, "2026-09-21", "LAURA PENHALLOW", "p1")]) == {"m1": ("2026-09-21", 200.0, "p1", False)}


def test_summary_counts():
    rows = [dict(unpaid("m1", "A B", 100, "2026-09-20"), bank_changed="yes"),
            dict(unpaid("m2", "C D", 50, "2026-09-26")),
            dict(unpaid("m3", "E F", 70, "2026-09-01"), paid_on="2026-09-02")]
    assert si.summary(rows, datetime.date(2026, 9, 28)) == {"unpaid": 2, "unpaid_total": 150.0, "oldest_days": 8, "bank_changed": 1}


class FakeClient:
    def __init__(self, payees=(), out=()):
        self._payees, self._out = list(payees), list(out)

    def payees(self):
        return self._payees

    def feed(self, since, until, direction):
        assert direction == "OUT"
        return self._out


def eml(body, sender="Ben Fenwick <ben@example.com>"):
    path = os.path.join(TMP, "msg.eml")
    with open(path, "w") as f:
        f.write(f"From: {sender}\nSubject: Invoice\nContent-Type: text/plain; charset=utf-8\n\n{body}")
    return path


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_store_lifecycle():
    """scan -> repeat scan -> paid --apply -> thanked, in order (one test: the runner sorts by name)."""
    if si.STORE.exists():
        si.STORE.unlink()
    a = Args(file=eml(LABELLED), message_id="m1", received="2026-09-25", sender_email="ben@example.com", sender_name="Ben Fenwick")
    si.cmd_scan(a, FakeClient())
    rows = lm.read_csv(si.STORE)
    assert len(rows) == 1 and rows[0]["amount_gbp"] == "100.00" and rows[0]["payee"] == si.NEW_PAYEE
    assert "12345678" not in si.STORE.read_text() and rows[0]["bank_last4"] == "5678"
    assert oct(si.STORE.stat().st_mode)[-3:] == "600"
    si.cmd_scan(a, FakeClient())
    assert len(lm.read_csv(si.STORE)) == 1

    si.cmd_paid(Args(apply=True), FakeClient(out=[{"direction": "OUT", "amount": {"minorUnits": 10000},
                                                   "transactionTime": "2026-09-26T09:00:00Z", "counterPartyName": "BEN FENWICK",
                                                   "feedItemUid": "f-1"}]))
    row = lm.read_csv(si.STORE)[0]
    assert (row["paid_on"], row["paid_amount"]) == ("2026-09-26", "100.00")

    si.cmd_thanked(Args(message_id="m1"))
    assert "paid reply drafted" in lm.read_csv(si.STORE)[0]["notes"]


# --- review fixes -----------------------------------------------------------------------------

def test_extract_amount_labels():
    assert si.extract("Invoice 12\nTotal £1,129.15\nTotal VAT £0.00")["amount"] == 1129.15
    assert si.extract("Invoice 12\nTotal £300.00\nBalance due £200.00\nTotal paid £100.00")["amount"] == 200.0
    assert si.extract("Balance due £200.00\nTotal paid £100.00")["amount"] == 200.0
    assert si.extract("Invoice 12\nTotal of 3 services\n£300")["amount"] == 300.0
    assert si.extract("Total: 25/09/2026")["amount"] == 0.0
    assert si.extract("Invoice 12\nSub-total £100\nDeposit paid £50")["amount"] == 100.0
    assert si.extract("Invoice 12\nRehearsal £50\nTotal hours 3\nTotal £150")["amount"] == 150.0
    assert si.extract("Invoice 12\nTotal: GBP 150.00")["amount"] == 150.0
    assert si.extract("Subtotal £1,000.00\nVAT £200.00\nTotal £1,200.00")["amount"] == 1200.0


def bank(text):
    e = si.extract(text)
    return e["sort_code"], e["account_number"]


def test_extract_bank_layouts():
    assert bank("Invoice 12\nTotal £100.00\nS/C 12-34-56 A/C 87654321") == ("123456", "87654321")
    assert bank("Invoice 12\nTotal £100.00\nSort code Account number\n12-34-56 87654321") == ("123456", "87654321")
    assert bank("Total £100\nSort code 12-34-56 Account number 1234567") == ("123456", "1234567")
    assert lm.bank_fingerprint("123456", "1234567") == lm.bank_fingerprint("123456", "01234567")
    assert bank("Total £100.00\nIBAN: GB29 NWBK 6016 1331 9268 19\nBIC NWBKGB2L") == ("601613", "31926819")
    assert bank("IBAN: GB29NWBK60161331926819\nSort code 60-16-13 Account number 31926819") == ("601613", "31926819")
    assert bank("Account enquiries: 0207 946 0958\nSort code 12-34-56\nAccount number 87654321") == ("123456", "87654321")
    assert bank("Accounts: 07700 900123\nSort code 12-34-56\nAccount number 87654321") == ("123456", "87654321")
    assert bank("Sort code 12.34.56\nAccount number 87654321") == ("123456", "87654321")
    assert bank("Sort code\n12-34-56\nAccount number\n87654321") == ("123456", "87654321")


def test_extract_bank_rejects_customer_account_and_ambiguity():
    text = "Customer account number: 55556666\nInvoice 12\nTotal £100\n\n\nSort code 12-34-56\nAccount number 87654321"
    assert bank(text) == ("123456", "87654321")
    assert bank("Your account no. 55556666\nSort code 12-34-56") == ("123456", "")
    near = "Account number 11112222\n\n\n\nTotal £100\nSort code 12-34-56 Account number 87654321"
    assert bank(near) == ("123456", "87654321")
    tie = "Account number 11112222\nSort code 12-34-56\nAccount number 33334444"
    assert bank(tie)[1] == ""
    a = si.assess_new(si.extract(tie), "b@x.com", "Ben Fenwick", [], {}, [])
    assert "no bank details found on the invoice" in a["warnings"]


def test_extract_ref_is_never_a_bank_number():
    assert si.extract("INVOICE\n87654321 12-34-56\nTotal £100")["invoice_ref"] == ""
    assert si.extract("Invoice 87654321\nSort code 12-34-56 Account number 87654321\nTotal £100")["invoice_ref"] == ""
    assert si.extract("Invoice 123456\nSort code 12-34-56 Account 11112222\nTotal £100")["invoice_ref"] == ""
    assert si.extract("Invoice number: LW-042\nTotal £150")["invoice_ref"] == "LW-042"


def test_normalise_name():
    for n in ("Ben Fenwick via QuickBooks", "Fenwick, Ben", "Ben Fenwick (tenor)", "Ben Fenwick Music",
              "BEN FENWICK LTD", "Ben Fenwick, tenor", "\"Fenwick, Ben\""):
        assert si.normalise_name(n) == "ben fenwick", n
    assert si.surname("Fenwick, Ben") == "fenwick"
    assert si.normalise_name("Olivia Smith") == "olivia smith"


def hrow(email, name, sc, acc, received, paid_on="", changed="no", mid="h", verified="", confirmed=""):
    return {"message_id": mid, "singer_email": email, "singer_name": name, "received": received,
            "bank_fp": lm.bank_fingerprint(sc, acc), "bank_last4": acc[-4:], "paid_on": paid_on, "bank_changed": changed,
            "paid_verified": verified, "bank_confirmed": confirmed}


def test_new_address_with_new_details_warns():
    history = [hrow("ben@example.com", "Ben Fenwick", "123456", "11112222", "2026-08-01", paid_on="2026-08-05", verified="yes")]
    a = si.assess_new(inv(), "ben.fenwick.tenor@gmail.com", "Fenwick, Ben", history, {}, [])
    assert a["bank_changed"] == "yes" and any("BANK DETAILS CHANGED" in w and "••••2222" in w for w in a["warnings"])


def test_invoicing_service_address_is_not_an_identity():
    history = [hrow("quickbooks@notification.intuit.com", "Amy Lee", "123456", "11112222", "2026-08-01")]
    a = si.assess_new(inv(), "quickbooks@notification.intuit.com", "Kathleen Jones", history, {}, [])
    assert a["bank_changed"] == "no"


def test_new_bank_details_warning():
    new = "NEW BANK DETAILS: confirm them by phone on a number you already hold before adding the payee"
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], {}, [])
    assert a["payee"] == si.NEW_PAYEE and new in a["warnings"]
    fps = {lm.bank_fingerprint("123456", "12345678"): "Ben W"}
    assert new not in si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Ben W"])["warnings"]
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "12345678", "2026-08-01", confirmed="yes")]
    assert new not in si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])["warnings"]
    history[0]["bank_confirmed"] = ""  # seen before but never confirmed or paid to verifiably: not-yet-verified, not new
    a2 = si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])
    assert new not in a2["warnings"]
    assert any(w.startswith(si.NOT_YET_VERIFIED) for w in a2["warnings"])


def test_new_bank_details_warning_names_the_confirm_command():
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], {}, [], message_id="m42")
    assert f"{si.NEW_DETAILS}, then run singer_invoices.py confirm m42" in a["warnings"]
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "12345678", "2026-08-01")]
    a2 = si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [], message_id="m43")
    assert f"{si.NOT_YET_VERIFIED}, then run singer_invoices.py confirm m43" in a2["warnings"]
    # without a message id (old callers), the hint is simply omitted
    assert si.NEW_DETAILS in si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], {}, [])["warnings"]


def test_changed_warning_notes_same_last_four_digits():
    history = [hrow("b@x.com", "Ben Fenwick", "111111", "11111234", "2026-08-01", verified="yes")]
    a = si.assess_new(inv("999999", "99991234"), "b@x.com", "Ben Fenwick", history, {}, [])
    assert any("was ••••1234" in w and "now ••••1234" in w
              and "(same last four digits, different sort code or account)" in w for w in a["warnings"])
    # a genuinely different last four never gets the note
    history2 = [hrow("b@x.com", "Ben Fenwick", "111111", "11112222", "2026-08-01", verified="yes")]
    a2 = si.assess_new(inv("999999", "99991234"), "b@x.com", "Ben Fenwick", history2, {}, [])
    assert not any("same last four digits" in w for w in a2["warnings"])


def test_changed_details_warn_until_verified():
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "11112222", "2026-08-01", verified="yes", mid="h1"),
               hrow("b@x.com", "Ben Fenwick", "123456", "12345678", "2026-09-01", changed="yes", mid="h2")]
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])
    assert a["bank_changed"] == "yes" and any("••••2222" in w for w in a["warnings"])
    history[1]["paid_on"] = "2026-09-03"  # a paid mark matched by name is not trust (C-1b)
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])["bank_changed"] == "yes"
    history[1]["paid_verified"] = "yes"
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])["bank_changed"] == "no"
    history[1]["paid_verified"], history[1]["bank_confirmed"] = "no", "yes"
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])["bank_changed"] == "no"


def test_was_figure_uses_most_recent_trusted_row():
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "33334444", "2026-09-01", mid="new", confirmed="yes"),
               hrow("b@x.com", "Ben Fenwick", "123456", "11112222", "2026-07-01", mid="old", verified="yes")]
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])
    assert any("was ••••4444" in w for w in a["warnings"])


def test_missing_bank_details_compare_with_trusted():
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "11112222", "2026-08-01")]
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", history, {}, [])
    assert "no bank details on the invoice: compare them with ••••2222 before paying" in a["warnings"]


def test_payee_name_match_is_whole_word():
    fps = {lm.bank_fingerprint("123456", "99990000"): "Kathleen Jones"}
    a = si.assess_new(inv(), "amy@x.com", "Amy Lee", [], fps, ["Kathleen Jones"])
    assert a["payee"] == si.NEW_PAYEE and a["bank_changed"] == "no"


def test_match_paid_whole_names():
    r = dict(unpaid("m1", "Ben Fenwick", 100, "2026-09-20"), payee="existing: Ben W")
    assert si.match_paid([r], [out(100, "2026-09-21", "HOWARD JONES", "p1")]) == {}
    rows = [unpaid("lee", "Amy Lee", 100, "2026-09-20"), unpaid("kat", "Kathleen Jones", 100, "2026-09-21")]
    assert si.match_paid(rows, [out(100, "2026-09-22", "KATHLEEN JONES", "p1")]) == {"kat": ("2026-09-22", 100.0, "p1", False)}


def test_match_paid_ambiguous_across_singers():
    rows = [unpaid("a", "Anna Smith", 100, "2026-09-20"), unpaid("j", "Andrew Smith", 100, "2026-09-21")]
    report = []
    assert si.match_paid(rows, [out(100, "2026-09-22", "SMITH A", "p1")], report) == {}
    assert report == ["AMBIGUOUS £100.00 on 2026-09-22 fits a (Anna), j (Andrew): check by hand"]
    rows[1]["singer_name"] = "John Smith"
    assert si.match_paid(rows, [out(100, "2026-09-22", "SMITH J", "p1")]) == {"j": ("2026-09-22", 100.0, "p1", False)}


def test_match_paid_before_invoice_arrived():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19")]
    report = []
    assert si.match_paid(rows, [out(200, "2026-09-10", "LAURA PENHALLOW", "p1")], report) == {}
    assert report == ["POSSIBLY ALREADY PAID m1: Laura £200.00 on 2026-09-10 (before the invoice arrived): check by hand"]
    report = []
    assert si.match_paid(rows, [out(200, "2026-09-01", "LAURA PENHALLOW", "p1")], report) == {} and report == []


def test_match_paid_feed_order():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19"), unpaid("m2", "Laura Penhallow", 200, "2026-09-24")]
    feed = [out(200, "2026-09-21", "LAURA PENHALLOW", "p1"), out(200, "2026-09-25", "LAURA PENHALLOW", "p2")]
    want = {"m1": ("2026-09-21", 200.0, "p1", False), "m2": ("2026-09-25", 200.0, "p2", False)}
    assert si.match_paid(rows, feed) == want
    assert si.match_paid(rows, feed[::-1]) == want


def test_match_paid_uses_london_date():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-26")]
    item = out(200, "2026-09-25", "LAURA PENHALLOW", "p1", at="T23:30:00Z")
    assert si.match_paid(rows, [item]) == {"m1": ("2026-09-26", 200.0, "p1", False)}


def fresh_store():
    if si.STORE.exists():
        si.STORE.unlink()


def test_paid_never_reuses_a_payment():
    fresh_store()
    body = "Invoice {n}\nTotal £100.00\nSort code 12-34-56\nAccount number 12345678"
    feed = FakeClient(out=[out(100, "2026-09-10", "BEN FENWICK", "feed-p")])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_scan(Args(file=eml(body.format(n=1)), message_id="A", received="2026-09-01",
                         sender_email="ben@example.com", sender_name="Ben Fenwick"), FakeClient())
        si.cmd_paid(Args(apply=True), feed)
        si.cmd_scan(Args(file=eml(body.format(n=2)), message_id="B", received="2026-09-05",
                         sender_email="ben@example.com", sender_name="Ben Fenwick"), FakeClient())
        si.cmd_paid(Args(apply=True), feed)
    rows = {r["message_id"]: r for r in lm.read_csv(si.STORE)}
    assert rows["A"]["paid_on"] == "2026-09-10" and rows["A"]["paid_ref"] == "feed-p"
    assert rows["B"]["paid_on"] == "", rows["B"]
    assert "12345678" not in buf.getvalue() and "123456" not in buf.getvalue() and "12345678" not in si.STORE.read_text()


def test_paid_skips_payments_recorded_before_paid_ref():
    fresh_store()
    base = {c: "" for c in si.COLUMNS}
    rows = [dict(base, message_id="A", received="2026-09-01", singer_name="Ben Fenwick", amount_gbp="100.00",
                 payee=si.NEW_PAYEE, bank_changed="no", paid_on="2026-09-10", paid_amount="100.00"),
            dict(base, message_id="B", received="2026-09-05", singer_name="Ben Fenwick", amount_gbp="100.00",
                 payee=si.NEW_PAYEE, bank_changed="no")]
    lm.write_csv(si.STORE, rows, [c for c in si.COLUMNS if c != "paid_ref"])
    with contextlib.redirect_stdout(io.StringIO()):
        si.cmd_paid(Args(apply=True), FakeClient(out=[out(100, "2026-09-10", "BEN FENWICK", "old-p")]))
    assert {r["message_id"]: r["paid_on"] for r in lm.read_csv(si.STORE)} == {"A": "2026-09-10", "B": ""}


def test_scan_newest_first_still_flags_the_newer_invoice():
    fresh_store()
    with contextlib.redirect_stdout(io.StringIO()):
        si.cmd_scan(Args(file=eml("Invoice 9\nTotal £100.00\nSort code 65-43-21\nAccount number 99998888"), message_id="new",
                         received="2026-09-25", sender_email="ben@x.com", sender_name="Ben Fenwick"), FakeClient())
        si.cmd_scan(Args(file=eml("Invoice 8\nTotal £100.00\nSort code 12-34-56\nAccount number 11112222"), message_id="old",
                         received="2026-09-20", sender_email="ben@x.com", sender_name="Ben Fenwick"), FakeClient())
    rows = {r["message_id"]: r for r in lm.read_csv(si.STORE)}
    assert rows["new"]["bank_changed"] == "yes" and "BANK DETAILS CHANGED" in rows["new"]["notes"]
    assert "99998888" not in si.STORE.read_text() and "11112222" not in si.STORE.read_text()


def test_received_must_be_iso():
    assert si.iso_date("2026-09-25") == "2026-09-25"
    assert si.iso_date("2026-09-25T10:00:00+00:00") == "2026-09-25"
    for bad in ("25/09/2026", "yesterday", "2026-09-25junk"):
        try:
            si.iso_date(bad)
        except argparse.ArgumentTypeError:
            continue
        raise AssertionError(f"accepted {bad!r}")
    rows = [dict(unpaid("m1", "A B", 100, "25/09/2026")), dict(unpaid("m2", "C D", 50, "2026-09-26"))]
    assert si.summary(rows, datetime.date(2026, 9, 28))["oldest_days"] == 2
    fresh_store()
    lm.write_csv(si.STORE, rows, si.COLUMNS)
    with contextlib.redirect_stdout(io.StringIO()):
        si.cmd_paid(Args(apply=False), FakeClient())
        si.cmd_status(Args())


def pdf_eml(pdf_bytes, body="See attached", fname="invoice.pdf"):
    b = base64.b64encode(pdf_bytes).decode()
    path = os.path.join(TMP, "pdf.eml")
    with open(path, "w") as f:
        f.write("From: Ben <ben@example.com>\nSubject: Invoice\nMIME-Version: 1.0\n"
                "Content-Type: multipart/mixed; boundary=XX\n\n"
                f"--XX\nContent-Type: text/plain\n\n{body}\n--XX\nContent-Type: application/pdf\n"
                f"Content-Disposition: attachment; filename=\"{fname}\"\nContent-Transfer-Encoding: base64\n\n{b}\n--XX--\n")
    return path


def test_unreadable_invoice_warns():
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w.encrypt(user_password="secret", owner_password="o")
    buf = io.BytesIO()
    w.write(buf)
    for data in (buf.getvalue(), b"%PDF-1.4 garbage"):
        found = si.read_invoice(pdf_eml(data))
        assert "could not read invoice.pdf (encrypted or damaged): check it by hand" in found["warnings"]
        assert "amount not found: check the invoice by hand" in found["warnings"]


def test_html_body_and_ref_without_amount():
    path = os.path.join(TMP, "html.eml")
    with open(path, "w") as f:
        f.write("From: B <b@x.com>\nSubject: inv\nContent-Type: text/html; charset=utf-8\n\n"
                "<p>Invoice 7</p><p>Total: &pound;150.00</p><p>Sort code: 12&#8209;34&#8209;56</p>"
                "<p>Account number: 8765&nbsp;4321</p>")
    found = si.read_invoice(path)
    assert (found["amount"], found["invoice_ref"], found["sort_code"], found["account_number"]) == (150.0, "7", "123456", "87654321")
    found = si.read_invoice(eml("Invoice 55\nThanks, see you Sunday"))
    assert found["invoice_ref"] == "55" and found["amount"] == 0.0


class Unavailable:
    def __init__(self, token):
        pass

    def payees(self):
        raise lm.StarlingError("no account")

    def feed(self, since, until, direction):
        import urllib.error
        raise urllib.error.HTTPError("https://api.starlingbank.com/x", 503, "down", {}, None)


def test_main_reports_starling_unavailable():
    fresh_store()
    saved = (lm.keychain_token, lm.StarlingReadOnly, sys.argv)
    lm.keychain_token, lm.StarlingReadOnly = (lambda: "tok"), Unavailable
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sys.argv = ["singer_invoices.py", "scan", eml(LABELLED), "--message-id", "m9", "--received", "2026-09-25",
                        "--sender-email", "b@x.com", "--sender-name", "Ben Fenwick"]
            si.main()
            lm.write_csv(si.STORE, [dict(unpaid("m1", "A B", 100, "2026-09-20"))], si.COLUMNS)
            before = si.STORE.read_text()
            sys.argv = ["singer_invoices.py", "paid", "--apply"]
            si.main()
        assert buf.getvalue().splitlines() == ["Starling unavailable (StarlingError); scan skipped",
                                               "Starling unavailable (HTTPError); paid skipped"], buf.getvalue()
        assert si.STORE.read_text() == before
    finally:
        lm.keychain_token, lm.StarlingReadOnly, sys.argv = saved


# --- round 3: the bank's own evidence, conflicting sources, names ------------------------------

def fp_out(amount, when, who, uid, sc, acc):
    return dict(out(amount, when, who, uid), counterPartySubEntityIdentifier=sc, counterPartySubEntitySubIdentifier=acc)


def fp_unpaid(mid, name, amount, received, sc="123456", acc="11112222"):
    return dict(unpaid(mid, name, amount, received), bank_fp=lm.bank_fingerprint(sc, acc), bank_last4=acc[-4:])


def test_match_paid_verified_by_bank_details_whatever_the_name():
    rows = [fp_unpaid("m1", "Ben Fenwick", 120, "2026-09-21")]
    item = fp_out(120, "2026-09-22", "BW MUSIC LTD", "v1", "12-34-56", "11112222")
    assert si.match_paid(rows, [item]) == {"m1": ("2026-09-22", 120.0, "v1", True)}
    assert si.match_paid(rows, [dict(item, amount={"minorUnits": 11000})]) == {}


def test_match_paid_mismatched_bank_details_block_the_name_match():
    rows = [fp_unpaid("m1", "Ben Fenwick", 120, "2026-09-21")]
    assert si.match_paid(rows, [fp_out(120, "2026-09-22", "BEN FENWICK", "x1", "654321", "99998888")]) == {}


def test_match_paid_reports_payment_to_different_bank_details():
    rows = [fp_unpaid("m1", "Ben Fenwick", 120, "2026-09-21")]
    report = []
    assert si.match_paid(rows, [fp_out(120, "2026-09-22", "BEN FENWICK", "x1", "654321", "99998888")], report) == {}
    assert report == ["PAID TO DIFFERENT BANK DETAILS £120.00 on 2026-09-22 to ••••8888 fits m1 "
                      "(Ben, invoice ••••2222): check by hand"]


def test_match_paid_different_bank_details_reported_once_per_item():
    fresh_store()
    anna = dict(email="anna@example.com", name="Anna Price")
    scan(INV_FP.format(n=1), "a1", "2026-09-01", client=FakeClient(payees=ANNA_PAYEE), **anna)
    paid(FakeClient(payees=ANNA_PAYEE, out=[fp_out(150, "2026-09-03", "ANNA PRICE", "p1", "20-30-40", "55667788")]))
    scan(NEW_FP.format(n=2), "a2", "2026-10-01", client=FakeClient(payees=ANNA_PAYEE), **anna)
    assert rows_by_id()["a2"]["bank_changed"] == "yes"
    report_out = paid(FakeClient(payees=ANNA_PAYEE,
                                  out=[fp_out(150, "2026-10-03", "ANNA PRICE", "p2", "20-30-40", "55667788")]))
    assert "PAID TO DIFFERENT BANK DETAILS £150.00 on 2026-10-03 to ••••7788 fits a2 " \
           "(Anna, invoice ••••3344): check by hand" in report_out
    assert rows_by_id()["a2"]["paid_on"] == ""


def test_match_paid_name_fallback_when_either_side_lacks_bank_details():
    rows = [unpaid("m1", "Ben Fenwick", 120, "2026-09-21")]
    item = fp_out(120, "2026-09-22", "BEN FENWICK", "n1", "654321", "99998888")
    assert si.match_paid(rows, [item]) == {"m1": ("2026-09-22", 120.0, "n1", False)}
    rows = [fp_unpaid("m1", "Ben Fenwick", 120, "2026-09-21")]
    assert si.match_paid(rows, [out(120, "2026-09-22", "B FENWICK", "n2")]) == {"m1": ("2026-09-22", 120.0, "n2", False)}


def test_match_paid_blocks_name_match_when_fp_is_trusted_for_a_different_singer():
    ben = fp_unpaid("ben1", "Ben Fenwick", 150, "2026-08-01", sc="112233", acc="99990000")
    ben["paid_on"], ben["paid_verified"] = "2026-08-05", "yes"  # Ben's own row: verified, and settled already
    bella = unpaid("bella1", "Bella Fenwick", 150, "2026-09-01")  # Bella's invoice carried no bank details
    item = fp_out(150, "2026-09-02", "B FENWICK", "x9", "112233", "99990000")  # but this payment carries Ben's fp
    report = []
    assert si.match_paid([bella], [item], report, history=[ben, bella]) == {}
    assert report == []
    # without the guard (no history passed) the initial+surname alone would have matched Bella
    assert si.match_paid([bella], [item]) == {"bella1": ("2026-09-02", 150.0, "x9", False)}


def test_match_paid_blocks_name_match_for_a_disagreeing_starling_payee():
    fp = lm.bank_fingerprint("112233", "99990000")
    bella = unpaid("bella1", "Bella Fenwick", 150, "2026-09-01")
    item = fp_out(150, "2026-09-02", "B FENWICK", "x9", "112233", "99990000")
    assert si.match_paid([bella], [item], history=[bella], payee_fps={fp: "Priya Kaur"}) == {}
    assert si.match_paid([bella], [item], history=[bella], payee_fps={fp: "Bella Fenwick"}) == \
        {"bella1": ("2026-09-02", 150.0, "x9", False)}


def test_match_paid_needs_the_first_name_or_initial():
    tom = [unpaid("m1", "Tom Jones", 120, "2026-09-21")]
    for who in ("BEN JONES", "A SMITH-JONES", "JONES B", "MR B JONES"):
        assert si.match_paid(tom, [out(120, "2026-09-22", who, "z")]) == {}, who
    for who in ("TOM JONES", "T JONES", "JONES T", "JONES TOM", "MR T JONES", "T A JONES"):
        assert si.match_paid(tom, [out(120, "2026-09-22", who, "z")]) == {"m1": ("2026-09-22", 120.0, "z", False)}, who
    anna = [unpaid("m1", "Anna Smith-Jones", 120, "2026-09-21")]
    assert si.match_paid(anna, [out(120, "2026-09-22", "A SMITH-JONES", "z")]) == {"m1": ("2026-09-22", 120.0, "z", False)}
    assert si.match_paid([unpaid("m1", "Anna Smith", 120, "2026-09-21")], [out(120, "2026-09-22", "A SMITHSON", "z")]) == {}


def test_match_paid_core_batch_of_four():
    un = [unpaid(f"m{i}", n, 120, "2026-09-21") for i, n in enumerate(["Ben Fenwick", "Anna Smith", "Anna Smith-Jones", "Tom Jones"])]
    feed = [out(120, "2026-09-22", w, f"q{i}") for i, w in enumerate(["B FENWICK", "ANNA SMITH", "A SMITH-JONES", "T JONES"])]
    got = si.match_paid(un, feed)
    assert {k: v[2] for k, v in got.items()} == {"m0": "q0", "m1": "q1", "m2": "q2", "m3": "q3"}
    got = si.match_paid([un[0], un[1], un[2]], feed)  # Tom not in the store: T JONES must not settle anything
    assert {k: v[2] for k, v in got.items()} == {"m0": "q0", "m1": "q1", "m2": "q2"}


def test_match_paid_short_sender_name_never_auto_matches():
    report = []
    assert si.match_paid([unpaid("m1", "Ben", 100, "2026-09-20")], [out(100, "2026-09-21", "BEN BROWN", "y")], report) == {}
    assert report == ["NAME TOO SHORT m1: check by hand"]
    report = []  # no payment of that amount: nothing to check
    assert si.match_paid([unpaid("m1", "Ben", 100, "2026-09-20")], [out(90, "2026-09-21", "BEN BROWN", "y")], report) == {}
    assert report == []
    row = dict(unpaid("m1", "Ben", 100, "2026-09-20"), bank_fp=lm.bank_fingerprint("123456", "11112222"))
    assert si.match_paid([row], [fp_out(100, "2026-09-21", "BEN BROWN", "y", "123456", "11112222")]) == \
        {"m1": ("2026-09-21", 100.0, "y", True)}


def test_match_paid_skips_items_without_an_id():
    report = []
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19")]
    assert si.match_paid(rows, [out(200, "2026-09-20", "LAURA PENHALLOW"), out(200, "2026-09-21", "LAURA PENHALLOW")], report) == {}
    assert len([x for x in report if "feed item without id skipped" in x]) == 1, report


def test_normalise_name_trade_words_honorifics_commas():
    assert si.normalise_name("Sarah Singer") == "sarah singer" and si.surname("Tom Bass") == "bass"
    assert si.normalise_name("Dr Ben Fenwick") == "ben fenwick"
    assert si.normalise_name("Revd. Ben Fenwick") == "ben fenwick"
    assert si.normalise_name("Ben Fenwick, BA Hons") == "ben fenwick"
    assert si.normalise_name("Ben Fenwick Music Ltd") == "ben fenwick"
    assert si.normalise_name("Anna Smith-Jones") == "anna smith-jones" and si.surname("Smith-Jones, Anna") == "smith-jones"
    assert si.normalise_name("Ben") == "ben"
    assert (si.first_name("Fenwick, Ben"), si.first_name("Dr Ben Fenwick"), si.first_name(""), si.first_name("Laura Penhallow")) == \
        ("Ben", "Ben", "?", "Laura")


def test_extract_account_label_variants():
    for label in ("Acc. No.:", "Acct No", "Acct. Number:", "A/C No.", "Account No.:", "Acc:"):
        assert bank(f"Sort code: 12-34-56\n{label} 11223344") == ("123456", "11223344"), label


def test_ref_never_contains_bank_numbers():
    assert si.extract("Invoice ref: 123456-11223344\nSort code 12-34-56 Account 11223344")["invoice_ref"] == ""
    assert si.extract("Invoice: 12345611223344\nPay to s/c 12-34-56 a/c 11223344")["invoice_ref"] == ""
    assert si.clean_ref("GB-1122334", "", "") == "GB-1122334"


def text_pdf(lines):
    content = "BT /F1 10 Tf 20 700 Td 12 TL " + " ".join(f"({x}) Tj T*" for x in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    data, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(data))
        data += f"{i} 0 obj\n{o}\nendobj\n".encode()
    x = len(data)
    data += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    return data + f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF".encode()


GENUINE_PDF = ["Invoice 2", "Total 100.00 GBP", "Sort code 12-34-56", "Account number 11112222"]
DIFFER = "BANK DETAILS DIFFER between the attachment and the email: ring them before paying"


def test_read_invoice_conflicting_sources_warn():
    body = "Hi, invoice attached. NB my bank has changed, please pay to\nSort code 65-43-21\nAccount number 99998888\nThanks"
    found = si.read_invoice(pdf_eml(text_pdf(GENUINE_PDF), body=body))
    assert found["sources_disagree"] and DIFFER in found["warnings"]
    assert (found["sort_code"], found["account_number"]) == ("123456", "11112222")
    tie = ["Invoice 3", "Total 100.00 GBP", "Old: Sort code 12-34-56 Account 11112222", "New: Sort code 65-43-21 Account 99998888"]
    found = si.read_invoice(pdf_eml(text_pdf(tie), body="see attached\nSort code 12-34-56\nAccount number 11112222"))
    assert found["sources_disagree"] and DIFFER in found["warnings"]
    for body in ("See attached, thanks", "Sort code 12-34-56\nAccount number 11112222"):
        found = si.read_invoice(pdf_eml(text_pdf(GENUINE_PDF), body=body))
        assert not found["sources_disagree"] and DIFFER not in found["warnings"], body
        assert (found["sort_code"], found["account_number"]) == ("123456", "11112222")


def test_scan_conflicting_sources_marks_bank_changed():
    fresh_store()
    body = "NB my bank has changed, please pay to\nSort code 65-43-21\nAccount number 99998888"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_scan(Args(file=pdf_eml(text_pdf(GENUINE_PDF), body=body), message_id="f1", received="2026-09-20",
                         sender_email="ben@example.com", sender_name="Ben Fenwick"), FakeClient())
    row = lm.read_csv(si.STORE)[0]
    assert row["bank_changed"] == "yes" and DIFFER in row["notes"] and DIFFER in buf.getvalue()
    for secret in ("99998888", "11112222", "654321", "123456"):
        assert secret not in buf.getvalue() and secret not in si.STORE.read_text(), secret


GEN = "Invoice {n}\nTotal £100.00\nSort code 12-34-56\nAccount number 11112222"
FRAUD = "Invoice {n}\nTotal £100.00\nSort code 65-43-21\nAccount number 99998888"
INV_FP = "Invoice {n}\nTotal £150.00\nSort code 20-30-40\nAccount number 55667788"
NEW_FP = "Invoice {n}\nTotal £150.00\nSort code 40-50-60\nAccount number 11223344"
ANNA_PAYEE = [{"payeeName": "Anna Price", "accounts": [{"bankIdentifier": "203040", "accountIdentifier": "55667788"}]}]


def scan(body, mid, received, client=None, email="ben@example.com", name="Ben Fenwick"):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_scan(Args(file=eml(body), message_id=mid, received=received, sender_email=email, sender_name=name),
                    client or FakeClient())
    return buf.getvalue()


def paid(client):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_paid(Args(apply=True), client)
    return buf.getvalue()


def rows_by_id():
    return {r["message_id"]: r for r in lm.read_csv(si.STORE)}


def test_unverified_paid_mark_never_trusts_new_details():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    paid(FakeClient(out=[out(100, "2026-08-02", "BEN FENWICK", "p0")]))  # by name: not verified
    assert rows_by_id()["g1"]["paid_verified"] == "no"
    scan(FRAUD.format(n=2), "f1", "2026-09-20")
    assert rows_by_id()["f1"]["bank_changed"] == "yes"
    paid(FakeClient(out=[out(100, "2026-09-22", "BEN FENWICK", "p1")]))
    scan(FRAUD.format(n=3), "f3", "2026-10-20")
    assert rows_by_id()["f3"]["bank_changed"] == "yes" and "BANK DETAILS CHANGED" in rows_by_id()["f3"]["notes"]


def test_verified_payment_is_trust_and_a_payment_to_other_details_settles_nothing():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    out1 = paid(FakeClient(out=[fp_out(100, "2026-08-02", "BW MUSIC", "p0", "123456", "11112222")]))
    assert "NEWLY PAID g1" in out1 and rows_by_id()["g1"]["paid_verified"] == "yes"
    assert "NEW BANK DETAILS" not in scan(GEN.format(n=2), "g2", "2026-08-20")
    warned = scan(FRAUD.format(n=3), "f1", "2026-09-20")
    assert "BANK DETAILS CHANGED" in warned and "was ••••2222" in warned
    paid(FakeClient(out=[fp_out(100, "2026-09-22", "BEN FENWICK", "p1", "123456", "11112222")]))  # pays g2, not f1
    r = rows_by_id()
    assert r["g2"]["paid_ref"] == "p1" and r["f1"]["paid_on"] == ""


def test_confirm_command():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_confirm(Args(message_id="g1"))
    assert buf.getvalue().splitlines()[0] == "g1: bank details confirmed"
    assert rows_by_id()["g1"]["bank_confirmed"] == "yes"
    assert "NEW BANK DETAILS" not in scan(GEN.format(n=2), "g2", "2026-08-20")
    assert "was ••••2222" in scan(FRAUD.format(n=3), "f1", "2026-09-20")
    try:
        si.cmd_confirm(Args(message_id="nope"))
        raise AssertionError("confirmed a missing invoice")
    except SystemExit:
        pass


def test_payee_name_check_needs_the_first_name():
    payees = [{"payeeName": "Tom Fenwick", "accounts": [{"bankIdentifier": "123456", "accountIdentifier": "99990000"}]}]
    fps = lm.payee_fingerprints(payees)
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", [], fps, ["Tom Fenwick"])
    assert a["payee"] == si.NEW_PAYEE and a["bank_changed"] == "no"
    fresh_store()
    payees[0]["payeeName"] = "B Fenwick"
    warned = scan("Invoice 1\nTotal £100.00\nSort code 12-34-56\nAccount number 12345678", "m1", "2026-09-20",
                  client=FakeClient(payees=payees))
    assert "BANK DETAILS CHANGED" in warned and "was ••••0000" in warned and rows_by_id()["m1"]["bank_changed"] == "yes"


def test_legacy_filter_is_per_singer():
    fresh_store()
    base = {c: "" for c in si.COLUMNS}
    lm.write_csv(si.STORE, [dict(base, message_id="L", received="2026-09-01", singer_name="Ben Fenwick", amount_gbp="100.00",
                                 payee=si.NEW_PAYEE, bank_changed="no", paid_on="2026-09-10", paid_amount="100.00"),
                            dict(base, message_id="A", received="2026-09-01", singer_name="Anna Smith", amount_gbp="100.00",
                                 payee=si.NEW_PAYEE, bank_changed="no")], si.COLUMNS)
    got = paid(FakeClient(out=[out(100, "2026-09-10", "BEN FENWICK", "pb"), out(100, "2026-09-10", "ANNA SMITH", "pa")]))
    assert "NEWLY PAID A" in got and rows_by_id()["A"]["paid_ref"] == "pa"


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
