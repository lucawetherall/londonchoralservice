#!/usr/bin/env python3
"""Register form_error's error_detail parameter as an event-scoped custom dimension on GA4 property 527915578.

js/form.js has sent error_detail with each failed send since 31 Oct 2026 (Web3Forms' message, or the
network error's name; never the form's contents). GA4 reports a parameter only once it is registered, and
only from the day it is: the 28 Oct christmas.html failures can't be read back. Owner approved 31 Oct 2026.

Default run is a dry run: reads the live property and prints current → new. The Admin API has no
validate_only, so --apply is only run after approval. Applied changes go to logs/ga4-changes.md.

    source .venv/bin/activate
    python scripts/ga4/error_detail_dimension_2026_10_31.py            # dry run
    python scripts/ga4/error_detail_dimension_2026_10_31.py --apply    # after approval

Needs the analytics.edit scope on Application Default Credentials.
"""

import argparse
import datetime
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROPERTY = "properties/527915578"
API = "https://analyticsadmin.googleapis.com/v1beta/"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ga4-changes.md"
SCRIPT = "scripts/ga4/error_detail_dimension_2026_10_31.py"
PARAM, DISPLAY = "error_detail", "Form error detail"
DESC = "Why a send failed: Web3Forms' message or the network error's name (form_error)"
REASON = "Shows why enquiry sends fail (three on christmas.html, 28 Oct 2026); owner approved 31 Oct 2026"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)

    def call(method, path, **kw):
        r = s.request(method, API + path, **kw)
        if not r.ok:
            raise SystemExit(f"{method} {path} failed: {r.status_code} {r.json().get('error', {}).get('message')}")
        return r.json() if r.content else {}

    dims = {d["parameterName"] for d in call("GET", PROPERTY + "/customDimensions").get("customDimensions", [])}
    if PARAM in dims:
        print(f"Nothing to change: {PARAM} is already registered.")
        return
    print(f"{'APPLYING' if args.apply else 'DRY RUN'}\n\ncustomDimension {PARAM}\n"
          f"   event-scoped dimension: not registered → registered as \"{DISPLAY}\"\n   reason: {REASON}\n")
    if not args.apply:
        print("Nothing was changed.")
        return
    call("POST", PROPERTY + "/customDimensions",
         json={"parameterName": PARAM, "displayName": DISPLAY, "description": DESC, "scope": "EVENT"})
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    row = (f"| {now} | customDimension {PARAM} | event-scoped dimension | not registered → registered as "
           f"\"{DISPLAY}\" | {REASON} | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("applied; logged to logs/ga4-changes.md")


if __name__ == "__main__":
    main()
