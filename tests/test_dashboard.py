#!/usr/bin/env python3
"""Tests for scripts/reports/dashboard.py. Stdlib only; never touches the real private files."""
import datetime, json, os, re, sys, tempfile

TMP = tempfile.mkdtemp()
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import dashboard as dash  # noqa: E402

lm, si = dash.lm, dash.si
T = datetime.date(2026, 9, 28)
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]
ENQ_COLS = ["enquiry_id", "first_seen", "source", "occasion", "event_date", "package", "quoted_gbp", "status",
            "last_contact", "booking_ref", "gclid", "followups", "notes"]
HEADINGS = ["Upcoming events", "Money", "Needs a hand check", "Singer invoices unpaid", "Pipeline", "Ads", "Bank balance"]


def reset():
    for name in os.listdir(TMP):
        p = os.path.join(TMP, name)
        if os.path.isdir(p):
            os.rmdir(p)
        else:
            os.remove(p)


def fake_data(**over):
    data = {
        "generated": "Monday 28 September 2026, 09:00",
        "bank_checked": True,
        "upcoming": [
            {"date": "2026-10-03", "ref": "0310", "first_name": "Ann", "occasion": "wedding", "ensemble": "Small Choir",
             "value": 1150.0, "state": "DEPOSIT_SEEN", "bank_checked": True},
            {"date": "2026-10-10", "ref": "1010", "first_name": "Tom", "occasion": "funeral", "ensemble": "Quartet",
             "value": 650.0, "state": "DEPOSIT_OVERDUE", "bank_checked": True},
        ],
        "money": ["received from clients, last 7 days: £575.00 (1 payment)", "deposits overdue: 1 (1010)"],
        "hand_check": [{"ref": "0909", "state": "NOTED_PAID", "label": "noted paid, not in bank", "value": 650.0,
                        "received": 0.0}],
        "singers": [{"received": "2026-09-20", "first_name": "Ben", "amount": 120.0, "payee": "yes",
                     "bank_changed": True, "ring_first": True, "last4": "5678"}],
        "pipeline": {"season_start": "2026-09-01",
                     "windows": [{"label": "Season", "counts": {"new": 2, "quoted": 3, "confirmed": 1},
                                  "total": 6, "quoted": 4, "confirmed": 1},
                                 {"label": "Last 30 days", "counts": {"quoted": 1}, "total": 1, "quoted": 1,
                                  "confirmed": 0}]},
        "ads": {"generated": "2026-09-28", "weeks": [
            {"week_start": "2026-09-21", "spend": 30.5, "clicks": 12, "enquiries": 2, "cpe": 15.25},
            {"week_start": "2026-09-14", "spend": 20.0, "clicks": 9, "enquiries": 0, "cpe": None}]},
        "bank": {"cleared": 1234.56, "effective": 1200.0},
    }
    data.update(over)
    return data


def test_render_has_every_section():
    out = dash.render(fake_data())
    assert "<title>LCS dashboard</title>" in out
    for h in HEADINGS:
        assert f">{h}</h2>" in out, h
    for bit in ["0310", "Ann", "Small Choir", "£1,150.00", "deposit overdue", "£575.00 (1 payment)", "0909",
                "noted paid, not in bank", "Ben", "£120.00", "••••5678", "ring before paying", "Season",
                "Last 30 days", "1 confirmed of 4 quoted (25%)", "£30.50", "£15.25", "£1,234.56", "£1,200.00",
                "28 September 2026"]:
        assert bit in out, bit
    assert "prefers-color-scheme: dark" in out and 'name="viewport"' in out


def test_values_are_escaped():
    evil = "<script>alert(1)</script>"
    out = dash.render(fake_data(upcoming=[{"date": "2026-10-03", "ref": evil, "first_name": evil, "occasion": evil,
                                           "ensemble": evil, "value": 1.0, "state": evil, "bank_checked": True}],
                                money=[evil]))
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_no_external_requests():
    out = dash.render(fake_data())
    assert not re.search(r"https?:", out, re.I), "an http(s) URL in the page"
    assert "//" not in out
    assert not re.search(r"\b(src|href|srcset|action)\s*=", out, re.I)
    assert "@import" not in out and "url(" not in out and "<script" not in out.lower()


def test_only_last4_of_a_bank_account_is_shown():
    # render trims whatever it is handed to four digits...
    out = dash.render(fake_data(singers=[{"received": "2026-09-20", "first_name": "Ben", "amount": 120.0,
                                          "payee": "yes", "bank_changed": False, "ring_first": False,
                                          "last4": "12345678"}]))
    assert "12345678" not in out and "••••5678" in out
    # ...and gather only ever passes the last four on from the store
    reset()
    lm.write_csv(si.STORE, [{"message_id": "m1", "received": "2026-09-20", "singer_name": "Ben Fenwick",
                             "singer_email": "ben@example.org", "amount_gbp": "120", "bank_fp": "abc",
                             "bank_last4": "87654321", "payee": "yes", "bank_changed": "yes", "paid_on": ""}],
                 si.COLUMNS)
    data = dash.gather(None, T)
    assert data["singers"][0]["last4"] == "4321", data["singers"]
    page = dash.render(data)
    assert "87654321" not in page and "••••4321" in page
    assert "Fenwick" not in page and "ben@example.org" not in page
    assert not re.search(r"\d{8}", page)


def test_missing_files_give_the_placeholders():
    reset()
    out = dash.render(dash.gather(None, T))
    assert "pipeline sheet not set up yet" in out
    assert "run the Monday review to fill this" in out
    assert "not checked" in out
    for h in HEADINGS:
        assert f">{h}</h2>" in out, h


def test_ledger_rows_without_bank_show_the_notes_state():
    reset()
    rows = [
        {"booking_ref": "0310", "invoice_date": "2026-09-01", "event_date": "2026-10-03", "client_name": "Ann Smith",
         "client_email": "ann@example.org", "occasion": "wedding", "ensemble": "Small Choir", "value_gbp": "1150",
         "notes": "deposit paid 5 Sep"},
        {"booking_ref": "0107", "invoice_date": "2026-06-01", "event_date": "2026-07-01", "client_name": "Old Past",
         "occasion": "funeral", "ensemble": "Quartet", "value_gbp": "650", "notes": ""},
        {"booking_ref": "1111", "invoice_date": "2026-09-20", "event_date": "2026-11-11", "client_name": "Cat Jones",
         "occasion": "wedding", "ensemble": "Quartet", "value_gbp": "650", "notes": "CANCELLED by client 2026-09-25"},
        {"booking_ref": "0510", "invoice_date": "2026-09-25", "event_date": "2026-10-05", "client_name": "Mr Dan Brown",
         "occasion": "funeral", "ensemble": "Quartet", "value_gbp": "650", "notes": "PENDING: invoiced"},
    ]
    lm.write_csv(lm.LEDGER, rows, LEDGER_COLS)
    data = dash.gather(None, T)
    assert [u["ref"] for u in data["upcoming"]] == ["0310", "0510"], data["upcoming"]
    assert data["upcoming"][1]["first_name"] == "Dan"
    assert not data["bank_checked"]
    out = dash.render(data)
    assert "bank not checked" in out and "noted paid" in out
    assert "Smith" not in out and "Brown" not in out and "ann@example.org" not in out
    assert "0107" in out  # past and unpaid: on the hand check


def test_pipeline_and_ads_from_files():
    reset()
    enq = [
        {"enquiry_id": "e1", "first_seen": "2026-09-22", "status": "quoted", "quoted_gbp": "650"},
        {"enquiry_id": "e2", "first_seen": "2026-09-23", "status": "confirmed", "quoted_gbp": "1150"},
        {"enquiry_id": "e3", "first_seen": "2026-09-10", "status": "new"},
        {"enquiry_id": "e4", "first_seen": "2026-07-01", "status": "lost", "quoted_gbp": "650"},
    ]
    lm.write_csv(os.path.join(TMP, "enquiries.csv"), enq, ENQ_COLS)
    with open(os.path.join(TMP, "ads-summary.json"), "w") as f:
        json.dump({"generated": "2026-09-28", "weeks": [
            {"week_start": "2026-08-31", "spend_gbp": 5, "clicks": 1, "conversions": 0},
            {"week_start": "2026-09-07", "spend_gbp": 10, "clicks": 2, "conversions": 0},
            {"week_start": "2026-09-14", "spend_gbp": 12, "clicks": 3, "conversions": 0},
            {"week_start": "2026-09-21", "spend_gbp": 30, "clicks": 12, "conversions": 1},
            {"week_start": "2026-09-28", "spend_gbp": 4, "clicks": 1, "conversions": 0}], "season": []}, f)
    data = dash.gather(None, T)
    season, last30 = data["pipeline"]["windows"]
    assert season["counts"] == {"quoted": 1, "confirmed": 1, "new": 1}, season
    assert (season["quoted"], season["confirmed"]) == (2, 1)
    assert last30["total"] == 3
    weeks = data["ads"]["weeks"]
    assert [w["week_start"] for w in weeks] == ["2026-09-28", "2026-09-21", "2026-09-14", "2026-09-07"], weeks
    assert weeks[1]["enquiries"] == 2 and weeks[1]["cpe"] == 15.0
    assert weeks[2]["enquiries"] == 0 and weeks[2]["cpe"] is None
    out = dash.render(data)
    assert "1 confirmed of 2 quoted (50%)" in out and "£15.00" in out and "no enquiries" in out


def test_ads_without_pipeline_has_no_cost_per_enquiry():
    reset()
    with open(os.path.join(TMP, "ads-summary.json"), "w") as f:
        json.dump({"generated": "2026-09-28", "weeks": [{"week_start": "2026-09-21", "spend_gbp": 30, "clicks": 12,
                                                         "conversions": 1}], "season": []}, f)
    data = dash.gather(None, T)
    assert data["ads"]["weeks"][0]["enquiries"] is None
    out = dash.render(data)
    assert "£30.00" in out and "Cost per enquiry" not in out


def test_a_failing_section_does_not_kill_the_page():
    out = dash.render(fake_data(pipeline={"failed": "ValueError"}, ads={"weeks": 5}))
    assert "couldn&#x27;t load (ValueError)" in out, out
    assert "couldn&#x27;t load (TypeError)" in out
    assert "£1,234.56" in out and "0310" in out
    # and in gather: an unreadable enquiries sheet fails the pipeline section only
    reset()
    os.mkdir(os.path.join(TMP, "enquiries.csv"))
    data = dash.gather(None, T)
    assert data["pipeline"] == {"failed": "IsADirectoryError"}, data["pipeline"]
    page = dash.render(data)
    assert "couldn&#x27;t load (IsADirectoryError)" in page and ">Bank balance</h2>" in page
    reset()


class FakeStarling:
    calls = []

    def __init__(self, token=None, fail=None):
        FakeStarling.calls.append(("init",))
        self.fail = fail

    def get(self, path):
        FakeStarling.calls.append(("get", path))
        if self.fail:
            raise self.fail
        if path.endswith("/balance"):
            return {"clearedBalance": {"currency": "GBP", "minorUnits": 123456},
                    "effectiveBalance": {"currency": "GBP", "minorUnits": 120000}}
        return {}

    def account(self):
        FakeStarling.calls.append(("account",))
        if self.fail:
            raise self.fail
        return {"accountUid": "uid-1", "defaultCategory": "cat-1"}

    def feed(self, since, until, direction):
        FakeStarling.calls.append(("feed", direction))
        if self.fail:
            raise self.fail
        return []


def test_bank_balance_and_errors():
    reset()
    FakeStarling.calls = []
    data = dash.gather(FakeStarling(), T)
    assert data["bank"] == {"cleared": 1234.56, "effective": 1200.0}, data["bank"]
    assert ("get", "/api/v2/accounts/uid-1/balance") in FakeStarling.calls
    for err in (lm.StarlingError("x"), TimeoutError(), OSError(), json.JSONDecodeError("x", "y", 0)):
        data = dash.gather(FakeStarling(fail=err), T)
        assert data["bank"] is None, err
    out = dash.render(dash.gather(FakeStarling(fail=TimeoutError()), T))
    assert "not checked" in out and "couldn&#x27;t load" not in out


def test_upcoming_uses_the_bank_when_it_answers():
    reset()
    lm.write_csv(lm.LEDGER, [{"booking_ref": "0310", "invoice_date": "2026-09-01", "event_date": "2026-10-03",
                              "client_name": "Ann Smith", "occasion": "wedding", "ensemble": "Small Choir",
                              "value_gbp": "1150", "notes": ""}], LEDGER_COLS)
    data = dash.gather(FakeStarling(), T)
    assert data["bank_checked"] and data["upcoming"][0]["state"] == "DEPOSIT_OVERDUE", data["upcoming"]
    assert "bank not checked" not in dash.render(data)
    data = dash.gather(FakeStarling(fail=OSError()), T)  # the feed fails: notes only
    assert not data["bank_checked"] and "bank not checked" in dash.render(data)


def test_file_is_written_mode_600():
    reset()
    path = dash.write("<p>x</p>")
    assert str(path) == os.path.join(TMP, "dashboard.html")
    assert os.stat(path).st_mode & 0o777 == 0o600
    path = dash.write("<p>y</p>")  # a rewrite keeps the mode and leaves no temp files
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert [n for n in os.listdir(TMP) if n.endswith(".tmp")] == []


def test_no_bank_makes_no_starling_calls():
    reset()
    real_token, real_client = dash.lm.keychain_token, dash.lm.StarlingReadOnly
    token_reads = []
    dash.lm.keychain_token = lambda: token_reads.append(1) or "tok"
    dash.lm.StarlingReadOnly = FakeStarling
    try:
        import contextlib, io
        FakeStarling.calls = []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            dash.main(["--no-bank"])
        assert FakeStarling.calls == [] and token_reads == [], FakeStarling.calls
        assert buf.getvalue() == f"dashboard written: {os.path.join(TMP, 'dashboard.html')}\n", buf.getvalue()
        with contextlib.redirect_stdout(io.StringIO()):
            dash.main([])  # the fake is wired in: without --no-bank it is used
        assert ("get", "/api/v2/accounts/uid-1/balance") in FakeStarling.calls
    finally:
        dash.lm.keychain_token, dash.lm.StarlingReadOnly = real_token, real_client


def test_payee_status_never_shows_the_payee_full_name():
    assert dash.payee_status("existing: Ben Fenwick") == "existing payee"
    assert "Fenwick" not in dash.payee_status("name matches payee Ben Fenwick but with different bank details")
    assert "Fenwick" not in dash.payee_status("probably existing: Ben Fenwick (no bank details on the invoice)")
    assert dash.payee_status("NEW: add as a payee in the Starling app").startswith("NEW")


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
