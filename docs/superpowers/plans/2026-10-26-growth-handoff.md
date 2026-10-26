# Handoff: growth work after the 25 October review

Written 26 October 2026 for an agent starting fresh. It carries everything that agent needs that is not already in `CLAUDE.md`: the context, the verified state, the work in order, and where each piece needs the owner. Read it top to bottom once, then work package by package.

## 1. How to use this document

- The companion file `docs/superpowers/plans/2026-10-25-growth-review.md` holds the evidence and the verdict on each of the 39 ideas it came from. This file is the plan; that file is the reasoning. When they disagree, this file wins.
- Everything here was checked on 25 October against the Google Ads account, GA4, the Monday report of 19 October, the ledger counts, Zoho Drafts, and the repo. Numbers move; re-pull before acting on any of them.
- The owner, Luca Wetherall (they/them in anything you write about them), has given a full mandate for London Choral Service work: decide, build, open and merge reviewed PRs, and verify live. Two things always need their explicit approval: any change to the Google Ads account (one approval per change set, shown as current value → new value with a reason), and any business-policy call. Batch those into one question rather than several.
- Nothing is ever sent by you. Emails are drafts in Zoho that the owner sends. Ads changes run validate-only until approved. Nothing in the account is ever deleted; pause instead.
- No client names, addresses or ledger money figures go into the repo, a PR, a commit message or `logs/`. The repo is public.

## 2. The business in one paragraph

The London Choral Service is the trading name of Alma Consort Ltd, a small company (incorporated October 2025, not VAT-registered) that supplies professional singers for funerals, weddings, Christmas carol events and corporate occasions, mostly in London. The offer is a choir, not soloists: a Small Choir of four from £1,150, quintet £1,400, sextet £1,600, Full Choir of eight £2,000, Chorus of twelve £3,000; an organist or pianist is £250 (so four voices plus organist is £1,400); a soloist is £250 but is never the lead offer. Prices on every page and in every email must match `pricing.html` and `christmas-pricing.html`. The website is about 165 hand-written static HTML pages on GitHub Pages with a small Python build. Enquiries arrive by WhatsApp, email and a web form; an automated assistant drafts replies, and the owner sends them. Marketing is three small Google Ads search campaigns (funeral, wedding, Christmas; about £13 a day in total) plus organic search, a Google Business Profile, and outreach emails to firms.

## 3. Read first, in this order

1. `CLAUDE.md` in the repo root. All of it. The sections "Google Ads & GA4" and "Email and invoices" are the rules you will touch most.
2. `docs/superpowers/plans/2026-10-25-growth-review.md`: the evidence behind this plan.
3. `docs/superpowers/specs/2026-10-24-competitor-and-intent-research.md`, section 5 ("Top five actions"): the SEO reasoning for the home-page retitle and the hiring-a-choir guide.
4. `docs/superpowers/plans/2026-10-23-wedding-season-2027.md`: the pattern for adding a second responsive search ad and the test rule for pausing the loser. You will copy it twice.
5. `scripts/ads/wedding_season_rsa_2026_10_23.py` and `scripts/ads/ads_log.py`: the shape every Ads change script takes (docstring with the reason, constants, validate by default, `--apply` after approval, a log row).
6. `scripts/ads/budget_cap.py`: the budget caps (£5 a day; £8 for the Christmas campaign 24295921372 from 28 Sep to 13 Dec 2026 only).
7. `logs/ads-changes.md`: what has already been changed and why, newest first. Check it before proposing anything, so you do not redo or undo a recent change.
8. `MANUAL-ACTIONS-REQUIRED.md`: owner-only dashboard tasks. Never attempt these; you may remind the owner of them.
9. `docs/ROADMAP.md`, items R22 and R23: scheduled checks (5 Jan bids, April ad test) and the open items from the 24 Oct site audit, several of which this plan picks up.
10. Skills, before the relevant work: `build-and-verify` before any CSS, partial, nav or bulk change; `writing-site-copy` and `stop-slop` before any visible copy; `new-page` before any new page.

## 4. Rules that bite

These are all in `CLAUDE.md`; they are repeated here because they are the ones a fresh agent breaks.

- **Build pipeline.** Never hand-edit the generated CSS block or the content between `@include-start` and `@include-end` markers in a page. Edit `css/*.css` or `partials/*.html` and run `./build.sh`. A diff touching about 165 files after a CSS or partial change is normal. `sitemap.xml`, `data/page-dates.json`, `llms-full.txt` and article dates are generated; never hand-edit them. `llms.txt` is hand-maintained.
- **Allowlist.** The live site serves only what `PUBLIC` in `scripts/stage_site.py` lists. A new page directory or asset type must be added there, or the build fails. `.md`, `.py`, `.yml`, `.json` and `docs/` are private and 404 on the site.
- **Ads changes** go only through new scripts in `scripts/ads/` using the `google-ads` Python library, after `source .venv/bin/activate`. Run validate-only first, show the owner current → new with a reason, apply only after their explicit approval, and log the applied change in `logs/ads-changes.md`. Never through the MCP tools, which are for reading. Never delete; pause. Never set a budget above the cap. Never target solo-singer searches; every campaign carries the negatives singer, soloist, solo, vocalist.
- **Email.** Drafts only, from office@londonchoralservice.com, one recipient, no Cc, no bank details, to the person who wrote. Outreach emails go only to incorporated firms checked at Companies House, to a published business address, with an opt-out line; the prospect list is `~/lcs-private/outreach.csv` and never enters the repo.
- **Copy rules.** UK English. Oxford comma. No em-dashes in prose (the house parenthetical `&thinsp;&mdash;&thinsp;` in page copy is the one exception, and it stays). Never advertise roster size. Never say we add voices to or sing alongside a London cathedral's or Westminster Abbey's own choir. Never foreground soloists in heroes or calls to action. "From" stays in front of prices (out-of-London quotes add travel). No star ratings, `AggregateRating` or `Review` schema anywhere. Never state or imply VAT registration.
- **Unresolved facts** (Business Profile URLs, review link, video dates) come only from `data/seo-fix-discovered-urls.yml`. Never invent one.
- **Graph.** Keep `graphify-out/` out of content and feature PRs. Refresh it in its own PR when the build's last line says it is behind.
- **Credentials.** Never read, print or commit anything under `~/.config/lcs/`, `~/.config/gcloud/`, or the Keychain. `ls` to check existence is fine.
- **Worktree.** Work in a git worktree, one branch per PR, commit messages in the existing style (`fix(scope): …`, `copy: …`, `chore: …`), ending with the attribution line the session gives you.

## 5. Verified state, 25 October 2026

Use these to understand the plan, and re-pull them before you act.

| Fact | Value | Source |
|------|-------|--------|
| Season since 1 Sep: ad spend, clicks, enquiries attributed to ads | £539, 134 clicks, 0 enquiries by any measure | Monday report 19 Oct, section 11; ledger counts |
| Season: enquiries and bookings from all sources | 11 enquiries, 5 bookings, all unattributed | report section 9 and 11 |
| Ledger rows with a click reference or the ad-measurement box ticked | 0 of 11 | report section 9 |
| Funeral campaign (23735776277), last 30 days | £134, 32 clicks, 2 Ads conversions; £5 budget; 5% of impressions lost to budget, 40% to rank | GAQL campaign |
| Christmas campaign (24295921372), last 30 days | £131, 39 clicks, 0 conversions; £8 budget; 5% lost to budget, 53% to rank | GAQL campaign |
| Wedding campaign (23739971001), last 30 days | £62, 18 clicks, 0 conversions; £4 budget | GAQL campaign |
| Christmas ad groups | "Hire carol singers" serves everything (918 impressions); "Carol singer prices", "Carol singers for events" and "Venue and lobby carols" have every keyword marked `RARELY_SERVED` | GAQL ad_group_criterion |
| Christmas keywords under bid | "carol singers london" phrase: bid £3.50, first-page estimate £9.46, 68% lost to rank; "christmas carol singers london" exact: bid £3.50, first page £5.46, 45% lost | GAQL keyword_view |
| Christmas Quality Score 1 keywords | "carol singers near me", exact and phrase; 4 clicks, £12.46, 0 conversions; every component below average | GAQL keyword_view |
| Christmas landing-page experience | below average on 9 live keywords; the live ad (825999587211) lands on christmas.html; carol-singers.html exists | GAQL quality_info |
| Funeral "funeral choir" phrase | QS 5, expected CTR below average, bid £5 already above the £4.85 top-of-page estimate | GAQL keyword_view |
| Live ads | funeral: one ad (826000407483), Average, price headline pinned to position 2 and description 1 pinned; wedding: the 23 Oct unpinned ad (829372414723) is rated Excellent | GAQL ad_group_ad |
| Conversion actions | primary: "Submit lead form" (last fired 19 Sep) and "WhatsApp or email click"; secondary duplicates "Contact" and "Contact (1)"; "Booked job" (upload, £1,150 default) has never received an upload | GAQL conversion_action; logs/ads-changes.md |
| Assets | call asset linked to funeral and wedding on 23 Oct (so "no call clicks" measures nothing yet); price assets on all three; no image assets, only the logo; sitelink "Hire Carol Singers" → carol-singers.html is paused despite 288 impressions and 8 clicks | GAQL campaign_asset |
| GA4, last 30 days | 164 sessions; 5 contact_click, 5 contact_message, 1 generate_lead; 10 paid-search sessions landing on `/pricing` (no `.html`) with 0% engagement, from no known ad URL | GA4 run_report |
| Search Console, week to 16 Oct | 65 clicks, 25 of them to music-guides/nine-lessons-and-carols.html (positions 1 to 7 on "order of service" queries); "wedding choir" 38.8 and "choir for hire" 34.5 both answered by the home page; "corporate events choir" 36 | report section 6 |
| Zoho Drafts | about 70 outreach drafts dated 23 and 24 Oct, unsent; 7 client reply drafts dated the morning of 24 Oct | ZohoMail listEmails, Drafts folder |
| Review programme | running; link in `data/seo-fix-discovered-urls.yml` (`gbp_review_url`); funeral clients never asked (code) | `.claude/agents/lcs-daily-pass.md` |
| Repo facts | nav "Contact" is a plain link; 97 of 156 pages have no hero image; borough pages' first CTA is 43 to 58 lines below the h1; `js/form.js` keeps nothing on a failed send; ad-measurement checkbox shown openly on funerals.html and contact.html; thank-you.html already personalised by `?from=`; listen.html has no per-film price; for-funeral-directors.html has no QR, no WhatsApp link, no single package price; 14 film stills in `assets/films/` at 640 and 1280 | repo grep, 25 Oct |

## 6. Owner-only tasks (remind, never do)

These need the owner's accounts or hands. List them in your first message to the owner and tick them off when they say so.

1. Zoho Drafts: send or discard the seven client reply drafts from 24 Oct (four are Christmas enquiries), then the outreach drafts: hotels, event agencies and livery companies first (Christmas is weeks away), then funeral directors and wedding venues.
2. Bing Places sign-up (MANUAL-ACTIONS item 2a). Imports from the Business Profile in minutes. Prerequisite for the January Microsoft Ads test.
3. One Christmas Business Profile post now; three are already scheduled for 10 Nov, 24 Nov and 8 Dec.
4. YouTube: retitle the 14 films with piece, occasion and ensemble size; add the guide link to each description.
5. Profiles: same name and site link on lucawetherall.co.uk, LinkedIn, the St Barnabas page and the Oxford profile.
6. A true list of venues and crematoria where the singers have sung, for the trust lines (work package 3, item j).
7. Decisions in section 9.

## 7. Work packages

Do them in this order. Each has a goal, the steps, the files, how to verify, and where approval sits.

### WP1. Google Ads changes (this week)

All through new scripts in `scripts/ads/`, named `<what>_2026_10_<dd>.py`, copying the structure of `wedding_season_rsa_2026_10_23.py`: docstring with the reason and the validate/apply commands, constants, validate-only by default, `--apply` after approval, `ads_log.append_row` on apply. Run each validate-only, show the owner every change as current → new with the reason, and apply only what they approve. One approval message can cover the whole package if you present it as one list.

a. **Second funeral ad, unpinned.** Campaign 23735776277, "Ad group 1", beside ad 826000407483 (which stays). Final URL `https://londonchoralservice.com/funerals.html`. No pins. "funeral choir" in at least five headlines and three descriptions. Every claim traced to funerals.html, pricing.html or about.html, with the source noted beside each line in the script. Keep the house rules: no VAT, no roster size, no "nothing on top" (travel outside Greater London is added to the quote). Test rule as in the wedding plan: in April 2027, pause the ad with the lower CTR at 300+ impressions each.

b. **Second Christmas ad to carol-singers.html.** Campaign 24295921372, ad group "Hire carol singers", beside ad 825999587211 (stays). Final URL `https://londonchoralservice.com/carol-singers.html`. No pins. Same tracing discipline; the copy sources are carol-singers.html, christmas.html and christmas-pricing.html. Reason: landing-page experience is the below-average component on nine keywords in this group and the live ad lands on christmas.html.

c. **Pause "carol singers near me", exact and phrase**, in "Hire carol singers". Reason: Quality Score 1, every component below average, 4 clicks and £12.46 with no conversion. Pause, never remove. Leave "christmas carol singers" and "xmas carol singers" (QS 2, no cost) alone.

d. **Pause the three rarely-served Christmas ad groups**: "Carol singer prices", "Carol singers for events", "Venue and lobby carols". Reason: every keyword `RARELY_SERVED`, zero impressions in 30 days; their intents are already headlines in the live group. Pause the ad groups (AdGroupService, status PAUSED), not the keywords one by one.

e. **Hide the duplicate conversion actions** "Contact" and "Contact (1)" (both secondary, last fired 19 Sep) by setting their status to HIDDEN, not REMOVED. Reason: they clutter the reports and count nothing the primaries do not.

f. **Christmas budget back to £5** (campaign 24295921372), owner decision (section 9). Reason: spend averages £4.36 a day under the £8 budget and only 5% of impressions are lost to budget. Use `scripts/ads/set_budget.py` if it fits; `budget_cap.py` already allows £5. Do not touch `budget_cap.py` itself unless the owner asks to end the exception early.

g. **Ask, do not change:** why the sitelink "Hire Carol Singers" (asset 424775770945, → carol-singers.html) is paused. If the owner has no reason, propose re-enabling it in the same approval list.

h. **One bid test, after b has run for two weeks:** "christmas carol singers london" exact from £3.50 to £5.50 (QS 4, first-page estimate £5.46). Do not raise "carol singers london" phrase towards its £9.46 estimate. Record the test's end date (two weeks) and the success measure (an A or B enquiry from the campaign, per the pipeline) in the script docstring.

Verification: after `--apply`, re-run the read query that showed the old state and paste the new state. Add the log rows. Nothing else in the account changes.

### WP2. Measurement (read-only, plus one rule proposal)

a. **Attribution audit.** Answer, with numbers: did the 134 ad clicks produce any enquiry? Three checks. (1) GoatCounter visits on the four ad landing pages (`scripts/reports/goatcounter.py`; the key is in the Keychain and the script reads it, you never do) against GA4 sessions on the same pages, to estimate the consent rate. (2) `~/lcs-private/enquiries.csv` notes, via `scripts/bookings/pipeline.py`, for any "Ad visit" or "Ref:" line on the 11 season enquiries (an "Ad visit" line needs no cookie consent, so its absence is meaningful). Read only; never copy identifiers out. (3) GoatCounter's enquiry events by landing page for paid sessions. Report the three results in one short table.

b. **The `/pricing` landings.** GA4 shows 10 paid-search sessions landing on `/pricing` (no `.html`) with 0% engagement. No ad, sitelink or price asset uses that URL; the live site serves it with a 200. Pull `page_location` with `gclid` present for those sessions. If bots, note it for the Internal Traffic or bot filter; if Google rewrites the URL, propose a canonical redirect in the next site PR.

c. **Spend-guard rule.** `scripts/reports/weekly_review.py`, `spend_guard_lines`: today a campaign at £80+ in 28 days is proposed for pausing only when it has no Ads conversion *and* no A or B enquiry. Funeral (£127, 29 clicks, 1 click-conversion, 0 enquiries) is held open by one click-conversion. Put the question to the owner (section 9). If they agree, change the condition to "no A or B enquiry" with the Ads conversions shown for information, update the docstring and the owner-decision comment, and extend `tests/test_economics.py` or the test that covers this function. Do not change the rule without the decision.

d. **Review programme check.** Count the review-request drafts made since September (`pipeline.py reviews-due`, `~/lcs-private/imap-drafts.csv`) against paid events, and whether they were sent (Sent folder, read-only). Report the count. Then, if the owner says yes to trade-booker reviews (section 9), extend `pipeline.py` and `.claude/agents/lcs-daily-pass.md` so a funeral booked by a funeral director or planner gets one request to that trade address, never to a family member, with the same Google-rules wording.

### WP3. Site changes by 7 November

One PR per item, each on its own branch from `main`, built with `./build.sh`, checked with the `build-and-verify` checklist, copy checked against `writing-site-copy` and `stop-slop`. Open the PR, let CI pass, merge, then `git fetch origin && python3 scripts/check_live_site.py`. Do not bundle these: several touch partials and will each produce a 165-file diff, which is normal.

a. **Nav "Get a quote" button.** `partials/nav.html` line with `<a href="/contact.html">Contact</a>`: make it a button-styled link reading "Get a quote". Styles in `css/components.css` or `css/layout.css` (the nav rules are in layout.css near `.nav-links`). Check the mobile menu and the private-register pages (they have their own header and must not change).

b. **Borough-page calls to action.** `areas/london/*.html` (33 pages): add the same three-button row funerals.html has within ten lines of its h1 (WhatsApp, email, enquire; WhatsApp and email before any call, no Call button). The pages are hand-written, so this is a scripted sweep; keep each page's existing wording. `lastmod` moving on 33 pages is expected.

c. **Form drafts on failure.** `js/form.js`: on a failed send (the existing catch block), write the field values (not the hCaptcha token, not `botcheck`) to `sessionStorage`; on load, restore them if present; clear on success. Keep the `h-captcha-response` check and the `botcheck` honeypot. Add a test to `tests/` if one covers form.js; otherwise test by hand in the browser preview with the network blocked.

d. **Ad-measurement checkbox.** Remove the `ad_measurement` block from funerals.html's form. On contact.html and the other forms, move it to last and reword the label as one plain sentence (load `writing-site-copy`). Keep the name `ad_measurement` and value `yes`: `scripts/ads/upload_bookings.py` and the pipeline depend on them.

e. **Home-page retitle and weddings table.** index.html: a brand-led `<title>` and h1 that stop competing for "wedding choir" and "choir for hire" (the 24 Oct research spec, action 1). weddings.html: add the size-and-price table (four to twelve voices, prices as on pricing.html, "From" kept) and move the proof (venues, credits) into the first screen. music-guides/hiring-a-choir.html: h1 and intro matched to "hire a choir" and "how to book a choir", plus the costs table and the "three ways to hire" table from the spec. Meta descriptions 141 to 161 characters, unique. Keep the Nine Lessons guide untouched in this PR.

f. **Official profiles block.** facts.html and llms.txt: a short "Official profiles" list with Companies House, YouTube, Wikidata (only if the sameAs on index.html already has it) and the Business Profile Maps URL, all taken from `data/seo-fix-discovered-urls.yml` or the existing `sameAs`. Never invent a URL.

g. **Named Christmas scenarios and the grace line.** christmas-pricing.html, section "What typical Christmas bookings cost": give each of the four scenarios a name and an `id` anchor so an email can link to one (for example `#office-reception`, `#hotel-lobby`, `#livery-carol-service`, `#charity-concert`); prices unchanged. for-livery-companies.html: one line on grace at a livery dinner, a Small Choir of four, £1,150 (the £250 on that page is the organist; a soloist is never the lead offer).

h. **Funeral-director page.** for-funeral-directors.html: a standard package line (quartet plus organist, £1,400); a WhatsApp link `https://wa.me/447356042468?text=` pre-filled with "FD referral: " and a space for the firm name (`data-whatsapp` attribute as in `partials/footer.html`, so the click tracking picks it up); a QR code image of that link for the printed sheet (generate it as an SVG into `assets/`, and add the asset type to `PUBLIC` in `scripts/stage_site.py` if SVG is not already listed). Say "we call the family the same working day" (true); do not say "confirmed same day" (singers are confirmed within 48 hours).

i. **Per-film price lines on listen.html.** Under each choir film: one sentence with the ensemble size and price, and an "Ask for this piece" link to contact.html with the `message` field pre-filled through a query string that `js/form.js` reads (add that reading; `occasion` and `choir_size` already exist as fields). Skip any soloist film.

j. **Trust lines.** funerals.html, weddings.html, index.html: one quiet sentence each naming venues or crematoria where the singers have sung, from the owner's list (section 6, item 6). Cathedral rule: as a separate ensemble, with permission; never "alongside" a London cathedral's choir. No logos, counts or stars. `validate_house_claims.py` runs in the build and will catch the London choir rule.

Verification for every PR: `./build.sh` passes (it runs the JSON-LD, house-claims, allowlist and link checks); the first screen looks right with and without the CSS bundle; `python3 scripts/check_live_site.py` after merge.

### WP4. November to December

Each of these starts with a spec in `docs/superpowers/specs/YYYY-MM-DD-<name>-design.md` in the style of the existing ones, approved by the owner before any page is written.

a. **Coverage rerun and borough decision.** On or after 7 Nov run `.venv/bin/python scripts/reports/index_coverage.py --section boroughs --json out.json` (about 15 minutes, read-only). Boroughs still unindexed: merge into areas/london.html with redirect stubs (see how existing stubs are done: a canonical and no `noindex`, per ROADMAP R23 item 10). Boroughs with real venue content stay and get it strengthened.

b. **London crematoria guides.** Five pages first (slot lengths, chapel size, organ, access, price), facts from councils' and operators' public pages with a checked date, distinct from the borough pages. Use the `new-page` skill; add to `llms.txt`, the music-guides index, and `PUBLIC` if a new directory. music-guides/crematorium-music.html already has two slot lengths to start from.

c. **UK choir price index.** A page built from `data/competitor-pricing.yml` (five competitors, dated verbatim quotes), with the method. Not under `compare/` (price-gated, for families). Extend `validate_competitor_claims.py` so the build fails if the page's figures drift from the data. Never link it from a `for-*.html` page.

d. **Order-of-service template** on the Nine Lessons and Carols guide (a printable section, one quiet line about a choir from £1,150), then the same pattern for a funeral order of service and a wedding order of service. This is the one organic pattern that already ranks.

e. **Planner partner sheet.** A one-page PDF for planners (10% commission per couple, paid after the client has paid, disclosed) with a tagged link following `docs/utm-conventions.md`. Place the PDF in `assets/` and add the type to `PUBLIC` if needed.

f. **Livestreaming and music-licensing guide** (PRS, CCLI, One License, what a church's licence covers). Music-guides format.

g. **Image assets for Ads.** Crop the 1280 stills in `assets/films/` to 1.91:1 (at least 600×314) and 1:1 (at least 300×300), upload as image assets through a `scripts/ads/` script, validate first, approval, log.

h. **Hospice and funeral-director memorial outreach and Business Improvement Districts** go on the list for July and August 2027, not now; note them in `~/lcs-private/outreach.csv` notes or the private outreach file, not in the repo.

### WP5. January 2027

- Rebooking drafts to 2026 business Christmas clients and planners (not private clients, never funeral clients), via the enquiry assistant's draft path, with an opt-out line.
- Hymn-number table (about 40 hymns, numbers in the main books, tune names, verses, timings); the owner checks it against the books.
- Microsoft Ads funeral-only test at £2 a day, after Bing Places is live; same change protocol, same caps, logged in `logs/ads-changes.md`.
- Funeral budget cap review on 5 Jan with the wedding bid check (ROADMAP R22).
- Showcase evening (quartet and octet, one church, one hour, planners and venue staff; about £1,200), doubling as the filming day for the "hear the difference" comparison set (one hymn sung by a soloist, four voices and eight voices in the same building).
- Five customer-research calls (past wedding and business clients and planners; never funeral clients).

## 8. What not to do

- Do not upload to "Booked job": there is nothing to upload (0 ledger rows with a click reference). Fix attribution first (WP2a).
- Do not raise either campaign's budget to fix "lost to rank": budget is not the constraint anywhere.
- Do not lower bids on the Quality Score 1 keywords instead of pausing them.
- Do not add a hero still "per page" on the theory that pages share one: 97 pages have none. If you add images, do it only on service and area pages, and check first paint on phones (ROADMAP R6 kept inlined CSS for that reason).
- Do not personalise thank-you.html further; it already switches by occasion.
- Do not build a Google lead-form asset, a keepsake-recording add-on, or a "what London sings at funerals" data story.
- Do not touch the Nine Lessons and Carols guide except to add the template (WP4d). It is the site's one organic earner.
- Do not run `imap_draft.py` Trash helpers, `--owner` commands, or anything that sends mail. Do not change Books by hand or ask the owner to.
- Do not put client names, email addresses, firm names from the outreach list, or booking amounts in any repo file, PR, commit or log.

## 9. Decisions to put to the owner, in one message

| Decision | Recommendation in the review |
|----------|------------------------------|
| Christmas budget back to £5 now (WP1f) | Yes; it does not bind, and it removes an exception. |
| Pause the QS 1 keywords and the three dead ad groups (WP1c, d) | Yes. |
| Hide the duplicate "Contact" conversion actions (WP1e) | Yes. |
| Re-enable the paused "Hire Carol Singers" sitelink (WP1g) | Ask why it was paused first. |
| Spend guard: should one click-conversion still hold a campaign open? (WP2c) | No; count A or B enquiries only. |
| Reviews from the trade booker on a funeral (WP2d) | Yes; the trade address only, never the family. |
| Remove the ad-measurement box from the funeral form (WP3d) | Yes. |
| Funeral budget cap | Keep £5; revisit 5 Jan. |
| Microsoft Ads funeral test in January | Yes, £2 a day. |
| Showcase evening | Yes, small, January or February. |

## 10. Reporting back

- First message to the owner: the owner-only list (section 6) and the decisions (section 9), in one message, nothing else.
- Each Ads change set: one message with every change as current → new and the reason, after the validate-only run; apply only what is approved; then the log rows and the re-read state.
- Each site PR: the PR link, what changed, the build result, and the live check result. Merge reviewed PRs yourself (owner mandate), then verify live.
- When the Monday report (`~/lcs-private/reports/<date>.txt`) next runs, read sections 1, 3, 11 and 12 to see whether anything here has moved the numbers, and say so plainly, including when it has not.
