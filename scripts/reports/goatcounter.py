#!/usr/bin/env python3
"""Read-only GoatCounter client for the Monday report: visits and enquiry events from every visitor.

GoatCounter (js/counter.js, live since 23 Oct 2026) counts visitors whether or not they accept cookies, so
these are the site's honest totals; GA4 sees only the quarter to a third who accept. The API key is a
read-only token the owner keeps in the macOS Keychain (service `lcs-goatcounter-read`); this module reads
it with `security`, sends it only to the site's own GoatCounter host, never prints or stores it, and makes
GET requests only. Add no other public methods.

    .venv/bin/python scripts/reports/goatcounter.py            # the section, last 7 days
    .venv/bin/python scripts/reports/goatcounter.py --check    # "key: found" or "key: missing" only
"""

import argparse
import datetime
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SITE_CODE = "londonchoralservice"  # partials/analytics.html LCS_COUNTER
API = f"https://{SITE_CODE}.goatcounter.com/api/v0"
KEYCHAIN_SERVICE = "lcs-goatcounter-read"
LIVE_SINCE = datetime.date(2026, 10, 23)
# js/counter.js event names → what they mean
EVENTS = {
    "enquiry-sent-form": "enquiry forms sent",
    "enquiry-sent-whatsapp": "WhatsApp taps",
    "enquiry-sent-email": "email taps",
    "enquiry-sent-call": "phone taps",
}


class GoatCounterError(Exception):
    """An HTTP error from the API. `http_status` is the code alone, which the Monday report prints (it carries
    no visitor or account data)."""

    def __init__(self, message, http_status=None):
        super().__init__(message)
        self.http_status = http_status


# A rate limit (429) or a server error (5xx) is usually gone a few seconds later: the 26 Oct 2026 report lost
# section 5c to one, and a manual run minutes later worked. Retry once, after Retry-After (capped) or RETRY_WAIT.
RETRY_WAIT = 5
RETRY_WAIT_MAX = 30


def _retryable(code):
    return code == 429 or 500 <= code <= 599


def _wait_for(err):
    try:
        wait = int((err.headers or {}).get("Retry-After", ""))
    except (TypeError, ValueError):
        wait = RETRY_WAIT
    return max(0, min(wait, RETRY_WAIT_MAX))


def keychain_token(service=KEYCHAIN_SERVICE, run=subprocess.run):
    r = run(["security", "find-generic-password", "-s", service, "-w"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


class GoatCounterReadOnly:
    """GET-only GoatCounter client. Add no other public methods."""

    def __init__(self, token, opener=None):
        self._token = token
        self._open = opener or urllib.request.urlopen

    def get(self, path, **params):
        url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json",
                                                                  "Content-Type": "application/json"})
        req.add_unredirected_header("Authorization", f"Bearer {self._token}")  # never follows a redirect
        for attempt in (1, 2):
            try:
                with self._open(req, timeout=30) as resp:
                    return json.loads(resp.read().decode("utf-8") or "{}")
            except urllib.error.HTTPError as e:
                if attempt == 1 and _retryable(e.code):
                    time.sleep(_wait_for(e))
                    continue
                raise GoatCounterError(f"GoatCounter API answered {e.code}", http_status=e.code) from None


def hits(client, start, end, limit=100):
    """[(path, title, count, is_event)] for start..end inclusive (dates), most first."""
    # The API wants RFC 3339 times (a bare date answers 404) and rate-limits bursts (429), so one request per
    # range; the site has well under `limit` paths.
    data = client.get("/stats/hits", start=f"{start.isoformat()}T00:00:00Z", end=f"{end.isoformat()}T23:59:59Z",
                      limit=limit)
    time.sleep(1)
    out = [(h.get("path", ""), h.get("title", ""), int(h.get("count") or 0), bool(h.get("event")))
           for h in data.get("hits") or []]
    return sorted(out, key=lambda r: -r[2])


def summary(rows):
    pages = [r for r in rows if not r[3]]
    events = {r[0]: r[2] for r in rows if r[3]}
    return sum(r[2] for r in pages), pages, events


def section(today=None, client=None, token_reader=None):
    """The report section's lines (a list of strings). Never raises for a missing key: says so instead."""
    today = today or datetime.date.today()
    end = today - datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=6)
    prev_end, prev_start = start - datetime.timedelta(days=1), start - datetime.timedelta(days=7)
    lines = ["\n== 5c. Visits from every visitor (GoatCounter, no cookies needed), last 7 days"]
    if client is None:
        token = (token_reader or keychain_token)()
        if not token:
            return lines + [f"   (no read key: the owner stores it in the Keychain as {KEYCHAIN_SERVICE}; see "
                            "MANUAL-ACTIONS §29)"]
        client = GoatCounterReadOnly(token)
    start = max(start, LIVE_SINCE)
    if start > end:
        return lines + [f"   counting started {LIVE_SINCE}; first full week reported from the next Monday"]
    views, pages, events = summary(hits(client, start, end))
    days = (end - start).days + 1
    lines.append(f"   {start} to {end} ({days} day{'s' if days != 1 else ''}): {views} page views")
    if prev_start >= LIVE_SINCE:
        pv, _, pe = summary(hits(client, prev_start, prev_end))
        lines[-1] += f" (the 7 days before: {pv})"
    else:
        pe = None
    ev = []
    for name, label in EVENTS.items():
        n = events.get(name, 0)
        ev.append(f"{label} {n}" + (f" (was {pe.get(name, 0)})" if pe is not None else ""))
    lines.append("   enquiry events: " + " · ".join(ev))
    lines.append("   top pages: " + (" · ".join(f"{p} {c}" for p, _, c, _ in pages[:8]) or "(none)"))
    lines.append("   Use these for totals (GA4 sees only visitors who accept cookies). An enquiry event is a send or "
                 "a tap, not a confirmed enquiry: compare with section 9b.")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help='print only "key: found" or "key: missing"')
    args = ap.parse_args(argv)
    if args.check:
        print("key: found" if keychain_token() else "key: missing")
        return 0
    try:
        print("\n".join(section()))
    except GoatCounterError as e:
        print(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
