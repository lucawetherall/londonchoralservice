#!/usr/bin/env python3
"""Italy, France, Spain, Portugal."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_country_pages import build

n = build('italy', 'Italy',
  'A Wedding Choir in Italy &mdash; Tuscany, Como, Amalfi | Alma Consort',
  'A British consort singing at Italian weddings: the nuptial Mass, what many parishes allow and '
  'refuse, Latin and Italian, and the acoustics of a Tuscan pieve.',
  'Italy gives a choir the building it was written for.',
  'Alma Consort flies from London to sing nuptial Masses and blessings in Tuscany, on the Amalfi Coast, '
  'at Lake Como, in Puglia and in Florence.',
  [
   ('The Mass', 'If you are having a nuptial Mass',
    ['A Mass is the most rewarding shape a choir can be asked to fill, and if it is the route you are '
     'taking it is worth understanding what it gives you. There is an entrance, a Kyrie and Gloria, a responsorial '
     'psalm and Gospel acclamation, the exchange of consent, an offertory, the Sanctus and Agnus Dei '
     'around the Eucharistic Prayer, communion motets, and a recessional. That is eight or nine points '
     'where music belongs, against three or four at a civil ceremony.',
     'A wedding without a Mass, a nuptial liturgy with the rite of marriage but no Eucharist, is common where one partner is not Catholic, and shortens the middle of the service without '
     'changing its shape.',
     'One practical point worth raising early with your parish: many Italian churches take a firmer '
     'line than English ones on what may be sung inside them. Requests for the Wagner and Mendelssohn '
     'wedding marches, and for secular songs during the service, are refused often enough that it is '
     'worth asking your priest before you plan around them. Sacred repertoire is never the problem, '
     'and there is a great deal of it. If your church says no to a piece you had set your heart on, '
     'tell us and we will suggest something that does the same job liturgically.']),
   ('Language', 'Latin, Italian, and a congregation split in two',
    ['The readings and the spoken rite will be in Italian, and if your guests are mostly British that '
     'is a large part of the service they will not follow. The sung parts are where we can even it out.',
     'Our usual recommendation is to sing the ordinary &mdash; Kyrie, Gloria, Sanctus, Agnus Dei &mdash; '
     'in Latin. Latin belongs to neither side of the aisle, it is what the building was designed around, '
     'and Italian guests recognise it as readily as the setting recognises them. Motets can then run in '
     'both directions: a Palestrina or Victoria at communion, and something unmistakably English '
     '&mdash; a Stanford, a Howells, an arrangement of a hymn your family knows &mdash; where the '
     'service opens out.',
     'Where a bilingual couple wants the congregation to sing rather than listen, we usually pick one '
     'hymn everybody can manage and print the words in both languages.']),
   ('Buildings', 'What Italian churches do to a consort',
    ['An Italian stone church is close to the acoustic English choral music assumes. A Romanesque pieve '
     'with a barrel-vaulted nave will carry eight voices to the back without help, and the two- or '
     'three-second reverberation flatters polyphony written for exactly that. In these buildings you '
     'generally need fewer singers than you would expect, not more.',
     'The exceptions are worth knowing. A small chapel in a villa garden has no reverberation at all '
     'and wants more voices to feel full. A baroque church with heavy drapes and side chapels can '
     'swallow sound. And an outdoor ceremony on a terrace gives nothing back, which is the single most '
     'common reason we recommend twelve voices where a couple had imagined eight.']),
   ('Travel', 'Getting a consort to Italy',
    ['Italy is the most straightforward destination we sing in. Flights from London to Pisa, Florence, '
     'Naples, Milan and Bari run several times a day, and the consort can fly out on the Friday, '
     'rehearse in the church on the Friday evening or Saturday morning, and sing that afternoon.',
     'As British musicians travelling into the Schengen area we work within the '
     'ninety-days-in-any-one-hundred-and-eighty limit and carry the social-security paperwork that '
     'applies to a short professional engagement. We handle that ourselves; it has never yet stopped '
     'a booking, and it is not something you need to manage. What we do ask is time: flights and rooms '
     'for twelve to twenty-four people on a summer Saturday in Tuscany or Amalfi need booking well '
     'before the venue would otherwise chase you.',
     'A foreign couple marrying in Italy will also have their own paperwork &mdash; a <em>nulla osta</em> '
     'and, for a church wedding, permissions routed through your home parish. Your planner or the '
     'church will lead on that. It affects our diary only in one way: start early.']),
  ],
  [
   ('Tuscany', 'tuscany',
    ['The reason most couples ask. A country pieve outside Siena or in the Val d&rsquo;Orcia gives you '
     'stone, a barrel vault and near-perfect conditions for Renaissance polyphony, and a consort of '
     'eight will fill it comfortably. Reception venues here are usually a drive from the church, which '
     'matters for planning: if you want us to sing again during drinks, build the transfer into the '
     'running order.']),
   ('The Amalfi Coast', 'amalfi-coast',
    ['Cliffside churches with vertical approaches and, often, no vehicle access to the door. Ravello and '
     'Positano both work well musically, the churches are stone and generous, but tell us early if the singers face a long stair climb in August heat, because that belongs in the schedule '
     'rather than in the surprise. Terraces here are spectacular and acoustically dead; plan voices '
     'accordingly.']),
   ('Lake Como', 'lake-como',
    ['A villa wedding on Como is usually a symbolic or civil ceremony in a garden or a loggia rather '
     'than a Mass, so the music sits differently: an entrance, something during the vows, and a set '
     'during the aperitivo. Several villas have small private chapels, which are lovely and small. Eight voices is often the maximum the space physically allows, and it is enough.']),
   ('Puglia', 'puglia',
    ['Masserie and baroque town churches. Lecce and the surrounding towns have some of the most '
     'flattering interiors in Italy for a choir. Bari and Brindisi are the airports; both add a drive, '
     'which is worth factoring into a Friday arrival.']),
   ('Florence', 'florence',
    ['City churches, short transfers, and the easiest logistics in Italy for a group this size. The '
     'trade-off is that central Florentine churches are heavily booked and often stricter about music '
     'than a country parish. Ask what is permitted before the programme is settled rather than after.']),
  ],
  [
   ('Can we have a choir at a Catholic wedding in Italy?',
    'Yes, and the nuptial Mass is the service that gives a choir most to do. What varies is the '
    'repertoire the parish will allow. Sacred music is never an issue; secular pieces and the two famous '
    'wedding marches are refused by some churches. Ask your priest early, and tell us what comes back. There is always a sacred piece that does the same job in the same place.'),
   ('Should the Mass be sung in Latin or Italian?',
    'We usually suggest Latin for the sung ordinary. It is neutral between a British and an Italian '
    'congregation, it suits the buildings, and it is what most of the repertoire was written for. The '
    'readings and spoken rite stay in Italian, and we can add an English motet where you want the '
    'service to feel like yours rather than a translation.'),
   ('How many singers do we need for a Tuscan church?',
    'Fewer than you would need at home in a drier room. A stone church with a vaulted nave does half the work: eight voices fill it, and twelve is enough for a substantial parish church. An outdoor ceremony or a garden chapel is the opposite case and wants '
    'more voices, not fewer. Send us a photograph of the space and we will tell you.'),
   ('How far ahead should we book for an Italian wedding?',
    'Nine to twelve months for a summer Saturday. The constraint is rarely the singers&rsquo; diaries; it '
    'is flights and accommodation for twelve to twenty-four people in Tuscany or on the Amalfi Coast in '
    'high season. A date closer than that is still worth asking about, particularly outside July and August.'),
  ])
print(f'italy {n}')

n = build('france', 'France',
  'A Wedding Choir in France &mdash; Provence, Loire, Riviera | Alma Consort',
  'A British consort singing at French weddings: why there are two ceremonies, where the music '
  'actually goes, and what a ch&acirc;teau terrace does to eight voices.',
  'In France the music belongs to the second ceremony.',
  'Alma Consort travels from London to sing church blessings, ch&acirc;teau ceremonies and reception sets '
  'in Provence, the Loire, the Dordogne and on the C&ocirc;te d&rsquo;Azur.',
  [
   ('The rite', 'Two ceremonies, and only one of them has music',
    ['France separates the legal wedding from the religious or celebrant-led one, and this catches out '
     'more British couples than any other single fact about marrying there. The marriage itself happens '
     'at the <em>mairie</em>, conducted by the mayor or a deputy. It is short, it is in French, it is '
     'administrative in tone, and there is generally no place in it for a choir.',
     'The ceremony your guests will remember is the one that follows: a Catholic or Protestant blessing '
     'in a church, or a celebrant-led ceremony in a ch&acirc;teau garden. That is where the music goes, '
     'and because it carries no legal weight you can shape it around what you want. In practice '
     'this is a gift. A blessing has no fixed liturgy to work around, so an entrance, two or three pieces '
     'across the vows and readings, and a recessional can be placed wherever they land best.',
     'Where the church ceremony is a full Catholic nuptial Mass, the shape is the same as it would be in '
     'Italy or Spain, with a sung ordinary and communion motets. Ask your parish which form of service '
     'you are having; the answer changes the programme.']),
   ('Language', 'French, Latin, and what your guests will follow',
    ['A church blessing in France will be conducted in French, sometimes with English readings where the '
     'celebrant is willing. For the sung music we generally set the ordinary in Latin and place at least one French piece in the programme. Fauré, Duruflé, Poulenc and Messiaen all wrote music that belongs in these buildings and signals to French guests that the day is theirs too.',
     'A celebrant-led ceremony at a ch&acirc;teau is usually in English if the couple is British, and '
     'then the choice is open. We are happy to sing in either language or both, and there is no need to '
     'balance them for the sake of it.']),
   ('Buildings', 'Churches, ch&acirc;teaux and the terrace problem',
    ['French parish churches are stone, cool and generous, and a consort of eight to twelve sounds '
     'substantial in almost any of them. Village churches in the Dordogne and Provence are often small '
     'enough that eight voices is plenty and sixteen would be too much.',
     'The ch&acirc;teau ceremony is a different problem. A ceremony on a gravel terrace or a lawn has no '
     'acoustic at all: nothing comes back, the voices carry only as far as they are thrown, and a group '
     'that filled a church sounds thin outdoors. Our recommendation for an outdoor ch&acirc;teau ceremony '
     'is usually twelve voices minimum, and to place the singers closer to the guests than instinct '
     'suggests. A stone orangery, a chapel or a vaulted salle des gardes is the best of both worlds and '
     'worth asking your venue about.']),
   ('Travel', 'Getting a consort to France',
    ['The easiest destination in Europe for a group this size, and the only one we can reach without '
     'flying. For Normandy, the Loire and Burgundy the Eurostar and a coach transfer often works better '
     'than an airport, which removes baggage limits and the risk of a delayed connection scattering '
     'the consort. For Provence, the Riviera and the Dordogne we fly to Nice, Marseille, Bordeaux or '
     'Bergerac.',
     'Post-Brexit we travel as British musicians into the Schengen area, working within the '
     'ninety-days-in-any-one-hundred-and-eighty limit and carrying the paperwork a short professional '
     'engagement requires. We manage that ourselves. France is well used to visiting performers and it '
     'has not been an obstacle.']),
  ],
  [
   ('Provence', 'provence',
    ['Village churches with good stone and short transfers, and some of the best small ceremony spaces '
     'in France. The summer heat is the practical constraint: a four o&rsquo;clock ceremony outdoors in '
     'August is hard on voices, and shade for the singers is worth arranging in advance rather than '
     'improvising. Nice and Marseille are both easy arrivals.']),
   ('The C&ocirc;te d&rsquo;Azur', 'french-riviera',
    ['Hotel and villa weddings, mostly celebrant-led, mostly outdoors, and mostly at the more expensive '
     'end of everything. Acoustically this is the least helpful part of France, and the programme should '
     'be planned around that rather than in spite of it: fewer, stronger pieces, sung closer in, with '
     'twelve voices rather than eight. Nice airport makes the travel simple.']),
   ('The Loire Valley', 'loire-valley',
    ['Ch&acirc;teau country, and the region where you are most likely to find a stone room worth singing '
     'in. Several ch&acirc;teaux have chapels or vaulted halls that turn a good programme into a memorable '
     'one. Reachable by Eurostar and coach, which we generally prefer for this region.']),
   ('The Dordogne', 'dordogne',
    ['Small honey-coloured village churches, often with a modest capacity and a fine acoustic, and a '
     'high proportion of British couples who have a house or family nearby. Bergerac is the convenient '
     'airport. Eight voices is usually the right answer here.']),
  ],
  [
   ('Do we need a choir at the mairie as well as the church?',
    'No, and in most cases you could not have one if you wanted. The civil ceremony at the mairie is '
    'short, administrative and rarely accommodates music. Everything we do belongs to the religious or '
    'celebrant-led ceremony that follows, which is also the one your guests will treat as the wedding.'),
   ('Can you sing at a ch&acirc;teau ceremony rather than in a church?',
    'Yes, and it is a large part of what we do in France. The main thing to plan for is the acoustic: '
    'an outdoor ceremony gives nothing back, so we usually recommend more voices than the same ceremony '
    'would need indoors, and placing the consort nearer you. If the ch&acirc;teau has a chapel, an '
    'orangery or a vaulted hall, ask about using it for the ceremony itself.'),
   ('Will the music be in French?',
    'Some of it, if you want it to be. We usually sing the ordinary in Latin and include at least one French piece. Fauré and Duruflé sit beautifully in these buildings. For a celebrant-led '
    'ceremony in English the choice is yours, and there is no obligation to balance the languages.'),
   ('Is it cheaper because France is close?',
    'Yes, meaningfully. Distance and nights are two of the three things that move the cost, and northern '
    'and central France can often be reached by train with a single night away rather than two. It is the '
    'least expensive place we travel to, and for the Loire and Normandy the gap against a UK engagement is '
    'smaller than most couples expect.'),
  ])
print(f'france {n}')

n = build('spain', 'Spain',
  'A Wedding Choir in Spain &mdash; Ibiza, Mallorca, Marbella | Alma Consort',
  'A British consort singing at Spanish weddings: the nuptial Mass on the mainland, villa ceremonies '
  'in the Balearics, and what changes between the two.',
  'Two countries, musically: the mainland church and the island villa.',
  'Alma Consort travels from London to sing nuptial Masses, blessings and villa ceremonies in Mallorca, '
  'Ibiza, Marbella and Tenerife.',
  [
   ('The music', 'What each route asks of a choir',
    ['The choice you make changes the music more than the venue does.',
     'A Catholic nuptial Mass on the mainland or in a Mallorcan town church is the full liturgical shape: '
     'sung ordinary, psalm, acclamation, offertory, communion motets, recessional. Spanish parishes are '
     'generally welcoming to a visiting choir and used to sung Masses. If your ceremony is a Mass, you '
     'have the richest possible canvas and we would encourage you to use it.',
     'A villa or hotel ceremony in Ibiza, Mallorca or Marbella is usually symbolic or celebrant-led, '
     'with no liturgy at all. There the music does structural work instead: it marks the entrance, it '
     'covers the moment before the vows, it lifts the exit, and it gives the drinks that follow a shape. '
     'Three or four pieces well placed beat eight scattered.',
     'A civil ceremony at a Spanish <em>ayuntamiento</em> is brief and, like the French mairie, is not '
     'usually where music belongs.']),
   ('Language', 'Latin, Spanish and the guests in the middle',
    ['A Spanish nuptial Mass will be spoken in Spanish, and often in Catalan in Mallorca and parts of '
     'the mainland. We sing the ordinary in Latin for the same reason we do in Italy: it is neutral, '
     'and it is what the buildings and the repertoire assume.',
     'Spanish sacred music is worth using rather than ignoring. Victoria and Guerrero wrote some of the finest Renaissance polyphony in Europe, and singing a Victoria motet in a Spanish church is not a gesture. It is the right piece in the right place. For an island ceremony in English, none '
     'of this applies and you should choose whatever you like.']),
   ('Buildings', 'Stone churches and stone terraces',
    ['Mainland and Mallorcan town churches are large, stone and reverberant, and a consort of twelve '
     'will fill one without effort. Cathedral-scale buildings in Seville, Palma or Marbella&rsquo;s old '
     'town want sixteen if you have a full congregation.',
     'Island villa ceremonies are the opposite. An open terrace above the sea has no reverberation and, '
     'frequently, a sea breeze that carries sound away from the guests rather than towards them. Twelve '
     'voices is our usual recommendation outdoors, placed close, and we will say so even where eight '
     'would have been ample indoors.']),
   ('Travel', 'Getting a consort to Spain',
    ['Excellent flight connections from London to Palma, Ibiza, M&aacute;laga and Tenerife, several times '
     'a day in season. Island weddings in July and August are the one case where accommodation, rather '
     'than flights, is the binding constraint: rooms for twelve to twenty-four people in Ibiza in August '
     'need booking a long way out.',
     'We travel as British musicians into the Schengen area and handle the associated paperwork and the '
     'ninety-day limit ourselves. Spain sees a great many visiting performers and this has not been an '
     'obstacle.']),
  ],
  [
   ('Mallorca', 'mallorca',
    ['The best of both cases. Palma and the inland towns have serious stone churches with real acoustics, '
     'while the coast and the Tramuntana offer villa and finca ceremonies outdoors. If you have any '
     'appetite for a church ceremony, Mallorca is where a consort earns its fare.']),
   ('Ibiza', 'ibiza',
    ['Villa and finca ceremonies, almost without exception, symbolic rather than liturgical, usually outdoors at '
     'the end of the afternoon. Plan for a dry acoustic and a breeze. Ibiza also has the highest '
     'concentration of couples who want the consort to sing again during drinks, which works well and '
     'should be agreed in advance so the singers are not standing in the sun for three hours.']),
   ('Marbella', 'marbella',
    ['A mixture: hotel ceremonies on the coast, and churches in the old town and in Ronda inland. Málaga '
     'airport makes this the easiest mainland arrival in southern Spain. Where a church is available it '
     'is generally the better room by a wide margin.']),
   ('Tenerife', 'tenerife',
    ['Hotel and resort ceremonies, with year-round sun and a slightly longer flight than the mainland. '
     'The island has churches in La Laguna and the older towns that are well worth singing in if a church '
     'ceremony is an option for you. Where the wedding stays at one resort, this is a good place to have '
     'us sing across the day rather than at the ceremony alone.']),
  ],
  [
   ('Can a British choir sing at a Catholic wedding in Spain?',
    'Yes. Spanish parishes are generally used to sung Masses and welcoming to visiting singers. Confirm with the church that a visiting choir is acceptable and whether they expect their own organist to be involved, and tell us either way. We are glad to work alongside a house organist.'),
   ('What music suits a villa ceremony in Ibiza or Mallorca?',
    'Fewer pieces, placed deliberately. An entrance, one piece during the signing or the vows, and a '
    'recessional will do more than a long list. Because there is no liturgy, the repertoire is open: unaccompanied part-songs, folk arrangements, and choral versions of songs that matter to you '
    'all work, and we will arrange something for the consort if no choral setting exists.'),
   ('Do we need more singers for an outdoor ceremony?',
    'Usually yes. An open terrace returns no sound and a coastal breeze carries it away from the guests. '
    'Where a stone church would be well served by eight voices, the same ceremony outdoors is better '
    'with twelve. Send us a photograph of where the ceremony will happen and we will give you a straight '
    'recommendation rather than the largest number.'),
   ('Will you sing in Spanish?',
    'We sing the Latin ordinary at a Mass, and we sing Spanish repertoire, Victoria and Guerrero especially, which in a Spanish church is the natural rather than the decorative choice. For '
    'an English-language ceremony on the islands there is no need for Spanish at all unless you want it.'),
  ])
print(f'spain {n}')

n = build('portugal', 'Portugal',
  'A Wedding Choir in Portugal &mdash; Algarve, Sintra, Lisbon | Alma Consort',
  'A British consort singing at Portuguese weddings: quinta ceremonies in the Algarve, palace '
  'weddings at Sintra, and city churches in Lisbon and Porto.',
  'Portugal is the short flight that still feels a long way from home.',
  'Alma Consort travels from London to sing at quintas in the Algarve, palaces and estates around '
  'Sintra, and churches in Lisbon and Porto.',
  [
   ('The rite', 'Masses, blessings and quinta ceremonies',
    ['Portugal is strongly Catholic, and a nuptial Mass in a Portuguese church gives a consort the full '
     'liturgical shape: a sung ordinary, psalm and acclamation, offertory, communion, recessional. '
     'Portuguese parishes are used to music and, in our experience, generous about a visiting choir.',
     'Most British couples marrying in Portugal, though, are at a quinta, a palace or a hotel rather '
     'than in a parish church, with a celebrant-led or symbolic ceremony. That format has no liturgy, so '
     'the music defines the structure instead. Portugal is also unusual in how often the ceremony space and the reception space are the same estate, which makes it easy to have the consort sing again during drinks without a transfer. Worth planning for, because it is the cheapest way to get more out of a group that has already flown out.']),
   ('Language', 'Portuguese, Latin and what to sing',
    ['A church service will be in Portuguese. As elsewhere we would sing the ordinary in Latin, which '
     'sits naturally in these buildings and needs no translation for either half of a mixed congregation.',
     'Where a couple wants something local rather than generic, Portuguese sacred polyphony &mdash; '
     'Cardoso, Lobo, Melgás &mdash; is a real and underused repertoire, and singing it in a Portuguese '
     'church tends to land with local guests in a way an international programme does not. For an '
     'English-language ceremony at a quinta, none of this is necessary and the programme is yours.']),
   ('Buildings', 'Azulejo churches, palace rooms and open lawns',
    ['Portuguese churches are stone and often tiled, and tile is acoustically hard: many of these '
     'buildings are brighter and more reverberant than their English equivalents. That flatters '
     'polyphony and punishes anything sung too fast. Eight voices goes a long way in a tiled church.',
     'The Sintra palaces and estates offer some of the finest interior rooms in Portugal, and if you have the '
     'option of an indoor ceremony there we would take it. The Algarve is the opposite: quinta '
     'ceremonies are outdoors on lawns or terraces with no reverberation, and want twelve voices where '
     'a church would have been content with eight.']),
   ('Travel', 'Getting a consort to Portugal',
    ['Faro, Lisbon and Porto are all served several times daily from London, and the flight is short '
     'enough that the consort can travel out on the Friday without a wasted day. Along with France and '
     'Spain, Portugal is at the affordable end of what we do.',
     'We travel as British musicians into the Schengen area and handle the paperwork and the ninety-day '
     'limit ourselves. The Algarve in high summer is the one place where accommodation for a group of '
     'this size wants booking early; outside July and August it is straightforward.']),
  ],
  [
   ('The Algarve', 'the-algarve',
    ['Quintas, hotels and beach clubs, ceremonies almost always outdoors, and the largest concentration '
     'of British couples in Portugal. Faro is a short transfer from most venues. Plan for a dry acoustic '
     'and, in July and August, for heat late in the afternoon; shade for the singers belongs in the '
     'running order.']),
   ('Sintra', 'sintra',
    ['Palaces and estates in the hills, and the best rooms in Portugal for a consort. Where an indoor '
     'ceremony is possible here, take it: several of these spaces have the stone and the height that '
     'make eight voices sound like sixteen. Close to Lisbon, so the travel is simple.']),
   ('Lisbon', 'lisbon',
    ['City churches, short transfers and easy logistics. A Lisbon church wedding is among the more '
     'rewarding services we sing: the buildings are generous, the parishes are used to music, and '
     'everything is within a short drive of the airport and the hotels.']),
   ('Porto', 'porto',
    ['Granite churches with a darker, weightier acoustic than Lisbon&rsquo;s, and estates in the Douro '
     'within reach for a ceremony followed by a reception up the valley. The transfer inland is the main '
     'thing to plan around if the ceremony and reception are in different places.']),
  ],
  [
   ('Can you sing at a quinta wedding rather than in a church?',
    'Yes, and it is the majority of what we do in Portugal. Without a liturgy the music carries the '
    'structure, so we would suggest fewer and better-placed pieces: an entrance, one during the vows or '
    'the signing, a recessional, and then a set during drinks if the ceremony and reception share the '
    'estate.'),
   ('Is it worth having us sing during the reception drinks?',
    'In Portugal, more often than anywhere else, yes. Because the ceremony and reception are usually on '
    'the same estate there is no transfer to lose time to, and a consort that has already flown out costs '
    'very little more to keep for another hour. Agree it in advance so the singers are scheduled rather '
    'than standing about in the heat.'),
   ('What is the acoustic like in Portuguese churches?',
    'Bright, and often more reverberant than you would expect, because tiled surfaces reflect sound '
    'rather than absorbing it. That suits polyphony and rewards a slower tempo. Eight voices is usually '
    'plenty in a parish church; an outdoor quinta ceremony wants twelve.'),
   ('How does the cost compare with Italy or Greece?',
    'Portugal is at the more affordable end. The flight is short, the transfers are usually brief, and '
    'one night away is often enough outside high season. Our UK rates are published on the '
    '<a href="/pricing.html">pricing page</a>; a Portuguese engagement adds flights and rooms for the '
    'singers, and we quote the whole thing before you commit.'),
  ])
print(f'portugal {n}')
