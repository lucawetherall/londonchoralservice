#!/usr/bin/env python3
"""23 Oct 2026 change set 5: Christmas ad headlines (campaign 24295921372).

1. All four ads: "Two Hours of Carols Included" → "Up to 2 Hours, Breaks Included". christmas.html
   and christmas-pricing.html sell up to two hours including breaks (three or four sets of
   about twenty-five minutes), not two hours of singing.
2. Ad 825999587211 ("Hire carol singers", lands on christmas.html):
   "Unaccompanied 4-Part Carols" → "Christmas Choir for Hire" and
   "Book Your December Date" → "Christmas Carol Singers", for searches such as
   "christmas choir hire" that the ad group's keywords bid on.

Each ad is edited in place with every headline resent in its own position and with its own
pin ("4 Carol Singers from £1,150" stays pinned to headline 2). The update mask names
responsive_search_ad.headlines only, so descriptions (the price description stays pinned to
description 1), final URLs and path1/path2 are untouched; a separate change to ad
825999587211's display paths does not clash with this one.

    source .venv/bin/activate
    python scripts/ads/christmas_headlines_2026_10_23.py            # validate
    python scripts/ads/christmas_headlines_2026_10_23.py --apply    # after approval
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
CAMPAIGN = "Christmas carol singers – events 2026"
ADS = (825999587211, 825999576408, 826040926768, 826124318366)
HIRE_AD = 825999587211
PRICE_HEADLINE = "4 Carol Singers from £1,150"
PRICE_DESCRIPTION = "Four professional carol singers for up to two hours, breaks included. £1,150, all in."
ALL_ADS = {"Two Hours of Carols Included": "Up to 2 Hours, Breaks Included"}
# The Hire-ad swaps planned here ("Christmas Choir for Hire", a carol singers headline) were made by the
# 23 Oct 15:32 copy refresh (PR #287), so only the two-hours headline is left to change.
HIRE_ONLY = {}
WHY = {
    "Two Hours of Carols Included": "the booking is up to two hours including breaks (christmas.html: 'A standard booking "
                                    "runs up to two hours including breaks'); 'two hours of carols' overstates the singing",
    "Unaccompanied 4-Part Carols": "matches 'christmas choir' searches; christmas.html sells a Small Choir (4) to a Full "
                                   "Choir (8) ('The choir were the highlight of our Christmas drinks')",
    "Book Your December Date": "matches the page's own title, 'Hire Christmas Carol Singers in London & the UK'",
}
WHY_PRICING_PAGE = ("the booking is up to two hours including breaks (christmas-pricing.html: 'A standard Christmas "
                    "booking covers up to two hours including breaks'); 'two hours of carols' overstates the singing")
SCRIPT = "scripts/ads/christmas_headlines_2026_10_23.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    ops, changes = [], []  # changes: (resource, field, current → new, reason)

    rows = {r.ad_group_ad.ad.id: r for r in q(
        "SELECT campaign.id, ad_group.name, ad_group_ad.status, ad_group_ad.ad.id, ad_group_ad.ad.resource_name, "
        "ad_group_ad.ad.final_urls, ad_group_ad.ad.responsive_search_ad.headlines, "
        "ad_group_ad.ad.responsive_search_ad.descriptions FROM ad_group_ad "
        f"WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.ad.id IN ({', '.join(map(str, ADS))})")}
    for ad_id in ADS:
        r = rows.get(ad_id)
        if r is None or r.ad_group_ad.status.name != "ENABLED":
            raise SystemExit(f"ad {ad_id} is not an enabled ad in the Christmas campaign; nothing sent")
        rsa = r.ad_group_ad.ad.responsive_search_ad
        pins = {h.text: h.pinned_field.name for h in rsa.headlines}
        if pins.get(PRICE_HEADLINE) != "HEADLINE_2":
            raise SystemExit(f'ad {ad_id}: "{PRICE_HEADLINE}" is not pinned to headline 2; nothing sent')
        if {d.text: d.pinned_field.name for d in rsa.descriptions}.get(PRICE_DESCRIPTION) != "DESCRIPTION_1":
            raise SystemExit(f"ad {ad_id}: the price description is not pinned to description 1; nothing sent")
        swap = dict(ALL_ADS, **(HIRE_ONLY if ad_id == HIRE_AD else {}))
        missing = [t for t in swap if t not in pins]
        if missing:
            raise SystemExit(f"ad {ad_id} lacks the headline(s) {missing}; nothing sent")
        new = [swap.get(h.text, h.text) for h in rsa.headlines]
        low = [t.lower() for t in new]
        if len(set(low)) != len(low):
            raise SystemExit(f"ad {ad_id} would have a duplicate headline; nothing sent")
        if any(len(t) > 30 for t in new):
            raise SystemExit(f"ad {ad_id}: a headline would be over 30 characters; nothing sent")

        op = c.get_type("MutateOperation")
        ad = op.ad_operation.update
        ad.resource_name = r.ad_group_ad.ad.resource_name
        for h in rsa.headlines:
            t = c.get_type("AdTextAsset")
            t.text = swap.get(h.text, h.text)
            if h.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN"):
                t.pinned_field = h.pinned_field
            ad.responsive_search_ad.headlines.append(t)
        op.ad_operation.update_mask.paths.append("responsive_search_ad.headlines")
        ops.append(op)
        url = r.ad_group_ad.ad.final_urls[0]
        for old, nw in swap.items():
            why = WHY[old]
            if old in ALL_ADS and url.endswith("christmas-pricing.html"):
                why = WHY_PRICING_PAGE
            changes.append((f'ad {ad_id} in "{r.ad_group.name}" ({url})', "headline",
                            f'"{old}" → "{nw}" ({len(nw)} chars, unpinned as before)', why))
        kept = [f'"{h.text}" → {h.pinned_field.name}' for h in rsa.headlines
                if h.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN")]
        print(f"ad {ad_id}: {len(new)} headlines resent in order; pins kept: {'; '.join(kept)}; "
              "descriptions and paths not in the update mask")

    print("\n" + ("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} ad(s), one atomic request\n")
    for res, field, what, why in changes:
        print(f"• {CAMPAIGN} · {res} · {field}: {what}\n    reason: {why}")
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
        ads_log.append_row(f'| {now} | campaign "{CAMPAIGN}" {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
