#!/usr/bin/env python3
"""Adds one destination-wedding cross-link sentence to each weddings-category guide.

The set is defined by music-guides/index.html's data-category="weddings" section,
not by filename — jerusalem.html belongs to it and a keyword search would miss it.
Each sentence is written for the guide it sits in: eighteen identical sentences
would read as boilerplate to a human and as a template to a crawler.
"""
import pathlib, re, sys

# slug -> the sentence, reached from that guide's own subject.
SENTENCES = {
'anima-christi-catholic-wedding':
  'A nuptial Mass abroad keeps this repertoire intact&thinsp;&mdash;&thinsp;the rite travels even when you do. '
  'See our <a href="../destinations/">country guides</a> for how the Mass is sung in Italy, Spain and Portugal.',
'be-thou-my-vision-wedding-hymn':
  'An Irish hymn is an obvious choice for an Irish wedding, and we sing at them; our '
  '<a href="../destinations/">destination guides</a> cover Ireland alongside the rest of the places we travel to.',
'best-wedding-choirs-london':
  'London choirs travel. If your wedding is abroad rather than in the city, our '
  '<a href="../destinations/">destination guides</a> set out what changes country by country.',
'choosing-wedding-hymns':
  'Choosing hymns for a wedding abroad adds a question this guide does not: which language the congregation '
  'will actually sing in. Our <a href="../destinations/">country guides</a> take that one country at a time.',
'jerusalem':
  'British couples marrying abroad often want one unmistakably British thing in the service, and this is '
  'usually it. Our <a href="../destinations/">destination guides</a> cover bringing a choir out to sing it.',
'lesser-known-wedding-choral-pieces':
  'Unaccompanied repertoire travels particularly well, because it needs no organ to be found at the other end. '
  'See our <a href="../destinations/">destination guides</a> if you are marrying abroad.',
'popular-wedding-organ-music':
  'Worth knowing before you plan around it: many wedding venues abroad have no organ at all. Our '
  '<a href="../destinations/">destination guides</a> cover what unaccompanied voices do in a room without one.',
'ubi-caritas-wedding':
  'Latin belongs to no single country, which is why it solves the problem of a congregation split between two '
  'languages. Our <a href="../destinations/">destination guides</a> explain where that comes up.',
'wedding-ceremony-music':
  'The shape described here is the shape of a British church service. A ceremony abroad may have a different '
  'rite or none at all&thinsp;&mdash;&thinsp;our <a href="../destinations/">country guides</a> set out how the '
  'music sits in each.',
'wedding-choir-guide':
  'Hiring a choir for a wedding abroad works the same way, with flights, accommodation and sometimes a work '
  'permit on top. Our <a href="../destinations/">destination guides</a> cover all three.',
'wedding-choral-repertoire':
  'This repertoire needs no organ and no amplification, which is why it survives the journey to a Tuscan church '
  'or a beach in the Caribbean. See our <a href="../destinations/">destination guides</a>.',
'wedding-music-costs':
  'Costs abroad follow a different arithmetic: the singers, the distance, and the nights they stay. Our guide to '
  '<a href="destination-wedding-choir.html">hiring a UK choir for a destination wedding</a> sets out what that adds.',
'wedding-music-ideas':
  'If the wedding is abroad, the venue tends to supply its own ideas&thinsp;&mdash;&thinsp;a cloister, a terrace, '
  'a beach at dusk. Our <a href="../destinations/">destination guides</a> cover what suits each.',
'wedding-organ-pop-songs':
  'Without an organ, these arrangements move to unaccompanied voices, which is the usual position at a wedding '
  'abroad. See our <a href="../destinations/">destination guides</a>.',
'wedding-organ-repertoire':
  'Almost none of this repertoire is available at a destination wedding, where an organ is the exception. Our '
  '<a href="../destinations/">country guides</a> cover what a consort sings in its place.',
'wedding-organist-guide':
  'Booking an organist abroad depends entirely on whether the building has an instrument worth playing. Our '
  '<a href="../destinations/">destination guides</a> say what to expect country by country.',
'wedding-pop-songs-choir':
  'A cappella pop arrangements need no instrument, which makes them one of the easier things to take abroad. '
  'See our <a href="../destinations/">destination guides</a>.',
'wedding-readings-and-music':
  'Pairing readings with music gets more interesting when the congregation is bilingual. Our '
  '<a href="../destinations/">country guides</a> cover which parts are usually sung in which language.',
}

MARK = '<p><strong>If you&rsquo;re planning a wedding</strong>'
changed = 0
for slug, sentence in SENTENCES.items():
    p = pathlib.Path(f'music-guides/{slug}.html')
    s = p.read_text(encoding='utf-8')
    if '/destinations/' in s or 'destination-wedding-choir.html' in s:
        print(f'  skip (already linked): {slug}')
        continue
    i = s.index(MARK)
    end = s.index('</p>', i) + len('</p>')
    new_para = f'\n      <p>{sentence}</p>'
    s = s[:end] + new_para + s[end:]
    p.write_text(s, encoding='utf-8')
    changed += 1
print(f'{changed} guides cross-linked')
