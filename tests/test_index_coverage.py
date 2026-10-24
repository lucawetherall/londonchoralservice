#!/usr/bin/env python3
"""Tests for scripts/reports/index_coverage.py. Stdlib only, a fake session, no network.
.venv/bin/python tests/test_index_coverage.py"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import index_coverage as ic  # noqa: E402

S = ic.SITE


class Resp:
    def __init__(self, status, body):
        self.status_code, self.ok, self.body = status, status == 200, body

    def json(self):
        return self.body


class Fake:
    def __init__(self, result):
        self.result, self.calls = result, []

    def post(self, url, json):
        self.calls.append(json)
        return Resp(200, {"inspectionResult": {"indexStatusResult": self.result}})


def test_sections():
    assert ic.section_of(f"{S}/") == "core"
    assert ic.section_of(f"{S}/weddings.html") == "core"
    assert ic.section_of(f"{S}/for-hotels.html") == "b2b"
    assert ic.section_of(f"{S}/areas/bath.html") == "areas"
    assert ic.section_of(f"{S}/areas/london/camden.html") == "boroughs"
    assert ic.section_of(f"{S}/music-guides/abide-with-me.html") == "guides"
    assert ic.section_of(f"{S}/destinations/italy.html") == "destinations"
    assert ic.section_of(f"{S}/compare/london-funeral-singers.html") == "compare"


def test_every_sitemap_url_has_a_local_page_with_its_own_canonical():
    for url in ic.sitemap_urls():
        assert ic.our_canonical(url) == url, url


def test_indexed_page_has_no_flags():
    row = ic.inspect(Fake({"verdict": "PASS", "coverageState": "Submitted and indexed", "robotsTxtState": "ALLOWED",
                           "googleCanonical": f"{S}/", "lastCrawlTime": "2026-10-20T01:02:03Z"}), f"{S}/")
    assert row["last_crawl"] == "2026-10-20" and ic.flags(row) == [], ic.flags(row)


def test_not_indexed_and_canonical_mismatch_are_flagged():
    url = f"{S}/areas/london/barnet.html"
    row = ic.inspect(Fake({"verdict": "NEUTRAL", "coverageState": "Crawled - currently not indexed",
                           "googleCanonical": f"{S}/areas/london.html"}), url)
    f = ic.flags(row)
    assert "NOT INDEXED" in f and "GOOGLE CHOSE /areas/london.html" in f, f


def test_never_crawled_page_is_not_a_robots_problem():
    row = ic.inspect(Fake({"verdict": "NEUTRAL", "coverageState": "Discovered - currently not indexed",
                           "robotsTxtState": "ROBOTS_TXT_STATE_UNSPECIFIED"}), f"{S}/professionals.html")
    assert ic.flags(row) == ["NOT INDEXED"], ic.flags(row)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
