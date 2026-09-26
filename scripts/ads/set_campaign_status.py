#!/usr/bin/env python3
"""Enable or pause one campaign. Never removes: pausing is the only way down.

Default run is validate_only. --apply only after approval; applied changes
are appended to logs/ads-changes.md. Refuses to enable a campaign whose
daily budget is above the £5 cap.

    source .venv/bin/activate
    python scripts/ads/set_campaign_status.py 24295921372 enabled --reason "..."
    python scripts/ads/set_campaign_status.py 24295921372 enabled --reason "..." --apply
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
MAX_DAILY_BUDGET_MICROS = 5_000_000
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/set_campaign_status.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_id", type=int)
    parser.add_argument("status", choices=["enabled", "paused"])
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    client = GoogleAdsClient.load_from_storage()
    rows = list(client.get_service("GoogleAdsService").search(
        customer_id=CUSTOMER_ID,
        query=f"SELECT campaign.name, campaign.status, campaign_budget.amount_micros "
              f"FROM campaign WHERE campaign.id = {args.campaign_id}"))
    if not rows:
        raise SystemExit(f"No campaign {args.campaign_id}")
    camp, budget = rows[0].campaign, rows[0].campaign_budget.amount_micros
    current, want = camp.status.name.lower(), args.status
    if current == want:
        print(f'"{camp.name}" is already {want}. Nothing to change.')
        return
    if want == "enabled" and budget > MAX_DAILY_BUDGET_MICROS:
        raise SystemExit(f"Refusing: daily budget £{budget/1e6:.2f} is above the £5 cap")

    resource = f'campaign "{camp.name}" ({args.campaign_id})'
    print(f"{'APPLYING' if args.apply else 'VALIDATE ONLY'}:\n\n{resource}\n   status: {current} → {want}"
          f"  (daily budget £{budget/1e6:.2f})\n   reason: {args.reason}\n")

    svc = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    op.update.resource_name = svc.campaign_path(CUSTOMER_ID, args.campaign_id)
    op.update.status = client.enums.CampaignStatusEnum[want.upper()]
    op.update_mask.paths.append("status")
    req = client.get_type("MutateCampaignsRequest")
    req.customer_id = CUSTOMER_ID
    req.operations.append(op)
    req.validate_only = not args.apply
    try:
        svc.mutate_campaigns(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("Google accepted the operation. Nothing was changed.")
        return
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    row = f"| {now} | {resource} | status | {current} → {want} | {args.reason} | `{SCRIPT}` |\n"
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
