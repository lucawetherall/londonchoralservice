#!/usr/bin/env python3
"""26 Oct 2026 change set: pause what does not serve in the Christmas campaign.
Plan: docs/superpowers/plans/2026-10-26-growth-handoff.md, WP1c and d.

- "carol singers near me", exact and phrase, in "Hire carol singers": Quality Score 1 with every component below
  average; 4 clicks and £12.46 with no conversion. Paused, not removed. "christmas carol singers" and "xmas carol
  singers" (QS 2, no cost) are left alone.
- Ad groups "Carol singer prices", "Carol singers for events" and "Venue and lobby carols": every keyword
  RARELY_SERVED, no impressions in 30 days; their intents are already headlines in "Hire carol singers". The ad
  groups are paused (status PAUSED); keywords and ads inside them are untouched.

WP1e (hide the duplicate "Contact" and "Contact (1)" conversion actions) is not here: Google's API refuses the
HIDDEN status for them (BLOCKED_VALUE, MUTATE_NOT_ALLOWED in the 26 Oct validate run). Hiding them is a dashboard
task for the owner.

Each item checks the current state first and is skipped if it already holds. Nothing is deleted.

    source .venv/bin/activate
    python scripts/ads/christmas_tidy_2026_10_26.py            # validate
    python scripts/ads/christmas_tidy_2026_10_26.py --apply    # after approval
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
CHRISTMAS, CAMPAIGN = 24295921372, "Christmas carol singers – events 2026"
HIRE_GROUP = 198315037857
KEYWORDS = {831881975711: ("carol singers near me", "EXACT"), 1199800558458: ("carol singers near me", "PHRASE")}
AD_GROUPS = {201141274032: "Carol singer prices", 201227532435: "Carol singers for events",
             201227532635: "Venue and lobby carols"}
SCRIPT = "scripts/ads/christmas_tidy_2026_10_26.py"

WHY_KEYWORD = "Quality Score 1, every component below average; 4 clicks, £12.46, no conversion"
WHY_GROUP = ("every keyword RARELY_SERVED, no impressions in 30 days to 25 Oct; its intents are headlines in "
             "\"Hire carol singers\"")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))
    ops, rows = [], []

    ids = ",".join(str(k) for k in KEYWORDS)
    found = q("SELECT ad_group_criterion.criterion_id, ad_group_criterion.keyword.text, "
              "ad_group_criterion.keyword.match_type, ad_group_criterion.status, campaign.id FROM ad_group_criterion "
              f"WHERE ad_group.id = {HIRE_GROUP} AND ad_group_criterion.criterion_id IN ({ids})")
    if len(found) != len(KEYWORDS):
        raise SystemExit("the two \"carol singers near me\" keywords were not both found; nothing sent")
    for r in found:
        k = r.ad_group_criterion
        if r.campaign.id != CHRISTMAS or (k.keyword.text, k.keyword.match_type.name) != KEYWORDS[k.criterion_id]:
            raise SystemExit(f"keyword {k.criterion_id} is not what this script expects; nothing sent")
        if k.status.name == "PAUSED":
            continue
        op = c.get_type("MutateOperation")
        u = op.ad_group_criterion_operation.update
        u.resource_name = ga.ad_group_criterion_path(CUSTOMER_ID, HIRE_GROUP, k.criterion_id)
        u.status = c.enums.AdGroupCriterionStatusEnum.PAUSED
        op.ad_group_criterion_operation.update_mask.paths.append("status")
        ops.append(op)
        rows.append((f'campaign "{CAMPAIGN}" ad group "Hire carol singers" keyword "{k.keyword.text}" '
                     f'({k.keyword.match_type.name.lower()}, {k.criterion_id})', "status",
                     f"{k.status.name.lower()} → paused", WHY_KEYWORD))

    ids = ",".join(str(k) for k in AD_GROUPS)
    found = q(f"SELECT ad_group.id, ad_group.name, ad_group.status, campaign.id FROM ad_group "
              f"WHERE ad_group.id IN ({ids})")
    if len(found) != len(AD_GROUPS):
        raise SystemExit("not every ad group was found; nothing sent")
    for r in found:
        g = r.ad_group
        if r.campaign.id != CHRISTMAS or g.name != AD_GROUPS[g.id]:
            raise SystemExit(f"ad group {g.id} is not what this script expects; nothing sent")
        if g.status.name == "PAUSED":
            continue
        op = c.get_type("MutateOperation")
        u = op.ad_group_operation.update
        u.resource_name = ga.ad_group_path(CUSTOMER_ID, g.id)
        u.status = c.enums.AdGroupStatusEnum.PAUSED
        op.ad_group_operation.update_mask.paths.append("status")
        ops.append(op)
        rows.append((f'campaign "{CAMPAIGN}" ad group "{g.name}" ({g.id})', "status",
                     f"{g.status.name.lower()} → paused", WHY_GROUP))

    if not ops:
        print("Everything already holds. Nothing to change.")
        return
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} changes\n")
    for res, field, change, why in rows:
        print(f"• {res}\n    {field}: {change}\n    reason: {why}")
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
    for res, field, change, why in reversed(rows):
        append_row(f"| {now} | {res} | {field} | {change} | {why} | `{SCRIPT}` |")
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
