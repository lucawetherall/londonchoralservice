#!/usr/bin/env python3
"""Submit or resubmit a sitemap (sitemap.xml by default) to Search Console so Google reads it.

Default run shows the sitemap's status and changes nothing. --apply submits it,
which needs the https://www.googleapis.com/auth/webmasters scope on Application
Default Credentials (the read-only scope is not enough; see CLAUDE.md), and
logs the change in logs/gsc-changes.md.

    .venv/bin/python scripts/gsc/submit_sitemap.py            # status only
    .venv/bin/python scripts/gsc/submit_sitemap.py --apply    # after approval
    .venv/bin/python scripts/gsc/submit_sitemap.py --sitemap sitemap_index.xml [--apply]
"""

import argparse
import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import google.auth
from google.auth.transport.requests import AuthorizedSession

SITE = "sc-domain:londonchoralservice.com"
ROOT_URL = "https://londonchoralservice.com/"
SITEMAPS = ("sitemap.xml", "sitemap_index.xml", "sitemap-video.xml", "sitemap-images.xml")
LOG = Path(__file__).resolve().parents[2] / "logs" / "gsc-changes.md"
REASONS = {
    "sitemap.xml": "Google had stopped re-reading the sitemap; new and changed pages were not being discovered",
    "sitemap-video.xml": "New sitemap of the films (VideoObject), for video search",
    "sitemap-images.xml": "New sitemap of the film stills, for image search",
    "sitemap_index.xml": "New sitemap index (pages, films, film stills), the one robots.txt lists",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sitemap", choices=SITEMAPS, default="sitemap.xml")
    args = ap.parse_args()
    SITEMAP = ROOT_URL + args.sitemap
    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}/sitemaps/{quote(SITEMAP, safe='')}"
    r = s.get(url)
    if r.status_code == 404:
        before = "not submitted"
    elif not r.ok:
        raise SystemExit(f"Status check failed: {r.status_code} {r.json().get('error', {}).get('message')}")
    else:
        m = r.json()
        before = (f"submitted {(m.get('lastSubmitted') or '')[:10]}, "
                  f"last read {(m.get('lastDownloaded') or 'never')[:10]}")
    print(f"{SITEMAP}: {before}")
    if not args.apply:
        print("Status only. Run with --apply (after approval) to submit it.")
        return
    r = s.put(url)
    if not r.ok:
        msg = r.json().get("error", {}).get("message", r.text[:200]) if r.content else r.status_code
        print(f"REJECTED: {r.status_code} {msg}")
        if r.status_code in (401, 403):
            print("This needs the webmasters (write) scope: redo the ADC sign-in in CLAUDE.md, then retry.")
        raise SystemExit(1)
    now = datetime.datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M")
    after = "submitted" if before == "not submitted" else "resubmitted"
    row = (f"| {now} | sitemap {SITEMAP} | submission | {before} → {after} | {REASONS[args.sitemap]} | "
           f"`scripts/gsc/submit_sitemap.py --sitemap {args.sitemap}` |\n")
    marker = "|---|---|---|---|---|---|\n"
    if not LOG.exists():
        LOG.write_text("# Search Console change log\n\nEvery change applied in Search Console "
                       "(sc-domain:londonchoralservice.com), newest first.\n\n"
                       "| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |\n" + marker)
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print(f"{after.capitalize()}; logged in logs/gsc-changes.md.")


if __name__ == "__main__":
    main()
