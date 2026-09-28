#!/usr/bin/env python3
"""Mark the 26 Sep 2026 changes on GA4's charts, so later trends are read
correctly: conversions before that date were over-counted, and the ads changed.

Default run is a dry run; --apply after approval (analytics.edit scope).
Applied changes go to logs/ga4-changes.md. Existing titles are skipped.

    .venv/bin/python scripts/ga4/annotations_2026_09.py            # dry run
    .venv/bin/python scripts/ga4/annotations_2026_09.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

API = "https://analyticsadmin.googleapis.com/v1alpha/properties/527915578/reportingDataAnnotations"
LOG = Path(__file__).resolve().parents[2] / "logs" / "ga4-changes.md"
SCRIPT = "scripts/ga4/annotations_2026_09.py"
NOTES = [
    ((2026, 9, 26), "Lead tracking rebuilt", "BLUE",
     "One lead per accepted enquiry; phone, email and WhatsApp taps now contact_click. "
     "Earlier conversion counts ran up to 3x per enquiry."),
    ((2026, 9, 26), "Ads: choir-only, Christmas campaign live", "GREEN",
     "Wedding and funeral ads refocused on choirs (singer keywords paused). "
     "Christmas carol singers campaign enabled at £5/day."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)
    r = s.get(API)
    if not r.ok:
        raise SystemExit(f"Could not list annotations: {r.status_code} {r.json().get('error', {}).get('message')}")
    have = {a.get("title") for a in r.json().get("reportingDataAnnotations", [])}
    todo = [n for n in NOTES if n[1] not in have]
    print(("APPLYING" if args.apply else "DRY RUN") + f" — {len(todo)} annotation(s)")
    for (y, m, d), title, color, desc in todo:
        print(f"• {y}-{m:02d}-{d:02d} {title}: {desc}")
    if not args.apply or not todo:
        return
    rows = ""
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    for (y, m, d), title, color, desc in todo:
        r = s.post(API, json={"title": title, "description": desc, "color": color,
                              "annotationDate": {"year": y, "month": m, "day": d}})
        if not r.ok:
            raise SystemExit(f"REJECTED {title}: {r.status_code} {r.json().get('error', {}).get('message')}")
        rows += (f"| {now} | reportingDataAnnotation \"{title}\" | annotation | none → {y}-{m:02d}-{d:02d} note | "
                 f"Explain the 26 Sep break in the charts | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + rows, 1))
    print("Applied and logged to logs/ga4-changes.md")


if __name__ == "__main__":
    main()
