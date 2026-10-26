#!/usr/bin/env python3
"""Read-only Core Web Vitals for the Monday report: Chrome UX Report field data, with a lab fallback.

For each money page it asks the Chrome UX Report (CrUX) API for the page's own 28-day field data on phones
(LCP, INP, CLS at the 75th percentile, the figures Google ranks on). A page with too few Chrome visitors has
no record of its own, so the section also prints the whole origin's phone record, and then a PageSpeed
Insights lab run (Lighthouse, mobile) for every page: lab numbers come from one simulated load, not from
visitors, so they are a guide to what changed, never a ranking figure.

The API key (restricted to the CrUX and PageSpeed Insights APIs on project lcs-marketing) is in the macOS
Keychain as `lcs-pagespeed`; this module reads it with `security`, sends it only to Google's two endpoints,
never prints or stores it, and makes read requests only. Add no other public methods.

    .venv/bin/python scripts/reports/cwv.py                  # the section (section 5d of the Monday report)
    .venv/bin/python scripts/reports/cwv.py --lab URL ...    # lab runs only, for a before/after check
    .venv/bin/python scripts/reports/cwv.py --check          # "key: found" or "key: missing" only
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ORIGIN = "https://londonchoralservice.com"
PAGES = ["/", "/funerals.html", "/weddings.html", "/christmas.html", "/christmas-pricing.html"]
# The enabled ads' final URLs as of 26 Oct 2026. Section 4 of the Monday report reads the live ones; until
# weekly_review.py passes them in (section(ad_landing=...)), this list stands in for them.
AD_LANDING = ["/funerals.html", "/weddings.html", "/christmas.html", "/christmas-pricing.html"]
# A lab run worth a second look: LCP above 4 s (Google's "poor" line) or a performance score under 50.
LAB_LCP_CHECK_MS = 4000
LAB_SCORE_CHECK = 50
KEYCHAIN_SERVICE = "lcs-pagespeed"
CRUX = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
PSI = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
# Google's "good" / "poor" thresholds at p75: (good <=, poor >)
THRESHOLDS = {
    "largest_contentful_paint": (2500, 4000),
    "interaction_to_next_paint": (200, 500),
    "cumulative_layout_shift": (0.1, 0.25),
}
LABELS = {"largest_contentful_paint": "LCP", "interaction_to_next_paint": "INP",
          "cumulative_layout_shift": "CLS"}


class CwvError(Exception):
    pass


def keychain_key(service=KEYCHAIN_SERVICE, run=subprocess.run):
    r = run(["security", "find-generic-password", "-s", service, "-w"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


class GoogleSpeedReadOnly:
    """CrUX query and PageSpeed run, nothing else. Add no other public methods."""

    def __init__(self, key, opener=None):
        self._key = key
        self._open = opener or urllib.request.urlopen

    def _call(self, url, body=None, timeout=30):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json"})
        req.add_unredirected_header("X-Goog-Api-Key", self._key)  # a header, so the key never sits in a URL
        try:
            with self._open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # CrUX: not enough visitors for a record
                return None
            raise CwvError(f"Google answered {e.code} for {url.split('?')[0]}") from None

    def crux(self, url=None, origin=None, form_factor="PHONE"):
        body = {"formFactor": form_factor, "metrics": list(THRESHOLDS)}
        body["url" if url else "origin"] = url or origin
        return self._call(CRUX, body)

    def lab(self, url, strategy="mobile"):
        q = urllib.parse.urlencode({"url": url, "strategy": strategy, "category": "performance"})
        return self._call(f"{PSI}?{q}", timeout=120)


def rating(metric, value):
    good, poor = THRESHOLDS[metric]
    return "good" if value <= good else ("poor" if value > poor else "needs work")


def fmt(metric, value):
    if metric == "cumulative_layout_shift":
        return f"{float(value):.2f}"
    return f"{float(value) / 1000:.1f}s" if metric == "largest_contentful_paint" else f"{int(float(value))}ms"


def field_line(record):
    """'LCP 2.1s good · INP 120ms good · CLS 0.02 good' from a CrUX record, or None."""
    if not record:
        return None
    metrics = record.get("record", {}).get("metrics", {})
    parts = []
    for m in THRESHOLDS:
        p75 = metrics.get(m, {}).get("percentiles", {}).get("p75")
        if p75 is not None:
            parts.append(f"{LABELS[m]} {fmt(m, p75)} {rating(m, float(p75))}")
    return " · ".join(parts) or None


def lab_summary(result):
    """(score 0-100, 'LCP 2.3s · TBT 120ms · CLS 0.01 · FCP 1.2s', bytes) from a PageSpeed result."""
    lh = result.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    score = lh.get("categories", {}).get("performance", {}).get("score")

    def num(a):
        return audits.get(a, {}).get("numericValue")

    parts = []
    for a, label in (("largest-contentful-paint", "LCP"), ("total-blocking-time", "TBT"),
                     ("cumulative-layout-shift", "CLS"), ("first-contentful-paint", "FCP")):
        v = num(a)
        if v is None:
            continue
        parts.append(f"{label} {v:.2f}" if label == "CLS" else
                     (f"{label} {int(v)}ms" if label == "TBT" else f"{label} {v / 1000:.1f}s"))
    weight = num("total-byte-weight")
    return (None if score is None else round(score * 100)), " · ".join(parts), weight


def lab_line(client, url):
    """(the lab line, score, LCP in ms or None) for one URL."""
    result = client.lab(url)
    score, parts, weight = lab_summary(result)
    lcp = result.get("lighthouseResult", {}).get("audits", {}).get("largest-contentful-paint", {}).get("numericValue")
    kb = f" · {int(weight / 1024)} KB" if weight else ""
    return f"score {score if score is not None else '?'} · {parts}{kb}", score, lcp


def site_path(url):
    """'/funerals.html' from a final URL or a path; '/' for the home page."""
    return urllib.parse.urlparse(url).path or "/"


def lab_check(path, score, lcp, ad_paths):
    """The 'check:' line for a slow lab run, or None."""
    slow = lcp is not None and lcp > LAB_LCP_CHECK_MS
    low = score is not None and score < LAB_SCORE_CHECK
    if not (slow or low):
        return None
    lcp_text = f"{lcp / 1000:.1f}s" if lcp is not None else "?"
    score_text = f" · score {score}" if low else ""
    kind = "ad landing page" if path in ad_paths else "money page"
    return f"   check: {path} lab LCP {lcp_text}{score_text} ({kind})"


def section(client=None, key_reader=None, pages=PAGES, ad_landing=None):
    """The report section's lines (a list of strings). Never raises for a missing key: says so instead.

    ad_landing: the enabled ads' final URLs (section 4 knows them); AD_LANDING when not given."""
    ad_paths = {site_path(u) for u in (AD_LANDING if ad_landing is None else ad_landing)}
    lines = ["\n== 5d. Core Web Vitals (phones; CrUX field data, 28 days, p75; lab fallback)"]
    if client is None:
        key = (key_reader or keychain_key)()
        if not key:
            return lines + [f"   (no API key: it lives in the Keychain as {KEYCHAIN_SERVICE})"]
        client = GoogleSpeedReadOnly(key)
    origin = field_line(client.crux(origin=ORIGIN))
    lines.append(f"   whole site: {origin or 'no field data yet (too few Chrome visitors)'}")
    no_field = []
    for path in pages:
        url = ORIGIN + path
        f = field_line(client.crux(url=url))
        if f:
            lines.append(f"   {path}: {f}")
        else:
            no_field.append(path)
    if no_field:
        lines.append("   no page-level field data for: " + " ".join(no_field)
                     + " (the whole-site line above stands in for them)")
    lines.append("   lab (PageSpeed Insights, one simulated mid-range phone load each; a guide, not a ranking "
                 "figure):")
    checks = []
    for path in pages:
        try:
            line, score, lcp = lab_line(client, ORIGIN + path)
        except CwvError as e:
            lines.append(f"   {path}: lab run failed ({e})")
            continue
        lines.append(f"   {path}: {line}")
        check = lab_check(path, score, lcp, ad_paths)
        if check:
            checks.append(check)
    if checks:
        lines += checks
        lines.append("   Two lab runs a week apart above 4 s on an ad landing page is worth a look with "
                     "`cwv.py --lab`, before and after a change.")
    lines.append("   Thresholds at p75: LCP good ≤2.5s, INP ≤200ms, CLS ≤0.1. Act on a field figure rated poor; "
                 "a lab score alone is not a reason to change a page.")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help='print only "key: found" or "key: missing"')
    ap.add_argument("--lab", nargs="+", metavar="URL", help="lab runs only, for these URLs")
    ap.add_argument("--json", action="store_true", help="with --lab: print the summaries as JSON")
    args = ap.parse_args(argv)
    if args.check:
        print("key: found" if keychain_key() else "key: missing")
        return 0
    try:
        if args.lab:
            key = keychain_key()
            if not key:
                print(f"no API key in the Keychain ({KEYCHAIN_SERVICE})")
                return 1
            client = GoogleSpeedReadOnly(key)
            out = {}
            for url in args.lab:
                score, parts, weight = lab_summary(client.lab(url))
                out[url] = {"score": score, "metrics": parts, "bytes": weight}
                if not args.json:
                    print(f"{url}: score {score} · {parts} · {int((weight or 0) / 1024)} KB")
            if args.json:
                print(json.dumps(out, indent=1))
            return 0
        print("\n".join(section()))
    except CwvError as e:
        print(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
