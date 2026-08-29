#!/usr/bin/env python3
"""Generates destinations/<country>.html pages.

Content per country is authored here, not templated: the doorway-page ship gate
requires each page to answer country-specific questions rather than restate a
shared outline with different nouns. The scaffold (head, header, form, scripts)
comes from build_register_page; everything below `COUNTRIES` is prose.

Legal and permit statements are written as orientation, not advice, and every
page carries a visible checked date. Where the position depends on the venue,
the diocese or the celebrant, the page says so rather than guessing.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_register_page as B
import destinations_data as D
from ceremony_sections import CEREMONY
from weekend_sections import WEEKEND

CHECKED = '29 August 2026'


def jsonld(slug, name, title, desc, faqs):
    url = f'{B.SITE}/destinations/{slug}.html'
    schema_country = D.SCHEMA_NAME.get(name, name)
    graph = [
        {'@type': 'Service', '@id': f'{url}#service',
         'name': f'Wedding choir and consort singers in {name}',
         'serviceType': 'Destination wedding choral engagements',
         'description': desc, 'url': url,
         'provider': {'@type': 'LocalBusiness', '@id': f'{B.SITE}/#organization',
                      'name': 'The London Choral Service'},
         'areaServed': {'@type': 'Country', 'name': schema_country}},
        {'@type': 'BreadcrumbList', '@id': f'{url}#breadcrumb', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Private Events',
             'item': f'{B.SITE}/private-events.html'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Destinations',
             'item': f'{B.SITE}/destinations/'},
            {'@type': 'ListItem', 'position': 3, 'name': name, 'item': url}]},
        {'@type': 'FAQPage', '@id': f'{url}#faq', 'mainEntity': [
            {'@type': 'Question', 'name': q.replace('&rsquo;', '’'),
             'acceptedAnswer': {'@type': 'Answer',
                                'text': a.replace('&rsquo;', '’').replace('&mdash;', '—')
                                         .replace('&thinsp;', '').replace('&pound;', '£')
                                         .replace('&eacute;', 'é').replace('&agrave;', 'à')
                                         .replace('&acirc;', 'â').replace('&egrave;', 'è')}}
            for q, a in faqs]},
    ]
    return '  ' + json.dumps({'@context': 'https://schema.org', '@graph': graph},
                             indent=2, ensure_ascii=False).replace('\n', '\n  ')


def build(slug, name, title, desc, hero_h1, hero_sub, sections, regions, faqs,
          nav_prev=None, nav_next=None):
    """sections: list of (rail_label, heading, [paragraph_html, ...])

    The 'what kind of ceremony are you having?' section is prepended for every
    country: the reader is an English-speaking couple travelling out and choosing
    their own form of service, not a local having the local rite.
    """
    # Ceremony framing first (the reader chooses the service, not the country),
    # then the weekend: the primary buyer is having a destination wedding, so the
    # marginal cost of singing more than once is the strongest argument we have.
    sections = [CEREMONY[slug], WEEKEND[slug]] + list(sections)
    body = f'''
    <section class="pe-section pe-section--light pe-hero">
      <div class="pe-hero__inner">
        <p class="pe-eyebrow">Alma Consort &middot; Destinations</p>
        <h1>{hero_h1}</h1>
        <div class="pe-hairline--candle" aria-hidden="true"></div>
        <p class="pe-hero__sub">{hero_sub}</p>
        <p class="pe-hero__cta"><a class="pe-btn" href="#enquire">Enquire about your wedding</a></p>
      </div>
    </section>
'''
    shade = ['mid', 'light']
    i = 0
    for label, heading, paras in sections:
        para_html = '\n          '.join(f'<p>{p}</p>' for p in paras)
        body += f'''
    <section class="pe-section pe-section--{shade[i % 2]}">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">{label}</p>
        <div class="pe-body" data-fade>
          <h2>{heading}</h2>
          {para_html}
        </div>
      </div>
    </section>
'''
        i += 1

    if regions:
        region_html = ''
        for rname, rid, rparas in regions:
            ps = '\n          '.join(f'<p>{p}</p>' for p in rparas)
            region_html += f'''
          <div class="pe-region" id="{rid}">
            <h3>{rname}</h3>
          {ps}
          </div>
'''
        body += f'''
    <section class="pe-section pe-section--{shade[i % 2]}">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Where</p>
        <div class="pe-body" data-fade>
          <h2>Where in {name}</h2>
{region_html}
        </div>
      </div>
    </section>
'''
        i += 1

    faq_html = '\n\n'.join(f'          <h3>{q}</h3>\n          <p>{a}</p>' for q, a in faqs)
    body += f'''
    <section class="pe-section pe-section--{shade[i % 2]}">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Questions</p>
        <div class="pe-body" data-fade>
          <h2>Questions about singing in {name}</h2>

{faq_html}
          <p class="pe-checked">Travel and permit information on this page last checked {CHECKED}.
            Requirements change and vary by venue, diocese and celebrant; confirm the current position
            with us before you fix a date. Other <a href="/destinations/">country guides</a>.</p>
        </div>
      </div>
    </section>
'''
    html = B.page(
        title=title, description=desc, path=f'destinations/{slug}.html',
        jsonld=jsonld(slug, name, title, desc, faqs),
        crumbs=[('Private Events', '/private-events.html'),
                ('Destinations', '/destinations/'), (name, None)],
        body=body, source_page=f'destinations/{slug}.html',
        subject=f'{name} wedding enquiry — Alma Consort / LCS',
        form_intro=f'Tell us where in {name} you are marrying and when. If the date is free, Luca '
                   f'Wetherall will come back with what the music could be and what the whole '
                   f'engagement would cost, travel included.')
    open(f'destinations/{slug}.html', 'w', encoding='utf-8').write(html)
    return len(desc)
