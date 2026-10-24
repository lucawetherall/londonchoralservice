# Competitor, ad landscape, search intent and link gap — research

**Date:** 2026-10-24
**Author:** Claude, for Luca Wetherall
**Status:** Findings and proposals. Nothing on the site, in Google Ads or on the Business Profile was changed.
**Related:** [data/competitor-pricing.yml](../../../data/competitor-pricing.yml), [compare/london-funeral-singers.html](../../../compare/london-funeral-singers.html), [docs/off-site-listings-pack.md](../../off-site-listings-pack.md), [2026-08-18-competitive-capture-design.md](2026-08-18-competitive-capture-design.md)

---

## Why this exists

Our hiring pages sit on page 3–5 of Google for head terms, while marketplaces and a few rivals take the clicks and the AI-answer citations. This week's work covered landing pages, priced answers, area pages and guides. This document tells the next round what to change: page types, messages, and the sites to be listed on.

## Method and limits

- **Rivals:** web search for the hiring queries below, then each rival's own pages fetched on 2026-10-24. Every price was copied verbatim; the ones we might use are now in `data/competitor-pricing.yml` (see §1.4).
- **Ads:** the free Google Ads Transparency Center, region United Kingdom, on 2026-10-24, plus a read-only check of our own account through the Google Ads API. Text ads show there as one rendered combination of a responsive ad, so the copy below is a sample, not every asset.
- **Search results:** google.co.uk, `gl=uk&hl=en-GB`, opened in a browser on 2026-10-24. That browser was signed in to a Google account (it showed Search Console figures on one query), so the order may be a little personalised. Ads in the result pages were not captured. Positions from Search Console are the 7-day figures in the 19 October Monday report.
- **Links:** free sources only (search plus fetching each page). Hitched, The Wedding Directory, Warble and Funeral Service Times refuse automated fetches, so those rows are unverified.

---

## 1. Competitive brief

### 1.1 Who we are up against

| Rival | What they sell | Price signals | Proof they show | Ads now? |
|---|---|---|---|---|
| **The London Funeral Singers** (londonfuneralsingers.co.uk) | Funeral soloists, choirs of 4/8/12, organists. The funeral specialist; ranks first for "funeral choir" and "funeral choir hire london". Sister brand **Rawle & Shipley** for weddings and corporate (same phone, no prices). | Published list, all **+ VAT**: soloist £275, choir of four £1,400, eight £2,400, twelve £4,000, organist £275, Mass responses add-on £35. Travel extra outside London. | "150+ auditioned singers", Royal Albert Hall and opera houses, "award-winning", press features (Stylist, VICE), Trustpilot profile. | **Yes**, two ads last shown 22–23 Oct |
| **The London Funeral Choir** (londonfuneralchoir.com) | New funeral-only choir site; second for both funeral queries. Instagram has a handful of followers. | None seen. | Little. | Not found |
| **Dream Gospel Choir** (on Last Minute Musicians) | Gospel choir for funerals, weddings, corporate. | Full funeral list: 4 £1,349, 8 £2,339, 11 £3,119. VAT not stated. Travel free within 25 miles of East London, then 45p a mile per vehicle. | Directory reviews. | Not checked by name |
| **Euphony Voices** (Encore, Poptop, FreeIndex) | Classical quartet for weddings, funerals, carols. Cheapest classical option seen. | Encore "From £662.50" for four, up to an hour; Poptop "from £650". | 80+ marketplace reviews. | — |
| **The London Wedding Choir** (londonweddingchoir.com, Encore) | Wedding choir, 4–16 singers. Ranks first for "wedding choir hire london". | Encore: £1,250 for four, up to an hour; ceremony package £3,125. | Encore reviews. | — |
| **Gospel Touch (GT Choir)**, **BIG Gospel Choir**, **Get Gospel** | Gospel choirs for weddings, some funerals. Hold the **local pack** for "hire a choir" and "wedding choir hire london". | BIG Gospel on Encore £3,733.75–£4,632.50. Others: none. | 83, 79 and 43 Google reviews. | GT and BIG **yes**, active 23 Oct |
| **Some Voices**, **Coro**, **Collegium Musicum**, **London Contemporary Voices** | Community or chamber choirs offering hire. Rank on "hire a choir" and "wedding choir hire london". | LCV on Encore "From £1600"; Some Voices on Hitched "from £2000". | Press, festival credits. | No |
| **Music for London Ltd** | Carol trios and quartets, gospel and show choirs. | "from £650.00 for a traditional vocal trio and range from £750.00 to £1,250+" for quartets. VAT not stated. | 558 testimonials, WhatsApp link. | — |
| **Julia Charles Event Management** | Agency; several carol acts. | Victorian carollers "From £945 Subject to VAT + Travel". | Agency portfolio. | No |
| **Alive Network** | Agency; Victorian and Christmas carollers. | Victorian quartet "From £1,079", travel extra; the same act shows £1,196 on another page. | "194,000 events booked", review stars. | Yes, not for choirs |
| **London Carol Singers** (londoncarolsingers.com) | Opera-singer carol quartets and duets; holds the knowledge panel for "carol singers for hire london" (14 Google reviews). | In its ads: duets from £445 or £535, quartets from £640 or £765, by the half-hour. | "Award-winning", "London's premier". | **Yes**, 29 Sep–4 Oct. The advertiser is registered in Australia. |
| **Singers for Funerals**, **Hartley Voices**, **Surrey Funeral Singers** | Soloist-led funeral and memorial music, west and south-west fringe. | Singers for Funerals on Encore "From £220". | Blogs ranking for "funeral choir". | Singers for Funerals last ran 31 May |

**Marketplaces**, which dominate every hiring query: Encore Musicians (London choirs "£340 – £4000+", 910 reviews shown as stars in the results), Poptop ("£600 to £1680, avg: £998", 3,752 reviews), Gig Heaven, Alive Network, Add to Event, Eventzone, Bands For Hire, Hitched listings. Their result snippets show review stars and price ranges, which no single-provider page can show because we may not add review schema.

### 1.2 How we compare on price

For four singers a family pays The London Funeral Singers **£1,680** (£1,400 + VAT) and us **£1,150**; for eight, £2,880 against £2,000; for twelve, £4,800 against £3,000. Dream Gospel's £1,349 for four is the nearest published funeral rival. On carols, Julia Charles's £945 + VAT is £1,134 before travel; our £1,150 for four singers for up to two hours includes London travel. The agencies' "from" prices usually cover three singers, or under an hour.

### 1.3 Gaps nobody claims, and where we stand

| Gap (no rival says it) | Do we already say it? | What to do |
|---|---|---|
| **One price, nothing added**: no VAT, London travel included | Yes, in the Christmas ads ("No VAT Added to Any Price") and on pricing.html | Make it the second line of the hero on funerals.html and weddings.html, and add it to the funeral and wedding ads (§2.3). It is the biggest difference from LFS (£1,680 vs £1,150). |
| **Illness cover in writing** | Yes: funerals.html and faq.html ("we cover the part from within the team… not cancelled for reasons on our side"); terms clause 7 | LFS says only that it can "almost always replace" a singer. Move our line up to the hero facts on funerals.html. |
| **A named musical director** | Yes (Luca Wetherall, Oxford) | Keep. LFS has only an unnamed "organist-conductor" at twelve voices. |
| **Small team that sings together, as the reason for quality** | Yes, in principle | Rivals sell scale ("150+", "over 1,000 singers"). Keep the opposite framing; never give a number. |
| **Five- and six-voice prices** | Yes (£1,400 and £1,600) | No classical rival prices these. Show them in the size tables proposed in §3. |
| **Organist at a flat £250 however booked** | Yes | LFS charges £330 with VAT. Say it beside the funeral size table. |
| **Deposit and cancellation terms on the provider's own site** | Yes (terms.html) | Only marketplaces show theirs. Link "Booking terms in plain English" from the funeral and wedding pages, next to the price. |
| **Repertoire lists for each occasion, no extra charge** | Partly (music guides) | Link the funeral and wedding repertoire guides from the price tables with "any of these, no extra charge". |
| **Working with the church**: clergy, the church's own organist, music rules | Partly | One short section on weddings.html and funerals.html. Keep the London cathedral rule: never say we join a cathedral or Abbey choir. |
| **Same-day reply** | Yes on funerals ("confirm availability the same day"); ads say "Quote in 1 working day" | Fine as is. |

### 1.4 Competitor figures added to `data/competitor-pricing.yml`

Every figure we might use is now in the data file with a verbatim quote and a checked date of 2026-10-24. No page uses them yet, and `compare/` is unchanged.

- LFS: the Mass-responses add-on, "Add singing Mass responses £35 + VAT".
- Dream Gospel Choir: funeral 4 £1,349, 8 £2,339, 11 £3,119.
- Music for London: carol trio from £650, quartet from £750.
- Julia Charles: Victorian carollers from £945 + VAT.
- Alive Network: Victorian quartet from £1,079.

Three of these rivals print no VAT treatment. The validator now accepts `price_as_quoted` for such a package: a compare page may print that figure, but never a derived "+ VAT" one. A test covers it. Marketplace ranges and LFS's older figures, seen only in search snippets (soloist £295, four £1,250, eight £1,950), are left out on purpose.

**Proposal, not done:** if a carol comparison is wanted, it belongs in `music-guides/booking-carol-singers-agency-vs-direct.html`, which addresses business buyers. Use ex-VAT figures there, since those buyers reclaim VAT, and keep it off `compare/`, which is for families.

---

## 2. Ad landscape (observations only)

### 2.1 Who advertises in the UK

| Advertiser | Ads | Last shown | Message |
|---|---|---|---|
| The London Funeral Singers | 9 (7 text, 1 video, 1 image) | 22–23 Oct (two live) | "Funeral Singers In Camberley - We Coordinate Everything - Book Now"; "Soloists, Choirs & More - Available Across The UK". Royal Albert Hall and opera houses, "150+ auditioned singers", "Award-Winning", short notice. Headlines and sitelinks named after **Home Counties places** (Camberley, Surrey, Berkshire, Bedfordshire). **No prices in the ads**, only a "Price Plans" sitelink. |
| BIG Gospel Choir | 39 | 23 Oct | "Luxury Gospel choir for weddings", "UK's premier gospel choir", funeral ads ("Bespoke Music for Cremations"). No prices. |
| Gospel Touch Ltd (GT Choir) | 5 | 23 Oct | "Gospel Choir For Your Wedding"; lead-form asset; ran a funeral ad until March. No prices. |
| London Carol Singers ("Jassy Husk", Australia) | 5 | 29 Sep–4 Oct | The only rival with **prices in its ads**: "Duets from £445. Quartets from £640"; later "Duets from £535, Quartets from £765, Hire by the half-hour". |
| Ingrid Wallis (solo Irish funeral singer) | 1 image | 19 Oct | Sidcup, repatriation, Catholic hymns. A soloist, outside our targeting. |
| Singers for Funerals | 1 | 31 May | "Refreshingly Affordable". Not running. |
| Marketplaces: Encore (98), Warble/Entertainment Nation (79 and about 300), Alive Network (32), Last Minute Musicians (27), Freak (12), Bark | many | live | Generic bands and acts; "0% Booking Fee", "Thousands Of 5-Star Reviews", seller-rating stars. No choir-specific ad seen in the samples. |
| Poptop, Julia Charles | 0 | — | Not advertising. |

### 2.2 What it means

- **Funerals:** LFS is the only serious funeral-choir bidder, and its ads carry no price. Ours lead with "Funeral Choir from £1,150" (pinned), which is the clearest contrast available. LFS also bids on Surrey and Berkshire town names, which are inside our funeral campaign's area.
- **Weddings:** the live wedding bidders are gospel choirs selling "luxury" and "premier". None shows a price; ours does. That is the right difference to hold.
- **Christmas:** only one carol-singer rival has advertised this season, with half-hour prices below ours. Its quartet "from £640" is for half an hour; our £1,150 covers up to two hours with breaks, and the live ads already say "Up to 2 Hours, Breaks Included". Keep that headline in rotation.
- **Our own listing:** the Transparency Center shows our ads under **Alma Consort**, the verified company name, and lists only two old ads (last shown 25 Sep) with "All Prices Include VAT" and "Soloists From £215". Checked in the account on 24 Oct: every enabled ad is clean, and those old callouts, sitelinks and text assets are **paused**. Nothing to fix; the Center is showing history.

### 2.3 Proposed ad changes (for scripts/ads, with Luca's approval; nothing applied)

1. **No VAT headline: not needed.** (Corrected 24 Oct.) The 23 Oct change set removed "No VAT Added, No Extras" from the funeral and wedding ads on purpose, because "no extras" is false for the home-counties audience, who pay travel. Those ads already say "no VAT" through the account callout "No VAT Added" and the price sitelinks ("No VAT, travel in London included"), so there is nothing to add.
2. **funeral expert campaign**: test one headline naming the Home Counties ("Funeral Choirs in Surrey & Kent"), matching where LFS bids, but only if the search-terms report shows impressions from those places. Location targeting stays as it is.
3. No change to Christmas copy: it already answers the only priced carol rival on length and travel.

---

## 3. Search intent: what Google ranks, and what we rank

### 3.1 Results seen on google.co.uk, 24 Oct 2026

| Query | What Google shows (organic, in order) | Dominant type | Our page and position |
|---|---|---|---|
| **funeral choir** | Video carousel (an unrelated film song); **LFS** with sitelinks; People Also Ask; London Funeral Choir; **LCS /funerals.html**; Surrey Funeral Singers; a Singers for Funerals blog post ("I need a choir for a funeral… or do I?"); LFC's Instagram. | Specialist service pages | /funerals.html, **third organic** in this browser. Search Console's 7-day average for funeral head terms is much lower, so treat this as a good day, not a settled rank. |
| **funeral choir hire london** | LFS; London Funeral Choir; PAA ("Can you hire a choir for a funeral?", "How much do singers charge for funerals?", "How much is it to hire a church choir?"); **LCS /areas/london.html** ("From £250"); Encore choirs; Eventzone funeral singers; Royal Holloway chapel choir; Wake Venues' LFS listing; Hartley Voices; Collegium Musicum. | Service pages, then marketplaces | **/areas/london.html**, third. Google prefers the London area page to /funerals.html for the "london" variant. |
| **wedding choir hire london** | Gospel Touch business panel (83 reviews); London Wedding Choir; Encore; Poptop (price range and stars); Collegium; Some Voices; PAA ("How expensive is it to hire a choir?", "How much do wedding singers charge in the UK?"); Bands For Hire; Coro; Hitched listing; Encore profile. | Marketplaces and choirs' own hire pages, with a business panel | **Not in the top 10.** Search Console: "wedding choir" 38.8, landing on the **homepage**, not /weddings.html. |
| **hire a choir** | Encore; **local pack** (Gospel Touch 83 reviews, Get Gospel 79, BIG Gospel 43); Collegium; PAA; Poptop; Some Voices; Coro; Soul Sanctuary Gospel; West End Musical Choir; Gig Heaven; Hart Male Voice Choir. "People also search for" mixes in joining a choir. | Marketplaces plus a local pack | **Not in the top 10.** Search Console: the hiring guide at 12; "choir for hire" 34.5 on the homepage. |
| **carol singers for hire london** | London Carol Singers knowledge panel (14 reviews); Encore carol singers; Poptop carolers; PAA; London Contemporary Voices; Music for London; Alive Network (twice); Hartley Voices; carolsingershire.uk; Gig Heaven. | Marketplaces and agencies, with a business panel | **Not in the top 10.** Search Console: "carol singers london" 8.7, "carolers for hire" 24.5, both on /carol-singers.html, which is a noindex page canonical to /christmas.html, so those impressions should move to /christmas.html. |
| **how to book a choir** | PAA ("How expensive is it to hire a choir?", "How much do choirs charge?"); Encore; Some Voices; Rock Choir (joining); Live Entertainment agency; Collegium; Love Soul Choir's "How To Book A Choir For Your Event [7 TIPS]"; Soul Sanctuary; Purcell Singers' "How to book the choir". | Mixed: hire pages plus one listicle guide; part "join a choir" intent | /music-guides/hiring-a-choir.html, average **13.9** over 90 days (161 impressions), shown by Search Console in the results page. |

Three patterns run through all six:

1. **Marketplaces win the generic hiring queries.** Their snippets carry a price range and review stars. A single provider cannot become a marketplace, but it can give the same two things a searcher scans for: a price for each size, and evidence.
2. **Local packs and business panels go to gospel choirs and a carol act with 14–83 Google reviews.** Our Business Profile had no reviews at the 23 October audit, so it does not appear. This is a review-count gap, not a page gap.
3. **Specialist service pages still win where the query names the occasion** ("funeral choir"). There, we are already competitive.

### 3.2 Proposals by page

| Page | Mismatch | Change |
|---|---|---|
| **/weddings.html** + **index.html** | The homepage title ("Professional Funeral Singers & Wedding Choirs") pulls "wedding choir" and "choir for hire" away from /weddings.html, and both rank 35–39. Wedding results are marketplace lists with prices and stars. | (a) Retitle the homepage to a general hire title (for example "Choirs for Hire in London: Funerals, Weddings, Christmas"), and link /weddings.html from the homepage with the anchor "wedding choir hire". (b) On /weddings.html, add a "Which wedding choir suits your ceremony?" table: size × venue size × moments covered × price, from pricing.html (4 £1,150, 5 £1,400, 6 £1,600, 8 £2,000, 12 £3,000, organist £250). (c) Move one wedding testimonial and the credits line to the first screen. (d) FAQ: "How much does a wedding choir cost in London?", "Will our church let us bring a choir?". Gospel is prominent in this result set; whether to mention it, even to say we don't offer it, is Luca's call. |
| **/funerals.html** | Already third for "funeral choir". The "london" variant goes to /areas/london.html. | (a) Add a funeral size table beside the price: soloist £250, 4 £1,150, 5 £1,400, 6 £1,600, 8 £2,000, 12 £3,000, organist £250 however booked. (b) Answer the PAA questions as FAQ entries ("Can you hire a choir for a funeral?", "How much do funeral singers charge?", "How much is it to hire a church choir?"). (c) Put "no VAT added" and the illness-cover line in the hero facts. (d) Link /compare/london-funeral-singers.html from the price table; compare/ is for families, so that link is allowed here. |
| **/areas/london.html** | It is the page Google picks for "funeral choir hire london". | Give it a short funeral section with the price and a prominent link to /funerals.html ("funeral choir hire in London"), so whichever page Google chooses converts. Don't fight the choice. |
| **/music-guides/hiring-a-choir.html** | The right page type for "hire a choir" and "how to book a choir", but the H1 ("What to expect when you hire a choir") doesn't match either query, and costs are prose. | (a) H1: "How to hire a choir: steps, costs and the day". (b) A costs table with the pricing.html figures, including "Christmas Eve and Christmas Day carry a premium of around 25%". (c) A "three ways to hire" table: marketplace or listing site, agency, or a professional ensemble direct; rows for who you deal with, whether the singers already sing together, booking fees, how prices are shown, lead time. (d) A short line for readers who want to join a choir, which keeps them from bouncing. |
| **/christmas.html** | Results are marketplaces and agencies; our redirect stub /carol-singers.html still collects the impressions. | (a) A "Choose your carol singers" table: format (roaming, lobby sets, office carol service, outdoors) × size × price for up to two hours. (b) Link `music-guides/best-christmas-carol-singers.html`, `carol-singers-cost.html` and `booking-carol-singers-agency-vs-direct.html` from it. (c) Point any remaining internal links at /christmas.html, not /carol-singers.html. Don't build a "best carol singers in London" list naming rivals. |

House rules apply to all of these: no roster size, never imply VAT registration, prices only from pricing.html, no review or rating schema, the London cathedral rule, and new copy through the `writing-site-copy` and `stop-slop` skills.

---

## 4. Link gap

No page checked links to us. The useful finding is how few editorial pages name any choir-hire firm at all; most of the gap is marketplaces.

| Source | Type | Names or links | How to get on it | Priority |
|---|---|---|---|---|
| Poetic Endings: "Singers and musicians for funerals (in London)", two pages | Funeral planner's resource | Links only to LFS | Editorial request to be added as a London choir option | **High**: it sends families to the rival now |
| Stationers' Hall, recommended music suppliers | City livery hall (weddings, Christmas parties, memorial receptions) | Lists agencies, **no choir** | Supplier application | High |
| Royal Borough of Kensington and Chelsea, approved wedding suppliers (Chelsea Old Town Hall) | Council register-office supplier list | Lists music suppliers, **no choir** | Supplier application | High |
| Julia Charles; Sternberg Clarke | Corporate and Christmas agency rosters | London Carollers, London Christmas Carollers, Voices of London, Candlelight Choir | Apply as a roster act | Medium (agency fees) |
| Last Minute Musicians | Paid directory, no commission | Euphony Voices, Dream Gospel; **LFS's profile has lapsed** | £59.99 for 6 months | Medium |
| FreeIndex | Free business directory | Euphony Voices (wedding and funeral choir) | Free listing | Medium (citation value) |
| Encore (choirs, carol singers, church and gospel choirs, London) | Marketplace | Most rivals | Already planned in the listings pack | Planned |
| Bridebook, Guides for Brides | Wedding directories | Wedding Singers; CK Gospel Choir | Already planned | Planned |
| weddingplanner.co.uk | Wedding directory | A London ceremony-music agency | Supplier sign-up; not in the pack | Low |
| Stylist; VICE; Funeral Service Times (unverified) | Press | LFS founder and business features | Editorial pitch: a business story, not a listing | Low, slow |
| The Good Funeral Guide (2010 post on Singers for Funerals) | Funeral resource | Singers for Funerals | Editorial pitch; its directory lists only funeral directors | Low |
| Add to Event | Pay-per-lead marketplace | Rawle & Shipley (names LFS as its sister), 18 London choirs | Skipped on purpose in the pack | Skip |
| NAFD and SAIF supplier membership | Funeral trade bodies | An old listing calls LFS an NAFD supplier member (unverified) | Paid membership | Ask Luca |

Searches of RSCM, Fair Funerals, Quaker Social Action, Coco Wedding Venues, Rock My Wedding, The Wedding Secret and the London Wedding Guide found no page naming a choir-hire rival.

The incorporated firms worth contacting from this table (four, each checked at Companies House on 24 Oct) are in the private outreach list as prospects. Emails go only as drafts that Luca sends, under the outreach rules in CLAUDE.md. The directory listings belong in `docs/off-site-listings-pack.md` when the next listings round runs.

---

## 5. Top five actions

1. **/weddings.html and the homepage title:** retitle index.html so it stops competing for "wedding choir" and "choir for hire". Add the wedding size-and-price table and move proof to the first screen of /weddings.html. Ranking 35–64 against marketplace lists is the biggest gap.
2. **/music-guides/hiring-a-choir.html:** match the H1 to "hire a choir" and "how to book a choir", and add the costs table and the "three ways to hire" table. It already sits at 12–14, the closest of our pages to page 1 on a generic hiring query.
3. **Google Business Profile reviews:** the local pack for "hire a choir" and the panels for "wedding choir hire london" and "carol singers for hire london" go to acts with 14–83 Google reviews. Our profile had none at the 23 October audit. The daily pass already drafts review requests (never to funeral clients), but they carry the direct Google review link only once `gbp_review_url` is filled in (MANUAL-ACTIONS §23). That link is the one step blocking the only route into those boxes.
4. **funerals.html and weddings.html hero facts:** say "no VAT added" next to the £1,150 price (done in PR #338). The ads already carry it through the account callout and price sitelinks; LFS, the only serious funeral bidder, prices at + VAT and shows no price in its ads.
5. **Poetic Endings, Stationers' Hall and the Kensington and Chelsea supplier list:** one sends families to LFS today; the other two list music suppliers but no choir. Draft the outreach emails, and send the two supplier applications.

Also worth doing: the funeral size table and PAA answers on /funerals.html; the carol format table and guide links on /christmas.html; the free FreeIndex listing and the £59.99 Last Minute Musicians listing in the next listings round.
