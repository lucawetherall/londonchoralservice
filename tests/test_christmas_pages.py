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


# ── christmas.html: the carol singers landing page ──

EVENT_FILMS = {'csFWUu-r85Y', 'zDlSFb74p4E', 'UaVhyyidlTs'}  # Most Wonderful Time, Ding Dong, Winter Wonderland
HYMNS = ('Be Thou My Vision', 'Guide Me, O Thou', 'All Things Bright')
INCLUDE = re.compile(r'<!-- @include-start (\S+) -->.*?<!-- @include-end \1 -->', re.S)


def main_part(html):
    """The page body between <main and </main>, outside any include region."""
    body = html.split('<main', 1)[1].split('</main>', 1)[0]
    return INCLUDE.sub('', body)


def hero(html):
    return html.split('class="hero-video"', 1)[1][:1500]


def faq_names(html):
    return re.findall(r'"@type": "Question",\s*"name": "([^"]+)"', html)


def faq_unique(path):
    mine = faq_names(read(path))
    check(len(mine) >= 5, f'{path}: expected at least five FAQ questions, found {len(mine)}')
    for rel in site_pages():
        if rel == path:
            continue
        clash = set(mine) & set(faq_names(read(rel)))
        check(not clash, f'{path}: FAQ question(s) also on {rel}: {sorted(clash)}')


def videos_have_schema(html, films, path):
    for vid in films:
        check(f'embed/{vid}"' in html, f'{path}: VideoObject for {vid}')
    embeds = set(re.findall(r'youtube-nocookie\.com/embed/([^"]+)"', html))
    check(embeds == set(films), f'{path}: VideoObjects {sorted(embeds)} should match films {sorted(films)}')


def form_contract(path, page, redirect, event_types):
    html = read(path)
    form = html.split('id="enquiry"', 1)[1] if 'id="enquiry"' in html else ''
    check(form != '', f'{path}: no #enquiry section')
    form = form.split('</form>', 1)[0]
    for needle in ('name="access_key" value="dc1af546-26ac-45b3-a85d-064a3a59886d"',
                   '<input type="hidden" name="occasion" value="christmas">',
                   f'<input type="hidden" name="page" value="{page}">',
                   'name="botcheck"', 'class="h-captcha"', 'name="ad_measurement"',
                   f'data-redirect="{redirect}"', 'name="event_type"', 'name="guests"',
                   'name="postcode_or_venue"', 'name="email"', 'name="name"'):
        check(needle in form, f'{path}: form needs {needle}')
    for bad in ('>Funeral<', '>Wedding<', '>A funeral director<', '>A wedding planner or venue<'):
        check(bad not in form, f'{path}: form still offers {bad}')
    options = re.findall(r'<option>([^<]+)</option>',
                         form.split('name="event_type"', 1)[1].split('</select>', 1)[0]) if 'name="event_type"' in form else []
    check(options == list(event_types), f'{path}: event_type options {options} should be {list(event_types)}')


def christmas_films():
    c = read('christmas.html')
    check('csFWUu-r85Y' in hero(c), "christmas.html: hero should be It's the Most Wonderful Time")
    films = set(re.findall(r'data-video="([^"]+)"', c))
    check(films == EVENT_FILMS, f'christmas.html: films {sorted(films)} should be {sorted(EVENT_FILMS)}')
    videos_have_schema(c, EVENT_FILMS, 'christmas.html')


def christmas_no_hymns():
    m = main_part(read('christmas.html'))
    for piece in HYMNS + ('Carol of the Bells', 'Blue Christmas'):
        check(piece not in m, f'christmas.html: {piece} should not be on the page')


def christmas_prices():
    c = read('christmas.html')
    for p in ('£1,150', '£1,400', '£1,600', '£2,000', '£3,000', '£250'):
        check(p in c or p.replace('£', '&pound;') in c, f'christmas.html: price {p} missing')
    check('VAT' not in main_part(c), 'christmas.html: no VAT wording')
    check('"name": "Soloist"' not in c, 'christmas.html: carol bookings start at four voices')


def christmas_order():
    c = read('christmas.html')
    m = c.split('<main', 1)[1]
    marks = ['class="hero-video"', 'James', 'href="#enquiry" class="btn-link">', 'id="enquiry"']
    first = m.find('class="hero-video"')
    # the mid-page CTA: a #enquiry button after the films section
    films_end = m.find('id="hear"')
    positions = [first, m.find('James'), m.find('href="#enquiry"', films_end), m.find('id="enquiry"')]
    check(-1 not in positions and positions == sorted(positions),
          f'christmas.html: section order wrong {list(zip(marks, positions))}')
    check(films_end != -1, 'christmas.html: films section needs id="hear"')


def christmas_guides():
    m = main_part(read('christmas.html'))
    n = len(re.findall(r'href="/?music-guides/[^"]+\.html"', m))
    check(n <= 6, f'christmas.html: {n} guide links in the body, at most six')
    check('christmas-carol-services.html' in m, 'christmas.html: disambiguation link to the church page')


def christmas_hero_offer():
    c = read('christmas.html')
    head = c.split('<div class="page-wrap hero">', 1)[1].split('<div class="hero-video">', 1)[0]
    check('class="hero-facts"' in head, 'christmas.html: facts sit between the h1 and the film')
    check('href="#enquiry" class="btn-link"' in head, 'christmas.html: primary button above the film')
    check('data-whatsapp' in head, 'christmas.html: WhatsApp button in the hero')
    for claim in ('&pound;1,150', 'two hours', 'December', 'Greater London', 'one working day'):
        check(claim in head, f'christmas.html: hero facts should mention {claim!r} (ad message match)')


# ── christmas-carol-services.html: the church carol services page ──

CHURCH_FILMS = {'SbvqWglsbMo', 'zDlSFb74p4E'}  # Once in Royal David's City, Ding Dong


def church_page():
    path = 'christmas-carol-services.html'
    g = read(path)
    check("SbvqWglsbMo" in hero(g), f"{path}: hero should be Once in Royal David's City")
    films = set(re.findall(r'data-video="([^"]+)"', g))
    check(films == CHURCH_FILMS, f'{path}: films {sorted(films)} should be {sorted(CHURCH_FILMS)}')
    videos_have_schema(g, CHURCH_FILMS, path)
    check('dGYqQf6BDAk' not in g and 'Carol of the Bells' not in g, f'{path}: no Carol of the Bells')
    m = main_part(g)
    for piece in HYMNS + ('Blue Christmas',):
        check(piece not in m, f'{path}: {piece} should not be on the page')
    check('Helen' in m and 'Laura' in m, f'{path}: Helen and Laura testimonials')
    check('&pound;250' in m, f'{path}: organist price')
    check(not re.search(r'church (hire|fee)|verger.{0,20}fee|all taxes, fees', g, re.I), f'{path}: silent on church fees')
    check('VAT' not in m, f'{path}: no VAT wording')
    check('<link rel="canonical" href="https://londonchoralservice.com/christmas-carol-services.html">' in g,
          f'{path}: canonical')
    check('href="christmas.html"' in m, f'{path}: disambiguation link to christmas.html')
    head = g.split('<div class="page-wrap hero">', 1)[1].split('<div class="hero-video">', 1)[0]
    check('class="hero-facts"' in head and 'href="#enquiry" class="btn-link"' in head,
          f'{path}: facts and primary button above the film')
    for rel in ('thank-you.html',):
        check("from === 'carol-service'" in read(rel), f'{rel}: needs copy for from=carol-service')
    llms = read('llms.txt')
    check('christmas-carol-services.html' in llms and '/carol-singers.html' not in llms, 'llms.txt: church page in, stub out')
    check('londonchoralservice.com/christmas-carol-services.html' in read('sitemap.xml'), 'sitemap.xml: church page')


def main():
    stub_preserves_query()
    stub_has_noscript_refresh()
    stub_is_noindex_canonical()
    christmas_films()
    christmas_no_hymns()
    christmas_prices()
    christmas_order()
    christmas_guides()
    christmas_hero_offer()
    form_contract('christmas.html', 'christmas', 'thank-you.html?from=christmas',
                  ('Office or staff party', 'Drinks reception', 'Hotel or venue lobby',
                   'Residents&rsquo; event', 'Market or light switch-on', 'Outdoor event', 'Other'))
    faq_unique('christmas.html')
    church_page()
    form_contract('christmas-carol-services.html', 'christmas-carol-services',
                  'thank-you.html?from=carol-service',
                  ('Church carol service', 'School or community service', 'Other'))
    faq_unique('christmas-carol-services.html')
    if failures:
        print(f'FAIL: {len(failures)} problem(s)')
        for f in failures[:60]:
            print('  -', f)
        sys.exit(1)
    print('OK: christmas pages')


if __name__ == '__main__':
    main()
