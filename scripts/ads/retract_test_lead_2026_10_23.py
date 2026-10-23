#!/usr/bin/env python3
"""Retract the one test "Submit lead form" conversion sent on 23 Oct 2026.

Luca approved one "TEST – please ignore" enquiry from the live site, sent with cookies accepted, to check
PR #278. Its conversion went to Google Ads with transaction ID lead-mvl1ttnp7evz5. This script uploads a
RETRACTION for that order ID, so the test lead stops counting in Conversions and in bidding.

Default run is validate_only. Pass --apply only after the change has been approved; an applied change is
appended to logs/ads-changes.md. Google takes a few hours to record a conversion; before then an apply
comes back with a "conversion not found"-style error and changes nothing, so run it again later.

    source .venv/bin/activate
    python scripts/ads/retract_test_lead_2026_10_23.py
    python scripts/ads/retract_test_lead_2026_10_23.py --apply
"""

import os
import argparse
import datetime

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from ads_log import append_row, check_log

CUSTOMER_ID = "8733881378"
ACTION_ID = 7603963809  # "Submit lead form"
ORDER_ID = "lead-mvl1ttnp7evz5"
SCRIPT = "scripts/ads/retract_test_lead_2026_10_23.py"
REASON = ("test enquiry sent from the live site on 23 Oct with Luca's OK to check PR #278 (form lead sent "
          "from the thank-you page); not a real lead")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="apply for real (default: validate_only)")
    args = parser.parse_args()
    if args.apply:
        check_log()

    client = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = client.get_service("GoogleAdsService")
    rows = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT conversion_action.name, conversion_action.status FROM conversion_action "
        f"WHERE conversion_action.id = {ACTION_ID}")))
    if not rows:
        raise SystemExit(f"No conversion action {ACTION_ID}")
    name = rows[0].conversion_action.name
    # What the account shows for this action today (it reports by click date, so this is a hint only).
    today = list(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT segments.conversion_action, metrics.all_conversions FROM customer "
        f"WHERE segments.date DURING LAST_30_DAYS AND segments.conversion_action = "
        f"'customers/{CUSTOMER_ID}/conversionActions/{ACTION_ID}'")))
    recorded = sum(r.metrics.all_conversions for r in today)

    resource = f'conversion_action "{name}" ({ACTION_ID}), order ID {ORDER_ID}'
    print(f"{'APPLYING' if args.apply else 'VALIDATE ONLY'}:\n\n{resource}\n"
          f"   adjustment: counted (value £1) → retracted (counts 0)\n   reason: {REASON}\n"
          f"   all conversions for this action, last 30 days (by click date): {recorded:g}\n")

    adj = client.get_type("ConversionAdjustment")
    adj.conversion_action = client.get_service("ConversionActionService").conversion_action_path(
        CUSTOMER_ID, ACTION_ID)
    adj.adjustment_type = client.enums.ConversionAdjustmentTypeEnum.RETRACTION
    adj.order_id = ORDER_ID
    adj.adjustment_date_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00")

    req = client.get_type("UploadConversionAdjustmentsRequest")
    req.customer_id = CUSTOMER_ID
    req.conversion_adjustments.append(adj)
    req.partial_failure = True
    req.validate_only = not args.apply
    try:
        resp = client.get_service("ConversionAdjustmentUploadService").upload_conversion_adjustments(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if resp.partial_failure_error.code:
        print("REJECTED:", resp.partial_failure_error.message)
        raise SystemExit(1)

    if not args.apply:
        print("Google accepted the operation. Nothing was changed.")
        return

    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    append_row(f"| {now} | {resource} | conversion adjustment | counted (£1) → retracted | {REASON} | `{SCRIPT}` |")
    print("Applied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
