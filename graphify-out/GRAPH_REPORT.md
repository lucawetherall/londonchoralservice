# Graph Report - site-audit-improvements-47d735  (2026-09-04)

## Corpus Check
- 158 files · ~1,628,608 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1167 nodes · 1576 edges · 85 communities (82 shown, 3 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.89)
- Token cost: 180,000 input · 9,500 output

## Community Hubs (Navigation)
- Core Site Pages & Schema
- London Borough Venues
- Christmas & Corporate Carol Guides
- Barnet Borough
- Bexley Borough
- Analytics, Ads & Cookie Consent
- Harrow & Hillingdon Boroughs
- Slough & Maidenhead Area
- Wedding Organ Repertoire
- Wedding Music & Ensembles
- A Cappella Christmas Songs
- Luca Wetherall's Credentials
- Abide With Me Guide
- Ensemble Tiers & Areas Served
- Wedding Pop Songs
- Wedding Choral Repertoire
- Barking & Dagenham Borough
- City of London Borough
- Croydon Borough
- Hammersmith & Fulham Borough
- Kingston upon Thames Borough
- Barbershop Grams Mini-Site
- Bromley Borough
- Ealing Borough
- Enfield Borough
- Newham Borough
- Wedding Song Arrangements
- Brent Borough
- Hackney Borough
- Haringey Borough
- Havering Borough
- Kensington & Chelsea Borough
- St Albans Area
- Basingstoke & Hampshire Area
- Barbershop Gram Enquiry Flow
- Barbershop Grams Roadmap & Plan
- Wedding Ceremony Music Guide
- Salisbury Area
- Lambeth Borough
- Barbershop Competitive Position
- Site Improvement Roadmap
- Hounslow Borough
- Non-Religious Funeral Music
- Funeral Hymns
- Choir & Singer Pricing
- Birmingham Area
- Islington Borough
- Barbershop Build Tasks
- Funeral Singers Comparison
- Be Thou My Vision Guide
- Choosing Singers & Market Rates
- Sitemap Generator
- Bath Area
- Areas We Serve Index
- Barbershop Repertoire Groups
- Brighton Area
- Lewisham Borough
- Cookie Consent Script
- Guildford Area
- Liverpool Area
- Manchester Area
- Soloist & Accompanist Pricing
- Cambridge Area
- Canterbury Area
- Chelmsford Area
- Chester Area
- Wandsworth Borough
- Oxford Area
- Reading Area
- Rochester Area
- Booking Carol Singers Direct
- Carol Lyrics & Meanings
- Gram Occasions
- Carol Singers for Law Firms
- Celebration of Life Music
- Charity Carol Concerts
- Make You Feel My Love
- Full Choir Tier
- Sextet Tier
- Small Choir Tier
- Alma Consort Ensemble
- Barbershop Footer & Link Rule
- Residents' Carol Events

## God Nodes (most connected - your core abstractions)
1. `Funeral and Wedding Choirs in London (page)` - 59 edges
2. `Luca Wetherall, Artistic Director (profile page)` - 38 edges
3. `Wedding Choirs & Singers (page)` - 36 edges
4. `Choir and Singer Pricing (page)` - 33 edges
5. `Music Guides (hub)` - 29 edges
6. `Music for Funerals, Weddings, and Ceremonies (page)` - 24 edges
7. `Popular Songs on the Organ at Your Wedding` - 24 edges
8. `Areas We Serve — Funeral & Wedding Choirs in the UK (page)` - 21 edges
9. `Luca Wetherall (Artistic Director)` - 21 edges
10. `The London Choral Service` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Barbershop Grams hub page` --references--> `Barbershop Grams Social Preview Image`  [EXTRACTED]
  barbershop-grams/index.html → assets/og-barbershop-grams.png
- `FAQ Page` --semantically_similar_to--> `Contact Us Page`  [INFERRED] [semantically similar]
  faq.html → contact.html
- `Soloist — 1 singer, from £250` --semantically_similar_to--> `Soloist — 1 voice`  [INFERRED] [semantically similar]
  pricing.html → services.html
- `Soloist — £250` --semantically_similar_to--> `Soloist — 1 singer, from £250`  [INFERRED] [semantically similar]
  weddings.html → pricing.html
- `Small Choir — 4 singers, from £1,150` --semantically_similar_to--> `Small Choir — 4 singers`  [INFERRED] [semantically similar]
  pricing.html → services.html

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **B2B 'For-*' Professional Landing Pages Family** — for_charities_page, for_event_managers_page, for_funeral_directors_page, for_hotels_page, for_livery_companies_page, for_property_managers_page, for_wedding_planners_page, concept_for_star_landing_pages [EXTRACTED 0.90]
- **Pages sharing the nav/footer/head-extras/analytics partials and inlined design system** — 404_page, about_page, accessibility_page, carol_singers_page, christmas_page, contact_page, corporate_page, faq_page, for_charities_page, for_event_managers_page, for_funeral_directors_page, for_hotels_page, for_livery_companies_page, for_property_managers_page, for_wedding_planners_page, funerals_page, index_page, listen_page, partials_nav_html, partials_footer_html, concept_site_design_system [EXTRACTED 0.95]
- **Christmas/carol-singer pillar content cluster (Sept 2026 audit scope)** — christmas_page, carol_singers_page, for_hotels_page, for_livery_companies_page, for_charities_page, for_property_managers_page, for_event_managers_page, manual_actions_christmas_season_prep [INFERRED 0.85]
- **Areas We Serve collection: index page grouping dedicated city pages** — areas_index_areas_we_serve, areas_bath_page, areas_birmingham_page, areas_london_page, areas_manchester_page, areas_oxford_page, areas_cambridge_page [EXTRACTED 0.90]
- **Small Choir (4 singers, from £1,150) as one consistent product referenced across pricing, services, and weddings pages** — pricing_small_choir_ensemble, services_small_choir_ensemble, weddings_small_choir_ensemble [INFERRED 0.90]
- **Luca Wetherall (Artistic Director, Tutor in Music at Oxford) referenced as the consultation point across service pages** — luca_wetherall_luca_wetherall, pricing_choir_and_singer_pricing, services_music_for_funerals_weddings_and_ceremonies, weddings_wedding_choirs_singers [EXTRACTED 0.90]
- **Home-counties city page shared template** — areas_salisbury_page, areas_slough_maidenhead_page, areas_st_albans_page, areas_winchester_page, areas_windsor_page [INFERRED 0.85]
- **London borough page shared template** — areas_london_barking_dagenham_page, areas_london_barnet_page, areas_london_bexley_page, areas_london_brent_page, areas_london_bromley_page, areas_london_camden_page, areas_london_city_of_london_page, areas_london_croydon_page, areas_london_ealing_page, areas_london_enfield_page, areas_london_greenwich_page, areas_london_hackney_page, areas_london_hammersmith_fulham_page, areas_london_haringey_page, areas_london_harrow_page, areas_london_havering_page, areas_london_hillingdon_page [INFERRED 0.85]
- **Golders Green Crematorium shared coverage (Camden & Barnet)** — areas_london_camden_page, areas_london_barnet_page, areas_london_camden_golders_green_crematorium, areas_london_barnet_golders_green_crematorium [INFERRED 0.95]
- **Barbershop Gram booking / Send-a-Gram flow** — barbershop_grams_index_page, barbershop_grams_index_send_a_gram, barbershop_grams_index_enquiry_form, barbershop_grams_repertoire_page [INFERRED 0.85]
- **Barbershop Grams product line shipment (R14)** — docs_roadmap_r14_barbershop_grams, docs_superpowers_plans_2026_09_03_barbershop_grams_page, barbershop_grams_index_page, barbershop_grams_repertoire_page [EXTRACTED 1.00]
- **Mutually cross-linked bordering boroughs (Lambeth, Southwark, Wandsworth, Westminster)** — areas_london_lambeth_page, areas_london_southwark_page, areas_london_wandsworth_page, areas_london_westminster_page [INFERRED 0.95]
- **Christmas/Advent carol repertoire guidance cluster** — music_guides_a_cappella_christmas_songs_guide, music_guides_best_carols_for_four_voices_guide, music_guides_christmas_carols_guide_guide, music_guides_advent_carols_vs_christmas_carols_guide [INFERRED 0.75]
- **Funeral music/hymn selection guidance cluster** — music_guides_abide_with_me_guide, music_guides_be_thou_my_vision_funeral_hymn_guide, music_guides_catholic_funeral_hymns_guide, music_guides_anima_christi_catholic_funeral_guide, music_guides_celebration_of_life_music_guide, music_guides_best_funeral_singers_london_guide [INFERRED 0.75]
- **Corporate/institutional carol-singing booking guidance cluster** — music_guides_carol_singers_cost_guide, music_guides_carol_singers_law_firms_guide, music_guides_best_christmas_carol_singers_guide, music_guides_booking_carol_singers_agency_vs_direct_guide, music_guides_charity_carol_concert_guide, music_guides_carols_by_candlelight_guide [INFERRED 0.75]
- **Christmas carol service hire content cluster** — music_guides_nine_lessons_and_carols_nine_lessons_and_carols, music_guides_corporate_carol_service_corporate_carol_service, music_guides_church_carol_service_choir_hire_church_carol_service_choir_hire, music_guides_christmas_choir_hire_christmas_choir_hire [INFERRED 0.85]
- **Funeral music planning and cost guidance cluster** — music_guides_funeral_music_guide_funeral_music_guide, music_guides_funeral_choir_guide_funeral_choir_guide, music_guides_funeral_music_costs_funeral_music_costs, music_guides_funeral_songs_funeral_songs, music_guides_hiring_a_choir_hiring_a_choir, music_guides_last_minute_funeral_singers_last_minute_funeral_singers, music_guides_crematorium_music_crematorium_music, music_guides_memorial_service_planning_memorial_service_planning [INFERRED 0.85]
- **Wedding choral repertoire selection cluster** — music_guides_humanist_wedding_music_humanist_wedding_music, music_guides_jerusalem_jerusalem, music_guides_lesser_known_wedding_choral_pieces_lesser_known_wedding_choral_pieces, music_guides_destination_wedding_choir_destination_wedding_choir [INFERRED 0.75]
- **Barbershop Grams mini-site: shared nav and scoped CSS partials** — partials_barbershop_nav_barbershop_grams_navigation, partials_barbershop_register_css_barbershop_register_design_tokens, barbershop_grams_index_barbershop_grams_hub_page, barbershop_grams_repertoire_barbershop_grams_repertoire_page [INFERRED 0.85]
- **Wedding organ music content cluster** — music_guides_popular_wedding_organ_music_popular_wedding_organ_music, music_guides_wedding_organ_repertoire_the_best_organ_pieces_for_a_wedding, music_guides_wedding_organist_guide_hiring_an_organist_for_your_wedding, music_guides_wedding_organ_pop_songs_popular_songs_on_the_organ_at_your_wedding [INFERRED 0.85]
- **Contemporary pop songs arranged across choral, organ, and choir wedding guides** — music_guides_wedding_choral_repertoire_a_thousand_years_christina_perri, music_guides_wedding_organ_pop_songs_a_thousand_years_christina_perri, music_guides_wedding_pop_songs_choir_a_thousand_years_christina_perri [INFERRED 0.85]

## Communities (85 total, 3 thin omitted)

### Community 0 - "Core Site Pages & Schema"
Cohesion: 0.08
Nodes (63): 404 Page Not Found, About Our Musicians Page, Accessibility Statement Page, Hire Carol Singers Page, Christmas Carol Services Page, CLAUDE.md (project instructions), GA4/Ads Consent Mode v2 Snippet, Build Pipeline (build.sh, partials, css generation) (+55 more)

### Community 1 - "London Borough Venues"
Cohesion: 0.06
Nodes (55): BBC Proms, Barking & Dagenham — St Margaret's Barking, Eastbrookend Cemetery, Rippleside Cemetery, Barnet — Hendon Crematorium, Golders Green Crematorium, St John the Baptist Chipping Barnet, Bexley — St Mary the Virgin Bexley, Eltham Crematorium, Brent — St Mary's Willesden, Willesden New Cemetery, Bromley — Beckenham Crematorium, St Peter & St Paul Bromley, All Saints Orpington, Camden — Hampstead Parish Church, St Pancras New Church, St Michael's Highgate, City of London — St Paul's Cathedral, Temple Church, St Bartholomew-the-Great (+47 more)

### Community 2 - "Christmas & Corporate Carol Guides"
Cohesion: 0.10
Nodes (48): Hiring a choir for your Christmas event, Music for a Christmas drinks reception, Music for a Christmas gala or awards dinner, Hiring a choir for a church carol service, Live choral music for company Christmas parties, Planning a corporate carol service, Choosing music for a crematorium service, Crematorium service structure and timings (+40 more)

### Community 3 - "Barnet Borough"
Cohesion: 0.07
Nodes (39): Barnet, Can you provide a choir for a wedding in Barnet?, Christmas carol singers section, Do you cover crematorium services in Barnet?, East Finchley Cemetery, Ensembles & pricing section, Frequently asked questions section, Funeral music section (+31 more)

### Community 4 - "Bexley Borough"
Cohesion: 0.07
Nodes (32): Bexley, Can you provide a choir for a wedding in Bexley?, Christmas carol singers section, Do you cover crematorium services in Bexley?, Eltham Crematorium, Ensembles & pricing section, Frequently asked questions section, Funeral music section (+24 more)

### Community 5 - "Analytics, Ads & Cookie Consent"
Cohesion: 0.07
Nodes (32): Alma Consort Ltd, _ga / _ga_* cookies (Google Analytics, up to two years), _gcl_au cookie (Google Ads, three months), Google Ads conversion tag, Google Analytics, Google Analytics opt-out browser add-on, hCaptcha (spam protection), lcs-consent cookie (stores cookie choice) (+24 more)

### Community 6 - "Harrow & Hillingdon Boroughs"
Cohesion: 0.08
Nodes (31): Breakspear Crematorium, Can you provide a choir for a wedding in Harrow?, Christmas carol singers section, Do you cover crematorium services in Harrow?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, Harrow (+23 more)

### Community 7 - "Slough & Maidenhead Area"
Cohesion: 0.08
Nodes (31): All Saints Maidenhead, Berkshire, Can you provide a choir for a wedding in Slough and Maidenhead?, Chilterns Crematorium, Christmas carol singers section, Do you cover crematorium services in Slough and Maidenhead?, Ensembles & pricing section, Frequently asked questions section (+23 more)

### Community 8 - "Wedding Organ Repertoire"
Cohesion: 0.10
Nodes (30): Air on the G String (Bach, c.1730), Arrival of the Queen of Sheba (Handel, 1748), Bridal Chorus (Wagner, 1850), Canon in D (Pachelbel, c.1680), Clair de Lune (Debussy, 1905), Crown Imperial (Walton, 1937), Hornpipe from Water Music (Handel, 1717), Imperial March (Elgar, 1897) (+22 more)

### Community 9 - "Wedding Music & Ensembles"
Cohesion: 0.07
Nodes (30): Alma Consort Ltd (trading as The London Choral Service), Anima Christi — Marco Frisina (Quintet, Nuptial Mass Communion), Ave Maria — Schubert (Soloist, most-requested piece), Barbershop quartet (reception entertainment, roams the room), Be Thou My Vision (Full Choir, 8th-c. Irish text, tune Slane), Be Thou My Vision as a wedding hymn (guide), Best wedding choirs in London (guide), Choosing a wedding organist (guide) (+22 more)

### Community 10 - "A Cappella Christmas Songs"
Cohesion: 0.08
Nodes (27): Close-harmony arrangement (concept), Coventry Carol, Fairytale of New York, A Cappella Christmas Songs for a Choir, Have Yourself a Merry Little Christmas, White Christmas, Advent season (liturgical concept), Coventry Carol (+19 more)

### Community 11 - "Luca Wetherall's Credentials"
Cohesion: 0.08
Nodes (24): Luca Wetherall, Tutor in Music, University of Oxford (team reference), Armonico Consort, BBC Singers, Choir of Merton College Oxford, Company Carpi (Music Supervisor/conductor role), Disunited Jukebox (Arts Council-funded opera tour), Ensemble Pro Victoria, Illumni Men's Chorale (+16 more)

### Community 12 - "Abide With Me Guide"
Cohesion: 0.09
Nodes (22): Abide With Me (hymn), Eventide (tune), FA Cup Final (association), Abide With Me — the most-requested funeral hymn, Henry Francis Lyte, William Henry Monk, Anima Christi (prayer), Anima Christi at a Catholic Funeral (+14 more)

### Community 13 - "Ensemble Tiers & Areas Served"
Cohesion: 0.10
Nodes (20): Chorus — 12 singers, from £3,000, Quintet — 5 singers, from £1,400, Alma Consort Ltd (trading as The London Choral Service), Brighton (area served), Cambridge (area served), London (area served), Manchester (area served), Oxford (area served) (+12 more)

### Community 14 - "Wedding Pop Songs"
Cohesion: 0.11
Nodes (19): A Thousand Years (Christina Perri, 2011), Ain't No Mountain High Enough (Marvin Gaye & Tammi Terrell / Diana Ross), All I Ask of You from The Phantom of the Opera (Andrew Lloyd Webber, 1986), All of Me (John Legend, 2013), All You Need Is Love (The Beatles, 1967), At Last (Etta James, 1960), Can You Feel the Love Tonight from The Lion King (Elton John & Tim Rice, 1994), Cinema Paradiso love theme (Ennio Morricone, 1988) (+11 more)

### Community 15 - "Wedding Choral Repertoire"
Cohesion: 0.12
Nodes (18): Maurice Durufle's Ubi Caritas setting (comparison), Ola Gjeilo's Ubi Caritas setting, Ubi Caritas at a wedding - Ola Gjeilo's setting, A Gaelic Blessing (Rutter), A Thousand Years (Christina Perri, choral arr.), Ave Maria (Bach/Gounod or Schubert), Ave Verum Corpus (Mozart), Brother James's Air (+10 more)

### Community 16 - "Barking & Dagenham Borough"
Cohesion: 0.15
Nodes (17): Barking Abbey, Barking and Dagenham, Can you provide a choir for a wedding in Barking and Dagenham?, Christmas carol singers section, Do you cover crematorium services in Barking and Dagenham?, Eastbrookend Cemetery, Ensembles & pricing section, Frequently asked questions section (+9 more)

### Community 17 - "City of London Borough"
Cohesion: 0.15
Nodes (17): Can you provide a choir for a wedding in City of London?, Christmas carol singers section, City of London, City of London Crematorium, Do you cover crematorium services in City of London?, Ensembles & pricing section, Frequently asked questions section, Funeral music section (+9 more)

### Community 18 - "Croydon Borough"
Cohesion: 0.15
Nodes (17): Can you provide a choir for a wedding in Croydon?, Christmas carol singers section, Croydon, Croydon Crematorium, Croydon Minster, Do you cover crematorium services in Croydon?, Ensembles & pricing section, Frequently asked questions section (+9 more)

### Community 19 - "Hammersmith & Fulham Borough"
Cohesion: 0.15
Nodes (17): All Saints Fulham, Can you provide a choir for a wedding in Hammersmith & Fulham?, Christmas carol singers section, Do you cover crematorium services in Hammersmith & Fulham?, Ensembles & pricing section, Frequently asked questions section, Fulham Palace Chapel, Funeral music section (+9 more)

### Community 20 - "Kingston upon Thames Borough"
Cohesion: 0.12
Nodes (17): All Saints Kingston, FAQ — Kingston upon Thames, Kingston Crematorium, Funeral and wedding choirs in Kingston upon Thames, Service: Funeral Singers & Wedding Choirs in Kingston upon Thames, St Raphael's Surbiton, FAQ — Merton, Morden Cemetery (+9 more)

### Community 21 - "Barbershop Grams Mini-Site"
Cohesion: 0.13
Nodes (17): Barbershop Grams Hub Page (barbershop-grams/index.html), Barbershop Grams Repertoire Page (barbershop-grams/repertoire.html), Barbershopogram Comparison Page (compare/barbershopogram.html), Barbershop Grams Navigation, Skip to Main Content Link, WhatsApp Enquiry Link (prefilled message), Barbershop Grams Wordmark Link, Barbershop Register CSS (design tokens & scoped styles) (+9 more)

### Community 22 - "Bromley Borough"
Cohesion: 0.15
Nodes (16): All Saints Orpington, Beckenham Crematorium, Bromley, Can you provide a choir for a wedding in Bromley?, Christmas carol singers section, Do you cover crematorium services in Bromley?, Ensembles & pricing section, Frequently asked questions section (+8 more)

### Community 23 - "Ealing Borough"
Cohesion: 0.15
Nodes (16): Can you provide a choir for a wedding in Ealing?, Christmas carol singers section, Do you cover crematorium services in Ealing?, Ealing, Ensembles & pricing section, Frequently asked questions section, Funeral music section, Greenford Park Cemetery (+8 more)

### Community 24 - "Enfield Borough"
Cohesion: 0.16
Nodes (16): Can you provide a choir for a wedding in Enfield?, Christ Church Southgate, Christmas carol singers section, Do you cover crematorium services in Enfield?, Edmonton Cemetery, Enfield, Enfield Crematorium, Ensembles & pricing section (+8 more)

### Community 25 - "Newham Borough"
Cohesion: 0.15
Nodes (16): City of London Cemetery and Crematorium (Manor Park), East London Crematorium, FAQ — Newham, Funeral and wedding choirs in Newham, Service: Funeral Singers & Wedding Choirs in Newham, St Mary Magdalene East Ham, FAQ — Redbridge, Forest Park Crematorium (+8 more)

### Community 26 - "Wedding Song Arrangements"
Cohesion: 0.12
Nodes (16): Songbird (Fleetwood Mac, choral arr.), Can't Help Falling in Love (Elvis Presley, 1961), A Thousand Years (Christina Perri, 2011), All of Me (John Legend, 2013), Can't Help Falling in Love (Elvis Presley, 1961), Here Comes the Sun (The Beatles, 1969), Home (Edward Sharpe & The Magnetic Zeros, 2009), Marry You (Bruno Mars, 2010) (+8 more)

### Community 27 - "Brent Borough"
Cohesion: 0.16
Nodes (15): Alperton Cemetery, Brent, Can you provide a choir for a wedding in Brent?, Christmas carol singers section, Do you cover crematorium services in Brent?, Ensembles & pricing section, Frequently asked questions section, Funeral music section (+7 more)

### Community 28 - "Hackney Borough"
Cohesion: 0.16
Nodes (15): Abney Park Cemetery, Can you provide a choir for a wedding in Hackney?, Christmas carol singers section, Do you cover crematorium services in Hackney?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, Hackney (+7 more)

### Community 29 - "Haringey Borough"
Cohesion: 0.16
Nodes (15): Can you provide a choir for a wedding in Haringey?, Christmas carol singers section, Do you cover crematorium services in Haringey?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, Haringey, How much does a funeral singer cost in Haringey? (+7 more)

### Community 30 - "Havering Borough"
Cohesion: 0.15
Nodes (15): Can you provide a choir for a wedding in Havering?, Christmas carol singers section, Do you cover crematorium services in Havering?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, Havering, How much does a funeral singer cost in Havering? (+7 more)

### Community 31 - "Kensington & Chelsea Borough"
Cohesion: 0.17
Nodes (15): Brompton Oratory, Chelsea Old Church, FAQ — Kensington & Chelsea, Mortlake Crematorium, Funeral and wedding choirs in Kensington & Chelsea, Putney Vale Crematorium, Service: Funeral Singers & Wedding Choirs in Kensington & Chelsea, Mortlake Crematorium (+7 more)

### Community 32 - "St Albans Area"
Cohesion: 0.16
Nodes (15): Can you provide a choir for a wedding in St Albans?, Christmas carol singers section, Do you cover crematorium services in St Albans?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, Hertfordshire, How much does a funeral singer cost in St Albans? (+7 more)

### Community 33 - "Basingstoke & Hampshire Area"
Cohesion: 0.17
Nodes (15): Basingstoke Crematorium, Can you provide a choir for a wedding in Winchester?, Christmas carol singers section, Do you cover crematorium services in Winchester?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, How much does a funeral singer cost in Winchester? (+7 more)

### Community 34 - "Barbershop Gram Enquiry Flow"
Cohesion: 0.16
Nodes (15): Barbershop Grams Web3Forms enquiry form (#bs-enquiry), Barbershop Grams FAQ (8 questions), fireGramConversion() Ads/GA4 conversion tracking (gram_source dimension), How it works: Enquiry, Quote, Briefing, On the day, Luca Wetherall, Artistic Director & Tutor in Music, University of Oxford, Barbershop Grams hub page, Barbershop Grams price table (£600/£800/£1,200/£200/£1,000), 'Send a Gram' WhatsApp enquiry CTA (+7 more)

### Community 35 - "Barbershop Grams Roadmap & Plan"
Cohesion: 0.14
Nodes (15): R14 — Barbershop Grams product line [done 2026-09-03], Rationale: no Services-dropdown nav entry for Barbershop Grams — partials/nav.html expands into every page including funeral-context pages, so a birthday-gift nav item would surface to bereaved/corporate visitors mid funeral enquiry, Rationale: gram prices deliberately excluded from pricing.html — barbershop is sold separately from the choral service and bookings are almost always a quartet; barbershop-grams/index.html is the source of truth for gram prices, Barbershop Grams Implementation Plan, Task 10: Sitemap and llms.txt wiring, Task 11: Record the work and refresh the graph, Task 12: Phase 1 verification, Task 13: Competitor data and the enforcement test (Phase 2 — gated on barbershop recording) (+7 more)

### Community 36 - "Wedding Ceremony Music Guide"
Cohesion: 0.15
Nodes (15): A Complete Guide to Wedding Ceremony Music, Full choir of eight - from GBP 2,000, Quintet of five - from GBP 1,400, Sextet of six - from GBP 1,600, Small choir of four - from GBP 1,150, Solo singer - from GBP 250, Twelve-voice chorus - from GBP 3,000, How to Hire a Choir for Your Wedding (+7 more)

### Community 37 - "Salisbury Area"
Cohesion: 0.18
Nodes (14): Can you provide a choir for a wedding in Salisbury?, Christmas carol singers section, Do you cover crematorium services in Salisbury?, Ensembles & pricing section, Frequently asked questions section, Funeral music section, How much does a funeral singer cost in Salisbury?, Funeral and wedding choirs in Salisbury (+6 more)

### Community 38 - "Lambeth Borough"
Cohesion: 0.17
Nodes (13): FAQ — Lambeth, Honor Oak Crematorium (in Southwark), Lambeth Palace, Funeral and wedding choirs in Lambeth, Service: Funeral Singers & Wedding Choirs in Lambeth, St John's Waterloo, Streatham Park Cemetery, West Norwood Cemetery (+5 more)

### Community 39 - "Barbershop Competitive Position"
Cohesion: 0.18
Nodes (13): Barbershop Grams (product), Barbershop-o-gram (competitor), Claims integrity rules (price_inc_vat vs price_ex_vat), compare/barbershopogram.html page plan, Barbershop Grams Design Doc, Go-to-market plan, barbershop-grams/index.html hub page plan, No nav entry decision (+5 more)

### Community 40 - "Site Improvement Roadmap"
Cohesion: 0.17
Nodes (12): Site improvement roadmap (docs/ROADMAP.md), R10 — Two duplicate FAQ questions site-wide [done], R11 — Replace the 'Victorian' verification grep with an allowlist [done], R1 — Remove self-serving review schema and rating claims [done], R2 — Refresh stale sitemap lastmod dates [done], R3 — Real VideoObject dates/durations + missing sameAs [done/blocked], R4 — Cookie consent / Google Consent Mode v2 [done], R5 — Merge duplicate form scripts [done] (+4 more)

### Community 41 - "Hounslow Borough"
Cohesion: 0.18
Nodes (11): FAQ — Hounslow, Funeral and wedding choirs in Hounslow, Service: Funeral Singers & Wedding Choirs in Hounslow, South West Middlesex Crematorium (Hanworth), St Mary's Hounslow, West London Crematorium, FAQ — Richmond upon Thames, Funeral and wedding choirs in Richmond upon Thames (+3 more)

### Community 42 - "Non-Religious Funeral Music"
Cohesion: 0.18
Nodes (11): Bring Him Home, Danny Boy, Fields of Gold, My Way, Non-Religious Funeral Music, Somewhere Over the Rainbow, Time to Say Goodbye (Con te partiro), What a Wonderful World (+3 more)

### Community 43 - "Funeral Hymns"
Cohesion: 0.18
Nodes (11): Abide with Me, All Things Bright and Beautiful, Amazing Grace, Be Thou My Vision, Dear Lord and Father of Mankind, Guide Me, O Thou Great Redeemer, How Great Thou Art, Jerusalem (+3 more)

### Community 44 - "Choir & Singer Pricing"
Cohesion: 0.18
Nodes (11): Alma Consort Ltd (trading as The London Choral Service), Carol singers cost guide (referenced), Celebration of life music guide (referenced), Choir and Singer Pricing (page), Christmas & carol singer pricing (table rates; Christmas Eve/Day +25% premium), Funeral music guide (referenced), Funeral songs guide (referenced), Instrumentalists (pianists, harpists, strings) — from £250 (+3 more)

### Community 45 - "Birmingham Area"
Cohesion: 0.20
Nodes (10): Birmingham Cathedral (St Philip's), Birmingham Oratory, Edgbaston, Lodge Hill Crematorium, Selly Oak, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Birmingham (page), Perry Barr Crematorium, St Martin in the Bull Ring, Sutton Coldfield Crematorium (+2 more)

### Community 46 - "Islington Borough"
Cohesion: 0.22
Nodes (10): FAQ — Islington, Islington Cemetery, East Finchley, Funeral and wedding choirs in Islington, Service: Funeral Singers & Wedding Choirs in Islington, City of London Crematorium, Manor Park, FAQ — Tower Hamlets, Funeral and wedding choirs in Tower Hamlets, Service: Funeral Singers & Wedding Choirs in Tower Hamlets (+2 more)

### Community 47 - "Barbershop Build Tasks"
Cohesion: 0.25
Nodes (9): Barbershop Grams Social Preview Image, GA4/Ads conversion tracking on repertoire page (gram_source: barbershop-grams-repertoire), Barbershop Gram Repertoire page, Task 1: The register partial (clone partials/private-register.css.html, rename pe- to bs-), Task 2: Nav and footer partials (partials/barbershop-nav.html, partials/barbershop-footer.html), Task 6: The repertoire page, partials/barbershop-footer.html (mini-site footer), partials/barbershop-nav.html (mini-site header) (+1 more)

### Community 48 - "Funeral Singers Comparison"
Cohesion: 0.25
Nodes (9): The London Funeral Singers (competitor), Competitor pricing sourced from londonfuneralsingers.co.uk/pricing, checked 18 August 2026, Comparison page FAQ (why prices are lower, VAT, inclusions, notice), Listen section: Abide With Me (Full Choir), Anima Christi (Quintet), 'How much singing you get' repertoire-coverage comparison table, London Funeral Singers vs The London Choral Service (comparison page), Ensemble price comparison table (soloist to twelve-voice chorus), VAT-status claim: Alma Consort Ltd is not VAT-registered (+1 more)

### Community 49 - "Be Thou My Vision Guide"
Cohesion: 0.25
Nodes (9): Be Thou My Vision (hymn), Why Be Thou My Vision Is the Best Funeral Hymn, Be Thou My Vision (hymn), Why Be Thou My Vision Is the Best Wedding Hymn, Be Thou My Vision (hymn), Choosing Hymns for Your Wedding, Jerusalem (hymn), Love Divine, All Loves Excelling (+1 more)

### Community 50 - "Choosing Singers & Market Rates"
Cohesion: 0.22
Nodes (9): Ensemble size guidance (concept), Best Christmas Carol Singers: What to Look For, Market price ranges (2026), Ensemble size guidance (concept), Best Funeral Singers in London — What to Look For, Market price ranges (2026), Ensemble size guidance (concept), Best Wedding Choirs in London — What to Look For (+1 more)

### Community 51 - "Sitemap Generator"
Cohesion: 0.42
Nodes (8): content_hash(), existing_meta(), git_seed_date(), is_noindex(), main(), pages(), Date of the oldest commit whose version of f still has content hash h, walking…, url_path()

### Community 52 - "Bath Area"
Cohesion: 0.25
Nodes (8): Bath Abbey, Bristol (nearby city served), Haycombe Crematorium, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Bath (page), St Mary's, Bathwick, St Swithin's, Walcot, Bath (area served)

### Community 53 - "Areas We Serve Index"
Cohesion: 0.25
Nodes (8): Areas We Serve — Funeral & Wedding Choirs in the UK (page), Pricing page (referenced for travel costs), Salisbury (area, no dedicated page in this chunk), Slough & Maidenhead (area, no dedicated page in this chunk), St Albans (area, no dedicated page in this chunk), The London boroughs (all 32 + City of London, each with own page), Winchester (area, no dedicated page in this chunk), Windsor (area, no dedicated page in this chunk)

### Community 54 - "Barbershop Repertoire Groups"
Cohesion: 0.25
Nodes (8): Repertoire teaser (6 songs) on the hub page, Repertoire group: Birthday and celebration, Repertoire group: Christmas, Repertoire group: Barbershop classics, Repertoire group: Doo-wop and later, Repertoire group: Leaving dos, Repertoire group: Love songs, Full ItemList of 42 repertoire songs

### Community 55 - "Brighton Area"
Cohesion: 0.29
Nodes (7): Brighton & Preston Cemetery, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Brighton (page), St Bartholomew's Church, Brighton, St Peter's, Brighton, The Downs Crematorium, Woodvale Crematorium

### Community 56 - "Lewisham Borough"
Cohesion: 0.29
Nodes (7): FAQ — Lewisham, Grove Park Cemetery, Hither Green Crematorium, Lewisham Crematorium, Funeral and wedding choirs in Lewisham, Service: Funeral Singers & Wedding Choirs in Lewisham, St Mary's Lewisham

### Community 57 - "Cookie Consent Script"
Cohesion: 0.52
Nodes (6): apply(), build(), init(), read(), show(), write()

### Community 58 - "Guildford Area"
Cohesion: 0.33
Nodes (6): Guildford Cathedral, Guildford Crematorium, Holy Trinity Church, Guildford, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Guildford (page), St Nicolas' Church, Guildford

### Community 59 - "Liverpool Area"
Cohesion: 0.33
Nodes (6): Anfield Crematorium, Liverpool Cathedral (Anglican, St James's Mount), Luca Wetherall, Tutor in Music, University of Oxford (team reference), Metropolitan Cathedral of Christ the King, Funeral and Wedding Choirs in Liverpool (page), Thornton Crematorium

### Community 60 - "Manchester Area"
Cohesion: 0.33
Nodes (6): Agecroft Crematorium, Salford, Blackley Crematorium, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Manchester Cathedral, Victoria Street, Manchester Crematorium, Barlow Moor Road, Funeral and Wedding Choirs in Manchester (page)

### Community 61 - "Soloist & Accompanist Pricing"
Cohesion: 0.33
Nodes (6): Organist/pianist added to any choir — £225 (vs £250 standalone), Organist / Pianist — from £250, Soloist — 1 singer, from £250, Soloist with organist/pianist combo — £450 (vs £500 apart), Soloist — 1 voice, Soloist — £250

### Community 62 - "Cambridge Area"
Cohesion: 0.40
Nodes (5): Cambridge Crematorium, Great St Mary's (University Church), King's College Chapel, Cambridge, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Cambridge (page)

### Community 63 - "Canterbury Area"
Cohesion: 0.40
Nodes (5): Barham Crematorium, Canterbury Cathedral, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Canterbury (page), St Martin's Church, Canterbury (oldest parish church in England)

### Community 64 - "Chelmsford Area"
Cohesion: 0.40
Nodes (5): Chelmsford Cathedral, Chelmsford Crematorium, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Chelmsford (page), South Essex Crematorium

### Community 65 - "Chester Area"
Cohesion: 0.40
Nodes (5): Blacon Crematorium, Chester Cathedral, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Chester (page), St John the Baptist Church, Chester

### Community 66 - "Wandsworth Borough"
Cohesion: 0.40
Nodes (5): All Saints Wandsworth, FAQ — Wandsworth, Funeral and wedding choirs in Wandsworth, Service: Funeral Singers & Wedding Choirs in Wandsworth, St Mary's Battersea

### Community 67 - "Oxford Area"
Cohesion: 0.40
Nodes (5): Christ Church Cathedral, Oxford, Luca Wetherall, Tutor in Music, University of Oxford (team reference), Oxford Crematorium, Funeral and Wedding Choirs in Oxford (page), University Church of St Mary the Virgin, Oxford

### Community 68 - "Reading Area"
Cohesion: 0.40
Nodes (5): Luca Wetherall, Tutor in Music, University of Oxford (team reference), Funeral and Wedding Choirs in Reading (page), Reading Crematorium, Henley Road, Caversham, Reading Minster (St Mary's), St Giles' Church, Reading

### Community 69 - "Rochester Area"
Cohesion: 0.40
Nodes (5): Luca Wetherall, Tutor in Music, University of Oxford (team reference), Medway Crematorium, Funeral and Wedding Choirs in Rochester (page), Rochester Cathedral (founded 604 AD), St Nicholas Church, Rochester

### Community 70 - "Booking Carol Singers Direct"
Cohesion: 0.40
Nodes (5): Agency booking route (concept), Direct booking route (concept), Booking Carol Singers: Agency vs Direct, Carol singer pricing (concept), How Much Does It Cost to Hire Carol Singers? (2026)

### Community 71 - "Carol Lyrics & Meanings"
Cohesion: 0.40
Nodes (5): God Rest Ye Merry, Gentlemen, Good King Wenceslas, Christmas Carol Lyrics and What They Mean, Hark! The Herald Angels Sing, Silent Night

### Community 72 - "Gram Occasions"
Cohesion: 0.50
Nodes (4): The surprise birthday gram (flagship occasion), Occasion strip: Birthday, Valentine's, Proposal, Leaving do, Anniversary, Just because, Office / leaving-do gram section, Proposal gram section

### Community 73 - "Carol Singers for Law Firms"
Cohesion: 0.67
Nodes (3): Client-facing register (concept), The December diary problem (concept), Carol Singers for Law Firms & Professional Services

### Community 74 - "Celebration of Life Music"
Cohesion: 0.67
Nodes (3): Celebration of life (concept), Music for a Celebration of Life, Live vs recorded music (concept)

### Community 75 - "Charity Carol Concerts"
Cohesion: 0.67
Nodes (3): Charity carol concert planning (concept), Planning a Charity Carol Concert, Running order (concept)

### Community 76 - "Make You Feel My Love"
Cohesion: 1.00
Nodes (3): Make You Feel My Love (Bob Dylan/Adele, choral arr.), Make You Feel My Love (Bob Dylan / Adele), Make You Feel My Love (Bob Dylan / Adele)

### Community 77 - "Full Choir Tier"
Cohesion: 0.67
Nodes (3): Full Choir — 8 singers, from £2,000, Full Choir — 8 singers, Full Choir — £2,000

### Community 78 - "Sextet Tier"
Cohesion: 0.67
Nodes (3): Sextet — 6 singers, from £1,600, Sextet — 6 singers, Sextet — £1,600

### Community 79 - "Small Choir Tier"
Cohesion: 0.67
Nodes (3): Small Choir — 4 singers, from £1,150, Small Choir — 4 singers, Small Choir (4) — £1,150

## Knowledge Gaps
- **617 isolated node(s):** `Barbershop mini-site footer partial`, `partials/head-extras.html`, `partials/analytics.html`, `partials/care-strip.html`, `Schema.org LocalBusiness JSON-LD` (+612 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Choir and Singer Pricing (page)` connect `Choir & Singer Pricing` to `London Borough Venues`, `Wedding Music & Ensembles`, `Ensemble Tiers & Areas Served`, `Birmingham Area`, `Bath Area`, `Areas We Serve Index`, `Brighton Area`, `Guildford Area`, `Liverpool Area`, `Manchester Area`, `Soloist & Accompanist Pricing`, `Cambridge Area`, `Canterbury Area`, `Chelmsford Area`, `Chester Area`, `Oxford Area`, `Reading Area`, `Rochester Area`, `Full Choir Tier`, `Sextet Tier`, `Small Choir Tier`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `Funeral and Wedding Choirs in London (page)` connect `London Borough Venues` to `Ensemble Tiers & Areas Served`, `Luca Wetherall's Credentials`, `Choir & Singer Pricing`, `Areas We Serve Index`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `Music for Funerals, Weddings, and Ceremonies (page)` connect `Ensemble Tiers & Areas Served` to `Analytics, Ads & Cookie Consent`, `Full Choir Tier`, `Birmingham Area`, `Sextet Tier`, `Small Choir Tier`, `Bath Area`, `Soloist & Accompanist Pricing`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **What connects `Barbershop mini-site footer partial`, `partials/head-extras.html`, `partials/analytics.html` to the rest of the system?**
  _617 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Core Site Pages & Schema` be split into smaller, more focused modules?**
  _Cohesion score 0.08283730158730158 - nodes in this community are weakly interconnected._
- **Should `London Borough Venues` be split into smaller, more focused modules?**
  _Cohesion score 0.05858585858585859 - nodes in this community are weakly interconnected._
- **Should `Christmas & Corporate Carol Guides` be split into smaller, more focused modules?**
  _Cohesion score 0.10283687943262411 - nodes in this community are weakly interconnected._