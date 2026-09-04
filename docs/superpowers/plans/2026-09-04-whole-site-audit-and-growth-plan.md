# Whole-site audit and growth plan

**Date:** 2026-09-04
**Author:** Luca Wetherall (with Claude)
**Status:** Proposed. Plan only. No page, style, partial or data file was edited for this document.
**Related:** [docs/ROADMAP.md](../../ROADMAP.md), [MANUAL-ACTIONS-REQUIRED.md](../../../MANUAL-ACTIONS-REQUIRED.md), [SEO-AUDIT-2026-05-08.md](../../../SEO-AUDIT-2026-05-08.md), [SITE-STOP-SLOP-PLAN.md](../../../SITE-STOP-SLOP-PLAN.md), [2026-08-29-international-luxury-weddings.md](2026-08-29-international-luxury-weddings.md)

> **For agentic workers:** this is a strategy document, not an execution plan. Each programme in Part 3 is sized and scoped so that it can be turned into its own `YYYY-MM-DD-<name>-design.md` spec and plan. Nothing here is pre-approved; items marked **owner decision** or **human only** must not be attempted by an agent. Do not re-derive the audit numbers in Part 2; they were measured on commit `ae513f6` and are reproducible with the commands in Appendix A.

---

## Part 1. Executive summary

### The verdict

The site is technically clean and editorially broad, and it is under-proven. Four months of concentrated work since the May audit have fixed almost everything a crawler can measure: zero broken links, zero duplicate titles or descriptions, canonical, hreflang and social tags on 162 of 163 pages, valid JSON-LD on all 163, one H1 everywhere, self-hosted fonts, deferred analytics, click-to-load video. The site has grown from 99 indexable pages to 160, with 60 guides, 53 area pages, 22 destination pages and 7 trade landing pages.

What it has not yet earned is belief. There is not one photograph on the site. No singer other than the director is named. Fourteen of the twenty pieces on the Listen page have no recording. One promotional video is reused on twelve pages. The testimonial pool is about thirty quotes, anonymised, and recycled across pages whose geography they do not match ("Margaret, Dulwich" appears on 19 pages). Every destination page describes singing in a country without evidence of ever having done so. The SERP baseline taken on 2026-08-19 shows the site absent from the top results for its four head terms, and the reason is not on-page: it is authority and proof.

The next phase of work should therefore invert the ratio of the last one. Less breadth, more evidence, and a small number of assets that nobody else in this market can build because they require a musicologist.

### Top five priorities, in order

1. **Proof programme** (Part 3, P1). Photography, a comparative recording set, named singers, consented and located testimonials, and a case-notes page. Almost all of it is human work; the site side is small. Nothing else on this list compounds without it.
2. **Trust and compliance gaps that a careful buyer notices** (P11, P12). No terms of booking, no cancellation policy for families, no accessibility statement, no cookie consent for GA4 and Ads cookies, inconsistent response-time promises across some 56 pages, and a testimonial that says "she" on seven pages of a site that says Luca reads every enquiry.
3. **Structural dead ends** (P9). The 22 destination pages have exactly one inbound link each and three outbound. The seven trade pages and the planners page are reachable from no menu. The private register has no route back to the main site. Corporate links to no guides.
4. **The repertoire library** (P2). Per-piece pages built to musicological standard (tune, text, composer, source, liturgical fit, duration, voicing, a recording) with a programme builder that pre-fills the enquiry. This is the site's defensible content asset and its best link magnet.
5. **Freshness signals that are currently false or missing** (P10). 139 of 160 sitemap entries carry a lastmod earlier than the file's last commit; 46 guides had `dateModified` bulk-set to one day; visible dates and schema dates disagree on 37 of 60 guides; OG `article:modified_time` equals the published date everywhere.

### Quick wins (agent work, no human dependency, under a week in total)

- Destination sibling and guide links; a Destinations link in the footer and from `weddings.html`.
- Footer rebuilt as columns (Services, For professionals, Guides, Areas, Company) with company number and address.
- Corporate page links to its guide cluster; the five orphaned guides get a root-page link.
- Title suffix policy applied (138 titles carry no brand; the other 25 use three different brands).
- `<time>` elements and a single visible "Updated" line per guide; schema and OG dates reconciled.
- Sitemap `lastmod` generated from git in `build.sh` (ROADMAP R2 stretch, promoted).
- The `?occasion=quote-check` pre-fill bug on the compare page.
- Nine stale `TODO` comments removed; README and CLAUDE.md page counts corrected.
- Web manifest, a root `favicon.ico`, and `preconnect` replacing `dns-prefetch` for the tag manager.

---

## Part 2. Audit findings

Method: four read-only sweeps on 2026-09-04 (strategy documents, technical checks by script, content and conversion read-through, architecture and link graph), cross-checked by grep. Figures are for the 163 served HTML files; `partials/` and `graphify-out/graph.html` excluded.

### 2.1 What is in good order (leave alone)

| Check | Result |
|---|---|
| Broken internal links | 0 |
| Duplicate titles / descriptions | 0 / 0 |
| Titles over 60 chars | 0 (median 44) |
| Descriptions outside 141–161 chars | 2, both noindex (`thank-you`, `404`) |
| Canonical, hreflang en-gb + x-default, full OG and Twitter set | 162/163 (the 404 page is the exception, correctly) |
| One H1, no heading-level skips | 163/163 |
| JSON-LD | valid on 163/163; `#organization` referenced by `@id` 252 times rather than duplicated |
| Sitemap | 160 URLs, 0 ghosts, 0 missing indexable pages |
| Fonts | 4 self-hosted WOFF2, `font-display: swap`, Latin subset, two faces preloaded |
| Video | click-to-load facades, no iframe at load, `VideoObject` with real dates on 9 pages |
| Analytics | present on 163/163, deferred until idle or first interaction |
| Near-duplicate content | max pairwise 8-word-shingle Jaccard 0.135 (city pages), 0.115 (boroughs), 0.107 (destinations); no pair above 0.3 |
| Lang, viewport, theme-colour, skip link, print styles, reduced motion | present (skip link and print styles absent only on the 25 private-register pages) |

### 2.2 Findings by theme

Each finding: what, evidence, impact, and where it is fixed in Part 3.

**A. Proof and E-E-A-T** (Impact: high; the ranking and conversion ceiling)

- A1. Zero photographs anywhere. `assets/` holds 12 PNG favicons and OG cards, one ICO, one SVG. The `private-events.html` caption "Alma Consort in performance." has no image. → P1.
- A2. Nobody but Luca is named. No singer bios, no headshots, no ensemble page. The claim "auditions every singer" is unverifiable on the page. → P1.
- A3. `listen.html` lists 20 titles; 6 have a player. The other 14 are descriptive prose under a heading called Listen. → P1, P13.
- A4. Seven YouTube videos in total; the generic promo (`Lov_NegzVhM`) is embedded on 12 pages. No wedding, crematorium or corporate footage. The private-events voicing selector has all four video slots `null`. → P1.
- A5. Testimonials: roughly 30 distinct quotes rendered 90 times, no surnames, no venues (one exception), no dates. "Margaret, Dulwich" on 19 pages. "Tony, Surrey" on 8 pages, none in Surrey (ROADMAP R12, open). One quote ("she just took the music completely off our hands") on 7 pages contradicts "Luca reads every enquiry". → P1, P13.
- A6. `areas/index.html` states "The venue lists are real bookings, not generic place-holders." Outer-borough pages (Bromley, Sutton, Havering, Bexley) do not visibly support that claim. → P13.
- A7. Destinations: 22 pages of capable, specific writing (permits, rites, acoustics, logistics) and no evidence of a single past engagement. Trust risk rather than SEO risk. → P1, P4.

**B. Trust, legal and compliance** (Impact: high for conversion; medium legal)

- B1. No terms of booking page. Deposit and payment terms appear only on `faq.html` and two `for-*` pages; cancellation, refund, weather, overrun and illness terms are absent for families. The `lcs-booking-agreement-generator` skill already holds 14 clauses of Terms of Booking that could be published. → P11.
- B2. No accessibility statement. → P11.
- B3. No cookie consent. GA4 and Google Ads set cookies; under PECR regulation 6 analytics and advertising cookies need consent. The snippet is inline on 163 pages, not a partial (ROADMAP R4 records the sequencing). → P10.
- B4. Company number 16785727 appears in JSON-LD and on 10 pages' body copy, but not in the shared footer; the registered office appears as a postcode only. Public liability insurance is mentioned on corporate and trade pages, not on weddings, funerals, pricing or FAQ. No DBS or safeguarding line for school and church work. → P11.
- B5. Response-time promises: "within the hour" (1 page), "within a few hours" (7), "within 24 hours" (1), "within 48 hours" (22), "one working day" (25). → P12.
- B6. `privacy.html` promises no marketing, which rules out email capture as a lead mechanism; the plan respects that. → P6, P8.

**C. Information architecture and internal linking** (Impact: high; cheap to fix)

- C1. Destination country pages: exactly 1 inbound body link each (from the hub), 3 outbound each, no sibling links, no guide links, no footer or nav path. Destinations are not mentioned by `partials/footer.html`, `partials/nav.html` or `partials/private-footer.html`. → P9.
- C2. Not reachable from nav or footer: all 7 `for-*` pages, `planners-and-venues.html`, `private-events.html`, `destinations/`, `compare/`, `luca-wetherall.html`. → P9.
- C3. The 25 private-register pages carry a header of logo plus Enquire only. No path to Pricing, Funerals or the guides. → P9, P7.
- C4. `corporate.html` links to 0 guides (6 links in total). Five guides receive no link from any root page: `abide-with-me`, `destination-wedding-choir`, `jerusalem`, `memorial-service-planning`, `popular-wedding-organ-music`. → P9.
- C5. Footer: one 19-city strip, no services column, no trade column, no legal column beyond FAQ and Privacy. `faq.html` and `privacy.html` have zero in-body inbound links. → P9.
- C6. Nav shows Christmas twice (dropdown and top level); scheduled for January removal (ROADMAP R9). → P9.
- C7. Link style is mixed: about 2,672 relative and 313 root-absolute hrefs, sometimes both in one page. Harmless to crawlers, a maintenance trap. → P10.
- C8. 25 pages (the private register) omit `<main id="main">`, the skip link and print styles. → P10.

**D. Freshness and date signals** (Impact: medium; currently sending false signals)

- D1. 139 of 160 sitemap `lastmod` values are earlier than the file's last git commit; the 2026-08-30 sweep touched 100 files and bumped 4 sitemap lines. → P10.
- D2. Guides: `dateModified` is 2026-08-18 on 46 of 60 and 2026-08-19 on 7 (a bulk set). The visible date is the published date on most pages; 37 of 60 show a visible date matching neither the day nor the month of `dateModified`. OG `article:modified_time` equals `datePublished`. No `<time>` element exists anywhere on the site. → P10.
- D3. Nine files still carry `<!-- TODO -->` comments above JSON-LD, six of them obsolete since R3. → P10.

**E. Titles, headings and page targeting** (Impact: medium)

- E1. Brand suffix: 138 titles carry none; 13 end "| London Choral Service", 9 "| LCS", 3 "| Alma Consort". → P10.
- E2. Two titles under 30 characters; `memorial-service-planning.html` is titled "How to Plan a Memorial Service" with no music keyword although the page is about music. → P13.
- E3. Destinations: editorial H1s ("Croatia has the stone; the difficulty is getting to it.") differ from titles on 17 pages. Acceptable if the opening paragraph carries the query, which it generally does. Keep, but audit the first 100 words per page. → P4.
- E4. `index.html` is the thinnest money page at 619 words and the only money page without a `BreadcrumbList` (correct) or any `Service` node. → P13.
- E5. `FAQPage` markup sits on 155 pages. Since August 2023 Google shows FAQ rich results only for authoritative government and health sites, so this markup earns no SERP feature here. It is harmless and still useful for AI answer engines; do not add more of it expecting rich results. `SpeakableSpecification` is Google News-oriented and likewise decorative here.

**F. Conversion path** (Impact: high)

- F1. The standard form has no venue, ensemble size or budget field, although the FAQ asks people to supply the venue. The private-register form has all three plus budget bands and UTM capture; the two forms should converge. → P12.
- F2. `compare/london-funeral-singers.html` sends `?occasion=quote-check`; `form.js` only pre-fills when a matching `<option>` exists, and contact has none, so the intent is dropped. → P12.
- F3. `thank-you.html` is 100 words, has no "what happens next", no calendar or WhatsApp follow-up, and the corporate `?from=` falls back to the generic conversion. → P12.
- F4. No price estimator, no room-size guidance tool, no availability signal beyond a sentence about December diaries. → P6.
- F5. Contact hours appear only on `contact.html`. → P12.

**G. Content quality and accuracy** (Impact: medium; the owner's stated priority is accuracy)

- G1. `music-guides/wedding-choir-guide.html`: "In a licensed venue, you cannot include any religious content, no hymns, no prayers, no readings from scripture." The restriction under the Approved Premises Regulations attaches to the ceremony proceedings, not the building or the day; General Register Office guidance permits incidental religious references; the local registration service rules on content; music before the proceedings and after the register is signed is unrestricted. The page's next sentence half-concedes this. Rewrite for precision and cite the regulation by name. → P13.
- G2. Borough template rigidity (ROADMAP R13): identical H2 order and FAQ set across 33 pages; the sentence about leading a congregation through a hymn "most of them only half-remember" appears on 24 pages. → P13, P3.
- G3. `wedding-choir-guide.html` ensemble section restates `pricing.html`; the strongest guides (`funeral-music-guide`, `carol-singers-cost`) carry named repertoire and real practice; the weakest lean on generic praise. Musical detail is names of pieces; tune names, keys, ranges, durations and sources are rare. → P2, P13.
- G4. Two brands run on one site with two design systems: The London Choral Service (138 pages) and Alma Consort (25 pages). The relationship is stated in body copy but not designed. → P7.
- G5. The house documents are stale: README and CLAUDE.md say ~106 pages, 37 guides, `contact.js` and `landing-form.js`; the repo has 163 pages, 60 guides and `form.js`. ROADMAP has two items numbered R9, and R7.2 (FAQ hub) and part of R7.3 (OG images) are done but unmarked. → P10.

**H. Performance and platform** (Impact: low to medium; needs field data to decide)

- H1. 51,422 bytes of CSS inlined on 138 pages; 19,786 on the other 25. Median page 81 KB before compression. LCP is text; no raster hero. Repeat-visit cost is the open question (ROADMAP R6, needs CrUX or GA4 pages-per-session). → P10.
- H2. No web manifest; no `/favicon.ico` at the root (crawlers and some browsers request it, producing 404 noise); `favicon-32/48/192.png` exist but nothing references them. → P10.
- H3. `dns-prefetch` for the tag manager and Web3Forms on every page; no `preconnect`. → P10.
- H4. `www.londonchoralservice.com` fails TLS rather than redirecting (MANUAL §15). Human only; the single most damaging open item for anyone who types "www". 
- H5. Security headers, HSTS preload, cache control and extensionless redirects are all impossible on GitHub Pages (MANUAL §5). A free Cloudflare proxy in front of Pages would provide them and Brotli. Owner decision.

**I. Off-site** (recorded, not re-planned)

Google Business Profile categories, five citations, the review workflow, Search Console credentials, seasonal Ads conversions, the Christmas listing surfaces, and the LinkedIn and ORCID identifiers are all open in `MANUAL-ACTIONS-REQUIRED.md`. The SERP baseline shows the AI answer layer quoting a stale £215 soloist price; a recrawl request is the fix. None of that is re-planned here; Part 4 sequences the on-site work so that it lands as those actions complete.

---

## Part 3. Growth programmes

Each programme has a purpose, a deliverable, the SEO target, the schema, dependencies, size, the metric that says it worked, and the risk. Sizes: S under a week, M two to four weeks, L a quarter, and always agent time unless marked human.

### P1. Proof programme

**Purpose.** Convert claims into evidence. This is the single change that raises the ceiling on everything else.

**Deliverables.**

1. *Photography day* (human). One rehearsal, one church, one crematorium chapel with permission, one reception room. Deliver: hero images for the 8 service pages, a portrait for `luca-wetherall.html`, ensemble images for soloist, four, eight and twelve, and 1200 × 630 crops for OG cards. Brief: plain dark dress, singers at the back of the building, no faces of mourners, no stock.
2. *The same hymn three ways* (human recording, agent wiring). Record one hymn and one anthem each as soloist, four voices and eight voices in one acoustic. Publish as a comparison player on `listen.html`, `pricing.html`, the private-events voicing selector (its four slots are `null` today) and the room-size tool (P6). Nobody else in this market has an A/B/C recording; it answers the question every enquirer asks and it is a natural link target.
3. *Singers page* (human consent, agent build). `/singers.html`: named singers with a two-line biography and a headshot, with written consent and a right to be removed. Schema: `Person` with `memberOf` the `#organization`. The page substantiates "auditioned", "conservatoire graduates" and the credit lists, and it gives Google entities to connect.
4. *Case notes* (human sourcing, agent writing). `/recent-services.html`: eight to twelve short, dated notes, each a real engagement with venue type, ensemble, programme and one sentence on what mattered. Names withheld where families prefer; venues and pieces named. Written to the `writing-site-copy` rules. Rotate quarterly. Schema: `ItemList` of `Event` with `performer` and `location`, no ratings.
5. *Testimonial consent and geography* (owner decision R12, then agent). Re-source every quote with first name, area and occasion type confirmed; remove the "she" quote or attribute it; place each quote only on pages whose geography matches; cap reuse at three pages per quote.

**SEO target.** Head terms ("funeral singers London", "wedding choir hire London", "hire carol singers London") are authority-limited. Proof assets earn links and brand searches; images give Google Images and Discover surfaces the site currently cannot appear on.

**Dependencies.** Human: photography, recordings, consent. Agent: everything else. Blocked until the human parts land; the wiring can be prepared with placeholders in a branch that is not merged.

**Size.** Human two days plus editing; agent M.

**Metric.** Enquiry-to-booking rate by page (needs GA4 events); brand-search impressions in Search Console.

**Risk.** Photographing in crematoria needs explicit permission. Singers may decline naming; publish only those who consent.

### P2. Repertoire library and programme builder

**Purpose.** Build the one content asset a musicologist can build and a directory cannot: an authoritative catalogue of the music the ensemble sings, per piece, to reference standard.

**Deliverables.**

1. `/repertoire/` hub with client-side filters (occasion, tradition, language, mood, voicing, duration, accompanied or unaccompanied) on the pattern of `js/music-guides.js`.
2. Piece pages, 80 to 120 over a year, starting from the seven hymn and motet pages that already exist as guides (`abide-with-me`, both `be-thou-my-vision` pages, `jerusalem`, `ubi-caritas-wedding`, both `anima-christi` pages). Each page carries: title and incipit; text author and source (with scriptural or liturgical origin where relevant); tune name, composer, date and first publication; hymnal references (New English Hymnal number via the `neh-lookup` skill, Common Praise and Hymns Ancient and Modern where known); typical key and range; performing forces and which of the ensemble's voicings suit it; duration; where in a service it sits (entrance, offertory, communion, commendation, recessional); the text where public domain, with a translation for Latin; a recording where one exists; three pieces that pair well; and the enquiry CTA. No invented facts; where a date or attribution is contested, say so.
3. *Programme builder.* On the hub, a user picks up to three performance pieces and any hymns; the page renders a printable running order and pre-fills the enquiry message with the selection. Static JS, no server, no email capture. Records the selection as a GA4 event.
4. Schema per piece: `MusicComposition` (`composer`, `lyricist`, `iswcCode` where known, `musicalKey`, `inLanguage`, `datePublished`) with `recordedAs` → `MusicRecording` → `VideoObject` where a recording exists; `BreadcrumbList`; `Article` for the commentary. Link each piece from the guides that name it and back.

**SEO target.** Long-tail queries the guides already touch but do not own: "[piece] funeral", "[piece] wedding", "[piece] lyrics meaning", "[piece] how long", "[hymn] tune name". Rich internal linking from 60 guides into 100 piece pages and back builds the topical cluster that currently stops at the guide level. Also the strongest link-earning content the site can have (organists, clergy, teachers and bloggers link to reference pages).

**Dependencies.** None for the first 40 pieces. Recordings from P1 improve it.

**Size.** L, in tranches of 20 pieces. The first tranche should be the 20 most-requested funeral pieces, because funeral search intent is the highest volume and the least seasonal.

**Metric.** Impressions and clicks on `/repertoire/` in Search Console; enquiries with a pre-filled programme.

**Risk.** Copyright: publish texts only where public domain (author died more than 70 years ago) and never reproduce copyrighted arrangements. Quality: one thin piece page undermines the whole; drop a piece rather than pad it.

### P3. Venue pages

**Purpose.** The most valuable local intent this business can serve is "[crematorium or church] music", and MANUAL §11 already holds Ads geo campaigns "until pages exist".

**Deliverables.**

1. `/venues/` with London crematoria first (Golders Green, City of London, West Norwood, Mortlake, Putney Vale, Honor Oak, Hendon, Enfield, South London, Beckenham, and the rest), then the churches and chapels the ensemble has actually sung in.
2. Each page: acoustic character, chapel sizes and time-slot lengths, organ or piano availability, where singers stand, how the ensemble arrives and warms up, which voicing suits the room, what the venue's own rules are (recorded music systems, livestream), travel and parking, and the local pricing note. Only venues with first-hand experience; label the source of knowledge on the page.
3. Cross-link: each borough page links its venues; each venue page links its borough, the funeral or wedding pillar, and the relevant repertoire.
4. Schema: `Place` (or `CivicStructure` / `Church`) for the venue, `Service` with `areaServed` referencing it, `BreadcrumbList`. No `LocalBusiness` for a venue the company does not own.

**SEO target.** "[venue name] funeral music", "[venue] singers", "[venue] wedding choir". Low competition, high intent, and it gives the borough pages something real to link to, which directly addresses A6 and G2.

**Dependencies.** A list of venues sung in (human, one hour). Nothing else.

**Size.** M for 30 London venues; a second tranche for cathedral-city venues from the `areas/` set.

**Metric.** Clicks from venue queries; Ads geo campaign CPA once §11 runs.

**Risk.** Accuracy of slot lengths and rules changes; carry a visible checked date like the destinations pages do.

### P4. Geography: counties, regions and destination regions

**Purpose.** The area set jumps from 20 cities to 33 London boroughs and stops. Testimonials cite Surrey, Hampshire and Buckinghamshire; there is no page for any county.

**Deliverables.**

1. Eight to ten county pages: Surrey, Kent, Essex, Hertfordshire, Berkshire, Buckinghamshire, Hampshire, Sussex, Oxfordshire, Cambridgeshire. Each written on the city-page pattern with real venues, travel bands from London, and a link list of the towns it covers. Schema `AdministrativeArea` with `containsPlace`.
2. Destination region pages (the unbuilt PR 4 of the 2026-08-29 plan): Lake Como, Amalfi, Tuscany, Côte d'Azur, Ibiza, Mallorca, Santorini. Do not build these until P1 has produced one overseas engagement to show; a further tier of unproven pages worsens A7.
3. A visible map or region index on `areas/index.html` so the 53 links stop being one list.

**SEO target.** "[county] funeral singers", "[county] wedding choir"; county terms carry more searches than most single towns.

**Size.** M for counties. Region pages M, gated.

**Metric.** Area-page impressions by county query; enquiries by postcode.

**Risk.** Doorway-page test as in the destinations plan: 60 per cent unique body copy, measured, not assumed.

### P5. New occasions and audiences

**Purpose.** Five occasions carry the site. Several adjacent occasions have search demand, match the ensemble's strengths and need no new capability.

**Deliverables, in priority order.**

1. *Memorial services and celebrations of life* pillar page. The contact form already offers "memorial"; a guide exists; there is no service page. Highest volume, year-round.
2. *For churches and clergy* (`for-churches.html`): a choir for a parish without one, for a patronal festival, an Easter or Christmas service, a wedding at your church, or a termly sung Evensong. Evensong is mentioned on two pages only. This is a continuity product (see P8) and a natural fit for the director's cathedral and college background.
3. *Requiem Mass and Catholic liturgy* page: Mass settings (plainsong, Byrd, Victoria, Fauré and Duruflé excerpts), Latin propers, what the rite requires and where sung music sits in it. Musicological credibility is the differentiator; write it to the standard of an ordo, not a brochure.
4. *Remembrance Sunday* and *Easter and Holy Week* seasonal pages, on the christmas.html model but smaller: for livery companies, councils, schools and churches (Remembrance), and parishes and cathedrals with stretched choirs (Easter). Anti-cannibalisation contract as in the Christmas spec.
5. *For schools* (`for-schools.html`): speech days, carol services, founders' days, memorial assemblies. Needs the DBS and safeguarding line from P11 first.
6. *Christenings, blessings and vow renewals* as one page; *interment of ashes and graveside singing* as a section on the funerals pillar.

**SEO target.** One head term per page, recorded in a contract table before writing.

**Size.** S per page; the set is M.

**Metric.** Enquiries by occasion type (the form select already captures it).

**Risk.** Spreading proof thinner. Each page must reuse P1 assets, not add claims.

### P6. Tools that answer the enquirer's question before they ask it

**Purpose.** The site's pricing is honest and complete; a small amount of interactivity turns it into a reason to enquire.

**Deliverables.**

1. *Price estimator* on `pricing.html`: ensemble, accompanist, travel band, Christmas Eve or Day premium, keyboard hire. Client-side, reads its figures from one JSON block generated from the pricing table so the house rule "prices must match pricing.html" is enforced by construction. Outputs a figure and a "send this estimate" button that pre-fills the form.
2. *Room-size guide*: capacity and building type in, recommended voicing out, using the sizing rules already written on `christmas.html` ("four singers will lead a room of 150; eight will carry a church of 400"). Embeds the P1 comparison recordings.
3. *Availability signal*: `data/availability.yml` maintained weekly by the owner with, for example, Saturdays remaining per month and December dates remaining; the build injects a truthful line on weddings and Christmas pages. Real scarcity only; the build fails if the file is older than 14 days in season.
4. *Programme builder* (P2).

**SEO target.** Indirect: engagement, and the estimator and calculator are link-worthy in their own right.

**Size.** S each; M together.

**Metric.** GA4 events on tool use; enquiries carrying an estimate.

**Risk.** An estimator that ever disagrees with `pricing.html`. Generate, never hand-copy, the figures.

### P7. Brand architecture: The London Choral Service and Alma Consort

**Purpose.** Two brands, two design systems and two navigation models on one domain is a decision made by accretion. It should be made on purpose.

**Options.**

- *A. One house, two registers.* Keep both, but give the private register a slim header with a route to the main site and give the main site a footer link to "Alma Consort for private engagements". Add `Organization.brand` / `alternateName` in schema and a short "About our two names" section on `about.html`.
- *B. Split the domains.* Move the 25 private-register pages to almaconsort.com with 301s. Cleaner brand story, but it halves the destination cluster's link equity and the site loses its luxury tier.
- *C. Fold Alma Consort into LCS* as "LCS Private" and retire the second brand on this site.

**Recommendation.** A, now; revisit B when almaconsort.com has its own proof. Under A, state on every register page which company invoices (already done in body copy) and use one `#organization` node.

**Size.** S. **Owner decision** on the option.

### P8. Offers for professionals: retained and repeat business

**Purpose.** Trade pages sell one-off referrals. The business frameworks point to continuity and bulk offers as the next revenue layer, and the trade audiences here are exactly the ones that buy annually.

**Deliverables.**

1. *Retained-choir arrangements* on `for-churches.html` and `for-hotels.html`: a termly Evensong or monthly sung service for a parish; a residency for a hotel's December. Priced as a term or season, invoiced quarterly, with a priority-date hold. Present as a named package with what is included, not as a discount.
2. *Standing carol-service booking* for corporate and livery clients: the same date held year on year, first refusal, one confirmation email. Continuity by default, cancellable by a stated date.
3. *Funeral director partnership page* deepened: a same-day confirmation promise, an order-of-service music insert the director can hand to families (P9 downloadables), and a quarterly repertoire update note. No referral fees on the page; if any exist they belong in the agreement, not the copy.
4. *Planner and venue supplier records* extended from `planners-and-venues.html` to a one-page PDF a planner can drop into a proposal.

**Size.** S per page. Pricing of retained arrangements is an **owner decision** and must appear on `pricing.html` first.

**Metric.** Repeat bookings per client; season bookings confirmed before September.

### P9. Information architecture, navigation and linking

**Purpose.** Fix the dead ends and give every page type a menu path.

**Deliverables.**

1. *Nav*: Services dropdown stays; add a "For professionals" dropdown (funeral directors, wedding planners, event managers, hotels, property managers, livery companies, charities, churches, schools, planners and venues); put Destinations under Weddings or Services; make the seasonal Christmas item data-driven (a date range in the partial) so R9 stops being a calendar task.
2. *Footer* rebuilt as five columns: Services; For professionals; Guides and repertoire; Areas (regions, not 19 flat links); Company (about, Luca, singers, terms, privacy, accessibility, company number and registered office, WhatsApp, phone, email).
3. *Private register header*: keep the register's look, add a compact link row (Weddings, Pricing, Contact, main site).
4. *Destinations*: sibling links within haul group; two guide links per country page; a "Marrying abroad?" module on `weddings.html` and the wedding guides; a Destinations link in both footers.
5. *Corporate*: link its guide cluster (the 24 Christmas guides already exist; there are no year-round corporate guides, which P13 addresses).
6. *The five orphaned guides* get a contextual link from a root page each.
7. *FAQ*: link contextually from every service page's FAQ block ("More questions").
8. Adopt one link style (root-absolute) for new work and convert on touch.

**Size.** S to M. Requires the `build-and-verify` skill and one ~163-file build diff.

**Metric.** Median in-body inbound links for destinations rising from 1 to 6 or more; crawl depth of trade pages falling to 2.

### P10. Technical platform and freshness

**Deliverables.**

1. *Analytics partial and consent mode* (R4): extract the GA4 and Ads snippet into `partials/analytics.html`, then add Consent Mode v2 with a minimal, house-styled banner. Default denied for analytics and ad storage in the UK; conversion modelling keeps Ads reporting usable. Compliance item, not an SEO item, and it must be done before Ads spend rises (MANUAL §11).
2. *Sitemap generated by `build.sh`* from the file tree and `git log -1 --format=%cs` per file, with an exclusion list for noindex pages (R2 stretch, promoted to ready). Removes the hand-maintenance convention and fixes D1 permanently.
3. *Dates*: one `<time datetime>` element per guide showing "Published" and "Updated"; `dateModified` and `article:modified_time` set from the same value; a rule that `dateModified` changes only with a substantive edit, so the bulk-set signal is not repeated.
4. *Title suffix policy*: money pages and hubs "| London Choral Service" where it fits in 60 characters; guides and piece pages no suffix; the private register "| Alma Consort". Document in `new-page`.
5. *OG images generated in the build*: a Playwright script renders a branded 1200 × 630 card per area, borough, destination and piece page from a template, so the 70 pages on the generic card get their own without a designer. Chromium is available in the agent environment; the output is committed like every other artefact.
6. *Manifest and favicons*: `site.webmanifest`, a root `favicon.ico`, reference the existing 192 px icon.
7. `preconnect` for the tag manager only on pages that load it; drop the redundant `dns-prefetch`.
8. *CSS strategy* (R6): stay inline until CrUX data exists; when it does, test a hybrid (8 KB critical inline, full sheet async with `rel=preload`). Not before.
9. *Cloudflare in front of Pages* (owner decision): security headers, HSTS preload, Brotli, cache control, extensionless redirects, and it also fixes the www TLS failure by proxying the subdomain.
10. *Hygiene*: remove the nine stale TODO comments; correct README and CLAUDE.md counts and file names; renumber the duplicate R9; mark R7.2 and R7.3 as done; add skip links, `<main id="main">` and print styles to the private register.

**Size.** Items 1 and 2 M; the rest S.

### P11. Trust pages

**Deliverables.**

1. `/terms.html`: Terms of Booking, derived from the 14 clauses the booking-agreement generator already uses, reviewed by the owner. Deposit, balance, cancellation windows and refunds, illness cover, weather and outdoor events, overrun, travel, keyboard hire, recording and photography consent, complaints.
2. `/accessibility.html`: a plain statement of what the site does (semantic HTML, skip links, contrast measured at 5.66:1, reduced-motion support, no autoplay) and how to ask for an alternative format.
3. Company number, registered office and public liability insurance in the footer Company column and on `faq.html`; a DBS and safeguarding line for school and church work once the facts are confirmed (**human**).
4. Add ICO registration reference to `privacy.html` if registered (**human to confirm**).

**Size.** S. Owner sign-off required on the terms.

### P12. Conversion path

**Deliverables.**

1. One enquiry form for the whole site: the private-register fields (venue, occasion, ensemble size, budget bands, how you heard, UTM capture, time on page) in the standard form, with the funerals variant kept short (name, phone, date, venue, message) because urgency is different.
2. Fix `?occasion=quote-check`: add the option, or map it to "funeral" with a hidden `source=quote-check` field.
3. One response promise, by channel, on every page: for example "WhatsApp and phone: same day. Email and form: one working day." Replace the five current variants.
4. `thank-you.html`: what happens next in three steps, the response promise, a WhatsApp deep link with the enquiry reference pre-filled, and the P8 downloadables. Add a corporate conversion label.
5. A "book a fifteen-minute call" link (Google Calendar appointment schedule or equivalent) for weddings and corporate; not for funerals.
6. Verify phone and WhatsApp click conversions actually fire (MANUAL §11 do-first) before any of the above is measured.

**Size.** S to M.

### P13. Content quality, accuracy and refresh

**Deliverables.**

1. *Accuracy corrections* (Appendix B), each a one-line fix. Do first.
2. *Listen page*: split into "Recordings" (the six with players, plus P1 additions) and "Repertoire" (linking to P2 pages). Stop describing sound the visitor cannot hear.
3. *Borough template* (R13, spec first): three or four alternative section orders, venue-first where P3 pages exist, one borough-specific FAQ per page, and testimonials only where geography matches.
4. *Guide refresh cycle*: each guide reviewed once a year in the month before its season; a checklist covering prices, links, dates, the `dateModified` rule, and one new paragraph of first-hand practice. Track in a `data/guide-review.yml` so the build can warn on guides untouched for 13 months.
5. *Year-round corporate guides*: three to five (AGM and awards dinners, memorial and remembrance events for firms, summer receptions, product launches and unveilings, livery installation dinners) so corporate stops depending on Christmas.
6. *Home page*: raise from 619 words with a proof band (P1), one paragraph per occasion, and `Service` nodes in schema.
7. *Cannibalisation watch* once Search Console exists: `christmas.html` against `carol-singers.html`; `funeral-choir-guide` against `funerals.html`; `hiring-a-choir` against `services.html`; the three "best in London" guides against their pillars. Consolidate or re-target on evidence, not in advance.

**Size.** S for corrections; M for the rest.

### P14. Original data and link earning

**Purpose.** Authority is the missing input. The site has two things that can earn links without asking: a musicologist and a booking record.

**Deliverables.**

1. *Annual report: what families and couples chose.* From the booking record, anonymised and aggregated: the most requested funeral pieces, wedding pieces and carols by year, by region, by ensemble size; average number of hymns; the share of non-religious funerals. Published each January as a page with a downloadable table and charts, refreshed yearly, pitched to funeral trade press, wedding press and church music publications. Original data is the most reliably linked content type there is, and nobody in this market publishes any.
2. *Reference pieces* only a musicologist writes: "Every setting of the Nunc Dimittis a small choir can sing", "The tunes behind the ten most-sung English hymns", "What the Requiem texts actually say" with translations. Written to the standard of a programme note, not a blog post.
3. *Owned links*: reciprocal links with almaconsort.com and lucawetherall.co.uk (MANUAL §13.5), the Oxford faculty page (exists), Delphian and any recording credits, church and school pages where the director holds posts (with their permission).

**Size.** Report M per year, human data export first. Reference pieces S each.

**Metric.** Referring domains in Search Console; brand searches.

### What not to do

- No `AggregateRating`, `Review` or star markup anywhere, including on a testimonials page. The build already enforces this.
- No further templated geography (more countries, towns or boroughs) until P1 has produced proof and P3 has given the local pages something real to reference.
- No blog. The guide, piece and reference formats already cover editorial content with a better shelf life.
- No email capture or newsletter; `privacy.html` promises none, and the lead mechanisms above do not need it.
- No CSS extraction without field data.
- No AI-generated imagery of singers, venues or services. Real photographs or none.

---

## Part 4. Sequencing

Christmas enquiries peak from September; the proof recordings and the conversion fixes must land before November. Everything that is only agent time can start now.

### Now to end of October (before the Christmas peak)

| Item | Type | Programme |
|---|---|---|
| Accuracy corrections (Appendix B) | agent, S | P13 |
| Linking fixes, footer columns, For professionals nav, destinations links | agent, S–M | P9 |
| Form convergence, quote-check fix, one response promise, thank-you page | agent, S–M | P12 |
| Verify phone and WhatsApp conversions fire | human, XS | P12 |
| Sitemap from git; dates and `<time>`; title suffix policy; TODO and doc hygiene | agent, S | P10 |
| Terms of booking and accessibility statement drafted for sign-off | agent draft, owner review | P11 |
| Photography day and the three-ways recording session | human | P1 |
| Availability signal for December | owner data, agent build | P6 |
| www TLS fix | human | H4 |

### November to February

| Item | Type | Programme |
|---|---|---|
| Wire P1 assets: heroes, comparison player, singers page, case notes | agent, M | P1 |
| Repertoire library tranche 1: 20 funeral pieces plus hub and builder | agent, M | P2 |
| Memorial services pillar; requiem and Catholic liturgy page | agent, S each | P5 |
| Venue pages tranche 1: London crematoria | agent, M | P3 |
| Analytics partial and Consent Mode v2 | agent, M | P10 |
| Price estimator and room-size guide | agent, S–M | P6 |
| January: seasonal nav demotion (data-driven), price date bump, annual report draft | agent | P9, P14 |

### March to August

| Item | Type | Programme |
|---|---|---|
| Repertoire tranches 2 and 3: wedding pieces, then carols before September | agent | P2 |
| County pages | agent, M | P4 |
| For churches, for schools, Easter and Remembrance pages | agent | P5, P8 |
| Borough template spec and rollout (R13) | agent, spec first | P13 |
| Year-round corporate guides | agent | P13 |
| Brand architecture decision and implementation | owner, then agent | P7 |
| Retained-choir offers on pricing and trade pages | owner pricing, then agent | P8 |
| Destination region pages, if an overseas engagement exists to show | agent, gated | P4 |
| CSS hybrid test, if CrUX data justifies it | agent | P10 |

### Dependencies that gate everything

1. Search Console and GA4 access (MANUAL §4). Without it every metric above is guessed. The single most valuable human action after the www fix.
2. Photography and recordings (P1). Gate P4 region pages, the singers page, the comparison player and the room-size guide.
3. Owner decisions: testimonial re-sourcing (R12), brand architecture (P7), retained-offer pricing (P8), Cloudflare (P10.9), the terms text (P11).

---

## Part 5. Measurement

The success metric stays the one set in the private-events spec: cost per qualified enquiry, per page. To read it, the site needs GA4 events that do not exist today.

| Event | Fires on | Programme |
|---|---|---|
| `enquiry_submit` with `occasion`, `ensemble`, `budget_band`, `source_page` | every form | P12 |
| `whatsapp_click`, `phone_click`, `email_click` with `source_page` | footer, sticky bar, CTAs (partly present via the thank-you redirect) | P12 |
| `estimate_created`, `programme_built`, `room_guide_used` | tools | P6, P2 |
| `recording_play` with `voicing` | comparison player | P1 |
| `download` with `asset` | order-of-service templates, planner PDF | P8 |

Search Console reads to take monthly once access exists: impressions and average position for the four head terms; clicks by directory (`/music-guides/`, `/repertoire/`, `/areas/`, `/venues/`, `/destinations/`); pages receiving zero clicks in 90 days (candidates for consolidation); the cannibalisation pairs in P13.7.

---

## Appendix A. Reproducing the audit numbers

All read-only. Run from the repo root on a clean tree.

```bash
# Page inventory
find . -name '*.html' -not -path './partials/*' -not -path './graphify-out/*' | wc -l

# Sitemap lastmod older than last commit (count)
python3 - <<'EOF'
import re,subprocess
sm=open('sitemap.xml').read()
n=0
for loc,lm in re.findall(r'<loc>https://londonchoralservice.com/([^<]*)</loc>\s*<lastmod>([^<]*)</lastmod>',sm):
    f=(loc or 'index.html'); f=f+'index.html' if f.endswith('/') else f
    c=subprocess.run(['git','log','-1','--format=%cs','--',f],capture_output=True,text=True).stdout.strip()
    n+= c>lm
print(n)
EOF

# Destinations inbound links (should be 1 each today)
grep -rl 'destinations/italy.html' --include='*.html' . | grep -v graphify

# Response-time promises
for p in "within the hour" "within a few hours" "within 24 hours" "within 48 hours" "one working day"; do printf '%s: ' "$p"; grep -rli "$p" --include='*.html' . | grep -v graphify | wc -l; done

# Stale TODO comments
grep -rl 'TODO' --include='*.html' . | grep -v graphify

# Testimonial reuse
grep -rl 'Margaret, Dulwich' --include='*.html' . | grep -v graphify | wc -l

# Guides with no root-page inbound link, JSON-LD validity
python3 validate_jsonld.py
```

## Appendix B. Accuracy corrections (do first, one commit)

| # | Page(s) | Issue | Correction |
|---|---|---|---|
| 1 | `music-guides/wedding-choir-guide.html` | "In a licensed venue, you cannot include any religious content, no hymns, no prayers, no readings from scripture." | The restriction (Marriages and Civil Partnerships (Approved Premises) Regulations 2005) applies to the ceremony proceedings as approved by the superintendent registrar; General Register Office guidance permits incidental religious references; music before the proceedings and after the register is signed is unrestricted. Rewrite to say so and cite the regulation. Verify against current GRO guidance before publishing. |
| 2 | 7 pages carrying "she just took the music completely off our hands" | Pronoun contradicts "Luca reads every enquiry" | Re-source, attribute to a named colleague, or remove. Owner decision R12 covers the wider pool. |
| 3 | ~56 pages | Five different response-time promises | One promise by channel (P12.3). |
| 4 | `compare/london-funeral-singers.html`, `js/form.js` | `?occasion=quote-check` never pre-fills | Add the option or map it (P12.2). |
| 5 | `areas/index.html` | "The venue lists are real bookings, not generic place-holders." | Either substantiate on every borough page or soften to "venues we know". |
| 6 | `listen.html` | 14 of 20 entries have no recording under a heading called Listen | Split into Recordings and Repertoire (P13.2). |
| 7 | `music-guides/memorial-service-planning.html` | Title lacks the music keyword the page is about | "How to Plan a Memorial Service: Music, Readings and Running Order". |
| 8 | 60 guides | Visible date is the published date; schema `dateModified` bulk-set; OG modified equals published | P10.3. |
| 9 | 9 files | Stale `<!-- TODO -->` comments above JSON-LD | Remove the six obsolete; keep the three genuine (ORCID, LinkedIn) until MANUAL §1 resolves. |
| 10 | 24 area pages | The "half-remember" sentence copied verbatim | Vary or cut on the R13 rollout. |
| 11 | README, CLAUDE.md, ROADMAP | Page and guide counts, script names, duplicate R9, unmarked R7.2 and R7.3 | Correct (P10.10). |
| 12 | `private-events.html` | Caption "Alma Consort in performance." with no image; voicing selector promises recordings it does not have | Remove the caption until P1; reword the selector note. |
| 13 | 25 private-register pages | No skip link, `<main id="main">` or print styles | Add via the register partial (P10.10). |

## Appendix C. Open ROADMAP items and where this plan places them

| ROADMAP | Status there | Here |
|---|---|---|
| R2 stretch (sitemap in build) | SPEC-FIRST | P10.2, promoted to ready |
| R3 sameAs (LinkedIn, ORCID) | BLOCKED-ON-HUMAN | unchanged |
| R4 consent mode | SPEC-FIRST | P10.1, sequenced before Ads spend |
| R6 CSS inlining | DECISION-NEEDED | P10.8, gated on CrUX |
| R7.1 listen audio | ready, assets blocked | P1.2, P13.2 |
| R7.2 FAQ hub | done, unmarked | P10.10 marks it |
| R7.3 per-page OG | partly done | P10.5 generates the rest |
| R9 (January nav) | scheduled | P9.1 makes it data-driven |
| R11 Victorian allowlist | ready | unchanged, do with P10.10 |
| R12 testimonials | DECISION-NEEDED | P1.5, Appendix B.2 |
| R13 borough template | SPEC-FIRST | P13.3, after P3 tranche 1 |
