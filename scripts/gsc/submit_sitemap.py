#!/usr/bin/env python3
"""Resubmit sitemap.xml to Search Console so Google re-reads it.

Default run shows the sitemap's status and changes nothing. --apply submits it,
which needs the https://www.googleapis.com/auth/webmasters scope on Application
Default Credentials (the read-only scope is not enough; see CLAUDE.md), and
logs the change in logs/gsc-changes.md.

    .venv/bin/python scripts/gsc/submit_sitemap.py            # status only
    .venv/bin/python scripts/gsc/submit_sitemap.py --apply    # after approval
"""

import argparse
import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import google.auth
from google.auth.transport.requests import AuthorizedSession

SITE = "sc-domain:londonchoralservice.com"
SITEMAP = "https://londonchoralservice.com/sitemap.xml"
LOG = Path(__file__).resolve().parents[2] / "logs" / "gsc-changes.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)
    url = f"https://www.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}/sitemaps/{quote(SITEMAP, safe='')}"
    r = s.get(url)
    if not r.ok:
        raise SystemExit(f"Status check failed: {r.status_code} {r.json().get('error', {}).get('message')}")
    m = r.json()
    before = f"submitted {(m.get('lastSubmitted') or '')[:10]}, last read {(m.get('lastDownloaded') or 'never')[:10]}"
    print(f"{SITEMAP}: {before}")
    if not args.apply:
        print("Status only. Run with --apply (after approval) to resubmit.")
        return
    r = s.put(url)
    if not r.ok:
        msg = r.json().get("error", {}).get("message", r.text[:200]) if r.content else r.status_code
        print(f"REJECTED: {r.status_code} {msg}")
        if r.status_code in (401, 403):
            print("This needs the webmasters (write) scope: redo the ADC sign-in in CLAUDE.md, then retry.")
        raise SystemExit(1)
    now = datetime.datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M")
    row = (f"| {now} | sitemap {SITEMAP} | submission | {before} → resubmitted | "
           f"Google had stopped re-reading the sitemap; new and changed pages were not being discovered | "
           f"`scripts/gsc/submit_sitemap.py` |\n")
    marker = "|---|---|---|---|---|---|\n"
    if not LOG.exists():
        LOG.write_text("# Search Console change log\n\nEvery change applied in Search Console "
                       "(sc-domain:londonchoralservice.com), newest first.\n\n"
                       "| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |\n" + marker)
    LOG.write_text(LOG.read_text().replace(marker, marker + row, 1))
    print("Resubmitted; logged in logs/gsc-changes.md.")


if __name__ == "__main__":
    main()
