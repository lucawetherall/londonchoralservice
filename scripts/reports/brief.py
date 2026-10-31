#!/usr/bin/env python3
"""Section 0 of the Monday report, "This week in brief": pure functions, no file or network access.

weekly_review.py reads the pipeline sheet and the ledger, gathers the figures sections 5c, 6 and 11 hand back,
and passes them here. Each line gives the last full Monday–Sunday week, the week before and the average of the
last 8 full weeks (economics.full_weeks). Counts and totals only: never a name, email or note.
"""

import datetime
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import economics as ec  # noqa: E402  week_activity: one rule for the weekly enquiry and booking counts
import pipeline  # noqa: E402  QUOTED_NOTE: the "quoted YYYY-MM-DD" note pipeline.py quoted writes

MAX_ALARMS = 12


def _date(value):
    try:
        return datetime.date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


def _monday(d):
    return d - datetime.timedelta(days=d.weekday())


def collect(enquiry_rows, ledger_rows, weeks):
    """The pipeline and ledger half of section 0 for `weeks` (Mondays, oldest first; the last is "this week").
    enquiry_rows None: no pipeline sheet."""
    act = ec.week_activity(enquiry_rows or [], ledger_rows or [], weeks)
    keys = [w.isoformat() for w in weeks]
    this = weeks[-1]
    out = {"weeks": list(weeks),
           "bookings": [(act[k]["bookings"], act[k]["booked_gbp"]) for k in keys]}
    if enquiry_rows is None:
        out["enquiries"] = out["quotes"] = None
        return out
    occasion, source = Counter(), Counter()
    quotes = dict.fromkeys(keys, 0)
    waits = []
    for r in enquiry_rows:
        seen = _date(r.get("first_seen"))
        if seen and _monday(seen) == this:
            occasion[(r.get("occasion") or "").strip().lower() or "unknown"] += 1
            source[(r.get("source") or "").strip().lower() or "unknown"] += 1
        dates = sorted(d for d in (_date(m) for m in pipeline.QUOTED_NOTE.findall(r.get("notes") or "")) if d)
        for d in dates:
            if _monday(d).isoformat() in quotes:
                quotes[_monday(d).isoformat()] += 1
        if dates and seen and _monday(dates[0]) == this and (dates[0] - seen).days >= 0:
            waits.append((dates[0] - seen).days)
    out["enquiries"] = {"by_week": [act[k]["enquiries"] for k in keys], "occasion": dict(occasion),
                        "source": dict(source)}
    out["quotes"] = {"by_week": [quotes[k] for k in keys],
                     "median_days": statistics.median(waits) if waits else None}
    return out


def _avg(values):
    return sum(values) / len(values) if values else 0.0


def _split(counts):
    return ", ".join(f"{k} {n}" for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _days(x):
    x = round(x, 1)
    text = f"{x:g}"
    return f"{text} day" + ("" if x == 1 else "s")


def lines(data):
    """Section 0's lines, heading first. data: collect()'s dict plus "ads" (economics.week_buckets for the same
    weeks, or None: section 11 failed), "pageviews" ((last 7 days, the 7 before or None), or None: 5c not read),
    "organic" ((this week, week before, first day, last day), or None: 6 not read) and "alarms" (problem lines)."""
    weeks = data["weeks"]
    w = weeks[-1]
    out = [f"== 0. This week in brief (week {w} to {w + datetime.timedelta(days=6)}; then the week before, then the "
           f"average of the last {len(weeks)} full weeks)"]
    e = data.get("enquiries")
    if e is None:
        out.append("   enquiries: no pipeline sheet yet")
    else:
        n = e["by_week"]
        line = f"   enquiries {n[-1]} · week before {n[-2]} · {len(n)}-week average {_avg(n):.1f}"
        if n[-1]:
            line += f" · this week by occasion: {_split(e['occasion'])} · by source: {_split(e['source'])}"
        out.append(line)
    qd = data.get("quotes")
    if qd is not None:
        n = qd["by_week"]
        line = f"   quotes sent {n[-1]} · week before {n[-2]} · {len(n)}-week average {_avg(n):.1f}"
        if qd["median_days"] is not None:
            line += f" · median {_days(qd['median_days'])} from first contact to quote"
        out.append(line)
    b = data["bookings"]
    counts, money = [x[0] for x in b], [x[1] for x in b]
    out.append(f"   bookings {counts[-1]} (£{money[-1]:,.0f}) · week before {counts[-2]} (£{money[-2]:,.0f})"
               f" · {len(b)}-week average {_avg(counts):.1f} (£{_avg(money):,.0f}) (by invoice date, cancelled "
               f"left out)")
    ads = data.get("ads")
    if ads:
        sp, ck = [a["spend_gbp"] for a in ads], [a["clicks"] for a in ads]
        out.append(f"   ad spend £{sp[-1]:,.2f} ({ck[-1]} clicks) · week before £{sp[-2]:,.2f} ({ck[-2]} clicks)"
                   f" · {len(ads)}-week average £{_avg(sp):,.2f} ({_avg(ck):.1f} clicks)")
    else:
        out.append("   ad spend: not read (section 11 has no figures)")
    pv = data.get("pageviews")
    if pv:
        out.append(f"   page views, every visitor (GoatCounter, the last 7 days) {pv[0]} · the 7 days before "
                   + (str(pv[1]) if pv[1] is not None else "not counted yet"))
    else:
        out.append("   page views (GoatCounter): not read (section 5c has no figures)")
    org = data.get("organic")
    if org:
        out.append(f"   organic clicks (Search Console, {org[2]} to {org[3]}) {org[0]} · week before {org[1]}")
    else:
        out.append("   organic clicks (Search Console): not read (section 6 has no figures)")
    alarms = data.get("alarms") or []
    if not alarms:
        out.append("   alarms: nothing alarming")
    else:
        out.append(f"   alarms: {len(alarms)} (the sections above give the detail)")
        out += [f"   alarm: {a}" for a in alarms[:MAX_ALARMS]]
        if len(alarms) > MAX_ALARMS:
            out.append(f"   and {len(alarms) - MAX_ALARMS} more")
    return out
