#!/usr/bin/env python3
"""23 Oct 2026 change set 8: link the approved call asset to the funeral and wedding campaigns.

Call asset 348067579141 is approved but serves nowhere: its only link is to "Funeral Singers in
London", a removed campaign. The script checks that its number is the one on the site (every
tel: link in funerals.html, weddings.html and contact.html), then links it as CALL to the
funeral expert campaign and wedding-leads. Not to Christmas. It reports, and leaves as it is,
the asset's call conversion setting.

    source .venv/bin/activate
    python scripts/ads/call_asset_2026_10_23.py            # validate
    python scripts/ads/call_asset_2026_10_23.py --apply    # after approval
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ads_log  # noqa: E402

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CUSTOMER_ID = "8733881378"
FUNERAL, WEDDING = 23735776277, 23739971001
NAMES = {FUNERAL: "funeral expert campaign", WEDDING: "wedding-leads"}
CALL_ASSET = 348067579141
CALL_CLICK_ACTION = 7796284058
PAGES = ("funerals.html", "weddings.html", "contact.html")
REPO = Path(__file__).resolve().parents[2]
SCRIPT = "scripts/ads/call_asset_2026_10_23.py"


def e164_uk(number):
    """'07356 042468' or '+447356042468' → '+447356042468'."""
    digits = re.sub(r"[^\d+]", "", number)
    if digits.startswith("+44"):
        return digits
    if digits.startswith("0"):
        return "+44" + digits[1:]
    raise SystemExit(f"can't read {number!r} as a UK number; nothing sent")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.apply:
        ads_log.check_log()  # refuse before changing anything if the log can't be written
    c = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    E = c.enums
    q = lambda s: list(ga.search(customer_id=CUSTOMER_ID, query=s))

    # --- the number on the site -------------------------------------------------
    site = set()
    for page in PAGES:
        path = REPO / page
        if not path.is_file():
            raise SystemExit(f"{page} not found at {path}; nothing sent")
        site |= {e164_uk(t) for t in re.findall(r'href="tel:([^"]+)"', path.read_text(encoding="utf-8"))}
    if len(site) != 1:
        raise SystemExit(f"the pages carry {sorted(site) or 'no'} tel: numbers, not exactly one; nothing sent")
    site_number = site.pop()

    # --- the asset ------------------------------------------------------------------
    rows = q("SELECT asset.id, asset.resource_name, asset.type, asset.call_asset.phone_number, asset.call_asset.country_code, "
             "asset.call_asset.call_conversion_reporting_state, asset.call_asset.call_conversion_action, "
             "asset.call_asset.ad_schedule_targets, asset.policy_summary.approval_status FROM asset "
             f"WHERE asset.id = {CALL_ASSET}")
    if len(rows) != 1 or rows[0].asset.type_.name != "CALL":
        raise SystemExit(f"call asset {CALL_ASSET} not found; nothing sent")
    a = rows[0].asset
    ca = a.call_asset
    if ca.country_code != "GB" or e164_uk(ca.phone_number) != site_number:
        raise SystemExit(f"call asset {CALL_ASSET} is {ca.phone_number} ({ca.country_code}); the site's number is "
                         f"{site_number}; nothing sent")
    if a.policy_summary.approval_status.name != "APPROVED":
        raise SystemExit(f"call asset {CALL_ASSET} is {a.policy_summary.approval_status.name}, not APPROVED; nothing sent")
    cust = q("SELECT customer.call_reporting_setting.call_reporting_enabled, "
             "customer.call_reporting_setting.call_conversion_reporting_enabled, "
             "customer.call_reporting_setting.call_conversion_action FROM customer")[0].customer.call_reporting_setting
    state = ca.call_conversion_reporting_state.name
    action = ca.call_conversion_action or cust.call_conversion_action
    action_id = action.rsplit("/", 1)[-1] if action else "none"
    named = {str(r.conversion_action.id): (r.conversion_action.name, r.conversion_action.type_.name) for r in q(
        "SELECT conversion_action.id, conversion_action.name, conversion_action.type FROM conversion_action")}
    action_desc = (f'"{named[action_id][0]}" ({action_id}, {named[action_id][1]})' if action_id in named else
                   f"conversionActions/{action_id}, a Google-defined action not listed among the account's own")
    print(f"site number (tel: links in {', '.join(PAGES)}): {site_number}")
    print(f"call asset {CALL_ASSET}: {ca.phone_number} ({ca.country_code}), {a.policy_summary.approval_status.name}, "
          f"ad schedule: {len(ca.ad_schedule_targets) or 'none (all hours)'}")
    print(f"call conversion: {state}; the asset's action is {action_desc}; the account's call reporting is "
          f"{'on' if cust.call_reporting_enabled else 'off'}, call conversions "
          f"{'on' if cust.call_conversion_reporting_enabled else 'off'}, default action "
          f"{cust.call_conversion_action.rsplit('/', 1)[-1]}")
    print(f'"Call click" ({CALL_CLICK_ACTION}) is {"the asset" if action_id == str(CALL_CLICK_ACTION) else "not the asset"}'
          f"'s action: it counts taps on the site's tel: links (a WEBPAGE action), not calls from the ad itself. "
          "Left as it is.\n")

    # --- links ----------------------------------------------------------------------
    linked = {r.campaign.id: r.campaign_asset.status.name for r in q(
        "SELECT campaign.id, campaign.status, campaign_asset.status FROM campaign_asset "
        f"WHERE asset.id = {CALL_ASSET} AND campaign_asset.status != 'REMOVED' AND campaign.status != 'REMOVED'")}
    calls_now = {r.campaign.id: r.asset.id for r in q(
        "SELECT campaign.id, asset.id FROM campaign_asset WHERE campaign_asset.field_type = 'CALL' "
        f"AND campaign_asset.status = 'ENABLED' AND campaign.id IN ({FUNERAL}, {WEDDING})")}
    ops, changes = [], []
    for cid in (FUNERAL, WEDDING):
        if cid in linked:
            raise SystemExit(f"call asset {CALL_ASSET} is already linked to {NAMES[cid]} ({linked[cid]}); nothing sent")
        if cid in calls_now:
            raise SystemExit(f"{NAMES[cid]} already has call asset {calls_now[cid]}; nothing sent")
        op = c.get_type("MutateOperation")
        op.campaign_asset_operation.create.campaign = ga.campaign_path(CUSTOMER_ID, cid)
        op.campaign_asset_operation.create.asset = a.resource_name
        op.campaign_asset_operation.create.field_type = E.AssetFieldTypeEnum.CALL
        ops.append(op)
        changes.append((f'campaign "{NAMES[cid]}"', f"call asset {CALL_ASSET} ({ca.phone_number})", "link",
                        "none → linked (existing approved asset)",
                        "the number on the site; its only link was to a removed campaign, so no ad shows a call button"))

    print(("APPLYING" if args.apply else "VALIDATE ONLY") + f" — {len(ops)} operation(s), one atomic request\n")
    for scope, res, field, what, why in changes:
        print(f"• {scope} · {res} · {field}: {what}\n    reason: {why}")
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
    for scope, res, field, what, why in reversed(changes):
        ads_log.append_row(f"| {now} | {scope} {res} | {field} | {what} | {why} | `{SCRIPT}` |")
    print("\nApplied and logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
