#!/usr/bin/env python3
"""Tests for scripts/reports/review_lint.py (the Monday review's reply, checked before it goes out). Stdlib only, no
network; the ledger is a temp file with made-up names. .venv/bin/python tests/test_review_lint.py"""
import csv, os, subprocess, sys, tempfile

_HOME = tempfile.mkdtemp()  # never the real ~/lcs-private
os.environ["LCS_PRIVATE_DIR"] = _HOME
os.environ.pop("LCS_BOOKINGS_CSV", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import review_lint as rl  # noqa: E402

PY, SCRIPT = sys.executable, os.path.join(ROOT, "scripts", "reports", "review_lint.py")
NAMES = ["Hermione Thaddeus-Barnes", "Al B"]  # made up; the second is too short to check


def found(text, names=NAMES):
    return [(line, check) for line, check, _ in rl.lint(text, names=names)]


def checks(text, names=NAMES):
    return {check for _, check in found(text, names)}


def review(*body, question="Approve 1 and 2?"):
    return "\n".join(["# Monday review, 2 Nov", "", *body, "", question]) + "\n"


# --- prices ---------------------------------------------------------------------------------------

def test_the_26_oct_case_a_soloist_at_250_is_flagged_and_1150_passes():
    text = review("**Landing page** (funerals.html)",
                  "- Add a price line: a soloist at £250, a small choir of four at £1,150.")
    got = rl.lint(text, names=[])
    assert [(line, check) for line, check, _ in got] == [(4, "price")], got
    assert "£250" in got[0][2] and "£275" in got[0][2] and "soloist" in got[0][2], got
    assert found(review("**Landing page**", "- a soloist at £275, a small choir of four at £1,150."), []) == []


def test_prices_pass_when_they_are_on_the_pricing_pages_or_the_claude_md_combinations():
    ok = review("## Decisions",
                "1. [site] funerals.html → hero: none → \"Small Choir + organist £1,400\" — combination",
                "2. [site] weddings.html → FAQ: none → \"soloist and organist £550\" — combination",
                "3. [site] christmas.html → example: none → \"Full Choir of eight and an organist, £2,250\" — page",
                "4. [site] pricing.html → line: none → \"an organist added to a choir at £250\" — page")
    assert found(ok, []) == [], rl.lint(ok, names=[])


def test_a_price_on_no_pricing_page_is_flagged_only_in_the_checked_sections():
    bad = review("## Ad copy", "Headline 3: Funeral choir from £1,250")
    assert found(bad, []) == [(4, "price")], rl.lint(bad, names=[])
    gbp = review("### GBP posts", "Post 1: carol singers from £999 this December")
    assert found(gbp, []) == [(4, "price")]
    # spend and money lines elsewhere are not price-checked
    money = review("## Money", "Season so far: £1,234 booked, £312.50 spend.", "## Headlines", "Spend £1,999")
    assert found(money, []) == []
    # outside £250 to £10,000: never checked
    assert found(review("## Ad copy", "Budget £8 a day; £12,500 season"), []) == []


def test_a_bold_label_opens_a_checked_section_until_the_next_label_or_heading():
    text = review("**Ad copy**: Headline: choirs from £1,250", "**Watch**: £1,250 spent", "## Notes", "£1,250")
    assert found(text, []) == [(3, "price")], rl.lint(text, names=[])
    assert found(review("**GBP post 2**", "carols from £1,234"), []) == [(4, "price")]


# --- contact details and client names --------------------------------------------------------------

def test_contact_details_are_flagged_except_the_business_own():
    assert checks(review("Reply to someone@example.com today")) == {"contact"}
    assert checks(review("Ring 020 7946 0123 back")) == {"contact"}
    assert checks(review("Ring +44 7700 900123 back")) == {"contact"}
    assert checks(review("Ring 07700-900-123 back")) == {"contact"}
    assert found(review("Our number 07356 042468 and +44 7356 042468, office@londonchoralservice.com, "
                        "Luca@AlmaConsort.com")) == []
    # campaign ids and dates are not phone numbers
    assert found(review("Campaign 24295921372 on 2026-10-26, gclid 12345678901")) == []


def test_a_client_name_is_flagged_whole_and_case_insensitive_and_never_printed():
    got = rl.lint(review("Booked: hermione   thaddeus-barnes, 12 Dec"), names=NAMES)
    assert [(line, check) for line, check, _ in got] == [(3, "client name")], got
    assert "ermione" not in got[0][2].lower() and "thaddeus" not in got[0][2].lower(), got
    assert found(review("Hermione booked")) == []  # part of a name is not the name
    assert found(review("Hermione Thaddeus-Barneses")) == []  # word-bounded
    assert found(review("Al B booked")) == []  # shorter than 5 characters: skipped


# --- house rules, proposal form, targeting, length -------------------------------------------------

def test_house_rules_come_from_validate_house_claims():
    assert checks(review("We have a roster of more than 150 singers.")) == {"house rule"}
    assert checks(review("We could supplement the cathedral choir at Southwark Cathedral.")) == {"house rule"}
    # the London rule needs a London cathedral nearby, as on the site
    assert found(review("At York Minster we may supplement the minster's choir with permission.")) == []
    import validate_house_claims as vhc
    assert all(any(p is b[0] for b in vhc.BANNED) for p, _, _ in rl.HOUSE_RULES)


def test_a_decision_without_an_arrow_is_flagged():
    text = review("## Decisions", "1. [ads] Wedding campaign → budget: £3 → £4 — demand", "2. [site] tidy the FAQ",
                  "## Watch", "3. no arrow needed here")
    assert found(text) == [(5, "proposal form")], rl.lint(text, names=NAMES)


def test_a_proposed_keyword_with_a_solo_word_is_flagged_but_a_negative_is_fine():
    bad = review("## Decisions", '1. [ads] Funeral campaign → add keyword: none → "funeral singer" phrase — volume')
    assert found(bad) == [(4, "targeting")], rl.lint(bad, names=NAMES)
    for word in ("soloist", "solo", "vocalist"):
        assert checks(review("## Decisions", f'1. [ads] Weddings → add keyword: none → "wedding {word}" — x')) \
            == {"targeting"}, word
    ok = [review("## Decisions", '1. [ads] Funeral campaign → add negative keyword: none → "singer" — solo searches'),
          review("## Decisions", '1. [ads] Christmas → add keyword: none → "carol singers london" — choir searches'),
          review("## Decisions", '1. [ads] Weddings → add keyword: none → "wedding choir" — not solo singer searches')]
    for text in ok:
        assert found(text) == [], rl.lint(text, names=NAMES)


def test_more_than_900_words_before_the_final_question_is_flagged():
    long = review(*(["word " * 10] * 91))  # 910 words, plus the 5-word heading
    got = found(long)
    assert got == [(len(long.splitlines()), "length")], got
    assert found(review(*(["word " * 10] * 89))) == []
    # words after the final question do not count; with no question, every word counts
    assert found("\n".join(["Approve?"] + ["word " * 10] * 100)) == []
    assert found("\n".join(["word " * 10] * 100)) == [(100, "length")]


# --- CLI -----------------------------------------------------------------------------------------

def cli(text, names=NAMES, ledger=True):
    d = tempfile.mkdtemp()
    if ledger:
        with open(os.path.join(d, "bookings.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["booking_ref", "client_name", "client_email"])
            w.writeheader()
            for i, n in enumerate(names):
                w.writerow({"booking_ref": f"01011{i}", "client_name": n, "client_email": "x@example.com"})
    path = os.path.join(d, "review.md")
    with open(path, "w") as f:
        f.write(text)
    env = dict(os.environ, LCS_PRIVATE_DIR=d)
    env.pop("LCS_BOOKINGS_CSV", None)
    return subprocess.run([PY, SCRIPT, path], capture_output=True, text=True, env=env)


def test_cli_clean_and_findings_format():
    p = cli(review("## Decisions", "1. [ads] Weddings → budget: £3 → £4 — demand"))
    assert (p.returncode, p.stdout) == (0, "lint: clean\n"), (p.returncode, p.stdout, p.stderr)
    p = cli(review("## Decisions", "1. [site] fix the hero for hermione thaddeus-barnes", "**Landing page**",
                   "a soloist at £250, call 020 7946 0123"))
    assert p.returncode == 1, (p.stdout, p.stderr)
    lines = p.stdout.splitlines()
    assert [ln.split(":")[0:2] for ln in lines] == [["line 4", " proposal form"], ["line 4", " client name"],
                                                    ["line 6", " contact"], ["line 6", " price"]], lines
    assert "thaddeus" not in p.stdout.lower() and "7946" not in p.stdout, p.stdout


def test_cli_without_a_ledger_still_lints_and_says_names_were_not_checked():
    p = cli(review("Fine."), ledger=False)
    assert p.returncode == 0 and p.stdout == "lint: clean\n" and "client names not checked" in p.stderr, p


def test_cli_usage():
    p = subprocess.run([PY, SCRIPT], capture_output=True, text=True)
    assert p.returncode == 2 and "usage" in p.stderr, p
    p = subprocess.run([PY, SCRIPT, os.path.join(_HOME, "missing.md")], capture_output=True, text=True)
    assert p.returncode == 2, p


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
