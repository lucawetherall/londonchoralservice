#!/usr/bin/env python3
"""Gibraltar, Ireland, Scotland — the three with no permit question."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_country_pages import build

n = build('gibraltar', 'Gibraltar',
  'A Wedding Choir in Gibraltar &mdash; Cathedrals and the Rock | Alma Consort',
  'A British consort at Gibraltar weddings: British law, two cathedrals, English throughout, and no '
  'work permit needed for visiting British musicians.',
  'British law, British paperwork, and a cathedral choir&rsquo;s worth of stone.',
  'Alma Consort travels from London to sing at cathedral, registry and Botanic Gardens ceremonies in '
  'Gibraltar.',
  [
   ('Why Gibraltar', 'The simplest destination on this list',
    ['Gibraltar removes almost every complication that makes a wedding abroad harder to organise than '
     'one at home. It is a British Overseas Territory, so the legal framework is one a British couple '
     'already understands and the ceremony is conducted in English. There is no visa question and no '
     'work-permit question for British musicians, because we are not foreign workers when we arrive.',
     'It also has a long reputation for weddings arranged quickly &mdash; the registry has married a '
     'good number of people on short notice, including at least one Beatle &mdash; and that reputation '
     'is deserved. If your timescale is short, Gibraltar is the destination most likely to accommodate '
     'it, ours included: with no permits to arrange, our lead time here is closer to a UK booking than '
     'to a European one.']),
   ('The rite', 'Cathedral, church or registry',
    ['Three formats, and they ask different things of a choir.',
     'The Catholic Cathedral of St Mary the Crowned and the Anglican Cathedral of the Holy Trinity both '
     'sit in the centre of town, and either gives a consort a proper building and a proper service. An '
     'Anglican wedding here is the one on this whole site that will feel most like a wedding at home: '
     'hymns your guests know and can sing, a familiar order of service, and an English-speaking '
     'congregation. A Catholic nuptial Mass at St Mary&rsquo;s gives the fuller sung shape, with the '
     'ordinary in Latin.',
     'A registry ceremony is short and administrative, and the music generally works better around it '
     '&mdash; as guests gather, or at the reception &mdash; than inside a ten-minute formality. Ceremonies '
     'at the Botanic Gardens are outdoors and celebrant-led, with no liturgy and an open programme.']),
   ('Buildings', 'Cathedral stone and an open garden',
    ['Both cathedrals are stone and generous, and either supports a consort of twelve comfortably; '
     'sixteen if you want the building to feel full. These are the best rooms available to a wedding in '
     'Gibraltar by a wide margin, and if you are choosing between a cathedral and an outdoor venue on '
     'musical grounds, the cathedral wins easily.',
     'The Botanic Gardens are an open-air venue and behave like one: no reverberation, some wind coming '
     'off the Strait, and a recommendation of twelve voices placed close to the guests. The Rock itself '
     'creates its own weather, and an exposed spot can be breezier than the town below.']),
   ('Travel', 'Getting a consort to Gibraltar',
    ['Direct flights from London run daily, at around three hours, and the airport is a walk from the town centre. The shortest transfer of any destination we sing at. The territory is small '
     'enough that everything is within a few minutes of everything else, which removes the usual risk '
     'of a long drive after a delayed flight.',
     'There is no work-permit or visa requirement for British musicians performing here, which is why '
     'Gibraltar is the one destination where a shorter lead time works. Accommodation '
     'for a group of twelve to twenty-four is the main thing to book early, because the territory is '
     'small and has a finite number of rooms.']),
  ],
  [
   ('The Rock and the town', 'the-rock',
    ['Both cathedrals, the registry and most of the hotels sit within a few streets of each other in the '
     'town below the Rock. For a group of singers this is close to ideal: no transfers to schedule, no '
     'traffic to allow for, and the ability to rehearse in the building the afternoon before without '
     'losing half a day to travel.']),
   ('The Botanic Gardens', 'botanical-gardens',
    ['The Alameda gardens are the outdoor option, and a lovely one, with the Rock above and the Strait '
     'beyond. Acoustically it is an open-air venue like any other: plan for twelve voices, a dry sound '
     'and some wind. Worth pairing with a cathedral ceremony earlier in the day if you want both the '
     'building and the view.']),
  ],
  [
   ('Do you need a work permit to sing in Gibraltar?',
    'No. Gibraltar is a British Overseas Territory and British musicians performing there are not '
    'foreign workers. That removes the single biggest lead-time constraint that applies elsewhere, and '
    'it is why we can consider Gibraltar dates at notice we could not accept for Europe, let alone the '
    'United States.'),
   ('Which is better for music, a cathedral or the Botanic Gardens?',
    'The cathedral, comfortably. Both of Gibraltar&rsquo;s cathedrals are stone buildings that carry '
    'voices and reward a proper programme; the gardens are an open-air venue with no reverberation and '
    'some wind. If you want both, a cathedral ceremony followed by a garden reception gives you the '
    'building where it matters and the view where it does not.'),
   ('Will our guests be able to sing hymns?',
    'Yes, and Gibraltar is one of the few destinations where that is straightforward. An Anglican '
    'service at Holy Trinity runs in English on an order of service British guests will recognise, and '
    'a congregation singing a familiar hymn in a stone cathedral is worth planning for.'),
   ('How quickly could you come?',
    'Faster than anywhere else on this list. With no permits to arrange, our constraint is the '
    'singers&rsquo; diaries and a flight, which in practice means a date a couple of months out is worth '
    'asking about rather than assuming is impossible. Accommodation is the thing most likely to be the '
    'obstacle, so ask early even for a short-notice wedding.'),
  ])
print(f'gibraltar {n}')

n = build('ireland', 'Ireland',
  'A Wedding Choir in Ireland &mdash; Castles, Churches, Country Houses | Alma Consort',
  'A British consort at Irish weddings: Catholic and Church of Ireland services, castle and country '
  'house ceremonies, and no permits or long-haul cost.',
  'A short hop, a familiar service, and buildings that flatter voices.',
  'Alma Consort travels from London to sing nuptial Masses, Church of Ireland services and castle '
  'ceremonies across Ireland.',
  [
   ('The rite', 'Two familiar traditions',
    ['Ireland is unusually easy for a British couple musically, because both of the main traditions are '
     'ones a visiting English consort already knows how to serve.',
     'A Catholic nuptial Mass gives the full sung shape &mdash; ordinary, psalm, acclamation, offertory, '
     'communion motets, recessional &mdash; and Irish parishes take music seriously. A Church of Ireland '
     'service is Anglican, which means the order of service, the hymnody and the expectations are almost '
     'exactly what they would be in an English parish church. If you have planned a wedding at home and '
     'then moved it to Ireland, very little about the music needs to change.',
     'Civil and celebrant-led ceremonies at castles and country houses are the third common format, with '
     'no liturgy and an open programme. Ireland also permits legally binding ceremonies at approved '
     'venues outside a church, which is why so many weddings here happen at the venue itself.']),
   ('Language', 'English, with Irish where you want it',
    ['Everything runs in English, so nothing is lost and no translation is needed. Where a couple wants '
     'something specifically Irish in the service, there is a real repertoire to draw on rather than a '
     'token gesture: Irish hymnody and the older Gaelic melodies arrange beautifully for unaccompanied '
     'voices, and <em>Be Thou My Vision</em> &mdash; an Irish text and an Irish tune &mdash; is one of '
     'the finest hymns available to any wedding. Our guide to '
     '<a href="/music-guides/be-thou-my-vision-wedding-hymn.html">that hymn</a> covers how it works in '
     'a service.']),
   ('Buildings', 'Churches, castles and the big draughty hall',
    ['Irish churches, Catholic and Church of Ireland alike, are generally stone and generous, and eight '
     'to twelve voices covers almost any of them. These are conditions the repertoire assumes and there '
     'is little to plan around.',
     'Castles and country houses are more variable. A vaulted hall or a chapel is excellent. A large timber-floored function room with soft furnishings absorbs a great deal, and an outdoor ceremony in a walled garden gives nothing back at all, and in Ireland an outdoor ceremony needs a wet-weather plan that includes the singers, because moving twelve people indoors at short notice is easier if somebody has thought about where they will stand.']),
   ('Travel', 'The easiest journey we make',
    ['Flights from London to Dublin, Cork, Shannon and Knock run constantly, and the crossing takes '
     'about an hour. Ireland and the United Kingdom share the Common Travel Area, so there is no visa or work-permit question at all for British musicians, the same position as Gibraltar, and unlike anywhere in the Schengen area.',
     'The practical effect is on cost and lead time. Ireland is the least expensive destination on this '
     'list: a short flight, often a single night, and no paperwork. For a wedding within reach of '
     'Dublin, the gap between an Irish engagement and an English one is smaller than most couples '
     'expect. Longer drives to the west coast are the main thing to build into the schedule.']),
  ],
  [
   ('Dublin and the east', 'dublin',
    ['The simplest logistics in Ireland: frequent flights, short transfers and a wide choice of churches '
     'and country houses within an hour of the city. Where a wedding is here, a single night away is '
     'usually enough, which keeps the cost closest to a UK booking.']),
   ('County Wicklow', 'wicklow',
    ['Estates and country houses within easy reach of Dublin, and some of the most-used destination '
     'venues in Ireland. Many have both a chapel or hall and a garden option; the indoor room is almost '
     'always the better one musically, and the weather makes it the safer one too.']),
   ('The south west', 'south-west',
    ['Kerry, Cork and the coast, reached through Cork or Shannon. Castle and country-house weddings '
     'dominate, and the drives are longer, so an early flight and a two-night stay are often the sensible '
     'shape rather than the cautious one.']),
   ('The west', 'the-west',
    ['Galway, Connemara and Mayo, through Knock or Shannon, with the longest transfers in the country and '
     'the most weather. Spectacular, and worth planning with more margin than the east coast needs.']),
  ],
  [
   ('Is Ireland cheaper than the rest of Europe?',
    'Yes, and by a clear margin. The flight is about an hour, one night away is often enough, and there '
    'is no permit paperwork because of the Common Travel Area. For a wedding near Dublin the cost sits '
    'closer to a UK engagement than to an Italian one. Our UK rates are on the '
    '<a href="/pricing.html">pricing page</a> and we quote the whole engagement before you commit.'),
   ('Will a Church of Ireland service feel familiar?',
    'Very. It is an Anglican service, so the order of service, the hymns and the way music sits in it '
    'are close to identical to an English parish wedding. If you have already planned the music for a '
    'wedding at home, almost all of that planning transfers.'),
   ('Can you sing at a castle or country house ceremony?',
    'Yes, and it is a large share of what we do in Ireland, because the law allows legally binding '
    'ceremonies at approved venues rather than requiring a church. Ask your venue whether there is a '
    'chapel or a vaulted room available: it will sound better than a function room by a wide margin, and it '
    'solves the weather problem at the same time.'),
   ('What about rain?',
    'Plan for it, and include the singers in the plan. An outdoor ceremony in Ireland needs an indoor alternative somebody has thought through, including where twelve people stand and '
    'whether the music still works in that room. We will ask about this when we quote; it is easier '
    'settled early than at nine in the morning on the day.'),
  ])
print(f'ireland {n}')

n = build('scotland', 'Scotland',
  'A Wedding Choir in Scotland &mdash; Castles, Highlands, Edinburgh | Alma Consort',
  'A British consort at Scottish weddings: why Scots law allows a legal ceremony anywhere, what that '
  'means for the music, and our published UK rates.',
  'Scotland lets you marry anywhere, which changes where the music goes.',
  'Alma Consort travels from London to sing at castle, Highland and city ceremonies across Scotland, on our published UK rates.',
  [
   ('The law', 'Why Scottish weddings happen in places English ones cannot',
    ['One difference in Scots law explains most of what is distinctive about a Scottish wedding. In '
     'England and Wales a legally binding marriage must take place in a registered building or approved '
     'premises. In Scotland the authority rests with the celebrant rather than the building, so a religious or belief celebrant can conduct a legally binding ceremony almost anywhere: a castle courtyard, a glen, a loch shore, a hotel lawn.',
     'That is why so many Scottish weddings happen somewhere spectacular and nowhere near a church, and '
     'why couples who wanted an outdoor ceremony in England often end up in Scotland instead.',
     'Musically it has one consequence worth planning for: the ceremony is frequently outdoors and '
     'frequently in a place with no acoustic and a good deal of weather. That is a solvable problem, '
     'but it is a different problem from the one a church presents.']),
   ('The rite', 'Church, castle and celebrant',
    ['A Church of Scotland service is Presbyterian in tradition: strong congregational singing, psalmody '
     'with real history behind it, and a plainer shape than an Anglican or Catholic wedding. A Scottish '
     'Episcopal service is Anglican and will feel like an English parish wedding. A Catholic nuptial '
     'Mass gives the full sung liturgical shape.',
     'A celebrant-led ceremony at a castle or in a glen has no liturgy at all, and the music does the '
     'structural work: the entrance, the moment around the vows, the exit, and a set afterwards. Because '
     'the ceremony is legally binding wherever it happens, there is no second service to plan around, '
     'which makes Scotland simpler than France in this respect.']),
   ('Buildings', 'Great halls, chapels and standing in a field',
    ['Scottish castles and country houses often have a chapel or a stone-vaulted hall, and where one is '
     'available it is the best room by a distance. Eight to twelve voices in a vaulted hall sounds '
     'substantial and needs no help.',
     'An outdoor Highland ceremony is the opposite case and deserves plain speaking. There is no '
     'reverberation, wind is close to guaranteed, and a group that sounded full in a chapel will sound '
     'thin on a hillside. We would recommend twelve voices minimum outdoors, positioned upwind and '
     'closer to the guests than looks natural, and a programme built from pieces with body rather than '
     'the most delicate thing we know. A wet-weather plan that says where the singers go is worth '
     'settling when you book rather than on the morning.']),
   ('Cost', 'Scotland is a UK engagement',
    ['Scotland is the one destination on this list that is not abroad, and the difference shows up '
     'directly in what you pay. There are no flights for the whole consort to price, no international '
     'accommodation, no permits and no currency question. Our standard rates apply, and they are '
     'published in full on the <a href="/pricing.html">pricing page</a> &mdash; a soloist from '
     '&pound;250, a choir of eight at &pound;2,000, twelve voices at &pound;3,000, with fees and taxes '
     'included.',
     'What a Scottish booking may add is travel and, for the Highlands and islands, a night&rsquo;s '
     'accommodation, because a group cannot reasonably drive from London and sing the same afternoon. '
     'For Edinburgh and Glasgow that is often unnecessary. We set it out in the quote rather than '
     'leaving you to guess.']),
  ],
  [
   ('Edinburgh and the Lothians', 'edinburgh',
    ['City churches, the Old Town and a strong choral tradition already in the air. The simplest travel in Scotland. The train from London runs directly and a day trip works for an afternoon ceremony, which keeps the cost at its lowest.']),
   ('The Highlands', 'the-highlands',
    ['Castles, glens and lochs, and the setting most couples picture when they choose Scotland. Also the '
     'longest journeys, the most weather and the driest acoustics. Plan for an overnight stay, twelve '
     'voices, and an indoor alternative that has been thought through.']),
   ('Loch Lomond and the Trossachs', 'loch-lomond',
    ['Close enough to Glasgow to keep the travel simple, dramatic enough to feel remote. Several venues '
     'here have both a hall and a lochside option; the hall will sound better, and in Scotland it is also '
     'the one that survives the forecast.']),
   ('Fife and Perthshire', 'fife-perthshire',
    ['Country houses and estates within reach of Edinburgh, with a good proportion of vaulted or '
     'stone-built ceremony rooms. A sensible middle ground between the accessibility of the central belt '
     'and the drama of the Highlands.']),
  ],
  [
   ('Can we have a legally binding ceremony outdoors in Scotland?',
    'Yes, and it is the main reason couples choose Scotland. Scots law attaches the authority to the '
    'celebrant rather than the building, so a religious or belief celebrant can marry you in a castle '
    'courtyard, a glen or beside a loch. Your celebrant will confirm the detail; from our side it means planning for an outdoor acoustic.'),
   ('Do you charge extra because Scotland is far from London?',
    'Our published UK rates apply &mdash; a soloist from &pound;250, eight voices at &pound;2,000, '
    'twelve at &pound;3,000, on the <a href="/pricing.html">pricing page</a>. What a Scottish booking may '
    'add is travel and, for the Highlands and islands, one night&rsquo;s accommodation, because a group '
    'cannot drive from London and sing well the same afternoon. Edinburgh and Glasgow often need neither.'),
   ('How many singers for an outdoor Highland ceremony?',
    'Twelve as a minimum, and we would say so even where eight would have been ample in a chapel. Open '
    'ground returns no sound and the wind takes what there is away from the guests. If the venue has a '
    'vaulted hall or a chapel, using it will get you a better result with fewer singers.'),
   ('What happens if the weather turns?',
    'We plan for it when you book. The question we will ask is where the singers stand if the ceremony moves indoors, and whether the programme still works in that room. A piece written for a stone chapel behaves differently in a marquee. Settling that in advance takes the decision out of '
    'the morning of the wedding.'),
  ])
print(f'scotland {n}')
