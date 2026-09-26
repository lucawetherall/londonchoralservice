#!/usr/bin/env python3
"""Rebuild the account's conversion actions around one lead = one conversion.

Default run is validate_only (Google checks every operation, nothing changes).
Pass --apply only after the change set has been approved; applied changes are
appended to logs/ads-changes.md.

    source .venv/bin/activate
    python scripts/ads/conversion_actions_2026_09.py            # validate
    python scripts/ads/conversion_actions_2026_09.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/conversion_actions_2026_09.py"

# Existing actions to demote. "Submit lead form" (7603963809) stays the one
# primary lead action and is not touched.
DEMOTE = {
    7566867509: "GA4 import of ads_conversion_Contact_1, which fired twice per thank-you view; the same enquiry again",
}
# "Contact" (7566855536) is a codeless URL-rule action: the API refuses to
# mutate it (MUTATE_NOT_ALLOWED), so it is demoted by hand in the Ads UI.
MANUAL = ('In Google Ads: Goals > Summary > "Contact" > Edit settings > Action optimisation: '
          'Secondary action. It counts the same enquiry the site tag already counts.')

# New secondary actions: reported in Ads, never used for bidding until the
# data shows how many taps turn into real enquiries.
CREATE = [
    ("Call click", "PHONE_CALL_LEAD",
     "Taps on the phone number were counted as full leads via a thank-you redirect; now observed separately"),
    ("WhatsApp or email click", "CONTACT",
     "Taps on WhatsApp/email links were counted as full leads via a thank-you redirect; now observed separately"),
]


def current_actions(client):
    ga = client.get_service("GoogleAdsService")
    query = """
        SELECT conversion_action.id, conversion_action.name, conversion_action.primary_for_goal,
               conversion_action.status
        FROM conversion_action WHERE conversion_action.status != 'REMOVED'"""
    return {r.conversion_action.id: r.conversion_action for r in ga.search(customer_id=CUSTOMER_ID, query=query)}


def build_operations(client, existing):
    svc = client.get_service("ConversionActionService")
    ops, changes = [], []
    names = {a.name for a in existing.values()}

    for action_id, reason in DEMOTE.items():
        a = existing[action_id]
        if not a.primary_for_goal:
            continue
        op = client.get_type("ConversionActionOperation")
        op.update.resource_name = svc.conversion_action_path(CUSTOMER_ID, action_id)
        op.update.primary_for_goal = False
        op.update_mask.paths.append("primary_for_goal")
        ops.append(op)
        changes.append((f'conversion_action "{a.name}" ({action_id})', "primary_for_goal",
                        "primary (counts in Conversions, drives bidding)", "secondary (reported only)", reason))

    for name, category, reason in CREATE:
        if name in names:
            continue
        op = client.get_type("ConversionActionOperation")
        ca = op.create
        ca.name = name
        ca.type_ = client.enums.ConversionActionTypeEnum.WEBPAGE
        ca.category = client.enums.ConversionActionCategoryEnum[category]
        ca.status = client.enums.ConversionActionStatusEnum.ENABLED
        ca.counting_type = client.enums.ConversionActionCountingTypeEnum.ONE_PER_CLICK
        ca.primary_for_goal = False
        ca.value_settings.default_value = 1.0
        ca.value_settings.default_currency_code = "GBP"
        ca.value_settings.always_use_default_value = True
        ops.append(op)
        changes.append((f'conversion_action "{name}"', "(new)", "does not exist",
                        f"created: {category}, one per click, secondary, £1", reason))
    return ops, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="apply for real (default: validate_only)")
    args = parser.parse_args()

    client = GoogleAdsClient.load_from_storage()
    existing = current_actions(client)
    ops, changes = build_operations(client, existing)
    if not ops:
        print("Nothing to change: account already matches the target state.")
        return

    print(f"{'APPLYING' if args.apply else 'VALIDATE ONLY'} — {len(ops)} change(s):\n")
    for i, (resource, field, cur, new, reason) in enumerate(changes, 1):
        print(f"{i}. {resource}\n   {field}: {cur} → {new}\n   reason: {reason}\n")

    req = client.get_type("MutateConversionActionsRequest")
    req.customer_id = CUSTOMER_ID
    req.operations.extend(ops)
    req.validate_only = not args.apply
    try:
        resp = client.get_service("ConversionActionService").mutate_conversion_actions(request=req)
    except GoogleAdsException as e:
        for err in e.failure.errors:
            print("REJECTED:", err.error_code, err.message)
        raise SystemExit(1)

    if not args.apply:
        print("Google accepted every operation. Nothing was changed.")
        print("\nManual step (not possible through the API):\n  " + MANUAL)
        return

    today = datetime.datetime.now(datetime.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    rows = "".join(f"| {today} | {r} | {f} | {c} → {n} | {why} | `{SCRIPT}` |\n" for r, f, c, n, why in changes)
    text = LOG.read_text()
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(text.replace(marker, marker + rows, 1))
    for r in resp.results:
        print("applied:", r.resource_name)
    print(f"Logged {len(changes)} change(s) to logs/ads-changes.md")


if __name__ == "__main__":
    main()
