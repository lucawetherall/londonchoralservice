#!/usr/bin/env python3
"""Upload enquiries from Google ads to Google Ads as "Enquiry received" conversions, from every channel (web
form, email, WhatsApp, phone), so Google Ads counts messages that arrived rather than taps on a link.
Spec: docs/superpowers/specs/2026-11-01-enquiry-conversion-design.md.

The pipeline is PRIVATE and lives outside the repo (never commit it):
    ~/lcs-private/enquiries.csv   (pipeline.py's columns; LCS_PRIVATE_DIR overrides the folder)

What goes up (select_ready), and nothing else: an enquiry with a click reference in its gclid column (a gclid,
gbraid:<id> or wbraid:<id>, or the gclid lookup_ref.py gave for a "Ref: XXXX" line), first seen on or after
27 Sep 2026. The site keeps a click ID only for a visitor who allowed cookies, and has done so since that day, so
the reference is the consent. Never an "Ad visit" (grade B: it carries no click ID, and the owner rejected
url_passthrough on 23 Oct 2026), an unresolved "Ref: XXXX" note, or an enquiry first seen more than 90 days ago
(outside the click window). No email goes up, hashed or not: the form's ad-measurement box promises that nothing
is sent for an enquiry that doesn't become a booking (privacy.html), so a ticked box with no click reference
stays out until the owner approves new wording for the box and the notice.

The enquiry_id (the Zoho thread id, or the WhatsApp enquiry's own id) is the order ID, so an enquiry can never
count twice. The conversion time is 23:59 London time on first_seen (after any click that day), or a minute ago
for an enquiry first seen today. No value goes up: "Booked job" carries the money. Default run is validate_only;
--apply uploads, stamps ads_uploaded_at in the pipeline and logs a count (no personal data) to
logs/ads-changes.md.

    source .venv/bin/activate
    python scripts/ads/upload_enquiries.py            # validate
    python scripts/ads/upload_enquiries.py --apply    # after approval
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import lcs_money as lm  # noqa: E402  (locked_rows, read_csv, today)
import pipeline  # noqa: E402  (the enquiries file and its columns)
from upload_bookings import click_id  # noqa: E402  (one reading of a stored click reference)

CUSTOMER_ID = "8733881378"
ACTION_NAME = "Enquiry received"
ENQUIRIES = pipeline.ENQUIRIES
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/upload_enquiries.py"
LONDON = ZoneInfo("Europe/London")
CONSENT_FROM = datetime.date(2026, 9, 27)  # the site has kept a click ID only with cookie consent since this day
WINDOW_DAYS = 90  # the action's click-through window: an older enquiry can't match its click
REF_NOTE = re.compile(r"(?:^|; )(?:ad )?ref: ", re.I)


def event_time(first_seen, now):
    """23:59 London time on the day first seen, or a minute before `now` when that is still to come."""
    d = datetime.datetime.combine(first_seen, datetime.time(23, 59), LONDON)
    return min(d, now - datetime.timedelta(minutes=1)).isoformat(timespec="seconds")


def select_ready(rows, today=None, now=None):
    """(ready, skipped): ready is [(row, event timestamp)] for rows to upload now; skipped is [(enquiry_id,
    reason)] for rows that point at an ad click but can't go. Rows already uploaded, and rows with no click
    reference and no ref note (an ad visit, or not from an ad as far as anyone can tell), are left out silently."""
    today = today or lm.today()
    now = now or datetime.datetime.now(LONDON)
    ready, skipped = [], []
    for r in rows:
        eid = (r.get("enquiry_id") or "").strip()
        if (r.get("ads_uploaded_at") or "").strip():
            continue
        gclid = (r.get("gclid") or "").strip()
        if not gclid:
            if REF_NOTE.search(r.get("notes") or ""):
                skipped.append((eid, "a Ref line not resolved to a click (lookup_ref.py found none or several)"))
            continue
        first = pipeline.to_date(r.get("first_seen"))
        if not first:
            skipped.append((eid, "missing or unreadable first_seen"))
            continue
        if (today - first).days > WINDOW_DAYS:
            skipped.append((eid, f"first seen more than {WINDOW_DAYS} days ago (outside the click window)"))
            continue
        if first < CONSENT_FROM:
            skipped.append((eid, "first seen before 27 Sep 2026: no recorded consent for the click reference"))
            continue
        ready.append((r, event_time(first, now)))
    return ready, skipped


def event(r, when):
    """One Data Manager event: the enquiry_id as order ID and its click reference. Never user data."""
    return {"eventTimestamp": when, "transactionId": r["enquiry_id"].strip(), "eventSource": "OTHER",
            "adIdentifiers": click_id(r["gclid"])}


def stamp_uploaded(done, now):
    """Stamp ads_uploaded_at on these enquiry ids, under the pipeline's own lock."""
    with lm.locked_rows(ENQUIRIES, pipeline.COLUMNS) as t:  # adds ads_uploaded_at to an older sheet
        for r in t.rows:
            if r.get("enquiry_id") in done and not (r.get("ads_uploaded_at") or "").strip():
                r["ads_uploaded_at"] = now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = lm.read_csv(ENQUIRIES) if ENQUIRIES.exists() else []
    ready, skipped = select_ready(rows)
    if not ready:
        for eid, why in skipped:
            print(f"skip {eid or '(no id)'}: {why}")
        print("Nothing to upload.")
        return

    import google.auth  # only here, so select_ready can be imported (and tested) without Google's libraries
    from google.ads.googleads.client import GoogleAdsClient
    from google.auth.transport.requests import AuthorizedSession

    c = GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    found = list(ga.search(customer_id=CUSTOMER_ID, query=(
        f"SELECT conversion_action.id FROM conversion_action WHERE conversion_action.name = '{ACTION_NAME}' "
        "AND conversion_action.status = 'ENABLED'")))
    if not found:
        print(f'No enabled "{ACTION_NAME}" conversion action yet: create it with '
              "scripts/ads/create_enquiry_received_action_2026_11.py (after approval).")
        raise SystemExit(1)
    action_id = found[0].conversion_action.id
    for eid, why in skipped:
        print(f"skip {eid or '(no id)'}: {why}")

    account = {"accountType": "GOOGLE_ADS", "accountId": CUSTOMER_ID}
    body = {
        "destinations": [{"operatingAccount": account, "loginAccount": account,
                          "productDestinationId": str(action_id)}],
        # Every row sent carries a click reference the site kept only with cookie consent; never ad personalisation.
        "consent": {"adUserData": "CONSENT_GRANTED", "adPersonalization": "CONSENT_DENIED"},
        "encoding": "HEX",
        "events": [event(r, when) for r, when in ready],
        "validateOnly": not args.apply,
    }
    print(("UPLOADING" if args.apply else "VALIDATE ONLY") + f" — {len(ready)} enquiry(ies)")
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/datamanager"])
    resp = AuthorizedSession(creds).post("https://datamanager.googleapis.com/v1/events:ingest", json=body)
    if not resp.ok:
        err = resp.json().get("error", {}) if resp.content else {}
        print("REJECTED:", resp.status_code, err.get("message", resp.text[:300]))
        if resp.status_code == 403:
            print("If this mentions scopes: re-run the ADC sign-in with the datamanager scope (see CLAUDE.md).")
        raise SystemExit(1)
    request_id = resp.json().get("requestId", "?")
    if not args.apply:
        print(f"Google accepted the request (validate only, request {request_id}). Nothing was uploaded.")
        return
    now = datetime.datetime.now(LONDON).strftime("%Y-%m-%d %H:%M")
    print(f"Accepted by Google (request {request_id}); processing status can be checked with that ID.")
    stamp_uploaded({r["enquiry_id"] for r, _ in ready}, now)
    row = (f"| {now} | conversion_action \"{ACTION_NAME}\" | offline upload | +{len(ready)} enquiry(ies) "
           f"| Enquiries from Google ads, every channel, counted as messages that arrived (request {request_id}) "
           f"| `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("Stamped ads_uploaded_at in the pipeline. Logged to logs/ads-changes.md")


if __name__ == "__main__":
    main()
