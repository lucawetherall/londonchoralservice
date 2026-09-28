#!/usr/bin/env python3
"""Read-only data pull for the Monday review: Google Ads, GA4 and Search
Console in one report. Changes nothing and prints no personal data.

Sections:
  1. Campaigns: last 7 days and since --since (impression share, budget use)
  2. Search terms, last 7 days, with the keyword that matched each one
  3. Conversions per action (7 and 28 days) and the last day each was seen
  4. Ads: approval, review status, strength, final URL
  5. GA4: lead/contact events with their parameters; sessions by channel
  6. Search Console: last 7 complete days vs the 7 before, by query and page
  7. Search Console coverage: sitemap freshness, index status of every ad landing page
  8. Tracking wiring: live tags and labels, Ads account settings, GA4 key events and links
  9. Bookings ledger: counts and totals only (no personal data)
  10. Money: client receipts, deposits overdue, balances due, singer invoices (totals only)

Uses google-ads.yaml for Ads and Application Default Credentials (the
analytics.readonly and webmasters.readonly scopes) for GA4 and Search Console.
Reads the private bookings ledger for counts only; prints no names or emails.

    source .venv/bin/activate
    python scripts/reports/weekly_review.py [--since 2026-09-26]
"""

import argparse
import datetime
import os
import re
import sys
from collections import defaultdict

import csv
import urllib.request
from pathlib import Path

import google.auth
from google.ads.googleads.client import GoogleAdsClient
from google.auth.transport.requests import AuthorizedSession

# .venv/bin/activate sets this; default it so a bare `.venv/bin/python` run works too.
os.environ.setdefault("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml"))

CUSTOMER_ID = "8733881378"
GA4_PROPERTY = "properties/527915578"
GSC_SITE = "sc-domain:londonchoralservice.com"
LEAD_EVENTS = ["generate_lead", "contact_click", "contact_message", "form_error"]
MONEY_TERMS = re.compile(r"funeral|wedding|carol|choir|choral", re.I)
SITE = "https://londonchoralservice.com"
REPO = Path(__file__).resolve().parents[2]
# the same ledger as scripts/bookings/lcs_money.py, so sections 9 and 10 always agree
LEDGER = Path(os.environ.get("LCS_BOOKINGS_CSV", Path(os.environ.get("LCS_PRIVATE_DIR", Path.home() / "lcs-private")) / "bookings.csv"))
EXPECTED_KEY_EVENTS = {"generate_lead", "contact_message"}


def gbp(micros):
    return f"£{micros / 1e6:,.2f}"


def pct(x):
    return f"{x * 100:.0f}%" if x else "-"


def ads_sections(since):
    c = GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")

    def q(query):
        return list(ga.search(customer_id=CUSTOMER_ID, query=query))

    today = datetime.date.today()
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

    print("\n== 2. Search terms, last 7 days (campaign | term | matched keyword | impr clicks cost conv)")
    rows = q("""SELECT campaign.name, search_term_view.search_term, segments.keyword.info.text,
            segments.keyword.info.match_type, metrics.impressions, metrics.clicks, metrics.cost_micros,
            metrics.conversions
            FROM search_term_view WHERE segments.date DURING LAST_7_DAYS
            ORDER BY metrics.cost_micros DESC, metrics.impressions DESC""")
    for r in rows:
        k = r.segments.keyword.info
        print(f"{r.campaign.name[:22]:22} | {r.search_term_view.search_term} | {k.text} ({k.match_type.name})"
              f" | {r.metrics.impressions} {r.metrics.clicks} {gbp(r.metrics.cost_micros)} {r.metrics.conversions:.1f}")
    if not rows:
        print("(none)")

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
    for action in q("SELECT conversion_action.name, conversion_action.status, conversion_action.primary_for_goal "
                    "FROM conversion_action WHERE conversion_action.status = 'ENABLED'"):
        name = action.conversion_action.name
        a = per.get(name, {"7": 0, "28": 0, "last": None})
        role = "primary" if action.conversion_action.primary_for_goal else "secondary"
        print(f"{name:32} {role:9} 7d {a['7']:.1f} · 28d {a['28']:.1f} · last seen {a['last'] or 'not in 90 days'}")

    print("\n== 4. Ads (enabled campaigns)")
    landing = set()
    for r in q("""SELECT campaign.name, ad_group.name, ad_group.status, ad_group_ad.ad.id, ad_group_ad.status,
            ad_group_ad.policy_summary.approval_status, ad_group_ad.policy_summary.review_status,
            ad_group_ad.ad_strength, ad_group_ad.action_items, ad_group_ad.ad.final_urls
            FROM ad_group_ad WHERE campaign.status = 'ENABLED' AND ad_group_ad.status != 'REMOVED'"""):
        a = r.ad_group_ad
        urls = list(a.ad.final_urls)
        if a.status.name == "ENABLED" and r.ad_group.status.name == "ENABLED":
            landing.update(urls)
        flags = []
        if a.policy_summary.approval_status.name not in ("APPROVED",):
            flags.append("NOT APPROVED")
        if any(u.startswith("http://") for u in urls):
            flags.append("HTTP URL")
        print(f"{r.campaign.name[:22]:22} {r.ad_group.name[:22]:22} {a.ad.id} {a.status.name}"
              f" {a.policy_summary.approval_status.name}/{a.policy_summary.review_status.name}"
              f" strength={a.ad_strength.name} → {', '.join(urls)} {' '.join('!' + f for f in flags)}")
        if a.status.name == "ENABLED" and a.ad_strength.name in ("POOR", "AVERAGE"):
            for item in a.action_items:
                print(f"      to improve: {item}")

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

    settings = {}
    for r in q("""SELECT customer.auto_tagging_enabled,
            customer.conversion_tracking_setting.accepted_customer_data_terms,
            customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled FROM customer"""):
        t = r.customer.conversion_tracking_setting
        settings = {"auto-tagging": r.customer.auto_tagging_enabled,
                    "customer data terms accepted": t.accepted_customer_data_terms,
                    "enhanced conversions for leads": t.enhanced_conversions_for_leads_enabled}
    return sorted(landing), settings


def ga4_section(s):
    api = f"https://analyticsdata.googleapis.com/v1beta/{GA4_PROPERTY}:runReport"

    thresholded = []

    def report(body):
        r = s.post(api, json=body)
        if not r.ok:
            print(f"GA4 error {r.status_code}: {r.json().get('error', {}).get('message')}")
            return []
        if r.json().get("metadata", {}).get("subjectToThresholding"):
            thresholded.append(", ".join(d["name"] for d in body.get("dimensions", [])))
        return r.json().get("rows", [])

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


def gsc_section(s):
    api = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{GSC_SITE}/searchAnalytics/query"
    end = datetime.date.today() - datetime.timedelta(days=3)  # Search Console data lags ~2-3 days
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

    def line(qry):
        r, b = now.get(qry), before.get(qry)
        pos = f"pos {r['position']:.1f}" if r else "not seen"
        was = f"was {b['position']:.1f}" if b else "new"
        return (f"   {qry[:48]:48} clicks {r['clicks'] if r else 0:.0f} · impr {r['impressions'] if r else 0:.0f}"
                f" · {pos} ({was})")

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
        age = lambda d: (datetime.date.today() - datetime.date.fromisoformat(d)).days if d else 9999
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


def wiring_section(s, ads_settings):
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
    for k, v in ads_settings.items():
        print(f"   Ads {k}: {'on' if v else 'OFF'}")
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


def ledger_section():
    print("\n== 9. Bookings ledger (counts only)")
    if not LEDGER.exists():
        print(f"   no ledger yet at {LEDGER}")
        return
    with open(LEDGER, newline="") as f:
        rows = list(csv.DictReader(f))

    def value(r):
        try:
            return float((r.get("value_gbp") or "0").replace("£", "").replace(",", ""))
        except ValueError:
            return 0.0

    has_ref = [r for r in rows if (r.get("gclid") or "").strip()]
    ready = [r for r in has_ref if (r.get("consent") or "").lower() == "granted" and not (r.get("uploaded_at") or "").strip()]
    uploaded = [r for r in rows if (r.get("uploaded_at") or "").strip()]
    latest = max((r.get("invoice_date") or "" for r in rows), default="")
    print(f"   {len(rows)} bookings, £{sum(map(value, rows)):,.2f} · latest invoice {latest or '-'}")
    print(f"   with an ad click reference {len(has_ref)} · ready to upload {len(ready)} · uploaded {len(uploaded)}")
    by = defaultdict(lambda: [0, 0.0])
    for r in rows:
        by[r.get("occasion") or "?"][0] += 1
        by[r.get("occasion") or "?"][1] += value(r)
    print("   by occasion: " + " · ".join(f"{k} {n} (£{v:,.0f})" for k, (n, v) in sorted(by.items())))


def money_section():
    print("\n== 10. Money (totals and invoice numbers only)")
    try:
        sys.path.insert(0, str(REPO / "scripts" / "bookings"))
        import check_payments
        import lcs_money
        import money_report
        import singer_invoices
        today = datetime.date.today()
        tok = lcs_money.keychain_token()
        if not tok:
            print("   no Starling token in the Keychain: money check skipped")
            return
        client = lcs_money.StarlingReadOnly(tok)
        rows = lcs_money.read_csv(check_payments.LEDGER)
        assessments = [a for _, _, a in check_payments.collect(client, rows, today)]
        receipts = check_payments.received_since(client, rows, today - datetime.timedelta(days=6), today)  # today and six days before
        singer = singer_invoices.summary(lcs_money.read_csv(singer_invoices.STORE), today)
        for line in money_report.summary_lines(assessments, receipts, singer, today):
            print("   " + line)
    except Exception as e:  # type name only: the message could carry ledger or bank data
        print(f"   money check failed: {type(e).__name__}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", type=datetime.date.fromisoformat, default=datetime.date(2026, 9, 26))
    args = p.parse_args()
    landing, ads_settings = ads_sections(args.since)
    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)
    ga4_section(s)
    gsc_section(s)
    coverage_section(s, landing)
    wiring_section(s, ads_settings)
    ledger_section()
    money_section()


if __name__ == "__main__":
    main()
