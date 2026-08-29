#!/usr/bin/env python3
"""United States, Mexico, Barbados, St Lucia, Jamaica."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_country_pages import build

n = build('united-states', 'United States',
  'A British Wedding Choir in the USA &mdash; The Visa Problem | Alma Consort',
  'A British consort at American weddings: the performance visa that governs the timeline, what it '
  'means for your date, and where the music goes at a US ceremony.',
  'Start with the visa. Everything else follows from it.',
  'Alma Consort travels from London to sing at weddings in New York, Florida and Las Vegas &mdash; on '
  'a timeline set by immigration rather than by aviation.',
  [
   ('The constraint', 'Why the United States is different from everywhere else we sing',
    ['This page leads with paperwork rather than music, because on this one destination the paperwork '
     'decides whether there is any music at all.',
     'Performing for a fee in the United States is not something a British musician can do on a tourist '
     'visa or under the visa waiver programme. It requires a petition-based performance visa, filed in '
     'advance, for the musicians travelling. That process takes months rather than weeks, it costs real '
     'money per engagement, and it cannot be compressed because a wedding date is approaching.',
     'The practical consequence is simple: the visa calendar, not the flight schedule, decides when we '
     'can come. A couple planning a New York wedding eighteen months out has no difficulty at all; one '
     'asking about a date six months away needs us to look at the specific timings before anyone '
     'promises anything. So raise it early &mdash; the earlier this conversation starts, the more of '
     'the calendar is open to you.',
     'Where the timeline does work, everything else about the States is straightforward: excellent '
     'flights, no language barrier, and venues used to handling suppliers professionally.']),
   ('The rite', 'What a US wedding asks of a choir',
    ['American weddings vary more than European ones, because the format follows the couple rather than '
     'the country. An Episcopal service in a New York church is Anglican and will feel entirely familiar '
     '&mdash; hymns the congregation can sing, an order of service a British couple would recognise, and '
     'a building that supports a consort properly. A Catholic nuptial Mass gives the full sung shape.',
     'Most destination weddings in Florida and Nevada, though, are celebrant-led ceremonies at a hotel, '
     'a beach or a garden venue, with no liturgy at all. There the music defines the structure: the '
     'processional, a piece during the ceremony, the recessional, and a set during the cocktail hour '
     'afterwards &mdash; which in the United States is a more established part of the day than it is in '
     'Britain, and a good use of a group that has flown a long way.']),
   ('Buildings', 'East coast stone against Florida sun',
    ['New York and the north east have serious stone churches, and they are among the best rooms we '
     'could sing in anywhere. Where a couple is marrying in one, a consort of twelve to sixteen is '
     'appropriate and the building will do the rest.',
     'Florida and Nevada are the opposite proposition: outdoor ceremonies, hotel lawns, beaches and '
     'poolside terraces, with no reverberation and, in Florida, heat and humidity that affect singers '
     'more than most people expect. Humid air is not kind to a group that has flown overnight. Twelve '
     'voices outdoors, shade before and during, and a ceremony scheduled away from the middle of the '
     'afternoon all make a material difference.']),
   ('Travel', 'Getting a consort to the United States, once the visas exist',
    ['Flights are the easy part: London to New York, Miami, Orlando and Las Vegas are all served many '
     'times daily. The consort would normally travel two days ahead for a transatlantic engagement '
     'rather than one, because singing well the morning after an overnight flight and a five- to '
     'eight-hour time change is not something we would promise.',
     'That second night is in the quote, as is the visa cost. We set both out explicitly rather than '
     'folding them into a single figure, so you can see what you are paying for. A US engagement is the '
     'most expensive thing on this list before a note is sung, and you should know that at the start.']),
  ],
  [
   ('New York City', 'new-york-city',
    ['The best case in the United States for a consort: real churches, real acoustics, and a city where '
     'a group of singers is unremarkable rather than exotic. An Episcopal or Catholic ceremony in a '
     'Manhattan or Brooklyn church gives you everything the repertoire was written for. Transfers are '
     'short and the venues are professional.']),
   ('Florida', 'florida',
    ['Orlando and Miami, and overwhelmingly outdoor or hotel ceremonies. The acoustic is dry and the '
     'climate is the main planning constraint: humidity is hard on voices, and an afternoon ceremony in '
     'summer is harder still. A late-afternoon or evening slot, shade, and twelve voices rather than '
     'eight is the shape that works.']),
   ('Las Vegas', 'las-vegas',
    ['Chapel, hotel and resort ceremonies, with venues as capable as any in the world at running a large '
     'private event and a level of production polish that is hard to find elsewhere. Ceremonies are often '
     'tightly scheduled, so the programme wants to be precise rather than long &mdash; and the reception '
     'that follows is usually where a consort has the most room to work.']),
  ],
  [
   ('Do British musicians need a visa to perform at a US wedding?',
    'Yes. Paid performance in the United States requires a petition-based performance visa; it cannot be '
    'done on the visa waiver programme or a tourist visa. The petition takes months and costs money per '
    'engagement. This is the single most important thing to know about booking a British choir for an '
    'American wedding, and it is why the answer depends on your timeline before it depends on our diary.'),
   ('How far ahead do we need to book?',
    'Considerably further than anywhere else we sing. Where Europe works at six to twelve months, the '
    'States needs the visa timeline built in on top, so the advice is to raise it before you fix the '
    'date rather than after. If your wedding is sooner than that, ask us anyway &mdash; the position '
    'depends on the visa route and on how the calendar is running, and we would rather look at your '
    'specific dates than turn you away on a general rule.'),
   ('Why is a US booking more expensive?',
    'Three things stack: transatlantic flights for the whole consort, two nights rather than one because '
    'we will not sing well the morning after an overnight flight and a large time change, and the visa '
    'cost per engagement. We itemise all three in the quote rather than hiding them in one number, '
    'because you should be able to see what you are paying for.'),
   ('Where does the music go at an American wedding?',
    'It depends entirely on the format. An Episcopal or Catholic church service has the familiar shape '
    'and gives a choir a great deal to do. A celebrant-led ceremony at a hotel or beach has no liturgy, '
    'so the music carries the structure &mdash; processional, a piece within the ceremony, recessional '
    '&mdash; and the cocktail hour afterwards is a natural second set.'),
  ])
print(f'united-states {n}')

n = build('mexico', 'Mexico',
  'A Wedding Choir in Mexico &mdash; Riviera Maya, Tulum, Canc&uacute;n | Alma Consort',
  'A British consort at Mexican weddings: beach and cenote ceremonies, colonial stone churches, and '
  'what tropical heat asks of singers who have flown overnight.',
  'Two Mexicos: the beach at sunset and the colonial church.',
  'Alma Consort travels from London to sing at beach, jungle and church ceremonies in the Riviera Maya, '
  'Tulum and Canc&uacute;n.',
  [
   ('The day', 'Where the music sits, and the buildings worth seeking out',
    ['Without a liturgy to sit inside, the music does the structural work: the processional, a piece at '
     'the exchange of vows, the recessional, and a set during the cocktail hour, which in Mexico is a '
     'well-established part of the day.',
     'If your wedding includes a church ceremony as well as a beach celebration, the church is where a '
     'consort earns its journey. Mexico&rsquo;s colonial churches, particularly inland and in the older '
     'towns, are magnificent buildings and the best acoustics in the country, and we would build the '
     'programme around one.',
     'A cenote ceremony &mdash; in or beside one of the limestone sinkholes of the Yucat&aacute;n &mdash; '
     'is a case worth mentioning on its own. Enclosed rock returns sound the way a chapel does, and a '
     'consort singing in one is a genuinely extraordinary thing. If your venue offers it, ask us about it.']),
   ('Climate', 'What tropical heat does to a choir',
    ['This deserves a section rather than a footnote, because it affects the result more than the '
     'repertoire does.',
     'Singing is physical work, and doing it in thirty-plus degrees with high humidity, after a '
     'ten-hour flight and a six-hour time change, is a different proposition from doing it in a cool '
     'English church. Voices tire faster, the group needs water and shade genuinely rather than '
     'nominally, and heavy formal dress in direct sun is not workable.',
     'None of this is a reason not to do it. It is a reason to plan the ceremony for late afternoon or '
     'early evening rather than the middle of the day, to arrange shade for the singers as a matter of '
     'course, and to arrive two days ahead rather than one. We raise this at the quote stage because it '
     'is easier to build into a running order than to fix on the day.']),
   ('Buildings', 'Sand, jungle, limestone and stone',
    ['A beach ceremony is the driest acoustic there is: open sky, open water, sound going out and never '
     'coming back, and often a breeze off the sea. Twelve voices is the minimum we would recommend, '
     'placed close to the guests and upwind where there is a choice.',
     'Jungle and garden ceremonies are marginally better because of the surrounding vegetation, though '
     'still dry. Cenotes and colonial churches are the two settings in Mexico with real acoustics, and '
     'both flatter a consort considerably.']),
   ('Travel', 'Getting a consort to Mexico',
    ['Canc&uacute;n is served directly from London and is the arrival point for the whole Riviera Maya, '
     'with transfers of up to two hours to the southern resorts and Tulum. The flight is around ten '
     'hours with a six-hour time change, so we travel two days ahead rather than one, and that second '
     'night is in the quote.',
     'Mexico has its own requirements for foreign performers working for a fee, and we handle that '
     'ourselves as part of arranging the engagement. As with everywhere on this list, the position can '
     'change; we confirm the current requirement when we quote rather than relying on what was true last '
     'year.']),
  ],
  [
   ('The Riviera Maya', 'the-riviera-maya',
    ['The main resort corridor south of Canc&uacute;n, and the largest concentration of destination '
     'weddings in Mexico. Beach and garden ceremonies at large resorts, professionally run, with the '
     'standard dry outdoor acoustic. Transfers from the airport can be long, which matters when '
     'scheduling a rehearsal the day before.']),
   ('Tulum', 'tulum',
    ['Jungle and beach venues at the more design-led end of the market, and the best place in Mexico to '
     'find a cenote ceremony. Acoustically the most interesting option in the country: enclosed limestone '
     'behaves like a chapel, and a consort in one sounds like nothing else on this list.']),
   ('Canc&uacute;n', 'cancun',
    ['Large hotel and resort weddings with the shortest transfers, since this is where you land. The '
     'venues are used to elaborate events and to visiting suppliers, which makes the logistics '
     'straightforward even where the acoustics are not.']),
  ],
  [
   ('Can you sing at a beach wedding?',
    'Yes, and it is most of what we do in Mexico. The thing to plan for is that a beach has no acoustic '
    'at all: sound goes out and nothing returns. We would recommend twelve voices rather than eight, '
    'placed closer to the guests than instinct suggests, and a programme of pieces with body rather than '
    'the most delicate ones in the repertoire.'),
   ('What about a cenote ceremony?',
    'Musically, the best thing available in Mexico. Enclosed limestone returns sound the way a chapel '
    'does, so a consort sounds full and resonant rather than thin. If your venue offers a cenote and you '
    'are choosing between that and a beach on musical grounds, take the cenote.'),
   ('Is the heat a problem for the singers?',
    'It is a real factor and we would rather discuss it than pretend otherwise. Singing is physical work, '
    'and doing it in tropical heat and humidity after a long flight is demanding. We plan around it: a '
    'late-afternoon or evening ceremony, shade arranged in advance, water on hand, and arriving two days '
    'early rather than one.'),
   ('How does the cost compare with Europe?',
    'Substantially higher, and it is worth being clear about why. Transatlantic flights for the whole '
    'consort, two nights rather than one because of the flight and the time change, and the local '
    'permissions for foreign performers all add to the figure. We quote the whole engagement itemised '
    'before you commit to anything.'),
  ])
print(f'mexico {n}')

n = build('barbados', 'Barbados',
  'A Wedding Choir in Barbados &mdash; Anglican Parish Churches | Alma Consort',
  'A British consort at Barbadian weddings: an Anglican tradition three centuries deep, coral stone '
  'parish churches, and a service British guests will recognise.',
  'The one long-haul destination where the tradition is already ours.',
  'Alma Consort travels from London to sing in the parish churches of St James, Christ Church and '
  'St Peter, and at west coast weddings.',
  [
   ('Why Barbados', 'A choral tradition that needs no translating',
    ['Most long-haul destinations ask a British consort to sing outside its own tradition. Barbados does '
     'not, and that makes it the most musically coherent long-haul wedding on this list.',
     'The island has been Anglican since the seventeenth century, and it shows in the buildings and in '
     'the services held in them. The parish churches are stone, they are old, and they were built by '
     'people who expected the Book of Common Prayer to be read in them and hymns to be sung. A wedding '
     'at St James Parish Church &mdash; a foundation dating to the earliest years of English settlement '
     '&mdash; is a service a British congregation would recognise in every particular, in a building '
     'that carries voices properly.',
     'The practical consequence is that everything we do at home transfers directly: the hymnody, the '
     'anthems, the order of service, the expectation that the congregation sings. There is no rite to '
     'negotiate around and no language to bridge.']),
   ('The rite', 'Anglican services and beach ceremonies',
    ['An Anglican wedding in a Barbadian parish church has the shape you would find in an English one: '
     'a processional, hymns, an anthem during the signing of the register, and a recessional. A consort '
     'of eight to twelve leads it and the congregation joins in. Our guide to '
     '<a href="/music-guides/choosing-wedding-hymns.html">choosing wedding hymns</a> applies here '
     'essentially unchanged.',
     'The alternative format is a beach or hotel ceremony on the west or south coast, celebrant-led and '
     'without liturgy. Those work too, on the usual outdoor terms. Where a couple is choosing between '
     'them and cares about the music, the parish church is the better room by a considerable margin '
     '&mdash; and combining the two, with a church service and a beach reception, is a common and '
     'sensible shape.']),
   ('Buildings', 'Coral stone and the trade wind',
    ['Barbadian parish churches are built of coral stone, with height and hard surfaces, and they behave '
     'much as English stone churches do &mdash; generous, forgiving, and well suited to eight or twelve '
     'voices. Several have galleries, which give a consort an excellent position.',
     'Beach and terrace ceremonies on the west coast are the standard dry outdoor case with one addition: '
     'the trade wind blows reliably here, more so than in the Mediterranean. Twelve voices, positioned '
     'upwind of the guests, is the recommendation. The heat is more manageable than in Mexico or the '
     'Indian Ocean because of that same wind, but a late-afternoon ceremony is still kinder to singers '
     'than a midday one.']),
   ('Travel', 'Getting a consort to Barbados',
    ['Direct flights from London to Bridgetown run daily, at around eight and a half hours with a four-hour '
     'time change &mdash; the shortest and least disruptive long-haul journey on this list. We travel two '
     'days ahead rather than one so the singers arrive rested, and that second night is in the quote.',
     'Barbados is a Commonwealth country and well used to visiting performers and to British suppliers '
     'generally. We confirm the current requirements for foreign performers working for a fee when we '
     'quote, and handle whatever applies ourselves. The island is small, so transfers from the airport '
     'to any parish are short.']),
  ],
  [
   ('St James', 'st-james',
    ['The west coast, the concentration of luxury hotels and villas, and St James Parish Church itself '
     '&mdash; one of the oldest Anglican foundations in the western hemisphere and the best building on '
     'the island to sing a wedding in. Ceremony in the church and reception at a west coast hotel is the '
     'shape we would recommend to anyone who cares how the day sounds.']),
   ('Christ Church', 'christ-church',
    ['The south coast, a broader range of hotels and a livelier stretch of the island, with its own '
     'substantial parish church. Close to the airport, which keeps transfers short. Beach ceremonies here '
     'are more exposed to wind than the west coast.']),
   ('St Peter', 'st-peter',
    ['The quieter north west, with Speightstown and a scattering of villa and estate venues. Fewer, '
     'larger private weddings rather than hotel packages, and the parish church at the centre of the '
     'town. Transfers are longer from the airport; plan the rehearsal accordingly.']),
  ],
  [
   ('Will a Barbadian church wedding feel familiar?',
    'Very. Barbados has been Anglican since the seventeenth century, so the order of service, the hymnody '
    'and the expectation that the congregation sings are all as they would be in an English parish church '
    '&mdash; in a coral stone building that carries voices properly. Of everywhere we travel long-haul, '
    'this is the one where nothing has to be adapted.'),
   ('Church or beach?',
    'On musical grounds, the church, and not by a small margin. The parish churches are stone, tall and '
    'built for singing; a beach has no acoustic and a steady trade wind. The obvious answer is to have '
    'both: the ceremony in the church, the reception on the coast, which is a common shape here anyway.'),
   ('How many singers do we need?',
    'Eight to twelve in a parish church, which is the same as it would be at home for a comparable '
    'building and congregation. Twelve for a beach or terrace ceremony, positioned upwind. Tell us which '
    'church and we will give you a specific answer rather than a range.'),
   ('Is Barbados easier than the other long-haul destinations?',
    'Yes, in every practical respect. It is the shortest long-haul flight on this list at around eight '
    'and a half hours, the time change is four hours rather than eight or more, the island is small so '
    'transfers are short, and the wedding tradition is one we already know how to serve.'),
  ])
print(f'barbados {n}')

n = build('st-lucia', 'St Lucia',
  'A Wedding Choir in St Lucia &mdash; Souffri&egrave;re and Rodney Bay | Alma Consort',
  'A British consort at St Lucian weddings: a Catholic island with real churches, resort ceremonies '
  'under the Pitons, and what the terrain asks of twelve singers.',
  'A Catholic island with mountains, and both matter to the music.',
  'Alma Consort travels from London to sing at church and resort ceremonies at Souffri&egrave;re, '
  'beneath the Pitons, and around Rodney Bay.',
  [
   ('The rite', 'A Catholic island, and what that offers',
    ['St Lucia is predominantly Catholic, which distinguishes it from its Anglican neighbours and gives '
     'a consort a different and fuller option: a nuptial Mass, with a sung ordinary, psalm and '
     'acclamation, offertory and communion motets. The island has substantial parish churches, and a '
     'Mass in one is the most rewarding thing we could be asked to sing here.',
     'Most weddings on the island, though, are resort ceremonies &mdash; celebrant-led, outdoors, and '
     'usually with the Pitons somewhere in the frame. Those have no liturgy and an open programme, and '
     'the music does the structural work: an entrance, a piece at the vows, a recessional, and a set '
     'during the drinks afterwards.',
     'If you are having a church ceremony and a resort reception, that is the combination we would '
     'encourage. The church gives the consort a proper building and a proper service, and the resort '
     'gives everybody the view.']),
   ('Language', 'English, and a French Creole undertow',
    ['English is the official language and the service will be conducted in it, so nothing is lost. '
     'A Catholic Mass would have its sung ordinary in Latin as anywhere else.',
     'St Lucia also has a French Creole heritage that is audible in the island&rsquo;s own music. Where '
     'a couple wants the day to acknowledge where it is happening rather than transplant an English '
     'wedding wholesale, that is a better place to look than a generic international programme, and we '
     'are glad to arrange something appropriate for the consort.']),
   ('Buildings and terrain', 'Churches, resorts, and a great deal of hillside',
    ['The parish churches are stone and generous, and eight to twelve voices covers them comfortably. '
     'They are the best rooms on the island by a distance.',
     'Resort ceremonies are outdoors, dry, and frequently on a terrace cut into a hillside &mdash; which '
     'brings a practical point specific to St Lucia. The island is steep, and venues around Souffri&egrave;re '
     'in particular involve serious gradients and sometimes long stepped approaches to the ceremony '
     'spot. Moving twelve singers, in formal dress, up a hillside in tropical heat is a schedule item '
     'rather than an afterthought. Tell us what the approach looks like and we will plan for it.']),
   ('Travel', 'Getting a consort to St Lucia',
    ['Direct flights from London run several times a week to Hewanorra in the south of the island, at '
     'around nine hours with a four- or five-hour time change. The transfer from the airport to '
     'Souffri&egrave;re or the north is long by island standards &mdash; the roads are mountainous and '
     'slow &mdash; so we plan arrivals two days ahead rather than one, both for the flight and for the drive.',
     'St Lucia is a Commonwealth country used to visiting suppliers. We confirm the current requirements '
     'for foreign performers working for a fee at the point of quoting, and handle whatever applies.']),
  ],
  [
   ('Souffri&egrave;re', 'soufriere',
    ['Beneath the Pitons, and the most dramatic setting in the Caribbean for a wedding. Also the steepest: '
     'venues here are cut into hillsides and the approach to a ceremony spot can involve a significant '
     'climb. Worth planning properly for a group of twelve. The parish church in the town is a good '
     'building and a considerably easier one to sing in.']),
   ('Rodney Bay', 'rodney-bay',
    ['The north of the island, with the largest concentration of hotels and the easiest logistics. '
     'Beach and terrace ceremonies predominate, on the usual dry outdoor terms. Transfers from the '
     'airport are long but the terrain around the venues is gentler than the south.']),
  ],
  [
   ('Can we have a nuptial Mass in St Lucia?',
    'Yes, and it is the fullest use of a consort available on the island. St Lucia is predominantly '
    'Catholic with substantial parish churches, and a sung Mass gives the choir the complete liturgical '
    'shape &mdash; ordinary, psalm, acclamation, offertory and communion motets &mdash; in a building '
    'that supports it.'),
   ('Is the hillside really a problem?',
    'It is a real scheduling factor rather than an obstacle. Venues around Souffri&egrave;re are cut into '
    'steep ground and some ceremony spots involve a long stepped approach. Twelve singers in formal '
    'dress climbing that in tropical heat needs to be in the running order, with time and water allowed '
    'for. Send us a description of the approach and we will plan it.'),
   ('Church or resort?',
    'The church sounds better; the resort looks better. If the day can accommodate both &mdash; a church '
    'ceremony and a resort reception &mdash; that is what we would suggest, and it is a common shape here. '
    'If it has to be one, and the music matters most to you, choose the church.'),
   ('How far ahead should we book?',
    'Nine to twelve months. The flight is direct but runs only a few times a week, which makes the travel '
    'less flexible than it looks, and accommodation for twelve to twenty-four people at the smaller '
    'resorts needs arranging well ahead. Tell us the date as soon as it is fixed.'),
  ])
print(f'st-lucia {n}')

n = build('jamaica', 'Jamaica',
  'A Wedding Choir in Jamaica &mdash; Montego Bay, Ocho Rios | Alma Consort',
  'A British consort at Jamaican weddings: an Anglican and Baptist choral tradition, great house '
  'ceremonies, and resort weddings on the north coast.',
  'An island that already knows what a choir is for.',
  'Alma Consort travels from London to sing at church, great house and resort ceremonies in Montego '
  'Bay, Ocho Rios and Negril.',
  [
   ('The rite', 'A choral culture of its own',
    ['Jamaica has a deep and living church-music tradition &mdash; Anglican, Baptist and Methodist &mdash; '
     'and congregational singing here is not a polite formality but something people actually do, and do '
     'well. A visiting English consort arrives somewhere that understands exactly what it is for, which '
     'is not true of every destination on this list.',
     'An Anglican service in a Jamaican parish church has the order of service a British couple would '
     'recognise, with hymns the congregation will sing with more conviction than most English '
     'congregations manage. If any of your guests are Jamaican, plan for that rather than against it: '
     'choose hymns that reward being sung properly, and let the consort lead rather than perform.',
     'The other common formats are ceremonies at a great house or plantation estate, and resort weddings '
     'on the north coast. Both are celebrant-led with no liturgy, and the music carries the structure.']),
   ('Buildings', 'Parish churches, great houses and the north coast',
    ['Jamaican parish churches are stone, often eighteenth century, and behave much as English ones do. '
     'Eight to twelve voices is right for most of them.',
     'Great houses give you a hard-surfaced interior room, which is a considerable improvement on a lawn '
     'and worth asking about if the venue offers a choice. Resort ceremonies on the north coast are the '
     'standard outdoor case &mdash; dry, breezy, and better served by twelve voices than eight.',
     'The heat is significant and the humidity more so. As with the rest of the Caribbean, a '
     'late-afternoon ceremony, shade for the singers, and two days on the island before the wedding all '
     'improve what you actually hear.']),
   ('Travel', 'Getting a consort to Jamaica',
    ['Direct flights from London to Montego Bay run several times a week at around ten hours, with a '
     'five- or six-hour time change. Montego Bay is the arrival point for the whole north coast, with '
     'transfers of up to two hours to Ocho Rios and rather longer to Negril in the west.',
     'We travel two days ahead. Jamaica is a Commonwealth country accustomed to visiting performers; we '
     'confirm the current requirements for foreign performers working for a fee when we quote and handle '
     'whatever applies ourselves.']),
  ],
  [
   ('Montego Bay', 'montego-bay',
    ['Where you land, and the largest concentration of resorts and great house venues. Short transfers, '
     'plenty of choice, and several parish churches. The easiest logistics on the island and the sensible '
     'default if the music matters and you have not settled on a region.']),
   ('Ocho Rios', 'ocho-rios',
    ['The north coast east of Montego Bay, with resort and villa weddings and a transfer of up to two '
     'hours from the airport. Some fine great house venues inland, which are acoustically much better '
     'than a beach and worth seeking out.']),
   ('Negril', 'negril',
    ['The west end, beaches and cliffs, and the longest transfer from the airport. Ceremonies here are '
     'almost entirely outdoors and often at sunset, which is beautiful and means the consort is working '
     'at the end of a hot day; plan shade and water in advance rather than on the afternoon.']),
  ],
  [
   ('Will Jamaican guests expect to sing?',
    'If your congregation includes Jamaican guests, expect the hymns to be sung with real conviction '
    '&mdash; the church-music tradition here is strong and participatory. Plan for it: choose hymns that '
    'reward a congregation singing properly, and let the consort lead the singing rather than perform '
    'over it. It is one of the better sounds available at any wedding.'),
   ('Can you sing at a great house wedding?',
    'Yes, and it is often the better option acoustically. A great house gives you hard surfaces and an '
    'enclosed room, which returns sound in a way a beach or lawn does not. If your venue offers both an '
    'interior room and an outdoor spot, the interior will sound markedly better with the same number of singers.'),
   ('How does the heat affect the singing?',
    'Meaningfully, and we plan around it rather than hoping. Humidity tires voices faster than dry heat, '
    'and a group that has flown ten hours and lost six hours feels it more. A late-afternoon or evening '
    'ceremony, shade before and during, and arriving two days early are what make the difference.'),
   ('What does it cost compared with Barbados?',
    'Broadly similar, with slightly longer flights and longer transfers, particularly for Negril. Both '
    'sit at the more affordable end of long-haul because the flights are direct and the time change is '
    'moderate. We itemise flights, accommodation and any local permissions in the quote rather than '
    'folding them into one figure.'),
  ])
print(f'jamaica {n}')
