#!/usr/bin/env python3
"""26 Oct 2026 change set: a second responsive search ad for the funeral expert campaign (23735776277).

The live ad (826000407483) is rated Average, with its price headline pinned to position 2 and description 1
pinned. "funeral choir" phrase scores Quality Score 5 with expected CTR below average, and its £5 bid already
beats the £4.85 top-of-page estimate, so the copy is what can move it. The current ad stays as it is; this one
runs beside it in "Ad group 1", built as the 23 Oct wedding ad was:

- no pins;
- "funeral choir" in five headlines and three descriptions;
- short notice, the hymns and the funeral director, from funerals.html.

Plan: docs/superpowers/plans/2026-10-26-growth-handoff.md, WP1a. Test rule as in
docs/superpowers/plans/2026-10-23-wedding-season-2027.md: in April 2027 the ad with the lower CTR at 300+
impressions each is paused (never removed).

Final URL https://londonchoralservice.com/funerals.html, paths /funeral-choir/hire. Bids, budget, keywords and
the existing ad are untouched. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/funeral_rsa_2026_10_26.py            # validate
    python scripts/ads/funeral_rsa_2026_10_26.py --apply    # after approval
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
FUNERAL, CAMPAIGN, AD_GROUP = 23735776277, "funeral expert campaign", "Ad group 1"
CURRENT_AD = 826000407483
FINAL_URL = "https://londonchoralservice.com/funerals.html"
PATH1, PATH2 = "funeral-choir", "hire"
SCRIPT = "scripts/ads/funeral_rsa_2026_10_26.py"

# Every claim traces to funerals.html, pricing.html or about.html (source after each line).
HEADLINES = [
    "Funeral Choir in London",          # funerals.html H1
    "Hire a Funeral Choir",             # funerals.html: "Hire a professional choir for a funeral"
    "Funeral Choir from £1,150",        # pricing.html: Small Choir (4) from £1,150
    "Funeral Choir Across the UK",      # funerals.html: "in London or anywhere in the UK"
    "Funeral Choir at Short Notice",    # funerals.html: "short notice is fine"
    "Voices to Lead the Hymns",         # funerals.html: "lead the congregational hymns"
    "Four to Twelve Voices",            # funerals.html hero
    "Churches and Crematoriums",        # funerals.html: churches, crematoriums, and chapels
    "Often Arranged Within 48 Hours",   # funerals.html: "We can often arrange singers within 48 hours"
    "Add an Organist for £250",         # pricing.html, funerals.html: organist £250
    "Conservatoire-Trained Singers",    # funerals.html, about.html: Royal Academy, Royal College
    "Reply Within 1 Working Day",       # funerals.html: "replies within one working day"
    "We Work With Your Director",       # funerals.html: "coordinates with your funeral director"
    "Music Planned with You",           # funerals.html: one-to-one music consultation
    "The London Choral Service",
]
DESCRIPTIONS = [
    "A funeral choir to lead the hymns and sing up to three pieces, from £1,150 for four.",  # funerals.html
    "Funeral choir prices: five voices £1,400; six £1,600; eight £2,000. No VAT added.",  # pricing.html
    "Book a funeral choir at short notice. We reply within one working day, often the same day.",  # funerals.html
    "A rehearsal in the venue and travel within Greater London are included in the price.",  # funerals.html
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
               f"WHERE campaign.id = {FUNERAL} AND ad_group.status = 'ENABLED'")
    hit = [g for g in groups if g.ad_group.name == AD_GROUP]
    if len(hit) != 1 or hit[0].campaign.name != CAMPAIGN:
        raise SystemExit(f'no single enabled "{AD_GROUP}" in campaign {FUNERAL} "{CAMPAIGN}"; nothing sent')
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
    why = ("\"funeral choir\" phrase is Quality Score 5 with expected CTR below average and the live ad is rated "
           "Average with pins; a second ad, unpinned and with the keyword in more lines, runs beside ad "
           "826000407483 until April 2027, when the lower-CTR "
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
