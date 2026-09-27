#!/usr/bin/env python3
"""Tests for validate_house_claims.py. Stdlib only — run with: python3 tests/test_house_claims.py"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_on(html, path="index.html"):
    """Drop `html` into a temp repo at `path`, run the validator, return (exit, output)."""
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.dirname(os.path.join(tmp, path)), exist_ok=True)
        with open(os.path.join(tmp, path), "w", encoding="utf-8") as f:
            f.write(html)
        shutil.copy(os.path.join(ROOT, "validate_house_claims.py"), tmp)
        p = subprocess.run([sys.executable, "validate_house_claims.py"],
                           cwd=tmp, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr
    finally:
        shutil.rmtree(tmp)


# ── each banned claim must fail the build ────────────────────────────────────

def test_roster_over_150_fails():
    code, out = run_on("<p>We draw on a roster of more than 150 singers and musicians.</p>")
    assert code == 1, out
    assert "roster-scale claim" in out, out

def test_over_150_auditioned_fails():
    code, out = run_on("<p>Over 150 auditioned musicians, hand-picked.</p>")
    assert code == 1, out

def test_150_plus_fails():
    code, out = run_on("<p>Our roster of 150-plus professional singers.</p>")
    assert code == 1, out

def test_roster_of_number_fails():
    code, out = run_on("<p>From our roster of 150 singers.</p>")
    assert code == 1, out

def test_vat_registered_fails():
    code, out = run_on("<p>The legal entity is Alma Consort Ltd. We are VAT-registered.</p>")
    assert code == 1, out
    assert "VAT-registration claim" in out, out

def test_vat_registered_appositive_fails():
    code, out = run_on("<p>run as Alma Consort Ltd, VAT-registered, with cover.</p>")
    assert code == 1, out

def test_five_star_fails():
    code, out = run_on("<p>Five-star rated by the families we have worked with.</p>")
    assert code == 1, out
    assert "rating claim" in out, out

def test_review_schema_fails():
    code, out = run_on('<script type="application/ld+json">{"@type": "Review"}</script>')
    assert code == 1, out

def test_aggregate_rating_fails():
    code, out = run_on('<script type="application/ld+json">{"AggregateRating": 5}</script>')
    assert code == 1, out


def test_supplement_choir_on_london_page_fails():
    code, out = run_on("<p>We can provide additional voices to supplement its own choir.</p>",
                       path="areas/london/southwark.html")
    assert code == 1, out
    assert "London cathedral-choir supplement claim" in out, out

def test_supplement_it_with_voices_near_london_cathedral_fails():
    code, out = run_on("<p>Southwark Cathedral has its own choir, and we supplement it with additional voices.</p>")
    assert code == 1, out

def test_alongside_abbey_foundation_fails():
    code, out = run_on("<p>At Westminster Abbey our singers work alongside the abbey&rsquo;s own choral foundation.</p>")
    assert code == 1, out

def test_supplement_st_pauls_choir_fails():
    code, out = run_on("<p>At St&nbsp;Paul&rsquo;s Cathedral we can supplement the cathedral choir.</p>")
    assert code == 1, out


# ── legitimate copy must NOT fail ────────────────────────────────────────────

def test_travel_supplement_passes():
    code, out = run_on("<p>A travel supplement may apply for a choir of eight outside London.</p>")
    assert code == 0, out

def test_supplement_outside_london_passes():
    """Outside London we may join a cathedral choir with the church's permission (owner, 2026-09-27)."""
    code, out = run_on("<p>With the cathedral&rsquo;s permission, we can sing alongside the cathedral&rsquo;s own choir.</p>",
                       path="areas/oxford.html")
    assert code == 0, out

def test_sing_with_permission_passes():
    code, out = run_on("<p>The Abbey has its own choir, and we sing there only with the Abbey&rsquo;s permission, as a separate ensemble.</p>")
    assert code == 0, out

def test_not_vat_registered_passes():
    """The true statement must not trip the VAT pattern."""
    code, out = run_on("<p>We are not VAT-registered, so no VAT is added to the invoice.</p>")
    assert code == 0, out

def test_room_capacity_passes():
    """carol-singers.html legitimately says a room holds up to 150 guests."""
    code, out = run_on("<p>Four singers suit a lobby or a room of up to 150 guests.</p>")
    assert code == 0, out

def test_css_values_pass():
    """z-index: 150 and 150ms transitions must not trip the roster pattern."""
    code, out = run_on("<style>.x{z-index:150;transition:150ms ease}</style><p>&pound;1,150</p>")
    assert code == 0, out

def test_hand_picked_copy_passes():
    code, out = run_on("<p>A small, hand-picked team chosen by an Oxford-trained Artistic Director.</p>")
    assert code == 0, out

def test_not_a_roster_passes():
    """for-funeral-directors.html deliberately says 'one person, not a roster'."""
    code, out = run_on("<p>The family deals with one person, not a roster.</p>")
    assert code == 0, out


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
