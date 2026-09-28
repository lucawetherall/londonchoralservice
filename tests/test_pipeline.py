#!/usr/bin/env python3
"""Tests for scripts/bookings/pipeline.py. Stdlib only: .venv/bin/python tests/test_pipeline.py"""
import csv, datetime, json, os, stat, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private, even for the in-process imports
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(_HOME, "bookings.csv")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import pipeline as pl  # noqa: E402

PY, SCRIPT = sys.executable, os.path.join(ROOT, "scripts", "bookings", "pipeline.py")
T = datetime.date(2026, 9, 28)
LEDGER_COLS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
               "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]


def days(n):
    return (T - datetime.timedelta(days=n)).isoformat()


def enq(eid="1001", status="quoted", last=None, followups=0, event="2027-06-12", **kw):
    r = {c: "" for c in pl.COLUMNS}
    r.update(enquiry_id=eid, first_seen=days(30), source="web form", occasion="wedding", event_date=event,
             package="Small Choir", quoted_gbp="1150", status=status, last_contact=last or days(0),
             followups=str(followups))
    r.update(kw)
    return r


def booking(ref, event, notes, name="Ann Smith"):
    r = {c: "" for c in LEDGER_COLS}
    r.update(booking_ref=ref, event_date=event, notes=notes, client_name=name, client_email="ann@example.com",
             value_gbp="1150", invoice_date="2026-06-01")
    return r


def kinds(rows, today=T):
    return {d["enquiry_id"]: d["kind"] for d in pl.followups_due(rows, today)}


# --- pure: followups_due -------------------------------------------------------------------------

def test_first_followup_day_4_is_not_due_day_5_is():
    assert kinds([enq(last=days(4))]) == {}
    assert kinds([enq(last=days(5))]) == {"1001": "first"}


def test_second_followup_day_14_is_not_due_day_15_is():
    assert kinds([enq(last=days(14), followups=1)]) == {}
    assert kinds([enq(last=days(15), followups=1)]) == {"1001": "second"}


def test_mark_lost_day_24_is_not_due_day_25_is():
    assert kinds([enq(last=days(24), followups=2)]) == {}
    assert kinds([enq(last=days(25), followups=2)]) == {"1001": "mark_lost"}


def test_the_count_decides_the_kind_not_the_age():
    # 20 days quiet with no follow-up yet: the first follow-up, not the second
    assert kinds([enq(last=days(20), followups=0)]) == {"1001": "first"}


def test_only_quoted_enquiries_get_followups():
    rows = [enq(eid=str(i), status=s, last=days(40)) for i, s in enumerate(sorted(pl.STATUSES)) if s != "quoted"]
    assert kinds(rows) == {}


def test_past_event_gives_mark_lost_never_a_followup():
    for n in (0, 1, 2):
        assert kinds([enq(last=days(1), followups=n, event=days(1))]) == {"1001": "mark_lost"}
    # event today: too late to chase
    assert kinds([enq(last=days(6), event=T.isoformat())]) == {"1001": "mark_lost"}
    # event tomorrow is still live
    assert kinds([enq(last=days(6), event=(T + datetime.timedelta(days=1)).isoformat())]) == {"1001": "first"}


def test_unknown_event_date_still_follows_up():
    assert kinds([enq(last=days(5), event="")]) == {"1001": "first"}


def test_missing_last_contact_falls_back_to_first_seen():
    r = enq(last="")
    r["last_contact"] = ""
    r["first_seen"] = days(5)
    assert kinds([r]) == {"1001": "first"}


def test_followups_due_output_has_only_id_and_kind():
    out = pl.followups_due([enq(last=days(5), notes="Ann Smith, St Mary's")], T)
    assert out == [{"enquiry_id": "1001", "kind": "first"}]


# --- pure: reviews_due ---------------------------------------------------------------------------

def test_reviews_due_includes_and_excludes_the_right_rows():
    rows = [
        booking("OK3", days(3), "deposit seen 2026-06-05 (Starling); paid in full 2026-09-20"),
        booking("OK14", days(14), "paid in full 2026-09-01"),
        booking("NOTPAID", days(5), "deposit seen 2026-06-05 (Starling)"),
        booking("CANC", days(5), "paid in full 2026-09-01; cancelled 2026-09-10"),
        booking("DONE", days(5), "paid in full 2026-09-01; review request drafted 2026-09-26"),
        booking("RECENT", days(2), "paid in full 2026-09-01"),
        booking("OLD", days(15), "paid in full 2026-09-01"),
        booking("FUTURE", "2026-10-10", "paid in full 2026-09-01"),
        booking("NODATE", "", "paid in full 2026-09-01"),
        booking("VAGUE", days(5), "paid in full"),
    ]
    got = pl.reviews_due(rows, T)
    assert got == [{"booking_ref": "OK3", "event_date": days(3)}, {"booking_ref": "OK14", "event_date": days(14)}], got


# --- pure: summary_dict --------------------------------------------------------------------------

def summary_rows():
    return [
        enq("1", status="new", first_seen="2026-09-01", source="web form", quoted_gbp="", package=""),
        enq("2", status="quoted", first_seen="2026-09-02", source="email", notes="quoted 2026-09-04"),
        enq("3", status="confirmed", first_seen="2026-09-03", source="web form", booking_ref="0612",
            notes="quoted 2026-09-04"),
        enq("4", status="done", first_seen="2026-08-01", source="phone", booking_ref="0808", notes="quoted 2026-08-02"),
        enq("5", status="lost", first_seen="2026-09-10", source="web form", notes="quoted 2026-09-20; quoted 2026-09-25"),
        enq("6", status="cancelled", first_seen="2026-09-11", source="referral", booking_ref="1010",
            notes="quoted 2026-09-12"),
    ]


def test_summary_numbers_for_everything():
    s = pl.summary_dict(summary_rows(), None)
    assert s["enquiries"] == 6
    assert s["by_status"] == {"new": 1, "quoted": 1, "confirmed": 1, "deposit_paid": 0, "done": 1, "lost": 1,
                              "cancelled": 1}, s["by_status"]
    assert s["quoted"] == 5, s  # every row that got a quote, whatever happened after
    assert s["confirmed"] == 3, s  # 3, 4 and 6 (booked, then cancelled)
    assert s["conversion_rate"] == 0.5, s
    assert s["by_source"] == {"web form": 3, "email": 1, "phone": 1, "referral": 1}, s["by_source"]
    # days to the first quote: 2, 1, 1, 10, 1 -> median 1
    assert s["median_days_to_quote"] == 1, s


def test_summary_since_filters_on_first_seen():
    s = pl.summary_dict(summary_rows(), "2026-09-03")
    assert s["enquiries"] == 3 and s["quoted"] == 3 and s["confirmed"] == 2, s
    assert s["conversion_rate"] == round(2 / 3, 3), s
    assert s["median_days_to_quote"] == 1, s  # 1, 10, 1
    assert pl.summary_dict(summary_rows(), datetime.date(2026, 9, 3)) == s


def test_summary_of_nothing():
    s = pl.summary_dict([], None)
    assert s["enquiries"] == 0 and s["conversion_rate"] is None and s["median_days_to_quote"] is None, s
    assert json.dumps(s)


# --- CLI -----------------------------------------------------------------------------------------

def home():
    d = tempfile.mkdtemp()
    return d


def cli(d, *args):
    env = dict(os.environ, LCS_PRIVATE_DIR=d, LCS_BOOKINGS_CSV=os.path.join(d, "bookings.csv"))
    return subprocess.run([PY, SCRIPT, *args], env=env, capture_output=True, text=True)


def enquiries(d):
    with open(os.path.join(d, "enquiries.csv"), newline="") as f:
        return {r["enquiry_id"]: r for r in csv.DictReader(f)}


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def add(d, **kw):
    row = {"enquiry_id": "1001", "first_seen": "2026-09-20", "source": "web form", "occasion": "wedding",
           "event_date": "2027-06-12"}
    row.update(kw)
    return cli(d, "add", json.dumps(row))


def test_cli_add_sets_defaults_and_mode_600():
    d = home()
    p = add(d, gclid="abc123")
    assert p.returncode == 0 and p.stdout.strip() == "enquiry 1001: added", (p.stdout, p.stderr)
    r = enquiries(d)["1001"]
    assert (r["status"], r["followups"], r["last_contact"], r["gclid"]) == ("new", "0", "2026-09-20", "abc123"), r
    path = os.path.join(d, "enquiries.csv")
    assert mode(path) == 0o600, oct(mode(path))
    with open(path, newline="") as f:
        assert next(csv.reader(f)) == pl.COLUMNS


def test_cli_add_refuses_duplicate_and_unknown_field():
    d = home()
    assert add(d).returncode == 0
    p = add(d, occasion="funeral")
    assert p.returncode != 0 and "duplicate" in p.stderr.lower(), (p.stdout, p.stderr)
    p = add(d, enquiry_id="1002", client_name="Ann Smith")
    assert p.returncode != 0 and "client_name" in p.stderr and "Ann" not in p.stderr + p.stdout, p.stderr
    assert list(enquiries(d)) == ["1001"]
    assert enquiries(d)["1001"]["occasion"] == "wedding"


def test_cli_add_validates_values():
    d = home()
    for bad in ({"source": "carrier pigeon"}, {"status": "maybe"}, {"first_seen": "20/09/2026"},
                {"event_date": "2027-13-01"}, {"followups": 3}, {"status": "confirmed"}, {"enquiry_id": ""},
                {"quoted_gbp": "lots"}, {"notes": "two\nlines"}):
        p = add(d, **bad)
        assert p.returncode != 0, (bad, p.stdout)
    assert not os.path.exists(os.path.join(d, "enquiries.csv")) or enquiries(d) == {}


def test_cli_add_accepts_json_numbers():
    d = home()
    assert add(d, quoted_gbp=1150, followups=0).returncode == 0
    assert enquiries(d)["1001"]["quoted_gbp"] == "1150"


def test_cli_quoted_contact_followed_and_status():
    d = home()
    add(d)
    p = cli(d, "quoted", "1001", "Small Choir", "1,150", "2026-09-21")
    assert p.returncode == 0 and p.stdout.strip() == "enquiry 1001: quoted", (p.stdout, p.stderr)
    r = enquiries(d)["1001"]
    assert (r["status"], r["package"], r["quoted_gbp"], r["last_contact"]) == ("quoted", "Small Choir", "1150",
                                                                                 "2026-09-21"), r
    assert "quoted 2026-09-21" in r["notes"], r
    p = cli(d, "followed", "1001", "1", "2026-09-26")
    assert p.returncode == 0, p.stderr
    r = enquiries(d)["1001"]
    assert (r["followups"], r["last_contact"]) == ("1", "2026-09-26"), r
    p = cli(d, "followed", "1001", "1", "2026-09-27")
    assert p.returncode != 0, "a follow-up recorded twice must be refused"
    p = cli(d, "contact", "1001", "2026-09-28")
    assert p.returncode == 0, p.stderr
    r = enquiries(d)["1001"]
    assert (r["followups"], r["last_contact"]) == ("0", "2026-09-28"), r
    p = cli(d, "status", "1001", "confirmed")
    assert p.returncode != 0 and "booking_ref" in p.stderr, p.stderr
    p = cli(d, "status", "1001", "confirmed", "1206")
    assert p.returncode == 0, p.stderr
    r = enquiries(d)["1001"]
    assert (r["status"], r["booking_ref"]) == ("confirmed", "1206"), r
    assert cli(d, "status", "1001", "sort of").returncode != 0
    assert mode(os.path.join(d, "enquiries.csv")) == 0o600


def test_cli_contact_resets_followups():
    d = home()
    add(d, status="quoted", followups=2, last_contact="2026-09-01", quoted_gbp=1150, package="Small Choir")
    assert cli(d, "contact", "1001", "2026-09-20").returncode == 0
    r = enquiries(d)["1001"]
    assert (r["followups"], r["last_contact"]) == ("0", "2026-09-20"), r
    p = cli(d, "followups-due", "--today", "2026-09-24")
    assert json.loads(p.stdout) == [], p.stdout
    p = cli(d, "followups-due", "--today", "2026-09-25")
    assert json.loads(p.stdout) == [{"enquiry_id": "1001", "kind": "first"}], p.stdout


def test_cli_unknown_enquiry_is_refused():
    d = home()
    add(d)
    for args in (["quoted", "9999", "Small Choir", "1150", "2026-09-21"], ["contact", "9999", "2026-09-21"],
                 ["status", "9999", "lost"], ["followed", "9999", "1", "2026-09-21"]):
        p = cli(d, *args)
        assert p.returncode != 0 and "9999" in p.stderr, (args, p.stderr)


def test_cli_followups_due_json():
    d = home()
    add(d, enquiry_id="A", status="quoted", last_contact="2026-09-20", quoted_gbp=1150)
    add(d, enquiry_id="B", status="quoted", last_contact="2026-09-10", followups=1, quoted_gbp=1150)
    add(d, enquiry_id="C", status="quoted", last_contact="2026-09-27", event_date="2026-09-26", quoted_gbp=1150)
    add(d, enquiry_id="D", status="new", last_contact="2026-09-01")
    p = cli(d, "followups-due", "--today", "2026-09-28")
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout) == [{"enquiry_id": "A", "kind": "first"}, {"enquiry_id": "B", "kind": "second"},
                                    {"enquiry_id": "C", "kind": "mark_lost"}], p.stdout


def test_cli_followups_due_with_no_file():
    d = home()
    p = cli(d, "followups-due", "--today", "2026-09-28")
    assert p.returncode == 0 and json.loads(p.stdout) == [], (p.stdout, p.stderr)


def write_ledger(d, rows, cols=LEDGER_COLS):
    path = os.path.join(d, "bookings.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.chmod(path, 0o644)  # a rewrite must tighten it to 600
    return path


def test_cli_reviews_due_and_reviewed_keep_columns_and_mode():
    d = home()
    cols = ["notes", "booking_ref", "client_name", "event_date", "value_gbp", "extra_col"]
    rows = [booking("2009", "2026-09-20", "paid in full 2026-09-19"),
            booking("1509", "2026-09-15", "deposit seen 2026-08-01 (Starling)", name="Bob Jones")]
    rows[0]["extra_col"] = "keep me"
    path = write_ledger(d, rows, cols)
    p = cli(d, "reviews-due", "--today", "2026-09-28")
    assert p.returncode == 0 and json.loads(p.stdout) == [{"booking_ref": "2009", "event_date": "2026-09-20"}], p.stdout
    p = cli(d, "reviewed", "2009", "2026-09-28")
    assert p.returncode == 0 and p.stdout.strip() == "2009: review request drafted 2026-09-28", (p.stdout, p.stderr)
    with open(path, newline="") as f:
        assert next(csv.reader(f)) == cols
    with open(path, newline="") as f:
        got = {r["booking_ref"]: r for r in csv.DictReader(f)}
    assert got["2009"]["notes"] == "paid in full 2026-09-19; review request drafted 2026-09-28", got["2009"]
    assert got["2009"]["extra_col"] == "keep me" and got["1509"]["client_name"] == "Bob Jones"
    assert mode(path) == 0o600, oct(mode(path))
    p = cli(d, "reviews-due", "--today", "2026-09-28")
    assert json.loads(p.stdout) == [], p.stdout
    p = cli(d, "reviewed", "9999", "2026-09-28")
    assert p.returncode != 0 and "9999" in p.stderr, p.stderr
    p = cli(d, "reviewed", "2009", "2026-09-29")
    assert p.returncode != 0 and "already" in p.stderr, "a second review request must be refused"


def test_cli_summary_json():
    d = home()
    add(d, enquiry_id="1", first_seen="2026-09-01", source="email")
    add(d, enquiry_id="2", first_seen="2026-09-10", source="web form")
    cli(d, "quoted", "2", "Small Choir", "1150", "2026-09-12")
    cli(d, "status", "2", "confirmed", "1206")
    p = cli(d, "summary")
    s = json.loads(p.stdout)
    assert (s["enquiries"], s["quoted"], s["confirmed"], s["conversion_rate"], s["median_days_to_quote"]) == (
        2, 1, 1, 0.5, 2), s
    assert s["by_source"] == {"email": 1, "web form": 1}, s
    s = json.loads(cli(d, "summary", "--since", "2026-09-05").stdout)
    assert s["enquiries"] == 1 and s["conversion_rate"] == 1.0, s


def test_cli_output_contains_no_names():
    d = home()
    name_bits = ["Ann", "Smith", "ann@example.com", "St Mary"]
    outs = [add(d, notes="Ann Smith, St Mary's, ann@example.com", last_contact="2026-09-01")]
    outs.append(cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-10"))
    outs.append(cli(d, "followups-due", "--today", "2026-09-28"))
    outs.append(cli(d, "followed", "1001", "1", "2026-09-28"))
    outs.append(cli(d, "contact", "1001", "2026-09-28"))
    outs.append(cli(d, "status", "1001", "confirmed", "1206"))
    outs.append(cli(d, "summary"))
    write_ledger(d, [booking("2009", "2026-09-20", "paid in full 2026-09-19")])
    outs.append(cli(d, "reviews-due", "--today", "2026-09-28"))
    outs.append(cli(d, "reviewed", "2009", "2026-09-28"))
    for p in outs:
        assert p.returncode == 0, (p.args, p.stderr)
        for bit in name_bits:
            assert bit not in p.stdout and bit not in p.stderr, (p.args, p.stdout)


def test_paths_follow_the_private_dir():
    assert str(pl.ENQUIRIES) == os.path.join(_HOME, "enquiries.csv"), pl.ENQUIRIES


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
