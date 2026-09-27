#!/usr/bin/env python3
"""28 Sep 2026 change set: accurate sitelinks and stronger Christmas ads.

1. funeral expert campaign: pause the old "Get a Quote" sitelink, which promises
   a "Same-day personal response" (the site says within one working day; the
   matching callout was paused on 26 Sep), and link the accurate "Get a Quote"
   sitelink already used by wedding-leads.
2. Christmas campaign: link two more existing, already-approved sitelinks
   ("Get a Quote", "About Us"), as Google's ad-strength check asks (4 → 6).
3. Christmas ads: unpin the two headline-1 headlines in each ad. The
   "4 Carol Singers from £1,150" headline stays pinned to headline 2 and the
   price description stays pinned to description 1, so every ad still shows
   the minimum and the price. All four ads are rated Poor, and Google's advice
   for each is to unpin assets.

Edits existing ads in place (AdService) and campaign sitelinks
(CampaignAssetService). validate_only by default; nothing is deleted.

    .venv/bin/python scripts/ads/ad_strength_sitelinks_2026_09_28.py            # validate
    .venv/bin/python scripts/ads/ad_strength_sitelinks_2026_09_28.py --apply    # after approval
"""

import argparse
import datetime
import os
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
FUNERAL, CHRISTMAS = 23735776277, 24295921372
OLD_QUOTE, GOOD_QUOTE, ABOUT_US = 348071213215, 424677730988, 348796933586
PRICE_HEADLINE = "4 Carol Singers from £1,150"
PRICE_DESCRIPTION = "Four professional carol singers for up to two hours, breaks included. £1,150, all in."
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/ad_strength_sitelinks_2026_09_28.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    changes = []  # (campaign, resource, field, what, reason)

    # --- sitelinks -----------------------------------------------------------
    linked = {(r.campaign.id, r.asset.id): r.campaign_asset for r in q(
        "SELECT campaign.id, asset.id, campaign_asset.status, campaign_asset.resource_name FROM campaign_asset "
        f"WHERE asset.type = 'SITELINK' AND campaign.id IN ({FUNERAL}, {CHRISTMAS}) AND campaign_asset.status != 'REMOVED'")}
    texts = {r.asset.id: r.asset.sitelink_asset.link_text for r in q(
        f"SELECT asset.id, asset.sitelink_asset.link_text FROM asset WHERE asset.id IN ({OLD_QUOTE}, {GOOD_QUOTE}, {ABOUT_US})")}
    ca_ops = []
    old = linked.get((FUNERAL, OLD_QUOTE))
    if old and old.status.name == "ENABLED":
        op = c.get_type("CampaignAssetOperation")
        op.update.resource_name = old.resource_name
        op.update.status = E.AssetLinkStatusEnum.PAUSED
        op.update_mask.paths.append("status")
        ca_ops.append(op)
        changes.append(("funeral expert campaign", f'sitelink "Get a Quote" ({OLD_QUOTE})', "status", "enabled → paused",
                        "Promises a same-day response; the site says within one working day (callout paused 26 Sep)"))
    for camp, name, asset, why in (
            (FUNERAL, "funeral expert campaign", GOOD_QUOTE, "Accurate replacement: 'Reply within one working day'"),
            (CHRISTMAS, "Christmas carol singers – events 2026", GOOD_QUOTE, "Google's ad-strength check asks for 2 more sitelinks (4 → 6)"),
            (CHRISTMAS, "Christmas carol singers – events 2026", ABOUT_US, "Google's ad-strength check asks for 2 more sitelinks (4 → 6)")):
        if (camp, asset) in linked:
            continue
        op = c.get_type("CampaignAssetOperation")
        op.create.campaign = ga.campaign_path(CUSTOMER_ID, camp)
        op.create.asset = ga.asset_path(CUSTOMER_ID, asset)
        op.create.field_type = E.AssetFieldTypeEnum.SITELINK
        ca_ops.append(op)
        changes.append((name, f'sitelink "{texts.get(asset, asset)}" ({asset})', "link", "not linked → linked (existing asset)", why))

    # --- Christmas ads: unpin headline 1, keep the price pins ------------------
    ad_ops = []
    for r in q("SELECT ad_group.name, ad_group_ad.ad.resource_name, ad_group_ad.ad.responsive_search_ad.headlines, "
               "ad_group_ad.ad.responsive_search_ad.descriptions FROM ad_group_ad "
               f"WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.status = 'ENABLED'"):
        rsa = r.ad_group_ad.ad.responsive_search_ad
        h1 = [h.text for h in rsa.headlines if h.pinned_field == E.ServedAssetFieldTypeEnum.HEADLINE_1]
        if not h1:
            continue
        if PRICE_HEADLINE not in [h.text for h in rsa.headlines] or PRICE_DESCRIPTION not in [d.text for d in rsa.descriptions]:
            raise SystemExit(f'"{r.ad_group.name}" lacks the price headline or description; not touching it')
        op = c.get_type("AdOperation")
        ad = op.update
        ad.resource_name = r.ad_group_ad.ad.resource_name
        for h in rsa.headlines:
            t = c.get_type("AdTextAsset"); t.text = h.text
            if h.text == PRICE_HEADLINE:
                t.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_2
            ad.responsive_search_ad.headlines.append(t)
        for d in rsa.descriptions:
            t = c.get_type("AdTextAsset"); t.text = d.text
            if d.text == PRICE_DESCRIPTION:
                t.pinned_field = E.ServedAssetFieldTypeEnum.DESCRIPTION_1
            ad.responsive_search_ad.descriptions.append(t)
        op.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])
        ad_ops.append(op)
        changes.append(("Christmas carol singers – events 2026", f'ad in "{r.ad_group.name}"', "pins",
                        f'headline 1 pinned to {" / ".join(h1)} → unpinned (price stays pinned to headline 2 and description 1)',
                        "Ad strength Poor; Google advises unpinning. More combinations can lift Ad Rank (82% of impressions lost to rank)"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ca_ops)} sitelink operation(s), {len(ad_ops)} ad(s)\n")
    for camp, res, field, what, why in changes:
        print(f"• {camp} · {res} · {field}: {what}\n    reason: {why}")
    if not changes:
        print("Nothing to change.")
        return
    try:
        if ca_ops:
            req = c.get_type("MutateCampaignAssetsRequest")
            req.customer_id = CUSTOMER_ID
            req.operations.extend(ca_ops)
            req.validate_only = not args.apply
            c.get_service("CampaignAssetService").mutate_campaign_assets(request=req)
        if ad_ops:
            req = c.get_type("MutateAdsRequest")
            req.customer_id = CUSTOMER_ID
            req.operations.extend(ad_ops)
            req.validate_only = not args.apply
            c.get_service("AdService").mutate_ads(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    rows = "".join(f'| {now} | campaign "{camp}" {res} | {field} | {what} | {why} | `{SCRIPT}` |\n'
                   for camp, res, field, what, why in changes)
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
