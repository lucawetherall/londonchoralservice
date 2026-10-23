#!/usr/bin/env python3
"""23 Oct 2026 change set (second of the day): Christmas phrase bids, brand broad match, wedding case duplicates.

1. Christmas: the phrase keywords in "Carol singer prices", "Carol singers for events" and "Venue and lobby
   carols" bid the £2.50 ad group default while their exact twins bid £4 and every phrase keyword in "Hire
   carol singers" bids £3.50. Set them to £3.50. All three groups are rarely served (low search volume), so
   this costs nothing until those searches appear; the Christmas budget (£8 cap) is less than half spent.
2. funeral expert campaign: pause the six BROAD competitor-brand keywords. The enabled PHRASE keyword
   "London Funeral Singers" (£2) already matches every one of those searches ("the london funeral singers",
   "... pricing", "... cost", "... reviews"); broad match reaches beyond them at quality score 3. The brand
   stays a keyword (owner rule, 26 Sep) and never appears in ad text.
3. wedding-leads: four keyword pairs differ only in letter case, which Google ignores. Pause the twin with
   no impressions in the last 90 days and keep the one with history.

Pause only, nothing deleted. Budgets untouched. Every keyword is checked against the account first.

    .venv/bin/python scripts/ads/keyword_tidy_2026_10_23.py            # validate
    .venv/bin/python scripts/ads/keyword_tidy_2026_10_23.py --apply    # after approval
"""

import argparse
import datetime
import os
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
SILENT_GROUPS = ("Carol singer prices", "Carol singers for events", "Venue and lobby carols")
NEW_BID = 3_500_000
BRAND_BROAD = {"london funeral singers", "the london funeral singers", "londonfuneralsingers.co.uk",
               "london funeral singers pricing", "london funeral singers cost", "london funeral singers reviews"}
BRAND_PHRASE = "london funeral singers"
# (text as stored, match type) of the twin to pause; its kept twin differs only in case
WEDDING_TWINS = [("wedding choir london", "EXACT"), ("wedding choir London", "PHRASE"),
                 ("hire wedding choir London", "PHRASE"), ("wedding choir hire London", "PHRASE")]
SCRIPT = "scripts/ads/keyword_tidy_2026_10_23.py"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    rows = q("SELECT campaign.id, ad_group.name, ad_group.cpc_bid_micros, ad_group_criterion.resource_name, "
             "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, ad_group_criterion.cpc_bid_micros, "
             "ad_group_criterion.effective_cpc_bid_micros, ad_group_criterion.status FROM ad_group_criterion "
             f"WHERE campaign.id IN ({FUNERAL}, {WEDDING}, {CHRISTMAS}) AND ad_group_criterion.type = 'KEYWORD' "
             "AND ad_group_criterion.negative = FALSE AND ad_group_criterion.status = 'ENABLED'")
    impressions = {}
    for r in q("SELECT ad_group_criterion.resource_name, metrics.impressions FROM keyword_view "
               f"WHERE campaign.id = {WEDDING} AND segments.date BETWEEN "
               f"'{(datetime.date.today() - datetime.timedelta(days=90)).isoformat()}' AND '{datetime.date.today().isoformat()}'"):
        impressions[r.ad_group_criterion.resource_name] = r.metrics.impressions
    ops, changes = [], []  # changes: (campaign, resource, field, current → new, reason)

    def update(r, field, value, what, why):
        op = c.get_type("MutateOperation")
        u = op.ad_group_criterion_operation.update
        u.resource_name = r.ad_group_criterion.resource_name
        setattr(u, field, value)
        op.ad_group_criterion_operation.update_mask.paths.append(field)
        ops.append(op)
        kw = r.ad_group_criterion.keyword
        changes.append((r.campaign.id, f'ad group "{r.ad_group.name}" keyword "{kw.text}" ({kw.match_type.name.lower()})',
                        "max CPC" if field == "cpc_bid_micros" else "status", what, why))

    # 1. Christmas phrase bids
    for r in rows:
        kw = r.ad_group_criterion.keyword
        if (r.campaign.id == CHRISTMAS and r.ad_group.name in SILENT_GROUPS and kw.match_type.name == "PHRASE"
                and r.ad_group_criterion.effective_cpc_bid_micros < NEW_BID):
            cur = r.ad_group_criterion.effective_cpc_bid_micros / 1e6
            src = "" if r.ad_group_criterion.cpc_bid_micros else " (ad group default)"
            update(r, "cpc_bid_micros", NEW_BID, f"£{cur:.2f}{src} → £3.50",
                   "its exact twin bids £4 and every phrase keyword in 'Hire carol singers' £3.50; rarely served, so no cost until searched")

    # 2. brand broad match
    if not any(r.campaign.id == FUNERAL and r.ad_group_criterion.keyword.text.lower() == BRAND_PHRASE
               and r.ad_group_criterion.keyword.match_type.name == "PHRASE" for r in rows):
        raise SystemExit(f'the PHRASE keyword "{BRAND_PHRASE}" is not enabled in the funeral campaign; nothing sent')
    found = set()
    for r in rows:
        kw = r.ad_group_criterion.keyword
        if r.campaign.id == FUNERAL and kw.match_type.name == "BROAD" and kw.text.lower() in BRAND_BROAD:
            found.add(kw.text.lower())
            update(r, "status", E.AdGroupCriterionStatusEnum.PAUSED, "enabled → paused",
                   'the enabled phrase keyword "London Funeral Singers" (£2) covers these searches; broad match reaches beyond them at QS 3')
    if found != BRAND_BROAD:
        print("note: brand broad keywords not found enabled:", ", ".join(sorted(BRAND_BROAD - found)))

    # 3. wedding case twins
    for text, mt in WEDDING_TWINS:
        twin = [r for r in rows if r.campaign.id == WEDDING and r.ad_group_criterion.keyword.text == text
                and r.ad_group_criterion.keyword.match_type.name == mt]
        kept = [r for r in rows if r.campaign.id == WEDDING and r.ad_group_criterion.keyword.text != text
                and r.ad_group_criterion.keyword.text.lower() == text.lower()
                and r.ad_group_criterion.keyword.match_type.name == mt]
        if len(twin) != 1 or len(kept) != 1:
            print(f'note: "{text}" ({mt.lower()}) has no enabled case twin; left alone')
            continue
        t_imp = impressions.get(twin[0].ad_group_criterion.resource_name, 0)
        k_imp = impressions.get(kept[0].ad_group_criterion.resource_name, 0)
        if t_imp > k_imp:
            raise SystemExit(f'"{text}" ({mt}) has more impressions than its twin; recheck before pausing; nothing sent')
        update(twin[0], "status", E.AdGroupCriterionStatusEnum.PAUSED, "enabled → paused",
               f'duplicate of "{kept[0].ad_group_criterion.keyword.text}" (Google ignores case); {t_imp} vs {k_imp} impressions in 90 days')

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for camp, res, field, what, why in changes:
        print(f"• {CAMPAIGNS[camp]} · {res} · {field}: {what}\n    reason: {why}")
    if not ops:
        print("Nothing to change.")
        return
    if args.apply:
        check_log()
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
