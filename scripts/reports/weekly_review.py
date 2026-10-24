#!/usr/bin/env python3
"""Read-only data pull for the Monday review: Google Ads, GA4 and Search
Console in one report. Changes nothing and prints no personal data.

Sections:
  1. Campaigns: last 7 days and since --since (impression share, budget use)
  2. Search terms, last 7 days, with the keyword that matched each one
  3. Conversions per action (7 and 28 days), primary or secondary, status, and the last day each was seen;
     "!CHECK" when an action other than the owner's two is primary or either of those isn't primary and ENABLED
  4. Ads: approval, review status, strength, headline and description counts, final URL; enabled sitelinks
     per campaign
  5. GA4: lead/contact events with their parameters; sessions by channel
  5c. GoatCounter: visits and enquiry events from every visitor
  5d. Core Web Vitals: CrUX field data (phones, p75) for the money pages, with a PageSpeed lab fallback
  6. Search Console: last 7 complete days vs the 7 before, by query and page
  7. Search Console coverage: sitemap freshness, index status of every ad landing page
  8. Tracking wiring: live tags and labels, Ads account settings, GA4 key events and links
  9. Bookings ledger: counts and totals only (no personal data)
  9b. Enquiries by ad source: the pipeline's enquiries graded A/B/C per campaign (enquiry_sources.py), this
      week's one per line and the last 28 days' counts (dates, occasions and grades only)
  10. Money: client receipts, deposits overdue, balances due, singer invoices (totals only)
  11. True cost per booking: season spend, enquiries, bookings and £ booked by campaign, crediting a campaign
      by click reference or, failing that, by the enquiry's A or B grade
      (also writes ~/lcs-private/ads-summary.json for the dashboard)
  12. Seasonal budget rules: proposals from data/budget-windows.yml (never above £5/day), the Christmas value
      check and the spend guard, both judged on Ads conversions and A or B enquiries (C never counts)
  13. Search Console shortlist: first Monday of the month, or with --gsc-shortlist

Each section runs on its own: one that fails prints its heading and "SECTION <id> FAILED: <exception type>"
(plus "looks like a Google auth error" when it does) and the rest still run.

Uses google-ads.yaml for Ads and Application Default Credentials (the
analytics.readonly and webmasters.readonly scopes) for GA4 and Search Console.
Reads the private bookings ledger for counts only; prints no names or emails.

    source .venv/bin/activate
    python scripts/reports/weekly_review.py [--since 2026-09-26] [--gsc-shortlist] [--save-report [--quiet]] [--write-proposals]

--save-report also archives everything printed to ~/lcs-private/reports/<today, Europe/London>.txt
(LCS_PRIVATE_DIR respected), mode 600 in a mode-700 directory, written atomically. A same-day rerun
overwrites the file. It still prints to stdout as normal, unless --quiet: then it prints only the path,
the sections present and any line that looks like a failure or an alarm (the Monday dispatcher's view;
its sub-agents read their own sections with scripts/reports/report_sections.py).

--write-proposals also writes each section 12 "PROPOSE" line as a Command Centre proposal,
~/lcs-private/command-centre/proposals/<id>.json (mode 600): kind "ads", scripts/ads/set_budget.py with the
campaign id and the £/day as its args, pinned to origin/main's commit and the script's blob there (git run with
command_centre/actions' hardened settings). Never above £5/day; a proposal with the same blob and args that is
still waiting (no .applied record) isn't written twice. The owner approves it in the app; nothing here changes
the account.
"""

import argparse
import contextlib
import datetime
import io
import json
import os
import re
import sys
from collections import defaultdict

import csv
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "bookings"))
sys.path.insert(0, str(REPO / "scripts" / "ads"))
sys.path.insert(0, str(REPO / "scripts" / "reports"))
import check_payments  # noqa: E402  is_cancelled: one cancelled rule for every ledger reader
import enquiry_sources as es  # noqa: E402  the A/B/C grades: sections 9b, 11 and 12
import goatcounter  # noqa: E402  section 5c: visits from every visitor, no cookies needed
import lcs_money as lm  # noqa: E402  LEDGER, parse_gbp, today
import upload_bookings  # noqa: E402  select_ready: section 9 counts what the upload would send

# .venv/bin/activate sets this; default it so a bare `.venv/bin/python` run works too.
os.environ.setdefault("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml"))

CUSTOMER_ID = "8733881378"
GA4_PROPERTY = "properties/527915578"
GSC_SITE = "sc-domain:londonchoralservice.com"
LEAD_EVENTS = ["generate_lead", "contact_click", "contact_message", "form_error"]
MONEY_TERMS = re.compile(r"funeral|wedding|carol|choir|choral", re.I)
SITE = "https://londonchoralservice.com"
LEDGER = lm.LEDGER  # the same ledger as every bookings script, so sections 9 and 10 always agree
EXPECTED_KEY_EVENTS = {"generate_lead", "contact_message"}
BUDGET_WINDOWS = REPO / "data" / "budget-windows.yml"


class _Tee(io.TextIOBase):
    """Writes to the original stream and also into an in-memory buffer, so a report can be printed as
    normal and archived at the same time."""

    def __init__(self, original, buffer):
        self._original = original
        self._buffer = buffer

    def write(self, s):
        if self._original is not None:
            self._original.write(s)
        self._buffer.write(s)
        return len(s)

    def flush(self):
        if self._original is not None:
            self._original.flush()


@contextlib.contextmanager
def tee_to(path, echo=True):
    """Mirror everything printed to stdout inside the block into `path`, mode 600, written atomically
    (a temp file in the same directory, then os.replace), in addition to printing as normal (echo=False:
    the file only). The directory is created mode 700 if missing. A same-day rerun (same `path`)
    overwrites the file."""
    path = Path(path)
    buffer = io.StringIO()
    original = sys.stdout
    sys.stdout = _Tee(original if echo else None, buffer)
    try:
        yield
    finally:
        sys.stdout = original
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(buffer.getvalue())
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise


def gbp(micros):
    return f"£{micros / 1e6:,.2f}"


def pct(x):
    return f"{x * 100:.0f}%" if x else "-"


def ads_query():
    from google.ads.googleads.client import GoogleAdsClient  # here, so the pure sections import without it
    """A read-only GAQL runner: search() only, never a mutate."""
    c = GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")

    def q(query):
        return list(ga.search(customer_id=CUSTOMER_ID, query=query))
    return q


def search_term_rows(q, where="segments.date DURING LAST_7_DAYS"):
    """Section 2's search-term query (read-only): one row per campaign, term and matched keyword, costliest first.
    The Command Centre's cache (cc_sync.py marketing) runs the same query for 7 and 28 days."""
    return q(f"""SELECT campaign.name, search_term_view.search_term, segments.keyword.info.text,
            segments.keyword.info.match_type, metrics.impressions, metrics.clicks, metrics.cost_micros,
            metrics.conversions
            FROM search_term_view WHERE {where}
            ORDER BY metrics.cost_micros DESC, metrics.impressions DESC""")


def search_term_flag(term):
    """economics.search_term_flag, imported here so the pure module stays the one rule (section 2 and the Command
    Centre flag the same terms)."""
    import economics as ec
    return ec.search_term_flag(term)


def ads_sections(since, q):
    """Sections 1 to 4b in a row, unguarded, and (landing pages, Ads settings): for the tests. run_sections runs
    each on its own."""
    campaigns_section(q, since)
    search_terms_section(q)
    conversions_section(q)
    landing = ads_section(q)
    recommendations_section(q)
    return landing, ads_settings(q)


def campaigns_section(q, since):
    today = lm.today()
    spans = [("last 7 days", "segments.date DURING LAST_7_DAYS", 7),
             (f"since {since}", f"segments.date BETWEEN '{since}' AND '{today}'", max((today - since).days, 1))]
    print("== 1. Campaigns")
    for label, where, days in spans:
        print(f"-- {label}")
        for r in q(f"""SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros,
                metrics.impressions, metrics.clicks, metrics.ctr, metrics.average_cpc, metrics.cost_micros,
                metrics.conversions, metrics.search_impression_share,
                metrics.search_budget_lost_impression_share, metrics.search_rank_lost_impression_share
                FROM campaign WHERE campaign.status != 'REMOVED' AND {where}"""):
            m = r.metrics
            print(f"{r.campaign.name} [{r.campaign.id}] {r.campaign.status.name} budget {gbp(r.campaign_budget.amount_micros)}/day"
                  f" · spend {gbp(m.cost_micros)} ({gbp(m.cost_micros / days)}/day avg)")
            print(f"   impr {m.impressions} · clicks {m.clicks} · CTR {pct(m.ctr)} · avg CPC {gbp(m.average_cpc)}"
                  f" · conv {m.conversions:.1f} · IS {pct(m.search_impression_share)}"
                  f" · lost to budget {pct(m.search_budget_lost_impression_share)}"
                  f" · lost to rank {pct(m.search_rank_lost_impression_share)}")
    logged_changes_lines(today)


def search_terms_section(q):
    print("\n== 2. Search terms, last 7 days (campaign | term | matched keyword | impr clicks cost conv)")
    import economics as ec
    negatives = defaultdict(list)
    for r in q("""SELECT campaign.name, campaign_criterion.keyword.text, campaign_criterion.keyword.match_type
                  FROM campaign_criterion WHERE campaign_criterion.negative = TRUE
                  AND campaign_criterion.type = 'KEYWORD' AND campaign.status = 'ENABLED'"""):
        negatives[r.campaign.name].append((r.campaign_criterion.keyword.text, r.campaign_criterion.keyword.match_type.name))
    rows = search_term_rows(q)
    for r in rows:
        k = r.segments.keyword.info
        why = search_term_flag(r.search_term_view.search_term)
        blocked = ec.negative_blocking(r.search_term_view.search_term, negatives[r.campaign.name])
        print(f"{r.campaign.name[:22]:22} | {r.search_term_view.search_term} | {k.text} ({k.match_type.name})"
              f" | {r.metrics.impressions} {r.metrics.clicks} {gbp(r.metrics.cost_micros)} {r.metrics.conversions:.1f}"
              + (f"  !CHECK: {why}" if why else "")
              + (f"  [now blocked by negative '{blocked[0]}' ({blocked[1]})]" if blocked else ""))
    if not rows:
        print("(none)")
    print(f"-- negatives in force: " + " · ".join(f"{name} {len(v)}" for name, v in sorted(negatives.items())))
    print("-- ad clicks by day, last 7 days (date | campaign | clicks | cost)")
    daily = q("""SELECT campaign.name, segments.date, metrics.clicks, metrics.cost_micros FROM campaign
                 WHERE segments.date DURING LAST_7_DAYS AND metrics.clicks > 0 ORDER BY segments.date""")
    for r in daily:
        print(f"   {r.segments.date} | {r.campaign.name} | {r.metrics.clicks} | {gbp(r.metrics.cost_micros)}")
    if not daily:
        print("   (none)")


PRIMARY_ACTIONS = ("Submit lead form", "WhatsApp or email click")  # the owner's two primary conversion actions


def conversions_section(q):
    today = lm.today()
    print("\n== 3. Conversions per action")
    start90 = today - datetime.timedelta(days=90)
    per = defaultdict(lambda: {"7": 0.0, "28": 0.0, "last": None})
    for r in q(f"""SELECT segments.conversion_action_name, segments.date, metrics.all_conversions
            FROM campaign WHERE segments.date BETWEEN '{start90}' AND '{today}' AND metrics.all_conversions > 0"""):
        a = per[r.segments.conversion_action_name]
        d = datetime.date.fromisoformat(r.segments.date)
        if (today - d).days <= 7:
            a["7"] += r.metrics.all_conversions
        if (today - d).days <= 28:
            a["28"] += r.metrics.all_conversions
        a["last"] = max(filter(None, [a["last"], d]))
    seen = set()
    for action in q("SELECT conversion_action.name, conversion_action.status, conversion_action.primary_for_goal "
                    "FROM conversion_action WHERE conversion_action.status != 'REMOVED'"):
        c = action.conversion_action
        name, status = c.name, c.status.name
        seen.add(name)
        # Hidden actions (GA4 imports Google keeps out of view) are listed only when they matter to the check.
        if status != "ENABLED" and name not in PRIMARY_ACTIONS and not c.primary_for_goal:
            continue
        a = per.get(name, {"7": 0, "28": 0, "last": None})
        role = "primary" if c.primary_for_goal else "secondary"
        flags = []
        if c.primary_for_goal and name not in PRIMARY_ACTIONS:
            flags.append("!CHECK: primary, but not one of the owner's two primary actions")
        if name in PRIMARY_ACTIONS and not c.primary_for_goal:
            flags.append("!CHECK: should be primary")
        if name in PRIMARY_ACTIONS and status != "ENABLED":
            flags.append(f"!CHECK: {status}, should be ENABLED")
        print(f"{name:32} {role:9} {status:7} 7d {a['7']:.1f} · 28d {a['28']:.1f} · "
              f"last seen {a['last'] or 'not in 90 days'}{''.join(' ' + f for f in flags)}")
    for name in PRIMARY_ACTIONS:
        if name not in seen:
            print(f"{name:32} !CHECK: not in the account (removed or renamed); it should be primary and ENABLED")


def ads_section(q):
    """Section 4; returns the enabled ads' final URLs (section 7 inspects them)."""
    print("\n== 4. Ads (enabled campaigns)")
    landing, campaigns = set(), set()
    for r in q("""SELECT campaign.name, ad_group.name, ad_group.status, ad_group_ad.ad.id, ad_group_ad.status,
            ad_group_ad.policy_summary.approval_status, ad_group_ad.policy_summary.review_status,
            ad_group_ad.ad_strength, ad_group_ad.action_items, ad_group_ad.ad.final_urls,
            ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions
            FROM ad_group_ad WHERE campaign.status = 'ENABLED' AND ad_group_ad.status != 'REMOVED'"""):
        a = r.ad_group_ad
        urls = list(a.ad.final_urls)
        rsa = a.ad.responsive_search_ad
        counts = f" headlines={len(rsa.headlines)} descriptions={len(rsa.descriptions)}"
        if a.status.name == "ENABLED" and r.ad_group.status.name == "ENABLED":
            landing.update(urls)
            campaigns.add(r.campaign.name)
        flags = []
        if a.policy_summary.approval_status.name not in ("APPROVED",):
            flags.append("NOT APPROVED")
        if any(u.startswith("http://") for u in urls):
            flags.append("HTTP URL")
        print(f"{r.campaign.name[:22]:22} {r.ad_group.name[:22]:22} {a.ad.id} {a.status.name}"
              f" {a.policy_summary.approval_status.name}/{a.policy_summary.review_status.name}"
              f" strength={a.ad_strength.name}{counts} → {', '.join(urls)} {' '.join('!' + f for f in flags)}")
        if a.status.name == "ENABLED" and a.ad_strength.name in ("POOR", "AVERAGE"):
            for item in a.action_items:
                print(f"      to improve: {item}")
    sitelinks = defaultdict(int, {c: 0 for c in campaigns})  # a campaign with ads but no sitelink shows 0
    for r in q("""SELECT campaign.id, campaign.name, campaign.status, campaign_asset.field_type, campaign_asset.status
            FROM campaign_asset WHERE campaign.status = 'ENABLED' AND campaign_asset.field_type = 'SITELINK'
            AND campaign_asset.status = 'ENABLED'"""):
        sitelinks[r.campaign.name] += 1
    for name in sorted(sitelinks):
        print(f"   {name[:40]:40} sitelinks={sitelinks[name]}")
    return sorted(landing)


def recommendations_section(q):
    print("\n== 4b. Google's recommendations (open, not dismissed)")
    names = {str(r.campaign.id): r.campaign.name for r in q("SELECT campaign.id, campaign.name FROM campaign")}
    recs = defaultdict(set)
    for r in q("SELECT recommendation.type, recommendation.campaign, recommendation.dismissed FROM recommendation"):
        if not r.recommendation.dismissed:
            camp = r.recommendation.campaign.split("/")[-1]
            recs[r.recommendation.type_.name].add(names.get(camp, "account") if camp else "account")
    for kind, camps in sorted(recs.items()):
        print(f"   {kind:34} {', '.join(sorted(camps))}")
    if not recs:
        print("   (none)")


def ads_settings(q):
    """The account's tracking settings for section 8: {label: on/off}."""
    settings = {}
    for r in q("""SELECT customer.auto_tagging_enabled,
            customer.conversion_tracking_setting.accepted_customer_data_terms,
            customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled FROM customer"""):
        t = r.customer.conversion_tracking_setting
        settings = {"auto-tagging": r.customer.auto_tagging_enabled,
                    "customer data terms accepted": t.accepted_customer_data_terms,
                    "enhanced conversions for leads": t.enhanced_conversions_for_leads_enabled}
    return settings


# ---------- the change log, for the ads agent's FLAGS (section 1) ----------

CHANGE_LOG = "logs/ads-changes.md"
LOG_DAYS, LOG_MAX = 21, 60
# The date of "THE ACCOUNT AS THE OWNER SET IT" in .claude/agents/lcs-review-ads.md: every change logged since then
# is printed (and the last LOG_DAYS days' anyway). Move both together (tests/test_enquiry_sources.py checks).
ADS_BASELINE = datetime.date(2026, 10, 23)
LOG_ROW = re.compile(r"^\| (\d{4}-\d{2}-\d{2})(?: \d{2}:\d{2})? \|")


def _log_text_at_origin(runner=None):
    """origin/main's copy of the change log (as of the last fetch; read-only, the hardened git), or None. The main
    checkout can lag GitHub when a change set was merged from a worktree."""
    import subprocess
    try:
        binary, safe, env = hardened_git()
        p = (runner or subprocess.run)([binary, "-C", str(REPO), *safe, "show", f"origin/main:{CHANGE_LOG}"],
                                       capture_output=True, text=True, timeout=15, env=env,
                                       stdin=subprocess.DEVNULL, shell=False)
        return p.stdout if p.returncode == 0 else None
    except Exception:
        return None


def logged_changes(text, today, days=LOG_DAYS, baseline=None):
    """(date, resource, field, current → new) for each change-log row dated within `days` of today or on or after
    `baseline` (ADS_BASELINE), newest first. Rows with the same time, field and change (one bid on many keywords)
    are one row: "<first> (+n more alike)"."""
    since = min(today - datetime.timedelta(days=days), baseline or ADS_BASELINE)
    out = []
    for ln in (text or "").splitlines():
        m = LOG_ROW.match(ln)
        if not m:
            continue
        try:
            day = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if day >= since and len(cells) >= 4:
            out.append([cells[0], cells[1], cells[2], cells[3], 0])
    merged = []
    for row in out:
        prev = merged[-1] if merged else None
        if prev and (prev[0], prev[2], prev[3]) == (row[0], row[2], row[3]):
            prev[4] += 1
        else:
            merged.append(row)
    return [(w, r + (f" (+{n} more alike)" if n else ""), f, c) for w, r, f, c, n in merged]


def logged_changes_lines(today, runner=None):
    """Section 1's tail: the Ads changes logged in the last four weeks, newest first, so a setting that differs from
    the agent's baseline but was changed on purpose is not reported as a finding. Whichever copy of the log is newer
    (this checkout's or origin/main's) is used."""
    try:
        local = (REPO / CHANGE_LOG).read_text(encoding="utf-8")
    except OSError:
        local = ""
    copies = [logged_changes(t, today) for t in (local, _log_text_at_origin(runner)) if t]
    rows = max(copies, key=lambda rows: (rows[0][0] if rows else "", len(rows)), default=[])
    since = min(today - datetime.timedelta(days=LOG_DAYS), ADS_BASELINE)
    print(f"-- changes logged in {CHANGE_LOG} since {since}, newest first (the owner's own changes"
          + (f"; the newest {LOG_MAX} of {len(rows)})" if len(rows) > LOG_MAX else ")"))
    for when, resource, field, change in rows[:LOG_MAX]:  # "log " keeps them out of --quiet's problem lines
        print(f"   log {when} · {resource[:180]} · {field[:40]} · {change[:160]}")
    if not rows:
        print("   (none)")


GA4_API = f"https://analyticsdata.googleapis.com/v1beta/{GA4_PROPERTY}:runReport"


class GA4Error(RuntimeError):
    """A GA4 report that didn't come back: .status and .detail (Google's message, printed only by section 5)."""

    def __init__(self, status, detail):
        super().__init__(f"GA4 error {status}")
        self.status, self.detail = status, detail


def ga4_report(s, body):
    """(rows, thresholded) for one GA4 runReport (read-only). GA4Error when it fails."""
    r = s.post(GA4_API, json=body)
    if not r.ok:
        try:
            detail = r.json().get("error", {}).get("message")
        except ValueError:
            detail = None
        raise GA4Error(r.status_code, detail)
    data = r.json()
    return data.get("rows", []), bool(data.get("metadata", {}).get("subjectToThresholding"))


def lead_category(event, method):
    """The weekly leads bucket for one LEAD_EVENTS event: form (generate_lead), whatsapp, email or call (a
    contact_click's method), message (contact_message) or form_error."""
    if event == "generate_lead":
        return "form"
    if event == "contact_click":
        return method if method in ("whatsapp", "email", "call") else "other"
    return {"contact_message": "message", "form_error": "form_error"}.get(event)


def ga4_lead_weeks(s, today, n=8):
    """The LEAD_EVENTS section 5 counts, by full Monday-Sunday week for the last `n` weeks, oldest first:
    ([{week_start, form, whatsapp, email, call, other, message, form_error}], thresholded). Counts only."""
    import economics as ec
    weeks = ec.full_weeks(today, n)
    end = weeks[-1] + datetime.timedelta(days=6)
    rows, thresholded = ga4_report(s, {
        "dateRanges": [{"startDate": str(weeks[0]), "endDate": str(end)}],
        "dimensions": [{"name": "date"}, {"name": "eventName"}, {"name": "customEvent:method"}],
        "metrics": [{"name": "eventCount"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {"values": LEAD_EVENTS}}},
        "limit": 10000})
    keys = ("form", "whatsapp", "email", "call", "other", "message", "form_error")
    acc = {w: dict.fromkeys(keys, 0) for w in weeks}
    for row in rows:
        day_s, event, method = (v.get("value", "") for v in row["dimensionValues"])
        try:
            day = datetime.date(int(day_s[:4]), int(day_s[4:6]), int(day_s[6:8]))
            count = int(float(row["metricValues"][0]["value"]))
        except (ValueError, KeyError, IndexError):
            continue
        week = day - datetime.timedelta(days=day.weekday())
        cat = lead_category(event, method)
        if week in acc and cat:
            acc[week][cat] += count
    return [{"week_start": w.isoformat(), **acc[w]} for w in weeks], thresholded


def ga4_section(s):
    thresholded = []

    def report(body):
        try:
            rows, held = ga4_report(s, body)
        except GA4Error as e:
            print(f"GA4 error {e.status}: {e.detail}")
            return []
        if held:
            thresholded.append(", ".join(d["name"] for d in body.get("dimensions", [])))
        return rows

    week = [{"startDate": "7daysAgo", "endDate": "yesterday"}]
    print("\n== 5. GA4, last 7 days")
    in_events = {"filter": {"fieldName": "eventName", "inListFilter": {"values": LEAD_EVENTS}}}
    for dims in (["eventName"],
                 ["eventName", "customEvent:occasion", "customEvent:lead_source"],
                 ["eventName", "customEvent:method", "customEvent:link_location"],
                 ["eventName", "customEvent:error_type"]):
        print("-- " + " × ".join(dims))
        rows = report({"dateRanges": week, "dimensions": [{"name": d} for d in dims],
                       "metrics": [{"name": "eventCount"}], "dimensionFilter": in_events, "limit": 50})
        for row in rows:
            vals = [v["value"] for v in row["dimensionValues"]]
            if len(dims) > 1 and all(v in ("(not set)", "") for v in vals[1:]):
                continue
            print("   " + " | ".join(vals) + f" : {row['metricValues'][0]['value']}")
        if not rows:
            print("   (none)")
    print("-- sessions by channel (last 7 days vs the 7 before)")
    rows = report({"dateRanges": week + [{"startDate": "14daysAgo", "endDate": "8daysAgo"}],
                   "dimensions": [{"name": "sessionDefaultChannelGroup"}],
                   "metrics": [{"name": "sessions"}, {"name": "keyEvents"}]})
    by = defaultdict(dict)
    for row in rows:
        ch, rng = row["dimensionValues"][0]["value"], row["dimensionValues"][1]["value"]
        by[ch][rng] = (row["metricValues"][0]["value"], row["metricValues"][1]["value"])
    for ch, v in sorted(by.items(), key=lambda kv: -int(kv[1].get("date_range_0", ("0",))[0])):
        now, before = v.get("date_range_0", ("0", "0")), v.get("date_range_1", ("0", "0"))
        print(f"   {ch:22} sessions {now[0]:>4} (was {before[0]:>4}) · key events {now[1]} (was {before[1]})")
    if thresholded:
        print("   !THRESHOLDED: GA4 withheld small numbers (Google signals data thresholds) in: " + "; ".join(thresholded)
              + ". Low counts may show as zero here; use the Ads conversions in section 3 instead.")


def goatcounter_section(today):
    """Section 5c: GoatCounter's totals (read-only key in the Keychain; scripts/reports/goatcounter.py)."""
    print("\n".join(goatcounter.section(today)))


def cwv_section():
    """Section 5d: Core Web Vitals, CrUX field data with a lab fallback (scripts/reports/cwv.py)."""
    import cwv  # read-only; its API key is in the Keychain as lcs-pagespeed, the owner approved it 24 Oct 2026
    print("\n".join(cwv.section()))


def gsc_section(s):
    api = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{GSC_SITE}/searchAnalytics/query"
    end = lm.today() - datetime.timedelta(days=3)  # Search Console data lags ~2-3 days
    cur = (end - datetime.timedelta(days=6), end)
    prev = (cur[0] - datetime.timedelta(days=7), cur[0] - datetime.timedelta(days=1))

    def query(span, dims, limit=250):
        r = s.post(api, json={"startDate": str(span[0]), "endDate": str(span[1]), "dimensions": dims,
                              "rowLimit": limit, "dataState": "final"})
        if not r.ok:
            print(f"Search Console error {r.status_code}: {r.json().get('error', {}).get('message')}")
            return []
        return r.json().get("rows", [])

    print(f"\n== 6. Search Console, {cur[0]} to {cur[1]} vs {prev[0]} to {prev[1]}")
    for label, span in (("this week", cur), ("week before", prev)):
        t = (query(span, []) or [{}])[0]
        print(f"   {label:11} clicks {t.get('clicks', 0):.0f} · impr {t.get('impressions', 0):.0f}"
              f" · CTR {pct(t.get('ctr', 0))} · avg pos {t.get('position', 0):.1f}")
    now = {r["keys"][0]: r for r in query(cur, ["query"])}
    before = {r["keys"][0]: r for r in query(prev, ["query"])}
    top_page = {}  # query -> the page with the most impressions for it this week (what Google shows)
    for r in sorted(query(cur, ["query", "page"], 1000), key=lambda r: -r["impressions"]):
        top_page.setdefault(r["keys"][0], r["keys"][1].replace(SITE, "") or "/")

    def line(qry):
        r, b = now.get(qry), before.get(qry)
        pos = f"pos {r['position']:.1f}" if r else "not seen"
        was = f"was {b['position']:.1f}" if b else "new"
        page = f" → {top_page[qry]}" if qry in top_page else ""
        return (f"   {qry[:48]:48} clicks {r['clicks'] if r else 0:.0f} · impr {r['impressions'] if r else 0:.0f}"
                f" · {pos} ({was}){page}")

    print("-- money queries (funeral, wedding, carol, choir), by impressions")
    money = sorted((q for q in set(now) | set(before) if MONEY_TERMS.search(q)),
                   key=lambda q: -(now.get(q, {}).get("impressions", 0)))
    for qry in money[:40]:
        print(line(qry))
    if not money:
        print("   (none)")
    print("-- top 15 queries overall, by clicks then impressions")
    for qry in sorted(now, key=lambda q: (-now[q]["clicks"], -now[q]["impressions"]))[:15]:
        print(line(qry))
    print("-- top 15 pages, by clicks then impressions")
    pages = query(cur, ["page"], 15)
    for r in sorted(pages, key=lambda r: (-r["clicks"], -r["impressions"])):
        print(f"   {r['keys'][0].replace('https://londonchoralservice.com', '') or '/':48} clicks {r['clicks']:.0f}"
              f" · impr {r['impressions']:.0f} · pos {r['position']:.1f}")


def coverage_section(s, landing):
    print("\n== 7. Search Console coverage")
    base = f"https://www.googleapis.com/webmasters/v3/sites/{GSC_SITE}"
    r = s.get(f"{base}/sitemaps")
    if not r.ok:
        print(f"   sitemaps error {r.status_code}: {r.json().get('error', {}).get('message')}")
    for m in r.json().get("sitemap", []) if r.ok else []:
        read = (m.get("lastDownloaded") or "")[:10]
        sent = (m.get("lastSubmitted") or "")[:10]
        age = lambda d: (lm.today() - datetime.date.fromisoformat(d)).days if d else 9999
        stale = age(read) > 14 and age(sent) > 7  # a fresh resubmission gets a week to be read
        counts = ", ".join(f"{c.get('submitted')} submitted / {c.get('indexed', '?')} indexed" for c in m.get("contents", []))
        print(f"   {m['path']} · submitted {(m.get('lastSubmitted') or '')[:10]} · last read by Google {read or 'never'}"
              f" · {counts} · errors {m.get('errors', 0)} · warnings {m.get('warnings', 0)}"
              f"{'  !STALE: resubmit' if stale else ('  (resubmitted, waiting for Google)' if age(read) > 14 else '')}")
    try:
        with urllib.request.urlopen(f"{SITE}/sitemap.xml", timeout=20) as f:
            print(f"   live sitemap.xml lists {f.read().decode().count('<loc>')} URLs")
    except OSError as e:
        print(f"   live sitemap.xml unreadable: {e}")
    print("-- ad landing pages (URL Inspection)")
    if landing is None:
        print("   not known: section 4 failed, so the ads' final URLs weren't read")
        landing = []
    for url in landing:
        r = s.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                   json={"inspectionUrl": url, "siteUrl": GSC_SITE})
        if not r.ok:
            print(f"   {url}: error {r.status_code} {r.json().get('error', {}).get('message', '')[:80]}")
            continue
        ir = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
        flag = "" if ir.get("verdict") == "PASS" else "  !NOT INDEXED"
        print(f"   {url.replace(SITE, '') or '/'}: {ir.get('coverageState', '?')} · last crawl "
              f"{(ir.get('lastCrawlTime') or 'never')[:10]}{flag}")


def wiring_section(s, q):
    print("\n== 8. Tracking wiring")
    partial = (REPO / "partials" / "analytics.html").read_text()
    labels = sorted(set(re.findall(r"AW-17988388404/[\w-]+", partial)))
    checks = {"/": ["G-9FENN7VS0E", "AW-17988388404", "contact_click", "lcsLead", *labels],
              "/contact.html": ["G-9FENN7VS0E", "h-captcha", "botcheck"],
              "/js/form.js": ["lcsLead", "lcsAttribution", "h-captcha-response"]}
    for path, needles in checks.items():
        try:
            with urllib.request.urlopen(f"{SITE}{path}", timeout=20) as f:
                body = f.read().decode("utf-8", "replace")
        except OSError as e:
            print(f"   {path}: unreachable ({e})  !CHECK")
            continue
        missing = [n for n in needles if n not in body]
        print(f"   {path}: " + ("all tags present" if not missing else "MISSING " + ", ".join(missing) + "  !CHECK"))
    try:
        for k, v in ads_settings(q).items():
            print(f"   Ads {k}: {'on' if v else 'OFF'}")
    except Exception as e:  # type name only; the GA4 lines below still print
        print(f"   Ads settings: not read, failed: {failure_note(e)}")
    admin = f"https://analyticsadmin.googleapis.com/v1beta/{GA4_PROPERTY}"
    r = s.get(f"{admin}/keyEvents")
    if r.ok:
        have = {e["eventName"] for e in r.json().get("keyEvents", [])}
        missing = EXPECTED_KEY_EVENTS - have
        print(f"   GA4 key events: {', '.join(sorted(have)) or '(none)'}"
              + (f"  !MISSING {', '.join(sorted(missing))}" if missing else ""))
    else:
        print(f"   GA4 key events: error {r.status_code}")
    r = s.get(f"{admin}/googleAdsLinks")
    links = [l.get("customerId") for l in r.json().get("googleAdsLinks", [])] if r.ok else []
    print(f"   GA4 ↔ Google Ads link: {'8733881378 linked' if '8733881378' in links else 'NOT LINKED  !CHECK'}")
    r = s.get(f"{admin}/dataRetentionSettings")
    if r.ok:
        print(f"   GA4 event data retention: {r.json().get('eventDataRetention', '?')}")


def ledger_counts(rows):
    """Section 9's figures. Cancelled bookings (check_payments.is_cancelled, the rule every ledger reader uses)
    are counted apart and left out of the totals; "ready" is exactly what upload_bookings.select_ready would send."""
    def value(r):
        return lm.money(r.get("value_gbp"))  # 0.0 when unreadable, nan or inf

    live = [r for r in rows if not check_payments.is_cancelled(r)]
    by = defaultdict(lambda: [0, 0.0])
    for r in live:
        by[r.get("occasion") or "?"][0] += 1
        by[r.get("occasion") or "?"][1] += value(r)
    return {
        "bookings": len(live),
        "total": round(sum(map(value, live)), 2),
        "cancelled": len(rows) - len(live),
        "latest": max((r.get("invoice_date") or "" for r in live), default=""),
        "with_ref": sum(1 for r in live if (r.get("gclid") or "").strip()),
        # the client ticked the web form's ad-measurement box (consent = form): may upload by hashed email alone
        "form_consent": sum(1 for r in live if (r.get("consent") or "").strip().lower() == "form"),
        "ready": len(upload_bookings.select_ready(rows)[0]),
        "uploaded": sum(1 for r in rows if (r.get("uploaded_at") or "").strip()),
        "by_occasion": {k: tuple(v) for k, v in sorted(by.items())},
    }


def ledger_section():
    print("\n== 9. Bookings ledger (counts only)")
    if not LEDGER.exists():
        print(f"   no ledger yet at {LEDGER}")
        return
    with open(LEDGER, newline="") as f:
        c = ledger_counts(list(csv.DictReader(f)))
    print(f"   {c['bookings']} bookings, £{c['total']:,.2f} · latest invoice {c['latest'] or '-'}"
          + (f" · {c['cancelled']} cancelled (not counted)" if c["cancelled"] else ""))
    print(f"   with an ad click reference {c['with_ref']} · ad-measurement box ticked {c['form_consent']}"
          f" · ready to upload {c['ready']} · uploaded {c['uploaded']}")
    print("   by occasion: " + " · ".join(f"{k} {n} (£{v:,.0f})" for k, (n, v) in c["by_occasion"].items()))


# ---------- 9b. enquiries by ad source (enquiry_sources.py) ----------
# Google Ads conversions can't judge a campaign here (most visitors refuse cookies), so the spend guard, the
# Christmas value check and section 11 also count the pipeline's enquiries, graded A (a click reference), B (an ad
# visit, or the client says "A Google ad") or C (only an ad click in the matching campaign that day or the day
# before: shown, never counted).

WEEK_DAYS = 7  # "this week": first seen on or after today minus 7 days, so last Monday after the run is kept


class AdClicks:
    """The Ads click lookups sections 9b and 11 share, so each is asked for once: click_view by date (a gclid's
    campaign, through economics.attribute and its private cache, saved by section 11) and the days each campaign
    had an ad click (grade C). Read-only on Google Ads."""

    def __init__(self, q, today):
        self.q, self.today, self.by_date, self.cache = q, today, {}, None

    def clicks_on(self, day):
        if day not in self.by_date:
            self.by_date[day] = {r.click_view.gclid: r.campaign.name for r in self.q(
                f"SELECT click_view.gclid, campaign.name FROM click_view WHERE segments.date = '{day}'")}
        return self.by_date[day]

    def gclid_cache(self):
        import economics as ec
        if self.cache is None:
            self.cache = ec.load_gclid_cache(ec.GCLID_CACHE, self.today)
        return self.cache

    def campaign_of(self, gclid, day):
        import economics as ec
        return ec.attribute(gclid, day, self.clicks_on, self.gclid_cache(), self.today)

    def save(self):
        import economics as ec
        if self.cache is not None:
            ec.save_json_private(ec.GCLID_CACHE, self.cache)

    def clicked_days(self, start):
        """{(date, campaign key)} for every day from `start` to today a campaign had an ad click."""
        rows = self.q(f"""SELECT campaign.id, campaign.name, segments.date, metrics.clicks FROM campaign
                          WHERE segments.date BETWEEN '{start}' AND '{self.today}' AND metrics.clicks > 0""")
        return {(datetime.date.fromisoformat(str(r.segments.date)), key) for r in rows
                if (key := es.campaign_key(r.campaign.name, r.campaign.id))}


def enquiry_grades(clicks, today, path=None):
    """(graded enquiries, or None when there is no pipeline sheet; note lines). Read-only. Ads failures don't stop
    the grading: without the click days there is no C, and an A whose click can't be looked up takes its campaign
    from its ad visit, if any."""
    import economics as ec
    rows = es.read_rows(path or ec.ENQUIRIES)
    if rows is None:
        return None, ["no pipeline sheet yet (enquiries.csv): enquiries not graded"]
    notes, failed = [], []
    try:
        season = ec.load_windows(BUDGET_WINDOWS)["season_start"]
    except Exception:
        season = None
    starts = [d for d in (season, today - datetime.timedelta(days=GUARD_DAYS), XMAS_FROM) if d]
    start = min(starts) - datetime.timedelta(days=1)
    try:
        days = clicks.clicked_days(start) if clicks else None
    except Exception as e:
        days = None
        notes.append(f"ad clicks by day not read, failed: {failure_note(e)}; no C grades this week")

    def campaign_of(gclid, day):
        try:
            return clicks.campaign_of(gclid, day)
        except Exception as e:
            failed.append(e)
            return None
    graded = es.grade_rows(rows, campaign_of if clicks else None, days)
    if failed:
        notes.append(f"click_view lookups failed: {failure_note(failed[0])}; those A enquiries take their campaign "
                     f"from their ad visit, if any")
    return graded, notes


def guard_since(today):
    return today - datetime.timedelta(days=GUARD_DAYS - 1)


def enquiries_section(clicks, today, path=None):
    """Section 9b; returns the graded enquiries (None without a pipeline sheet) for sections 11 and 12."""
    print("\n== 9b. Enquiries by ad source (A a click reference · B an ad visit, or the client says 'A Google ad' · "
          "C only an ad click in the matching campaign that day or the day before: shown, never counted)")
    graded, notes = enquiry_grades(clicks, today, path)
    for n in notes:
        print("   " + n)
    if graded is None:
        return None
    week = today - datetime.timedelta(days=WEEK_DAYS)
    print(f"-- this week's enquiries, first seen {week} to {today} (date · occasion · source · grade campaign (why))")
    shown = es.within(graded, week, today)
    for g in shown:
        print("   " + es.line(g))
    if not shown:
        print("   (none)")
    since = guard_since(today)
    print(f"-- by campaign, {since} to {today} (the spend guard's {GUARD_DAYS} days)")
    for ln in es.counts_lines(es.counts(graded, since, today)):
        print("   " + ln)
    return graded


def money_section():
    print("\n== 10. Money (totals and invoice numbers only)")
    try:
        sys.path.insert(0, str(REPO / "scripts" / "bookings"))
        import check_payments
        import lcs_money
        import money_report
        import singer_invoices
        today = lm.today()
        singer = singer_invoices.summary(lcs_money.read_csv(singer_invoices.STORE), today)
        tok = lcs_money.keychain_token()
        if not tok:  # the singer line needs no token: its bank-change warning must never go missing
            print("   no Starling token in the Keychain: client money check skipped")
            print("   " + money_report.singer_line(singer))
            return
        client = lcs_money.StarlingReadOnly(tok)
        rows = lcs_money.read_csv(check_payments.LEDGER)
        assessments = [a for _, _, a in check_payments.collect(client, rows, today)]
        receipts = check_payments.received_since(client, rows, today - datetime.timedelta(days=6), today)  # today and six days before
        for line in money_report.summary_lines(assessments, receipts, singer, today):
            print("   " + line)
    except Exception as e:  # type name only: the message could carry ledger or bank data
        print(f"   money check failed: {type(e).__name__}")


def season_attribution(clicks, today, season, graded, names):
    """(bookings, enquiries) for economics.cost_table over the season. A booking is credited by its own ledger
    gclid (click_view); failing that, by its enquiry's grade (the pipeline row with its booking_ref, A or B with a
    campaign). Each enquiry is credited by its grade (A or B with a campaign, else unattributed). Without grades
    (graded None) enquiries fall back to their gclid alone; without a pipeline sheet enquiries is None."""
    import economics as ec
    by_ref = {g["booking_ref"]: g for g in graded or [] if g.get("booking_ref")}

    def name(key):
        return names.get(key) or es.label(key)
    bookings = []
    for r in ec.season_bookings(ec.lcs_money.read_csv(ec.lcs_money.LEDGER), season):
        value = ec.lcs_money.money(r.get("value_gbp"))
        camp = ec.attribute_booking(r, clicks.clicks_on, clicks.gclid_cache(), today)
        if camp:
            bookings.append((camp, value, "click"))
            continue
        g = by_ref.get((r.get("booking_ref") or "").strip())
        if g and g["grade"] in ("A", "B") and g["campaign"]:
            bookings.append((name(g["campaign"]), value, g["grade"]))
        else:
            bookings.append((None, value, None))
    if graded is not None:
        enquiries = [((name(g["campaign"]), g["grade"]) if g["grade"] in ("A", "B") and g["campaign"] else (None, None))
                     for g in graded if g["first_seen"] >= season]
    elif ec.ENQUIRIES.exists():
        enquiries = [ec.attribute(r.get("gclid"), r.get("first_seen"), clicks.clicks_on, clicks.gclid_cache(), today)
                     for r in ec.season_enquiries(ec.lcs_money.read_csv(ec.ENQUIRIES), season)]
    else:
        enquiries = None
    return bookings, enquiries


def cost_section(q, today, clicks=None, graded=None):
    print("\n== 11. True cost per booking (season to date, by campaign)")
    try:
        import economics as ec
        season = ec.load_windows(BUDGET_WINDOWS)["season_start"]
        if not season:
            print("   config error: season_start")
            return
        print(f"   season since {season}")
        print("   bookings: ledger rows invoiced since then, cancelled ones left out (check_payments.is_cancelled),"
              " PENDING ones (deposit not yet seen) counted")
        print("   credited to a campaign by click reference (gclid → click_view), else by the enquiry's grade (section"
              " 9b): A a click reference, B an ad visit or 'A Google ad'; C never counts")
        spend = defaultdict(lambda: [0, 0])
        names = {}  # campaign key (enquiry_sources) -> the Ads campaign name, matched by id
        for r in q(f"""SELECT campaign.id, campaign.name, metrics.cost_micros, metrics.clicks FROM campaign
                WHERE segments.date BETWEEN '{season}' AND '{today}'"""):
            spend[r.campaign.name][0] += r.metrics.cost_micros
            spend[r.campaign.name][1] += r.metrics.clicks
            key = es.campaign_key(None, r.campaign.id)
            if key:
                names[key] = r.campaign.name
        clicks = clicks or AdClicks(q, today)
        try:
            bookings, enquiries = season_attribution(clicks, today, season, graded, names)
        finally:
            clicks.save()
        table = ec.cost_table({k: tuple(v) for k, v in spend.items()}, bookings, enquiries)
        if enquiries is None:
            print("   enquiries: pipeline sheet not set up yet")
        elif graded is None:
            print("   enquiries: not graded this week (section 9b), so credited by click reference only")
        for line in ec.cost_lines(table):
            print("   " + line)
        start = ec.full_weeks(today, 8)[0]
        daily = [(r.segments.date, r.metrics.cost_micros, r.metrics.clicks, r.metrics.conversions)
                 for r in q(f"""SELECT segments.date, metrics.cost_micros, metrics.clicks, metrics.conversions
                        FROM customer WHERE segments.date BETWEEN '{start}' AND '{today}'""")]
        summary = ec.ads_summary(ec.week_buckets(daily, today, 8), table, season, datetime.datetime.now())
        ec.save_json_private(ec.ADS_SUMMARY, summary)
        print(f"   wrote {ec.ADS_SUMMARY.name} (last 8 full weeks and the season)")
    except Exception as e:  # type name only: the message could carry ledger data
        print(f"   true cost per booking failed: {failure_note(e)}")


def budget_section(q, today, write=False, git_runner=None, now=None, graded=None):
    """Section 12. graded: section 9b's enquiries (None: not graded, and the value check and spend guard say so)."""
    print("\n== 12. Seasonal budget rules (data/budget-windows.yml; proposals only, nothing changed)")
    try:
        import economics as ec
        cfg = ec.load_windows(BUDGET_WINDOWS)
        campaigns = [{"id": str(r.campaign.id), "name": r.campaign.name, "status": r.campaign.status.name,
                      "budget_gbp": r.campaign_budget.amount_micros / 1e6}
                     for r in q("""SELECT campaign.id, campaign.name, campaign.status, campaign_budget.amount_micros
                            FROM campaign WHERE campaign.status != 'REMOVED'""")]
        items = ec.proposals(campaigns, cfg["windows"], today)
        for line in ec.proposal_lines(items):
            print("   " + line)
    except Exception as e:
        print(f"   seasonal budget rules failed: {failure_note(e)}")
        return
    try:
        for line in value_check_lines(q, today, graded):
            print("   " + line)
    except Exception as e:  # type name only
        print(f"   Christmas value check failed: {failure_note(e)}")
    try:
        for line in spend_guard_lines(q, today, graded):
            print("   " + line)
    except Exception as e:  # type name only
        print(f"   spend guard failed: {failure_note(e)}")
    if write:
        try:
            for line in write_proposals(items, today, git_runner=git_runner, now=now):
                print("   " + line)
        except Exception as e:  # type name only
            print(f"   Command Centre proposals not written: {type(e).__name__}")


XMAS_ID, XMAS_FROM, XMAS_CHECK_BY, XMAS_EXTRA_LIMIT = 24295921372, datetime.date(2026, 9, 28), \
    datetime.date(2026, 11, 2), 60.0


def value_check_lines(q, today, graded=None):
    """The stop rule for the Christmas £8 cap (scripts/ads/budget_cap.py): spend above the £5/day level since
    28 Sep 2026, whether it has passed £60, and the evidence the campaign earns it: its Ads conversions (form,
    WhatsApp or email) and its A or B enquiries since 28 Sep (section 9b's grades; C is shown and never counts).
    graded None: the enquiries weren't graded, and the line says so. The hiring share is judged by the review."""
    if today < XMAS_FROM:
        return []
    extra = spent = conv = 0.0
    for r in q(f"""SELECT segments.date, metrics.cost_micros, metrics.conversions FROM campaign
                   WHERE campaign.id = {XMAS_ID} AND segments.date BETWEEN '{XMAS_FROM}' AND '{today}'"""):
        cost = r.metrics.cost_micros / 1e6
        spent += cost
        extra += max(0.0, cost - 5.0)
        conv += r.metrics.conversions
    line = (f"Christmas value check: £{spent:,.2f} spent since {XMAS_FROM:%d %b}, £{extra:,.2f} of it above the "
            f"£5/day level · {conv:g} Ads conversions")
    n = es.counts(graded, XMAS_FROM, today)["christmas"] if graded is not None else None
    line += (f" · enquiries from Christmas ads: A {n['A']} · B {n['B']} (C {n['C']}, never counts)" if n is not None
             else " · enquiries not graded this week (section 9b)")
    when = f" (checked from {XMAS_CHECK_BY:%d %b})" if today < XMAS_CHECK_BY else ""
    if extra > XMAS_EXTRA_LIMIT:
        if n is None:
            line += (f" — PAST £{XMAS_EXTRA_LIMIT:.0f}: back to £5 unless the pipeline shows an A or B enquiry from "
                     f"Christmas ads or an Ads conversion{when}")
        elif es.ab(n) or conv:
            line += (f" — over £{XMAS_EXTRA_LIMIT:.0f}, but the campaign brought "
                     + " and ".join(x for x in (f"{es.ab(n)} A/B enquiries" if es.ab(n) else "",
                                                f"{conv:g} Ads conversions" if conv else "") if x)
                     + ": keep £8 on this test")
        else:
            line += (f" — PAST £{XMAS_EXTRA_LIMIT:.0f} with no A or B enquiry from Christmas ads and no Ads "
                     f"conversion: back to £5{when}")
    return [line, "stop rule: back to £5 if the extra passes £60 by 2 Nov with no enquiry from Christmas ads (an A or B "
                  "grade; C never counts) and no Ads conversion, or if under 90% of a week's spend went on hiring "
                  "searches"]


GUARD_DAYS, GUARD_SPEND_GBP, GUARD_MIN_CLICKS = 28, 80.0, 15


def spend_guard_lines(q, today, graded=None):
    """The stop rule for every enabled campaign (owner, 28 Sep 2026; enquiry-aware since 23 Oct 2026): £80 or more
    in the last 28 days with no Ads conversion (form, WhatsApp or email click) AND no A or B enquiry for that
    campaign in those days (section 9b's grades) means the campaign is proposed for pausing, never deletion, until
    the owner decides. C enquiries are shown and never count. Under 15 clicks is too little to judge and is said
    so. graded None: the enquiries weren't graded, so a STOP GUARD says to check the pipeline first."""
    since = guard_since(today)
    c = es.counts(graded, since, today) if graded is not None else None
    lines = []
    for r in q(f"""SELECT campaign.id, campaign.name, metrics.cost_micros, metrics.clicks, metrics.conversions
                   FROM campaign WHERE campaign.status = 'ENABLED'
                   AND segments.date BETWEEN '{since}' AND '{today}'"""):
        cost, clicks, conv = r.metrics.cost_micros / 1e6, r.metrics.clicks, r.metrics.conversions
        key = es.campaign_key(r.campaign.name, r.campaign.id)
        n = None if c is None else c[key] if key else dict.fromkeys(es.GRADES, 0)
        line = (f"spend guard {r.campaign.name}: £{cost:,.2f}, {clicks} clicks, {conv:g} Ads conversions in "
                f"{GUARD_DAYS} days · enquiries " + (es.abc(n) if n is not None else "not graded"))
        if cost >= GUARD_SPEND_GBP and conv == 0:
            if n is not None and es.ab(n):
                line += " — held: an A or B enquiry came from this campaign, so no pause"
            elif clicks < GUARD_MIN_CLICKS:
                line += f" — under {GUARD_MIN_CLICKS} clicks, too few to judge; watch next week"
            elif budget_cap_gbp(r.campaign.id, today) > PROPOSAL_CAP_GBP:
                # Owner decision 23 Oct 2026: a campaign inside a dated budget exception (budget_cap.py) is judged
                # by that exception's own stop rule (section 12's value check), not paused by this guard.
                line += (" — deferred: inside its dated budget exception, judged by its own stop rule "
                         "(the value check in section 12), not paused here")
            else:
                line += " — STOP GUARD: propose pausing (never deleting) until the owner decides"
                if n is None:
                    line += " (enquiries not graded this week: check the pipeline first)"
                elif es.ab(c[None]):
                    line += f" ({es.ab(c[None])} ad enquiries in these {GUARD_DAYS} days name no campaign: check them first)"
        lines.append(line)
    return lines + [f"stop rule: £{GUARD_SPEND_GBP:.0f}+ in {GUARD_DAYS} days with no Ads conversion and no A or B "
                    f"enquiry → propose pausing (C never counts)"]


# ---------- 12b. Command Centre proposals (--write-proposals) ----------
# Each PROPOSE line becomes ~/lcs-private/command-centre/proposals/<id>.json (mode 600), the format
# command_centre/actions.load_proposal checks: the app runs scripts/ads/set_budget.py <campaign id> <£/day> from
# the pinned commit of GitHub's main, --validate-only and then --apply, after the owner's passkey. Nothing here
# talks to Google or changes the account.

SET_BUDGET = "scripts/ads/set_budget.py"
PROPOSAL_CAP_GBP = 5.0  # the base cap; budget_cap.py may raise it for one campaign on set dates (set_budget.py
#                        checks the same module)
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
AMOUNT_RE = re.compile(r"^\d{1,4}\.\d{2}$")


def proposals_dir():
    """Read at call time, so the tests (and a moved private tree) never touch ~/lcs-private."""
    return Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "command-centre" / "proposals"


def hardened_git():
    """(git binary, global options, environment) from command_centre/actions, the app's hardened git: no global or
    system config, none of the caller's GIT_* variables, no replace refs, fsmonitor and hooks off. If the app's
    module can't be imported (a machine without its dependencies), the same settings, copied here."""
    try:
        if str(REPO) not in sys.path:
            sys.path.insert(0, str(REPO))
        from command_centre import actions
        return actions.git_binary(), list(actions.GIT_SAFE), actions.git_env()
    except Exception:
        keep = ("HOME", "PATH", "LANG", "TZ", "https_proxy", "HTTPS_PROXY", "no_proxy", "NO_PROXY")
        env = {k: os.environ[k] for k in keep if k in os.environ}
        env.update(GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                   GIT_NO_REPLACE_OBJECTS="1")
        safe = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null",
                "--no-replace-objects"]
        return ("/usr/bin/git" if os.path.exists("/usr/bin/git") else "git"), safe, env


def git_pins(runner=None):
    """(script blob, commit): `git rev-parse origin/main:scripts/ads/set_budget.py` and `origin/main`, run in this
    repo with the hardened git settings. Raises if either isn't a full object id."""
    import subprocess
    binary, safe, env = hardened_git()

    def rev(spec):
        p = (runner or subprocess.run)([binary, "-C", str(REPO), *safe, "rev-parse", "--verify", "--quiet", spec],
                                       capture_output=True, text=True, timeout=15, env=env,
                                       stdin=subprocess.DEVNULL, shell=False)
        out = (p.stdout or "").strip()
        if p.returncode != 0 or not SHA_RE.fullmatch(out):
            raise RuntimeError("git rev-parse failed")
        return out
    return rev(f"origin/main:{SET_BUDGET}"), rev("origin/main^{commit}")


def _private_dirs(path):
    missing, d = [], Path(path)
    while not d.exists():
        missing.append(d)
        d = d.parent
    for d in reversed(missing):
        d.mkdir(mode=0o700, exist_ok=True)


def _waiting(pdir, blob, args):
    """The id of a proposal already in `pdir` with this blob and these args and no .applied record, or None."""
    for p in sorted(pdir.glob("*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("script_blob") == blob and rec.get("args") == args \
                and not (pdir / f"{p.stem}.applied").exists():
            return p.stem
    return None


def _write_new(pdir, pid, record):
    """Write <pid>.json at mode 600, all at once and never over an existing file (a temp file, then a hard link)."""
    tmp = pdir / f".{pid}.{os.getpid()}.{os.urandom(4).hex()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp, pdir / f"{pid}.json")
    finally:
        tmp.unlink(missing_ok=True)


def _supersede_older(pdir, cid, new_pid):
    """Mark every other still-waiting set_budget proposal for the same campaign `cid` as superseded by `new_pid`
    (a "superseded_by" field the Command Centre hides), so the list doesn't pile up with stale amounts."""
    for p in sorted(pdir.glob("*.json")):
        if p.stem == new_pid:
            continue
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not (isinstance(rec, dict) and rec.get("script_path") == SET_BUDGET
                and list(rec.get("args") or [])[:1] == [cid] and not rec.get("superseded_by")
                and not (pdir / f"{p.stem}.applied").exists()):
            continue
        rec["superseded_by"] = new_pid
        tmp = pdir / f".{p.stem}.{os.getpid()}.{os.urandom(4).hex()}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, p)
        finally:
            tmp.unlink(missing_ok=True)


def budget_cap_gbp(cid, today):
    """The campaign's cap on `today` from scripts/ads/budget_cap.py; the base £5 if the module can't load."""
    try:
        sys.path.insert(0, str(REPO / "scripts" / "ads"))
        import budget_cap
        return budget_cap.cap_gbp(cid, today)
    except Exception:
        return PROPOSAL_CAP_GBP


def write_proposals(items, today, git_runner=None, now=None):
    """Write one Command Centre proposal per "propose" item; returns the lines to print. Never above £5/day, and
    never a second proposal while one with the same script blob and args is still waiting (no .applied record)."""
    wanted = [i for i in items if i.get("kind") == "propose"]
    if not wanted:
        return ["no budget proposals to write"]
    blob, commit = git_pins(git_runner)
    pdir = proposals_dir()
    _private_dirs(pdir)
    created = (now or datetime.datetime.now().astimezone()).isoformat(timespec="seconds")
    lines = []
    for i in wanted:
        cid, name = str(i.get("campaign_id") or ""), str(i.get("campaign") or "?")
        try:
            new, cur = float(i["proposed"]), float(i["current"])
        except (KeyError, TypeError, ValueError):
            lines.append(f"not written ({name}): no usable amount")
            continue
        if not cid.isdigit():
            lines.append(f"not written ({name}): no campaign id")
            continue
        cap = budget_cap_gbp(cid, today)
        if not (0 < new <= cap):
            lines.append(f"not written ({name}): £{new:,.2f}/day is outside £0–£{cap:g}")
            continue
        amount = f"{new:.2f}"
        if not AMOUNT_RE.fullmatch(amount):
            lines.append(f"not written ({name}): bad amount")
            continue
        args = [cid, amount]
        waiting = _waiting(pdir, blob, args)
        if waiting:
            lines.append(f"proposal already waiting: {waiting}")
            continue
        room = 120 - len(f"Budget:  £{cur:.2f} → £{new:.2f}/day")
        shown = name if len(name) <= room else name[:room - 1] + "…"
        record = {
            "id": "", "kind": "ads", "title": f"Budget: {shown} £{cur:.2f} → £{new:.2f}/day",
            "summary": (f"Seasonal window {i.get('window', '?')} (data/budget-windows.yml): set the daily budget of "
                        f"{name} (campaign {cid}) from £{cur:.2f} to £{new:.2f}. From the Monday review of {today}. "
                        f"Runs {SET_BUDGET} {cid} {amount}, validate-only first; never above £{cap:g}/day.")[:1000],
            "script_path": SET_BUDGET, "created": created, "commit": commit, "script_blob": blob, "args": args}
        base = f"budget-{cid}-{int(round(new * 100))}-{today:%Y%m%d}"
        for n in range(1, 10):
            pid = base if n == 1 else f"{base}-{n}"
            try:
                _write_new(pdir, pid, dict(record, id=pid))
            except FileExistsError:
                continue
            _supersede_older(pdir, cid, pid)
            lines.append(f"proposal written: {pid}")
            break
        else:
            lines.append(f"not written ({name}): too many proposals with that id today")
    return lines


class SearchConsoleError(RuntimeError):
    def __init__(self, status):
        super().__init__(f"Search Console error {status}")
        self.status = status


def shortlist_items(s, today, limit=10):
    """(start, end, items) for section 13 (read-only): economics.shortlist over the last 28 final days of Search
    Console query x page rows. SearchConsoleError when the query fails. The Command Centre caches it daily."""
    import economics as ec
    start, end = ec.gsc_window(today)
    api = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{GSC_SITE}/searchAnalytics/query"
    r = s.post(api, json={"startDate": str(start), "endDate": str(end), "dimensions": ["query", "page"],
                          "rowLimit": 5000, "dataState": "final"})
    if not r.ok:
        raise SearchConsoleError(r.status_code)
    return start, end, ec.shortlist(r.json().get("rows", []), ec.page_h2s_from(REPO), limit=limit)


def shortlist_section(s, today, force):
    print("\n== 13. Search Console shortlist (hiring intent, positions 8–20)")
    try:
        import economics as ec
        if not force and not ec.is_first_monday(today):
            print(f"   runs on the first Monday of the month (next {ec.next_first_monday(today)});"
                  " use --gsc-shortlist to run it now")
            return
        try:
            start, end, items = shortlist_items(s, today)
        except SearchConsoleError as e:
            print(f"   Search Console error {e.status}")
            return
        print(f"   {start} to {end}, top 10 by impressions")
        for line in ec.shortlist_lines(items):
            print("   " + line)
    except Exception as e:
        print(f"   Search Console shortlist failed: {failure_note(e)}")


def google_session():
    """An AuthorizedSession on Application Default Credentials (GA4 and Search Console reads)."""
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    creds, _ = google.auth.default()
    return AuthorizedSession(creds)


# ---------- running the sections, each on its own ----------
# The 12 Oct 2026 report died after its first Ads query and lost every section after it. Now each section runs
# guarded: one that raises keeps what it printed, gets its heading if it never printed one, and ends with
# "SECTION <id> FAILED: <exception type>"; the next section still runs, and --quiet lists the failure.

AUTH_TYPE = re.compile(r"refresh|credential|unauthenticated|permissiondenied|forbidden|auth", re.I)
AUTH_TEXT = re.compile(r"invalid_grant|unauthenticated|authentication_error|authorization_error|permission_denied|"
                       r"invalid_scope|insufficient\w*\s+\w*\s*scopes?|credentials", re.I)


def failure_note(e):
    """The exception's type name, plus "(looks like a Google auth error: check the sign-in)" when its type or
    Google's error text says so, so the dispatcher's stop rule still sees it (a GoogleAdsException carries it in
    .failure and .error, not its message). Nothing but the type name is ever printed: the text could carry ledger,
    bank or account data. A local file error (OSError) is never called an auth error."""
    name = type(e).__name__
    try:
        text = " ".join(str(x)[:4000] for x in (e, getattr(e, "failure", ""), getattr(e, "error", "")))
    except Exception:
        text = ""
    if not isinstance(e, OSError) and (AUTH_TYPE.search(name) or AUTH_TEXT.search(text)):
        return f"{name} (looks like a Google auth error: check the sign-in)"
    # A missing sign-in file (google-ads.yaml or the gcloud credentials) is a sign-in problem too, so the
    # dispatcher stops rather than running the agents on an empty Ads half. Only the type name is printed.
    if isinstance(e, FileNotFoundError) and re.search(r"google-ads\.yaml|application_default_credentials", text):
        return f"{name} (looks like a Google auth error: the sign-in file is missing; check the sign-in)"
    return name


def run_section(sid, title, fn, *args, **kwargs):
    """Run one report section and return its result, or None if it raised (see above)."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            result = fn(*args, **kwargs)
    except Exception as e:
        text = buf.getvalue()
        if not re.search(rf"^== {re.escape(sid)}\.", text, re.M):
            text += f"\n== {sid}. {title}\n"
        sys.stdout.write(text)
        print(f"   SECTION {sid} FAILED: {failure_note(e)}")
        return None
    sys.stdout.write(buf.getvalue())
    return result


class _Lazy:
    """A Google client made on first use, once. If making it fails, every use raises that same error, so each
    section that needs it fails on its own (SECTION <id> FAILED) and the sections that don't still run."""

    def __init__(self, make):
        self._make, self._obj, self._err = make, None, None

    def _get(self):
        if self._err is not None:
            raise self._err
        if self._obj is None:
            try:
                self._obj = self._make()
            except Exception as e:
                self._err = e
                raise
        return self._obj

    def __call__(self, *a, **k):
        return self._get()(*a, **k)

    def __getattr__(self, name):
        return getattr(self._get(), name)


def run_sections(args, q=None, s=None):
    today = lm.today()
    q = q or _Lazy(ads_query)
    s = s or _Lazy(google_session)
    clicks = AdClicks(q, today)
    run_section("1", "Campaigns", campaigns_section, q, args.since)
    run_section("2", "Search terms, last 7 days", search_terms_section, q)
    run_section("3", "Conversions per action", conversions_section, q)
    landing = run_section("4", "Ads (enabled campaigns)", ads_section, q)
    run_section("4b", "Google's recommendations (open, not dismissed)", recommendations_section, q)
    run_section("5", "GA4, last 7 days", ga4_section, s)
    run_section("5c", "Visits from every visitor (GoatCounter)", goatcounter_section, today)
    run_section("5d", "Core Web Vitals", cwv_section)
    run_section("6", "Search Console", gsc_section, s)
    run_section("7", "Search Console coverage", coverage_section, s, landing)
    run_section("8", "Tracking wiring", wiring_section, s, q)
    run_section("9", "Bookings ledger (counts only)", ledger_section)
    graded = run_section("9b", "Enquiries by ad source", enquiries_section, clicks, today)
    run_section("10", "Money (totals and invoice numbers only)", money_section)
    run_section("11", "True cost per booking (season to date, by campaign)", cost_section, q, today, clicks, graded)
    run_section("12", "Seasonal budget rules", budget_section, q, today, write=args.write_proposals, graded=graded)
    run_section("13", "Search Console shortlist (hiring intent, positions 8–20)", shortlist_section, s, today,
                args.gsc_shortlist)


def report_path(today=None):
    """~/lcs-private/reports/<today, Europe/London>.txt (LCS_PRIVATE_DIR respected via lcs_money.PRIVATE)."""
    return lm.PRIVATE / "reports" / f"{today or lm.today()}.txt"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", type=datetime.date.fromisoformat, default=datetime.date(2026, 9, 26))
    p.add_argument("--gsc-shortlist", action="store_true", help="run section 13 even if it isn't the first Monday")
    p.add_argument("--save-report", action="store_true",
                   help="also archive everything printed to ~/lcs-private/reports/<today>.txt (mode 600)")
    p.add_argument("--quiet", action="store_true",
                   help="with --save-report: print only where the report is, its sections and any problem lines")
    p.add_argument("--write-proposals", action="store_true",
                   help="write each section 12 PROPOSE line as a Command Centre proposal (mode 600)")
    args = p.parse_args()
    if args.quiet and not args.save_report:
        p.error("--quiet needs --save-report (the report has to go somewhere)")
    if args.save_report:
        path = report_path()
        with tee_to(path, echo=not args.quiet):
            run_sections(args)
        if args.quiet:
            print(quiet_summary(path))
    else:
        run_sections(args)


PROBLEM_RE = re.compile(r"\b(error|failed|refused|denied|permission|invalid_grant|unauthenticated|not written|"
                        r"CONFIG ERROR|STOP GUARD|STALE|NOT INDEXED|SECTION \w+ FAILED)\b|PAST £", re.I)


def quiet_summary(path):
    """What --quiet prints instead of the report: where it is, which sections it holds and every line that
    looks like a failure or an alarm (a "SECTION <id> FAILED" line included), so the Monday dispatcher can stop on
    an auth error without reading it. The stop-rule reminders and section 1's change-log rows are never problems."""
    text = Path(path).read_text(encoding="utf-8")
    heads = re.findall(r"^== (\w+)\.", text, re.M)
    problems = [l.strip() for l in text.splitlines()
                if PROBLEM_RE.search(l) and not l.strip().startswith(("stop rule:", "log "))]
    out = [f"report saved: {path}", f"sections: {' '.join(heads) or 'none'}"]
    out += [f"problem: {l}" for l in problems[:20]] or ["problems: none"]
    return "\n".join(out)


if __name__ == "__main__":
    main()
