#!/usr/bin/env python3
"""Tests for scripts/reports/enquiry_sources.py: grading the pipeline's enquiries A/B/C by Google Ads campaign.
Stdlib only, synthetic rows in a temp private dir, no network. .venv/bin/python tests/test_enquiry_sources.py"""
import contextlib, csv, datetime, io, json, os, re, stat, sys, tempfile

TMP = tempfile.mkdtemp(prefix="lcs-enq-test-")
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import enquiry_sources as es  # noqa: E402

D = datetime.date
DAY = D(2026, 10, 22)
COLUMNS = ["enquiry_id", "first_seen", "source", "occasion", "event_date", "package", "quoted_gbp", "status",
           "last_contact", "booking_ref", "gclid", "followups", "notes"]


def row(occasion="christmas", notes="", gclid="", first_seen=DAY, source="web form", booking_ref=""):
    r = dict.fromkeys(COLUMNS, "")
    r.update(enquiry_id="t1", first_seen=str(first_seen), source=source, occasion=occasion, notes=notes,
             gclid=gclid, booking_ref=booking_ref, status="new")
    return r


def resolver(found):
    """campaign_of(gclid, day) from {gclid: campaign name}; records each call."""
    calls = []

    def campaign_of(gclid, day):
        calls.append((gclid, day))
        return found.get(gclid)
    campaign_of.calls = calls
    return campaign_of


# ---------- A ----------

def test_a_gclid_takes_its_clicks_campaign():
    g = es.grade(row("wedding", gclid="Cj0KCQjwTestClickId123"), resolver({"Cj0KCQjwTestClickId123": "wedding-leads"}))
    assert (g["grade"], g["campaign"]) == ("A", "wedding"), g
    assert "its click's campaign" in g["how"], g


def test_a_gbraid_with_an_ad_visit_takes_the_pages_campaign():
    g = es.grade(row("funeral", gclid="gbraid:0AAAAATestBraid", notes="ad visit: funerals"), resolver({}))
    assert (g["grade"], g["campaign"]) == ("A", "funeral"), g
    assert "gbraid" in g["how"] and "page funerals" in g["how"], g


def test_a_without_a_campaign_is_still_an_ad_enquiry():
    g = es.grade(row("christmas", gclid="wbraid:0BBBBTestBraid"), resolver({}))
    assert (g["grade"], g["campaign"]) == ("A", None), g
    assert "campaign not found" in g["how"]


def test_a_short_ref_note_counts_but_a_booking_ref_never_does():
    assert es.grade(row("christmas", notes="Ref: K7P2"))["grade"] == "A"
    assert es.grade(row("christmas", notes="Ad ref: Cj0KCQjwTestClickId123"))["grade"] == "A"
    assert es.grade(row("christmas", notes="booking ref: 2111; quoted 2026-10-23"))["grade"] == "-"


def test_a_resolver_naming_an_unknown_campaign_falls_back_to_the_ad_visit():
    g = es.grade(row("wedding", gclid="Cj0KCQjwTestClickId999", notes="ad visit: weddings"),
                 resolver({"Cj0KCQjwTestClickId999": "Brand test"}))
    assert (g["grade"], g["campaign"]) == ("A", "wedding"), g


# ---------- B ----------

def test_b_ad_visit_page_names_the_campaign():
    for page, key in (("weddings", "wedding"), ("funerals", "funeral"), ("carol-singers", "christmas"),
                      ("christmas", "christmas"), ("christmas-pricing", "christmas"),
                      ("christmas-carol-services", "christmas")):
        g = es.grade(row("other", notes=f"ad visit: {page}"))
        assert (g["grade"], g["campaign"]) == ("B", key), (page, g)


def test_b_campaign_suffix_outranks_the_page():
    g = es.grade(row("wedding", notes="ad visit: weddings (christmas-carol-singers-2026)"))
    assert (g["grade"], g["campaign"]) == ("B", "christmas"), g
    g = es.grade(row("christmas", notes="Ad visit: pricing (funeral-expert); ad measurement: yes"))
    assert (g["grade"], g["campaign"], g["measured"]) == ("B", "funeral", True), g
    g = es.grade(row("wedding", notes="ad visit: home (wedding-leads)"))
    assert (g["grade"], g["campaign"]) == ("B", "wedding"), g


def test_b_unknown_suffix_leaves_it_to_the_page():
    g = es.grade(row("wedding", notes="ad visit: weddings (spring-test-2027)"))
    assert (g["grade"], g["campaign"]) == ("B", "wedding"), g


def test_b_pricing_page_without_a_suffix_names_no_campaign():
    for page in ("pricing", "home", "contact", "areas/london/camden"):
        g = es.grade(row("christmas", notes=f"ad visit: {page}"), clicks={(DAY, "christmas")})
        assert (g["grade"], g["campaign"]) == ("B", None), (page, g)
        assert "names no campaign" in g["how"]


def test_b_client_says_a_google_ad():
    for answer in ("A Google ad", "A Google ad (marked Sponsored)"):
        g = es.grade(row("wedding", notes=f"heard: {answer}; Catholic Mass"))
        assert (g["grade"], g["campaign"]) == ("B", None), (answer, g)
        assert "client says: A Google ad" in g["how"]


def test_an_ad_visit_outranks_the_clients_answer():
    g = es.grade(row("wedding", notes="heard: Recommended by someone; ad visit: weddings"))
    assert (g["grade"], g["campaign"]) == ("B", "wedding"), g


# ---------- C and not from an ad ----------

def test_c_only_a_matching_click_the_same_day_or_the_day_before():
    r = row("christmas", notes="heard: Searching on Google")
    for day in (DAY, DAY - datetime.timedelta(days=1)):
        g = es.grade(r, clicks={(day, "christmas")})
        assert (g["grade"], g["campaign"]) == ("C", "christmas"), (day, g)
        assert "never counts" in g["how"]
    assert es.grade(r, clicks={(DAY - datetime.timedelta(days=2), "christmas")})["grade"] == "-"
    assert es.grade(r, clicks={(DAY, "wedding")})["grade"] == "-"
    g = es.grade(r, clicks=None)
    assert g["grade"] == "-" and "ad clicks not checked" in g["how"], g


def test_c_corporate_matches_christmas_and_the_occasion_never_makes_a_or_b():
    g = es.grade(row("corporate"), clicks={(DAY, "christmas")})
    assert (g["grade"], g["campaign"]) == ("C", "christmas"), g
    assert es.grade(row("private event"), clicks={(DAY, "christmas")})["grade"] == "-"


def test_another_answer_means_not_from_an_ad():
    g = es.grade(row("funeral", notes="heard: A funeral director"), clicks={(DAY, "funeral")})
    assert (g["grade"], g["how"]) == ("-", "client says: A funeral director"), g
    g = es.grade(row("funeral", notes="heard: my neighbour Mrs Example"), clicks={(DAY, "funeral")})
    assert (g["grade"], g["heard"]) == ("-", "Other"), g


# ---------- counts, lines, privacy ----------

def test_counts_per_campaign_in_the_window():
    rows = [row("wedding", notes="ad visit: weddings", first_seen=D(2026, 10, 1)),
            row("wedding", notes="ad visit: weddings", first_seen=D(2026, 10, 20)),
            row("christmas", gclid="Cj0KCQjwTestClickId123", first_seen=D(2026, 10, 21)),
            row("christmas", first_seen=D(2026, 10, 22)),
            row("christmas", notes="ad visit: pricing", first_seen=D(2026, 10, 22)),
            row("funeral", notes="heard: A wedding planner or venue", first_seen=D(2026, 10, 22)),
            row("wedding", first_seen="not a date")]
    graded = es.grade_rows(rows, resolver({"Cj0KCQjwTestClickId123": "Christmas carol singers – events 2026"}),
                           clicks={(D(2026, 10, 22), "christmas")})
    assert len(graded) == 6 and graded[0]["first_seen"] == D(2026, 10, 1)
    c = es.counts(graded, D(2026, 10, 5), D(2026, 10, 26))
    assert c["wedding"] == {"A": 0, "B": 1, "C": 0}, c
    assert c["christmas"] == {"A": 1, "B": 0, "C": 1}, c
    assert c["funeral"] == {"A": 0, "B": 0, "C": 0} and c[None] == {"A": 0, "B": 1, "C": 0}, c
    assert es.ab(c["christmas"]) == 1
    lines = es.counts_lines(c)
    assert lines[2] == "Christmas carol singers – events 2026: A 1 · B 0 · C 1", lines
    assert lines[-1] == "no campaign named: A 0 · B 1", lines


def test_lines_carry_no_free_text_from_the_notes():
    secret = "6 singers at The Example Hall, Somewhere Lane; mics asked"
    g = es.grade(row("christmas", notes=f"{secret}; heard: Searching on Google; quoted 2026-10-23"),
                 clicks={(DAY, "christmas")})
    text = es.line(g)
    assert text == ("2026-10-22 · christmas · web form · C Christmas carol singers – events 2026 (only a Christmas "
                    "carol singers – events 2026 ad click that day or the day before, cookies declined?; never "
                    "counts) · heard: Searching on Google"), text
    for word in ("Example", "Somewhere", "mics", "quoted"):
        assert word not in text
    g = es.grade(row("wedding", notes="heard: Recommended by someone"))
    assert es.line(g).endswith("· not from an ad (client says: Recommended by someone)"), es.line(g)
    g = es.grade(row("wedding", notes="ad visit: weddings (wedding-leads); ad measurement: yes"))
    assert es.line(g) == ("2026-10-22 · wedding · web form · B wedding-leads (ad visit: weddings (wedding-leads))"
                          " · ad measurement: yes"), es.line(g)


def test_line_never_says_a_problem_word():
    """The --quiet summary lists lines with these words as problems; a graded enquiry is never one."""
    problem = re.compile(r"\b(error|failed|refused|denied|permission|STOP GUARD|STALE)\b", re.I)
    for r, clicks in ((row("christmas"), None), (row("christmas"), {(DAY, "christmas")}),
                      (row("wedding", notes="ad visit: pricing"), None), (row("funeral", gclid="gbraid:0AAAATest"), None)):
        assert not problem.search(es.line(es.grade(r, None, clicks))), es.line(es.grade(r, None, clicks))


def test_campaign_key_by_id_slug_and_name():
    assert es.campaign_key("anything", 24295921372) == "christmas"
    assert es.campaign_key(None, "23739971001") == "wedding"
    assert es.campaign_key("funeral-expert") == "funeral"
    assert es.campaign_key("christmas-carol-singers-2026") == "christmas"
    assert es.campaign_key("Christmas carol singers – events 2026") == "christmas"
    assert es.campaign_key("funeral expert campaign") == "funeral"
    assert es.campaign_key("Brand test") is None and es.campaign_key("") is None and es.campaign_key(None) is None


# ---------- read-only ----------

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    os.chmod(path, 0o600)


def snapshot(d):
    return sorted((n, os.stat(os.path.join(d, n)).st_mtime_ns, stat.S_IMODE(os.stat(os.path.join(d, n)).st_mode))
                  for n in os.listdir(d))


def test_reading_writes_nothing_and_a_corrupt_cache_is_left_alone():
    d = tempfile.mkdtemp(dir=TMP)
    path = os.path.join(d, "enquiries.csv")
    write_csv(path, [row("wedding", notes="ad visit: weddings"), row("christmas", gclid="Cj0KCQjwTestClickId123")])
    cache = os.path.join(d, "gclid-campaigns.json")
    with open(cache, "w") as f:
        f.write("{not json")
    before = snapshot(d)
    rows = es.read_rows(path)
    graded = es.grade_rows(rows, es.cached_campaign_of(cache))
    assert [g["grade"] for g in graded] == ["B", "A"], graded
    assert snapshot(d) == before, "enquiry_sources must never write, move or chmod anything"
    with open(cache, "w") as f:
        json.dump({"Cj0KCQjwTestClickId123": "wedding-leads", "x@2026-10-01/30": None}, f)
    assert es.cached_campaign_of(cache)("Cj0KCQjwTestClickId123", DAY) == "wedding-leads"
    assert es.cached_campaign_of(cache)("x@2026-10-01/30", DAY) is None
    assert es.read_rows(os.path.join(d, "missing.csv")) is None


def test_the_command_prints_the_weeks_lines():
    write_csv(es.ENQUIRIES, [row("wedding", notes="ad visit: weddings; Some Venue", first_seen=D(2026, 10, 20)),
                             row("funeral", first_seen=D(2026, 9, 1))])
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert es.main(["--today", "2026-10-26"]) == 0
    text = out.getvalue()
    assert "2026-10-20 · wedding · web form · B wedding-leads (ad visit: weddings)" in text, text
    assert "2026-09-01" not in text and "Venue" not in text, text
    os.remove(es.ENQUIRIES)
    with contextlib.redirect_stdout(io.StringIO()):
        assert es.main(["--today", "2026-10-26"]) == 1


def test_the_ads_agent_reads_the_generated_settings_not_a_hand_written_baseline():
    """Since 26 Oct 2026 the agent takes the account's settings from section 1b (generated, with a diff) and no
    longer carries a hand-written baseline that goes stale."""
    body = open(os.path.join(ROOT, ".claude", "agents", "lcs-review-ads.md"), encoding="utf-8").read()
    assert "THE ACCOUNT AS THE OWNER SET IT" not in body
    assert re.search(r"report_sections\.py 1 1b ", body), "the agent's command must read section 1b"
    assert "£80+ in 28 days with no A or B enquiry" in body
    assert "no Ads conversion and no A or B enquiry" not in body


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
