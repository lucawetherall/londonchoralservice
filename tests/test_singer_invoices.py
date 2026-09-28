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
    assert si.match_paid(rows, [out(200, "2026-09-19", "LAURA PENHALLOW", "p1")]) == {"m1": ("2026-09-19", 200.0, "p1")}


def test_match_paid_uses_payee_name():
    rows = [unpaid("m1", "Maddy Kessell", 160, "2026-09-01", payee="existing: M M Kessell")]
    assert si.match_paid(rows, [out(160, "2026-09-02", "M M KESSELL", "p1")]) == {"m1": ("2026-09-02", 160.0, "p1")}


def test_match_paid_rejects_wrong_amount_early_date_and_double_use():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-19"), unpaid("m2", "Laura Penhallow", 200, "2026-09-20")]
    assert si.match_paid(rows, [out(150, "2026-09-21", "LAURA PENHALLOW")]) == {}
    assert si.match_paid(rows[:1], [out(200, "2026-09-10", "LAURA PENHALLOW")]) == {}
    assert si.match_paid(rows, [out(200, "2026-09-21", "LAURA PENHALLOW", "p1")]) == {"m1": ("2026-09-21", 200.0, "p1")}


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
                                                   "transactionTime": "2026-09-26T09:00:00Z", "counterPartyName": "BEN FENWICK"}]))
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


def hrow(email, name, sc, acc, received, paid_on="", changed="no", mid="h"):
    return {"message_id": mid, "singer_email": email, "singer_name": name, "received": received,
            "bank_fp": lm.bank_fingerprint(sc, acc), "bank_last4": acc[-4:], "paid_on": paid_on, "bank_changed": changed}


def test_new_address_with_new_details_warns():
    history = [hrow("ben@example.com", "Ben Fenwick", "123456", "11112222", "2026-08-01", paid_on="2026-08-05")]
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
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "12345678", "2026-08-01")]
    assert new not in si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])["warnings"]


def test_changed_details_warn_until_paid():
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "11112222", "2026-08-01", mid="h1"),
               hrow("b@x.com", "Ben Fenwick", "123456", "12345678", "2026-09-01", changed="yes", mid="h2")]
    a = si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])
    assert a["bank_changed"] == "yes" and any("••••2222" in w for w in a["warnings"])
    history[1]["paid_on"] = "2026-09-03"
    assert si.assess_new(inv(), "b@x.com", "Ben Fenwick", history, {}, [])["bank_changed"] == "no"


def test_was_figure_uses_most_recent_trusted_row():
    history = [hrow("b@x.com", "Ben Fenwick", "123456", "33334444", "2026-09-01", mid="new"),
               hrow("b@x.com", "Ben Fenwick", "123456", "11112222", "2026-07-01", mid="old")]
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
    assert si.match_paid(rows, [out(100, "2026-09-22", "KATHLEEN JONES", "p1")]) == {"kat": ("2026-09-22", 100.0, "p1")}


def test_match_paid_ambiguous_across_singers():
    rows = [unpaid("a", "Anna Smith", 100, "2026-09-20"), unpaid("j", "John Smith", 100, "2026-09-21")]
    report = []
    assert si.match_paid(rows, [out(100, "2026-09-22", "SMITH J", "p1")], report) == {}
    assert report == ["AMBIGUOUS £100.00 on 2026-09-22: check by hand"]


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
    want = {"m1": ("2026-09-21", 200.0, "p1"), "m2": ("2026-09-25", 200.0, "p2")}
    assert si.match_paid(rows, feed) == want
    assert si.match_paid(rows, feed[::-1]) == want


def test_match_paid_uses_london_date():
    rows = [unpaid("m1", "Laura Penhallow", 200, "2026-09-26")]
    item = out(200, "2026-09-25", "LAURA PENHALLOW", "p1", at="T23:30:00Z")
    assert si.match_paid(rows, [item]) == {"m1": ("2026-09-26", 200.0, "p1")}


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
