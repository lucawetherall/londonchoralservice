#!/usr/bin/env python3
"""Tests for scripts/bookings/singer_invoices.py. Stdlib only. Uses a temp private dir."""
import argparse, base64, contextlib, datetime, io, os, sys, tempfile, zipfile

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
    rows = [unpaid("m1", "Laura Pembury", 200, "2026-09-19")]
    assert si.match_paid(rows, [out(200, "2026-09-19", "LAURA PEMBURY", "p1")]) == {"m1": ("2026-09-19", 200.0, "p1", False)}


def test_match_paid_uses_payee_name():
    rows = [unpaid("m1", "Tilly Thorne", 160, "2026-09-01", payee="existing: T T Thorne")]
    assert si.match_paid(rows, [out(160, "2026-09-02", "T T THORNE", "p1")]) == {"m1": ("2026-09-02", 160.0, "p1", False)}


def test_match_paid_rejects_wrong_amount_early_date_and_double_use():
    rows = [unpaid("m1", "Laura Pembury", 200, "2026-09-19"), unpaid("m2", "Laura Pembury", 200, "2026-09-20")]
    assert si.match_paid(rows, [out(150, "2026-09-21", "LAURA PEMBURY", "p0")]) == {}
    assert si.match_paid(rows[:1], [out(200, "2026-09-10", "LAURA PEMBURY", "p0")]) == {}
    assert si.match_paid(rows, [out(200, "2026-09-21", "LAURA PEMBURY", "p1")]) == {"m1": ("2026-09-21", 200.0, "p1", False)}


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
    rows = [unpaid("m1", "Laura Pembury", 200, "2026-09-19")]
    report = []
    assert si.match_paid(rows, [out(200, "2026-09-10", "LAURA PEMBURY", "p1")], report) == {}
    assert report == ["POSSIBLY ALREADY PAID m1: Laura £200.00 on 2026-09-10 (before the invoice arrived): check by hand"]
    report = []
    assert si.match_paid(rows, [out(200, "2026-09-01", "LAURA PEMBURY", "p1")], report) == {} and report == []


def test_match_paid_feed_order():
    rows = [unpaid("m1", "Laura Pembury", 200, "2026-09-19"), unpaid("m2", "Laura Pembury", 200, "2026-09-24")]
    feed = [out(200, "2026-09-21", "LAURA PEMBURY", "p1"), out(200, "2026-09-25", "LAURA PEMBURY", "p2")]
    want = {"m1": ("2026-09-21", 200.0, "p1", False), "m2": ("2026-09-25", 200.0, "p2", False)}
    assert si.match_paid(rows, feed) == want
    assert si.match_paid(rows, feed[::-1]) == want


def test_match_paid_uses_london_date():
    rows = [unpaid("m1", "Laura Pembury", 200, "2026-09-26")]
    item = out(200, "2026-09-25", "LAURA PEMBURY", "p1", at="T23:30:00Z")
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
                "<p>Invoice 107</p><p>Total: &pound;150.00</p><p>Sort code: 12&#8209;34&#8209;56</p>"
                "<p>Account number: 8765&nbsp;4321</p>")
    found = si.read_invoice(path)
    assert (found["amount"], found["invoice_ref"], found["sort_code"], found["account_number"]) == (150.0, "107", "123456", "87654321")
    found = si.read_invoice(eml("Invoice 555\nThanks, see you Sunday"))
    assert found["invoice_ref"] == "555" and found["amount"] == 0.0


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
    assert report == ["PAYMENT TO ANOTHER SINGER'S ACCOUNT £150.00 on 2026-09-02 ••••0000 not matched to bella1 (Bella): "
                      "check by hand"], report  # round 5: the blocked payment is reported, once
    # without the guard (no history passed) the initial+surname alone would have matched Bella
    assert si.match_paid([bella], [item]) == {"bella1": ("2026-09-02", 150.0, "x9", False)}


def test_match_paid_blocks_name_match_for_a_disagreeing_starling_payee():
    fp = lm.bank_fingerprint("112233", "99990000")
    bella = unpaid("bella1", "Bella Fenwick", 150, "2026-09-01")
    item = fp_out(150, "2026-09-02", "B FENWICK", "x9", "112233", "99990000")
    assert si.match_paid([bella], [item], history=[bella], payee_fps={fp: "Ines Calloway"}) == {}
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
    rows = [unpaid("m1", "Laura Pembury", 200, "2026-09-19")]
    assert si.match_paid(rows, [out(200, "2026-09-20", "LAURA PEMBURY"), out(200, "2026-09-21", "LAURA PEMBURY")], report) == {}
    assert len([x for x in report if "feed item without id skipped" in x]) == 1, report


def test_normalise_name_trade_words_honorifics_commas():
    assert si.normalise_name("Sarah Singer") == "sarah singer" and si.surname("Tom Bass") == "bass"
    assert si.normalise_name("Dr Ben Fenwick") == "ben fenwick"
    assert si.normalise_name("Revd. Ben Fenwick") == "ben fenwick"
    assert si.normalise_name("Ben Fenwick, BA Hons") == "ben fenwick"
    assert si.normalise_name("Ben Fenwick Music Ltd") == "ben fenwick"
    assert si.normalise_name("Anna Smith-Jones") == "anna smith-jones" and si.surname("Smith-Jones, Anna") == "smith-jones"
    assert si.normalise_name("Ben") == "ben"
    assert (si.first_name("Fenwick, Ben"), si.first_name("Dr Ben Fenwick"), si.first_name(""), si.first_name("Laura Pembury")) == \
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


# --- round 5: hand-settled invoices, guard-blocked payments, "Paid!" only on verified matches ----

def settle(mid, day):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_settled(Args(message_id=mid, date=day))
    return buf.getvalue()


def test_settled_command():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    assert settle("g1", "2026-08-03").splitlines() == ["g1: settled by hand"]
    r = rows_by_id()["g1"]
    assert (r["paid_on"], r["paid_amount"], r["paid_verified"], r["bank_confirmed"], r["paid_ref"]) == \
        ("2026-08-03", "100.00", "no", "", ""), r
    assert r["notes"].endswith("settled by hand"), r["notes"]
    try:  # a paid invoice is never settled over
        settle("g1", "2026-08-09")
        raise AssertionError("settled a paid invoice again")
    except SystemExit:
        assert rows_by_id()["g1"]["paid_on"] == "2026-08-03"
    assert si.summary(lm.read_csv(si.STORE), datetime.date(2026, 9, 28))["unpaid"] == 0
    # a hand settlement is never trust: the same details on the next invoice are still unverified
    assert "NOT YET VERIFIED" in scan(GEN.format(n=2), "g2", "2026-08-20")
    assert "BANK DETAILS CHANGED" in scan(FRAUD.format(n=4), "f1", "2026-09-20")
    # the payment itself, once in the feed, is recognised as g1's and settles or flags nothing else
    got = paid(FakeClient(out=[out(100, "2026-08-03", "BEN FENWICK", "late")]))
    assert "NEWLY PAID" not in got and "POSSIBLY ALREADY PAID" not in got, got


def test_settled_command_errors():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    for mid, day in (("nope", "2026-08-03"), ("g1", "3 Aug")):
        before = si.STORE.read_text()
        try:
            settle(mid, day)
            raise AssertionError(f"settled {mid} {day}")
        except (SystemExit, argparse.ArgumentTypeError):
            pass
        assert si.STORE.read_text() == before


def test_settled_refuses_a_date_after_today():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    before = si.STORE.read_text()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    try:
        settle("g1", tomorrow)
        raise AssertionError(f"settled g1 on {tomorrow}")
    except SystemExit as e:
        assert "after today" in str(e.code), e.code
    assert si.STORE.read_text() == before
    assert settle("g1", datetime.date.today().isoformat()).strip() == "g1: settled by hand"


def test_settled_cli():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    saved = sys.argv
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sys.argv = ["singer_invoices.py", "settled", "g1", "2026-08-04"]
            si.main()
        assert buf.getvalue().strip() == "g1: settled by hand" and rows_by_id()["g1"]["paid_on"] == "2026-08-04"
        sys.argv = ["singer_invoices.py", "settled", "zz", "2026-08-04"]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                si.main()
            raise AssertionError("settled an unknown invoice")
        except SystemExit as e:
            assert e.code and "zz" in str(e.code), e.code
    finally:
        sys.argv = saved


def test_a_payment_blocked_by_the_guard_is_reported_once():
    fp = lm.bank_fingerprint("112233", "99990000")
    bella = unpaid("bella1", "Bella Fenwick", 150, "2026-09-01")
    bella2 = unpaid("bella2", "Bella Fenwick", 150, "2026-09-05")
    item = fp_out(150, "2026-09-06", "B FENWICK", "x9", "112233", "99990000")
    report = []
    assert si.match_paid([bella, bella2], [item], report, history=[bella, bella2], payee_fps={fp: "Ines Calloway"}) == {}
    assert report == ["PAYMENT TO ANOTHER SINGER'S ACCOUNT £150.00 on 2026-09-06 ••••0000 not matched to bella1 (Bella): "
                      "check by hand"], report
    # a payment that settles another invoice by its own bank details is not reported
    ines = fp_unpaid("p1", "Ines Calloway", 150, "2026-09-02", sc="112233", acc="99990000")
    report = []
    assert si.match_paid([bella, ines], [item], report, history=[bella, ines], payee_fps={fp: "Ines Calloway"}) == \
        {"p1": ("2026-09-06", 150.0, "x9", True)}
    assert report == [], report


def test_newly_paid_by_name_says_check_before_thanking():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    scan(GEN.format(n=2), "g2", "2026-08-02")
    got = paid(FakeClient(out=[out(100, "2026-08-03", "BEN FENWICK", "p0"),
                               fp_out(100, "2026-08-04", "BW MUSIC", "p1", "123456", "11112222")]))
    lines = [x for x in got.splitlines() if x.startswith("NEWLY PAID")]
    assert lines == ["NEWLY PAID g1: Ben £100.00 on 2026-08-03 (matched by name, check before thanking)",
                     "NEWLY PAID g2: Ben £100.00 on 2026-08-04 (bank details match)"], lines


# --- round 6: what the first live backfill showed: .docx, fetching by id, rescan, refs --------------

def test_extract_ref_backfill_shapes():
    ref = lambda t: si.extract(t)["invoice_ref"]  # noqa: E731
    assert ref("Invoice 21st September\nTotal £100") == ""
    assert ref("Invoice No. 018\nTotal £100") == "018"
    assert ref("Recording Session 24/09 Invoice\nTotal £100") == ""
    assert ref("Invoice INV-0107\nTotal £100") == "INV-0107" and ref("Ref INV-0107") == "INV-0107"
    assert ref("Invoice 1020\nTotal £100") == "1020"
    for text in ("Invoice - 27th Sept", "Invoice 21/09", "Invoice 2026-09-21", "Invoice 21.9.26", "Invoice 12",
                 "Invoice for 21/09/2026", "INVOICE\n\n122 Wedding", "Invoice date 21/09/2026"):
        assert ref(text) == "", (text, ref(text))
    assert ref("Invoice Number:\n122\nTotal £100") == "122"  # labelled, the value on the next line
    assert ref("Invoice #1020") == "1020" and ref("Inv No: 123") == "123"
    assert ref("Invoice 21st September\nInvoice No: 1020") == "1020"  # the date is skipped, the label found
    assert ref("INVOICE\n\nLW-042") == "LW-042" and ref("INVOICE\n20260309-001") == "20260309-001"
    # live shapes: a short ref counts only after an explicit No / Number / # / Ref label
    assert ref("\tAlma Consort Ltd 20 Wenlock Road, London Invoice #37\t\t") == "37"
    assert ref("Anna Price Invoice\t\t\t21.9.26\nInvoice number: 1") == "1"
    assert ref("Invoice No: 21st") == "" and ref("Invoice #21/09") == ""


def test_extract_bare_total_in_a_gbp_column():
    bare = "Anna Price Invoice\t\t21.9.26\nInvoice number: 1\nDate\tDescription\tAmount (GBP)\n" \
                "21.9.26\tFuneral\t100\nTOTAL\t\t100"
    e = si.extract(bare)
    assert (e["amount"], e["invoice_ref"]) == (100.0, "1"), e
    assert si.extract("Date\tDescription\tAmount (£)\nTotal 1,250\n")["amount"] == 1250.0
    assert si.extract("Rehearsal and service\nTOTAL\t\t100")["amount"] == 0.0  # no currency named anywhere
    assert si.extract("Amount (GBP)\nTotal hours 3\nTotal: 25/09/2026")["amount"] == 0.0
    assert si.extract("Amount (GBP)\nTotal 3 services")["amount"] == 0.0  # the number must end the line
    assert si.extract("Fee £80\nTravel £20\nTOTAL 100")["amount"] == 100.0  # a labelled total beats the largest £


def make_docx(paragraphs=(), tables=(), footer=None, raw_body=""):
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    p = lambda t: f"<w:p><w:r><w:t xml:space=\"preserve\">{t}</w:t></w:r></w:p>"  # noqa: E731
    tbl = lambda rows: "<w:tbl><w:tblPr/>" + "".join(  # noqa: E731
        "<w:tr>" + "".join(f"<w:tc><w:tcPr/>{''.join(p(x) for x in c.split('|'))}</w:tc>" for c in r) + "</w:tr>"
        for r in rows) + "</w:tbl>"
    body = "".join(p(x) for x in paragraphs) + "".join(tbl(t) for t in tables) + raw_body
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {ns}><w:body>{body}<w:sectPr/></w:body></w:document>')
        if footer:
            z.writestr("word/footer1.xml", f'<?xml version="1.0"?><w:ftr {ns}>{p(footer)}</w:ftr>')
    return buf.getvalue()


DOCX_INVOICE = dict(
    paragraphs=["Marnie Example, soprano", "Invoice No. 018", "Date: 21st September 2026"],
    tables=[[("Description", "Amount"), ("Funeral, St Mary's, 21/09", "£150.00"), ("Total", "£150.00")],
            [("Sort code", "12-34-56"), ("Account number", "12345678")]],
    raw_body='<w:p><w:r><w:t>Pay</w:t></w:r><w:r><w:tab/><w:t>by transfer</w:t></w:r></w:p>')


def att_eml(data, fname, ctype, body="Invoice attached, thanks!"):
    b = base64.b64encode(data).decode()
    path = os.path.join(TMP, "att.eml")
    with open(path, "w") as f:
        f.write("From: Marnie <marnie@example.com>\nSubject: Invoice\nMIME-Version: 1.0\n"
                "Content-Type: multipart/mixed; boundary=XX\n\n"
                f"--XX\nContent-Type: text/plain\n\n{body}\n--XX\nContent-Type: {ctype}\n"
                f"Content-Disposition: attachment; filename=\"{fname}\"\nContent-Transfer-Encoding: base64\n\n{b}\n--XX--\n")
    return path


def test_docx_text_keeps_table_rows_on_one_line():
    text = si.docx_text(make_docx(**DOCX_INVOICE, footer="Thank you"))
    lines = text.splitlines()
    assert "Total\t£150.00" in lines and "Sort code\t12-34-56" in lines and "Invoice No. 018" in lines, lines
    assert "Pay\tby transfer" in lines and lines[-1] == "Thank you", lines
    two = si.docx_text(make_docx(tables=[[("Bank details|Sort code 12-34-56", "Account 12345678")]]))
    assert two == "Bank details Sort code 12-34-56\tAccount 12345678", two
    assert si.docx_text(b"not a zip") == "" and si.docx_text(None) == ""


def test_read_invoice_from_docx_attachment():
    found = si.read_invoice(att_eml(make_docx(**DOCX_INVOICE), "Marnie invoice.docx", si.DOCX_TYPE))
    assert (found["amount"], found["invoice_ref"], found["sort_code"], found["account_number"]) == \
        (150.0, "018", "123456", "12345678"), found
    assert found["warnings"] == [], found["warnings"]
    # no filename, but the Word content type
    path = att_eml(make_docx(**DOCX_INVOICE), "", si.DOCX_TYPE)
    assert si.read_invoice(path)["amount"] == 150.0


def test_doc_and_damaged_docx_warn():
    found = si.read_invoice(att_eml(b"\xd0\xcf\x11\xe0 old word file", "Invoice.doc", "application/msword"))
    assert "could not read Invoice.doc (.doc): check by hand" in found["warnings"], found["warnings"]
    assert "amount not found: check the invoice by hand" in found["warnings"]
    found = si.read_invoice(att_eml(b"PK garbage", "Invoice.docx", si.DOCX_TYPE))
    assert "could not read Invoice.docx (encrypted or damaged): check it by hand" in found["warnings"], found["warnings"]


def raw_mime(body):
    return f"From: Ben Fenwick <ben@example.com>\nSubject: Invoice\nContent-Type: text/plain; charset=utf-8\n\n{body}"


@contextlib.contextmanager
def fake_fetch(texts, calls=None):
    """Stand in for the MCP fetch: message id -> raw MIME text (or an exception to raise)."""
    saved = si.fetch_raw

    def fetch(mid):
        (calls if calls is not None else []).append(mid)
        got = texts[mid]
        if isinstance(got, Exception):
            raise got
        return got
    si.fetch_raw = fetch
    try:
        yield
    finally:
        si.fetch_raw = saved


def run_main(argv):
    saved = (lm.keychain_token, sys.argv)
    lm.keychain_token = lambda: None  # no Starling in tests
    buf = io.StringIO()
    try:
        sys.argv = ["singer_invoices.py", *argv]
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            si.main()
    finally:
        lm.keychain_token, sys.argv = saved
    return buf.getvalue()


SCAN_ARGS = ["--message-id", "177", "--received", "2026-09-25", "--sender-email", "ben@example.com", "--sender-name", "Ben Fenwick"]


def test_scan_fetch_reads_the_fetched_message():
    fresh_store()
    calls = []
    with fake_fetch({"177": raw_mime(GEN.format(n=101))}, calls):
        got = run_main(["scan", "--fetch", *SCAN_ARGS])
        again = run_main(["scan", "--fetch", *SCAN_ARGS])
    assert again.splitlines()[0] == "already recorded: 177", again
    assert calls == ["177"], calls  # a recorded invoice isn't fetched again
    # a crashed run resumes: the stored line and the bill lines again
    assert again.splitlines()[1:] == [l for l in got.splitlines()], (got, again)
    assert got.splitlines()[0] == "Ben: £100.00 (ref 101) · payee unknown (no Starling token) · bank ••••2222", got
    row = rows_by_id()["177"]
    assert (row["amount_gbp"], row["invoice_ref"], row["bank_last4"]) == ("100.00", "101", "2222")
    assert "11112222" not in got and "11112222" not in si.STORE.read_text()


def test_scan_needs_either_fetch_or_a_file():
    fresh_store()
    for argv in (["scan", *SCAN_ARGS], ["scan", eml(GEN.format(n=1)), "--fetch", *SCAN_ARGS],
                 ["rescan", "177"], ["rescan", "177", eml(GEN.format(n=1)), "--fetch"]):
        try:
            run_main(argv)
            raise AssertionError(f"accepted {argv}")
        except SystemExit as e:
            assert e.code == 2, (argv, e.code)
    assert not si.STORE.exists()


def test_scan_fetch_failure_names_the_server_only():
    fresh_store()
    import lcs_mcp
    with fake_fetch({"177": lcs_mcp.McpError("zoho-mail: timed out after 90s")}):
        try:
            run_main(["scan", "--fetch", *SCAN_ARGS])
            raise AssertionError("no error")
        except SystemExit as e:
            assert e.code == "could not fetch 177: zoho-mail: timed out after 90s; scan skipped", e.code
    assert not si.STORE.exists()


def rescan(mid, file=None, fetch=False, client=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        si.cmd_rescan(Args(message_id=mid, file=file, fetch=fetch), client or FakeClient())
    return buf.getvalue()


def test_rescan_fills_in_an_unread_invoice():
    fresh_store()
    first = scan("Invoice attached, thanks!", "h1", "2026-09-21", email="marnie@example.com", name="Marnie Example")
    assert first.startswith("Marnie: £0.00 (ref ?)") and "amount not found" in first
    got = rescan("h1", file=att_eml(make_docx(**DOCX_INVOICE), "invoice.docx", si.DOCX_TYPE))
    assert got.splitlines()[0] == ("Marnie: £150.00 (ref 018) · payee NEW: add as a payee in the Starling app "
                                   "· bank ••••5678"), got
    assert f"{si.NEW_DETAILS}, then run singer_invoices.py confirm h1" in got
    rows = lm.read_csv(si.STORE)
    assert len(rows) == 1
    r = rows[0]
    assert (r["amount_gbp"], r["invoice_ref"], r["bank_last4"], r["received"], r["singer_email"]) == \
        ("150.00", "018", "5678", "2026-09-21", "marnie@example.com"), r
    assert "amount not found" not in r["notes"] and f"rescanned {datetime.date.today()}" in r["notes"], r["notes"]
    assert "12345678" not in got and "12345678" not in si.STORE.read_text()


def test_rescan_with_fetch():
    fresh_store()
    scan("Invoice attached", "177", "2026-09-25")
    with fake_fetch({"177": raw_mime(GEN.format(n=202))}):
        got = run_main(["rescan", "177", "--fetch"])
    assert got.splitlines()[0] == "Ben: £100.00 (ref 202) · payee unknown (no Starling token) · bank ••••2222", got


def test_rescan_refuses_paid_and_unknown_invoices():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    settle("g1", "2026-08-03")
    before = si.STORE.read_text()
    calls = []
    with fake_fetch({"g1": raw_mime(GEN.format(n=9))}, calls):
        for mid, want in (("g1", "already paid on 2026-08-03"), ("nope", "no invoice nope")):
            try:
                rescan(mid, fetch=True)
                raise AssertionError(f"rescanned {mid}")
            except SystemExit as e:
                assert want in str(e.code), e.code
    assert calls == [] and si.STORE.read_text() == before


def test_rescan_keeps_a_confirmation_only_for_the_same_details():
    fresh_store()
    scan(GEN.format(n=1), "g1", "2026-08-01")
    with contextlib.redirect_stdout(io.StringIO()):
        si.cmd_confirm(Args(message_id="g1"))
    got = rescan("g1", file=eml(GEN.format(n=1)))
    r = rows_by_id()["g1"]
    assert r["bank_confirmed"] == "yes" and r["bank_changed"] == "no" and "NEW BANK DETAILS" not in got, got
    assert "bank details confirmed by phone" in r["notes"], r["notes"]
    got = rescan("g1", file=eml(FRAUD.format(n=1)))
    r = rows_by_id()["g1"]
    assert "BANK DETAILS CHANGED" in got and "was ••••2222, now ••••8888" in got, got
    assert r["bank_confirmed"] == "" and r["bank_changed"] == "yes" and "confirmed by phone" not in r["notes"], r


def test_rescan_flags_a_newer_invoice_with_other_details():
    fresh_store()
    scan("Invoice attached", "old", "2026-09-01")
    scan(FRAUD.format(n=2), "new", "2026-09-20")
    got = rescan("old", file=eml(GEN.format(n=1)))
    assert "   ! new: BANK DETAILS CHANGED: ••••8888 differs from an older invoice (••••2222)" in got, got
    assert rows_by_id()["new"]["bank_changed"] == "yes"


# --- review of PR 152: bare totals, .docx limits, rescan never loses data, names ---------------------

def test_bare_total_must_agree_with_the_pound_figures():
    amount = lambda t: si.extract(t)["amount"]  # noqa: E731
    assert amount("Invoice No: 55\nService\tHours\tRate\nFuneral\t3\t£50\nTotal 3\n£150") == 150.0  # hours, not money
    assert amount("Invoice No: 55\nFee £120\nTravel £30\nTOTAL 2\n£150.00") == 150.0
    assert amount("Invoice No 77\nFee £200\nTotal due 30") == 200.0  # "due in 30 days"
    assert amount("Invoice No 77\nFee £200\nTOTAL\t07700900123") == 200.0  # a phone number: over six digits
    assert amount("Invoice No 77\nFee £200\nTotal 2026") == 200.0  # a year
    assert amount("Invoice No 77\nAmount (£)\nTotal: 1,500") == 1500.0  # no £ figure to check it against
    assert amount("Invoice No 77\n£150.50 fee\nTotal 150.5") == 150.5
    assert amount("Invoice No 77\nFee £100\nSubtotal 100\nTotal 120") == 100.0
    assert amount("Invoice No 77\nMileage claimed\nTotal 120\nat 45p per mile = £54.00") == 54.0
    # a bare total that is one of the £ figures, or their sum, stands
    assert amount("Fee £80\nTravel £20\nTOTAL 100") == 100.0 and amount("Fee £80\nTravel £20\nTOTAL\t80") == 80.0
    # one singer's layout: GBP only in the column heading, no £ figures at all
    assert amount("Anna Price Invoice\t\t21.9.26\nInvoice number: 1\nDate\tDescription\tAmount (GBP)\n"
                  "21.9.26\tFuneral\t100\nTOTAL\t\t100") == 100.0
    assert amount("Amount (GBP)\nTOTAL 1234567") == 0.0  # seven digits: never a bare total
    # a known limit: a quantity total in a GBP table with no £ figure reads like one singer's layout
    assert amount("Invoice 1020\nItem Qty Amount (GBP)\nTotal 4\n") == 4.0


def test_extract_ref_probe_shapes():
    ref = lambda t: si.extract(t)["invoice_ref"]  # noqa: E731
    assert ref("Invoice #1\nTotal £100") == "1"
    assert ref("Invoice No:\n12345678\nSort code 12-34-56 Account 12345678\nTotal £1.00") == ""
    assert ref("Invoice No:\n1234567\nSort code 12-34-56 Account 1234567\nTotal £1.00") == ""
    assert ref("Invoice No: 5678\nSort code 12-34-56\nAccount number 12345678\nTotal £1.00") == "5678"
    assert ref("Invoice No:\n123456\nSort code 12-34-56\nAccount 11112222\nAccount 33334444\nTotal £1.00") == ""
    # bank details too ambiguous to keep, but the account number still never becomes the ref
    assert ref("Invoice number:\n1234567\nSort code 12-34-56 Sort code 65-43-21\nAccount 1234567\nTotal £1.00") == ""
    assert ref("Invoice No:\n07700900123\nTotal £1.00") == "07700900123"
    assert ref("Inv. No. 12\nTotal £1.00") == "12"
    assert ref("Invoice No.\n21/09/2026\nTotal £1") == ""
    assert ref("Invoice ref: AC12345678\nSort code 12-34-56 Acc no 12345678\n£1.00") == ""


@contextlib.contextmanager
def patched(obj, **values):
    saved = {k: getattr(obj, k) for k in values}
    for k, v in values.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(obj, k, v)


def docx_parts(parts):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, xml in parts.items():
            z.writestr(name, xml)
    return buf.getvalue()


NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def doc_xml(*paras, pad=0):
    ps = "".join(f"<w:p><w:r><w:t>{t}</w:t></w:r></w:p>" for t in paras)
    return f'<?xml version="1.0"?><w:document {NS}><w:body>{ps}<!--{"x" * pad}--></w:body></w:document>'


def ftr_xml(text):
    return f'<?xml version="1.0"?><w:ftr {NS}><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:ftr>'


TOO_LARGE = "could not read big.docx (too large or malformed): check it by hand"


def test_docx_part_over_the_size_limit_is_skipped():
    data = docx_parts({"word/document.xml": doc_xml("Invoice No. 5", pad=5000), "word/footer1.xml": ftr_xml("Total £150.00")})
    with patched(si, DOCX_MAX_PART=2000):
        text, problem = si.docx_read(data)
        assert text == "Total £150.00" and problem, (text, problem)
        found = si.read_invoice(att_eml(data, "big.docx", si.DOCX_TYPE))
    assert found["amount"] == 150.0 and TOO_LARGE in found["warnings"], found
    assert not any("encrypted or damaged" in w for w in found["warnings"]), found["warnings"]
    assert si.DOCX_MAX_PART == 5 << 20 and si.DOCX_MAX_TOTAL == 15 << 20
    assert si.DOCX_MAX_EXTRA_PARTS == 10 and si.DOCX_MAX_TEXT == 1 << 20 and si.DOCX_MAX_DEPTH == 200


def test_docx_total_read_is_capped():
    data = docx_parts({"word/document.xml": doc_xml("Invoice No. 5", pad=1500), "word/footer1.xml": ftr_xml("x" * 1500)})
    with patched(si, DOCX_MAX_PART=2500, DOCX_MAX_TOTAL=3000):
        text, problem = si.docx_read(data)
    assert text == "Invoice No. 5" and problem, (text, problem)
    with patched(si, DOCX_MAX_PART=2500, DOCX_MAX_TOTAL=5000):
        assert si.docx_read(data)[1] is False


def test_docx_header_and_footer_parts_are_capped():
    parts = {"word/document.xml": doc_xml("Body")}
    parts.update({f"word/footer{i}.xml": ftr_xml(f"F{i}") for i in range(1, 13)})
    text, problem = si.docx_read(docx_parts(parts))
    lines = text.splitlines()
    assert problem and lines == ["Body"] + [f"F{i}" for i in range(1, 11)], lines


def test_docx_text_is_truncated():
    data = docx_parts({"word/document.xml": doc_xml("Total £150.00", "y" * 500)})
    with patched(si, DOCX_MAX_TEXT=50):
        text, problem = si.docx_read(data)
    assert len(text) == 50 and text.startswith("Total £150.00") and problem, (len(text), problem)


def test_deep_docx_is_refused_not_crashed():
    deep = f'<?xml version="1.0"?><w:document {NS}><w:body>' + "<w:sdt>" * 300 + \
        "<w:p><w:r><w:t>Total £1.00</w:t></w:r></w:p>" + "</w:sdt>" * 300 + "</w:body></w:document>"
    data = docx_parts({"word/document.xml": deep, "word/footer1.xml": ftr_xml("Invoice No. 9")})
    text, problem = si.docx_read(data)
    assert problem and text == "Invoice No. 9", (text, problem)
    found = si.read_invoice(att_eml(data, "big.docx", si.DOCX_TYPE))
    assert TOO_LARGE in found["warnings"], found["warnings"]
    # past the depth cap Python's own recursion limit would hit first: RecursionError is caught too
    deeper = deep.replace("<w:sdt>" * 300, "<w:sdt>" * 3000).replace("</w:sdt>" * 300, "</w:sdt>" * 3000)
    with patched(si, DOCX_MAX_DEPTH=10 ** 6):
        text, problem = si.docx_read(docx_parts({"word/document.xml": deeper}))
    assert (text, problem) == ("", True)


def test_unknown_charset_falls_back():
    raw = "From: a@b.com\nSubject: Invoice\nContent-Type: text/plain; charset=x-no-such-charset\n\nInvoice No 5 Total £10.00"
    found = si.read_invoice(raw=raw)
    assert found["amount"] == 10.0 and found["invoice_ref"] == "5", found


GOOD = "Invoice No: 101\nTotal £100.00\nSort code 11-22-33\nAccount number 11112222"


def confirmed_row(mid="177"):
    fresh_store()
    with fake_fetch({mid: raw_mime(GOOD)}):
        run_main(["scan", "--fetch", *SCAN_ARGS])
    with contextlib.redirect_stdout(io.StringIO()):
        si.cmd_confirm(Args(message_id=mid))
    return si.STORE.read_text()


def test_rescan_without_bank_details_changes_nothing():
    before = confirmed_row()
    with fake_fetch({"177": raw_mime("Invoice attached, thanks!")}):
        got = run_main(["rescan", "177", "--fetch"])
    assert got.strip() == "no bank details found on rescan; nothing changed", got
    assert si.STORE.read_text() == before


def test_rescan_keeps_the_old_amount_and_ref():
    confirmed_row()
    with fake_fetch({"177": raw_mime("Sort code 11-22-33\nAccount number 11112222\nThanks")}):
        got = run_main(["rescan", "177", "--fetch"])
    r = rows_by_id()["177"]
    assert (r["amount_gbp"], r["invoice_ref"], r["bank_confirmed"]) == ("100.00", "101", "yes"), r
    assert "bank details confirmed by phone" in r["notes"] and "amount not found" not in r["notes"], r["notes"]
    assert got.splitlines()[0].startswith("Ben: £100.00 (ref 101)"), got
    assert "11112222" not in got and "112233" not in got


def test_rescan_prints_each_change_masked():
    confirmed_row()
    with fake_fetch({"177": raw_mime("Invoice No: 102\nTotal £120.00\nSort code 65-43-21\nAccount number 99998888")}):
        got = run_main(["rescan", "177", "--fetch"])
    lines = got.splitlines()
    for want in ("   amount: £100.00 → £120.00", "   ref: 101 → 102", "   bank details: ••••2222 → ••••8888",
                 "   bank changed: no → yes", "   bank confirmed: yes → no"):
        assert want in lines, (want, lines)
    assert "99998888" not in got and "11112222" not in got and "654321" not in got
    same = "Invoice No: 102\nTotal £120.00\nSort code 65-43-21\nAccount number 99998888"
    with fake_fetch({"177": raw_mime(same)}):
        got = run_main(["rescan", "177", "--fetch"])
    assert "   nothing changed" in got.splitlines(), got  # and the change flagged before still stands
    r = rows_by_id()["177"]
    assert r["bank_changed"] == "yes" and "BANK DETAILS CHANGED since their last invoice (was ••••2222" in r["notes"], r
    four = "Invoice No: 102\nTotal £120.00\nSort code 12-12-12\nAccount number 99998888"
    with fake_fetch({"177": raw_mime(four)}):
        got = run_main(["rescan", "177", "--fetch"])
    assert "   bank details: ••••8888 → ••••8888 (different sort code or account)" in got.splitlines(), got


def test_scan_and_rescan_lock_the_store_after_the_fetch():
    fresh_store()
    events = []

    @contextlib.contextmanager
    def lock(path):
        events.append(("lock", str(path)))
        yield
        events.append(("unlock", str(path)))

    def fetch(mid):
        events.append(("fetch", mid))
        return raw_mime(GOOD)
    with patched(lm, ledger_lock=lock), patched(si, fetch_raw=fetch):
        run_main(["scan", "--fetch", *SCAN_ARGS])
        run_main(["rescan", "177", "--fetch"])
    store = str(si.STORE)
    assert events == [("fetch", "177"), ("lock", store), ("unlock", store)] * 2, events


def test_probe_rescan_row_survives_an_unreadable_fetch():
    confirmed_row()
    keep = {k: rows_by_id()["177"][k] for k in si.COLUMNS}
    for bad in ("Invoice attached, thanks!", "Invoice No: 999\nTotal £5.00"):
        with fake_fetch({"177": raw_mime(bad)}):
            assert run_main(["rescan", "177", "--fetch"]).strip() == "no bank details found on rescan; nothing changed"
        assert {k: rows_by_id()["177"][k] for k in si.COLUMNS} == keep


def test_names_equivalent_pairs():
    yes = [("Benjamin Fenwick", "Ben Harrow-Fenwick"), ("Crispin Fairleighbrook", "Crispin Fairleigh Brook"),
           ("Jessie A Wendover", "Jess Wendover"), ("Kate Brown", "Catherine Brown"), ("Tom Jones", "THOMAS JONES"),
           ("B FENWICK", "Ben Fenwick"), ("FENWICK BEN", "Benjamin Fenwick"), ("Liz Tay", "Elizabeth Tay"),
           ("Sean O'Brien", "Sean OBrien"), ("Dan Smith", "Daniel Smith"), ("Chris Lee", "Christine Lee"),
           # decided: a double-barrelled surname agrees with one of its parts (4+ letters) when the first names do
           ("Anna Smith", "Anna Smith-Jones")]
    no = [("Ben Fenwick", "Benedict Oakridge-Smith"), ("Benedict Oakridge-Smith", "Ben Harrow-Fenwick"),
          ("Tom Jones", "Ben Jones"), ("Anna Smith", "Anna Smithson"), ("Ben", "Ben Fenwick"),
          ("Anna Smith-Jones", "Anna Jones-Smith"), ("Jo Smith", "Joanna Smith"), ("Ann Lee", "Ann Le-Bo"),
          ("Tom Jones", "A SMITH-JONES"), ("Tom Jones", "JONES B")]
    for a, b in yes:
        assert si.names_equivalent(a, b) and si.names_equivalent(b, a), (a, b)
    for a, b in no:
        assert not si.names_equivalent(a, b) and not si.names_equivalent(b, a), (a, b)
    assert si.name_match("Anna Smith", "ANNA SMITH") == 2 and si.name_match("Anna Smith-Jones", "ANNA SMITH") == 1


BEN_PAYEE = [{"payeeName": "Benjamin Fenwick", "accounts": [{"bankIdentifier": "203040", "accountIdentifier": "55667788"}]}]
CRISPIN_PAYEE = [{"payeeName": "Crispin Fairleighbrook", "accounts": [{"bankIdentifier": "102030", "accountIdentifier": "44556677"}]}]


def test_payee_recognised_under_an_equivalent_name():
    fresh_store()
    got = scan("Invoice 1\nTotal £100.00", "b1", "2026-09-20", client=FakeClient(payees=BEN_PAYEE),
               email="ben@hf.example", name="Ben Harrow-Fenwick")
    assert rows_by_id()["b1"]["payee"] == "probably existing: Benjamin Fenwick (no bank details on the invoice)", got
    got = scan("Invoice 2\nTotal £100.00\nSort code 20-30-40\nAccount number 55667788", "b2", "2026-09-21",
               client=FakeClient(payees=BEN_PAYEE), email="ben@hf.example", name="Ben Harrow-Fenwick")
    assert rows_by_id()["b2"]["payee"] == "existing: Benjamin Fenwick" and "NEW BANK DETAILS" not in got, got
    got = scan("Invoice 3\nTotal £90.00", "o1", "2026-09-21", client=FakeClient(payees=CRISPIN_PAYEE),
               email="crispin@x.example", name="Crispin Fairleigh Brook")
    assert rows_by_id()["o1"]["payee"] == "probably existing: Crispin Fairleighbrook (no bank details on the invoice)", got
    got = scan("Invoice 4\nTotal £90.00\nSort code 11-11-11\nAccount number 22223333", "o2", "2026-09-22",
               client=FakeClient(payees=CRISPIN_PAYEE), email="crispin@x.example", name="Crispin Fairleigh Brook")
    assert "BANK DETAILS CHANGED: Starling payee 'Crispin Fairleighbrook'" in got, got


def test_payee_name_fitting_two_payees_or_another_open_singer_is_ambiguous():
    two = [{"payeeName": "Ben Fenwick", "accounts": []}, {"payeeName": "Benjamin Fenwick", "accounts": []}]
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", [], lm.payee_fingerprints(two), [p["payeeName"] for p in two])
    assert a["payee"].startswith("ambiguous: Ben Fenwick, Benjamin Fenwick"), a["payee"]
    bella = [unpaid("bella1", "Bella Fenwick", 100, "2026-09-10")]
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", bella, {}, ["B Fenwick"])
    assert a["payee"].startswith("ambiguous: B Fenwick"), a["payee"]
    a = si.assess_new(inv("", ""), "b@x.com", "Ben Fenwick", [dict(bella[0], paid_on="2026-09-11")], {}, ["B Fenwick"])
    assert a["payee"] == "probably existing: B Fenwick (no bank details on the invoice)", a["payee"]


def test_match_paid_by_equivalent_names():
    ben = [unpaid("b1", "Ben Harrow-Fenwick", 100, "2026-09-20")]
    assert si.match_paid(ben, [out(100, "2026-09-21", "BENJAMIN FENWICK", "p1")]) == {"b1": ("2026-09-21", 100.0, "p1", False)}
    orl = [unpaid("o1", "Crispin Fairleigh Brook", 90, "2026-09-20")]
    assert si.match_paid(orl, [out(90, "2026-09-21", "CRISPIN FAIRLEIGHBROOK", "p2")]) == {"o1": ("2026-09-21", 90.0, "p2", False)}
    assert si.match_paid([unpaid("x", "Ben Fenwick", 100, "2026-09-20")],
                         [out(100, "2026-09-21", "BENEDICT OAKRIDGE-SMITH", "p3")]) == {}
    # equivalent to two open singers at the same strength: reported, never applied
    report = []
    two = [unpaid("b1", "Ben Harrow-Fenwick", 100, "2026-09-20"), unpaid("b2", "Ben Oakridge-Fenwick", 100, "2026-09-20")]
    assert si.match_paid(two, [out(100, "2026-09-21", "BENJAMIN FENWICK", "p4")], report) == {}
    assert report and report[0].startswith("AMBIGUOUS £100.00"), report
    # an exact name beats a looser one: ANNA SMITH pays Anna Smith, not Anna Smith-Jones
    annas = [unpaid("a1", "Anna Smith", 100, "2026-09-20"), unpaid("a2", "Anna Smith-Jones", 100, "2026-09-20")]
    assert si.match_paid(annas, [out(100, "2026-09-21", "ANNA SMITH", "p5")]) == {"a1": ("2026-09-21", 100.0, "p5", False)}


# --- bill lines for Zoho Books (handover Appendix E, step 4a) --------------------------------------

BEN_TRUSTED = [{"payeeName": "Ben Fenwick", "accounts": [{"bankIdentifier": "123456", "accountIdentifier": "11112222"}]}]


def bill_lines(out):
    return [l for l in out.splitlines() if l.startswith(("bill:", "bill_number:"))]


def test_bill_number_rule():
    assert si.bill_number("1020", "6133510000000123456") == "1020"
    assert si.bill_number("INV-0107", "6133510000000123456") == "INV-0107"
    assert si.bill_number("INV-2026-017", "6133510000000123456") == "SI-23456"  # 2026-017 is one run of 7
    assert si.bill_number("20260309-001", "6133510000000123456") == "SI-23456"
    assert si.bill_number("A 12.345", "6133510000000123456") == "A 12.345"  # a run of exactly 5 is fine
    assert si.bill_number("A 123.456", "6133510000000123456") == "SI-23456"
    assert si.bill_number("", "6133510000000123456") == "SI-23456"
    assert si.bill_number("?", "6133510000000123456") == "SI-23456"


def test_scan_prints_bill_yes_for_a_trusted_payee():
    fresh_store()
    out = scan(GEN.format(n=1020), "6133510000000170001", "2026-09-25", FakeClient(payees=BEN_TRUSTED))
    assert bill_lines(out) == ["bill: yes", "bill_number: 1020"], out


def test_scan_prints_bill_no_for_a_bank_warning():
    fresh_store()
    out = scan(GEN.format(n=1020), "6133510000000170002", "2026-09-25")  # new details: ring first
    assert "!" in out and bill_lines(out) == ["bill: no (bank warning)", "bill_number: 1020"], out


def test_scan_prints_bill_no_when_the_amount_is_missing_or_zero():
    fresh_store()
    out = scan("Invoice 1021\nThanks!", "6133510000000170003", "2026-09-25", FakeClient(payees=BEN_TRUSTED))
    assert bill_lines(out)[0] == "bill: no (amount not found)", out
    fresh_store()
    zero = "Invoice 1022\nTotal £0.00\nSort code 12-34-56\nAccount number 11112222"
    out = scan(zero, "6133510000000170004", "2026-09-25", FakeClient(payees=BEN_TRUSTED))
    assert bill_lines(out)[0] in ("bill: no (zero amount)", "bill: no (amount not found)"), out


def test_scan_long_ref_gets_an_si_bill_number():
    fresh_store()
    out = scan(GEN.format(n="INV-2026-017"), "6133510000000170005", "2026-09-25", FakeClient(payees=BEN_TRUSTED))
    assert bill_lines(out) == ["bill: yes", "bill_number: SI-70005"], out


def test_already_recorded_reprints_the_stored_line_and_bill_lines():
    fresh_store()
    first = scan(GEN.format(n=1020), "6133510000000170006", "2026-09-25", FakeClient(payees=BEN_TRUSTED))
    again = scan(GEN.format(n=1020), "6133510000000170006", "2026-09-25", FakeClient(payees=BEN_TRUSTED))
    assert again.splitlines()[0] == "already recorded: 6133510000000170006", again
    assert again.splitlines()[1] == first.splitlines()[0], (first, again)
    assert bill_lines(again) == ["bill: yes", "bill_number: 1020"], again
    assert "11112222" not in again
    fresh_store()
    scan(GEN.format(n=1020), "6133510000000170007", "2026-09-25")
    again = scan(GEN.format(n=1020), "6133510000000170007", "2026-09-25")
    assert "   ! NEW BANK DETAILS" in again and bill_lines(again)[0] == "bill: no (bank warning)", again


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
            except Exception as e:
                print(f"ERROR {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
