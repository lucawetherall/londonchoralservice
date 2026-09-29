#!/usr/bin/env python3
"""Tests for scripts/ads/lookup_ref.py: the Python ref must equal the one the site's lcsShortRef
(partials/analytics.html) writes into WhatsApp messages and emails. Runs the partial's own function
under node; never contacts Google."""
import datetime, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
import lookup_ref as lr  # noqa: E402

IDS = [
    "CjwKCAjwoOjVBhArEiwAUwDak-w3VeuymUYYNXR3A5xT5q1Kt9HQYShaxk8NdB7p4D2-y6d0JV-eNhoCJmkQAvD_BwE",
    "Cj0KCQjw_example-gclid_123",
    "0AAAAAD-example-gbraid",
    "a",
]


def js_refs(ids):
    src = open(os.path.join(ROOT, "partials", "analytics.html")).read()
    fn = re.search(r"function lcsShortRef\(id\) \{.*?\n    \}\n", src, re.S)
    assert fn, "lcsShortRef not found in partials/analytics.html"
    code = fn.group(0) + f"console.log(JSON.stringify({json.dumps(ids)}.map(lcsShortRef)));"
    return json.loads(subprocess.run(["node", "-e", code], capture_output=True, text=True, check=True).stdout)


def test_matches_site():
    if not shutil.which("node"):
        print("skip: node not installed")
        return
    assert js_refs(IDS) == [lr.short_ref(i) for i in IDS]


def test_shape():
    for i in IDS:
        r = lr.short_ref(i)
        assert len(r) == 4 and all(c in lr.ALPHABET for c in r), r
    assert lr.short_ref(IDS[0]) != lr.short_ref(IDS[1])


def test_normalise():
    r = lr.short_ref(IDS[0])
    assert lr.normalise(f"Ref: {r.lower()}") == r
    for bad in ("K0P2", "KIP2", "K7P", "K7P2X"):
        try:
            lr.normalise(bad)
        except SystemExit:
            continue
        raise AssertionError(bad)


def test_days():
    today = datetime.date(2026, 9, 29)
    assert lr.days_to_search("2026-09-28", today) == [datetime.date(2026, 9, d) for d in (28, 27, 26)]
    assert len(lr.days_to_search(None, today)) == 90
    assert lr.days_to_search("2026-01-01", today) == []


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
    print("ok")
