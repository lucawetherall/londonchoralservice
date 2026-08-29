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
   ('The rite', 'Why an Orthodox wedding is a different proposition',
    ['This is the most important thing on the page, and it is better said plainly than discovered late. '
     'A Greek Orthodox wedding is not structured like a Western one. It has no congregational hymns, no '
     'sung ordinary in the Latin sense, and no natural gaps for a visiting choir. The service is chanted '
     'by a cantor or a small Byzantine ensemble in a tradition with its own repertoire, its own '
     'scale system and its own performers, and the crowning and the procession around the table are '
     'sung as part of that tradition rather than accompanied by outside music.',
     'We would not propose inserting an English consort into an Orthodox service, and any supplier who '
     'tells you otherwise is selling rather than advising. Where a couple is having an Orthodox ceremony '
     'and wants us there, the honest place for the music is around it: singing as guests arrive, or at '
     'the reception afterwards, where a consort can do a great deal.',
     'The good news is that most British couples marrying in Greece are not having an Orthodox service '
     'at all. They are having a symbolic or civil ceremony at a hotel, a villa or a clifftop terrace, '
     'and that format is entirely open. There is no liturgy to respect and no repertoire restriction: '
     'the music is whatever you want it to be, placed wherever it works.']),
   ('The ceremony', 'What we do at a Greek destination wedding',
    ['For a symbolic or civil ceremony, we would usually suggest three or four pieces rather than a long '
     'programme. Something as the guests are seated and the bride arrives; something in the still moment '
     'before or after the vows; something as you leave. A consort singing unaccompanied on a terrace '
     'above the caldera is a genuinely striking thing, and it works better as a few deliberate moments '
     'than as continuous background.',
     'A second set during the drinks that follow is worth considering. The singers have already flown '
     'out, the ceremony itself uses perhaps twenty minutes of them, and an hour of part-songs and '
     'arrangements during the aperitif is the least expensive way to get more from the booking.']),
   ('Buildings', 'Terraces, caldera edges and the wind',
    ['Greece is acoustically the hardest place we sing. Almost every ceremony is outdoors, in the late '
     'afternoon, on a hard terrace with the sea below and open sky above, and open air returns nothing. '
     'On top of that, the islands are windy in a way photographs never convey. The meltemi in the '
     'Cyclades can take a quiet piece away from the guests entirely.',
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
    ['Larger, greener and considerably easier logistically than the Cyclades, with more venues that have '
     'an indoor option and better flight resilience. If you are choosing between islands and want the '
     'music to be at its best, Crete gives you more to work with.']),
   ('Rhodes', 'rhodes',
    ['The medieval old town has stone buildings and courtyards that behave acoustically, which is rare '
     'in Greece and worth seeking out. Resort ceremonies on the coast are the more common format and are '
     'the standard outdoor case.']),
   ('Zakynthos', 'zakynthos',
    ['Predominantly resort and hotel weddings at the more economical end of the Greek market. Worth '
     'being straightforward: for a package-priced wedding here, flying a consort from London will look '
     'out of proportion to the rest of the day. Where the wedding is a villa event at the top end, it '
     'works as well as anywhere in Greece.']),
  ],
  [
   ('Can you sing at a Greek Orthodox wedding?',
    'Not within the service itself, and we would advise against trying. An Orthodox wedding is chanted '
    'by a cantor in a tradition that has no gaps for a visiting Western choir, and inserting one would '
    'sit badly with the rite and with the priest. What works is singing around it: as guests arrive '
    'beforehand, or at the reception afterwards, where a consort has plenty to do.'),
   ('What if our ceremony is symbolic rather than religious?',
    'Then the music is completely open, and most British couples marrying in Greece are in exactly this '
    'position. With no liturgy to work around, we would suggest three or four deliberate moments rather '
    'than a continuous programme, and repertoire chosen purely because you like it.'),
   ('Will the wind be a problem on a clifftop?',
    'It can be, and it is the thing couples underestimate most about the Cyclades. We plan around it: '
    'more voices than the guest count alone would need, the consort positioned upwind of the guests, and '
    'a programme that favours pieces with body over the most delicate ones. Tell us where the ceremony '
    'will be and we will tell you what we would do.'),
   ('How much of the cost is accommodation?',
    'On Santorini and Mykonos in July and August, more than most couples expect &mdash; enough that it '
    'is worth discussing before you settle the date. Rooms for twelve to twenty-four people on those '
    'islands in high season are a material part of the quote. Crete and Rhodes are considerably easier '
    'on that front.'),
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
   ('The rite', 'Civil ceremonies, hotel weddings and the Orthodox question',
    ['Cyprus is one of the simplest places for a British couple to marry legally, which is why so many '
     'do. The great majority of those weddings are civil ceremonies conducted by a municipality &mdash; '
     'Paphos town hall being the best known &mdash; or celebrant-led ceremonies at a hotel or villa. '
     'Neither has a liturgy, so the music is entirely yours to place.',
     'The Greek Orthodox position in Cyprus is the same as in Greece: the service is chanted in its own '
     'tradition and has no natural place for a visiting Western choir. If your ceremony is Orthodox, the '
     'sensible use of a consort is before or after rather than during.',
     'There is also a long-standing Anglican presence on the island, and a small number of couples marry '
     'in an Anglican church there. That service is the one most British couples would recognise, with '
     'hymns the congregation can actually sing, and it suits a consort better than any other option in '
     'Cyprus.']),
   ('Being straight about cost', 'Whether this suits your wedding',
    ['Cyprus deserves a franker paragraph than most destinations, because the island serves two very '
     'different markets and we would rather say so than take an enquiry we cannot serve well.',
     'A large part of the Cyprus wedding business is package-priced: a hotel handles the ceremony, the '
     'flowers, the photography and the meal for a figure that, for many couples, is less than the cost '
     'of flying twelve professional singers from London and putting them up for two nights. If that is '
     'the shape of your day, a consort will be out of proportion to it, and a soloist or a small group '
     'of four is the honest recommendation rather than a choir.',
     'At the other end, villa weddings in the Paphos hills and private events on the east coast run at a '
     'scale where a consort fits naturally. If you are in that range, everything below applies. If you '
     'are not, tell us your budget in the form and we will say plainly whether we are the right answer.']),
   ('Buildings', 'Terraces, town halls and a good deal of stone',
    ['Municipal ceremony rooms are small, dry and unglamorous acoustically; the music tends to work '
     'better just outside them, as guests gather, than inside during a ten-minute ceremony.',
     'Hotel and villa ceremonies are outdoors, and the standard outdoor rules apply: no reverberation, '
     'a coastal breeze, and a recommendation of twelve voices where a church would want eight. Cyprus '
     'is hot late into the season, and an afternoon ceremony in August needs shade for the singers '
     'arranged in advance.',
     'The island does have stone worth singing in &mdash; monastery churches inland and the older '
     'buildings in Paphos among them. Where a venue offers an indoor or courtyard option, it is usually '
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
    ['Predominantly package and hotel weddings, and the part of the island where the honest cost '
     'conversation above matters most. A soloist or a group of four often serves this format better than '
     'a full consort, and we would rather propose that than oversell.']),
  ],
  [
   ('Is a choir worth it for a Cyprus wedding?',
    'It depends entirely which Cyprus wedding you are having. For a villa event in the Paphos hills at '
    'the upper end of the market, yes. For a hotel package where the whole day costs less than flying a '
    'consort out, no &mdash; and we would suggest a soloist or a group of four instead. Tell us your '
    'budget and we will give you a straight answer rather than a quote.'),
   ('Can you sing at a Cypriot civil ceremony?',
    'Yes. Civil and celebrant-led ceremonies have no liturgy, so the music is entirely open. Municipal '
    'ceremony rooms are small and acoustically flat, so we often suggest placing the singing outside as '
    'guests gather, and around the ceremony rather than inside a ten-minute formality.'),
   ('What about a Greek Orthodox ceremony in Cyprus?',
    'The same as in Greece: the service is chanted by a cantor in a tradition with no room for a '
    'visiting Western choir, and we would not propose singing during it. Before the service, or at the '
    'reception afterwards, a consort works well.'),
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
     'awkward elsewhere &mdash; no building, no liturgy, a language barrier, a dry outdoor acoustic '
     '&mdash; simply does not apply here.']),
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
     'Catholic church and suits these buildings completely.',
     'Because English is an official language, this is the one Mediterranean destination where you can '
     'reasonably expect the congregation to sing a hymn. If you want that &mdash; and a congregation '
     'singing in a Maltese church is a considerable sound &mdash; choose something well known and let '
     'us lead it. Our guide to <a href="/music-guides/choosing-wedding-hymns.html">choosing wedding '
     'hymns</a> applies here almost unchanged.']),
   ('Buildings', 'Stone, height and a great deal of reverberation',
    ['Maltese limestone churches are reverberant, sometimes strikingly so, with tails long enough that '
     'tempo becomes the main musical decision. Polyphony sounds magnificent; anything fast turns to mud. '
     'We plan Maltese programmes slower than we would at home, and we use the building rather than '
     'fighting it.',
     'The size of these churches means the number of singers is driven by the room rather than the guest '
     'count. A large parish church or the co-cathedral scale of building wants sixteen voices to feel '
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
    ['Quieter, greener, and with parish churches out of all proportion to the size of their villages '
     '&mdash; which is excellent news acoustically. The ferry crossing means building an extra hour into '
     'the schedule each way, and we would generally arrive the day before rather than the morning of.']),
  ],
  [
   ('Why is Malta better for a choir than Italy or Spain?',
    'Three reasons that stack. The churches are baroque, stone and tall, which is the acoustic this '
    'repertoire assumes. English is an official language, so nothing is lost in translation and your '
    'guests can actually sing a hymn. And a nuptial Mass with a sung ordinary is the normal form of '
    'service rather than something to request. Elsewhere you get one or two of those; Malta gives you all three.'),
   ('Will the church have its own organist?',
    'Often, yes, and that is a good thing rather than a complication. An organ in a Maltese church is '
    'worth using, and we plan programmes that give a house organist a real part rather than working '
    'around them. Tell us early what the parish expects.'),
   ('How many singers for a Maltese church?',
    'Driven by the building more than the guest list. A large parish church wants sixteen voices to feel '
    'right even with eighty guests, because the room is enormous. A small chapel in Mdina or a village '
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
     'than like a terrace. A consort of eight in a Dubrovnik cloister sounds substantially better than '
     'the same eight on a hotel lawn anywhere else on this list.',
     'The churches themselves are stone-vaulted and generous, and eight to twelve voices covers almost '
     'anything. Where a ceremony is genuinely open-air &mdash; a clifftop on Hvar, a vineyard in Istria '
     '&mdash; the usual outdoor rules return and we would recommend twelve.']),
   ('Travel', 'Getting a consort to Croatia, and the island question',
    ['Dubrovnik, Split and Zagreb are served directly from London through the season, and Pula for '
     'Istria. The mainland is straightforward.',
     'The islands are the complication, and it is worth planning for properly. Hvar and the other Adriatic '
     'islands are reached by ferry or catamaran from Split, on schedules that thin out sharply outside '
     'summer and can be disrupted by weather. Moving twelve to twenty-four people plus luggage across a '
     'ferry connection on the morning of a wedding is a risk we will not take, so for island weddings we '
     'arrive two days early rather than one. That is a second night in the quote, and it is not '
     'negotiable &mdash; it is the difference between a choir at your wedding and a choir on a quayside.',
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
     'easy airport. Split is also the ferry port for the islands, so a wedding here avoids the crossing '
     'entirely &mdash; the simplest choice in Dalmatia for a group this size.']),
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
    'Considerably, and it is the main reason Croatia punches above its weight musically. Enclosed stone '
    'returns sound the way a church does, so eight voices in a Dubrovnik cloister carries and blooms '
    'where the same eight on an open lawn would sound thin. If your venue offers both, we would push you '
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
