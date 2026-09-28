#!/usr/bin/env python3
"""Set one campaign's daily budget. Refuses anything above the £5 cap before calling Google.

Validate-only by default (--validate-only says so explicitly); --apply changes the budget and adds a row to
logs/ads-changes.md (LCS_ADS_LOG overrides the path). The campaign is its numeric id or its exact name.
Refuses a shared budget (it would move other campaigns too), a zero or negative amount, more than two decimal
places, and a campaign that isn't found exactly once. Never removes anything.

This is the first proposal-aware script: the Command Centre runs it with --validate-only, then --apply.

    source .venv/bin/activate
    python scripts/ads/set_budget.py 24295921372 4.50                   # validate only
    python scripts/ads/set_budget.py 24295921372 4.50 --validate-only   # the same, said explicitly
    python scripts/ads/set_budget.py 24295921372 4.50 --apply           # after approval
"""

import argparse
import datetime
import decimal
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402

CUSTOMER_ID = "8733881378"
MAX_DAILY_BUDGET_MICROS = 5_000_000
SCRIPT = "scripts/ads/set_budget.py"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._&'()–-]{0,99}$")


def budget_micros(text):
    """Pounds (up to two decimal places) as micros, or SystemExit: never above the £5 cap, never zero or less."""
    if not re.fullmatch(r"\d{1,4}(\.\d{1,2})?", text or ""):
        raise SystemExit(f"the daily budget must be pounds like 4.50, not {text!r}; nothing changed")
    micros = int(decimal.Decimal(text) * 1_000_000)
    if micros <= 0:
        raise SystemExit("the daily budget must be more than £0; nothing changed")
    if micros > MAX_DAILY_BUDGET_MICROS:
        raise SystemExit(f"Refusing: £{decimal.Decimal(text):.2f} a day is above the £5 cap; nothing changed")
    return micros


def parse(argv=None):
    p = argparse.ArgumentParser(description="Set one campaign's daily budget (never above £5).")
    p.add_argument("campaign", help="the campaign id (digits) or its exact name")
    p.add_argument("daily", help="the new daily budget in pounds, at most 5.00")
    p.add_argument("--reason", default="approved in the Command Centre")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--validate-only", action="store_true", help="the default: Google checks it, nothing changes")
    mode.add_argument("--apply", action="store_true")
    args = p.parse_args(argv)
    if not (args.campaign.isdigit() or NAME_RE.fullmatch(args.campaign)):
        p.error("the campaign must be its id or its exact name")
    if "|" in args.reason or "\n" in args.reason or len(args.reason) > 300:
        p.error("the reason must be one line of at most 300 characters, without '|'")
    return args


def load_client():
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))


def find_campaign(client, campaign):
    if campaign.isdigit():
        where = f"campaign.id = {int(campaign)}"
    else:
        where = "campaign.name = '" + campaign.replace("\\", "\\\\").replace("'", "\\'") + "'"
    rows = list(client.get_service("GoogleAdsService").search(
        customer_id=CUSTOMER_ID,
        query="SELECT campaign.id, campaign.name, campaign.status, campaign_budget.resource_name, "
              "campaign_budget.amount_micros, campaign_budget.explicitly_shared "
              f"FROM campaign WHERE {where} AND campaign.status != 'REMOVED'"))
    if len(rows) != 1:
        raise SystemExit(f"{'no campaign' if not rows else 'more than one campaign'} matches {campaign!r}; "
                         "nothing changed")
    return rows[0]


def is_google_ads_error(e):
    return type(e).__name__ == "GoogleAdsException" and hasattr(e, "failure")


def main(argv=None, client=None, now=None):
    args = parse(argv)
    new = budget_micros(args.daily)  # the cap is checked before anything talks to Google
    if args.apply:
        ads_log.check_log()
    client = client or load_client()
    row = find_campaign(client, args.campaign)
    camp, budget = row.campaign, row.campaign_budget
    if budget.explicitly_shared:
        raise SystemExit(f'"{camp.name}" uses a shared budget; change it in Google Ads, not here. Nothing changed')
    current = int(budget.amount_micros)
    resource = f'campaign "{camp.name}" ({camp.id}) budget'
    print(f"{'APPLYING' if args.apply else 'VALIDATE ONLY'}:\n\n{resource}\n"
          f"   daily budget: £{current / 1e6:.2f} → £{new / 1e6:.2f}\n   reason: {args.reason}\n")
    if current == new:
        print("Already that amount. Nothing to change.")
        return 0
    svc = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    op.update.resource_name = budget.resource_name
    op.update.amount_micros = new
    op.update_mask.paths.append("amount_micros")
    req = client.get_type("MutateCampaignBudgetsRequest")
    req.customer_id = CUSTOMER_ID
    req.operations.append(op)
    req.validate_only = not args.apply
    try:
        svc.mutate_campaign_budgets(request=req)
    except Exception as e:
        if not is_google_ads_error(e):
            raise
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("Google accepted the operation. Nothing was changed.")
        return 0
    when = (now or datetime.datetime.now().astimezone()).strftime("%Y-%m-%d %H:%M")
    ads_log.append_row(f"| {when} | {resource} | daily budget | £{current / 1e6:.2f} → £{new / 1e6:.2f} | "
                       f"{args.reason} | `{SCRIPT}` |")
    print("Applied and logged to logs/ads-changes.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
