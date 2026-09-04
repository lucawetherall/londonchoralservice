#!/usr/bin/env python3
"""Keep every date signal on an article page in agreement.

Run by build.sh after generate_sitemap.py. For each page carrying Article
JSON-LD (music-guides/*.html, compare/*.html) the content-change date in
data/page-dates.json becomes the single source for:

- JSON-LD "dateModified"
- <meta property="article:modified_time">
- the visible date line: <p class="guide-meta">Published <time>…</time>
  · Updated <time>…</time></p> (the Updated half is omitted while the
  page has never changed since publication)

datePublished is never touched. generate_sitemap.py strips all three
signals before hashing, so this script never changes a page's lastmod.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DATES = json.load(open('data/page-dates.json'))
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


def uk(iso):
    y, m, d = iso.split('-')
    return f'{int(d)} {MONTHS[int(m) - 1]} {y}'


def date_line(pub, mod):
    s = f'<p class="guide-meta">Published <time datetime="{pub}">{uk(pub)}</time>'
    if mod > pub:
        s += f' &middot; Updated <time datetime="{mod}">{uk(mod)}</time>'
    return s + '</p>'


DATE_LINE_RX = re.compile(r'<p class="guide-meta">(?:Published|Last updated:)[^<]*(?:<time[^>]*>[^<]*</time>[^<]*)*</p>')
BYLINE_PUB_RX = re.compile(r'(<p class="guide-meta">By Luca Wetherall[^<]*?) &middot; Published [^<]*</p>')


def main():
    n = 0
    for f in sorted(glob.glob('music-guides/*.html') + glob.glob('compare/*.html')):
        s = open(f, encoding='utf-8').read()
        if '"@type": "Article"' not in s:
            continue
        u = '/' + f
        if u not in DATES:
            print(f'sync_dates: no lastmod for {f}', file=sys.stderr)
            return 1
        mod = DATES[u]['lastmod']
        pub_m = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})"', s)
        if not pub_m:
            print(f'sync_dates: no datePublished in {f}', file=sys.stderr)
            return 1
        pub = pub_m.group(1)
        if mod < pub:
            mod = pub
        t = re.sub(r'"dateModified":\s*"[^"]*"', f'"dateModified": "{mod}"', s)
        t = re.sub(r'<meta property="article:modified_time" content="[^"]*">',
                   f'<meta property="article:modified_time" content="{mod}">', t)
        line = date_line(pub, mod)
        # byline variant carrying "· Published …": move the date to its own line
        t = BYLINE_PUB_RX.sub(r'\1</p>\n          ' + line, t)
        if DATE_LINE_RX.search(t):
            t = DATE_LINE_RX.sub(line, t, count=1)
        elif line not in t:
            # no visible date line at all: add one after the byline
            t = re.sub(r'(<p class="guide-meta">By Luca Wetherall[^<]*</p>)', r'\1\n          ' + line, t, count=1)
        if t != s:
            open(f, 'w', encoding='utf-8').write(t)
            n += 1
    print(f'Synchronised dates on {n} article pages')
    return 0


if __name__ == '__main__':
    sys.exit(main())
