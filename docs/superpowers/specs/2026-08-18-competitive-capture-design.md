# Competitive capture programme — design doc

**Date:** 2026-08-18
**Author:** Luca Wetherall (with Claude)
**Status:** Draft for review
**Related:** [pricing.html](../../../pricing.html), [docs/ROADMAP.md](../../ROADMAP.md), `data/seo-fix-discovered-urls.yml`

---

## Goal

Capture enquiries that currently go to The London Funeral Singers, the closest direct competitor in the London funeral-music market, by publishing a verifiable comparison and pointing paid search at it.

The commercial case rests on three differences that are checkable rather than asserted:

1. **Price.** LCS is 24–38% cheaper on every equivalent configuration once VAT is accounted for.
2. **Repertoire allowance.** Their small choir and full choir each include *"One performance piece."* Ours include up to three, plus every hymn. This is the difference least likely to be competed away, because closing it means changing their cost model rather than their price list.
3. **How the ensemble is assembled.** They advertise *"over 150 auditioned singers and instrumentalists on our books."* LCS is a small hand-picked team under a named Artistic Director who auditions every musician himself.

Point 3 is the strategic centre of this document, and it required repairing the site before it could be made — see Phase 0.

## Non-goals

- **A named-singer roster page.** Ruled out by the owner. Proof of quality comes from recordings, the Artistic Director's credential, and the fixed-ensemble argument instead.
- **Review or rating schema of any kind.** Prohibited site-wide (CLAUDE.md; ROADMAP R1).
- **Comparisons against providers other than The London Funeral Singers.** The architecture extends to more, but each added competitor multiplies the fact-checking burden. One is enough to prove the model.
- **Crematorium and borough landing pages.** High value, but a distinct programmatic project. Deferred, not dismissed.
- **Any claim about the competitor beyond price, VAT treatment, and published package inclusions.** These three are the only things they publish in writing, and therefore the only things we can source.
- **Cookie consent / Consent Mode v2.** Still ROADMAP R4. It limits conversion modelling but does not block this work.

---

## Competitive position: the facts

All competitor figures below are quoted from `https://www.londonfuneralsingers.co.uk/pricing`, retrieved 2026-08-18. They are stated as published, with VAT shown separately because that is how the source states them.

### Price

LCS figures are the post-merge values from the `site-audit-improvements-47d735` worktree (soloist £250, organist £250 standalone / £225 added to a choir). VAT computed at the standard 20% rate.

| Configuration | LFS as published | LFS inc. VAT | LCS all-in | Difference |
|---|---|---|---|---|
| Soloist | £275 + VAT | £330 | £250 | £80 (24%) |
| Organist | £275 + VAT | £330 | £250 | £80 (24%) |
| Soloist + organist | £550 + VAT | £660 | £450 | £210 (32%) |
| Small choir (4) | £1,400 + VAT | £1,680 | £1,150 | £530 (32%) |
| Small choir (4) + organist | £1,675 + VAT | £2,010 | £1,375 | £635 (32%) |
| Full choir (8) | £2,400 + VAT | £2,880 | £2,000 | £880 (31%) |
| Chorus (12) | £4,000 + VAT | £4,800 | £3,000 | £1,800 (38%) |

**The VAT point is load-bearing, and it is where the soloist comparison lives or dies.** £250 against £275 looks like a rounding difference. £250 against £330 does not. A family ringing round hears the pre-VAT number and forms an impression that the invoice then contradicts.

**The honest qualifier, which must appear in the copy.** Alma Consort Ltd is not VAT-registered, so nothing is added to a LCS invoice and there is nothing to reclaim from one. A VAT-registered business buyer reclaims the VAT on a competitor's invoice, so for them the real comparison is £250 against £275 — 9%, not 24%. Families cannot reclaim, so the full gap is the correct figure on family-facing pages. Use the full gap on funeral and comparison pages; use ex-VAT figures on the `for-*.html` B2B pages.

### Repertoire allowance

| Configuration | LFS includes | LCS includes |
|---|---|---|
| Small choir (4) | One performance piece, up to three hymns | Up to three performance pieces, all hymns |
| Full choir (8) | One performance piece, up to three hymns | Up to three performance pieces, all hymns |
| Chorus (12) | Two performance pieces, up to four hymns | Up to four performance pieces, all hymns |

At quartet level this is three times the sung music for roughly two-thirds of the price. It is a stronger argument than price alone and it does not decay if they discount.

LCS also offers quintet (£1,400) and sextet (£1,600) configurations. LFS jumps from four singers to eight, so a family wanting six voices must buy eight.

### Positioning

| | LFS | LCS |
|---|---|---|
| Scale | "over 150 auditioned singers and instrumentalists on our books" | A small hand-picked team |
| Selection | "We audition every singer in person" | Luca Wetherall auditions every musician himself |
| Named musical leadership | None published | Artistic Director, Tutor in Music, University of Oxford |
| Recordings published | Not established — see below | Six on [listen.html](../../../listen.html) |
| Founded | 2015, by Penny and Briony | — |

**Do not make claims about their recordings, their staff, or their musical quality.** Their media pages may change, and any such claim would need maintaining and would edge toward denigration. LCS recordings go on the page; the reader compares for themselves.

---

## Phase 0 — prerequisites

### 0a. Roster-scale claims removed site-wide — **done 2026-08-18**

The site advertised roster scale in **13 places across 9 files** — `index.html`, `about.html`, `services.html`, `funerals.html`, `for-funeral-directors.html`, `areas/index.html`, `areas/winchester.html`, `music-guides/booking-carol-singers-agency-vs-direct.html`, and `llms.txt` — including two JSON-LD FAQ answers. The homepage lede read *"Over 150 auditioned musicians"*; `about.html` read *"We maintain a roster of over 150 auditioned singers and instrumentalists."*

That second line is near-verbatim the competitor's own: LFS advertises *"over 150 auditioned singers and instrumentalists on our books."*

The site was therefore making the competitor's argument, in the competitor's words, while the owner's actual position is the opposite one. Any comparison page built on "hand-picked, not a big book" would have been contradicted by the homepage lede.

Scale claims were replaced with selection claims. A further 30 uses of "roster" vocabulary across 15 `areas/` pages and 2 `music-guides/` pages were normalised to "team" or "hand-picked", since the word itself connotes the large-book model. **43 edits across 23 files in total.**

Three uses of "roster" were kept deliberately, because they argue *against* the large-book model:

- `for-funeral-directors.html` (×2) — "The family deals with one person, not a roster."
- `music-guides/booking-carol-singers-agency-vs-direct.html` — "groups built around a fixed roster of singers under a named director", describing the market category LCS belongs to.

Verify: `grep -rn 'over 150\|more than 150\|150-plus\|150 auditioned\|150 singers\|150 musicians' --include='*.html' --include='*.txt' .` → empty.

### 0b. VAT-registration claims removed — **done 2026-08-18**

Six B2B landing pages stated *"We are VAT-registered"* in 13 places, two of them inside `FAQPage` JSON-LD. Alma Consort Ltd is not VAT-registered. Beyond being false, this was a live commercial exposure: a managing agent or hotel finance team reading it would expect a VAT number on the invoice and could reject the invoice without one.

Removed rather than negated. On a B2B invoicing paragraph, "we are not VAT-registered" is noise; silence is accurate and reads better. The positive framing ("nothing added to the price") belongs on family-facing comparison content, where it is an advantage.

Files: `for-charities.html`, `for-event-managers.html`, `for-hotels.html`, `for-livery-companies.html`, `for-property-managers.html`.

Verify: `grep -rn 'VAT' --include='for-*.html' .` → empty.

### 0c. Pricing merge — **blocked on `site-audit-improvements-47d735`**

That branch raises the single-musician rate to £250 and reprices organist combinations. Every figure in this document assumes it has landed. The comparison page must not ship before it, or the site will quote two different soloist prices.

### 0d. Residual `£215` sweep — **blocked on 0c**

After the merge, `£215` survives in content the pricing branch did not touch. Known: [music-guides/funeral-music-costs.html](../../../music-guides/funeral-music-costs.html) (×4, including a `FAQPage` answer), [funerals.html](../../../funerals.html) (×1), `llms.txt` (×1). Re-grep after merging; do not work from this list alone.

Verify: `grep -rn '£215\|&pound;215\|"215"' --include='*.html' --include='*.txt' .` → empty.

---

## 1. The named comparison page

**Path:** `compare/london-funeral-singers.html`

A new top-level `compare/` directory rather than `music-guides/`. This is a commercial page, and filing it under the guides hub would dilute an editorial section that currently earns its ranking on genuinely useful content.

**Not in the main nav.** A "Compare" tab on a funeral site reads as combative and would be the first thing a bereaved visitor sees. Reached instead from `funerals.html`, `pricing.html`, both funeral guides, and the footer.

**Indexed and in the sitemap.** The organic intent here is real: people search a provider's name alongside "prices", "reviews", and "alternative".

### Structure

1. **Opening.** Two or three sentences acknowledging that the reader is comparing quotes during a hard week, and stating plainly what the page contains. No hook, no marketing throat-clearing.
2. **The price table.** Their published figure, the same figure with VAT, ours, the difference. Source link and retrieval date directly beneath.
3. **The VAT explanation.** Why one quote says £275 and another says £250, and what each becomes on the invoice. Includes the business-buyer qualifier.
4. **Repertoire allowance.** The three-pieces-against-one table. This section carries the most weight and should come before any quality argument.
5. **How the ensemble is put together.** The fixed-quartet argument — singers who rehearse together against four diaries booked for a Friday. The material already exists, well written, in [best-funeral-singers-london.html](../../../music-guides/best-funeral-singers-london.html); adapt rather than rewrite.
6. **Listen.** The existing quartet recording of *Abide With Me* (`G9-R6k5n7Io`) embedded, plus *Anima Christi* (`ZVSQ2Ts4GZE`). IDs and durations are in `data/seo-fix-discovered-urls.yml`. This is the quality evidence; it is not decoration and belongs high on the page, not in a footer.
7. **What's included, both sides.** Two lists, stated as facts. No adjectives.
8. **Already got a quote?** CTA into `contact.html?occasion=quote-check`, using the existing `?occasion=` pre-fill in `js/contact.js`. Highest-intent traffic on the page: someone holding a number.
9. **FAQ.** Four to six questions, with matching `FAQPage` JSON-LD.

### Schema

`BreadcrumbList` + `Article` + `FAQPage`, following the `music-guides/` pattern.

**No `Product`, `Offer`, or `AggregateOffer` node containing competitor prices.** Offer markup asserts that the marked-up entity sells at that price; using it for a third party's figures misrepresents the relationship. LCS prices may carry `Offer` as they do elsewhere.

### Wiring checklist

Follow the `new-page` skill. In addition: `sitemap.xml` entry with today's `lastmod`; `llms.txt` entry; inbound links from `funerals.html`, `pricing.html`, `music-guides/funeral-music-costs.html`, `music-guides/best-funeral-singers-london.html`, and `partials/footer.html`. The footer link is a partial edit, so `./build.sh` is mandatory.

---

## 2. Claims integrity

A page quoting a competitor's prices becomes a liability the moment those prices change. This must be structural, not a note in a document nobody reads.

### `data/competitor-pricing.yml`

Single source of truth, following the `data/seo-fix-discovered-urls.yml` precedent (commented header, explicit provenance, `TODO` markers for anything unverified).

```yaml
providers:
  london-funeral-singers:
    name: "The London Funeral Singers"
    url: "https://www.londonfuneralsingers.co.uk/"
    pricing_url: "https://www.londonfuneralsingers.co.uk/pricing"
    checked_date: "2026-08-18"
    vat_treatment: "quoted excluding VAT"
    travel: "Travel charges apply outside of London"   # verbatim
    packages:
      soloist:
        price_ex_vat: 275
        source_quote: "Soloist: From £275 + VAT"
        includes: "One solo performance piece; Congregation leading - up to three hymns"
      small_choir:
        price_ex_vat: 1400
        source_quote: "Small Choir: £1,400 + VAT"
        includes: "Four singers; One performance piece; Leading the congregation - up to three hymns"
      # … full choir, chorus, organist, instrumentalists
```

Every figure carries the verbatim source string it came from. If a claim cannot be quoted, it does not go on the page.

### `validate_competitor_claims.py`

Run from `build.sh` alongside `validate_jsonld.py`.

- **Hard fail** if a price figure appears in `compare/*.html` that is not present in the YAML. This is the check that matters: it makes it impossible to hand-edit a competitor figure into the page.
- **Warn loudly** if any `checked_date` is more than 120 days old. A warning rather than a failure, so a stale competitor price never blocks unrelated work on the site.
- Print the provider name and age on every run, so staleness is visible rather than discovered.

### Visible provenance

The page states, in body text and not in a tooltip: *"Prices as published at londonfuneralsingers.co.uk/pricing, checked 18 August 2026."*

### Human cadence

Add a recurring entry to `MANUAL-ACTIONS-REQUIRED.md`: re-check competitor pricing quarterly, update `checked_date`, and update the page in the same commit.

### CLAUDE.md convention

Extend the existing rule. Currently: *"Prices quoted anywhere must match `pricing.html`."* Add: *"Competitor figures must match `data/competitor-pricing.yml` and carry a visible checked date."*

---

## 3. Copy and claim rules

UK comparative advertising is lawful where the comparison is against an identified competitor, addresses the same need, compares material and verifiable features, and neither misleads nor denigrates. Those constraints happen to describe the most persuasive register available here, so they are not a tax on the writing — they are the writing.

Binding rules for anything on `compare/`:

1. **Every competitor claim is a verbatim quote** from their published page, with a link and a retrieval date. Paraphrase is not permitted, because paraphrase is where misrepresentation enters.
2. **Compare identical configurations,** and state where the packages differ rather than smoothing it over. Four singers against four singers.
3. **State the VAT basis on both sides,** every time a figure appears.
4. **No adjectives about them.** Not "better", not "cheaper than they let on", nothing implying they mislead or overcharge. State what each includes; the reader draws the conclusion, and the conclusion is more persuasive for being theirs.
5. **No claims about their musicians, their staff, or their quality.** Price, VAT, and published inclusions only.
6. **The business-buyer qualifier stays in,** even though it weakens the headline. Omitting it would make the page misleading to a segment of its readers, which is precisely the failure mode the regulations describe.
7. **House copy rules apply in full** — the `writing-site-copy` skill, loaded before writing any visible text. Funeral copy is restrained and practical. This page in particular must never read as a price war; the reader is bereaved and comparing quotes because they have to.

---

## 4. Transparency cluster

Upgrades to pages that already exist and already rank. **No new neutral cost page** — [music-guides/funeral-music-costs.html](../../../music-guides/funeral-music-costs.html) already targets that query, already says *"other providers may differ, but this gives you an honest benchmark"*, and a second page would cannibalise it.

### 4a. `music-guides/funeral-music-costs.html`

Add a market-comparison section using the same single competitor and the same YAML source, consistent with the non-goal above — not a multi-provider survey. Update the `£215` figures (Phase 0d) and the corresponding `FAQPage` answers.

### 4b. `music-guides/best-funeral-singers-london.html`

Its market table currently gives a quartet range of £900–£1,400 and a soloist range of £200–£300. The published market rate is £1,680 inc. VAT for a quartet. The table understates the market and therefore understates LCS's own advantage. Correct it against real data, and keep the existing paragraph about VAT varying between providers — it is accurate and now has evidence behind it.

### 4c. `pricing.html`

A "what you are not charged for" block, listing the real items: travel within Greater London, sheet music, rehearsal, music director, funeral-director liaison, and VAT. Concrete list, no preamble.

---

## 5. Proof of quality

With a named roster ruled out, quality has to be evidenced three other ways.

1. **The Artistic Director's credential.** Luca Wetherall, Tutor in Music, University of Oxford — verifiable at `https://www.music.ox.ac.uk/people/luca-wetherall`, already recorded in `data/seo-fix-discovered-urls.yml`. Stated on the comparison page inline, not as a badge.
2. **Recordings.** Six exist on [listen.html](../../../listen.html). They belong above the fold on the comparison page. A reader can settle the quality question in ninety seconds, which no amount of prose achieves.
3. **The fixed-ensemble argument,** promoted from a paragraph in the funeral-singers guide to a section of its own: a quartet that rehearses together every week against a quartet assembled from four diaries. This is now the site's central differentiator and should read as such.
4. **Service standards, stated specifically.** Arrive 45–60 minutes early, check in with the funeral director, plain dark dress, no social posting, stand at the back unless asked. Specifics read as competence; adjectives do not. The material exists in the funeral-singers guide.

---

## 6. Google Ads

Five campaigns, in order of expected return.

1. **Generic funeral, price-led.** "funeral singer london", "funeral choir hire london", "singer for funeral service", "funeral choir cost". RSA headlines led on *"From £250, nothing added"* and *"Three sung pieces included, not one"*. Landing: `funerals.html`, with the comparison page as a tested alternative. **This is where the budget goes.**
2. **Call-only, short notice.** Funerals are urgent and a bereaved person at nine in the evening rings rather than fills in a form. Evening and weekend scheduling. Keywords around "short notice", "this week", "urgent".
3. **Brand defence.** LCS brand terms, exact match, capped budget. Cheap insurance.
4. **Conquest.** Competitor brand terms as keywords, landing on the comparison page. **Their trademark must not appear in ad text** — Google permits the mark as a keyword but restricts it in creative, and the owner can complain. The landing page does the naming; the ad does not. Expect low volume, high CPC, and a poor quality score. Worth running as a small line item, not as the strategy.
5. **Borough and crematorium geo.** Held until those landing pages exist.

### Before spend

Confirm that phone-click and WhatsApp-click conversions actually fire. `AW-17988388404` is present on every page and wired for form submissions; call conversions are unverified. A call-only campaign with no call conversion action is money spent blind.

### Landing-page note

Inlined CSS means no render-blocking stylesheet request, which helps page-experience signals. Keep the comparison page within the size envelope of comparable pages (55–78KB).

---

## 7. Measurement

- **Primary:** cost per enquiry by campaign, from Google Ads.
- **Secondary:** GA4 landing-page → conversion rate for `compare/london-funeral-singers.html` against `funerals.html`, to settle which converts paid traffic better.
- **Organic:** impressions and position for the competitor's brand terms plus "funeral singer london prices", in Search Console.
- **Not measured:** how many enquirers were also quoting the competitor. Capturing it means adding a question to the contact form, and a bereaved family filling in a funeral enquiry should not be surveyed. The commercial signal from CPA is sufficient.

Conversion modelling is degraded until Consent Mode v2 exists (ROADMAP R4). Interpret Ads figures accordingly rather than treating them as exact.

---

## 8. Sequencing

| Phase | Contents | Depends on |
|---|---|---|
| **0** | Roster sweep ✅ · VAT removal ✅ · pricing merge · `£215` sweep | `site-audit-improvements-47d735` |
| **1** | `data/competitor-pricing.yml` · `validate_competitor_claims.py` · `compare/london-funeral-singers.html` · sitemap + `llms.txt` · inbound links · CLAUDE.md convention | Phase 0 complete |
| **2** | Call-conversion verification, then ads campaigns 1–3 | Phase 0c (prices must be right before ads quote them) |
| **2b** | Ads campaign 4 (conquest) | Phase 1 live — it lands on the comparison page |
| **3** | Cost-guide market section · market-table correction · pricing inclusions block | Phase 0d |
| **4** | Credential, ensemble argument, service standards, recordings placement | Phase 1 |

Phases 3 and 4 are independent of each other and can run in either order.

---

## 9. Deferred

Listed so they are not lost, and so the decision to exclude them is on the record.

- **Crematorium and borough landing pages.** Golders Green, Honor Oak, Mortlake, West London, Hendon, Islington. The highest-value remaining idea after this programme; the existing funeral-singers guide already contains per-acoustic advice for these rooms, which is unusual and nobody else has it. A distinct programmatic project.
- **Instant quote calculator.** Weaponises the price transparency, but it is a build rather than a page.
- **Additional named competitors.** The `compare/` architecture and the YAML both extend cleanly.
- **Directory listings** where the competitor already appears (Last Minute Musicians, Add to Event, Poptop, Bark).
- **Funeral-director outreach.** One director sends dozens of services a year. Probably a larger commercial lever than the entire ad budget, and unrelated to site content.

---

## Appendix: competitor data as retrieved 2026-08-18

Source: `https://www.londonfuneralsingers.co.uk/` and `/pricing`, `/faqs`, `/about`.

| Item | As published |
|---|---|
| Soloist | "From £275 + VAT" — "One solo performance piece", "Congregation leading - up to three hymns" |
| Organist | "£275 + VAT" |
| Instrumentalists | "Starting at £275 + VAT" |
| Small Choir | "£1,400 + VAT" — "Four singers", "One performance piece", "Leading the congregation - up to three hymns" |
| Full Choir | "£2,400 + VAT" — "Eight singers", "One performance piece", "Leading the congregation - up to three hymns" |
| Chorus | "£4,000 + VAT" — "Twelve singers", "Two performance pieces", "Leading the congregation - up to four hymns", plus organist-conductor |
| Travel | "Travel charges apply outside of London" |
| Roster | "over 150 auditioned singers and instrumentalists on our books" |
| Selection | "We audition every singer in person, so we can vouch for their quality" |
| Lead time | "as little as a day's notice" |
| Founded | 2015, by Penny and Briony; "combined 20 years' experience in the arts"; "over 500 funerals" |

These values move into `data/competitor-pricing.yml` in Phase 1. This appendix is a snapshot for review, not the source of truth.
