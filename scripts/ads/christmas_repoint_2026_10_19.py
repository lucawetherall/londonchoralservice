#!/usr/bin/env python3
"""19 Oct 2026 change set: point the Christmas campaign at the new landing pages.

carol-singers.html now forwards to christmas.html (the new carol singers landing
page), and church carol services moved to christmas-carol-services.html.

1. Ad 825999587211 ("Hire carol singers"): final URL carol-singers.html →
   christmas.html. Headlines, descriptions, paths and tracking stay as they are
   (the update mask names final_urls only).
2. Sitelink "Carol Services" (424859628369, linked to this campaign only):
   final URL christmas.html → christmas-carol-services.html. If Google won't
   change the asset's URL, the script instead creates "Church Carol Services" →
   that URL, links it, and pauses the old link (--fallback).
3. Sitelink "Hire Carol Singers" (424775770945): pause its link on this campaign;
   after (1) it would repeat the ad's own final URL.

The other ad groups, the budget and the bids are untouched. Nothing is deleted.
Every value is checked against the account before anything is sent.

    .venv/bin/python scripts/ads/christmas_repoint_2026_10_19.py               # validate
    .venv/bin/python scripts/ads/christmas_repoint_2026_10_19.py --apply       # after approval
    add --fallback to either if Google refuses the sitelink URL change
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
AD_ID = 825999587211
CAROL_SERVICES, HIRE_CAROL_SINGERS = 424859628369, 424775770945
SITE = "https://londonchoralservice.com/"
OLD_AD_URL, NEW_AD_URL = SITE + "carol-singers.html", SITE + "christmas.html"
OLD_CS_URL, NEW_CS_URL = SITE + "christmas.html", SITE + "christmas-carol-services.html"
SCRIPT = "scripts/ads/christmas_repoint_2026_10_19.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--fallback", action="store_true",
                    help="create a new 'Church Carol Services' sitelink instead of changing the old one's URL")
    args = ap.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    # --- check the account matches what was approved --------------------------
    ads = q("SELECT ad_group.name, ad_group_ad.ad.resource_name, ad_group_ad.ad.final_urls FROM ad_group_ad "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.ad.id = {AD_ID}")
    if len(ads) != 1:
        raise SystemExit(f"ad {AD_ID} not found in the Christmas campaign; nothing sent")
    ad = ads[0]
    if list(ad.ad_group_ad.ad.final_urls) != [OLD_AD_URL]:
        raise SystemExit(f"ad {AD_ID} final URL is {list(ad.ad_group_ad.ad.final_urls)}, not {OLD_AD_URL}; nothing sent")

    links = {r.asset.id: r for r in q(
        "SELECT campaign.id, campaign_asset.resource_name, campaign_asset.status, asset.id, asset.resource_name, "
        "asset.final_urls, asset.sitelink_asset.link_text, asset.sitelink_asset.description1, "
        "asset.sitelink_asset.description2 FROM campaign_asset "
        f"WHERE campaign.id = {CHRISTMAS} AND asset.type = 'SITELINK' AND campaign_asset.status != 'REMOVED'")}
    for a in (CAROL_SERVICES, HIRE_CAROL_SINGERS):
        if a not in links or links[a].campaign_asset.status.name != "ENABLED":
            raise SystemExit(f"sitelink {a} is not enabled on the Christmas campaign; nothing sent")
    cs = links[CAROL_SERVICES]
    if list(cs.asset.final_urls) != [OLD_CS_URL]:
        raise SystemExit(f"sitelink {CAROL_SERVICES} URL is {list(cs.asset.final_urls)}, not {OLD_CS_URL}; nothing sent")
    shared = [r.campaign.id for r in q(
        f"SELECT campaign.id FROM campaign_asset WHERE asset.id = {CAROL_SERVICES} AND campaign_asset.status != 'REMOVED'")]
    if set(shared) != {CHRISTMAS}:
        raise SystemExit(f"sitelink {CAROL_SERVICES} is also linked to {shared}; changing it would reach them; nothing sent")

    # --- build one atomic request ----------------------------------------------
    ops, changes = [], []  # changes: (resource, field, current → new, reason)

    op = c.get_type("MutateOperation")
    op.ad_operation.update.resource_name = ad.ad_group_ad.ad.resource_name
    op.ad_operation.update.final_urls.append(NEW_AD_URL)
    op.ad_operation.update_mask.paths.append("final_urls")
    ops.append(op)
    changes.append((f'ad {AD_ID} in "{ad.ad_group.name}"', "final URL", f"{OLD_AD_URL} → {NEW_AD_URL}",
                    "carol-singers.html now forwards to christmas.html, the new carol singers landing page"))

    if not args.fallback:
        op = c.get_type("MutateOperation")
        op.asset_operation.update.resource_name = cs.asset.resource_name
        op.asset_operation.update.final_urls.append(NEW_CS_URL)
        op.asset_operation.update_mask.paths.append("final_urls")
        ops.append(op)
        changes.append((f'sitelink "Carol Services" ({CAROL_SERVICES})', "final URL", f"{OLD_CS_URL} → {NEW_CS_URL}",
                        "church carol services moved to christmas-carol-services.html"))
    else:
        tmp = ga.asset_path(CUSTOMER_ID, "-1")
        op = c.get_type("MutateOperation")
        new = op.asset_operation.create
        new.resource_name = tmp
        new.final_urls.append(NEW_CS_URL)
        new.sitelink_asset.link_text = "Church Carol Services"
        new.sitelink_asset.description1 = cs.asset.sitelink_asset.description1
        new.sitelink_asset.description2 = cs.asset.sitelink_asset.description2
        ops.append(op)
        op = c.get_type("MutateOperation")
        op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, CHRISTMAS)
        op.campaign_asset_operation.create.asset = tmp
        op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.SITELINK
        ops.append(op)
        op = c.get_type("MutateOperation")
        op.campaign_asset_operation.update.resource_name = cs.campaign_asset.resource_name
        op.campaign_asset_operation.update.status = E.AssetLinkStatusEnum.PAUSED
        op.campaign_asset_operation.update_mask.paths.append("status")
        ops.append(op)
        changes.append(('sitelink "Church Carol Services" (new)', "create + link",
                        f"none → linked, {NEW_CS_URL}, descriptions copied from the old link",
                        "Google refused to change the old sitelink's URL; church carol services moved"))
        changes.append((f'sitelink "Carol Services" ({CAROL_SERVICES})', "link status", "enabled → paused",
                        "replaced by \"Church Carol Services\""))

    op = c.get_type("MutateOperation")
    op.campaign_asset_operation.update.resource_name = links[HIRE_CAROL_SINGERS].campaign_asset.resource_name
    op.campaign_asset_operation.update.status = E.AssetLinkStatusEnum.PAUSED
    op.campaign_asset_operation.update_mask.paths.append("status")
    ops.append(op)
    changes.append((f'sitelink "Hire Carol Singers" ({HIRE_CAROL_SINGERS})', "link status", "enabled → paused",
                    "it now matches the ad's own final URL (christmas.html); christmas-pricing.html is already a sitelink"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
    if args.apply:
        log_path()  # refuse before changing anything if the log can't be written
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
        append_row(f'| {now} | campaign "{CAMPAIGN}" {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
