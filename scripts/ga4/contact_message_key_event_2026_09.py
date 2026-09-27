#!/usr/bin/env python3
"""Give GA4 a key event that matches the Google Ads goals: a WhatsApp or email
contact. The site sends contact_click with method = call | email | whatsapp;
two event-create rules copy the WhatsApp and email ones into contact_message,
which becomes a key event (calls stay secondary, as in Google Ads).

Default run is a dry run (the Admin API has no validate_only); --apply after
approval. Applied changes go to logs/ga4-changes.md.

    source .venv/bin/activate
    python scripts/ga4/contact_message_key_event_2026_09.py            # dry run
    python scripts/ga4/contact_message_key_event_2026_09.py --apply    # after approval
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
SCRIPT = "scripts/ga4/contact_message_key_event_2026_09.py"
DEST = "contact_message"
METHODS = ["whatsapp", "email"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)

    def call(method, path, version="v1beta", **kw):
        r = s.request(method, API + version + "/" + path, **kw)
        if not r.ok:
            raise SystemExit(f"{method} {path} failed: {r.status_code} {r.text[:200]}")
        return r.json() if r.content else {}

    rules = call("GET", STREAM + "/eventCreateRules", "v1alpha").get("eventCreateRules", [])
    have = {next((c["value"] for c in r.get("eventConditions", []) if c.get("field") == "method"), None)
            for r in rules if r.get("destinationEvent") == DEST}
    key_events = {k["eventName"] for k in call("GET", PROPERTY + "/keyEvents").get("keyEvents", [])}

    plan = []
    for m in METHODS:
        if m not in have:
            body = {"destinationEvent": DEST, "sourceCopyParameters": True, "eventConditions": [
                {"field": "event_name", "comparisonType": "EQUALS", "value": "contact_click"},
                {"field": "method", "comparisonType": "EQUALS", "value": m}]}
            plan.append((f"eventCreateRule contact_click[{m}] → {DEST}", "rule", "none",
                         f"contact_click with method={m} also recorded as {DEST}",
                         "WhatsApp and email are the owner's preferred contact routes (primary in Google Ads)",
                         lambda b=body: call("POST", STREAM + "/eventCreateRules", "v1alpha", json=b)))
    if DEST not in key_events:
        plan.append((f"keyEvent {DEST}", "key event", "not a key event", "key event, once per session",
                     "GA4 key events now match the Google Ads primary goals",
                     lambda: call("POST", PROPERTY + "/keyEvents", json={"eventName": DEST, "countingMethod": "ONCE_PER_SESSION"})))

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
    rows = ""
    for res, field, cur, new, why, action in plan:
        action()
        rows += f"| {now} | {res} | {field} | {cur} → {new} | {why} | `{SCRIPT}` |\n"
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print(f"Applied and logged {len(plan)} change(s) to logs/ga4-changes.md")


if __name__ == "__main__":
    main()
