#!/usr/bin/env python3
"""Tests for scripts/reports/cwv.py (Monday report section 5d) and scripts/generate_video_sitemap.py.
Stdlib only, a fake client, no network, no Keychain. .venv/bin/python tests/test_cwv.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import cwv  # noqa: E402


def record(lcp, inp, cls):
    m = {"largest_contentful_paint": lcp, "interaction_to_next_paint": inp, "cumulative_layout_shift": cls}
    return {"record": {"metrics": {k: {"percentiles": {"p75": v}} for k, v in m.items() if v is not None}}}


def lab(score, lcp_ms):
    return {"lighthouseResult": {"categories": {"performance": {"score": score}}, "audits": {
        "largest-contentful-paint": {"numericValue": lcp_ms}, "total-blocking-time": {"numericValue": 120},
        "cumulative-layout-shift": {"numericValue": 0.01}, "first-contentful-paint": {"numericValue": 1100},
        "total-byte-weight": {"numericValue": 512 * 1024}}}}


class Fake:
    def __init__(self, field):
        self.field, self.labs = field, []

    def crux(self, url=None, origin=None, form_factor="PHONE"):
        return self.field.get(url or origin)

    def lab(self, url, strategy="mobile"):
        self.labs.append(url)
        return lab(0.9, 2400)


def test_field_data_per_page_and_lab_for_every_page():
    fake = Fake({cwv.ORIGIN: record(2100, 150, "0.05"), cwv.ORIGIN + "/": record(5000, 600, "0.30")})
    lines = cwv.section(client=fake)
    text = "\n".join(lines)
    assert lines[0].startswith("\n== 5d. Core Web Vitals"), lines[0]
    assert "whole site: LCP 2.1s good · INP 150ms good · CLS 0.05 good" in text, text
    assert "   /: LCP 5.0s poor · INP 600ms poor · CLS 0.30 poor" in text, text
    assert "no page-level field data for: /funerals.html /weddings.html" in text, text
    assert fake.labs == [cwv.ORIGIN + p for p in cwv.PAGES], fake.labs
    assert "/funerals.html: score 90 · LCP 2.4s · TBT 120ms · CLS 0.01 · FCP 1.1s · 512 KB" in text, text


def test_no_field_data_says_so():
    text = "\n".join(cwv.section(client=Fake({})))
    assert "whole site: no field data yet (too few Chrome visitors)" in text, text


def test_missing_key_never_raises():
    lines = cwv.section(key_reader=lambda: None)
    assert lines[-1] == "   (no API key: it lives in the Keychain as lcs-pagespeed)", lines


def test_ratings_at_the_thresholds():
    assert cwv.rating("largest_contentful_paint", 2500) == "good"
    assert cwv.rating("largest_contentful_paint", 4000) == "needs work"
    assert cwv.rating("interaction_to_next_paint", 501) == "poor"
    assert cwv.rating("cumulative_layout_shift", 0.1) == "good"


def test_video_sitemap_entries_from_json_ld_and_film_stills():
    import generate_video_sitemap as gv
    page = ('<script type="application/ld+json">{"@graph": [{"@type": "VideoObject", "name": "Abide", '
            '"description": "Live.", "thumbnailUrl": "t.jpg", "uploadDate": "2026-04-02", "duration": "PT1M2S", '
            '"embedUrl": "https://www.youtube-nocookie.com/embed/G9"}]}</script>'
            '<img src="/assets/films/film-G9-1280.webp" srcset="x"><img src="assets/films/hero-film-640.webp">')
    vids, images = gv.entries("p.html", page)
    assert [v["name"] for v in vids] == ["Abide"] and gv.seconds(vids[0]["duration"]) == 62
    assert images == [gv.SITE + "/assets/films/film-G9-1280.webp", gv.SITE + "/assets/films/hero-film-1280.webp"]
    try:
        gv.entries("p.html", page.replace('"uploadDate": "2026-04-02", ', ""))
    except SystemExit as e:
        assert "has no uploadDate" in str(e)
    else:
        raise AssertionError("a VideoObject without uploadDate must fail the build")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as e:
                failures += 1
                print("FAIL", name, e)
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
