#!/usr/bin/env python3
"""ONE-SHOT. Already run; do NOT run again.

This built music-guides/destination-wedding-choir.html once, from a cloned
exemplar. The page has been hand-edited many times since (the weekend section,
the ceremony-type reframing, the sizing rules, a stop-slop pass), and none of
that is reflected here. Re-running this script would overwrite all of it.

Kept only as a record of how the page was first assembled. Edit the built page
directly; the destination country pages are the ones with live generators.
"""
import sys
if __name__ == '__main__':
    sys.exit("gen_destination_guide.py is one-shot and already run — see the "
             "module docstring. Edit music-guides/destination-wedding-choir.html directly.")

import re, json, pathlib

P = pathlib.Path('music-guides/destination-wedding-choir.html')
s = P.read_text(encoding='utf-8')

SITE = 'https://londonchoralservice.com'
URL = f'{SITE}/music-guides/destination-wedding-choir.html'
OLD_URL = f'{SITE}/music-guides/wedding-pop-songs-choir.html'
TITLE = 'Hiring a UK Choir for a Destination Wedding'
DESC = ('What it takes to bring a British choir to a wedding abroad: lead times, work permits, '
        'costs, and what changes when there is no organ and no stone building.')
assert 141 <= len(DESC) <= 161, len(DESC)

# ---------- head ----------
s = s.replace('<title>Pop Songs for a Wedding Choir to Sing</title>', f'<title>{TITLE}</title>')
s = s.replace('Pop songs arranged for four-part voices for a church wedding. Modern love ballads, classic standards, and practical advice on bespoke choral arrangements.', DESC)
s = s.replace('Pop Songs for a Wedding Choir to Sing', TITLE)
s = s.replace(OLD_URL, URL)

# ---------- JSON-LD ----------
old_ld = re.search(r'  <script type="application/ld\+json">\n(.*?)\n  </script>', s, re.S).group(0)
FAQS = [
    ("Can you hire a UK choir for a wedding abroad?",
     "Yes. A consort travels the way any other supplier does: the singers rehearse in London, fly out "
     "together, arrive the day before and rehearse in the building. The complications are administrative "
     "rather than musical — chiefly whether the country requires a permit before a British musician may "
     "be paid to perform, and how far ahead that has to be arranged."),
    ("How much does it cost to fly a choir to your wedding?",
     "Three things move the number: how many singers, how far they travel, and how many nights they stay. "
     "Published UK rates run from £250 for a soloist to £2,000 for a choir of eight and £3,000 for twelve "
     "voices. An engagement abroad adds return flights and rooms for every singer, plus the night before "
     "for rehearsal, so the travel component often exceeds the music fee on long-haul dates."),
    ("How far in advance should we book?",
     "Six to twelve months for Europe, and nearer twelve than six in practice: booking flights and "
     "accommodation for twelve to twenty-four people takes longer than clearing their diaries. The United "
     "States needs considerably longer, because paid performance there runs through a visa petition with a "
     "lead time measured in months rather than weeks."),
    ("Do British musicians need a visa or work permit to perform abroad?",
     "It depends on the country, and the honest answer is that this is the question most couples have not "
     "thought about. Inside the Schengen area the issues are social-security paperwork and the "
     "ninety-days-in-any-one-hundred-and-eighty limit. The United States requires a petition-based "
     "performance visa. Several long-haul destinations have their own rules for paid performers. Ask before "
     "you fix a date, not after."),
    ("What if there is no church, no organ and no stage?",
     "That describes most destination weddings, and it suits a consort better than it suits almost any "
     "other kind of live music. Unaccompanied singing needs no instrument, no power and no amplification. "
     "What changes is the number of voices: an open terrace or a beach gives nothing back acoustically, so "
     "it wants more singers than a stone chapel with the same number of guests."),
]
new_graph = {
    '@context': 'https://schema.org',
    '@graph': [
        {'@type': 'Article', 'headline': 'Hiring a UK choir for a destination wedding', 'url': URL,
         'inLanguage': 'en-GB', 'datePublished': '2026-08-29', 'dateModified': '2026-08-29',
         'description': DESC,
         'author': [
             {'@type': 'Person', 'name': 'Luca Wetherall', 'jobTitle': 'Artistic Director',
              'url': f'{SITE}/about.html'},
             {'@type': 'Organization', 'name': 'The London Choral Service',
              'alternateName': 'London Choral Service', 'url': SITE}],
         'image': {'@type': 'ImageObject', 'url': f'{SITE}/assets/og-weddings.png',
                   'width': 1200, 'height': 630},
         'wordCount': 1750,
         'speakable': {'@type': 'SpeakableSpecification',
                       'cssSelector': ['.lede', '.guide-body p:first-of-type']},
         'publisher': {'@type': 'Organization', 'name': 'The London Choral Service',
                       'alternateName': 'London Choral Service', 'url': SITE,
                       'logo': {'@type': 'ImageObject', 'url': f'{SITE}/assets/og-image.png'}},
         'mainEntityOfPage': {'@type': 'WebPage', '@id': URL}},
        {'@type': 'LocalBusiness', '@id': f'{SITE}/#organization',
         'name': 'The London Choral Service'},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE},
            {'@type': 'ListItem', 'position': 2, 'name': 'Music Guides',
             'item': f'{SITE}/music-guides/'},
            {'@type': 'ListItem', 'position': 3, 'name': TITLE, 'item': URL}]},
        {'@type': 'FAQPage', 'mainEntity': [
            {'@type': 'Question', 'name': q,
             'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FAQS]},
    ]
}
new_ld = ('  <script type="application/ld+json">\n  '
          + json.dumps(new_graph, indent=2, ensure_ascii=False).replace('\n', '\n  ')
          + '\n  </script>')
s = s.replace(old_ld, new_ld)

# ---------- body ----------
start = s.index('  <main id="main">')
end = s.index('    <!-- @include-start partials/footer.html -->')
faq_html = '\n\n'.join(
    f'          <h3>{q}</h3>\n          <p>{a.replace("—", "&thinsp;&mdash;&thinsp;").replace("£", "&pound;")}</p>'
    for q, a in FAQS)

BODY = '''  <main id="main">
    <article>

      <section class="section" style="padding-block-end: var(--space-2xl)">
        <div class="prose">
          <nav class="breadcrumb" aria-label="Breadcrumb">
            <ol>
              <li><a href="../index.html">Home</a></li>
              <li><a href="./">Music Guides</a></li>
              <li>Hiring a UK Choir for a Destination Wedding</li>
            </ol>
          </nav>
          <h1>Hiring a UK choir for a destination wedding</h1>
          <p class="guide-meta">By Luca Wetherall, Artistic Director &amp; Tutor in Music, University of Oxford</p>
          <p class="guide-meta">Published 29 August 2026</p>
          <hr class="rule">
        </div>
      </section>

      <section class="section" style="padding-block-start: var(--space-2xl)">
        <div class="prose">
          <p class="lede">Couples who have heard a choir sing in an English church often want that sound at
            a wedding in Tuscany, the Algarve or Barbados, and assume it is either impossible or
            extravagant beyond reason. It is neither, but it is a different kind of booking from hiring
            singers at home, and the differences are worth understanding before you fall in love with the
            idea. This guide covers what determines the cost, how far ahead you need to commit,
            the work-permit question almost nobody raises until it is late, and what changes musically when
            there is no organ and no stone.</p>
        </div>
      </section>

      <section class="section">
        <div class="prose">
          <h2>What you are paying for</h2>
          <p>Three things move the figure, and only one of them is the music: the number of singers, the
            distance they travel, and the nights they stay.</p>
          <p>The fee for the singing is the part you can look up. Our rates are published on the
            <a href="../pricing.html">pricing page</a> and start at &pound;250 for a soloist, &pound;1,150
            for a small choir of four, and &pound;2,000 for a choir of eight. What a wedding abroad adds
            is return flights and accommodation for every singer who travels, and a night before the
            wedding, because a consort that has not sung in the building is guessing at it.</p>
          <p>The consequence is uncomfortable but easy to state. For a wedding in Italy or Portugal, travel
            is a real but manageable addition to the music budget. For the Maldives or Bali, the flights
            alone will exceed what many weddings set aside for music altogether. That does not make it
            impossible &thinsp;&mdash;&thinsp; we have singers who have flown a great deal further for less
            interesting reasons &thinsp;&mdash;&thinsp; but it does mean the conversation should start with
            the number rather than end with it.</p>
          <p>One thing that does <em>not</em> change is the size of the group you need. A church that
            wanted eight voices in Hampshire wants eight voices in Puglia. Nobody saves money by shipping
            a quartet to do a choir&rsquo;s work.</p>
        </div>
      </section>

      <section class="section">
        <div class="prose">
          <h2>Lead times, and the one that catches people out</h2>
          <p>Six to twelve months is the usual window for Europe, and in practice you want the longer end.
            Clearing twelve professional diaries for a Saturday is the easy half; booking flights and rooms
            for twelve people on a summer weekend in Amalfi is the half that fails if you leave it.</p>
          <p>Then there is the United States, which behaves differently from everywhere else. Performing
            for a fee in the US requires a petition-based performance visa for each musician, and the
            timeline for that is measured in months. A couple who decide in March on a September wedding in
            New York have a music problem they do not yet know about. If you are considering the States,
            raise it at the first conversation, and treat the visa calendar rather than the venue calendar
            as the binding constraint.</p>
          <p>Elsewhere the paperwork varies. Inside the Schengen area the questions are social-security
            certificates and the ninety-days-in-any-one-hundred-and-eighty rule. Several long-haul
            destinations have their own requirements for paid performers. None of this is insurmountable;
            all of it is worse when discovered late.</p>
        </div>
      </section>

      <section class="section">
        <div class="prose">
          <h2>Which parts get sung, and in what language</h2>
          <p>The single biggest musical variable abroad is the rite. A Catholic nuptial Mass in Italy has a
            sung ordinary, a psalm and acclamations, and a shape a choir can be built into. A civil ceremony
            at a French ch&acirc;teau has no liturgy at all, so the music sits in the gaps: the entrance, the
            signing, the exit, and whatever the couple wants during the vows. A Church of Ireland or Anglican
            service abroad will feel familiar to anyone who has planned a wedding at home. A beach ceremony in
            the Indian Ocean is closer to a concert with a wedding in the middle of it.</p>
          <p>Language follows from the rite. We sing the Latin ordinary as standard, and in Italian, French,
            Spanish, Portuguese and German where the ceremony calls for it. Where the congregation is split
            between two languages, the usual solution is to sing the ordinary in Latin, which belongs to
            neither family and is recognisable to both, and to keep the congregational hymns in whichever
            language most of the guests will sing.</p>
          <p>For the repertoire itself, our guides to
            <a href="wedding-choral-repertoire.html">choral pieces for a wedding</a> and
            <a href="choosing-wedding-hymns.html">choosing wedding hymns</a> apply the same abroad as at
            home; what changes is where they sit in the service.</p>
        </div>
      </section>

      <section class="section">
        <div class="prose">
          <h2>No organ, no stage, no stone</h2>
          <p>Most destination weddings happen somewhere that was never built for music: a terrace, a
            cloister, a lawn, a beach. This suits an unaccompanied consort better than it suits a string
            quartet or a band, because there is nothing to plug in, nothing to tune, and nothing to strike
            afterwards.</p>
          <p>What it does change is the number of voices. A stone church returns sound to the room and
            flatters a small group; an outdoor ceremony returns nothing at all, and a carpeted ballroom
            actively absorbs it. As a rule of thumb, a space with no reverberation wants more singers than
            the guest count alone would suggest &thinsp;&mdash;&thinsp; twelve where a chapel would have
            been happy with eight. Heat matters too: a group singing at four in the afternoon in the
            Caribbean needs shade and water in a way it does not in Winchester, and that belongs in the
            running order rather than being discovered on the day.</p>
        </div>
      </section>

      <section class="section">
        <div class="prose">
          <h2>Questions couples ask</h2>

''' + faq_html + '''
        </div>
      </section>

      <section class="section">
        <div class="prose">
          <h2>If you are marrying abroad</h2>
          <p>Our performing ensemble, Alma Consort, takes the engagements that travel. There are
            <a href="../destinations/">country guides</a> covering the rite, the sung language, the
            buildings, and the travel and permit position for each of the places we are asked about most,
            and a general page on <a href="../private-events.html">private and international
            engagements</a>. If you are working with a planner, our
            <a href="../planners-and-venues.html">page for planners and venues</a> has the paperwork and
            lead-time detail they will want.</p>
          <p>Tell us the date and the venue as early as you have them, even if the music is nowhere near
            settled. Early is what makes the rest of it easy.</p>
          <p><a href="../private-events.html" class="btn-link">Tell us about your wedding abroad</a></p>
        </div>
      </section>

    </article>

    <section class="related-guides">
      <h2>Related</h2>
      <p><strong>If you&rsquo;re planning a wedding</strong> &mdash; see our <a href="../weddings.html">Weddings</a> page, or the <a href="../destinations/">destination guides</a> if you are marrying abroad.</p>
      <ul>
        <li><a href="wedding-music-costs.html">What Wedding Music Costs</a></li>
        <li><a href="wedding-choral-repertoire.html">Choral Pieces for a Wedding</a></li>
        <li><a href="wedding-ceremony-music.html">Wedding Ceremony Music</a></li>
      </ul>
    </section>

  </main>

'''
s = s[:start] + BODY + s[end:]
P.write_text(s, encoding='utf-8')
print(f'guide written — meta description {len(DESC)} chars')
