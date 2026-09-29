#!/usr/bin/env python3
"""Turn the short "Ref: K7P2" on a WhatsApp message or email back into its ad click ID.

The site (partials/analytics.html, lcsShortRef) adds a four-character ref to
WhatsApp messages and emails started from a page reached through a Google ad,
for visitors who allowed cookies. The ref is a hash of the click ID, so no
store is needed: this script lists the account's ad clicks day by day
(click_view, which Google keeps for 90 days) and prints every click whose ID
gives the same ref. The gclid it prints goes in the ledger's gclid column, and
upload_bookings.py then reports the booking.

Read-only: it changes nothing in Google Ads.

    .venv/bin/python scripts/ads/lookup_ref.py K7P2 --date 2026-09-28   # enquiry date: that day and 2 before
    .venv/bin/python scripts/ads/lookup_ref.py K7P2                      # every day Google still has (90)
    .venv/bin/python scripts/ads/lookup_ref.py --hash <click id>          # the ref a click ID gives

Limits: click_view lists gclids only, so an iPhone click that carried only a
gbraid or wbraid is not found (the script says so). Four characters give about
a million refs; a clash with another click on the same few days is very
unlikely, and the date, campaign and device printed with each match settle it.
"""

import argparse
import datetime
import os
import sys
from zoneinfo import ZoneInfo

CUSTOMER_ID = "8733881378"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I; must match lcsShortRef on the site
LONDON = ZoneInfo("Europe/London")
KEPT_DAYS = 90


def short_ref(click_id):
    """Four characters from the 32-bit FNV-1a hash of the click ID (low 5 bits first), as lcsShortRef."""
    h = 0x811C9DC5
    for b in click_id.encode("latin-1", "replace"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    out = ""
    for _ in range(4):
        out += ALPHABET[h & 31]
        h >>= 5
    return out


def normalise(ref):
    """Accept "Ref: k7p2" or "K7P2"; a ref never holds 0, O, 1 or I, so a typo there is caught here."""
    r = ref.strip().upper()
    if r.startswith("REF:"):
        r = r[4:].strip()
    if len(r) != 4 or any(c not in ALPHABET for c in r):
        raise SystemExit(f'"{ref}" is not a ref: expected four characters from {ALPHABET}')
    return r


def days_to_search(date, today):
    oldest = today - datetime.timedelta(days=KEPT_DAYS - 1)
    if date:
        d = datetime.date.fromisoformat(date)
        days = [d - datetime.timedelta(days=n) for n in range(3)]
    else:
        days = [today - datetime.timedelta(days=n) for n in range(KEPT_DAYS)]
    return [d for d in days if oldest <= d <= today]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("ref", nargs="?")
    parser.add_argument("--date", help="enquiry date (YYYY-MM-DD): search that day and the two before")
    parser.add_argument("--hash", metavar="CLICK_ID", help="print the ref this click ID gives, and stop")
    args = parser.parse_args()
    if args.hash:
        print(short_ref(args.hash))
        return
    if not args.ref:
        parser.error("give a ref, or --hash <click id>")
    ref = normalise(args.ref)
    today = datetime.datetime.now(LONDON).date()
    days = days_to_search(args.date, today)
    if not days:
        raise SystemExit(f"Google keeps clicks for {KEPT_DAYS} days; {args.date} is outside them.")

    from google.ads.googleads.client import GoogleAdsClient
    client = GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))
    ga = client.get_service("GoogleAdsService")
    matches, clicks = [], 0
    for d in days:
        for r in ga.search(customer_id=CUSTOMER_ID, query=(
                "SELECT segments.date, campaign.name, segments.device, click_view.gclid "
                f"FROM click_view WHERE segments.date = '{d.isoformat()}'")):
            clicks += 1
            if r.click_view.gclid and short_ref(r.click_view.gclid) == ref:
                matches.append((r.segments.date, r.campaign.name, r.segments.device.name, r.click_view.gclid))

    print(f"Ref {ref}: searched {len(days)} day(s), {days[-1]} to {days[0]}, {clicks} click(s).")
    if not matches:
        print("No click matches. Either the click was more than 90 days ago, it was an iPhone click with "
              "only a gbraid/wbraid (Google doesn't list those), or the ref was mistyped.")
        sys.exit(1)
    for date, campaign, device, gclid in matches:
        print(f"match: {date} · {campaign} · {device}")
        print(f"  ledger gclid: {gclid}")
    if len(matches) > 1:
        print("More than one click gives this ref: pick the one whose date and campaign fit the enquiry.")


if __name__ == "__main__":
    main()
