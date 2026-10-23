#!/usr/bin/env python3
"""23 Oct 2026 change set: more distinct headlines in every ad, two more sitelinks for funerals and Christmas.

Every enabled ad is rated Average. Google's advice on each: more unique headlines (or fewer pins), and for the
funeral and three Christmas ads, two more sitelinks. The Christmas campaign loses about 44% of impressions to
ad rank over the last 14 days, and predicted CTR is below average on its busiest keywords.

1. Christmas, four ads: each ad group shared 12 of its 15 headlines with the other three, and several were near
   repeats ("Hire Carol Singers in London" / "Carol Singers for Hire"). Each ad swaps five to eight of them for
   headlines on its own keywords (prices, office parties, hotel lobbies) and facts from its landing page.
   "4 Carol Singers from £1,150" stays pinned to headline 2 and the £1,150 description to description 1.
   Three ads get a new second description written for their ad group.
2. Funeral and wedding ads: both pinned two headlines to headline 1. The keyword headline is unpinned and the
   price headline moves to headline 2 (the pattern the Christmas ads use), and two near-repeats are replaced.
   The wedding ad's last two descriptions now carry "wedding choir", as Google asks.
3. Sitelinks: funeral campaign 4 → 6 ("Funeral Music Guide", "Popular Funeral Hymns"); Christmas 5 → 7
   ("Hear Our Carols", "Office Christmas Parties"). New assets, linked to that campaign only.

Final URLs, paths, bids and budgets are untouched. Nothing is deleted. Every ad is checked against the
account's current text before anything is sent, and every line against the house rules below.

    .venv/bin/python scripts/ads/ad_copy_refresh_2026_10_23.py            # validate
    .venv/bin/python scripts/ads/ad_copy_refresh_2026_10_23.py --apply    # after approval
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
FUNERAL, WEDDING, CHRISTMAS = 23735776277, 23739971001, 24295921372
CAMPAIGNS = {FUNERAL: "funeral expert campaign", WEDDING: "wedding-leads",
             CHRISTMAS: "Christmas carol singers – events 2026"}
SITE = "https://londonchoralservice.com/"
PRICE_HEADLINE = "4 Carol Singers from £1,150"
PRICE_DESCRIPTION = "Four professional carol singers for up to two hours, breaks included. £1,150, all in."
SCRIPT = "scripts/ads/ad_copy_refresh_2026_10_23.py"

H2, D1 = "HEADLINE_2", "DESCRIPTION_1"

# Shared Christmas lines kept in every Christmas ad.
XMAS_KEEP = ["Same Price in December", "Two Hours of Carols Included", "Quote in 1 Working Day",
             "The London Choral Service"]
XMAS_D3 = "December costs the same as June. London travel, sheet music and rehearsals included."
XMAS_D4 = "Carols planned with our Artistic Director, a University of Oxford music tutor."
XMAS_D2_OLD = "Office parties, hotel lobbies and receptions across London. Quote within one working day."

# ad id → (campaign id, ad group, headlines [(text, pin)], descriptions [(text, pin)], why)
ADS = {
    825999587211: (CHRISTMAS, "Hire carol singers", [
        ("Hire Carol Singers in London", None), (PRICE_HEADLINE, H2),
        ("Christmas Carol Singers London", None), ("Christmas Choir for Hire", None),
        ("Professional Carol Singers", None), ("Roaming Carols or Fixed Sets", None),
        ("Royal Academy-Trained Voices", None), ("Last-Minute Dates Welcome", None),
        ("Concert Dress or Xmas Jumpers", None), ("4 to 12 Voices Available", None),
        ("Book Your December Date", None)] + [(t, None) for t in XMAS_KEEP],
        [(PRICE_DESCRIPTION, D1), (XMAS_D2_OLD, None), (XMAS_D3, None), (XMAS_D4, None)],
        "headlines on its own keywords (christmas carol singers london, christmas choir for hire) "
        "replace near-repeats"),
    825999576408: (CHRISTMAS, "Carol singer prices", [
        ("Prices for Carol Singers", None), (PRICE_HEADLINE, H2),
        ("How Much Do Carol Singers Cost", None), ("Carol Singers Rates for 2026", None),
        ("Quintet £1,400, Sextet £1,600", None), ("Choir of Eight £2,000", None),
        ("Chorus of 12 for £3,000", None), ("See Our Christmas Prices", None),
        ("London Travel Included", None), ("No VAT Added to Any Price", None),
        ("Written Quote Before You Book", None)] + [(t, None) for t in XMAS_KEEP],
        [(PRICE_DESCRIPTION, D1),
         ("Quintet £1,400, sextet £1,600, choir of eight £2,000, chorus of twelve £3,000.", None),
         (XMAS_D3, None), (XMAS_D4, None)],
        "Google asks for its keywords (cost, prices, rates) in the headlines; every price from christmas-pricing.html"),
    826040926768: (CHRISTMAS, "Carol singers for events", [
        ("Carol Singers for Events", None), (PRICE_HEADLINE, H2),
        ("Office Party Carol Singers", None), ("Corporate Carol Singers", None),
        ("Christmas Party Carol Singers", None), ("Invoice Against Your PO", None),
        ("Carols as Your Guests Arrive", None), ("Concert Dress or Xmas Jumpers", None),
        ("Unaccompanied 4-Part Carols", None), ("Royal Academy-Trained Voices", None),
        ("Book Your December Date", None)] + [(t, None) for t in XMAS_KEEP],
        [(PRICE_DESCRIPTION, D1),
         ("Carols as guests arrive, then a last set the whole office can join. We invoice your PO.", None),
         (XMAS_D3, None), (XMAS_D4, None)],
        "headlines on its own keywords (christmas party, corporate) and what a company buyer asks (PO invoicing)"),
    826124318366: (CHRISTMAS, "Venue and lobby carols", [
        ("Carol Singers for Hotels", None), (PRICE_HEADLINE, H2),
        ("Lobby Carol Singers", None), ("Carol Singers for Residents", None),
        ("Hotel Carol Singers in London", None), ("Carol Singers for Receptions", None),
        ("Sets Timed to Your Guests", None), ("Festive Afternoon Tea Carols", None),
        ("Pianist Between Sets, £250", None), ("Unaccompanied 4-Part Carols", None),
        ("Book Your December Date", None)] + [(t, None) for t in XMAS_KEEP],
        [(PRICE_DESCRIPTION, D1),
         ("Three or four short sets across an evening, timed to the flow of guests through the lobby.", None),
         (XMAS_D3, None), (XMAS_D4, None)],
        "Google asks for its keywords (hotel, reception) in the headlines; lobby facts from christmas.html"),
    826000407483: (FUNERAL, "Ad group 1", [
        ("Funeral Choir Hire in London", None), ("Funeral Choir from £1,150", H2),
        ("Church & Crematorium Choirs", None), ("Memorial Service Choir", None),
        ("Hymns Led by a Live Choir", None), ("Available at Short Notice", None),
        ("Funeral Director Liaison", None), ("Written Quote Before You Book", None),
        ("Coronation & BBC Proms Singers", None), ("Oxford-Trained Director", None),
        ("Royal Academy Musicians", None), ("Rehearsals & Music Included", None),
        ("Travel in London Included", None), ("Quartet £1,150, Choir £2,000", None),
        ("The London Choral Service", None)],
        None,  # descriptions unchanged
        "two headlines were pinned to headline 1; Google advises unpinning and more distinct headlines"),
    826000407486: (WEDDING, "Ad group 1", [
        ("Wedding Choir Hire in London", None), ("Wedding Choirs from £1,150", H2),
        ("Church Wedding Choirs", None), ("Music for Signing the Register", None),
        ("Hymns, Anthems & Motets", None), ("Choir for Wedding Ceremonies", None),
        ("Written Quote Before You Book", None), ("Coronation & BBC Proms Singers", None),
        ("Oxford-Trained Director", None), ("Royal Academy Musicians", None),
        ("Rehearsals & Music Included", None), ("Travel in London Included", None),
        ("Hire a Choir for Your Wedding", None), ("Quartet £1,150, Choir £2,000", None),
        ("The London Choral Service", None)],
        [("Wedding choirs from £1,150: four voices lead your hymns and sing up to three pieces.", None),
         ("Quintet £1,400, sextet £1,600, choir of eight £2,000. No VAT added and nothing on top.", None),
         ("Wedding choir repertoire planned with our Oxford-trained director. Rehearsals included.", None),
         ("Hire a wedding choir of Royal Academy and Royal College singers, chosen for your day.", None)],
        "two headlines were pinned to headline 1; Google asks for more keywords in the descriptions"),
}

# (campaign id, link text, description 1, description 2, final URL)
SITELINKS = [
    (FUNERAL, "Funeral Music Guide", "Hymns, anthems and exit music", "Help choosing music for a service",
     SITE + "music-guides/funeral-music-guide.html"),
    (FUNERAL, "Popular Funeral Hymns", "Abide with Me, Crimond and more", "Notes on each hymn",
     SITE + "music-guides/popular-funeral-hymns.html"),
    (CHRISTMAS, "Hear Our Carols", "Films of our winter sets", "Carols and Christmas songs",
     SITE + "christmas-listen.html"),
    (CHRISTMAS, "Office Christmas Parties", "Carols as guests arrive", "We invoice against your PO",
     SITE + "for-event-managers.html"),
]

# House rules every new line must pass (CLAUDE.md, owner decision 26 Sep 2026).
BANNED = [r"\bsinger\b", r"\bsoloists?\b", r"\bsolo\b", r"\bvocalists?\b", r"london funeral singers",
          r"vat[- ]registered", r"inc(l|luding)?\.? vat", r"\d{2,}\+", r"—", r"\bstars?\b|rated"]


def check_text(text, limit, where):
    problems = []
    if len(text) > limit:
        problems.append(f"{len(text)} characters, limit {limit}")
    for pat in BANNED:
        if re.search(pat, text, re.I):
            problems.append(f"matches house-rule pattern {pat!r}")
    if problems:
        raise SystemExit(f'{where}: "{text}" — {"; ".join(problems)}; nothing sent')


def check_spec():
    for ad_id, (camp, group, heads, descs, _) in ADS.items():
        where = f"ad {ad_id} ({group})"
        texts = [t for t, _ in heads]
        if len(texts) != 15 or len(set(t.lower() for t in texts)) != 15:
            raise SystemExit(f"{where}: needs 15 distinct headlines, has {len(set(texts))}; nothing sent")
        for t, _ in heads:
            check_text(t, 30, where)
        for t, _ in descs or []:
            check_text(t, 90, where)
        if descs is not None and len(descs) != 4:
            raise SystemExit(f"{where}: needs 4 descriptions; nothing sent")
        if camp == CHRISTMAS:
            if (PRICE_HEADLINE, H2) not in heads or (PRICE_DESCRIPTION, D1) not in descs:
                raise SystemExit(f"{where}: the Christmas price pins are missing; nothing sent")
            if [p for _, p in heads if p] != [H2] or [p for _, p in descs if p] != [D1]:
                raise SystemExit(f"{where}: only the two price pins are allowed; nothing sent")
    for camp, text, d1, d2, _ in SITELINKS:
        check_text(text, 25, "sitelink")
        check_text(d1, 35, f'sitelink "{text}"')
        check_text(d2, 35, f'sitelink "{text}"')


def pins_of(items, E):
    return [(a.text, None if a.pinned_field in (E.ServedAssetFieldTypeEnum.UNSPECIFIED, 0) else a.pinned_field.name)
            for a in items]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    check_spec()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    ops, changes = [], []  # changes: (campaign, resource, field, current → new, reason)

    # --- ads -------------------------------------------------------------------
    ids = ", ".join(str(i) for i in ADS)
    rows = {r.ad_group_ad.ad.id: r for r in q(
        "SELECT campaign.id, ad_group.name, ad_group_ad.status, ad_group_ad.ad.id, ad_group_ad.ad.resource_name, "
        "ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions "
        f"FROM ad_group_ad WHERE ad_group_ad.ad.id IN ({ids})")}
    for ad_id, (camp, group, heads, descs, why) in ADS.items():
        r = rows.get(ad_id)
        if not r or r.campaign.id != camp or r.ad_group.name != group or r.ad_group_ad.status.name != "ENABLED":
            raise SystemExit(f"ad {ad_id} is not the enabled ad in {CAMPAIGNS[camp]} / {group}; nothing sent")
        rsa = r.ad_group_ad.ad.responsive_search_ad
        cur_h, cur_d = pins_of(rsa.headlines, E), pins_of(rsa.descriptions, E)
        new_d = descs if descs is not None else cur_d
        if cur_h == heads and cur_d == new_d:
            continue
        op = c.get_type("MutateOperation")
        ad = op.ad_operation.update
        ad.resource_name = r.ad_group_ad.ad.resource_name
        for t, pin in heads:
            a = c.get_type("AdTextAsset"); a.text = t
            if pin:
                a.pinned_field = getattr(E.ServedAssetFieldTypeEnum, pin)
            ad.responsive_search_ad.headlines.append(a)
        for t, pin in new_d:
            a = c.get_type("AdTextAsset"); a.text = t
            if pin:
                a.pinned_field = getattr(E.ServedAssetFieldTypeEnum, pin)
            ad.responsive_search_ad.descriptions.append(a)
        op.ad_operation.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])
        ops.append(op)
        res = f'ad {ad_id} in "{group}"'
        old_t, new_t = {t for t, _ in cur_h}, {t for t, _ in heads}
        gone, added = [t for t, _ in cur_h if t not in new_t], [t for t, _ in heads if t not in old_t]
        if gone or added:
            changes.append((camp, res, "headlines", "; ".join(gone) + " → " + "; ".join(added), why))
        pin_old = {t: p for t, p in cur_h if t in new_t}
        moved = [f'"{t}" {pin_old[t] or "unpinned"} → {p or "unpinned"}' for t, p in heads
                 if t in pin_old and pin_old[t] != p]
        if moved:
            changes.append((camp, res, "pins", "; ".join(moved), "one pin at most, on headline 2, as in the Christmas ads"))
        old_dt = {t for t, _ in cur_d}
        d_gone = [t for t, _ in cur_d if t not in {t for t, _ in new_d}]
        d_added = [t for t, _ in new_d if t not in old_dt]
        if d_gone or d_added:
            changes.append((camp, res, "descriptions", "; ".join(d_gone) + " → " + "; ".join(d_added), why))

    # --- sitelinks ---------------------------------------------------------------
    linked = {(r.campaign.id, r.asset.sitelink_asset.link_text.lower()) for r in q(
        "SELECT campaign.id, asset.sitelink_asset.link_text FROM campaign_asset "
        f"WHERE asset.type = 'SITELINK' AND campaign.id IN ({FUNERAL}, {CHRISTMAS}) AND campaign_asset.status = 'ENABLED'")}
    for i, (camp, text, d1, d2, url) in enumerate(SITELINKS, start=1):
        if (camp, text.lower()) in linked:
            continue
        tmp = ga.asset_path(CUSTOMER_ID, str(-i))
        op = c.get_type("MutateOperation")
        new = op.asset_operation.create
        new.resource_name = tmp
        new.final_urls.append(url)
        new.sitelink_asset.link_text = text
        new.sitelink_asset.description1 = d1
        new.sitelink_asset.description2 = d2
        ops.append(op)
        op = c.get_type("MutateOperation")
        op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, camp)
        op.campaign_asset_operation.create.asset = tmp
        op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.SITELINK
        ops.append(op)
        changes.append((camp, f'sitelink "{text}" (new)', "create + link",
                        f"none → linked, {url.removeprefix(SITE)}, \"{d1}\" / \"{d2}\"",
                        "Google's ad-strength check asks for 2 more sitelinks"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for camp, res, field, what, why in changes:
        print(f"• {CAMPAIGNS[camp]} · {res} · {field}:\n    {what}\n    reason: {why}")
    if not ops:
        print("Nothing to change.")
        return
    if args.apply:
        check_log()  # refuse before changing anything if the log can't be written
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
    for camp, res, field, what, why in reversed(changes):
        append_row(f'| {now} | campaign "{CAMPAIGNS[camp]}" {res} | {field} | {what} | {why} | `{SCRIPT}` |')
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
