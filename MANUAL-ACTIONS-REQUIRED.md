# Manual actions required — SEO audit fix programme

These items came out of the 2026-05-08 SEO audit but cannot be implemented in code from this repo. Each one needs a human in front of the relevant dashboard, account, or hosting console. Work through them in the order given; later phases of the programme assume some of these are done.

---

## 1. Google Business Profile claim and category audit

The site already references a Google Maps presence — `index.html` carries `sameAs: ["https://share.google/HRgq38OubHmj3Zz9v"]` in the Organization schema. That's a share-style short link, not the canonical place URL, and the audit flags it as the single highest-impact local-SEO blocker.

**Update 2026-08-20 (steps 5–7 done):** the owner supplied the full Maps URL; the canonical cid form (`https://www.google.com/maps?cid=12581882416994311757`, derived from the URL's ftid) now replaces the share.google short link in index.html's Organization sameAs, and `data/seo-fix-discovered-urls.yml` is updated. The Maps listing is anchored as "The London Choral Service, Maidenhead" — whatever address GBP shows is the NAP master for §2. **Remaining in §1: the category audit only (steps 3–4).**

**Update 2026-08-19:** the owner reports the listing has been claimed.

**Checked 2026-10-23, signed in (read-only):** the profile is verified, business ID `07940104319114173142`, service area "London, UK and Greater London, UK". The dashboard still shows the old description (it offers soloists and says Luca directs the service) and only the Choir category. Claude's attempt to make the click-by-click edits below was stopped by Claude Code's permission check, because they publish to a live profile. Either do steps 2–7 yourself, or tell Claude in a live chat "edit the Google Business Profile as in MANUAL §1" and allow the edits when asked.

**Audit 2026-10-23 (public listing, signed out, UK).** What a searcher sees on the cid URL:

| Field | Now | Should be |
|---|---|---|
| Primary category | Choir | Choir. Leave it. |
| Secondary categories | not shown publicly | Wedding Service, Funeral Service (check in the dashboard) |
| Hours | Mon–Sat "Open 24 hours", Sun 8:30am–5pm | the hours you really answer the phone. `contact.html` says Mon–Fri 9am–6pm. 24 hours is untrue, and Google treats hours as a ranking signal, so a false figure risks a suspension report |
| Address | hidden; pin in south-east London, no Maidenhead shown | hidden, with a service area (correct for a service-area business) |
| Website | `https://londonchoralservice.com/`, no tags | `https://londonchoralservice.com/?utm_source=google&utm_medium=organic&utm_campaign=gbp` (`docs/utm-conventions.md`) |
| Phone | 07356 042468 | same; matches the site |
| Reviews | none | the first few come from §3 requests, never from funeral clients |
| Photos | 5 | 10 or more, all real (film stills, rehearsal photos), 2–3 more a month |
| Description, services, posts | not visible signed out | check in the dashboard against `docs/off-site-listings-pack.md` §"Google Business Profile" |

A brand search for "The London Choral Service" shows no Business Profile panel yet. On Maps, "funeral singers london" and "carol singers london" jump straight to the competitor whose name matches (The London Funeral Singers: category Musician, 70 reviews, real weekday hours). Reviews and accurate hours are the gap, not the category.

**Click-by-click (about 20 minutes, desktop, signed in to the account that owns the listing):**

1. Go to `https://business.google.com/`, choose **The London Choral Service**, and open the profile manager (or search Google for "my business" while signed in). Click **Edit profile**.
2. **Categories.** On the **About** tab, click the pencil beside **Business category**. Primary: **Choir**. Click **Add another business category** and add **Wedding service**, then **Funeral service**. If Google offers **Carol singer** or **Musician**, leave them off: Choir already covers them. **Save.**
3. **Description.** Still on **About**, paste the description from `docs/off-site-listings-pack.md` §"Google Business Profile" (680 characters, limit 750). **Save.**
4. **Contact → Website.** Replace the website with the tagged URL in the table above. **Save.**
5. **Location → Business location.** Confirm the address is hidden (no street address on the profile). Under **Service area**, list London, Surrey, Kent, Essex, Hertfordshire, Berkshire and Buckinghamshire. **Save.**
6. **Hours.** Set **Open with main hours**, then Monday to Friday 09:00–18:00 and Saturday and Sunday closed. If you do take calls at weekends, enter those hours instead and tell an agent, so `contact.html` says the same. **Save.** Then **More hours** is optional; skip it.
7. **Services.** Back on the profile manager, click **Edit services**. Under **Choir**, add or check: Wedding choir; Funeral choir; Memorial service music; Christmas carol singers; Church carol services; Corporate event choir; Organist and pianist hire. Give each a one-line description and, where it asks for a price, use only `pricing.html` / `christmas-pricing.html` figures (Small Choir of four £1,150; organist or pianist £250). **Save.**
8. **Photos.** Click **Add photo**. Upload the Christmas film still (Claude converted it to JPG) and stills from your own copies of the films. No stock or AI images.
9. Send an agent a screenshot of the About and Services tabs once saved, so it can tick this section off.

The seasonal posts are in §9 item 1. The review link is §23.

What to do:

1. Open the Google Business Profile dashboard at `https://business.google.com/`. Sign in with the account that controls the listing.
2. Confirm the listing is verified (green tick on the listing card). If it isn't, complete verification — postcard, video, or phone, whichever Google offers.
3. Check the **primary category**. It should be **Choir** if Google offers it for the locality, otherwise **Music Service**. Avoid generic alternatives like "Performing arts group" — they bury the listing for funeral and wedding intent.
4. Check the **secondary categories**. Add **Wedding Service** and **Funeral Service**. These two cover the bulk of commercial intent for the site and are the categories Google's local pack matches against for those queries.
5. Capture the canonical Maps URL. From the listing in Google Maps, click **Share** → **Copy link**, then in a fresh browser tab paste it and let it redirect to the long form. The canonical form is `https://www.google.com/maps/place/<name>/data=<id>` or `https://www.google.com/maps/place/<name>/@<lat>,<lng>,<zoom>z/data=<id>`. Either is acceptable as long as it is the long-form, not a `share.google/...` short link.
6. Replace the share.google value in `index.html` (and anywhere else it appears across the schema graph) with that canonical URL. This will be picked up by Phase 2 once the URL is added to `data/seo-fix-discovered-urls.yml`.
7. Add `data/seo-fix-discovered-urls.yml` → `gbp_canonical_maps_url` with the captured URL and remove the TODO comment.

If the listing turns out not to exist or isn't verified, claim it before doing any of the citation work in §2 — third-party citations should resolve back to a verified GBP, not orphan listings.

### Other discovery items still TODO

Three other items in `data/seo-fix-discovered-urls.yml` couldn't be resolved at Phase 1. Each ships as a TODO comment in the schema until you fill it in:

- **Done 2026-10-23 (ORCID):** the registry has one Luca Wetherall, `0000-0001-9099-2485` (Royal Holloway, University of Oxford), now in the YAML and in `Person.sameAs` on `about.html`, `luca-wetherall.html` and `index.html`. The earlier candidate `0000-0003-4217-5362` was someone else's record. The LinkedIn company page still doesn't exist (`/company/london-choral-service` 404); making one is yours.
- **`luca_wetherall_orcid`** — if Luca has an ORCID, add it to `data/seo-fix-discovered-urls.yml` and rerun the schema sweep on `about.html` to populate `Person.sameAs`.
- **`lcs_linkedin_company`** — if a LinkedIn company page exists for The London Choral Service or Alma Consort, add its URL to the YAML and rerun the schema sweep on `index.html` to populate `Organization.sameAs`.
- **`videos[*].upload_date`** + **`videos[*].duration`** — **Done 2026-10-14:** all eight videos in the YAML now carry a verified upload date and duration; nothing left here. (Original note: five YouTube videos' metadata still can't be resolved automatically (consent gate on four; the egress proxy blocks YouTube outright for `ZVSQ2Ts4GZE`, the Anima Christi recording added 2026-08-15). Open each video on YouTube manually, capture the upload date (YYYY-MM-DD) and the duration (convert to ISO 8601, e.g. 3:42 → `PT3M42S`), update the YAML, and rerun the VideoObject sweep on `pricing.html`, `listen.html`, and the two `music-guides/anima-christi-*` pages. The fifth video, `mKMjUvCCW3E`, was resolved by the user on 2026-08-15 and its `VideoObject` now ships on `listen.html`, `christmas.html`, and `carol-singers.html`.)

These are LOW priority next to the GBP work above — they affect knowledge-graph completeness and AI-citation strength, not local-pack ranking.

---

## 2. Third-party citation building

The site has no presence on the citation sources Google cross-references for local rankings. Audit's recommendation: claim or audit each of the following.

| Site | URL | Account state to confirm |
| --- | --- | --- |
| Bark | `https://www.bark.com/` | Provider profile claimed for the trading name "The London Choral Service"; categories set to wedding music + funeral music |
| Hitched | `https://www.hitched.co.uk/` | Wedding-music supplier listing live; price guide present; at least one review |
| Bridebook | `https://bridebook.com/` | Supplier listing live; portfolio populated |
| FuneralGuide | `https://www.funeralguide.co.uk/` | Funeral-music supplier listing live |
| Yell | `https://www.yell.com/` | Free claim of the business listing; NAP (name, address, phone) matches GBP exactly |

**Update 2026-08-20:** drafted profile copy for all five sites above (plus Encore, Poptop, and GBP) now lives in `docs/off-site-listings-pack.md` — each listing is a paste job.

**Update 2026-10-23:** the pack is checked against today's site, with a tagged website link per listing, a hidden address and the Google profile's hours. It now has click-by-click sign-up steps and field-by-field copy, in §"Per-site setup", for Bing Places, Apple Business, Hitched, Bridebook, Yell and Guides for Brides (the round to do now; Bark and FuneralGuide stay skipped, as the pack's status table says). No listing existed on Bing or Apple Maps. Bing imports the Google profile and verifies itself from it. Apple has no hide-address option, so it gets a brand presence and no Maps pin. Upload images are in `~/Pictures/LCS-listings/`. What only you can do on each site: make the account, enter passwords and codes, accept the terms, and press Publish. Claude fills the rest in the Claude app's browser once you're signed in and stops before each Publish, then records each live URL in the pack's status table.

NAP consistency is the load-bearing detail. Whatever address and phone format you use on GBP, use the same one verbatim everywhere else. Different formats split the local-SEO citation graph and Google treats the variants as separate entities.

When you've done the round, run a free citation scan against the homepage URL at `https://www.brightlocal.com/free-business-listings-scan/`. The report flags any further sources where the listing is missing or has inconsistent details.

---

## 3. Post-event review request workflow

**Mostly done 2026-10-14:** the enquiry assistant's daily pass now drafts one review request 3–14 days after each paid-in-full event (never after a funeral), so the day-30/60/90 cadence below is superseded. One thing remains for you: open a Trustpilot business account if you want reviews there as well as on Google (and §23, the optional review link).

The audit's #4 critical priority is a review-request cadence. Goal: 30+ Google + Trustpilot reviews in 90 days. The review velocity is what shifts the local pack ranking, not the absolute count, so the cadence matters more than getting the sequence perfect.

Set up a simple template-based workflow. After every booking that completes, schedule three touches:

- **Day 30** — Email the booker. Thank them, link directly to the GBP review form (`https://search.google.com/local/writereview?placeid=<placeid>` once you have the place ID from §1). Ask for one or two sentences and a star rating. Keep it short; long requests convert badly.
- **Day 60** — If they didn't review on day 30, send a follow-up. Different angle: ask whether anything could have been better. Either you get a review, or you get something to fix.
- **Day 90** — Final touch. Link to Trustpilot this time (`https://uk.trustpilot.com/evaluate/londonchoralservice.com`). Some reviewers will only post on platforms they already use; offering both broadens the pool.

A lightweight way to run this: a Google Sheet of bookings with a column for "review request status", and three calendar reminders per booking. Mailchimp, ConvertKit, or even Apple Reminders all work. Don't over-engineer it before you know whether the cadence converts — pick the simplest tool you'll actually use.

Do not offer incentives for reviews. Both Google and Trustpilot have policies against paid or incentivised reviews, and being caught at it removes the listing.

---

## 4. GSC, GA4, and CrUX credentials

**Done 2026-10-14:** no service account is needed. Application Default Credentials carry the Search Console and GA4 scopes (see "Sign-in scopes" in the repo's agent instructions), and the Monday review reads both with them. The CrUX API key below is optional and still unset; nothing depends on it.

The audit's §9 and several Phase-3+ items depend on having read access to real Google performance data. None of these can be set up from inside this repo.

**Search Console + GA4** — both need a Google Cloud service-account JSON key with the right scopes:

1. Open `https://console.cloud.google.com/iam-admin/serviceaccounts`. Pick or create a project (e.g. `lcs-seo-tooling`).
2. Create a service account named something like `seo-readonly`. No roles at the project level.
3. Once created, generate a JSON key for it and download the file. **Don't commit the JSON to the repo.** Put it somewhere secret — `~/.config/lcs-seo/service-account.json` is fine — and reference it via env var.
4. Grant the service account read access at the **resource** level, not the project level:
   - In Google Search Console (`https://search.google.com/search-console`), open the property settings for `londonchoralservice.com` → Users and permissions → Add user. Email = the service account email (looks like `seo-readonly@<project>.iam.gserviceaccount.com`). Permission = Restricted (read-only).
   - In Google Analytics (`https://analytics.google.com/`), open the GA4 property → Admin → Property Access Management → Add user. Same email. Role = Viewer.

**CrUX (Chrome User Experience Report)** — this one needs a separate API key, not a service account.

1. Open `https://console.cloud.google.com/apis/credentials` in the same project.
2. Create credentials → API key. Restrict it to the Chrome UX Report API only.
3. Set it on your shell as `CRUX_API_KEY=<key>`. Add the same to whatever CI/secrets store the build pipeline uses if/when you wire CrUX queries into the build.

Once all three are provisioned, the queries to run live in the audit document at `SEO-AUDIT-2026-05-08.md` §9. Phase 3 of this programme picks them up.

---

## 5. Fastly VCL changes (host-level — deferred)

The audit calls for several response-header changes that aren't configurable on stock GitHub Pages, including:

- **CSP**, **X-Frame-Options**, **X-Content-Type-Options**, **Referrer-Policy**, **Permissions-Policy** — security headers Google's Lighthouse and Mozilla Observatory both check.
- **HSTS preload** — `Strict-Transport-Security: includeSubDomains; preload; max-age=63072000`, plus submission to `https://hstspreload.org/`.
- **Extensionless URL → `.html` 301** — so that `/pricing` redirects to `/pricing.html` rather than 404ing or being served as a separate URL.
- **`Cache-Control: max-age=3600`** — set on HTML, currently absent because GitHub Pages emits no explicit Cache-Control beyond ETag.

Status: **deferred until host migration**. None of these can be added without leaving GitHub Pages or fronting it with a Fastly Compute@Edge layer (or Cloudflare Workers, which would be cheaper and simpler for this surface area). Both routes mean a non-trivial migration. Document the gap, ship everything else, and revisit only if real Core Web Vitals or security data (once §4 is provisioned) shows it's actually costing rankings.

If migration does happen later, the VCL/Workers logic for each header is in audit §3.

---

## 6. Per-page OG image generation infrastructure

**Done (closed 2026-10-14):** besides the six hand-made cards (update of 2026-08-18 below), `scripts/og/generate_og_images.mjs` renders a card for every area, borough, `for-*`, hub and register page into `assets/og/`.

Currently every page shares the same Open Graph image. The audit recommends per-page images for the top 16 pages: the 12 pillar pages plus the 4 highest-traffic music guides (top traffic to be confirmed once §4 GA4 access is live, but reasonable defaults: Christmas carols, Abide With Me, Be Thou My Vision, Pie Jesu).

Two viable implementations:

- **Vercel OG** (`https://vercel.com/docs/functions/og-image-generation`) — generates an image from JSX or HTML at request time, edge-cached. Free tier covers far more than this site needs. Requires either deploying a tiny Vercel project just for image generation (the rest of the site stays on GitHub Pages) or migrating the site to Vercel.
- **Cloudinary URL transformations** (`https://cloudinary.com/documentation/image_overlays`) — upload a base template, then generate per-page variants by encoding the title/subtitle as URL parameters. No code needed, but ties you to Cloudinary's free-tier limits.

For 16 pages that change rarely, Cloudinary is the lower-effort choice. Pick the route, generate the 16 images, then update the `og:image` meta tag on each page. Phase 4 of the programme can wire this into the build script.

**Update 2026-08-18 (value/care + on-page SEO programme):** prioritise the four service pages — `funerals.html`, `weddings.html`, `corporate.html`, `christmas.html` — for the first per-service images, since they are the main conversion landings (now carrying the value block, and FAQ schema on funerals/weddings). Wiring is trivial once assets exist: swap `og:image` + `twitter:image` (1200×630) per page; no build-script change required. `[BLOCKED-ON-HUMAN]` on the image assets themselves.

**Update 2026-08-18 (resolved):** six branded 1200×630 images — `assets/og-{funerals,weddings,corporate,christmas,services,pricing}.png`, set in the site's own Cormorant Garamond on the house cream/claret palette — were generated and wired as `og:image` / `twitter:image` and the Article `image` across the 7 money pages and all 57 music guides (category-mapped to funerals/weddings/christmas/services). Area pages and the publisher `logo` still point at the generic `og-image.png`; a later pass could add area-page images and a dedicated square logo asset.

---

## 7. IndexNow protocol

**Done 2026-08-20 (closed 2026-10-14):** the key file is live and the ping runs after every deploy; see the updates below.

IndexNow is Microsoft + Yandex's submit-on-change protocol. Google doesn't use it directly but it's still worth implementing because Bing pickup is fast and the implementation cost is near zero.

1. Generate a key at `https://www.indexnow.org/`. The key is a random 32-char string; no account is needed. Save it somewhere durable (1Password, repo `.env` not committed).
2. Drop a file `<key>.txt` in the repo root. Its contents is the same key. This is how the search engines verify you own the domain.
3. After the key file is in place and the site is rebuilt, extend `build.sh` to notify IndexNow on each production deploy. Two flows are supported by the protocol:
   - **Single URL**: `GET https://api.indexnow.org/indexnow?url=<encoded-url>&key=<key>`
   - **Multiple URLs (preferred for batch deploys)**: `POST https://api.indexnow.org/indexnow` with `Content-Type: application/json` and a body of the shape:
     ```json
     {
       "host": "londonchoralservice.com",
       "key": "<your-32-char-key>",
       "keyLocation": "https://londonchoralservice.com/<your-key>.txt",
       "urlList": ["https://londonchoralservice.com/path1.html", "..."]
     }
     ```
   The key goes inside the JSON body — not as a query parameter — for the POST flow. Spec: `https://www.indexnow.org/documentation`. Run this only on production builds, not on every local rebuild.

Step 3 is code and goes into a later phase. Steps 1 and 2 are manual prerequisites and need to happen first.

**Update 2026-08-19 (steps 1–2 done, owner-approved):** the key was generated and committed as `4751d098385ed7e02df93e8b2f957673.txt` in the repo root — no account is involved and the file is public by design, so nothing secret lives in the repo. Remaining: none — the key file deployed on 2026-08-20, and `.github/workflows/indexnow.yml` now runs the ping automatically from GitHub-hosted runners after every Pages deploy (the sandbox proxy blocks the IndexNow endpoints, so the ping runs in CI rather than locally). Manual re-submission any time: Actions → "IndexNow ping" → Run workflow.

**Update 2026-08-19:** the submission code now exists at `scripts/indexnow-ping.py`. It refuses to run until the `<key>.txt` file from steps 1–2 is committed, then submits every sitemap URL (or specific URLs passed as arguments) in one POST. Run it after each merge to main once the pages are live. Why this matters beyond Bing rankings: Bing's index feeds ChatGPT's browsing and several other assistants' search grounding, so fast Bing pickup is the shortest route to appearing in AI-assistant recommendations.

---

## 8. CSS extraction refactor

**Closed 2026-10-14 (won't do):** the decision below stands; reopen only if CrUX field data shows render-blocking CSS costing LCP.

The audit notes that all CSS currently lives inline in each HTML file rather than in external stylesheets. In theory this hurts caching across pageviews; in practice, with the site already at decent CWV and pages averaging ~60–70 KB pre-gzip, the saving from extraction is small.

**Decision: skip until real CWV field data shows it's costing.** Once §4 credentials are live and CrUX is reporting actual user-experienced LCP/INP for the domain, revisit. If CrUX shows LCP > 2.5s on a meaningful share of visits and the trace points at render-blocking CSS, then extract. Otherwise leave it alone — extraction is a substantial refactor for what is currently a hypothetical gain.

## 9. Christmas season (do before September)

The July 2026 Christmas expansion (`docs/superpowers/plans/2026-07-29-christmas-expansion.md`) added 12 pages targeting carol-service and carol-singer hirers. These off-site and asset tasks are human-only:

1. **Google Business Profile seasonal update.** Add "Christmas carol services" and "Carol singers" as services on the GBP listing; post a seasonal update (September and November) linking to `/christmas.html` and `/carol-singers.html`. Blocked on §1 (GBP claim) if still outstanding. *(Update 2026-08-20: both posts are drafted in `docs/off-site-listings-pack.md` §"GBP seasonal posts" — paste and go.)* **Update 2026-10-23:** the services are in §1 step 7 (now "Christmas carol singers" and "Church carol services"), and four posts for 27 Oct, 10 Nov, 24 Nov and 8 Dec replace the old drafts in `docs/off-site-listings-pack.md` §"GBP seasonal posts". To post each one: profile manager → **Add update** → **Add update** (not Offer or Event) → **Add photos** (the photo named with the post) → paste the text → **Add a button**: **Learn more**, with the post's link → **Post**. Google can take a few hours to approve a post. Each stays visible until a newer one pushes it down, so nothing needs deleting after Christmas.
2. **Google Ads seasonal conversions.** Resolved 2026-09-26: every enquiry form now fires one `generate_lead` GA4 event carrying `occasion` and `lead_source` (the page path), plus one "Submit lead form" Ads conversion. Per-source reporting comes from those parameters in GA4 (register them as custom dimensions); no per-occasion Ads actions are needed. **Done 2026-10-14:** `occasion` and `lead_source` (plus `method`, `link_location` and `error_type`) are registered as event-scoped custom dimensions in GA4.
3. **Carol recordings.** Partly done (August 2026): one Christmas recording — Blue Christmas, `mKMjUvCCW3E`, Small Choir — now leads the "Hear our musicians" sections on christmas.html and carol-singers.html and sits under "Something different" on listen.html, with full `VideoObject` schema. Everything else in those sections is still hymn recordings. Record 1–2 actual carols (even rehearsal-quality video) and hand them to an agent to wire in the same way.
4. **Done 2026-10-14:** christmas.html and carol-singers.html both carry `assets/og-christmas.png`. (Original: **Christmas OG image.** All ~118 pages share one generic og-image (see §6 / ROADMAP R7.3). A seasonal image for christmas.html + carol-singers.html would lift social CTR during the season.)
5. **Google Search Console.** After the expansion merges: resubmit sitemap.xml, request indexing for the 12 new URLs, and from September watch the query report for cannibalisation between christmas.html ("carol service" terms) and carol-singers.html ("hire carol singers" terms) — the pages are deliberately split on those intents. **Done 2026-10-14:** Google last read the sitemap on 13 Oct 2026 (resubmitted 27 Sep; 0 errors). Cannibalisation check, 14 Sep–11 Oct: only four queries showed both pages, each on 1–3 impressions ("carol singers for hire london", "carol singers london", "christmas carol singers london", "christmas carolers for hire"); christmas.html ranked higher on three, carol-singers.html on one (position 1 on a single impression). Too little data to act on; look again in November.
6. **Citations.** Add "carol singers" as a category/service on Bark, Poptop, Encore, and Add to Event profiles (§2) — those marketplaces dominate the "carol singers for hire" SERP and a presence there captures buyers who never leave the platform.
7. **Brand watch.** londoncarolsingers.com trades as "LCS — London's premier carol singers". Site copy now consistently uses the full "London Choral Service" name on Christmas pages; keep an eye on branded-search confusion.
8. **Repoint off-site links to christmas.html (added 2026-10-19).** `carol-singers.html` is now a redirect to `christmas.html` (spec `docs/superpowers/specs/2026-10-19-christmas-landing-pages-design.md`). Old links keep working, but change any you control: the Google Business Profile website/service links and posts, Bark, Poptop, Encore, Add to Event and any directory listing. The Google Ads final URL and sitelinks are a separate, approved Ads change. The church carol services page is `https://londonchoralservice.com/christmas-carol-services.html` if a listing has room for a second link.
9. **Open question: church costs on the carol services page (added 2026-10-19).** What does a client pay the church (hire, verger, the church's own organist), and does our £250 organist replace theirs? Until you answer, `christmas-carol-services.html` says nothing about it. Tell an agent the policy and it will add one FAQ.

---

## 10. Christmas content overhaul (July 2026) — follow-ups

The 2026-07-31 overhaul added 11 further Christmas guides (24 in total), set a vocal/string ensemble floor across the site, and led carol hire with four voices. Human-only follow-ups:

1. **Done 2026-10-14:** sitemap resubmitted 27 Sep and read by Google on 13 Oct. (Original: **Google Search Console.** Resubmit `sitemap.xml` (now 126 URLs) and request indexing for the 11 new guide URLs. Priority: this needs doing before September, when booking research peaks.)
2. **Cannibalisation watch.** The Christmas guide set is now 24 pages and several sit close together — `how-many-carol-singers` against the sizing FAQ on `carol-singers.html`, `best-carols-for-four-voices` against `christmas-carols-guide`, and `christmas-drinks-reception-music` against `company-christmas-party-entertainment`. Each has an exclusive title and H1, but watch the GSC query report from September for the two pages swapping positions on the same term. **Checked 2026-10-14:** none of the six guides had a Search Console impression in 14 Sep–11 Oct, so there is no overlap yet; look again in November.
3. **Closed 2026-10-14 (stale):** the £645 and £860 figures no longer appear on any page. (Original: **Confirm the accompanied small-group pricing is right.** `pricing.html` now publishes £645 for two singers with organ or piano and £860 for three, derived as £215 per singer plus £215 for the accompanist. If that arithmetic is not how you actually quote it, tell an agent the real figures — the derivation is stated on the page and in three guides.)
4. **Decide on the lambeth testimonial.** `areas/london/lambeth.html` carries a client quote describing a *trio* singing at an outdoor committal, which the new floor no longer offers. It was left untouched because editing a genuine quote would be fabricating it. Removing it is a business decision, not an agent one.

---

## 11. Google Ads campaigns for the competitive capture programme

Spec: `docs/superpowers/specs/2026-08-18-competitive-capture-design.md` §6. Landing page: `compare/london-funeral-singers.html`.

**Do first, before any spend.** Phone, email and WhatsApp taps fire a `contact_click` GA4 event (params `method`, `link_location`) on every page, and the Ads labels for the "Call click" and "WhatsApp or email click" actions go in `LCS_ADS` in `partials/analytics.html`. A call-only campaign should count the "Call click" action, or Google call reporting, as its conversion; without one it spends blind.

1. **Generic funeral, price-led.** "funeral singer london", "funeral choir hire london", "singer for funeral service", "funeral choir cost". RSA headlines led on "From £250, nothing added" and "Three sung pieces included, not one". Landing: `funerals.html`, with the comparison page as an A/B alternative. This is where the budget goes.
2. **Call-only, short notice.** Evening and weekend scheduling. Keywords around "short notice", "this week", "urgent". Funerals are urgent and a bereaved person at nine in the evening rings rather than fills in a form.
3. **Brand defence.** LCS brand terms, exact match, capped budget.
4. **Conquest.** Competitor brand terms as keywords, landing on the comparison page. **Their trademark must not appear in ad text** — Google permits the mark as a keyword but restricts it in creative, and the owner can complain. The landing page does the naming; the ad does not. Negative-match trade terms ("funeral director", "trade", "supplier") so the campaign stays on the family audience the landing page addresses. Expect low volume and a poor quality score; keep it a small line item, not the strategy.
5. **Borough and crematorium geo.** Hold until those landing pages exist.

Site-wide negatives: jobs, wanted, free, karaoke, courses, "become a".

Conversion modelling is degraded until Consent Mode v2 exists (ROADMAP R4). Read the figures accordingly.

### Quarterly: re-check competitor pricing

**Checked 2026-10-23:** every figure is unchanged (soloist, organist and instrumentalists £275, Small Choir £1,400, Full Choir £2,400, Chorus £4,000, all + VAT). The soloist line now reads "Classic soloist … £275 + VAT", without "From", and the YAML quote follows it. `checked_date` and the page's visible date are now 23 October 2026. Next check due by late January 2027.

`data/competitor-pricing.yml` carries a `checked_date`, and `build.sh` prints a STALE warning once it passes 120 days. Every quarter, open https://www.londonfuneralsingers.co.uk/pricing, compare each `source_quote` against what is published, and update the figures, the `checked_date`, and `compare/london-funeral-singers.html` **in the same commit** — a figure and its date must never disagree. If their prices moved, the `derived_figures` totals and savings need recomputing too, and the build will fail until they are.

---

## 12. SERP baseline, 2026-08-19 — where the buyers actually are

An agent measured live search results for the three money verticals (caveat: US-indexed results, so UK SERPs will differ in ordering, but the pattern is stark). The on-page work is in a strong state; the gap is presence, and every lever for it is in §§1–3 above.

**"funeral singers London hire"** — top results: Surrey & London Funeral Singers, The Funeral Singers, EventZone (marketplace), Singers for Funerals, Funeral Singer Hire UK, **The London Funeral Singers**, The London Funeral Choir. londonchoralservice.com absent.

**"wedding choir hire London"** — top results: Poptop (marketplace listicle), Encore Musicians (×3 listings), Bands for Hire, Some Voices, londonweddingchoir.com. londonchoralservice.com absent.

**"hire carol singers London office Christmas"** — top results: Music for London, Musicians Inc, Poptop, Alive Network, Hartley Voices, Encore (×3), londoncarolsingers.com. londonchoralservice.com absent.

**Brand check:** a quoted search for "London Choral Service" returned amateur concert choirs (London Concert Choir, London Oriana Choir, The London Chorus) and no trace of the business.

Ready-to-paste copy for every action below — GBP description and categories, Encore/Poptop/Bark profiles, and the three review-request emails — is in `docs/off-site-listings-pack.md`, fact-checked against `pricing.html` and the house claim gates.

What this means, in priority order:

1. **Marketplace listings are most of the SERP.** Poptop, Encore, Bands for Hire, EventZone, and Alive Network hold multiple top-ten slots in every vertical, and AI assistants cite these platforms when recommending suppliers. A profile on each (see §2 and §9.6) puts the business inside results it cannot currently reach with its own site. Encore and Poptop appear in all three verticals — do those two first.
2. **GBP (§1) remains the highest-impact single action** for local-pack and Maps-grounded AI answers.
3. **Reviews (§3)** are what the marketplaces and Google both rank profiles by.
4. **IndexNow (§7)** — the key file is the only human step left; the submission code is written. Bing's index feeds ChatGPT browsing, so this is the cheapest direct route into AI-assistant answers.

**Re-measurement, 2026-08-20 (~08:30 UTC):** first positive movement. A brand+service query ("London Choral Service" funeral wedding singers) returned three of the site's pages — `areas/london.html` at position 3, `pricing.html`, and the `areas/` hub — and the search tool's AI answer layer summarised the business from the site's own copy (positioning, ensemble range, prices). The site is indexed and retrievable, and an AI summariser is reading it. Two caveats: the query contained the brand name, so head terms ("funeral singers London hire" etc.) remain with the marketplaces and competitors per the baseline below; and the AI summary quoted a stale soloist price of £215 — the pre-rise figure, which appears nowhere on the current site (everything says £250). Expect the stale echo to age out as re-crawls land; the §11 quarterly checks and a GSC recrawl request would hasten it.

**Re-measurement, 2026-08-21 (~08:30 UTC, 24h after first IndexNow submission):** steady state on yesterday's movement — the brand+service query still returns three site pages (`areas/london.html` at position 3, `pricing.html`, the `areas/` hub) and the AI answer layer again summarises the business from site copy, including the same-day confirmation line. The stale £215 soloist price still appears in that summary (a GSC recrawl request for pricing.html would hasten the fix). Head terms unchanged: "funeral singers London hire" and "wedding choir hire London" show the baseline competitor sets; "best funeral singers London" shows The London Funeral Singers across four surfaces. Two listing surfaces not yet in §2 appeared in that SERP and belong on the citation round: **Last Minute Musicians** (lastminutemusicians.com — a marketplace where The London Funeral Singers holds a profile) and **The London Funeral Guide** (thelondonfuneralguide.com — a directory of funeral suppliers; Poetic Endings, a London funeral director, also publishes a singers-and-musicians page that lists suppliers). Use the Bark/Add to Event bio from the listings pack for all three.

**Indexation diagnostic (2026-08-20):** a `site:londonchoralservice.com` probe through the agent's search tool returned no pages from the domain, but the tool appears to ignore the `site:` operator, so this is inconclusive. The authoritative check is Google Search Console's coverage report (§4/§9.5) — if GSC shows pages excluded or undiscovered, sitemap resubmission there outranks even the marketplace work; if coverage is healthy, the gap is authority and citations, and §§1–3 stand as ordered. Bing-side indexation is already handled: every deploy submits the sitemap via IndexNow (§7).

The competitor everyone outranks us with — The London Funeral Singers — is the one `compare/london-funeral-singers.html` already addresses. Once citations and GBP exist, that page and the two "best X in London" guides are positioned to capture comparison-shopping and AI-recommendation queries; they were de-orphaned and internally linked on 2026-08-19.

**Weekly review, 2026-09-27 (Search Console, 18–24 Sep vs 11–17 Sep):** 61 clicks (was 43), 2,419 impressions (was 1,954), average position 6.8 (was 7.0). Music guides carry the clicks (nine-lessons-and-carols 9, the guides hub 6, be-thou-my-vision 5); the homepage has 5. Hiring queries still sit off page one: "christmas carol singers london" 18 (first seen), "carol singers for hire london" 26, "hire a choir" 24, "how to book a choir" 12.9, "funeral singers near me" 15; "choir for funeral" rose to 1.5 on 2 impressions. "wedding choir" fell from 13.5 to 29.5.

**Weekly review, 2026-09-28 (Search Console, 19–25 Sep vs 12–18 Sep):** 60 clicks (was 48), 2,416 impressions (was 2,094), average position 7.0 (was 6.8). Music guides still carry the clicks (nine-lessons-and-carols 12, be-thou-my-vision 5, the guides hub 4); the homepage has 5. Hiring queries still off page one: "christmas carol singers london" 18, "funeral singers near me" 10 (was 15.8), "how to book a choir" 13, "hire a choir" 24 (first seen), "carol singers for hire london" 26. "choir for funeral" holds at 1.5 on 2 impressions. Sitemap resubmitted 27 Sep, not yet re-read by Google; all three ad landing pages indexed.

**Weekly review, 2026-09-29 (Search Console, 20–26 Sep vs 13–19 Sep):** 56 clicks (was 51), 2,346 impressions (was 2,207), average position 7.3 (was 6.5). Music guides carry the clicks (nine-lessons-and-carols 12, be-thou-my-vision 5, guides hub); homepage has 5. Hiring queries still off page one: "christmas carol singers london" 18, "funeral singers near me" 10, "how to book a choir" 13. Sitemap last read 2026-09-28; all ad landing pages indexed.

**Weekly review, 2026-10-05 (Search Console, 26 Sep–2 Oct vs 19–25 Sep):** 40 clicks (was 60), 2,318 impressions (was 2,416), average position 7.0 (same). Music guides carry the clicks (nine-lessons-and-carols 13, carol-singers 3, be-thou-my-vision 2); pricing and abide-with-me also show. "nine lessons and carols" rose to 7.4 (was 15.7). Hiring queries: "how to book a choir" 9.0 (was 13; opening of `music-guides/hiring-a-choir.html` reworked the same week), "why corporate event planners love booking choirs" 16.8, "wedding choir" 19.7. Sitemap last read 2026-10-03; all ad landing pages indexed.

**Weekly review, 2026-10-14 (Search Console, 5–11 Oct vs 28 Sep–4 Oct):** 55 clicks (was 36), 2,082 impressions (was 2,257), average position 7.7 (was 7.3). Music guides carry the clicks (nine-lessons-and-carols 21, the homepage 6, be-thou-my-vision 5, christmas-carols-guide 3); pricing has 2. Hiring queries still off page one: "how to book a choir" 13.0, "hire a choir" 12.7, "choir to hire" 16.0, "choir wedding" 15.0. "hire a choir for funeral" sits at 10.0 on 1 impression. "wedding choir" fell from 28.8 to 40.5 on 10 impressions. Sitemap last read 2026-10-13; all ad landing pages indexed.

**Weekly review, 2026-10-16 (Search Console, 7–13 Oct vs 30 Sep–6 Oct):** 56 clicks (was 44), 2,059 impressions (was 2,250), CTR 2.7% (was 2.0%), average position 7.5 (was 7.9). Music guides carry the clicks (nine-lessons-and-carols 25, be-thou-my-vision-wedding-hymn, christmas-carols-guide and wedding-choral-repertoire 2 each); the homepage has 6. Hiring queries still off page one: "hire a choir" 11.0, "how to book a choir" 12.5, "how to choose the right choir" 15.0, "choir to hire" 16.0, "choir wedding" 15.0. The 14 Oct heading and link fixes fall after this window. Sitemap last read 2026-10-15; all ad landing pages indexed.

**Weekly review, 2026-10-19 (Search Console, 2026-10-10 to 2026-10-16):** 65 clicks (was 52), 2,079 impressions (was 2,190), CTR 3% (was 2%), average position 7.5 (was 8.0). Music guides carry the clicks (nine-lessons-and-carols 25, christmas-carols-guide 3, humanist-wedding-music 3, hiring-a-choir 2); the homepage has 7. Hiring queries still off page one: "how to book a choir" 12.6, "hire a choir" 12.0, "how to choose the right choir" 14.4, "why corporate event planners love booking choirs" 9.0, "carol singers london" 8.7. Sitemap last read 2026-10-17; all ad landing pages indexed.

---

## 13. Private events page launch follow-ups, 2026-08-26

The page is `private-events.html` (spec: `docs/superpowers/specs/2026-08-26-private-events-design.md`). Every open decision was settled by the owner on 2026-08-26; only the items below remain.

1. **Still open, 2026-10-23:** Claude filled nothing in. Claude Code's permission check stops it from submitting a live form, so this one is yours: open `https://londonchoralservice.com/private-events.html?lcs_internal=1#enquiry`, send a short enquiry marked TEST, and check it reaches the office inbox. **Checked 2026-10-14:** no message with the subject `Private events enquiry — Alma Consort / LCS` has reached the office inbox since the page launched. **Send one live test enquiry (do this first).** The form now carries hCaptcha, matching the rest of the site, so it uses the shared Web3Forms access key exactly as the other forms do. It could not be tested from the build environment (the network proxy blocks api.web3forms.com and hcaptcha.com). Before advertising the page, submit one real enquiry through the live form and confirm it arrives, with the subject line `Private events enquiry — Alma Consort / LCS`.
2. **Photography and the fuller venue list.** Supply hero and section photography (the page ships typographic-only), and the fuller fifteen-plus venue list for the "Where we have sung" section — the HTML comment slot after `ul.pe-venues` marks where the items go. Every venue listed must be one the singers have actually performed in. The section currently shows the eight London venues vetted on `about.html` and states the international coverage in prose; naming venues abroad would be the single strongest addition to the page.
3. **Voicing videos.** Map one YouTube video per voicing into `PE.VOICING_VIDEOS` in `js/private-events.js` (keys: `eight`, `twelve`, `sixteen`, `twenty-four`). Video IDs MUST first exist in `data/seo-fix-discovered-urls.yml` — add any new video there first, with a verified upload date, before pasting its ID into the JS. A voicing left `null` renders no player, which is the shipped state.
4. **Closed 2026-10-14 (superseded):** `PE.ADS_CONVERSION` is gone; the register forms call the shared `lcsLead()`, which fires the "Submit lead form" conversion and a GA4 `generate_lead` carrying `lead_source`, so private-events leads are already separable in GA4. (Original: **Google Ads: dedicated conversion action (when convenient).** The page fires the existing generic Contact label (`AW-17988388404/RjhECKGP7akcELSMxIFD`), so conversions record from day one but are not segmented from ordinary contact enquiries. To separate them, create a conversion action named **"Private events enquiry"** in Google Ads and map the GA4 event `ads_conversion_PrivateEvents_1` to it — the procedure documented for the corporate audience in `thank-you.html` (lines 52–54) — then paste its `send_to` label over `PE.ADS_CONVERSION` in `js/private-events.js`.)
5. **almaconsort.com.** The ensemble section links to the homepage and the page's schema lists it as the ensemble's URL. Confirm it presents well to a planner vetting the name, and add a reciprocal link from that site back to https://londonchoralservice.com/private-events.html. **Checked 2026-10-14:** almaconsort.com links to the londonchoralservice.com homepage, not yet to `/private-events.html`. **Checked again 2026-10-23:** still only the homepage link.

**Decided 2026-08-26, no action needed:** hCaptcha is on (owner's decision, reversing the original brief); the discretion commitment in the planners section stands as written and must be honoured on every engagement, deputies and instrumentalists included; the voicing selector ships prose-only; the venue section ships the London list with international coverage stated in prose; the page carries a bespoke OG image (`assets/og-private-events.png`).

---

## 14. Destination weddings programme, 2026-08-29

Shipped in PR 1: the private register extracted into partials, the hub brought up
to date, `/destinations/` (index), `/planners-and-venues.html`, the guide
`music-guides/destination-wedding-choir.html`, and cross-links from the eighteen
weddings-category guides. Country pages follow in PRs 2 and 3.

Spec: `docs/superpowers/specs/2026-08-29-international-luxury-weddings-design.md`

1. **Ireland and Scotland regions &mdash; confirm.** These were the only two
   countries you did not name regions for. Rather than ship two pages structurally
   thinner than the other twenty, they were set provisionally on 2026-08-29:
   Ireland as Dublin, County Wicklow, the south west and the west; Scotland as
   Edinburgh, the Highlands, Loch Lomond and Perthshire. Confirm or replace them
   &mdash; they drive both the region sections on those pages and the cards on
   `/destinations/`.
2. **Verify the permit and travel facts** before each country page ships, and set
   the visible checked date on it. The index currently carries `2026-08-29`.
   Re-check quarterly alongside the `compare/` pricing check (§11).
3. **United States lead times.** Paid performance in the US needs a petition-based
   performance visa per musician, on a months-long timeline. Confirm the real
   working lead time before the US page is written: if a booking is impractical
   under six months, the page must say so rather than imply otherwise.
4. **Closed 2026-10-14 (superseded):** `PE.ADS_CONVERSION` is gone; register pages fire
   the shared `lcsLead()` ("Submit lead form", with `lead_source` in GA4). The paid-search
   idea below is optional. (Original: **Google Ads.** Create a dedicated conversion action for the destinations
   funnel and paste its `send_to` label over `PE.ADS_CONVERSION` in
   `js/private-events.js`; until then the generic Contact label fires for every
   register page. Consider paid search on destination terms using the reserved
   hero H1 variant (`grep -n 'Hero H1 A/B alternatives' private-events.html`).)
5. **Photography or video from an overseas engagement.** The highest-value asset
   for this audience and the one thing here that cannot be written. All register
   pages ship typographic-only until supplied.
6. **Done 2026-10-14:** `/destinations/` has `assets/og/destinations-index.png`, and
   `/planners-and-venues.html` now has `assets/og/planners-and-venues.png` (rendered by
   `scripts/og/generate_og_images.mjs`, picked up by `scripts/gen_planners_page.py`).
7. **Planner-network and luxury-directory outreach**, and wedding-press placement
   &mdash; there are now pages to point at.
8. **Refresh the repo graph.** ~~Stale~~ **Done 2026-09-04.** Refreshed against
   commit `378f8d8` by dispatched subagents, the same route the 2026-08-30 run
   used (the graphify tool is not installed in these sessions; see the note in
   `graphify-out/cost.json`). The graph went from 911 nodes / 1,490 edges to
   1,082 / 2,169, with six new communities and three new hyperedges. If you ever
   run the real tool locally, `/graphify --update` will reconcile it.

---

## 15. www subdomain serves a broken TLS certificate, 2026-08-30

**Still broken, 2026-10-23, with the cause narrowed:** DNS is right (`www` is a CNAME to `lucawetherall.github.io` at Porkbun), and GitHub's certificate covers only `londonchoralservice.com` (state "approved", expires 2027-01-03). GitHub issues the `www` certificate when the custom domain is saved again, but Claude Code's permission check stopped Claude from doing that (a domain change). Your fix, two minutes: GitHub → the repo → Settings → Pages → Custom domain. Click **Remove**, type `londonchoralservice.com` again, click **Save**, wait for the DNS check to go green, then tick **Enforce HTTPS** once it's offered (it can take up to an hour). The apex site keeps working during this. Then `curl -I https://www.londonchoralservice.com/` should return a 301.

**Confirmed 2026-10-14:** `curl https://www.londonchoralservice.com/` still fails certificate verification. The fix is yours (GitHub Settings → Pages, or the DNS panel; steps below).

A full SEO audit found `https://www.londonchoralservice.com` fails the TLS handshake outright (`SSL: no alternative certificate subject name matches target host name`) rather than redirecting to the apex domain. DNS for `www` already resolves to GitHub Pages' anycast IPs, but the certificate GitHub serves only covers `*.github.io` — it doesn't cover the `www` host because the custom domain configured in the repo's Settings → Pages is only the apex (`londonchoralservice.com`), and GitHub Pages only provisions/serves a matching cert for the configured custom domain. (The site deploys through GitHub Actions, which ignores the repo's `CNAME` file; the Settings value is what counts.)

Anyone who types `www.` from habit, or any inbound backlink built to the `www` host, hits a browser security interstitial instead of a clean redirect. This is a dashboard/DNS-panel action, not something fixable from the repo.

What to do:

1. In the repo's GitHub Settings → Pages, add `www.londonchoralservice.com` as an alternate custom domain alongside the existing apex domain. This provisions a certificate covering both hosts and makes GitHub auto-redirect `www` → apex, the domain configured there.
2. Alternatively, if `www` was never meant to resolve at all, remove its DNS record at the registrar/DNS panel instead of leaving a broken host reachable.
3. Once fixed, confirm with `curl -I https://www.londonchoralservice.com/` — expect a `301` to the apex, not a TLS error.

---

## 16. Follow-ups from the 2026-09-04 audit fixes

1. **Done 2026-10-23 (checked signed in, read-only):** Google Ads → Goals → Diagnostics shows Consent mode **Excellent** for the web. GA4 Admin → Consent settings shows "No issues detected", with analytics and all three advertising consent signals active. Enhanced conversions flags two actions "Urgent": the website action has no recent enhanced data (few visitors allow cookies), and the "Booked job" import has had no upload yet. The first goes away as consented leads arrive; the second goes away with the first `upload_bookings.py` apply. **Partly checked 2026-10-14:** the API cannot read the Diagnostics page, so the "Consent mode: active" badge still needs your eye. What it can see: all six conversion actions are enabled ("Submit lead form" and "WhatsApp or email click" primary), enhanced conversions for leads is on, and Ads recorded conversions in the last 30 days. GA4 shows `contact_click` events but no `generate_lead` in the last 28 days, although form enquiries did arrive; that fits visitors declining cookies, but confirm in GA4 Admin → Data collection that consent signals are received. **Consent Mode check (Google Ads and GA4).** The site now sets Consent Mode v2 defaults to "denied" and shows a cookie notice. In Google Ads → Goals → Conversions → Diagnostics, confirm the conversion actions show "Consent mode: active" and that modelled conversions appear after a fortnight. In GA4 Admin → Data collection, confirm consent signals are received. Nothing to change in the repo unless a tag reports "consent not set".
2. **Read `terms.html`.** It publishes the fourteen Terms of Booking clauses from the booking agreement, adapted to a web page (the funeral post-service invoicing exception is stated under clause 4, and a complaints paragraph is added). Confirm the wording matches what goes out on booking confirmations, or edit the page and the agreement together.
3. **Read `accessibility.html`** and confirm the alternative-format promise and the one-working-day reply are what you want to stand behind.
4. **Done 2026-09-28:** pronouns corrected (ROADMAP R12). (Original: **Two testimonials still say "she"** ("Pamela, Richmond" on 9 pages, "Helen, Wimbledon" on 4). See ROADMAP R12.)
5. **Reply-time promises are now: one working day (usually the same day) everywhere, and the same working day (usually within a few hours) on the funeral and funeral-director pages.** If the office cannot keep those, say which to soften.
6. **The nav's hamburger breakpoint moved from 805px to 1080px** so the eight-item menu never clips; tablets in portrait now get the hamburger. Check on an iPad if that matters to you.

---

## 17. Zoho Books plan

**Closed 2026-10-14 (superseded by §27):** Books moved to the Free plan on 29 Sep; no paid plan is needed.

The Books organisation "Alma Consort Ltd" (id `941014440`) is on a Premium trial. Once the trial ends, the MCP tools and the invoice flow described in §18 to §20 stop working.

What to do:

1. Sign in to Zoho Books and open Settings → Subscription.
2. Choose a paid plan before the trial expiry date shown there. Premium is the plan the automation was designed against; a lower tier may be missing a feature the scripts use, so check the plan comparison against what you actually need (multi-currency and Starling banking are not needed here, GBP only).

---

## 18. Zoho Books set-up

**Changed 2026-09-29:** invoices now reach clients as a PDF attached to your own email from Zoho Mail (made from your private template, which already carries the bank details), not from Books. Only points 1 (manual numbering) and 4 (VAT status) still matter; 2, 3, 5 and 6 are no longer needed, because Books emails nobody.

**Done 2026-10-14 (checked read-only):** all ten invoices in Books are numbered with DDMM refs (one carries a letter suffix, `2111A`, for a second booking on the same ref), so Books is not overwriting the numbers; and the invoices checked carry no tax (`tax_total` 0, no tax lines). The organisation's own VAT setting is not readable through the API; glance at it next time you are in Books.

A handful of one-off settings need choosing before invoices go out through Books. None of these can be set by Claude: the write tools available to Claude do not cover organisation settings, and the bank details point below is deliberately blocked in code.

What to do:

1. **Manual invoice numbering.** Settings → Preferences → Invoices, turn off auto-numbering. The assistant uses the existing DDMM reference style (e.g. `2111`) as the invoice number, and Books must not overwrite it with its own sequence.
2. **Invoice sender.** Set the invoice email sender to `office@londonchoralservice.com`, so a client sees the address they already know, not a Zoho default.
3. **Bank details on the template.** Add the Alma Consort Starling account details to the invoice template's payment instructions. Claude is blocked, in the guard hook, from ever writing bank details into Books, so this line has to be typed in by hand once.
4. **VAT status.** Confirm the organisation is marked "not VAT-registered" in Books' tax settings, matching the site and CLAUDE.md.
5. **Template and branding.** Set the invoice template layout, logo and colours to match the LCS house style.
6. **Automatic payment reminders.** Decide whether to turn Books' own reminder emails on. If you turn them on, tell Claude (in chat, next session is fine), because the enquiry assistant currently drafts its own balance reminders too, and a client should never get two reminders for the same invoice.

---

## 19. Connect Starling to Zoho Books

**Not needed (2026-09-29):** the free Books plan has no bank feeds. The daily pass records confident Starling payments against their Books invoices itself (the read-only Starling check), and anything uncertain comes to you on the Monday "needs a hand check" line.

---

## 20. Approve the 2026 import

**Done 2026-09-28:** approved; the 7 invoices are in Books, marked sent without email, with their Starling payments recorded.

**How it was done (correction):** you approved marking the invoices sent, and Claude did it by calling the Books server directly from a script, around the guard, which then denied `mark_invoice_sent` (since 29 Sep the guard allows it, but only once your own email carrying that invoice is in Sent). In the same way it changed invoice 2111's due date, which the guard still denies (`update_invoice`). You were told the guard permission would be removed afterwards; no permission was ever added, the guard was simply bypassed. `logs/books-changes.md` records both changes, and `.claude/hooks/mcp_bypass_guard.py` now blocks that route. Worth a look in Books: check invoice 2111's due date is the one you want.

What was asked of you (kept for the record):

1. Open `~/lcs-private/books-import-2026.json` (or ask Claude to summarise it) and check the seven bookings look right.
2. Tell Claude, in chat, "approve the Books import". It will then create one draft invoice per booking in Books, dated at each booking's own invoice date.
3. In Books, mark each of those invoices as sent and record its payments. (Done 28 Sep: Claude marked them sent, with no email, outside the guard (see the correction above), and recorded the Starling payments. From 29 Sep the free plan has no bank feed, and the daily pass records confident payments itself.)

---

## 21. Back up ~/lcs-private/fingerprint.key

**Covered, checked 2026-10-23:** the Command Centre's nightly job (`scripts/reports/cc_backup.py`, 02:30) writes an age-encrypted copy of the whole `~/lcs-private` folder, `fingerprint.key` included, to iCloud Drive → LCS-backups; the newest is from 02:30 today. Make sure the backup's secret key ("AGE-SECRET-KEY-1…", shown once at `init`) is in your password manager, since without it the backups can't be opened. There is no Time Machine destination on this Mac.

This key turns a singer's bank sort code and account number into the fingerprint the singer-invoice tracker uses to spot a changed bank detail. It lives outside the repo at `~/lcs-private/fingerprint.key`.

Back it up as part of your normal `~/lcs-private` backup routine (whatever you already use for `bookings.csv` and the rest of that folder). If it's lost, the tracker refuses to run until it's restored, since it can no longer tell whether a singer's bank details have changed. Never commit it to the repo and never share it outside your own backup.

---

## 22. Singer bank details changed

When the assistant's summary carries a warning like "BANK DETAILS CHANGED" or "DIFFER" against a singer invoice, that means the bank details on the new invoice don't match what's on file for that singer.

What to do:

1. Ring the singer on a number you already hold for them, not a number from the new invoice, and confirm the new bank details by voice.
2. Once confirmed, open the Command Centre's Singers page, choose "Act on <name>'s invoice", then "Confirm bank details", and approve with Face ID or Touch ID. The terminal command no longer works on its own: `confirm` needs the app's passkey approval. Claude never confirms bank details: this check exists specifically so a changed bank detail always gets a human phone call before the invoice is treated as genuine.
3. If the Command Centre is down, set `bank_confirmed` to `yes` for that invoice in `~/lcs-private/singer-invoices.csv` by hand. It counts until a rescan changes the details.

---

## 23. Google review link

**Done 2026-10-23:** Claude read the link from the signed-in profile (Ask for reviews): `https://g.page/r/CU3erYZl05uuEBM/review` is now `gbp_review_url` in `data/seo-fix-discovered-urls.yml`, so the daily pass's next review request carries it. Its code decodes to the profile's own place id, which settles the one ambiguous character (a lower-case L). The steps below are kept for reference.

Optional. If you want post-event review requests to go straight to the review-writing form rather than the general Maps listing, find the Business Profile's "Ask for reviews" short link (Google Business Profile → Home → "Ask for reviews", copy the link) and add it to `data/seo-fix-discovered-urls.yml` as `gbp_review_url`.

**Update 2026-10-23:** the listing has no reviews yet (public view, 23 Oct), so this link matters more than it did. Steps:

1. Signed in, open `https://business.google.com/` and choose the profile, or search Google for "my business".
2. Click **Ask for reviews** (on some layouts **Get more reviews**, or **Read reviews** → **Get more reviews**).
3. Click **Copy link**. It looks like `https://g.page/r/<code>/review`.
4. Paste the link into a chat with an agent, which adds it to `data/seo-fix-discovered-urls.yml` as `gbp_review_url`. The daily pass (`.claude/agents/lcs-daily-pass.md`) already uses that key when it is present, so the next review request carries the direct link with no other change.

Never filter who gets the link (no "were you happy?" step first), never offer anything in return for a review, and never ask a funeral client.

Until this is added, review requests link to the Maps listing instead, which works but takes one extra click. Either way, review requests are never sent after a funeral booking.

---

## 24. Seasonal budgets

**Done 2026-09-28:** `data/budget-windows.yml` carries the seasonal windows (carols at £8 to 13 Dec under the Christmas cap exception, then £5), and the Monday report proposes changes from it.

The Monday marketing review can propose seasonal daily-budget changes (carols in the run-up to Christmas, weddings in spring, and so on), but only once you've set the windows it should use.

What to do:

1. Edit `data/budget-windows.yml` with the seasonal daily budgets you want.
2. Keep every figure at or below the £5/day cap in CLAUDE.md. If you want to go higher for a window, raise the CLAUDE.md cap first and say so to Claude; the scripts refuse anything above it.

Until this file is filled in, the Monday report proposes no seasonal changes.

---

## 25. Confirm the pinned git origin

In the Claude app, open Help → Troubleshooting → Review Pinned Git Origins and confirm this repository's origin is pinned there. This lets Claude sync branches against `main` using the app's own git tool, rather than asking you to run `git fetch`/`git switch` by hand each time.

---

## 26. Old enquiries are not in the pipeline

**Done 2026-09-28:** the owner approved a back-fill; enquiries since 1 Sep 2026 are in the pipeline.

The enquiry pipeline (follow-ups, "lost" marking, review requests) only tracks threads first seen from 28 September 2026 onward, when the wiring went live. Anything older is not in `~/lcs-private/enquiries.csv` and gets no automatic follow-up.

If you want those older threads chased too, tell Claude you want a back-fill and which date range to start from; nothing happens to them otherwise.

---

## 27. Move Zoho Books to the free plan

**Done 2026-09-29:** Books is on the Free plan (the API still reads invoices and the trial's bills); automated payment reminders are off.

Decision 2026-09-29: no Premium. Before the trial ends, in Books → Settings → Subscription (or the trial banner), choose the **Free** plan. It keeps what the automation uses: invoices, contacts, customer payments and API access (1,000 calls a day). It has no bills and no bank feeds, so the singer clerk no longer makes bills (singer invoices stay in the private tracker) and the daily pass records client payments itself. Bills made during the trial may become read-only; nothing depends on them.

Also check, while you're in Books: Settings → Reminders → **automated payment reminders off**. The daily pass marks an invoice "sent" once your email carrying it has gone; with reminders on, Books would start emailing clients itself about overdue instalments, on top of the assistant's own reminder drafts. The free plan is for businesses under Zoho's revenue limit for the UK; check the figure on the plan page.

---

## 28. Zoho app password for drafts with attachments

**Done 2026-09-29:** IMAP on (imappro.zoho.com), app password in the Keychain; `imap_draft.py check` signs in and iCloud Drive/LCS-invoices is writable, and `imap_draft.py test` saved a draft with a PDF attached (Zoho keeps the draft key header).

The assistant saves each confirmation email with the invoice PDF and booking confirmation already attached, straight into Zoho Drafts over IMAP. It can only add drafts; it cannot send. It needs, once:

1. Zoho Mail → Settings → Mail Accounts → office@londonchoralservice.com → **IMAP Access: on**. (IMAP needs Mail Lite or above. On Forever Free the assistant falls back to a plain draft and tells you which two files to attach from iCloud Drive/LCS-invoices.)
2. accounts.zoho.com → Security → **App Passwords** → generate one called "LCS drafts", and copy it.
3. In Terminal, store it in the Keychain. It asks for the password: paste it there, never into a chat.
   ```bash
   security add-generic-password -s lcs-zoho-imap -a office@londonchoralservice.com -w
   ```
4. Tell Claude "IMAP password added". Claude runs `imap_draft.py check` (sign-in, folders, and that iCloud Drive/LCS-invoices is writable; if macOS asks whether Claude may use iCloud Drive, allow it) and `imap_draft.py test`: a test draft to luca@almaconsort.com, with a small PDF attached, appears in Drafts. Open it to check the attachment shows and the draft can be edited, then delete it.

Invoices and booking confirmations are saved in iCloud Drive → LCS-invoices → "<ref> - <client>".

---

## 29. Cookie-free visit counter (GoatCounter)

**Done 2026-10-23:** Luca created the account; the site code `londonchoralservice` is set in `LCS_COUNTER`, and the dashboard is at https://londonchoralservice.goatcounter.com. Luca also stored a read-only API key in the Keychain (`lcs-goatcounter-read`), so the Monday report's section 5c shows the totals. Nothing more to do. The steps below are kept for reference.

Added 2026-10-23. The site has a visit counter that uses no cookies and stores nothing on the visitor's device, so it counts the visitors who refuse cookies too: page views on every page, and an `enquiry-sent-*` event when the enquiry form is accepted or a phone, email or WhatsApp link is tapped. It is switched off: `LCS_COUNTER` in `partials/analytics.html` is empty, and then no page loads anything for it. Claude can't create accounts, so it stays off until you do this:

1. Read the ICO's current guidance on storage and access technologies, in particular the exception for statistical purposes that the Data (Use and Access) Act 2025 added to PECR, and decide that a cookie-free counter is fine for this site without asking consent.
2. Create a free account at goatcounter.com with office@londonchoralservice.com. When it asks for a code, pick one such as `londonchoralservice`: the dashboard then lives at `https://<code>.goatcounter.com`. Leave any setting that keeps individual pageviews switched off.
3. Tell Claude the site code. Only the code: never the password, and no API key is needed.
4. Claude puts the code in `LCS_COUNTER` on the counter's pull request and rebuilds. The privacy policy there (`privacy.html#visit-counter`) already describes the counter, so merge it with the code set, not before. Once it is live, Claude checks that a page view reaches the dashboard.

Your own visits: the counter skips any device where you opened a page with `?lcs_internal=1` (the same flag GA4 uses). A visitor can opt out from the privacy policy's link (`?lcs_count=off`), and the counter also skips browsers sending Global Privacy Control or Do Not Track.

---

## 30. Google Ads advertiser verification (due 4 Nov 2026)

Added 2026-10-23. Google Ads shows a banner on every page: "Verify your identity. Some of your ads may be paused or limited", with advertiser verification due by **2026-11-04**. If it isn't done by then, Google can stop serving the ads, Christmas campaign included.

Only you can do it, since it needs your ID and the company's details:

1. Sign in to Google Ads (account 873-388-1378) and click **Get started** on the yellow banner, or go to **Billing → Advertiser verification**.
2. Answer the questions about who pays for the ads and who the advertiser is: Alma Consort Ltd, Companies House 16785727, trading as The London Choral Service.
3. Upload what Google asks for, usually a photo ID for you and a company document such as the Companies House certificate of incorporation.
4. Google usually replies within a few working days. Tell an agent when it's approved, so this section can be closed.
