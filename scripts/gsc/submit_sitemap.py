#!/usr/bin/env python3
"""Submit or resubmit a sitemap (sitemap.xml by default) to Search Console so Google reads it.

Default run shows the sitemap's status and changes nothing. --apply submits it,
which needs the https://www.googleapis.com/auth/webmasters scope on Application
Default Credentials (the read-only scope is not enough; see CLAUDE.md), and
logs the change in logs/gsc-changes.md.

    .venv/bin/python scripts/gsc/submit_sitemap.py            # status only
    .venv/bin/python scripts/gsc/submit_sitemap.py --apply    # after approval
    .venv/bin/python scripts/gsc/submit_sitemap.py --sitemap sitemap_index.xml [--apply]

session(), status(), submit(), log_row() and append_log() are the same steps without the command line, for
scripts/ads/standing_approvals.py (a resubmission when the Monday report says STALE).
"""

import argparse
import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

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
MARKER = "|---|---|---|---|---|---|\n"


def session():
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    creds, _ = google.auth.default()
    return AuthorizedSession(creds)


def api_url(sitemap):
    return (f"https://www.googleapis.com/webmasters/v3/sites/{quote(SITE, safe='')}/sitemaps/"
            f"{quote(ROOT_URL + sitemap, safe='')}")


def status(s, sitemap):
    """'not submitted' or 'submitted YYYY-MM-DD, last read YYYY-MM-DD'; SystemExit if the check fails."""
    r = s.get(api_url(sitemap))
    if r.status_code == 404:
        return "not submitted"
    if not r.ok:
        raise SystemExit(f"Status check failed: {r.status_code} {r.json().get('error', {}).get('message')}")
    m = r.json()
    return (f"submitted {(m.get('lastSubmitted') or '')[:10]}, "
            f"last read {(m.get('lastDownloaded') or 'never')[:10]}")


def submit(s, sitemap, before):
    """Submit it; returns 'submitted' or 'resubmitted'. Prints REJECTED and raises SystemExit(1) on a refusal."""
    r = s.put(api_url(sitemap))
    if not r.ok:
        msg = r.json().get("error", {}).get("message", r.text[:200]) if r.content else r.status_code
        print(f"REJECTED: {r.status_code} {msg}")
        if r.status_code in (401, 403):
            print("This needs the webmasters (write) scope: redo the ADC sign-in in CLAUDE.md, then retry.")
        raise SystemExit(1)
    return "submitted" if before == "not submitted" else "resubmitted"


def log_row(sitemap, before, after, reason, script, now=None):
    now = (now or datetime.datetime.now(ZoneInfo("Europe/London"))).strftime("%Y-%m-%d %H:%M")
    return (f"| {now} | sitemap {ROOT_URL + sitemap} | submission | {before} → {after} | {reason} | "
            f"`{script}` |\n")


def append_log(row, log=LOG):
    """Add one row under the table header (newest first), creating the log if it isn't there."""
    log = Path(log)
    if not log.exists():
        log.write_text("# Search Console change log\n\nEvery change applied in Search Console "
                       "(sc-domain:londonchoralservice.com), newest first.\n\n"
                       "| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |\n" + MARKER)
    log.write_text(log.read_text().replace(MARKER, MARKER + row, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sitemap", choices=SITEMAPS, default="sitemap.xml")
    args = ap.parse_args()
    s = session()
    before = status(s, args.sitemap)
    print(f"{ROOT_URL + args.sitemap}: {before}")
    if not args.apply:
        print("Status only. Run with --apply (after approval) to submit it.")
        return
    after = submit(s, args.sitemap, before)
    append_log(log_row(args.sitemap, before, after, REASONS[args.sitemap],
                       f"scripts/gsc/submit_sitemap.py --sitemap {args.sitemap}"))
    print(f"{after.capitalize()}; logged in logs/gsc-changes.md.")


if __name__ == "__main__":
    main()
