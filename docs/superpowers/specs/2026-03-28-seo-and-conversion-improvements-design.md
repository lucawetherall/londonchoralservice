# SEO & Lead Conversion Improvements — Design Spec

## Problem

London Choral Service is being outranked by The London Funeral Singers. The competitor uses aggressive schema markup (AggregateRating, FAQPage on every page), dense trust signals (BBC, Classic FM, Royal Albert Hall), and 22 articles targeting exact search queries. Traffic that does arrive converts at a lower rate than it should because the path from reading content to making an enquiry has too much friction.

## Competitor Analysis Summary

**Their strengths:**
- Sitewide AggregateRating schema (5.0 / 45 reviews) generating rich snippets
- FAQPage schema on multiple pages triggering FAQ dropdowns in SERPs
- Trust signal density: media logos, venue logos, named founders, third-party review badges
- 22 articles targeting exact funeral music search queries
- Phone number and "Book now" CTA on every page

**Their vulnerabilities:**
- 14 of 22 articles are under 600 words — bare song title lists with no context
- No Article/BlogPosting schema on content pages
- Only 8 county location pages (we have 47 area pages)
- No embedded audio or video in articles
- Boilerplate location pages with ~60% shared content
- No individual hymn/song pages
- No advice content beyond music selection

## Solution: Three Workstreams

### Workstream 1: Schema & Technical SEO Upgrades

Quick wins that change SERP appearance and improve crawlability.

#### 1.1 AggregateRating Schema

Add AggregateRating to the existing LocalBusiness JSON-LD, present on every page. Must reference real, verifiable reviews (Google Business or collected testimonials). The competitor displays "5.0 / 45 reviews" sitewide — matching or exceeding this unlocks star ratings in search results.

**Implementation:** Add `aggregateRating` property to the existing `@graph` LocalBusiness node in each HTML file's JSON-LD block.

#### 1.2 FAQPage Schema

Add FAQPage structured data to pages with natural question-and-answer content:

- **Pricing page** — questions about costs, inclusions, VAT, travel, customisation
- **Service pages** — how booking works, what to expect, timelines
- **Music guides** — questions about hymn choices, ceremony placement, suitability

Each page gets 3-8 FAQ pairs embedded in the JSON-LD. Questions must appear visibly on the page (Google requires FAQ content to be user-visible).

**Implementation:** Add `FAQPage` type to the `@graph` array in each qualifying page's JSON-LD. Add corresponding visible FAQ sections to the page HTML.

#### 1.3 Article Schema on Music Guides

Add Article (or BlogPosting) structured data to all 30 music guide pages. The competitor lacks this entirely.

Each guide's JSON-LD gets:
- `@type: Article`
- `headline` — the guide title
- `author` — linked to the Organization or a named person
- `datePublished` and `dateModified`
- `publisher` — linked to the Organization node
- `description` — concise summary for SERP display
- `image` — if a relevant image exists

**Implementation:** Add Article node to each music guide's `@graph` array.

#### 1.4 BreadcrumbList Schema

Add BreadcrumbList structured data to all pages. Gives Google hierarchy signals and can replace raw URLs in SERPs with readable breadcrumb trails.

Breadcrumb structure:
- Home > Areas > [Area Name]
- Home > Music Guides > [Guide Name]
- Home > Services
- Home > Pricing

**Implementation:** Add `BreadcrumbList` node to each page's `@graph` array. No visible breadcrumb UI is required (schema-only is valid), but visible breadcrumbs can be added later if desired.

#### 1.5 Internal Linking Improvements

Strengthen the link graph between related pages with contextual (in-content) links:

- Music guides link to relevant area pages ("Planning a funeral in Lambeth? See our Lambeth page")
- Area pages link to relevant music guides ("Choosing hymns? See our guide to funeral hymns")
- Service pages cross-link to related guides
- Area pages link to geographically adjacent area pages
- Every page has at least 2-3 contextual internal links beyond navigation

**Implementation:** Add contextual link sections or inline links to HTML content. Prioritise pages in Tier 1 and Tier 2 (see Workstream 2).

### Workstream 2: High-Impact Content Enrichment

Outrank the competitor by creating genuinely deeper content. Prioritised in three tiers by competitive impact.

**Content principles (all pages):**
- No filler phrases, no AI voice, no throat-clearing openers
- Active voice throughout — every sentence has a human subject doing something
- Specific details over vague claims — name the venue, state the number, describe the moment
- The reader is someone planning a funeral or wedding. Write for them, not for search engines
- Vary sentence length. Two items beat three. No em dashes.

#### Tier 1: Music Guides (highest priority)

These directly compete with the competitor's top-ranking articles. Their weakness: most articles are bare lists. Our opportunity: make every guide substantive.

For each music guide, enrich with:
- Historical and cultural context for each piece mentioned
- Ceremony placement guidance — when in the service this piece works best and why
- Audio or video embeds from the Listen page or YouTube where available
- Cross-links to related guides and service pages
- FAQ section at the bottom (feeds FAQPage schema)

**Target word count:** 1,500-3,000 words per guide depending on topic depth. No padding — every paragraph earns its place.

**Priority guides (compete directly with their top articles):**
- Funeral hymns guide
- Popular funeral songs guide
- Wedding music guide
- Any guides covering Irish, Welsh, Scottish, or Catholic music
- Celebration of life music guide

#### Tier 2: Core Pages

These are the money pages — where ready buyers decide whether to get in touch.

**Services page:**
- Expand each service type with specifics: what's included, what to expect, how the process works from first contact to the day
- Add social proof inline (testimonial snippets relevant to each service type)
- FAQ section covering common service questions

**Pricing page:**
- Add inline FAQ content: what's included at each tier, travel policy, VAT, customisation options
- Clarify the value at each price point — what the client gets, not just a number
- Testimonial snippet near pricing to reduce price anxiety

**About page:**
- Strengthen trust signals: Oxford credentials, performance history, number of services performed, notable venues
- Named team members where appropriate
- The competitor plasters BBC and Royal Albert Hall logos — equivalent social proof needed here

**Homepage:**
- Tighten the value proposition — lead with differentiation, not description
- Surface trust signals above the fold (review rating, years of experience, notable venues)
- Stronger primary CTA

#### Tier 3: High-Value Area Pages

Our 47 area pages are a structural advantage over their 8. But templated, thin pages get treated as low-value by Google.

Priority area pages (likely highest search volume) get:
- Unique venue information: churches, crematoriums, ceremony venues specific to that area
- Area-specific testimonials if available
- Local logistics context (parking, transport, access)
- Genuinely distinct content — not find-and-replace template copy
- Cross-links to relevant music guides and adjacent area pages

**Which area pages first:** Focus on Central London boroughs (Westminster, Kensington & Chelsea, Camden, Southwark, Lambeth) and any areas where search console data shows impressions but low clicks.

### Workstream 3: Conversion Path Improvements

Turn more existing visitors into enquiries. No new mechanisms — smoother journey from reading to contact.

#### 3.1 Contextual CTAs on Music Guides

Each music guide gets two contextual CTAs:
- **Mid-content CTA** — placed after the reader has received substantial value. Connects the guide topic to the service: "Not sure which hymns suit your service? We can help you choose." Links to contact page or shows phone number.
- **End-of-content CTA** — at the bottom of the guide, before any footer content.

No popups. No additional sticky bars beyond the existing mobile CTA. The CTAs are inline text with a link, not banner ads.

#### 3.2 Trust Signals Distributed Throughout Site

Move trust signals out of the about page and distribute them where they influence decisions:

- **Testimonial snippets** on service pages, pricing page, and high-traffic music guides. One or two short quotes per page, not a reviews wall.
- **Credentials and experience numbers** — years of experience, number of services performed, Oxford background. Specific figures on relevant pages.
- **Notable venue references** — if you've performed at recognisable venues, name them on service pages and area pages where geographically relevant.

#### 3.3 Contact Page Refinements

The form works. Small improvements to reduce friction:
- Add a reassurance line near the form — expected response time, who will reply
- Consider making the occasion dropdown more granular (e.g. "church funeral" vs "crematorium service") — signals expertise and helps triage
- Thank-you page confirms what happens next (when they'll hear back, from whom)

#### 3.4 Phone Number Visibility

Phone number appears in:
- **Footer** on every page (already present)
- **Within content** on high-intent pages: services, pricing, area pages
- **NOT in the header** — per requirement

The competitor puts their number in the header on every page. We achieve similar visibility through footer and in-content placement without cluttering the header.

## Constraints

- **No email capture or newsletter.** Keep conversion simple — contact form, phone, email.
- **No phone number in header.** Footer and in-content placement only.
- **Static HTML site.** All changes are to hand-crafted HTML files with inlined CSS. No templating engine, no build framework beyond the CSS concatenation script.
- **Stop-slop writing principles.** All new or revised copy follows stop-slop rules: no filler, active voice, specific details, varied rhythm, trust the reader.
- **98 existing pages.** Changes are prioritised by impact, not applied uniformly. Tier 1 pages first, then Tier 2, then Tier 3.

## Success Criteria

- Rich snippets (star ratings, FAQ dropdowns) appearing in Google search results within 4-8 weeks of schema deployment
- Improved rankings for primary keywords (funeral hymns, funeral singers London, wedding choir London) — measurable via Search Console
- Increased click-through rate from SERPs (richer snippets + better meta descriptions)
- Higher contact form submission rate from music guide visitors (measurable via GA4 thank-you page tracking with referrer data)
- Closing the ranking gap with The London Funeral Singers on overlapping keyword terms

## Out of Scope

- New page types (no individual hymn pages, no blog, no reviews page in this phase)
- Email marketing or newsletter infrastructure
- Paid advertising
- Social media integration
- Site redesign or CSS framework changes
- New JavaScript functionality beyond what exists
