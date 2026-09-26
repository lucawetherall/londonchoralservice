#!/usr/bin/env python3
"""Refocus every campaign on choir and carol singers bookings, and remove
inaccurate claims from ads and assets.

Owner decision (2026-09-26): no solo singer bookings; wedding and funeral
campaigns target choir searches only, Christmas targets "carol singers".

One atomic mutate, validate_only by default. Nothing is deleted: keywords,
ads, sitelinks and callouts are PAUSED and replaced.

    source .venv/bin/activate
    python scripts/ads/choir_focus_2026_09.py            # validate
    python scripts/ads/choir_focus_2026_09.py --apply    # after approval
"""

import argparse
import datetime
import re
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/choir_focus_2026_09.py"
SITE = "https://londonchoralservice.com/"

FUNERAL, WEDDING, CHRISTMAS = 23735776277, 23739971001, 24295921372
FUNERAL_AG, WEDDING_AG = 195400451979, 203778897508
SOLO = re.compile(r"singer|soloist|vocalist|singing")
# Owner: keep the competitor-brand keywords running (they lead to the choir ad and compare/ page).
COMPETITOR = re.compile(r"london\s*funeral\s*singers|londonfuneralsingers")

# Account callouts to pause: false (VAT), unsupported (rating), solo pricing, over-promise.
PAUSE_CALLOUTS = {
    347993535995: "States VAT is included; Alma Consort Ltd is not VAT-registered",
    347993535998: "Unsupported rating claim; no ratings are published on the site",
    347993536010: "Sells soloists (owner: choir bookings only) at £215, which is not a site price",
    347993536001: "Over-promises: the site says a reply within one working day, usually the same day",
}
NEW_CALLOUTS = ["No VAT Added", "Written Quote Upfront", "Rehearsals Included", "Hand-Picked Singers"]

PAUSE_SITELINKS = {  # asset id: (campaign, reason)
    348071213209: (FUNERAL, "Sitelink says all prices include VAT"),
    348142147041: (FUNERAL, "Sitelink advertises soloists"),
    348796933577: (WEDDING, "Sitelink quotes £215, a soloist price not on the site"),
    348796933580: (WEDDING, "Sitelink claims studio quality; recordings are live performances"),
    348796933589: (WEDDING, "Sitelink promises a quote in 24 hours; site says one working day"),
}
NEW_SITELINKS = {
    FUNERAL: [("Funeral Choir Prices", "Four voices from £1,150", "No VAT added, no extras", SITE + "pricing.html"),
              ("Hear Our Choirs", "Recordings of our choirs", "Hymns and anthems, live", SITE + "listen.html")],
    WEDDING: [("Wedding Choir Prices", "Four voices from £1,150", "No VAT added, no extras", SITE + "pricing.html"),
              ("Hear Our Choirs", "Recordings of our choirs", "Hymns and anthems, live", SITE + "listen.html"),
              ("Get a Quote", "Reply within one working day", "Call or enquire online", SITE + "contact.html")],
}
CHOIR_PRICES = [("Small Choir (4)", "Hymns and up to 3 pieces", 1150), ("Quintet (5)", "Hymns and up to 3 pieces", 1400),
                ("Sextet (6)", "Hymns and up to 3 pieces", 1600), ("Full Choir (8)", "Hymns and up to 3 pieces", 2000),
                ("Chorus (12)", "Hymns and up to 4 pieces", 3000)]
SNIPPET = ("Types", ["Quartets", "Quintets", "Sextets", "Full Choirs", "Choruses"])

NEGATIVES = ["singer", "soloist", "solo", "vocalist"]  # singular "singer" does not block "carol singers"
NEW_KEYWORDS = {
    FUNERAL_AG: [("funeral choir", "EXACT"), ("funeral choir hire", "EXACT"), ("funeral choir london", "EXACT"),
                 ("hire funeral choir", "PHRASE"), ("church choir for funeral", "PHRASE"), ("choir for funeral", "PHRASE")],
    WEDDING_AG: [("wedding choir", "PHRASE"), ("wedding choir", "EXACT"), ("church wedding choir", "PHRASE"),
                 ("wedding choir hire", "EXACT")],
    "Hire carol singers": [("carol singers", "EXACT"), ("christmas carol singers", "EXACT"), ("xmas carol singers", "EXACT")],
}
ADS = {
    FUNERAL_AG: {
        "url": SITE + "funerals.html", "path": ("funeral-choir", "london"),
        "reason": "Old ad claimed prices include VAT, 5-star ratings and £215 soloists, and landed on pricing.html; strength Poor",
        "pinned": ["Funeral Choir Hire in London", "Funeral Choir from £1,150"],
        "headlines": ["Four to Twelve Voices", "Hymns Led by a Live Choir", "Available at Short Notice",
                      "No VAT Added, No Extras", "Written Quote Before You Book", "Coronation & BBC Proms Singers",
                      "Oxford-Trained Director", "Royal Academy Musicians", "Rehearsals & Music Included",
                      "Travel in London Included", "Choir for Funeral Services", "Quartet £1,150, Choir £2,000",
                      "The London Choral Service"],
        "descriptions": ["A funeral choir from £1,150: four professional voices lead the hymns and sing 3 pieces.",
                         "Quintet £1,400, sextet £1,600, choir of eight £2,000. No VAT added and nothing on top.",
                         "We coordinate with your funeral director and venue, and can often help at short notice.",
                         "Singers from the Royal Academy and Royal College, chosen by an Oxford-trained director."],
    },
    WEDDING_AG: {
        "url": SITE + "weddings.html", "path": ("wedding-choir", "london"),
        "reason": "Old ad claimed a 5-star rating, used singer headlines and an http:// URL; strength Poor",
        "pinned": ["Wedding Choir Hire in London", "Wedding Choirs from £1,150"],
        "headlines": ["Church Wedding Choirs", "Four to Twelve Voices", "Hymns, Anthems & Motets",
                      "No VAT Added, No Extras", "Written Quote Before You Book", "Coronation & BBC Proms Singers",
                      "Oxford-Trained Director", "Royal Academy Musicians", "Rehearsals & Music Included",
                      "Travel in London Included", "Hire a Choir for Your Wedding", "Quartet £1,150, Choir £2,000",
                      "The London Choral Service"],
        "descriptions": ["Wedding choirs from £1,150: four voices lead your hymns and sing up to three pieces.",
                         "Quintet £1,400, sextet £1,600, choir of eight £2,000. No VAT added and nothing on top.",
                         "Repertoire planned with our Oxford-trained director. Rehearsals and sheet music included.",
                         "Singers from the Royal Academy and Royal College, auditioned and chosen for your day."],
    },
}


def check_limits():
    for ag, ad in ADS.items():
        heads = ad["pinned"] + ad["headlines"]
        assert len(heads) == 15 and len(set(heads)) == 15, ag
        assert all(len(h) <= 30 for h in heads), [h for h in heads if len(h) > 30]
        assert all(len(d) <= 90 for d in ad["descriptions"]), [d for d in ad["descriptions"] if len(d) > 90]
        assert all(len(p) <= 15 for p in ad["path"])
    assert all(len(c) <= 25 for c in NEW_CALLOUTS + SNIPPET[1])
    for links in NEW_SITELINKS.values():
        assert all(len(t) <= 25 and len(a) <= 35 and len(b) <= 35 for t, a, b, _ in links)
    assert all(len(h) <= 25 and len(d) <= 25 for h, d, _ in CHOIR_PRICES)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    check_limits()
    c = GoogleAdsClient.load_from_storage()
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    ops, changes, temp = [], [], iter(range(-1, -1000, -1))

    def new_op():
        o = c.get_type("MutateOperation"); ops.append(o); return o

    def search(query):
        return list(ga.search(customer_id=CUSTOMER_ID, query=query))

    names = {r.campaign.id: r.campaign.name for r in search(
        f"SELECT campaign.id, campaign.name FROM campaign WHERE campaign.id IN ({FUNERAL}, {WEDDING}, {CHRISTMAS})")}
    xmas_ag = search(f"SELECT ad_group.id FROM ad_group WHERE campaign.id = {CHRISTMAS} AND ad_group.name = 'Hire carol singers'")[0].ad_group.id
    NEW_KEYWORDS[xmas_ag] = NEW_KEYWORDS.pop("Hire carol singers")
    camp_of_ag = {FUNERAL_AG: FUNERAL, WEDDING_AG: WEDDING, xmas_ag: CHRISTMAS}

    # 1. Account callouts
    for r in search("SELECT customer_asset.resource_name, asset.id, asset.callout_asset.callout_text FROM customer_asset "
                    "WHERE customer_asset.field_type = 'CALLOUT' AND customer_asset.status = 'ENABLED'"):
        if r.asset.id in PAUSE_CALLOUTS:
            o = new_op().customer_asset_operation
            o.update.resource_name = r.customer_asset.resource_name
            o.update.status = E.AssetLinkStatusEnum.PAUSED
            o.update_mask.paths.append("status")
            changes.append(("account callout", f'"{r.asset.callout_asset.callout_text}"', "enabled → paused", PAUSE_CALLOUTS[r.asset.id]))
    for text in NEW_CALLOUTS:
        rn = ga.asset_path(CUSTOMER_ID, next(temp))
        a = new_op().asset_operation.create; a.resource_name = rn; a.callout_asset.callout_text = text
        ca = new_op().customer_asset_operation.create; ca.asset = rn; ca.field_type = E.AssetFieldTypeEnum.CALLOUT
    changes.append(("account callouts", "new", "added: " + ", ".join(NEW_CALLOUTS), "Accurate replacements, all supported by pricing.html"))

    # 2. Sitelinks
    for r in search(f"SELECT campaign.id, campaign_asset.resource_name, asset.id, asset.sitelink_asset.link_text FROM campaign_asset "
                    f"WHERE campaign.id IN ({FUNERAL}, {WEDDING}) AND campaign_asset.status = 'ENABLED' AND campaign_asset.field_type = 'SITELINK'"):
        if r.asset.id in PAUSE_SITELINKS:
            o = new_op().campaign_asset_operation
            o.update.resource_name = r.campaign_asset.resource_name
            o.update.status = E.AssetLinkStatusEnum.PAUSED
            o.update_mask.paths.append("status")
            changes.append((names[r.campaign.id], f'sitelink "{r.asset.sitelink_asset.link_text}"', "enabled → paused", PAUSE_SITELINKS[r.asset.id][1]))
    for camp, links in NEW_SITELINKS.items():
        for text, d1, d2, url in links:
            rn = ga.asset_path(CUSTOMER_ID, next(temp))
            a = new_op().asset_operation.create; a.resource_name = rn; a.final_urls.append(url)
            a.sitelink_asset.link_text = text; a.sitelink_asset.description1 = d1; a.sitelink_asset.description2 = d2
            ca = new_op().campaign_asset_operation.create
            ca.campaign = ga.campaign_path(CUSTOMER_ID, camp); ca.asset = rn; ca.field_type = E.AssetFieldTypeEnum.SITELINK
        changes.append((names[camp], "sitelinks", "added: " + ", ".join(t for t, *_ in links), "Accurate, choir-focused replacements"))

    # 3. Price asset + structured snippet for wedding and funeral
    price_rn = ga.asset_path(CUSTOMER_ID, next(temp))
    a = new_op().asset_operation.create; a.resource_name = price_rn
    a.price_asset.type_ = E.PriceExtensionTypeEnum.SERVICES; a.price_asset.language_code = "en"
    for h, d, price in CHOIR_PRICES:
        po = c.get_type("PriceOffering"); po.header = h; po.description = d
        po.price.amount_micros = price * 1_000_000; po.price.currency_code = "GBP"
        po.unit = E.PriceExtensionPriceUnitEnum.UNSPECIFIED; po.final_url = SITE + "pricing.html"
        a.price_asset.price_offerings.append(po)
    snip_rn = ga.asset_path(CUSTOMER_ID, next(temp))
    a = new_op().asset_operation.create; a.resource_name = snip_rn
    a.structured_snippet_asset.header = SNIPPET[0]; a.structured_snippet_asset.values.extend(SNIPPET[1])
    for camp in (FUNERAL, WEDDING):
        for rn, ft in ((price_rn, E.AssetFieldTypeEnum.PRICE), (snip_rn, E.AssetFieldTypeEnum.STRUCTURED_SNIPPET)):
            ca = new_op().campaign_asset_operation.create
            ca.campaign = ga.campaign_path(CUSTOMER_ID, camp); ca.asset = rn; ca.field_type = ft
        changes.append((names[camp], "price + snippet assets", "none → choir prices £1,150–£3,000; Types: quartets to choruses",
                        "Shows choir sizes and prices up front, filters out solo and budget searches"))

    # 4. Keywords: pause solo-intent and broad match in wedding/funeral; add choir replacements
    for camp, ag in ((FUNERAL, FUNERAL_AG), (WEDDING, WEDDING_AG)):
        paused = []
        for r in search(f"SELECT ad_group_criterion.resource_name, ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type "
                        f"FROM ad_group_criterion WHERE ad_group.id = {ag} AND ad_group_criterion.type = 'KEYWORD' "
                        f"AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED'"):
            k = r.ad_group_criterion
            if COMPETITOR.search(k.keyword.text.lower()):
                continue
            if SOLO.search(k.keyword.text.lower()) or k.keyword.match_type.name == "BROAD":
                o = new_op().ad_group_criterion_operation
                o.update.resource_name = k.resource_name
                o.update.status = E.AdGroupCriterionStatusEnum.PAUSED
                o.update_mask.paths.append("status")
                paused.append(f"{k.keyword.text} ({k.keyword.match_type.name.lower()})")
        changes.append((names[camp], f"keywords paused ({len(paused)})", "; ".join(paused),
                        "Singer/soloist intent (owner: choir bookings only) or broad match"))
    existing = {(r.ad_group.id, r.ad_group_criterion.keyword.text.lower(), r.ad_group_criterion.keyword.match_type.name) for r in search(
        f"SELECT ad_group.id, ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type FROM ad_group_criterion "
        f"WHERE ad_group.id IN ({FUNERAL_AG}, {WEDDING_AG}, {xmas_ag}) AND ad_group_criterion.type = 'KEYWORD' "
        f"AND ad_group_criterion.status != 'REMOVED'")}
    for ag, kws in NEW_KEYWORDS.items():
        added = []
        for text, mt in kws:
            if (ag, text, mt) in existing:
                continue
            k = new_op().ad_group_criterion_operation.create
            k.ad_group = ga.ad_group_path(CUSTOMER_ID, ag); k.status = E.AdGroupCriterionStatusEnum.ENABLED
            k.keyword.text = text; k.keyword.match_type = E.KeywordMatchTypeEnum[mt]
            added.append(f"{text} ({mt.lower()})")
        if added:
            reason = ("Head carol terms: 170, 70 and 320 searches/mo in Greater London, peaking at 880–2,900 in December"
                      if ag == xmas_ag else "Choir-intent replacements for paused broad match")
            changes.append((names[camp_of_ag[ag]], f"keywords added ({len(added)})", ", ".join(added), reason))

    # 5. Negatives on all three campaigns
    for camp in (FUNERAL, WEDDING, CHRISTMAS):
        have = {r.campaign_criterion.keyword.text.lower() for r in search(
            f"SELECT campaign_criterion.keyword.text FROM campaign_criterion WHERE campaign.id = {camp} "
            f"AND campaign_criterion.negative = TRUE AND campaign_criterion.type = 'KEYWORD'")}
        new = [n for n in NEGATIVES if n not in have]
        for n in new:
            cc = new_op().campaign_criterion_operation.create
            cc.campaign = ga.campaign_path(CUSTOMER_ID, camp); cc.negative = True
            cc.keyword.text = n; cc.keyword.match_type = E.KeywordMatchTypeEnum.BROAD
        if new:
            changes.append((names[camp], "negative keywords", "+" + ", ".join(new), "Blocks solo searches; 'singer' leaves 'carol singers' untouched"))

    # 6. New choir-only RSA per ad group; pause the old ads
    for ag, spec in ADS.items():
        camp = camp_of_ag[ag]
        old = search(f"SELECT ad_group_ad.resource_name FROM ad_group_ad WHERE ad_group.id = {ag} AND ad_group_ad.status = 'ENABLED'")
        for r in old:
            o = new_op().ad_group_ad_operation
            o.update.resource_name = r.ad_group_ad.resource_name
            o.update.status = E.AdGroupAdStatusEnum.PAUSED
            o.update_mask.paths.append("status")
        ad = new_op().ad_group_ad_operation.create
        ad.ad_group = ga.ad_group_path(CUSTOMER_ID, ag); ad.status = E.AdGroupAdStatusEnum.ENABLED
        ad.ad.final_urls.append(spec["url"])
        rsa = ad.ad.responsive_search_ad; rsa.path1, rsa.path2 = spec["path"]
        for i, h in enumerate(spec["pinned"] + spec["headlines"]):
            t = c.get_type("AdTextAsset"); t.text = h
            if i < len(spec["pinned"]):
                t.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1
            rsa.headlines.append(t)
        for d in spec["descriptions"]:
            t = c.get_type("AdTextAsset"); t.text = d; rsa.descriptions.append(t)
        changes.append((names[camp], f"ad ({len(old)} old paused)", f"new choir-only RSA → {spec['url']}",
                        spec["reason"]))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operations\n")
    for res, field, what, why in changes:
        print(f"• {res} · {field}\n    {what}\n    reason: {why}")
    req = c.get_type("MutateGoogleAdsRequest")
    req.customer_id = CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = not args.apply
    try:
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            loc = ".".join(f"{p.field_name}[{p.index}]" if p.index else p.field_name for p in err.location.field_path_elements)
            print("REJECTED:", err.error_code, err.message, "@", loc)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    rows = "".join(f"| {now} | {res} | {field} | {what} | {why} | `{SCRIPT}` |\n" for res, field, what, why in changes)
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
