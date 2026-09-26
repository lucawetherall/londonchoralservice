#!/usr/bin/env python3
"""Make one conversion action primary (counts in Conversions, drives bidding)
or secondary (reported only).

Default run is validate_only. Pass --apply only after the change has been
approved; applied changes are appended to logs/ads-changes.md.

    source .venv/bin/activate
    python scripts/ads/set_conversion_primary.py 7796284061 primary --reason "..."
    python scripts/ads/set_conversion_primary.py 7796284061 primary --reason "..." --apply
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/set_conversion_primary.py"
LABEL = {True: "primary (counts in Conversions, drives bidding)", False: "secondary (reported only)"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action_id", type=int)
    parser.add_argument("role", choices=["primary", "secondary"])
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true", help="apply for real (default: validate_only)")
    args = parser.parse_args()
    want = args.role == "primary"

    client = GoogleAdsClient.load_from_storage()
    rows = list(client.get_service("GoogleAdsService").search(
        customer_id=CUSTOMER_ID,
        query=f"SELECT conversion_action.name, conversion_action.primary_for_goal "
              f"FROM conversion_action WHERE conversion_action.id = {args.action_id}"))
    if not rows:
        raise SystemExit(f"No conversion action {args.action_id}")
    action = rows[0].conversion_action
    if action.primary_for_goal == want:
        print(f'"{action.name}" is already {args.role}. Nothing to change.')
        return

    resource = f'conversion_action "{action.name}" ({args.action_id})'
    print(f"{'APPLYING' if args.apply else 'VALIDATE ONLY'}:\n\n{resource}\n"
          f"   primary_for_goal: {LABEL[action.primary_for_goal]} → {LABEL[want]}\n   reason: {args.reason}\n")

    svc = client.get_service("ConversionActionService")
    op = client.get_type("ConversionActionOperation")
    op.update.resource_name = svc.conversion_action_path(CUSTOMER_ID, args.action_id)
    op.update.primary_for_goal = want
    op.update_mask.paths.append("primary_for_goal")
    req = client.get_type("MutateConversionActionsRequest")
    req.customer_id = CUSTOMER_ID
    req.operations.append(op)
    req.validate_only = not args.apply
    try:
        svc.mutate_conversion_actions(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)

    if not args.apply:
        print("Google accepted the operation. Nothing was changed.")
        return

    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    row = (f"| {now} | {resource} | primary_for_goal | {LABEL[action.primary_for_goal]} → {LABEL[want]} "
           f"| {args.reason} | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
