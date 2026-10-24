#!/usr/bin/env python3
"""Read-only: which sitemap pages Google has indexed. Runs Search Console's URL Inspection (the same call as
weekly_review.py section 7) over every <loc> in the repo's sitemap.xml and prints, per URL, the coverage state,
the last crawl, Google's chosen canonical against ours, and a flag for anything not indexed; then a summary by
section (core, b2b, areas, boroughs, guides, destinations, compare). Changes nothing.

Uses Application Default Credentials (webmasters.readonly is enough). The quota is 2,000 inspections a day and
600 a minute per property; a full run is ~165, so it can run a few times a day.

    .venv/bin/python scripts/reports/index_coverage.py [--section boroughs] [--limit 20] [--json out.json]
    .venv/bin/python scripts/reports/index_coverage.py --from-json out.json   # re-print a saved run, no API calls

"Ours" is the page's <link rel="canonical"> in the repo; a page whose canonical isn't its own URL is flagged too.
"""

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GSC_SITE = "sc-domain:londonchoralservice.com"
SITE = "https://londonchoralservice.com"
INSPECT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SECTIONS = ["core", "b2b", "areas", "boroughs", "guides", "destinations", "compare"]
CANONICAL = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)


def sitemap_urls(path=REPO / "sitemap.xml"):
    return re.findall(r"<loc>([^<]+)</loc>", path.read_text(encoding="utf-8"))


def section_of(url):
    path = url.replace(SITE, "").lstrip("/")
    if path.startswith("areas/london/"):
        return "boroughs"
    for prefix, name in (("areas/", "areas"), ("music-guides/", "guides"), ("destinations/", "destinations"),
                         ("compare/", "compare"), ("for-", "b2b")):
        if path.startswith(prefix):
            return name
    return "core"


def local_file(url):
    path = url.replace(SITE, "").lstrip("/")
    return REPO / (path + "index.html" if path == "" or path.endswith("/") else path)


def our_canonical(url):
    f = local_file(url)
    if not f.exists():
        return None
    m = CANONICAL.search(f.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def inspect(s, url):
    """One URL Inspection call, retried once on a 429/5xx. Returns the row this script prints and saves."""
    for attempt in (0, 1):
        r = s.post(INSPECT, json={"inspectionUrl": url, "siteUrl": GSC_SITE})
        if r.ok or r.status_code not in (429, 500, 503) or attempt:
            break
        time.sleep(20)
    row = {"url": url, "section": section_of(url), "ours": our_canonical(url)}
    if not r.ok:
        row["error"] = f"{r.status_code} {r.json().get('error', {}).get('message', '')[:80]}"
        return row
    ir = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
    row.update(verdict=ir.get("verdict", "?"), coverage=ir.get("coverageState", "?"),
               last_crawl=(ir.get("lastCrawlTime") or "")[:10], google=ir.get("googleCanonical"),
               declared=ir.get("userCanonical"), robots=ir.get("robotsTxtState"), indexing=ir.get("indexingState"),
               fetch=ir.get("pageFetchState"), referrers=len(ir.get("referringUrls") or []),
               in_sitemap=bool(ir.get("sitemap")))
    return row


def flags(row):
    out = []
    if row.get("error"):
        return ["ERROR " + row["error"]]
    if row.get("verdict") != "PASS":
        out.append("NOT INDEXED")
    if row.get("ours") and row["ours"] != row["url"]:
        out.append("OUR CANONICAL POINTS ELSEWHERE")
    if row.get("google") and row["google"] != (row.get("ours") or row["url"]):
        out.append("GOOGLE CHOSE " + (row["google"].replace(SITE, "") or "/"))
    if row.get("robots") not in (None, "ALLOWED", "ROBOTS_TXT_STATE_UNSPECIFIED"):  # unspecified: never crawled
        out.append(f"robots {row['robots']}")
    if row.get("indexing") not in (None, "INDEXING_ALLOWED", "INDEXING_STATE_UNSPECIFIED"):
        out.append(f"indexing {row['indexing']}")
    if row.get("fetch") not in (None, "SUCCESSFUL", "PAGE_FETCH_STATE_UNSPECIFIED"):
        out.append(f"fetch {row['fetch']}")
    return out


def line(row):
    path = row["url"].replace(SITE, "") or "/"
    if row.get("error"):
        return f"   {path:56} ERROR {row['error']}"
    f = flags(row)
    return (f"   {path:56} {row['coverage'][:40]:40} crawl {row['last_crawl'] or 'never':10}"
            f"{'  !' + '; '.join(f) if f else ''}")


def report(rows):
    by = defaultdict(list)
    for row in rows:
        by[row["section"]].append(row)
    for name in SECTIONS:
        if not by[name]:
            continue
        print(f"\n== {name} ({len(by[name])})")
        for row in sorted(by[name], key=lambda r: (r.get("verdict") == "PASS", r["url"])):
            print(line(row))
    print("\n== summary: indexed / inspected, by section")
    total = Counter()
    for name in SECTIONS:
        rs = by[name]
        if not rs:
            continue
        ok = sum(r.get("verdict") == "PASS" for r in rs)
        states = Counter(r.get("coverage", "error") for r in rs if r.get("verdict") != "PASS")
        total.update(ok=ok, all=len(rs))
        rest = ", ".join(f"{n} {s}" for s, n in states.most_common())
        print(f"   {name:13} {ok:3} / {len(rs):3}{'   not indexed: ' + rest if rest else ''}")
    print(f"   {'all':13} {total['ok']:3} / {total['all']:3}")
    mism = [r for r in rows if any(x.startswith(("GOOGLE CHOSE", "OUR CANONICAL")) for x in flags(r))]
    print(f"   canonical mismatches: {len(mism)}")
    for r in mism:
        print(f"     {r['url'].replace(SITE, '') or '/'}: ours {r.get('ours')} · Google {r.get('google')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=SECTIONS)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--json", type=Path, help="also save the rows here")
    ap.add_argument("--from-json", type=Path, help="print a saved run instead of calling the API")
    args = ap.parse_args()
    if args.from_json:
        report(json.loads(args.from_json.read_text()))
        return
    urls = [u for u in sitemap_urls() if not args.section or section_of(u) == args.section][:args.limit]
    import google.auth
    from google.auth.transport.requests import AuthorizedSession
    creds, _ = google.auth.default()
    s = AuthorizedSession(creds)
    rows = []
    for i, url in enumerate(urls, 1):
        rows.append(inspect(s, url))
        print(f"\r   inspected {i}/{len(urls)}", end="", file=sys.stderr, flush=True)
    print(file=sys.stderr)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1))
    report(rows)


if __name__ == "__main__":
    main()
