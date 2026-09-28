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


def booking(ref, event, notes, name="Ann Smith", occasion="Wedding"):
    r = {c: "" for c in LEDGER_COLS}
    r.update(booking_ref=ref, event_date=event, notes=notes, client_name=name, client_email="ann@example.com",
             value_gbp="1150", invoice_date="2026-06-01", occasion=occasion)
    return r


def kinds(rows, today=T):
    return {d["enquiry_id"]: d["kind"] for d in pl.followups_due(rows, today)}


# --- pure: followups_due -------------------------------------------------------------------------

def test_first_followup_day_4_is_not_due_day_5_is():
    assert kinds([enq(last=days(4))]) == {}
    assert kinds([enq(last=days(5))]) == {"1001": "first"}


def test_second_followup_9_days_after_the_first_is_not_due_10_is():
    # last_contact is the day of the first follow-up (`followed` moves it)
    assert kinds([enq(last=days(9), followups=1)]) == {}
    assert kinds([enq(last=days(10), followups=1)]) == {"1001": "second"}


def test_mark_lost_9_days_after_the_second_is_not_due_10_is():
    assert kinds([enq(last=days(9), followups=2)]) == {}
    assert kinds([enq(last=days(10), followups=2)]) == {"1001": "mark_lost"}


def test_timing_constants():
    assert (pl.FIRST_AFTER, pl.SECOND_AFTER, pl.LOST_AFTER) == (5, 10, 10)


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


def test_booked_enquiries_are_never_chased():
    # a booking_ref means the client booked, whatever the status says
    assert kinds([enq(last=days(20), booking_ref="0612")]) == {}
    assert kinds([enq(last=days(20), followups=2, booking_ref="0612", event=days(1))]) == {}


def test_funeral_enquiries_are_never_chased():
    for occasion in ("funeral", "Funeral", "FUNERAL SERVICE", "Memorial service", "requiem", "celebration of life"):
        for n in (0, 1, 2):
            assert kinds([enq(last=days(40), followups=n, occasion=occasion)]) == {}, (occasion, n)
        # once the event has passed the enquiry is closed, without a chase
        assert kinds([enq(last=days(40), occasion=occasion, event=days(1))]) == {"1001": "mark_lost"}, occasion
        # with no event date, it is never marked lost either
        assert kinds([enq(last=days(400), followups=2, occasion=occasion, event="")]) == {}, occasion
    assert kinds([enq(last=days(5), occasion="wedding")]) == {"1001": "first"}


def test_blank_occasion_is_never_chased():
    assert kinds([enq(last=days(40), occasion="")]) == {}


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


def test_reviews_due_never_asks_a_funeral_or_an_unknown_occasion():
    rows = [booking(f"R{i}", days(5), "paid in full 2026-09-20", occasion=o)
            for i, o in enumerate(["Funeral", "FUNERAL SERVICE", "Memorial service", "", "  ", "Wedding"])]
    assert pl.reviews_due(rows, T) == [{"booking_ref": "R5", "event_date": days(5)}], pl.reviews_due(rows, T)


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


def test_summary_counts_quoted_status_drops_negative_waits_and_ignores_case():
    rows = [
        enq("1", status="quoted", first_seen="2026-09-01", quoted_gbp="", notes=""),  # quoted, no figure recorded
        enq("2", status="Confirmed", first_seen="2026-09-01", booking_ref="0612", notes="quoted 2026-09-03"),
        enq("3", status=" LOST ", first_seen="2026-09-10", quoted_gbp="", notes="quoted 2026-09-05"),  # typo'd date
    ]
    s = pl.summary_dict(rows, None)
    assert s["by_status"]["quoted"] == 1 and s["by_status"]["confirmed"] == 1 and s["by_status"]["lost"] == 1, s
    assert s["quoted"] == 3, s
    assert s["confirmed"] == 1, s
    assert s["median_days_to_quote"] == 2, s  # the -5 is dropped


def test_summary_of_nothing():
    s = pl.summary_dict([], None)
    assert s["enquiries"] == 0 and s["conversion_rate"] is None and s["median_days_to_quote"] is None, s
    assert json.dumps(s)


# --- pure: helpers -------------------------------------------------------------------------------

def refused(fn, *a):
    try:
        fn(*a)
    except SystemExit:
        return True
    return False


def test_gbp_limits():
    assert pl.gbp("1,150") == "1150" and pl.gbp("100000") == "100000" and pl.gbp("0.5") == "0.50"
    for bad in ("0", "0.004", "-5", "100000.01", "250000", "inf", "nan", "lots"):
        assert refused(pl.gbp, bad), bad


def test_to_date_turns_a_datetime_into_a_date():
    d = pl.to_date(datetime.datetime(2026, 9, 28, 10, 30))
    assert d == datetime.date(2026, 9, 28) and type(d) is datetime.date, d


# --- CLI -----------------------------------------------------------------------------------------

def home():
    d = tempfile.mkdtemp()
    return d


def cli(d, *args, stdin=None):
    env = dict(os.environ, LCS_PRIVATE_DIR=d, LCS_BOOKINGS_CSV=os.path.join(d, "bookings.csv"))
    return subprocess.run([PY, SCRIPT, *args], env=env, capture_output=True, text=True, input=stdin)


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
    p = add(d, gclid="Cj0KCQjw_abc123-XYZ")
    assert p.returncode == 0 and p.stdout.strip() == "enquiry 1001: added", (p.stdout, p.stderr)
    r = enquiries(d)["1001"]
    assert (r["status"], r["followups"], r["last_contact"], r["gclid"]) == ("new", "0", "2026-09-20",
                                                                             "Cj0KCQjw_abc123-XYZ"), r
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


def test_cli_add_limits_lengths_and_names_only_the_field():
    d = home()
    secret = "Ann Smith " * 40
    p = add(d, notes=secret[:301])
    assert p.returncode != 0 and "notes" in p.stderr and "Ann" not in p.stderr + p.stdout, p.stderr
    p = add(d, package="Ann Smith choir " * 6)
    assert p.returncode != 0 and "package" in p.stderr and "Ann" not in p.stderr + p.stdout, p.stderr
    assert not os.path.exists(os.path.join(d, "enquiries.csv")) or enquiries(d) == {}
    assert add(d, notes="x" * 300, package="y" * 80).returncode == 0


def test_cli_add_occasion_must_be_known():
    d = home()
    for bad in ("party", "", "wedding reception"):
        p = add(d, occasion=bad)
        assert p.returncode != 0 and "occasion" in p.stderr, (bad, p.stderr)
    no_occasion = dict(enquiry_id="1002", first_seen="2026-09-20", source="email")
    p = cli(d, "add", json.dumps(no_occasion))
    assert p.returncode != 0 and "occasion" in p.stderr, p.stderr
    for i, ok in enumerate(("wedding", "funeral", "christmas", "corporate", "private event", "other", "Private Event")):
        assert add(d, enquiry_id=f"OK{i}", occasion=ok).returncode == 0, ok
    assert enquiries(d)["OK6"]["occasion"] == "private event"


def test_cli_add_gclid_shape():
    d = home()
    long_ok = "Cj0KCQjw" + "a" * 142  # 150 characters: longer than the 80 for other fields
    for i, ok in enumerate(("Cj0KCQjw_abc-123", "gbraid:0AAAAAoXyz_12345", "wbraid:CkEKCQjw1234567", long_ok)):
        p = add(d, enquiry_id=f"G{i}", gclid=ok)
        assert p.returncode == 0, (ok, p.stderr)
    assert enquiries(d)["G3"]["gclid"] == long_ok
    for bad in ("abc123", "gclid=Cj0KCQjw_abc", "Cj0KCQ jw_abc123", "fbraid:Cj0KCQjw_abc", "a" * 201):
        p = add(d, enquiry_id="BAD", gclid=bad)
        assert p.returncode != 0 and "gclid" in p.stderr, (bad, p.stderr)
    assert "BAD" not in enquiries(d)


def test_cli_add_reads_json_from_stdin():
    d = home()
    row = {"enquiry_id": "1001", "first_seen": "2026-09-20", "source": "email", "occasion": "wedding",
           "notes": "4 singers, bride's side, it's in Kent"}
    p = cli(d, "add", "-", stdin=json.dumps(row))
    assert p.returncode == 0, p.stderr
    assert enquiries(d)["1001"]["notes"] == "4 singers, bride's side, it's in Kent"
    p = cli(d, "add", "-", stdin="not json")
    assert p.returncode != 0


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


def test_cli_chase_timeline():
    d = home()
    add(d, first_seen="2026-09-01")
    assert cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-01").returncode == 0

    def due(day):
        p = cli(d, "followups-due", "--today", day)
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)

    assert due("2026-09-05") == []
    assert due("2026-09-06") == [{"enquiry_id": "1001", "kind": "first"}]
    assert cli(d, "followed", "1001", "1", "2026-09-06").returncode == 0
    assert due("2026-09-15") == []
    assert due("2026-09-16") == [{"enquiry_id": "1001", "kind": "second"}]
    assert cli(d, "followed", "1001", "2", "2026-09-16").returncode == 0
    assert due("2026-09-25") == []
    assert due("2026-09-26") == [{"enquiry_id": "1001", "kind": "mark_lost"}]


def test_cli_contact_refuses_an_older_message():
    d = home()
    add(d, first_seen="2026-09-01")
    cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-02")
    cli(d, "followed", "1001", "1", "2026-09-07")
    p = cli(d, "contact", "1001", "2026-09-03")  # an old message read late must not restart the chase
    assert p.returncode != 0 and "is before the last contact; nothing changed" in p.stderr, (p.stdout, p.stderr)
    r = enquiries(d)["1001"]
    assert (r["followups"], r["last_contact"]) == ("1", "2026-09-07"), r
    assert cli(d, "contact", "1001", "2026-09-07").returncode == 0  # the same day is not before


def test_cli_quoted_refuses_an_older_date_or_a_repeat():
    d = home()
    add(d, first_seen="2026-09-01")
    assert cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-02").returncode == 0
    p = cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-02")  # the same quote seen again
    assert p.returncode != 0 and "nothing changed" in p.stderr, (p.stdout, p.stderr)
    cli(d, "followed", "1001", "1", "2026-09-07")
    p = cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-02")  # a re-run after the chase
    assert p.returncode != 0 and "is before the last contact; nothing changed" in p.stderr, (p.stdout, p.stderr)
    p = cli(d, "quoted", "1001", "Small Choir", "1150", "2026-09-05")  # an older quote not seen before
    assert p.returncode != 0 and "is before the last contact; nothing changed" in p.stderr, (p.stdout, p.stderr)
    r = enquiries(d)["1001"]
    assert (r["followups"], r["last_contact"], r["notes"]) == ("1", "2026-09-07", "quoted 2026-09-02"), r
    # a genuinely new quote after the chase restarts the clock
    assert cli(d, "quoted", "1001", "Large Choir", "1900", "2026-09-10").returncode == 0
    r = enquiries(d)["1001"]
    assert (r["followups"], r["last_contact"], r["quoted_gbp"]) == ("0", "2026-09-10", "1900"), r


def test_cli_status_never_moves_a_booking_back():
    d = home()
    for booked in ("confirmed", "deposit_paid", "done"):
        eid = f"E{booked}"
        add(d, enquiry_id=eid)
        assert cli(d, "status", eid, booked, "0612").returncode == 0
        for back in ("new", "quoted"):
            p = cli(d, "status", eid, back)
            assert p.returncode != 0 and booked in p.stderr, (booked, back, p.stderr)
            assert enquiries(d)[eid]["status"] == booked
    assert cli(d, "status", "Econfirmed", "deposit_paid").returncode == 0
    assert cli(d, "status", "Edeposit_paid", "done").returncode == 0
    assert cli(d, "status", "Edone", "cancelled").returncode == 0


def test_cli_event_sets_the_event_date():
    d = home()
    add(d, event_date="", status="quoted", quoted_gbp=1150, last_contact="2026-09-01")
    p = cli(d, "event", "1001", "2026-09-27")
    assert p.returncode == 0 and p.stdout.strip() == "enquiry 1001: event 2026-09-27", (p.stdout, p.stderr)
    assert enquiries(d)["1001"]["event_date"] == "2026-09-27"
    p = cli(d, "followups-due", "--today", "2026-09-28")
    assert json.loads(p.stdout) == [{"enquiry_id": "1001", "kind": "mark_lost"}], p.stdout
    assert cli(d, "event", "1001", "27/09/2026").returncode != 0
    assert cli(d, "event", "9999", "2026-09-27").returncode != 0
    assert enquiries(d)["1001"]["event_date"] == "2026-09-27"


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
                 ["status", "9999", "lost"], ["followed", "9999", "1", "2026-09-21"], ["event", "9999", "2027-01-01"]):
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
    cols = ["notes", "booking_ref", "client_name", "event_date", "occasion", "value_gbp", "extra_col"]
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


def test_cli_reviewed_refuses_a_row_wider_than_the_header():
    d = home()
    path = write_ledger(d, [booking("2009", "2026-09-20", "paid in full 2026-09-19")])
    with open(path, "a", newline="") as f:
        f.write("1509,2026-06-01,2026-09-15,Bob,bob@example.com,Wedding,,1150,,,,,,notes,SPILL\n")
    with open(path, "rb") as f:
        before = f.read()
    p = cli(d, "reviewed", "2009", "2026-09-28")
    assert p.returncode != 0 and "nothing written" in p.stderr, (p.stdout, p.stderr)
    assert "Bob" not in p.stderr + p.stdout
    with open(path, "rb") as f:
        assert f.read() == before


def test_cli_thread_maps_a_booking_ref_to_its_enquiry():
    d = home()
    add(d, enquiry_id="T1", status="confirmed", booking_ref="2111")
    add(d, enquiry_id="T2", status="quoted", quoted_gbp=1150)
    p = cli(d, "thread", "2111")
    assert p.returncode == 0 and p.stdout.strip() == "T1", (p.stdout, p.stderr)
    p = cli(d, "thread", "9999")
    assert p.returncode == 0 and p.stdout.strip() == "no thread", (p.stdout, p.stderr)


def test_cli_thread_with_no_file_says_no_thread():
    d = home()
    p = cli(d, "thread", "2111")
    assert p.returncode == 0 and p.stdout.strip() == "no thread", (p.stdout, p.stderr)


def test_cli_review_skipped_stops_reviews_due_listing_it():
    d = home()
    path = write_ledger(d, [booking("2009", "2026-09-20", "paid in full 2026-09-19")])
    assert json.loads(cli(d, "reviews-due", "--today", "2026-09-28").stdout) != []
    p = cli(d, "review-skipped", "2009", "planner")
    assert p.returncode == 0 and "review request skipped" in p.stdout, (p.stdout, p.stderr)
    with open(path, newline="") as f:
        notes = next(csv.DictReader(f))["notes"]
    assert notes.startswith("paid in full 2026-09-19; review request skipped ") and notes.endswith("(planner)"), notes
    assert json.loads(cli(d, "reviews-due", "--today", "2026-09-28").stdout) == []
    assert mode(path) == 0o600
    p = cli(d, "review-skipped", "2009", "planner")
    assert p.returncode != 0 and "already" in p.stderr, p.stderr
    p = cli(d, "reviewed", "2009", "2026-09-28")
    assert p.returncode != 0 and "already" in p.stderr, "no review request after a skip"


def test_cli_review_skipped_takes_one_plain_word():
    d = home()
    write_ledger(d, [booking("2009", "2026-09-20", "paid in full 2026-09-19")])
    for bad in ("Ann Smith", "a;b", "", "x" * 30):
        assert cli(d, "review-skipped", "2009", bad).returncode != 0, bad
    assert cli(d, "review-skipped", "9999", "unresolved").returncode != 0


def test_cli_done_due():
    d = home()
    for eid, status, ref in (("A", "confirmed", "0901"), ("B", "deposit_paid", "0902"), ("C", "confirmed", "1010"),
                             ("D", "done", "0903"), ("E", "quoted", ""), ("F", "confirmed", "0904"),
                             ("G", "deposit_paid", "0928"), ("H", "confirmed", "0905")):
        add(d, enquiry_id=eid, occasion="funeral" if eid == "A" else "wedding")
        if ref:
            assert cli(d, "status", eid, status, ref).returncode == 0
        else:
            cli(d, "quoted", eid, "Small Choir", "1150", "2026-09-21")
    write_ledger(d, [
        booking("0901", "2026-09-01", "paid in full 2026-08-30", occasion="Funeral"),  # A: due, funeral too
        booking("0902", "2026-09-02", "deposit seen 2026-08-01 (Starling)"),           # B: not paid in full
        booking("1010", "2026-10-10", "paid in full 2026-09-20"),                      # C: event to come
        booking("0903", "2026-09-03", "paid in full 2026-09-01"),                      # D: already done
        booking("0904", "2026-09-04", "paid in full 2026-09-01; cancelled 2026-09-02"),  # F: cancelled
        booking("0928", "2026-09-28", "paid in full 2026-09-20"),                      # G: event today
        booking("0905", "2026-09-05", "paid in full 2026-09-01"),                      # H: due
    ])
    p = cli(d, "done-due", "--today", "2026-09-28")
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout) == [{"enquiry_id": "A", "booking_ref": "0901"},
                                    {"enquiry_id": "H", "booking_ref": "0905"}], p.stdout
    assert "Ann" not in p.stdout
    p = cli(home(), "done-due", "--today", "2026-09-28")
    assert p.returncode == 0 and json.loads(p.stdout) == [], (p.stdout, p.stderr)


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


def test_quoted_and_followed_read_the_status_whatever_its_case():
    d = tempfile.mkdtemp()
    rows = [enq("q1", status="Quoted ", last="2026-09-20"), enq("c1", status="CONFIRMED", booking_ref="2111")]
    with open(os.path.join(d, "enquiries.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pl.COLUMNS)
        w.writeheader()
        w.writerows(rows)
    p = cli(d, "followed", "q1", "1", "2026-09-25")
    assert p.returncode == 0, p.stderr
    p = cli(d, "quoted", "c1", "Small Choir", "1150", "2026-09-26")
    assert p.returncode != 0 and "is confirmed; not re-quoted" in p.stderr, p.stderr
    assert enquiries(d)["c1"]["status"] == "CONFIRMED"


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
