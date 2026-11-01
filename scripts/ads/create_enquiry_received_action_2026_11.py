#!/usr/bin/env python3
"""Create the "Enquiry received" conversion action that enquiries from Google ads, from every channel, are
uploaded to (scripts/ads/upload_enquiries.py; spec 2026-11-01-enquiry-conversion-design.md).

Secondary (reported, not bid on), in the Submit lead form category beside the site's "Submit lead form" tag.
Making it primary is a later owner decision, and then "Submit lead form" goes secondary, or a consented form
enquiry would count twice. It counts enquiries, not money ("Booked job" carries the value): no value, one per
click, 90-day window. Validate_only by default.

    source .venv/bin/activate
    python scripts/ads/create_enquiry_received_action_2026_11.py            # validate
    python scripts/ads/create_enquiry_received_action_2026_11.py --apply    # after approval
"""

import os
import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
NAME = "Enquiry received"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/create_enquiry_received_action_2026_11.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    c = GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    existing = list(ga.search(customer_id=CUSTOMER_ID, query=(
        f"SELECT conversion_action.id FROM conversion_action WHERE conversion_action.name = '{NAME}' "
        "AND conversion_action.status != 'REMOVED'")))
    if existing:
        print(f'"{NAME}" already exists (id {existing[0].conversion_action.id}). Nothing to change.')
        return

    op = c.get_type("ConversionActionOperation")
    ca = op.create
    ca.name = NAME
    ca.type_ = E.ConversionActionTypeEnum.UPLOAD_CLICKS
    ca.category = E.ConversionActionCategoryEnum.SUBMIT_LEAD_FORM
    ca.status = E.ConversionActionStatusEnum.ENABLED
    ca.counting_type = E.ConversionActionCountingTypeEnum.ONE_PER_CLICK
    ca.primary_for_goal = False
    ca.click_through_lookback_window_days = 90
    ca.value_settings.default_value = 0.0
    ca.value_settings.default_currency_code = "GBP"
    ca.value_settings.always_use_default_value = True

    what = ("does not exist → created: offline upload (click reference), submit lead form, "
            "one per click, 90-day window, no value, secondary")
    why = ("Counts enquiries that arrived from an ad, on every channel (form, email, WhatsApp), instead of taps "
           "on a link; set beside the pipeline's A-graded count each Monday")
    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f'\n\nconversion_action "{NAME}"\n   {what}\n   reason: {why}\n')
    req = c.get_type("MutateConversionActionsRequest")
    req.customer_id = CUSTOMER_ID
    req.operations.append(op)
    req.validate_only = not args.apply
    try:
        resp = c.get_service("ConversionActionService").mutate_conversion_actions(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)
    if not args.apply:
        print("Google accepted the operation. Nothing was changed.")
        return
    rn = resp.results[0].resource_name
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    row = f'| {now} | conversion_action "{NAME}" ({rn.rsplit("/", 1)[1]}) | (new) | {what} | {why} | `{SCRIPT}` |\n'
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print(f"Created {rn}. Logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
