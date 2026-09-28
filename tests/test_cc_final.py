#!/usr/bin/env python3
"""Tests for the Command Centre's phase 6 (final wiring): Books and margins on the pages, the calendar cache
round trip, the drafts inbox (cc_sync.py drafts-put and the draft-mark action), the quote calculator and the
background refresh job.

Stdlib runner, Starlette's TestClient, FAKE fixtures in a temp LCS_PRIVATE_DIR (fake names, example.org
emails), a fake Starling client and a fake subprocess runner. Never touches ~/lcs-private, the bank, Zoho or
Google. .venv/bin/python tests/test_cc_final.py
"""
import asyncio, contextlib, datetime, html as html_mod, io, json, os, re, stat, subprocess, sys, tempfile, threading
from pathlib import Path
from zoneinfo import ZoneInfo

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ.pop("CC_DEV_LOGIN", None)
os.environ.pop("CC_NO_REFRESH_JOB", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
from starlette.testclient import TestClient  # noqa: E402

import cc_sync  # noqa: E402
from command_centre import actions, auth, data, drafts, jobs, models, quote  # noqa: E402
from command_centre.app import create_app  # noqa: E402

lm, si, pl, cp = data.lm, data.si, data.pl, data.cp
LONDON = ZoneInfo("Europe/London")
NOW = datetime.datetime(2026, 9, 28, 9, 30, tzinfo=LONDON)
TODAY = NOW.date()
LOGIN = "owner@example.org"
HOST = "mac.example-tailnet.ts.net"
ORIGIN = f"https://{HOST}"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
POST_HEADERS = dict(HEADERS, Origin=ORIGIN)
LOCAL = ("127.0.0.1", 50000)
CACHE = Path(TMP) / "command-centre" / "cache"
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]
THREAD = "1789828736363141700"
ZOHO_DRAFTS = "https://mail.zoho.com/zm/#mail/folder/drafts"


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


class FakeBank:
    def account(self):
        return {"accountUid": "acc-1", "defaultCategory": "cat-1"}

    def get(self, path):
        return {"clearedBalance": {"minorUnits": 123456}, "effectiveBalance": {"minorUnits": 120000}}

    def feed(self, since, until, direction):
        return []


def write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def books_invoice(number, status, date, total, balance, first="Ann"):
    return {"number": number, "status": status, "date": date, "due_date": "", "total": total, "balance": balance,
            "customer": first}


INVOICES = [
    books_invoice("0310", "sent", "2026-09-01", 1150.0, 1150.0),
    books_invoice("1212", "draft", "2026-09-20", 1400.0, 1400.0, "Cat"),
    books_invoice("0801", "paid", "2026-07-01", 650.0, 0.0, "Dan"),
]
BILLS = [{"number": "BF-12", "vendor": "Ben", "status": "open", "total": 120.0, "balance": 120.0,
          "date": "2026-09-20"}]


def books_json(invoices=INVOICES, bills=BILLS):
    return {"generated_at": "2026-09-28T07:00:00+01:00", "invoices": invoices, "bills": bills,
            "totals": cc_sync.totals(invoices, bills)}


def clean():
    for dirpath, dirnames, filenames in os.walk(TMP, topdown=False):
        for f in filenames:
            os.remove(os.path.join(dirpath, f))
        for d in dirnames:
            p = os.path.join(dirpath, d)
            (os.remove if os.path.islink(p) else os.rmdir)(p)


def fixtures(books=True):
    clean()
    auth.save_config({"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": HOST, "passkeys": []})
    lm.write_csv(lm.LEDGER, [
        {"booking_ref": "0310", "invoice_date": "2026-09-01", "event_date": "2026-10-03", "client_name": "Ann Smithfield",
         "client_email": "ann@example.org", "occasion": "wedding", "ensemble": "Small Choir", "value_gbp": "1150",
         "notes": ""},
        {"booking_ref": "1212", "invoice_date": "2026-09-20", "event_date": "2026-12-12", "client_name": "Cat Jonesworth",
         "client_email": "cat@example.org", "occasion": "christmas", "ensemble": "Small Choir", "value_gbp": "1400",
         "notes": ""},
        {"booking_ref": "0801", "invoice_date": "2026-07-01", "event_date": "2026-08-01", "client_name": "Dan Closedman",
         "client_email": "dan@example.org", "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": "paid in full 2026-07-20"},
        {"booking_ref": "0915", "invoice_date": "2026-09-01", "event_date": "2026-11-15", "client_name": "Fay Cancelwood",
         "client_email": "fay@example.org", "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": "cancelled 2026-09-10"},
    ], LEDGER_COLS)
    lm.write_csv(si.STORE, [
        {"message_id": "m1", "received": "2026-09-20", "singer_name": "Ben Fenwickson", "singer_email": "ben@example.org",
         "invoice_ref": "BF-12", "amount_gbp": "120", "bank_fp": "abc", "bank_last4": "4321", "payee": "", "bank_changed": "no",
         "paid_on": "", "booking_ref": "0310"},
        {"message_id": "m2", "received": "2026-09-22", "singer_name": "Dora Quillfeather", "singer_email": "dora@example.org",
         "invoice_ref": "DQ7", "amount_gbp": "150", "bank_fp": "def", "bank_last4": "1111", "payee": "", "bank_changed": "no",
         "paid_on": "2026-09-25", "booking_ref": "0310"},
        {"message_id": "m3", "received": "2026-09-23", "singer_name": "Zed Mistakeham", "singer_email": "zed@example.org",
         "invoice_ref": "Z1", "amount_gbp": "80", "bank_fp": "zzz", "bank_last4": "9999", "payee": "", "bank_changed": "no",
         "paid_on": "", "withdrawn": "2026-09-24", "booking_ref": "0310"},
        {"message_id": "m4", "received": "2026-09-24", "singer_name": "Eve Organstone", "singer_email": "eve@example.org",
         "invoice_ref": "EO1", "amount_gbp": "250", "bank_fp": "eee", "bank_last4": "2222", "payee": "", "bank_changed": "no",
         "paid_on": "", "booking_ref": "1212"},
    ], si.COLUMNS)
    lm.write_csv(pl.ENQUIRIES, [], pl.COLUMNS)
    if books:
        write(CACHE / "books.json", json.dumps(books_json()))


def make(bank=None, **kw):
    app = create_app(client_factory=(lambda: bank), now=lambda: NOW, clock=Clock(), checkout=lambda: "main", **kw)
    return TestClient(app, base_url=ORIGIN, client=LOCAL, follow_redirects=False)


def page(c, path):
    r = c.get(path, headers=HEADERS)
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    return r.text


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).replace("&gt;", ">").replace("&amp;", "&") \
        .replace("&#39;", "'")


def quiet(fn, *a, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(*a, **kw)
    return code, buf.getvalue()


def audit_lines():
    p = Path(TMP) / "command-centre" / "audit.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


# ---------------------------------------------------------------- Books (R17)


def flag_case(ref, books_status, state, total=1000.0, balance=None, date="2026-09-01", notes=""):
    inv = books_invoice(ref, books_status, date, total, total if balance is None else balance)
    return inv, {"booking_ref": ref, "notes": notes}, {"ref": ref, "state": state}


def test_books_flags_follow_appendix_a_6g():
    cases = [
        flag_case("2001", "paid", "DEPOSIT_SEEN", balance=0.0),                       # Books paid, Starling not
        flag_case("2002", "paid", "CLOSED", balance=0.0, notes="paid in full 2026-09-01"),  # agree: no flag
        flag_case("2003", "sent", "DEPOSIT_SEEN"),                                   # Starling matched, Books unpaid
        flag_case("2004", "partially_paid", "PAID_IN_FULL", balance=400.0),          # part-paid vs paid in full
        flag_case("2005", "draft", "AWAITING_DEPOSIT", date="2026-09-25"),           # 3 days old: flag
        flag_case("2006", "draft", "AWAITING_DEPOSIT", date="2026-09-26"),           # 2 days old: no flag
        flag_case("2007", "overdue", "DEPOSIT_SEEN", balance=500.0),                 # something paid: no flag
        flag_case("2008", "overdue", "AWAITING_DEPOSIT"),                            # both unpaid: agree
        flag_case("2009", "paid", "PAID_IN_FULL", balance=0.0),                      # agree
        flag_case("2010", "unpaid", "CLOSED", notes="paid in full 2026-09-02"),     # note counts as matched
    ]
    invoices = [c[0] for c in cases]
    ledger = [c[1] for c in cases]
    bookings = [c[2] for c in cases]
    flags = models.books_flags(invoices, ledger, bookings, TODAY, True)
    got = {(f["ref"], f["text"]) for f in flags}
    assert got == {
        ("2001", "Books paid, Starling not matched"),
        ("2003", "Starling matched, Books unpaid"),
        ("2004", "Starling paid in full, Books part-paid"),
        ("2005", "Books draft not sent (>2 days)"),
        ("2010", "Starling matched, Books unpaid"),
    }, got
    # Starling not checked: the two comparisons are skipped, as 6g skips them; the draft rule stays
    flags = models.books_flags(invoices, ledger, bookings, TODAY, False)
    assert {(f["ref"], f["text"]) for f in flags} == {("2005", "Books draft not sent (>2 days)")}
    # INV-prefixed numbers match the ledger ref (check_payments.norm_ref)
    inv = books_invoice("INV2001", "paid", "2026-09-01", 100.0, 0.0)
    assert models.books_flags([inv], [{"booking_ref": "2001", "notes": ""}], [{"ref": "2001", "state": "DEPOSIT_SEEN"}],
                              TODAY, True)
    assert models.books_invoice("2001", [inv]) is inv and models.books_invoice("", [inv]) is None


def test_books_summary_and_timeline_lines():
    s = models.books_summary(books_json())
    assert s["totals"]["receivables"] == 1150.0 and s["totals"]["receivables_count"] == 1
    assert s["drafts"] == [{"number": "1212", "href": None}] and s["overdue"] == []  # no ledger: no link
    s = models.books_summary(books_json(), [{"booking_ref": "1212"}])
    assert s["drafts"] == [{"number": "1212", "href": "/bookings/1212"}], s["drafts"]
    s = models.books_summary(books_json([books_invoice("INV1212", "draft", "2026-09-20", 1.0, 1.0)]),
                             [{"booking_ref": "1212"}, {"booking_ref": "0310"}])
    assert s["drafts"] == [{"number": "INV1212", "href": "/bookings/1212"}], s["drafts"]  # norm_ref, the ledger's ref
    assert s["generated_at"].hour == 7 and s["generated_at"].tzinfo is not None
    items = models.books_timeline("0310", books_json()["invoices"])
    assert len(items) == 1 and items[0]["kind"] == "books" and items[0]["date"] == datetime.date(2026, 9, 1)
    assert "Books invoice 0310: sent" in items[0]["text"] and "£1,150.00" in items[0]["text"], items
    assert models.books_timeline("9999", books_json()["invoices"]) == []


def test_money_page_books_panel_and_season_total():
    fixtures()
    c = make(FakeBank())
    out = text_of(page(c, "/money"))
    assert "Books" in out and "Receivables" in out and "£1,150.00" in out, out[:2000]
    assert "Drafts not yet sent" in out and "1212" in out
    assert "Unpaid bills" in out and "£120.00" in out
    assert "Books as of Mon 28 Sep 2026, 07:00" in out, out
    # season from data/budget-windows.yml (2026-09-01): 0310 and 1212; 0801 is before, 0915 cancelled
    assert "Season margin" in out and "£2,550.00" in out and "£520.00" in out and "£2,030.00" in out, out
    assert "79.6%" in out
    assert "couldn't load" not in out


def test_money_page_shows_unlinked_singer_invoices():
    fixtures()
    rows = lm.read_csv(si.STORE)
    rows.append({"message_id": "m5", "received": "2026-09-25", "singer_name": "Uma Unlinked",
                 "singer_email": "uma@example.org", "invoice_ref": "UN1", "amount_gbp": "90", "bank_fp": "uuu",
                 "bank_last4": "3333", "payee": "", "bank_changed": "no", "paid_on": "", "booking_ref": ""})
    lm.write_csv(si.STORE, rows, si.COLUMNS)
    out = text_of(page(make(FakeBank()), "/money"))
    assert "Unlinked singer invoices: 1, £90.00." in out, out
    assert "Uma Unlinked" not in out  # first name only, like every other singer row


def test_today_flags_books_disagreements():
    fixtures()
    c = make(FakeBank())
    base = text_of(page(c, "/"))
    assert "1212" in base and "Books draft not sent (>2 days)" in base, base[:3000]
    m = re.search(r"(\d+) things? needs? you", base)
    fixtures(books=False)
    without = text_of(page(make(FakeBank()), "/"))
    assert "Books not synced yet" in without
    n = re.search(r"(\d+) things? needs? you", without)
    assert m and int(m.group(1)) == (int(n.group(1)) if n else 0) + 1, (m, n)


def test_books_flags_compare_the_ledger_with_books():
    def row(ref, invoiced, notes=""):
        return {"booking_ref": ref, "invoice_date": invoiced, "notes": notes}
    ledger = [row("2101", "2026-09-25"),                          # 3 days, not in Books: flag
              row("2102", "2026-09-27"),                          # 1 day: too soon
              row("2108", "2026-09-26"),                          # exactly 2 days: flag
              row("2103", "2026-09-01", "cancelled 2026-09-10"),  # cancelled: no
              row("2104", "2026-09-01", "paid in full 2026-09-20"),  # closed: no
              row("2105", "2026-09-01"),                          # paid in full per Starling: no
              row("2106", "2026-09-01"),                          # only a void invoice in Books: flag
              row("2107", "2026-09-01"),                          # a Books draft counts as in Books
              row("2109", "")]                                    # no invoice date: no
    bookings = [{"ref": "2105", "state": "PAID_IN_FULL"}]
    invoices = [books_invoice("INV2106", "void", "2026-09-02", 1.0, 1.0),
                books_invoice("2107", "draft", "2026-09-27", 1.0, 1.0),
                books_invoice("3001", "sent", "2026-09-20", 1.0, 1.0),     # not in the ledger: flag
                books_invoice("3002", "draft", "2026-09-27", 1.0, 1.0),    # a draft: no
                books_invoice("3003", "void", "2026-09-20", 1.0, 1.0),     # void: no
                books_invoice("INV2104", "paid", "2026-09-02", 1.0, 0.0)]  # in the ledger (norm_ref): no
    flags = models.books_flags(invoices, ledger, bookings, TODAY, False)
    got = {(f["ref"], f["text"], f["href"]) for f in flags}
    assert got == {("2101", "in the ledger, not in Books", "/bookings/2101"),
                   ("2108", "in the ledger, not in Books", "/bookings/2108"),
                   ("2106", "in the ledger, not in Books", "/bookings/2106"),
                   ("3001", "in Books, not in the ledger", None)}, got
    assert all(f["tone"] == "warn" for f in flags)
    # the existing rules link to the ledger's own ref, not the Books number
    inv = books_invoice("INV2001", "draft", "2026-09-01", 100.0, 100.0)
    f = models.books_flags([inv], [row("2001", "2026-09-01")], [], TODAY, False)
    assert f == [{"ref": "INV2001", "text": "Books draft not sent (>2 days)", "tone": "warn",
                  "href": "/bookings/2001"}], f


def store_row(mid, name, ref, **over):
    base = {"message_id": mid, "received": "2026-09-20", "singer_name": name, "singer_email": "x@example.org",
            "invoice_ref": ref, "amount_gbp": "120", "bank_fp": "abc", "bank_last4": "4321", "payee": "",
            "bank_changed": "no", "paid_on": "", "paid_verified": "", "notes": "", "withdrawn": "", "booking_ref": ""}
    return dict(base, **over)


def bill(number, vendor, status, balance):
    return {"number": number, "vendor": vendor, "status": status, "total": 120.0, "balance": balance,
            "date": "2026-09-20"}


def test_singer_bill_flags_compare_the_store_with_books():
    rows = [store_row("m1", "Ann Paidopen", "A1", paid_on="2026-09-25", paid_verified="yes"),   # flag
            store_row("m2", "Bob Paidpaid", "B1", paid_on="2026-09-25", paid_verified="yes"),   # agree
            store_row("m3", "Cy Settled", "C1", paid_on="2026-09-25", paid_verified="no"),      # by hand: no
            store_row("m4", "Di Openhere", "D1"),                                               # flag
            store_row("m5", "Ed Withdrawn", "E1", withdrawn="2026-09-24"),                      # withdrawn: no
            store_row("m6", "Flo Nobill", "F1", paid_on="2026-09-25", paid_verified="yes"),     # no bill: no
            store_row("1789828736363141707", "Gus Longref", "12345678", paid_on="2026-09-25", paid_verified="yes"),
            store_row("m8", "Hal Same", "SAME-1"), store_row("m9", "Ivy Same", "SAME-1")]
    bills = [bill("A1", "Ann", "open", 120.0), bill("B1", "Bob", "paid", 0.0), bill("C1", "Cy", "open", 120.0),
             bill("d1 ", "Di", "paid", 0.0), bill("E1", "Ed", "paid", 0.0),
             bill("SI-41707", "Gus", "overdue", 120.0),                # bill_number() of a long ref: SI- + message id
             bill("SAME-1", "Hal", "paid", 0.0), bill("SAME-1", "Ivy", "open", 120.0),  # two share a number
             bill("A1", "Ann", "void", 120.0)]                          # void bills never count
    flags = models.singer_bill_flags(rows, bills)
    got = {(f["ref"], f["text"]) for f in flags}
    assert got == {("A1 Ann", "paid in Starling, bill open in Books"),
                   ("D1 Di", "bill paid in Books, invoice open here"),
                   ("SI-41707 Gus", "paid in Starling, bill open in Books"),
                   ("SAME-1 Hal", "bill paid in Books, invoice open here")}, got
    assert all(f["href"] == "/singers" and f["tone"] == "warn" for f in flags)
    assert models.singer_bill_flags(rows, []) == []


def test_today_books_card_shows_bills_links_and_how_old_books_is():
    fixtures()
    rows = lm.read_csv(si.STORE)
    for r in rows:
        if r["message_id"] == "m2":  # Dora: paid to verified details, her bill still open in Books
            r["paid_verified"] = "yes"
    lm.write_csv(si.STORE, rows, si.COLUMNS)
    before = text_of(page(make(FakeBank()), "/"))
    invoices = INVOICES + [books_invoice("4444", "sent", "2026-09-20", 10.0, 10.0)]
    write(CACHE / "books.json", json.dumps(books_json(invoices, BILLS + [
        {"number": "DQ7", "vendor": "Dora", "status": "open", "total": 150.0, "balance": 150.0, "date": "2026-09-22"}])))
    html = page(make(FakeBank()), "/")
    out = text_of(html)
    assert "DQ7 Dora paid in Starling, bill open in Books" in out, out[:3000]
    assert '<a class="mono" href="/singers">DQ7 Dora</a>' in html
    assert "4444 in Books, not in the ledger" in out and '<span class="mono">4444</span>' in html
    assert 'href="/bookings/4444"' not in html
    assert '<a class="mono" href="/bookings/1212">1212</a>' in html  # the draft flag links to the ledger booking
    assert "Books as of Mon 28 Sep 2026, 07:00." in out and "more than 24 hours old" not in out
    n0 = int(re.search(r"(\d+) things? needs? you", before).group(1))
    n1 = int(re.search(r"(\d+) things? needs? you", out).group(1))
    assert n1 == n0 + 2, (n0, n1)  # the singer bill and the Books-only invoice
    stale = dict(books_json(), generated_at="2026-09-27T07:00:00+01:00")  # 26 and a half hours before NOW
    write(CACHE / "books.json", json.dumps(stale))
    out = text_of(page(make(FakeBank()), "/"))
    assert "Books as of Sun 27 Sep 2026, 07:00." in out and "more than 24 hours old" in out, out[:3000]


def test_money_page_links_books_numbers_to_the_ledger_only():
    fixtures()
    write(CACHE / "books.json", json.dumps(books_json(INVOICES + [
        books_invoice("7777", "draft", "2026-09-27", 10.0, 10.0)])))
    html = page(make(FakeBank()), "/money")
    assert '<a class="mono" href="/bookings/1212">1212</a>' in html
    assert '<span class="mono">7777</span>' in html and 'href="/bookings/7777"' not in html


def test_health_lists_the_age_of_each_cache():
    from command_centre import sources
    fixtures()
    write(CACHE / "drafts.json", "[]")
    two_hours = (NOW - datetime.timedelta(hours=2)).timestamp()
    old = (NOW - datetime.timedelta(hours=30)).timestamp()
    os.utime(CACHE / "books.json", (two_hours, two_hours))
    os.utime(CACHE / "drafts.json", (old, old))
    rows = {r["label"]: r for r in sources.run_proxies(NOW)[0]}
    books, diary, drafts_ = (rows["Books cache (cc_sync.py books)"], rows["Diary cache (the daily pass)"],
                             rows["Drafts cache (the assistant)"])
    assert books["age"] == "2 hours ago" and not books["stale"], books
    assert diary["when"] is None and diary["age"] is None and diary["stale"], diary
    assert drafts_["age"] == "30 hours ago" and not drafts_["stale"], drafts_
    os.utime(CACHE / "books.json", (old, old))
    assert {r["label"]: r for r in sources.run_proxies(NOW)[0]}["Books cache (cc_sync.py books)"]["stale"]
    out = text_of(page(make(FakeBank()), "/health"))
    assert "Books cache (cc_sync.py books)" in out and "(30 hours ago) stale" in out, out
    assert "Diary cache (the daily pass) never stale" in out, out


def test_booking_timeline_books_status_singers_and_margin():
    fixtures()
    c = make(FakeBank())
    out = text_of(page(c, "/bookings/0310"))
    assert "Books invoice 0310: sent" in out, out
    assert "Ben" in out and "Dora" in out and "Zed" not in out, out
    assert "Fenwickson" not in out and "Quillfeather" not in out
    assert "Singer costs" in out and "£270.00" in out and "£880.00" in out and "76.5%" in out, out
    out = text_of(page(c, "/bookings/1212"))
    assert "Books invoice 1212: draft" in out and "Eve" in out and "£1,150.00" in out and "82.1%" in out, out
    out = text_of(page(c, "/bookings/0915"))
    assert "Not in Books" in out


def test_bookings_list_shows_margins():
    fixtures()
    out = text_of(page(make(FakeBank()), "/bookings?when=all"))
    assert "Margin" in out and "£880.00" in out and "76.5%" in out and "£270.00" in out, out


def test_a_bad_books_cache_breaks_only_its_panel():
    fixtures()
    write(CACHE / "books.json", json.dumps({"invoices": "nope"}))
    c = make(FakeBank())
    for path in ("/", "/money", "/bookings/0310"):
        out = text_of(page(c, path))
        assert "couldn't load (ValueError)" in out, (path, out[:1500])
    out = text_of(page(c, "/money"))
    assert "£2,030.00" in out  # the season margin still renders
    write(CACHE / "books.json", "{not json")
    assert "couldn't load" in text_of(page(c, "/money"))


def test_a_failing_margin_breaks_only_its_panel():
    fixtures()
    saved = si.margins
    si.margins = lambda *a: (_ for _ in ()).throw(KeyError("x"))
    try:
        c = make(FakeBank())
        out = text_of(page(c, "/bookings?when=all"))
        assert "0310" in out and "couldn't load (KeyError)" in out, out[:1500]
        out = text_of(page(c, "/money"))
        assert "£1,150.00" in out and "couldn't load (KeyError)" in out
        out = text_of(page(c, "/bookings/0310"))
        assert "Books invoice 0310" in out
    finally:
        si.margins = saved


# ---------------------------------------------------------------- calendar


def test_calendar_reads_what_calendar_put_writes():
    fixtures()
    events = [{"start": "2026-10-01T18:00:00+01:00", "end": "2026-10-01T20:00:00+01:00",
               "summary": "Rehearsal at St Example", "calendar": "Work"},
              {"start": "2026-10-02", "end": "2026-10-04", "summary": "Away", "calendar": "Personal"}]
    code, out = quiet(cc_sync.cmd_calendar_put, json.dumps(events))
    assert code == 0, out
    assert (CACHE / "calendar.json").exists()
    html = text_of(page(make(FakeBank()), "/calendar?view=week&date=2026-10-01"))
    assert "18:00 Rehearsal at St Example · Work" in html, html[:3000]
    assert html.count("Away · Personal") == 2  # all-day, end exclusive: 2 and 3 October


# ---------------------------------------------------------------- drafts inbox


def draft(**kw):
    d = {"thread_id": THREAD, "kind": "reply", "first_name": "Ann", "subject": "Re: Wedding on 3 October",
         "created": "2026-09-28"}
    d.update(kw)
    return d


def test_drafts_put_validates_and_writes_nothing_on_a_refusal():
    clean()
    bad = [
        "not json", json.dumps("a string"), json.dumps({}),
        json.dumps(dict(draft(), extra="x")),
        json.dumps({k: v for k, v in draft().items() if k != "created"}),
        json.dumps(draft(kind="send-now")),
        json.dumps(draft(subject="x" * 81)),
        json.dumps(draft(subject="line\nbreak")),
        json.dumps(draft(subject="   ")),
        json.dumps(draft(first_name="ann")),
        json.dumps(draft(first_name="Ann Smithfield")),
        json.dumps(draft(created="28/09/2026")),
        json.dumps(draft(created="2026-02-30")),
        json.dumps(draft(thread_id="12 34")),
        json.dumps(draft(thread_id="x" * 41)),
        json.dumps(draft(thread_id=12345)),
        json.dumps([draft()] * 51),
        json.dumps([draft(), draft(kind="nope")]),
    ]
    for text in bad:
        code, out = quiet(cc_sync.cmd_drafts_put, text)
        assert code == 2 and out.startswith("drafts: refused ("), (text[:60], out)
        assert not (CACHE / "drafts.json").exists(), text[:60]
    code, out = quiet(cc_sync.cmd_drafts_put, "x" * (cc_sync.MAX_INPUT + 1))
    assert code == 2


def test_drafts_put_merges_and_keeps_mode_600():
    clean()
    code, out = quiet(cc_sync.cmd_drafts_put, json.dumps(draft(subject="Re: Wedding")))
    assert code == 0 and out.strip() == "drafts: 1 recorded, 1 in the inbox", out
    code, out = quiet(cc_sync.cmd_drafts_put, json.dumps([draft(subject="Re: Wedding, v2"),
                                                           draft(thread_id="ABC123", kind="receipt", first_name="Dan")]))
    assert code == 0 and out.strip() == "drafts: 2 recorded, 2 in the inbox", out
    saved = json.loads((CACHE / "drafts.json").read_text())
    assert isinstance(saved, list) and len(saved) == 2
    assert {d["subject"] for d in saved} == {"Re: Wedding, v2", "Re: Wedding on 3 October"}
    assert stat.S_IMODE(os.stat(CACHE / "drafts.json").st_mode) == 0o600
    assert stat.S_IMODE(os.stat(CACHE).st_mode) == 0o700
    assert cc_sync.main(["drafts-put", json.dumps(draft(kind="review"))]) == 0


def test_the_agents_record_each_saved_draft():
    for name in ("lcs-reply-drafter", "lcs-daily-pass", "lcs-singer-clerk"):
        body = (Path(ROOT) / ".claude" / "agents" / f"{name}.md").read_text(encoding="utf-8")
        assert ".venv/bin/python scripts/reports/cc_sync.py drafts-put '" in body, name
    settings = json.loads((Path(ROOT) / ".claude" / "settings.json").read_text())
    assert "Bash(.venv/bin/python scripts/reports/cc_sync.py *)" in settings["permissions"]["allow"]


def test_drafts_page_lists_and_links_to_zoho():
    fixtures()
    quiet(cc_sync.cmd_drafts_put, json.dumps([draft(), draft(thread_id="T2", kind="receipt", first_name="Dan",
                                                             subject="Re: Payment received", created="2026-09-27")]))
    html = page(make(FakeBank()), "/drafts")
    out = text_of(html)
    assert "Re: Wedding on 3 October" in out and "Ann" in out and "Re: Payment received" in out, out
    assert f'href="{ZOHO_DRAFTS}"' in html and "Open Zoho Mail drafts" in out
    assert THREAD not in html  # the thread id never reaches the page or a form
    assert re.search(r'rel="noopener noreferrer"', html)
    assert out.index("Re: Wedding on 3 October") < out.index("Re: Payment received")  # newest first
    clean()
    auth.save_config({"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": HOST, "passkeys": []})
    assert "No drafts recorded yet" in text_of(page(make(FakeBank()), "/drafts"))


def test_mark_a_draft_sent_is_local_csrf_protected_and_audited():
    fixtures()
    quiet(cc_sync.cmd_drafts_put, json.dumps(draft()))
    key = drafts.draft_key(draft())
    assert re.fullmatch(r"[a-z]{12}", key)
    c = make(FakeBank())
    assert f'value="{key}"' in page(c, "/drafts")
    body = {"input": {"key": key, "state": "sent"}}
    assert c.post("/actions/draft-mark/run", json=body, headers=HEADERS).status_code == 403  # no Origin
    assert c.post("/actions/draft-mark/run", json=body,
                  headers=dict(HEADERS, Origin="https://evil.example")).status_code == 403
    r = c.post("/actions/draft-mark/preview", json=body, headers=POST_HEADERS)
    assert r.status_code == 200 and r.json()["passkey"] is False and "sent" in r.json()["summary"], r.text
    assert "Ann" in r.json()["summary"] and THREAD not in r.json()["summary"]
    r = c.post("/actions/draft-mark/run", json=body, headers=POST_HEADERS)
    assert r.status_code == 200 and r.json()["ok"], r.text
    marks = Path(TMP) / "command-centre" / "drafts-marks.json"
    assert stat.S_IMODE(os.stat(marks).st_mode) == 0o600
    assert json.loads(marks.read_text())[key]["state"] == "sent"
    out = text_of(page(c, "/drafts"))
    assert "Marked sent" in out, out
    assert any(e["action"] == "draft-mark" and e["result"] == "ok" for e in audit_lines())
    for bad in ({"key": "zzzzzzzzzzzz", "state": "sent"}, {"key": key, "state": "deleted"},
                {"key": key, "state": "sent", "x": "y"}, {"key": THREAD, "state": "sent"}):
        r = c.post("/actions/draft-mark/run", json={"input": bad}, headers=POST_HEADERS)
        assert r.status_code == 400, (bad, r.status_code)
    r = c.post("/actions/draft-mark/run", json={"input": {"key": key, "state": "open"}}, headers=POST_HEADERS)
    assert r.status_code == 200 and json.loads(marks.read_text())[key]["state"] == "open"


def test_registry_includes_draft_mark_without_a_passkey():
    a = actions.REGISTRY["draft-mark"]
    assert a.passkey is False and "draft-mark" in actions.ROUTED


# ---------------------------------------------------------------- quote calculator


def page_figures(name):
    """Every £ figure in the page's pricing-price cells, read with a plain regex (not the parser under test)."""
    html = (Path(ROOT) / name).read_text(encoding="utf-8")
    cells = re.findall(r'class="pricing-price"[^>]*>(.*?)</td>', html, re.S)
    return [int(m.replace(",", "")) for c in cells for m in re.findall(r"£([\d,]+)", html_mod.unescape(c))]


def test_quote_figures_come_from_the_pages():
    lists = quote.load_lists()
    std, xmas = lists["standard"], lists["christmas"]
    by = {p["key"]: p for p in std["packages"]}
    assert by["small-choir"]["price"] == 1150 and by["small-choir"]["singers"] == 4
    assert by["soloist"]["price"] == 250 and by["soloist"]["singers"] == 1
    assert std["organist"] == 250 and std["soloist_organist"] == 450
    assert {p["key"] for p in xmas["packages"]} == {"small-choir", "quintet", "sextet", "full-choir", "chorus"}
    assert xmas["organist"] == 250
    for lst, name in ((std, "pricing.html"), (xmas, "christmas-pricing.html")):
        figures = page_figures(name)
        for p in lst["packages"]:
            assert p["price"] in figures, (name, p)
        assert lst["organist"] in figures


def test_quote_totals():
    lists = quote.load_lists()
    q = quote.calculate(lists, "standard", "small-choir", organist=True)
    assert q["total"] == 1400, q
    assert quote.calculate(lists, "standard", "small-choir")["total"] == 1150
    assert quote.calculate(lists, "standard", "soloist", organist=True)["total"] == 450
    assert quote.calculate(lists, "standard", "soloist")["total"] == 250
    # the Christmas page's own worked examples
    assert quote.calculate(lists, "christmas", "full-choir", organist=True)["total"] == 2250
    assert quote.calculate(lists, "christmas", "chorus", organist=True)["total"] == 3250
    assert quote.calculate(lists, "christmas", "small-choir", organist=True)["total"] == 1400
    for bad in (("standard", "nope"), ("nope", "small-choir"), ("christmas", "soloist")):
        try:
            quote.calculate(lists, *bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_quote_wording_follows_the_house_rules():
    lists = quote.load_lists()
    for lst in ("standard", "christmas"):
        for p in lists[lst]["packages"]:
            for org in (False, True):
                for travel in (False, True):
                    for day in (False, True):
                        w = quote.calculate(lists, lst, p["key"], organist=org, travel=travel, premium_day=day)["wording"]
                        assert "No VAT is added." in w, w
                        assert w.count("VAT") == 1, w
                        assert not re.search(r"\b(roster|\d+\+|over \d+ singers|our team of)", w, re.I), w
                        assert "—" not in w, w  # no em dashes in the sentences
                        assert not re.search(r"\b(color|organize|program)\b", w), w
                        if travel:
                            s = next(x for x in re.split(r"(?<=\.)\s", w) if "ravel" in x)
                            assert "confirm" in s and "with the quote" in s and "£" not in s, s
                        else:
                            assert "ravel" not in w
    w = quote.calculate(lists, "standard", "small-choir", organist=True)["wording"]
    assert "£1,400" in w and "£1,150" in w and "£250" in w and "four singers" in w, w
    w = quote.calculate(lists, "standard", "small-choir", premium_day=True)["wording"]
    assert "25%" in w  # the page's own premium sentence, no figure added to the total


def test_quote_page():
    fixtures()
    c = make(FakeBank())
    out = text_of(page(c, "/quote"))
    assert "Small Choir (4 singers)" in out and "Pick a package" in out
    html = page(c, "/quote?list=standard&package=small-choir&organist=yes&travel=yes")
    out = text_of(html)
    assert "£1,400" in out and "No VAT is added." in out and "with the quote" in out, out
    assert 'class="button quiet cc-copy"' in html
    out = text_of(page(c, "/quote?list=christmas&package=full-choir&organist=yes"))
    assert "£2,250" in out
    out = text_of(page(c, "/quote?list=standard&package=%3Cb%3E"))
    assert "Pick a package" in out and "<b>" not in page(c, "/quote?list=standard&package=%3Cb%3E")
    r = c.get("/quote", headers=HEADERS)
    assert r.status_code == 200 and not (Path(TMP) / "command-centre" / "quote").exists()


# ---------------------------------------------------------------- background refresh


class Recorder:
    def __init__(self, fail=None):
        self.calls, self.fail, self.locked = [], fail or {}, []

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        self.locked.append(actions._LOCKS["refresh"].locked())
        what = "books" if argv[-1] == "books" else "singer-paid" if argv[-1] == "--apply" else "dashboard"
        f = self.fail.get(what)
        if isinstance(f, BaseException):
            raise f
        return subprocess.CompletedProcess(argv, f if isinstance(f, int) else 0, b"secret output 12345678", b"")


def at(h, m, day=28, month=9):
    return datetime.datetime(2026, month, day, h, m, tzinfo=LONDON)


def test_refresh_job_schedule():
    job = jobs.RefreshJob(clear=lambda: None, runner=Recorder())
    assert not job.due(at(6, 59))
    assert job.due(at(7, 0))
    job.last_slot = jobs.slot(at(7, 0))
    assert not job.due(at(7, 10)) and not job.due(at(7, 29))
    assert job.due(at(7, 30)) and job.due(at(21, 45)) and job.due(at(22, 0)) and job.due(at(22, 20))
    assert not job.due(at(22, 30)) and not job.due(at(23, 59)) and not job.due(at(0, 30))
    # London time, whatever the clock's zone: 06:30 UTC in summer is 07:30 in London
    assert job.due(datetime.datetime(2026, 9, 28, 6, 30, tzinfo=datetime.timezone.utc))
    assert not job.due(datetime.datetime(2026, 12, 1, 6, 30, tzinfo=datetime.timezone.utc))  # 06:30 GMT
    # a fake clock through one day: 31 runs, at :00 and :30 from 07:00 to 22:00
    rec = Recorder()
    job = jobs.RefreshJob(clear=lambda: None, runner=rec)
    t = at(0, 0)
    runs = []
    while t < at(0, 0, day=29):
        if job.tick(t):
            runs.append(t)
        t += datetime.timedelta(minutes=1)
    assert len(runs) == 31 and runs[0] == at(7, 0) and runs[-1] == at(22, 0), (len(runs), runs[:2], runs[-1:])
    assert all(r.minute in (0, 30) for r in runs)


def test_refresh_job_runs_its_scripts_and_clears_the_bank_cache():
    clean()
    rec, cleared = Recorder(), []
    job = jobs.RefreshJob(clear=lambda: cleared.append(1), runner=rec)
    assert job.run_once() == "ok"
    # the singer payments first (a verified payment is recorded within 30 minutes), then the dashboard and Books
    assert [c[0][1:] for c in rec.calls] == [[str(Path(ROOT) / "scripts/bookings/singer_invoices.py"), "paid", "--apply"],
                                             [str(Path(ROOT) / "scripts/reports/dashboard.py")],
                                             [str(Path(ROOT) / "scripts/reports/cc_sync.py"), "books"]]
    assert jobs.SCRIPTS[0] == ("singer-paid", ["scripts/bookings/singer_invoices.py", "paid", "--apply"], 180)
    for argv, kw in rec.calls:
        assert argv[0] == sys.executable and kw["shell"] is False and 0 < kw["timeout"] <= 600
        assert kw["env"]["LCS_PRIVATE_DIR"] == TMP and not any(k.startswith("CC_") for k in kw["env"])
        assert kw["stdin"] == subprocess.DEVNULL
    assert cleared == [1] and all(rec.locked)
    assert not actions._LOCKS["refresh"].locked()
    assert audit_lines() == []  # a clean run is not logged


def test_refresh_job_failures_are_isolated_and_logged_by_type_only():
    clean()
    rec, cleared = Recorder(fail={"singer-paid": 2, "dashboard": subprocess.TimeoutExpired("x", 5), "books": 1}), []
    job = jobs.RefreshJob(clear=lambda: cleared.append(1), runner=rec)
    assert job.run_once() == "failed"
    assert len(rec.calls) == 3 and cleared == [1]  # each script still ran after the one before failed
    lines = audit_lines()
    assert [e["result"] for e in lines] == ["failed: NonZeroExit", "failed: TimeoutExpired",
                                            "failed: NonZeroExit"], lines
    assert [e["summary"] for e in lines] == ["Background refresh: singer-paid", "Background refresh: dashboard",
                                             "Background refresh: books"], lines
    assert all(e["action"] == "refresh-job" for e in lines)
    assert "secret" not in json.dumps(lines) and "12345678" not in json.dumps(lines)
    rec = Recorder(fail={"books": OSError("/Users/someone/secret path")})
    jobs.RefreshJob(clear=lambda: None, runner=rec).run_once()
    assert audit_lines()[-1]["result"] == "failed: OSError" and "secret" not in json.dumps(audit_lines())
    # a failing clear() is logged too, never raised
    def boom():
        raise RuntimeError("private")
    assert jobs.RefreshJob(clear=boom, runner=Recorder()).run_once() == "failed"
    assert audit_lines()[-1]["result"] == "failed: RuntimeError"


def test_refresh_job_never_overlaps_a_manual_refresh():
    clean()
    rec = Recorder()
    job = jobs.RefreshJob(clear=lambda: None, runner=rec)
    assert actions._LOCKS["refresh"].acquire(timeout=1)
    try:
        assert job.run_once() == "skipped" and rec.calls == []
    finally:
        actions._LOCKS["refresh"].release()
    assert job._lock.acquire(timeout=1)  # its own lock: a second job pass is skipped too
    try:
        assert job.run_once() == "skipped" and rec.calls == []
    finally:
        job._lock.release()
    # while the job runs, it holds the manual refresh's lock
    assert job.run_once() == "ok" and all(rec.locked)


def test_refresh_job_is_off_in_tests_and_dev_and_on_for_the_service():
    fixtures()
    assert make(FakeBank()).app.state.refresh_job is None
    app = create_app(client_factory=lambda: None, now=lambda: NOW, checkout=lambda: "main", watch=True)
    assert isinstance(app.state.refresh_job, jobs.RefreshJob)
    os.environ["CC_NO_REFRESH_JOB"] = "1"
    try:
        app = create_app(client_factory=lambda: None, now=lambda: NOW, checkout=lambda: "main", watch=True)
        assert app.state.refresh_job is None
    finally:
        os.environ.pop("CC_NO_REFRESH_JOB")


def test_refresh_job_loop_stops_and_survives_a_bad_pass():
    calls = []

    class Job(jobs.RefreshJob):
        def tick(self, now):
            calls.append(now)
            if len(calls) == 1:
                raise RuntimeError("private detail")
            if len(calls) >= 3:
                stop.set()
            return False

    stop = None

    async def go():
        nonlocal stop
        stop = asyncio.Event()
        await asyncio.wait_for(jobs.loop(Job(clear=lambda: None, runner=Recorder()), stop, poll=0,
                                         now=lambda: NOW), timeout=5)

    asyncio.run(go())
    assert len(calls) == 3


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
                print(f"FAIL {name}: {type(e).__name__}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
