#!/usr/bin/env python3
"""Second pass of the 28 September 2026 account review: three settings the consistency check found.

1. Final URL suffix: wedding-leads carries a full page URL where query parameters belong (so every ad click
   lands on weddings.html?https://londonchoralservice.com/weddings.html); funeral has none. Both get the
   utm_source/medium/campaign tags the Christmas campaign already uses, so GA4 names the campaign even when
   the click ID is lost.
2. Business logo: the logo asset that already serves on wedding-leads (eligible, 1356×1346) is linked to the
   funeral and Christmas campaigns too. Nothing new is uploaded.
3. wedding-leads observes Google's "Wedding Planning" in-market audience with no bid adjustment; under manual
   CPC a +20% adjustment pays a little more for people Google sees actively planning a wedding.

Validate-only by default; --apply after approval, logged to logs/ads-changes.md. Nothing is removed.

    source .venv/bin/activate
    python scripts/ads/account_tidy_2026_09_28.py            # validate
    python scripts/ads/account_tidy_2026_09_28.py --apply    # after approval
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
FUNERAL, WEDDING, CHRISTMAS = 23735776277, 23739971001, 24295921372
SCRIPT = "scripts/ads/account_tidy_2026_09_28.py"
SUFFIX = {FUNERAL: "utm_source=google&utm_medium=cpc&utm_campaign=funeral-expert",
          WEDDING: "utm_source=google&utm_medium=cpc&utm_campaign=wedding-leads"}
LOGO = "customers/8733881378/assets/336552898779"
WEDDING_AUDIENCE = "customers/8733881378/campaignCriteria/23739971001~61610668640"
AUDIENCE_MODIFIER = 1.2


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

    names = {}
    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT campaign.id, campaign.name, campaign.resource_name, campaign.final_url_suffix FROM campaign "
            f"WHERE campaign.id IN ({FUNERAL}, {WEDDING}, {CHRISTMAS})")):
        k = r.campaign
        names[k.id] = f'campaign "{k.name}" ({k.id})'
        if k.id in SUFFIX and k.final_url_suffix != SUFFIX[k.id]:
            o = c.get_type("MutateOperation")
            u = o.campaign_operation.update
            u.resource_name = k.resource_name
            u.final_url_suffix = SUFFIX[k.id]
            o.campaign_operation.update_mask.paths.append("final_url_suffix")
            ops.append(o)
            changes.append((names[k.id], "final URL suffix", repr(k.final_url_suffix) if k.final_url_suffix else "none",
                            SUFFIX[k.id],
                            "A page URL is not a suffix; every wedding click landed with it stuck on the end. "
                            "Both campaigns now carry the utm tags the Christmas campaign uses" if k.id == WEDDING
                            else "The utm tags the Christmas campaign uses, so GA4 names the campaign without a click ID"))
    if len(names) != 3:
        raise SystemExit("not all three campaigns found; nothing changed")

    linked = {r.campaign.id for r in ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT campaign.id, campaign_asset.status FROM campaign_asset WHERE campaign_asset.field_type = 'BUSINESS_LOGO' "
        f"AND asset.resource_name = '{LOGO}' AND campaign_asset.status != 'REMOVED'"))}
    for cid in (FUNERAL, CHRISTMAS):
        if cid in linked:
            continue
        o = c.get_type("MutateOperation")
        ca = o.campaign_asset_operation.create
        ca.campaign = ga.campaign_path(CUSTOMER_ID, cid)
        ca.asset = LOGO
        ca.field_type = E.AssetFieldTypeEnum.BUSINESS_LOGO
        ops.append(o)
        changes.append((names[cid], "business logo", "none", "the logo already serving on wedding-leads",
                        "Free ad real estate; the same eligible asset, nothing new uploaded"))

    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT campaign.id, campaign_criterion.resource_name, campaign_criterion.bid_modifier, "
            "campaign_criterion.user_interest.user_interest_category FROM campaign_criterion "
            f"WHERE campaign_criterion.resource_name = '{WEDDING_AUDIENCE}'")):
        cc = r.campaign_criterion
        if abs(cc.bid_modifier - AUDIENCE_MODIFIER) < 0.001:
            continue
        o = c.get_type("MutateOperation")
        u = o.campaign_criterion_operation.update
        u.resource_name = cc.resource_name
        u.bid_modifier = AUDIENCE_MODIFIER
        o.campaign_criterion_operation.update_mask.paths.append("bid_modifier")
        ops.append(o)
        changes.append((f'{names[WEDDING]} audience "Wedding Planning" (in-market, observation)', "bid adjustment",
                        f"{'none' if not cc.bid_modifier else f'{(cc.bid_modifier - 1) * 100:+.0f}%'}", "+20%",
                        "Manual CPC honours it: a little more for people Google sees actively planning a wedding, "
                        "nobody excluded"))

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
