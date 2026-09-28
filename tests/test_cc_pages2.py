#!/usr/bin/env python3
"""Tests for the Command Centre's phase-2 pages: Bookings, Enquiries, Singers, Marketing, Calendar, Search,
Reports, Runs and health, To-do and Exports (command_centre/data.py, models.py, sources.py, todo.py,
actions.py, app.py, templates).

Stdlib runner, Starlette's TestClient, fake fixtures in a temp LCS_PRIVATE_DIR (fake names, example.org
emails), a fake Starling client and a fake home folder. Never touches the real private files, the real bank,
~/.claude or the Google credentials.
"""
import argparse, contextlib, datetime, io, json, os, re, sys, tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

TMP = tempfile.mkdtemp()
HOME = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
os.environ["CC_SCHEDULED_TASKS_DIR"] = os.path.join(HOME, ".claude", "scheduled-tasks")
os.environ.pop("CC_DEV_LOGIN", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from starlette.testclient import TestClient  # noqa: E402

from command_centre import actions, auth, data, models, sources, todo  # noqa: E402
from command_centre.app import create_app  # noqa: E402

lm, si, pl = data.lm, data.si, data.pl
LONDON = ZoneInfo("Europe/London")
NOW = datetime.datetime(2026, 9, 28, 9, 30, tzinfo=LONDON)
LOGIN = "owner@example.org"
HOST = "mac.example-tailnet.ts.net"
ORIGIN = f"https://{HOST}"
HEADERS = {"Tailscale-User-Login": LOGIN, "Tailscale-User-Name": "Owner"}
POST_HEADERS = dict(HEADERS, Origin=ORIGIN)
LOCAL = ("127.0.0.1", 50000)
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]
GCLID = "Cj0KCQabcdefghij1234"
SECRET_URL = "https://secret-mcp.example.net/zoho/abc123token"
ADC_SECRET = "adc-refresh-token-do-not-show"
PAGES = ["/bookings", "/bookings?when=past", "/bookings?when=all", "/bookings/0310", "/enquiries",
         "/enquiries/ENQ-A", "/singers", "/marketing", "/calendar", "/calendar?view=week", "/search?q=an",
         "/search", "/reports", "/reports/2026-09-21.txt", "/health", "/todo", "/exports", "/more"]
MANUAL = """# Manual actions required

Intro text.

## 1. Google Business Profile claim

**Status:** open. Claim the profile at the `GBP` dashboard and [verify](https://example.org/x) it.
Second line of the same paragraph.

A later paragraph that is not shown.

## 21. Back up ~/lcs-private/fingerprint.key

Copy the key into the password manager.

### A subheading

## 22. Singer bank details <changed>

Ring the singer first.
"""


class Clock:
    def __init__(self):
        self.t = 5000.0

    def __call__(self):
        return self.t


class FakeBank:
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
        return {"clearedBalance": {"minorUnits": 123456}, "effectiveBalance": {"minorUnits": 120000}}

    def feed(self, since, until, direction):
        self.calls += 1
        return []


def write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def fixtures(calendar=None):
    for base in (TMP, HOME):
        for dirpath, dirnames, filenames in os.walk(base, topdown=False):
            for f in filenames:
                os.remove(os.path.join(dirpath, f))
            for d in dirnames:
                p = os.path.join(dirpath, d)
                (os.remove if os.path.islink(p) else os.rmdir)(p)
    auth.save_config({"allowed_logins": [LOGIN], "origin": ORIGIN, "rp_id": HOST, "passkeys": []})
    lm.write_csv(lm.LEDGER, [
        {"booking_ref": "0310", "invoice_date": "2026-09-01", "event_date": "2026-10-03", "client_name": "Ann Smithfield",
         "client_email": "ann@example.org", "occasion": "wedding", "ensemble": "Small Choir", "value_gbp": "1150",
         "notes": "deposit paid 2026-09-05 by Smithfield; contact ann@example.org"},
        {"booking_ref": "0107", "invoice_date": "2026-06-01", "event_date": "2026-07-01", "client_name": "Olly Pastmore",
         "client_email": "olly@example.org", "occasion": "funeral", "ensemble": "Quartet", "value_gbp": "650", "notes": ""},
        {"booking_ref": "1212", "invoice_date": "2026-09-20", "event_date": "2026-12-12", "client_name": "Cat Jonesworth",
         "client_email": "cat@example.org", "occasion": "carols", "ensemble": "Quartet", "value_gbp": "650", "notes": ""},
        {"booking_ref": "0801", "invoice_date": "2026-07-01", "event_date": "2026-08-01", "client_name": "Dan Closedman",
         "client_email": "dan@example.org", "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": "paid in full 2026-07-20; review request drafted 2026-08-05"},
        {"booking_ref": "0915", "invoice_date": "2026-09-01", "event_date": "2026-11-15", "client_name": "Fay Cancelwood",
         "client_email": "fay@example.org", "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650",
         "notes": "cancelled 2026-09-10"},
    ], LEDGER_COLS)
    lm.write_csv(pl.ENQUIRIES, [
        {"enquiry_id": "ENQ-A", "first_seen": "2026-08-18", "source": "web form", "occasion": "wedding",
         "event_date": "2026-10-03", "package": "Small Choir", "quoted_gbp": "1150", "status": "confirmed",
         "last_contact": "2026-08-25", "booking_ref": "0310", "gclid": GCLID, "followups": "0",
         "notes": "quoted 2026-08-20"},
        {"enquiry_id": "ENQ-B", "first_seen": "2026-09-08", "source": "email", "occasion": "wedding",
         "event_date": "2027-06-01", "package": "Quartet", "quoted_gbp": "650", "status": "quoted",
         "last_contact": "2026-09-10", "booking_ref": "", "gclid": "", "followups": "0", "notes": "quoted 2026-09-10"},
        {"enquiry_id": "ENQ-C", "first_seen": "2026-09-27", "source": "whatsapp", "occasion": "christmas",
         "event_date": "2026-12-20", "package": "", "quoted_gbp": "", "status": "new", "last_contact": "2026-09-27",
         "booking_ref": "", "gclid": "", "followups": "0", "notes": ""},
        {"enquiry_id": "ENQ-D", "first_seen": "2026-07-01", "source": "phone", "occasion": "funeral",
         "event_date": "2026-07-10", "package": "", "quoted_gbp": "", "status": "lost", "last_contact": "2026-07-01",
         "booking_ref": "", "gclid": "", "followups": "0", "notes": ""},
        {"enquiry_id": "ENQ-E", "first_seen": "2026-09-24", "source": "web form", "occasion": "wedding",
         "event_date": "2027-05-01", "package": "Quartet", "quoted_gbp": "650", "status": "quoted",
         "last_contact": "2026-09-25", "booking_ref": "", "gclid": "", "followups": "0", "notes": "quoted 2026-09-25"},
    ], pl.COLUMNS)
    lm.write_csv(si.STORE, [
        {"message_id": "m1", "received": "2026-09-20", "singer_name": "Ben Fenwickson", "singer_email": "ben@example.org",
         "invoice_ref": "BF-12", "amount_gbp": "120", "bank_fp": "abc", "bank_last4": "87654321",
         "payee": "existing: Ben Fenwickson", "bank_changed": "yes", "paid_on": "", "notes": "BANK DETAILS CHANGED: ring them"},
        {"message_id": "m0", "received": "2026-08-10", "singer_name": "Fenwickson, Ben (tenor)",
         "singer_email": "ben@example.org", "invoice_ref": "123456789", "amount_gbp": "100", "bank_fp": "abc0",
         "bank_last4": "5555", "payee": "existing: Ben Fenwickson", "bank_changed": "no", "paid_on": "2026-08-12",
         "paid_amount": "100", "paid_verified": "yes"},
        {"message_id": "m2", "received": "2026-09-22", "singer_name": "Dora Quillfeather",
         "singer_email": "dora@example.org", "invoice_ref": "DQ7", "amount_gbp": "150", "bank_fp": "def",
         "bank_last4": "1111", "payee": "", "bank_changed": "no", "paid_on": ""},
        {"message_id": "m9", "received": "2026-09-23", "singer_name": "Zed Mistakeham", "singer_email": "zed@example.org",
         "invoice_ref": "Z1", "amount_gbp": "80", "bank_fp": "zzz", "bank_last4": "9999", "payee": "",
         "bank_changed": "no", "paid_on": "", "withdrawn": "2026-09-24", "notes": "withdrawn 2026-09-24 (not-ours)"},
    ], si.COLUMNS)
    weeks = [{"week_start": (datetime.date(2026, 8, 3) + datetime.timedelta(weeks=i)).isoformat(),
              "spend_gbp": 20 + i * 3.5, "clicks": 4 + i, "conversions": 0.0} for i in range(8)]
    ads = {"generated": "2026-09-28T08:00:00", "weeks": weeks,
           "season": {"start": "2026-08-01", "campaigns": [
               {"campaign": "Weddings London", "spend_gbp": 150.0, "clicks": 40, "enquiries": 3, "bookings": 1,
                "booked_gbp": 1150.0, "cost_per_enquiry": 50.0, "cost_per_booking": 150.0},
               {"campaign": "<b>Carols</b>", "spend_gbp": 60.0, "clicks": 20, "enquiries": 0, "bookings": 0,
                "booked_gbp": 0.0, "cost_per_enquiry": None, "cost_per_booking": None}],
               "unattributed": {"enquiries": 2, "bookings": 0, "booked_gbp": 0.0},
               "total": {"spend_gbp": 210.0, "clicks": 60, "enquiries": 5, "bookings": 1, "booked_gbp": 1150.0,
                         "cost_per_enquiry": 42.0, "cost_per_booking": 210.0}}}
    write(os.path.join(TMP, "ads-summary.json"), json.dumps(ads))
    write(os.path.join(TMP, "gclid-campaigns.json"),
          json.dumps({GCLID: "Weddings London", "zzz@2026-09-01/30": None}))
    write(os.path.join(TMP, "reports", "2026-09-21.txt"), "== Monday review\n<b>not bold</b> 0107 past, unpaid\n")
    write(os.path.join(TMP, "reports", "notes.txt"), "not a report")
    os.symlink(lm.LEDGER, os.path.join(TMP, "reports", "2026-09-20.txt"))
    write(os.path.join(TMP, "assistant-state.json"), json.dumps({"last_checked": "2026-09-28T08:00:00+01:00",
                                                                   "handled": [], "daily_done": ""}))
    write(os.path.join(HOME, ".claude", "scheduled-tasks", "enquiry-assistant", "SKILL.md"),
          "---\nname: enquiry-assistant\ndescription: Every 2 hours: drafts replies\n---\n\nSECRET PROMPT BODY\n")
    write(os.path.join(HOME, ".config", "gcloud", "application_default_credentials.json"), ADC_SECRET)
    write(os.path.join(HOME, ".claude.json"), json.dumps({"projects": {str(sources.REPO): {"mcpServers": {
        "zoho-mail": {"type": "http", "url": SECRET_URL}, "google-ads": {"command": "x"}}}}}))
    write(os.path.join(TMP, "manual.md"), MANUAL)
    if calendar is not None:
        write(os.path.join(TMP, "command-centre", "cache", "calendar.json"), json.dumps(calendar))


class Patched:
    """Point the readers at the fake home folder and the fake MANUAL-ACTIONS file."""

    def __enter__(self):
        self.saved = (sources.HOME, todo.MANUAL_ACTIONS)
        sources.HOME = Path(HOME)
        todo.MANUAL_ACTIONS = Path(TMP) / "manual.md"
        return self

    def __exit__(self, *exc):
        sources.HOME, todo.MANUAL_ACTIONS = self.saved


def make(bank=None, calendar=None):
    fixtures(calendar)
    app = create_app(client_factory=(lambda: bank), now=lambda: NOW, clock=Clock(), checkout=lambda: "main")
    return TestClient(app, base_url=ORIGIN, client=LOCAL, follow_redirects=False)


def page(c, path):
    r = c.get(path, headers=HEADERS)
    assert r.status_code == 200, (path, r.status_code, r.text[:300])
    return r.text


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# ---------------------------------------------------------------- every page


def test_each_page_renders_with_chrome_and_freshness():
    with Patched():
        c = make(FakeBank())
        for path in PAGES:
            out = page(c, path)
            assert '<html lang="en-GB"' in out, path
            assert "As of Monday 28 September 2026, 09:30" in out, path
            assert 'class="tabbar"' in out and 'href="/more"' in out, path
            assert "couldn&#39;t load" not in out and "couldn't load" not in out, (path, text_of(out)[:400])


def test_every_page_is_reachable_from_more_and_nav():
    with Patched():
        c = make(FakeBank())
        out = page(c, "/more")
        for href in ["/", "/money", "/bookings", "/enquiries", "/singers", "/marketing", "/calendar", "/search",
                     "/reports", "/health", "/todo", "/exports", "/passkeys"]:
            assert f'href="{href}"' in out, href
        tab = page(c, "/bookings").split('class="tabbar"')[1]
        assert re.search(r'href="/bookings"[^>]*aria-current="page"', tab)
        assert "soon" not in text_of(page(c, "/"))


def test_pages_stay_local_and_private():
    with Patched():
        c = make(FakeBank())
        for path in PAGES:
            out = page(c, path)
            assert not re.search(r"https?:", out, re.I), path
            assert not re.search(r"\sstyle\s*=", out, re.I) and not re.search(r"\son[a-z]+\s*=", out, re.I), path
            for tag in re.findall(r"<script\b[^>]*>", out, re.I):
                assert re.search(r'src="/static/[a-z.]+\.js"', tag), tag
            for bad in ["Smithfield", "Pastmore", "Fenwickson", "Quillfeather", "Mistakeham", "example.org",
                        "87654321", "123456789", SECRET_URL, ADC_SECRET, "SECRET PROMPT"]:
                assert bad not in out, (path, bad)


def test_no_get_route_has_a_side_effect():
    with Patched():
        c = make(FakeBank())
        for path in PAGES:
            page(c, path)
        assert not (Path(TMP) / "command-centre" / "todo.json").exists()
        assert not (Path(TMP) / "command-centre" / "audit.jsonl").exists()
        assert c.get("/todo/tick", headers=HEADERS).status_code == 405


# ---------------------------------------------------------------- bookings


def test_bookings_list_and_filters():
    with Patched():
        c = make(FakeBank())
        up = text_of(page(c, "/bookings"))
        assert "0310" in up and "1212" in up and "Ann" in up and "0107" not in up and "0801" not in up
        assert "deposit overdue" in up
        past = text_of(page(c, "/bookings?when=past"))
        assert "0107" in past and "0801" in past and "0310" not in past
        assert "past, unpaid" in past and "paid in full (closed)" in past
        every = text_of(page(c, "/bookings?when=all"))
        assert all(ref in every for ref in ["0310", "0107", "1212", "0801", "0915"]) and "cancelled" in every
        only = text_of(page(c, "/bookings?when=all&state=DEPOSIT_OVERDUE"))
        assert "1212" in only and "0310" not in only
        odd = page(c, "/bookings?when=%3Cscript%3E&state=%3Cscript%3Ealert(1)")
        assert "<script>alert" not in odd and "0310" in odd


def test_booking_timeline():
    with Patched():
        c = make(FakeBank())
        out = page(c, "/bookings/0310")
        t = text_of(out.split('class="timeline"', 1)[1])
        for bit in ["Enquiry", "ENQ-A", "web form", "Quoted", "£1,150.00", "Invoice", "Deposit due", "Event",
                    "Tue 1 Sep 2026", "deposit paid"]:
            assert bit in t, bit
        assert "Smithfield" not in out and "ann@example.org" not in out  # notes masked
        assert t.find("Enquiry") < t.find("Invoice") < t.find("Event"), t
        closed = text_of(page(c, "/bookings/0801"))
        assert "review" in closed.lower() and "paid in full" in closed
        assert c.get("/bookings/..%2Fetc", headers=HEADERS).status_code == 404
        assert c.get("/bookings/9999", headers=HEADERS).status_code == 404


# ---------------------------------------------------------------- enquiries


def test_enquiries_board_followups_conversion_sources():
    with Patched():
        c = make(FakeBank())
        t = text_of(page(c, "/enquiries"))
        for status in pl.STATUS_ORDER:
            assert status.replace("_", " ") in t.lower(), status
        assert "ENQ-B" in t and "first" in t.lower()           # follow-up due (pipeline.followups_due)
        assert "web form" in t and "whatsapp" in t             # sources
        assert "%" in t                                        # conversion rate
        e = text_of(page(c, "/enquiries/ENQ-A"))
        assert "Weddings London" in e and "0310" in e and "Quoted" in e
        b = text_of(page(c, "/enquiries/ENQ-E"))
        assert "Next follow-up" in b and "Wed 30 Sep 2026" in b, b
        assert c.get("/enquiries/bad%20id", headers=HEADERS).status_code == 404


def test_enquiries_offers_a_reply_handoff_picker():
    # No in-app chat: each enquiry needing a follow-up gets an option in a "Draft a reply to" picker, built
    # server-side from the enquiries the pipeline already flagged as due — never a free-text thread id.
    with Patched():
        c = make(FakeBank())
        out = page(c, "/enquiries")
        assert '<select id="reply-handoff-select"' in out
        opt = re.search(r'<option value="ENQ-B" data-prompt="([^"]*)">ENQ-B</option>', out)
        assert opt, out
        assert "ENQ-B" in opt.group(1) and "scripts/bookings/pipeline.py" in opt.group(1)
        assert "Zoho draft only" in opt.group(1) and "never send it" in opt.group(1)
        assert '<script src="/static/handoffs.js" defer></script>' in out


def test_next_followup_uses_the_pipeline_rules():
    today = datetime.date(2026, 9, 28)
    row = {"enquiry_id": "x", "status": "quoted", "occasion": "wedding", "last_contact": "2026-09-25",
           "followups": "0", "event_date": "2027-05-01", "booking_ref": ""}
    assert models.next_followup(row, today) == (datetime.date(2026, 9, 30), "first")
    assert models.next_followup(dict(row, followups="1"), today) == (datetime.date(2026, 10, 5), "second")
    assert models.next_followup(dict(row, occasion="funeral"), today) == (datetime.date(2027, 5, 1), "mark_lost")
    assert models.next_followup(dict(row, booking_ref="0310"), today) is None
    assert models.next_followup(dict(row, status="new"), today) is None
    assert models.next_followup(dict(row, last_contact="2026-09-01"), today) == (today, "first")  # overdue: today


# ---------------------------------------------------------------- singers


def test_singers_directory():
    with Patched():
        c = make(FakeBank())
        out = page(c, "/singers")
        t = text_of(out)
        assert t.count("Ben") >= 1 and "Dora" in t
        assert "••••4321" in t and "87654321" not in out
        assert "ring before paying" in t.lower() or "ring" in t.lower()
        assert "£100.00" in t                                  # Ben's total paid
        assert "existing payee" in t
        assert "withdrawn" in t.lower() and "Zed" in t
        assert "123456789" not in out
        ben = [g for g in models.singer_directory(lm.read_csv(si.STORE), datetime.date(2026, 9, 28))
               if g["first_name"] == "Ben"]
        assert len(ben) == 1 and len(ben[0]["invoices"]) == 2, ben   # "Fenwickson, Ben (tenor)" groups with Ben


def test_confirmed_bank_details_clear_the_singers_card_and_today():
    # owner report: after `confirm`, the old CHANGED clause stayed in the row's notes and kept the card red
    def ben():
        return next(g for g in models.singer_directory(lm.read_csv(si.STORE), datetime.date(2026, 9, 28))
                    if g["first_name"] == "Ben")

    with Patched():
        c = make(FakeBank())
        assert "No changed bank details waiting" not in page(c, "/")
        assert ben()["warnings"] and ben()["bank_check"] == "not yet verified"
        with contextlib.redirect_stdout(io.StringIO()):
            si.cmd_confirm(argparse.Namespace(message_id="m1"))
        g = ben()
        assert g["warnings"] == [] and g["bank_check"] == "confirmed by phone", g
        assert not any(i["ring_first"] for i in g["invoices"]), g["invoices"]
        assert "BANK DETAILS CHANGED" in next(r for r in lm.read_csv(si.STORE) if r["message_id"] == "m1")["notes"]
        c = TestClient(create_app(client_factory=(lambda: FakeBank()), now=lambda: NOW, clock=Clock(),
                                  checkout=lambda: "main"), base_url=ORIGIN, client=LOCAL, follow_redirects=False)
        assert "card-bad" not in page(c, "/singers")
        today = page(c, "/")
        assert "No changed bank details waiting" in today and "changed: ring before paying" not in today


# ---------------------------------------------------------------- marketing


def test_marketing_page():
    with Patched():
        c = make(FakeBank())
        out = page(c, "/marketing")
        t = text_of(out)
        assert "Data as of" in t and "28 Sep 2026" in t
        assert "Weddings London" in t and "£150.00" in t and "£50.00" in t
        assert "&lt;b&gt;Carols&lt;/b&gt;" in out and "<b>Carols" not in out
        assert "<svg" in out and 'role="img"' in out and "<rect" in out
        assert "1 click id" in t or "click ids" in t


def test_marketing_without_a_summary_says_so():
    with Patched():
        c = make(FakeBank())
        os.remove(os.path.join(TMP, "ads-summary.json"))
        t = text_of(page(c, "/marketing"))
        assert "No Ads summary yet" in t


# ---------------------------------------------------------------- calendar


def test_calendar_without_the_diary():
    with Patched():
        c = make(FakeBank())
        t = text_of(page(c, "/calendar?date=2026-10-01"))
        assert "diary not synced yet" in t.lower()
        assert "October 2026" in t and "0310" in t              # the event on 3 Oct
        wk = text_of(page(c, "/calendar?view=week&date=2026-09-28"))
        assert "Follow-up" in wk and "ENQ-E" in wk              # 30 Sep
        assert "0310" in wk and "Balance due" in wk            # 30 Sep: three days before 3 Oct
        dec = text_of(page(c, "/calendar?date=2026-12-01"))
        assert "1212" in dec and "0915" not in dec             # cancelled bookings aren't shown
        sep = text_of(page(c, "/calendar?date=2026-09-01"))
        assert "Deposit due" in sep and "1212" in sep          # 27 Sep
        bad = page(c, "/calendar?view=%3Cx%3E&date=nope")
        assert "<x>" not in bad and "September 2026" in text_of(bad)


def test_calendar_with_the_diary():
    cal = [{"start": "2026-10-03T14:00:00+01:00", "end": "2026-10-03T16:00:00+01:00",
            "summary": "<i>Rehearsal</i> St Mary", "calendar": "LCS"},
           {"start": "2026-10-05", "end": "2026-10-06", "summary": "Day off", "calendar": "Personal"},
           {"start": "not a date", "summary": "skipped"}, "junk"]
    with Patched():
        c = make(FakeBank(), calendar=cal)
        out = page(c, "/calendar?date=2026-10-01")
        t = text_of(out)
        assert "diary not synced" not in t.lower() and "synced" in t.lower()
        assert "&lt;i&gt;Rehearsal&lt;/i&gt; St Mary" in out and "Day off" in t and "skipped" not in t


# ---------------------------------------------------------------- search


def test_search_finds_and_escapes():
    with Patched():
        c = make(FakeBank())
        out = page(c, "/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E")
        assert "<script>alert(1)" not in out and "&lt;script&gt;alert(1)&lt;/script&gt;" in out
        t = text_of(page(c, "/search?q=smithfield"))
        assert "0310" in t and "Ann" in t
        t = text_of(page(c, "/search?q=INV1212"))
        assert "1212" in t
        t = text_of(page(c, "/search?q=christmas"))
        assert "ENQ-C" in t
        t = text_of(page(c, "/search?q=quill"))
        assert "Dora" in t
        t = text_of(page(c, "/search?q=DQ7"))
        assert "DQ7" in t and "Dora" in t
        t = text_of(page(c, "/search?q=a"))
        assert "at least 2" in t
        long = page(c, "/search?q=" + "x" * 500)
        assert 'value="' + "x" * 80 + '"' in long and "“" + "x" * 81 not in long


# ---------------------------------------------------------------- reports


def test_reports_list_and_view():
    with Patched():
        c = make(FakeBank())
        t = text_of(page(c, "/reports"))
        assert "2026-09-21" in t and "notes.txt" not in t
        out = page(c, "/reports/2026-09-21.txt")
        assert "<pre" in out and "&lt;b&gt;not bold&lt;/b&gt;" in out and "<b>not bold" not in out


def test_report_names_are_traversal_safe():
    with Patched():
        c = make(FakeBank())
        for bad in ["/reports/notes.txt", "/reports/..%2Fbookings.csv", "/reports/..%2F..%2Fetc%2Fpasswd",
                    "/reports/2026-09-21.txt%00", "/reports/2026-9-21.txt", "/reports/2026-09-20.txt",
                    "/reports/%2E%2E", "/reports/2026-09-22.txt"]:
            r = c.get(bad, headers=HEADERS)
            assert r.status_code == 404, (bad, r.status_code)
            assert "Ann" not in r.text and "booking_ref" not in r.text, bad
        assert sources.report_text("../bookings.csv") is None
        assert sources.report_text("2026-09-20.txt") is None  # a symlink


# ---------------------------------------------------------------- health


def test_health_checks_and_runs():
    with Patched():
        bank = FakeBank()
        c = make(bank)
        out = page(c, "/health")
        t = text_of(out)
        assert "enquiry-assistant" in t and "Every 2 hours" in t
        assert "Starling" in t and "account readable" in t.lower()
        assert "Google credentials file present" in t
        assert "zoho-mail" in t and "zoho-books" in t and "not configured" in t
        assert "fingerprint" in t.lower() and "backup" in t.lower()
        assert "disk" in t.lower() and "main" in t
        assert "Run now" in t and "Routines" in t  # explains the Claude app's own trigger; no button here
        assert "cc-copy" in out and "What&#39;s owed this week?" in out and "Summarise today&#39;s business" in out
        for bad in [SECRET_URL, ADC_SECRET, "SECRET PROMPT", "acc-1"]:
            assert bad not in out, bad
        calls = bank.calls
        page(c, "/health")
        assert bank.calls == calls, "the Starling check is cached"


def test_health_never_opens_the_adc_file():
    real_open = open
    adc = os.path.join(HOME, ".config", "gcloud", "application_default_credentials.json")

    def guarded(path, *a, **k):
        assert os.path.abspath(str(path)) != adc, "the ADC file was opened"
        return real_open(path, *a, **k)

    import builtins
    with Patched():
        c = make(None)
        builtins.open = guarded
        try:
            t = text_of(page(c, "/health"))
        finally:
            builtins.open = real_open
    assert "not checked" in t.lower()  # no bank token


# ---------------------------------------------------------------- to-do


def test_todo_lists_sections_with_first_paragraph():
    with Patched():
        c = make(FakeBank())
        out = page(c, "/todo")
        t = text_of(out)
        assert "Google Business Profile claim" in t and "Back up ~/lcs-private/fingerprint.key" in t
        assert "Claim the profile at the GBP dashboard and verify it." in t
        assert "A later paragraph" not in t and "example.org/x" not in out
        assert "&lt;changed&gt;" in out
    items = todo.parse(MANUAL)
    assert [i["number"] for i in items] == [1, 21, 22]
    assert items[1]["key"] == "21-back-up-lcs-private-fingerprint-key"


def tick(c, key, done="yes", headers=None):
    return c.post("/todo/tick", data={"key": key, "done": done}, headers=headers or POST_HEADERS)


def test_todo_tick_writes_locally_and_logs():
    with Patched():
        c = make(FakeBank())
        key = todo.parse(MANUAL)[1]["key"]
        r = tick(c, key)
        assert r.status_code == 303 and r.headers["location"] == "/todo", (r.status_code, r.text)
        store = Path(TMP) / "command-centre" / "todo.json"
        assert json.loads(store.read_text())[key]["done"] is True
        assert oct(store.stat().st_mode & 0o777) == "0o600"
        audit = (Path(TMP) / "command-centre" / "audit.jsonl").read_text().splitlines()
        entry = json.loads(audit[-1])
        assert entry["action"] == "todo-tick" and "tick to-do 21" in entry["summary"] and entry["login"] == LOGIN
        t = text_of(page(c, "/todo"))
        assert "Done" in t
        assert tick(c, key, "no").status_code == 303
        assert json.loads(store.read_text())[key]["done"] is False
        assert tick(c, "99-made-up").status_code == 400
        assert tick(c, "<script>").status_code == 400
        assert tick(c, key, "maybe").status_code == 400


def test_todo_tick_needs_the_right_origin_and_host():
    with Patched():
        c = make(FakeBank())
        key = todo.parse(MANUAL)[0]["key"]
        assert tick(c, key, headers=HEADERS).status_code == 403                                  # no Origin
        assert tick(c, key, headers=dict(HEADERS, Origin="https://evil.example")).status_code == 403
        assert tick(c, key, headers=dict(POST_HEADERS, **{"Sec-Fetch-Site": "cross-site"})).status_code == 403
        assert tick(c, key, headers=dict(POST_HEADERS, Host="evil.example")).status_code == 403
        assert tick(c, key, headers={"Origin": ORIGIN}).status_code == 403                       # no identity
        assert not (Path(TMP) / "command-centre" / "todo.json").exists()


def test_todo_tick_posts_with_fetch_not_a_plain_form():
    # Referrer-Policy: no-referrer makes a browser send "Origin: null" on a plain form POST, which the same-origin
    # check refuses (it did, in a real browser). todo.js posts the form with fetch(), which sends the real Origin,
    # and the route answers JSON with the page to load.
    static = Path(ROOT) / "command_centre" / "static"
    js = (static / "todo.js").read_text()
    assert 'querySelectorAll("form.todo-tick")' in js and '"Accept": "application/json"' in js
    assert "preventDefault" in js and "fetch(f.action" in js
    with Patched():
        c = make(FakeBank())
        out = page(c, "/todo")
        forms = re.findall(r"<form\b[^>]*>", out)
        assert forms and all('class="todo-tick"' in f for f in forms if 'method="post"' in f), forms
        assert '<script src="/static/todo.js" defer></script>' in out and "<script>" not in out
        assert c.get("/static/todo.js", headers=HEADERS).status_code == 200
        key = todo.parse(MANUAL)[1]["key"]
        assert tick(c, key, headers=dict(POST_HEADERS, Origin="null")).status_code == 403   # what a plain form sends
        js_headers = dict(POST_HEADERS, Accept="application/json")
        r = tick(c, key, headers=js_headers)
        assert r.status_code == 200 and r.json() == {"url": "/todo"}, (r.status_code, r.text)
        assert json.loads((Path(TMP) / "command-centre" / "todo.json").read_text())[key]["done"] is True
        r = tick(c, "99-made-up", headers=js_headers)
        assert r.status_code == 400 and set(r.json()) == {"error"}, r.text


def test_every_post_form_in_the_templates_is_sent_by_a_script():
    # A plain <form method="post"> would be refused in a browser (see above); each one needs a class that a static
    # script intercepts. The action forms (class cc-action) have no method and are sent by actions.js.
    handled = {"todo-tick": "todo.js"}
    templates = Path(ROOT) / "command_centre" / "templates"
    for f in sorted(templates.glob("*.html")):
        for form in re.findall(r"<form\b[^>]*>", f.read_text()):
            if re.search(r'method="?post', form, re.I):
                cls = re.search(r'class="([^"]*)"', form)
                names = set(cls.group(1).split()) if cls else set()
                assert names & set(handled), (f.name, form)


def test_todo_tick_is_a_registered_local_action_without_a_passkey():
    a = actions.REGISTRY["todo-tick"]
    assert a.passkey is False
    assert "todo-tick" not in auth.PHASE1_ACTIONS  # it can't be used to mint passkey challenges either
    items = todo.parse(MANUAL)
    with Patched():
        fixtures()
        act = a.build({"key": items[1]["key"], "done": "yes"})
        assert isinstance(act, auth.Action) and act.summary.startswith("tick to-do 21: Back up")
        for bad in [{}, {"key": items[1]["key"]}, {"key": "x", "done": "yes"}, {"key": items[1]["key"], "done": "1"}]:
            try:
                a.build(bad)
            except actions.ActionError:
                pass
            else:
                raise AssertionError(bad)


# ---------------------------------------------------------------- exports


def test_exports_are_attachments_without_bank_numbers():
    with Patched():
        c = make(FakeBank())
        t = text_of(page(c, "/exports"))
        assert "bookings.csv" in t and "singer-invoices.csv" in t and "pipeline.csv" in t
        for name in ["bookings", "singer-invoices", "pipeline"]:
            r = c.get(f"/exports/{name}.csv", headers=HEADERS)
            assert r.status_code == 200, name
            assert r.headers["content-disposition"].startswith("attachment;"), r.headers["content-disposition"]
            assert f"lcs-{name}-2026-09-28.csv" in r.headers["content-disposition"]
            assert "no-store" in r.headers["cache-control"]
            assert r.headers["content-type"].startswith("text/csv")
            if name != "pipeline":  # enquiry ids are Zoho thread ids, long numbers that are not bank details
                assert not re.search(r"\d{6,}", r.text), (name, re.findall(r"\d{6,}", r.text))
            for bad in ["Smithfield", "example.org", "Fenwickson", GCLID]:
                assert bad not in r.text, (name, bad)
        s = c.get("/exports/singer-invoices.csv", headers=HEADERS).text
        assert "••••4321" in s and "87654321" not in s and "Ben" in s
        b = c.get("/exports/bookings.csv", headers=HEADERS).text
        assert "0310" in b and "Ann" in b
        p = c.get("/exports/pipeline.csv", headers=HEADERS).text
        assert "ENQ-A" in p and "Weddings London" in p and "notes" not in p.splitlines()[0]
        assert c.get("/exports/other.csv", headers=HEADERS).status_code == 404
        assert c.get("/exports/..%2Fbookings.csv", headers=HEADERS).status_code == 404


def test_csv_cells_cannot_become_formulas():
    assert models.csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert models.csv_safe("+1") == "'+1" and models.csv_safe("@x") == "'@x" and models.csv_safe("-2") == "'-2"
    assert models.csv_safe("Ann") == "Ann" and models.csv_safe(12.5) == "12.5"


# ---------------------------------------------------------------- isolation


def test_a_failing_source_is_isolated():
    real = data.lm.read_csv

    def boom(path):
        if str(path) == str(pl.ENQUIRIES):
            raise PermissionError("Smithfield secret")
        return real(path)

    with Patched():
        c = make(FakeBank())
        data.lm.read_csv = boom
        try:
            for path in ["/enquiries", "/bookings/0310", "/calendar", "/search?q=an", "/marketing"]:
                out = page(c, path)
                assert "couldn't load (PermissionError)" in out.replace("&#39;", "'"), path
                assert "Smithfield secret" not in out, path
            assert "0310" in page(c, "/bookings/0310")        # the rest of the timeline still renders
            assert "0310" in text_of(page(c, "/calendar?date=2026-10-01"))
            assert "Dora" in text_of(page(c, "/search?q=dora"))
            assert c.get("/exports/pipeline.csv", headers=HEADERS).status_code == 503
        finally:
            data.lm.read_csv = real


def test_a_failing_builder_is_isolated_on_each_page():
    targets = {"/bookings": "booking_rows", "/singers": "singer_directory", "/marketing": "weekly_chart",
               "/calendar": "calendar_items", "/search?q=an": "search", "/health": "disk_check",
               "/todo": "todo_items", "/reports": "report_list"}
    with Patched():
        c = make(FakeBank())
        for path, name in targets.items():
            mod = sources if hasattr(sources, name) else models if hasattr(models, name) else todo
            real = getattr(mod, name)

            def boom(*a, **k):
                raise ValueError("private detail Smithfield")

            setattr(mod, name, boom)
            try:
                out = page(c, path)
                assert "couldn't load (ValueError)" in out.replace("&#39;", "'"), (path, name)
                assert "private detail" not in out, path
            finally:
                setattr(mod, name, real)


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
