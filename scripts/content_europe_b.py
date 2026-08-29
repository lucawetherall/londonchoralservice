#!/usr/bin/env python3
"""Greece, Cyprus, Malta, Croatia."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_country_pages import build

n = build('greece', 'Greece',
  'A Wedding Choir in Greece &mdash; Santorini, Crete, Mykonos | Alma Consort',
  'A British consort at Greek weddings: why an Orthodox service works differently, and how music '
  'is placed at a clifftop ceremony in Santorini or Mykonos.',
  'Greece needs a straight answer about the Orthodox service.',
  'Alma Consort travels from London to sing at clifftop and resort ceremonies in Santorini, Mykonos, '
  'Crete, Rhodes and Zakynthos.',
  [
   ('Orthodox', 'If you are having an Orthodox service',
    ['This is the most important thing on the page, and it is better said plainly than discovered late. '
     'A Greek Orthodox wedding is not structured like a Western one. It has no congregational hymns, no '
     'sung ordinary in the Latin sense, and no natural gaps for a visiting choir. The service is chanted '
     'by a cantor or a small Byzantine ensemble in a tradition with its own repertoire, its own '
     'scale system and its own performers, and the crowning and the procession around the table are '
     'sung as part of that tradition rather than accompanied by outside music.',
     'The rite is therefore complete without us, and we leave it to itself. What the consort does is '
     'sing everywhere else in the day, and at a Greek wedding that is a great deal: as your guests gather and are seated beforehand, at the drinks that follow, through the '
     'wedding breakfast, and at a welcome dinner the evening before. Couples who have had both tell us the contrast works in their favour. The chanting belongs to the rite, and the consort belongs to the celebration around it.',
     'Many couples in this position have both &mdash; an Orthodox service for the family and a '
     'ceremony of their own, humanist or celebrant-led, at the venue &mdash; and we sing at the second '
     'from beginning to end.']),
   ('The ceremony', 'What we do at a Greek destination wedding',
    ['For a symbolic or civil ceremony, we would usually suggest three or four pieces rather than a long '
     'programme. Something as the guests are seated and the bride arrives; something in the still moment '
     'before or after the vows; something as you leave. A consort singing unaccompanied on a terrace '
     'above the caldera is a striking thing, and it works better as a few deliberate moments '
     'than as continuous background.',
     'A second set during the drinks that follow is worth considering. The singers have already flown '
     'out, the ceremony itself uses perhaps twenty minutes of them, and an hour of part-songs and '
     'arrangements during the aperitif is the least expensive way to get more from the booking.']),
   ('Buildings', 'Terraces, caldera edges and the wind',
    ['Greece is acoustically the hardest place we sing. Almost every ceremony is outdoors, in the late '
     'afternoon, on a hard terrace with the sea below and open sky above, and open air returns nothing. '
     'On top of that, the islands are windy in a way photographs never convey. The meltemi in the '
     'Cyclades can take a quiet piece away from the guests.',
     'What follows is practical. Twelve voices rather than eight for an outdoor island ceremony; the '
     'singers positioned upwind of the guests rather than beside them; and a programme weighted towards '
     'pieces with weight and momentum rather than the most delicate thing in the repertoire. Where a '
     'venue has a chapel or a vaulted room, it is worth considering for the ceremony itself even if the '
     'terrace is the better photograph.']),
   ('Travel', 'Getting a consort to the Greek islands',
    ['Direct summer flights from London to Santorini, Mykonos, Crete, Rhodes and Zakynthos are frequent, '
     'though island connections are more fragile than mainland ones and a missed link is harder to '
     'recover from with a group of twelve. We build in the margin rather than cutting it fine, which '
     'usually means arriving two days before rather than one for the smaller islands.',
     'Accommodation on Santorini and Mykonos in high season is the real constraint, and it is expensive '
     'for a group of this size. This belongs in the conversation early, because it is a material part '
     'of the quote rather than a rounding error. We travel as British musicians into the Schengen area '
     'and handle the associated paperwork ourselves.']),
  ],
  [
   ('Santorini', 'santorini',
    ['Caldera-edge terraces, late afternoon light, and the most photographed ceremony setting in Europe. '
     'Also small venues, long stair approaches, high wind and no acoustic whatsoever. Twelve voices, '
     'placed close and upwind. Accommodation in season is the largest single variable in the cost.']),
   ('Mykonos', 'mykonos',
    ['Similar conditions to Santorini with more wind and a later schedule. Ceremonies here often run '
     'towards sunset, which is beautiful and means the singers are working at the end of a hot day; '
     'water and shade beforehand are not a courtesy but a requirement for a group that has to sing.']),
   ('Crete', 'crete',
    ['Larger, greener and easier logistically than the Cyclades, with more venues that have '
     'an indoor option and better flight resilience. If you are choosing between islands and want the '
     'music to be at its best, Crete gives you more to work with.']),
   ('Rhodes', 'rhodes',
    ['The medieval old town has stone buildings and courtyards that behave acoustically, which is rare '
     'in Greece and worth seeking out. Resort ceremonies on the coast are the more common format and are '
     'the standard outdoor case.']),
   ('Zakynthos', 'zakynthos',
    ['Resort, hotel and villa weddings on a green and unexpectedly dramatic island, with direct summer '
     'flights from London. Ceremonies are outdoors and the standard island conditions apply. Zakynthos '
     'is a good candidate for singing across the whole day rather than the ceremony alone: the venues '
     'tend to keep guests in one place from the vows through to dinner, so a consort that has flown out '
     'can sing at the ceremony, again over drinks, and once more before the meal.']),
  ],
  [
   ('Where do you sing at a Greek wedding?',
    'Everywhere except inside the Orthodox rite itself, which is chanted by a cantor in its own tradition '
    'and is complete as it stands. Around it there is a great deal: as your guests gather and are seated, '
    'at the drinks afterwards, through the wedding breakfast, and at a welcome dinner the evening before. '
    'And if you are having a symbolic ceremony as well, as most British couples in Greece are, we sing at that from start to finish.'),
   ('What if our ceremony is symbolic rather than religious?',
    'Then the music is open, and most British couples marrying in Greece are in exactly this '
    'position. With no liturgy to work around, we would suggest three or four deliberate moments rather '
    'than a continuous programme, and repertoire chosen purely because you like it.'),
   ('Will the wind be a problem on a clifftop?',
    'It can be, and it is the thing couples underestimate most about the Cyclades. We plan around it: '
    'more voices than the same ceremony would need in a church, the consort positioned upwind of you, and '
    'a programme that favours pieces with body over the most delicate ones. Tell us where the ceremony '
    'will be and we will tell you what we would do.'),
   ('How much of the cost is accommodation?',
    'On Santorini and Mykonos in July and August, more than most couples expect. Enough that it is worth discussing before you settle the date. Rooms for twelve to twenty-four people on those '
    'islands in high season are a material part of the quote. Crete and Rhodes cost less on that front.'),
  ])
print(f'greece {n}')

n = build('cyprus', 'Cyprus',
  'A Wedding Choir in Cyprus &mdash; Paphos, Protaras, Ayia Napa | Alma Consort',
  'A British consort at Cypriot weddings: town hall ceremonies, hotel and villa weddings, and an '
  'honest word about which end of the Cyprus market this suits.',
  'Cyprus is easy to marry in and easy to misjudge musically.',
  'Alma Consort travels from London to sing at civil, hotel and villa ceremonies in Paphos, Protaras '
  'and Ayia Napa.',
  [
   ('Options', 'What each route means for the music',
    ['A <strong>civil ceremony</strong> at a municipality is short and businesslike, and the music '
     'generally works better around it &mdash; as guests gather outside, or at the reception &mdash; '
     'than inside a ten-minute formality.',
     'A <strong>humanist or celebrant-led ceremony</strong> at a hotel or villa has no liturgy, so the programme is open: an entrance, a piece at the vows, a recessional, and as much or as '
     'little else as you want.',
     'An <strong>Anglican service</strong> is the one that gives a consort most to do, and the one '
     'couples least often realise is available. It runs on the order of service you would recognise '
     'from home, with hymns your guests can sing and a natural place for an anthem during the signing.',
     'A <strong>Greek Orthodox service</strong>, where one partner is Cypriot or Orthodox, is chanted '
     'in its own tradition and is complete without us; we sing around it, which at a Cypriot wedding '
     'covers a great deal of the day.']),
   ('Across the day', 'Where the music goes at a Cypriot wedding',
    ['Cyprus suits singing across a whole day better than most destinations, because so many weddings '
     'here keep everybody in one place. The ceremony, the drinks and the dinner are frequently at the '
     'same hotel or villa, with no transfer to lose an hour to.',
     'That opens up more than a ceremony programme. We can sing as your guests arrive and are seated, '
     'through the ceremony itself, over the drinks that follow, and again before or during the wedding '
     'breakfast. A welcome dinner the evening before is another natural point, and one couples often '
     'do not think to ask about.',
     'We come in sizes from a soloist upwards, so the shape can be built around your day rather than '
     'the other way round: a quartet close in at a small villa ceremony reads quite differently from '
     'twelve voices filling a church, and both are worth considering. Tell us what the day looks like '
     'and we will suggest what we would bring.']),
   ('Buildings', 'Terraces, town halls and a good deal of stone',
    ['Municipal ceremony rooms are small, dry and unglamorous acoustically; the music tends to work '
     'better just outside them, as guests gather, than inside during a ten-minute ceremony.',
     'Hotel and villa ceremonies are outdoors, and the standard outdoor rules apply: no reverberation, '
     'a coastal breeze, and a recommendation of twelve voices where a church would want eight. Cyprus '
     'is hot late into the season, and an afternoon ceremony in August needs shade for the singers '
     'arranged in advance.',
     'The island does have stone worth singing in, monastery churches inland and the older buildings in Paphos among them. Where a venue offers an indoor or courtyard option, it is usually '
     'the better room even when the terrace is the better view.']),
   ('Travel', 'Getting a consort to Cyprus',
    ['Direct flights from London to Paphos and Larnaca run daily and year-round, and the island is small '
     'enough that transfers are short from either airport. Cyprus is a member of the European Union, so '
     'we travel as British musicians under the same arrangements that apply across the Schengen area '
     'and handle the paperwork ourselves.',
     'The season runs long here, and a wedding in May or October avoids both the worst of the heat and '
     'the peak accommodation rates, which for a group of this size makes a noticeable difference to the '
     'quote.']),
  ],
  [
   ('Paphos', 'paphos',
    ['The centre of the British wedding market in Cyprus, with the town hall ceremony room, a long list '
     'of hotels, and villa venues in the hills behind the town. The hill venues are where a consort makes '
     'most sense: larger events, more space, and often a courtyard that behaves better acoustically than '
     'an open terrace.']),
   ('Protaras', 'protaras',
    ['Coastal hotel weddings, frequently on a terrace or a beach deck, and the chapel at Agioi Anargyroi '
     'as the picturesque option. Standard outdoor conditions with a reliable sea breeze; plan voices and '
     'positions for it.']),
   ('Ayia Napa', 'ayia-napa',
    ['Hotel and beach weddings on the east coast, with the easiest logistics on the island and a long '
     'season. Ceremonies here are compact and the guests are usually close in, which suits a smaller group singing near them as well as it suits a full consort. A quartet at the ceremony and again over drinks is a shape that works well in this part of Cyprus.']),
  ],
  [
   ('How many singers suit a Cyprus wedding?',
    'It depends on the room more than on a standard answer. An open villa terrace in the Paphos hills '
    'gives nothing back acoustically and wants twelve voices; a compact hotel ceremony with the guests '
    'close in can be better served by four singing near them than by twelve at a distance. We come in '
    'sizes from a soloist upwards. Tell us the venue and the numbers and we will recommend what we would bring.'),
   ('Can you sing at a Cypriot civil ceremony?',
    'Yes. Civil and celebrant-led ceremonies have no liturgy, so the music is open. Municipal '
    'ceremony rooms are small and acoustically flat, so we often suggest placing the singing outside as '
    'guests gather, and around the ceremony rather than inside a ten-minute formality.'),
   ('What about a Greek Orthodox ceremony in Cyprus?',
    'The rite itself is chanted by a cantor in its own tradition, so we do not sing during it. We sing '
    'around it instead, which at a Cypriot wedding covers a lot of ground: as guests gather beforehand, '
    'at the drinks afterwards, and through the wedding breakfast. Couples having an Orthodox service and '
    'a separate symbolic ceremony often have us at the second as well.'),
   ('When is the best time of year?',
    'May and October, for the music as much as the weather. The heat is manageable for singers working '
    'outdoors, and accommodation for a group of twelve to twenty-four is markedly cheaper than in high '
    'summer, which shows up directly in the quote.'),
  ])
print(f'cyprus {n}')

n = build('malta', 'Malta',
  'A Wedding Choir in Malta &mdash; Valletta, Mdina, Gozo | Alma Consort',
  'A British consort at Maltese weddings: baroque churches built for singing, English as an official '
  'language, and the shortest paperwork in the Mediterranean.',
  'Of everywhere we travel, Malta suits a choir best.',
  'Alma Consort travels from London to sing nuptial Masses and blessings in Valletta, Mdina and on Gozo.',
  [
   ('Why Malta', 'The destination that was built for this',
    ['If a couple asked us to name the single best place outside England to hear a consort at a wedding, '
     'the answer would be Malta, and it is not a close contest.',
     'The islands have an extraordinary density of baroque churches, built in stone, built tall, and '
     'built at a time when music was assumed to be part of what happened inside them. English is an '
     'official language, so the celebrant, the venue and your guests all operate in it without anyone '
     'translating. The country is Catholic, so a nuptial Mass with a full sung ordinary is the norm '
     'rather than something to negotiate. And the flight is under three and a half hours.',
     'The practical consequence is that almost everything that makes a destination wedding musically '
     'awkward elsewhere &mdash; no building, no liturgy, a language barrier, a dry outdoor acoustic &mdash; does not apply here.']),
   ('The rite', 'The nuptial Mass in a Maltese church',
    ['A Maltese wedding is usually a full nuptial Mass, and the parishes are accustomed to music being '
     'taken seriously. The shape is the familiar one: entrance, Kyrie and Gloria, psalm and acclamation, '
     'the rite of marriage, offertory, Sanctus and Agnus Dei, communion motets and a recessional.',
     'Maltese churches often have their own organ and, in some parishes, their own singers. We are glad '
     'to work alongside a house organist rather than around one, and it usually improves the result: an '
     'organ in a building like this is worth using. Tell us early if the church expects its own musicians '
     'to be involved, and we will plan the programme so that everybody has something to do.']),
   ('Language', 'English, Latin and Maltese',
    ['The service may be conducted in English or in Maltese, or in a mixture, and your celebrant will '
     'tell you which. Either way we would sing the ordinary in Latin, which needs no negotiation in a '
     'Catholic church and suits these buildings.',
     'Because English is an official language, this is the one Mediterranean destination where you can '
     'reasonably expect the congregation to sing a hymn. If you want that, and a congregation singing in a Maltese church is a considerable sound, choose something well known and let '
     'us lead it. Our guide to <a href="/music-guides/choosing-wedding-hymns.html">choosing wedding '
     'hymns</a> applies here almost unchanged.']),
   ('Buildings', 'Stone, height and a great deal of reverberation',
    ['Maltese limestone churches are reverberant, sometimes strikingly so, with tails long enough that '
     'tempo becomes the main musical decision. Polyphony sounds magnificent; anything fast turns to mud. '
     'We plan Maltese programmes slower than we would at home, and we use the building rather than '
     'fighting it.',
     'The size of these churches means the number of singers is driven by the room rather than by how '
     'many people are standing in it. A large parish church or the co-cathedral scale of building wants sixteen voices to feel '
     'proportionate even with a modest congregation; a small chapel in Mdina or on Gozo is well served '
     'by eight. This is the one destination where we regularly recommend more singers because of the '
     'architecture rather than because of an absent acoustic.']),
   ('Travel', 'Getting a consort to Malta',
    ['Direct flights from London run daily and year-round, at around three and a half hours. Malta is a '
     'member of the European Union, so we travel as British musicians under the same arrangements that '
     'apply across the Schengen area, and we handle that paperwork ourselves.',
     'The island is small enough that transfers from the airport to any venue are short, which removes '
     'the usual risk of a long inland drive after a delayed flight. Gozo adds a ferry crossing and '
     'should be planned with an extra margin.']),
  ],
  [
   ('Valletta', 'valletta',
    ['City churches at the grandest end of what the islands offer, with the height and stone that make '
     'sixteen voices sound like a cathedral choir. Everything is within a short transfer of the airport '
     'and the hotels, which makes Valletta the simplest logistics of any destination on our list.']),
   ('Mdina', 'mdina',
    ['The old walled city, and the most atmospheric setting in Malta for a wedding. The cathedral and the '
     'smaller churches within the walls are both worth singing in; the smaller ones need eight voices '
     'rather than sixteen. Vehicle access inside the walls is restricted, so plan the approach.']),
   ('Gozo', 'gozo',
    ['Quieter, greener, and with parish churches out of all proportion to the size of their villages, which is excellent news acoustically. The ferry crossing means building an extra hour into '
     'the schedule each way, and we would generally arrive the day before rather than the morning of.']),
  ],
  [
   ('Why is Malta better for a choir than Italy or Spain?',
    'Three reasons that stack. The churches are baroque, stone and tall, which is the acoustic this '
    'repertoire assumes. English is an official language, so nothing is lost in translation and your guests can sing a hymn. And a nuptial Mass with a sung ordinary is the normal form of '
    'service rather than something to request. Elsewhere you get one or two of those; Malta gives you all three.'),
   ('Will the church have its own organist?',
    'Often, yes, and that is a good thing rather than a complication. An organ in a Maltese church is '
    'worth using, and we plan programmes that give a house organist a real part rather than working '
    'around them. Tell us early what the parish expects.'),
   ('How many singers for a Maltese church?',
    'Driven by the building more than the guest list. A large parish church wants sixteen voices to feel '
    'proportionate, because the room is enormous. A small chapel in Mdina or a village '
    'church on Gozo is well served by eight. Send us the church and we will tell you.'),
   ('Can our guests sing hymns?',
    'Yes, and Malta is the destination where we most often suggest it. With English as an official '
    'language there is no barrier, and a congregation singing a familiar hymn in a building with that '
    'much stone is one of the better sounds available at a wedding anywhere.'),
  ])
print(f'malta {n}')

n = build('croatia', 'Croatia',
  'A Wedding Choir in Croatia &mdash; Dubrovnik, Hvar, Split | Alma Consort',
  'A British consort at Croatian weddings: Adriatic stone churches, old-town cloisters, and what an '
  'island ceremony asks of a group of twelve singers.',
  'Croatia has the stone; the difficulty is getting to it.',
  'Alma Consort travels from London to sing in the old towns of Dubrovnik and Split, on Hvar, and at '
  'estates in Istria.',
  [
   ('The rite', 'Catholic Croatia and the celebrant-led alternative',
    ['Croatia is strongly Catholic, and a nuptial Mass in a Dalmatian church has the same shape a British '
     'couple would recognise from Italy or Spain: a sung ordinary, psalm and acclamation, offertory and '
     'communion motets, and a recessional. Parishes in the old towns are used to weddings and to visiting '
     'musicians.',
     'A large share of foreign weddings here, though, are celebrant-led ceremonies in a cloister, a '
     'terrace or a garden, with the legal formality handled separately. Those have no liturgy, which '
     'leaves the programme open. Croatia is unusual in that the non-liturgical venues are often as good '
     'acoustically as the churches, because so many of them are enclosed stone courtyards rather than '
     'open lawns.']),
   ('Language', 'Croatian, Latin and the practical answer',
    ['A church service will be in Croatian, and the sung ordinary in Latin as elsewhere. For a '
     'celebrant-led ceremony in English there is no requirement to include anything Croatian, and most '
     'couples do not.',
     'Where a couple wants to acknowledge the country, the honest option is a piece of Adriatic '
     'Renaissance polyphony rather than a folk arrangement; the region had a real school of church '
     'composition and it belongs in these buildings.']),
   ('Buildings', 'Cloisters, old-town churches and enclosed courtyards',
    ['This is Croatia&rsquo;s advantage over most of the Mediterranean. The old towns are built of stone '
     'and built tight, and a cloister or a walled courtyard behaves acoustically far more like a church '
     'than like a terrace. A consort of eight in a Dubrovnik cloister carries in a way the same eight would not on a hotel lawn anywhere else on this list.',
     'The churches themselves are stone-vaulted and generous, and eight to twelve voices covers almost '
     'anything. Where a ceremony is open-air &mdash; a clifftop on Hvar, a vineyard in Istria '
     '&mdash; the usual outdoor rules return and we would recommend twelve.']),
   ('Travel', 'Getting a consort to Croatia, and the island question',
    ['Dubrovnik, Split and Zagreb are served directly from London through the season, and Pula for '
     'Istria. The mainland is straightforward.',
     'The islands are the complication, and it is worth planning for properly. Hvar and the other Adriatic '
     'islands are reached by ferry or catamaran from Split, on schedules that thin out sharply outside '
     'summer and can be disrupted by weather. Moving twelve to twenty-four people plus luggage across a '
     'ferry connection on the morning of a wedding is a risk we will not take, so for island weddings we '
     'arrive two days early rather than one. That is a second night in the quote, and it is not negotiable. It is the difference between a choir at your wedding and a choir on a quayside.',
     'Croatia is in the European Union and the Schengen area, and we travel as British musicians under '
     'the arrangements that apply there, handling the paperwork ourselves.']),
  ],
  [
   ('Dubrovnik', 'dubrovnik',
    ['The best acoustics available to a foreign wedding in Croatia: old-town churches and, better still, '
     'the cloisters. Vehicle access within the walls is restricted and much is reached on foot up steps, '
     'which is worth knowing when scheduling a group in August. The airport is close.']),
   ('Split', 'split',
    ['Diocletian&rsquo;s palace and the buildings inside it, with a good deal of enclosed stone and an '
     'easy airport. Split is also the ferry port for the islands, so a wedding here avoids the crossing, the simplest choice in Dalmatia for a group this size.']),
   ('Hvar', 'hvar',
    ['Beautiful, and the most logistically demanding place on this page. The ferry from Split is the '
     'binding constraint and the reason we plan two nights rather than one. Once there, the town has '
     'stone churches and enclosed spaces that reward the effort.']),
   ('Istria', 'istria',
    ['Hilltop towns, vineyards and estates, closer to Venice in feel than to Dalmatia, and reachable '
     'through Pula or overland from Trieste. Ceremonies here are more often outdoors among vines than in '
     'a church, so plan for twelve voices and a dry acoustic.']),
  ],
  [
   ('Is a cloister really better than a terrace?',
    'By a wide margin, and it is the main reason Croatia punches above its weight musically. Enclosed stone '
    'returns sound the way a church does, so eight voices in a Dubrovnik cloister carry and bloom where the same eight on an open lawn would sound thin. If your venue offers both, we would push you '
    'towards the cloister.'),
   ('Why do you need two nights for an island wedding?',
    'Because the ferry is the weak link. Catamaran and ferry schedules to Hvar and the other islands '
    'thin out outside summer and are subject to weather, and we will not put a twelve-person group on a '
    'crossing on the morning of the wedding. Arriving two days ahead costs a second night in the quote '
    'and removes the only real way this goes wrong.'),
   ('Can you sing at a Catholic wedding in a Croatian church?',
    'Yes. The nuptial Mass is the usual form and parishes in the old towns are used to weddings and to '
    'visiting musicians. We sing the ordinary in Latin; the spoken service will be in Croatian. Confirm '
    'with the parish that a visiting choir is welcome and whether their own organist expects to play.'),
   ('When is the best time of year?',
    'May, June and September. July and August bring cruise-ship crowds to Dubrovnik and Split, higher '
    'accommodation costs for a group of this size, and heat that is hard on singers working outdoors. '
    'The shoulder months are better in every respect, including the quote.'),
  ])
print(f'croatia {n}')
