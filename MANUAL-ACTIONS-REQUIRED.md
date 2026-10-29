# Manual actions required

Things only you can do: your identity, an account in your name, accepting terms, or a decision or material only you have. Claude never does these. Updated 29 Oct 2026.

Every item below is complete in itself: what it is, why it matters, exactly what to do, and how you'll know it's done. Nothing sends you to another section. When you finish one, tell an agent so it can be removed from this file.

Finished work, old notes and reference material are in `docs/MANUAL-ACTIONS-ARCHIVE.md` (the old section numbers in code comments refer to that file).

**At a glance**

| # | Action | Time | When |
|---|---|---|---|
| 1 | Ask Google to recrawl nine pages (Search Console) | 10 min | 30 Oct |
| 2 | Directory sign-ups (seven sites) | 15–20 min each | this week |
| 3 | Fix the `www` address at Porkbun | 10 min | this week |
| 4 | Check the Google Business Profile edits | 5 min | from 30 Oct |
| 5 | Send four outreach drafts | 10 min | this week |
| 6 | Ask Kensington and Chelsea how to join their supplier list | 5 min | this week |
| 7 | Link to the private-events page from almaconsort.com | 5 min | when you can |
| 8–9 | Optional: Trustpilot, LinkedIn | 10 min each | none |
| 10 | Dates to remember | | |
| 11 | Web3Forms: restrict the form key to the site and enforce hCaptcha | 5 min | this week |
| 12 | Google Ads: hide two old conversion actions | 5 min | this week |

---

## 1. Ask Google to recrawl nine pages (Search Console)

On 24 Oct you requested eleven of twelve pages; Google refused the twelfth (the funeral-hymns guide) because the day's quota was used up. Later that day PR #370 rewrote seven more pages to match what people search for, so Google needs to fetch the new versions. That includes three you had already requested (Newham, wedding ceremony music, carol services): their earlier requests are for versions that no longer exist.

- **Funeral hymns guide:** Google found it in February and has never fetched it. It now carries the hymn table and is the page for "funeral hymns" searches.
- **Nine Lessons and Carols:** the fastest-growing page on the site, now with the readings and order of service at the top. Its searches peak in December, so it comes first.
- **Christmas carol services:** a new section on where we sing carol services.
- **Newham:** Google crawled it and chose not to index it; it now has local cemeteries, churches and the register office.
- **Wedding ceremony music:** now aimed at processional, signing the register and recessional searches.
- **Listen, Be Thou My Vision, Abide With Me:** new titles; the two hymn pages now carry the full words.

**How:** open Search Console (https://search.google.com/search-console) and choose the property `londonchoralservice.com`. For each URL, paste it into the search bar at the top ("Inspect any URL"), wait for the result, click **Request indexing** and wait for the confirmation. Google allows about ten requests a day.

**25 Oct, these five first:**

```
https://londonchoralservice.com/music-guides/nine-lessons-and-carols.html
https://londonchoralservice.com/music-guides/popular-funeral-hymns.html
https://londonchoralservice.com/christmas-carol-services.html
https://londonchoralservice.com/areas/london/newham.html
https://londonchoralservice.com/music-guides/wedding-ceremony-music.html
```

**26 Oct, these three:**

```
https://londonchoralservice.com/listen.html
https://londonchoralservice.com/music-guides/be-thou-my-vision-wedding-hymn.html
https://londonchoralservice.com/music-guides/abide-with-me.html
```

**27 Oct, these four.** They are new guides from PR #373 (memorial service songs, and three hymns whose words are out of copyright). Google would find them through the sitemap anyway; a request gets them crawled sooner.

```
https://londonchoralservice.com/music-guides/memorial-service-songs.html
https://londonchoralservice.com/music-guides/it-is-well-with-my-soul.html
https://londonchoralservice.com/music-guides/love-divine-all-loves-excelling.html
https://londonchoralservice.com/music-guides/the-lords-my-shepherd.html
```

**28 Oct, these six.** They are new Christmas carol guides from PR #375 (the words, history and choir notes for each carol). Carol-lyric searches peak in December, so they need to be in Google's index before then.

```
https://londonchoralservice.com/music-guides/silent-night.html
https://londonchoralservice.com/music-guides/hark-the-herald-angels-sing.html
https://londonchoralservice.com/music-guides/o-come-all-ye-faithful.html
https://londonchoralservice.com/music-guides/once-in-royal-davids-city.html
https://londonchoralservice.com/music-guides/o-little-town-of-bethlehem.html
https://londonchoralservice.com/music-guides/the-holly-and-the-ivy.html
```

**29 Oct, these seven.** PR #379 changed their visible text (contact order, the Birmingham cathedral line, a competitor-price date, and Oxford commas in guide titles). The ten other pages #379 changed (the six carol guides, the two 27 Oct guides, wedding ceremony music, and carol services) are already above and changed again, so request them on their listed days, not twice.

```
https://londonchoralservice.com/funerals.html
https://londonchoralservice.com/weddings.html
https://londonchoralservice.com/facts.html
https://londonchoralservice.com/areas/birmingham.html
https://londonchoralservice.com/music-guides/funeral-music-costs.html
https://londonchoralservice.com/music-guides/index.html
https://londonchoralservice.com/music-guides/christmas.html
```

**Done on 29 Oct (by Claude in Chrome, until Google's daily quota ran out):** the carol services page, the funeral hymns guide, weddings, corporate, Guildford, Liverpool, Reading, Slough & Maidenhead and Rochester were accepted into the priority crawl queue. Chelmsford and Bath were sent in a batch that timed out before the confirmation was seen, so request those two again to be sure. The new versions were live before any request went in.

**30 Oct, these nine.** A 29 Oct pass rewrote the city pages (churches, crematoria and travel), so Google needs the new versions. Winchester and St Albans were refused for quota on 29 Oct.

```
https://londonchoralservice.com/areas/chelmsford.html
https://londonchoralservice.com/areas/bath.html
https://londonchoralservice.com/areas/winchester.html
https://londonchoralservice.com/areas/st-albans.html
https://londonchoralservice.com/areas/chester.html
https://londonchoralservice.com/areas/canterbury.html
https://londonchoralservice.com/areas/salisbury.html
https://londonchoralservice.com/areas/windsor.html
https://londonchoralservice.com/music-guides/weddings.html
```

The sitemap doesn't need resubmitting: the build updated each page's date in it, and Google reads it every few days.

**Done when:** the nine pages above are accepted. About 7 Nov an agent reruns the index-coverage report on these pages and the eleven from 24 Oct. Any page still "Crawled - currently not indexed" then needs a content fix, not another request.

---

## 2. Directory sign-ups

No third-party listing is live yet except Google Business Profile. Google cross-checks listings like these for local rankings, and the marketplaces hold most of the first page for our searches. For each site below you make the account, enter the passwords and codes, accept the terms, and press Publish. Claude can't do any of those, even with your go-ahead. Everything else, Claude does: once you are signed in (in the Claude app's browser, or Chrome with Claude in Chrome), say "fill the Hitched listing from the pack" and it enters every field, uploads the logo and photos, and stops before Publish. Then Claude records the live link.

**Before you start:** sign up with `office@londonchoralservice.com` so leads reach the enquiry inbox. All copy, prices, the tagged website link for each site, and the exact name, phone, hours and service area to use are in `docs/off-site-listings-pack.md`. Use that name, phone number and hours **word for word** on every site: different formats split Google's picture of the business into separate entities. Where a Christmas link is needed, use `christmas.html` (the old `carol-singers.html` is now a redirect). Photos for upload: the five press stills in `~/Pictures/LCS-listings/press/` (full size, 2560 × 1440).

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

## 3. Fix the `www` address at Porkbun

`https://www.londonchoralservice.com` shows a browser security warning (checked again on 24 Oct), because GitHub's certificate covers only `londonchoralservice.com`. Anyone who types `www.` from habit lands on that warning. GitHub closed the support ticket without looking at it: on a free account, Pages support is self-service only. So the fix moves to the domain registrar. Porkbun can redirect `www` to the main address itself, with its own certificate, so GitHub no longer has to serve `www` at all.

**How:**

1. Sign in at https://porkbun.com → **Domain Management** → `londonchoralservice.com` → **DNS**.
2. Find the `CNAME` record for `www` (it points to `lucawetherall.github.io`) and delete it. Don't touch the four `A` records for the main address: they keep the site up.
3. Back in Domain Management, open **URL Forwarding** for the domain and add a forward:
   - **Host:** `www`
   - **Forward to:** `https://londonchoralservice.com`
   - **Type:** Permanent (301)
   - **Include path:** yes (so `www…/weddings.html` lands on `/weddings.html`)
   - **Wildcard:** no
4. Save. Porkbun issues a certificate for the forward on its own; allow up to an hour.
5. Don't change anything in GitHub's Pages settings. It may now say the `www` record isn't set up; that is expected and harmless.

**If Porkbun's forward still shows a certificate warning after a day:** delete the forward too. The `www` address then stops resolving, which is cleaner than a security warning.

**Done when:** `curl -I https://www.londonchoralservice.com/` returns `301` with `location: https://londonchoralservice.com/` and no certificate error. Ask an agent to run that check.

---

## 4. Check the Google Business Profile edits (from 30 Oct)

On 23 Oct Claude made a batch of edits to the profile; Google shows each as "pending review" until it approves it, which can take days. Check they all went through.

**How:** from about 30 Oct, sign in at https://business.google.com/, choose **The London Choral Service**, and check each of these is live:

- **Categories:** Choir (primary) and Wedding service. Google offers no "Funeral service" category (only "Pet funeral service" and "Funeral celebrant service", which would misdescribe a choir), so funerals are carried by the Funeral choir service and the description instead.
- **Description:** the 680-character text from the listings pack.
- **Website:** `https://londonchoralservice.com/?utm_source=google&utm_medium=organic&utm_campaign=gbp`.
- **Service area:** London, Greater London, Surrey, Kent, Essex, Hertfordshire, Berkshire, Buckinghamshire; address hidden.
- **Hours:** Monday to Friday 09:00–18:00, weekends closed.
- **Services:** seven, six at "From £1,150" and Organist and pianist hire at £275 (£250 added to a choir).
- **Photos:** nine. While you're there, add the five press stills from `~/Pictures/LCS-listings/press/` (**Photos → Add photos**), which takes it past the ten Google likes to see.

If an edit was rejected or reverted, tell an agent which and it will redo it in a live chat. Three Christmas posts are already scheduled for 09:00 on 10 Nov, 24 Nov and 8 Dec; you can edit or cancel one under **Posts** before its date.

**Done when:** every item above shows on the public listing. Recheck the categories each quarter in case Google adds a funeral category.

---

## 5. Send four outreach drafts

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

## 6. Ask Kensington and Chelsea how to join their supplier list

The council keeps an approved-suppliers list for weddings at Chelsea Old Town Hall and the Kensington register office (https://www.rbkc.gov.uk/marry-me-in-kensington-and-chelsea/node/733, section "Music and musicians"). It has no choir. The council publishes no email address, only an "Email us" form and the phone number 020 7361 4100, so the application is yours to make.

**How:** ring 020 7361 4100 or use the "Email us" form on that page. Ask how a supplier joins the approved list for music and musicians, and give them `https://londonchoralservice.com/weddings.html`.

**Done when:** you have their answer (a form, a fee, or a no). Tell an agent so it can be recorded.

---

## 7. Link to the private-events page from almaconsort.com

almaconsort.com links only to the London Choral Service homepage (checked 23 Oct). A link to the private-events page helps that page rank, and a planner checking the Alma Consort name finds the right page straight away. Claude can't edit almaconsort.com.

**How:** add a link on almaconsort.com, ideally on its home or contact page, to `https://londonchoralservice.com/private-events.html`, with text such as "Private events and weddings abroad".

**Done when:** the link is live. Tell an agent so it can check it.

---

## 8. Optional: Trustpilot business account

Reviews already come through Google (the enquiry assistant drafts a review request after each paid-in-full event, except funerals, for you to send). Trustpilot would add a second place for reviews, but it isn't needed.

**How, if you want it:** go to https://business.trustpilot.com, sign up with `office@londonchoralservice.com`, and claim "The London Choral Service". Then tell an agent, which adds Trustpilot's link to the review-request drafts. Never offer anything in return for a review: Google and Trustpilot both remove listings for that.

---

## 9. Optional: LinkedIn company page

The page `linkedin.com/company/london-choral-service` doesn't exist. A company page strengthens how Google and AI assistants recognise the business as one entity.

**How:** on LinkedIn, open **For Business → Create a Company Page**, and make a page named "The London Choral Service" (type: company, industry: Entertainment Providers or Musicians; the legal entity is Alma Consort Ltd). Then send an agent the page's address, and it adds it to the site's structured data.

---

## 10. Dates to remember

| When | What | Who |
|---|---|---|
| 25 Oct | Request indexing for the last page (action 1) | you |
| About 28 Oct | Google Ads: check the identity-verification banner has gone (submitted 24 Oct). If Google asks for more, it emails you | you |
| About 31 Oct | Bing Webmaster Tools → **Site Explorer**: check pages are appearing (sitemap index submitted 24 Oct) | you, or tell an agent what you see |
| 30 Oct onwards | Check the Business Profile edits (action 4) | you |
| About 7 Nov | Rerun the index-coverage report on the twenty-five recrawled pages | agent, on your word |
| 10 Nov, 24 Nov, 8 Dec | Scheduled Business Profile posts publish at 09:00 | automatic |
| November | Look again at whether `christmas.html` and the Christmas guides compete for the same Search Console queries (too little data on 14 Oct) | agent |
| **Late January 2027** | **Re-check competitor prices.** Open https://www.londonfuneralsingers.co.uk/pricing and compare each `source_quote` in `data/competitor-pricing.yml` with what is published. Update the figures, the `checked_date` and `compare/london-funeral-singers.html` in the same commit (a figure and its date must never disagree). `build.sh` prints a STALE warning past 120 days. Last checked 23 Oct 2026: every figure unchanged. The file also holds Dream Gospel Choir, Music for London, Julia Charles and Alive Network figures checked 24 Oct, used by no page yet; re-check them too | agent, on your word |
| Each quarter | Re-verify the permit and travel facts on the destination pages (visible checked date: 29 Aug 2026), and check whether Google has added a funeral category for the Business Profile | agent / you |

---

## 11. Web3Forms: restrict the form key to the site and enforce hCaptcha

The site's Web3Forms access key is public by design (it is in every form's HTML). The key should only work from londonchoralservice.com, and Web3Forms should reject any submission without a valid hCaptcha token, so a bot can't post straight to the API and skip the checkbox.

**How:** sign in at https://app.web3forms.com, open the form that sends to office@londonchoralservice.com, and under its settings:
1. Set the allowed domain to `londonchoralservice.com`.
2. Turn on hCaptcha verification (server-side), if it isn't already on.

**Done when:** both settings show as saved. Send a test enquiry from the contact page afterwards to check it still arrives.

---

## 12. Google Ads: hide two old conversion actions

Two legacy conversion actions, "Contact" and "Contact (1)", are still in the account as secondary actions; neither has fired since 19 Sep 2026. Claude tried to set them to Hidden through the API on 26 Oct and Google refused, so it has to be done in the Google Ads screens. Until then the Monday report lists them every week as legacy; they are not a finding.

**How:** sign in at https://ads.google.com/, open **Goals → Conversions → Summary**, and for each of "Contact" and "Contact (1)": open it, set its status to **Hidden**, and save. Hide them; don't remove them, so their history stays.

**Done when:** neither shows in the Summary list with the default filter. Tell an agent, so the report stops listing them.
