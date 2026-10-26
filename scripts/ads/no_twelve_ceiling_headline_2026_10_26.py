#!/usr/bin/env python3
"""26 Oct 2026 change set: replace the headline "Four to Twelve Voices" in the two live ads that carry it.

The owner supplies choirs larger than twelve (16 and 24 voices are on the Christmas price list since #396, and a
24-voice quote went out recently), and the site no longer gives twelve as a ceiling (#398). Two enabled ads still
say "Four to Twelve Voices": the 23 Oct wedding ad (829372414723) and the 26 Oct funeral ad (829543104168). Each
gets "Four Voices or More" in its place (funerals.html and weddings.html: "Four voices or more ..."). The other
headlines and descriptions are resent unchanged; neither ad has pins. The two paused 2025 ads are left alone.

    source .venv/bin/activate
    python scripts/ads/no_twelve_ceiling_headline_2026_10_26.py            # validate
    python scripts/ads/no_twelve_ceiling_headline_2026_10_26.py --apply    # after approval
"""

import argparse
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ads_log import append_row, check_log  # noqa: E402
from funeral_rsa_2026_10_26 import check_text  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
ADS = {829372414723: (23739971001, "wedding-leads"), 829543104168: (23735776277, "funeral expert campaign")}
OLD, NEW = "Four to Twelve Voices", "Four Voices or More"
SCRIPT = "scripts/ads/no_twelve_ceiling_headline_2026_10_26.py"
WHY = ("we supply choirs larger than twelve (16 and 24 voices on the Christmas price list); the site no longer "
       "gives twelve as a ceiling")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_text(NEW, 30, "headline")
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    ids = ",".join(str(a) for a in ADS)
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT campaign.id, ad_group_ad.ad.id, ad_group_ad.ad.responsive_search_ad.headlines, "
        "ad_group_ad.ad.responsive_search_ad.descriptions FROM ad_group_ad "
        f"WHERE ad_group_ad.ad.id IN ({ids}) AND ad_group_ad.status = 'ENABLED'")))
    if len(rows) != len(ADS):
        raise SystemExit("not every ad is enabled and found; nothing sent")

    ops, changes = [], []
    for r in rows:
        ad_id, rsa = r.ad_group_ad.ad.id, r.ad_group_ad.ad.responsive_search_ad
        campaign_id, campaign = ADS[ad_id]
        if r.campaign.id != campaign_id:
            raise SystemExit(f"ad {ad_id} is not in campaign {campaign_id}; nothing sent")
        heads = [h.text for h in rsa.headlines]
        if NEW in heads and OLD not in heads:
            print(f"ad {ad_id} already carries \"{NEW}\". Skipped.")
            continue
        if OLD not in heads:
            raise SystemExit(f"ad {ad_id} does not carry \"{OLD}\"; nothing sent")
        if any(h.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN") for h in rsa.headlines):
            raise SystemExit(f"ad {ad_id} has pinned headlines; this script resends them unpinned; nothing sent")
        op = c.get_type("AdOperation")
        ad = op.update
        ad.resource_name = ga.ad_path(CUSTOMER_ID, ad_id)
        for h in heads:
            t = c.get_type("AdTextAsset"); t.text = NEW if h == OLD else h
            ad.responsive_search_ad.headlines.append(t)
        for d in rsa.descriptions:
            t = c.get_type("AdTextAsset"); t.text = d.text
            ad.responsive_search_ad.descriptions.append(t)
        op.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])
        ops.append(op)
        changes.append(f'campaign "{campaign}" ad {ad_id} in "Ad group 1"')

    if not ops:
        print("Nothing to change.")
        return
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} ad(s)\n")
    for res in changes:
        print(f'• {res}\n    headline: "{OLD}" → "{NEW}" ({len(NEW)} chars, unpinned as before)\n    reason: {WHY}')
    if args.apply:
        check_log()
    try:
        req = c.get_type("MutateAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.operations.extend(ops)
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
    for res in reversed(changes):
        append_row(f'| {now} | {res} | headline | "{OLD}" → "{NEW}" ({len(NEW)} chars, unpinned as before) '
                   f"| {WHY} | `{SCRIPT}` |")
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
