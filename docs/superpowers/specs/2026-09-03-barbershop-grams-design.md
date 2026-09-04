# Barbershop Grams — design doc

**Date:** 2026-09-03
**Author:** Luca Wetherall (with Claude)
**Status:** Draft for review
**Related:** [docs/superpowers/specs/2026-08-18-competitive-capture-design.md](2026-08-18-competitive-capture-design.md) (the `compare/` model this reuses), [docs/superpowers/specs/2026-08-26-private-events-design.md](2026-08-26-private-events-design.md) (the register-insulation model this reuses), [pricing.html](../../../pricing.html), `data/competitor-pricing.yml`, [MANUAL-ACTIONS-REQUIRED.md](../../../MANUAL-ACTIONS-REQUIRED.md)

---

## Goal

Launch a second product line, **Barbershop Grams**: four singers sent as a gift to surprise one person, wherever they are, with Happy Birthday in four-part harmony and a song chosen for them. Birthday is the flagship occasion; romantic surprises, proposals, and office send-offs follow it.

The line competes with Barbershop-o-gram (`barbershopogram.co.uk`), the established London barbershop quartet, for the surprise-singing market. We match them on exactly one thing, the price of their entry product (£600 for up to ten minutes), and beat them on the product itself: response time, a 48-hour notice commitment, a published repertoire, ensemble sizes a fixed quartet cannot offer, a named Artistic Director, and, once filmed, better video.

**Success metric:** enquiries tagged `barbershop-gram` per month, then cost per enquiry once ads run. Traffic is not the metric.

## Owner decisions, recorded so the plan does not relitigate them

| Decision | Outcome |
|---|---|
| Genre claim | Barbershop-led. The product is branded and sold as barbershop; the repertoire underneath is any four-voice a cappella arrangement, standard or bespoke. |
| Pricing | Price-match **only** the £600 ten-minute gram. Every other tier is priced on our own terms (§Product). |
| The competitor's other tiers | Never mentioned, on any page, with or without a number. Enforced structurally (§Claims integrity). |
| Separation from the site | Full: own directory, own register, own nav and footer. The main site links in from the Services dropdown only. |
| Notice | We commit to 48 hours. |
| Repertoire | A published list. Drafted in this document; the Artistic Director confirms every title before it goes live. |
| Video | Recordings are forthcoming and will be the product's main proof. A barbershop listen page is planned for when they exist. |
| Cheaper non-barbershop gram | No. Four voices or it is not a Barbershop Gram. |
| Nav prominence | **No nav entry at all** (owner decision, 2026-09-03, revised during implementation). `partials/nav.html` expands into every page, so a Services-dropdown entry cannot be withheld from `funerals.html`, the funeral guides, the `for-*.html` pages or `compare/london-funeral-singers.html`. "Dropdown only, never on funeral pages" was not satisfiable with one shared nav, and the owner chose to drop the entry rather than show a birthday-gift product to a bereaved visitor. Reachable instead from `services.html`, `pricing.html`, `weddings.html` and `corporate.html`. |
| Directories | Yes, as a human action (§Go-to-market). |
| Domain | Subdirectory on the main domain, not a subdomain. Domain authority carries into the new pages; the register does the brand separation. |

## Non-goals

- **A cheaper gram.** A £250 soloist singing Happy Birthday would undercut the product's identity. The FAQ says so.
- **Any claim about the competitor beyond one published price and its inclusion line.** Not their other tiers, not their travel policy, not their responsiveness, not their site. The tip-off that prompted this work stays out of print; it only tells us where to lead.
- **A VAT comparison.** Their prices page shows a bare "£600" to consumers, with no VAT statement or VAT number anywhere on their site. UK price-marking rules require consumer-facing prices to include VAT, so £600 is the buyer's cost either way and there is no delta to claim in either direction. An inc-VAT figure invented for them would be the one unsourced claim on an otherwise sourced page. Note that this is the opposite situation to the funeral-singers comparison, where the competitor quotes "+ VAT" and the delta is the whole argument.
- **Online payment.** The site is static with no backend. Enquiry-to-written-quote, as everywhere else. A gift certificate PDF covers the "give it as a present" case (§Go-to-market).
- **Per-occasion landing pages in phase 1.** They are phase 3, triggered by Search Console data, not built on speculation.
- **Any mention on `funerals.html`, the funeral guides, `compare/london-funeral-singers.html`, or any `for-*.html` page.** A bereaved family must never meet a birthday gram.
- **Review or rating schema.** Prohibited site-wide.
- **A product name resembling "Barbershop-o-gram".** Naming them for comparison is lawful; trading under a near-identical name is passing off. The product is "Barbershop Grams".
- **Testimonials.** None exist for this product. None are invented. The first real quote goes on the page when a real client gives one.

---

## Competitive position: the facts

Retrieved from `https://www.barbershopogram.co.uk/` and `/prices` on 2026-09-03. Only the first row below may ever be published; the appendix records the rest for the quarterly re-check.

| Item | As published |
|---|---|
| Entry product | "Up to 10 minutes (including Happy Birthdays)" · "£600" |
| Inclusions line | "All fees include music from our standard repertoire and include travel within London zone 5 unless otherwise stated." |
| VAT | No VAT statement and no VAT number anywhere on the site — `/`, `/prices`, and no `/terms`, `/faq`, or `/about` page exists (checked 2026-09-03). Treated as consumer-inclusive: £600 is what a buyer pays. |

### Where we differ, stated as facts about us

| | Barbershop-o-gram | Barbershop Grams |
|---|---|---|
| Ten-minute gram | £600 | £600 |
| Notice | Not published | 48 hours |
| First reply | Contact form | WhatsApp, usually the same day |
| Repertoire | Linked list | Published page, with the option of any song arranged from £200 |
| Ensemble | A quartet | Four voices as standard; eight or twelve by quotation |
| Musical leadership | Not published | Luca Wetherall, Artistic Director, Tutor in Music, University of Oxford |
| Occasion pages | One page | Birthday-led hub now; occasion pages in phase 3 |

The right-hand column is entirely ours to state. Nothing in the left-hand column is published except the price, which is why the comparison page compares only the price.

---

## Product

### Pricing

| Tier | Price | What it is |
|---|---|---|
| Surprise Barbershop Gram | **£600** | Up to ten minutes. Four singers find the person, sing Happy Birthday (or the occasion's equivalent) in four-part harmony, then one song from the repertoire chosen for them, with their name worked in. |
| Half-hour set | from £800 | Three or four songs for one occasion, or a roaming set that reaches several people across an office or a party. |
| One-hour set | from £1,200 | A programme of eight to ten songs with a break. Drinks receptions, garden parties, company summer dos. |
| Bespoke arrangement | from £200 | Their song, arranged for four voices in 24 hours. Add it to any tier. |
| Video recording session | from £1,000 | A filmed performance for someone who is not in London, or for a company video. Licence agreed per use. |

Rules:

- The £600 is **flat**, not "from". It is the matched figure and a "from" would not be a match.
- Travel within Greater London is included, in the site's existing words. Outside Greater London we quote travel in the written quote before the client commits.
- No VAT is added, in the site's existing words.
- Longer sets are described by what they contain, never as "more minutes". A buyer with the competitor's price list open will do per-minute arithmetic on a duration ladder; they will not on a programme.
- Larger ensembles (eight, twelve) are quoted individually. The existing size-based prices on `pricing.html` are for full services, not a ten-minute visit, and must not be reused here.

### Included with every gram

A one-to-one conversation with Luca about the person and the song · the singers' preparation and any sheet music · a phone call to whoever is on the inside the day before · travel within Greater London · a written quote that is the whole cost.

### Notice and rescheduling

48 hours' notice. One rescheduling at no charge if we hear before the singers set off; after that the fee stands. (Owner may adjust; the plan implements whatever this table says at the time.)

### Where `pricing.html` fits

**It does not.** Gram prices never appear on `pricing.html` (owner decision, 2026-09-03, revised during implementation): barbershop is sold separately from the choral service, and the bookings are almost always for a quartet, so mixing its rates into the choral price list works against the separation the rest of this design maintains.

A section was added there during implementation and then removed. **`barbershop-grams/index.html` is the source of truth for the five gram prices**, and `pricing.html` remains the source of truth for choral prices — singers, choirs, instrumentalists, Christmas. The CLAUDE.md convention was rewritten to carve this out rather than left to imply the old rule.

The main site still links to the mini-site from `services.html`, `weddings.html` and `corporate.html`, but those links carry no figures, so they do not reintroduce the mixing.

---

## Architecture: a second register

### Directory

```
barbershop-grams/
  index.html        phase 1   the hub
  repertoire.html   phase 1   the published list
  listen.html       phase 2   when videos exist
  birthday.html     phase 3   occasion pages, on Search Console evidence
  valentines.html   phase 3
  proposals.html    phase 3
  office.html       phase 3
compare/
  barbershopogram.html   phase 2   stays under compare/ because the validator globs it
```

Canonical URLs use the directory form: `https://londonchoralservice.com/barbershop-grams/`.

### Partials

Three new partials, mirroring the private register exactly:

- `partials/barbershop-register.css.html`: a `<style>` block whose **first inner line is a comment** naming this document. That comment is what stops `build.sh` Pass A mistaking the block for the site bundle. Contains its own tokens, the two self-hosted `@font-face` rules copied from `css/base.css`, and every style the mini-site uses.
- `partials/barbershop-nav.html`: wordmark "Barbershop Grams", links to Occasions (anchor), Repertoire, Pricing (anchor), and a WhatsApp button.
- `partials/barbershop-footer.html`: contact line, "Barbershop Grams is a product of The London Choral Service" linking to `/`, company line, privacy link.

Every page in `barbershop-grams/` and the comparison page carry `partials/head-extras.html` (font preloads), the GA4/Ads snippet (duplicated inline as on every page), and the three partials above. **They never carry `partials/nav.html`, `partials/footer.html`, or a `style.css` link.** Both mistakes are one build away from shipping the whole site bundle onto the page; the idempotency check (second `./build.sh`, empty diff) is the tripwire.

### Visual register

Same two typefaces as the site, so no new font assets. A different palette and a different class prefix (`bs-`), so nothing collides with the site bundle or the `pe-` private register. Proposed tokens, scoped to the partial and nowhere else:

| Token | Role |
|---|---|
| `--bs-paper` `#FBF7EF` | page ground |
| `--bs-ink` `#1F1A17` | text |
| `--bs-red` `#B3261E` | accent: buttons, rules, small caps |
| `--bs-navy` `#1F3A5F` | second accent: occasion labels, table heads |
| `--bs-cream` `#F1E9DA` | alternating section field |

Warm and well-made, not a striped-waistcoat pastiche. No barber's-pole motif. The register should read as a gift you would be pleased to have chosen, and it should not read as the choir that sings at funerals.

### Linking, asymmetric on purpose

**Main site → mini-site** (in):
- **Not the nav.** See the Nav prominence row above: a shared nav partial reaches every page including the funeral surfaces, so there is no nav entry.
- `services.html`: a short note **after** the ensemble grid (not a card inside it — the grid is a size ladder from soloist to twelve-voice chorus, and a gram is not a point on that scale), plus a `Gifts & Surprises` `OfferCatalog` in the page's JSON-LD, sibling to `Choirs & Singers` and `Instrumentalists`.
- `pricing.html`: **nothing.** Gram prices are deliberately kept off it — see the Product section. It is not an inbound link either.
- `weddings.html` and `corporate.html`: one in-copy sentence each ("a barbershop quartet for the drinks reception"), because "barbershop quartet hire London" is a head term the hub should also win.
- Never from `index.html`'s hero, `funerals.html`, any funeral guide, `private-events.html`, `destinations/`, or any `for-*.html`.

**Mini-site → main site** (out):
- The footer attribution line only. A gram buyer may want a wedding choir next year; the door stays open one way.
- The privacy-policy link in the same footer line does not count against this and must stay: these pages carry the site-wide GA4/Google Ads snippet, there is no cookie banner anywhere on the site, and `privacy.html` is the single page every other footer points to for cookie disclosure. The rule is about funnel links, not legal ones.

**Comparison page**: linked from the hub's FAQ and the mini-site footer only. Not from the main-site footer, where it would sit beneath `funerals.html`.

### Validators to extend (plan items, all mandatory)

- `validate_house_claims.py`: its `FILES` list is explicit and does not include a new directory. Add `barbershop-grams/*.html`.
- `validate_jsonld.py`: confirm its glob covers `barbershop-grams/`; extend if not (the `compare/` precedent needed this).
- `scripts/generate_llms_full.py`: confirm the new directory is picked up.
- `validate_competitor_claims.py`: **must be patched** to support `price_inc_vat` before the new provider entry lands. It reads `pkg["price_ex_vat"]` unconditionally, so a package without that key raises `KeyError` and breaks the build. See §Claims integrity.

---

## Page 1: the hub, `barbershop-grams/index.html`

**Title:** `Barbershop Grams | Surprise Barbershop Quartet in London`
**Meta description (verify 141–161):** `Send a surprise barbershop quartet to someone in London: Happy Birthday in four-part harmony at their desk, door, or table. £600 all in, 48 hours' notice.`

**Schema:** `Service` (provider: the existing Organization) with one `Offer` at £600 GBP (LCS's own price, so `Offer` is correct), `FAQPage` matching the visible FAQ string-for-string, `BreadcrumbList`. No `Offer` for the "from" tiers; a "from" price is not an offer.

### Sections, with draft copy

Draft copy is the register to hit, not final text. Every line goes through `writing-site-copy` and `stop-slop` again at implementation.

**1. Hero**
> **A barbershop quartet at the door, singing Happy Birthday to someone who had no idea.**
> Four voices in harmony, wherever the person is: the office, the kitchen, a restaurant table. £600 all in within Greater London, booked with 48 hours' notice.
> [Send a gram on WhatsApp] [See the repertoire]

**2. Occasion strip** (six labels, birthday first and larger): Birthday · Valentine's · Proposal · Leaving do · Anniversary · Just because

**3. The surprise birthday gram** (flagship, the longest section)
> You tell us where they will be and when. Four singers arrive, find the right person, and sing Happy Birthday in four-part harmony, then one song chosen for them from our repertoire, with their name worked in. Ten minutes from the first note to the last.
> It works in an open-plan office, a kitchen at breakfast, or a restaurant table between courses.
> Fortieths, fiftieths, and eightieths get the same four voices. Tell us the age and the singers will work that in too.

**4. For someone you love**
> Valentine's Day, an anniversary, or a Tuesday. *Hello! Ma Baby*, *Let Me Call You Sweetheart*, and *I Love You Truly* are in the repertoire. If you have a song that is yours, we arrange it for four voices from £200; the singers learn it in 24 hours, inside the usual 48 hours' notice.

**5. Proposals**
> We arrive before you ask, sing while you get the ring out, and leave the room to the two of you. If it goes well, we also do weddings.

**6. Leaving dos, promotions, work anniversaries**
> A quartet across the desk from someone on their last day. Bigger floor? We can send eight or twelve voices instead of four. Ask for a quote.

**7. How it works** (four numbered steps, matching the `pricing.html` process block's shape)
1. Message us on WhatsApp with the date, the place, and who it is for.
2. We confirm within the day and send a written quote.
3. You tell us the song, the name, and anything the singers should know.
4. We turn up and sing.

**8. Making sure the surprise lands** (checklist; the section no competitor has)
- Someone on the inside who knows: a receptionist, a manager, a flatmate.
- A ten-minute window when the person will be in one place.
- Access: building sign-in, a table booking, a gate code.
- A phone number for the day that is not the recipient's.
- Whether you want it filmed, and by whom.

**9. Pricing**: the table from §Product, then: "Every price is the whole price. We do not add VAT. Travel within Greater London is included; outside it, we quote travel before you commit."

**10. Repertoire teaser**: six or eight titles and a link to `repertoire.html`.

**11. FAQ** (visible accordion and `FAQPage`, identical strings)
- *How much notice do you need?* 48 hours. Ask early for Valentine's week and December, the busiest dates in our year. (State this as a request, never as an observation about how fast grams book: the product has no trading history to support a demand claim. December is separately supportable from the existing business — `christmas.html` already says most years the December dates go by mid-September.)
- *Where will you sing?* Anywhere within Greater London we can get four singers into: offices, homes, restaurants, parks, care homes, hospital wards with the ward's permission.
- *What if they are not there?* We rearrange once at no charge if you tell us before the singers set off. After that the fee stands.
- *Is it a surprise?* Only if you keep it. We contact the number you give us and no other.
- *Can you sing our song?* Yes. We arrange it for four voices from £200. The singers learn it in 24 hours, inside the usual 48 hours' notice.
- *Can we film it?* Yes, and we would like a copy. We ask the recipient before anything is posted.
- *Is there a cheaper version?* No. A Barbershop Gram is four voices. A soloist is a different thing and we do not sell it as a gram.
- *Who sings?* Singers chosen for the booking by Luca Wetherall, our Artistic Director and Tutor in Music at the University of Oxford.

**12. Enquire**: WhatsApp button with a gram-specific pre-fill (`?text=Hello, I'd like to send a Barbershop Gram. Date: / Place: / Who it's for:`), phone, and the register's own enquiry form. The pre-fill text is distinct from the site-wide one so gram WhatsApp clicks are distinguishable in analytics. WhatsApp stays the primary route; the form is there for the buyer who would rather write it down.

### The enquiry form

The register hosts its own Web3Forms form, the way `private-events.html` and `destinations/` do, and links to `contact.html` from nowhere. Sending a gift buyer to the main contact page put them on a form that opens on "your occasion" and lists Funeral first, which is the wrong room for a birthday present.

Fields: name, email, telephone, date, place, who it is for, and a free-text note. A hidden `product` field marks the enquiry as a Barbershop Gram in the Web3Forms inbox, since grams are quoted from their own price list. The honeypot and the `h-captcha-response` guard stay, as they must on every form on this site.

The handler is inline, not `/js/form.js`. `form.js` binds to the main site's `.contact-form` markup and finishes by redirecting to `/thank-you.html`, which carries main-site chrome; the register confirms in place instead, as `private-events.js` does. `/js/nav.js` is never loaded here for the same reason. The only external script the register loads is the Web3Forms client, which renders the hCaptcha widget. Without JavaScript the plain POST redirects back to `#bs-form-success` on the hub and a `:target` rule reveals the confirmation, so even the fallback keeps the buyer inside the register.

`contact.html` keeps its `<option value="barbershop-gram">Barbershop Gram / surprise</option>`: someone who reaches the main form by another route still needs a way to say what they want.

---

## Page 2: the repertoire, `barbershop-grams/repertoire.html`

The competitor links to a repertoire list. Ours is a page, indexed, because "barbershop quartet songs" and "songs for a singing birthday surprise" are queries.

**Rules:** titles only, never lyrics. Live performance licensing sits with the venue's PRS cover where one applies; the page does not discuss it. Group by occasion so a buyer can scan for their case.

**Draft list. The Artistic Director confirms every title before publication and removes anything the singers have not rehearsed. Nothing below is a claim until then.**

| Group | Titles |
|---|---|
| Birthday and celebration | Happy Birthday to You (four-part) · For He's a Jolly Good Fellow · When You're Smiling · Side by Side · Ain't She Sweet · Bye Bye Blackbird |
| Love songs | Hello! Ma Baby · Let Me Call You Sweetheart · I Love You Truly · Heart of My Heart · Sweet Adeline · Down by the Old Mill Stream · Can't Help Falling in Love · L-O-V-E · Only You |
| Barbershop classics | Coney Island Baby · Wait 'Til the Sun Shines, Nellie · In the Good Old Summertime · Shine On, Harvest Moon · By the Light of the Silvery Moon · Daisy Bell · Bill Bailey, Won't You Please Come Home · Goodnight, Sweetheart, Goodnight · Sweet Georgia Brown · Yes Sir, That's My Baby · Five Foot Two |
| Doo-wop and later | Mr Sandman · Lida Rose · Sh-Boom · Blue Moon · Under the Boardwalk · Stand By Me |
| Leaving dos | Show Me the Way to Go Home · We'll Meet Again · Hit the Road Jack · Auld Lang Syne |
| Christmas | Jingle Bells · Winter Wonderland · Let It Snow · White Christmas · Silent Night · Deck the Halls · Have Yourself a Merry Little Christmas |

Closing line: "Not here? We arrange any song for four voices from £200."

**Title:** `Barbershop Gram Repertoire | Songs for a Surprise Quartet`. Schema: `ItemList` of the titles is acceptable; `BreadcrumbList`.

---

## Page 3: the comparison, `compare/barbershopogram.html` (phase 2)

Built **after** a barbershop recording exists. A comparison page whose proof is a funeral hymn hurts more than no page.

Uses the barbershop register, not the site chrome, because a reader arriving from a search for the competitor's name is a gift buyer and should land in the gift register.

**Title:** `Barbershop-o-gram vs London Choral Service: Prices`
**Meta (verify 141–161):** `Comparing barbershop quartet prices in London? Barbershop-o-gram's ten-minute gram and ours cost the same, £600. Here is what each one includes.`

### The page compares exactly one thing

1. **Opening.** Two sentences: you are comparing two quartets for a surprise; the entry product costs the same from both; this page says what each includes.
2. **The table.** One row. Their "Up to 10 minutes (including Happy Birthdays)" at "£600", quoted verbatim, against our Surprise Barbershop Gram at £600. Beneath it: *Price as published at barbershopogram.co.uk/prices, checked 3 September 2026.*
3. **What £600 buys from us.** The inclusions list from §Product. Facts, no adjectives.
4. **How we work.** 48 hours' notice. WhatsApp, usually the same day. Four voices as standard, eight or twelve by quotation. A published repertoire (link). A named Artistic Director. Each stated about us; none set against them.
5. **Listen.** The barbershop recording, embedded. This is why the page waits.
6. **Everything else we offer** is one sentence linking to `pricing.html#barbershop-grams`. **No other number appears on this page.** Printing our own £800 or £1,200 would need adding to `lcs_prices` and would invite the reader to line them up against a ladder this page has chosen not to discuss.
7. **Already got a quote?** Point at the hub's own enquiry form (`/barbershop-grams/#enquire`), not `contact.html`. This page carries the gift register's styles, and the register never hands a buyer to main-site chrome.
8. **FAQ.** Four questions, `FAQPage`.

**Schema:** `BreadcrumbList` + `Article` + `FAQPage`. No `Offer` for the competitor's figure.

### Claim rules, binding

The seven rules in the 2026-08-18 spec §3 apply unchanged. Two additions for this page:

8. **Only the entry product is discussed.** Not their sets, not their recording sessions, not their bespoke pricing, not their travel policy. The YAML enforces this for numbers; the author enforces it for words.
9. **No claim about their responsiveness, availability, or booking handling.** We have a tip-off, not a source.

---

## Claims integrity

### `data/competitor-pricing.yml`

```yaml
  barbershopogram:
    name: "Barbershop-o-gram"
    url: "https://www.barbershopogram.co.uk/"
    pricing_url: "https://www.barbershopogram.co.uk/prices"
    checked_date: "2026-09-03"
    vat_treatment: "consumer-inclusive; no VAT statement or VAT number anywhere on their site (checked 2026-09-03)"
    travel: "All fees include music from our standard repertoire and include travel within London zone 5 unless otherwise stated."   # verbatim; inclusion line, not published on our pages
    packages:
      ten_minute_gram:
        price_inc_vat: 600
        source_quote: "Up to 10 minutes (including Happy Birthdays) £600"
        includes: "All fees include music from our standard repertoire"
    # Deliberately no other packages. The owner's instruction is that their other tiers are never
    # mentioned; leaving them out of this file means the build rejects any page that prints them.
```

`lcs_prices` gains `barbershop_gram: 600`. No `derived_figures` are needed: there is no saving to state.

### Why the price field is `price_inc_vat`, and the validator change it requires

The funeral-singers entry uses `price_ex_vat`, correctly: that provider prints "+ VAT" against every figure, so a family pays 20% more than the number shown, and `allowed_figures()` deriving the inc-VAT twin is what let the comparison page state the real cost.

Barbershop-o-gram prints a bare "£600" on a page addressed to consumers. No VAT statement and no VAT number appears anywhere on their site, and UK price-marking rules require consumer-facing prices to include VAT — so £600 is what the buyer pays whether or not part of it is VAT the provider remits. There is no VAT delta in either direction, which is why this comparison makes no VAT argument at all.

Reusing `price_ex_vat` here would therefore assert something false and would make `allowed_figures()` admit `round(600 × 1.2) = 720`, a figure describing nothing real. **`validate_competitor_claims.py` must handle both keys:**

```python
for pkg in provider.get("packages", {}).values():
    if "price_ex_vat" in pkg:                      # quoted excluding VAT
        ex = pkg["price_ex_vat"]
        allowed.add(ex)
        allowed.add(round(ex * (1 + vat)))         # what a family actually pays
    if "price_inc_vat" in pkg:                     # already the buyer's cost
        allowed.add(pkg["price_inc_vat"])          # no twin: there is nothing to add
```

A mistyped key allows no figure and fails the build loudly, which is the right failure direction. This keeps the funeral-singers behaviour byte-for-byte unchanged.

### `tests/test_competitor_claims.py`

One new case using the real YAML: a compare page containing `&pound;750` (one of their unlisted tiers) must fail the build. This is the test that keeps the "entry product only" instruction alive after everyone has forgotten why.

### Human cadence

`MANUAL-ACTIONS-REQUIRED.md` §11's quarterly re-check now covers two providers. Same rule: update `checked_date` and the page in one commit.

---

## Copy and register rules

- `writing-site-copy` and `stop-slop`, loaded before writing, run again after.
- The voice is warm, specific, and well-made. Not zany, not winking. Jokes come from the situation (a quartet at a desk), never from the copy trying to be funny.
- Name real things: the office, the restaurant table, the age on the cake. No "unforgettable", no "magical".
- No invented testimonials, venues, or media credits. The competitor has radio and BBC credits; we do not, and the page does not pretend otherwise. Our proof is the recording, the credential, and the repertoire.
- No adjectives about the competitor anywhere.
- `validate_house_claims.py` runs on the new directory; nothing here should trip it, and if a new pattern is worth banning after this work, add it there.

---

## Go-to-market

### Phase 0: before the page is worth sending traffic to

1. **A barbershop recording.** Happy Birthday in four parts plus one standard, filmed, two to three minutes. Without it the hub has no genre-appropriate proof and the comparison page cannot exist. Human action.
2. **The repertoire confirmed** by the Artistic Director against what the singers have rehearsed. Human action.
3. **One or two seeded grams** for colleagues or friends: real footage, the first honest quote, and a rehearsal of the logistics checklist against reality. Human action.
4. **Consent wording** for filming: the buyer confirms on enquiry whether we may film; the recipient is asked afterwards, before anything is posted. Goes in the FAQ and the booking agreement.
5. **`og-barbershop-grams.png`**, 1200×630. Until it exists the pages use `og-image.png`. Human action.
6. **GBP re-anchored to London.** The site's schema already says London (N1 7GU, Greater London); the Maps listing says Maidenhead. Human action, with the address-versus-service-area choice written up in `MANUAL-ACTIONS-REQUIRED.md`. "Barbershop quartet London" in the local pack needs this.

### Search

- Phase 1 targets, hub: "barbershop gram", "singing telegram London", "surprise singers birthday London", "barbershop quartet hire London", "singing birthday surprise". Repertoire page: "barbershop quartet songs".
- Phase 3, on evidence: a page per occasion once Search Console shows impressions for "singing valentine London", "proposal singers London", "office birthday surprise singers", or their neighbours. Each page gets its own head, schema, and FAQ under the `new-page` skill; none is built on speculation.
- Seasonal nav: the Services dropdown entry is enough; no top-level promotion, unlike Christmas, because the register argument applies year-round.

### Short-form video: the lever that matters most

Surprise-reaction clips are among the most shared formats on Reels, TikTok, and Shorts, and this is the one product where watching a reaction sells better than any sentence. A standing cadence (one clip per gram, with consent, cut to under thirty seconds) is a real acquisition channel and costs nothing but the ask. The forthcoming videos seed it; the seeded grams supply the first clips. Human action, ongoing.

### Ads (human action, `MANUAL-ACTIONS-REQUIRED.md`)

Same shape as §11 of the manual actions file. Before spend, confirm the WhatsApp-click conversion fires; gram enquiries arrive by WhatsApp more than by form.

1. **Generic gram, all year.** "singing telegram london", "barbershop quartet hire london", "surprise singers birthday", "singing birthday gram". Landing: the hub. Headlines: "£600, nothing added" · "Four voices, 48 hours' notice" · "Happy Birthday in four-part harmony".
2. **Seasonal occasion bursts.** Valentine's terms 25 January to 14 February. Proposal terms late November to early January (the UK's proposal peak). Landing: the hub's occasion anchors until phase 3 pages exist.
3. **Brand defence.** Exact match, capped.
4. **Conquest.** Their brand terms as keywords, landing on the comparison page. Their name never in ad creative. Negatives specific to them: "sheet music", "arrangement", "pdf", "shop", "licence": their site sells arrangements, and those searchers are choirs, not buyers.
5. **Office.** "office birthday surprise ideas", "leaving do surprise London". Landing: the hub's office anchor.

Site-wide negatives: jobs, join, audition, lyrics, chords, sheet music, karaoke, costume, hire a barber.

### Seasonal calendar

| Moment | Date | Content live by | Ads |
|---|---|---|---|
| Valentine's | 14 Feb | 15 Jan (indexing lead) | 25 Jan – 14 Feb |
| Mothering Sunday | 7 Mar 2027 | 10 Feb | 20 Feb – 7 Mar |
| Father's Day | 20 Jun 2027 | 20 May | 5 – 20 Jun |
| Graduations and leaving dos | Jul | 1 Jun | Jun – Jul |
| Proposal peak | 20 Dec – 2 Jan | 15 Nov | 25 Nov – 1 Jan |
| Christmas office grams | Dec | 1 Nov | Nov – mid Dec |

Dates roll each year; the January nav pass in ROADMAP R9 is the natural place to refresh them.

### Partnerships (human action)

- **Florists and gift-delivery services**: a mutual upsell, their bouquet plus our four voices.
- **Restaurants**: a handful of London restaurants that already sell "surprise" occasions get a turnkey performance partner. The table booking is the access problem solved.
- **Wedding planners, already on `for-wedding-planners.html`**: a proposal gram is a wedding lead. A single-product quartet cannot make this offer; we can, and the proposal section says so in one sentence.
- **Office managers and People teams**: a recurring "someone's leaving" product, not a one-off.

### Directories (human action)

Last Minute Musicians, Add to Event, Poptop, Encore, Bark. The category listing is where "barbershop quartet hire" buyers who never reach Google's organic results go. Extend `docs/off-site-listings-pack.md` with a Barbershop Grams profile: the £600 figure, the 48-hour line, the repertoire link, the same house rules as the existing pack.

### Gift certificate

A PDF, generated the way invoices and booking agreements already are, sent to the buyer after payment so the gram can be wrapped and given for a date to be fixed later. No site build; a template and a line in the booking workflow.

### Digital PR (human action)

Gift-guide outreach twice a year: "experience gifts" round-ups for Valentine's and for milestone birthdays. A journalist needs a photograph, the price, and a link. The link is the point.

### Referral

"Send one, get £50 off the next" as a code quoted on the thank-you page after a gram enquiry converts. Tracked by the code in the enquiry text; no infrastructure.

---

## Measurement

- **Primary:** enquiries whose occasion field is `barbershop-gram`, from Web3Forms, plus WhatsApp clicks with the gram-specific pre-fill text, from GA4.
- **Secondary:** cost per enquiry by campaign, once ads run.
- **Organic:** impressions and position for the search targets above, in Search Console, reviewed at each seasonal moment. Phase 3 pages are triggered by this, not by the calendar.
- **Not measured:** which enquirers also contacted the competitor. Not worth a question on the form.

---

## Sequencing

| Phase | Contents | Depends on |
|---|---|---|
| **0** | Recording · repertoire confirmed · seeded grams · consent wording · OG image · GBP to London | Owner |
| **1** | Register partials · hub · repertoire page · `pricing.html` section · contact select option · nav/services/weddings/corporate links · validators extended · `sitemap.xml` · `llms.txt` · ROADMAP entry · `/graphify --update` | Repertoire confirmed (0.2); everything else in phase 0 can follow |
| **2** | `data/competitor-pricing.yml` entry · new test case · `compare/barbershopogram.html` · `barbershop-grams/listen.html` | Recording (0.1) |
| **3** | Occasion pages | Search Console evidence after phase 1 has been live a season |
| **4** | Ads · directories · partnerships · PR · seasonal calendar | Phase 1 live; ads also on 0.1 and 0.3 |

Phase 1 can ship before the recording exists; Phase 2 cannot. Note that no proof slot was designed into the hero, so landing 0.1 means finding a home for the recording as well as making it — the hero's two-CTA row is the obvious place.

---

## Deferred

- **A subdomain or separate domain**, if the product grows into its own business. The register makes the move mechanical.
- **Online payment.** A build, not a page.
- **A soloist or duo gram.** Ruled out for now; recorded so the reason is on file.
- **An audio-only recording tier.** The competitor sells one. We fold it into the video session.
- **Barbershop Christmas rounds**, distinct from `carol-singers.html`. The repertoire page carries a Christmas group; a product around it waits for December demand.
- **Per-occasion pages** (phase 3, above).

---

## Appendix: competitor data as retrieved 2026-09-03

Source: `https://www.barbershopogram.co.uk/` and `/prices`. **For the quarterly re-check only. Rows 2 to 8 are never published, in words or numbers, on any page of this site.**

| # | As published |
|---|---|
| 1 | "Up to 10 minutes (including Happy Birthdays)" · "£600" |
| 2 | "Half hour set" · "£750" |
| 3 | "One hour set" · "£900" |
| 4 | "Bespoke composition or arrangement" · "from £225" |
| 5 | "One hour audio only recording session" · "£1000" |
| 6 | "One hour video recording session" · "£1200" |
| 7 | "Licences for 5 and 6 are negotiated separately depending on usage" |
| 8 | "Travel outside London zone 5: we charge £250 per hour spent travelling, plus travel costs" |
| Inclusions | "All fees include music from our standard repertoire and include travel within London zone 5 unless otherwise stated." |
| VAT | Not stated |
| Founded | 2011, "when schoolfriends Andy and Chris were asked to sing at another schoolfriend's Hen Night" |
| Positioning | "the finest barbershop quartet in London"; "Our fees begin at £600." |
| Site | Single-page with anchored sections plus `/prices`, `/carol-singing`, `/media`, `/shop-1` (arrangements for sale); contact form only |
