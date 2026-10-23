#!/usr/bin/env python3
"""23 Oct 2026 (third change set): exact keywords in "Carol singer prices" £2.50 → £4.

keyword_tidy_2026_10_23.py raised the group's phrase keywords to £3.50, leaving its exact keywords on the
£2.50 ad group default, below their own phrase twins. Every other Christmas exact keyword bids £4. That
script's log rows also gave the reason "its exact twin bids £4", which was wrong for this group; these rows
correct it. The group is rarely served (low search volume), so nothing is spent until those searches appear.

    .venv/bin/python scripts/ads/christmas_price_exact_bids_2026_10_23.py            # validate
    .venv/bin/python scripts/ads/christmas_price_exact_bids_2026_10_23.py --apply    # after approval
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
CHRISTMAS = 24295921372
CAMPAIGN = "Christmas carol singers – events 2026"
GROUP = "Carol singer prices"
NEW_BID = 4_000_000
EXPECTED = 7
SCRIPT = "scripts/ads/christmas_price_exact_bids_2026_10_23.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT ad_group_criterion.resource_name, ad_group_criterion.keyword.text, "
        "ad_group_criterion.cpc_bid_micros, ad_group_criterion.effective_cpc_bid_micros FROM ad_group_criterion "
        f"WHERE campaign.id = {CHRISTMAS} AND ad_group.name = '{GROUP}' AND ad_group_criterion.type = 'KEYWORD' "
        "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED' "
        "AND ad_group_criterion.keyword.match_type = 'EXACT'")))
    todo = [r for r in rows if r.ad_group_criterion.effective_cpc_bid_micros < NEW_BID]
    if len(rows) != EXPECTED:
        raise SystemExit(f'expected {EXPECTED} enabled exact keywords in "{GROUP}", found {len(rows)}; nothing sent')
    ops, changes = [], []
    for r in todo:
        op = c.get_type("MutateOperation")
        u = op.ad_group_criterion_operation.update
        u.resource_name = r.ad_group_criterion.resource_name
        u.cpc_bid_micros = NEW_BID
        op.ad_group_criterion_operation.update_mask.paths.append("cpc_bid_micros")
        ops.append(op)
        cur = r.ad_group_criterion.effective_cpc_bid_micros / 1e6
        src = "" if r.ad_group_criterion.cpc_bid_micros else " (ad group default)"
        changes.append((f'ad group "{GROUP}" keyword "{r.ad_group_criterion.keyword.text}" (exact)',
                        f"£{cur:.2f}{src} → £4.00",
                        "was below its own phrase twin (£3.50); every other Christmas exact keyword bids £4. "
                        "Corrects keyword_tidy_2026_10_23's reason for this group, which said the exact twin bid £4"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for res, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · max CPC: {what}\n    reason: {why}")
    if not ops:
        print("Nothing to change.")
        return
    if args.apply:
        check_log()
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
    for res, what, why in reversed(changes):
        append_row(f'| {now} | campaign "{CAMPAIGN}" {res} | max CPC | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
