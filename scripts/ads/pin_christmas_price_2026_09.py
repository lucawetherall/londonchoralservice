#!/usr/bin/env python3
"""Pin the minimum booking and price into every Christmas carol ad, so no one
clicks without seeing "4 Carol Singers from £1,150".

Headline 2 is pinned to the price headline; description 1 is pinned to the
price description. Headline 1 keeps each ad group's own pinned headlines.
Edits the existing RSAs in place (AdService), validate_only by default.

    source .venv/bin/activate
    python scripts/ads/pin_christmas_price_2026_09.py            # validate
    python scripts/ads/pin_christmas_price_2026_09.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
CHRISTMAS = 24295921372
PRICE_HEADLINE = "4 Carol Singers from £1,150"
PRICE_DESCRIPTION = "Four professional carol singers for up to two hours, breaks included. £1,150, all in."
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/pin_christmas_price_2026_09.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    c = GoogleAdsClient.load_from_storage()
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    ops, changes = [], []
    for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT ad_group.name, ad_group_ad.ad.resource_name, ad_group_ad.ad.responsive_search_ad.headlines, "
            "ad_group_ad.ad.responsive_search_ad.descriptions FROM ad_group_ad "
            f"WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.status = 'ENABLED'")):
        rsa = r.ad_group_ad.ad.responsive_search_ad
        texts = [h.text for h in rsa.headlines]
        dtexts = [d.text for d in rsa.descriptions]
        if PRICE_HEADLINE not in texts or PRICE_DESCRIPTION not in dtexts:
            raise SystemExit(f'"{r.ad_group.name}" is missing the price headline or description; not touching it')
        op = c.get_type("AdOperation")
        ad = op.update
        ad.resource_name = r.ad_group_ad.ad.resource_name
        for h in rsa.headlines:
            t = c.get_type("AdTextAsset"); t.text = h.text
            if h.text == PRICE_HEADLINE:
                t.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_2
            elif h.pinned_field == E.ServedAssetFieldTypeEnum.HEADLINE_1:
                t.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1
            ad.responsive_search_ad.headlines.append(t)
        for d in rsa.descriptions:
            t = c.get_type("AdTextAsset"); t.text = d.text
            if d.text == PRICE_DESCRIPTION:
                t.pinned_field = E.ServedAssetFieldTypeEnum.DESCRIPTION_1
            ad.responsive_search_ad.descriptions.append(t)
        op.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])
        ops.append(op)
        changes.append((f'ad in "{r.ad_group.name}"', "pins",
                        f'price headline unpinned → pinned to headline 2; price description unpinned → pinned to description 1'))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} ads\n")
    for res, field, what in changes:
        print(f"• {res} · {field}: {what}")
    svc = c.get_service("AdService")
    try:
        req = c.get_type("MutateAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.operations.extend(ops)
        req.validate_only = not args.apply
        svc.mutate_ads(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    reason = "Every carol ad must show the four-singer minimum and £1,150 price, so only serious bookers click"
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    rows = "".join(f'| {now} | campaign "Christmas carol singers – events 2026" {res} | {field} | {what} | {reason} | `{SCRIPT}` |\n'
                   for res, field, what in changes)
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
