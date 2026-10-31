#!/usr/bin/env python3
"""31 Oct 2026: new headline and description set for the Christmas "Hire carol singers" ad.

Monday review 2026-10-31, item 2026-10-31-03 (approved by the owner, "Approve all"). Ad 825999587211
(campaign 24295921372, lands on christmas.html) takes all 46 of the campaign's clicks in 30 days and
has AVERAGE strength; Google asks for more unique headlines. The set below is the growth agent's,
exactly as approved: 15 headlines and 4 descriptions, every claim on christmas.html.
"4 Carol Singers from £1,150" stays pinned to headline 2 and the price description is pinned to
description 1; everything else is unpinned.

The ad is edited in place. The update mask names responsive_search_ad.headlines and
responsive_search_ad.descriptions only, so final URLs and path1/path2 are untouched.

    source .venv/bin/activate
    python scripts/ads/christmas_hire_ad_set_2026_10_31.py            # validate
    python scripts/ads/christmas_hire_ad_set_2026_10_31.py --apply    # after approval
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
AD = 825999587211
HEADLINES = [  # (text, pin)
    ("Hire Carol Singers in London", None),
    ("4 Carol Singers from £1,150", "HEADLINE_2"),
    ("Office Party Carol Singers", None),
    ("Roaming or Fixed Carol Sets", None),
    ("Quote Within One Working Day", None),
    ("No Charges Added Later", None),
    ("Same Price Throughout December", None),
    ("London Travel Included", None),
    ("Up to 2 Hours, Breaks Included", None),
    ("Carols Sung Unaccompanied", None),
    ("Hotel Lobby Carol Singers", None),
    ("Conservatoire-Trained Singers", None),
    ("Set List Agreed With You", None),
    ("Santa Hats if You Want Them", None),
    ("Check Your Date With Us", None),
]
DESCRIPTIONS = [
    ("Four carol singers £1,150 for up to two hours, breaks included. London travel included.", "DESCRIPTION_1"),
    ("Carols as guests arrive, then a last set the office can join. Roaming or from one spot.", None),
    ("Four singers or more, each chosen for your event. Written quote within one working day.", None),
    ("Unaccompanied carols your guests know, sung in your lobby, bar or reception room.", None),
]
REASON = ("Monday review 2026-10-31 item 2026-10-31-03: ad strength AVERAGE, Google asks for more unique "
          "headlines; this ad takes all 46 Christmas clicks in 30 days; every claim is on christmas.html")
SCRIPT = "scripts/ads/christmas_hire_ad_set_2026_10_31.py"


def check_set():
    for kind, items, limit in (("headline", HEADLINES, 30), ("description", DESCRIPTIONS, 90)):
        texts = [t for t, _ in items]
        if len({t.lower() for t in texts}) != len(texts):
            raise SystemExit(f"duplicate {kind}; nothing sent")
        for t in texts:
            if len(t) > limit:
                raise SystemExit(f'{kind} "{t}" is over {limit} characters; nothing sent')


def fmt(assets):
    return [f'"{a.text}"' + (f" [{a.pinned_field.name}]" if a.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN") else "")
            for a in assets]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_set()
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT ad_group.name, ad_group_ad.status, ad_group_ad.ad.resource_name, ad_group_ad.ad.final_urls, "
        "ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions "
        f"FROM ad_group_ad WHERE campaign.id = {CHRISTMAS} AND ad_group_ad.ad.id = {AD}")))
    if not rows or rows[0].ad_group_ad.status.name != "ENABLED":
        raise SystemExit(f"ad {AD} is not an enabled ad in the Christmas campaign; nothing sent")
    r = rows[0]
    rsa = r.ad_group_ad.ad.responsive_search_ad
    url = r.ad_group_ad.ad.final_urls[0]

    op = c.get_type("MutateOperation")
    ad = op.ad_operation.update
    ad.resource_name = r.ad_group_ad.ad.resource_name
    for items, field, enum in ((HEADLINES, ad.responsive_search_ad.headlines, "HEADLINE"),
                               (DESCRIPTIONS, ad.responsive_search_ad.descriptions, "DESCRIPTION")):
        for text, pin in items:
            t = c.get_type("AdTextAsset")
            t.text = text
            if pin:
                t.pinned_field = getattr(c.enums.ServedAssetFieldTypeEnum, pin)
            field.append(t)
    op.ad_operation.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])

    old_h, old_d = fmt(rsa.headlines), fmt(rsa.descriptions)
    new_h = [f'"{t}"' + (f" [{p}]" if p else "") for t, p in HEADLINES]
    new_d = [f'"{t}"' + (f" [{p}]" if p else "") for t, p in DESCRIPTIONS]
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f' — ad {AD} in "{r.ad_group.name}" ({url})\n')
    print("headlines, current:\n  " + "\n  ".join(old_h))
    print("headlines, new:\n  " + "\n  ".join(new_h))
    print("descriptions, current:\n  " + "\n  ".join(old_d))
    print("descriptions, new:\n  " + "\n  ".join(new_d))
    print(f"reason: {REASON}")
    try:
        req = c.get_type("MutateGoogleAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.mutate_operations.append(op)
        req.validate_only = not args.apply
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted the operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    res = f'campaign "{CAMPAIGN}" ad {AD} in "{r.ad_group.name}" ({url})'
    ads_log.append_row(f'| {now} | {res} | descriptions | {"; ".join(old_d)} → {"; ".join(new_d)} | {REASON} | `{SCRIPT}` |')
    ads_log.append_row(f'| {now} | {res} | headlines | {"; ".join(old_h)} → {"; ".join(new_h)} | {REASON} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
