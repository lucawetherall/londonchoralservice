# Manual actions required — SEO audit fix programme

These items came out of the 2026-05-08 SEO audit but cannot be implemented in code from this repo. Each one needs a human in front of the relevant dashboard, account, or hosting console. Work through them in the order given; later phases of the programme assume some of these are done.

---

## 1. Google Business Profile claim and category audit

The site already references a Google Maps presence — `index.html` carries `sameAs: ["https://share.google/HRgq38OubHmj3Zz9v"]` in the Organization schema. That's a share-style short link, not the canonical place URL, and the audit flags it as the single highest-impact local-SEO blocker.

**Update 2026-08-20 (steps 5–7 done):** the owner supplied the full Maps URL; the canonical cid form (`https://www.google.com/maps?cid=12581882416994311757`, derived from the URL's ftid) now replaces the share.google short link in index.html's Organization sameAs, and `data/seo-fix-discovered-urls.yml` is updated. The Maps listing is anchored as "The London Choral Service, Maidenhead" — whatever address GBP shows is the NAP master for §2. **Remaining in §1: the category audit only (steps 3–4).**

**Update 2026-08-19:** the owner reports the listing has been claimed.

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

- **`luca_wetherall_orcid`** — if Luca has an ORCID, add it to `data/seo-fix-discovered-urls.yml` and rerun the schema sweep on `about.html` to populate `Person.sameAs`.
- **`lcs_linkedin_company`** — if a LinkedIn company page exists for The London Choral Service or Alma Consort, add its URL to the YAML and rerun the schema sweep on `index.html` to populate `Organization.sameAs`.
- **`videos[*].upload_date`** + **`videos[*].duration`** — five YouTube videos' metadata still can't be resolved automatically (consent gate on four; the egress proxy blocks YouTube outright for `ZVSQ2Ts4GZE`, the Anima Christi recording added 2026-08-15). Open each video on YouTube manually, capture the upload date (YYYY-MM-DD) and the duration (convert to ISO 8601, e.g. 3:42 → `PT3M42S`), update the YAML, and rerun the VideoObject sweep on `pricing.html`, `listen.html`, and the two `music-guides/anima-christi-*` pages. The fifth video, `mKMjUvCCW3E`, was resolved by the user on 2026-08-15 and its `VideoObject` now ships on `listen.html`, `christmas.html`, and `carol-singers.html`.

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

NAP consistency is the load-bearing detail. Whatever address and phone format you use on GBP, use the same one verbatim everywhere else. Different formats split the local-SEO citation graph and Google treats the variants as separate entities.

When you've done the round, run a free citation scan against the homepage URL at `https://www.brightlocal.com/free-business-listings-scan/`. The report flags any further sources where the listing is missing or has inconsistent details.

---

## 3. Post-event review request workflow

The audit's #4 critical priority is a review-request cadence. Goal: 30+ Google + Trustpilot reviews in 90 days. The review velocity is what shifts the local pack ranking, not the absolute count, so the cadence matters more than getting the sequence perfect.

Set up a simple template-based workflow. After every booking that completes, schedule three touches:

- **Day 30** — Email the booker. Thank them, link directly to the GBP review form (`https://search.google.com/local/writereview?placeid=<placeid>` once you have the place ID from §1). Ask for one or two sentences and a star rating. Keep it short; long requests convert badly.
- **Day 60** — If they didn't review on day 30, send a follow-up. Different angle: ask whether anything could have been better. Either you get a review, or you get something to fix.
- **Day 90** — Final touch. Link to Trustpilot this time (`https://uk.trustpilot.com/evaluate/londonchoralservice.com`). Some reviewers will only post on platforms they already use; offering both broadens the pool.

A lightweight way to run this: a Google Sheet of bookings with a column for "review request status", and three calendar reminders per booking. Mailchimp, ConvertKit, or even Apple Reminders all work. Don't over-engineer it before you know whether the cadence converts — pick the simplest tool you'll actually use.

Do not offer incentives for reviews. Both Google and Trustpilot have policies against paid or incentivised reviews, and being caught at it removes the listing.

---

## 4. GSC, GA4, and CrUX credentials

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

Currently every page shares the same Open Graph image. The audit recommends per-page images for the top 16 pages: the 12 pillar pages plus the 4 highest-traffic music guides (top traffic to be confirmed once §4 GA4 access is live, but reasonable defaults: Christmas carols, Abide With Me, Be Thou My Vision, Pie Jesu).

Two viable implementations:

- **Vercel OG** (`https://vercel.com/docs/functions/og-image-generation`) — generates an image from JSX or HTML at request time, edge-cached. Free tier covers far more than this site needs. Requires either deploying a tiny Vercel project just for image generation (the rest of the site stays on GitHub Pages) or migrating the site to Vercel.
- **Cloudinary URL transformations** (`https://cloudinary.com/documentation/image_overlays`) — upload a base template, then generate per-page variants by encoding the title/subtitle as URL parameters. No code needed, but ties you to Cloudinary's free-tier limits.

For 16 pages that change rarely, Cloudinary is the lower-effort choice. Pick the route, generate the 16 images, then update the `og:image` meta tag on each page. Phase 4 of the programme can wire this into the build script.

**Update 2026-08-18 (value/care + on-page SEO programme):** prioritise the four service pages — `funerals.html`, `weddings.html`, `corporate.html`, `christmas.html` — for the first per-service images, since they are the main conversion landings (now carrying the value block, and FAQ schema on funerals/weddings). Wiring is trivial once assets exist: swap `og:image` + `twitter:image` (1200×630) per page; no build-script change required. `[BLOCKED-ON-HUMAN]` on the image assets themselves.

**Update 2026-08-18 (resolved):** six branded 1200×630 images — `assets/og-{funerals,weddings,corporate,christmas,services,pricing}.png`, set in the site's own Cormorant Garamond on the house cream/claret palette — were generated and wired as `og:image` / `twitter:image` and the Article `image` across the 7 money pages and all 57 music guides (category-mapped to funerals/weddings/christmas/services). Area pages and the publisher `logo` still point at the generic `og-image.png`; a later pass could add area-page images and a dedicated square logo asset.

---

## 7. IndexNow protocol

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

The audit notes that all CSS currently lives inline in each HTML file rather than in external stylesheets. In theory this hurts caching across pageviews; in practice, with the site already at decent CWV and pages averaging ~60–70 KB pre-gzip, the saving from extraction is small.

**Decision: skip until real CWV field data shows it's costing.** Once §4 credentials are live and CrUX is reporting actual user-experienced LCP/INP for the domain, revisit. If CrUX shows LCP > 2.5s on a meaningful share of visits and the trace points at render-blocking CSS, then extract. Otherwise leave it alone — extraction is a substantial refactor for what is currently a hypothetical gain.

## 9. Christmas season (do before September)

The July 2026 Christmas expansion (`docs/superpowers/plans/2026-07-29-christmas-expansion.md`) added 12 pages targeting carol-service and carol-singer hirers. These off-site and asset tasks are human-only:

1. **Google Business Profile seasonal update.** Add "Christmas carol services" and "Carol singers" as services on the GBP listing; post a seasonal update (September and November) linking to `/christmas.html` and `/carol-singers.html`. Blocked on §1 (GBP claim) if still outstanding. *(Update 2026-08-20: both posts are drafted in `docs/off-site-listings-pack.md` §"GBP seasonal posts" — paste and go.)*
2. **Google Ads seasonal conversions.** All Christmas-intent forms (christmas, carol-singers, and the four new B2B pages) currently pool into `ads_conversion_Christmas_1` via `thank-you.html?from=christmas`. If per-source attribution is wanted, create `ads_conversion_CarolSingers_1` (and per-B2B events) in Google Ads, then ask an agent to extend the `events` map in `thank-you.html` and switch the relevant forms to new `?from=` params — do not change the params before the Ads events exist, or conversions will silently drop to the generic Contact event.
3. **Carol recordings.** Partly done (August 2026): one Christmas recording — Blue Christmas, `mKMjUvCCW3E`, Small Choir — now leads the "Hear our musicians" sections on christmas.html and carol-singers.html and sits under "Something different" on listen.html, with full `VideoObject` schema. Everything else in those sections is still hymn recordings. Record 1–2 actual carols (even rehearsal-quality video) and hand them to an agent to wire in the same way.
4. **Christmas OG image.** All ~118 pages share one generic og-image (see §6 / ROADMAP R7.3). A seasonal image for christmas.html + carol-singers.html would lift social CTR during the season.
5. **Google Search Console.** After the expansion merges: resubmit sitemap.xml, request indexing for the 12 new URLs, and from September watch the query report for cannibalisation between christmas.html ("carol service" terms) and carol-singers.html ("hire carol singers" terms) — the pages are deliberately split on those intents.
6. **Citations.** Add "carol singers" as a category/service on Bark, Poptop, Encore, and Add to Event profiles (§2) — those marketplaces dominate the "carol singers for hire" SERP and a presence there captures buyers who never leave the platform.
7. **Brand watch.** londoncarolsingers.com trades as "LCS — London's premier carol singers". Site copy now consistently uses the full "London Choral Service" name on Christmas pages; keep an eye on branded-search confusion.

---

## 10. Christmas content overhaul (July 2026) — follow-ups

The 2026-07-31 overhaul added 11 further Christmas guides (24 in total), set a vocal/string ensemble floor across the site, and led carol hire with four voices. Human-only follow-ups:

1. **Google Search Console.** Resubmit `sitemap.xml` (now 126 URLs) and request indexing for the 11 new guide URLs. Priority: this needs doing before September, when booking research peaks.
2. **Cannibalisation watch.** The Christmas guide set is now 24 pages and several sit close together — `how-many-carol-singers` against the sizing FAQ on `carol-singers.html`, `best-carols-for-four-voices` against `christmas-carols-guide`, and `christmas-drinks-reception-music` against `company-christmas-party-entertainment`. Each has an exclusive title and H1, but watch the GSC query report from September for the two pages swapping positions on the same term.
3. **Confirm the accompanied small-group pricing is right.** `pricing.html` now publishes £645 for two singers with organ or piano and £860 for three, derived as £215 per singer plus £215 for the accompanist. If that arithmetic is not how you actually quote it, tell an agent the real figures — the derivation is stated on the page and in three guides.
4. **Decide on the lambeth testimonial.** `areas/london/lambeth.html` carries a client quote describing a *trio* singing at an outdoor committal, which the new floor no longer offers. It was left untouched because editing a genuine quote would be fabricating it. Removing it is a business decision, not an agent one.

---

## 11. Google Ads campaigns for the competitive capture programme

Spec: `docs/superpowers/specs/2026-08-18-competitive-capture-design.md` §6. Landing page: `compare/london-funeral-singers.html`.

**Do first, before any spend.** Confirm phone-click and WhatsApp-click conversion actions exist and fire. `AW-17988388404` is on every page and wired for form submissions; call conversions are unverified. A call-only campaign without a call conversion action spends blind.

1. **Generic funeral, price-led.** "funeral singer london", "funeral choir hire london", "singer for funeral service", "funeral choir cost". RSA headlines led on "From £250, nothing added" and "Three sung pieces included, not one". Landing: `funerals.html`, with the comparison page as an A/B alternative. This is where the budget goes.
2. **Call-only, short notice.** Evening and weekend scheduling. Keywords around "short notice", "this week", "urgent". Funerals are urgent and a bereaved person at nine in the evening rings rather than fills in a form.
3. **Brand defence.** LCS brand terms, exact match, capped budget.
4. **Conquest.** Competitor brand terms as keywords, landing on the comparison page. **Their trademark must not appear in ad text** — Google permits the mark as a keyword but restricts it in creative, and the owner can complain. The landing page does the naming; the ad does not. Negative-match trade terms ("funeral director", "trade", "supplier") so the campaign stays on the family audience the landing page addresses. Expect low volume and a poor quality score; keep it a small line item, not the strategy.
5. **Borough and crematorium geo.** Hold until those landing pages exist.

Site-wide negatives: jobs, wanted, free, karaoke, courses, "become a".

Conversion modelling is degraded until Consent Mode v2 exists (ROADMAP R4). Read the figures accordingly.

### Quarterly: re-check competitor pricing

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

---

## 13. Private events page launch follow-ups, 2026-08-26

The page is `private-events.html` (spec: `docs/superpowers/specs/2026-08-26-private-events-design.md`). Every open decision was settled by the owner on 2026-08-26; only the items below remain.

1. **Send one live test enquiry (do this first).** The form now carries hCaptcha, matching the rest of the site, so it uses the shared Web3Forms access key exactly as the other forms do. It could not be tested from the build environment (the network proxy blocks api.web3forms.com and hcaptcha.com). Before advertising the page, submit one real enquiry through the live form and confirm it arrives, with the subject line `Private events enquiry — Alma Consort / LCS`.
2. **Photography and the fuller venue list.** Supply hero and section photography (the page ships typographic-only), and the fuller fifteen-plus venue list for the "Where we have sung" section — the HTML comment slot after `ul.pe-venues` marks where the items go. Every venue listed must be one the singers have actually performed in. The section currently shows the eight London venues vetted on `about.html` and states the international coverage in prose; naming venues abroad would be the single strongest addition to the page.
3. **Voicing videos.** Map one YouTube video per voicing into `PE.VOICING_VIDEOS` in `js/private-events.js` (keys: `eight`, `twelve`, `sixteen`, `twenty-four`). Video IDs MUST first exist in `data/seo-fix-discovered-urls.yml` — add any new video there first, with a verified upload date, before pasting its ID into the JS. A voicing left `null` renders no player, which is the shipped state.
4. **Google Ads: dedicated conversion action (when convenient).** The page fires the existing generic Contact label (`AW-17988388404/RjhECKGP7akcELSMxIFD`), so conversions record from day one but are not segmented from ordinary contact enquiries. To separate them, create a conversion action named **"Private events enquiry"** in Google Ads and map the GA4 event `ads_conversion_PrivateEvents_1` to it — the procedure documented for the corporate audience in `thank-you.html` (lines 52–54) — then paste its `send_to` label over `PE.ADS_CONVERSION` in `js/private-events.js`.
5. **almaconsort.com.** The ensemble section links to the homepage and the page's schema lists it as the ensemble's URL. Confirm it presents well to a planner vetting the name, and add a reciprocal link from that site back to https://londonchoralservice.com/private-events.html.

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
4. **Google Ads.** Create a dedicated conversion action for the destinations
   funnel and paste its `send_to` label over `PE.ADS_CONVERSION` in
   `js/private-events.js`; until then the generic Contact label fires for every
   register page. Consider paid search on destination terms using the reserved
   hero H1 variant (`grep -n 'Hero H1 A/B alternatives' private-events.html`).
5. **Photography or video from an overseas engagement.** The highest-value asset
   for this audience and the one thing here that cannot be written. All register
   pages ship typographic-only until supplied.
6. **A bespoke OG image** for `/destinations/` and `/planners-and-venues.html`;
   both currently reuse `assets/og-private-events.png`.
7. **Planner-network and luxury-directory outreach**, and wedding-press placement
   &mdash; there are now pages to point at.
8. **Refresh the repo graph.** `graphify-out/` is now stale: this programme added
   twenty-five pages and edited nineteen more, and the graphify tool was not
   available in the session that built them, so the committed graph still
   describes the site as it was before. Run `/graphify --update` and commit
   `graphify-out/` when convenient. Nothing depends on it at runtime; it only
   affects agents querying the graph instead of re-reading the repo.

---

## 15. www subdomain serves a broken TLS certificate, 2026-08-30

A full SEO audit found `https://www.londonchoralservice.com` fails the TLS handshake outright (`SSL: no alternative certificate subject name matches target host name`) rather than redirecting to the apex domain. DNS for `www` already resolves to GitHub Pages' anycast IPs, but the certificate GitHub serves only covers `*.github.io` — it doesn't cover the `www` host because the `CNAME` file in this repo only declares the apex (`londonchoralservice.com`), and GitHub Pages only provisions/serves a matching cert for whichever custom domain is configured in the repo's own Settings → Pages.

Anyone who types `www.` from habit, or any inbound backlink built to the `www` host, hits a browser security interstitial instead of a clean redirect. This is a dashboard/DNS-panel action, not something fixable from the repo.

What to do:

1. In the repo's GitHub Settings → Pages, add `www.londonchoralservice.com` as an alternate custom domain alongside the existing apex domain. This provisions a certificate covering both hosts and makes GitHub auto-redirect `www` → apex per the `CNAME` file's value.
2. Alternatively, if `www` was never meant to resolve at all, remove its DNS record at the registrar/DNS panel instead of leaving a broken host reachable.
3. Once fixed, confirm with `curl -I https://www.londonchoralservice.com/` — expect a `301` to the apex, not a TLS error.

---

## 16. Follow-ups from the 2026-09-04 audit fixes

1. **Consent Mode check (Google Ads and GA4).** The site now sets Consent Mode v2 defaults to "denied" and shows a cookie notice. In Google Ads → Goals → Conversions → Diagnostics, confirm the conversion actions show "Consent mode: active" and that modelled conversions appear after a fortnight. In GA4 Admin → Data collection, confirm consent signals are received. Nothing to change in the repo unless a tag reports "consent not set".
2. **Read `terms.html`.** It publishes the fourteen Terms of Booking clauses from the booking agreement, adapted to a web page (the funeral post-service invoicing exception is stated under clause 4, and a complaints paragraph is added). Confirm the wording matches what goes out on booking confirmations, or edit the page and the agreement together.
3. **Read `accessibility.html`** and confirm the alternative-format promise and the one-working-day reply are what you want to stand behind.
4. **Two testimonials still say "she"** ("Pamela, Richmond" on 9 pages, "Helen, Wimbledon" on 4). See ROADMAP R12.
5. **Reply-time promises are now: one working day (usually the same day) everywhere, and the same working day (usually within a few hours) on the funeral and funeral-director pages.** If the office cannot keep those, say which to soften.
6. **The nav's hamburger breakpoint moved from 805px to 1080px** so the eight-item menu never clips; tablets in portrait now get the hamburger. Check on an iPad if that matters to you.

