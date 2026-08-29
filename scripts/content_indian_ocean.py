#!/usr/bin/env python3
"""Mauritius, Maldives, Seychelles, Thailand, Bali, South Africa."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_country_pages import build

MAURITIUS_COST = (
 'Mauritius sits at the more reasonable end of long-haul, and the reason is the flight: direct from '
 'London, no domestic connection, and a resort transfer of an hour or two rather than a day. Beyond the '
 'singing you are paying return fares and two nights for the singers who travel, and we quote all of it '
 'itemised before you commit. Two things make that go further. A church ceremony gets more from fewer '
 'voices, because the building does half the work. And because the ceremony and the reception are usually at the same resort, a consort that has flown out can sing across the whole day rather than for twenty minutes: the arrival, the ceremony, the drinks, the dinner. Tell us the shape of the '
 'day and we will suggest the size of group that fits it.')

SEYCHELLES_COST = (
 'One thing shapes a Seychelles quote more than anything else: which island. Every domestic flight or '
 'ferry adds fares for the whole group and, because we build in margin rather than risking a same-day '
 'connection, usually a night as well. A wedding on Mah&eacute; therefore costs noticeably less to bring '
 'a consort to than one on La Digue, which is worth knowing while the venue is still being chosen rather than after. Tell us the island and we will quote the real figure, itemised, before you '
 'commit to anything.')

THAILAND_COST = (
 'A Thai engagement is priced by the journey more than by anything else: twelve hours in the air, two '
 'nights minimum on the ground, and a domestic connection if the wedding is on Samui. We itemise all of '
 'it rather than folding it into one figure. The lever worth knowing about is group size, and it is a '
 'musical decision as much as a financial one: Thai villa ceremonies tend to be intimate, with guests '
 'close in, and four to eight voices in a covered pavilion is a warmer and more direct sound than '
 'twelve at a distance. Tell us the venue and the guest numbers and we will say what we would bring.')

BALI_COST = (
 'Bali is the longest journey we make, and the quote reflects it: fourteen to sixteen hours with a stop '
 'for each singer who travels, plus a minimum of two nights before the ceremony. We set it out itemised '
 'before you commit. What works in your favour here is the architecture. Bali&rsquo;s clifftop chapels '
 'are not large, and eight voices inside one carries further and blends better than twelve outside it, so the group that sounds best is often the one that costs least to fly. Tell us the venue and '
 'we will say what we would bring.')

n = build('mauritius', 'Mauritius',
  'A Wedding Choir in Mauritius &mdash; Belle Mare, Le Morne | Alma Consort',
  'A British consort at Mauritian weddings: beach and resort ceremonies, colonial churches, and what '
  'a long flight and tropical humidity ask of singers.',
  'A long way to bring a choir, and a real church at the end of it.',
  'Alma Consort travels from London to sing at resort and church ceremonies at Belle Mare, Le Morne '
  'and Grand Baie.',
  [
   ('The ceremony', 'Resort weddings, and the churches most couples miss',
    ['Almost every foreign wedding in Mauritius happens at a resort: a beach, a garden, or a deck over '
     'the lagoon, celebrant-led, with no liturgy. The music therefore carries the structure rather than filling a service: an entrance, a piece at the exchange of vows, a recessional, and a set during the drinks that follow.',
     'What is easy to overlook is that Mauritius has a substantial Catholic population and a number of '
     'fine colonial-era churches, several of them stone and none of them far from the coastal resorts. '
     'If a church ceremony is possible for you, it transforms what a consort can do here: a real '
     'building with a real acoustic, in a country where the alternative is an open beach. Ask your '
     'planner whether a church ceremony followed by a resort reception is available; it usually is.']),
   ('Climate and voices', 'What the journey and the humidity actually do',
    ['Mauritius is a twelve-hour flight from London with a three- or four-hour time change. Long in the air, but with less disruption to the body clock than the Caribbean or the United States. '
     'The heat and humidity are the larger factor.',
     'Singing is physical work. In high humidity, after a long overnight flight, a group tires faster '
     'and sounds tired sooner. We travel two days ahead rather than one so the consort arrives rested, '
     'and we would push for a late-afternoon or early-evening ceremony rather than the middle of the '
     'day. Shade and water for the singers are practical requirements rather than courtesies. All of '
     'this belongs in the running order at the planning stage.']),
   ('Buildings', 'Lagoon decks, gardens and colonial stone',
    ['A beach or lagoon-deck ceremony has no acoustic: open water and open sky return nothing, and the '
     'trade wind carries what there is away. Twelve voices minimum, placed close to the guests and '
     'upwind where the layout allows.',
     'Resort gardens are marginally better for the vegetation around them. The colonial churches are the only rooms on the island with a real acoustic, and where one is available it is worth reorganising the '
     'day around.']),
   ('Cost', 'What a Mauritian engagement costs', [MAURITIUS_COST]),
  ],
  [
   ('Belle Mare', 'belle-mare',
    ['The east coast, with a run of large resorts and long beaches. Ceremonies are almost always on sand '
     'or a deck, with a reliable breeze off the lagoon. Standard outdoor planning applies: more voices, '
     'placed close, upwind.']),
   ('Le Morne', 'le-morne',
    ['The south west, under the mountain, and the most dramatic setting on the island. Also the windiest stretch of coast, it is a kitesurfing centre for a reason, which is a genuine consideration for unamplified voices outdoors. Worth discussing the ceremony position with the '
     'venue rather than accepting the default.']),
   ('Grand Baie', 'grand-baie',
    ['The north, the busiest part of the island, with the shortest transfers from the airport in the south being the trade-off, allow well over an hour. More venues, more choice, and better '
     'access to churches than the remoter coasts.']),
  ],
  [
   ('Is there anywhere with a proper acoustic in Mauritius?',
    'Yes, and it is the thing most couples do not realise. Mauritius has a substantial Catholic '
    'population and several fine colonial-era churches within reach of the coastal resorts. A church '
    'ceremony followed by a resort reception gives the consort a real building to sing in and you a much '
    'better result than a beach. Ask your planner. The option is usually there.'),
   ('How long is the flight and does it matter?',
    'Around twelve hours, but with only a three- or four-hour time change, so the body clock disruption '
    'is milder than a Caribbean or American trip. The length still matters: we travel two days ahead so '
    'the singers arrive rested rather than singing on the morning after an overnight flight.'),
   ('How many singers for a beach ceremony?',
    'Twelve as a minimum. Open water and open sky return no sound at all, and the trade wind takes what '
    'there is away from the guests. Where a church is available, eight will do more than twelve on the beach, the building does the work.'),
   ('What will this cost?',
    'More than a European engagement, because the flights and two nights of accommodation for the '
    'singers who travel dominate the figure. We quote it itemised so you can see each part. Two things '
    'stretch it further: a church ceremony, where the building lets fewer voices do more, and singing '
    'across the whole day rather than the ceremony alone, since the travel is already paid for. Tell us '
    'the shape of the day and we will suggest what fits it.'),
  ])
print(f'mauritius {n}')

n = build('maldives', 'Maldives',
  'A Wedding Choir in the Maldives &mdash; Mal&eacute; and Ari Atolls | Alma Consort',
  'A British consort at Maldivian weddings: island resort ceremonies, seaplane logistics, and an '
  'honest account of what bringing twelve singers this far involves.',
  'The furthest we go, and the one that needs the plainest talking.',
  'Alma Consort travels from London to sing at resort ceremonies in the North Mal&eacute; and South '
  'Ari atolls.',
  [
   ('Getting there', 'The journey, and why we plan it the way we do',
    ['The Maldives asks more of the logistics than anywhere else we sing, and we would rather set that '
     'out at the top than leave you to discover it.',
     'It is a ten- to eleven-hour flight to Mal&eacute;, followed by a seaplane or speedboat transfer to '
     'the resort island. Seaplanes fly in daylight only, carry limited baggage, and do not always run to '
     'the timetable agreed. Moving a group plus formal dress through that chain is a real exercise, and '
     'it is why we arrive two full days before the wedding rather than one. That margin is what makes '
     'the booking reliable rather than hopeful, and it is priced in rather than sprung on you later.',
     'One choice makes everything easier, and it happens to be the musically better one too. Maldivian '
     'ceremonies are small and close &mdash; a sandbank, a jetty, a stretch of beach &mdash; and a '
     'smaller group singing near the guests sounds warmer and more direct than a large one spread '
     'along a shoreline. Eight voices is often exactly right here, and eight people '
     'move through a seaplane transfer far more easily than twenty-four.']),
   ('The ceremony', 'What we sing, and where',
    ['Weddings in the Maldives are symbolic or celebrant-led ceremonies at a resort. The legal marriage is almost always completed at home beforehand. There is no liturgy and no repertoire '
     'restriction, so the programme is yours.',
     'The settings are small and close, so we would suggest a shorter, more deliberate programme than the scale of the journey might imply, three or four pieces that land, rather than a long list. Beyond the ceremony there is the sunset drinks hour, the dinner, and often a welcome '
     'gathering the evening before, all of which suit unaccompanied voices and none of which cost '
     'anything more in travel.']),
   ('Buildings', 'There are none, and that is the whole point',
    ['This is the only destination on our list with no built acoustic to speak of. There are '
     'no churches to sing in; the ceremony is on sand, on a deck, or on a sandbank, under open sky, '
     'beside open water.',
     'That means everything the consort does is unsupported. There is no reverberation to blend the '
     'sound, nothing to carry it to the back, and a sea breeze working against you. In compensation, '
     'the guest numbers are usually small and everyone is close, which is exactly the condition where '
     'an unaccompanied group still works. The music should be chosen for it: pieces with clear lines '
     'and real body, sung close in, rather than the most delicate polyphony in the repertoire.']),
   ('Climate', 'Heat, humidity and salt air',
    ['Consistently hot and humid all year, which tires voices faster than dry heat does. A ceremony at '
     'sunset rather than in the afternoon is much better for the singing as well as for the light, and '
     'shade beforehand is a requirement rather than a nicety.',
     'The practical detail people forget is salt and sand: neither is good for formal dress or for '
     'printed music, and both are unavoidable on a beach. We plan for it and mention it here only so '
     'that nobody is surprised when we ask about the walk to the ceremony spot.']),
  ],
  [
   ('North Mal&eacute; Atoll', 'north-male-atoll',
    ['The closest resorts to the airport, many reachable by speedboat rather than seaplane, which '
     'removes the single most fragile link in the journey. If you want a consort in the Maldives and '
     'have a choice of atoll, this is the one that makes the logistics workable.']),
   ('South Ari Atoll', 'south-ari-atoll',
    ['Further out, and seaplane-served, with the daylight-only constraint and baggage limits that come '
     'with that. Beautiful, and materially harder to move a group of singers to. We would arrive two '
     'days ahead without exception and build slack into every connection.']),
  ],
  [
   ('Can you really bring singers to a Maldives resort island?',
    'Yes, and we have planned the way we do it around the one weak link, which is the seaplane. We '
    'arrive two full days early so no connection sits between us and your wedding, and we usually recommend a smaller group, eight voices rather than twenty-four, because it suits the intimate settings and moves through the transfer chain far more easily. Tell us the resort and '
    'we will tell you exactly how we would do it.'),
   ('How many singers would you recommend?',
    'Fewer than you might expect, on musical grounds. Maldivian ceremonies are small, with guests close '
    'to the couple, and eight voices sung near them carries better and sounds warmer than a larger group '
    'spread along a beach. The fact that eight people also move through a seaplane transfer more easily '
    'than twenty-four is a happy coincidence rather than the reason.'),
   ('Why do you need two days on the island first?',
    'The seaplane chain. Seaplanes fly in daylight only, take limited baggage, and are subject to '
    'weather and to timetable changes. Moving twelve to twenty-four people through that on the day '
    'before a wedding leaves no room for anything to go wrong. Two days is the margin that makes it safe.'),
   ('Is there anywhere with an acoustic?',
    'Not in the way a church provides one. There are no stone buildings to sing in, so everything is outdoors and unsupported. We plan the programme around that: clear lines, real body, sung close '
    'in. The small guest numbers work in our favour here, and an unaccompanied group is the one kind of '
    'live music that needs nothing from the venue at all.'),
  ])
print(f'maldives {n}')

n = build('seychelles', 'Seychelles',
  'A Wedding Choir in the Seychelles &mdash; Mah&eacute;, Praslin, La Digue | Alma Consort',
  'A British consort at Seychellois weddings: granite island ceremonies, Catholic churches on '
  'Mah&eacute;, and inter-island logistics for a group of twelve.',
  'Granite islands, a Catholic tradition, and three separate journeys.',
  'Alma Consort travels from London to sing at church and beach ceremonies on Mah&eacute;, Praslin '
  'and La Digue.',
  [
   ('The ceremony', 'Resort weddings and a real Catholic tradition',
    ['Most foreign weddings in the Seychelles are resort ceremonies on a beach or in a garden, '
     'celebrant-led and without liturgy, and the music does structural work rather than filling a service.',
     'The islands are also strongly Catholic, with parish churches on Mah&eacute; and Praslin that are '
     'real buildings rather than chapels of convenience. A nuptial Mass here gives a consort the full '
     'sung shape, and the acoustic is a different world from a beach. If a church ceremony is possible, '
     'it is the single change that most improves what you hear, and it is worth asking '
     'your planner about even if the resort has not offered it.']),
   ('Islands', 'Three islands, and moving between them',
    ['This is the logistical fact that shapes a Seychelles booking. The three main islands are separate '
     'journeys: Mah&eacute; has the international airport, Praslin is a short domestic flight or a '
     'ferry away, and La Digue is reached by ferry from Praslin.',
     'For a group of twelve to twenty-four with luggage and formal dress, each of those transfers is a '
     'point of failure, and ferry and domestic flight schedules are weather-dependent. We therefore '
     'arrive two days ahead for Mah&eacute; and would not attempt a same-day connection to Praslin or '
     'La Digue on the day before a wedding. If your ceremony is on La Digue, plan for us to be there '
     'well in advance and price the additional night accordingly.']),
   ('Buildings', 'Granite, palms and open water',
    ['Beach ceremonies here have the same absent acoustic as anywhere else, with the granite boulders '
     'the islands are famous for offering a little reflection if the ceremony is set among them: marginal, but real, and worth positioning for.',
     'The churches on Mah&eacute; and Praslin are the only settings with a genuine acoustic. Eight to '
     'twelve voices in one of them will do more than twice that number on a beach.']),
   ('Cost', 'Why the island you choose changes the price', [SEYCHELLES_COST]),
  ],
  [
   ('Mah&eacute;', 'mahe',
    ['The main island, the international airport and the best access to churches. If the music matters '
     'and you are choosing between islands, Mah&eacute; is the practical answer: no additional transfer, '
     'real buildings available, and the shortest chain between the plane and the ceremony.']),
   ('Praslin', 'praslin',
    ['A short domestic flight or ferry from Mah&eacute;, quieter, with resort and beach venues and a '
     'parish church. Add a night to the schedule for the transfer; we would not move a group of this '
     'size across on the day before a wedding.']),
   ('La Digue', 'la-digue',
    ['The furthest and the most beautiful, reached by ferry from Praslin, with bicycles and ox-carts '
     'rather than cars. Charming, and the hardest place on this page to deliver twelve singers and their '
     'formal dress to on schedule. Plan generously and expect the additional nights in the quote.']),
  ],
  [
   ('Should we get married on Mah&eacute; rather than La Digue?',
    'If the music is a priority, yes. Mah&eacute; has the international airport, so there is no ferry or '
    'domestic flight in the chain, and it has the churches, the only places in the Seychelles with a real acoustic. La Digue is more beautiful and materially harder to deliver a group of '
    'singers to on time.'),
   ('Is there a church option?',
    'Yes, and it is underused by foreign couples. The Seychelles are strongly Catholic and the parish '
    'churches on Mah&eacute; and Praslin are proper buildings. A nuptial Mass gives the consort the full '
    'sung shape and an acoustic that does half the work. Ask your planner even if the resort has not '
    'raised it.'),
   ('Why the extra nights?',
    'Because every island transfer is weather-dependent and every one is a point at which a group of '
    'twelve with luggage can be delayed. We arrive two days ahead for Mah&eacute;, and more where a '
    'domestic flight or ferry is involved. Those nights are in the quote; they are what makes the '
    'booking reliable rather than hopeful.'),
   ('Would a smaller group be better?',
    'Often, yes. Seychelles ceremonies tend to be small and close, and eight voices sung near the guests sound warmer than a larger group on an open beach, while being much easier to move between islands. Tell us the guest numbers and the venue and we will give you a specific recommendation.'),
  ])
print(f'seychelles {n}')

n = build('thailand', 'Thailand',
  'A Wedding Choir in Thailand &mdash; Phuket and Koh Samui | Alma Consort',
  'A British consort at Thai weddings: villa and beach ceremonies, a Buddhist blessing alongside a '
  'Western one, and what a twelve-hour flight asks of singers.',
  'A Western ceremony in a country with its own ideas about ritual.',
  'Alma Consort travels from London to sing at villa, resort and beach ceremonies in Phuket and on '
  'Koh Samui.',
  [
   ('The day', 'Where the music sits, and the Thai blessing alongside it',
    ['Whichever form your ceremony takes, it will almost certainly be outdoors or in a pavilion rather '
     'than a church, and without a liturgy to sit inside, the music does the structural work: the '
     'entrance, a piece at the vows, the recessional, and a set during the drinks that follow.',
     'Many couples also include a traditional Thai element: a Buddhist blessing, a monks’ ceremony in the morning, or the water-pouring <em>rod nam sang</em> ritual. Those have their own '
     'form and their own sound and are complete without us, so we leave them to stand on their own and '
     'sing at everything else: the Western ceremony, the drinks, the dinner, and the welcome party the '
     'evening before. Couples who have had both tell us the two halves set each other off rather than competing. The morning belongs to Thailand and the afternoon to them.']),
   ('Climate', 'Heat, humidity and a twelve-hour flight',
    ['Thailand is around twelve hours from London with a six- or seven-hour time change, and it is hot '
     'and very humid for most of the year. That combination is the hardest one on this list for singers: '
     'a long flight, a substantial time shift, and a climate that tires voices quickly.',
     'We travel two days ahead as standard and would push hard for an evening ceremony rather than an '
     'afternoon one. Shade, water and somewhere cool to wait beforehand are practical requirements. The monsoon season is worth avoiding for an outdoor ceremony, and your venue will advise on the local timing. It differs between Phuket on the west and Samui on the east.']),
   ('Buildings', 'Villas, beaches and no church to speak of',
    ['Thailand offers no Western church acoustic. Ceremonies are on beaches, in villa '
     'gardens, on cliff terraces and by pools, all of which return no sound at all.',
     'What Thailand does have, and it is a genuine advantage, is a large number of luxury villas with hard-surfaced interior spaces: polished stone terraces, covered pavilions, high-ceilinged sala. A covered pavilion with a hard floor is markedly better acoustically than open sand, and '
     'many villas have one. It is worth asking where the ceremony could be held rather than accepting '
     'the beach as a default.']),
   ('Cost', 'What twelve hours in the air adds', [THAILAND_COST]),
  ],
  [
   ('Phuket', 'phuket',
    ['Direct or one-stop from London, the largest concentration of luxury villas in Thailand, and the '
     'best chance of finding a covered pavilion or hard-surfaced terrace to sing in. Transfers from the '
     'airport to the west coast resorts are manageable. The practical default for a Thai wedding with '
     'music at the centre of it.']),
   ('Koh Samui', 'koh-samui',
    ['Reached by a domestic flight or a ferry, which adds a transfer and a point of failure for a group of this size. We would arrive an extra day early. Villa weddings on the north and west '
     'coasts, often on cliff terraces with spectacular views and no acoustic whatsoever.']),
  ],
  [
   ('How does a Thai blessing fit alongside what you sing?',
    'They sit side by side rather than overlapping. A monks&rsquo; ceremony or a water-pouring ritual has '
    'its own form and its own sound and is complete as it stands, so we leave it to itself and sing at everything else: the Western ceremony, the drinks, the dinner, and the welcome party the '
    'evening before. Couples who have had both say the two halves set each other off: the morning '
    'belongs to Thailand, the afternoon to them.'),
   ('Where should the ceremony be for the music to work?',
    'A covered pavilion or a hard-surfaced terrace rather than open sand. Many Thai luxury villas have '
    'a sala or a stone terrace that returns some sound, and the difference against a beach is large. Ask '
    'your venue what the options are rather than accepting the beach as the default; it is the single '
    'cheapest improvement available.'),
   ('How bad is the heat for singers?',
    'It is the most demanding climate on this list, because the humidity comes on top of a twelve-hour '
    'flight and a six- or seven-hour time change. We travel two days ahead, we would push for an evening '
    'ceremony, and we ask for shade and somewhere cool to wait. Planned for, it works.'),
   ('How many singers suit a Thai villa wedding?',
    'Often fewer than the journey might suggest. Thai villa ceremonies are intimate, with guests close '
    'in and a covered pavilion or terrace rather than a large room, and four to eight voices singing '
    'near people is warmer and more direct there than twelve at a distance. We come in sizes from a '
    'soloist upwards; tell us the venue and the guest numbers and we will recommend what we would bring.'),
  ])
print(f'thailand {n}')

n = build('indonesia', 'Bali',
  'A Wedding Choir in Bali &mdash; Uluwatu, Ubud, Seminyak | Alma Consort',
  'A British consort at Balinese weddings: clifftop chapels, jungle ceremonies, and the glass '
  'chapels that turn out to be the best rooms on the island.',
  'The island where the wedding venues built themselves a chapel.',
  'Alma Consort travels from London to sing at clifftop, jungle and resort ceremonies at Uluwatu, '
  'Ubud and Seminyak.',
  [
   ('The day', 'Where the music sits across a Balinese wedding',
    ['With no liturgy to sit inside, the music carries the structure of your ceremony: the entrance, a '
     'piece at the vows, the recessional, and a set afterwards. That is where a consort does most of '
     'its work in Bali.',
     'If you are also having a Balinese Hindu blessing, it belongs to a living tradition with its own '
     'musicians and is complete without us, so the two stand side by side in one day. A gamelan '
     'ensemble at the reception alongside a consort earlier is a combination worth planning for rather '
     'than choosing between.',
     'Across a Balinese wedding there is a good deal for us to sing at beyond the ceremony: the arrival, '
     'the drinks on the cliff, the dinner, and a welcome party the night before, which at a destination '
     'wedding with guests who have flown a long way is often the warmest hour of the whole trip.']),
   ('Buildings', 'The glass chapels, and why they matter',
    ['Bali is unusual, and in a way that works in our favour. The island&rsquo;s wedding industry has '
     'built a considerable number of purpose-made chapels. Glass and stone structures on the clifftops at Uluwatu and elsewhere, designed for exactly this kind of ceremony.',
     'Acoustically these are far better than an open lawn. Glass and polished stone are hard surfaces: '
     'they reflect sound rather than swallowing it, and a consort of eight in a clifftop chapel sounds '
     'full where the same eight on a beach below would sound thin. If you are choosing a Bali venue and '
     'the music matters, choosing one with a built chapel is the most effective single decision '
     'available to you.',
     'Jungle and rice-terrace ceremonies around Ubud are the opposite: beautiful, open, and acoustically dead. Twelve voices, close in.']),
   ('Climate and travel', 'A long way, and humid at the end of it',
    ['Bali is a fourteen- to sixteen-hour journey from London with a stop, and a seven- or eight-hour time change. The longest travel on this list. We arrive two days ahead as a minimum, and '
     'for a group this size we would build in more margin than that if the connection is tight.',
     'The island is hot and humid year-round with a distinct wet season, and the humidity tires voices '
     'in the way it does elsewhere in the tropics. A late-afternoon or evening ceremony, shade '
     'beforehand, and somewhere cool to wait are all worth arranging. Indonesia has its own requirements '
     'for foreign performers working for a fee; we confirm the current position when we quote and handle '
     'what applies.']),
   ('Cost', 'The longest journey on the list', [BALI_COST]),
  ],
  [
   ('Uluwatu', 'uluwatu',
    ['The clifftops in the south, and the greatest concentration of purpose-built wedding chapels on the '
     'island. Musically the best part of Bali by a clear margin: a glass and stone chapel above the ocean '
     'gives a consort hard surfaces to work with and a setting that needs no help. Wind on the cliff edge '
     'is a factor for any part of the ceremony held outside the chapel.']),
   ('Ubud', 'ubud',
    ['Inland among the rice terraces and the jungle, cooler than the coast and open acoustically. Ceremonies here are in gardens, on terraces and beside rivers, with nothing to '
     'reflect sound. Twelve voices, placed close. The setting is the reason to come here; the acoustic '
     'is the price of it.']),
   ('Seminyak', 'seminyak',
    ['The west coast, beach clubs and villas, and the easiest logistics on the island for transfers and '
     'accommodation. Beach and poolside ceremonies predominate, with the standard dry outdoor conditions '
     'and a sea breeze in the late afternoon.']),
  ],
  [
   ('Where do you sing at a Balinese wedding?',
    'At the Western-style ceremony foreign couples have, which is the one almost everyone we speak to is planning, and then across the rest of the day: the arrival, the drinks on the cliff, '
    'the dinner, and the welcome party the night before. A Balinese blessing has its own music and stands '
    'on its own, and a gamelan ensemble at the reception alongside a consort earlier in the day is a '
    'combination worth planning for rather than choosing between.'),
   ('Which Bali venue is best for a choir?',
    'One with a built chapel, and Uluwatu has the most of them. These glass and stone structures reflect '
    'sound the way a church does, so eight voices sound full where the same eight on the beach below '
    'would sound thin. If the music matters to you, choosing a venue with a chapel does more for the '
    'result than any other decision.'),
   ('How long does it take to get there?',
    'Fourteen to sixteen hours with a stop, and a seven- or eight-hour time change, the longest journey on this list. We arrive a minimum of two days ahead, and more if the connection is tight. '
    'Nobody sings well the morning after that trip, and we would rather build the margin in than promise '
    'something we cannot deliver.'),
   ('Would a smaller group work?',
    'Frequently, yes. Bali chapels are not large, guest numbers at destination weddings here are often '
    'modest, and eight voices in a chapel sounds better than twelve outside one. Given what the flights '
    'cost at this distance, a smaller group in a better room is usually the sensible trade. Tell us the '
    'venue and we will say what we would bring.'),
  ])
print(f'indonesia {n}')

n = build('south-africa', 'South Africa',
  'A Wedding Choir in South Africa &mdash; Cape Town, Franschhoek | Alma Consort',
  'A British consort at South African weddings: Cape Dutch wine estates, Anglican cathedrals, barrel '
  'cellars, and a country with a choral tradition of its own.',
  'A country that takes choral singing as seriously as we do.',
  'Alma Consort travels from London to sing at wine estate, cathedral and safari-lodge ceremonies in '
  'Cape Town, Franschhoek and beyond.',
  [
   ('Why South Africa', 'Arriving somewhere that already sings',
    ['South Africa is the only long-haul destination on this list with a choral culture that rivals '
     'anything in Europe. Choral singing here is popular rather than specialist &mdash; in '
     'churches, in schools, in communities &mdash; and standards are high. A visiting English consort '
     'arrives among people who know precisely what it is listening to.',
     'That has a practical consequence worth planning for. If your congregation includes South African '
     'guests, they will sing, and they will sing in parts without being asked. Choosing hymns that '
     'reward that, rather than something that assumes a congregation which mumbles, turns the '
     'congregational singing into one of the best moments of the day.']),
   ('The rite', 'Anglican services, estate ceremonies and safari lodges',
    ['South Africa has a substantial Anglican tradition, and a service in a Cape Town church or cathedral '
     'is one a British couple would recognise: the same order, the same hymnody, the same place for an anthem during the signing. Catholic and Dutch Reformed services are also common; '
     'the Reformed tradition is plainer and psalm-centred, with less room for an anthem but strong '
     'congregational singing.',
     'The most common format for a foreign wedding, though, is a ceremony at a wine estate in the '
     'Winelands, celebrant-led and without liturgy. Many of these estates have Cape Dutch buildings, '
     'barrel cellars or converted stone structures, and those are far better rooms than a lawn. Safari '
     'lodge weddings in the Kruger area are the other case: small, remote, outdoors, and requiring their '
     'own logistical planning.']),
   ('Buildings', 'Cape Dutch stone, barrel cellars and the open veld',
    ['The Winelands are unusually well provided acoustically. Cape Dutch farm buildings have thick walls '
     'and hard surfaces, and a barrel cellar, which several estates use for ceremonies or dinners, is one of the best spaces to sing in on this list, closer to a crypt than to a function room. Where an '
     'estate offers one, take it.',
     'Cape Town&rsquo;s churches and cathedral are stone and generous and support twelve to sixteen '
     'voices properly. Safari and bush ceremonies are open, dry, and often at dawn or dusk when '
     'the temperature is workable; twelve voices, close in.']),
   ('Travel', 'Getting a consort to South Africa',
    ['Direct overnight flights from London to Cape Town and Johannesburg run daily, at around eleven to twelve hours, and, unusually for long-haul, with almost no time change, which makes this '
     'much easier on singers than the Caribbean or Southeast Asia. An overnight flight arriving in the '
     'morning still means we travel two days ahead, but the recovery is faster than anywhere else at '
     'this distance.',
     'Cape Town to the Winelands is a short drive. The Kruger area needs a domestic flight and a further '
     'transfer, which we would plan with an extra day. We confirm the current requirements for foreign '
     'performers working for a fee when we quote and handle whatever applies.']),
  ],
  [
   ('Cape Town', 'cape-town',
    ['Churches and a cathedral with real acoustics, a short drive from the airport, and the strongest '
     'choral culture in the country. If the music is central to your day, a Cape Town church ceremony '
     'followed by a reception on the coast or in the Winelands is the shape we would suggest.']),
   ('Franschhoek and the Winelands', 'franschhoek',
    ['Cape Dutch estates within an hour of Cape Town, and the best non-church rooms in South Africa: '
     'thick-walled farm buildings and barrel cellars that behave acoustically far better than the lawns '
     'most couples default to. Ask each estate what indoor spaces are available for the ceremony. It is the question that most improves the result.']),
   ('The Kruger area', 'the-kruger-area',
    ['Safari lodge weddings: small, remote, outdoors, and usually at dawn or dusk. Reaching them means a '
     'domestic flight and a transfer on top of the international leg, so we would plan an additional day '
     'and price it. Twelve voices close to a small group of guests under open sky is the shape that works.']),
  ],
  [
   ('Will South African guests sing?',
    'Yes, and better than most congregations you will have heard. Choral singing here is popular rather '
    'than specialist, and a congregation with South African guests in it will often sing in parts without '
    'being asked. Choose hymns that reward that and let the consort lead rather than dominate; it makes '
    'for one of the best moments of the day.'),
   ('What is the best room at a wine estate?',
    'A barrel cellar, if the estate has one, or any thick-walled Cape Dutch building. These have hard '
    'surfaces and real reverberation and sound closer to a crypt than to a function room. Most estates '
    'default to offering a lawn; asking what indoor space is available is the single most effective '
    'question you can put to them.'),
   ('Is the jet lag as bad as other long-haul destinations?',
    'No, and it is South Africa&rsquo;s quiet advantage. The flight is eleven to twelve hours but the '
    'time difference is an hour or two at most, so singers arrive tired rather than displaced. Recovery '
    'is much faster than for the Caribbean, the United States or Southeast Asia, which shows in what you '
    'hear on the day.'),
   ('How does the cost compare with the Caribbean?',
    'Broadly comparable for Cape Town and the Winelands, where the flight is direct and the transfers '
    'short. A Kruger-area safari wedding costs more, because it adds a domestic flight, a further '
    'transfer and usually an extra night for the whole group. We itemise all of it before you commit.'),
  ])
print(f'south-africa {n}')
