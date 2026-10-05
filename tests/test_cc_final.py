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
        ("2005", "Invoice email not sent (>2 days): check Zoho Drafts"),
        ("2010", "Starling matched, Books unpaid"),
    }, got
    # Starling not checked: the two comparisons are skipped, as 6g skips them; the draft rule stays
    flags = models.books_flags(invoices, ledger, bookings, TODAY, False)
    assert {(f["ref"], f["text"]) for f in flags} == {("2005", "Invoice email not sent (>2 days): check Zoho Drafts")}
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
    assert "1212" in base and "Invoice email not sent (>2 days): check Zoho Drafts" in base, base[:3000]
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
    assert f == [{"ref": "INV2001", "text": "Invoice email not sent (>2 days): check Zoho Drafts", "tone": "warn",
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
    for path in ("/money", "/bookings/0310"):
        out = text_of(page(c, path))
        assert "couldn't load (ValueError)" in out, (path, out[:1500])
    # Today names it, and its count is a floor, never a green 0
    out = text_of(page(c, "/"))
    assert "Some sources didn't load: the Books cache (ValueError)." in out, out[:1500]
    assert re.search(r"at least \d+ things? needs? you", out) and "Nothing needs you" not in out, out[:1500]
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
    assert std["organist"] == 250 and std["soloist_organist"] is None
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
    assert quote.calculate(lists, "standard", "soloist", organist=True)["total"] == 500
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


# ---------------------------------------------------------------- marketing panels (cc_sync.py marketing)


def marketing_json(generated_at="2026-09-28T07:00:00+01:00"):
    weeks = [{"week_start": (datetime.date(2026, 8, 3) + datetime.timedelta(weeks=i)).isoformat(), "form": i % 3,
              "whatsapp": i, "email": 1, "call": 0, "other": 0, "message": 0, "form_error": 1 if i == 5 else 0}
             for i in range(8)]
    return {"generated_at": generated_at,
            "search_terms": {"looked_at": 12, "items": [
                {"term": "wedding singer london", "campaign": "Weddings", "clicks_7": 2, "cost_7": 3.1, "clicks_28": 6,
                 "cost_28": 8.0, "impressions_28": 45, "why": "solo-singer search ('singer'): choirs of four or more only"},
                {"term": "<script>alert(1)</script> lyrics", "campaign": "Funerals", "clicks_7": 0, "cost_7": 0,
                 "clicks_28": 1, "cost_28": 0.9, "impressions_28": 4, "why": "not a hiring search ('lyrics')"}]},
            "shortlist": {"start": "2026-08-29", "end": "2026-09-25", "items": [
                {"query": "funeral choir hire london", "page": "/funerals.html", "position": 11.2, "impressions": 60,
                 "clicks": 1, "fix": "add an internal link from a related page with anchor 'funeral choir hire london'"},
                {"query": "odd page", "page": "javascript:alert(1)", "position": 9, "impressions": 20, "clicks": 0,
                 "fix": "x"}]},
            "leads": {"weeks": weeks, "thresholded": True}}


def test_marketing_panels_render_from_the_cache():
    fixtures()
    write(CACHE / "marketing.json", json.dumps(marketing_json()))
    out = page(make(FakeBank()), "/marketing")
    t = text_of(out)
    assert "Still to come" not in t
    assert "Search terms to check" in t and "wedding singer london" in t and "Weddings" in t and "£8.00" in t
    assert "solo-singer search ('singer'): choirs of four or more only" in t
    assert "negatives are proposed in the Monday review and applied only after you approve them" in t
    assert "<script>alert(1)" not in out and "&lt;script&gt;alert(1)&lt;/script&gt; lyrics" in out
    assert "Search Console shortlist" in t and "Sat 29 Aug 2026 to Fri 25 Sep 2026" in t
    assert "funeral choir hire london" in t and "/funerals.html" in t and "11.2" in t
    assert "javascript:" not in out  # a page that isn't a site path shows as "/"
    assert "GA4 leads by week" in t and 'aria-labelledby="leads-title leads-desc"' in out
    assert out.count('<rect class="bar"') == 8 and "week of 21 Sep: 1 form enquiry, 8 WhatsApp or email taps" in out
    assert "Weekly form enquiries (bars) and WhatsApp or email taps (line)" in t
    assert "Form errors in these weeks: 1." in t and "thresholded" in t
    assert t.count("As of Mon 28 Sep 2026, 07:00") == 3, t
    assert "More than 36 hours old" not in t and "Not synced yet" not in t
    assert "couldn't load" not in t


def test_marketing_panels_not_synced_and_stale():
    fixtures()
    t = text_of(page(make(FakeBank()), "/marketing"))
    assert t.count("Not synced yet: the refresh job writes this once a day") == 3, t
    assert "Search terms to check" in t and "GA4 leads by week" in t
    write(CACHE / "marketing.json", json.dumps(marketing_json("2026-09-26T21:29:00+01:00")))  # 36 h 1 min old
    t = text_of(page(make(FakeBank()), "/marketing"))
    assert t.count("More than 36 hours old") == 3 and "Not synced yet" not in t, t
    write(CACHE / "marketing.json", json.dumps(marketing_json("2026-09-26T21:31:00+01:00")))  # 35 h 59 min
    assert "More than 36 hours old" not in text_of(page(make(FakeBank()), "/marketing"))
    write(CACHE / "marketing.json", json.dumps(marketing_json("not a time")))
    t = text_of(page(make(FakeBank()), "/marketing"))
    assert "As of an unknown time" in t and "More than 36 hours old" in t
    write(CACHE / "marketing.json", "[1, 2]")  # not an object: the panels say so and the page still renders
    t = text_of(page(make(FakeBank()), "/marketing"))
    assert "couldn't load (ValueError)" in t and "Ads change sets to approve" in t, t
    empty = dict(marketing_json(), search_terms={"items": [], "looked_at": 7}, shortlist={"start": "2026-08-29",
                 "end": "2026-09-25", "items": []}, leads={"weeks": [], "thresholded": False})
    write(CACHE / "marketing.json", json.dumps(empty))
    t = text_of(page(make(FakeBank()), "/marketing"))
    assert "No search term flagged in the last 28 days (7 looked at)" in t
    assert "No hiring-intent query at positions 8 to 20" in t and "No weekly GA4 figures in the cache" in t


def test_health_lists_the_marketing_cache():
    fixtures()
    t = text_of(page(make(FakeBank()), "/health"))
    assert "Marketing cache (cc_sync.py marketing, daily)" in t


# ---------------------------------------------------------------- background refresh


class Recorder:
    def __init__(self, fail=None):
        self.calls, self.fail, self.locked = [], fail or {}, []

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        self.locked.append(actions._LOCKS["refresh"].locked())
        what = {"books": "books", "--apply": "singer-paid", "marketing": "marketing"}.get(argv[-1], "dashboard")
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
    assert jobs.SCRIPTS[0] == ("singer-paid", ["scripts/bookings/singer_invoices.py", "paid", "--apply"], 180, False)
    assert jobs.SCRIPTS[-1] == ("marketing", ["scripts/reports/cc_sync.py", "marketing"], 300, True)
    for argv, kw in rec.calls:
        assert argv[0] == sys.executable and kw["shell"] is False and 0 < kw["timeout"] <= 600
        assert kw["env"]["LCS_PRIVATE_DIR"] == TMP and not any(k.startswith("CC_") for k in kw["env"])
        assert kw["stdin"] == subprocess.DEVNULL
    assert cleared == [1] and all(rec.locked)
    assert not actions._LOCKS["refresh"].locked()
    assert audit_lines() == []  # a clean run is not logged


def test_refresh_job_runs_the_daily_scripts_in_the_first_pass_of_each_day_only():
    clean()
    rec = Recorder()
    job = jobs.RefreshJob(clear=lambda: None, runner=rec)
    daily = [what for what, _, _, is_daily in jobs.SCRIPTS if is_daily]
    assert daily == ["marketing"]
    # a fake clock over two days: every pass runs the half-hourly scripts, the 07:00 pass alone adds marketing
    t, passes = at(0, 0), []
    while t < at(0, 0, day=30):
        before = len(rec.calls)
        if job.tick(t):
            passes.append((t, [c[0][-1] for c in rec.calls[before:]]))
        t += datetime.timedelta(minutes=1)
    with_marketing = [p for p, argv in passes if "marketing" in argv]
    assert with_marketing == [at(7, 0), at(7, 0, day=29)], with_marketing
    assert len(passes) == 62 and all(len(argv) == (4 if p.time() == datetime.time(7, 0) else 3) for p, argv in passes)
    first = next(argv for p, argv in passes if p == at(7, 0))
    assert first == ["--apply", str(Path(ROOT) / "scripts/reports/dashboard.py"), "books", "marketing"], first
    # the service started at 14:10: its first pass that day runs marketing, the next ones don't
    rec = Recorder()
    job = jobs.RefreshJob(clear=lambda: None, runner=rec)
    assert job.tick(at(14, 10)) and rec.calls[-1][0][-2:] == [str(Path(ROOT) / "scripts/reports/cc_sync.py"),
                                                              "marketing"]
    n = len(rec.calls)
    assert job.tick(at(14, 30)) and len(rec.calls) == n + 3
    # a first slot skipped as busy (a manual refresh) leaves marketing for the next pass
    rec = Recorder()
    job = jobs.RefreshJob(clear=lambda: None, runner=rec)
    assert actions._LOCKS["refresh"].acquire(timeout=1)
    try:
        assert job.tick(at(7, 0)) and rec.calls == []
    finally:
        actions._LOCKS["refresh"].release()
    assert job.tick(at(7, 30)) and [c[0][-1] for c in rec.calls][-1] == "marketing"
    # a failed marketing sync is logged by type and not retried until tomorrow
    rec = Recorder(fail={"marketing": 1})
    job = jobs.RefreshJob(clear=lambda: None, runner=rec)
    assert job.run_once(at(7, 0)) == "failed"
    assert audit_lines()[-1]["summary"] == "Background refresh: marketing"
    assert audit_lines()[-1]["result"] == "failed: NonZeroExit"
    assert job.run_once(at(7, 30)) == "ok" and "marketing" not in [c[0][-1] for c in rec.calls[4:]]
    # run_once() with no clock (a direct call) never runs a daily script
    rec = Recorder()
    assert jobs.RefreshJob(clear=lambda: None, runner=rec).run_once() == "ok" and len(rec.calls) == 3


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


# ---------------------------------------------------------------- reliability: the thread pool, Today, refresh


class CountingBank(FakeBank):
    def __init__(self):
        self.calls = 0

    def feed(self, since, until, direction):
        self.calls += 1
        return []


def needs_rows(html):
    return [(k, int(n)) for k, n in re.findall(r'<li class="need[^"]*" data-kind="([^"]+)" data-count="(\d+)">', html)]


def lede_number(html):
    m = re.search(r'<span class="count[^"]*">\s*(?:at least )?(\d+|\?)\s*<', html)
    return m.group(1) if m else None


def blocks_nothing(patch_owner, name, request):
    """Patch patch_owner.name to wait until released, start `request(c)` in a thread, and check that /healthz and
    another page still answer meanwhile (the slow work runs in the thread pool, not on the event loop)."""
    import time
    started, release = threading.Event(), threading.Event()
    real = getattr(patch_owner, name)

    def slow(*a, **kw):
        started.set()
        release.wait(10)
        return real(*a, **kw)

    setattr(patch_owner, name, slow)
    got = []
    try:
        app = create_app(client_factory=lambda: FakeBank(), now=lambda: NOW, clock=Clock(), checkout=lambda: "main")
        with TestClient(app, base_url=ORIGIN, client=LOCAL) as c:
            t = threading.Thread(target=lambda: got.append(request(c).status_code))
            t.start()
            assert started.wait(5), name
            t0 = time.monotonic()
            assert c.get("/healthz").status_code == 200
            assert c.get("/passkeys", headers=HEADERS).status_code == 200
            assert time.monotonic() - t0 < 3 and not got, (name, got)  # answered while the slow one waited
            release.set()
            t.join(10)
    finally:
        release.set()
        setattr(patch_owner, name, real)
    return got


def test_pages_exports_and_previews_run_in_the_thread_pool():
    fixtures()
    assert blocks_nothing(data.Data, "money_page", lambda c: c.get("/money", headers=HEADERS)) == [200]
    assert blocks_nothing(data.Data, "today_page", lambda c: c.get("/", headers=HEADERS)) == [200]
    assert blocks_nothing(data.Data, "export", lambda c: c.get("/exports/bookings.csv", headers=HEADERS)) == [200]
    assert blocks_nothing(actions, "list_proposals", lambda c: c.get("/marketing", headers=HEADERS)) == [200]
    assert blocks_nothing(actions, "fields", lambda c: c.post("/actions/refresh-data/preview", json={"input": {}},
                                                               headers=POST_HEADERS)) == [200]


def test_refresh_post_drops_the_bank_cache_and_no_get_does():
    fixtures()
    bank = CountingBank()
    c = make(bank)
    page(c, "/money")
    first = bank.calls
    page(c, "/money")
    assert bank.calls == first  # cached
    assert c.get("/refresh", headers=HEADERS).status_code == 405  # a GET changes nothing
    assert c.post("/refresh", headers=HEADERS).status_code == 403  # same-origin, like every POST
    r = c.post("/refresh", headers=POST_HEADERS)
    assert r.status_code == 204 and r.content == b""
    page(c, "/money")
    assert bank.calls > first  # read afresh
    base = page(c, "/")
    link = re.search(r'<a class="button quiet cc-refresh"[^>]*>Refresh</a>', base).group(0)
    assert 'hx-trigger="cc-refresh"' in link and 'hx-get="/"' in link and 'href="/"' in link
    assert '<script src="/static/swap.js" defer></script>' in base and 'id="cc-swap-error"' in base
    js = (Path(ROOT) / "command_centre" / "static" / "swap.js").read_text()
    assert 'fetch("/refresh", { method: "POST"' in js and 'htmx.trigger(link, "cc-refresh")' in js
    assert "htmx:responseError" in js and "htmx:sendError" in js
    assert "/static/swap.js" in (Path(ROOT) / "command_centre" / "static" / "sw.js").read_text()


def test_scripts_survive_a_refresh_swap():
    """The Refresh link swaps #main, so a listener bound to an element inside it at load would be lost: the page
    scripts listen on the document instead."""
    static = Path(ROOT) / "command_centre" / "static"
    passkey = (static / "passkey.js").read_text()
    assert 'document.addEventListener("click"' in passkey and 'closest("#pk-register, #pk-test")' in passkey
    assert "reg.addEventListener" not in passkey and "test.addEventListener" not in passkey
    push_js = (static / "push.js").read_text()
    assert 'document.addEventListener("click"' in push_js and 'document.addEventListener("htmx:load"' in push_js
    assert not re.search(r"(enable|approve|off|clearButton)\.addEventListener", push_js)
    todo_js = (static / "todo.js").read_text()
    assert 'document.addEventListener("submit"' in todo_js and "querySelectorAll" not in todo_js
    for name in ("passkey.js", "push.js", "todo.js", "swap.js"):
        assert "https:" not in (static / name).read_text() and "eval(" not in (static / name).read_text(), name


def test_manual_refresh_waits_for_a_background_pass_then_says_so():
    fixtures()
    c = make(FakeBank())
    saved = actions.REFRESH_WAIT
    actions.REFRESH_WAIT = 0.2
    lock = actions._LOCKS["refresh"]
    assert lock.acquire(timeout=1)
    try:
        actions.BACKGROUND_REFRESH.set()
        r = c.post("/actions/refresh-data/run", json={"input": {}}, headers=POST_HEADERS)
        assert r.status_code == 409 and r.json()["error"] == actions.BACKGROUND_BUSY, r.text
        assert audit_lines()[-1]["result"] == "refused: a background refresh is running"
        actions.BACKGROUND_REFRESH.clear()  # another manual refresh holds it: the usual answer
        r = c.post("/actions/refresh-data/run", json={"input": {}}, headers=POST_HEADERS)
        assert r.status_code == 409 and r.json()["error"].startswith("another action is running"), r.text
    finally:
        actions.BACKGROUND_REFRESH.clear()
        lock.release()
        actions.REFRESH_WAIT = saved
    assert saved == 20 and actions.RUN_WAIT == 5
    # the wait is real: a pass that ends within it lets the manual refresh run
    ran = []
    saved_runner = actions.RUNNER
    actions.RUNNER = lambda argv, **kw: ran.append(argv) or subprocess.CompletedProcess(argv, 0, b"", b"")
    assert lock.acquire(timeout=1)
    actions.BACKGROUND_REFRESH.set()

    def finish():
        actions.BACKGROUND_REFRESH.clear()
        lock.release()
    timer = threading.Timer(0.5, finish)
    timer.start()
    try:
        r = c.post("/actions/refresh-data/run", json={"input": {}}, headers=POST_HEADERS)
        assert r.status_code == 200 and r.json()["ok"] and len(ran) == 2, r.text
    finally:
        timer.join()
        actions.RUNNER = saved_runner


def test_refresh_job_flags_its_pass_and_tidies_the_mirror():
    clean()
    seen, tidied = [], []

    def runner(argv, **kw):
        seen.append(actions.BACKGROUND_REFRESH.is_set())
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    job = jobs.RefreshJob(clear=lambda: None, runner=runner, tidy=lambda: tidied.append(1))
    assert job.run_once() == "ok"
    assert seen == [True, True, True] and tidied == [1] and not actions.BACKGROUND_REFRESH.is_set()

    def boom():
        raise OSError("/Users/someone/private")
    assert jobs.RefreshJob(clear=lambda: None, runner=runner, tidy=boom).run_once() == "failed"
    assert audit_lines()[-1]["summary"] == "Background refresh: tidy the Ads mirror"
    assert audit_lines()[-1]["result"] == "failed: OSError" and not actions.BACKGROUND_REFRESH.is_set()
    # the real tidy: no mirror yet, nothing made; the default job uses it
    assert actions.tidy_mirror() == "none" and not actions.mirror_dir().exists()
    assert jobs.RefreshJob(clear=lambda: None).tidy is actions.tidy_mirror


def test_today_lists_drafts_follow_ups_runs_and_a_stale_backup():
    fixtures()
    c = make(FakeBank())
    base = needs_rows(page(c, "/"))
    new = {"drafts", "followups", "runs", "backup"}
    assert not new & {k for k, _ in base}, base
    # two drafts, one marked sent: one to review
    write(CACHE / "drafts.json", json.dumps([draft(thread_id="T1"), draft(thread_id="T2", created="2026-09-27")]))
    key = drafts.draft_key(draft(thread_id="T2", created="2026-09-27"))
    write(Path(TMP) / "command-centre" / "drafts-marks.json", json.dumps({key: {"state": "sent", "at": "x"}}))
    # a follow-up due (quoted 8 days ago, never chased) and one not yet due
    lm.write_csv(pl.ENQUIRIES, [
        {"enquiry_id": "e1", "first_seen": "2026-09-19", "status": "quoted", "last_contact": "2026-09-20",
         "followups": "0", "occasion": "wedding", "event_date": "2027-06-01", "source": "email"},
        {"enquiry_id": "e2", "first_seen": "2026-09-26", "status": "quoted", "last_contact": "2026-09-27",
         "followups": "0", "occasion": "wedding", "event_date": "2027-06-01", "source": "email"}], pl.COLUMNS)
    # the static dashboard last written 40 hours ago; the Ads summary never (not set up: Health's business)
    write(Path(TMP) / "dashboard.html", "<p>old</p>")
    old = (NOW - datetime.timedelta(hours=40)).timestamp()
    os.utime(Path(TMP) / "dashboard.html", (old, old))
    # a backup key, and the last backup two days ago
    cfg = auth.load_config()
    auth.save_config(dict(cfg, backup={"recipient": "age1example", "target": "/tmp/x"}))
    write(Path(TMP) / "command-centre" / "backup-state.json",
          json.dumps({"at": (NOW - datetime.timedelta(hours=50)).isoformat(), "name": "b.tar.gz.age", "size": 1}))
    html = page(c, "/")
    rows = needs_rows(html)
    assert [r for r in rows if r[0] in new] == [("drafts", 1), ("followups", 1), ("runs", 1), ("backup", 1)], rows
    assert [r for r in rows if r[0] not in new] == base, (rows, base)
    assert lede_number(html) == str(sum(n for _, n in rows)) and sum(n for _, n in rows) == sum(n for _, n in base) + 4
    out = text_of(html)
    assert "1 draft to review and send" in out and "1 follow-up due" in out
    assert "1 run hasn't written on time" in out and "Static dashboard" in out, out[:3000]
    assert "The last backup is over 36 hours old" in out
    assert "Ads summary" not in out  # never written: not a failure
    # a backup that isn't set up yet is the Health page's business, not Today's
    auth.save_config(cfg)
    assert ("backup", 1) not in needs_rows(page(c, "/"))


def test_needs_you_rules():
    P = data.Panel
    singer = lambda key, first, amount, ring=False, trusted=True: {  # noqa: E731
        "key": key, "first_name": first, "amount": amount, "ring_first": ring, "trusted": trusted and not ring}
    panels = {
        "singers": P(value=[singer("aaa", "Ann", 100.0), singer("bbb", "Bob", 50.0, ring=True),
                            singer("ccc", "Cy", 70.0)]),
        "hand": P(value=[{"ref": "0107", "state": "PAST_UNMATCHED", "label": "past, unpaid"}]),
        "bank": P(value={"assessments": [{"ref": "1", "state": "DEPOSIT_OVERDUE"}, {"ref": "2", "state": "BALANCE_DUE"},
                                         {"ref": "3", "state": "BALANCE_DUE"}, {"ref": "4", "state": "AWAITING_DEPOSIT"},
                                         {"ref": "5", "state": "ARRANGED"}]}),
        "proposals": P(value=[{"id": "a", "title": "A", "applied": False, "problem": None},
                              {"id": "b", "title": "B", "applied": True, "problem": None},
                              {"id": "c", "title": "C", "applied": False, "problem": "can't"}]),
        "books_import": P(value={"state": "stale"}),
        "bill_flags": P(value=[{"ref": "X Cy", "text": "bill paid in Books, invoice open here", "tone": "warn",
                                "href": "/singers", "key": "ccc"}]),
        "books": P(value={"invoices": []}),
    }
    rows, missing = models.needs_you(panels)
    assert [(r["kind"], r["count"]) for r in rows] == [("ring", 1), ("hand", 1), ("deposits", 1), ("balances", 2),
                                                       ("approval", 1), ("bill", 1), ("pay", 1)], rows
    pay = rows[-1]
    assert [s["first_name"] for s in pay["items"]] == ["Ann"] and pay["total"] == 100.0  # not Bob (ring), not Cy
    assert rows[3]["refs"] == ["2", "3"] and missing == []
    # the import only while it waits for approval
    rows, _ = models.needs_you(dict(panels, books_import=P(value={"state": "waiting"})))
    assert ("books-import", 1) in [(r["kind"], r["count"]) for r in rows]
    # Starling unreachable: the payment guesses go, and the bank is named
    rows, missing = models.needs_you(panels, bank_unreachable=True)
    assert not {"hand", "deposits", "balances"} & {r["kind"] for r in rows} and missing == ["the bank (Starling)"]
    # a failed root names the root once, with its error type, and its categories list nothing
    rows, missing = models.needs_you(dict(panels, singer_store=P(error="PermissionError"),
                                          singers=P(error="PermissionError")))
    assert missing == ["the singer invoices (PermissionError)"], missing
    assert not {"ring", "pay"} & {r["kind"] for r in rows}
    rows, missing = models.needs_you(dict(panels, ledger=P(error="OSError"), hand=P(error="OSError"),
                                          bank=P(error="OSError")))
    assert missing == ["the bookings ledger (OSError)"], missing
    # Books not synced (None) is information, not a failure
    rows, missing = models.needs_you(dict(panels, books=P(value=None), books_flags=P(value=None),
                                          bill_flags=P(value=None)))
    assert missing == [] and "bill" not in {r["kind"] for r in rows}


# ---------------------------------------------------------------- the sync strip


def set_age(path, hours):
    path = Path(path)
    if not path.exists():
        write(path, "[]" if path.name in ("drafts.json", "calendar.json") else "{}")
    t = (NOW - datetime.timedelta(hours=hours)).timestamp()
    os.utime(path, (t, t))


def chips(html):
    """The strip's chips: {label: (tone, element, sync source or None, href or None, shown text)}."""
    strip = re.search(r'<ul class="sync-chips"[^>]*>(.*?)</ul>', html, re.S)
    assert strip, "no sync strip"
    out = {}
    for li in re.findall(r"<li>(.*?)</li>", strip.group(1), re.S):
        m = re.search(r'<(span|a|button)[^>]*class="chip chip-(\w+)"[^>]*>(.*?)</\1>', li, re.S)
        label = re.search(r'<span class="chip-label">([^<]+)</span>', li).group(1)
        source = re.search(r'name="source" value="([^"]+)"', li)
        href = re.search(r'href="([^"]+)"', li)
        shown = text_of(li).replace(label, "", 1).split(",")[0].strip()
        out[label] = (m.group(2), m.group(1), source.group(1) if source else None, href.group(1) if href else None,
                      shown)
    return out


class DownBank(FakeBank):
    def account(self):
        import urllib.error
        raise urllib.error.URLError("down")

    def feed(self, since, until, direction):
        import urllib.error
        raise urllib.error.URLError("down")


def test_sync_strip_renders_every_tone():
    from command_centre import sources
    fixtures()
    sources.forget_outcomes()
    set_age(CACHE / "books.json", 1)                          # ok
    set_age(CACHE / "drafts.json", 40)                        # stale (over 36 hours): the app can't sync it
    (CACHE / "calendar.json").unlink(missing_ok=True)         # never written: stale, "never"
    set_age(Path(TMP) / "ads-summary.json", 48)               # ok (the Monday review, weekly)
    set_age(CACHE / "marketing.json", 2)                      # ok, until a failed attempt after it
    sources.record_outcome("marketing", False, at=NOW)
    c = make(FakeBank())
    got = chips(page(c, "/"))
    assert list(got) == ["Bank", "Books", "Drafts", "Diary", "Ads", "Marketing"], got
    assert got["Bank"] == ("ok", "span", None, None, "09:30"), got["Bank"]
    assert got["Books"] == ("ok", "span", None, None, "08:30"), got["Books"]
    assert got["Drafts"] == ("stale", "a", None, "/health#syncs", "Sat 17:30"), got["Drafts"]
    assert got["Diary"] == ("stale", "a", None, "/health#syncs", "never"), got["Diary"]
    assert got["Ads"] == ("ok", "span", None, None, "Sat 09:30"), got["Ads"]
    assert got["Marketing"] == ("failed", "button", "marketing", None, "07:30"), got["Marketing"]
    # a stale Books cache is a sync-now button; a failed attempt after the last good write says failed
    set_age(CACHE / "books.json", 25)
    assert chips(page(c, "/money"))["Books"][:3] == ("stale", "button", "books")
    set_age(CACHE / "books.json", 1)
    sources.record_outcome("books", False, at=NOW)
    assert chips(page(c, "/money"))["Books"][:3] == ("failed", "button", "books")
    sources.record_outcome("books", True, at=NOW)
    assert chips(page(c, "/money"))["Books"][:3] == ("ok", "span", None)
    # the Bank: unreachable is failed (a sync-now bank button); no client is off; a page that doesn't read the bank
    # never makes the strip read it
    down = make(DownBank())
    assert chips(page(down, "/"))["Bank"] == ("failed", "button", "bank", None, "not read yet")
    none = make(None)
    assert chips(page(none, "/"))["Bank"][:2] == ("off", "span") and "not connected" in chips(page(none, "/"))["Bank"][4]
    counted = FakeBank()
    calls = []
    counted.account = lambda: calls.append(1) or FakeBank.account(counted)
    fresh = make(counted)
    assert chips(page(fresh, "/quote"))["Bank"][4] == "not read yet" and calls == []
    # every page carries it, and a strip that fails never breaks the page
    for path in ("/", "/money", "/health", "/quote", "/drafts", "/marketing", "/enquiries", "/activity"):
        assert 'class="sync-strip"' in page(c, path), path
    real = sources.sync_chips
    sources.sync_chips = lambda now, bank: 1 / 0
    try:
        out = page(c, "/")
        assert 'class="sync-strip"' not in out and ("Needs you" in out or "Nothing needs you" in out)
    finally:
        sources.sync_chips = real
    # Health explains the ones the app can't sync
    health = text_of(page(c, "/health"))
    assert "can't read Mail or the calendar itself" in health and "Run now" in health
    sources.forget_outcomes()


def test_sync_strip_scrolls_inside_itself_on_a_phone():
    css = (Path(ROOT) / "command_centre" / "static" / "app.css").read_text()
    rule = lambda sel: re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css).group(1)  # noqa: E731
    assert "overflow-x: auto" in rule(".sync-chips") and "flex-wrap: nowrap" in rule(".sync-chips")
    assert "overflow: hidden" in rule(".sync-strip") and "min-width: 0" in rule(".sync-strip")
    assert "white-space: nowrap" in re.search(r"\n\.chip \{([^}]*)\}", css).group(1)


def test_the_refresh_job_notes_each_sync_for_the_strip():
    from command_centre import sources
    clean()
    sources.forget_outcomes()
    job = jobs.RefreshJob(clear=lambda: None, runner=Recorder(fail={"books": 1}))
    assert job.run_once(at(7, 0)) == "failed"
    got = {k: v["ok"] for k, v in sources.outcomes().items()}
    assert got == {"singer-paid": True, "dashboard": True, "books": False, "marketing": True}, got
    job = jobs.RefreshJob(clear=lambda: None, runner=Recorder())
    assert job.run_once() == "ok" and sources.outcomes()["books"]["ok"] is True
    sources.forget_outcomes()


def test_sync_strip_chip_times():
    from command_centre import sources
    now = NOW
    assert sources.short_time(now - datetime.timedelta(minutes=5), now) == "09:25"
    assert sources.short_time(now - datetime.timedelta(days=2), now) == "Sat 09:30"
    assert sources.short_time(now - datetime.timedelta(days=20), now) == "8 Sep"


# ---------------------------------------------------------------- enquiries waiting over a day


def enquiry(eid, first_seen, status="new", occasion="wedding"):
    return {"enquiry_id": eid, "first_seen": first_seen, "status": status, "last_contact": first_seen,
            "followups": "0", "occasion": occasion, "source": "email", "event_date": "2027-06-01"}


def test_enquiries_waiting_over_a_day_count_each_once_and_skip_drafted_threads():
    fixtures()
    lm.write_csv(pl.ENQUIRIES, [
        enquiry("e1", "2026-09-26"),                    # two days: waiting
        enquiry("e1", "2026-09-26"),                    # the same enquiry twice: counted once
        enquiry("e2", "2026-09-27", occasion="funeral"),  # yesterday: its midnight is 33.5 hours ago
        enquiry("e3", "2026-09-28"),                    # today: not yet
        enquiry("e4", "2026-09-25"),                    # drafted: the assistant has a reply waiting in Drafts
        enquiry("e5", "2026-09-20", status="quoted"),  # already quoted
        enquiry("e6", "2026-09-20", status="lost"),
    ], pl.COLUMNS)
    write(CACHE / "drafts.json", json.dumps([draft(thread_id="e4")]))
    key = drafts.draft_key(draft(thread_id="e4"))  # a draft marked sent still counts as drafted
    write(Path(TMP) / "command-centre" / "drafts-marks.json", json.dumps({key: {"state": "sent", "at": "x"}}))
    c = make(FakeBank())
    html = page(c, "/")
    rows = needs_rows(html)
    assert ("waiting", 2) in rows, rows
    assert lede_number(html) == str(sum(n for _, n in rows))
    li = re.search(r'data-kind="waiting".*?</li>', html, re.S).group(0)
    assert "2 enquiries waiting over a day for a reply" in text_of(li) and 'href="/enquiries"' in li
    assert "Sat 26 Sep 2026" in text_of(li) and "e1" not in li and "Ann" not in li
    # the rule itself: first_seen's midnight (London) more than 24 hours ago
    rows_ = [enquiry("x", "2026-09-27")]
    edge = datetime.datetime(2026, 9, 28, 0, 0, tzinfo=LONDON)
    assert models.enquiries_waiting(rows_, None, edge) == []
    assert [e["enquiry_id"] for e in models.enquiries_waiting(rows_, None, edge + datetime.timedelta(seconds=1))] == ["x"]
    assert models.enquiries_waiting(rows_, ([{"thread_id": "x"}], None), NOW) == []
    # one enquiry: singular words
    lm.write_csv(pl.ENQUIRIES, [enquiry("e1", "2026-09-26")], pl.COLUMNS)
    assert "1 enquiry waiting over a day for a reply" in text_of(page(c, "/"))
    # a drafts cache that won't load: the row can't be trusted, so it goes and the source is named
    write(CACHE / "drafts.json", json.dumps({"not": "a list"}))
    html = page(c, "/")
    assert "waiting" not in {k for k, _ in needs_rows(html)}
    assert "the drafts inbox (ValueError)" in text_of(html)


# ---------------------------------------------------------------- the singer pay list


def pay_fixtures():
    fixtures(books=False)
    base = {"payee": "", "bank_changed": "no", "bank_confirmed": "", "paid_on": "", "paid_verified": "",
            "withdrawn": "", "booking_ref": "0310"}
    lm.write_csv(si.STORE, [dict(base, **r) for r in [
        {"message_id": "m1", "received": "2026-09-20", "singer_name": "Ben Fenwickson", "singer_email": "ben@example.org",
         "invoice_ref": "BF-12", "amount_gbp": "120", "bank_fp": "abc", "bank_last4": "4321", "bank_confirmed": "yes"},
        {"message_id": "m2", "received": "2026-09-22", "singer_name": "Dora Quillfeather", "singer_email": "dora@example.org",
         "invoice_ref": "DQ7", "amount_gbp": "150", "bank_fp": "def", "bank_last4": "1111", "bank_confirmed": "yes",
         "paid_on": "2026-09-25"},
        {"message_id": "m3", "received": "2026-09-23", "singer_name": "Zed Mistakeham", "singer_email": "zed@example.org",
         "invoice_ref": "Z1", "amount_gbp": "80", "bank_fp": "zzz", "bank_last4": "9999", "bank_confirmed": "yes",
         "withdrawn": "2026-09-24"},
        {"message_id": "m4", "received": "2026-09-24", "singer_name": "Eve Organstone", "singer_email": "eve@example.org",
         "invoice_ref": "EO1", "amount_gbp": "250", "bank_fp": "eee", "bank_last4": "2222"},
        {"message_id": "m5", "received": "2026-09-01", "singer_name": "Eve Organstone", "singer_email": "eve@example.org",
         "invoice_ref": "EO0", "amount_gbp": "250", "bank_fp": "eee", "bank_last4": "2222", "paid_on": "2026-09-05",
         "paid_verified": "yes"},
        {"message_id": "m6", "received": "2026-09-10", "singer_name": "Fay Ringwood", "singer_email": "fay@example.org",
         "invoice_ref": "FR1", "amount_gbp": "100", "bank_fp": "ff01", "bank_last4": "3333", "paid_on": "2026-09-12",
         "paid_verified": "yes"},
        {"message_id": "m7", "received": "2026-09-26", "singer_name": "Fay Ringwood", "singer_email": "fay@example.org",
         "invoice_ref": "FR2", "amount_gbp": "100", "bank_fp": "ff02", "bank_last4": "4444", "bank_changed": "yes"},
        {"message_id": "m8", "received": "2026-09-21", "singer_name": "Gus Newman", "singer_email": "gus@example.org",
         "invoice_ref": "INV-1234567", "amount_gbp": "75", "bank_fp": "ggg", "bank_last4": "5555"},
        {"message_id": "m9", "received": "2026-09-22", "singer_name": "Hal Nodetails", "singer_email": "hal@example.org",
         "invoice_ref": "H1", "amount_gbp": "60", "bank_fp": "", "bank_last4": ""},
        {"message_id": "m10", "received": "2026-09-25", "singer_name": "Ivy Payee", "singer_email": "ivy@example.org",
         "invoice_ref": "IP-3", "amount_gbp": "90", "bank_fp": "iii", "bank_last4": "6666",
         "payee": "existing: Ivy Payee"},
        {"message_id": "m11", "received": "2026-09-19", "singer_name": "Jo Booksdone", "singer_email": "jo@example.org",
         "invoice_ref": "JO-1", "amount_gbp": "55", "bank_fp": "jjj", "bank_last4": "7777", "bank_confirmed": "yes"},
    ]], si.COLUMNS)
    bills = [{"number": "BF-12", "vendor": "Ben", "status": "open", "total": 120.0, "balance": 120.0, "date": "2026-09-20"},
             {"number": "JO-1", "vendor": "Jo", "status": "paid", "total": 55.0, "balance": 0.0, "date": "2026-09-19"}]
    write(CACHE / "books.json", json.dumps(books_json(bills=bills)))


def singer_card(html):
    return re.search(r'<article class="card card-wide" id="singer-invoices">(.*?)</article>', html, re.S).group(1)


def test_money_pay_list_is_trusted_accounts_only_and_matches_today():
    pay_fixtures()
    c = make(FakeBank())
    card = singer_card(page(c, "/money"))
    table = re.search(r'<table class="table pay-table"[^>]*>(.*?)</table>', card, re.S).group(1)
    names = re.findall(r'data-label="Singer">([^<]+)<', table)
    assert names == ["Ben", "Eve", "Ivy"], names  # trusted only, oldest first
    # each amount and bill number is a copy button (handoffs.js: no passkey, not an action form)
    for amount, bill in (("120.00", "BF-12"), ("250.00", "EO1"), ("90.00", "IP-3")):
        assert f'class="button quiet small cc-copy copy-value" data-prompt="{amount}"' in table, amount
        assert f'data-prompt="{bill}"' in table, bill
    assert 'data-prompt="460.00"' in table and "£460.00" in text_of(table)  # the total
    assert "••••4321" in table and "••••2222" in table and "••••6666" in table
    trust = text_of(table)
    assert "confirmed by phone" in trust and "paid to verifiably" in trust and "Starling payee" in trust
    assert text_of(page(c, "/money")).count("Pay in the Starling app") == 1
    # ring first below it, with the reason; then the ones to confirm; Books-paid named, withdrawn and paid never
    ring = card[card.index('id="singer-ring"'):card.index('id="singer-confirm"')]
    assert "Fay" in ring and models.RING_REASON in text_of(ring) and "cc-copy" not in ring
    confirm = card[card.index('id="singer-confirm"'):]
    assert "Gus" in confirm and "Hal" in confirm and models.NEW_REASON in text_of(confirm)
    assert models.NO_BANK_REASON in text_of(confirm) and "cc-copy" not in confirm
    assert "SI-" not in card and "1234567" not in card
    assert "Books already shows that bill paid" in text_of(card) and "Jo" in text_of(card)
    assert "Jo" not in names and "Zed" not in card and "Dora" not in card
    # Today's pay row is exactly this list
    today = page(c, "/")
    rows = dict((k, n) for k, n in needs_rows(today) if k in ("pay", "confirm"))
    assert rows == {"pay": 3, "confirm": 2}, needs_rows(today)
    li = re.search(r'data-kind="pay".*?</li>', today, re.S).group(0)
    assert "Pay 3 singer invoices, £460.00" in text_of(li) and "(Ben, Eve, Ivy)" in text_of(li)
    li = re.search(r'data-kind="confirm".*?</li>', today, re.S).group(0)
    assert "Confirm the bank details on 2 singer invoices before paying" in text_of(li) and "(Gus, Hal)" in text_of(li)
    assert ("ring", 1) in needs_rows(today) and ("bill", 1) in needs_rows(today)
    assert lede_number(today) == str(sum(n for _, n in needs_rows(today)))
    # the model agrees with itself: pay + ring + confirm + books_paid is every open invoice, once
    singers = data.open_singers(lm.read_csv(si.STORE))
    split = models.singer_pay_list(singers, models.singer_bill_flags(lm.read_csv(si.STORE), json.loads(
        (CACHE / "books.json").read_text())["bills"]))
    keys = [s["key"] for part in ("pay", "ring", "confirm", "books_paid") for s in split[part]]
    assert sorted(keys) == sorted(s["key"] for s in singers) and len(keys) == len(set(keys)) == 7
    assert split["total"] == 460.0


def test_pay_list_trust_rules():
    rows = [{"message_id": "a", "singer_name": "Ann Test", "singer_email": "a@example.org", "bank_fp": "f1",
             "bank_changed": "no", "payee": "existing: Ann Test", "invoice_ref": "A-1"}]
    t = models.singer_trust(rows, rows[0])
    assert t == {"trusted": True, "trust": "Starling payee", "reason": "", "held": [], "bill_number": "A-1"}, t
    # a payee named but the details changed since: never trusted from the payee alone
    changed = dict(rows[0], bank_changed="yes")
    t = models.singer_trust([changed], changed)
    assert t["trusted"] is False and t["reason"] == models.RING_REASON
    # no details: not trusted, and a bill number with a long digit run falls back to SI- plus 5 digits
    none = {"message_id": "1789828736363141700", "singer_name": "Bo Test", "bank_fp": "", "invoice_ref": "123456789"}
    t = models.singer_trust([none], none)
    assert t["trusted"] is False and t["reason"] == models.NO_BANK_REASON and t["bill_number"] == "SI-41700"


def test_health_marks_an_old_static_dashboard_stale():
    from command_centre import sources
    fixtures()
    write(Path(TMP) / "dashboard.html", "x")
    for hours, stale in ((30, False), (37, True)):
        t = (NOW - datetime.timedelta(hours=hours)).timestamp()
        os.utime(Path(TMP) / "dashboard.html", (t, t))
        row = {r["label"]: r for r in sources.run_proxies(NOW)[0]}["Static dashboard"]
        assert row["stale"] is stale, (hours, row)


def test_activity_filters_the_refresh_job_and_timeouts():
    fixtures()
    actions.write_audit("refresh-job", "Background refresh: books", jobs.SYSTEM_USER, "failed: NonZeroExit")
    actions.write_audit("refresh-data", "Refresh data now", {"login": LOGIN}, "timed out")
    actions.write_audit("todo-tick", "tick", {"login": LOGIN}, "ok")
    c = make(FakeBank())
    html = page(c, "/activity")
    assert '<option value="refresh-job"' in html and '<option value="timed out"' in html
    out = text_of(page(c, "/activity?action=refresh-job"))
    assert "Background refresh: books" in out and "tick" not in out.split("Filter")[-1], out[-1500:]
    out = text_of(page(c, "/activity?result=timed+out"))
    assert "Refresh data now" in out.split("Filter")[-1] and "Background refresh" not in out.split("Filter")[-1]


def test_quote_page_without_an_organist_row():
    fixtures()
    real = quote.load_lists

    def no_organist(root=quote.REPO):
        lists = real(root)
        for v in lists.values():
            v["organist"], v["organist_name"], v["soloist_organist"] = None, "", None
        return lists
    data.quote.load_lists = no_organist
    try:
        c = make(FakeBank())
        out = text_of(page(c, "/quote?list=standard&package=small-choir"))
        assert "No organist price on this page" in out and "£1,150" in out, out[:2000]
        assert 'name="organist"' not in page(c, "/quote")
        assert page(c, "/quote?list=standard&package=small-choir&organist=yes")  # refused quietly, no crash
    finally:
        data.quote.load_lists = real


def test_enquiries_follow_ups_card_shows_its_own_failure():
    fixtures()
    real = pl.followups_due
    pl.followups_due = lambda rows, today: (_ for _ in ()).throw(KeyError("e1 private"))
    try:
        out = text_of(page(make(FakeBank()), "/enquiries"))
        card = out[out.index("Follow-ups due"):]
        assert card.startswith("Follow-ups due couldn't load (KeyError)"), card[:200]
        assert "private" not in out
    finally:
        pl.followups_due = real


def test_dead_code_and_stale_text_are_gone():
    import inspect
    from command_centre import app as app_module
    assert not hasattr(app_module, "SOON") and not hasattr(actions, "archived")
    assert "cache" not in inspect.signature(models.enquiry_items).parameters
    assert "cache" not in inspect.signature(models.enquiry_timeline).parameters
    assert "cache" not in inspect.signature(models.booking_enquiries).parameters
    root = Path(ROOT) / "command_centre"
    assert "soon" not in (root / "templates" / "base.html").read_text()
    assert ".soon" not in (root / "static" / "app.css").read_text()
    for name in ("calendar.html", "marketing.html", "passkeys.html"):
        text = (root / "templates" / name).read_text()
        assert not re.search(r"phase \d", text), name
    src = inspect.getsource(app_module.create_app)
    assert src.count("models.hand_check_prompt(") == 1  # built once per ref


# ---------------------------------------------------------------- the state log on the pages (structured state, PR 5)


def fact(subject, id_, kind, fields, by, on, clause=None, src="live", eid=None):
    """Append one fact to the temp state log (an owner fact as the Command Centre's owner run would)."""
    import lcs_owner
    saved, lcs_owner._PROVEN = lcs_owner._PROVEN, True
    csv_env = os.environ.pop("LCS_BOOKINGS_CSV")
    try:
        return cp.lcs_events.append(subject, id_, kind, fields, by, on=on, src=src, eid=eid,
                                    note=cp.lcs_events.note_hash(clause) if clause else None)
    finally:
        lcs_owner._PROVEN, os.environ["LCS_BOOKINGS_CSV"] = saved, csv_env


def set_notes(ref, notes):
    rows = lm.read_csv(lm.LEDGER)
    for r in rows:
        if r["booking_ref"] == ref:
            r["notes"] = notes
    lm.write_csv(lm.LEDGER, rows, LEDGER_COLS)


def held_fixtures():
    """0915's notes say cancelled, then "back on": the recorded cancellation claims only the first clause, so the
    booking is held (cancellation); m4's recorded withdrawal was undone, but a loose "withdrawn" clause is in its
    notes, so the invoice is held (withdrawal)."""
    fixtures()
    set_notes("0915", "cancelled 2026-09-10; client says back on 2026-09-20")
    fact("booking", "0915", "cancelled", {}, "script", "2026-09-10", "cancelled 2026-09-10", src="migration",
         eid="0123456789abcdef")
    rows = lm.read_csv(si.STORE)
    for r in rows:
        if r["message_id"] == "m4":
            r["notes"] = "withdrawn 2026-09-17 (duplicate)"
    lm.write_csv(si.STORE, rows, si.COLUMNS)
    eid = fact("singer_invoice", "m4", "withdrawn", {"reason": "not-ours"}, "script", "2026-09-15")
    fact("singer_invoice", "m4", "retract", {"target": eid, "why": "mistake"}, "owner", "2026-09-16")
    cp.lcs_events.clear_cache()


def test_booking_timeline_shows_each_recorded_fact_once():
    fixtures()
    set_notes("0801", "PENDING: invoiced; paid in full 2026-07-20; 4 singers")
    fact("booking", "0801", "paid-in-full", {"basis": "owner"}, "owner", "2026-07-20", "paid in full 2026-07-20")
    fact("booking", "0801", "reminder-drafted", {"what": "deposit"}, "script", "2026-07-08")
    undone = fact("booking", "0801", "reminder-drafted", {"what": "balance"}, "script", "2026-07-15")
    fact("booking", "0801", "retract", {"target": undone, "why": "mistake"}, "owner", "2026-07-16")
    cp.lcs_events.clear_cache()
    row = next(r for r in lm.read_csv(lm.LEDGER) if r["booking_ref"] == "0801")
    booking = next(b for b in models.booking_rows([row], [], False, TODAY))
    items = [i for i in models.ledger_timeline(row, booking, TODAY) if i["kind"] in ("fact", "note")]
    got = [(i["date"].isoformat() if i["date"] else None, i["kind"], i["text"]) for i in items]
    assert ("2026-07-20", "fact", "Paid in full (you)") in got, got
    assert ("2026-07-08", "fact", "Reminder or receipt drafted (the assistant)") in got, got
    assert ("2026-07-15", "fact", "Reminder or receipt drafted (the assistant), undone on 16 Jul 2026") in got, got
    assert not any("paid in full 2026-07-20" in t for _, _, t in got), "a claimed clause is shown once, as its fact"
    assert (None, "note", "PENDING: invoiced") in got and (None, "note", "4 singers") in got, got
    assert not any(k == "fact" and "etract" in t for _, k, t in got), got
    out = text_of(page(make(FakeBank()), "/bookings/0801"))
    assert "Paid in full (you)" in out and out.count("paid in full 2026-07-20") == 0, out


def test_today_and_money_show_a_held_booking_with_both_readings():
    held_fixtures()
    c = make(FakeBank())
    for path in ("/", "/money"):
        html = page(c, path)
        out = text_of(html)
        assert "notes and recorded facts disagree: cancellation" in out, (path, out)
        assert "the notes say not cancelled; the recorded facts say cancelled" in out, (path, out)
        assert 'data-action="notes-checked"' in html and 'value="0915"' in html, path
        assert "client says" not in out and "Cancelwood" not in out, path  # never the note text or a surname
    assert text_of(page(c, "/")).count("notes and recorded facts disagree: cancellation") == 1, "a held row once"
    html = page(c, "/bookings/0915")  # its own page says so too, by the resolve form
    assert "the notes say not cancelled; the recorded facts say cancelled" in text_of(html)
    assert 'data-action="notes-checked"' in html
    assert 'data-action="notes-checked"' not in page(c, "/bookings/0310")
    # without the bank the held booking (cancelled by its recorded fact, so not open) is still a hand check
    out = text_of(page(make(None), "/"))
    assert "the notes say not cancelled; the recorded facts say cancelled" in out, out


def test_today_names_a_held_singer_invoice_as_held_not_as_changed_details():
    held_fixtures()
    c = make(FakeBank())
    html = page(c, "/")
    out = text_of(html)
    assert "Eve" in out and "notes and recorded facts disagree: withdrawal" in out, out
    assert "the notes say withdrawn; the recorded facts say not withdrawn" in out, out
    assert "Eve's bank details changed" not in out, out
    s = next(x for x in data.open_singers(lm.read_csv(si.STORE)) if x["first_name"] == "Eve")
    assert s["ring_first"] and s["reason"].startswith("notes and recorded facts disagree: withdrawal"), s
    assert s["held"] == [{"family": "withdrawal", "notes": "withdrawn", "facts": "not withdrawn",
                          "clauses": [cp.lcs_events.note_hash("withdrawn 2026-09-17 (duplicate)")]}], s["held"]
    assert 'data-action="notes-checked"' in html and 'value="singer_invoice"' in html and "m4" not in html


def test_health_shows_the_state_log():
    from command_centre import sources
    fixtures()
    c = make(FakeBank())
    got = sources.state_log_check()
    assert got["name"] == "State log" and got["ok"] is None and "no state log yet" in got["detail"], got
    set_notes("0915", "cancelled 2026-09-10")
    fact("booking", "0915", "cancelled", {}, "script", "2026-09-10", "cancelled 2026-09-10")
    fact("booking", "0310", "deposit-seen", {}, "script", "2026-09-05")
    got = sources.state_log_check()
    assert got["ok"] is True and got["detail"].startswith("2 lines, chain whole, last written "), got
    assert "State log" in text_of(page(c, "/health"))
    fact("booking", "1212", "cancelled", {}, "script", "2026-09-12", "cancelled 2026-09-12 by client email")
    got = sources.state_log_check()  # 1212's notes never got the clause: the fact decides, the record is missing
    assert got["ok"] is False and "1 fact without its note" in got["detail"] and "events.py verify" in got["detail"], got
    with open(Path(TMP) / "events.jsonl", "a") as f:
        f.write("{not json}\n")
    got = sources.state_log_check()
    assert got["ok"] is False and "1 line skipped" in got["detail"], got
    os.chmod(Path(TMP) / "events.jsonl", 0o644)
    got = sources.state_log_check()
    assert got["ok"] is False and "can't be read" in got["detail"], got
    os.chmod(Path(TMP) / "events.jsonl", 0o600)
    for secret in ("Fay", "client email", "1789"):
        assert secret not in got["detail"]


def test_singer_trust_says_when_the_details_were_confirmed():
    fixtures()
    fp = "a1b2c3d4e5f60718"
    rows = lm.read_csv(si.STORE)
    for r in rows:
        if r["message_id"] == "m4":
            r.update(bank_fp=fp, bank_confirmed="yes", notes="bank details confirmed by phone 2026-09-21")
    lm.write_csv(si.STORE, rows, si.COLUMNS)
    eve = lambda: next(g for g in models.singer_directory(lm.read_csv(si.STORE), TODAY)  # noqa: E731
                       if g["first_name"] == "Eve")
    assert eve()["bank_check"] == "confirmed by phone on 21 Sep 2026", eve()["bank_check"]
    fact("singer_invoice", "m4", "bank-confirmed", {"fp8": fp[:8]}, "owner", "2026-09-22",
         "bank details confirmed by phone 2026-09-22")
    cp.lcs_events.clear_cache()
    assert eve()["bank_check"] == "confirmed by phone on 22 Sep 2026", eve()["bank_check"]
    s = next(x for x in data.open_singers(lm.read_csv(si.STORE)) if x["first_name"] == "Eve")
    assert s["trust"] == "confirmed by phone on 22 Sep 2026", s
    assert "confirmed by phone on 22 Sep 2026" in text_of(page(make(FakeBank()), "/singers"))


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
