# Growth ideas review, 25 October 2026

A second opinion on the 39 suggestions (items 8 to 46) another agent produced on 25 October. Each one was checked against the Google Ads account (30 days to 25 Oct), GA4, the Monday report of 19 Oct, the ledger counts, Zoho Drafts, and the repo. Verdicts: **Do now**, **Do**, **Later**, **Change** (worth doing in a different form), **Drop**. Prices quoted here match pricing.html: soloist £250, Small Choir of four £1,150, quintet £1,400, sextet £1,600, Full Choir of eight £2,000, Chorus of twelve £3,000, organist £250.

No client names, addresses or ledger money figures appear in this file; they live in `~/lcs-private`.

## 1. What the data says before any idea

1. **Enquiries come, but not from the ads.** Since 1 Sep the three campaigns cost £539 for 134 clicks and produced no enquiry by any measure: no ledger row with a click reference, no "Ad visit" line, no pipeline enquiry with a campaign, and no ad-measurement box ticked (ledger: 0 of 11). In the same period 11 enquiries arrived and 5 became bookings, all unattributed. The close rate is not the problem; enquiry volume and where it comes from is.
2. **Budget is not the constraint anywhere.** Last 30 days: funeral spent £134 (£4.46 a day of £5; 5% of impressions lost to budget, 40% lost to rank). Christmas spent £131 (£4.36 a day under an £8 budget; 5% lost to budget, 53% lost to rank). The £8 Christmas exception has bought nothing because the bids, not the budget, cap delivery. The 2 Nov decision is therefore about bids and ad quality, not the daily cap.
3. **Christmas: one ad group serves, three never do.** All 918 impressions in 30 days came from "Hire carol singers". Every keyword in "Carol singer prices", "Carol singers for events" and "Venue and lobby carols" (about 40 of them) is marked rarely served by Google. The two biggest live keywords are under bid: "carol singers london" (phrase) bids £3.50 against a first-page estimate of £9.46 and loses 68% of impressions to rank; "christmas carol singers london" (exact) bids £3.50 against £5.46 and loses 45%. Landing-page experience is rated below average on 9 live keywords, all landing on christmas.html while carol-singers.html exists.
4. **Funeral converts and has the quality problem.** Two Ads conversions in 30 days, the only campaign with any. "funeral choir" (phrase) is Quality Score 5 with expected click-through below average; its bid (£5) is already above the top-of-page estimate (£4.85), so the 41% lost to rank is a quality problem, not a bid problem. The wedding campaign got an unpinned second ad on 23 Oct and Google rates it Excellent; funeral has not.
5. **Organic is one page.** 65 Search Console clicks in the week to 16 Oct; 25 of them to the Nine Lessons and Carols guide, which ranks 1 to 7 for "order of service" queries. Money queries rank on page 3 or 4: "wedding choir" 38.8 and "choir for hire" 34.5, both answered by the home page rather than weddings.html; "corporate events choir" 36. The home page competes with its own service pages.
6. **The biggest lever is sitting in Zoho Drafts.** About 70 outreach drafts saved on 23 and 24 Oct are unsent (roughly 22 funeral directors, 21 wedding venues, 6 planners, 5 hotels, 5 event agencies, 4 livery companies, 4 supplier-list or link requests). Seven client reply drafts dated the morning of 24 Oct are also still in Drafts; if they were not sent another way, those enquiries have waited a day and a half, and four are Christmas enquiries.
7. **Reviews: the programme runs, but half the work is never asked.** The daily pass drafts a review request 2 to 14 days after a paid event and uses the direct Google link (`gbp_review_url` in `data/seo-fix-discovered-urls.yml`, read 23 Oct). The code never asks a funeral client, and funerals are three of the eleven bookings, so the trade booker on a funeral (the funeral director or planner who booked) is the untapped route. Rivals in the local pack show 14 to 83 reviews. (Corrected 26 Oct: an earlier draft of this file said the link was missing.)

## 2. Verdicts on the 39 suggestions

### Christmas (8 to 14)

| # | Idea | Verdict | Why, and what to change |
|---|------|---------|-------------------------|
| 8 | Named packages at list prices | **Change** | christmas-pricing.html already has four priced scenarios (office drinks reception £1,150; hotel lobby £1,400; livery-hall carol service £2,250; charity carol concert £3,250). Give those four names and anchor ids so an email can link to one, and add "grace at a livery dinner" to for-livery-companies.html at its real price: a Small Choir of four, £1,150. The agent's £250 grace price is wrong (£250 is the organist, and a solo singer is never the lead offer). The ads already say "Invoice Against Your PO". |
| 9 | Second Christmas ad with "Carol Singers" in five headlines | **Change** | The live ad already has carol singers in four headlines plus "Christmas Choir for Hire". The weak component is landing-page experience (below average on 9 keywords) because the ad lands on christmas.html. Add a second, unpinned ad in "Hire carol singers" whose final URL is carol-singers.html, by 1 Nov, through `scripts/ads/` with validate first. Also ask why the "Hire Carol Singers" sitelink (288 impressions, 8 clicks) is paused. |
| 10 | Lower bids on the weakest keywords to £2.50 | **Change** | "carol singers near me" is Quality Score 1 on both match types with every component below average: Google considers it irrelevant, and a lower bid keeps buying £3 clicks that never convert (4 clicks, £12.46, 0). Pause both. Leave "christmas carol singers" and "xmas carol singers" (QS 2, no cost). Do not raise bids towards the £9.46 first-page estimate on "carol singers london" phrase; a QS 4 keyword is not worth it. Raise "christmas carol singers london" (exact) to about £5.50 only after the landing-page change in item 9 lifts its score. |
| 11 | Hospice remembrance and funeral-director memorial services at £1,400 | **Later (Aug 2027)** | Good audience and the right price (quartet plus organist). Hospice "Light up a Life" and funeral directors' December memorials are planned by September, so 2026 is gone. Build the list in July 2027, incorporated bodies only (most hospices are companies or CIOs). |
| 12 | Send the outreach drafts by 7 Nov; add BIDs for 2027 | **Do now** | Not four drafts: about 70. Hotels, event agencies, and livery companies are already late for Christmas 2026, so send those this week; funeral directors and wedding venues are evergreen. Business Improvement Districts run the lights switch-ons and markets and are usually companies limited by guarantee: add them to the August 2027 list. |
| 13 | January rebooking email to 2026 business Christmas clients | **Do (Jan 2027)** | Cheap and the natural follow-up. Business clients and planners only: private Christmas clients book one party, weddings do not repeat, and funeral clients are never emailed. Drafts only, with an opt-out line; existing customers can be emailed about similar services. |
| 14 | A Christmas Business Profile post this week | **Do (owner, 5 min)** | Three posts are scheduled for 10 Nov, 24 Nov, and 8 Dec. One now costs nothing. Expect little from it; the review link (item 22) is the Business Profile item that matters. |

### Ads and measurement (15 to 20)

| # | Idea | Verdict | Why, and what to change |
|---|------|---------|-------------------------|
| 15 | Upload ad-sourced bookings to "Booked job" | **Drop as framed** | There is nothing to upload: the ledger shows 0 rows with a click reference and 0 with the measurement box ticked ("ready to upload 0"). The script is ready and defaults to validate-only; the input is empty. The missing step is upstream (section 3, idea A). |
| 16 | Second funeral ad, unpinned | **Do now** | Same pattern as the wedding ad of 23 Oct, which Google now rates Excellent. Funeral is the only converting campaign and its one live ad pins the price headline and the first description. Expect this to do more than any bid or budget change. |
| 17 | Check the 23 Oct lead-form fix on 2 Nov | **Do (queued)** | "Submit lead form" last fired 19 Sep. GA4 shows one `generate_lead` and one `form_start` in 30 days, so forms are rare in any case; most enquiries arrive by WhatsApp and email. Keep the check. |
| 18 | Image assets from the film stills | **Do** | No image assets exist (only the logo), and Google's dynamic-image recommendation is open. There are 14 stills, not 28 (each at 640 and 1280). Image assets need 1.91:1 and 1:1 crops of at least 600×314 and 300×300, so crop the 1280 versions. Mobile is 60% of Christmas and 67% of funeral impressions, where images show. |
| 19 | Funeral budget cap | **Keep £5 for now** | Spend averages £4.46 a day and only 5% of impressions are lost to budget; 40% are lost to rank with the bid already above the top-of-page estimate. The lever is ad quality (item 16). Revisit the cap on 5 Jan with the wedding bid check (ROADMAP R22). |
| 20 | Wedding lead form; Microsoft Ads; call extensions | **Drop / Later / Keep** | Google lead-form assets produce low-intent leads and the enquiry needs date, venue, and occasion: drop. Microsoft Ads at £1 to £2 a day is worth a funeral-only test in January once Bing Places is live (Bing skews older and desktop, which fits funeral bookers; the import from Google takes 20 minutes). Keep the call asset: it was only linked on 23 Oct, so "no call clicks in 90 days" measures nothing yet. Meta and paid YouTube: agreed, not worth it. |

### Search, AI answers, and getting found (21 to 28)

| # | Idea | Verdict | Why, and what to change |
|---|------|---------|-------------------------|
| 21 | Bing Places first | **Do now (owner, 10 min)** | Open in MANUAL-ACTIONS (item 2a). Imports from the Business Profile; feeds Copilot and ChatGPT local results; prerequisite for item 20's Microsoft test. |
| 22 | Google reviews from trade bookers | **Do (owner decision, then a small code change)** | Asking the funeral director or planner who booked (never the family) is within Google's rules: they had the experience, and the ask is not filtered by sentiment. The programme already asks every booked client except funeral clients, with the direct link in place. Extend `pipeline.py reviews-due` and the daily-pass rules so a funeral booked by a trade client gets one request to the trade address only, never to a family member. |
| 23 | Official profiles block on facts.html and llms.txt | **Do (30 min)** | Partly true: facts.html already links Companies House, and the `sameAs` links sit on index, about, and luca-wetherall. Add a short "Official profiles" list to both files, using only URLs already recorded in `data/seo-fix-discovered-urls.yml` (never invent the Business Profile URL). |
| 24 | YouTube titles, descriptions, and captions | **Do (owner, 1 hr)** | 14 films; the embed already forces captions on, but YouTube's auto-captions on sung text are poor. Title each film with piece, occasion, and ensemble size, and link to its guide. Pairs with ROADMAP R23 item 9. |
| 25 | Monthly AI-answer check | **Do, as a small addition** | Add ten fixed questions to the first-Monday growth agent, which already reports AI-search readiness, and log which sites are cited. No new tooling. |
| 26 | Consistent profiles | **Do the owner's four; skip the singers** | Same name and site link on lucawetherall.co.uk, LinkedIn, St Barnabas, and the Oxford profile is 30 minutes. Asking singers to add a line to their bios is a favour with little effect. |
| 27 | Journalists' requests | **Later** | ResponseSource charges experts; #journorequest is free but needs daily attention. A better route to press is a dated data story (item 41), pitched twice a year. |
| 28 | Weak borough pages | **Do, after the 7 Nov coverage rerun** | Borough pages get almost no impressions (areas/london.html had 31 in the week). Merge the ones still unindexed into the London page with redirects; keep and enrich those with real venue content (crematoria, churches). Combine with the CTA fix in item 32. |

### Conversion and design (29 to 33)

| # | Idea | Verdict | Why, and what to change |
|---|------|---------|-------------------------|
| 29 | A price beside every film with a pre-filled enquiry | **Do, light** | listen.html has six films and no per-film price; the enquiry links are page-level. Add one line under each choir film ("Sung here by four voices, £1,150") and an "Ask for this piece" link that pre-fills the contact form's message. Only under choir films: soloists are never the lead offer. |
| 30 | "Which size do I need?" picker | **Later, spec first** | A real conversion tool, but the data says enquiries convert well and are too few; traffic and outreach come first. Build it after the cheap fixes, as three questions (occasion, venue, guests) ending in a pre-filled WhatsApp message, with no new dependencies. |
| 31 | Personalised thank-you page | **Drop** | Already done in substance: thank-you.html switches h1, detail, and next steps by `?from=funeral|wedding|christmas|...`. A name and date add nothing a visitor needs. |
| 32a | Nav "Contact" as a "Get a quote" button | **Do** | True: plain link, no class. Standard fix in partials/nav.html plus css; rebuild. |
| 32b | A different film still per page's hero | **Change** | The claim is false: 97 of 156 pages have no hero image at all (all 33 boroughs, 31 guides, 20 areas, 13 root pages); 39 show YouTube thumbnails from several films. The gap is the opposite one. Add a still to the service and area pages (14 stills to choose from), and leave the guides without, to protect first paint on phones (ROADMAP R6 kept inlined CSS for that reason). |
| 32c | Buttons near the top of borough pages | **Do** | True: the first call to action is 43 to 58 lines after the h1, after several h2 sections; funerals.html has three within 10 lines. A template sweep bumps lastmod on 33 pages, which is acceptable. |
| 32d | Save form drafts if sending fails | **Do, small** | True: the catch block only shows the error and resets hCaptcha. Keep field values in sessionStorage on failure, restore on reload, clear on success. |
| 32e | Ad-measurement box behind "Optional" | **Change** | The box is shown openly on the funeral and contact forms and nobody has ticked it (0 of 11). Hiding it in a disclosure will not help. Remove it from the funeral form (a bereaved visitor will not tick a Google box) and reword it on the others as a plain sentence, last in the form. |
| 33 | Trust line naming venues and crematoria | **Do (owner supplies the list)** | Borough pages already name crematoria; funerals.html, weddings.html, and index.html do not. One quiet line each, from a true list, following the cathedral rule (we sing there as a separate ensemble, with permission). |

### Partnerships and offline (34 to 38)

| # | Idea | Verdict | Why, and what to change |
|---|------|---------|-------------------------|
| 34 | Funeral director fast lane | **Do** | for-funeral-directors.html exists but has no QR code, no WhatsApp link, and no single package price. Add a standard package (quartet plus organist, £1,400), a WhatsApp link pre-filled with "FD referral: [firm]" (which also tracks referrals without cookies), and a QR code for the printed sheet. Say "we call the family the same working day", which is true; "confirmed same day" is not (singers are confirmed within 48 hours). |
| 35 | Walk a borough's independent funeral directors; post to parish offices | **Do (owner)** | Suppliers to funeral directors still win work by visiting. One borough a month with the printed sheet from item 34. Letters sit outside the email rules. |
| 36 | Register-office supplier lists in four more boroughs | **Do (20 min batch)** | Low probability, near-zero cost. Note that register-office ceremonies cannot include religious music, so the pitch is the secular repertoire. |
| 37 | Planner partner sheet with a tracked link | **Do** | Commission agreed at 10%, disclosed; six planner drafts are in Zoho now. A one-page PDF and a tagged link (docs/utm-conventions.md) is an afternoon. |
| 38 | Five customer research calls | **Do (owner, Dec or Jan)** | Expected click-through is below average on nearly every keyword: the ads need the clients' own words. Past wedding and business clients and planners; never funeral clients. |

### Creative bets (39 to 46)

| # | Idea | Verdict | Why, and what to change |
|---|------|---------|-------------------------|
| 39 | Hymn-number table | **Do (Dec or Jan)** | Nothing like it exists on the site or, as far as the agent found, elsewhere. Hymn numbers are facts, so no copyright problem; Luca checks against the books. Fits the one organic pattern that works here: order-of-service material. |
| 40 | "Will it fit the slot?" planner | **Later** | Niche. The crematorium guide already gives Mortlake and City of London slot lengths. Do item 42 first; this can sit on top of it. |
| 41 | UK choir price index | **Do, spec first** | The data exists: five competitors, dated verbatim quotes, a validator in the build. A page with the method is the kind of original data AI answers and journalists cite. Decide where it lives (not under compare/, which is price-gated for families), extend `validate_competitor_claims.py` to cover it, and never link it from a for-* page. |
| 42 | London crematoria guides | **Do, spec first (five pages, Nov to Dec)** | Real utility for families and funeral directors; the funeral campaign's traffic is the audience. Facts from councils' and operators' public pages, with a checked date. Must be distinct from the borough pages or it becomes thin content. |
| 43 | "Hear the difference" recording | **Blocked on recordings** | Still the best argument for stepping up from four to eight voices (+£850). Film it on the showcase day (item 44). |
| 44 | Showcase evening | **Yes, small (Jan or Feb 2027)** | Quartet and octet, one church, one hour, planners and venue staff invited as the follow-up to the drafts going out now; doubles as the filming day for item 43. Budget about £1,200 (eight singers at the usual fee plus venue). |
| 45 | Keepsake recording add-on; "what London sings at funerals" data story | **Drop for now** | The add-on needs church consent and live-funeral audio is variable. The data story has three funerals of data behind it. |
| 46 | Livestreaming and licensing guide; alumni-newsletter note | **Do the guide; Later for the note** | Families and churches ask about livestream music licensing (PRS, CCLI, One License); a real question with little good coverage. The alumni note helps Wikidata only marginally. |

Agreed with the agent's one dropped item: "From" stays in front of prices, because out-of-London quotes add travel on purpose.

## 3. Better and additional ideas

Ordered by expected return for the time.

**A. Settle the attribution question in a week, not a season.** 134 clicks, zero enquiries by any measure, is either true or a measurement hole, and the Christmas decision on 2 Nov depends on which. Three checks: (1) compare GoatCounter visits with GA4 sessions on the ad landing pages to get the consent rate; (2) read the first message of each of the 11 enquiries in the pipeline for an "Ad visit" or "Ref:" line that was missed (no consent needed for "Ad visit"); (3) count paid-session WhatsApp and email clicks in GoatCounter by landing page. If all three say zero, the ads produced nothing and the spend guard should say so.

**B. Make the spend guard count enquiries, not clicks.** The guard in `scripts/reports/weekly_review.py` (`spend_guard_lines`) proposes a pause at £80 in 28 days only when there is no Ads conversion *and* no A or B enquiry. A single "WhatsApp or email click" conversion therefore holds a campaign open, which is why funeral (£127, 29 clicks, 1 click-conversion, 0 enquiries) was not proposed. Owner decision needed: should a click-conversion alone still count as a lead? If not, the condition becomes "no A or B enquiry", with the Ads conversions shown for information. With the current data every campaign outside its dated exception would then be proposed for pausing, which is the honest reading.

**C. Fold the three dead Christmas ad groups.** About 40 keywords marked rarely served. Pause the three groups (never delete) and stop spending time on them; their intents (hotels, offices, prices) are already headlines in the live ad. Fewer groups also concentrates data on the one that serves.

**D. Retitle the home page and let weddings.html rank for "wedding choir".** The 24 Oct research spec's first action, not yet done: index.html's title ("Choirs for Hire: Funerals & Weddings") makes the home page the ranking URL for "wedding choir" (38.8) and "choir for hire" (34.5). Make the home title brand-led, add the size-and-price table to weddings.html, and point internal links with "wedding choir" anchors at it. Same for hiring-a-choir.html at positions 12 to 14 for "hire a choir" and "how to book a choir": match the h1 and add the costs table.

**E. Build on the one organic pattern that works.** The Nine Lessons and Carols guide earns 25 of 65 weekly clicks on "order of service" queries. Add a printable order-of-service template to it with one quiet line ("a choir for your carol service from £1,150"), then repeat the pattern where the same intent exists: a funeral order of service template, a cremation service running order, a wedding order of service. Items 39 and 42 belong to the same family.

**F. Send the seven client reply drafts, or confirm they went another way.** Dated the morning of 24 Oct; four concern Christmas, which is decided in days. Then send the outreach queue (item 12).

**G. Check the review programme is firing.** The link is in place and the daily pass drafts requests, yet the profile shows about no reviews. Count the review-request drafts made so far (`pipeline.py reviews-due` and the imap-drafts record) against paid events since September, and find out whether they were sent. Then make the trade-booker change in item 22.

**H. Investigate the paid landings on `/pricing` without `.html`.** GA4 shows 10 paid-search sessions landing there in 30 days with 0% engagement. No ad, sitelink, or price asset uses that URL. Either Google rewrites it, or it is bot traffic. Check `page_location` with a gclid; if it is bots, exclude; if Google, make the extensionless URL canonicalise.

**I. Tidy the conversion actions.** "Contact" and "Contact (1)" are duplicates (secondary, last seen 19 Sep). Pause them so reports read cleanly; keep "WhatsApp or email click" and "Submit lead form" as the primaries.

**J. Check christmas.html on phones with `cwv.py --lab`.** Landing-page experience is the below-average component on nine Christmas keywords. If the lab run shows a slow first paint, that is the fix; if not, relevance is (item 9).

**K. Decide the Christmas bids on 2 Nov with the right question.** Not "£8 or £5" (neither binds), but: pause "carol singers near me" (QS 1), hold "carol singers london" phrase where it is (the £9.46 first-page estimate is not worth a QS 4 click), and test "christmas carol singers london" exact at £5.50 for two weeks after the landing-page change. Return the budget to £5 at the same time: it changes nothing in delivery and removes an exception from `budget_cap.py`.

**L. Reorder the priorities.** Enquiries convert at roughly one in two; the shortage is enquiries. That puts outreach (F, item 12), reviews (G), and discoverability (D, E, 28, 42) ahead of the conversion-and-design pieces (29 to 33), which are cheap enough to do but will not move the number on their own.

## 4. Decisions for the owner, with a recommendation

| Decision | Recommendation |
|----------|----------------|
| Reviews from trade bookers (22) | Yes: ask the funeral director or planner who booked, never the family. |
| Funeral budget cap (19) | Keep £5. Add the unpinned funeral ad; revisit on 5 Jan. |
| Christmas budget on 2 Nov (K) | Back to £5 now; it does not bind. Pause the QS 1 keywords; one bid test. |
| Microsoft Ads (20) | Funeral-only test, £2 a day, January, after Bing Places. |
| Wedding lead form (20) | No. |
| Call extension (20) | Keep; judge in January. |
| January rebooking email (13) | Business Christmas clients and planners only. |
| Showcase evening (44) | Yes, small: about £1,200, January or February, filming the comparison set. |
| Recording add-on price (45) | Not now. |
| Ad-measurement box on the funeral form (32e) | Remove it there; reword elsewhere. |

## 5. Sequence

**This week (owner, about two hours):** send or confirm the seven client drafts; send the Christmas-relevant outreach drafts (hotels, event agencies, livery), then the rest; Bing Places; one Business Profile post; the YouTube titles.

**This week (Claude, through `scripts/ads/` with validate first and approval per change):** unpinned funeral ad; second Christmas ad to carol-singers.html; pause "carol singers near me" (both); pause the three rarely-served Christmas ad groups; pause the duplicate "Contact" conversion actions; attribution checks A and H; the spend-guard rule in B.

**By 7 Nov (site PRs):** nav button; borough-page CTAs; form-draft saving; ad-measurement box change; home-page retitle and weddings.html table; official-profiles block; named Christmas scenarios and the grace line; funeral-director page (package, WhatsApp pre-fill, QR); per-film price lines on listen.html.

**November to December:** coverage rerun and borough decision (28); crematoria guides spec and first five pages (42); price-index spec (41); order-of-service template (E); planner sheet (37); livestreaming guide (46); image assets (18).

**January 2027:** rebooking drafts (13); hymn-number table (39); Microsoft Ads test; research calls (38); showcase (44, 43); cap review (19).
