#!/usr/bin/env python3
"""Markup contract for the quiet design fixes (spec 2026-09-29).

Stdlib only — run with: python3 tests/test_design_markup.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# build.sh skips dot-directories, graphify-out, command_centre and partials;
# docs, tests and node_modules hold no site pages either.
SKIP_DIRS = {'command_centre', 'partials', 'node_modules', 'graphify-out', 'docs', 'tests'}

PROMO = 'Lov_NegzVhM'
ABIDE = 'G9-R6k5n7Io'
UBI = '-GQaQEGhYEs'
# It's the Most Wonderful Time of the Year (re-upload, 30 Sep 2026).
WONDERFUL = 'UOy498rsonU'

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
    'christmas.html': WONDERFUL,
    'carol-singers.html': WONDERFUL,
    'christmas-pricing.html': WONDERFUL,
    'for-funeral-directors.html': ABIDE,
    'for-wedding-planners.html': UBI,
}

# The promo film carries no caption (owner decision, 29 Sep 2026).
CAPTIONS = {
    PROMO: None,
    ABIDE: 'Abide With Me, sung by our full choir',
    UBI: 'Ubi Caritas by Ola Gjeilo, sung by a quintet',
    WONDERFUL: 'It&rsquo;s the Most Wonderful Time of the Year, sung by our full choir',
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
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith('.html'):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


def check_nav_carets():
    nav = read('partials/nav.html')
    check('&#9662;' not in nav, 'partials/nav.html still has the ▾ glyph')
    carets = re.findall(r'<span class="dropdown-caret" aria-hidden="true">(.*?)</span>', nav)
    check(len(carets) == 3, f'expected 3 dropdown carets, found {len(carets)}')
    check(all(c == '' for c in carets), 'dropdown carets must be empty spans')


def check_play_buttons():
    new = 0
    for rel in site_pages():
        html = read(rel)
        if 'M66.52' in html:
            failures.append(f'{rel}: old YouTube play pill still present')
        new += html.count(NEW_PLAY_BTN)
        check(html.count('class="play-btn"') == html.count(NEW_PLAY_BTN),
              f'{rel}: a play-btn does not use the new SVG')
    check(new >= 72, f'expected at least 72 new play buttons, found {new}')
    return new


def check_heroes():
    for page, film in HERO_FILMS.items():
        html = read(page)
        start = html.find('<div class="page-wrap hero">')
        check(start != -1, f'{page}: no hero')
        if start == -1:
            continue
        # Markup order matches the phone layout (and so the tab order):
        # breadcrumb, h1, film with caption, then the hero text.
        video_at = html.find('<div class="hero-video">', start)
        text_at = html.find('<div class="hero-text">', start)
        section_end = html.find('</section>', start)
        check(-1 not in (text_at, video_at, section_end), f'{page}: hero markup not found')
        if -1 in (text_at, video_at, section_end):
            continue
        check(video_at < text_at < section_end, f'{page}: .hero-video must come before .hero-text')
        if not video_at < text_at < section_end:
            continue
        head = html[start:video_at]
        video = html[video_at:text_at]
        text = html[text_at:section_end]

        check('<h1>' in head, f'{page}: h1 must sit before .hero-video')
        check('<div class="hero-text">' not in head, f'{page}: .hero-text must not sit before the film')
        check('<h1>' not in text, f'{page}: h1 inside .hero-text')
        check('class="breadcrumb"' not in text, f'{page}: breadcrumb inside .hero-text')
        if page != 'index.html':
            check('class="breadcrumb"' in head, f'{page}: breadcrumb must sit before the h1')
            check(head.find('class="breadcrumb"') < head.find('<h1>'),
                  f'{page}: breadcrumb must come before the h1')

        check(f'data-video="{film}"' in video, f'{page}: hero film should be {film}')
        check(f'/vi/{film}/maxresdefault.jpg' in video, f'{page}: hero thumbnail should be {film}')
        if CAPTIONS[film] is None:
            check('class="video-caption"' not in video, f'{page}: the {film} film takes no caption')
        else:
            caption = f'<p class="video-caption">{CAPTIONS[film]}</p>'
            check(video.count(caption) == 1, f'{page}: needs exactly one caption "{CAPTIONS[film]}"')


def main():
    check_nav_carets()
    plays = check_play_buttons()
    check_heroes()
    if failures:
        print(f'FAIL: {len(failures)} problem(s)')
        for f in failures[:40]:
            print('  -', f)
        sys.exit(1)
    print(f'OK: nav carets, {plays} play buttons, {len(HERO_FILMS)} hero pages')


if __name__ == '__main__':
    main()
