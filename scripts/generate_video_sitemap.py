#!/usr/bin/env python3
"""Generate sitemap-video.xml: the films and hero images on each page, for Google's video and image search.

Run by build.sh straight after scripts/generate_sitemap.py, and only over the pages that sitemap.xml lists
(so a noindex page never appears). For each page:

- every VideoObject in its JSON-LD becomes a <video:video> entry: title (name), description, thumbnail,
  player (embedUrl), upload date and, when given, duration. The JSON-LD is the single source; a film shown
  on a page without its VideoObject is not listed, and a VideoObject missing a required field fails the
  build rather than writing a half entry.
- every film still or hero image the page shows from assets/films/ (the click-to-play WebPs) becomes an
  <image:image> entry, the 1280px file.

A page with neither is left out. The file is generated; never hand-edit it.
"""
import json
import os
import re
import sys
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://londonchoralservice.com'
OUT = 'sitemap-video.xml'
REQUIRED = ('name', 'description', 'thumbnailUrl', 'uploadDate', 'embedUrl')
LDJSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
FILM_IMG = re.compile(r'<img src="/?(assets/films/[\w-]+?)(?:-640|-1280)\.webp"')
DURATION = re.compile(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$')


def page_file(loc):
    path = loc[len(SITE):].lstrip('/')
    return path + 'index.html' if path == '' or path.endswith('/') else path


def videos(node):
    """Every VideoObject dict anywhere in a JSON-LD value."""
    if isinstance(node, dict):
        t = node.get('@type')
        if t == 'VideoObject' or (isinstance(t, list) and 'VideoObject' in t):
            yield node
        for v in node.values():
            yield from videos(v)
    elif isinstance(node, list):
        for v in node:
            yield from videos(v)


def seconds(iso):
    m = DURATION.match(iso or '')
    if not m or not any(m.groups()):
        return None
    h, mi, s = (int(g or 0) for g in m.groups())
    return h * 3600 + mi * 60 + s


def entries(f, html):
    """([video dicts], [image URLs]) for one page."""
    found, seen = [], set()
    for block in LDJSON.findall(html):
        for v in videos(json.loads(block)):
            missing = [k for k in REQUIRED if not v.get(k)]
            if missing:
                raise SystemExit(f'{f}: VideoObject "{v.get("name", "?")}" has no {", ".join(missing)}')
            if v['embedUrl'] not in seen:
                seen.add(v['embedUrl'])
                found.append(v)
    images = []
    for base in FILM_IMG.findall(html):
        url = f'{SITE}/{base}-1280.webp'
        if url not in images:
            images.append(url)
    return found, images


def main():
    sitemap = open('sitemap.xml', encoding='utf-8').read()
    locs = re.findall(r'<loc>([^<]+)</loc>', sitemap)
    lines = ["<?xml version='1.0' encoding='UTF-8'?>",
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"',
             '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    n_pages = n_videos = n_images = 0
    for loc in locs:
        f = page_file(loc)
        html = open(f, encoding='utf-8').read()
        vids, images = entries(f, html)
        if not vids and not images:
            continue
        n_pages += 1
        lines += ['  <url>', f'    <loc>{escape(loc)}</loc>']
        for url in images:
            n_images += 1
            lines += ['    <image:image>', f'      <image:loc>{escape(url)}</image:loc>', '    </image:image>']
        for v in vids:
            n_videos += 1
            lines += ['    <video:video>',
                      f'      <video:thumbnail_loc>{escape(v["thumbnailUrl"])}</video:thumbnail_loc>',
                      f'      <video:title>{escape(v["name"][:100])}</video:title>',
                      f'      <video:description>{escape(v["description"][:2048])}</video:description>',
                      f'      <video:player_loc>{escape(v["embedUrl"])}</video:player_loc>']
            d = seconds(v.get('duration'))
            if d:
                lines.append(f'      <video:duration>{d}</video:duration>')
            lines += [f'      <video:publication_date>{escape(v["uploadDate"])}</video:publication_date>',
                      '      <video:family_friendly>yes</video:family_friendly>',
                      '    </video:video>']
        lines.append('  </url>')
    lines.append('</urlset>')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'Generated {OUT} ({n_pages} pages, {n_videos} film entries, {n_images} images)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
