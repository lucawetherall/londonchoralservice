#!/usr/bin/env python3
"""Generate sitemap.xml from the built pages, with lastmod driven by content.

Run by build.sh after partial expansion and CSS inlining. Rules:

- Every *.html outside partials/ and graphify-out/ is a candidate; pages
  carrying <meta name="robots" content="noindex…"> are excluded.
- lastmod comes from data/page-dates.json, keyed by URL path. Each entry
  stores a hash of the page's *content* (body with the inlined <style>,
  the @include regions and the date markers stripped) and the date that
  content last changed. When the hash changes the date becomes today.
  A page not yet in the file is seeded from git: the date of the oldest
  commit whose version has the same content hash (today if uncommitted).
- changefreq and priority are carried over from the existing sitemap.xml;
  new pages get defaults by directory.

The effect: a CSS-only rebuild or a nav change never bumps lastmod, and a
real copy edit always does. sitemap.xml and data/page-dates.json are both
generated; do not hand-edit either.
"""
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://londonchoralservice.com'
DATES = 'data/page-dates.json'
SITEMAP = 'sitemap.xml'
TODAY = dt.date.today().isoformat()

DEFAULTS = [  # (path prefix, changefreq, priority)
    ('music-guides/', 'monthly', '0.6'),
    ('areas/london/', 'monthly', '0.5'),
    ('areas/', 'monthly', '0.6'),
    ('destinations/', 'monthly', '0.5'),
    ('compare/', 'monthly', '0.6'),
    ('', 'monthly', '0.7'),
]

STRIP = [
    re.compile(r'<style>.*?</style>', re.S),
    re.compile(r'<!-- @include-start [^ ]+ -->.*?<!-- @include-end [^ ]+ -->', re.S),
    re.compile(r'<p class="guide-meta">(?:Published|Updated|Last updated)[^<]*(?:<time[^>]*>[^<]*</time>[^<]*)*</p>'),
    re.compile(r'"dateModified":\s*"[^"]*"'),
    re.compile(r'<meta property="article:modified_time" content="[^"]*">'),
    re.compile(r'<time datetime="[^"]*">[^<]*</time>'),
]


def pages():
    out = []
    for dirpath, dirnames, filenames in os.walk('.'):
        # Skip every dot-directory, not just .git. Tooling writes scratch HTML into
        # .superpowers/ and .claude/, and a walk that picks those up puts fragments
        # into the public sitemap and crashes generate_llms_full.py, which splits on
        # </head>. The named entries below are the non-hidden directories to skip.
        dirnames[:] = [d for d in dirnames
                       if not d.startswith('.')
                       and d not in ('partials', 'graphify-out', 'node_modules')]
        for fn in filenames:
            if fn.endswith('.html'):
                out.append(os.path.normpath(os.path.join(dirpath, fn)))
    return sorted(out)


def url_path(f):
    if f == 'index.html':
        return '/'
    if f.endswith('/index.html'):
        return '/' + f[:-len('index.html')]
    return '/' + f


def content_hash(html):
    body = html.split('</head>', 1)[-1]
    for rx in STRIP:
        body = rx.sub('', body)
    body = re.sub(r'\s+', ' ', body).strip()
    return hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]


def is_noindex(html):
    return re.search(r'<meta name="robots" content="noindex', html) is not None


def git_seed_date(f, h, limit=40):
    """Date of the oldest commit whose version of f still has content hash h,
    walking back from HEAD; None if the working copy differs from HEAD."""
    r = subprocess.run(['git', 'log', f'-{limit}', '--format=%H %cs', '--', f], capture_output=True, text=True)
    seed = None
    for line in r.stdout.splitlines():
        sha, date = line.split()
        v = subprocess.run(['git', 'show', f'{sha}:{f}'], capture_output=True, text=True)
        if v.returncode != 0 or content_hash(v.stdout) != h:
            break
        seed = date
    return seed


def existing_meta():
    meta = {}
    order = []
    if not os.path.exists(SITEMAP):
        return meta, order
    s = open(SITEMAP, encoding='utf-8').read()
    for m in re.finditer(r'<url>\s*<loc>([^<]+)</loc>(.*?)</url>', s, re.S):
        loc = m.group(1).replace(SITE, '') or '/'
        cf = re.search(r'<changefreq>([^<]+)</changefreq>', m.group(2))
        pr = re.search(r'<priority>([^<]+)</priority>', m.group(2))
        meta[loc] = (cf.group(1) if cf else None, pr.group(1) if pr else None)
        order.append(loc)
    return meta, order


def main():
    dates = json.load(open(DATES)) if os.path.exists(DATES) else {}
    meta, order = existing_meta()
    entries = {}
    changed = []
    for f in pages():
        html = open(f, encoding='utf-8').read()
        if is_noindex(html):
            continue
        u = url_path(f)
        h = content_hash(html)
        rec = dates.get(u)
        if rec and rec.get('hash') == h:
            lastmod = rec['lastmod']
        elif rec:
            lastmod = TODAY
            changed.append(u)
        else:
            lastmod = git_seed_date(f, h) or TODAY
        dates[u] = {'hash': h, 'lastmod': lastmod}
        cf, pr = meta.get(u, (None, None))
        if cf is None or pr is None:
            for prefix, dcf, dpr in DEFAULTS:
                if f.startswith(prefix):
                    cf, pr = cf or dcf, pr or dpr
                    break
        entries[u] = (lastmod, cf, pr)

    # drop records for pages that no longer exist
    for u in list(dates):
        if u not in entries:
            del dates[u]

    ordered = [u for u in order if u in entries] + sorted(u for u in entries if u not in order)
    lines = ["<?xml version='1.0' encoding='UTF-8'?>",
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in ordered:
        lastmod, cf, pr = entries[u]
        lines += ['  <url>', f'    <loc>{SITE}{u}</loc>', f'    <lastmod>{lastmod}</lastmod>',
                  f'    <changefreq>{cf}</changefreq>', f'    <priority>{pr}</priority>', '  </url>']
    lines.append('</urlset>')
    open(SITEMAP, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    os.makedirs('data', exist_ok=True)
    json.dump(dict(sorted(dates.items())), open(DATES, 'w', encoding='utf-8'), indent=1)
    open(DATES, 'a').write('\n')
    print(f'Generated sitemap.xml ({len(ordered)} URLs; {len(changed)} lastmod bumped to {TODAY})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
