# Graph Report - site-audit-improvements-47d735  (2026-09-26)

## Corpus Check
- 58 files · ~1,683,895 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1086 nodes · 2069 edges · 111 communities (73 shown, 38 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 193 edges (avg confidence: 0.86)
- Token cost: 239,224 input · 0 output

## Community Hubs (Navigation)
- Christmas Pages & Pricing
- Nav, Footer & Layout CSS
- Outer London Boroughs (North/East)
- Project Skills & Build Rules
- Europe Destination Weddings
- Site Audit Findings
- Build Script & Date Sync
- Asia & Indian Ocean Destinations
- Private Register Page Generator
- Cathedral City Area Pages
- Catholic Funeral Music
- Caribbean Destination Weddings
- Celebration of Life Songs
- House Claims Validator Tests
- Private Events Page & JS
- Ads & GA4 Conversion Tracking
- Choral Wedding Repertoire
- Wedding Organ Music
- East London Boroughs
- Lambeth & South London
- Scotland & Spain Regions
- Charity Carol Concerts
- Hymn-Leading & West Country
- Carol Singer Cost & Sizing
- Carol Lyrics & History
- London & Manchester Hubs
- Hammersmith & Fulham
- Project Instructions (CLAUDE.md)
- Outer London Boroughs (West/East)
- Funeral Music Guides
- Roadmap & Manual Actions
- Kensington & Chelsea
- Kingston & Merton
- Advent Carols
- Corporate & Law Firm Carols
- SEO & Conversion Plans
- Private Events Design Decisions
- Haringey & Islington
- Cookie Consent Banner
- Classic Funeral Hymns
- Competitor Claims Validator Tests
- Oxford & Reading Area Pages
- Nav & Services Redesign Plans
- A Cappella Christmas Songs
- Carols for Four Voices
- How to Organise an Office Carol Service
- Westminster borough page
- Greece destination wedding page
- Italy destination wedding page
- P10 Technical Platform and Freshness
- music-guides.js
- Christmas Entertainment for Hotels
- accessibility.html
- Jerusalem
- create_christmas_carol_campaign_2026.py
- Anima Christi at a Catholic funeral
- conversion_actions_2026_09.py
- allowed_figures()
- Christmas Expansion Plan
- Competitive Capture Spec
- Hark! The Herald Angels Sing
- Ding Dong! Merrily on High
- No December/seasonal surcharge policy
- indexnow-ping.py
- House claim rules applied off-site: neve
- Head Extras Partial
- 404 Page Not Found
- Apple Touch Icon
- Favicon: Serif L Monogram
- LCS Favicon - Serif 'L' Monogram
- Favicon: Serif 'L' Monogram
- Favicon Brand Mark
- Christmas OG Social Share Image
- Corporate Events OG Share Image
- Funerals OG Social-Share Image
- Default Open Graph Social Share Image
- Pricing Page OG Image
- Services Page OG Social Share Image
- Weddings OG Social Preview Image
- Cross-sell from destination pages to UK 
- Alma Consort Ltd Companies House record
- GBP canonical Google Maps URL for The Lo
- geo_cities coordinates registry
- Luca Wetherall LinkedIn URL
- Luca Wetherall Oxford Music Faculty page
- Destination page dead-end fix
- IndexNow Verification Key File
- Haul-group sibling linking
- Nearby destinations section
- services.html
- Stop-Slop Pattern: Adverb Crutches
- Stop-Slop Pattern: Binary Contrasts
- Stop-Slop Pattern: Em-Dash Fragmentation
- Stop-Slop Pattern: "Here's what / here's
- Stop-Slop Pattern: Inanimate-Object-As-H
- Stop-Slop Pattern: Lazy Extremes
- Stop-Slop Pattern: Narrator-From-A-Dista
- Stop-Slop Pattern: Punchy One-Liner Clos
- Stop-Slop Pattern: Triadic Rhythm As Def
- Stop-Slop Pattern: Vague Declaratives
- Three haul-group taxonomy

## God Nodes (most connected - your core abstractions)
1. `Pricing page` - 46 edges
2. `A Complete Guide to Wedding Ceremony Music` - 46 edges
3. `How Much Does Wedding Music Cost?` - 43 edges
4. `Whole-Site Audit and Growth Plan` - 42 edges
5. `Christmas Carol Services page` - 35 edges
6. `For Planners, Venues & Estates (page)` - 31 edges
7. `How to Hire a Choir for Your Wedding` - 30 edges
8. `Weddings service page (weddings.html)` - 30 edges
9. `London area page` - 27 edges
10. `Hiring a UK Choir for a Destination Wedding guide` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Dead .audio-placeholder rules removed (12 lines off every page)` --conceptually_related_to--> `data/page-dates.json (generated lastmod store)`  [INFERRED]
  css/components.css → data/page-dates.json
- `OG image: Private & International Choral Engagements` --conceptually_related_to--> `Destinations hub page (destination weddings index)`  [INFERRED]
  assets/og-private-events.png → destinations/index.html
- `1080px nav breakpoint` --conceptually_related_to--> `Split breakpoint: nav 1080px vs sticky-CTA/hero 805px`  [EXTRACTED]
  js/nav.js → css/components.css
- `.dropdown-menu mobile breakpoint (max-width: 1080px)` --implements--> `1080px nav breakpoint`  [EXTRACTED]
  css/components.css → js/nav.js
- `.nav-links mobile breakpoint (max-width: 1080px)` --implements--> `1080px nav breakpoint`  [EXTRACTED]
  css/layout.css → js/nav.js

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Competitor price-claim gate (YAML source + compare page + quarterly re-check)** — data_competitor_pricing, compare_london_funeral_singers, data_competitor_pricing_derived_figures, manual_actions_required_quarterly_competitor_check, the_london_funeral_singers [EXTRACTED 1.00]
- **Lead and contact conversion tracking (site tag, Ads actions, GA4 key events)** — partials_analytics_lcslead, partials_analytics_contact_click, partials_analytics_lcs_ads, logs_ads_changes_conversion_rebuild, logs_ga4_changes_generate_lead_key_event, partials_analytics_consent_mode_defaults [INFERRED 0.85]
- **B2B for-* landing pages feeding Christmas bookings** — for_charities, for_event_managers, for_hotels, for_livery_companies, for_property_managers, christmas, carol_singers [INFERRED 0.85]
- **Ensemble sizing by acoustics and venue across carol guides** — music_guides_how_many_carol_singers_room_acoustics_first, music_guides_outdoor_carol_singing_add_two_voices_outdoors, music_guides_carol_singers_cost_venue_size_matching, music_guides_church_carol_service_choir_hire_four_voices_lead_150, music_guides_how_many_carol_singers_four_smallest_unaccompanied [INFERRED 0.85]
- **Guides quoting the pricing.html ladder verbatim** — music_guides_carol_singers_cost_article, music_guides_wedding_music_costs_article, music_guides_last_minute_funeral_singers, music_guides_charity_carol_concert_article, music_guides_christmas_choir_hire_article, music_guides_church_carol_service_choir_hire_article, pricing_pricingpage [INFERRED 0.95]
- **Corporate Christmas event guide cluster** — music_guides_carol_singers_law_firms_article, music_guides_christmas_drinks_reception_music_article, music_guides_christmas_gala_dinner_music_article, music_guides_company_christmas_party_entertainment_article, music_guides_office_carol_service_planning, music_guides_corporate_carol_service_article, for_event_managers [INFERRED 0.85]
- **Harrow and Hillingdon sharing Breakspear Crematorium** — areas_london_harrow_borough, areas_london_hillingdon_borough, areas_london_harrow_breakspearcrematorium [EXTRACTED 1.00]
- **Commercial Pillar Pages (Christmas, Corporate, Funerals + Weddings)** — christmas, corporate, funerals [EXTRACTED 1.00]
- **Hawksmoor churches of Tower Hamlets** — areas_london_tower_hamlets_christchurchspitalfields, areas_london_tower_hamlets_stanneslimehouse, areas_london_tower_hamlets_hawksmoorchurches, areas_london_tower_hamlets_borough [EXTRACTED 1.00]
- **Creation history of the hymn Jerusalem (text, music, orchestration, commission)** — music_guides_jerusalem_williamblake, music_guides_jerusalem_hubertparry, music_guides_jerusalem_edwardelgar, music_guides_jerusalem_robertbridges [EXTRACTED 1.00]
- **Most Popular UK Funeral Hymns (per FAQ list)** — music_guides_popular_funeral_hymns_abide_with_me, music_guides_popular_funeral_hymns_the_lords_my_shepherd_crimond, music_guides_popular_funeral_hymns_how_great_thou_art, music_guides_popular_funeral_hymns_amazing_grace, music_guides_popular_funeral_hymns_jerusalem, music_guides_popular_funeral_hymns_guide_me_o_thou_great_redeemer, music_guides_popular_funeral_hymns_dear_lord_and_father_of_mankind, music_guides_popular_funeral_hymns_all_things_bright_and_beautiful [EXTRACTED 1.00]
- **New Page Creation Workflow (head, internal linking, JSON-LD)** — _claude_skills_new_page_skill, _claude_skills_new_page_references_head_checklist, _claude_skills_new_page_references_internal_linking, _claude_skills_new_page_references_jsonld_by_page_type [EXTRACTED 1.00]
- **Popular Catholic Funeral Hymns (per FAQ list)** — music_guides_catholic_funeral_hymns_be_not_afraid, music_guides_catholic_funeral_hymns_here_i_am_lord, music_guides_catholic_funeral_hymns_ave_maria, music_guides_catholic_funeral_hymns_panis_angelicus, music_guides_popular_funeral_hymns_how_great_thou_art, music_guides_popular_funeral_hymns_the_lords_my_shepherd_crimond, music_guides_popular_funeral_hymns_make_me_a_channel_of_your_peace, music_guides_catholic_funeral_hymns_on_eagles_wings, music_guides_catholic_funeral_hymns_soul_of_my_saviour, music_guides_popular_funeral_hymns_abide_with_me [EXTRACTED 1.00]
- **Private-register bespoke design system (parchment/choirStall/cassockRed theme, shared private-register.css.html and private-events.js, distinct from the main site nav/footer partials)** — js_private_events, planners_and_venues, alma_consort, partials_private_footer [EXTRACTED 1.00]
- **Private-register page family: bespoke scoped CSS + footer shared by private-events.html, destinations/, and planners-and-venues.html (outside the standard nav/footer system)** — partials_private_register_css_privateregisterstylesheet, partials_private_footer_privateeventsfooter, destinations_index_countryguidesindex [EXTRACTED 1.00]
- **Boroughs sharing City of London Cemetery and Crematorium (Manor Park)** — areas_london_hackney_cityoflondoncemeteryandcrematorium, areas_london_hackney_borough, areas_london_newham_borough, areas_london_tower_hamlets_borough, areas_london_waltham_forest_borough [EXTRACTED 1.00]
- **The five wedding organ processionals booked most** — music_guides_popular_wedding_organ_music_trumpet_voluntary, music_guides_popular_wedding_organ_music_bridal_chorus, music_guides_popular_wedding_organ_music_canon_in_d, music_guides_popular_wedding_organ_music_arrival_of_the_queen_of_sheba, music_guides_popular_wedding_organ_music_prelude_in_c [EXTRACTED 1.00]
- **Web3Forms + hCaptcha Enquiry Flow** — web3forms_contact_form_pattern, js_form, contact, funerals [EXTRACTED 1.00]
- **Wedding-music SEO guide cluster (ten cross-linked how-to/repertoire articles)** — music_guides_wedding_ceremony_music_article, music_guides_wedding_choir_guide_article, music_guides_wedding_music_costs_article, music_guides_wedding_music_ideas_article, music_guides_wedding_organ_pop_songs_article, music_guides_wedding_organ_repertoire_article, music_guides_wedding_organist_guide_article, music_guides_wedding_pop_songs_choir_article, music_guides_wedding_readings_and_music_article [EXTRACTED 1.00]
- **Choral pieces for the wedding register signing** — music_guides_catholic_funeral_hymns_ave_maria, music_guides_wedding_choral_repertoire_ave_maria_bach_gounod, music_guides_catholic_funeral_hymns_panis_angelicus, music_guides_wedding_choral_repertoire_pie_jesu_faure, music_guides_wedding_choral_repertoire_pie_jesu_lloyd_webber, music_guides_wedding_choral_repertoire_laudate_dominum, music_guides_wedding_choral_repertoire_the_lord_bless_you_and_keep_you, music_guides_wedding_choral_repertoire_o_mio_babbino_caro [EXTRACTED 1.00]
- **Copy Quality Toolkit (house rules, generic editing, plain English)** — _claude_skills_writing_site_copy_skill, _claude_skills_copy_editing_skill, _claude_skills_copy_editing_references_plain_english_alternatives [INFERRED 0.65]
- **Destinations addressing Catholic nuptial Mass permissions (Italy, France, Croatia)** — destinations_italy_nuptial_mass, destinations_france_two_ceremonies, destinations_croatia [INFERRED 0.65]
- **Small-Team Positioning Correction Cluster** — docs_superpowers_plans_2026_08_18_competitive_capture_competitive_capture, docs_superpowers_plans_2026_08_18_value_care_and_onpage_seo_value_care_onpage_seo, docs_superpowers_plans_2026_08_18_competitive_capture, docs_superpowers_plans_2026_08_18_value_care_and_onpage_seo [INFERRED 0.65]
- **Destinations sharing a pre-existing Anglican/Baptist choral tradition (Barbados, Jamaica, Ireland)** — destinations_barbados_anglican_tradition, destinations_jamaica_anglican_baptist_tradition, destinations_ireland_no_permits [INFERRED 0.75]
- **Long-haul destinations requiring extended travel/acclimatisation logistics (Bali, Maldives, Mauritius)** — destinations_indonesia_longest_journey, destinations_maldives_seaplane_logistics, destinations_mauritius_colonial_churches [INFERRED 0.75]
- **Funeral repertoire guides (hymns, songs, non-religious music) cross-reference each other** — music_guides_funeral_songs, music_guides_non_religious_funeral_music [INFERRED 0.75]
- **Luca Wetherall's Oxford academic role used as a distinctive local credibility hook** — areas_oxford, areas_london [INFERRED 0.75]
- **Nav Dropdown & Services Hub Redesign Cluster** — docs_superpowers_plans_2026_05_09_nav_services_dropdown, docs_superpowers_specs_2026_05_09_nav_services_dropdown_design, docs_superpowers_plans_2026_05_09_services_page_redesign, docs_superpowers_specs_2026_05_09_services_page_redesign_design, docs_superpowers_plans_2026_05_09_nav_services_dropdown_nav_services_dropdown, docs_superpowers_plans_2026_05_09_services_page_redesign_services_page_redesign [INFERRED 0.75]
- **Pre-Commit Quality Gates (build, copy, wiring)** — _claude_skills_build_and_verify_skill, _claude_skills_writing_site_copy_skill, _claude_skills_new_page_skill [INFERRED 0.75]
- **The private-register partial architecture (shared CSS/footer partials) forms the technical basis shared by the private-events plan and the destination pages built on it** — docs_superpowers_specs_2026_08_29_international_luxury_weddings_design_registerbecomespartial, destinations_scotland_scotland, destinations_united_states_unitedstates, docs_superpowers_plans_2026_08_26_private_events_plan [INFERRED 0.75]
- **Anima Christi covered for two audiences (Catholic funeral and Catholic wedding) from a shared prayer identity** — music_guides_anima_christi_catholic_funeral_page, music_guides_anima_christi_catholic_wedding_page, music_guides_anima_christi_catholic_funeral_prayer [INFERRED 0.85]
- **Be Thou My Vision covered for two audiences (funeral and wedding) from a shared hymn identity** — music_guides_be_thou_my_vision_funeral_hymn_page, music_guides_be_thou_my_vision_wedding_hymn_page, music_guides_be_thou_my_vision_funeral_hymn_hymn [INFERRED 0.85]
- **Programmatic local-SEO area-page template (shared head/nav/footer partials, Service+LocalBusiness+BreadcrumbList+FAQPage JSON-LD, and FAQ/pricing prose pattern)** — areas_bath, areas_birmingham, areas_brighton, areas_cambridge, areas_canterbury, areas_chelmsford, areas_chester, areas_guildford, areas_liverpool, areas_index [INFERRED 0.85]
- **Shared UK city/town area-page template (hero, funeral/wedding sections, venues, ensembles & pricing, pull-quote, Christmas, FAQ)** — areas_london, areas_manchester, areas_oxford, areas_reading, areas_rochester, areas_salisbury, areas_slough_maidenhead, areas_st_albans, areas_winchester, areas_windsor [INFERRED 0.90]
- **Shared London-borough page template (breadcrumb to London hub, venue paragraphs, ensembles, pull-quote, FAQ)** — areas_london_barking_dagenham, areas_london_barnet, areas_london_bexley, areas_london_brent, areas_london_bromley, areas_london_camden, areas_london_city_of_london, areas_london_croydon, areas_london_ealing, areas_london_enfield, areas_london_greenwich [INFERRED 0.90]
- **Trust and compliance pages (terms, accessibility, cookie consent)** — terms, accessibility, privacy, js_consent, partials_analytics [EXTRACTED 1.00]
- **Professionals nav dropdown (seven trade pages plus the planners page)** — for_funeral_directors, for_wedding_planners, for_event_managers, for_hotels, for_property_managers, for_livery_companies, for_charities, planners_and_venues [EXTRACTED 1.00]
- **Generated freshness signals (sitemap.xml, page-dates.json, article dates)** — scripts_sync_dates_py, data_page_dates_json, concept_generated_sitemap_never_hand_edit, build_sh__entry [EXTRACTED 1.00]

## Communities (111 total, 38 thin omitted)

### Community 0 - "Christmas Pages & Pricing"
Cohesion: 0.07
Nodes (80): About Our Musicians Page, Areas We Serve — City Hub (areas/), B2B booking & invoicing (PO, £5m PLI), Hire Carol Singers page, Carol singers hire intent (vs carol service intent), Christmas Carol Services page, Christmas Carol Singer Prices page, Two-hour standard Christmas booking (+72 more)

### Community 1 - "Nav, Footer & Layout CSS"
Cohesion: 0.07
Nodes (64): Hire Carol Singers page (carol-singers.html), Christmas carol services page (christmas.html), 1080px nav breakpoint, Five-column footer grid, Split breakpoint: nav 1080px vs sticky-CTA/hero 805px, .dropdown-menu mobile breakpoint (max-width: 1080px), .footer-grid rule (five-column footer), .nav-links mobile breakpoint (max-width: 1080px) (+56 more)

### Community 2 - "Outer London Boroughs (North/East)"
Cohesion: 0.05
Nodes (45): Barking and Dagenham borough page, Eastbrookend Cemetery, London Borough of Barking and Dagenham, St Margaret's Church, Barking, Barnet borough page, Golders Green Crematorium, Hendon Crematorium, London Borough of Barnet (+37 more)

### Community 3 - "Project Skills & Build Rules"
Cohesion: 0.07
Nodes (38): ab-test-setup Skill, ai-seo Skill, analytics-tracking Skill, build-and-verify Skill, CSS Inlining Build Pipeline (build.sh 4 steps), Site-Wide Sweep Procedure (scripted bulk edits outside partials), Two Cardinal Rules (never hand-edit generated style block or partial markers), competitor-alternatives Skill (+30 more)

### Community 4 - "Europe Destination Weddings"
Cohesion: 0.08
Nodes (38): OG image: Private & International Choral Engagements, Croatia destination wedding page, Dubrovnik, Hvar (island logistics), Istria, Split, Cyprus destination wedding page, Ayia Napa (+30 more)

### Community 5 - "Site Audit Findings"
Cohesion: 0.12
Nodes (32): Finding: Destination Pages Have One Inbound Link Each, Finding: Five Different Response-Time Promises, Finding: 14 of 20 Listen Page Titles Have No Recording, Finding: No Singer Named but the Director, Finding: No Terms of Booking or Accessibility Statement, Finding: ?occasion=quote-check Never Pre-Fills, Finding: Testimonials Recycled Across Mismatched Geography, Finding: thank-you.html Has No Next Steps (+24 more)

### Community 6 - "Build Script & Date Sync"
Cohesion: 0.10
Nodes (29): build.sh script, dateModified JSON-LD sync, article:modified_time meta sync, Build-noise does not bump lastmod, sitemap+date-sync step order (after CSS inline, before llms-full), Byline · Published date-line migration (BYLINE_PUB_RX), changefreq/priority carried from existing sitemap, Content-hash lastmod (+21 more)

### Community 7 - "Asia & Indian Ocean Destinations"
Cohesion: 0.12
Nodes (31): Bali (Indonesia) destination wedding page, Bali glass chapels (venue fact), Bali as longest-haul destination (travel logistics fact), Seminyak, Ubud, Uluwatu, Maldives destination wedding page, North Malé Atoll (+23 more)

### Community 8 - "Private Register Page Generator"
Cohesion: 0.10
Nodes (13): enquiry_form(), head(), head_close(), header(), page(), crumbs: list of (label, href) with href None for the current page., The register's shared enquiry form. source_page is the attribution value:…, path is site-relative with no leading slash, e.g. 'destinations/italy.html'. (+5 more)

### Community 9 - "Cathedral City Area Pages"
Cohesion: 0.08
Nodes (26): Rochester area page, Rochester Cathedral (founded 604 AD, second oldest in England), Rochester (city), Medway Crematorium, St Nicholas Church, Rochester, Salisbury area page, Salisbury Cathedral (tallest spire in Britain, holds a Magna Carta copy), Salisbury Crematorium (+18 more)

### Community 10 - "Catholic Funeral Music"
Cohesion: 0.11
Nodes (25): Anima Christi (Frisina), Ave Maria (Schubert), Be Not Afraid, Best Hymns for a Catholic Funeral (guide), Here I Am, Lord, On Eagle's Wings, Panis Angelicus (Franck), Soul of My Saviour (+17 more)

### Community 11 - "Caribbean Destination Weddings"
Cohesion: 0.13
Nodes (23): Barbados destination wedding page, Barbados Anglican choral tradition (three centuries), Christ Church parish (Barbados), St James parish (Barbados), St Peter parish (Barbados), Jamaica destination wedding page, Jamaican Anglican and Baptist choral tradition, Montego Bay (+15 more)

### Community 12 - "Celebration of Life Songs"
Cohesion: 0.09
Nodes (22): Music for a Celebration of Life, Blackbird (The Beatles), Bridge Over Troubled Water (Simon & Garfunkel), Bring Him Home (Les Misérables), Danny Boy, Fields of Gold, Fly Me to the Moon, Heroes (David Bowie) (+14 more)

### Community 13 - "House Claims Validator Tests"
Cohesion: 0.16
Nodes (20): Drop `html` into a temp repo as index.html, run the validator, return (exit,…, The true statement must not trip the VAT pattern., carol-singers.html legitimately says a room holds up to 150 guests., z-index: 150 and 150ms transitions must not trip the roster pattern., for-funeral-directors.html deliberately says 'one person, not a roster'., run_on(), test_150_plus_fails(), test_aggregate_rating_fails() (+12 more)

### Community 14 - "Private Events Page & JS"
Cohesion: 0.14
Nodes (16): Accessibility Statement Page, Alma Consort (performing ensemble, 8-24 voices), Five-Column Site Footer, applyVoicing(), renderVoicingMedia(), showError(), trackError(), The London Choral Service / Alma Consort Ltd (organization) (+8 more)

### Community 15 - "Ads & GA4 Conversion Tracking"
Cohesion: 0.16
Nodes (20): Alma Consort Ltd (operating company), R4 Cookie consent / Consent Mode v2, GA4 property 527915578 (G-9FENN7VS0E), Conversion action rebuild 2026-09-26 (Call click, WhatsApp/email click, Contact demoted), GA4 change log, Removal of ads_conversion_Contact_1 double count, generate_lead key event + custom dimensions, Google Ads campaigns for competitive capture (§11) (+12 more)

### Community 16 - "Choral Wedding Repertoire"
Cohesion: 0.12
Nodes (19): Lesser-Known Choral Pieces for a Wedding, Ubi Caritas at a Wedding — Ola Gjeilo's Setting, Maurice Duruflé (composer, 1960 Ubi Caritas setting), Ola Gjeilo (composer, 2001 Ubi Caritas setting), The Best Choral Pieces for a Wedding, A Gaelic Blessing (Rutter), Ave Maria (Bach/Gounod), Ave Verum Corpus (Mozart) (+11 more)

### Community 17 - "Wedding Organ Music"
Cohesion: 0.11
Nodes (19): Popular Wedding Organ Music, A Thousand Years (Christina Perri, organ arr.), Air on the G String (Bach), All You Need Is Love (The Beatles), Arrival of the Queen of Sheba (Handel), Bridal Chorus (Wagner), Canon in D (Pachelbel), Can't Help Falling in Love (Elvis Presley) (+11 more)

### Community 18 - "East London Boroughs"
Cohesion: 0.16
Nodes (18): Abney Park Cemetery, Hackney (London Borough), City of London Cemetery and Crematorium (Manor Park), St John at Hackney, St Mary of Eton, Newham (London Borough), East London Crematorium (Plaistow), St Mary Magdalene, East Ham (+10 more)

### Community 19 - "Lambeth & South London"
Cohesion: 0.12
Nodes (18): Lambeth (London Borough), Honor Oak Crematorium, Lambeth Palace Chapel, Magnificent Seven Victorian Cemeteries of London, St John's Waterloo, St Mary's Lambeth (Garden Museum), West Norwood Cemetery, Lewisham (London Borough) (+10 more)

### Community 20 - "Scotland & Spain Regions"
Cohesion: 0.14
Nodes (18): Edinburgh and the Lothians (Scotland region), Fife and Perthshire (Scotland region), The Highlands (Scotland region), Loch Lomond and the Trossachs (Scotland region), Scotland (destination wedding page), Ibiza (Spain region), Mallorca (Spain region), Marbella (Spain region) (+10 more)

### Community 21 - "Charity Carol Concerts"
Cohesion: 0.16
Nodes (18): Carols by Candlelight guide, Congregational carols chosen for singing from memory, Singers reading music by candlelight, Real candles and venue fire rules, Placing the fundraising appeal in the running order, Planning a Charity Carol Concert guide, Fill the church to about four-fifths capacity rule, Church copyright licence coverage for ticketed concerts (+10 more)

### Community 22 - "Hymn-Leading & West Country"
Cohesion: 0.21
Nodes (17): Live choir leads an unfamiliar hymn (value proposition), Hymn-leading wording: "make the hymns sound intended rather than endured", Hymn-leading wording: "give the hymns a lead the congregation can follow without embarrassment", Hymn-leading wording: "keep a nervous congregation in tune and in time through the hymns", Hymn-leading wording: "carry the hymns for guests who have not sung since school", Hymn-leading wording: "hold the hymns together for a congregation that is unsure of the tune", Bath area page, Brighton area page (+9 more)

### Community 23 - "Carol Singer Cost & Sizing"
Cohesion: 0.21
Nodes (17): Birmingham area page, Cambridge area page, Best Christmas Carol Singers guide, Booking Carol Singers: Agency vs Direct guide, How Much Does It Cost to Hire Carol Singers guide, LCS Ensemble Pricing Ladder (Soloist £250 to 12-voice Chorus £3000), Ensemble size by room (lobby 4, party 6, church 8, cathedral 12), Hiring a Choir for Your Christmas Event guide (+9 more)

### Community 24 - "Carol Lyrics & History"
Cohesion: 0.13
Nodes (15): Christmas Carol Lyrics and What They Mean, God Rest Ye Merry, Gentlemen, Meaning of 'God rest ye merry, gentlemen' (rest=keep/make, merry=strong; comma misplacement), Good King Wenceslas (Neale), Real tenth-century Duke of Bohemia; Feast of Stephen dating; thirteenth-century spring-carol tune repurposed in 1853, In the Bleak Midwinter (Rossetti), Poem's history, invented midwinter setting, and closing question about the singer, O Come, All Ye Faithful (Adeste Fideles; Wade/Oakeley) (+7 more)

### Community 25 - "London & Manchester Hubs"
Cohesion: 0.15
Nodes (14): London area page, St Martin-in-the-Fields, Temple Church (London hub page), Manchester area page, Manchester Cathedral, Manchester Crematorium, Manchester (city), Choral Music for a Humanist Wedding (+6 more)

### Community 26 - "Hammersmith & Fulham"
Cohesion: 0.18
Nodes (14): All Saints Fulham, Hammersmith & Fulham (London Borough), Fulham Palace Chapel, Margravine Cemetery, Mortlake Crematorium, St Paul's Hammersmith, West London Crematorium (Kensal Green), Hounslow (London Borough) (+6 more)

### Community 27 - "Project Instructions (CLAUDE.md)"
Cohesion: 0.19
Nodes (14): CLAUDE.md (project instructions), Google Ads change protocol (validate_only, approval, £5/day cap, no deletes), Build pipeline (CSS inlining + partial expansion via build.sh), Generated files: sitemap.xml, page-dates.json, llms-full.txt, style.css, graphify-out knowledge graph, @include-start / @include-end partial markers, Meta description 141-161 chars + canonical/hreflang/OG convention, No AggregateRating/Review schema rule (+6 more)

### Community 28 - "Outer London Boroughs (West/East)"
Cohesion: 0.18
Nodes (13): Harrow (London Borough), Breakspear Crematorium, St Mary's Harrow-on-the-Hill, Havering (London Borough), South Essex Crematorium (Corbets Tey), St Andrew's Church, Hornchurch, Hillingdon (London Borough), Hillingdon Cemetery (+5 more)

### Community 29 - "Funeral Music Guides"
Cohesion: 0.40
Nodes (13): Video entry: Abide With Me (Eventide), G9-R6k5n7Io, What to Expect from a Funeral Choir, How Much Does Funeral Music Cost?, How to Choose Music for a Funeral, The Most Popular Funeral Songs, What to Expect When You Hire a Choir, Music Guides (hub index), Booking Funeral Singers at Short Notice (+5 more)

### Community 30 - "Roadmap & Manual Actions"
Cohesion: 0.19
Nodes (12): Site improvement roadmap, R12 Testimonial pool reused across mismatched pages, R13 Rigid borough page template, R5 Merge duplicate form scripts into js/form.js, R6 CSS inlining vs cached stylesheet (decision needed), Roadmap status labels (BLOCKED-ON-HUMAN, SPEC-FIRST, DECISION-NEEDED), Third-party citation building and NAP consistency (§2), CSS extraction deferred until CrUX data (§8) (+4 more)

### Community 31 - "Kensington & Chelsea"
Cohesion: 0.18
Nodes (12): Royal Borough of Kensington and Chelsea, Brompton Oratory, Chelsea Old Church, Holy Trinity Sloane Square, Royal Hospital Chelsea Chapel, St Luke's Chelsea, St Mary Abbots, St Mary Abbots' 278-foot Spire (Tallest in London) (+4 more)

### Community 32 - "Kingston & Merton"
Cohesion: 0.18
Nodes (12): All Saints Kingston, Royal Borough of Kingston upon Thames, Kingston Crematorium, St Raphael's Surbiton, Merton (London Borough), Morden Cemetery, South London Crematorium (Mitcham), St Mary's Wimbledon (Wimbledon Parish Church) (+4 more)

### Community 33 - "Advent Carols"
Cohesion: 0.18
Nodes (12): Advent Carols vs Christmas Carols, Away in a Manger, Come, Thou Long Expected Jesus (Wesley), Hills of the North, Rejoice, In the Bleak Midwinter, Lo, He Comes with Clouds Descending (tune: Helmsley), O Come, O Come, Emmanuel, O Little Town of Bethlehem (+4 more)

### Community 34 - "Corporate & Law Firm Carols"
Cohesion: 0.18
Nodes (12): Carol Singers for Law Firms and Professional Services guide, Carol singing as client-entertaining differentiator, Separate client and staff Christmas events, Ambient, formal performance and audience participation modes, Music for a Christmas Drinks Reception guide, Roaming vs stationary singers, Start singing before the first guest arrives, Music for a Christmas Gala or Awards Dinner guide (+4 more)

### Community 35 - "SEO & Conversion Plans"
Cohesion: 0.24
Nodes (11): SEO & Conversion Improvements Plan, SEO & Conversion Improvements Initiative, Site Improvements Plan (v2), Site Improvements Programme (v2), Music Guides Redesign Plan, Music Guides Index Redesign Initiative, SEO Audit Fixes Plan, SEO Audit Fixes Initiative (+3 more)

### Community 36 - "Private Events Design Decisions"
Cohesion: 0.20
Nodes (11): Five-lens parallel review (code, copy/slop, accessibility+design, SEO/head/schema, visual) required before shipping private-events.html, Idempotency check: run build.sh twice, git diff private-events.html must be empty the second time — the tripwire for a broken Pass A defence, Private Events Page Implementation Plan, Positioning: LCS is the booking office of Alma Consort, functional not hierarchical; 'elite' and 'premium tier' framings are banned outright because they invite re-pricing the rest of the site downwards, hCaptcha decision reversed on 2026-08-26: originally specified without one to protect conversion rate, but a form that silently fails against the shared Web3Forms access key is judged worse than added friction, Full insulation from site chrome: no shared nav/footer partials, to avoid tier-mixing (funeral pricing bleeding into a luxury planner's view) and to keep the page's bespoke CSS register out of the site-wide inlined bundle, No AggregateRating or Review schema, ever — prohibited site-wide, The Pass A defence: the page's hand-authored <style> block opens with a comment line so build.sh Pass A never mistakes it for the generated CSS bundle and deletes it — the most expensive mistake available on the page (+3 more)

### Community 37 - "Haringey & Islington"
Cohesion: 0.20
Nodes (10): Haringey (London Borough), New Southgate Cemetery, St Augustine's Highgate, Tottenham Cemetery, Islington (London Borough), Islington Cemetery (East Finchley), St James Church, Clerkenwell, St Mary's Islington (+2 more)

### Community 38 - "Cookie Consent Banner"
Cohesion: 0.31
Nodes (9): apply(), Cookie choices banner (Allow/Decline), build(), data-consent-open attribute reopens banner from footer link, init(), lcs-consent localStorage key, read(), show() (+1 more)

### Community 39 - "Classic Funeral Hymns"
Cohesion: 0.27
Nodes (10): Eventide — tune by William Henry Monk, 1861, Henry Francis Lyte — wrote Abide With Me in 1847 in his final weeks of life as a dying curate in Brixham, Devon, Abide With Me (hymn), Abide With Me — the most-requested funeral hymn (guide), Dallan Forgaill — sixth-century Irish monk traditionally credited with the text of Be Thou My Vision, Be Thou My Vision (hymn), Why Be Thou My Vision Is the Best Funeral Hymn (guide), Slane — Irish folk tune named after the Hill of Slane, County Meath, to which Be Thou My Vision is sung (+2 more)

### Community 40 - "Competitor Claims Validator Tests"
Cohesion: 0.31
Nodes (8): Copy the validator into a temp repo, run it, return (exit_code, output)., £550 is 275+275, but arithmetic alone must not make a figure acceptable., run_in_sandbox(), test_declared_derived_figure_passes(), test_sourced_figures_pass(), test_stale_data_warns_but_passes(), test_undeclared_sum_fails(), test_unsourced_figure_fails()

### Community 41 - "Oxford & Reading Area Pages"
Cohesion: 0.22
Nodes (9): Oxford area page, Christ Church Cathedral, Oxford, Oxford (city), New College Chapel, Oxford, University Church of St Mary the Virgin, Oxford, Reading area page, Reading Crematorium, Henley Road, Caversham, Reading (city) (+1 more)

### Community 42 - "Nav & Services Redesign Plans"
Cohesion: 0.31
Nodes (9): Nav Services Dropdown Plan, Nav Services Dropdown Initiative, Services Page Redesign Plan, Services Page Hub Redesign Initiative, Value, Care & On-Page SEO Plan, Value, Bespoke Care & On-Page SEO Initiative, Nav Services Dropdown Spec, Services Page Redesign Spec (+1 more)

### Community 43 - "A Cappella Christmas Songs"
Cohesion: 0.22
Nodes (9): A Cappella Christmas Songs for a Choir (guide), Have Yourself a Merry Little Christmas, Let It Snow, Santa Claus Is Comin' to Town, Christmas songs vs carols distinction, The Christmas Song (Chestnuts Roasting), White Christmas, Winter Wonderland (+1 more)

### Community 44 - "Carols for Four Voices"
Cohesion: 0.22
Nodes (9): The Best Carols for Four Voices, Coventry Carol, Es ist ein Ros entsprungen (Praetorius), Gaudete, In the Bleak Midwinter (Holst), Personent Hodie, The Holly and the Ivy, The Sussex Carol (+1 more)

### Community 45 - "How to Organise an Office Carol Service"
Cohesion: 0.25
Nodes (9): Live Choral Music for Company Christmas Parties guide, Featured performance slot, Choosing Music for a Crematorium Service guide, What to Expect When You Hire a Choir (guide, referenced), Secular English part-song repertoire for humanist weddings, How to Organise an Office Carol Service, Keeping an office carol service inclusive, Sample office carol service running order (+1 more)

### Community 46 - "Westminster borough page"
Cohesion: 0.25
Nodes (8): Westminster borough page, Westminster Abbey (venue), Westminster Cathedral (venue), Westminster page FAQPage schema, Guards' Chapel, Wellington Barracks (venue), Westminster funeral singer pricing FAQ answer (£250 solo, £2,000 full choir), St Margaret's Westminster (venue), geo_areas.westminster coordinates [51.49594, -0.13495]

### Community 47 - "Greece destination wedding page"
Cohesion: 0.25
Nodes (8): Cypriot civil ceremony / Greek Orthodox ceremony music logistics, Greece destination wedding page, Crete, Mykonos, Greek Orthodox ceremony music logistics, Rhodes, Santorini, Zakynthos

### Community 48 - "Italy destination wedding page"
Cohesion: 0.25
Nodes (8): Italy destination wedding page, The Amalfi Coast, Florence, Lake Como, Nuptial Mass in Italian Catholic parishes (permit/permission fact), Puglia, Tuscany, Malta: shortest paperwork in the Mediterranean, English official language (fact)

### Community 49 - "P10 Technical Platform and Freshness"
Cohesion: 0.33
Nodes (4): Finding: README and CLAUDE.md Page Counts Were Stale, Finding: 139 of 160 Sitemap Lastmods Are Stale, Dead .audio-placeholder rules removed (12 lines off every page), P10 Technical Platform and Freshness

### Community 50 - "music-guides.js"
Cohesion: 0.80
Nodes (5): applyFilter(), getCategoryFromURL(), init(), onChipClick(), onPopState()

### Community 51 - "Christmas Entertainment for Hotels"
Cohesion: 0.33
Nodes (6): Working with office building management, Christmas Entertainment for Hotels, Hotel formats by space (lobby, afternoon tea, ballroom, frontage), Unaccompanied choir needs no stage, power or sound check, Scheduling singers across several December dates, Carol evening as lowest-effort residents' event

### Community 52 - "accessibility.html"
Cohesion: 0.40
Nodes (3): Alternative formats on request (large print, plain text), Text/background contrast ratio of 5.66:1 (above AA), Known accessibility shortfalls (YouTube captions, hCaptcha challenge)

### Community 53 - "Jerusalem"
Cohesion: 0.70
Nodes (5): Jerusalem — the Most British of Wedding Hymns, Edward Elgar (orchestrated Jerusalem in 1922), Hubert Parry (composer, set the hymn to music in 1916), Robert Bridges (Poet Laureate, commissioned Parry's setting), William Blake (wrote the text, c.1804)

### Community 54 - "create_christmas_carol_campaign_2026.py"
Cohesion: 0.70
Nodes (4): build(), check_limits(), main(), summary()

### Community 55 - "Anima Christi at a Catholic funeral"
Cohesion: 0.83
Nodes (4): Marco Frisina — Monsignor, priest of the Diocese of Rome, composer of the widely-used Anima Christi setting, Anima Christi at a Catholic funeral — Frisina's setting (guide), Anima Christi (Latin prayer, anonymous c.1300, placed at the opening of St Ignatius of Loyola's Spiritual Exercises), Anima Christi at a Catholic wedding — Frisina's setting (guide)

### Community 56 - "conversion_actions_2026_09.py"
Cohesion: 0.83
Nodes (3): build_operations(), current_actions(), main()

### Community 57 - "allowed_figures()"
Cohesion: 0.67
Nodes (3): allowed_figures(), main(), Every figure a compare/ page may legitimately print. Explicit only. Deriving…

### Community 58 - "Christmas Expansion Plan"
Cohesion: 1.00
Nodes (3): Christmas Expansion Plan, Christmas Expansion & Seasonal SEO Initiative, Christmas Expansion Spec

### Community 59 - "Competitive Capture Spec"
Cohesion: 1.00
Nodes (3): Competitive Capture Plan, Competitive Capture Programme Initiative, Competitive Capture Spec

### Community 61 - "Hark! The Herald Angels Sing"
Cohesion: 0.67
Nodes (3): Hark! The Herald Angels Sing, Hark! The Herald Angels Sing (Wesley/Mendelssohn), Meaning of 'veiled in flesh the Godhead see' and the tune's non-Christmas origin

### Community 62 - "Ding Dong! Merrily on High"
Cohesion: 0.67
Nodes (3): Ding Dong! Merrily on High, Ding Dong! Merrily on High (Woodward), Sixteenth-century French dance tune with 1924 mock-archaic Woodward lyrics; meaning of 'Hosanna in excelsis'

### Community 63 - "No December/seasonal surcharge policy"
Cohesion: 0.67
Nodes (3): No December/seasonal surcharge policy, No short-notice surcharge, Transparent all-inclusive pricing (no admin fees or surcharges)

## Ambiguous Edges - Review These
- `Ceremony moment: the processional` → `Musical piece: Can't Help Falling in Love (Elvis Presley) - organ arrangement`  [AMBIGUOUS]
  music-guides/wedding-organ-pop-songs.html · relation: conceptually_related_to

## Knowledge Gaps
- **427 isolated node(s):** `404 Page Not Found`, `partials/care-strip.html`, `contact.html No Quotable Opening / No FAQPage Schema Finding`, `VideoObject: He Shall Feed His Flock — Soloist (nasqXWlbf1g)`, `VideoObject: Ubi Caritas — Full Choir, Ola Gjeilo (-GQaQEGhYEs)` (+422 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **38 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Ceremony moment: the processional` and `Musical piece: Can't Help Falling in Love (Elvis Presley) - organ arrangement`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Pricing page` connect `Christmas Pages & Pricing` to `Project Skills & Build Rules`, `Asia & Indian Ocean Destinations`, `How to Organise an Office Carol Service`, `Private Events Page & JS`, `Christmas Entertainment for Hotels`, `Charity Carol Concerts`, `Hymn-Leading & West Country`, `Carol Singer Cost & Sizing`, `London & Manchester Hubs`, `Project Instructions (CLAUDE.md)`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `How Much Does Wedding Music Cost?` connect `Asia & Indian Ocean Destinations` to `Christmas Pages & Pricing`, `Nav, Footer & Layout CSS`, `Europe Destination Weddings`, `Oxford & Reading Area Pages`, `Catholic Funeral Music`, `Caribbean Destination Weddings`, `How to Organise an Office Carol Service`, `Greece destination wedding page`, `Italy destination wedding page`, `Scotland & Spain Regions`, `Hymn-Leading & West Country`, `Carol Singer Cost & Sizing`, `London & Manchester Hubs`, `No December/seasonal surcharge policy`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `London area page` connect `London & Manchester Hubs` to `Outer London Boroughs (North/East)`, `Asia & Indian Ocean Destinations`, `How to Organise an Office Carol Service`, `Private Events Page & JS`, `Lambeth & South London`, `Christmas Entertainment for Hotels`, `Charity Carol Concerts`, `Carol Singer Cost & Sizing`, `Funeral Music Guides`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Christmas Carol Services page` (e.g. with `Ensemble price ladder (£250 soloist to £3,000 chorus)` and `llms-full.txt — Generated Full-Site Text Export`) actually correct?**
  _`Christmas Carol Services page` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `404 Page Not Found`, `partials/care-strip.html`, `contact.html No Quotable Opening / No FAQPage Schema Finding` to the rest of the system?**
  _427 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Christmas Pages & Pricing` be split into smaller, more focused modules?**
  _Cohesion score 0.07098765432098765 - nodes in this community are weakly interconnected._