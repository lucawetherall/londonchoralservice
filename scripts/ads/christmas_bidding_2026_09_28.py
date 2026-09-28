#!/usr/bin/env python3
"""Christmas carol campaign: pay more for bookers, less for browsers (owner's go-ahead, 28 Sep 2026).

1. Bidding: Maximise clicks (max £3.50 a click) → manual CPC, no enhanced CPC.
2. Every ad group's default bid → £2.50 (phrase match, price and cost searches, generic "carol singers").
3. Exact-match hiring and booking keywords → £4.00 (Google's top-of-page range for "hire carol singers"
   is £1.60–£3.91).
4. New keywords in "Hire carol singers": christmas choir hire / christmas choir for hire / hire a christmas
   choir (exact £4.00, phrase at the £2.50 default) and carol singers near me (exact and phrase, £2.50).
5. The "Hire carol singers" ad lands on carol-singers.html ("Hire carol singers") instead of the price page;
   the other three ad groups stay on christmas-pricing.html. The £1,150 price stays pinned in every ad.

Targeting stays Greater London only. Budget is untouched (set_budget.py does that). Nothing is removed.
Validate-only by default; --apply after approval, logged to logs/ads-changes.md.

    source .venv/bin/activate
    python scripts/ads/christmas_bidding_2026_09_28.py            # validate
    python scripts/ads/christmas_bidding_2026_09_28.py --apply    # after approval
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
CHRISTMAS = 24295921372
SCRIPT = "scripts/ads/christmas_bidding_2026_09_28.py"
DEFAULT_BID = 2_500_000
HIRING_BID = 4_000_000
HIRE_GROUP = "Hire carol singers"
PRICE_PAGE = "https://londonchoralservice.com/christmas-pricing.html"
HIRE_PAGE = "https://londonchoralservice.com/carol-singers.html"

HIRING_EXACT = {
    "carol singers for hire", "hire carol singers", "carol singers hire", "christmas carol singers for hire",
    "book carol singers", "hire carol singers london",
    "corporate carol singers", "carol singers for events", "carol singers for corporate events",
    "carol singers for office party", "carol singers for christmas party", "christmas party carol singers",
    "carol singers for a party", "carol singers for company",
    "carol singers for hotels", "hotel carol singers", "lobby carol singers", "carol singers for residents",
    "carol singers for reception", "carol singers for christmas reception",
    "christmas choir hire", "christmas choir for hire", "hire a christmas choir",
}
NEW_KEYWORDS = [  # (text, match type), all in HIRE_GROUP; exact hiring ones get HIRING_BID
    ("christmas choir hire", "EXACT"), ("christmas choir hire", "PHRASE"),
    ("christmas choir for hire", "EXACT"), ("christmas choir for hire", "PHRASE"),
    ("hire a christmas choir", "EXACT"), ("hire a christmas choir", "PHRASE"),
    ("carol singers near me", "EXACT"), ("carol singers near me", "PHRASE"),
]


def gbp(micros):
    return f"£{micros / 1e6:.2f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        ads_log.check_log()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    ops, changes = [], []

    def change(resource, field, cur, new, why):
        changes.append((resource, field, cur, new, why))

    camp = next(iter(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT campaign.name, campaign.resource_name, campaign.bidding_strategy_type, "
        f"campaign.target_spend.cpc_bid_ceiling_micros FROM campaign WHERE campaign.id = {CHRISTMAS}")))).campaign
    cres = f'campaign "{camp.name}" ({CHRISTMAS})'
    if camp.bidding_strategy_type.name != "MANUAL_CPC":
        o = c.get_type("MutateOperation")
        u = o.campaign_operation.update
        u.resource_name = camp.resource_name
        manual = c.get_type("ManualCpc")
        manual.enhanced_cpc_enabled = False
        c.copy_from(u.manual_cpc, manual)
        o.campaign_operation.update_mask.paths.append("manual_cpc.enhanced_cpc_enabled")
        ops.append(o)
        change(cres, "bidding", f"Maximise clicks (max {gbp(camp.target_spend.cpc_bid_ceiling_micros)} a click)",
               "manual CPC, no enhanced CPC",
               "Maximise clicks bids the same for browsers and bookers; manual bids pay more for hiring searches")

    groups = {}
    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT ad_group.name, ad_group.resource_name, ad_group.cpc_bid_micros FROM ad_group "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group.status = 'ENABLED'")):
        g = r.ad_group
        groups[g.name] = g.resource_name
        if g.cpc_bid_micros != DEFAULT_BID:
            o = c.get_type("MutateOperation")
            u = o.ad_group_operation.update
            u.resource_name = g.resource_name
            u.cpc_bid_micros = DEFAULT_BID
            o.ad_group_operation.update_mask.paths.append("cpc_bid_micros")
            ops.append(o)
            change(f'{cres} ad group "{g.name}"', "default max CPC", gbp(g.cpc_bid_micros), gbp(DEFAULT_BID),
                   "Default bid for phrase match, price searches and generic terms")
    if HIRE_GROUP not in groups:
        raise SystemExit(f'ad group "{HIRE_GROUP}" not found; nothing changed')

    existing = set()
    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT ad_group.name, ad_group_criterion.resource_name, ad_group_criterion.keyword.text, "
            "ad_group_criterion.keyword.match_type, ad_group_criterion.cpc_bid_micros FROM ad_group_criterion "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group_criterion.type = 'KEYWORD' "
            "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED'")):
        k = r.ad_group_criterion
        text, mt = k.keyword.text.lower(), k.keyword.match_type.name
        existing.add((r.ad_group.name, text, mt))
        if mt == "EXACT" and text in HIRING_EXACT and k.cpc_bid_micros != HIRING_BID:
            o = c.get_type("MutateOperation")
            u = o.ad_group_criterion_operation.update
            u.resource_name = k.resource_name
            u.cpc_bid_micros = HIRING_BID
            o.ad_group_criterion_operation.update_mask.paths.append("cpc_bid_micros")
            ops.append(o)
            change(f'{cres} keyword [{text}] in "{r.ad_group.name}"', "max CPC",
                   "ad group default" if not k.cpc_bid_micros else gbp(k.cpc_bid_micros), gbp(HIRING_BID),
                   "Exact hiring or booking search: worth more than a browsing click")

    for text, mt in NEW_KEYWORDS:
        if (HIRE_GROUP, text, mt) in existing:
            continue
        o = c.get_type("MutateOperation")
        k = o.ad_group_criterion_operation.create
        k.ad_group = groups[HIRE_GROUP]
        k.status = E.AdGroupCriterionStatusEnum.ENABLED
        k.keyword.text = text
        k.keyword.match_type = E.KeywordMatchTypeEnum[mt]
        bid = HIRING_BID if (mt == "EXACT" and text in HIRING_EXACT) else None
        if bid:
            k.cpc_bid_micros = bid
        ops.append(o)
        shown = f"[{text}]" if mt == "EXACT" else f'"{text}"'
        change(f'{cres} ad group "{HIRE_GROUP}"', "keyword", "absent",
               f"{shown} added, max CPC {gbp(bid) if bid else 'default ' + gbp(DEFAULT_BID)}",
               "Hiring search not yet covered (UK volume: 'carol singers near me' 170 in Nov, 320 in Dec)"
               if "near me" in text else "Choir-for-hire search at Christmas, not yet covered")

    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT ad_group.name, ad_group_ad.ad.resource_name, ad_group_ad.ad.final_urls FROM ad_group_ad "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.status = 'ENABLED' "
            f"AND ad_group.name = '{HIRE_GROUP}'")):
        urls = list(r.ad_group_ad.ad.final_urls)
        if urls == [HIRE_PAGE]:
            continue
        if urls != [PRICE_PAGE]:
            raise SystemExit(f'the "{HIRE_GROUP}" ad lands on {urls}, not the price page; not touching it')
        o = c.get_type("MutateOperation")
        a = o.ad_operation.update
        a.resource_name = r.ad_group_ad.ad.resource_name
        a.final_urls.append(HIRE_PAGE)
        o.ad_operation.update_mask.paths.append("final_urls")
        ops.append(o)
        change(f'{cres} ad in "{HIRE_GROUP}"', "final URL", "/christmas-pricing.html", "/carol-singers.html",
               "Landing-page experience rated below average; the hire page matches 'hire carol singers' "
               "searches. Price stays pinned in the ad")

    if not ops:
        print("Nothing to change.")
        return
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operations\n")
    for res, field, cur, new, why in changes:
        print(f"{res}\n   {field}: {cur} → {new}\n   reason: {why}\n")
    req = c.get_type("MutateGoogleAdsRequest")
    req.customer_id = CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = not args.apply
    try:
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("Google accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    for res, field, cur, new, why in reversed(changes):
        ads_log.append_row(f"| {now} | {res} | {field} | {cur} → {new} | {why} | `{SCRIPT}` |")
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
