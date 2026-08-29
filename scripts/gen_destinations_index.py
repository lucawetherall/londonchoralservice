#!/usr/bin/env python3
"""Generates destinations/index.html — the hub for the country pages."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_register_page as B
import destinations_data as D

TITLE = 'Destination Weddings &mdash; A British Choir Abroad | Alma Consort'
DESC = ('Alma Consort travels from London to sing weddings abroad. Country guides to the rite, '
        'the sung language, and the travel and permit position for a British choir.')

CHECKED = '2026-08-29'

def groups_html():
    out = []
    for group, countries in D.GROUPS:
        cards = []
        for slug, name, regions, _ in countries:
            sub = D.regions_phrase(regions) or 'Castles, country houses and parish churches'
            cards.append(
                f'            <li><a href="/destinations/{slug}.html">'
                f'<span class="n">{name}</span><span class="r">{sub}</span></a></li>')
        out.append(
            f'          <div class="pe-group">\n'
            f'            <h3>{group}</h3>\n'
            f'            <ul class="pe-dests" role="list">\n'
            + '\n'.join(cards) + '\n'
            f'            </ul>\n'
            f'          </div>')
    return '\n'.join(out)

FAQS = [
    ('Can a British choir sing at a wedding abroad?',
     'Yes. The practical questions are the same everywhere: whether the country requires a permit for '
     'paid performance, what kind of ceremony you are having, and what the building does to the sound. '
     'The answers differ enough by country that we have written them up one country at a time rather '
     'than offering a single reassurance.'),
    ('Can you sing more than once across the weekend?',
     'Yes, and it is the thing we would most encourage you to consider. The expensive part of bringing a '
     'consort abroad is the fares and the rooms, and those are spent whether we sing once or four times. '
     'A welcome dinner, the ceremony, the drinks afterwards and a late unaccompanied set in a stone room '
     'cost far less together than they look, and they give your guests something at each stage rather '
     'than twenty minutes in the middle of a Saturday. It works at any size of wedding: a small party '
     'close in wants fewer voices, not fewer moments.'),
    ('We live in the country rather than flying out. Does that change anything?',
     'Only in your favour. Everything on these guides applies, and the planning is simpler because you '
     'already know the venue, the celebrant and the season. We travel from London either way; what '
     'changes is that you will have far better local knowledge than most couples we work with, and we '
     'will lean on it.'),
    ('Do we have to have a religious ceremony?',
     'No, and most of the couples we sing for abroad do not. Humanist, non-denominational and '
     'celebrant-led ceremonies are the most common thing we are asked about, and without a liturgy to '
     'work around, the music is entirely yours to place. Anglican and Catholic services are available in '
     'more of these countries than couples expect, including through English-speaking chaplaincies '
     'across Europe. Whichever you choose, the country you have picked rarely restricts it.'),
    ('How far ahead should we book a wedding abroad?',
     'Six to twelve months for Europe, and the longer end of that in practice: booking flights and rooms '
     'for twelve to twenty-four people takes longer than clearing the singers&rsquo; diaries. The United States '
     'is the exception and needs far longer, because paid performance there runs through a visa petition '
     'rather than a boarding pass. Tell us the date as soon as it is fixed, even if the music is nowhere near settled.'),
    ('What does it cost to bring a choir abroad?',
     'Three things move the figure: the number of singers, the distance they travel, and the nights they '
     'stay. A twelve-voice consort at a Tuscan church for one night sits at one end; a long-haul engagement '
     'with two nights and connecting flights sits well beyond it. We quote for the whole engagement before '
     'you commit, and we invoice in pounds sterling, euros or US dollars.'),
    ('Do you sing in languages other than English?',
     'We sing the Latin ordinary as a matter of course, and we sing in Italian, French, Spanish, Portuguese '
     'and German where the ceremony calls for it. Where a congregation is split between languages we usually '
     'set the sung ordinary in Latin, which belongs to neither side and is familiar to both, and keep the '
     'hymns in the language most of the guests will sing.'),
    ('What if there is no church and no organ?',
     'Most destination ceremonies happen outdoors or in a room with no organ, and the consort is built for '
     'exactly that: unaccompanied singing needs no instrument, no stage and no amplification. What it does '
     'need is the right number of voices for the space, which is why an open terrace usually wants more '
     'singers than a stone chapel does. The room decides the number, not the size of the guest list.'),
]

def jsonld():
    graph = [
        {
            '@type': 'Service',
            '@id': f'{B.SITE}/destinations/#service',
            'name': 'Destination wedding choir and consort singers',
            'serviceType': 'International and destination choral engagements',
            'description': ('Alma Consort, a professional consort of eight to twenty-four voices based in '
                            'London, travelling to sing weddings and ceremonies at destinations worldwide.'),
            'url': f'{B.SITE}/destinations/',
            'provider': {'@type': 'LocalBusiness', '@id': f'{B.SITE}/#organization',
                         'name': 'The London Choral Service'},
            'areaServed': [{'@type': 'Country', 'name': D.SCHEMA_NAME.get(n, n)}
                           for _, n, _, _ in D.ALL if D.SCHEMA_NAME.get(n, n) != 'United Kingdom']
                          + [{'@type': 'Country', 'name': 'United Kingdom'}],
        },
        {
            '@type': 'BreadcrumbList',
            '@id': f'{B.SITE}/destinations/#breadcrumb',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Private Events',
                 'item': f'{B.SITE}/private-events.html'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Destinations',
                 'item': f'{B.SITE}/destinations/'},
            ],
        },
        {
            '@type': 'FAQPage',
            '@id': f'{B.SITE}/destinations/#faq',
            'mainEntity': [
                {'@type': 'Question', 'name': q.replace('&rsquo;', '’'),
                 'acceptedAnswer': {'@type': 'Answer',
                                    'text': a.replace('&rsquo;', '’').replace('&mdash;', '—')}}
                for q, a in FAQS
            ],
        },
    ]
    return '  ' + json.dumps({'@context': 'https://schema.org', '@graph': graph},
                             indent=2, ensure_ascii=False).replace('\n', '\n  ')

faq_html = '\n\n'.join(
    f'          <h3>{q}</h3>\n          <p>{a}</p>' for q, a in FAQS)

BODY = f'''
    <!-- Hero -->
    <section class="pe-section pe-section--light pe-hero">
      <div class="pe-hero__inner">
        <p class="pe-eyebrow">Alma Consort &middot; London</p>
        <h1>English choral singing, wherever you are marrying.</h1>
        <div class="pe-hairline--candle" aria-hidden="true"></div>
        <p class="pe-hero__sub">Your guests have travelled to be there, and they will be together for
          days. A consort of eight to twenty-four voices travels too, and sings across the whole weekend
          &mdash; the welcome dinner, the ceremony, the reception.</p>
        <p class="pe-hero__cta"><a class="pe-btn" href="#enquire">Enquire about your wedding</a></p>
      </div>
    </section>

    <!-- What travelling actually involves -->
    <section class="pe-section pe-section--mid">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Travelling</p>
        <div class="pe-body" data-fade>
          <h2>A wedding that lasts a weekend</h2>
          <p>A destination wedding is not a ceremony with a holiday attached. You have moved your family
            and your closest friends to one place, at real expense to them and to you, and they will be
            together for three or four days. Whether that is thirty people or two hundred, it is the
            thing worth designing around, and it changes what live music can do for you.</p>
          <p>A consort that has flown out for the ceremony is already paid for in the part that costs
            most: the fares and the rooms. Singing again at the welcome dinner on the Friday, or over
            drinks after the ceremony, or unaccompanied in a stone hall once the meal is over, costs a
            fraction of what the first appearance did. Guests who have travelled to be there hear three
            different things instead of one, and the two evenings either side of the wedding day stop
            being the parts nobody planned.</p>
          <p>Where each of those moments works best depends on the country, and the guides below say so
            one at a time &mdash; a Portuguese quinta keeps everybody on one estate, a Dalmatian old town
            has your guests walking between stone rooms, and a Maldivian resort island has nobody going
            anywhere at all.</p>

          <h3>Whatever kind of ceremony you are having</h3>
          <p>Most couples we sing for abroad are British, Irish, American or Australian, marrying in a
            country they do not live in and choosing the shape of the day themselves. Your ceremony might
            be humanist, non-denominational, celebrant-led, Anglican, Catholic or interfaith, and in most
            of these countries all of those are open to you &mdash; the local majority religion decides
            far less than couples expect. What the country changes is which routes are legally
            recognised, whether there is an English-speaking chaplaincy, and what buildings you can get
            into. Each guide sets that out.</p>
          <p>If you live in the country rather than travelling to it, everything here applies just as
            well; we sing for couples based abroad as readily as for those flying their guests out.</p>

          <h3>What travels with us</h3>
          <p>The singing is the part that does not change. The consort rehearses in London, flies out
            together, arrives the day before, and rehearses in the building where it will sing. Everything
            around that changes by country, and the differences are large enough to be worth writing down
            properly: whether the ceremony has a sung rite at all, which language its congregation expects
            to hear, whether a permit is needed before a British musician may be paid to perform, and what
            a room with no stone and no organ does to a twelve-voice sound.</p>
          <p>We arrange the singers&rsquo; travel and accommodation ourselves and liaise with your venue,
            planner and celebrant. You are booking the music, not the logistics behind it.</p>
        </div>
      </div>
    </section>

    <!-- Country guides -->
    <section class="pe-section pe-section--light">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Where</p>
        <div class="pe-body" data-fade>
          <h2>Country guides</h2>
          <p>Each guide sets out the rite and the running order, the language the ceremony is sung in,
            the buildings and what they do to the voicing, and the travel and permit position for a group
            of this size.</p>
{groups_html()}
          <p style="margin-top:2rem">Marrying somewhere not listed? Ask us. The calendar and the flight
            schedule decide, and the answer is more often yes than not.</p>
        </div>
      </div>
    </section>

    <!-- Cost drivers -->
    <section class="pe-section pe-section--mid">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Cost</p>
        <div class="pe-body" data-fade>
          <h2>What moves the cost</h2>
          <p>Three things: the number of singers, the distance they travel, and the nights they stay.
            A consort abroad carries return flights and rooms for everyone who sings, and the singers
            arrive a day early to rehearse in the space, so a wedding in Puglia and a wedding in the
            Maldives are different propositions before anyone has discussed music.</p>
          <p>It is worth being plain about what that means. Bringing a British consort to a beach ceremony
            in Southeast Asia costs more in travel alone than many weddings budget for music altogether.
            If the figure is likely to be uncomfortable, better that you know it now than after three
            emails. Our rates for engagements in the United Kingdom are published on the
            <a href="/pricing.html">pricing page</a>; an engagement abroad is quoted whole, before you
            commit to anything.</p>
        </div>
      </div>
    </section>

    <!-- Permits -->
    <section class="pe-section pe-section--light">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Permits</p>
        <div class="pe-body" data-fade>
          <h2>Permits and paperwork</h2>
          <p>A group of British musicians travelling to perform for a fee is not the same as a group of
            British tourists, and the rules differ sharply by country. Within the Schengen area the
            questions are social-security certificates and the ninety-days-in-any-one-hundred-and-eighty
            limit. The United States is the difficult one: paid performance there runs through a visa
            petition with a lead time measured in months, which changes when you need to book rather than
            whether you can.</p>
          <p>Each country guide states the position as we understand it, with the date we last checked.
            Where we are not certain, the guide says so and asks you to check with us rather than guessing
            on your behalf.</p>
          <p class="pe-checked">Permit and travel information across these guides last checked {CHECKED}.
            Rules change; confirm current requirements with us before you fix a date.</p>
        </div>
      </div>
    </section>

    <!-- Questions -->
    <section class="pe-section pe-section--mid">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Questions</p>
        <div class="pe-body" data-fade>
          <h2>Destination wedding questions</h2>

{faq_html}
        </div>
      </div>
    </section>
'''

html = B.page(
    title=TITLE, description=DESC, path='destinations/', jsonld=jsonld(),
    crumbs=[('Private Events', '/private-events.html'), ('Destinations', None)],
    body=BODY, source_page='destinations/',
    subject='Destination wedding enquiry — Alma Consort / LCS',
    form_intro='Tell us where you are marrying and when. If we have the date free, Luca Wetherall '
               'will come back with what the music could be and what the whole engagement would cost.')

os.makedirs('destinations', exist_ok=True)
open('destinations/index.html', 'w', encoding='utf-8').write(html)
print(f'destinations/index.html written — meta description {len(DESC)} chars')
