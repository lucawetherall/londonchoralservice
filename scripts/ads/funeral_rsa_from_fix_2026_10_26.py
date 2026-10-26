#!/usr/bin/env python3
"""26 Oct 2026 correction to the funeral ad made this morning by funeral_rsa_2026_10_26.py (829543104168).

Its second description, "Funeral choir prices: five voices £1,400; six £1,600; eight £2,000. No VAT added.",
gives the prices without "from". pricing.html gives every ensemble as "From £…", because travel outside Greater
London is added to the quote (the 23 Oct price-asset fix set the qualifier to "From" for the same reason). This
replaces that one description; the headlines and the other three descriptions are resent unchanged, no pins.

    source .venv/bin/activate
    python scripts/ads/funeral_rsa_from_fix_2026_10_26.py            # validate
    python scripts/ads/funeral_rsa_from_fix_2026_10_26.py --apply    # after approval
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
FUNERAL, CAMPAIGN, AD = 23735776277, "funeral expert campaign", 829543104168
OLD = "Funeral choir prices: five voices £1,400; six £1,600; eight £2,000. No VAT added."
NEW = "Funeral choir from £1,400 for five, £1,600 for six or £2,000 for eight. No VAT added."  # pricing.html
SCRIPT = "scripts/ads/funeral_rsa_from_fix_2026_10_26.py"
WHY = ("pricing.html gives every ensemble as 'From £…' (travel outside Greater London is added to the quote); "
       "the description gave the prices without 'from'")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_text(NEW, 90, "description")
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT campaign.id, ad_group_ad.ad.responsive_search_ad.headlines, "
        "ad_group_ad.ad.responsive_search_ad.descriptions FROM ad_group_ad "
        f"WHERE ad_group_ad.ad.id = {AD} AND ad_group_ad.status = 'ENABLED'")))
    if len(rows) != 1 or rows[0].campaign.id != FUNERAL:
        raise SystemExit(f"ad {AD} is not a single enabled ad in campaign {FUNERAL}; nothing sent")
    rsa = rows[0].ad_group_ad.ad.responsive_search_ad
    descs = [d.text for d in rsa.descriptions]
    if NEW in descs:
        print("The ad already carries the new description. Nothing to change.")
        return
    if OLD not in descs:
        raise SystemExit("the ad does not carry the expected old description; nothing sent")

    op = c.get_type("AdOperation")
    ad = op.update
    ad.resource_name = ga.ad_path(CUSTOMER_ID, AD)
    for h in rsa.headlines:
        t = c.get_type("AdTextAsset"); t.text = h.text
        ad.responsive_search_ad.headlines.append(t)
    for d in descs:
        t = c.get_type("AdTextAsset"); t.text = NEW if d == OLD else d
        ad.responsive_search_ad.descriptions.append(t)
    op.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])

    res = f'campaign "{CAMPAIGN}" ad {AD} in "Ad group 1"'
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — 1 change\n\n• {res}\n"
          f'    description: "{OLD}" → "{NEW}" ({len(NEW)} chars, unpinned as before)\n    reason: {WHY}')
    if args.apply:
        check_log()
    try:
        req = c.get_type("MutateAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.operations.append(op)
        req.validate_only = not args.apply
        c.get_service("AdService").mutate_ads(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted the operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    append_row(f'| {now} | {res} | description | "{OLD}" → "{NEW}" ({len(NEW)} chars, unpinned as before) '
               f"| {WHY} | `{SCRIPT}` |")
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
