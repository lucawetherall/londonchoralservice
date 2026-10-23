#!/usr/bin/env python3
"""23 Oct 2026 change set 6: wedding-leads (23739971001) keyword "wedding choir" phrase, max CPC £3.00 → £4.00.

Google's first-page estimate for it is £3.72 and top of page £5.12; 64% of its impressions are lost to ad rank.
The exact [wedding choir] keeps its own £4.50, so the phrase still bids below it. Only this one keyword is
touched; the script refuses a bid above £4.00 and refuses if the keyword isn't the enabled phrase "wedding choir"
at £3.00. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/wedding_choir_bid_2026_10_23.py            # validate
    python scripts/ads/wedding_choir_bid_2026_10_23.py --apply    # after approval
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
WEDDING = 23739971001
CAMPAIGN = "wedding-leads"
KW_ID, KW_TEXT = 311485562869, "wedding choir"
OLD_BID, NEW_BID, MAX_BID = 3_000_000, 4_000_000, 4_000_000
SCRIPT = "scripts/ads/wedding_choir_bid_2026_10_23.py"


def gbp(micros):
    return f"£{micros / 1e6:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if NEW_BID > MAX_BID:
        raise SystemExit(f"bid {gbp(NEW_BID)} is above the approved {gbp(MAX_BID)}; nothing sent")
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    camp = q(f"SELECT campaign.name FROM campaign WHERE campaign.id = {WEDDING}")
    if len(camp) != 1 or camp[0].campaign.name != CAMPAIGN:
        raise SystemExit(f'campaign {WEDDING} is not "{CAMPAIGN}"; nothing sent')
    rows = q("SELECT ad_group.name, ad_group_criterion.resource_name, ad_group_criterion.criterion_id, "
             "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, ad_group_criterion.status, "
             "ad_group_criterion.cpc_bid_micros FROM ad_group_criterion "
             f"WHERE campaign.id = {WEDDING} AND ad_group_criterion.type = 'KEYWORD' "
             "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status != 'REMOVED'")
    hit = [r for r in rows if r.ad_group_criterion.criterion_id == KW_ID]
    if len(hit) != 1:
        raise SystemExit(f"keyword {KW_ID} not found in the campaign; nothing sent")
    k = hit[0].ad_group_criterion
    if (k.keyword.text.lower(), k.keyword.match_type.name, k.status.name, k.cpc_bid_micros) != \
            (KW_TEXT, "PHRASE", "ENABLED", OLD_BID):
        raise SystemExit(f"keyword {KW_ID} is {k.keyword.text!r} {k.keyword.match_type.name} {k.status.name} at "
                         f"{gbp(k.cpc_bid_micros)}, not \"{KW_TEXT}\" PHRASE ENABLED at {gbp(OLD_BID)}; nothing sent")
    exact = [r.ad_group_criterion for r in rows if r.ad_group_criterion.keyword.text.lower() == KW_TEXT
             and r.ad_group_criterion.keyword.match_type.name == "EXACT"]

    op = c.get_type("AdGroupCriterionOperation")
    op.update.resource_name = k.resource_name
    op.update.cpc_bid_micros = NEW_BID
    op.update_mask.paths.append("cpc_bid_micros")
    changes = [(f'ad group "{hit[0].ad_group.name}" keyword "{KW_TEXT}" (phrase, {KW_ID})', "max CPC",
                f"{gbp(OLD_BID)} → {gbp(NEW_BID)}",
                "Google first-page estimate £3.72, top of page £5.12; 64% of impressions lost to ad rank")]

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + " — 1 keyword bid\n")
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
    for e in exact:
        print(f"  unchanged: [{e.keyword.text}] (exact) {e.status.name.lower()} at {gbp(e.cpc_bid_micros)}")
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    try:
        req = c.get_type("MutateAdGroupCriteriaRequest")
        req.customer_id = CUSTOMER_ID
        req.operations.append(op)
        req.validate_only = not args.apply
        c.get_service("AdGroupCriterionService").mutate_ad_group_criteria(request=req)
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
