#!/usr/bin/env python3
"""Upload confirmed bookings to Google Ads as "Booked job" conversions, with
their real value, so bidding can learn which searches become paid bookings.

The ledger is PRIVATE and lives outside the repo (never commit it):
    ~/lcs-private/bookings.csv   (override with $LCS_BOOKINGS_CSV or $LCS_PRIVATE_DIR)

Columns (header row required):
    booking_ref, invoice_date, event_date, client_name, client_email, occasion,
    ensemble, value_gbp, enquiry_date, source, gclid, consent, uploaded_at, notes

Uploads go through Google's Data Manager API (events:ingest), which Google
now requires for new offline-conversion integrations; it needs the
https://www.googleapis.com/auth/datamanager scope on Application Default
Credentials and the Data Manager API enabled on the Cloud project.

Only rows with an ad click reference, consent = granted, a value, and no
uploaded_at are uploaded. Rows whose notes start with "PENDING" (invoiced,
deposit not yet seen) wait until the flag is cleared; "CANCELLED" rows never go. The reference comes from the enquiry (the site adds
it only for visitors who allowed cookies): a plain value is a gclid; iPhone
clicks may carry "gbraid:<value>" or "wbraid:<value>" instead. When
"Enhanced conversions for leads" is on in the Ads account, the client's email
also goes up, SHA-256 hashed, to improve matching. booking_ref is sent as the order ID, so a row
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
import hashlib
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import google.auth
from google.ads.googleads.client import GoogleAdsClient
from google.auth.transport.requests import AuthorizedSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import lcs_money as lm  # noqa: E402  (ledger path and lock shared with the bookings scripts)

CUSTOMER_ID = "8733881378"
ACTION_NAME = "Booked job"
LEDGER = lm.LEDGER  # $LCS_BOOKINGS_CSV, else bookings.csv in $LCS_PRIVATE_DIR (default ~/lcs-private)
COLUMNS = ["booking_ref", "invoice_date", "event_date", "client_name", "client_email", "occasion", "ensemble",
           "value_gbp", "enquiry_date", "source", "gclid", "consent", "uploaded_at", "notes"]
LOG = Path(__file__).resolve().parents[2] / "logs" / "ads-changes.md"
SCRIPT = "scripts/ads/upload_bookings.py"
LONDON = ZoneInfo("Europe/London")


def ensure_ledger():
    with lm.ledger_lock(LEDGER):
        if LEDGER.exists():
            return
        LEDGER.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(LEDGER, "w", newline="") as f:
            csv.writer(f).writerow(COLUMNS)
        os.chmod(LEDGER, 0o600)
    print(f"Created an empty private ledger at {LEDGER}")


def stamp_uploaded(done, now):
    """Stamp uploaded_at on these booking refs. Re-reads the ledger under the shared lock so a row
    another writer added or changed during the upload is kept. lm.ledger_lock is not re-entrant:
    never call this while holding it."""
    with lm.ledger_lock(LEDGER):
        rows = lm.read_csv(LEDGER)
        cols = list(rows[0].keys()) if rows else list(COLUMNS)
        cols += [c for c in COLUMNS if c not in cols]
        for r in rows:
            if r.get("booking_ref") in done:
                r["uploaded_at"] = now
        lm.write_csv(LEDGER, rows, cols)
        os.chmod(LEDGER, 0o600)


def to_datetime(day):
    """Booking confirmed on the invoice date; noon London time, with offset."""
    d = datetime.datetime.strptime(day.strip()[:10], "%Y-%m-%d").replace(hour=12, tzinfo=LONDON)
    return d, d.isoformat(timespec="seconds")


def click_id(raw):
    """Ledger value -> Data Manager adIdentifiers ("gbraid:"/"wbraid:" prefixes, else gclid)."""
    raw = raw.strip()
    for kind in ("gbraid", "wbraid", "gclid"):
        if raw.lower().startswith(kind + ":"):
            return {kind: raw.split(":", 1)[1].strip()}
    return {"gclid": raw}


def hashed_email(raw):
    """Google's normalisation: trim, lowercase, drop dots before @ for Gmail; then SHA-256 hex."""
    email = (raw or "").strip().lower()
    if "@" not in email:
        return None
    local, domain = email.rsplit("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
    return hashlib.sha256(f"{local}@{domain}".encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ensure_ledger()
    with lm.ledger_lock(LEDGER), open(LEDGER, newline="") as f:
        rows = list(csv.DictReader(f))

    ready, skipped = [], []
    for r in rows:
        ref = (r.get("booking_ref") or "").strip()
        if (r.get("uploaded_at") or "").strip():
            continue
        flag = (r.get("notes") or "").strip().upper()
        if flag.startswith("PENDING"):
            skipped.append((ref, "PENDING: no deposit seen yet (clear the flag in notes once it is paid)"))
            continue
        if flag.startswith("CANCELLED"):
            skipped.append((ref, "cancelled"))
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

    c = GoogleAdsClient.load_from_storage(os.environ.get("GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = c.get_service("GoogleAdsService")
    action_id = next(iter(ga.search(customer_id=CUSTOMER_ID, query=(
        f"SELECT conversion_action.id FROM conversion_action WHERE conversion_action.name = '{ACTION_NAME}' "
        "AND conversion_action.status = 'ENABLED'")))).conversion_action.id

    ec_for_leads = next(iter(ga.search(customer_id=CUSTOMER_ID, query=(
        "SELECT customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled FROM customer")))
    ).customer.conversion_tracking_setting.enhanced_conversions_for_leads_enabled

    def event(r, value, when_str):
        e = {"adIdentifiers": click_id(r["gclid"]), "eventTimestamp": when_str,
             "transactionId": r["booking_ref"].strip(), "eventSource": "OTHER",
             "conversionValue": value, "currency": "GBP"}
        h = hashed_email(r.get("client_email")) if ec_for_leads else None
        if h:
            e["userData"] = {"userIdentifiers": [{"emailAddress": h}]}
        return e

    account = {"accountType": "GOOGLE_ADS", "accountId": CUSTOMER_ID}
    body = {
        "destinations": [{"operatingAccount": account, "loginAccount": account,
                          "productDestinationId": str(action_id)}],
        # Visitors allowed ad measurement; the site never allows ad personalisation.
        "consent": {"adUserData": "CONSENT_GRANTED", "adPersonalization": "CONSENT_DENIED"},
        "encoding": "HEX",
        "events": [event(r, value, when_str) for r, value, when_str in ready],
        "validateOnly": not args.apply,
    }
    total = sum(v for _, v, _ in ready)
    print(("UPLOADING" if args.apply else "VALIDATE ONLY") + f" — {len(ready)} booking(s), £{total:,.2f} total"
          + (" (with hashed emails: enhanced conversions for leads is on)" if ec_for_leads else ""))
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
    stamp_uploaded(done, now)
    uploaded_value = sum(v for r, v, _ in ready if r["booking_ref"] in done)
    row = (f"| {now} | conversion_action \"{ACTION_NAME}\" | offline upload | +{len(done)} booking(s), "
           f"£{uploaded_value:,.2f} total | Confirmed bookings from the private ledger (not in repo) | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print(f"Uploaded {len(done)} booking(s); ledger stamped; logged (count and total only).")


if __name__ == "__main__":
    main()
