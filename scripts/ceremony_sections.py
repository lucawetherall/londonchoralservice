#!/usr/bin/env python3
"""The 'what kind of ceremony are you having?' section for each country page.

The reader is an English-speaking couple travelling out to marry, not a local
having a local service. The kind of ceremony they have is their choice — humanist,
non-denominational, celebrant-led, Anglican, Catholic, interfaith or civil — and
is not determined by the country's majority religion. Each country changes what
is *available* and what is legally recognised, which is what these sections cover.

Legal statements are orientation, not advice; every page carries a checked date
and directs anything venue-, diocese- or celebrant-specific back to us.
"""

CEREMONY = {

'italy': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Almost every couple we sing for in Italy is British, Irish, American or Australian, marrying in a '
 'country they do not live in, and choosing the shape of the day themselves. What Italy offers is '
 'range.',
 'A <strong>Catholic nuptial Mass</strong> is available if one of you is Catholic, and it gives a '
 'choir more to do than any other option. A <strong>Church of England service</strong> is possible '
 'too, and more often than couples realise: the Diocese in Europe has Anglican chaplaincies in '
 'Florence, Milan, Rome and elsewhere, and an English-language Anglican wedding in Italy runs on the '
 'order of service you would recognise from home, hymns included. A <strong>humanist or '
 'celebrant-led ceremony</strong> at a villa or garden has no liturgy at all, which leaves the music open. Many couples handle the legal marriage quietly at home and treat the Italian day as '
 'the ceremony that matters.',
 'Tell us which of those you are having when you enquire, because it changes the programme more than '
 'the venue does. A Mass wants a sung ordinary; a humanist ceremony wants three or four pieces placed '
 'where the words stop.']),

'france': ('Your ceremony', 'What kind of ceremony are you having?', [
 'France has one rule that catches British couples out and one that works in their favour.',
 'The rule that catches people out: the legal marriage must happen at the <em>mairie</em>, conducted '
 'by the mayor, and there is generally no place for music in it. The rule that helps: everything '
 'after that is yours to design. A <strong>church blessing</strong>, Catholic or Protestant, carries '
 'no legal weight in France and so can be shaped freely. The Diocese in Europe has Anglican '
 'chaplaincies across the country, including in the Dordogne where the British population is '
 'substantial, so a <strong>Church of England service</strong> is a real option rather than a stretch. '
 'A <strong>humanist or celebrant-led ceremony</strong> at a ch&acirc;teau is now the most common '
 'choice of all among the couples we sing for.',
 'Many couples marry legally at home first and have a single ceremony in France, which avoids the mairie. Whichever route you take, the ceremony your guests will remember is the one we '
 'sing at.']),

'spain': ('Your ceremony', 'What kind of ceremony are you having?', [
 'The couples we sing for in Spain are almost all travelling out, and their ceremonies fall into '
 'three broad shapes.',
 'A <strong>Catholic nuptial Mass</strong> in a mainland or Mallorcan town church, if one of you is '
 'Catholic. A <strong>Church of England service</strong> — the Diocese in Europe has long-established '
 'Anglican chaplaincies on the Costa del Sol, in Madrid and in the Balearics, serving exactly this '
 'kind of congregation. Or a <strong>humanist, non-denominational or celebrant-led ceremony</strong> '
 'at a villa or finca, which is what most of our Ibiza and Marbella enquiries turn out to be.',
 'Spanish civil marriage has residency and paperwork requirements that many visiting couples find '
 'easier to sidestep by marrying legally at home, then having the ceremony they want in Spain. That choice has no effect on the music at all, and it is worth knowing you have it.']),

'portugal': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Portugal is one of the easier countries in Europe for a visiting couple, and the ceremony is your choice rather than the country&rsquo;s.',
 'A <strong>Catholic nuptial Mass</strong> if one of you is Catholic, in parishes that take music '
 'seriously. A <strong>Church of England service</strong> through the Anglican chaplaincies in Lisbon '
 'and the Algarve, which serve a large resident British community and are used to visiting couples. '
 'Or — and this is the majority of what we are asked for here — a <strong>humanist, '
 'non-denominational or celebrant-led ceremony</strong> at a quinta, a palace or a hotel, with the '
 'legal formality handled separately.',
 'Because so many Portuguese venues host the ceremony and the reception on one estate, the choice of '
 'service matters less to the logistics here than almost anywhere else. What it changes is the '
 'programme, so tell us which you are planning.']),

'greece': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Worth clearing up first, because it is the assumption most often made about Greece: you do not have '
 'to have an Orthodox wedding, and the great majority of couples we sing for there do not.',
 'A <strong>symbolic, humanist or celebrant-led ceremony</strong> at a hotel, villa or clifftop '
 'terrace is far and away the most common choice, with the legal marriage done at home beforehand. '
 'There is no liturgy, no repertoire restriction and no language barrier, so the music is yours. A <strong>Church of England service</strong> is available through the Anglican chaplaincies '
 'in Athens and on Corfu. A <strong>Greek Orthodox wedding</strong> is the route for couples where one '
 'partner is Greek or Orthodox, and some couples have an Orthodox blessing for the family alongside a '
 'ceremony of their own.',
 'Only the last of those has a fixed sung tradition of its own, and we cover what that means below. '
 'For everything else, you are choosing the shape of your own day.']),

'cyprus': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Cyprus is among the simplest countries in Europe for a British couple to marry in legally, which is '
 'why so many do — and the ceremony itself can take almost any form you want.',
 'A <strong>civil ceremony</strong> conducted by a municipality is legally binding and straightforward '
 'for visitors; Paphos town hall marries a great many British couples every year. A <strong>Church of '
 'England service</strong> is a genuine option here, more so than on most of this list: the Anglican '
 'chaplaincies in Paphos, Limassol and elsewhere serve a large resident British community, and an '
 'Anglican wedding in Cyprus runs on the order of service you would recognise, with hymns your guests '
 'can sing. A <strong>humanist or celebrant-led ceremony</strong> at a hotel or villa is the other '
 'common choice. A <strong>Greek Orthodox service</strong> applies where one partner is Cypriot or '
 'Orthodox.',
 'Of everything on the island, the Anglican route is the one that gives a consort most to work with, '
 'and it is the one couples least often know is there.']),

'malta': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Malta makes almost every route easy for a visiting couple, which along with the buildings is why we '
 'rate it so highly.',
 'A <strong>Catholic nuptial Mass</strong> is the island&rsquo;s normal form of wedding and needs no '
 'negotiating. A <strong>Church of England service</strong> is equally available: St Paul&rsquo;s '
 'Anglican Pro-Cathedral in Valletta is a working chaplaincy of the Diocese in Europe, and an Anglican '
 'wedding there is as close to an English cathedral wedding as you will get outside England. A '
 '<strong>civil ceremony</strong> is legally straightforward for visitors, and <strong>humanist or '
 'celebrant-led ceremonies</strong> at hotels and private venues are common.',
 'English is an official language, so whichever you choose, nothing has to be translated and your '
 'guests can follow — and sing — throughout.']),

'croatia': ('Your ceremony', 'What kind of ceremony are you having?', [
 'The couples we sing for in Croatia are travelling out, and the country accommodates most shapes of '
 'ceremony without difficulty.',
 'A <strong>Catholic nuptial Mass</strong> in an old-town church if one of you is Catholic. A '
 '<strong>humanist, non-denominational or celebrant-led ceremony</strong> in a cloister, a courtyard '
 'or a garden, which is what most foreign weddings here are. A <strong>civil ceremony</strong> for the '
 'legal side, which many couples complete at home instead to keep the paperwork simple. Anglican '
 'provision is thinner here than in Italy or Spain, so if a Church of England service matters to you, '
 'raise it early &mdash; a visiting chaplain is sometimes possible.',
 'Croatia&rsquo;s particular advantage is that the non-liturgical venues are often as good acoustically '
 'as the churches, which is unusual and covered below.']),

'gibraltar': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Gibraltar removes more obstacles than anywhere else on this list, because it is a British Overseas '
 'Territory: British legal framework, English throughout, and no visa or work-permit question for '
 'anybody involved, us included.',
 'A <strong>Church of England service</strong> at the Cathedral of the Holy Trinity is the option '
 'closest to a wedding at home &mdash; same order of service, same hymnody, same expectation that the '
 'congregation sings. A <strong>Catholic wedding</strong> at the Cathedral of St Mary the Crowned '
 'gives the fuller sung Mass. A <strong>civil ceremony</strong> at the registry is legally simple and '
 'famously quick, and <strong>celebrant-led ceremonies</strong> at the Botanic Gardens and other '
 'venues are straightforward.',
 'The registry&rsquo;s reputation for short-notice weddings is deserved, and it extends to us: with no '
 'permits to arrange, Gibraltar is the destination where we can most often say yes to a date a couple '
 'of months out.']),

'ireland': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Ireland offers British couples something most destinations do not: a legally binding ceremony in '
 'almost any form, at a venue of your choosing, with no language barrier and no permits for us.',
 'A <strong>Church of Ireland service</strong> is Anglican, so the order of service, the hymns and the '
 'place of an anthem are all as they would be at home. A <strong>Catholic nuptial Mass</strong> gives '
 'the full sung shape. And Ireland legally recognises <strong>humanist and secular ceremonies</strong> '
 '&mdash; a registered humanist celebrant can solemnise a marriage that is binding in law, at an '
 'approved venue rather than only in a church, which is why so many Irish weddings happen at castles '
 'and country houses.',
 'That last point is worth dwelling on: you do not have to choose between a ceremony that counts '
 'legally and one that happens where you want it. Both are available, which is not true in France, '
 'Spain or Italy.']),

'scotland': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Scotland gives you more freedom over the form and the place of your wedding than anywhere else in '
 'the United Kingdom, and couples travel there from England for exactly that reason.',
 'Scots law attaches the authority to the celebrant rather than to the building, so a religious or '
 'belief celebrant can conduct a legally binding ceremony almost anywhere. <strong>Humanist '
 'ceremonies</strong> have been legally binding in Scotland since 2005, well before England recognised '
 'anything comparable, and they are now among the most common forms of wedding in the country. A '
 '<strong>Scottish Episcopal service</strong> is Anglican and will feel like an English parish '
 'wedding. A <strong>Church of Scotland service</strong> is Presbyterian, plainer, and strong on '
 'congregational singing. A <strong>Catholic nuptial Mass</strong> gives the full sung liturgy.',
 'The practical upshot for the music is that there is no second ceremony to work around and no '
 'compromise between legality and setting &mdash; but the ceremony is frequently outdoors, which is '
 'its own problem and covered below.']),

'united-states': ('Your ceremony', 'What kind of ceremony are you having?', [
 'For a British couple marrying in the United States, the ceremony is unusually unconstrained. Most '
 'states will license almost any officiant, so the form of service follows what you want rather than '
 'what is on offer.',
 'An <strong>Episcopal service</strong> is Anglican and will feel familiar &mdash; the same '
 'order, the same hymnody, and in the north east some of the finest church buildings we could sing in '
 'anywhere. A <strong>Catholic nuptial Mass</strong> gives the fuller sung shape. <strong>Humanist, '
 'interfaith and non-denominational ceremonies</strong> are widespread and unremarkable, often '
 'conducted by a friend or family member licensed for the day, and carry no liturgy at all.',
 'Legal marriage is generally simple for visitors, with requirements varying by state. The '
 'complication in the United States is not the ceremony &mdash; it is our side of the arrangement, '
 'and it is significant enough to take the next section.']),

'mexico': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Nearly every couple we are asked about in Mexico is travelling from Britain, Ireland or the United '
 'States, and nearly every one is having a symbolic ceremony rather than a Mexican legal one.',
 'Mexican civil marriage involves residency, translated documents and local medical requirements that '
 'most visiting couples decide are not worth the trouble, so they <strong>marry legally at home</strong> '
 'and have the ceremony that matters in Mexico. That ceremony is then open: '
 '<strong>humanist, non-denominational, celebrant-led or spiritual</strong>, on a beach, in a jungle '
 'clearing or beside a cenote, shaped however you want it.',
 'A <strong>Catholic nuptial Mass</strong> is available in the colonial churches for couples who want '
 'one, and those are the best buildings in the country to sing in. Some couples add a Mayan blessing, '
 'which has its own form and its own performers and sits alongside rather than inside the ceremony we '
 'sing at.']),

'barbados': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Barbados is one of the easiest countries in the world for a visiting couple to marry in legally '
 '&mdash; a licence can usually be obtained without a residency period &mdash; and the range of '
 'ceremony available to you is wide.',
 'The island has been <strong>Anglican</strong> since the seventeenth century, so a Church of England '
 'service in a Barbadian parish church is not an approximation of an English wedding; it is the same '
 'service, in a coral stone building that carries voices properly, with a congregation that sings. '
 'That is the single best reason to bring a consort here. A <strong>Catholic wedding</strong> is '
 'available, and <strong>humanist or celebrant-led ceremonies</strong> on the beach or at a hotel are '
 'common for couples who want something secular.',
 'If the music matters to you, the church is the option that repays the journey.']),

'st-lucia': ('Your ceremony', 'What kind of ceremony are you having?', [
 'St Lucia is straightforward for visiting couples to marry in legally, and the ceremony can take '
 'whichever form suits you.',
 'The island is predominantly <strong>Catholic</strong>, with substantial parish churches, so a '
 'nuptial Mass is available and gives a choir the fullest possible shape. <strong>Anglican</strong> '
 'provision exists too, for couples who want a Church of England service. And the majority of what we '
 'are asked about here is a <strong>humanist, non-denominational or celebrant-led ceremony</strong> at '
 'a resort, usually outdoors with the Pitons somewhere in the frame.',
 'English is the official language, so nothing needs translating whichever route you take, and your '
 'guests will follow the service without effort.']),

'jamaica': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Jamaica is simple for visitors to marry in legally &mdash; a short residency and a licence &mdash; '
 'and the ceremony is yours to choose.',
 'The island has a deep and living <strong>Anglican</strong> tradition alongside Baptist and Methodist '
 'churches, and church singing here is participatory in a way it often is not at home. A Church of '
 'England service in a Jamaican parish church puts a consort in front of a congregation that will sing. A <strong>Catholic wedding</strong> is available. And <strong>humanist and '
 'celebrant-led ceremonies</strong> at great houses and north coast resorts are the other common '
 'shape, with no liturgy and an open programme.',
 'If any of your guests are Jamaican, the congregational singing is worth planning around rather than '
 'through &mdash; more on that below.']),

'mauritius': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Mauritius allows visiting couples to marry legally with a short residency, and it accommodates most '
 'forms of ceremony.',
 'The great majority of what we are asked about is a <strong>humanist, non-denominational or '
 'celebrant-led ceremony</strong> at a resort &mdash; a beach, a garden, or a deck over the lagoon '
 '&mdash; with no liturgy and a programme of your choosing. A <strong>Catholic wedding</strong> '
 'is available in the island&rsquo;s colonial-era churches, which are the only settings here with a '
 'real acoustic and are covered below. <strong>Anglican</strong> provision exists in Port Louis and '
 'elsewhere for couples who want a Church of England service.',
 'The island is religiously plural &mdash; Hindu, Catholic, Muslim and Christian communities all live '
 'alongside each other &mdash; so nothing about your choice will seem unusual to anyone local.']),

'maldives': ('Your ceremony', 'What kind of ceremony are you having?', [
 'One fact shapes every Maldivian wedding and is worth stating before anything else: legal marriage in '
 'the Maldives is not available to non-Muslim visitors. Every wedding a foreign couple has here is a '
 '<strong>symbolic ceremony</strong>, with the legal marriage completed at home before or after.',
 'That sounds like a limitation and functions as a freedom. There is no registrar, no prescribed '
 'wording, no liturgy and no restriction on repertoire. A <strong>humanist, non-denominational or '
 'celebrant-led ceremony</strong> on a sandbank or a jetty can be built around the two of you, in whatever order you like, for exactly as long as you want it to last. Some couples write the '
 'whole thing themselves.',
 'For the music, that means we are not fitting around a service &mdash; we are helping you build one. '
 'Tell us the shape you have in mind and we will suggest where the singing belongs.']),

'seychelles': ('Your ceremony', 'What kind of ceremony are you having?', [
 'The Seychelles is straightforward for visiting couples to marry in legally, and the ceremony is '
 'yours to shape.',
 'Most of what we are asked about is a <strong>humanist, non-denominational or celebrant-led '
 'ceremony</strong> on a beach or in a resort garden, with no liturgy and an open programme. The '
 'islands are also strongly <strong>Catholic</strong>, with real parish churches on Mah&eacute; and '
 'Praslin, so a nuptial Mass is available &mdash; and those are the only buildings here with '
 'an acoustic worth the name. <strong>Anglican</strong> provision exists on Mah&eacute; for a Church '
 'of England service.',
 'The church option is underused by visiting couples, largely because resorts do not tend to mention '
 'it. If the singing matters to you, it is worth asking about.']),

'thailand': ('Your ceremony', 'What kind of ceremony are you having?', [
 'The couples we sing for in Thailand are British, Irish, Australian and American, marrying at a villa '
 'or resort in a country they are visiting. Their ceremonies look much as they would at home, and are '
 'chosen for the same reasons.',
 'A <strong>humanist, non-denominational or celebrant-led ceremony</strong> is what most of them have '
 '&mdash; personal, written with the celebrant, no liturgy, no restrictions, and the music placed '
 'wherever it works. Legal registration at a district office is possible for visitors, though many '
 'couples find it simpler to <strong>marry legally at home</strong> and treat the Thai day as the '
 'wedding. A <strong>Christian service</strong> is available for couples who want one; Christ Church '
 'Bangkok is an Anglican chaplaincy, and some couples arrange a visiting minister to conduct a '
 'service at the venue.',
 'A <strong>Buddhist blessing</strong> is an optional addition rather than the default, and one many '
 'couples enjoy having alongside their own ceremony. It has its own form, which we come back to below.']),

'indonesia': ('Your ceremony', 'What kind of ceremony are you having?', [
 'Bali attracts couples from Britain, Australia and across Asia, and almost none of them are having an '
 'Indonesian legal wedding. Indonesian marriage law requires both parties to share a recognised '
 'religion and involves considerable paperwork, so visiting couples overwhelmingly <strong>marry '
 'legally at home</strong> and have the ceremony they want in Bali.',
 'That ceremony is a <strong>humanist, non-denominational, spiritual or celebrant-led</strong> one, '
 'held in a clifftop chapel, a garden or a jungle clearing, with no liturgy and nothing off limits '
 'musically. A <strong>Christian service</strong> is possible &mdash; Bali has Catholic and Protestant '
 'churches serving its own Christian minority and the expatriate community &mdash; and some couples '
 'bring a minister with them.',
 'A <strong>Balinese Hindu blessing</strong> is an optional addition that some couples arrange '
 'alongside their own ceremony. It belongs to a living tradition with its own musicians, and it sits '
 'beside your ceremony rather than replacing it.']),

'south-africa': ('Your ceremony', 'What kind of ceremony are you having?', [
 'South Africa is straightforward for visiting couples to marry in legally, and it is one of the few '
 'long-haul destinations where a full range of ceremony is available in practice rather than on paper.',
 'An <strong>Anglican service</strong> is the closest thing to home: the Anglican Church of Southern '
 'Africa is substantial, Cape Town has real churches and a cathedral, and the congregational singing '
 'is better than you will hear in most English parishes. A <strong>Catholic nuptial Mass</strong> '
 'gives the full sung shape. <strong>Humanist, interfaith and celebrant-led ceremonies</strong> are '
 'common and unremarkable, and wine estate weddings are usually of this kind. South Africa also '
 'recognises a wide range of marriage officers, so an officiant can generally be found for whatever '
 'you have in mind.',
 'This is the long-haul destination with the strongest choral culture of its own, which changes what a '
 'visiting consort walks into &mdash; covered next.']),
}
