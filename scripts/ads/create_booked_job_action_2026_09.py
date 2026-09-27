#!/usr/bin/env python3
"""Create the "Booked job" conversion action that confirmed bookings are
uploaded to (scripts/ads/upload_bookings.py), with each booking's real value.

Secondary for now (reported, not bid on); make it primary only once enough
bookings have been uploaded to steer bidding. Validate_only by default.

    source .venv/bin/activate
    python scripts/ads/create_booked_job_action_2026_09.py            # validate
    python scripts/ads/create_booked_job_action_2026_09.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
NAME = "Booked job"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/create_booked_job_action_2026_09.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    c = GoogleAdsClient.load_from_storage()
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
    ca.category = E.ConversionActionCategoryEnum.CONVERTED_LEAD
    ca.status = E.ConversionActionStatusEnum.ENABLED
    ca.counting_type = E.ConversionActionCountingTypeEnum.ONE_PER_CLICK
    ca.primary_for_goal = False
    ca.click_through_lookback_window_days = 90
    ca.value_settings.default_value = 1150.0
    ca.value_settings.default_currency_code = "GBP"
    ca.value_settings.always_use_default_value = False

    what = ("does not exist → created: offline upload (gclid), converted lead, one per click, 90-day window, "
            "real booking value (default £1,150), secondary")
    why = "Lets Google Ads learn which searches become paid bookings, and their value, not just enquiries"
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
