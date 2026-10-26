#!/usr/bin/env python3
"""26 Oct 2026 change set: a two-week bid test on "christmas carol singers london" (exact) in "Hire carol singers".

The keyword bids £3.50 against a first-page estimate of £5.46 (top of page the same), Quality Score 4, and loses
44% of its impressions to ad rank (30 days to 26 Oct: 138 impressions, 5 clicks, £17.35). Budget does not bind
(5% of the campaign's impressions lost to budget at £5 a day), so rank is what holds it back. This raises the one
keyword to £5.50, just above the estimate. "carol singers london" (phrase, first page £9.46) is not raised.

Plan: docs/superpowers/plans/2026-10-26-growth-handoff.md, WP1h, brought forward by the owner on 26 Oct rather
than waiting for a second Christmas ad (dropped: carol-singers.html is a noindex redirect to christmas.html).

Test: ends 9 Nov 2026. Success is an A or B enquiry from the Christmas campaign in the pipeline (section 9b of
the Monday report). Without one, the bid goes back to £3.50 by a new script, after approval.

Refuses a bid above £5.50. Budget, other keywords and ad groups are untouched. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/christmas_london_bid_test_2026_10_26.py            # validate
    python scripts/ads/christmas_london_bid_test_2026_10_26.py --apply    # after approval
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ads_log import append_row, check_log  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
CHRISTMAS, CAMPAIGN = 24295921372, "Christmas carol singers – events 2026"
AD_GROUP_ID, AD_GROUP = 198315037857, "Hire carol singers"
KEYWORD_ID, KEYWORD = 433540298868, "christmas carol singers london"
OLD_BID, NEW_BID, MAX_BID = 3_500_000, 5_500_000, 5_500_000
SCRIPT = "scripts/ads/christmas_london_bid_test_2026_10_26.py"
WHY = ("bid below the £5.46 first-page estimate, QS 4, 44% of impressions lost to ad rank; budget does not bind. "
       "Two-week test to 9 Nov: kept only with an A or B enquiry from the campaign")


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
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT campaign.id, ad_group.name, ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, "
        "ad_group_criterion.status, ad_group_criterion.cpc_bid_micros FROM ad_group_criterion "
        f"WHERE ad_group.id = {AD_GROUP_ID} AND ad_group_criterion.criterion_id = {KEYWORD_ID}")))
    if len(rows) != 1:
        raise SystemExit(f"keyword {KEYWORD_ID} not found exactly once; nothing sent")
    r = rows[0]
    k = r.ad_group_criterion
    if (r.campaign.id, r.ad_group.name, k.keyword.text, k.keyword.match_type.name, k.status.name) != (
            CHRISTMAS, AD_GROUP, KEYWORD, "EXACT", "ENABLED"):
        raise SystemExit(f"keyword {KEYWORD_ID} is not the enabled exact \"{KEYWORD}\" in {AD_GROUP}; nothing sent")
    if k.cpc_bid_micros == NEW_BID:
        print(f"\"{KEYWORD}\" already bids {gbp(NEW_BID)}. Nothing to change.")
        return
    if k.cpc_bid_micros != OLD_BID:
        raise SystemExit(f"\"{KEYWORD}\" bids {gbp(k.cpc_bid_micros)}, not {gbp(OLD_BID)}; nothing sent")

    op = c.get_type("AdGroupCriterionOperation")
    op.update.resource_name = ga.ad_group_criterion_path(CUSTOMER_ID, AD_GROUP_ID, KEYWORD_ID)
    op.update.cpc_bid_micros = NEW_BID
    op.update_mask.paths.append("cpc_bid_micros")
    res = f'campaign "{CAMPAIGN}" ad group "{AD_GROUP}" keyword "{KEYWORD}" (exact, {KEYWORD_ID})'
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — 1 keyword bid\n\n• {res}\n"
          f"    max CPC: {gbp(OLD_BID)} → {gbp(NEW_BID)}\n    reason: {WHY}")
    if args.apply:
        check_log()
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
        print("\nGoogle accepted the operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    append_row(f"| {now} | {res} | max CPC | {gbp(OLD_BID)} → {gbp(NEW_BID)} | {WHY} | `{SCRIPT}` |")
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
