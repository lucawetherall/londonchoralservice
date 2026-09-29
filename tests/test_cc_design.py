#!/usr/bin/env python3
"""Tests for the Command Centre's design and phone-layout pass: the transfer-fee question on Today, the hand-check
reasons, hashed enquiry URLs (old ones redirect), control names that carry context, table roles, and the CSS and
script rules that keep every page inside a 375 px screen with 44 px targets.

Stdlib runner and Starlette's TestClient, on test_cc_final's FAKE fixtures in a temp LCS_PRIVATE_DIR (fake names,
example.org emails) and a fake GET-only Starling client. Never touches ~/lcs-private, the bank, Zoho or Google.
.venv/bin/python tests/test_cc_design.py
"""
import datetime, html as html_mod, json, os, re, sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_cc_final as base  # noqa: E402  its fixtures, client and helpers (and its temp LCS_PRIVATE_DIR)

from command_centre import actions, models  # noqa: E402

lm, cp, pl, si = base.lm, base.cp, base.pl, base.si
TODAY = base.TODAY
STATIC = Path(ROOT) / "command_centre" / "static"
TEMPLATES = Path(ROOT) / "command_centre" / "templates"
THREAD = "1789828736363141700"


def ago(n):
    return (TODAY - datetime.timedelta(days=n)).isoformat()


def ahead(n):
    return (TODAY + datetime.timedelta(days=n)).isoformat()


def booking(ref, value, event, notes="", first="Bea"):
    return {"booking_ref": ref, "invoice_date": ago(40), "event_date": event, "client_name": f"{first} Testworthy",
            "client_email": f"{first.lower()}@example.org", "occasion": "wedding", "ensemble": "Octet",
            "value_gbp": value, "notes": notes}


# ref -> the confident payments in the fake feed, (pence, days ago)
PAYMENTS = {
    "2408": ((47500, 35), (46260, 2)),    # £937.60 of £950 (98.7%), event ahead: £12.40 short -> a fee row
    "0909": ((36654, 50), (33039, 10)),   # £696.93 of £733.08 (95.1%), event passed: a hand check with the fee folded
    "1010": ((57500, 40),),               # £575 of £1,150 (50%), event passed: a hand check, never a fee question
    "3030": ((70000, 30),),               # £700 of £730 (95.9%), event in 2 days: BALANCE_DUE, £30 short -> a fee row
    "5050": ((10000, 30),),               # £100 of £130 (76.9%): a £30 gap under 90% in -> no fee row
    "6060": ((90000, 30),),               # £900 of £945 (95.2%): £45 short, over the £40 cap -> no fee row
}


class FeeBank(base.FakeBank):
    def feed(self, since, until, direction):
        return [{"direction": "IN", "amount": {"minorUnits": m}, "transactionTime": f"{ago(d)}T10:00:00Z",
                 "reference": f"INV {ref}", "counterPartyName": "B TESTWORTHY"}
                for ref, pays in PAYMENTS.items() for m, d in pays]


def fee_fixtures():
    base.fixtures()
    rows = lm.read_csv(cp.LEDGER) + [
        booking("2408", "950", ahead(20), f"deposit seen {ago(35)} (Starling)"),
        booking("0909", "733.08", ago(5), first="Cy"),
        booking("1010", "1150", ago(8), first="Di"),
        booking("3030", "730", ahead(2), first="Ed"),
        booking("5050", "130", ahead(20), first="Gil"),
        booking("6060", "945", ahead(20), first="Hal"),
    ]
    lm.write_csv(lm.LEDGER, rows, base.LEDGER_COLS)


def assessments():
    rows = lm.read_csv(cp.LEDGER)
    return {a["ref"]: a for _, _, a in cp.collect(FeeBank(), rows, TODAY)}


def text(html):
    """The visible text, tags gone, and no space left before punctuation where a tag ended."""
    return re.sub(r"\s+([:;.,?)])", r"\1", html_mod.unescape(base.text_of(html)))


def need_li(html, kind, ref=None):
    for m in re.finditer(r'<li class="need[^"]*" data-kind="([^"]+)" data-count="\d+">(.*?)</li>', html, re.S):
        if m.group(1) == kind and (ref is None or f"/bookings/{ref}" in m.group(2)):
            return m.group(2)
    return None


# ---------------------------------------------------------------- the transfer-fee question (item 1)


def test_fee_shortfall_rules():
    fee_fixtures()
    a = assessments()
    assert a["2408"]["state"] == "DEPOSIT_SEEN" and a["0909"]["state"] == "PAST_PART_PAID", a
    got = {ref: models.fee_shortfall(x, True) for ref, x in a.items()}
    assert got["2408"] == {"ref": "2408", "gap": 12.4, "value": 950.0, "received": 937.6, "state": "DEPOSIT_SEEN"}
    assert got["0909"]["gap"] == 36.15 and got["0909"]["value"] == 733.08
    assert got["3030"]["gap"] == 30.0 and a["3030"]["state"] == "BALANCE_DUE"
    assert got["1010"] is None       # half paid: the gap is over the cap, and under 90% is in
    assert got["5050"] is None       # a £30 gap, but only 76.9% in: a deposit-sized payment never qualifies
    assert got["6060"] is None       # 95% in, but £45 short: over check_payments.FEE_CAP
    assert got["0310"] is None       # nothing in the bank
    assert all(v is None for v in (models.fee_shortfall(x, False) for x in a.values()))  # bank not checked
    # the edges: 1p and exactly the cap count; a 1p-over-cap gap, a gap that isn't the whole balance and a state
    # outside FEE_STATES don't
    edge = dict(a["2408"], value=1000.0, received=960.0, balance=40.0)
    assert models.fee_shortfall(edge, True)["gap"] == 40.0
    assert models.fee_shortfall(dict(edge, received=959.99, balance=40.01), True) is None
    assert models.fee_shortfall(dict(edge, received=999.99, balance=0.01), True)["gap"] == 0.01
    assert models.fee_shortfall(dict(edge, balance=12.0), True) is None
    assert models.fee_shortfall(dict(edge, state="CHECK_PAYMENT"), True) is None
    assert models.fee_shortfall(dict(edge, value=400.0, received=360.0), True)["gap"] == 40.0   # exactly 90%
    assert models.fee_shortfall(dict(edge, value=400.0, received=359.0, balance=41.0), True) is None
    assert models.fee_shortfall(dict(edge, value=300.0, received=269.0, balance=31.0), True) is None  # 89.7%
    assert actions.FEE_STATES == models.FEE_STATES


def test_today_asks_about_fee_shortfalls_once_each():
    fee_fixtures()
    c = base.make(FeeBank())
    out = base.page(c, "/")
    rows = base.needs_rows(out)
    li = need_li(out, "fee", "2408")
    assert li and "2408: £12.40 short of £950.00 — accept as transfer fees?" in text(li), li
    assert 'name="choice" value="short-by-fees"' in li and 'name="amount" value="12.40"' in li
    assert need_li(out, "fee", "3030") and 'name="amount" value="30.00"' in need_li(out, "fee", "3030")
    # a hand check that is also a shortfall stays one row, with the fee form folded in
    hand = need_li(out, "hand", "0909")
    assert hand and "£36.15 short of £733.08; the event has passed" in text(hand), hand
    assert "Accept the £36.15 as transfer fees?" in text(hand) and 'name="amount" value="36.15"' in hand
    money_rows = re.findall(r'data-kind="(hand|fee|balances|deposits)" data-count="\d+">(.*?)</li>', out, re.S)
    assert need_li(out, "fee", "0909") is None and sum("/bookings/0909" in li for _, li in money_rows) == 1
    # no fee question under 90% in, over the cap, or with nothing in the bank
    for ref in ("1010", "5050", "6060", "0310", "1212"):
        assert need_li(out, "fee", ref) is None, ref
    assert "accept as transfer fees" not in text(need_li(out, "hand", "1010"))
    # a BALANCE_DUE balance that is only a fee shortfall isn't also chased in the balances row
    bal = need_li(out, "balances")
    assert bal is None or "3030" not in bal
    # the count is the rows
    assert base.lede_number(out) == str(sum(n for _, n in rows)), (base.lede_number(out), rows)
    assert [k for k, _ in rows].count("fee") == 2
    # the server still checks the amount against the bank (actions._fee_facts): the row's form is valid
    cleaned = actions.RESOLVE_HAND_CHECK.validate({"ref": "2408", "choice": "short-by-fees", "date": TODAY.isoformat(),
                                                   "amount": "12.40"})
    assert cleaned["phrase"].startswith("short by fees £12.40 accepted")


def test_fee_rows_need_a_checked_bank():
    fee_fixtures()
    out = base.page(base.make(None), "/")   # no bank client: payment states come from the ledger notes
    assert "data-kind=\"fee\"" not in out and "short-by-fees" not in out


# ---------------------------------------------------------------- hand-check reasons (item 2)


def test_hand_reasons_say_why_with_the_amounts():
    a = {"ref": "X1", "value": 733.08, "received": 696.93, "balance": 36.15, "event_date": "2026-09-23"}
    r = lambda **kw: models.hand_reason(dict(a, **kw), True)  # noqa: E731
    assert r(state="PAST_PART_PAID") == "£36.15 short of £733.08; the event has passed"
    assert r(state="PAST_UNMATCHED", received=0) == "no payment for £733.08 in the bank; the event has passed"
    assert r(state="NOTED_PAID") == "£696.93 of £733.08 in the bank; the ledger notes say the rest was paid"
    assert r(state="NOTED_PAID", received=0) == "no payment for £733.08 in the bank; the ledger notes say it was paid"
    assert r(state="CHECK_PAYMENT", received=0, unconfirmed=[["2026-09-20", 250.0]]) == \
        "£250.00 on 20 Sep may be for this £733.08 booking: confirm it"
    assert r(state="CHECK_PAYMENT", possible_balance=[["2026-09-25", 36.15]]) == \
        "£696.93 of £733.08 in; £36.15 on 25 Sep may be the balance: confirm it"
    assert r(state="CHECK_VALUE", value=0) == "the fee is missing or unreadable in the ledger"
    assert r(state="CHECK_VALUE") == "the invoice or event date is missing or unreadable in the ledger"
    assert r(state="PAYMENT_ON_CANCELLED", hand_check_payments=[["2026-09-01", 150.0]]) == \
        "£150.00 on 1 Sep paid on a cancelled booking: refund or keep"
    assert r(state="PAYMENT_AFTER_CLOSE", hand_check_payments=[["2026-09-02", 20.0]]) == \
        "£20.00 on 2 Sep paid after it was paid in full"
    assert r(state="ARRANGED", arranged_no_deposit=True) == \
        "£36.15 to collect in cash or by cheque on the day (23 Sep); no deposit seen"
    assert "ledger notes" in models.hand_reason(dict(a, state="PAST_UNMATCHED"), False)
    # every hand-check state has a reason of its own, never just the label
    for state in cp.HAND_CHECK_STATES | {"ARRANGED"}:
        assert models.hand_reason(dict(a, state=state), True) != models.mr.HAND_CHECK[state], state


def test_money_lists_the_reason_too():
    fee_fixtures()
    out = base.page(base.make(FeeBank()), "/money")
    t = text(out)
    assert "£36.15 short of £733.08; the event has passed" in t and "£575.00 short of £1,150.00" in t
    assert "Resolve 0909" in t and "Resolve 1010" in t


# ---------------------------------------------------------------- hashed enquiry URLs (item 8)


def enquiry_fixtures():
    base.fixtures()
    row = dict({k: "" for k in pl.COLUMNS}, enquiry_id=THREAD, first_seen=ago(3), source="website",
               occasion="wedding", status="quoted", quoted_gbp="650", last_contact=ago(3), event_date=ahead(40))
    lm.write_csv(pl.ENQUIRIES, [row], pl.COLUMNS)


def test_enquiry_pages_use_the_hashed_id_and_old_urls_redirect():
    enquiry_fixtures()
    key = models.enquiry_key(THREAD)
    assert re.fullmatch(r"[a-z]{12}", key) and key == models.enquiry_key(THREAD) != models.enquiry_key(THREAD + "1")
    c = base.make(base.FakeBank())
    r = c.get(f"/enquiries/{THREAD}", headers=base.HEADERS)
    assert r.status_code == 301 and r.headers["location"] == f"/enquiries/{key}", (r.status_code, r.headers)
    before = sorted(p.name for p in Path(base.TMP).rglob("*"))
    out = base.page(c, f"/enquiries/{key}")
    assert sorted(p.name for p in Path(base.TMP).rglob("*")) == before  # a GET writes nothing
    assert THREAD not in out and f"Enquiry {key}" in out and "wedding" in out
    assert c.get("/enquiries/abcdefghijkl", headers=base.HEADERS).status_code == 404   # a key nobody has
    assert c.get("/enquiries/1789828736363140000", headers=base.HEADERS).status_code == 404  # an unknown thread
    assert c.get("/enquiries/bad%20id", headers=base.HEADERS).status_code == 404
    assert c.post(f"/enquiries/{THREAD}", headers=base.POST_HEADERS).status_code == 405
    # no page names the thread: the list, the calendar and search link to the key
    for path in ("/enquiries", f"/calendar?date={ahead(40)}", "/search?q=wedd"):
        page = base.page(c, path)
        assert THREAD not in page and f"/enquiries/{key}" in page, path


# ---------------------------------------------------------------- names with context, table roles (items 6, 7)


def test_controls_carry_their_context():
    fee_fixtures()
    base.write(base.CACHE / "drafts.json", json.dumps([
        {"thread_id": "1789828736363141999", "kind": "follow-up", "first_name": "Maddy", "subject": "Your quote",
         "created": ago(1), "source": "assistant"}]))
    cfg = base.auth.load_config()
    cfg["push_subscriptions"] = [{"id": "0123456789abcdef", "service": "Apple", "added": "2026-09-20T10:00:00+01:00",
                                  "endpoint": "https://web.push.apple.com/x", "p256dh": "k", "auth": "a"}]
    base.auth.save_config(cfg)
    os.environ["CC_VAPID_STORE"] = "file"
    try:
        c = base.make(FeeBank())
        today = text(base.page(c, "/"))
        assert "Resolve 0909" in today and "Resolve 1010" in today
        money = base.page(c, "/money")
        assert "Act on Ben's invoice" in text(money) and 'aria-label="Mark paid: Ben"' in money
        assert "Act on Ben's invoice" in text(base.page(c, "/singers"))
        drafts = base.page(c, "/drafts")
        assert 'aria-label="Mark sent: Maddy, quote follow-up"' in drafts and ">Mark sent<" in drafts
        assert 'data-label=""' not in drafts and "<th role=\"columnheader\"></th>" not in drafts
        device = base.page(c, "/device")
        assert "Remove this device" in text(device) and 'aria-label="Remove this device (Apple, 0123456789abcdef)"' in device
        # every accessible name starts with the visible label (WCAG 2.5.3)
        for page in (money, drafts, device):
            for label, inner in re.findall(r'<button[^>]*aria-label="([^"]+)"[^>]*>([^<]+)</button>', page):
                assert html_mod.unescape(label).startswith(html_mod.unescape(inner.strip())), (label, inner)
    finally:
        os.environ.pop("CC_VAPID_STORE", None)


def test_stacked_tables_keep_their_roles():
    fee_fixtures()
    c = base.make(FeeBank())
    for path in ("/", "/money", "/bookings", "/singers"):
        out = base.page(c, path)
        for table in re.findall(r"<table\b[^>]*>.*?</table>", out, re.S):
            assert 'role="table"' in table.split(">", 1)[0], path
            assert not re.search(r"<(tr|td|th)(?![^>]*role=)[\s>]", table), (path, table[:200])
            assert 'data-label=""' not in table
    for name in TEMPLATES.glob("*.html"):
        src = name.read_text()
        assert not re.search(r"<td(?![^>]*role=)[\s>]", src), name.name


# ---------------------------------------------------------------- calendar (item 5)


def test_calendar_entries_link_and_show_in_full():
    enquiry_fixtures()
    c = base.make(base.FakeBank())
    out = base.page(c, "/calendar?date=2026-10-01")
    assert 'role="grid"' not in out and 'role="gridcell"' not in out and 'role="row"' not in out
    assert re.search(r'<a class="cal-item k-event" href="/bookings/0310">0310 Ann, wedding</a>', out), out
    assert re.search(r'<a class="cal-num" href="/calendar\?view=week&amp;date=2026-10-03" aria-label="Sat 3 Oct 2026, '
                     r'\d+ entr(y|ies): open the week">3</a>', out)
    assert "+1 more" not in out and "more</span>" not in out
    css = (STATIC / "app.css").read_text()
    cal = re.search(r"\.cal-item \{([^}]*)\}", css).group(1)
    assert "ellipsis" not in cal and "nowrap" not in cal and "overflow-wrap: anywhere" in cal


# ---------------------------------------------------------------- CSS and scripts (items 3, 4, 9)


def rule(css, selector):
    m = re.search(r"(?:^|\n)" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert m, selector
    return m.group(1)


def test_nothing_forces_a_page_wider_than_a_phone():
    css = (STATIC / "app.css").read_text()
    for sel in (".button", ".badge"):
        body = rule(css, sel)
        assert "white-space: normal" in body and "nowrap" not in body and "max-width: 100%" in body, sel
    assert "white-space: normal" in rule(css, ".table td .badge")
    assert "overflow-wrap: anywhere" in rule(css, "h1") and "overflow-wrap: anywhere" in rule(css, ".need-text")
    # the header nav and the sync strip scroll inside themselves, with an edge shade as the cue
    assert "overflow-x: auto" in rule(css, ".nav") and "background-attachment" not in rule(css, ".nav")
    shade = rule(css, ".top .nav, .sync-chips")
    assert shade.count("local") == 2 and shade.count("scroll") == 2 and "var(--edge)" in shade


def test_touch_targets_safe_areas_and_the_dialog():
    css = (STATIC / "app.css").read_text()
    assert "--target: 44px" in css
    for sel in (".button", ".button.small", "details summary", ".act > summary", ".chip", ".seg-item", ".copy-value",
                ".foot a", ".brand", ".nav-item", ".agenda-item"):
        assert "min-height: var(--target)" in rule(css, sel), sel
    assert re.search(r"\.cal-num \{[^}]*min-width: var\(--target\); min-height: var\(--target\)", css)
    assert "summary:focus-visible" in css and "select:focus-visible" in css
    dialog = rule(css, ".dialog")
    assert "calc(100vh - 32px)" in dialog and "calc(100dvh - 32px)" in dialog
    assert dialog.index("100vh") < dialog.index("100dvh")  # the fallback first
    assert "env(safe-area-inset-left)" in css and "env(safe-area-inset-right)" in css
    for sel in (".top-inner", ".main", ".foot"):
        assert "var(--gutter-l)" in rule(css, sel) and "var(--gutter-r)" in rule(css, sel), sel
    assert "viewport-fit=cover" in (TEMPLATES / "base.html").read_text()


def test_clear_offline_copies_never_waits_forever():
    js = (STATIC / "push.js").read_text()
    assert "READY_WAIT" in js and "Promise.race" in js
    # only ready() reads it, raced against the timeout: nothing awaits or chains on it directly
    assert "await navigator.serviceWorker.ready" not in js and "serviceWorker.ready.then" not in js
    assert "Nothing to clear: this browser keeps no offline copies" in js
    swap = (STATIC / "swap.js").read_text()
    assert 'querySelector(\'[aria-current="page"]\')' in swap and "scrollLeft" in swap


def test_masking_keeps_dates_and_hides_bank_numbers():
    # 29 Sep: 2408's timeline showed "short by fees £36.15 accepted ••••0929" (the date was masked)
    assert models.mask_note("short by fees £36.15 accepted 2026-09-29 (owner)") == \
        "short by fees £36.15 accepted 2026-09-29 (owner)"
    assert models.mask_digits("paid in full 2026-09-29; deposit seen 2026-08-26") == \
        "paid in full 2026-09-29; deposit seen 2026-08-26"
    for raw, shown in (("account 12345678", "account ••••5678"), ("sort code 12-34-56", "sort code ••••3456"),
                       ("1234 5678", "••••5678"), ("2026-13-01", "••••1301"), ("20260929", "••••0929")):
        assert models.mask_digits(raw) == shown, (raw, models.mask_digits(raw))


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:  # an error is a failure too
            failures += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"{failures} failure(s)")
    sys.exit(1 if failures else 0)
