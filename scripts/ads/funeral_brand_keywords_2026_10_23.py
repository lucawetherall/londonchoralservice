#!/usr/bin/env python3
"""23 Oct 2026 change set 7: the "London Funeral Singers" competitor-brand keywords in "Ad group 1" of the
funeral expert campaign (23735776277). At £2.00 with quality score 3 they took £36.08 for 9 clicks in 90 days
and converted nothing, landing on the ad's funerals.html.

a. Every brand keyword's own final URL: none (the ad's funerals.html) → compare/london-funeral-singers.html,
   the page that sets the competitor's published prices next to ours. Before anything is sent the script fetches
   that page: it must answer 200 without a redirect and be its own canonical, or nothing is sent. It then checks
   every claim and price in the ad group's enabled ad(s) against the page and lists, prominently, any the page
   doesn't state (the set still validates; the owner decides). It refuses if any enabled ad's text names the
   competitor.
b. Adds exact [london funeral singers] and [the london funeral singers] at £2.00 (skips any that exist; refuses
   a bid above £2.00, or a new keyword an existing negative would block).
c. Pauses the broad-match brand variants; the phrase "London Funeral Singers" (and any exact ones) stay enabled.
   Owner rule: the competitor-brand keywords are kept.

The brand keywords are named below by id; the script refuses if the ad group's brand keywords, their match
types, statuses, bids or final URLs differ from what was reviewed. Nothing is deleted; budget and other bids are
untouched. One atomic request.

    source .venv/bin/activate
    python scripts/ads/funeral_brand_keywords_2026_10_23.py            # validate
    python scripts/ads/funeral_brand_keywords_2026_10_23.py --apply    # after approval
"""

import argparse
import datetime
import html
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402
from negative_match import blocked  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
FUNERAL = 23735776277
CAMPAIGN = "funeral expert campaign"
AD_GROUP_ID, AD_GROUP = 195400451979, "Ad group 1"
COMPARE_URL = "https://londonchoralservice.com/compare/london-funeral-singers.html"
BID, MAX_BID = 2_000_000, 2_000_000
BRAND_MARKS = ("london funeral singers", "londonfuneralsingers")
# id: (text, match type, after) — as reviewed on 23 Oct 2026; every one enabled at £2.00 with no final URL
BRAND = {
    673509934241: ("London Funeral Singers", "PHRASE", "ENABLED"),
    2477876560719: ("London funeral singers", "BROAD", "PAUSED"),
    2278475817768: ("the london funeral singers", "BROAD", "PAUSED"),
    2479669124823: ("London Funeral Singers cost", "BROAD", "PAUSED"),
    2478529512201: ("London Funeral Singers pricing", "BROAD", "PAUSED"),
    2479797201825: ("London Funeral Singers reviews", "BROAD", "PAUSED"),
    2477927494749: ("londonfuneralsingers.co.uk", "BROAD", "PAUSED"),
}
NEW_EXACT = ["london funeral singers", "the london funeral singers"]
URL_WHY = ("a searcher typing the competitor's name is comparing prices; the compare page sets their published "
           "prices next to ours (quality score 3 on funerals.html; 90 days £36.08 for 9 clicks, 0 conversions)")
PAUSE_WHY = ("broad brand variant: the phrase \"London Funeral Singers\" and the new exact keywords keep the brand "
             "searches (90 days: broad took 8 of the 9 brand clicks, £31.26, 0 conversions)")
NEW_WHY = "exact brand search at the same £2.00, landing on the compare page, in place of the paused broad variants"
SCRIPT = "scripts/ads/funeral_brand_keywords_2026_10_23.py"

# Each enabled ad asset → what the compare page must say for it (label, regex on the page's lower-case text).
FOUR = ("four singers £1,150", r"four singers.{0,80}?£1,150")
EIGHT = ("eight singers £2,000", r"eight singers.{0,80}?£2,000")
NO_VAT = ("no VAT", r"not vat-registered|no vat")
SHORT = ("short notice", r"short notice")
HYMNS = ("the choir sings every hymn", r"every hymn")
OX = ("Oxford-trained director", r"oxford[- ]trained|(trained|studied) at (the university of )?oxford|"
                                 r"graduate of (the university of )?oxford|oxford graduate")
RAM = ("Royal Academy", r"royal academy")
CLAIMS = {
    "Funeral Choir Hire in London": [("funeral", r"funeral"), ("London", r"london")],
    "Funeral Choir from £1,150": [FOUR],
    "Four to Twelve Voices": [("four singers", r"four singers"), ("twelve voices", r"twelve")],
    "Hymns Led by a Live Choir": [HYMNS],
    "Available at Short Notice": [SHORT],
    "No VAT Added, No Extras": [NO_VAT, ("nothing added", r"no fee added|nothing is added")],
    "Written Quote Before You Book": [("a written quote before booking", r"written quote|quote in writing")],
    "Coronation & BBC Proms Singers": [("Coronation", r"coronation"), ("BBC Proms", r"proms")],
    "Oxford-Trained Director": [OX],
    "Royal Academy Musicians": [RAM],
    "Rehearsals & Music Included": [("rehearsal", r"rehearsal"), ("sheet music", r"sheet music")],
    "Travel in London Included": [("travel in London included", r"travel within greater london")],
    "Choir for Funeral Services": [("funeral", r"funeral"), ("choir", r"choir")],
    "Quartet £1,150, Choir £2,000": [FOUR, EIGHT],
    "The London Choral Service": [("our name", r"the london choral service")],
    "A funeral choir from £1,150: four professional voices lead the hymns and sing 3 pieces.":
        [FOUR, HYMNS, ("three pieces", r"(three|3) performance pieces")],
    "Quintet £1,400, sextet £1,600, choir of eight £2,000. No VAT added and nothing on top.":
        [("quintet £1,400", r"(quintet|five singers).{0,80}?£1,400"),
         ("sextet £1,600", r"(sextet|six singers).{0,80}?£1,600"), EIGHT, NO_VAT],
    "We coordinate with your funeral director and venue, and can often help at short notice.":
        [("coordination with the funeral director and venue", r"coordinat\w* with your funeral director and the venue"),
         SHORT],
    "Singers from the Royal Academy and Royal College, chosen by an Oxford-trained director.":
        [RAM, ("Royal College", r"royal college"), OX,
         ("the director picks the singers", r"auditions every singer|picks the ensemble")],
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a redirect surfaces as an HTTPError with its 3xx code


def fetch_page(url):
    """(status, html) without following redirects."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "lcs-ads-check/1.0"})
    try:
        with opener.open(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


def page_text(src):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", src)
    t = re.sub(r"(?s)<!--.*?-->", " ", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).lower()


def shown(text, match):
    return f"[{text}]" if match == "EXACT" else (f'"{text}"' if match == "PHRASE" else text)


def gbp(micros):
    return f"£{micros / 1e6:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--keywords-only", action="store_true",
                    help="pause the broad variants and add the exact keywords, but leave every final URL as it is "
                         "(owner decision 23 Oct: the compare page lacks some of the ad's claims)")
    args = ap.parse_args()
    if BID > MAX_BID:
        raise SystemExit(f"bid {gbp(BID)} is above the approved {gbp(MAX_BID)}; nothing sent")

    # --- the landing page ----------------------------------------------------------
    status, src = fetch_page(COMPARE_URL)
    if status != 200:
        raise SystemExit(f"{COMPARE_URL} answered {status} (200 without a redirect required); nothing sent")
    canon = re.findall(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', src)
    if canon != [COMPARE_URL]:
        raise SystemExit(f"{COMPARE_URL} canonical is {canon}, not itself; nothing sent")
    text = page_text(src)

    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    # --- check the account matches what was approved --------------------------
    grp = q(f"SELECT campaign.name, ad_group.name FROM ad_group WHERE ad_group.id = {AD_GROUP_ID} "
            f"AND campaign.id = {FUNERAL}")
    if len(grp) != 1 or (grp[0].campaign.name, grp[0].ad_group.name) != (CAMPAIGN, AD_GROUP):
        raise SystemExit(f'ad group {AD_GROUP_ID} is not "{AD_GROUP}" in "{CAMPAIGN}"; nothing sent')

    ads = q("SELECT ad_group_ad.ad.id, ad_group_ad.ad.responsive_search_ad.headlines, "
            "ad_group_ad.ad.responsive_search_ad.descriptions, ad_group_ad.ad.responsive_search_ad.path1, "
            "ad_group_ad.ad.responsive_search_ad.path2 FROM ad_group_ad "
            f"WHERE ad_group.id = {AD_GROUP_ID} AND ad_group_ad.status = 'ENABLED'")
    if not ads:
        raise SystemExit("no enabled ad in the ad group; nothing sent")
    assets = []  # (ad id, kind, text)
    for a in ads:
        rsa = a.ad_group_ad.ad.responsive_search_ad
        assets += [(a.ad_group_ad.ad.id, "headline", h.text) for h in rsa.headlines]
        assets += [(a.ad_group_ad.ad.id, "description", d.text) for d in rsa.descriptions]
        assets += [(a.ad_group_ad.ad.id, "path", p) for p in (rsa.path1, rsa.path2) if p]
    named = [(i, k, t) for i, k, t in assets if any(m in t.lower().replace("-", " ") for m in BRAND_MARKS)
             or "londonfuneralsingers" in t.lower()]
    if named:
        for i, k, t in named:
            print(f'NAMES THE COMPETITOR: ad {i} {k} "{t}"')
        raise SystemExit("an enabled ad uses the competitor's brand name; nothing sent")
    lacking, unchecked = [], []
    for i, k, t in assets:
        if k == "path":
            continue
        if t not in CLAIMS:
            unchecked.append((i, k, t))
            continue
        miss = [label for label, rx in CLAIMS[t] if not re.search(rx, text, re.S)]
        if miss:
            lacking.append((i, k, t, miss))

    kws = q("SELECT ad_group_criterion.criterion_id, ad_group_criterion.resource_name, "
            "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, ad_group_criterion.status, "
            "ad_group_criterion.cpc_bid_micros, ad_group_criterion.final_urls FROM ad_group_criterion "
            f"WHERE ad_group.id = {AD_GROUP_ID} AND ad_group_criterion.type = 'KEYWORD' "
            "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED'")
    brand_rows = {r.ad_group_criterion.criterion_id: r.ad_group_criterion for r in kws
                  if any(m in r.ad_group_criterion.keyword.text.lower() for m in BRAND_MARKS)}
    exact_new = {k.keyword.text.lower(): k for k in brand_rows.values() if k.keyword.match_type.name == "EXACT"}
    reviewed = {i: k for i, k in brand_rows.items() if i in BRAND}
    if set(reviewed) != set(BRAND) or set(brand_rows) - set(BRAND) - {k.criterion_id for k in exact_new.values()}:
        raise SystemExit(f"the ad group's brand keywords {sorted(brand_rows)} differ from the reviewed "
                         f"{sorted(BRAND)}; nothing sent")
    for i, (t, m, _) in BRAND.items():
        k = reviewed[i]
        got = (k.keyword.text, k.keyword.match_type.name, k.status.name, k.cpc_bid_micros, list(k.final_urls))
        if got != (t, m, "ENABLED", BID, []):
            raise SystemExit(f"keyword {i} is {got}, not {(t, m, 'ENABLED', BID, [])}; nothing sent")

    to_add = [t for t in NEW_EXACT if t not in exact_new]
    negs = [(r.campaign_criterion.keyword.text, r.campaign_criterion.keyword.match_type.name) for r in q(
        "SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type FROM campaign_criterion "
        f"WHERE campaign.id = {FUNERAL} AND campaign_criterion.negative = TRUE "
        "AND campaign_criterion.type = 'KEYWORD'")]
    negs += [(r.ad_group_criterion.keyword.text, r.ad_group_criterion.keyword.match_type.name) for r in q(
        "SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type FROM ad_group_criterion "
        f"WHERE ad_group.id = {AD_GROUP_ID} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = TRUE")]
    hits = blocked(negs, [(t, "EXACT") for t in to_add])
    if hits:
        for nt, nm, kt, km in hits:
            print(f"BLOCKED: the existing negative {shown(nt, nm)} would block the new {shown(kt, km)}")
        raise SystemExit("a new keyword would be blocked by an existing negative; nothing sent")

    # --- build one atomic request ----------------------------------------------
    ops, changes = [], []  # changes: (resource, field, current → new, reason)
    for i, (t, m, after) in BRAND.items():
        k = reviewed[i]
        op = c.get_type("MutateOperation")
        u = op.ad_group_criterion_operation.update
        u.resource_name = k.resource_name
        if not args.keywords_only:
            u.final_urls.append(COMPARE_URL)
            op.ad_group_criterion_operation.update_mask.paths.append("final_urls")
        res = f'ad group "{AD_GROUP}" keyword {shown(t, m)} ({m.lower()}, {i})'
        if after == "PAUSED":
            u.status = E.AdGroupCriterionStatusEnum.PAUSED
            op.ad_group_criterion_operation.update_mask.paths.append("status")
            changes.append((res, "status", "enabled → paused", PAUSE_WHY))
        if not args.keywords_only:
            changes.append((res, "final URL", f"none (ad's funerals.html) → {COMPARE_URL}",
                            URL_WHY + ("" if after == "ENABLED" else "; set too so it lands there if re-enabled")))
        if op.ad_group_criterion_operation.update_mask.paths:
            ops.append(op)
    for t in to_add:
        op = c.get_type("MutateOperation")
        cr = op.ad_group_criterion_operation.create
        cr.ad_group = ga.ad_group_path(CUSTOMER_ID, AD_GROUP_ID)
        cr.status = E.AdGroupCriterionStatusEnum.ENABLED
        cr.keyword.text = t
        cr.keyword.match_type = E.KeywordMatchTypeEnum.EXACT
        cr.cpc_bid_micros = BID
        if not args.keywords_only:
            cr.final_urls.append(COMPARE_URL)
        ops.append(op)
        landing = "the ad's funerals.html" if args.keywords_only else COMPARE_URL
        changes.append((f'ad group "{AD_GROUP}" keyword [{t}] (exact, new)', "keyword",
                        f"none → added, max CPC {gbp(BID)}, enabled, final URL {landing}",
                        "exact brand search at the same £2.00, in place of the paused broad variants"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    print(f"LANDING PAGE {COMPARE_URL}")
    print("  answers 200 without a redirect; canonical is itself")
    print(f"  checked {len(assets)} asset(s) of enabled ad(s) {', '.join(str(a.ad_group_ad.ad.id) for a in ads)}: "
          "none names the competitor")
    if lacking or unchecked:
        n = sum(len(m) for *_, m in lacking)
        print(f"\n  !!! THE PAGE LACKS {n} CLAIM(S) FROM {len(lacking)} AD ASSET(S): a keyword landing here would show "
              "an ad promising what the page doesn't say !!!")
        for i, k, t, miss in lacking:
            print(f'  !!! ad {i} {k} "{t}"\n  !!!     page lacks: {"; ".join(miss)}')
        for i, k, t in unchecked:
            print(f'  !!! ad {i} {k} "{t}" is not on this script\'s checklist: check it against the page by hand')
        print()
    else:
        print("  states every claim and price in the enabled ad(s)\n")
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
    print(f'\nBrand keywords in "{AD_GROUP}", before → after:')
    for i, (t, m, after) in BRAND.items():
        k = reviewed[i]
        print(f"  {shown(t, m):<34} {m.lower():<6} {gbp(k.cpc_bid_micros)}  {k.status.name.lower()} → "
              f"{after.lower():<8} final URL " + ("unchanged" if args.keywords_only else "none → compare page"))
    for t in NEW_EXACT:
        if t in exact_new:
            k = exact_new[t]
            print(f"  {shown(t, 'EXACT'):<34} exact  {gbp(k.cpc_bid_micros)}  {k.status.name.lower()} (exists; skipped)")
        else:
            print(f"  {shown(t, 'EXACT'):<34} exact  {gbp(BID)}  none → enabled  final URL " + ("the ad's" if args.keywords_only else "compare page") + " (new)")
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    try:
        req = c.get_type("MutateGoogleAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.mutate_operations.extend(ops)
        req.validate_only = not args.apply
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    for res, field, what, why in reversed(changes):
        ads_log.append_row(f'| {now} | campaign "{CAMPAIGN}" {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
