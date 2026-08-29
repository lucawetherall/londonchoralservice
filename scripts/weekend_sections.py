#!/usr/bin/env python3
"""The 'across the weekend' section for each country page.

The primary buyer is a couple having a destination wedding: they have moved
their family and friends to one place, often for three or four days, and they
feel the weight of having asked eighty people to fly somewhere. A consort that
has already travelled can sing several times across that weekend for very little
more than it costs to sing once — which is the strongest commercial argument
available on these pages, and it is country-specific because the geography is.

Secondary but real: couples already living in the country. Acknowledged on the
index rather than repeated twenty-two times.
"""

WEEKEND = {

'italy': ('The weekend', 'Across a Tuscan or Amalfi weekend', [
 'Italian weddings are rarely contained in an afternoon. Guests arrive on the Thursday or Friday, there '
 'is a dinner in the town the night before, the ceremony and reception fill the Saturday, and a good '
 'many stay through Sunday lunch.',
 'The thing worth knowing is that a consort which has flown out for the ceremony costs very little more '
 'to keep for the rest of it. The flights and the rooms are the expensive part and they are already '
 'paid. Singing at a welcome dinner in a courtyard on the Friday, then in the church on the Saturday, then again over drinks in the villa garden, gives your guests three quite different experiences of the same group, and in Italy the first two usually happen in different buildings, so the two sound quite different.',
 'Italy&rsquo;s one geographical quirk: the church and the reception villa are often twenty to forty '
 'minutes apart. Tell us the plan and we will work out whether we travel with the guests or go ahead. '
 'One sizing note: the villa set has to carry over a party in full flow, so it usually wants more '
 'voices than the church did, where everyone was silent and the stone was helping.']),

'france': ('The weekend', 'Across a ch&acirc;teau weekend', [
 'A French ch&acirc;teau wedding is usually an exclusive-use booking for two or three nights, with '
 'guests sleeping on the estate. That is close to the ideal shape for us: everyone is in one place, '
 'nobody is driving anywhere, and the whole party is together from Friday evening to Sunday morning.',
 'It also means the ceremony is a small part of what we could do. A consort can sing at the welcome dinner, at the ceremony itself, through the drinks in the gardens, and unaccompanied in a stone hall after the meal, which, with the lights down and the guests close in, tends to be the part they describe afterwards. All of it on one set of fares.',
 'France also has the mairie in the mix for couples marrying legally there, which spreads the weekend '
 'across another day. We can sing at the celebration afterwards if the two are separated. Bear in mind '
 'that the ch&acirc;teau dinner is a noisier room than the blessing was: singing over a party in full '
 'voice takes more singers than singing to one that has gone quiet.']),

'spain': ('The weekend', 'Across an island or coastal weekend', [
 'Spanish destination weddings, particularly on Ibiza and Mallorca, tend to be villa takeovers: guests '
 'in the house and nearby, a long welcome dinner, the wedding day itself, and a recovery lunch on the '
 'Sunday. People are together for days rather than hours.',
 'With the travel already paid for, a consort can appear at more than one of those. Something the '
 'guests do not expect on the Friday evening; the ceremony on the Saturday; and part-songs and '
 'arrangements during the aperitif afterwards. Spain is also the country where couples most often ask us to sing something unexpected late on. A piece arranged for the consort that means something to the two of them.',
 'If your ceremony is in a town church and the reception is at a finca, factor the transfer in; we '
 'will plan around whichever end you want us at.']),

'portugal': ('The weekend', 'Across a quinta weekend', [
 'Portugal has the best geography on this list for a multi-day wedding, and it is worth choosing on '
 'that basis. Quintas and estates routinely host the welcome dinner, the ceremony, the reception and '
 'the guest accommodation on one property, so nothing needs a coach and nobody loses an hour to a '
 'transfer.',
 'For a consort, that means the marginal cost of singing more than once is almost nothing. We can sing '
 'at the Friday dinner, at the ceremony, over drinks, and again before the meal, without anybody moving '
 'and without a single additional fare. Of everywhere we travel, Portugal is where a group that has '
 'flown out earns its journey most easily.',
 'If your ceremony is in a Lisbon or Porto church with the reception up the valley, that changes; tell '
 'us and we will plan the day around the drive. Worth flagging when you plan the day: the quinta terrace during drinks is a talking room, and a talking room needs more voices to carry than a quiet church does. The number rises with the size of the party, not with the size of the estate.']),

'greece': ('The weekend', 'Across an island weekend', [
 'A Greek island wedding is a three- or four-day event by necessity: guests fly in, there is nowhere '
 'else for them to be, and the celebrations spread across a welcome dinner, the wedding day and a long '
 'lunch afterwards. Everyone is in the same handful of hotels in the same town.',
 'That concentration is an opportunity. The ceremony itself may use twenty minutes of a consort that '
 'has flown from London; the rest of the weekend has room for a good deal more. Singing at the welcome '
 'dinner on a terrace, or indoors somewhere with stone around it, gives your guests the version of the '
 'group that the clifftop ceremony acoustically cannot.',
 'Worth planning deliberately in Greece: the best-sounding moment of the weekend is often not the '
 'ceremony. Ask us where on the island the singing will land best and we will tell you. And '
 'size the two differently: the clifftop ceremony is quiet, the taverna dinner is not, and voices have '
 'to clear the noise of however many people are talking through it.']),

'cyprus': ('The weekend', 'Across a Cyprus weekend', [
 'Cypriot weddings keep everybody in one place better than almost anywhere. The hotel or villa usually '
 'hosts the ceremony, the drinks, the dinner and the guests themselves, so the party is together from '
 'arrival to departure with no coaches and no scattering.',
 'The season is long here too, which means guests often stay a week rather than a weekend. That gives '
 'a consort more than one natural moment: a welcome dinner, the ceremony, the reception, and sometimes '
 'a second evening of its own. All on one set of fares, since the expensive part of bringing '
 'us is the getting here.',
 'Cyprus also has the shortest transfers on this list. Whatever the plan, nothing is more than an hour '
 'from anything else. One thing to price separately: a poolside reception with a bar running is a '
 'louder room than the ceremony was, and the louder the room, the more voices it takes to be heard '
 'across it.']),

'malta': ('The weekend', 'Across a Maltese weekend', [
 'Malta is small enough that a wedding weekend has no logistics to speak of. Guests stay in Valletta or '
 'Sliema, the church may be in Mdina, the reception somewhere else again, and none of it is more than '
 'half an hour away. The whole party moves easily.',
 'With the buildings Malta has, that is worth exploiting. A consort can sing at a welcome dinner, then in a baroque church on the Saturday, then at the reception, and the church is such a different acoustic from anything else on the island that guests hear two distinct things from the same singers.',
 'If any part of the weekend is on Gozo, add the ferry to the plan; everything else is straightforward.']),

'croatia': ('The weekend', 'Across a Dalmatian weekend', [
 'Dubrovnik and Split old towns are walkable, which shapes the whole weekend: guests stay inside the '
 'walls, walk to dinner, walk to the ceremony, and walk home. Nothing is coached anywhere.',
 'That is unusually good for us. A consort can sing in a cloister on the Friday evening, at the '
 'ceremony on the Saturday, and at the reception afterwards, with guests moving between them on foot '
 'in ten minutes. And because the old towns are stone throughout, every one of those spaces sounds '
 'better than its equivalent almost anywhere else on this list.',
 'Island weddings on Hvar work the same way once everyone is there; it is only the arrival that needs '
 'the extra planning.']),

'gibraltar': ('The weekend', 'Across a Gibraltar weekend', [
 'Everything in Gibraltar is within walking distance of everything else. Guests stay in the town, the '
 'cathedrals are in the town, the registry is in the town, and the airport is a few minutes from all '
 'of it. A wedding weekend here needs no transport plan at all.',
 'For a consort that means unusual flexibility: we can sing at a dinner the night before, at a '
 'cathedral service the next day, and at the reception, with no travel time between any of them. '
 'Because there is no work-permit question here either, Gibraltar is the destination where a '
 'multi-part weekend is easiest to arrange at short notice.',
 'Some couples pair a cathedral ceremony with a reception at the Botanic Gardens or a hotel terrace; '
 'both are minutes away.']),

'ireland': ('The weekend', 'Across an Irish castle weekend', [
 'The Irish castle wedding is built around exclusive use: your guests take over the house for two or '
 'three nights, and the weekend runs from a Friday dinner through to a Sunday breakfast with everyone '
 'under one roof.',
 'Nothing suits a consort better. We can sing at the dinner on the Friday, at the ceremony on the '
 'Saturday &mdash; in a church or in the house itself, since Ireland allows both to be legally binding '
 '&mdash; and unaccompanied in a hall after the meal. Ireland is also the cheapest destination on this '
 'list to bring us to, so a multi-part weekend costs less here than a single ceremony does further '
 'afield.',
 'Because so many Irish venues have their own chapel or great hall, you are rarely choosing between the '
 'setting and the acoustic.']),

'scotland': ('The weekend', 'Across a Scottish castle weekend', [
 'Scottish castle weddings are almost always exclusive-use, and guests travelling from England or '
 'abroad stay for two or three nights. The weekend has its own rhythm: an arrival dinner, the wedding '
 'day, and a long unhurried Sunday.',
 'A consort can be part of more than one of those, and because Scotland is a domestic engagement on our '
 '<a href="/pricing.html">published rates</a> with no flights to price for the whole group, the cost of '
 'adding a second appearance is smaller here than anywhere else we sing.',
 'Scotland also has the ceilidh problem, which is an opportunity: the evening belongs to a band, '
 'so the consort&rsquo;s moments are the day and the dinner. Placed there, the two do not compete at '
 'all.']),

'united-states': ('The weekend', 'Across an American wedding weekend', [
 'The multi-day wedding weekend is more established in the United States than anywhere else, and the '
 'vocabulary already exists for it: the rehearsal dinner on the Friday, the ceremony and reception on '
 'the Saturday, the farewell brunch on the Sunday. Guests expect three events, not one.',
 'That is a good fit for a group that has crossed the Atlantic. The rehearsal dinner in particular suits a consort. It is smaller, indoors, and the guests are close, which is where unaccompanied singing is at its best. With the flights and visas already arranged, adding it costs '
 'very little.',
 'If your ceremony is in a New York church and the reception is elsewhere in the city, that is an easy '
 'transfer; Florida and Nevada resorts usually keep everything on one site. Size the cocktail hour on '
 'its own terms rather than the ceremony&rsquo;s: a room of people with drinks in their hands makes a '
 'great deal of noise, and unamplified voices have to get over it.']),

'mexico': ('The weekend', 'Across a Riviera Maya weekend', [
 'Mexican destination weddings are resort takeovers: guests stay on site for three or four nights, and '
 'the celebrations spread across a welcome party, the wedding day and often a beach brunch to close.',
 'Everybody being in one place for days is the argument for using a consort more than once. The '
 'transatlantic flights are the expensive part of bringing us and they are already spent, so a welcome '
 'party on the Thursday and the ceremony on the Saturday cost far less together than they would apart.',
 'Worth thinking about where each moment happens. If the resort has a cenote, a chapel or any enclosed space, put one of the performances there rather than putting everything on the beach. The contrast is what your guests will remember.']),

'barbados': ('The weekend', 'Across a Barbados week', [
 'Barbados weddings tend to run longer than a weekend. Guests fly eight hours and make a holiday of it, '
 'so the party is on the island for a week and the wedding sits in the middle of it.',
 'That opens up a different shape from a European weekend. A consort can sing at a welcome '
 'dinner early in the week, at the church service, and at the reception afterwards, with days in '
 'between rather than hours. And because the parish churches are the best rooms on the island, the '
 'church appearance is the one that will sound quite unlike the others.',
 'Ceremony on the west coast and reception at a nearby hotel is the usual shape, and the transfers are '
 'short.']),

'st-lucia': ('The weekend', 'Across a St Lucia week', [
 'Like Barbados, St Lucia is a week rather than a weekend: guests come a long way and stay, and the '
 'wedding is the centre of a longer holiday for everybody.',
 'With the fares already paid, a consort can appear more than once across that: a welcome evening, the ceremony, the reception. The one thing to plan carefully is movement: the island is '
 'steep, transfers between the north and Souffri&egrave;re take real time, and a group of singers in '
 'formal dress does not move quickly on a hillside.',
 'If everything is at one resort, none of that applies and the weekend is straightforward.']),

'jamaica': ('The weekend', 'Across a Jamaican week', [
 'Jamaican weddings draw guests for a week, often mixing family who have travelled from Britain or '
 'America with family who live on the island. That combination shapes what works: a service with real '
 'congregational singing lands differently when half the congregation grew up singing in church.',
 'Across the week a consort can sing at a welcome event, at the church, and at a great house reception. '
 'The great house is worth using for at least one of them. Hard surfaces and an enclosed room carry where a lawn does not, and it gives your guests something distinct from the beach.',
 'Negril adds a long transfer from Montego Bay; Ocho Rios and the north coast keep the week compact.']),

'mauritius': ('The weekend', 'Across a Mauritius week', [
 'Mauritius is a twelve-hour flight, so guests stay for a week or more and the wedding is one day '
 'inside a longer holiday. Everybody is usually at one or two resorts on the same coast.',
 'Given what it costs to fly a consort that distance, singing once is the least efficient use of the '
 'booking. A welcome dinner, the ceremony and the reception spread across the week make the fares work '
 'far harder, and cost only the singers&rsquo; extra nights rather than another journey.',
 'If a church ceremony is part of the plan, make that one of the appearances. It is the only setting on '
 'the island where the building does any of the work.']),

'maldives': ('The weekend', 'Across a Maldivian stay', [
 'The Maldives produces the most concentrated wedding party of any destination we sing at. Your guests '
 'are on one island, in one resort, with nowhere else to go, for four or five days. Nobody drives '
 'anywhere; nobody leaves.',
 'That is the strongest case anywhere on this list for using a consort more than once. Getting singers '
 'to a Maldivian resort island is the whole expense; once they are there, a welcome dinner on the '
 'Thursday, the ceremony on the Saturday and a sunset performance on another evening cost only the '
 'additional nights.',
 'Maldivian weddings tend to be among the smallest we sing at, which points the same way: a smaller '
 'group singing close in, several times across the stay, is both the better sound and the better use '
 'of the journey.']),

'seychelles': ('The weekend', 'Across a Seychelles stay', [
 'Seychelles weddings run over a week, with guests staying at one or two resorts and the wedding day '
 'in the middle. The islands are quiet enough that the party tends to stay together throughout.',
 'Because getting a consort here is the expensive part, spreading its appearances across the stay is '
 'the sensible plan: a welcome evening, the ceremony, and the reception. If a church is part of it, put one appearance there. It is the only setting in the Seychelles with a real acoustic, and the difference against a beach is large.',
 'If guests are split across islands, tell us early; ferry and domestic flight timings shape what is '
 'possible across a week as much as they shape the arrival.']),

'thailand': ('The weekend', 'Across a Thai wedding week', [
 'Thai destination weddings are usually villa takeovers running four or five days: guests arrive, '
 'settle into the house or the resort, and stay put. There is a welcome dinner, a full wedding day, and '
 'usually a relaxed final evening.',
 'A twelve-hour flight makes singing once an inefficient use of the arrangement. Spread across the '
 'week, a consort can sing at the welcome dinner, at the ceremony, and at a farewell evening, for the '
 'cost of the extra nights rather than another journey.',
 'The evening performances are often the best ones here. Thai heat makes the middle of the day hard '
 'work, and a covered pavilion after dark, with guests close in and the day&rsquo;s heat gone, is where '
 'unaccompanied voices sound their best.']),

'indonesia': ('The weekend', 'Across a Bali wedding week', [
 'Bali weddings run long. Guests have travelled fourteen hours or more, so they stay a week, and the '
 'wedding sits inside a stretch of villa dinners, beach days and excursions with the same party '
 'throughout.',
 'The journey is the expense, so once a consort is on the island, additional appearances are cheap by '
 'comparison. A welcome dinner in a villa, the ceremony in a clifftop chapel, and a final evening '
 'performance give your guests three different rooms and three different moods from one booking.',
 'Put at least one of them in the chapel if your venue has one. It is the only enclosed space most Bali '
 'weddings involve, and it will sound unlike anything else in the week.']),

'south-africa': ('The weekend', 'Across a Winelands weekend', [
 'Cape wine estates are set up for multi-day weddings: guest accommodation on the property, a welcome '
 'dinner in the cellar or on the stoep, the wedding day itself, and often a long Sunday lunch before '
 'people scatter to safari or the coast.',
 'For a consort this is close to the Portuguese case. Everyone in one place, no transfers, and several natural moments to sing across two or three days. The barrel cellar is the room to use for '
 'at least one of them.',
 'South Africa has an advantage nowhere else on this list has: the flight is long but the time change '
 'is an hour or two, so singers arrive able to work rather than needing a day to recover. A multi-part '
 'weekend is easier to deliver well here than anywhere else at this distance. The cellar dinner is the '
 'one to size up for: hard surfaces help, but a full room in conversation still takes more voices to '
 'carry than a silent ceremony does.']),
}
