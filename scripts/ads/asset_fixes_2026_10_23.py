#!/usr/bin/env python3
"""23 Oct 2026 change set 3: asset fixes found by the ads review.

a. Price asset 424863736833 (funeral expert campaign, wedding-leads): price qualifier
   unspecified → "From". pricing.html gives every ensemble as "From £…". Changed in place;
   if Google refuses, --price-fallback creates a copy with the same five offerings plus
   "From", links it where the old one is enabled and pauses the old links.
   The Christmas price asset (424775774227) is left alone: christmas-pricing.html gives
   flat two-hour prices ("Price for two hours", £1,150 …), not "from" prices.
b. Wedding sitelink "Our Repertoire" (348880851148): final URL listen.html →
   music-guides/wedding-choral-repertoire.html (a list of choral wedding pieces by ceremony
   moment; "Hear Our Choirs" already sends people to listen.html), with descriptions that
   are true on that page. Changed in place when wedding-leads is the only campaign
   linking it; if any other campaign links it (or --sitelink-fallback), a new sitelink is
   created and swapped in on wedding-leads only, and the old link there is paused.
c. funeral expert campaign: two new sitelinks (4 → 6, as Google asks), "Funeral Choir
   Guide" and "Short-Notice Funerals", each to its music guide.
d. Account: business name "The London Choral Service" (the existing text asset
   348134569764) linked as BUSINESS_NAME on the customer. --campaign-level links it to
   the three enabled campaigns instead, if Google wants it there.

Every current value is checked against the account first; any difference stops the
script before anything is sent. One atomic request. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/asset_fixes_2026_10_23.py                 # validate
    python scripts/ads/asset_fixes_2026_10_23.py --apply         # after approval
    add --price-fallback / --sitelink-fallback / --campaign-level if Google refuses a part
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
FUNERAL, WEDDING, CHRISTMAS = 23735776277, 23739971001, 24295921372
NAMES = {FUNERAL: "funeral expert campaign", WEDDING: "wedding-leads",
         CHRISTMAS: "Christmas carol singers – events 2026"}
SITE = "https://londonchoralservice.com/"
SCRIPT = "scripts/ads/asset_fixes_2026_10_23.py"

PRICE_ASSET, XMAS_PRICE_ASSET = 424863736833, 424775774227
PRICE_OFFERINGS = [("Small Choir (4)", 1_150), ("Quintet (5)", 1_400), ("Sextet (6)", 1_600),
                   ("Full Choir (8)", 2_000), ("Chorus (12)", 3_000)]

REPERTOIRE = 348880851148
REP_OLD = {"link_text": "Our Repertoire", "url": SITE + "listen.html",
           "d1": "Hymns, anthems and ceremony music.", "d2": "Browse our full wedding list."}
REP_NEW = {"url": SITE + "music-guides/wedding-choral-repertoire.html",
           "d1": "Pieces for arrivals and signing", "d2": "Ave Maria, Rutter, Gjeilo and more"}

FUNERAL_SITELINKS_NOW = {348071213212, 424677730988, 424863742104, 424863742110}
NEW_FUNERAL_SITELINKS = [
    ("Funeral Choir Guide", SITE + "music-guides/funeral-choir-guide.html",
     "Choir sizes from four to twelve", "Hymns, solo and choral pieces"),
    ("Short-Notice Funerals", SITE + "music-guides/last-minute-funeral-singers.html",
     "We confirm availability same day", "No extra charge for short notice"),
]

BUSINESS_NAME_ASSET, BUSINESS_NAME = 348134569764, "The London Choral Service"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--price-fallback", action="store_true",
                    help="create a new price asset with 'From' instead of changing the old one")
    ap.add_argument("--sitelink-fallback", action="store_true",
                    help="create a new repertoire sitelink instead of changing the old one")
    ap.add_argument("--campaign-level", action="store_true",
                    help="link the business name to the three campaigns instead of the account")
    args = ap.parse_args()
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    ops, changes = [], []  # changes: (scope, resource, field, current → new, reason)
    tmp_ids = iter(range(-1, -100, -1))

    def mop():
        op = c.get_type("MutateOperation")
        ops.append(op)
        return op

    def links_of(asset_id, field_type):
        return {r.campaign.id: r.campaign_asset for r in q(
            "SELECT campaign.id, campaign.status, campaign_asset.resource_name, campaign_asset.status FROM campaign_asset "
            f"WHERE asset.id = {asset_id} AND campaign_asset.field_type = '{field_type}' "
            "AND campaign_asset.status != 'REMOVED' AND campaign.status != 'REMOVED'")}

    # --- a. price asset qualifier ---------------------------------------------------
    rows = q("SELECT asset.id, asset.resource_name, asset.type, asset.price_asset.type, asset.price_asset.price_qualifier, "
             "asset.price_asset.language_code, asset.price_asset.price_offerings FROM asset "
             f"WHERE asset.id IN ({PRICE_ASSET}, {XMAS_PRICE_ASSET})")
    price = {r.asset.id: r.asset for r in rows}
    pa = price.get(PRICE_ASSET)
    if pa is None or pa.type_.name != "PRICE":
        raise SystemExit(f"price asset {PRICE_ASSET} not found; nothing sent")
    if pa.price_asset.price_qualifier.name != "UNSPECIFIED":
        raise SystemExit(f"price asset {PRICE_ASSET} qualifier is {pa.price_asset.price_qualifier.name}, "
                         "not UNSPECIFIED; nothing sent")
    got = [(o.header, o.price.amount_micros // 1_000_000) for o in pa.price_asset.price_offerings]
    if got != PRICE_OFFERINGS or any(o.price.currency_code != "GBP" for o in pa.price_asset.price_offerings):
        raise SystemExit(f"price asset {PRICE_ASSET} offerings are {got}, not {PRICE_OFFERINGS}; nothing sent")
    price_links = {k: v for k, v in links_of(PRICE_ASSET, "PRICE").items() if v.status.name == "ENABLED"}
    if set(price_links) != {FUNERAL, WEDDING}:
        raise SystemExit(f"price asset {PRICE_ASSET} is enabled on {sorted(price_links)}, not funeral + wedding; nothing sent")
    offer_list = ", ".join(f"{h} £{p:,}" for h, p in PRICE_OFFERINGS)
    if not args.price_fallback:
        op = mop()
        op.asset_operation.update.resource_name = pa.resource_name
        op.asset_operation.update.price_asset.price_qualifier = E.PriceExtensionPriceQualifierEnum.FROM
        op.asset_operation.update_mask.paths.append("price_asset.price_qualifier")
        changes.append(("funeral expert campaign + wedding-leads", f"price asset ({PRICE_ASSET}: {offer_list})",
                        "price qualifier", "unspecified → From",
                        'pricing.html gives every ensemble as "From £…"; travel outside Greater London is added to the quote'))
    else:
        tmp = ga.asset_path(CUSTOMER_ID, str(next(tmp_ids)))
        op = mop()
        new = op.asset_operation.create
        new.resource_name = tmp
        new.price_asset.type_ = pa.price_asset.type_
        new.price_asset.language_code = pa.price_asset.language_code
        new.price_asset.price_qualifier = E.PriceExtensionPriceQualifierEnum.FROM
        for o in pa.price_asset.price_offerings:
            n = c.get_type("PriceOffering")
            n.header, n.description, n.final_url = o.header, o.description, o.final_url
            n.price.currency_code, n.price.amount_micros = o.price.currency_code, o.price.amount_micros
            n.unit = o.unit
            new.price_asset.price_offerings.append(n)
        changes.append(("account", "price asset (new)", "create",
                        f"none → copy of {PRICE_ASSET} ({offer_list}, same descriptions and URLs) with qualifier From",
                        "Google refused to change the old asset's qualifier"))
        for cid in (FUNERAL, WEDDING):
            op = mop()
            op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, cid)
            op.campaign_asset_operation.create.asset = tmp
            op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.PRICE
            op = mop()
            op.campaign_asset_operation.update.resource_name = price_links[cid].resource_name
            op.campaign_asset_operation.update.status = E.AssetLinkStatusEnum.PAUSED
            op.campaign_asset_operation.update_mask.paths.append("status")
            changes.append((f'campaign "{NAMES[cid]}"', "price asset", "link",
                            f"{PRICE_ASSET} enabled → paused; new From copy linked", 'prices shown as "From"'))
    xa = price.get(XMAS_PRICE_ASSET)
    xmas_note = (f"unchanged: Christmas price asset {XMAS_PRICE_ASSET} (qualifier "
                 f"{xa.price_asset.price_qualifier.name if xa else 'not found'}): christmas-pricing.html gives flat "
                 'two-hour prices ("Price for two hours", £1,150 …), not "from" prices')

    # --- b. wedding repertoire sitelink -------------------------------------------
    rows = q("SELECT asset.id, asset.resource_name, asset.final_urls, asset.sitelink_asset.link_text, "
             "asset.sitelink_asset.description1, asset.sitelink_asset.description2 FROM asset "
             f"WHERE asset.id = {REPERTOIRE}")
    if len(rows) != 1:
        raise SystemExit(f"sitelink {REPERTOIRE} not found; nothing sent")
    rep = rows[0].asset
    now_rep = {"link_text": rep.sitelink_asset.link_text, "url": list(rep.final_urls),
               "d1": rep.sitelink_asset.description1, "d2": rep.sitelink_asset.description2}
    want = dict(REP_OLD, url=[REP_OLD["url"]])
    if now_rep != want:
        raise SystemExit(f"sitelink {REPERTOIRE} is {now_rep}, not {want}; nothing sent")
    rep_links = links_of(REPERTOIRE, "SITELINK")
    if WEDDING not in rep_links or rep_links[WEDDING].status.name != "ENABLED":
        raise SystemExit(f"sitelink {REPERTOIRE} is not enabled on wedding-leads; nothing sent")
    shared = sorted(set(rep_links) - {WEDDING})
    cust_rep = q(f"SELECT customer_asset.status FROM customer_asset WHERE asset.id = {REPERTOIRE} "
                 "AND customer_asset.status != 'REMOVED'")
    ag_rep = q(f"SELECT ad_group_asset.status FROM ad_group_asset WHERE asset.id = {REPERTOIRE} "
               "AND ad_group_asset.status != 'REMOVED'")
    rep_old_txt = f'"{REP_OLD["d1"]}" / "{REP_OLD["d2"]}", {REP_OLD["url"]}'
    rep_new_txt = f'"{REP_NEW["d1"]}" / "{REP_NEW["d2"]}", {REP_NEW["url"]}'
    rep_why = ("listen.html is already the 'Hear Our Choirs' sitelink; the repertoire page lists choral pieces by "
               "ceremony moment (arrivals, signing, after the vows) but no hymns, and it is not a full list")
    if not (shared or cust_rep or ag_rep or args.sitelink_fallback):
        op = mop()
        u = op.asset_operation.update
        u.resource_name = rep.resource_name
        u.final_urls.append(REP_NEW["url"])
        u.sitelink_asset.description1 = REP_NEW["d1"]
        u.sitelink_asset.description2 = REP_NEW["d2"]
        op.asset_operation.update_mask.paths.extend(
            ["final_urls", "sitelink_asset.description1", "sitelink_asset.description2"])
        changes.append(('campaign "wedding-leads" (only campaign linking it)', f'sitelink "Our Repertoire" ({REPERTOIRE})',
                        "final URL + descriptions", f"{rep_old_txt} → {rep_new_txt}", rep_why))
    else:
        if shared or cust_rep or ag_rep:
            print(f"note: sitelink {REPERTOIRE} is also linked to campaigns {shared}, "
                  f"{len(cust_rep)} account link(s), {len(ag_rep)} ad group link(s): not changed in place\n")
        tmp = ga.asset_path(CUSTOMER_ID, str(next(tmp_ids)))
        op = mop()
        new = op.asset_operation.create
        new.resource_name = tmp
        new.final_urls.append(REP_NEW["url"])
        new.sitelink_asset.link_text = REP_OLD["link_text"]
        new.sitelink_asset.description1 = REP_NEW["d1"]
        new.sitelink_asset.description2 = REP_NEW["d2"]
        op = mop()
        op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, WEDDING)
        op.campaign_asset_operation.create.asset = tmp
        op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.SITELINK
        op = mop()
        op.campaign_asset_operation.update.resource_name = rep_links[WEDDING].resource_name
        op.campaign_asset_operation.update.status = E.AssetLinkStatusEnum.PAUSED
        op.campaign_asset_operation.update_mask.paths.append("status")
        changes.append(('campaign "wedding-leads"', 'sitelink "Our Repertoire" (new)', "create + link",
                        f"none → {rep_new_txt}", rep_why))
        changes.append(('campaign "wedding-leads"', f'sitelink "Our Repertoire" ({REPERTOIRE})', "link status",
                        "enabled → paused", "replaced by the new \"Our Repertoire\" sitelink"))

    # --- c. two more funeral sitelinks --------------------------------------------
    fl = {r.asset.id: r for r in q(
        "SELECT campaign.id, asset.id, asset.final_urls, asset.sitelink_asset.link_text, campaign_asset.status FROM campaign_asset "
        f"WHERE campaign.id = {FUNERAL} AND campaign_asset.field_type = 'SITELINK' AND campaign_asset.status != 'REMOVED'")}
    enabled = {a for a, r in fl.items() if r.campaign_asset.status.name == "ENABLED"}
    if enabled != FUNERAL_SITELINKS_NOW:
        raise SystemExit(f"funeral campaign's enabled sitelinks are {sorted(enabled)}, not {sorted(FUNERAL_SITELINKS_NOW)}; "
                         "nothing sent")
    for text, url, d1, d2 in NEW_FUNERAL_SITELINKS:
        for r in fl.values():
            if r.asset.sitelink_asset.link_text == text or url in r.asset.final_urls:
                raise SystemExit(f'the funeral campaign already has a sitelink "{r.asset.sitelink_asset.link_text}" '
                                 f"({r.asset.id}) for {text} / {url}; nothing sent")
        tmp = ga.asset_path(CUSTOMER_ID, str(next(tmp_ids)))
        op = mop()
        new = op.asset_operation.create
        new.resource_name = tmp
        new.final_urls.append(url)
        new.sitelink_asset.link_text = text
        new.sitelink_asset.description1 = d1
        new.sitelink_asset.description2 = d2
        op = mop()
        op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, FUNERAL)
        op.campaign_asset_operation.create.asset = tmp
        op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.SITELINK
        changes.append(('campaign "funeral expert campaign"', f'sitelink "{text}" (new)', "create + link",
                        f'none → "{text}" / "{d1}" / "{d2}", {url}',
                        "the campaign has 4 enabled sitelinks; Google asks for 6"))

    # --- d. business name -----------------------------------------------------------
    rows = q(f"SELECT asset.resource_name, asset.type, asset.text_asset.text FROM asset WHERE asset.id = {BUSINESS_NAME_ASSET}")
    if len(rows) != 1 or rows[0].asset.type_.name != "TEXT" or rows[0].asset.text_asset.text != BUSINESS_NAME:
        raise SystemExit(f'text asset {BUSINESS_NAME_ASSET} is not "{BUSINESS_NAME}"; nothing sent')
    bn = rows[0].asset.resource_name
    have = q("SELECT customer_asset.resource_name, asset.id FROM customer_asset "
             "WHERE customer_asset.field_type = 'BUSINESS_NAME' AND customer_asset.status != 'REMOVED'")
    have += q("SELECT campaign.id, campaign.status, asset.id FROM campaign_asset WHERE campaign_asset.field_type = 'BUSINESS_NAME' "
              "AND campaign_asset.status != 'REMOVED' AND campaign.status != 'REMOVED'")
    if have:
        raise SystemExit(f"a business name is already linked ({len(have)} link(s)); nothing sent")
    if not args.campaign_level:
        op = mop()
        op.customer_asset_operation.create.asset = bn
        op.customer_asset_operation.create.field_type = E.AssetFieldTypeEnum.BUSINESS_NAME
        changes.append((f"account {CUSTOMER_ID}", f"business name (text asset {BUSINESS_NAME_ASSET})", "link",
                        f'none → "{BUSINESS_NAME}" ({len(BUSINESS_NAME)} chars)',
                        "no business name is set; Google can show it with the logo, already linked to all three campaigns"))
    else:
        for cid in (FUNERAL, WEDDING, CHRISTMAS):
            op = mop()
            op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, cid)
            op.campaign_asset_operation.create.asset = bn
            op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.BUSINESS_NAME
            changes.append((f'campaign "{NAMES[cid]}"', f"business name (text asset {BUSINESS_NAME_ASSET})", "link",
                            f'none → "{BUSINESS_NAME}" ({len(BUSINESS_NAME)} chars)',
                            "no business name is set; Google would not take it at account level"))

    # --- send -------------------------------------------------------------------
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for scope, res, field, what, why in changes:
        print(f"• {scope} · {res} · {field}: {what}\n    reason: {why}")
    print(f"• {xmas_note}")
    try:
        req = c.get_type("MutateGoogleAdsRequest")
        req.customer_id = CUSTOMER_ID
        req.mutate_operations.extend(ops)
        req.validate_only = not args.apply
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            idx = [f.index for f in err.location.field_path_elements if f.field_name == "mutate_operations"]
            print("REJECTED:", f"operation {idx[0]}:" if idx else "", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("\nGoogle accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    for scope, res, field, what, why in reversed(changes):
        ads_log.append_row(f"| {now} | {scope} {res} | {field} | {what} | {why} | `{SCRIPT}` |")
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
