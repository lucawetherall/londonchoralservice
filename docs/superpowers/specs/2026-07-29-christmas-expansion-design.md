# Christmas Expansion & Seasonal SEO

**Date:** 2026-07-29
**Pages affected:** `christmas.html`, `pricing.html`, `index.html`, `corporate.html`, `for-funeral-directors.html`, `for-wedding-planners.html`, `music-guides/index.html`
**New pages:** 12 (1 service page, 4 B2B landing pages, 7 music guides)
**Site-wide change:** all 52 area pages (19 cities + 33 London boroughs); global nav and footer (every `.html` file)
**Branch:** `claude/christmas-website-expansion-seo-9smuoe`
**Deadline pressure:** everything live and indexed by mid-August — booking research for December peaks from September, and the site's own copy says December dates fill by mid-September.

## Problem

Christmas is the highest-value season for a choir-for-hire business, and the site's entire Christmas surface is one corporate-only page plus six music guides. Audit findings, each verified against the repo:

1. **`christmas.html` has no FAQ section and no `FAQPage` node.** Its JSON-LD contains only `Service` + `AggregateOffer` + `BreadcrumbList` + two `LocalBusiness` stubs. `corporate.html`, `services.html`, `pricing.html` and every recent B2B page carry a visible FAQ mirrored into schema; the Christmas hub does not, so it forfeits FAQ rich results and answer-engine extraction on the site's most commercially valuable seasonal query set.
2. **`christmas.html` is missing from `llms.txt` entirely.** `grep -c 'christmas.html' llms.txt` returns 0. The site courts GPTBot/ClaudeBot via `robots.txt` and a hand-maintained `llms.txt`, and the Christmas hub is the one commercial page absent from it.
3. **The page is positioned corporate-only.** Title `Christmas Carol Singers for Corporate Events | LCS`, H1 "Christmas Carol Singers for Corporate Events", lede and body all address companies and office parties. Hotels, luxury apartment buildings, livery companies, charities running fundraising carol concerts, and private parties — all real, high-value Christmas hirers — have no entry point.
4. **The guides hub silently drops a guide.** Six Christmas guides exist on disk; `christmas.html` links five. `music-guides/best-christmas-carol-singers.html` is missing from `christmas.html`'s guide block *and* from the visible Christmas section of `music-guides/index.html`, although it is already present in that page's `ItemList` JSON-LD — a listing/structured-data mismatch of the same kind the May 2026 guides redesign was meant to eliminate.
5. **Zero Christmas content across all 52 area pages.** No city or borough page mentions Christmas, carols, or December in body copy, FAQ, or `Service.serviceType`. The site's entire local-SEO surface is invisible for seasonal local queries.
6. **"Nine Lessons and Carols" appears in no title or heading anywhere on the site.** The phrase occurs in body prose on three guides only. It is the highest-intent seasonal UK service phrase and nothing on the site is built to rank for it.
7. **No page targets "hire carol singers".** `christmas.html` targets *carol service*; the head term *hire carol singers / carol singers for hire* is a distinct, higher-volume intent (people who want singers moving through a party, not a structured service) and has no owner. The market is dominated by agency directories (Encore, Alive Network, Poptop, londoncarolsingers.com) whose average carol-group hire sits around £958–£1,108 per event.
8. **No B2B landing pages for the seasonal buyer types.** Three exist — funeral directors, wedding planners, event managers — and none covers hotels, property managers, livery companies, or charities, which are precisely the December decision-makers.
9. **Ensemble-label drift in the pricing area.** `pricing.html` calls the four-singer tier "a small choir of four singers"; `christmas.html`, `for-funeral-directors.html` and `for-wedding-planners.html` say "Quartet". Prices quoted anywhere must match `pricing.html`, and so should the labels attached to them.
10. **Stale offer validity.** `priceValidUntil` is `2026-12-31` in 12 places — inside the December booking window this reads as expired pricing to a crawler evaluating offers made in September for December events.

## Goals

1. Win hirers of carol services *and* carol singers: offices, hotels, luxury apartment buildings, livery companies, charities running fundraising carol concerts, and organisations holding carol services in churches they have booked themselves.
2. Own two distinct head-term families without cannibalising: *carol service* (`christmas.html`) and *hire carol singers* (`carol-singers.html`).
3. Rank for "Nine Lessons and Carols" with a genuinely useful planning guide, not a thin doorway.
4. Make every area page seasonally relevant without creating a single new geo page.
5. State the real commercial differentiator plainly: standard prices apply at Christmas — no seasonal uplift — against an agency market that charges more in December.
6. Ship the whole expansion with exactly one partial-touching build so the ~106-file diff appears once and is reviewable.
7. Every price, dress option, repertoire claim and duration statement on every new page traces to a verified fact in §2 or to `pricing.html`. No invented figures.

## Non-goals

- No new geo/doorway pages. The 52 existing area pages get sections, not siblings.
- No dedicated "carol singers in London" page — `carol-singers.html` carries a London-weighted body paragraph instead.
- No livery-company *guide*; the B2B page owns that low-volume intent on its own.
- No new CSS components. Everything reuses existing classes, so no `css/` change and no second build phase.
- No carol audio. The site has three hymn recordings and no carol recordings; copy must never imply otherwise. Recording carols is a human task.
- No `AggregateRating` / `Review` / star-rating schema anywhere (house rule, Google policy).
- No new `?from=` conversion parameter. Nothing in `thank-you.html` maps one, and inventing one silently drops the conversion.
- No seasonal price uplift, no duo or trio tiers.

---

## Design

### 1. Keyword/intent split (anti-cannibalisation contract — load-bearing)

No page may target another row's head term in its `<title>` or H1. This table is the contract; every content agent receives its own row.

| Page | Title (≤60c) | H1 | Owns |
|---|---|---|---|
| christmas.html | `Christmas Carol Services for Companies & Venues \| LCS` | Christmas carol services | carol service, corporate/office carol service, carol service in a church |
| **carol-singers.html** (new) | `Hire Carol Singers \| Professional Carol Singers for Events` | Hire carol singers | hire carol singers, carol singers for hire, carol singers London (London-weighted body — substitutes for a dedicated London page) |
| music-guides/nine-lessons-and-carols.html | `Nine Lessons and Carols: Order of Service & Planning` | Nine Lessons and Carols: how to plan the service | nine lessons and carols, order of service, readings |
| music-guides/carol-singers-cost.html | `How Much Does It Cost to Hire Carol Singers? (2026)` | How much does it cost to hire carol singers? | carol singers cost/prices |
| music-guides/charity-carol-concert.html | `Planning a Charity Carol Concert \| A Practical Guide` | Planning a charity carol concert | charity carol concert/service |
| music-guides/hotel-christmas-entertainment.html | `Christmas Entertainment for Hotels & Venues` | Christmas entertainment for hotels | hotel christmas entertainment |
| music-guides/residents-christmas-carol-event.html | `Hosting a Residents' Christmas Carol Event` | Hosting a residents' carol event | residents' event, carol singers apartment building/BTR |
| music-guides/when-to-book-christmas-entertainment.html | `When to Book Christmas Entertainment (and Why It's Now)` | When to book Christmas entertainment | booking-timing/urgency queries |
| for-hotels.html | `Carol Singers & Christmas Music for Hotels \| LCS` | For hotels & venues | B2B hotel/venue events & F&B managers |
| for-property-managers.html | `Residents' Carol Events for Property Managers \| LCS` | For property managers | B2B BTR/estate/block managers |
| for-livery-companies.html | `Choirs for Livery Company Carol Services \| LCS` | For livery companies | B2B clerks/beadles; livery hall services, grace-singing |
| for-charities.html | `Choirs for Charity Carol Concerts \| LCS` | For charities | B2B charity events/fundraising teams |

Plus guide #7: `booking-carol-singers-agency-vs-direct.html` → `Booking Carol Singers: Agency vs Direct (What to Know)` — owns agency-comparison queries.

Supporting rules:

- **"Carol Singers" leaves `christmas.html`'s title.** The current title contains both head terms; keeping them there would guarantee cannibalisation of the new page.
- **Two-way disambiguation.** `christmas.html` and `carol-singers.html` each carry one sentence near the top pointing at the other, with a descriptive anchor matching the target's head term — "Want singers moving through a party rather than a structured service? …" and the inverse. Never a bare "click here" or a repeated anchor.
- **Variant spellings.** Work "carollers" and "carolers" naturally into body copy on `carol-singers.html` only.
- **Brand disambiguation.** Competitor londoncarolsingers.com also brands itself "LCS". Christmas pages use the full "London Choral Service" name in body copy; the `| LCS` title suffix stays for consistency with the existing title pattern.
- **FAQ uniqueness is part of the contract.** Every FAQ question text must be unique site-wide; the duplicate check is a grep before each commit, not a judgement call.

### 2. Pricing policy & verified facts

Everything in this section came from the business owner and is final. It is the only permitted source for pricing, dress, repertoire, accompaniment and duration claims on Christmas pages. Anything not here does not go on the site.

**Pricing**

- Standard prices apply to Christmas bookings. **No seasonal uplift. No duo or trio tiers.** This is a genuine differentiator against the agency market and should be stated plainly rather than hinted at.
- The ladder, which must match `pricing.html` exactly: Soloist £215 · Small Choir (4) £1,150 · Quintet £1,400 · Sextet £1,600 · Full Choir (8) £2,000 · Chorus (12) £3,000 · organist/pianist from £215.
- Prices are inclusive of all taxes, fees, and travel within Greater London (this mirrors `pricing.html`'s existing FAQ wording — reuse it, don't reinvent it).
- **A premium applies only to Christmas Eve and Christmas Day bookings** — typically around 25%, confirmed in the written quote. The choir *is* available on 24 and 25 December; "carols by candlelight on Christmas Eve" is real search intent and the availability is FAQ-worthy.
- **Standard Christmas booking length: up to 1.5 hours including breaks, or the length of a church service.** Longer bookings attract a premium fee, quoted upfront. No figure is published.
- **Keyboard surcharge:** if a venue has no piano and LCS must bring a keyboard and speaker, an extra charge applies, quoted upfront in the written quote. No figure is published — consistent with the existing no-hidden-fees FAQ.
- Verify every figure against `pricing.html` immediately before writing it anywhere.

**Performance facts**

- The choir can roam throughout an event — lobbies, receptions, among guests, light switch-ons — or perform stationary sets.
- Dress: concert dress, all black, casual, or Christmas jumpers. Santa hats available.
- **No Victorian costumes.** Not offered, never claimed. A grep for "Victorian" is part of verification.

**Repertoire & accompaniment**

- Huge range: all the traditional carols, plus a cappella arrangements of popular Christmas songs.
- Fully a cappella performance available — no instrument, no amplification needed.
- Organist can be provided (church services). Pianist can be provided to support singing.
- A **"choir + background piano between sets"** package is available.

**Label fix carried by this work:** standardise on **"Small Choir (4)"** wherever the four-singer price tier is named on the pages this feature touches.

### 3. New-page inventory and exemplars

Twelve net-new pages. Every one is built by cloning an exemplar, never from scratch (`new-page` skill).

| New page | Exemplar to clone | Sitemap priority | Section set |
|---|---|---|---|
| `carol-singers.html` | post-Task-1 `christmas.html` | 0.8 | hero + byline · how it works · **where carol singers work** · hear our musicians · price cards · guide links · FAQ (~6) · contact form |
| `for-hotels.html` | `for-event-managers.html` | 0.7 | hero + byline · how we work with X · what your guests receive · booking & invoicing · useful resources · FAQ (4–5) · Related · form |
| `for-property-managers.html` | `for-event-managers.html` | 0.7 | as above |
| `for-livery-companies.html` | `for-event-managers.html` | 0.7 | as above |
| `for-charities.html` | `for-event-managers.html` | 0.7 | as above |
| 7 × `music-guides/*.html` | `music-guides/best-christmas-carol-singers.html` | 0.6 | byline · 3-level breadcrumb · long-form body · FAQ (3–4) · related-guides block · service CTA |

**B2B page angles and FAQ themes**

| File | Audience/angle | FAQ themes (4–5) |
|---|---|---|
| `for-hotels.html` | Hotel/venue events & F&B managers: lobby carols, festive afternoon teas, switch-ons, party-season programmes, December residencies | multiple sets per evening (or choir + background piano between sets); working-lobby logistics, no amplification needed; residency vs one-off; insurance/compliance; party-season booking window |
| `for-property-managers.html` | Luxury apartment/BTR/estate managers: residents' carol evenings, lobby performances | lobby/courtyard formats; singalong vs performance; invoicing to a managing agent (reuse the verified invoicing facts from `for-event-managers.html` only); duration; lead time |
| `for-livery-companies.html` | Clerks & beadles: carol services in livery halls and City churches, Nine Lessons, grace-singing at Christmas court dinners and banquets | Nine Lessons with organist in a City church; singing grace; hall staff/beadle coordination; repertoire formality; annual rebooking |
| `for-charities.html` | Charity events & fundraising teams running ticketed carol concerts in churches | leading congregational carols vs performance sets; supporting celebrity/VIP readers and a running order with appeal moments; hired-church logistics (rehearsal, organist); cost drivers; December church lead times |

**Guide briefs**

1. `nine-lessons-and-carols.html` — history (King's, 1918), the nine readings, carol placement, congregational vs choir-only, corporate/charity/livery adaptations, hiring choir + organist into a church the client has booked. Links `christmas.html`, `for-livery-companies.html`, `for-charities.html`.
2. `carol-singers-cost.html` — cost breakdown **strictly from `pricing.html`**: standard figures, no Christmas uplift stated as the selling point, Christmas Eve/Day premium noted, keyboard surcharge "quoted upfront", all-inclusive within Greater London, standard Christmas booking up to 1.5 hours including breaks or the length of a church service. What moves the price: ensemble size, duration beyond the standard booking, travel outside Greater London, 24–25 December dates. Mirrors the structure of `funeral-music-costs.html`. Links `carol-singers.html` + `pricing.html`.
3. `charity-carol-concert.html` — church venue hire, ticketing, readers, running order with appeal moments, rehearsals, lead times. Links `for-charities.html` + the Nine Lessons guide.
4. `hotel-christmas-entertainment.html` — formats by space, residencies, guest experience. Links `for-hotels.html` + `carol-singers.html`.
5. `residents-christmas-carol-event.html` — BTR/estate formats, song sheets, the shape of a mulled-wine evening. Links `for-property-managers.html` + `carol-singers.html`.
6. `when-to-book-christmas-entertainment.html` — urgency guide using only verifiable date facts: December closes out by mid-September (already claimed in site copy), 24/25 December bookable with a premium. Links `christmas.html` + `carol-singers.html`.
7. `booking-carol-singers-agency-vs-direct.html` — targets "carol singers agency" and "christmas choir agency", the queries the directories dominate. Factual and non-disparaging: what agencies do, what booking a professional choir direct means (one artistic director, consistent line-up, no commission layer), questions worth asking either way. Links `carol-singers.html` + `best-christmas-carol-singers.html`.

**Forms on all five new root-level pages:** subject line naming the page's intent (e.g. `Carol singers enquiry — London Choral Service`), occasion preselect `christmas`, and `data-redirect="thank-you.html?from=christmas"`. The `christmas` parameter is **reused deliberately**: `thank-you.html` maps `christmas → ads_conversion_Christmas_1`, and no other seasonal event exists. Web3Forms endpoint, hCaptcha guard and `botcheck` honeypot are cloned unchanged.

### 4. Geo insertion pattern (52 pages)

All 19 `areas/*.html` city pages (excluding `areas/index.html`) and all 33 `areas/london/*.html` borough pages. The pattern is defined once here, inserted mechanically, and the copy inside it is hand-varied per page.

1. **New section**, `<section class="section"><div class="prose">`, placed after the FAQ section and before the neighbour-links block:
   - `<h2>Christmas carol singers in {Place}</h2>`
   - 2–3 sentences localised by reusing a venue, church, or landmark **already named on that page**. No invented local facts.
   - Links to `christmas.html` and `carol-singers.html` with rotated anchor text.
2. **One Q&A appended to the visible FAQ and to the `FAQPage` `mainEntity` array**: "Do you provide carol singers in {Place} in December?" with a localised answer that mentions December booking pressure and links `christmas.html`. Verify the FAQ markup shape on the exemplars first — `areas/manchester.html` for cities, `areas/london/camden.html` for boroughs — because the visible FAQ and the schema array are separate structures that must stay in sync.
3. **Append `"Christmas Carol Singing"`** to the existing `Service.serviceType` array.
4. **`sitemap.xml` `lastmod` → today** for all 52.

Anti-thinness rules: no sentence may appear verbatim on two pages; the anchor text rotates across "Christmas carol singers", "hire carol singers", "carol services", "book carol singers for December"; the localising detail must already exist on the page. Every page passes the `writing-site-copy` gate.

### 5. JSON-LD graphs per page type

| Page type | `@graph` nodes | Notes |
|---|---|---|
| `christmas.html` | `Service` (broadened description) + `AggregateOffer` 1150–3000 + `OfferCatalog` + `BreadcrumbList` + `FAQPage` (~7 Q) + `LocalBusiness` stubs | `priceValidUntil` → `2027-12-31`; `dateModified` → today; `FAQPage` is new |
| `carol-singers.html` | `Service` ("Carol Singers for Hire", `AggregateOffer` 1150–3000, `priceValidUntil` 2027-12-31) + `OfferCatalog` + `BreadcrumbList` + `FAQPage` (~6 Q) + `LocalBusiness` stub | `OfferCatalog` mirrors the `services.html` pattern, enumerating ensembles at `pricing.html` figures |
| 4 × B2B pages | `ProfessionalService` (`priceRange` "£215–£3,000", `audience: BusinessAudience`) + `BreadcrumbList` + `FAQPage` + `LocalBusiness` stub | `priceRange` must stay consistent with `pricing.html` |
| 7 × guides | `Article` + `WebPage` (with `speakable`) + `FAQPage` + `BreadcrumbList` + `LocalBusiness` — the exact graph on `best-christmas-carol-singers.html` | `og:type` `article`; 3-level breadcrumb; `datePublished`/`dateModified` today |
| 52 × area pages | existing graph, with one `Question` appended to `FAQPage.mainEntity` and `"Christmas Carol Singing"` appended to `Service.serviceType` | no new nodes |
| `pricing.html` | existing `FAQPage` node gains 1–2 Christmas questions | the node is near line 2021 |

Global JSON-LD rules for this feature: no `AggregateRating` or `Review` nodes are introduced anywhere; visible FAQ text and schema answer text are identical strings; every touched node gets a fresh `dateModified`; every `priceValidUntil` this work touches moves to `2027-12-31`; `python3 validate_jsonld.py` must exit 0 after every phase.

### 6. Nav and footer changes

One partial-touching phase only, so the ~106-file rebuild diff appears exactly once.

**`partials/nav.html`**
- Add a **top-level "Christmas"** link, placed before "Pricing". Seasonal promotion — it comes back out in January (logged as a follow-up in `docs/ROADMAP.md`).
- Add **"Carol Singers"** to the Services dropdown. Keep "Christmas" in the dropdown as well, so the dropdown remains complete when the top-level link is later removed.

**`partials/footer.html`**
- Strapline gains Christmas and corporate: "…for funerals, weddings, memorials, Christmas, and corporate events across the United Kingdom".
- Add `christmas.html` and `carol-singers.html` links near the areas row.

Nothing else in the partials changes, so the expected diff is: two partial files, plus the corresponding `@include-start`/`@include-end` blocks in every HTML file, and **no change inside any inlined `<style>` block**. A style-block diff means something went wrong — stop and investigate.

### 7. Internal-link graph

The new pages must be reachable from hubs and must pass weight to each other rather than dead-ending.

```
                      nav (top-level) ─┐   footer ─┐
                                       ▼           ▼
index.html ──► christmas.html ◄────────────────► carol-singers.html
   │                 │  ▲                              │  ▲
   │                 │  └──── services.html (occasion card) ─┘
   │                 ▼
   │        for-hotels · for-property-managers · for-livery-companies · for-charities
   │                 │            (each ──► christmas.html + carol-singers.html + its guide)
   ▼                 ▼
corporate.html   music-guides/index.html ──► 6 existing + 7 new Christmas guides
                        │                          │
pricing.html ◄──────────┴──── carol-singers-cost ──┘
```

Concrete requirements:
- `christmas.html` and `carol-singers.html` link to each other with the disambiguating sentences from §1.
- Each B2B page links to `christmas.html`, `carol-singers.html`, and its own paired guide; each paired guide links back to its B2B page.
- Each new guide appears in `music-guides/index.html` **twice** — as a visible card in the Christmas section and as an `ItemList` entry — and in the split guide-links block on `christmas.html` and `carol-singers.html`.
- Each of the six existing Christmas guides gains 1–2 related-guides pointers into the new set.
- `music-guides/best-christmas-carol-singers.html` is added to the visible Christmas section of `music-guides/index.html`, repairing the existing listing bug (Problem 4).
- `index.html` gets a proper Christmas occasion block/CTA replacing the single inline link; `corporate.html` gets a short Christmas cross-sell section; `services.html`'s occasion list gains a carol-singers entry.
- The guide-links block on `christmas.html` splits into "Planning a carol service" and "Hiring singers" sub-lists — thirteen flat links is not scannable.

### 8. SEO upgrades applied across the feature

- **PAA-shaped FAQs.** Phrase every FAQ question as a real People-Also-Ask query — "How much does it cost to hire carol singers?", "How long do carol singers perform for?", "Can carol singers perform outside?" — with a concise 40–60-word lead answer. This targets FAQ rich results and AI Overviews/answer engines simultaneously, which matters because the site already invites GPTBot and ClaudeBot.
- **`OfferCatalog`** on `christmas.html` and `carol-singers.html`, mirroring `services.html`, enumerating the ensemble options at `pricing.html` figures.
- **Freshness signals.** "(2026)" in the cost guide's title; "Last updated: July 2026" bylines on everything touched; fresh `sitemap.xml` `lastmod`; `dateModified` bumps in every touched JSON-LD node; `priceValidUntil` → `2027-12-31`.
- **Anchor-text variation.** Rotate anchors across the 52-page geo sweep and all hub links. No single anchor string repeated site-wide.
- **Alt text.** Any image on a touched page gets descriptive alt text, including natural Christmas phrasing where that is truthful for the image.
- **Meta descriptions.** Unique, 141–161 characters, mirrored to `og:description` and `twitter:description`. Canonical + hreflang (en-gb, x-default) + full OG/Twitter set on every new page.
- **Post-merge manual actions** (human only, recorded in `MANUAL-ACTIONS-REQUIRED.md`): resubmit the sitemap in GSC; request indexing for the 12 new URLs; watch GSC queries for cannibalisation between the two head-term families; brand watch on the "LCS" clash.

---

## Implementation order

Seven phases, each ending in a build, a verification pass, and one commit. Every phase leaves a working, deployable site.

1. **Fix and broaden `christmas.html`** — retitle per §1, rewrite the meta description, widen the lede beyond corporate, add the "Carol services in churches" block and the accompaniment-options paragraph, relabel "Quartet" → "Small Choir (4)", add the all-inclusive/no-uplift pricing line, add the missing sixth guide link and split the guide block, add the FAQ section + `FAQPage` node, broaden the `Service` description, bump `priceValidUntil` and `dateModified`, add the page to `llms.txt`, repair the `music-guides/index.html` card.
2. **`carol-singers.html`** — clone the fixed `christmas.html`; §3 section set; §5 graph; wiring into sitemap, `llms.txt`, `services.html`, and the two-way disambiguated cross-links.
3. **Four B2B landing pages** — clone `for-event-managers.html`; §3 angles and FAQ themes; §5 graph; sitemap and `llms.txt` entries.
4. **Seven music guides** — clone `best-christmas-carol-singers.html`; §3 briefs; index cards *and* `ItemList`; related-guides pointers on the six existing Christmas guides; bump the "36 music guides" count line in `llms.txt` to 43.
5. **Geo sweep** — the §4 pattern across all 52 area pages.
6. **Site-wide body edits, then partials + the single build** — `index.html`, `corporate.html`, `pricing.html` Christmas section, the two label-drift relabels; then `partials/nav.html` and `partials/footer.html` and `./build.sh`. Splitting these into two commits keeps the ~106-file rebuild diff isolated and reviewable.
7. **Docs, tracking, manual actions** — `docs/ROADMAP.md` (January nav demotion, annual `priceValidUntil` bump), `MANUAL-ACTIONS-REQUIRED.md` (a "Christmas season (before September)" block).

Phases 2–4 parallelise across agents; phases 1, 5, 6 and 7 are serial. Shared files — `sitemap.xml`, `llms.txt`, `music-guides/index.html`, `partials/*`, existing guides' related-guides blocks — are edited by one owner only, never by a content agent working in parallel with another.

## Open questions / risks

- **Meta-description audit finding did not reproduce.** The original audit recorded `christmas.html`'s meta description as 187 characters; measured today it is 160 — inside the 141–161 house range. The rewrite still happens, because the page's positioning and title change and the description must follow, but do not treat "fix the over-length description" as the reason. Re-measure after rewriting rather than trusting either number.
- **The `Quartet` verification grep is broader than the label-fix scope.** The planned check is `grep -rn 'Quartet' --include='*.html' .` → empty, but "Quartet" currently appears in 11 files, and the May 2026 services redesign deliberately renamed "Small Choir" *to* "Quartet" on `services.html` to match what it then believed `pricing.html` said. `pricing.html` today says "a small choir of four singers". Decide before Phase 6: either narrow the grep to the pages this feature touches (`christmas.html`, `for-funeral-directors.html`, `for-wedding-planners.html`), or take the site-wide rename as explicit extra scope and revisit the earlier decision. Do not let a failing grep drive an unplanned 11-file rename mid-phase.
- **`christmas.html` is not the only FAQ-less service page.** `weddings.html` and `funerals.html` also lack a visible FAQ and a `FAQPage` node. That is out of scope here, but it is worth logging in `docs/ROADMAP.md` while the observation is fresh.
- **Cannibalisation between the two head-term families** is the central risk. Mitigations: the exclusive-title contract in §1, removing "Carol Singers" from `christmas.html`'s title, the disambiguation sentences, and fully disjoint FAQ sets. It is still a post-launch GSC watch item, not something the markup can guarantee.
- **Doorway thinness on 52 area pages.** Mitigated by adding no new pages, reusing landmarks already named on each page, and varying phrasing. The failure mode is an agent falling back on a template sentence across a batch — the copy review pass exists to catch exactly that.
- **FAQ schema duplication.** With ~7 + ~6 + ~20 + ~25 + 52 new questions, collisions are likely by accident. The duplicate check (extract all `FAQPage` `name` strings, `sort | uniq -d` → empty) runs before every commit, not just at the end.
- **Price accuracy.** No uplifted figure may appear anywhere. The Christmas Eve/Day premium ("typically around 25%") is user-stated and may be quoted in FAQ copy; the keyboard surcharge and the over-length-booking premium have no published figure and must always be described as "quoted upfront".
- **Conversion pooling.** All Christmas sources share `?from=christmas` → `ads_conversion_Christmas_1`. Per-source Ads events (e.g. `ads_conversion_CarolSingers_1`) require a dashboard action first; the `thank-you.html` map is only extended once those events exist.
- **No carol audio and no Christmas OG image.** Copy must never claim carol recordings — the three tracks on the site are hymns. Both are flagged as manual actions.
- **Diff discipline.** Exactly one partial-touching commit. Any other phase producing a ~106-file diff means a stray `./build.sh` ran at the wrong time.

---

## Appendix: file inventory

**New files (12)**

Root service page (1):
- `carol-singers.html`

Root B2B landing pages (4):
- `for-hotels.html`
- `for-property-managers.html`
- `for-livery-companies.html`
- `for-charities.html`

Music guides (7):
- `music-guides/nine-lessons-and-carols.html`
- `music-guides/carol-singers-cost.html`
- `music-guides/charity-carol-concert.html`
- `music-guides/hotel-christmas-entertainment.html`
- `music-guides/residents-christmas-carol-event.html`
- `music-guides/when-to-book-christmas-entertainment.html`
- `music-guides/booking-carol-singers-agency-vs-direct.html`

**Existing Christmas guides (6) — all gain related-guides pointers**
- `music-guides/best-christmas-carol-singers.html` ⭐ exemplar for the seven new guides; also the page missing from the visible index
- `music-guides/christmas-carols-guide.html`
- `music-guides/christmas-choir-hire.html`
- `music-guides/company-christmas-party-entertainment.html`
- `music-guides/corporate-carol-service.html`
- `music-guides/office-carol-service-planning.html`

**Edited existing pages**
- `christmas.html` — hub fix; exemplar for `carol-singers.html`
- `pricing.html` — new "Christmas & carol singers" section; source of truth for every figure
- `index.html` — Christmas occasion block/CTA
- `corporate.html` — Christmas cross-sell section
- `services.html` — carol-singers occasion entry
- `for-funeral-directors.html`, `for-wedding-planners.html` — "Quartet" → "Small Choir (4)"
- `music-guides/index.html` — visible cards + `ItemList` for 7 new guides + the missing existing card
- `partials/nav.html`, `partials/footer.html` — the single build phase
- `sitemap.xml`, `llms.txt` — touched in every phase
- `docs/ROADMAP.md`, `MANUAL-ACTIONS-REQUIRED.md`

**Area pages (52) — all receive the §4 pattern**

Cities (19): bath · birmingham · brighton · cambridge · canterbury · chelmsford · chester · guildford · liverpool · london · manchester · oxford · reading · rochester · salisbury · slough-maidenhead · st-albans · winchester · windsor
*(`areas/index.html` is excluded — it is a directory page, not a place page.)*

London boroughs (33): all files in `areas/london/`.

Pattern exemplars: `areas/manchester.html` (city shape), `areas/london/camden.html` (borough shape).

**Reference only — not edited**
- `thank-you.html` — confirms `christmas → ads_conversion_Christmas_1`
- `data/seo-fix-discovered-urls.yml` — the only source for GBP URL and video dates
- `for-event-managers.html` — exemplar for the four B2B pages

**Counts to expect after the work**
| Metric | Before | After |
|---|---|---|
| `<loc>` entries in `sitemap.xml` | 103 | 115 |
| Guide files (excluding index) | 36 | 43 |
| `llms.txt` guide-count line | "36 music guides" | "43 music guides" |
| `priceValidUntil": "2026-12-31"` occurrences | 12 | 0 |
| Pages with a Christmas section in `areas/` | 0 | 52 |
