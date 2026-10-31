#!/usr/bin/env python3
"""One-off sweep for the Christmas landing pages (spec 2026-10-19).

carol-singers.html is now a redirect stub, so nothing on the site should link
to it. This rewrites, outside the @include regions (the build owns those):

1. every link to carol-singers.html -> christmas.html, keeping its prefix;
2. every link to christmas.html whose anchor text names a carol service or
   carol concert -> christmas-carol-services.html (the church page owns those);
3. in the church-service guides, the enquiry buttons and the sticky-bar
   "Enquire" -> christmas-carol-services.html.

Kept in the repo as the record of the sweep.

Usage: python3 scripts/repoint_christmas_links.py [--dry-run]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'partials', 'node_modules', 'graphify-out', 'docs', 'tests'}
CHURCH_GUIDES = {
    'music-guides/nine-lessons-and-carols.html',
    'music-guides/church-carol-service-choir-hire.html',
    'music-guides/carols-by-candlelight.html',
    'music-guides/advent-carols-vs-christmas-carols.html',
    'music-guides/christmas-carols-guide.html',
    'music-guides/corporate-carol-service.html',
}
INCLUDE = re.compile(r'(<!-- @include-start (\S+) -->.*?<!-- @include-end \2 -->)', re.S)
# The prefix is empty or ends in "/", so best-christmas-carol-singers.html never matches.
LINK = re.compile(r'(<a\b[^>]*?href=")((?:[^"]*/)?)(carol-singers|christmas)\.html((?:[?#][^"]*)?"[^>]*>)(.*?)(</a>)', re.S)
SERVICE = re.compile(r'carol (service|concert)', re.I)


def repoint(rel, text):
    counts = {'stub': 0, 'service': 0, 'cta': 0}

    def fix(m):
        start, prefix, page, attrs, anchor, end = m.groups()
        if page == 'carol-singers':
            counts['stub'] += 1
            page = 'christmas'
        if page == 'christmas':
            is_cta = 'class="btn-link' in start + attrs or 'mobile-cta-enquire' in start + attrs
            if SERVICE.search(re.sub(r'<[^>]+>', '', anchor)):
                counts['service'] += 1
                page = 'christmas-carol-services'
            elif rel in CHURCH_GUIDES and is_cta:
                counts['cta'] += 1
                page = 'christmas-carol-services'
        return f'{start}{prefix}{page}.html{attrs}{anchor}{end}'

    parts = INCLUDE.split(text)
    out = []
    # INCLUDE.split yields text, whole region, partial name, text, ...
    i = 0
    while i < len(parts):
        out.append(LINK.sub(fix, parts[i]))
        if i + 1 < len(parts):
            out.append(parts[i + 1])
        i += 3
    return ''.join(out), counts


def main():
    dry = '--dry-run' in sys.argv
    total = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.') and d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith('.html'):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
            if rel == 'carol-singers.html':
                continue
            path = os.path.join(ROOT, rel)
            with open(path, encoding='utf-8') as fh:
                text = fh.read()
            new, counts = repoint(rel, text)
            if new != text:
                total += 1
                print(f'{rel}: ' + ', '.join(f'{k} {v}' for k, v in counts.items() if v))
                if not dry:
                    with open(path, 'w', encoding='utf-8') as fh:
                        fh.write(new)
    print(f'{"Would change" if dry else "Changed"} {total} files')


if __name__ == '__main__':
    main()
