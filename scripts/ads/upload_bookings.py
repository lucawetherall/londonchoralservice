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

Only rows with an ad click reference, consent = granted, a value above zero,
and no uploaded_at are uploaded (select_ready). Rows whose notes start with
"PENDING" (invoiced, deposit not yet seen) wait until the flag is cleared; a
cancelled booking never goes, by the same rule check_payments uses
(is_cancelled: "cancelled" anywhere in the notes, unless a later "reinstated"
or the like undoes it). The reference comes from the enquiry (the site adds
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
import datetime
import hashlib
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bookings"))
import check_payments as cp  # noqa: E402  (is_cancelled, is_pending: one rule for every ledger reader)
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
    """Create an empty ledger (header only, mode 600, written atomically) if there is none."""
    with lm.ledger_lock(LEDGER):
        if LEDGER.exists():
            return
        lm.write_csv(LEDGER, [], COLUMNS)
    print(f"Created an empty private ledger at {LEDGER}")


def stamp_uploaded(done, now):
    """Stamp uploaded_at on these booking refs. Re-reads the ledger under the shared lock (lm.locked_rows:
    the ledger's own header, atomic mode-600 write) so a row another writer added or changed during the
    upload is kept. lm.ledger_lock is not re-entrant: never call this while holding it."""
    with lm.locked_rows(LEDGER, COLUMNS) as t:
        for r in t.rows:
            if r.get("booking_ref") in done:
                r["uploaded_at"] = now


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


def select_ready(rows):
    """(ready, skipped): ready is [(row, value, event timestamp)] for rows to upload now; skipped is
    [(booking_ref, reason)]. Rows already uploaded are left out silently. A cancelled booking
    (check_payments.is_cancelled, so an appended "; cancelled 2026-10-05 by client email" counts) and a
    PENDING one are never ready, nor is a value that is unreadable, not finite, or not above zero."""
    ready, skipped = [], []
    for r in rows:
        ref = (r.get("booking_ref") or "").strip()
        if (r.get("uploaded_at") or "").strip():
            continue
        if cp.is_cancelled(r):
            skipped.append((ref, "cancelled"))
            continue
        if cp.is_pending(r.get("notes") or ""):
            skipped.append((ref, "PENDING: no deposit seen yet (clear the flag in notes once it is paid)"))
            continue
        if not (r.get("gclid") or "").strip():
            skipped.append((ref, "no ad click reference (not from a Google ad, or cookies declined)"))
            continue
        if (r.get("consent") or "").strip().lower() != "granted":
            skipped.append((ref, "no recorded consent for ad measurement"))
            continue
        try:
            when, when_str = to_datetime(r["invoice_date"])
            enquired = to_datetime(r["enquiry_date"])[0] if (r.get("enquiry_date") or "").strip() else None
        except (ValueError, KeyError, AttributeError):
            skipped.append((ref, "missing or unreadable invoice_date / enquiry_date"))
            continue
        value = lm.parse_gbp(r.get("value_gbp"))  # None when unreadable, nan or inf
        if value is None or value <= 0:
            skipped.append((ref, "value_gbp is missing, unreadable or not above zero"))
            continue
        if enquired and (when - enquired).days > 90:
            skipped.append((ref, "booked more than 90 days after the enquiry (outside the conversion window)"))
            continue
        ready.append((r, value, when_str))
    return ready, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ensure_ledger()
    rows = lm.read_csv(LEDGER)

    ready, skipped = select_ready(rows)

    for ref, why in skipped:
        print(f"skip {ref or '(no ref)'}: {why}")
    if not ready:
        print("Nothing to upload.")
        return

    import google.auth  # only here, so select_ready can be imported (and tested) without Google's libraries
    from google.ads.googleads.client import GoogleAdsClient
    from google.auth.transport.requests import AuthorizedSession

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
    now = datetime.datetime.now(LONDON).strftime("%Y-%m-%d %H:%M")
    print(f"Accepted by Google (request {request_id}); processing status can be checked with that ID.")
    done = {r["booking_ref"] for r, _, _ in ready}
    stamp_uploaded(done, now)
    uploaded_value = sum(v for r, v, _ in ready if r["booking_ref"] in done)
    row = (f"| {now} | conversion_action \"{ACTION_NAME}\" | offline upload | +{len(done)} booking(s), "
           f"£{uploaded_value:,.2f} total | Confirmed bookings from the private ledger (not in repo) | `{SCRIPT}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print(f"Uploaded {len(done)} booking(s); ledger stamped; logged (count and total only).")


if __name__ == "__main__":
    main()
