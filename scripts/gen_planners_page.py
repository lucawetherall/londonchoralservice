#!/usr/bin/env python3
"""Generates planners-and-venues.html — the supplier-record page for the trade."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_register_page as B

TITLE = 'For Wedding Planners, Venues and Estates | Alma Consort'
DESC = ('How Alma Consort works with wedding planners, venues and private offices: lead times, '
        'insurance and confidentiality, standing arrangements, and invoicing.')

FAQS = [
    ('What do you need from us, and by when?',
     'The date, the venue and the running order as soon as they exist, even in draft. Everything else can '
     'follow. Six to twelve months is the usual lead time for Europe; the United States needs considerably '
     'longer because paid performance there runs through a visa petition. If a date is closer than that, '
     'ask anyway — a free Saturday is a free Saturday.'),
    ('Do you carry insurance and provide method statements?',
     'We hold public liability insurance, and we provide risk assessments and method statements on request. '
     'Venues that need a supplier pack before they will confirm can have one; tell us what your compliance '
     'team asks for and we will send it in their format rather than ours.'),
    ('Will the consort sign a confidentiality agreement?',
     'Yes. We do not name clients, publish photographs, or release recordings from a private engagement '
     'without permission, and every singer on the engagement signs the same agreement — including a deputy '
     'brought in at short notice.'),
    ('What does the consort need from the venue?',
     'Room to stand where the guests can hear them, which in a church usually means the chancel, a gallery '
     'or the west end. No stage, no PA, no piano. For a ballroom, a terrace or a marquee, send us the '
     'dimensions and tell us whether the floor is carpeted: a soft room absorbs sound a chapel would carry, '
     'and that changes the number of singers we recommend.'),
    ('How do you invoice?',
     'In pounds sterling, euros or US dollars, to whichever entity you nominate — the couple, your agency, '
     'or the venue. Deposit and balance terms are set out in the booking agreement before anything is '
     'confirmed. Alma Consort Ltd is not registered for VAT, so no VAT is added to our invoices.'),
    ('Can we set up a standing arrangement?',
     'Yes, and it is worth doing if you expect to bring us more than one engagement. A standing arrangement '
     'means we hold your compliance paperwork on file, quote from a known baseline, and give your dates '
     'first refusal against general enquiries. Tell us about your events and we will set it up.'),
]

def jsonld():
    graph = [
        {'@type': 'Service',
         '@id': f'{B.SITE}/planners-and-venues.html#service',
         'name': 'Choral engagements for wedding planners, venues and estates',
         'serviceType': 'Choral engagements booked through planners, venues and private offices',
         'description': ('How Alma Consort works with wedding and event planners, venue and hotel event '
                         'teams, and private offices: lead times, insurance and method statements, '
                         'confidentiality, standing arrangements, and invoicing in pounds sterling, '
                         'euros or US dollars.'),
         'url': f'{B.SITE}/planners-and-venues.html',
         'provider': {'@type': 'LocalBusiness', '@id': f'{B.SITE}/#organization',
                      'name': 'The London Choral Service'},
         'audience': {'@type': 'BusinessAudience',
                      'audienceType': 'Wedding planners, event planners, venue and hotel event teams, private offices'}},
        {'@type': 'BreadcrumbList',
         '@id': f'{B.SITE}/planners-and-venues.html#breadcrumb',
         'itemListElement': [
             {'@type': 'ListItem', 'position': 1, 'name': 'Private Events',
              'item': f'{B.SITE}/private-events.html'},
             {'@type': 'ListItem', 'position': 2, 'name': 'Planners and venues',
              'item': f'{B.SITE}/planners-and-venues.html'}]},
        {'@type': 'FAQPage',
         '@id': f'{B.SITE}/planners-and-venues.html#faq',
         'mainEntity': [{'@type': 'Question', 'name': q.replace('&rsquo;','’'),
                         'acceptedAnswer': {'@type': 'Answer',
                                            'text': a.replace('&rsquo;','’').replace('&mdash;','—')}}
                        for q, a in FAQS]},
    ]
    return '  ' + json.dumps({'@context': 'https://schema.org', '@graph': graph},
                             indent=2, ensure_ascii=False).replace('\n', '\n  ')

faq_html = '\n\n'.join(f'          <h3>{q}</h3>\n          <p>{a}</p>' for q, a in FAQS)

BODY = f'''
    <!-- Hero -->
    <section class="pe-section pe-section--light pe-hero">
      <div class="pe-hero__inner">
        <p class="pe-eyebrow">Alma Consort &middot; London</p>
        <h1>A supplier your compliance team will not have to chase.</h1>
        <div class="pe-hairline--candle" aria-hidden="true"></div>
        <p class="pe-hero__sub">How we work with wedding and event planners, venue and hotel event teams,
          and private offices &mdash; in the United Kingdom and at destinations worldwide.</p>
        <p class="pe-hero__cta"><a class="pe-btn" href="#enquire">Tell us about your events</a></p>
      </div>
    </section>

    <!-- Who we are -->
    <section class="pe-section pe-section--mid">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">The ensemble</p>
        <div class="pe-body" data-fade>
          <h2>What you are booking</h2>
          <p>Alma Consort is a professional ensemble of eight to twenty-four consort singers based in
            London; The London Choral Service is its booking office. The same singers perform every
            engagement, and Luca Wetherall, Tutor in Music at the University of Oxford, auditions every
            one of them and directs the consort himself. The singers are prize-winning graduates of the
            Royal Academy of Music, the Royal College of Music, the Guildhall School of Music &amp; Drama,
            and the Universities of Oxford and Cambridge.</p>
          <p>For a planner the practical point is narrower: this is one supplier, one contact, one invoice,
            and a group that arrives the day before and rehearses in the room. You are not assembling
            singers from a directory and hoping they have met.</p>
        </div>
      </div>
    </section>

    <!-- The working relationship -->
    <section class="pe-section pe-section--light">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Working together</p>
        <div class="pe-body" data-fade>
          <h2>How a booking runs</h2>
          <ol class="pe-process" role="list">
            <li>
              <span class="n" aria-hidden="true">1</span>
              <h3>Date and outline</h3>
              <p>You send the date, the venue and whatever the running order looks like so far. We confirm
                availability, usually the same day.</p>
            </li>
            <li>
              <span class="n" aria-hidden="true">2</span>
              <h3>Quote and paperwork</h3>
              <p>A single quote covering fees, travel and accommodation, with the booking agreement
                alongside it. Insurance certificates, risk assessments and method statements come with it
                rather than after three requests.</p>
            </li>
            <li>
              <span class="n" aria-hidden="true">3</span>
              <h3>Programme</h3>
              <p>Luca proposes music and a running order and revises it with you or directly with the
                couple, whichever suits how you work. We will talk to the celebrant and the organist
                ourselves if that saves you a thread.</p>
            </li>
            <li>
              <span class="n" aria-hidden="true">4</span>
              <h3>On the day</h3>
              <p>The consort arrives the day before for engagements abroad, rehearses in the building,
                and reports to whoever you nominate on site. Nobody needs to find us a green room or a
                power socket.</p>
            </li>
          </ol>
        </div>
      </div>
    </section>

    <!-- For venues specifically -->
    <section class="pe-section pe-section--mid">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Venues</p>
        <div class="pe-body" data-fade>
          <h2>For venue and estate teams</h2>
          <p>A consort makes fewer demands on a building than almost any other kind of live music.
            Unaccompanied singing needs no stage, no power, no PA and no piano, and it leaves no rig to
            strike afterwards. In a stone building it needs no amplification at all.</p>
          <p>What matters instead is where the singers stand and what the room does to the sound. A chancel,
            a gallery or the west end of a church all work. A ballroom with a carpeted floor and soft
            furnishings absorbs sound a chapel would carry, and an outdoor terrace gives nothing back at
            all, so both usually want more voices than the guest count alone would suggest. Send us
            dimensions and a photograph and we will tell you what we would recommend before you quote it
            to a client.</p>
          <p>If you keep a preferred-supplier list, we are glad to go on it and to hold whatever paperwork
            your compliance process needs on file.</p>
        </div>
      </div>
    </section>

    <!-- Destinations pointer -->
    <section class="pe-section pe-section--light">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Abroad</p>
        <div class="pe-body" data-fade>
          <h2>Engagements abroad</h2>
          <p>We travel from London across Europe and the Mediterranean, to the Caribbean and the Americas,
            and to the Indian Ocean, Southeast Asia and South Africa. The variables a planner will care
            about &mdash; lead times, work permits for paid performers, what the local rite expects to hear
            sung, and what a room with no organ does to the voicing &mdash; differ by country, and our
            <a href="/destinations/">country guides</a> set them out one at a time.</p>
          <p>The one that catches people out is the United States, where paid performance needs a visa
            petition rather than a flight booking, on a lead time measured in months. If a client is
            considering a wedding there, raise it early and we will tell you what the calendar allows.</p>
        </div>
      </div>
    </section>

    <!-- Questions -->
    <section class="pe-section pe-section--mid">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Questions</p>
        <div class="pe-body" data-fade>
          <h2>Trade questions</h2>

{faq_html}
        </div>
      </div>
    </section>
'''

html = B.page(
    title=TITLE, description=DESC, path='planners-and-venues.html', jsonld=jsonld(),
    crumbs=[('Private Events', '/private-events.html'), ('Planners and venues', None)],
    body=BODY, source_page='planners-and-venues.html',
    subject='Planner or venue enquiry — Alma Consort / LCS',
    enquiring_as_default='Planner or agency',
    form_intro='Tell us about the engagement, or about the events you handle in general if you are '
               'looking to set up a standing arrangement.')

open('planners-and-venues.html', 'w', encoding='utf-8').write(html)
print(f'planners-and-venues.html written — meta description {len(DESC)} chars')
