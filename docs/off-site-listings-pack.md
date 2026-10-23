# Off-site listings pack

Ready-to-paste copy for the directory listings in `MANUAL-ACTIONS-REQUIRED.md` §2. Rewritten 4 October 2026 to current prices and the owner's choir focus (26 Sep 2026: choir bookings of four or more voices); checked against the site again on 23 October 2026, when the per-site setup steps were added. Soloists are left out on purpose, so these listings don't draw solo-singer requests. Every figure comes from `pricing.html` and `christmas-pricing.html`; every credential is one the site already states. House rules apply off-site too: no roster size, no VAT claims either way beyond "No VAT is added", no star ratings, no incentivised reviews.

## How a listing gets made

Claude can't create accounts, enter passwords or solve CAPTCHAs, even with the owner's go-ahead. For each site the owner does the sign-up (account, email check, any phone or ID check) and stays signed in, in the browser built into the Claude app or in Chrome with Claude in Chrome. Claude then fills every profile field from this pack, uploads the logo and photos, sets categories, service area and prices, and stops before each Publish, Submit or Accept-terms button for the owner's yes. Afterwards Claude checks the listing is live, records its URL in the status table below, and adds it to the Organization `sameAs` on `index.html`.

## Status

| Site | Cost (researched 23 Oct 2026) | Account | Listing live | URL |
| --- | --- | --- | --- | --- |
| Google Business Profile | free | yes | yes (address hidden, service area set) | https://www.google.com/maps?cid=12581882416994311757 |
| Bing Places | free; imports and auto-verifies from the Google profile | no | no (none on Bing Maps, 23 Oct) | |
| Apple Business | free; Apple Account for Work, organisation verified with two proofs | no | no (none on Apple Maps, 23 Oct); brand presence only, no Maps pin | |
| Yell | free listing (paid upsells declined) | no | no (search blocked by a bot check; Luca to search) | |
| Hitched | free storefront | no | no | |
| Bridebook | free Limited Profile after a three-month Basic trial (Basic £20/mo, Classic £99/mo, plus VAT) | no | no | |
| Guides for Brides | free basic listing (paid £14.50–£59.50/mo, plus VAT) | no | no | |
| whiteballoon (funeral) | £20/mo, first month free; "Singers & Musicians" category | no | no | |
| Poptop | free Basic; 12% booking fee, bookings stay on the platform | no | no | |
| Encore | free; 20% of the quote, bookings stay on the platform | no | no | |

Skipped: FuneralGuide (lists funeral directors only), Bark and Add to Event (shared pay-per-lead credits that draw cheap soloist requests). Sign up with office@londonchoralservice.com so leads reach the enquiry inbox.

## Canonical NAP: use verbatim everywhere

| Field | Value |
| --- | --- |
| Business name | The London Choral Service |
| Phone | 07356 042468 |
| Email | office@londonchoralservice.com |
| Website | https://londonchoralservice.com/?utm_source=<site>&utm_medium=referral&utm_campaign=listing, with `<site>` from the table below (`docs/utm-conventions.md`) |
| Address | None shown. We are a service-area business, and the Google profile hides its address. Where a site needs an address to verify the business, give the registered office (Alma Consort Ltd, postcode N1 7GU, as on Companies House) and tick "hide address" or "I serve customers at their location". Never type a Maidenhead or home address, and never invent a street address. |
| Hours | Monday to Friday 9am–6pm, weekends closed (as on `contact.html` and the Google profile) |
| Legal entity | The London Choral Service is a trading name of Alma Consort Ltd (Companies House 16785727) |
| Service area | London, Surrey, Kent, Essex, Hertfordshire, Berkshire and Buckinghamshire (as on the Google profile); further afield on request |

| Site | `utm_source` | Website link to paste |
| --- | --- | --- |
| Bing Places | `bing-places` | `https://londonchoralservice.com/?utm_source=bing-places&utm_medium=referral&utm_campaign=listing` |
| Apple Business | `apple-business` | `https://londonchoralservice.com/?utm_source=apple-business&utm_medium=referral&utm_campaign=listing` |
| Yell | `yell` | `https://londonchoralservice.com/?utm_source=yell&utm_medium=referral&utm_campaign=listing` |
| Hitched | `hitched` | `https://londonchoralservice.com/weddings.html?utm_source=hitched&utm_medium=referral&utm_campaign=listing` |
| Bridebook | `bridebook` | `https://londonchoralservice.com/weddings.html?utm_source=bridebook&utm_medium=referral&utm_campaign=listing` |
| Guides for Brides | `guides-for-brides` | `https://londonchoralservice.com/weddings.html?utm_source=guides-for-brides&utm_medium=referral&utm_campaign=listing` |
| whiteballoon | `whiteballoon` | `https://londonchoralservice.com/funerals.html?utm_source=whiteballoon&utm_medium=referral&utm_campaign=listing` |
| Poptop | `poptop` | `https://londonchoralservice.com/?utm_source=poptop&utm_medium=referral&utm_campaign=listing` |
| Encore | `encore` | `https://londonchoralservice.com/?utm_source=encore&utm_medium=referral&utm_campaign=listing` |

If a site rejects a link with a query string, paste the plain page address instead and note it in the status table.

**Images** (ready on Luca's Mac in `~/Pictures/LCS-listings/`, made 23 Oct 2026 from the site's own files): `logo-1024.png` (the red L monogram, 1024 × 1024), `choir-film-still-1280.jpg` (the choir in church, 1280 × 720) and `christmas-film-still-1280.jpg` (1280 × 720). Real stills of our singers only, never stock or AI images. A cover or banner slot takes a film still; the logo slot takes the monogram.

## Prices to enter (from pricing.html and christmas-pricing.html, checked 23 Oct 2026)

| Ensemble | Price |
| --- | --- |
| Small Choir (4 singers) | from £1,150 |
| Quintet (5 singers) | from £1,400 |
| Sextet (6 singers) | from £1,600 |
| Full Choir (8 singers) | from £2,000 |
| Chorus (12 singers) | from £3,000 |
| Organist or pianist | £250, alone or added to a choir |

December dates cost the same, except Christmas Eve and Christmas Day (around 25% more). No VAT is added. Travel beyond Greater London is quoted with the booking. When a site asks for one "starting price", enter £1,150.

## Google Business Profile

**Primary category:** Choir (or Music Service if Choir is unavailable). **Secondary:** Wedding Service, Funeral Service.

**Description (limit 750 characters):**

> The London Choral Service provides professional choirs for weddings, funerals, memorial services, Christmas carol singing and corporate events in London, the home counties and beyond. A Small Choir of four voices costs £1,150, a sextet £1,600, a choir of eight £2,000 and a twelve-voice chorus £3,000, with an organist or pianist for £250. Our singers trained at the Royal Academy of Music, the Royal College of Music and Britain's other leading conservatoires, and have sung at the coronation of King Charles III, Westminster Abbey and the BBC Proms. Luca Wetherall, Tutor in Music at the University of Oxford, arranges every booking, and you get a written quote before you book.

**Services to list:** Wedding choir · Funeral choir · Memorial service music · Christmas carol singers · Church carol services · Corporate event choir · Organist and pianist hire.

## Encore Musicians profile

**Headline:** Professional choirs for weddings, funerals and carol services

**Bio:**

> We are a small ensemble of professional singers, hand-picked by Luca Wetherall, Tutor in Music at the University of Oxford. Our singers trained at the Royal Academy of Music, the Royal College of Music and Britain's other leading conservatoires, and have sung at the coronation of King Charles III, Westminster Abbey, the Royal Albert Hall and the BBC Proms.
>
> We sing at weddings, funerals, memorials, Christmas carol services and corporate events, as a choir of four voices or a chorus of up to twelve. We plan the repertoire with you, rehearse it, and agree timings with your venue, clergy or funeral director. We sing sacred and classical music, hymns, and pop arranged for voices. If you want a piece we don't yet sing, we can arrange it for your choir, sometimes for an extra charge.

**Pricing:** choirs from £1,150 (four voices) to £3,000 (twelve). Organist or pianist £250. No VAT is added. Travel beyond Greater London is quoted with the booking.

## Poptop profile

**Short pitch:**

> Professional choirs for weddings, funerals and Christmas events. At a funeral, four voices lead the hymns and sing during the service, and we can often help at short notice. At a wedding we sing from the processional to the recessional. In December our a cappella carol singers perform at offices, hotel lobbies and residents' evenings. Our singers' credits include the coronation of King Charles III and the BBC Proms. Choirs from £1,150, with a written quote before you book.

## Bark / Add to Event (short bio; skipped for now, kept for reference)

> The London Choral Service provides professional choirs for weddings, funerals and Christmas events in London and the home counties. Our singers trained at the Royal Academy and Royal College of Music, and we carry public liability insurance. Choirs start at £1,150 for four voices, and you get a written quote before you book.

## Hitched profile

**Headline:** Wedding choirs, from four voices to a twelve-voice chorus

**About:**

> We sing church and civil weddings: the processional as you walk in, hymns your guests can follow, an anthem while you sign the register, and a recessional as you leave. Our singers trained at the Royal Academy of Music, the Royal College of Music and Britain's other leading conservatoires. Luca Wetherall, Tutor in Music at the University of Oxford, picks the singers and plans the music with you.
>
> We sing in churches and licensed venues across London, the home counties and beyond. We talk to your organist, vicar or coordinator, and arrive early and rehearsed. Our repertoire runs from Renaissance motets to pop arranged for voices. If you want a piece we don't yet sing, we can arrange it, sometimes for an extra charge.

**Price guide:** a Small Choir of four voices costs £1,150, a sextet £1,600 and a choir of eight £2,000. Add an organist for £250. No VAT is added; travel beyond Greater London is quoted with the booking.

## Bridebook profile

> Professional wedding choirs, from four voices to a twelve-voice chorus, for church and civil ceremonies. Our singers have sung at the coronation of King Charles III, Westminster Abbey and the BBC Proms. We plan the music with you, from sacred classics to pop arranged for choir. A Small Choir of four costs £1,150 and a choir of eight £2,000, and you get a written quote before you book.

## whiteballoon and other funeral directories

> We provide professional choirs for funerals, memorials and committals in London and the home counties. Four voices lead the hymns and sing during the service; a larger choir suits a full church. We take bookings at short notice, and agree timings and the order of service with the funeral director and clergy. A Small Choir of four costs £1,150. The family normally pays us directly, and we can send the invoice to whomever the funeral director nominates.

## Short description (Yell, Apple Business, and any site with a short "About" box)

> The London Choral Service provides professional choirs for weddings, funerals, memorial services, Christmas carol singing and corporate events in London, the home counties and further afield. A Small Choir of four voices costs £1,150, and an organist or pianist £250. Our singers trained at the Royal Academy of Music, the Royal College of Music and other leading conservatoires. No VAT is added. The London Choral Service is a trading name of Alma Consort Ltd.

(461 characters.) Where a site allows more, use the Google Business Profile description above (680 characters).

## Per-site setup (researched 23 Oct 2026)

Order: Bing, Apple, Hitched, Bridebook, then Yell and Guides for Brides. Each sign-up uses office@londonchoralservice.com and 07356 042468. Luca does every step marked **(Luca)**: making the account, passwords, codes sent by text, email or phone, accepting terms, and the final Publish or Submit. Everything else Claude can fill once Luca is signed in, in the browser built into the Claude app. Before each sign-up, search the site for "London Choral Service" so it doesn't create a duplicate. On 23 Oct, Bing Maps and Apple Maps had no listing for us; Yell's search sits behind a bot check, so Luca searches it himself.

### 1. Bing Places (about 10 minutes; imports from Google)

Bing feeds Copilot, ChatGPT search and Alexa, so it matters more than its share of searches suggests.

1. **(Luca)** Go to `https://www.bing.com/forbusiness/` (bingplaces.com redirects there). Click **Sign in** and use a Microsoft account; make one with office@londonchoralservice.com if needed. Accept Microsoft's terms.
2. **(Luca)** Choose **Import from your Google Business Profile**, sign in to the Google account that owns the profile, and allow Bing to read it.
3. **(Luca)** Pick a sync schedule (**Weekly** is best) and import the listing Bing finds.
4. Bing verifies an imported listing on its own when the Google profile is verified. It goes live in 7 to 12 days.

What comes across: name, address setting, phone, hours, photos and the description. A synced listing can't be edited in Bing: change the Google profile and Bing follows at the next sync. That has two side effects to accept. The website link arrives with the Google tag (`utm_source=google ... utm_campaign=gbp`), so Bing visits show as Google Business Profile visits in GA4. And the category may not match; Bing has no exact "Choir", so check it reads Musician or Entertainment, not something unrelated.

After it goes live, open the listing on Bing Maps and check the address is hidden (city and postcode only at most). If Bing shows a street address, unlink the sync and set **Basic details → "Are customers expected to visit your address?" → No**, then enter the service areas by hand (London, Surrey, Kent, Essex, Hertfordshire, Berkshire, Buckinghamshire) and the website link from the table above.

### 2. Apple Business (about 20 minutes, then up to 5 working days)

Apple renamed Business Connect to Apple Business; `businessconnect.apple.com` redirects to `https://business.apple.com`. There is no import from Google.

The catch: an Apple Maps place card needs a map pin on a building customers visit, and Apple has no hide-address setting. We have no premises, and the registered office is not where clients meet us, so **don't add a Maps location**. Use Apple's brand presence instead, which Apple offers to businesses without a physical location: Apple's brand features (Branded Mail, Business Caller ID) can show our name and logo to iPhone users. If Apple later adds service areas, revisit this.

1. **(Luca)** Go to `https://business.apple.com` → **Sign up now**. Choose **Create an Apple Account for Work** (a personal Apple Account gets only some features). Enter Alma Consort Ltd as the organisation, your legal name and a password; leave the agency box unticked. Enter the codes Apple texts and emails. Click **Agree** to the terms.
2. **(Luca)** Verify the organisation within 60 days. Apple needs two proofs. Two that fit us: a D-U-N-S number (free from Dun & Bradstreet UK, if Alma Consort Ltd has one), and a DNS TXT record on londonchoralservice.com (Apple shows the record; you or Claude add it at the domain registrar, once you're signed in there). If neither fits, an official document such as the Companies House certificate of incorporation. If Apple doesn't approve the organisation within 60 days, it deletes it.
3. Once verified, in **Brands**, add the brand: display name **The London Choral Service** (no ® or ™), logo `logo-1024.png`, website `https://londonchoralservice.com/?utm_source=apple-business&utm_medium=referral&utm_campaign=listing`, phone 07356 042468, and the short description above for any About field.
4. **(Luca)** Submit the brand for review.

### 3. Hitched (about 15 minutes)

1. **(Luca)** Go to `https://www.hitched.co.uk/business-login/` → **Create your free listing**.
2. Fill: **Name of the business** The London Choral Service · **Town/City** London · **Select a group** Wedding Suppliers · **Main business category** Music and DJs (Hitched has no choir or singer category) · **Phone number** 07356 042468 · **Email** office@londonchoralservice.com (Hitched publishes it as the contact address).
3. **(Luca)** Choose a username (lower case, at least five characters) and a password, tick **I accept Hitched's Terms of Use and Privacy notice**, and click **Create your account**. Confirm the email if Hitched sends one.
4. In the storefront editor: **Headline**, **About** and **Price guide** from "Hitched profile" above; website `https://londonchoralservice.com/weddings.html?utm_source=hitched&utm_medium=referral&utm_campaign=listing`; photos `choir-film-still-1280.jpg` first, then the logo; service area London and the home counties. If a field asks for a single starting price, enter £1,150.
5. Decline any paid upgrade. **(Luca)** Publish.

### 4. Bridebook (about 15 minutes)

Bridebook starts a free three-month trial of its paid Basic plan (no card). After that, Basic costs £20 a month plus VAT; let it lapse and the listing becomes the free Limited Profile, which shows lower in searches. Decline Classic (£99 a month).

1. **(Luca)** Go to `https://business.bridebook.com/signup`. Enter **Business name** The London Choral Service, **Country** United Kingdom, **Website** `https://londonchoralservice.com/weddings.html?utm_source=bridebook&utm_medium=referral&utm_campaign=listing`, phone and email → **Proceed to step 2 of 2**.
2. **(Luca)** If step 2 asks for an address, use the registered-office postcode N1 7GU (Bridebook allows one account per postcode) and hide the street line if it offers that. Open the activation email and set the password.
3. In **Improve Profile**: category **Music**; description from "Bridebook profile" above; photos as for Hitched; prices from the table above (starting price £1,150). Bridebook's progress sliders rise as each section fills, which lifts the listing in its search.
4. **(Luca)** Accept any terms and publish. Put a reminder in the diary for the trial's end (three months after sign-up) to decide whether to keep Basic.

### 5. Yell (about 15 minutes; expect a sales call)

1. **(Luca)** Search `https://www.yell.com` for "The London Choral Service" first. If a listing exists, click **More Info** → **Claim Business** → **Claim this business**. If not, go to `https://www.yell.com/free-listing/`.
2. Step 1 of 3: **First name** and **Last name** (Luca's) · **Business name** The London Choral Service · **Postcode** N1 7GU · **Business phone number** 07356 042468 · **Email** office@londonchoralservice.com → **Continue**. Yell publishes what you enter here.
3. Next steps: choose the address (or **Add manually**) and hide it if Yell offers that; classification: the closest of Choirs, Musicians or Entertainers (Yell accepts only its own list); years trading and legal status (limited company, Alma Consort Ltd). Description: the short description above. Website: the Yell link from the table above. Hours: Monday to Friday 9am–6pm.
4. Yell offers to send your details to Apple, Alexa and Microsoft. Untick that, since Bing and Apple get their own listings and a second copy can make a duplicate.
5. **(Luca)** Accept the terms and submit. A moderator checks it and Yell emails when it's live. Decline the paid products on the follow-up call.

### 6. Guides for Brides (about 10 minutes)

1. **(Luca)** Go to `https://guidesforbrides.co.uk/free-advertising` → **Add your business** → enter office@londonchoralservice.com → **Get Started**. It first looks for an existing record of the business.
2. Category **Discos, DJs & Live Music** (no choir category). Counties: London, Surrey, Kent, Essex, Hertfordshire, Berkshire, Buckinghamshire. Description:

> We sing church and civil weddings in London, the home counties and further afield: the processional, hymns your guests can follow, an anthem while you sign the register, and the recessional. Our singers trained at the Royal Academy of Music, the Royal College of Music and other leading conservatoires. We plan the music with you, from Renaissance motets to pop arranged for voices. A Small Choir of four costs £1,150 and a choir of eight £2,000, with an organist for £250. No VAT is added, and you get a written quote before you book.

3. Website: the Guides for Brides link from the table above. Photos as for Hitched.
4. Stay on the free basic listing (paid tiers run £14.50 to £59.50 a month plus VAT, and only move the listing up the search). **(Luca)** Accept the terms and submit.

### After each listing goes live

Send Claude the listing's URL. Claude checks the name, phone, hidden address, prices and link against this pack, records the URL in the status table, and adds it to the Organization `sameAs` on `index.html`. When all six are live, Claude runs the BrightLocal free listings scan in MANUAL §2, with Luca's go-ahead (it submits a form).

## GBP seasonal posts

Christmas 2026, drafted 23 Oct. Post type **Update**, button **Learn more**. Prices from `christmas-pricing.html`; no phone number in the text (the profile has a Call button). Photos must be real stills of our singers.

**1. Christmas prices, post on 27 Oct.** Photo: the It's the Most Wonderful Time of the Year still (`assets/films/hero-christmas-1280.webp` as a JPG). Link: `https://londonchoralservice.com/christmas-pricing.html?utm_source=google&utm_medium=organic&utm_campaign=gbp`

> Christmas carol singers in London cost £1,150 for four voices and up to two hours of singing, breaks included, and a December date costs the same as one in June. A quintet is £1,400, a sextet £1,600, a choir of eight £2,000 and a chorus of twelve £3,000. Each price covers rehearsals, sheet music and travel within Greater London, and we add no VAT. Christmas Eve and Christmas Day carry a premium of around 25%. Send us your date and venue and we reply within one working day with a written quote.

**2. Church carol services, post on 10 Nov.** Photo: a still from the Once in Royal David's City film. Link: `https://londonchoralservice.com/christmas-carol-services.html?utm_source=google&utm_medium=organic&utm_campaign=gbp`

> We sing carol services in churches and livery halls across London. A choir of eight with an organist costs £2,250. For a large church, a chorus of twelve with an organist costs £3,250 and can lead a full congregation. Luca Wetherall, our Artistic Director and Tutor in Music at the University of Oxford, chooses the carols with you, and the booking runs the length of the service however the readings fall. Our carol services page has a film of the choir singing Once in Royal David's City.

**3. Office and hotel carol singers, post on 24 Nov.** Photo: a still from the Ding Dong! Merrily on High or Winter Wonderland film. Link: `https://londonchoralservice.com/christmas.html?utm_source=google&utm_medium=organic&utm_campaign=gbp`

> Four unaccompanied carol singers carry across an office drinks reception or a hotel lobby without a microphone. Over two hours they sing three or four sets of about twenty-five minutes, with breaks so your guests can talk. A Small Choir of four costs £1,150. Add a pianist for £250 to play between the sets, £1,400 in all. The singers dress to suit the room, in concert dress, all black or Christmas jumpers, and Luca plans the sets around your running order, from arrivals to the speeches.

**4. December dates, post on 8 Dec.** Photo: a still from the Carol of the Bells film. Link: `https://londonchoralservice.com/christmas-pricing.html?utm_source=google&utm_medium=organic&utm_campaign=gbp#enquiry`

> December carol bookings cost the same as bookings in any other month. A Small Choir of four costs £1,150 for up to two hours, and only Christmas Eve and Christmas Day carry a premium. Send us the date, the venue and a rough idea of numbers, however close the date is. We confirm whether we can take it and send a written quote within one working day.

## Review-request emails (MANUAL §3)

The enquiry assistant drafts these itself. Step c of `.claude/agents/lcs-daily-pass.md` holds the wording: a request 2–14 days after a paid-in-full event, with a couple, a business, and a planner and venue version, then one reminder 7–14 days later. Funeral clients are never asked. For a hand-sent request (a booking from before the pipeline), use the couple version:

> Dear [first name],
>
> Thank you for having us at your wedding on [date]. [One sentence about the day, if there is one to say.]
>
> If you have a minute, would you write a Google review? Couples planning their own weddings read them, and a sentence or two is plenty: https://g.page/r/CU3erYZl05uuEBM/review
>
> Best wishes,
>
> Luca

Ask everyone who booked in the same words, whatever you think they made of the day. Never ask only the clients you expect to be happy.

## Rules that apply off-site (from the house claim gates)

- Never state a roster size ("150+ singers" is a competitor's line and a banned claim).
- Alma Consort Ltd is not VAT-registered. Say "No VAT is added"; never "prices include VAT", "include all fees and taxes" or "plus VAT".
- No star-rating or "5-star" claims anywhere.
- Quote only figures on `pricing.html`, and update every listing in the same pass whenever those prices change.
- London cathedrals and Westminster Abbey: name them only as places the singers have sung, never as choirs we join or add voices to.
- No incentives for reviews, ever: both Google and Trustpilot delist for it.
