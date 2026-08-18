# Graph Report - site-audit-improvements-47d735  (2026-08-18)

## Corpus Check
- Large corpus: 203 files · ~981,595 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 834 nodes · 1417 edges · 76 communities (57 shown, 19 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 81 edges (avg confidence: 0.81)
- Token cost: 481,000 input · 148,000 output

## Community Hubs (Navigation)
- Christmas Carol Repertoire
- Funeral & Wedding Hymns
- Core Site Pages
- Wedding Music Repertoire
- Build Pipeline & Conventions
- Project Skills Toolkit
- Traditional Christmas Carols
- Brand & Founder Identity
- Cambridge Area Page
- House Claims Validator Tests
- Barking & Dagenham Page
- Site Improvement Roadmap
- Newham Borough Page
- Redbridge Borough Page
- Brent Borough Page
- Bromley Borough Page
- Camden Borough Page
- Harrow Borough Page
- SEO & Site Improvement Plans
- Chester & Manchester Pages
- Birmingham Area Page
- Funeral Hymn Repertoire
- Islington Borough Page
- Cross-Borough References
- Richmond Borough Page
- Westminster Borough Page
- Kensington & Chelsea Page
- Kingston Borough Page
- Lambeth Borough Page
- Lewisham Borough Page
- Merton Borough Page
- Southwark Borough Page
- Sutton Borough Page
- Compare Page & Shared Chrome
- Bath Area Page
- Canterbury Area Page
- Barnet Borough Page
- Bexley Borough Page
- London Home-Base Page
- Croydon Borough Page
- Ealing Borough Page
- Enfield Borough Page
- Haringey Borough Page
- Hounslow Borough Page
- Wandsworth Borough Page
- Rochester Area Page
- Windsor Area Page
- Music Guides JS Filtering
- Brighton Area Page
- Chelmsford Area Page
- Guildford Area Page
- Liverpool Area Page
- Reading Area Page
- Slough & Maidenhead Page
- St Albans Area Page
- Competitor Pricing Comparison
- Christmas Event Planning Guides
- Apple Touch Icon
- Favicon 192px
- Favicon 32px
- Favicon 48px
- Favicon SVG
- Christmas OG Image
- Corporate OG Image
- Funerals OG Image
- Default OG Image
- Pricing OG Image
- Services OG Image
- Weddings OG Image
- Geo Coordinates Data
- SEO Fix URLs Data
- Non-Religious Funeral Guide
- Outdoor Carol Singing Guide
- Residents Carol Event Guide
- Care Strip Partial

## God Nodes (most connected - your core abstractions)
1. `The best carols for four voices` - 29 edges
2. `Christmas carol lyrics and what they mean` - 25 edges
3. `Music for a celebration of life` - 24 edges
4. `Best hymns for a Catholic funeral` - 21 edges
5. `Music Guides Index` - 21 edges
6. `The London Choral Service` - 21 edges
7. `The Best Choral Pieces for a Wedding (guide)` - 21 edges
8. `The Best Organ Pieces for a Wedding (guide)` - 21 edges
9. `Areas We Serve — Hub Page` - 21 edges
10. `Luca Wetherall` - 20 edges

## Surprising Connections (you probably didn't know these)
- `Compare: London funeral singers` --references--> `Embedded Video Metadata List`  [AMBIGUOUS]
  compare/london-funeral-singers.html → data/seo-fix-discovered-urls.yml
- `Pricing Consistency Rule` --references--> `pricing.html`  [EXTRACTED]
  CLAUDE.md → .claude/skills/new-page/SKILL.md
- `Stop-Slop Before/After Example 1 (About Page)` --references--> `About Page`  [EXTRACTED]
  SITE-STOP-SLOP-PLAN.md → about.html
- `Contact Page` --implements--> `contact.html No Quotable Opening / No FAQPage Schema Finding`  [INFERRED]
  contact.html → SEO-AUDIT-2026-05-08.md
- `No AggregateRating/Review Schema Rule` --implements--> `AggregateRating Sitewide Policy Violation Finding`  [INFERRED]
  CLAUDE.md → SEO-AUDIT-2026-05-08.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Best-X hiring guides sharing one structural template** — music_guides_best_christmas_carol_singers_page, music_guides_best_funeral_singers_london_page, music_guides_best_wedding_choirs_london_page [INFERRED 0.85]
- **Be Thou My Vision funeral/wedding companion guides** — music_guides_be_thou_my_vision_funeral_hymn_page, music_guides_be_thou_my_vision_wedding_hymn_page, be_thou_my_vision [EXTRACTED 1.00]
- **Anima Christi funeral/wedding companion guides** — music_guides_anima_christi_catholic_funeral_page, music_guides_anima_christi_catholic_wedding_page, anima_christi [EXTRACTED 1.00]
- **Christmas corporate event booking guide network** — music_guides_christmas_carols_guide_article, music_guides_christmas_choir_hire_article, music_guides_corporate_carol_service_article, music_guides_company_christmas_party_entertainment_article, music_guides_hiring_a_choir_standard_ensemble_pricing_ladder [INFERRED 0.85]
- **Funeral music guide network** — music_guides_funeral_music_guide_article, music_guides_funeral_choir_guide_article, music_guides_funeral_songs_article, music_guides_funeral_music_costs_article, music_guides_crematorium_music_article [INFERRED 0.85]
- **Ensemble sizing reasoning pattern across occasions** — music_guides_how_many_carol_singers_article, music_guides_funeral_choir_guide_article, music_guides_hiring_a_choir_article, music_guides_hiring_a_choir_standard_ensemble_pricing_ladder [INFERRED 0.80]
- **Wedding organ repertoire content cluster** — music_guides_popular_wedding_organ_music, music_guides_wedding_organ_repertoire, music_guides_wedding_organist_guide, music_guides_wedding_organ_pop_songs [INFERRED 0.80]
- **Wedding choral and organ pop-song cluster** — music_guides_wedding_choral_repertoire, music_guides_wedding_organ_pop_songs, music_guides_wedding_pop_songs_choir [INFERRED 0.75]
- **Christmas carol event-planning content cluster** — music_guides_office_carol_service_planning, music_guides_outdoor_carol_singing, music_guides_residents_christmas_carol_event, music_guides_when_to_book_christmas_entertainment [INFERRED 0.75]
- **Thames Valley & Home Counties City Cluster** — areas_reading_page, areas_slough_maidenhead_page, areas_windsor_page, areas_oxford_page, areas_st_albans_page [EXTRACTED 1.00]
- **South & South West City Cluster** — areas_winchester_page, areas_salisbury_page, areas_bath_page [EXTRACTED 1.00]
- **London & South East City Cluster** — areas_guildford_page, areas_brighton_page, areas_canterbury_page, areas_rochester_page, areas_chelmsford_page [EXTRACTED 1.00]
- **Thames-side Borough Pages** — areas_london_barking_dagenham_borough, areas_london_greenwich_borough, areas_london_hammersmith_fulham_borough [INFERRED 0.65]
- **Boroughs Foregrounding Historic Ecclesiastical Venues** — areas_london_camden_borough, areas_london_city_of_london_borough, areas_london_greenwich_borough [INFERRED 0.70]
- **Boroughs Framed by London's Green-Belt Edge** — areas_london_havering_borough, areas_london_hillingdon_borough, areas_london_enfield_borough [INFERRED 0.65]
- **East London boroughs sharing Manor Park crematorium venues** — areas_london_newham_page, areas_london_waltham_forest_page, areas_london_tower_hamlets_page, areas_london_redbridge_page [INFERRED 0.75]
- **Central/west London boroughs directing families to Richmond and Putney Vale crematoria** — areas_london_richmond_page, areas_london_kensington_chelsea_page, areas_london_westminster_page [INFERRED 0.75]
- **South London boroughs linked via Honor Oak Crematorium and explicit neighbour cross-links** — areas_london_lambeth_page, areas_london_southwark_page, areas_london_lewisham_page [EXTRACTED 1.00]
- **Christmas Expansion Documentation Cluster** — docs_roadmap, docs_superpowers_plans_2026_07_29_christmas_expansion, docs_superpowers_specs_2026_07_29_christmas_expansion_design, docs_superpowers_plans_2026_07_29_christmas_expansion_christmas_expansion [EXTRACTED 1.00]
- **Nav Dropdown & Services Hub Redesign Cluster** — docs_superpowers_plans_2026_05_09_nav_services_dropdown, docs_superpowers_specs_2026_05_09_nav_services_dropdown_design, docs_superpowers_plans_2026_05_09_services_page_redesign, docs_superpowers_specs_2026_05_09_services_page_redesign_design, docs_superpowers_plans_2026_05_09_nav_services_dropdown_nav_services_dropdown, docs_superpowers_plans_2026_05_09_services_page_redesign_services_page_redesign [INFERRED 0.75]
- **Small-Team Positioning Correction Cluster** — docs_superpowers_plans_2026_08_18_competitive_capture_competitive_capture, docs_superpowers_plans_2026_08_18_value_care_and_onpage_seo_value_care_onpage_seo, docs_superpowers_plans_2026_08_18_competitive_capture, docs_superpowers_plans_2026_08_18_value_care_and_onpage_seo [INFERRED 0.65]
- **New Page Creation Workflow (head, internal linking, JSON-LD)** — _claude_skills_new_page_skill, _claude_skills_new_page_references_head_checklist, _claude_skills_new_page_references_internal_linking, _claude_skills_new_page_references_jsonld_by_page_type [EXTRACTED 1.00]
- **Pre-Commit Quality Gates (build, copy, wiring)** — _claude_skills_build_and_verify_skill, _claude_skills_writing_site_copy_skill, _claude_skills_new_page_skill [INFERRED 0.75]
- **Copy Quality Toolkit (house rules, generic editing, plain English)** — _claude_skills_writing_site_copy_skill, _claude_skills_copy_editing_skill, _claude_skills_copy_editing_references_plain_english_alternatives [INFERRED 0.65]
- **Shared Site Chrome Partials (nav, footer, head-extras, care-strip)** — partials_nav_html, partials_footer_html, partials_head_extras_html, partials_care_strip_html [INFERRED 0.75]
- **Competitor Pricing Comparison Dataset (LFS vs LCS)** — compare_london_funeral_singers_pricing_table, data_competitor_pricing_lfs_provider, data_competitor_pricing_lcs_prices, data_competitor_pricing_derived_figures [EXTRACTED 1.00]
- **B2B Landing Page Family (for-*.html)** — for_charities, for_event_managers, for_funeral_directors, for_hotels, for_livery_companies, for_property_managers, for_wedding_planners [INFERRED 0.85]
- **Christmas Season Conversion Page Cluster** — christmas, carol_singers, for_hotels, for_livery_companies, for_charities, for_property_managers, for_event_managers [INFERRED 0.75]
- **CLAUDE.md House Conventions** — claude_vat_non_registration_rule, claude_no_review_schema_rule, claude_pricing_consistency_rule, claude_competitor_claim_validation, claude_compare_pages_isolation_rule, claude_form_security_convention [EXTRACTED 1.00]
- **SEO Audit Fix Programme Manual Tasks** — manual_actions_gbp_claim, manual_actions_citation_building, manual_actions_review_workflow, manual_actions_gsc_ga4_credentials, manual_actions_fastly_vcl, manual_actions_og_image_infra, manual_actions_indexnow, manual_actions_css_extraction [EXTRACTED 1.00]
- **Commercial Pillar Pages (Christmas, Corporate, Funerals + Weddings)** — christmas, corporate, funerals [EXTRACTED 1.00]
- **Marketing pages that repeat the pricing.html figures (single source of truth)** — pricing_choir_singer_pricing, weddings_wedding_choirs_singers, services_funeral_wedding_ceremony_music_services, index_the_london_choral_service, llms_ai_crawler_manifest [INFERRED 0.75]
- **Core pages assembled from the shared nav/footer partials via build.sh** — index_the_london_choral_service, listen_listen_to_our_singers_musicians, pricing_choir_singer_pricing, services_funeral_wedding_ceremony_music_services, weddings_wedding_choirs_singers, privacy_privacy_policy, thank_you_thank_you_page [INFERRED 0.65]

## Communities (76 total, 19 thin omitted)

### Community 0 - "Christmas Carol Repertoire"
Cohesion: 0.05
Nodes (80): A Spotless Rose, Adam Lay Ybounden, All I Want for Christmas Is You, Boris Ord, Carol singers, Cecil Frances Alexander, Charles Wesley, Christina Rossetti (+72 more)

### Community 1 - "Funeral & Wedding Hymns"
Cohesion: 0.06
Nodes (77): All Things Bright and Beautiful, Amazing Grace, Anima Christi, Ave Maria (Schubert), Be Not Afraid, Be Thou My Vision, Blackbird (The Beatles), Bridge Over Troubled Water (+69 more)

### Community 2 - "Core Site Pages"
Cohesion: 0.09
Nodes (50): 404 Not Found Page, About Page, Carol Singers Page, Carol Singers Hire Offering, Christmas Page, Christmas Carol Services Offering, Compare Pages / B2B Landing Page Isolation Rule, Form Security Convention (hCaptcha + Honeypot) (+42 more)

### Community 3 - "Wedding Music Repertoire"
Cohesion: 0.09
Nodes (45): A Thousand Years (Christina Perri), Air on the G String (Bach), All of Me (John Legend), Arrival of the Queen of Sheba (Handel), Ave Maria (Bach/Gounod or Schubert), Ave Verum Corpus (Mozart), Bridal Chorus (Wagner), Brother James's Air (+37 more)

### Community 4 - "Build Pipeline & Conventions"
Cohesion: 0.06
Nodes (36): build-and-verify Skill, build.sh script, GA4/Ads Sitewide Analytics Sweep Convention, Build Pipeline Convention, Competitor Claim Validation Convention, CSS Source Files Convention, No AggregateRating/Review Schema Rule, Partials System (Shared Markup Source of Truth) (+28 more)

### Community 5 - "Project Skills Toolkit"
Cohesion: 0.08
Nodes (37): ab-test-setup Skill, ai-seo Skill, analytics-tracking Skill, build-and-verify Skill, CSS Inlining Build Pipeline (build.sh 4 steps), Site-Wide Sweep Procedure (scripted bulk edits outside partials), Two Cardinal Rules (never hand-edit generated style block or partial markers), competitor-alternatives Skill (+29 more)

### Community 6 - "Traditional Christmas Carols"
Cohesion: 0.22
Nodes (37): The Best Christmas Carols for a Carol Service, Hark! The Herald Angels Sing, In the Bleak Midwinter, O Come, All Ye Faithful, Once in Royal David's City, Silent Night, Hiring a Choir for Your Christmas Event, Music for a Christmas Drinks Reception (+29 more)

### Community 7 - "Brand & Founder Identity"
Cohesion: 0.11
Nodes (33): Alma Consort Ltd (legal name; The London Choral Service is its operating/trading name), Intro video — YouTube Lov_NegzVhM, "Singers for Funerals, Weddings, and Events across the UK" (uploaded 2026-03-13, 43s), Luca Wetherall — Founder & Artistic Director, Tutor in Music at University of Oxford, JSON-LD numberOfEmployees minValue 150 (organization schema on index.html) — potentially inconsistent with the site's 'small, hand-picked team' positioning stated in the same page's copy, Royal Academy of Music (source conservatoire for musicians), Royal College of Music (source conservatoire for musicians), index.html — Homepage (The London Choral Service), University of Oxford (Luca Wetherall's academic affiliation) (+25 more)

### Community 8 - "Cambridge Area Page"
Cohesion: 0.08
Nodes (25): Christmas Carol Singers in Cambridge, Cambridge, Funeral Music in Cambridge, King's College Chapel Choral Tradition (500+ years), Funeral and Wedding Choirs in Cambridge (page), Wedding Choirs in Cambridge, Christmas Carol Singers in Oxford, Oxford (+17 more)

### Community 9 - "House Claims Validator Tests"
Cohesion: 0.16
Nodes (20): Drop `html` into a temp repo as index.html, run the validator, return (exit,…, The true statement must not trip the VAT pattern., carol-singers.html legitimately says a room holds up to 150 guests., z-index: 150 and 150ms transitions must not trip the roster pattern., for-funeral-directors.html deliberately says 'one person, not a roster'., run_on(), test_150_plus_fails(), test_aggregate_rating_fails() (+12 more)

### Community 10 - "Barking & Dagenham Page"
Cohesion: 0.19
Nodes (18): London Borough of Barking and Dagenham, Funeral Singers in Barking and Dagenham, The London Choral Service, Funeral and wedding choirs in Barking and Dagenham (page), St Margaret's Church, Barking, Wedding Choirs in Barking and Dagenham, Royal Borough of Greenwich, Funeral Singers in Greenwich (+10 more)

### Community 11 - "Site Improvement Roadmap"
Cohesion: 0.18
Nodes (17): Site Improvement Roadmap, Nav Services Dropdown Plan, Nav Services Dropdown Initiative, Services Page Redesign Plan, Services Page Hub Redesign Initiative, Christmas Expansion Plan, Christmas Expansion & Seasonal SEO Initiative, Competitive Capture Plan (+9 more)

### Community 12 - "Newham Borough Page"
Cohesion: 0.19
Nodes (13): London Borough of Newham, Christmas carol singers in Newham, City of London Cemetery and Crematorium (Manor Park), East London Crematorium, Funeral music in Newham, Funeral and wedding choirs in Newham, Wedding choirs in Newham, Waltham Forest (+5 more)

### Community 13 - "Redbridge Borough Page"
Cohesion: 0.21
Nodes (13): London Borough of Redbridge, Christmas carol singers in Redbridge, Forest Park Crematorium, Funeral music in Redbridge, Funeral and wedding choirs in Redbridge, St Mary the Virgin, Wanstead, Wedding choirs in Redbridge, Christ Church Spitalfields (+5 more)

### Community 14 - "Brent Borough Page"
Cohesion: 0.29
Nodes (12): London Borough of Brent, Funeral Singers in Brent, The London Choral Service, Funeral and wedding choirs in Brent (page), St Mary's Willesden, Wedding Choirs in Brent, London Borough of Hackney, Funeral Singers in Hackney (+4 more)

### Community 15 - "Bromley Borough Page"
Cohesion: 0.29
Nodes (12): London Borough of Bromley, Funeral Singers in Bromley, The London Choral Service, Funeral and wedding choirs in Bromley (page), St Peter & St Paul Bromley Parish Church, Wedding Choirs in Bromley, Havering, Funeral Singers in Havering (+4 more)

### Community 16 - "Camden Borough Page"
Cohesion: 0.29
Nodes (12): London Borough of Camden, Funeral Singers in Camden, The London Choral Service, Funeral and wedding choirs in Camden (page), St Pancras Old Church, Wedding Choirs in Camden, City of London, Funeral Singers in City of London (+4 more)

### Community 17 - "Harrow Borough Page"
Cohesion: 0.29
Nodes (12): London Borough of Harrow, Breakspear Crematorium, Funeral Singers in Harrow, The London Choral Service, Funeral and wedding choirs in Harrow (page), Wedding Choirs in Harrow, London Borough of Hillingdon, Breakspear Crematorium (+4 more)

### Community 18 - "SEO & Site Improvement Plans"
Cohesion: 0.24
Nodes (11): SEO & Conversion Improvements Plan, SEO & Conversion Improvements Initiative, Site Improvements Plan (v2), Site Improvements Programme (v2), Music Guides Redesign Plan, Music Guides Index Redesign Initiative, SEO Audit Fixes Plan, SEO Audit Fixes Initiative (+3 more)

### Community 19 - "Chester & Manchester Pages"
Cohesion: 0.20
Nodes (10): Christmas Carol Singers in Chester, Chester, Funeral Music in Chester, Funeral and Wedding Choirs in Chester (page), Wedding Choirs in Chester, Christmas Carol Singers in Manchester, Manchester, Funeral Music in Manchester (+2 more)

### Community 20 - "Birmingham Area Page"
Cohesion: 0.22
Nodes (9): Christmas Carol Singers in Birmingham, Birmingham, Funeral Music in Birmingham, Funeral and Wedding Choirs in Birmingham (page), Wedding Choirs in Birmingham, Coverage Model: Same Musicians Travel From London, 33 London Borough Pages (linked from the London hub), Areas We Serve — Hub Page (+1 more)

### Community 21 - "Funeral Hymn Repertoire"
Cohesion: 0.22
Nodes (9): All Things Bright and Beautiful, Amazing Grace, Dear Lord and Father of Mankind, Guide Me, O Thou Great Redeemer, How Great Thou Art, Jerusalem (hymn), The Lord's My Shepherd (Crimond), Make Me a Channel of Your Peace (+1 more)

### Community 22 - "Islington Borough Page"
Cohesion: 0.32
Nodes (8): London Borough of Islington, Christmas carol singers in Islington, Funeral music in Islington, Islington Cemetery, Funeral and wedding choirs in Islington, Pricing from £295 (Islington), Union Chapel, Wedding choirs in Islington

### Community 23 - "Cross-Borough References"
Cohesion: 0.29
Nodes (8): Royal Borough of Kensington and Chelsea, London Borough of Lambeth, London Borough of Lewisham, London Borough of Merton, London Borough of Southwark, Tower Hamlets, London Borough of Wandsworth, City of Westminster

### Community 24 - "Richmond Borough Page"
Cohesion: 0.32
Nodes (8): London Borough of Richmond upon Thames, Christmas carol singers in Richmond, Funeral music in Richmond, Hampton Court Chapel, Mortlake Crematorium, Funeral and wedding choirs in Richmond upon Thames, Pricing from £295 (Richmond), Wedding choirs in Richmond

### Community 25 - "Westminster Borough Page"
Cohesion: 0.39
Nodes (8): Christmas carol singers in Westminster, Funeral music in Westminster, Guards Chapel, Wellington Barracks, Funeral and wedding choirs in Westminster, Pricing from £295 (Westminster), Richmond Crematorium / Putney Vale Crematorium, Savoy Chapel, Westminster Cathedral

### Community 26 - "Kensington & Chelsea Page"
Cohesion: 0.38
Nodes (7): Christmas carol singers in Kensington Chelsea, Funeral music in Kensington Chelsea, Funeral and wedding choirs in Kensington & Chelsea, Pricing from £295 (Kensington-Chelsea), Richmond Crematorium / Putney Vale Crematorium, Royal Hospital Chelsea Chapel, Wedding choirs in Kensington Chelsea

### Community 27 - "Kingston Borough Page"
Cohesion: 0.33
Nodes (7): Royal Borough of Kingston upon Thames, Christmas carol singers in Kingston, Funeral music in Kingston, Kingston Crematorium, Funeral and wedding choirs in Kingston upon Thames, Pricing from £295 (Kingston), Wedding choirs in Kingston

### Community 28 - "Lambeth Borough Page"
Cohesion: 0.43
Nodes (7): Christmas carol singers in Lambeth, Funeral music in Lambeth, Honor Oak Crematorium (Southwark), Funeral and wedding choirs in Lambeth, St John's Waterloo, Wedding choirs in Lambeth, West Norwood Cemetery Chapel

### Community 29 - "Lewisham Borough Page"
Cohesion: 0.43
Nodes (7): Christmas carol singers in Lewisham, Funeral music in Lewisham, Grove Park Cemetery, Hither Green Crematorium, Lewisham Crematorium, Funeral and wedding choirs in Lewisham, Wedding choirs in Lewisham

### Community 30 - "Merton Borough Page"
Cohesion: 0.43
Nodes (7): Christmas carol singers in Merton, Funeral music in Merton, Morden Cemetery, Funeral and wedding choirs in Merton, South London Crematorium, Wedding choirs in Merton, Wimbledon Parish Church

### Community 31 - "Southwark Borough Page"
Cohesion: 0.38
Nodes (7): Christmas carol singers in Southwark, Funeral music in Southwark, Honor Oak Crematorium, Funeral and wedding choirs in Southwark, Southwark Cathedral, Wedding choirs in Southwark, Wedding choirs in Westminster

### Community 32 - "Sutton Borough Page"
Cohesion: 0.38
Nodes (7): All Saints Church, Carshalton, London Borough of Sutton, Christmas carol singers in Sutton, Funeral music in Sutton, North East Surrey Crematorium, Funeral and wedding choirs in Sutton, Wedding choirs in Sutton

### Community 33 - "Compare Page & Shared Chrome"
Cohesion: 0.29
Nodes (7): Compare Page FAQPage Content, Compare: London funeral singers, Competitor Pricing Data (data/competitor-pricing.yml), Embedded Video Metadata List, Site Footer Partial (shared site chrome), Head Extras Partial (font preloads), Site Navigation Partial (shared site chrome)

### Community 34 - "Bath Area Page"
Cohesion: 0.33
Nodes (6): Christmas Carol Singers in Bath, Bath, Funeral Music in Bath, Funeral and Wedding Choirs in Bath (page), Bath UNESCO World Heritage City Claim, Wedding Choirs in Bath

### Community 35 - "Canterbury Area Page"
Cohesion: 0.33
Nodes (6): Augustine's 597 AD Founding of English Christianity at Canterbury, Christmas Carol Singers in Canterbury, Canterbury, Funeral Music in Canterbury, Funeral and Wedding Choirs in Canterbury (page), Wedding Choirs in Canterbury

### Community 36 - "Barnet Borough Page"
Cohesion: 0.60
Nodes (6): London Borough of Barnet, Funeral Singers in Barnet, Golders Green Crematorium, The London Choral Service, Funeral and wedding choirs in Barnet (page), Wedding Choirs in Barnet

### Community 37 - "Bexley Borough Page"
Cohesion: 0.60
Nodes (6): London Borough of Bexley, Funeral Singers in Bexley, The London Choral Service, Funeral and wedding choirs in Bexley (page), St Mary the Virgin, Bexley, Wedding Choirs in Bexley

### Community 38 - "London Home-Base Page"
Cohesion: 0.33
Nodes (6): Christmas Carol Singers in London, London, Funeral Music in London, London as The London Choral Service's Home Base, Funeral and Wedding Choirs in London (page), Wedding Choirs in London

### Community 39 - "Croydon Borough Page"
Cohesion: 0.60
Nodes (6): London Borough of Croydon, Croydon Minster (Parish Church of St John the Baptist), Funeral Singers in Croydon, The London Choral Service, Funeral and wedding choirs in Croydon (page), Wedding Choirs in Croydon

### Community 40 - "Ealing Borough Page"
Cohesion: 0.60
Nodes (6): London Borough of Ealing, Funeral Singers in Ealing, The London Choral Service, Funeral and wedding choirs in Ealing (page), St Mary's Ealing, Wedding Choirs in Ealing

### Community 41 - "Enfield Borough Page"
Cohesion: 0.60
Nodes (6): London Borough of Enfield, Enfield Crematorium, Funeral Singers in Enfield, The London Choral Service, Funeral and wedding choirs in Enfield (page), Wedding Choirs in Enfield

### Community 42 - "Haringey Borough Page"
Cohesion: 0.60
Nodes (6): London Borough of Haringey, Funeral Singers in Haringey, The London Choral Service, Funeral and wedding choirs in Haringey (page), St Augustine's Highgate, Wedding Choirs in Haringey

### Community 43 - "Hounslow Borough Page"
Cohesion: 0.40
Nodes (6): London Borough of Hounslow, Christmas carol singers in Hounslow, Funeral music in Hounslow, Hanwell Crematorium, Funeral and wedding choirs in Hounslow, Wedding choirs in Hounslow

### Community 44 - "Wandsworth Borough Page"
Cohesion: 0.47
Nodes (6): All Saints Church, Wandsworth, Christmas carol singers in Wandsworth, Funeral music in Wandsworth, Funeral and wedding choirs in Wandsworth, Putney Vale Crematorium, Wedding choirs in Wandsworth

### Community 45 - "Rochester Area Page"
Cohesion: 0.33
Nodes (6): Christmas Carol Singers in Rochester, Rochester, Charles Dickens' Connection to Rochester, Funeral Music in Rochester, Funeral and Wedding Choirs in Rochester (page), Wedding Choirs in Rochester

### Community 46 - "Windsor Area Page"
Cohesion: 0.33
Nodes (6): Christmas Carol Singers in Windsor, Windsor, Funeral Music in Windsor, Funeral and Wedding Choirs in Windsor (page), Windsor's Royal and Ceremonial History (St George's Chapel), Wedding Choirs in Windsor

### Community 47 - "Music Guides JS Filtering"
Cohesion: 0.80
Nodes (5): applyFilter(), getCategoryFromURL(), init(), onChipClick(), onPopState()

### Community 48 - "Brighton Area Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in Brighton, Brighton, Funeral Music in Brighton, Funeral and Wedding Choirs in Brighton (page), Wedding Choirs in Brighton

### Community 49 - "Chelmsford Area Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in Chelmsford, Chelmsford, Funeral Music in Chelmsford, Funeral and Wedding Choirs in Chelmsford (page), Wedding Choirs in Chelmsford

### Community 50 - "Guildford Area Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in Guildford, Guildford, Funeral Music in Guildford, Funeral and Wedding Choirs in Guildford (page), Wedding Choirs in Guildford

### Community 51 - "Liverpool Area Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in Liverpool, Liverpool, Funeral Music in Liverpool, Funeral and Wedding Choirs in Liverpool (page), Wedding Choirs in Liverpool

### Community 52 - "Reading Area Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in Reading, Reading, Funeral Music in Reading, Funeral and Wedding Choirs in Reading (page), Wedding Choirs in Reading

### Community 53 - "Slough & Maidenhead Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in Slough & Maidenhead, Slough & Maidenhead, Funeral Music in Slough & Maidenhead, Funeral and Wedding Choirs in Slough & Maidenhead (page), Wedding Choirs in Slough & Maidenhead

### Community 54 - "St Albans Area Page"
Cohesion: 0.40
Nodes (5): Christmas Carol Singers in St Albans, St Albans, Funeral Music in St Albans, Funeral and Wedding Choirs in St Albans (page), Wedding Choirs in St Albans

### Community 55 - "Competitor Pricing Comparison"
Cohesion: 0.50
Nodes (4): LFS vs LCS Pricing Comparison Table, Derived Combo/Saving Figures Whitelist, LCS Mirrored Prices (whitelist), London Funeral Singers Provider Pricing

## Ambiguous Edges - Review These
- `Compare: London funeral singers` → `Embedded Video Metadata List`  [AMBIGUOUS]
  compare/london-funeral-singers.html · relation: references
- `index.html — Homepage (The London Choral Service)` → `JSON-LD numberOfEmployees minValue 150 (organization schema on index.html) — potentially inconsistent with the site's 'small, hand-picked team' positioning stated in the same page's copy`  [AMBIGUOUS]
  index.html · relation: conceptually_related_to

## Knowledge Gaps
- **287 isolated node(s):** `build.sh script`, `Company Christmas party entertainment`, `Lesser-known wedding choral pieces`, `Wedding choral repertoire`, `Information for event managers` (+282 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Compare: London funeral singers` and `Embedded Video Metadata List`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **What is the exact relationship between `index.html — Homepage (The London Choral Service)` and `JSON-LD numberOfEmployees minValue 150 (organization schema on index.html) — potentially inconsistent with the site's 'small, hand-picked team' positioning stated in the same page's copy`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Luca Wetherall` connect `Funeral & Wedding Hymns` to `Christmas Carol Repertoire`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `Areas We Serve — Hub Page` connect `Birmingham Area Page` to `Bath Area Page`, `Canterbury Area Page`, `London Home-Base Page`, `Cambridge Area Page`, `Rochester Area Page`, `Windsor Area Page`, `Brighton Area Page`, `Chelmsford Area Page`, `Guildford Area Page`, `Chester & Manchester Pages`, `Liverpool Area Page`, `Reading Area Page`, `Slough & Maidenhead Page`, `St Albans Area Page`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `SITE-STOP-SLOP-PLAN.md` connect `Build Pipeline & Conventions` to `Core Site Pages`, `Project Skills Toolkit`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **What connects `build.sh script`, `Company Christmas party entertainment`, `Lesser-known wedding choral pieces` to the rest of the system?**
  _287 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Christmas Carol Repertoire` be split into smaller, more focused modules?**
  _Cohesion score 0.050949367088607596 - nodes in this community are weakly interconnected._