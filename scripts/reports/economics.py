#!/usr/bin/env python3
"""Marketing economics for the Monday report (sections 11-13). Pure functions
plus two private-file helpers; weekly_review.py does every Google call.

  11. True cost per booking: Ads spend by campaign joined to the ledger's
      bookings and the pipeline's enquiries through each gclid.
  12. Seasonal budget rules: data/budget-windows.yml turned into proposals,
      never above the campaign's cap (£5/day, or a dated exception in
      scripts/ads/budget_cap.py).
  13. Search Console shortlist: hiring-intent queries at positions 8-20, each
      with one page and one suggested fix.

Nothing here talks to Google, prints names or changes anything.
"""

import datetime
import html
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import lcs_money  # noqa: E402  PRIVATE, LEDGER, read_csv, money
import check_payments  # noqa: E402  is_cancelled: one cancelled rule for the ledger
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ads"))
import budget_cap  # noqa: E402  the £5 cap and its dated exceptions

PRIVATE = lcs_money.PRIVATE
GCLID_CACHE = PRIVATE / "gclid-campaigns.json"
ADS_SUMMARY = PRIVATE / "ads-summary.json"
ENQUIRIES = PRIVATE / "enquiries.csv"
BUDGET_CAP_GBP = budget_cap.BASE_CAP_MICROS / 1_000_000
LOOKBACK_DAYS = 30      # a booking's click is looked for from its enquiry date back this many days
CLICK_VIEW_DAYS = 90    # Google keeps click_view for the last 90 days only
SETTLE_DAYS = 2         # click_view for a date is complete once it is this many days old


# ---------- private files ----------

def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json_private(path, obj):
    """Atomic write, mode 600, in a mode-700 directory."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def load_gclid_cache(path, today):
    """The gclid cache, or {} when it's missing. A corrupt file is renamed
    <name>.corrupt-<date> (never deleted) and a fresh cache is started."""
    path = Path(path)
    try:
        with open(path) as f:
            cache = json.load(f)
        if isinstance(cache, dict):
            return cache
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    aside = path.with_name(f"{path.name}.corrupt-{today.isoformat()}")
    n = 2
    while aside.exists():
        aside = path.with_name(f"{path.name}.corrupt-{today.isoformat()}-{n}")
        n += 1
    os.replace(path, aside)
    return {}


def _date(value):
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(str(value or "").strip()[:10])
    except ValueError:
        return None


# ---------- 11. true cost per booking ----------

def _miss_key(gclid, start, days):
    return f"{gclid}@{start.isoformat()}/{days}"


def attribute(gclid, enquiry_date, clicks_on, cache, today, days=LOOKBACK_DAYS):
    """Campaign name for a gclid, or None (unattributed).

    clicks_on(date) -> {gclid: campaign name} runs the click_view query for one date.
    Dates are tried from the enquiry date back `days` days, stopping at the first hit.
    A hit is cached under the gclid. A miss is cached only when the search was
    complete (the enquiry date is SETTLE_DAYS or more old, so click_view has landed),
    and under the gclid, date and span, so a corrected date searches again.
    An unparseable date returns None and caches nothing; an error propagates and
    nothing is cached."""
    gclid = (gclid or "").strip()
    if not gclid or gclid.startswith(("gbraid:", "wbraid:")):
        return None
    start = _date(enquiry_date)
    if not start:
        return None
    if cache.get(gclid):  # a bare-gclid None is from an older version: search again
        return cache[gclid]
    miss = _miss_key(gclid, start, days)
    if miss in cache:
        return None
    found = None
    oldest = today - datetime.timedelta(days=CLICK_VIEW_DAYS - 1)
    day = min(start, today)
    stop = start - datetime.timedelta(days=days)
    while day >= stop and day >= oldest:
        campaign = clicks_on(day).get(gclid)
        if campaign:
            found = campaign
            break
        day -= datetime.timedelta(days=1)
    settled = start <= today - datetime.timedelta(days=SETTLE_DAYS)
    if found:
        cache[gclid] = found
    elif settled:
        cache[miss] = None
    return found


def attribute_booking(row, clicks_on, cache, today):
    """attribute() for a ledger row. With no enquiry date, the click can be anywhere
    before the invoice, so the whole retained click_view window is searched."""
    if (row.get("enquiry_date") or "").strip():
        return attribute(row.get("gclid"), row.get("enquiry_date"), clicks_on, cache, today)
    return attribute(row.get("gclid"), row.get("invoice_date"), clicks_on, cache, today, days=CLICK_VIEW_DAYS)


def season_bookings(rows, season_start):
    """Ledger rows invoiced on or after season_start that check_payments doesn't treat as cancelled."""
    out = []
    for r in rows:
        d = _date(r.get("invoice_date"))
        if d and d >= season_start and not check_payments.is_cancelled(r):
            out.append(r)
    return out


def season_enquiries(rows, season_start):
    return [r for r in rows if (d := _date(r.get("first_seen"))) and d >= season_start]


def divide(a, b):
    return round(a / b, 2) if b else None


def gbp_or_dash(x):
    return "–" if x is None else f"£{x:,.2f}"


def _n(x):
    return "–" if x is None else str(x)


def cost_table(spend, bookings, enquiries):
    """spend: {campaign: (cost_micros, clicks)}; bookings: [(campaign or None, £ value)];
    enquiries: [campaign or None] or None when the pipeline sheet doesn't exist."""
    names = set(spend) | {c for c, _ in bookings if c} | {c for c in (enquiries or []) if c}
    have_enq = enquiries is not None
    rows = []
    for name in names:
        micros, clicks = spend.get(name, (0, 0))
        s = round(micros / 1e6, 2)
        b = [v for c, v in bookings if c == name]
        e = sum(1 for c in enquiries if c == name) if have_enq else None
        rows.append({"campaign": name, "spend_gbp": s, "clicks": clicks, "enquiries": e,
                     "bookings": len(b), "booked_gbp": round(sum(b), 2),
                     "cost_per_enquiry": divide(s, e) if have_enq else None,
                     "cost_per_booking": divide(s, len(b))})
    rows.sort(key=lambda r: (-r["spend_gbp"], r["campaign"].lower()))
    ub = [v for c, v in bookings if not c]
    un = {"enquiries": sum(1 for c in enquiries if not c) if have_enq else None,
          "bookings": len(ub), "booked_gbp": round(sum(ub), 2)}
    ts = round(sum(r["spend_gbp"] for r in rows), 2)
    te = len(enquiries) if have_enq else None
    total = {"spend_gbp": ts, "clicks": sum(r["clicks"] for r in rows), "enquiries": te,
             "bookings": len(bookings), "booked_gbp": round(sum(v for _, v in bookings), 2),
             "cost_per_enquiry": divide(ts, te) if have_enq else None,
             "cost_per_booking": divide(ts, len(bookings))}
    return {"campaigns": rows, "unattributed": un, "total": total}


def _cost_line(label, r):
    return (f"{label}: spend £{r['spend_gbp']:,.2f} · clicks {r['clicks']} · enquiries {_n(r['enquiries'])}"
            f" · bookings {r['bookings']} · booked £{r['booked_gbp']:,.2f}"
            f" · per enquiry {gbp_or_dash(r['cost_per_enquiry'])} · per booking {gbp_or_dash(r['cost_per_booking'])}")


def cost_lines(table):
    lines = [_cost_line(r["campaign"], r) for r in table["campaigns"]]
    u = table["unattributed"]
    lines.append(f"unattributed: enquiries {_n(u['enquiries'])} · bookings {u['bookings']} · booked £{u['booked_gbp']:,.2f}")
    lines.append(_cost_line("total", table["total"]))
    return lines


def full_weeks(today, n):
    """Mondays of the last n complete Monday-Sunday weeks before today."""
    last_sunday = today - datetime.timedelta(days=today.weekday() + 1)
    first = last_sunday - datetime.timedelta(days=6 + 7 * (n - 1))
    return [first + datetime.timedelta(weeks=i) for i in range(n)]


def week_buckets(daily, today, n=8):
    """daily: [(date, cost_micros, clicks, conversions)] -> one dict per full week, oldest first."""
    weeks = full_weeks(today, n)
    acc = {w: [0, 0, 0.0] for w in weeks}
    for day, micros, clicks, conv in daily:
        d = _date(day)
        if not d:
            continue
        w = d - datetime.timedelta(days=d.weekday())
        if w in acc:
            acc[w][0] += micros
            acc[w][1] += clicks
            acc[w][2] += conv
    return [{"week_start": w.isoformat(), "spend_gbp": round(acc[w][0] / 1e6, 2), "clicks": acc[w][1],
             "conversions": round(acc[w][2], 2)} for w in weeks]


def ads_summary(weeks, table, season_start, generated):
    """The shape of ~/lcs-private/ads-summary.json, read by the owner's dashboard."""
    return {"generated": generated.isoformat(timespec="seconds"), "weeks": weeks,
            "season": {"start": season_start.isoformat(), **table}}


# ---------- 12. seasonal budget rules ----------

def load_windows(path):
    """season_start is None when missing or not a real date (the caller reports a config error)."""
    import yaml

    class Loader(yaml.SafeLoader):  # dates stay strings, so "2026-13-01" is a bad value, not a crash
        pass
    Loader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))
    with open(path) as f:
        cfg = yaml.load(f, Loader=Loader) or {}
    windows = []
    for w in cfg.get("windows") or []:
        w = dict(w)
        w["campaigns"] = ["" if c is None else str(c) for c in w.get("campaigns") or []]
        w["start"], w["end"] = str(w.get("start", "")), str(w.get("end", ""))
        windows.append(w)
    return {"season_start": _date(cfg.get("season_start")), "windows": windows}


def _mmdd(s):
    m = re.fullmatch(r"(\d\d)-(\d\d)", s or "")
    if not m:
        return None
    try:
        datetime.date(2000, int(m[1]), int(m[2]))  # a leap year, so 02-29 is allowed
    except ValueError:
        return None
    return int(m[1]), int(m[2])


def in_window(day, start, end):
    s, e, d = _mmdd(start), _mmdd(end), (day.month, day.day)
    return s <= d <= e if s <= e else (d >= s or d <= e)


def proposals(campaigns, windows, today):
    """campaigns: [{name, status, budget_gbp, id (optional)}]. Returns items with kind error / propose / note.
    Only ENABLED campaigns get proposals, and no proposal is ever above the campaign's cap (budget_cap.py:
    £5/day unless a dated exception names the campaign's id)."""
    items, valid = [], []
    for w in windows:
        name = w.get("name", "?")
        try:
            daily = float(w.get("daily_gbp"))
        except (TypeError, ValueError):
            daily = None
        if daily is None or not math.isfinite(daily) or daily <= 0:
            items.append({"kind": "error", "text": f"window {name} has no usable daily_gbp (want a number above 0): skipped"})
            continue
        if not _mmdd(w.get("start")) or not _mmdd(w.get("end")):
            items.append({"kind": "error", "text": f"window {name} has a bad start or end (want MM-DD): skipped"})
            continue
        if not w.get("campaigns"):
            items.append({"kind": "error", "text": f"window {name} names no campaigns: skipped"})
            continue
        if any(not c.strip() for c in w["campaigns"]):
            items.append({"kind": "error", "text": f"window {name} has a blank campaign name: skipped"})
            continue
        valid.append({**w, "daily": daily})
    flagged = set()
    for c in campaigns:
        if c.get("status") != "ENABLED":
            continue
        lname = c["name"].lower()
        active = [w for w in valid if any(s.lower() in lname for s in w["campaigns"])
                  and in_window(today, w["start"], w["end"])]
        if not active:
            items.append({"kind": "note", "text": f"no window covers {c['name']} today: left as it is"})
            continue
        if len(active) > 1:
            items.append({"kind": "error", "text": f"{c['name']} is in {len(active)} windows today "
                                                   f"({', '.join(w['name'] for w in active)}): no proposal"})
            continue
        w = active[0]
        cap = budget_cap.cap_gbp(c.get("id"), today)
        daily = min(w["daily"], cap)
        if w["daily"] > cap and (w["name"], cap) not in flagged:
            flagged.add((w["name"], cap))
            items.append({"kind": "error", "text": f"window {w['name']} asks for £{w['daily']:,.2f}/day, above the "
                                                   f"£{cap:g} cap: capped at £{cap:,.2f}"})
        if abs(daily - c["budget_gbp"]) >= 0.005:
            items.append({"kind": "propose", "campaign": c["name"], "campaign_id": c.get("id"),
                          "current": c["budget_gbp"], "proposed": daily, "window": w["name"],
                          "text": f"{c['name']} £{c['budget_gbp']:,.2f} → £{daily:,.2f}/day (window {w['name']})"})
    return items


def proposal_lines(items):
    errors = [f"CONFIG ERROR: {i['text']}" for i in items if i["kind"] == "error"]
    rest = [f"PROPOSE: {i['text']}" if i["kind"] == "propose" else i["text"] for i in items if i["kind"] != "error"]
    lines = errors + rest
    if not errors and not any(i["kind"] == "propose" for i in items):
        lines.append("budgets match the season's windows")
    return lines


# ---------- 13. Search Console shortlist ----------

INTENT = re.compile(r"\b(choirs?|singers|carol(ler)?s? singers?|carollers|choristers?|quartets?|ensembles?"
                    r"|hire|hiring|book|booking)\b", re.I)
NOT_INTENT = re.compile(r"\b(solo|soloists?|singer|vocalists?|lyrics|chords|meaning|history|youtube|free"
                        r"|readings|order of service|join|auditions?)\b", re.I)
STOP = {"a", "an", "the", "for", "of", "in", "at", "to", "and", "or", "with", "near", "me", "my", "uk", "london",
        "hire", "hiring", "hired", "book", "booking", "cost", "costs", "price", "prices", "how", "much", "best",
        "local", "cheap", "service", "services"}
GENERIC = {"choir", "choirs", "singers", "choral", "ensemble", "ensembles"}


def hiring_intent(query):
    return bool(INTENT.search(query or "")) and not NOT_INTENT.search(query or "")


# Search terms (section 2 and the Command Centre's "Search terms to check"). CLAUDE.md's targeting rule: choir and
# "carol singers" (plural) bookings only, never solo-singer searches; every campaign carries the negatives singer,
# soloist, solo and vocalist. A flag is a reason to look, never a change: negatives are proposed in the Monday
# review and applied only after the owner approves them.
SOLO_TERMS = re.compile(r"\b(solo|soloists?|singer|vocalists?)\b", re.I)
CHOIR_WORDS = re.compile(r"\b(choral|chorus|carols?)\b", re.I)  # with INTENT: a term that names what we sell


def search_term_flag(term):
    """Why a search term needs a look, or None: a solo-singer word (the targeting rule), another word that isn't
    a hiring search (economics.NOT_INTENT), or no choir or hiring word at all."""
    term = term or ""
    m = SOLO_TERMS.search(term)
    if m:
        return f"solo-singer search ('{m[1].lower()}'): choirs of four or more only"
    m = NOT_INTENT.search(term)
    if m:
        return f"not a hiring search ('{m[1].lower()}')"
    if not INTENT.search(term) and not CHOIR_WORDS.search(term):
        return "no choir or hiring word"
    return None


def main_term(query):
    words = re.findall(r"[a-z0-9']+", (query or "").lower())
    for w in words:
        if w not in STOP and w not in GENERIC and not w.isdigit():
            return w
    for w in words:
        if w in GENERIC:
            return w
    return (query or "").lower().strip()


def is_first_monday(day):
    return day.weekday() == 0 and day.day <= 7


def next_first_monday(day):
    d = day
    while not is_first_monday(d):
        d += datetime.timedelta(days=1)
    return d


def gsc_window(today):
    """The last 28 days Search Console has final data for (it lags about 3 days)."""
    end = today - datetime.timedelta(days=3)
    return end - datetime.timedelta(days=27), end


def shortlist(rows, h2s=None, limit=10):
    """rows: Search Console rows with keys [query, page]. Returns the top `limit` hiring-intent queries
    (by impressions) at average position 8-20 with 20+ impressions, each with its main page and one fix.
    h2s(page) -> [h2 text] or None when the page can't be read (the h2 rule is then skipped)."""
    by = defaultdict(lambda: {"impr": 0, "clicks": 0, "pos_x_impr": 0.0, "pages": defaultdict(int)})
    for r in rows:
        query, page = r["keys"][0], r["keys"][1]
        a = by[query]
        a["impr"] += r.get("impressions", 0)
        a["clicks"] += r.get("clicks", 0)
        a["pos_x_impr"] += r.get("position", 0) * r.get("impressions", 0)
        a["pages"][page] += r.get("impressions", 0)
    out = []
    for query, a in by.items():
        if not a["impr"] or not hiring_intent(query):
            continue
        # Impression-weighted mean of the per-page positions: an approximation of the
        # query's own average position, which Search Console doesn't give per query x page.
        pos = a["pos_x_impr"] / a["impr"]
        if a["impr"] < 20 or not 8 <= pos <= 20:
            continue
        page = max(a["pages"].items(), key=lambda kv: (kv[1], kv[0]))[0]
        out.append({"query": query, "page": page, "position": pos, "impressions": a["impr"],
                    "clicks": a["clicks"], "ctr": a["clicks"] / a["impr"]})
    out.sort(key=lambda x: (-x["impressions"], x["query"]))
    out = out[:limit]
    for item in out:
        item["fix"] = suggested_fix(item, h2s(item["page"]) if h2s else None)
    return out


def suggested_fix(item, h2s):
    q = item["query"]
    term = main_term(q)
    if term.endswith("s") and not term.endswith("ss") and len(term) > 1:
        term = term[:-1]  # one plural s only: "weddings" -> "wedding", "bass" stays
    if h2s is not None and not any(term in h.lower() for h in h2s):
        return f"add a section answering '{q}'"
    if 8 <= item["position"] <= 12:
        return f"add an internal link from a related page with anchor '{q}'"
    return f"strengthen the title/meta for '{q}'"


def shortlist_lines(items, site="https://londonchoralservice.com"):
    if not items:
        return ["(no hiring-intent queries at positions 8–20 with 20+ impressions)"]
    lines = []
    for i in items:
        page = i["page"].replace(site, "") or "/"
        lines.append(f"{i['query']} → {page} · pos {i['position']:.1f} · impr {i['impressions']:.0f}"
                     f" · CTR {i['ctr'] * 100:.1f}%")
        lines.append(f"   suggested fix: {i['fix']}")
    return lines


def page_h2s_from(root):
    """Returns h2s(url) -> [h2 texts] read from the local copy of the page under root, or None."""
    root = Path(root).resolve()

    def h2s(url):
        path = urlparse(url).path or "/"
        rel = path.lstrip("/")
        candidates = [rel + "index.html"] if path.endswith("/") else (
            [rel] if Path(rel).suffix else [rel + ".html", rel + "/index.html"])
        for c in candidates:
            f = (root / c).resolve()
            if f.suffix != ".html" or root not in f.parents or not f.is_file():
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            found = re.findall(r"<h2\b[^>]*>(.*?)</h2>", text, re.S | re.I)
            return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h))).strip() for h in found]
        return None

    return h2s
