#!/usr/bin/env python3
"""19 Oct 2026 change set: phrase-match bids in "Hire carol singers" to £3.50.

The Christmas campaign loses 55% of its impression share to ad rank and spends about
£2.50/day of its £8 budget. Its phrase-match keywords in "Hire carol singers" have
no bid of their own, so they bid the ad group default of £2.50, below the £3.50–£4
on the exact matches. This sets each such phrase keyword's own bid to £3.50.

Only enabled phrase-match keywords in that ad group whose own bid is unset (0) are
touched; any phrase keyword already carrying a bid keeps it. Exact-match keywords,
the ad group default, the budget and the other ad groups are left alone. Refuses a
bid above £3.50. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/christmas_phrase_bids_2026_10_19.py            # validate
    python scripts/ads/christmas_phrase_bids_2026_10_19.py --apply    # after approval
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ads_log import append_row, log_path  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
CHRISTMAS = 24295921372
CAMPAIGN = "Christmas carol singers – events 2026"
AD_GROUP = "Hire carol singers"
NEW_BID = 3_500_000
MAX_BID = 3_500_000
SCRIPT = "scripts/ads/christmas_phrase_bids_2026_10_19.py"


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

    groups = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT ad_group.id, ad_group.cpc_bid_micros FROM ad_group "
        f"WHERE campaign.id = {CHRISTMAS} AND ad_group.name = '{AD_GROUP}' AND ad_group.status = 'ENABLED'")))
    if len(groups) != 1:
        raise SystemExit(f'ad group "{AD_GROUP}" not found exactly once; nothing sent')
    default = groups[0].ad_group.cpc_bid_micros
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT ad_group_criterion.resource_name, ad_group_criterion.keyword.text, "
        "ad_group_criterion.cpc_bid_micros FROM ad_group_criterion "
        f"WHERE ad_group.id = {groups[0].ad_group.id} AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED' "
        "AND ad_group_criterion.keyword.match_type = 'PHRASE'")))

    ops, changes, kept = [], [], []
    for r in sorted(rows, key=lambda r: r.ad_group_criterion.keyword.text):
        k = r.ad_group_criterion
        if k.cpc_bid_micros:
            kept.append(f'"{k.keyword.text}" keeps its own {gbp(k.cpc_bid_micros)}')
            continue
        op = c.get_type("AdGroupCriterionOperation")
        op.update.resource_name = k.resource_name
        op.update.cpc_bid_micros = NEW_BID
        op.update_mask.paths.append("cpc_bid_micros")
        ops.append(op)
        changes.append((f'keyword "{k.keyword.text}" (phrase)', "max CPC",
                        f"{gbp(default)} (ad group default) → {gbp(NEW_BID)}",
                        "55% of impressions lost to ad rank; exact matches already bid £3.50–£4"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f' — {len(ops)} keyword bid(s) in "{AD_GROUP}"\n')
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
    for line in kept:
        print(f"  unchanged: {line}")
    if not ops:
        print("Nothing to change.")
        return
    if args.apply:
        log_path()  # refuse before changing anything if the log can't be written
    try:
        req = c.get_type("MutateAdGroupCriteriaRequest")
        req.customer_id = CUSTOMER_ID
        req.operations.extend(ops)
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
        append_row(f'| {now} | campaign "{CAMPAIGN}" ad group "{AD_GROUP}" {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
