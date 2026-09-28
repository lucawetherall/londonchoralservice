#!/usr/bin/env python3
"""Tests for the Command Centre's pages (command_centre/app.py, data.py, templates).

Stdlib runner, Starlette's TestClient, fixture CSVs with fake people in a temp LCS_PRIVATE_DIR, and a fake
Starling client. Never touches the real private files or the real bank.
"""
import datetime, os, re, sys, tempfile, urllib.error
from zoneinfo import ZoneInfo

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from starlette.testclient import TestClient  # noqa: E402

from command_centre import auth, data  # noqa: E402
from command_centre.app import create_app  # noqa: E402

lm, si = data.lm, data.si
LONDON = ZoneInfo("Europe/London")
NOW = datetime.datetime(2026, 9, 28, 9, 30, tzinfo=LONDON)
LOGIN = "owner@example.org"
ORIGIN = "https://mac.example-tailnet.ts.net"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
LOCAL = ("127.0.0.1", 50000)  # the app refuses any peer but loopback
PAGES = ["/", "/money", "/passkeys"]
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


class FakeBank:
    """Stands in for lcs_money.StarlingReadOnly: GET-shaped methods only, counts its calls."""

    def __init__(self, fail=None):
        self.calls = 0
        self.fail = fail

    def account(self):
        self.calls += 1
        if self.fail:
            raise self.fail
        return {"accountUid": "acc-1", "defaultCategory": "cat-1"}

    def get(self, path):
        self.calls += 1
        if self.fail:
            raise self.fail
        assert path == "/api/v2/accounts/acc-1/balance", path
        return {"clearedBalance": {"minorUnits": 123456}, "effectiveBalance": {"minorUnits": 120000}}

    def feed(self, since, until, direction):
        self.calls += 1
        if self.fail:
            raise self.fail
        return []


def fixtures():
    for name in os.listdir(TMP):
        p = os.path.join(TMP, name)
        if os.path.isfile(p):
            os.remove(p)
    auth.save_config({"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": "mac.example-tailnet.ts.net",
                      "passkeys": []})
    lm.write_csv(lm.LEDGER, [
        {"booking_ref": "0310", "invoice_date": "2026-09-01", "event_date": "2026-10-03", "client_name": "Ann Smithfield",
         "client_email": "ann@example.org", "occasion": "wedding", "ensemble": "Small Choir", "value_gbp": "1150",
         "notes": "deposit paid 5 Sep"},
        {"booking_ref": "0107", "invoice_date": "2026-06-01", "event_date": "2026-07-01", "client_name": "Olly Pastmore",
         "client_email": "olly@example.org", "occasion": "funeral", "ensemble": "Quartet", "value_gbp": "650", "notes": ""},
        {"booking_ref": "1212", "invoice_date": "2026-09-20", "event_date": "2026-12-12", "client_name": "Cat Jonesworth",
         "client_email": "cat@example.org", "occasion": "carols", "ensemble": "Quartet", "value_gbp": "650", "notes": ""},
    ], LEDGER_COLS)
    lm.write_csv(si.STORE, [
        {"message_id": "m1", "received": "2026-09-20", "singer_name": "Ben Fenwickson", "singer_email": "ben@example.org",
         "amount_gbp": "120", "bank_fp": "abc", "bank_last4": "87654321", "payee": "existing: Ben Fenwickson",
         "bank_changed": "yes", "paid_on": ""},
        {"message_id": "m2", "received": "2026-09-22", "singer_name": "Dora Quillfeather",
         "singer_email": "dora@example.org", "amount_gbp": "150", "bank_fp": "def", "bank_last4": "1111",
         "payee": "", "bank_changed": "no", "paid_on": ""},
        {"message_id": "m3", "received": "2026-09-01", "singer_name": "Eve Paidup", "singer_email": "eve@example.org",
         "amount_gbp": "99", "bank_fp": "ghi", "bank_last4": "2222", "payee": "", "bank_changed": "no",
         "paid_on": "2026-09-05"},
    ], si.COLUMNS)


def make(bank=None, clock=None):
    fixtures()
    app = create_app(client_factory=(lambda: bank), now=lambda: NOW, clock=clock or Clock(),
                     checkout=lambda: "main")
    return TestClient(app, base_url=ORIGIN, client=LOCAL), app


def page(c, path):
    r = c.get(path, headers=HEADERS)
    assert r.status_code == 200, (path, r.status_code)
    return r.text


# ---------------------------------------------------------------- Today


def needs_rows(out):
    """Today's "Needs you" rows: [(kind, count, text)]."""
    return [(k, int(n), re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip())
            for k, n, body in re.findall(r'<li class="need[^"]*" data-kind="([^"]+)" data-count="(\d+)">(.*?)</li>',
                                         out, re.S)]


def plain(out):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", out))


def lede_count(out):
    m = re.search(r'<span class="count[^"]*">\s*(?:at least )?(\d+|\?)\s*<', out)
    return m.group(1) if m else None


def test_today_puts_attention_first_in_priority_order():
    c, _ = make(FakeBank())
    out = page(c, "/")
    marks = ['data-kind="ring"', 'data-kind="hand"', 'data-kind="deposits"', 'data-kind="pay"', "This week", "Later"]
    pos = [out.find(m) for m in marks]
    assert all(p >= 0 for p in pos), list(zip(marks, pos))
    assert pos == sorted(pos), list(zip(marks, pos))
    assert "ring first" in out and "before paying" in out and "••••4321" in out
    assert "0107" in out and "past, unpaid" in out          # hand check from money_report.needs_hand_check
    assert "Dora" in out and "£150.00" in out                # unpaid singer invoice
    assert "Eve" not in out                                  # paid invoices aren't shown
    assert "0310" in out and "Ann" in out and "1212" in out  # upcoming events
    assert out.find("0310") < out.find("1212")


def test_today_counts_what_needs_attention():
    c, _ = make(FakeBank())
    out = page(c, "/")
    rows = needs_rows(out)
    # Ben's changed bank details (ring first), two hand checks, 1212's overdue deposit, and Dora's invoice to pay:
    # Ben's invoice is its own row, never also in the pay group
    assert [(k, n) for k, n, _ in rows] == [("ring", 1), ("hand", 1), ("hand", 1), ("deposits", 1), ("pay", 1)], rows
    assert lede_count(out) == "5" and "5 things need you." in plain(out)
    assert "Pay 1 singer invoice, £150.00" in rows[-1][2] and "Ben" not in rows[-1][2]


def test_today_count_equals_the_rows_and_no_empty_category_shows():
    """The owner's rule: only what needs him is under Needs you, the count is the sum of the rows' own numbers, and
    a category with nothing in it adds no row and no "nothing here" text."""
    empty = ["No changed bank details waiting", "Nothing needs a hand check", "Nothing waiting for approval",
             "Books and Starling agree", "No unpaid singer invoices", "No follow-ups due"]
    c, _ = make(FakeBank())
    out = page(c, "/")
    rows = needs_rows(out)
    assert rows and int(lede_count(out)) == sum(n for _, n, _ in rows)
    assert not any(e in out for e in empty), [e for e in empty if e in out]
    # a grouped row counts its items, and says so: three open invoices to pay are 3
    store = lm.read_csv(si.STORE)
    for i, name in enumerate(["Fay Extraone", "Gil Extratwo"]):
        store.append(dict(store[1], message_id=f"x{i}", singer_name=name, singer_email=f"x{i}@example.org"))
    lm.write_csv(si.STORE, store, si.COLUMNS)
    out = page(c, "/")
    rows = needs_rows(out)
    pay =[r for r in rows if r[0] == "pay"]
    assert pay and pay[0][1] == 3 and "Pay 3 singer invoices, £450.00" in pay[0][2], pay
    assert int(lede_count(out)) == sum(n for _, n, _ in rows) == 7
    # nothing needs him: one line, no Needs you section, no empty cards
    lm.write_csv(lm.LEDGER, [], LEDGER_COLS)
    lm.write_csv(si.STORE, [], si.COLUMNS)
    out = page(c, "/")
    assert needs_rows(out) == [] and 'id="needs-you"' not in out
    assert '<span class="count ok">0</span> Nothing needs you.' in out
    assert not any(e in out for e in empty)


def test_today_leaves_out_what_is_not_yet_due():
    """A deposit not yet due, an ARRANGED balance more than 7 days out and a follow-up not yet due never show."""
    c, _ = make(FakeBank())
    lm.write_csv(lm.LEDGER, [
        {"booking_ref": "2001", "invoice_date": "2026-09-27", "event_date": "2026-12-01", "client_name": "Ivy New",
         "client_email": "ivy@example.org", "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": ""},
        {"booking_ref": "2002", "invoice_date": "2026-08-01", "event_date": "2026-11-01", "client_name": "Jo Cash",
         "client_email": "jo@example.org", "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": "deposit paid 2026-08-05 (Starling); balance to be paid in cash on the day"},
    ], LEDGER_COLS)
    lm.write_csv(si.STORE, [], si.COLUMNS)
    lm.write_csv(data.pl.ENQUIRIES, [
        {"enquiry_id": "t1", "first_seen": "2026-09-25", "status": "quoted", "last_contact": "2026-09-26",
         "notes": "quoted 2026-09-26", "occasion": "wedding", "event_date": "2027-05-01", "source": "web"},
    ], list(data.pl.COLUMNS))
    out = page(c, "/")
    assert needs_rows(out) == [], needs_rows(out)
    assert "Nothing needs you." in out


def test_today_offers_handoff_prompts_instead_of_a_chat():
    # No in-app chat: Today offers copy-to-clipboard prompts for Claude Code Remote Control. The general
    # prompts are fixed text; the hand-check prompt is picked per ref, so the page carries one option per ref
    # currently on the hand check, never a free-text field.
    c, _ = make(FakeBank())
    out = page(c, "/")
    assert "cc-copy" in out and "What&#39;s owed this week?" in out and "Summarise today&#39;s business" in out
    assert "scripts/reports/dashboard.py" in out and "scripts/bookings/money_report.py" in out
    assert '<select id="hand-handoff-select"' in out
    opt = re.search(r'<option value="0107" data-prompt="([^"]*)">0107</option>', out)
    assert opt, out
    assert "0107" in opt.group(1) and "check_payments.py" in opt.group(1) and "hand check" in opt.group(1)
    assert '<script src="/static/handoffs.js" defer></script>' in out


# ---------------------------------------------------------------- Money


def test_money_shows_balance_lines_checks_and_invoices():
    c, _ = make(FakeBank())
    out = page(c, "/money")
    for bit in ["Bank balance", "£1,234.56", "£1,200.00", "Money lines", "Needs a hand check", "0107",
                "Singer invoices unpaid", "Ben", "Dora", "£270.00", "existing payee"]:
        assert bit in out, bit
    assert "received from clients, last 7 days" in out


def test_money_without_a_bank_says_so():
    c, _ = make(None)
    out = page(c, "/money")
    assert "bank not checked" in out.lower() or "not checked" in out
    assert "£1,234.56" not in out


def test_bank_errors_mean_not_checked_not_a_crash():
    c, _ = make(FakeBank(fail=urllib.error.URLError("down")))
    for path in ["/", "/money"]:
        out = page(c, path)
        assert "not checked" in out or path == "/", path
        assert "down" not in re.sub(r"<[^>]+>", " ", out).split(), path
    # Today says the bank is unreachable (not a setting), leaves out the notes-only payment guesses, and its count
    # is a floor with the bank named
    out = page(c, "/")
    assert "Bank unreachable at 09:30 (retrying)." in out and "Bank not" not in out
    assert "Some sources didn't load: the bank (Starling)." in out
    assert [k for k, _, _ in needs_rows(out)] == ["ring", "pay"], needs_rows(out)
    assert lede_count(out) == "2" and "at least 2 things need you." in plain(out)


def test_no_bank_client_is_a_setting_not_a_failure():
    c, _ = make(None)
    out = page(c, "/")
    assert "Bank not connected (no Starling token): payment states come from the ledger notes." in out
    assert "didn't load" not in out and "at least" not in out


def test_a_failed_bank_read_is_retried_after_a_minute():
    clock = Clock()
    bank = FakeBank(fail=urllib.error.URLError("down"))
    c, _ = make(bank, clock)
    page(c, "/")
    first = bank.calls
    clock.t += 30
    page(c, "/")
    assert bank.calls == first  # kept for a minute
    clock.t += 31
    bank.fail = None
    out = page(c, "/")
    assert bank.calls > first and "Bank checked at 09:30." in out and "unreachable" not in out
    after = bank.calls
    clock.t += 300
    page(c, "/")
    assert bank.calls == after  # a good read is kept for ten minutes


def test_bank_reads_are_cached_for_ten_minutes():
    clock = Clock()
    bank = FakeBank()
    c, _ = make(bank, clock)
    page(c, "/money")
    first = bank.calls
    assert first > 0
    page(c, "/")
    page(c, "/money")
    assert bank.calls == first, (first, bank.calls)
    clock.t += 601
    page(c, "/money")
    assert bank.calls > first


# ---------------------------------------------------------------- isolation and escaping


def test_a_failing_source_is_isolated():
    c, _ = make(FakeBank())
    real = data.dash.singers

    def boom(rows, history=None):
        raise ValueError("Fenwickson secret message")

    data.dash.singers = boom
    try:
        for path in ["/", "/money"]:
            out = page(c, path)
            if path == "/":
                assert "Some sources didn't load: the singer invoices (ValueError)." in out, out
            else:
                assert "couldn&#39;t load (ValueError)" in out or "couldn't load (ValueError)" in out, path
            assert "secret message" not in out and "Fenwickson" not in out
            assert "0107" in out, path  # the hand checks still render
    finally:
        data.dash.singers = real


def test_a_failing_ledger_is_isolated():
    c, _ = make(FakeBank())
    with open(lm.LEDGER, "a") as f:
        f.write("0999,2026-09-01,2026-10-01,Too,Many,Fields,Here,1,2,3,4,5,6,7,8,9,10\n")
    real = data.lm.read_csv

    def boom(path):
        if str(path) == str(lm.LEDGER):
            raise PermissionError("nope")
        return real(path)

    data.lm.read_csv = boom
    try:
        out = page(c, "/")
        assert "couldn&#39;t load (PermissionError)" in out or "couldn't load (PermissionError)" in out
        assert "Dora" in out  # singer invoices still render
    finally:
        data.lm.read_csv = real


def test_values_are_escaped():
    fixtures()
    rows = lm.read_csv(lm.LEDGER)
    rows[0]["client_name"] = "<script>alert(1)</script> Smith"
    rows[0]["ensemble"] = '"><img src=x onerror=alert(1)>'
    lm.write_csv(lm.LEDGER, rows, LEDGER_COLS)
    app = create_app(client_factory=lambda: None, now=lambda: NOW, clock=Clock())
    out = TestClient(app, base_url=ORIGIN, client=LOCAL).get("/", headers=HEADERS).text
    assert "<script>alert" not in out and "<img src=x" not in out
    assert "&lt;img src=x" in out or "&lt;script&gt;" in out


def test_private_detail_never_shown():
    c, _ = make(FakeBank())
    for path in PAGES:
        out = page(c, path)
        for bad in ["Smithfield", "Pastmore", "Fenwickson", "Quillfeather", "example.org", "87654321"]:
            assert bad not in out, (path, bad)
        assert not re.search(r"\d{8}", re.sub(r"<[^>]+>", " ", out)), path


# ---------------------------------------------------------------- chrome and headers


def test_chrome_nav_and_freshness():
    c, _ = make(FakeBank())
    for path in PAGES:
        out = page(c, path)
        assert '<html lang="en-GB"' in out, path
        assert 'name="viewport"' in out and 'name="color-scheme" content="light dark"' in out
        assert "As of Monday 28 September 2026, 09:30" in out, path
        # phase 2: every page is live (no "soon" items); tests/test_cc_pages2.py checks the nav and the tab bar
        assert 'aria-disabled="true"' not in out, path
        for href in ["/", "/money", "/bookings", "/enquiries", "/singers", "/marketing", "/calendar", "/search",
                     "/reports", "/health", "/todo", "/more"]:
            assert f'href="{href}"' in out, (path, href)
    assert 'aria-current="page"' in page(c, "/money").split('href="/money"')[1][:40]


def test_security_headers():
    c, _ = make(FakeBank())
    for path in PAGES + ["/static/app.css", "/healthz"]:
        r = c.get(path, headers=HEADERS)
        assert r.status_code == 200, path
        csp = r.headers["content-security-policy"]
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp, csp
        assert "script-src 'self'" in csp and "object-src 'none'" in csp and "base-uri 'none'" in csp
        assert "unsafe-inline" not in csp and "unsafe-eval" not in csp and "http" not in csp
        assert r.headers["referrer-policy"] == "no-referrer"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "no-store" in r.headers["cache-control"], path
        assert "server" not in r.headers or "uvicorn" not in r.headers["server"].lower()


def test_no_external_urls_or_inline_code():
    c, _ = make(FakeBank())
    for path in PAGES:
        out = page(c, path)
        assert not re.search(r"https?:", out, re.I), path
        assert not re.search(r"""(src|href|action|srcset)\s*=\s*["']?\s*//""", out, re.I), path
        assert "@import" not in out and "url(" not in out, path
        assert not re.search(r"\sstyle\s*=", out, re.I), path
        assert not re.search(r"\son[a-z]+\s*=", out, re.I), path
        for tag in re.findall(r"<script\b[^>]*>", out, re.I):
            assert re.search(r'src="/static/[a-z.]+\.js"', tag), tag
        for m in re.findall(r"""(?:src|href)="([^"]*)\"""", out):
            assert (m.startswith("/") and not m.startswith("//")) or re.fullmatch(r"#[a-z-]+", m), m
    css = c.get("/static/app.css", headers=HEADERS).text
    assert not re.search(r"https?:|@import|url\(", css, re.I)
    js = c.get("/static/passkey.js", headers=HEADERS).text
    assert not re.search(r"https?:", js, re.I)


def test_htmx_is_local_and_locked_down():
    c, _ = make(FakeBank())
    out = page(c, "/")
    assert '<script src="/static/htmx.min.js" defer></script>' in out
    assert '"includeIndicatorStyles":false' in out and '"allowEval":false' in out
    assert c.get("/static/htmx.min.js", headers=HEADERS).status_code == 200


def test_passkeys_page_says_what_can_be_done():
    c, _ = make(FakeBank())
    out = page(c, "/passkeys")
    assert "No passkeys yet" in out and "Register this device" in out
    cfg = auth.load_config()
    cfg["passkeys"] = [{"id": "abc", "public_key": "def", "sign_count": 3, "created": "2026-09-28T09:00:00+01:00",
                        "login": LOGIN, "label": ""}]
    auth.save_config(cfg)
    out = page(c, "/passkeys")
    assert "1 passkey" in out and "Test a passkey" in out and "def" not in re.sub(r"<[^>]+>", " ", out).split()


def test_no_bank_flag_skips_the_keychain():
    real = data.lm.keychain_token

    def refuse():
        raise AssertionError("Keychain read with CC_NO_BANK set")

    data.lm.keychain_token = refuse
    os.environ["CC_NO_BANK"] = "1"
    try:
        assert data.default_client() is None
    finally:
        os.environ.pop("CC_NO_BANK", None)
        data.lm.keychain_token = real


def test_a_crash_is_a_500_with_headers_and_no_detail():
    fixtures()
    real = data.Data.today_page

    def crash(self):
        raise RuntimeError("Smithfield private detail")

    data.Data.today_page = crash
    try:
        app = create_app(client_factory=lambda: None, now=lambda: NOW, clock=Clock())
        r = TestClient(app, base_url=ORIGIN, raise_server_exceptions=False, client=LOCAL).get("/", headers=HEADERS)
    finally:
        data.Data.today_page = real
    assert r.status_code == 500
    assert "Smithfield" not in r.text
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert "no-store" in r.headers["cache-control"]


def test_unknown_page_is_404_with_headers():
    c, _ = make(FakeBank())
    r = c.get("/no-such-page", headers=HEADERS)
    assert r.status_code == 404
    assert "no-store" in r.headers["cache-control"]


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
