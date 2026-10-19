#!/usr/bin/env python3
"""Contract for the Christmas landing pages (spec 2026-10-19).

christmas.html is the carol singers landing page, christmas-carol-services.html
the church carol services page, and carol-singers.html a redirect stub that
keeps the query string (and so the ad click ID).

Stdlib only — run with: python3 tests/test_christmas_pages.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Same walk as tests/test_design_markup.py: no site pages live in these.
SKIP_DIRS = {'command_centre', 'partials', 'node_modules', 'graphify-out', 'docs', 'tests'}

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def site_pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith('.html'):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


# ── carol-singers.html: the redirect stub ──

def stub_preserves_query():
    s = read('carol-singers.html')
    check("location.replace('/christmas.html' + location.search + location.hash)" in s,
          'carol-singers.html: stub must forward the query string and hash')


def stub_has_noscript_refresh():
    s = read('carol-singers.html')
    check('<noscript><meta http-equiv="refresh" content="0; url=/christmas.html"></noscript>' in s,
          'carol-singers.html: no-JS fallback missing')


def stub_is_noindex_canonical():
    s = read('carol-singers.html')
    check('<meta name="robots" content="noindex, follow">' in s, 'carol-singers.html: stub must be noindex')
    check('<link rel="canonical" href="https://londonchoralservice.com/christmas.html">' in s,
          'carol-singers.html: stub canonical must be christmas.html')
    check('<form' not in s and 'googletagmanager' not in s, 'carol-singers.html: stub must stay minimal')
    check('londonchoralservice.com/carol-singers.html' not in read('sitemap.xml'), 'sitemap.xml must not list the stub')


def main():
    stub_preserves_query()
    stub_has_noscript_refresh()
    stub_is_noindex_canonical()
    if failures:
        print(f'FAIL: {len(failures)} problem(s)')
        for f in failures[:60]:
            print('  -', f)
        sys.exit(1)
    print('OK: christmas pages')


if __name__ == '__main__':
    main()
