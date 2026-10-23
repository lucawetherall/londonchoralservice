#!/usr/bin/env python3
"""23 Oct 2026 change set: a second responsive search ad for wedding-leads (23739971001), for the 2027 season.

"wedding choir" is the campaign's main search (about 50 a month across the UK, per Keyword Planner). Both its
keywords score Quality Score 5 with expected CTR below average; ad relevance is already above average and the
landing page average. Expected CTR is what the ad copy can move. The ad refreshed earlier today (826000407486)
stays as it is; this one runs beside it in "Ad group 1" with a different build:

- no pins, where the current ad pins its price headline to headline 2;
- "wedding choir" in five headlines and three descriptions, where the current ad has it in two and two;
- the ceremony moments from weddings.html (processional, register, recessional) and a 2027 booking headline.

Plan and test rules: docs/superpowers/plans/2026-10-23-wedding-season-2027.md. In April 2027 the ad with the
lower CTR at 300+ impressions each is paused (never removed).

Final URL https://londonchoralservice.com/weddings.html, paths /wedding-choir/hire. Bids, budget, keywords and
the existing ad are untouched. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/wedding_season_rsa_2026_10_23.py            # validate
    python scripts/ads/wedding_season_rsa_2026_10_23.py --apply    # after approval
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ads_log import append_row, check_log  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
WEDDING, CAMPAIGN, AD_GROUP = 23739971001, "wedding-leads", "Ad group 1"
CURRENT_AD = 826000407486
FINAL_URL = "https://londonchoralservice.com/weddings.html"
PATH1, PATH2 = "wedding-choir", "hire"
SCRIPT = "scripts/ads/wedding_season_rsa_2026_10_23.py"

# Every claim traces to weddings.html, pricing.html or about.html (source after each line).
HEADLINES = [
    "Wedding Choir in London",          # weddings.html H1
    "Hire a Wedding Choir",             # weddings.html
    "London Wedding Choir Hire",        # weddings.html
    "Book Your 2027 Wedding Choir",     # call to action
    "Wedding Choir from £1,150",        # pricing.html: Small Choir (4) from £1,150
    "Four to Twelve Voices",            # weddings.html hero
    "Choir for Your Church Wedding",    # weddings.html
    "Processional to Recessional",      # weddings.html: processional, hymns, signing, recessional
    "Zadok for the Processional",       # weddings.html: "Zadok for the processional"
    "Add an Organist for £250",         # pricing.html: organist £250, alone or with a choir
    "Conservatoire-Trained Singers",    # about.html: RAM, RCM, Guildhall graduates
    "Music Planned with You",           # weddings.html: consultation with the Artistic Director
    "Quote Within 1 Working Day",       # weddings.html, about.html: within one working day
    "Church or Country House",          # weddings.html: churches, hotels, country houses
    "The London Choral Service",
]
DESCRIPTIONS = [
    "Wedding choir hire with rehearsals, sheet music and travel within London included.",
    "Prices from £1,150 for four voices, £1,400 for five, £1,600 for six, £2,000 for eight.",
    "We plan the processional, hymns, register signing and recessional with your wedding choir.",
    "Wedding choir singers from the Royal Academy, Royal College and Guildhall. Send your date.",
]

# House rules every line must pass (CLAUDE.md; as in ad_copy_refresh_2026_10_23.py).
BANNED = [r"\bsinger\b", r"\bsoloists?\b", r"\bsolo\b", r"\bvocalists?\b", r"london funeral singers",
          r"vat[- ]registered", r"inc(l|luding)?\.? vat", r"\d{2,}\+", r"—", r"\bstars?\b|rated"]
# Prices must be ones pricing.html gives for these ensembles.
PRICES = {"£1,150", "£1,400", "£1,600", "£2,000", "£3,000", "£250"}


def check_text(text, limit, where):
    problems = []
    if len(text) > limit:
        problems.append(f"{len(text)} characters, limit {limit}")
    for pat in BANNED:
        if re.search(pat, text, re.I):
            problems.append(f"matches house-rule pattern {pat!r}")
    for p in re.findall(r"£[\d,]+", text):
        if p not in PRICES:
            problems.append(f"price {p} is not on pricing.html")
    if problems:
        raise SystemExit(f'{where}: "{text}" — {"; ".join(problems)}; nothing sent')


def check_spec():
    if len(HEADLINES) != 15 or len({h.lower() for h in HEADLINES}) != 15:
        raise SystemExit("needs 15 distinct headlines; nothing sent")
    if len(DESCRIPTIONS) != 4 or len({d.lower() for d in DESCRIPTIONS}) != 4:
        raise SystemExit("needs 4 distinct descriptions; nothing sent")
    for h in HEADLINES:
        check_text(h, 30, "headline")
    for d in DESCRIPTIONS:
        check_text(d, 90, "description")
    for p in (PATH1, PATH2):
        check_text(p, 15, "path")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_spec()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    groups = q("SELECT campaign.name, ad_group.id, ad_group.name, ad_group.status FROM ad_group "
               f"WHERE campaign.id = {WEDDING} AND ad_group.status = 'ENABLED'")
    hit = [g for g in groups if g.ad_group.name == AD_GROUP]
    if len(hit) != 1 or hit[0].campaign.name != CAMPAIGN:
        raise SystemExit(f'no single enabled "{AD_GROUP}" in campaign {WEDDING} "{CAMPAIGN}"; nothing sent')
    group_id = hit[0].ad_group.id
    ads = q("SELECT ad_group_ad.ad.id, ad_group_ad.status, ad_group_ad.ad.responsive_search_ad.headlines "
            f"FROM ad_group_ad WHERE ad_group.id = {group_id} AND ad_group_ad.status = 'ENABLED'")
    enabled = {r.ad_group_ad.ad.id for r in ads}
    if CURRENT_AD not in enabled:
        raise SystemExit(f"the current ad {CURRENT_AD} is not enabled in {AD_GROUP}; nothing sent")
    for r in ads:
        if {h.text for h in r.ad_group_ad.ad.responsive_search_ad.headlines} == set(HEADLINES):
            print(f"Ad {r.ad_group_ad.ad.id} already carries these headlines. Nothing to change.")
            return
    if len(enabled) >= 3:
        raise SystemExit(f"{AD_GROUP} already has {len(enabled)} enabled ads (Google allows 3); nothing sent")

    op = c.get_type("AdGroupAdOperation")
    new = op.create
    new.ad_group = ga.ad_group_path(CUSTOMER_ID, group_id)
    new.status = c.enums.AdGroupAdStatusEnum.ENABLED
    new.ad.final_urls.append(FINAL_URL)
    rsa = new.ad.responsive_search_ad
    rsa.path1, rsa.path2 = PATH1, PATH2
    for t in HEADLINES:
        a = c.get_type("AdTextAsset"); a.text = t
        rsa.headlines.append(a)
    for t in DESCRIPTIONS:
        a = c.get_type("AdTextAsset"); a.text = t
        rsa.descriptions.append(a)

    res = f'ad group "{AD_GROUP}" new responsive search ad ({FINAL_URL.removeprefix("https://")}/{PATH1}/{PATH2})'
    what = ("none → enabled, no pins; headlines: " + "; ".join(HEADLINES)
            + " | descriptions: " + " / ".join(DESCRIPTIONS))
    why = ("\"wedding choir\" keywords are Quality Score 5 with expected CTR below average; a second ad, unpinned "
           "and with the keyword in more lines, runs beside ad 826000407486 until April 2027, when the lower-CTR "
           "ad is paused")

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + " — 1 new ad\n")
    print(f"• {CAMPAIGN} · {res}")
    print(f"    current: 1 enabled ad ({CURRENT_AD}), unchanged")
    print("    new headlines (unpinned):")
    for h in HEADLINES:
        print(f"      {len(h):>2}  {h}")
    print("    new descriptions:")
    for d in DESCRIPTIONS:
        print(f"      {len(d):>2}  {d}")
    print(f"    reason: {why}")
    if args.apply:
        check_log()  # refuse before changing anything if the log can't be written
    try:
        req = c.get_type("MutateAdGroupAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.operations.append(op)
        req.validate_only = not args.apply
        c.get_service("AdGroupAdService").mutate_ad_group_ads(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    append_row(f'| {now} | campaign "{CAMPAIGN}" {res} | ad | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
