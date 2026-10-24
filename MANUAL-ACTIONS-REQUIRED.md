# Manual actions required

Things only you can do: your identity, an account in your name, accepting terms, or a decision or material only you have. Claude never does these. Updated 24 Oct 2026.

Every item below is complete in itself: what it is, why it matters, exactly what to do, and how you'll know it's done. Nothing sends you to another section. When you finish one, tell an agent so it can be removed from this file.

Finished work, old notes and reference material are in `docs/MANUAL-ACTIONS-ARCHIVE.md` (the old section numbers in code comments refer to that file).

**At a glance**

| # | Action | Time | Deadline |
|---|---|---|---|
| 1 | Google Ads identity check | 15 min | **4 Nov** |
| 2 | Ask Google to recrawl 12 pages | 10 min a day, two days | this weekend |
| 3 | Submit the sitemaps to Bing Webmaster Tools | 5 min | this weekend |
| 4 | Directory sign-ups (seven sites) | 15–20 min each | this week |
| 5 | Fix the `www` certificate (GitHub Support) | 5 min | this week |
| 6 | Check the Google Business Profile edits | 5 min | from 30 Oct |
| 7 | Send four outreach drafts | 10 min | this week |
| 8 | Ask Kensington and Chelsea how to join their supplier list | 5 min | this week |
| 9 | Choose press photographs | 30 min | when you can |
| 10–14 | Optional: Trustpilot, LinkedIn, backup key, Books VAT check, pinned git origin | 5 min each | none |
| 15–18 | Material only you have: carol recordings, private-events assets, wedding-abroad footage, almaconsort.com link | | none |
| 19–22 | Decisions: testimonials, Ireland and Scotland regions, US lead time, sign-offs | | none |
| 23 | When a singer's bank details change | | when it happens |
| 24 | Dates to remember | | |

---

## 1. Google Ads identity check (due 4 Nov 2026)

Google Ads shows a yellow banner on every page: "Verify your identity. Some of your ads may be paused or limited." If verification isn't done by 4 Nov, Google can stop serving the ads, the Christmas campaign included. Only you can do it, because it needs your ID and the company's details.

**Have ready:** your passport or driving licence, and the certificate of incorporation (free from Companies House: company number 16785727 → Filing history → download the certificate).

**How:**

1. Sign in to Google Ads (account 873-388-1378).
2. Click **Get started** on the yellow banner. If the banner has gone, go to **Billing → Advertiser verification**.
3. Answer the questions: who pays for the ads, and who the advertiser is. The advertiser is Alma Consort Ltd, Companies House 16785727, trading as The London Choral Service.
4. Upload your photo ID and the certificate of incorporation when asked.
5. Submit. Google usually replies within a few working days.

**Done when:** Google Ads shows the verification as approved and the banner is gone. Tell an agent.

---

## 2. Ask Google to recrawl 12 pages

Google has indexed 153 of our 165 sitemap pages. These 12 are the exceptions. Some Google has never fetched; the others it judged in the spring, before they were rewritten, and hasn't looked at since. The Search Console API can't request indexing, so you do it by hand. Google allows about ten requests a day, so split it over two days.

**How, for each URL:**

1. Open Search Console (https://search.google.com/search-console) and choose the property `londonchoralservice.com`.
2. Paste the URL into the search bar at the top ("Inspect any URL"). Wait for the result.
3. Click **Request indexing** and wait for the confirmation. (If it says "URL is on Google" it is already indexed; request anyway, since the page was rewritten.)

**Today, the eight pages Google crawled before they were rewritten:**

```
https://londonchoralservice.com/areas/london/barnet.html
https://londonchoralservice.com/areas/london/hammersmith-fulham.html
https://londonchoralservice.com/areas/london/hillingdon.html
https://londonchoralservice.com/areas/london/kingston.html
https://londonchoralservice.com/areas/london/newham.html
https://londonchoralservice.com/areas/london/richmond.html
https://londonchoralservice.com/areas/london/tower-hamlets.html
https://londonchoralservice.com/music-guides/wedding-ceremony-music.html
```

**Tomorrow, the four pages Google has never crawled:**

```
https://londonchoralservice.com/professionals.html
https://londonchoralservice.com/christmas-carol-services.html
https://londonchoralservice.com/christmas-listen.html
https://londonchoralservice.com/music-guides/popular-funeral-hymns.html
```

**You don't need to resubmit the sitemap.** Google read it on 23 Oct, and the new sitemap index was submitted through the API on 24 Oct.

**Done when:** all 12 requests are made. Two weeks later (about 7 Nov) an agent reruns the index-coverage report; any page still "Crawled - currently not indexed" then needs a content fix, not another request.

---

## 3. Submit the sitemaps to Bing Webmaster Tools

Bing's index feeds ChatGPT search and Copilot. A check on 24 Oct found the site missing from Bing even for its own name. Nothing on the site blocks Bing (robots.txt allows it, no sitemap page is noindex, and the IndexNow ping after each deploy gets HTTP 200), but Bing indexes a little-linked new site slowly until it is verified in Bing Webmaster Tools.

**The sitemaps (all four return HTTP 200 today):**

| Sitemap | URL | What it lists | Do you submit it? |
|---|---|---|---|
| **Sitemap index** | `https://londonchoralservice.com/sitemap_index.xml` | the three below, in one file; the only one `robots.txt` names | **Yes. This is the one submission you need.** |
| Pages | `https://londonchoralservice.com/sitemap.xml` | 164 pages | Not separately; the index covers it. If the import below brings it in on its own, leave it. |
| Video | `https://londonchoralservice.com/sitemap-video.xml` | 36 film entries | Not separately; the index covers it. |
| Images | `https://londonchoralservice.com/sitemap-images.xml` | 21 film stills | Not separately; the index covers it. |

Do **not** submit `llms.txt` or `llms-full.txt`: they are not sitemaps. If you'd rather see each file's status in Bing's report, submitting the three children as well as the index does no harm (Bing treats a repeat as the same sitemap).

**How:**

1. Go to https://www.bing.com/webmasters and click **Sign in**. Use the Google account that owns the Search Console property, or a Microsoft account.
2. On **Add a site**, choose **Import your sites from GSC** (the left-hand card), not "Add your site manually".
3. Click **Continue**, pick the same Google account, and allow Bing to view your Search Console data (read-only).
4. Tick **londonchoralservice.com** and click **Import**. This verifies the site, so you need no meta tag or DNS record.
5. Open **Sitemaps** in the left menu. If `https://londonchoralservice.com/sitemap_index.xml` isn't listed, click **Submit sitemap**, paste that URL and click **Submit**.
6. Open **URL Inspection**, inspect `https://londonchoralservice.com/` and click **Request indexing** if it isn't indexed. Do the same for `/weddings.html`, `/funerals.html`, `/christmas.html` and `/pricing.html`. The IndexNow ping covers every other page.

**Done when:** the Sitemaps page lists `sitemap_index.xml` with status "Success" (it can read "Pending" for a day) and the five pages are requested. Tell an agent. Bing usually shows first results within a week; **Site Explorer** then shows which pages are indexed.

---

## 4. Directory sign-ups

No third-party listing is live yet except Google Business Profile. Google cross-checks listings like these for local rankings, and the marketplaces hold most of the first page for our searches. For each site below you make the account, enter the passwords and codes, accept the terms, and press Publish. Claude can't do any of those, even with your go-ahead. Everything else, Claude does: once you are signed in (in the Claude app's browser, or Chrome with Claude in Chrome), say "fill the Hitched listing from the pack" and it enters every field, uploads the logo and photos, and stops before Publish. Then Claude records the live link.

**Before you start:** sign up with `office@londonchoralservice.com` so leads reach the enquiry inbox. Upload images are in `~/Pictures/LCS-listings/`. All copy, prices, the tagged website link for each site, and the exact name, phone, hours and service area to use are in `docs/off-site-listings-pack.md`. Use that name, phone number and hours **word for word** on every site: different formats split Google's picture of the business into separate entities. Where a Christmas link is needed, use `christmas.html` (the old `carol-singers.html` is now a redirect).

**In this order. Your steps are listed for each site; once you've done them and are signed in, say "fill the <site> listing from the pack" and Claude does the rest.**

**a. Bing Places** (free, about 10 minutes; live 7–12 days later)

1. Go to https://www.bing.com/forbusiness/ and click **Sign in**. Use a Microsoft account (make one with office@londonchoralservice.com if needed) and accept the terms.
2. Choose **Import from your Google Business Profile**, sign in to the Google account that owns the profile, and allow Bing to read it.
3. Pick the **Weekly** sync schedule and import the listing Bing finds. Bing verifies it itself.
4. Once it is live, open it on Bing Maps. If a street address shows, tell an agent; the fix is in the pack.

**b. Apple Business** (free, about 20 minutes, then up to 5 working days)

1. Go to https://business.apple.com → **Sign up now** → **Create an Apple Account for Work**. Organisation: Alma Consort Ltd; leave the agency box unticked. Enter the codes Apple texts and emails, and accept the terms.
2. Verify the organisation within 60 days. Apple wants two proofs. The Companies House certificate of incorporation is one; a D-U-N-S number (free from Dun & Bradstreet UK) or a DNS TXT record at the domain registrar are the others.
3. Tell Claude when verified. It adds the brand (name, logo, tagged website, phone). **Don't add a Maps location**: Apple can't hide an address and we have no premises.
4. Submit the brand for review.

**c. Hitched** (free storefront, about 15 minutes)

1. Go to https://www.hitched.co.uk/business-login/ → **Create your free listing**.
2. Business name: The London Choral Service. Group: Wedding Suppliers. Category: Music and DJs (Hitched has no choir category). Phone 07356 042468. Email office@londonchoralservice.com.
3. Choose a username (lower case, at least five characters) and a password, tick the terms box, click **Create your account**, and confirm the email Hitched sends.
4. Claude fills the headline, About text, price guide, photos and tagged website link. Decline any paid upgrade, then press **Publish**.

**d. Bridebook** (free after a three-month trial, about 15 minutes)

1. Go to https://business.bridebook.com/signup. Business name: The London Choral Service. Country: United Kingdom. Website: `https://londonchoralservice.com/weddings.html?utm_source=bridebook&utm_medium=referral&utm_campaign=listing`. Phone and email as above → **Proceed to step 2 of 2**.
2. If it asks for an address, use the registered-office postcode N1 7GU and hide the street line if offered. Open the activation email and set the password.
3. Claude fills the profile (category Music, description, photos, prices from £1,150). Accept the terms and publish.
4. Bridebook starts a three-month trial of its paid Basic plan (no card). **Decline Classic (£99 a month)**, and diary the trial's end to decide on Basic (£20 a month plus VAT). If you let it lapse, the listing becomes the free Limited Profile, which ranks lower.

**e. Yell** (free, about 15 minutes; expect a sales call)

1. Search https://www.yell.com for "The London Choral Service". If a listing exists, click **More Info → Claim Business → Claim this business**. If not, go to https://www.yell.com/free-listing/.
2. Step 1: your first and last name, business name The London Choral Service, postcode N1 7GU, phone 07356 042468, email office@londonchoralservice.com → **Continue**. Yell publishes what you enter here.
3. Claude fills the address (hidden if offered), classification, description, website and hours Monday to Friday 9am–6pm. **Untick** the offer to send your details to Apple, Alexa and Microsoft: they get their own listings and a copy makes a duplicate.
4. Accept the terms and submit. A moderator checks it. Decline the paid products when Yell rings.

**f. Guides for Brides** (free basic listing, about 10 minutes)

1. Go to https://guidesforbrides.co.uk/free-advertising → **Add your business** → enter office@londonchoralservice.com → **Get Started**.
2. Claude fills the category (Discos, DJs & Live Music), counties, description, tagged website and photos.
3. Stay on the free basic listing (paid tiers run £14.50 to £59.50 a month plus VAT). Accept the terms and submit.

**g. FreeIndex** (free)

1. Go to https://www.freeindex.co.uk/ and make an account with office@londonchoralservice.com. It lists Euphony Voices as a London wedding and funeral choir and doesn't list us.
2. Claude fills the listing from the pack. Skip the paid upgrade. Press **Publish**.

Skipped on purpose, don't sign up: Bark and Add to Event (pay-per-lead credits that attract cheap soloist requests), FuneralGuide (lists funeral directors only), Last Minute Musicians (£59.99 for six months; revisit only if the free listings bring nothing).

**Done when:** each listing is live and Claude has recorded its link in the pack's status table. Afterwards, run the free scan at https://www.brightlocal.com/free-business-listings-scan/ with the homepage URL; it flags any other site where our details are missing or different.

---

## 5. Fix the `www` certificate (GitHub Support ticket)

`https://www.londonchoralservice.com` shows a browser security warning, because GitHub's certificate for the site covers only `londonchoralservice.com`. Anyone who types `www.` from habit, and any link built to the `www` address, lands on that warning. The DNS is right, and the remove-and-re-add of the custom domain has already been done (doing it again won't help), but GitHub still hasn't issued a certificate for `www`. Only GitHub can fix this now.

**How:**

1. Go to https://support.github.com → **Contact support** → choose **GitHub Pages**.
2. Paste this ticket:

   > Subject: Certificate missing for the www host of my Pages custom domain
   >
   > Repository: lucawetherall/londonchoralservice. Custom domain: londonchoralservice.com (Settings → Pages, deployed with GitHub Actions). The `www` host has a CNAME to lucawetherall.github.io and the Pages health check lists www.londonchoralservice.com as valid and eligible for HTTPS. But https://www.londonchoralservice.com/ still serves the *.github.io certificate, and the certificate for londonchoralservice.com lists only the apex name. I removed and re-saved the custom domain on 23 Oct 2026 and toggled Enforce HTTPS off and on; a day later nothing had changed. There are no CAA records on the domain. Please issue a certificate that covers www.londonchoralservice.com.

3. Send it.

**If GitHub can't fix it:** delete the `www` CNAME record at Porkbun (the registrar's DNS panel). The `www` address then stops resolving, which is cleaner than showing a warning.

**Done when:** `curl -I https://www.londonchoralservice.com/` returns `301` (a redirect to the main address) instead of a certificate error. An agent can run that for you.

---

## 6. Check the Google Business Profile edits (from 30 Oct)

On 23 Oct Claude made a batch of edits to the profile; Google shows each as "pending review" until it approves it, which can take days. Check they all went through.

**How:** from about 30 Oct, sign in at https://business.google.com/, choose **The London Choral Service**, and check each of these is live:

- **Categories:** Choir (primary) and Wedding service. Google offers no "Funeral service" category (only "Pet funeral service" and "Funeral celebrant service", which would misdescribe a choir), so funerals are carried by the Funeral choir service and the description instead.
- **Description:** the 680-character text from the listings pack.
- **Website:** `https://londonchoralservice.com/?utm_source=google&utm_medium=organic&utm_campaign=gbp`.
- **Service area:** London, Greater London, Surrey, Kent, Essex, Hertfordshire, Berkshire, Buckinghamshire; address hidden.
- **Hours:** Monday to Friday 09:00–18:00, weekends closed.
- **Services:** seven, six at "From £1,150" and Organist and pianist hire at £250.
- **Photos:** nine (more are wanted: see action 9).

If one was rejected or reverted, tell an agent which and it will redo it in a live chat. Three Christmas posts are already scheduled for 09:00 on 10 Nov, 24 Nov and 8 Dec; you can edit or cancel one under **Posts** before its date.

**Done when:** every item above shows on the public listing. Recheck the categories each quarter in case Google adds a funeral category.

---

## 7. Send four outreach drafts

Claude drafted four first-contact emails to firms that list or link to rival choirs. They are in Zoho Drafts, from `office@londonchoralservice.com`, each with an opt-out line and a tagged link. Claude never sends them.

| Firm type | Why it was chosen |
|---|---|
| A funeral planner | its London funeral-music page links only to The London Funeral Singers |
| A City livery hall | its music-suppliers list has no choir |
| Two event agencies | their act lists carry rival carol choirs |

All four are limited companies, checked at Companies House on 24 Oct.

**How:** open Zoho Mail → **Drafts**. Read each draft, edit it if you like, and press **Send**. If a firm replies "no thanks", tell an agent, which marks it opted out so it is never contacted again.

**Done when:** all four are sent (or deleted if you decide against one).

---

## 8. Ask Kensington and Chelsea how to join their supplier list

The council keeps an approved-suppliers list for weddings at Chelsea Old Town Hall and the Kensington register office (https://www.rbkc.gov.uk/marry-me-in-kensington-and-chelsea/node/733, section "Music and musicians"). It has no choir. The council publishes no email address, only an "Email us" form and the phone number 020 7361 4100, so the application is yours to make.

**How:** ring 020 7361 4100 or use the "Email us" form on that page. Ask how a supplier joins the approved list for music and musicians, and give them `https://londonchoralservice.com/weddings.html`.

**Done when:** you have their answer (a form, a fee, or a no). Tell an agent so it can be recorded.

---

## 9. Choose press photographs

`facts.html` (the public fact sheet) says we have no press photographs yet and offers two film stills instead. Directories, journalists and venues ask for real photographs, and the Google profile wants ten or more (it has nine). Claude can't take or choose photographs.

**How:**

1. Pick three to six photographs you own the rights to: the singers in a church, a choir at a wedding or carol service, and one portrait of you. Real photographs only, never stock or AI images. Get the photographer's permission to publish, and the client's if a client or guest can be recognised. Never use a funeral.
2. Save them in `~/Pictures/LCS-listings/` as JPGs, at least 1600 pixels on the long side.
3. Tell an agent, with each photographer's name for the credit. It makes web-sized copies, puts them on the fact sheet with credits and alt text, replaces the "no press photographs yet" line, and lists them for upload to the Google profile and the directories in action 4.

**Done when:** the fact sheet shows the photographs.

---

## 10. Optional: Trustpilot business account

Reviews already come through Google (the enquiry assistant drafts a review request after each paid-in-full event, except funerals, for you to send). Trustpilot would add a second place for reviews, but it isn't needed.

**How, if you want it:** go to https://business.trustpilot.com, sign up with `office@londonchoralservice.com`, and claim "The London Choral Service". Then tell an agent, which adds Trustpilot's link to the review-request drafts. Never offer anything in return for a review: Google and Trustpilot both remove listings for that.

---

## 11. Optional: LinkedIn company page

The page `linkedin.com/company/london-choral-service` doesn't exist. A company page strengthens how Google and AI assistants recognise the business as one entity.

**How:** on LinkedIn, open **For Business → Create a Company Page**, and make a page named "The London Choral Service" (type: company, industry: Entertainment Providers or Musicians; the legal entity is Alma Consort Ltd). Then send an agent the page's address, and it adds it to the site's structured data.

---

## 12. Optional: check the backup key is saved

The Command Centre's nightly job writes an encrypted copy of your whole `~/lcs-private` folder to iCloud Drive → LCS-backups at 02:30 (the newest was made on 23 Oct). The copies can't be opened without the secret key, a long string starting `AGE-SECRET-KEY-1…`, which was shown once when the backup was set up.

**How:** open your password manager and check that key is saved. If you can't find it, tell an agent: it can generate a new one, but backups made with the lost key stay unreadable.

---

## 13. Optional: confirm Zoho Books isn't set to VAT

Alma Consort Ltd is not VAT-registered, and invoices must carry no tax. Claude has checked the invoices (none carry tax), but the organisation's own VAT setting can't be read through the API.

**How:** in Zoho Books, go to **Settings → Taxes** and confirm the organisation is marked **not VAT-registered**. If it says otherwise, change it. Don't ask Claude to: it has no access to that setting.

---

## 14. Optional: pin this repository's git origin

This lets Claude sync branches with `main` using the Claude app's own git tool rather than asking you to run git commands by hand.

**How:** in the Claude app, open **Help → Troubleshooting → Review Pinned Git Origins** and confirm this repository's origin is in the list.

---

## 15. Material only you have: carol recordings

The "Hear our musicians" sections on `christmas.html` and the Christmas pages show one Christmas recording (Blue Christmas); everything else is hymns. Record one or two real carols (rehearsal-quality video is fine) and upload them to YouTube. Give an agent the links and it wires them in, with the upload date and duration the structured data needs.

---

## 16. Material only you have: private-events page

`private-events.html` ships typographic-only. Three things would lift it. Send each to an agent when ready:

1. **Photographs** from real engagements, for the hero and the sections.
2. **The fuller venue list** (fifteen or more) for the "Where we have sung" section. Only venues the singers have actually performed in. Venues abroad are the strongest addition.
3. **One video per voicing** (8, 12, 16 and 24 voices) on YouTube. A voicing with no video shows no player, which is the shipped state.

---

## 17. Material only you have: footage from a wedding abroad

Photography or video from an overseas engagement is the highest-value asset for the destination-weddings pages, which all ship typographic-only. Send an agent the footage or the YouTube link, with the venue, country and date.

---

## 18. Material only you have: a link from almaconsort.com

almaconsort.com links only to the London Choral Service homepage. A link to the private-events page would strengthen it, and a planner vetting the Alma Consort name would find it.

**How:** add a link on almaconsort.com to `https://londonchoralservice.com/private-events.html` (text such as "Private events and weddings abroad"). Then tell an agent so it can confirm the link is live.

---

## 19. Decision: five testimonials, keep or remove

Each of these client quotes appears on one page only, and nothing in the repo or the bookings ledger ties it to a real booking. Agents never edit testimonials, because changing a genuine quote would be fabricating it, so only you can say whether each is a real client.

| Quote attributed to | Page | Note |
|---|---|---|
| Lambeth quote | `areas/london/lambeth.html` | describes a *trio* at an outdoor committal, which you no longer offer |
| David R., Battersea | `music-guides/celebration-of-life-music.html` | |
| Eleanor M., Hampstead | `music-guides/funeral-songs.html` | |
| Margaret K., Islington | `music-guides/catholic-funeral-hymns.html` | names "Father O'Brien" |
| Sophie and Tom W., Greenwich | `music-guides/wedding-ceremony-music.html` | |

**How:** reply to an agent, for each one, "keep" or "remove". It removes the ones you name and rebuilds. A kept quote needs nothing.

---

## 20. Decision: Ireland and Scotland regions

You named regions for twenty destination countries but not these two. To keep their pages as full as the others, regions were set provisionally on 29 Aug: **Ireland** as Dublin, County Wicklow, the south west and the west; **Scotland** as Edinburgh, the Highlands, Loch Lomond and Perthshire. They drive the region sections on those pages and the cards on `/destinations/`.

**How:** reply to an agent "keep both", or give replacement regions.

---

## 21. Decision: United States lead time

Paid performance in the US needs a petition-based performance visa for each musician, on a months-long timeline. The US destination page must not imply a booking is practical if it isn't.

**How:** tell an agent the real working lead time, for example "at least nine months". If a booking is impractical under six months, the page says so.

---

## 22. Read and sign off

Three published pages make promises on your behalf. Read each and tell an agent "fine" or what to change.

1. **`terms.html`:** it publishes the fourteen Terms of Booking clauses from your booking agreement, adapted for the web (the funeral invoice-after-the-service exception is under clause 4, and a complaints paragraph is added). Check the wording matches what goes out on your booking confirmations. If not, the page and the agreement are edited together.
2. **`accessibility.html`:** check you are happy to stand behind the alternative-format promise and the one-working-day reply.
3. **Reply-time promises:** the site says you reply within one working day (usually the same day) everywhere, and the same working day (usually within a few hours) on the funeral and funeral-director pages. If the office can't keep those, say which to soften.

Optional: open the site on an iPad in portrait. The menu switched to the hamburger layout below 1080 pixels wide so the eight items never clip; check it looks right.

---

## 23. When a singer's bank details change

If the enquiry assistant's summary shows "BANK DETAILS CHANGED" or "DIFFER" against a singer's invoice, the bank details on the new invoice don't match what's on file. This check exists so a changed account always gets a phone call before anyone is paid; Claude never confirms bank details.

**How:**

1. Ring the singer on a number you already hold for them, never a number from the new invoice, and confirm the new bank details by voice.
2. Open the Command Centre → **Singers**, choose **Act on <name>'s invoice → Confirm bank details**, and approve with Face ID or Touch ID.
3. If the Command Centre is down, set `bank_confirmed` to `yes` for that invoice in `~/lcs-private/singer-invoices.csv`. It counts until a rescan changes the details.

---

## 24. Dates to remember

| When | What | Who |
|---|---|---|
| **4 Nov 2026** | Google Ads identity check due (action 1) | you |
| About 7 Nov | Rerun the index-coverage report on the 12 pages (action 2) | agent, on your word |
| 10 Nov, 24 Nov, 8 Dec | Scheduled Business Profile posts publish at 09:00 | automatic |
| November | Look again at whether `christmas.html` and the Christmas guides compete for the same Search Console queries; too little data on 14 Oct | agent |
| **Late January 2027** | **Re-check competitor prices.** Open https://www.londonfuneralsingers.co.uk/pricing and compare each `source_quote` in `data/competitor-pricing.yml` with what is published. Update the figures, the `checked_date` and `compare/london-funeral-singers.html` in the same commit (a figure and its date must never disagree). `build.sh` prints a STALE warning past 120 days. Last checked 23 Oct 2026: every figure unchanged. The file also holds Dream Gospel Choir, Music for London, Julia Charles and Alive Network figures checked 24 Oct, used by no page yet; re-check them too | agent, on your word |
| Each quarter | Re-verify the permit and travel facts on the destination pages (visible checked date: 29 Aug 2026), and check whether Google has added a funeral category for the Business Profile | agent / you |
