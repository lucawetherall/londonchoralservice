#!/usr/bin/env python3
"""Upload confirmed bookings to Google Ads as "Booked job" conversions, with
their real value, so bidding can learn which searches become paid bookings.

The ledger is PRIVATE and lives outside the repo (never commit it):
    ~/lcs-private/bookings.csv   (override with $LCS_BOOKINGS_CSV)

Columns (header row required):
    booking_ref, invoice_date, event_date, client_name, client_email, occasion,
    ensemble, value_gbp, enquiry_date, source, gclid, consent, uploaded_at, notes

Uploads go through Google's Data Manager API (events:ingest), which Google
now requires for new offline-conversion integrations; it needs the
https://www.googleapis.com/auth/datamanager scope on Application Default
Credentials and the Data Manager API enabled on the Cloud project.

Only rows with a gclid, consent = granted, a value, and no uploaded_at are
uploaded. The gclid comes from the enquiry email (the site adds it only for
visitors who allowed cookies). booking_ref is sent as the order ID, so a row
can never be counted twice. Default run is validate_only; --apply uploads,
stamps uploaded_at in the ledger, and logs a count and total (no personal
data) to logs/ads-changes.md.

    source .venv/bin/activate
    python scripts/ads/upload_bookings.py            # validate
    python scripts/ads/upload_bookings.py --apply    # after approval
"""

import argparse
import csv
import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import google.auth
from google.ads.googleads.client import GoogleAdsClient
from google.auth.transport.requests import AuthorizedSession

CUSTOMER_ID = "8733881378"
ACTION_NAME = "Booked job"
LEDGER = Path(os.environ.get("LCS_BOOKINGS_CSV", Path.home() / "lcs-private" / "bookings.csv"))
COLUMNS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
           "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/upload_bookings.py"
LONDON = ZoneInfo("Europe/London")


def ensure_ledger():
    if LEDGER.exists():
        return
    LEDGER.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with open(LEDGER, "w", newline="") as f:
        csv.writer(f).writerow(COLUMNS)
    os.chmod(LEDGER, 0o600)
    print(f"Created an empty private ledger at {LEDGER}")


def to_datetime(day):
    """Booking confirmed on the invoice date; noon London time, with offset."""
    d = datetime.datetime.strptime(day.strip()[:10], "%Y-%m-%d").replace(hour=12, tzinfo=LONDON)
    return d, d.isoformat(timespec="seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ensure_ledger()
    with open(LEDGER, newline="") as f:
        rows = list(csv.DictReader(f))

    ready, skipped = [], []
    for r in rows:
        ref = (r.get("booking_ref") or "").strip()
        if (r.get("uploaded_at") or "").strip():
            continue
        if not (r.get("gclid") or "").strip():
            skipped.append((ref, "no ad click reference (not from a Google ad, or cookies declined)"))
            continue
        if (r.get("consent") or "").strip().lower() != "granted":
            skipped.append((ref, "no recorded consent for ad measurement"))
            continue
        try:
            value = float((r.get("value_gbp") or "").replace("£", "").replace(",", ""))
            when, when_str = to_datetime(r["invoice_date"])
        except (ValueError, KeyError):
            skipped.append((ref, "missing or unreadable value_gbp / invoice_date"))
            continue
        if r.get("enquiry_date"):
            enquired, _ = to_datetime(r["enquiry_date"])
            if (when - enquired).days > 90:
                skipped.append((ref, "booked more than 90 days after the enquiry (outside the conversion window)"))
                continue
        ready.append((r, value, when_str))

    for ref, why in skipped:
        print(f"skip {ref or '(no ref)'}: {why}")
    if not ready:
        print("Nothing to upload.")
        return

    c = GoogleAdsClient.load_from_storage()
    ga = c.get_service("GoogleAdsService")
    action_id = next(iter(ga.search(customer_id=CUSTOMER_ID, query=(
        f"SELECT conversion_action.id FROM conversion_action WHERE conversion_action.name = '{ACTION_NAME}' "
        "AND conversion_action.status = 'ENABLED'")))).conversion_action.id

    account = {"accountType": "GOOGLE_ADS", "accountId": CUSTOMER_ID}
    body = {
        "destinations": [{"operatingAccount": account, "loginAccount": account,
                          "productDestinationId": str(action_id)}],
        # Visitors allowed ad measurement; the site never allows ad personalisation.
        "consent": {"adUserData": "CONSENT_GRANTED", "adPersonalization": "CONSENT_DENIED"},
        "encoding": "HEX",
        "events": [{"adIdentifiers": {"gclid": r["gclid"].strip()}, "eventTimestamp": when_str,
                    "transactionId": r["booking_ref"].strip(), "eventSource": "OTHER",
                    "conversionValue": value, "currency": "GBP"} for r, value, when_str in ready],
        "validateOnly": not args.apply,
    }
    total = sum(v for _, v, _ in ready)
    print(("UPLOADING" if args.apply else "VALIDATE ONLY") + f" — {len(ready)} booking(s), £{total:,.2f} total")
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
    failed = set()
    now = datetime.datetime.now(LONDON).strftime("%Y-%m-%d %H:%M")
    print(f"Accepted by Google (request {request_id}); processing status can be checked with that ID.")
    done = {ready[i][0]["booking_ref"] for i in range(len(ready)) if i not in failed}
    for r in rows:
        if r.get("booking_ref") in done:
            r["uploaded_at"] = now
    with open(LEDGER, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.chmod(LEDGER, 0o600)
    uploaded_value = sum(v for r, v, _ in ready if r["booking_ref"] in done)
    row = (f"| {now} | conversion_action \"{ACTION_NAME}\" | offline upload | +{len(done)} booking(s), "
           f"£{uploaded_value:,.2f} total | Confirmed bookings from the private ledger (not in repo) | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print(f"Uploaded {len(done)} booking(s); ledger stamped; logged (count and total only).")


if __name__ == "__main__":
    main()
