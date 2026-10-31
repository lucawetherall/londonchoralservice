#!/usr/bin/env python3
"""Enable or pause one campaign. Never removes: pausing is the only way down.

Default run is validate_only. --apply only after approval; applied changes
are appended to logs/ads-changes.md. Refuses to enable a campaign whose
daily budget is above its cap (£5, or a dated exception in budget_cap.py).

    source .venv/bin/activate
    python scripts/ads/set_campaign_status.py 24295921372 enabled --reason "..."
    python scripts/ads/set_campaign_status.py 24295921372 enabled --reason "..." --apply

change() is the same run without the command line, for scripts/ads/validate_proposal.py (which never applies).
"""

import os
import argparse
import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import budget_cap  # noqa: E402

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/set_campaign_status.py"


def load_client():
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))


def is_google_ads_error(e):
    return type(e).__name__ == "GoogleAdsException" and hasattr(e, "failure")


def parse(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_id", type=int)
    parser.add_argument("status", choices=["enabled", "paused"])
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def change(campaign_id, want, reason, apply=False, client=None, now=None):
    """Validate (or, with apply, make) one status change, printing current → new. SystemExit on a refusal."""
    client = client or load_client()
    rows = list(client.get_service("GoogleAdsService").search(
        customer_id=CUSTOMER_ID,
        query=f"SELECT campaign.name, campaign.status, campaign_budget.amount_micros "
              f"FROM campaign WHERE campaign.id = {int(campaign_id)}"))
    if not rows:
        raise SystemExit(f"No campaign {campaign_id}")
    camp, budget = rows[0].campaign, rows[0].campaign_budget.amount_micros
    current = camp.status.name.lower()
    if current == want:
        print(f'"{camp.name}" is already {want}. Nothing to change.')
        return
    cap = budget_cap.cap_micros(campaign_id)
    if want == "enabled" and budget > cap:
        raise SystemExit(f"Refusing: daily budget £{budget/1e6:.2f} is above the £{cap/1e6:g} cap")

    resource = f'campaign "{camp.name}" ({campaign_id})'
    print(f"{'APPLYING' if apply else 'VALIDATE ONLY'}:\n\n{resource}\n   status: {current} → {want}"
          f"  (daily budget £{budget/1e6:.2f})\n   reason: {reason}\n")

    svc = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    op.update.resource_name = svc.campaign_path(CUSTOMER_ID, campaign_id)
    op.update.status = client.enums.CampaignStatusEnum[want.upper()]
    op.update_mask.paths.append("status")
    req = client.get_type("MutateCampaignsRequest")
    req.customer_id = CUSTOMER_ID
    req.operations.append(op)
    req.validate_only = not apply
    try:
        svc.mutate_campaigns(request=req)
    except Exception as e:
        if not is_google_ads_error(e):
            raise
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not apply:
        print("Google accepted the operation. Nothing was changed.")
        return
    now = (now or datetime.datetime.now().astimezone()).strftime("%Y-%m-%d %H:%M")
    row = f"| {now} | {resource} | status | {current} → {want} | {reason} | `{SCRIPT}` |\n"
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("Applied and logged to logs/ads-changes.md")


def main(argv=None, client=None):
    args = parse(argv)
    change(args.campaign_id, args.status, args.reason, apply=args.apply, client=client)


if __name__ == "__main__":
    main()
