# Christmas landing pages: carolling first, church services apart

**Date:** 2026-10-19
**Status:** Approved for implementation. Owner, live in chat on 19 Oct 2026: improve christmas.html as a landing page "to convert to more sales", provide a landing page for church services and one for general carolling, with general carolling (outdoor events, corporate entertainment) "definitely the main focus as this is where most of the enquiries come from", using It's the Most Wonderful Time and Ding Dong as the main films. On the open question about carol-singers.html: "do whatever you think is best". The calls marked *(our call)* are ours, not his.

## Why

Most Christmas enquiries are for carolling at events: office parties, receptions, lobbies, markets, switch-ons and outdoor events. The site splits that buyer across two pages and buries the offer.

What the audit found (19 Oct 2026, origin/main 3ec269c1):

- **The two pages cannibalise each other.**
  - Spec 2026-07-29 §1 split them on purpose. christmas.html takes structured carol services and concerts ("This page covers structured carol services and concerts", christmas.html:3127). carol-singers.html takes parties and lobbies.
  - In practice they share the James testimonial, the tracks, the prices, the form and several FAQ answers.
  - In Search Console (18 Jul to 16 Oct), Google showed christmas.html for "carol singers london", "carol singers for hire", "christmas carolers for hire" and "christmas choir hire": 59 impressions, against 31 for carol-singers.html. Neither page got a click.
- **Ads and internal links point at different pages.**
  - Every paid click (21 in the last 30 days, £69, 0 conversions) lands on carol-singers.html.
  - christmas.html gets two nav links and 83 in-body links, including the Enquire bar on 23 guides. carol-singers.html gets one nav link and 68 body links.
- **christmas.html is a weak landing page.**
  - Above the fold, a large video comes before any offer, and the only call to action is a text link.
  - The form sits about 11 sections down. Before it come nine videos and two hymns, 24 guide links and five for-* links, and nothing in between asks for the enquiry.
  - The strongest testimonial (Laura, Canary Wharf, 300 guests) sits *after* the form.
  - The church section speaks to a different buyer.
  - The occasion dropdown offers Funeral and Wedding, and "How did you hear" offers "A funeral director".
  - The "Text us on WhatsApp" line isn't a link.
  - Price, what's included and reply time aren't in the hero.
- **The leads can't be told apart.** Both forms redirect to `thank-you.html?from=christmas`. Only the email subject differs.

## Goals

1. **christmas.html becomes the one carolling landing page**: carol singers for office parties, receptions, hotel and residential lobbies, markets, switch-ons and outdoor events. It is the page Ads, the nav and the guides send that buyer to, and the page that should rank for "carol singers for hire / london".
2. **A new church carol services page, `christmas-carol-services.html`**, for a carol service in a church: Nine Lessons and Carols, an organist, working with the vicar and verger. Company and charity carol services held in a church count. It owns "christmas carol service(s)" searches.
3. **carol-singers.html is merged into christmas.html.** Its URL becomes a redirect stub, so ads, bookmarks and backlinks keep working, and the click ID survives *(our call; see below)*.
4. Each page leads with the offer. A visitor who reads only the first screen knows:
   - what they get
   - from what price
   - how fast we reply
   - how to enquire, by form or WhatsApp
5. Enquiries record which page they came from.

## Non-goals

- No price changes. Every figure comes from `pricing.html` and `christmas-pricing.html` as they stand.
- No changes to `christmas-pricing.html` beyond links, and no new pages beyond the church page.
- No Google Ads changes from this work. The ad's final URL change is a separate, owner-approved Ads change (see "Ads follow-up").
- No CSS framework, no new JS library, no A/B testing tool. If a new component is needed it goes in `css/components.css` or `css/pages.css` and is built with `./build.sh`.

## Anti-goals

- **Non-Christmas pieces are foregrounded on a Christmas or carol page** (owner, 19 Oct 2026). This covers hymns such as Be Thou My Vision, Guide Me O Thou Great Redeemer and All Things Bright and Beautiful. Only Christmas repertoire is shown, in films or track lists, on christmas.html and christmas-carol-services.html.

These would make the work a failure even if it shipped:

- **The click ID is lost.** A paid visitor who lands on `carol-singers.html?gclid=…` must arrive on christmas.html with the same query string, or the ad-visit tag and gclid capture break (spec 2026-10-14).
- **The pipeline breaks.** The enquiry assistant must still read form emails, including `occasion`, `ad_visit`, `ad_measurement`, `gclid`/`gbraid`/`wbraid`, `botcheck` and the hCaptcha guard. New fields are added; existing field names and values are not changed.
- **New claims are invented.** That means testimonials, venue or client names, booking counts, star ratings or `AggregateRating`. Reuse only the testimonials already on the site.
- **A rule is broken.** No roster size, no VAT wording, and no claim to supplement a London cathedral or Westminster Abbey choir.
- **Carol of the Bells is foregrounded on the church page.** Per the owner on 19 Oct 2026, it is not sung at church carol services.

## Page 1: christmas.html (carol singers for your event)

**Audience:** event managers, office managers, PAs, hotel and venue managers, property managers, market and switch-on organisers, people hosting a party. They are booking entertainment, not a liturgy.

**Head**
- **Title** *(our call; final wording passes writing-site-copy)*: "Hire Christmas Carol Singers in London & the UK | LCS".
- **Meta description:** 141–161 characters, naming carol singers, events, London/UK and "from £1,150".
- Keep the canonical self-referencing, hreflang, and full OG and Twitter tags. Regenerate the OG image from the new h1.
- **JSON-LD:**
  - Service + OfferCatalog with the existing figures, quintet included.
  - FAQPage with questions unique site-wide (spec 2026-07-29 §1 rule).
  - BreadcrumbList.
  - VideoObject for each film shown.

**Section order** (top to bottom). Copy comes from the existing two pages where it is good, rewritten to the house style.

1. **Hero.**
   - h1 along the lines of "Carol singers for your Christmas event". The sub names the occasions: office parties, receptions, lobbies, markets and switch-ons.
   - **Film:** It's the Most Wonderful Time of the Year (`csFWUu-r85Y`), with the existing caption.
   - Beside or under the h1, three facts:
     - "From £1,150 for four singers, all in"
     - "Four to twelve voices, roaming or in sets"
     - "We reply within one working day, usually the same day" (wording already used on the site)
   - **Buttons:** a primary button "Check your date" (or similar) to `#enquiry`, and a secondary "WhatsApp us" link using the site's existing WhatsApp handler and labelling, so the Ref/ad-visit lines still attach.
   - Keep the byline, but below the fold-critical content.
   - The disambiguation line ("Planning a carol service in a church? See church carol services") sits under the buttons in small text.
2. **Proof strip.** James (law firm partner, "highlight of our Christmas drinks") is the only event testimonial on the site, so he runs alone, with attribution unchanged. Add the sector line (law firms, banks, hotels, charities) and the conservatoire credential. Helen's and Laura's quotes are both about carol services, so they move to the church page *(our call)*. Never write a new quote to fill the space.
3. **What you get.** The existing "Included with every booking" ticks, rewritten for events:
   - singers in black, with the dress options from the FAQ
   - repertoire chosen with you
   - roaming or stationary sets
   - travel within Greater London included
   - one point of contact
   
   End with the price line.
4. **Hear them.** Two films only *(our call)*:
   - Ding Dong! Merrily on High (`zDlSFb74p4E`)
   - Winter Wonderland (`UaVhyyidlTs`)
   
   Each gets a one-line description. Then a link to listen.html for more. Most Wonderful Time is already the hero. Carol of the Bells and Blue Christmas stay on listen.html, and the hymns go.
5. **Where we sing.** Short cards or a list, condensed from carol-singers.html's "Where carol singers work": office party, drinks reception, hotel or residential lobby, market or light switch-on, outdoor event. Each item is a sentence or two and links to its guide or for-* page where one exists. This replaces both "Who we work with" blocks.
6. **Mid-page call to action.** One line and a button to `#enquiry`.
7. **Pricing.** Cards for 4 / 5 / 6 / 8 / 12 voices (the quintet at £1,400 is added). Then the existing notes: no Christmas uplift, the Christmas Eve/Day premium wording as on christmas-pricing.html, and keyboard if the venue has no piano. Link to christmas-pricing.html for worked examples.
8. **How it works.** Three steps (enquire → we confirm singers and repertoire → we turn up and sing), merged from both pages.
9. **FAQ.** Six to eight event questions, merged from both pages without duplicates:
   - dress
   - outdoors and weather
   - roaming
   - how many singers
   - last-minute bookings
   - Christmas Eve and Day
   - what the venue needs
   - booking and payment

   Move the church questions to page 2.
10. **Enquiry form** (`#enquiry`): see "Form" below. The WhatsApp/phone line under it becomes a real WhatsApp link.
11. **Further reading.** At most six guide links (e.g. carol-singers-cost, how-many-carol-singers, hotel-christmas-entertainment, outdoor-carol-singing, company-christmas-party-entertainment, when-to-book). This replaces the 24-link wall.

**Remove from christmas.html:**
- the church section (it moves to page 2)
- the hymn tracks
- the 24-link guide wall
- the duplicated "Who we work with"
- the second, third and fourth Christmas films

## Page 2: christmas-carol-services.html (church carol services)

**Audience:** someone organising a carol service in a church. That might be a company or charity booking a church, a parish without its own choir, or a school or livery company.

**Head**
- **Title** *(our call)*: "Choir for a Christmas Carol Service | London & UK | LCS".
- Unique meta description, canonical and hreflang, OG and Twitter tags, and an OG image.
- **JSON-LD:** Service + offers (choir sizes plus organist £250), FAQPage with unique questions, BreadcrumbList, VideoObject.
- Built from the `new-page` skill's service-page exemplar (clone christmas.html's head and structure). Wired into `llms.txt`; the sitemap is generated.

**Sections**
1. **Hero.**
   - h1 "Choir for your Christmas carol service".
   - **Film:** Once in Royal David's City (`SbvqWglsbMo`).
   - The same three facts, but an organist line replaces "roaming".
   - **Buttons:** "Check your date" and WhatsApp.
   - Disambiguation line pointing to christmas.html for parties and events.
2. **Proof.** Helen (annual City carol service) and Laura (Canary Wharf carol service for 300), both moved from christmas.html.
3. **What we do at a service.** From christmas.html's "Carol services in churches":
   - Nine Lessons and Carols order
   - congregational carols and choir pieces
   - organist (£250)
   - working with the vicar, verger and the church's own musicians
   - rehearsal on the day
   
   Link to nine-lessons-and-carols and christmas-carols-guide.
4. **Hear them.** Once in Royal David's City is the hero. Ding Dong! Merrily on High is the one other film (a carol that also belongs in church). **No Carol of the Bells and no hymns** (owner, 19 Oct 2026). If a Christmas recording with organ is made later, it goes here.
5. **Pricing.** Choir sizes as on page 1, plus the organist line and the Christmas Eve/Day note. Link to christmas-pricing.html.
6. **How it works**, **FAQ**, and the **form**.
   - **FAQ topics (church-specific):** order of service, the church's permission, our organist, rehearsal, and congregational singing.
   - **Copy limits (builder check):**
     - Say nothing about church hire fees, verger fees, or who pays the church's own organist. The site has no stated policy, and a guess would be a price claim. It stays an open question for the owner.
     - The organist answer may say only what the site already says: we can bring an organist who knows the instrument (£250), and we coordinate with the church's organist and verger.
7. **Further reading.** Carol-service guides: nine-lessons-and-carols, christmas-carols-guide, church-carol-service-choir-hire, carols-by-candlelight, corporate-carol-service, charity-carol-concert.

**House rules apply to all copy.** No supplementing London cathedral choirs. Other cathedrals only with the church's permission.

## carol-singers.html → redirect stub *(our call)*

**Why merge rather than swap roles:**
- christmas.html already carries the nav and the 23 guide Enquire bars.
- Google already shows it for carol-singer queries.
- The owner asked for christmas.html to be the improved page.

One strong page beats two half-pages splitting the signals.

**The stub:**
- A minimal HTML page with:
  - `<link rel="canonical" href="https://londonchoralservice.com/christmas.html">`
  - `<meta name="robots" content="noindex, follow">`
  - an inline script that runs `location.replace('/christmas.html' + location.search + location.hash)`, which keeps `?gclid=…`
  - a `<noscript><meta http-equiv="refresh" content="0; url=/christmas.html"></noscript>`
  - a visible link "Hire carol singers: continue to our Christmas page"
- GitHub Pages can't send a 301; this is the standard Pages substitute.
- The stub carries the analytics partial *only if* it is needed for the ad-visit tag. It isn't, because christmas.html reads the forwarded URL. So the stub stays minimal, with no analytics and no form.
- It stays in `PUBLIC` (it must return 200) and is excluded from `sitemap.xml` and `llms-full.txt` (the generators must skip noindex pages; check `scripts/generate_sitemap.py` and `generate_llms_full.py`, and add a skip if they don't already).
- Every in-repo link to `carol-singers.html` is repointed: partials, the 68 body links, guides and areas. They go to `christmas.html`, or to `christmas-carol-services.html` where the context is a church service. After the sweep, nothing on the site links to the stub.
- `check_live_site.py`, `stage_site.py` and the build's broken-link check must all pass. The design-markup test's hero list drops carol-singers.html and adds christmas-carol-services.html.

## Form (both pages)

Same Web3Forms endpoint, hCaptcha guard, `botcheck` honeypot, `ad_measurement` checkbox, `data-redirect` pattern and `js/form.js`. Changes:

- **Occasion select:** replace the funeral/wedding list with a hidden `occasion` = `christmas`, so the pipeline value is unchanged. Add a visible **`event_type`** select:
  - page 1: Office or staff party / Drinks reception / Hotel or venue lobby / Residents' event / Market or light switch-on / Outdoor event / Other
  - page 2: Church carol service / School or community service / Other
- **New optional fields:** `guests` (approximate number) and `postcode_or_venue` (venue or postcode). Both pages already say these are what we need to quote.
- **"How did you hear of us?":** drop "A funeral director" and "A wedding planner or venue" on these two pages.
- **Hidden `page`** = `christmas` / `christmas-carol-services`. The subject lines become "Christmas carol singers enquiry" and "Church carol service enquiry". Redirects: `thank-you.html?from=christmas` (unchanged) and `?from=carol-service`. The thank-you page already varies by `from`; add copy for `carol-service`.
- **Submit button** reads "Send enquiry" or "Check availability" (copy skill decides).
- **The enquiry assistant docs must learn the new fields:** `.claude/agents/lcs-reply-drafter.md` and Appendix E of the handover need a sentence each saying that `event_type`, `guests` and `postcode_or_venue` may appear, and that the `page` line tells carolling from church. The ad-visit campaign mapping (spec 2026-10-14; handover Appendix A; `lcs-review-bookings.md`) gains `christmas-carol-services` → Christmas.

## Off-site links to carol-singers.html

The stub keeps them working, but they should move:

- `docs/off-site-listings-pack.md`: the November Google Business Profile post links carol-singers.html. Repoint it to christmas.html.
- Add an item to `MANUAL-ACTIONS-REQUIRED.md` for the owner: change any live profile or listing link from carol-singers.html to christmas.html.
- Ads sitelinks and final URLs go through the Ads follow-up below. The script `create_christmas_carol_campaign_2026.py` is historical and stays as written.

## Site wiring

- **`partials/nav.html`:**
  - Services dropdown: "Christmas carol singers" → /christmas.html and "Church carol services" → /christmas-carol-services.html. This replaces "Christmas" and "Carol Singers".
  - The top-level seasonal "Christmas" link stays → /christmas.html.
- **`partials/footer.html`:** "Christmas carol singers" and "Church carol services".
- **index.html:** the Christmas block links both, carolling first.
- **for-* pages:** for-hotels, for-property-managers, for-event-managers and for-charities link christmas.html. for-livery-companies links both.
- **Music guides:**
  - Sticky-bar Enquire and in-body CTAs: the church-service guides point to christmas-carol-services.html. These are nine-lessons-and-carols, church-carol-service-choir-hire, carols-by-candlelight, advent-carols-vs-christmas-carols, christmas-carols-guide and corporate-carol-service when it discusses a church service.
  - Everything else points to christmas.html.
- **areas/*:** the "hire carol singers" and "book a carol service" links are repointed to the matching page.
- **Maintained files:**
  - `llms.txt`: the christmas.html line is rewritten, the carol-singers line removed, and a line added for the church page.
  - `graphify-out/` is refreshed (`/graphify --update`) since a page is added and one removed.
  - `data/seo-fix-discovered-urls.yml` video `page:` lists are updated.
  - Update the anti-cannibalisation contract in spec 2026-07-29 §1 with a dated note pointing here.

## Measurement

- GA4 already receives `lead_source = pathname` and `occasion` on the lead event. The hidden `page` field adds the same to the email.
- No new tracking scripts.
- Baseline to compare against: christmas.html and carol-singers.html sessions and key events since 1 Sep (tiny under Consent Mode). The Ads "Hire carol singers" group: 21 clicks, 0 conversions in 30 days. Judge the change by enquiries in the pipeline, not GA4.

## Ads follow-up (separate change, owner-approved)

After the new christmas.html is live, the Ads agent proposes the following, current → new, validate first:

- **Final URL:** the "Hire carol singers" ad's final URL moves from `https://londonchoralservice.com/carol-singers.html` to `https://londonchoralservice.com/christmas.html`.
- **Sitelinks:** any sitelink or asset pointing at carol-singers.html is repointed. A sitelink to christmas-carol-services.html is considered.
- **Other ad groups:** the paused/zero-impression groups that land on christmas-pricing.html are untouched.

The redirect stub keeps the old URL working, so there's no rush and no lost click. The prompt for that agent is given to the owner in chat.

## Noted, not a problem

- The generators already skip noindex pages (`generate_sitemap.py:91-92,131`; `generate_llms_full.py` reads only sitemap URLs), so the stub needs no script change.
- `js/form.js:23-28` reads `[name="occasion"]` whatever kind of field it is, so a hidden `occasion` keeps GA4's `occasion` value.
- It's the Most Wonderful Time becomes the hero on both christmas.html and christmas-pricing.html. That is acceptable: both pages are for the event buyer.

## Open question for the owner (does not block the build)

What does the client pay the church (hire, verger, the church's own organist), and does our £250 organist replace theirs? Until he says, the church page stays silent on it (see page 2 FAQ).

## Left to the builder

- Exact copy, written through the `writing-site-copy` and `stop-slop` skills.
- The hero layout. Reuse `.hero` / `.hero-video` / `.hero-text`. A compact "facts" list and a primary button style may need a small new component in `css/components.css`. Check mobile at 375 px: the h1, facts and button must sit above the fold, with the film below them on mobile if that is what it takes.
- Card markup for "Where we sing".
- Which guides make the six-link list, as long as it stays at six or fewer.
