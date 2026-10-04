#!/usr/bin/env python3
"""Changes from the account review of 4 October 2026, approved by the owner the same day.

1. Christmas campaign: phrase negatives for people looking for carol concerts to attend.
2. Wedding and funeral campaigns: add the six home counties around London to the locations. Choir
   searches are scarce (Keyword Planner: about 10 a month per choir phrase in Greater London, four to
   five times that across the UK); budgets and each campaign's presence setting stay as they are.

Default run is validate_only. --apply only after approval; each applied change is logged to
logs/ads-changes.md. Existing negatives and locations are skipped.

    .venv/bin/python scripts/ads/ads_review_2026_10_04.py            # validate
    .venv/bin/python scripts/ads/ads_review_2026_10_04.py --apply    # after approval
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
SCRIPT = "scripts/ads/ads_review_2026_10_04.py"
CHRISTMAS, WEDDING, FUNERAL = 24295921372, 23739971001, 23735776277

NEGATIVES = {
    CHRISTMAS: {
        "reason": "Most impressions since 26 Sep were people looking for carol concerts to attend ('carols at the "
                  "royal albert hall', 'christmas carol concerts london 2026', 'king's college london choir "
                  "christmas'). 'service' is left out: a church booking singers for a carol service is a buyer",
        "negatives": ["albert hall", "concert", "concerts", "tickets", "singalong", "sing along", "king's college"],
    },
}

# Greater London is already targeted; these are the counties around it (Keyword Planner geo constants).
HOME_COUNTIES = {9041123: "Surrey", 9199185: "Kent", 9198629: "Essex", 9041114: "Hertfordshire",
                 9217074: "Berkshire", 9212963: "Buckinghamshire"}
LOCATION_REASON = ("Choir searches are scarce in Greater London (about 10 a month per phrase); the home counties "
                   "add families and couples within reach, and the Maps listing is in Maidenhead. Budget and the "
                   "presence setting unchanged; travel outside London is quoted on top")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.apply:
        ads_log.check_log()
    client = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = client.get_service("GoogleAdsService")
    E = client.enums
    names = {r.campaign.id: r.campaign.name for r in ga.search(customer_id=CUSTOMER_ID, query=(
        f"SELECT campaign.id, campaign.name FROM campaign WHERE campaign.id IN ({CHRISTMAS}, {WEDDING}, {FUNERAL})"))}
    if len(names) != 3:
        raise SystemExit(f"expected 3 campaigns, found {sorted(names)}; nothing changed")

    ops, changes = [], []
    for cid, plan in NEGATIVES.items():
        existing = {(r.campaign_criterion.keyword.text.lower(), r.campaign_criterion.keyword.match_type.name)
                    for r in ga.search(customer_id=CUSTOMER_ID, query=(
                        "SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type "
                        f"FROM campaign_criterion WHERE campaign.id = {cid} AND campaign_criterion.negative = TRUE "
                        "AND campaign_criterion.type = 'KEYWORD'"))}
        new = [t for t in plan["negatives"] if (t, "PHRASE") not in existing]
        for t in new:
            o = client.get_type("MutateOperation")
            cc = o.campaign_criterion_operation.create
            cc.campaign = ga.campaign_path(CUSTOMER_ID, cid)
            cc.negative = True
            cc.keyword.text = t
            cc.keyword.match_type = E.KeywordMatchTypeEnum.PHRASE
            ops.append(o)
        if new:
            changes.append((f'campaign "{names[cid]}" ({cid})', "negative keywords (phrase)",
                            f"{len(existing)} negatives", "+" + ", ".join(f'"{t}"' for t in new), plan["reason"]))

    for cid in (WEDDING, FUNERAL):
        have = {r.campaign_criterion.location.geo_target_constant for r in ga.search(customer_id=CUSTOMER_ID, query=(
            "SELECT campaign_criterion.location.geo_target_constant FROM campaign_criterion "
            f"WHERE campaign.id = {cid} AND campaign_criterion.type = 'LOCATION' "
            "AND campaign_criterion.negative = FALSE AND campaign_criterion.status != 'REMOVED'"))}
        add = {gid: n for gid, n in HOME_COUNTIES.items() if f"geoTargetConstants/{gid}" not in have}
        for gid in add:
            o = client.get_type("MutateOperation")
            cc = o.campaign_criterion_operation.create
            cc.campaign = ga.campaign_path(CUSTOMER_ID, cid)
            cc.location.geo_target_constant = f"geoTargetConstants/{gid}"
            ops.append(o)
        if add:
            current = ", ".join(sorted(h.rsplit("/", 1)[1] for h in have))
            changes.append((f'campaign "{names[cid]}" ({cid})', "locations",
                            f"geo targets {current}", "+" + ", ".join(add.values()), LOCATION_REASON))

    if not ops:
        print("Nothing to change: every negative and location already exists.")
        return
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operations\n")
    for res, field, cur, new, why in changes:
        print(f"{res}\n   {field}: {cur} → {new}\n   reason: {why}\n")
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = CUSTOMER_ID
    req.mutate_operations.extend(ops)
    req.validate_only = not args.apply
    try:
        ga.mutate(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("Google accepted every operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    for res, field, cur, new, why in reversed(changes):
        ads_log.append_row(f"| {now} | {res} | {field} | {cur} → {new} | {why} | `{SCRIPT}` |")
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
