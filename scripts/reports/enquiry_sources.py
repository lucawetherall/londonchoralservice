#!/usr/bin/env python3
"""Which Google Ads campaign, if any, each enquiry came from, graded by how sure we can be.

Google Ads conversions can't measure this business: most visitors refuse cookies, and Google's modelling never
starts at this volume. So the Monday report (weekly_review.py: section 9b, the cost per booking in section 11, the
spend guard and the Christmas value check in section 12) grades the private enquiry pipeline,
~/lcs-private/enquiries.csv (pipeline.py's columns: no names or emails), instead:

  A  a click reference: the gclid column (a gclid, gbraid:<id> or wbraid:<id>, or the gclid lookup_ref.py gave
     for a "Ref: XXXX" line), or a "ref: XXXX" / "ad ref: <id>" note
  B  an ad visit, "ad visit: <page>" or "ad visit: <page> (<utm_campaign>)" in the notes (the visitor landed from
     an ad click with cookies refused), or the client's own answer "heard: A Google ad" (or "A Google ad (marked
     Sponsored)")
  C  none of those, but the campaign matching the occasion had an ad click the same day or the day before.
     Shown for information; it never decides anything
  -  not from an ad, as far as anyone can tell (or the client named another source)

The campaign: for A, the click's own campaign (click_view, through the caller's resolver), else what B would give;
for B, the utm_campaign suffix (funeral-expert, wedding-leads, christmas-carol-singers-2026), which outranks the
page, else the page (weddings, funerals, the Christmas pages); any other page names no campaign. The occasion is
used only to pick C's campaign. A or B without a campaign is still an ad enquiry, counted apart as "no campaign".

Read-only: it reads the CSV (and, from the command line, the gclid cache) and never writes, calls a network or
prints a note's free text: only the parsed page, campaign slug and the form's fixed "How did you hear of us?"
answers. Stdlib only.

    .venv/bin/python scripts/reports/enquiry_sources.py [--days 7] [--today YYYY-MM-DD]
        this week's enquiries, graded A or B (C needs the day's ad clicks, so only the Monday report shows it)
"""

import argparse
import csv
import datetime
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

PRIVATE = Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private"))
ENQUIRIES = PRIVATE / "enquiries.csv"
GCLID_CACHE = PRIVATE / "gclid-campaigns.json"  # economics.attribute's cache: gclid -> campaign name

# key -> (Google Ads campaign id, the utm_campaign of its final URL suffix, the label the report prints)
CAMPAIGNS = {
    "funeral": ("23735776277", "funeral-expert", "funeral expert campaign"),
    "wedding": ("23739971001", "wedding-leads", "wedding-leads"),
    "christmas": ("24295921372", "christmas-carol-singers-2026", "Christmas carol singers – events 2026"),
}
ORDER = ("funeral", "wedding", "christmas")
# The page an ad click landed on (partials/analytics.html's lcsAdVisitSlug) -> campaign. Any other page (pricing,
# home, contact, a guide) names none: sitelinks can land there from any campaign.
PAGE_CAMPAIGN = {"weddings": "wedding", "funerals": "funeral", "carol-singers": "christmas",
                 "christmas": "christmas", "christmas-pricing": "christmas", "christmas-carol-services": "christmas"}
# C only: the occasion picks the campaign whose clicks are looked at.
OCCASION_CAMPAIGN = {"wedding": "wedding", "funeral": "funeral", "christmas": "christmas", "corporate": "christmas"}
# The contact form's "How did you hear of us?" options: the only answers ever printed (anything else is "other").
HEARD_ANSWERS = ("Searching on Google", "A Google ad", "A Google ad (marked Sponsored)", "Recommended by someone",
                 "A funeral director", "A wedding planner or venue", "A directory or listings site", "Other")
GRADES = ("A", "B", "C")

AD_VISIT = re.compile(r"\bad visit:\s*([a-z0-9-]+(?:/[a-z0-9-]+)*)(?:\s*\(\s*([A-Za-z0-9_.-]{1,80})\s*\))?", re.I)
HEARD = re.compile(r"\bheard:\s*([^;]+)", re.I)
# "Ad ref: <click id>" (messages before 29 Sep 2026) or the site's four-character "Ref: K7P2" (lookup_ref.py's
# alphabet: a booking ref, DDMM, always holds a 0 or 1, so it never matches)
REF_NOTE = re.compile(r"\b(?i:ad ref):\s*[A-Za-z0-9_:-]{10,}|\b(?i:ref):\s*[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{4}\b")
MEASURED = re.compile(r"\bad measurement:\s*yes\b", re.I)


def to_date(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    s = str(value or "").strip()[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def campaign_key(name=None, cid=None):
    """'funeral', 'wedding' or 'christmas' for a Google Ads campaign (its id first, then its utm_campaign slug or its
    name), or None."""
    cid = str(cid or "").strip()
    for key, (kid, slug, _label) in CAMPAIGNS.items():
        if cid and cid == kid:
            return key
    n = str(name or "").strip().lower()
    if not n:
        return None
    for key, (_kid, slug, label) in CAMPAIGNS.items():
        if n in (slug, label.lower()):
            return key
    if "funeral" in n:
        return "funeral"
    if "wedding" in n:
        return "wedding"
    if "christmas" in n or "carol" in n:
        return "christmas"
    return None


def label(key):
    return CAMPAIGNS[key][2] if key in CAMPAIGNS else "no campaign"


def heard_answer(notes):
    """The form's "How did you hear of us?" answer from the notes, as one of HEARD_ANSWERS ("Other" for anything
    else), or None."""
    m = HEARD.search(notes or "")
    if not m:
        return None
    given = re.sub(r"\s+", " ", m.group(1)).strip().lower()
    for a in HEARD_ANSWERS:
        if given == a.lower():
            return a
    return "A Google ad" if given.startswith("a google ad") else "Other"


def ad_visit(notes):
    """(page, utm_campaign or None) from an "ad visit: <page>[ (<campaign>)]" note, or (None, None)."""
    m = AD_VISIT.search(notes or "")
    if not m:
        return None, None
    return m.group(1).lower(), (m.group(2).lower() if m.group(2) else None)


def grade(row, campaign_of=None, clicks=None):
    """One enquiry row -> {first_seen, occasion, source, grade, campaign, how, heard, measured}.
    campaign_of(gclid, first_seen) -> a campaign name or None (click_view; None or missing: not resolved).
    clicks: a set of (date, campaign key) that had an ad click, or None when the clicks aren't known (no C then)."""
    notes = row.get("notes") or ""
    first = to_date(row.get("first_seen"))
    occasion = (row.get("occasion") or "").strip().lower()
    gclid = (row.get("gclid") or "").strip()
    page, suffix = ad_visit(notes)
    heard = heard_answer(notes)
    out = {"first_seen": first, "occasion": occasion or "?", "source": (row.get("source") or "").strip() or "?",
           "booking_ref": (row.get("booking_ref") or "").strip(), "grade": "-", "campaign": None, "how": "",
           "heard": heard, "measured": bool(MEASURED.search(notes))}
    # B's campaign: the utm_campaign suffix outranks the page; an unknown suffix leaves it to the page.
    b_key = campaign_key(suffix) if suffix else None
    b_from = f"campaign {suffix}" if b_key else None
    if not b_key and page:
        b_key = PAGE_CAMPAIGN.get(page)
        b_from = f"page {page}" if b_key else None
    visit = f"ad visit: {page}" + (f" ({suffix})" if suffix else "") if page else None
    if gclid or REF_NOTE.search(notes):
        key = None
        if gclid and campaign_of is not None:
            key = campaign_key(campaign_of(gclid, first))
        kind = ("gbraid" if gclid.startswith("gbraid:") else "wbraid" if gclid.startswith("wbraid:")
                else "gclid" if gclid else "ref note")
        how = f"click reference ({kind}"
        if key:
            how += ", its click's campaign)"
        elif b_key:
            key, how = b_key, how + f", campaign from the {b_from})"
        else:
            how += ", campaign not found)"
        out.update(grade="A", campaign=key, how=how)
        return out
    if visit:
        out.update(grade="B", campaign=b_key, how=visit + ("" if b_key else ", names no campaign"))
        return out
    if heard and heard.startswith("A Google ad"):
        out.update(grade="B", campaign=None, how=f"client says: {heard}, names no campaign")
        return out
    if heard and heard != "Searching on Google":  # people often take an ad for a search result: that one keeps C
        out["how"] = f"client says: {heard}"
        return out
    key = OCCASION_CAMPAIGN.get(occasion)
    if key and first and clicks is not None and \
            ((first, key) in clicks or (first - datetime.timedelta(days=1), key) in clicks):
        out.update(grade="C", campaign=key,
                   how=f"only a {label(key)} ad click that day or the day before, cookies declined?; never counts")
        return out
    out["how"] = ("no click reference, ad visit or Google-ad answer" if clicks is not None
                  else "no click reference, ad visit or Google-ad answer; ad clicks not checked")
    return out


def grade_rows(rows, campaign_of=None, clicks=None):
    """grade() for every row with a readable first_seen, oldest first."""
    graded = [grade(r, campaign_of, clicks) for r in rows]
    return sorted((g for g in graded if g["first_seen"]), key=lambda g: g["first_seen"])


def within(graded, start, end):
    return [g for g in graded if start <= g["first_seen"] <= end]


def counts(graded, start, end):
    """{campaign key or None: {"A": n, "B": n, "C": n}} for enquiries first seen from start to end (inclusive).
    Every campaign key is present; None holds the A and B enquiries that name no campaign."""
    out = {k: dict.fromkeys(GRADES, 0) for k in (*ORDER, None)}
    for g in within(graded, start, end):
        if g["grade"] in GRADES:
            out.setdefault(g["campaign"], dict.fromkeys(GRADES, 0))[g["grade"]] += 1
    return out


def ab(c):
    return c["A"] + c["B"]


def abc(c):
    return f"A {c['A']} · B {c['B']} · C {c['C']}"


def line(g):
    """One enquiry as the report prints it: date, occasion, source, grade and campaign, and why. No free text."""
    if g["grade"] in GRADES:
        verdict = f"{g['grade']} {label(g['campaign'])}"
    else:
        verdict = "not from an ad"
    extra = (f" · heard: {g['heard']}" if g["heard"] and g["heard"] not in g["how"] else "") \
        + (" · ad measurement: yes" if g["measured"] else "")
    return f"{g['first_seen']} · {g['occasion']} · {g['source']} · {verdict} ({g['how']}){extra}"


def counts_lines(c, labels=None):
    """'<campaign>: A n · B n · C n' per campaign, then the ad enquiries that name no campaign."""
    labels = labels or {}
    out = [f"{labels.get(k) or label(k)}: {abc(c[k])}" for k in ORDER]
    out.append(f"no campaign named: A {c[None]['A']} · B {c[None]['B']}")
    return out


def read_rows(path=None):
    """The pipeline rows, or None when there is no pipeline sheet. Read-only."""
    path = Path(path or ENQUIRIES)
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cached_campaign_of(path=None):
    """campaign_of() from the gclid cache economics.attribute keeps, read-only (a bad or missing file: nothing)."""
    try:
        with open(path or GCLID_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    if not isinstance(cache, dict):
        cache = {}
    return lambda gclid, _day: cache.get(gclid) if isinstance(cache.get(gclid), str) else None


def main(argv=None):
    p = argparse.ArgumentParser(description="Grade the pipeline's enquiries by ad source (read-only).")
    p.add_argument("--days", type=int, default=7, help="look back this many days (default 7)")
    p.add_argument("--today", type=datetime.date.fromisoformat, default=None)
    args = p.parse_args(argv)
    today = args.today or datetime.date.today()
    rows = read_rows()
    if rows is None:
        print(f"no pipeline sheet at {ENQUIRIES}")
        return 1
    graded = grade_rows(rows, cached_campaign_of(), clicks=None)
    start = today - datetime.timedelta(days=args.days)
    shown = within(graded, start, today)
    print(f"enquiries {start} to {today} (C needs the day's ad clicks: see the Monday report's section 9b)")
    for g in shown:
        print("   " + line(g))
    if not shown:
        print("   (none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
