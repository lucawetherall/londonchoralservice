#!/usr/bin/env python3
"""23 Oct 2026 change set 4: take "no extras" out of the funeral and wedding ads.

Since 4 Oct both campaigns also show in Surrey, Kent, Essex, Hertfordshire, Berkshire and
Buckinghamshire, and pricing.html says travel beyond Greater London is added to the written
quote. "No extras" and "nothing on top" are therefore false for part of the audience.

1. Both enabled RSAs (funeral 826000407483, wedding 826000407486), edited in place with every
   other headline, description and pin resent exactly as it is:
   headline "No VAT Added, No Extras" → "Full Cost Quoted Upfront";
   description "… No VAT added and nothing on top." → "… Travel within London included.";
   funeral only: "… and sing 3 pieces." → "… and sing up to three pieces." (funerals.html says
   "up to three choral or solo pieces").
2. Sitelinks "Funeral Choir Prices" (424863742104) and "Wedding Choir Prices" (424779985660):
   description 2 "No VAT added, no extras" → "No VAT, travel in London included", in place. If
   Google refuses, --fallback creates replacements and swaps them in, pausing the old links.

Before sending, the script scans every enabled RSA in the two campaigns and every enabled
sitelink and callout linked to them or to the account, and stops if any text it is not
fixing still says "no extras", "nothing on top" or "all in".

    source .venv/bin/activate
    python scripts/ads/no_extras_fix_2026_10_23.py              # validate
    python scripts/ads/no_extras_fix_2026_10_23.py --apply      # after approval
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
FUNERAL, WEDDING = 23735776277, 23739971001
NAMES = {FUNERAL: "funeral expert campaign", WEDDING: "wedding-leads"}
ADS = {826000407483: FUNERAL, 826000407486: WEDDING}
SCRIPT = "scripts/ads/no_extras_fix_2026_10_23.py"

HEADLINES = {"No VAT Added, No Extras": "Full Cost Quoted Upfront"}
DESCRIPTIONS = {
    "Quintet £1,400, sextet £1,600, choir of eight £2,000. No VAT added and nothing on top.":
        "Quintet £1,400, sextet £1,600, choir of eight £2,000. Travel within London included.",
    "A funeral choir from £1,150: four professional voices lead the hymns and sing 3 pieces.":
        "A funeral choir from £1,150: four voices lead the hymns and sing up to three pieces.",
}
WHY = {
    "No VAT Added, No Extras": "travel beyond Greater London is added to the quote, and the campaign now shows in six "
                               "home counties; funerals.html/weddings.html: 'A written quote, confirmed before you "
                               "commit' (neither page mentions VAT; the account callout 'No VAT Added' stays)",
    "Quintet £1,400, sextet £1,600, choir of eight £2,000. No VAT added and nothing on top.":
        "'nothing on top' is false outside Greater London; landing pages: 'All ensemble sizes include preparation, "
        "travel within London, and a music director on the day'",
    "A funeral choir from £1,150: four professional voices lead the hymns and sing 3 pieces.":
        "funerals.html: 'perform up to three choral or solo pieces', not exactly three",
}
SITELINKS = {424863742104: ("Funeral Choir Prices", FUNERAL), 424779985660: ("Wedding Choir Prices", WEDDING)}
SL_OLD = {"url": "https://londonchoralservice.com/pricing.html", "d1": "Four voices from £1,150",
          "d2": "No VAT added, no extras"}
SL_NEW_D2 = "No VAT, travel in London included"
# "no extras" (plural): set 3's "No extra charge for short notice" is a narrower, true claim and must not trip this
FLAG = re.compile(r"\bno extras\b|nothing on top|\ball[- ]in\b|nothing (else|more) to pay", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--fallback", action="store_true",
                    help="create replacement price sitelinks instead of changing the old ones")
    args = ap.parse_args()
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    ops, changes = [], []  # changes: (scope, resource, field, current → new, reason)
    fixing = set(HEADLINES) | set(DESCRIPTIONS) | {SL_OLD["d2"]}

    def mop():
        op = c.get_type("MutateOperation")
        ops.append(op)
        return op

    # --- scan: every enabled text in the two campaigns and the account ---------------
    ads = q("SELECT campaign.id, ad_group.name, ad_group_ad.ad.id, ad_group_ad.ad.resource_name, "
            "ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions "
            f"FROM ad_group_ad WHERE campaign.id IN ({FUNERAL}, {WEDDING}) AND ad_group_ad.status = 'ENABLED' "
            "AND ad_group.status = 'ENABLED' AND ad_group_ad.ad.type = 'RESPONSIVE_SEARCH_AD'")
    found = {r.ad_group_ad.ad.id: r for r in ads}
    if set(found) != set(ADS):
        raise SystemExit(f"enabled RSAs in the two campaigns are {sorted(found)}, not {sorted(ADS)}; nothing sent")
    texts = []  # (where, text)
    for r in ads:
        rsa = r.ad_group_ad.ad.responsive_search_ad
        texts += [(f"ad {r.ad_group_ad.ad.id} headline", h.text) for h in rsa.headlines]
        texts += [(f"ad {r.ad_group_ad.ad.id} description", d.text) for d in rsa.descriptions]
    for r in q("SELECT campaign.id, asset.id, asset.type, asset.sitelink_asset.link_text, asset.sitelink_asset.description1, "
               "asset.sitelink_asset.description2, asset.callout_asset.callout_text FROM campaign_asset "
               f"WHERE campaign.id IN ({FUNERAL}, {WEDDING}) AND campaign_asset.status = 'ENABLED' "
               "AND asset.type IN ('SITELINK', 'CALLOUT')"):
        a = r.asset
        texts += [(f"{a.type_.name.lower()} {a.id}", t) for t in (
            a.sitelink_asset.link_text, a.sitelink_asset.description1, a.sitelink_asset.description2,
            a.callout_asset.callout_text) if t]
    for r in q("SELECT asset.id, asset.type, asset.sitelink_asset.link_text, asset.sitelink_asset.description1, "
               "asset.sitelink_asset.description2, asset.callout_asset.callout_text FROM customer_asset "
               "WHERE customer_asset.status = 'ENABLED' AND asset.type IN ('SITELINK', 'CALLOUT')"):
        a = r.asset
        texts += [(f"account {a.type_.name.lower()} {a.id}", t) for t in (
            a.sitelink_asset.link_text, a.sitelink_asset.description1, a.sitelink_asset.description2,
            a.callout_asset.callout_text) if t]
    stray = [(w, t) for w, t in texts if FLAG.search(t) and t not in fixing]
    if stray:
        raise SystemExit("other enabled texts also promise no extras, not covered by this script; nothing sent:\n"
                         + "\n".join(f"  {w}: {t!r}" for w, t in stray))
    hits = [(w, t) for w, t in texts if t in fixing]
    print(f"scan: {len(texts)} enabled texts checked; {len(hits)} to fix, no others say no extras / nothing on top / all in\n")

    # --- 1. RSAs, edited in place ------------------------------------------------------
    for ad_id, cid in ADS.items():
        r = found[ad_id]
        rsa = r.ad_group_ad.ad.responsive_search_ad
        h_old = [h.text for h in rsa.headlines]
        d_old = [d.text for d in rsa.descriptions]
        todo_h = [t for t in h_old if t in HEADLINES]
        todo_d = [t for t in d_old if t in DESCRIPTIONS]
        # The 23 Oct 15:32 copy refresh (PR #287) already replaced the "No VAT Added, No Extras" headline;
        # the descriptions and sitelinks below still carry the claim.
        if not any("nothing on top" in t for t in todo_d):
            raise SystemExit(f'ad {ad_id} lacks the "nothing on top" description; nothing sent')
        h_new = [HEADLINES.get(t, t) for t in h_old]
        d_new = [DESCRIPTIONS.get(t, t) for t in d_old]
        for kind, lst in (("headline", h_new), ("description", d_new)):
            low = [t.lower() for t in lst]
            if len(set(low)) != len(low):
                raise SystemExit(f"ad {ad_id} would have a duplicate {kind}; nothing sent")
        if any(len(t) > 30 for t in h_new) or any(len(t) > 90 for t in d_new):
            raise SystemExit(f"ad {ad_id}: a new text is over Google's limit; nothing sent")
        op = mop()
        ad = op.ad_operation.update
        ad.resource_name = r.ad_group_ad.ad.resource_name
        for h in rsa.headlines:
            t = c.get_type("AdTextAsset")
            t.text = HEADLINES.get(h.text, h.text)
            if h.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN"):
                t.pinned_field = h.pinned_field
            ad.responsive_search_ad.headlines.append(t)
        for d in rsa.descriptions:
            t = c.get_type("AdTextAsset")
            t.text = DESCRIPTIONS.get(d.text, d.text)
            if d.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN"):
                t.pinned_field = d.pinned_field
            ad.responsive_search_ad.descriptions.append(t)
        op.ad_operation.update_mask.paths.extend(["responsive_search_ad.headlines", "responsive_search_ad.descriptions"])
        pins = [f'"{h.text}" → {h.pinned_field.name}' for h in rsa.headlines if h.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN")]
        pins += [f'"{d.text[:30]}…" → {d.pinned_field.name}' for d in rsa.descriptions if d.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN")]
        for old in todo_h:
            changes.append((f'campaign "{NAMES[cid]}"', f'ad {ad_id} in "{r.ad_group.name}"', "headline",
                            f'"{old}" → "{HEADLINES[old]}" ({len(HEADLINES[old])} chars, unpinned as before)', WHY[old]))
        for old in todo_d:
            changes.append((f'campaign "{NAMES[cid]}"', f'ad {ad_id} in "{r.ad_group.name}"', "description",
                            f'"{old}" → "{DESCRIPTIONS[old]}" ({len(DESCRIPTIONS[old])} chars, unpinned as before)', WHY[old]))
        print(f"ad {ad_id}: {len(h_new)} headlines and {len(d_new)} descriptions resent; pins kept: {'; '.join(pins) or 'none'}")
    print()

    # --- 2. price sitelinks ------------------------------------------------------------
    rows = {r.asset.id: r.asset for r in q(
        "SELECT asset.id, asset.resource_name, asset.final_urls, asset.sitelink_asset.link_text, "
        "asset.sitelink_asset.description1, asset.sitelink_asset.description2 FROM asset "
        f"WHERE asset.id IN ({', '.join(map(str, SITELINKS))})")}
    for aid, (text, cid) in SITELINKS.items():
        a = rows.get(aid)
        cur = a and (a.sitelink_asset.link_text, list(a.final_urls), a.sitelink_asset.description1, a.sitelink_asset.description2)
        want = (text, [SL_OLD["url"]], SL_OLD["d1"], SL_OLD["d2"])
        if cur != want:
            raise SystemExit(f"sitelink {aid} is {cur}, not {want}; nothing sent")
        links = {r.campaign.id: r.campaign_asset for r in q(
            "SELECT campaign.id, campaign.status, campaign_asset.resource_name, campaign_asset.status FROM campaign_asset "
            f"WHERE asset.id = {aid} AND campaign_asset.status != 'REMOVED' AND campaign.status != 'REMOVED'")}
        if cid not in links or links[cid].status.name != "ENABLED":
            raise SystemExit(f"sitelink {aid} is not enabled on {NAMES[cid]}; nothing sent")
        others = sorted(set(links) - {cid})
        if others:
            print(f"note: sitelink {aid} is also linked to {others}; the in-place change reaches them too\n")
        why = ("travel beyond Greater London is added to the quote; pricing.html lists 'Travel within Greater London' "
               "and 'VAT, which we are not registered for and do not add' under what you are not charged for")
        if not args.fallback:
            op = mop()
            op.asset_operation.update.resource_name = a.resource_name
            op.asset_operation.update.sitelink_asset.description2 = SL_NEW_D2
            op.asset_operation.update_mask.paths.append("sitelink_asset.description2")
            changes.append((f'campaign "{NAMES[cid]}"', f'sitelink "{text}" ({aid})', "description 2",
                            f'"{SL_OLD["d2"]}" → "{SL_NEW_D2}" ({len(SL_NEW_D2)} chars)', why))
        else:
            tmp = ga.asset_path(CUSTOMER_ID, str(-1 - len(ops)))
            op = mop()
            new = op.asset_operation.create
            new.resource_name = tmp
            new.final_urls.append(SL_OLD["url"])
            new.sitelink_asset.link_text = text
            new.sitelink_asset.description1 = SL_OLD["d1"]
            new.sitelink_asset.description2 = SL_NEW_D2
            for lcid, link in links.items():
                if link.status.name != "ENABLED":
                    continue
                op = mop()
                op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, lcid)
                op.campaign_asset_operation.create.asset = tmp
                op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.SITELINK
                op = mop()
                op.campaign_asset_operation.update.resource_name = link.resource_name
                op.campaign_asset_operation.update.status = E.AssetLinkStatusEnum.PAUSED
                op.campaign_asset_operation.update_mask.paths.append("status")
            changes.append((f'campaign "{NAMES[cid]}"', f'sitelink "{text}" (new)', "create + link",
                            f'none → "{text}" / "{SL_OLD["d1"]}" / "{SL_NEW_D2}", {SL_OLD["url"]}', why))
            changes.append((f'campaign "{NAMES[cid]}"', f'sitelink "{text}" ({aid})', "link status",
                            "enabled → paused", f'replaced by the new "{text}" sitelink'))

    # --- send -------------------------------------------------------------------------
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for scope, res, field, what, why in changes:
        print(f"• {scope} · {res} · {field}: {what}\n    reason: {why}")
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
