#!/usr/bin/env python3
"""Align GA4 property 527915578 with the site's conversion tracking.

Default run is a dry run: reads the live property and prints current → new
for each change. The Admin API has no validate_only, so --apply is only run
after the plan has been approved. Applied changes go to logs/ga4-changes.md.

    source .venv/bin/activate
    python scripts/ga4/setup_tracking_2026_09.py            # dry run
    python scripts/ga4/setup_tracking_2026_09.py --apply    # after approval

Needs the analytics.edit scope on Application Default Credentials.
"""

import argparse
import datetime
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROPERTY = "properties/527915578"
STREAM = PROPERTY + "/dataStreams/13893838615"
API = "https://analyticsadmin.googleapis.com/"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ga4-changes.md"
SCRIPT = "scripts/ga4/setup_tracking_2026_09.py"

DIMENSIONS = [
    ("occasion", "Occasion", "Occasion chosen on the enquiry form (generate_lead)"),
    ("lead_source", "Lead source page", "Page path the enquiry was sent from (generate_lead, form_error)"),
    ("method", "Contact method", "call, email or whatsapp (contact_click)"),
    ("link_location", "Contact link location", "header, footer, mobile_bar or body (contact_click)"),
    ("error_type", "Form error type", "captcha, incomplete, timing, network or submit (form_error)"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)

    def call(method, path, version="v1beta", **kw):
        r = s.request(method, API + version + "/" + path, **kw)
        if not r.ok:
            raise SystemExit(f"{method} {path} failed: {r.status_code} {r.json().get('error', {}).get('message')}")
        return r.json() if r.content else {}

    prop = call("GET", PROPERTY)
    retention = call("GET", PROPERTY + "/dataRetentionSettings")
    key_events = {k["eventName"]: k for k in call("GET", PROPERTY + "/keyEvents").get("keyEvents", [])}
    dims = {d["parameterName"] for d in call("GET", PROPERTY + "/customDimensions").get("customDimensions", [])}
    rules = call("GET", STREAM + "/eventCreateRules", "v1alpha").get("eventCreateRules", [])

    plan = []  # (resource, field, current, new, reason, action)
    if prop.get("timeZone") != "Europe/London":
        plan.append(("property", "timeZone", prop.get("timeZone"), "Europe/London",
                     "Match Google Ads; days were an hour off during BST",
                     lambda: call("PATCH", PROPERTY, params={"updateMask": "timeZone"},
                                  json={"timeZone": "Europe/London"})))
    if retention.get("eventDataRetention") != "FOURTEEN_MONTHS":
        plan.append(("dataRetentionSettings", "eventDataRetention", retention.get("eventDataRetention"),
                     "FOURTEEN_MONTHS", "Year-on-year and seasonal analysis; data was deleted after 8 weeks",
                     lambda: call("PATCH", PROPERTY + "/dataRetentionSettings",
                                  params={"updateMask": "eventDataRetention"},
                                  json={"eventDataRetention": "FOURTEEN_MONTHS"})))
    if "generate_lead" not in key_events:
        plan.append(("keyEvent generate_lead", "key event", "not a key event", "key event, once per session",
                     "The one real lead event fired by js/form.js and js/private-events.js",
                     lambda: call("POST", PROPERTY + "/keyEvents",
                                  json={"eventName": "generate_lead", "countingMethod": "ONCE_PER_SESSION"})))
    if "ads_conversion_Contact_1" in key_events:
        name = key_events["ads_conversion_Contact_1"]["name"]
        plan.append(("keyEvent ads_conversion_Contact_1", "key event", "key event",
                     "not a key event (event and history kept)", "Duplicate lead count, fired twice per thank-you view",
                     lambda: call("DELETE", name)))
    for rule in rules:
        if rule.get("destinationEvent") == "ads_conversion_Contact_1":
            plan.append((f"eventCreateRule {rule['name'].rsplit('/', 1)[1]}", "rule",
                         "page_view on /thank-you.html → ads_conversion_Contact_1", "removed (config only, no data)",
                         "Source of the double count; the site now records leads itself",
                         lambda n=rule["name"]: call("DELETE", n, "v1alpha")))
    for param, display, desc in DIMENSIONS:
        if param not in dims:
            plan.append((f"customDimension {param}", "event-scoped dimension", "not registered",
                         f'registered as "{display}"', desc,
                         lambda p=param, d=display, t=desc: call("POST", PROPERTY + "/customDimensions", json={
                             "parameterName": p, "displayName": d, "description": t, "scope": "EVENT"})))

    if not plan:
        print("Nothing to change: property already matches the target state.")
        return
    print(f"{'APPLYING' if args.apply else 'DRY RUN'} — {len(plan)} change(s):\n")
    for i, (res, field, cur, new, why, _) in enumerate(plan, 1):
        print(f"{i}. {res}\n   {field}: {cur} → {new}\n   reason: {why}\n")
    if not args.apply:
        print("Nothing was changed.")
        return

    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    if not LOG.exists():
        LOG.write_text("# GA4 change log\n\nEvery change applied to GA4 property 527915578, newest first.\n\n"
                       "| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |\n"
                       "|---|---|---|---|---|---|\n")
    rows = ""
    for res, field, cur, new, why, action in plan:
        action()
        print("applied:", res)
        rows += f"| {now} | {res} | {field} | {cur} → {new} | {why} | `{SCRIPT}` |\n"
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print(f"Logged {len(plan)} change(s) to logs/ga4-changes.md")


if __name__ == "__main__":
    main()
