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
    app = create_app(client_factory=(lambda: bank), now=lambda: NOW, clock=clock or Clock())
    return TestClient(app, base_url=ORIGIN), app


def page(c, path):
    r = c.get(path, headers=HEADERS)
    assert r.status_code == 200, (path, r.status_code)
    return r.text


# ---------------------------------------------------------------- Today


def test_today_puts_attention_first_in_priority_order():
    c, _ = make(FakeBank())
    out = page(c, "/")
    marks = ["Bank details changed", "Needs a hand check", "Singer invoices unpaid", "This week", "Later"]
    pos = [out.find(m) for m in marks]
    assert all(p >= 0 for p in pos), list(zip(marks, pos))
    assert pos == sorted(pos), list(zip(marks, pos))
    assert "ring before paying" in out and "••••4321" in out
    assert "0107" in out and "past, unpaid" in out          # hand check from money_report.needs_hand_check
    assert "Dora" in out and "£150.00" in out                # unpaid singer invoice
    assert "Eve" not in out                                  # paid invoices aren't shown
    assert "0310" in out and "Ann" in out and "1212" in out  # upcoming events
    assert out.find("0310") < out.find("1212")


def test_today_counts_what_needs_attention():
    c, _ = make(FakeBank())
    out = page(c, "/")
    assert re.search(r'class="count[^"]*">\s*4\s*<', out), "4 things: 2 hand checks and 2 unpaid invoices (the bank warning is one of those invoices)"


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
        assert "not checked" in out, path
        assert "down" not in re.sub(r"<[^>]+>", " ", out).split(), path


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

    def boom(rows):
        raise ValueError("Fenwickson secret message")

    data.dash.singers = boom
    try:
        for path in ["/", "/money"]:
            out = page(c, path)
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
    out = TestClient(app, base_url=ORIGIN).get("/", headers=HEADERS).text
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
        for soon in ["Bookings", "Enquiries", "Singers", "Marketing", "Calendar", "Search", "Reports", "Health",
                     "To-do"]:
            assert re.search(rf'aria-disabled="true"[^>]*>\s*{soon}\s*<span class="soon">soon</span>', out), (path, soon)
        assert 'href="/"' in out and 'href="/money"' in out
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
        r = TestClient(app, base_url=ORIGIN, raise_server_exceptions=False).get("/", headers=HEADERS)
    finally:
        data.Data.today_page = real
    assert r.status_code == 500
    assert "Smithfield" not in r.text
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert "no-store" in r.headers["cache-control"]


def test_unknown_page_is_404_with_headers():
    c, _ = make(FakeBank())
    r = c.get("/bookings", headers=HEADERS)
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
