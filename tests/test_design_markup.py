#!/usr/bin/env python3
"""Markup contract for the quiet design fixes (spec 2026-09-29).

Stdlib only — run with: python3 tests/test_design_markup.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', '.claude', 'partials', 'node_modules', 'graphify-out', '.venv', 'docs', 'tests'}

PROMO = 'Lov_NegzVhM'
ABIDE = 'G9-R6k5n7Io'
UBI = '-GQaQEGhYEs'
BELLS = 'dGYqQf6BDAk'

HERO_FILMS = {
    'index.html': PROMO,
    'weddings.html': PROMO,
    'funerals.html': PROMO,
    'corporate.html': PROMO,
    'pricing.html': PROMO,
    'for-charities.html': PROMO,
    'for-event-managers.html': PROMO,
    'for-hotels.html': PROMO,
    'for-livery-companies.html': PROMO,
    'for-property-managers.html': PROMO,
    'christmas.html': BELLS,
    'carol-singers.html': BELLS,
    'christmas-pricing.html': BELLS,
    'for-funeral-directors.html': ABIDE,
    'for-wedding-planners.html': UBI,
}

CAPTIONS = {
    PROMO: 'A 43-second film of our singers',
    ABIDE: 'Abide With Me, sung by our full choir',
    UBI: 'Ubi Caritas by Ola Gjeilo, sung by a quintet',
    BELLS: 'Carol of the Bells, sung by our full choir',
}

NEW_PLAY_BTN = ('<svg class="play-btn" viewBox="0 0 56 56" aria-hidden="true">'
                '<circle cx="28" cy="28" r="27"/><path d="M23 19v18l15-9z"/></svg>')

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def site_pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith('.html'):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


def test_nav_carets_are_empty():
    nav = read('partials/nav.html')
    check('&#9662;' not in nav, 'partials/nav.html still has the ▾ glyph')
    carets = re.findall(r'<span class="dropdown-caret" aria-hidden="true">(.*?)</span>', nav)
    check(len(carets) == 3, f'expected 3 dropdown carets, found {len(carets)}')
    check(all(c == '' for c in carets), 'dropdown carets must be empty spans')


def test_play_buttons():
    old = new = 0
    for rel in site_pages():
        html = read(rel)
        if 'M66.52' in html:
            old += 1
            failures.append(f'{rel}: old YouTube play pill still present')
        new += html.count(NEW_PLAY_BTN)
        check(html.count('class="play-btn"') == html.count(NEW_PLAY_BTN),
              f'{rel}: a play-btn does not use the new SVG')
    check(new == 72, f'expected 72 new play buttons, found {new}')


def test_hero_order_caption_and_film():
    for page, film in HERO_FILMS.items():
        html = read(page)
        start = html.find('<div class="page-wrap hero">')
        check(start != -1, f'{page}: no hero')
        if start == -1:
            continue
        text_at = html.find('<div class="hero-text">', start)
        video_at = html.find('<div class="hero-video">', start)
        section_end = html.find('</section>', start)
        head = html[start:text_at]
        text = html[text_at:video_at]
        video = html[video_at:section_end]

        check('<h1>' in head, f'{page}: h1 must sit before .hero-text')
        check('<h1>' not in text, f'{page}: h1 still inside .hero-text')
        check('class="breadcrumb"' not in text, f'{page}: breadcrumb still inside .hero-text')
        if page != 'index.html':
            check('class="breadcrumb"' in head, f'{page}: breadcrumb must sit before .hero-text')
            check(head.find('class="breadcrumb"') < head.find('<h1>'),
                  f'{page}: breadcrumb must come before the h1')

        check(f'data-video="{film}"' in video, f'{page}: hero film should be {film}')
        check(f'/vi/{film}/maxresdefault.jpg' in video, f'{page}: hero thumbnail should be {film}')
        caption = f'<p class="video-caption">{CAPTIONS[film]}</p>'
        check(video.count(caption) == 1, f'{page}: missing caption "{CAPTIONS[film]}"')


def main():
    test_nav_carets_are_empty()
    test_play_buttons()
    test_hero_order_caption_and_film()
    if failures:
        print(f'FAIL: {len(failures)} problem(s)')
        for f in failures[:40]:
            print('  -', f)
        sys.exit(1)
    print('OK: nav carets, 72 play buttons, 15 hero pages')


if __name__ == '__main__':
    main()
