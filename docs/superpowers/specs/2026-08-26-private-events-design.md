# Private & international engagements page — design doc

**Date:** 2026-08-26
**Author:** Luca Wetherall (with Claude)
**Status:** Draft for review
**Related:** [docs/superpowers/plans/2026-08-26-private-events.md](../plans/2026-08-26-private-events.md), [about.html](../../../about.html), `data/seo-fix-discovered-urls.yml`, [MANUAL-ACTIONS-REQUIRED.md](../../../MANUAL-ACTIONS-REQUIRED.md)

---

## Goal

One page — `/private-events.html` — that converts very high-value private and international enquiries: luxury wedding planners, venue and hotel event directors, and private principals. It presents Alma Consort as the performing ensemble, carries no prices, and funnels everything into an application-style enquiry form with budget bands.

**Success metric: cost per qualified enquiry.** Not traffic, not raw enquiry volume. A page that produces three serious conversations a month has done its job; a page that produces thirty tyre-kickers has not.

## Positioning: the booking office and the ensemble

The London Choral Service is presented as **the booking office of Alma Consort**. The framing is functional, not hierarchical: LCS handles the arrangements; Alma Consort does the singing; the same singers perform every engagement. The page must never describe itself as a "premium tier" of LCS, and the word "elite" is banned outright — both framings invite the reader to re-price the rest of the site downwards.

The ensemble's own home is **https://www.almaconsort.com** — an external, owner-controlled site, linked from the ensemble section as the place to read about Alma Consort itself. There is deliberately no on-site `/alma-consort` page (see Non-goals); the external domain serves that purpose. The link target is unverifiable from the build environment, so verifying it renders well, and adding a reciprocal link back to `/private-events.html`, are owner actions in `MANUAL-ACTIONS-REQUIRED.md`.

## Full insulation from the site chrome

The page carries a bespoke minimal header (wordmark plus a single "Enquire" anchor) and a discreet one-block footer. It includes **none** of the site's nav or footer partials. Two reasons, both structural:

1. **Tier-mixing.** The global nav and footer would surround the page with funeral pricing, borough pages, and "from £250" services — precisely the price-anchored context this audience must not see. One click from a planner's proposal into a funeral price list undoes the positioning.
2. **The CSS bundle.** Every partial-carrying page receives the single inlined site stylesheet. Pulling the partials in would either ship the whole site bundle onto this page, or require this page's own styles to enter `css/pages.css` — which the build would then inline into **every other page on the site**. Insulation keeps this page's register out of the site bundle and the site bundle off this page.

The page is still linked *from* the site — a discreet nav item, plus one in-copy link each on `weddings.html` and `about.html`. Never from `compare/` or any `for-*.html` page. Insulation is one-way: the site may point in; the page does not point back out into the funnel.

## The Pass A defence — read this before touching the page

**This is the most expensive future mistake available on this page, so it is recorded here prominently.**

`build.sh` Pass A (build.sh:84–96) recognises the generated inline bundle by pattern: a line that is exactly `  <style>` whose **next line** matches `:root {`, and replaces the whole block with a `style.css` link for re-inlining. This page's hand-authored `<style>` block therefore **starts with a comment line** as its first inner line, so Pass A can never mistake it for the generated bundle and delete it. The comment says exactly this, in place.

Two invariants, both build-fatal in slow motion if broken:

- **Never remove the comment line at the top of the page's `<style>` block.** Without it, the next build replaces the entire hand-authored stylesheet with a link to the site bundle, and the page's design is gone.
- **The page must never contain a `style.css` link.** Pass B inlines the site bundle wherever that link exists; a well-meaning "add the missing stylesheet" edit ships the whole site's CSS onto this page.

The Phase C idempotency check (second `./build.sh` → `git diff private-events.html` empty) is the tripwire that catches either regression.

## The light parchment register

All-light. The brief's dark inversion was considered and **dropped by the owner** ("I don't want dark page design"). The page lives in the same visual world as the LCS invoice and booking-agreement print collateral: parchment fields, ink text, a single liturgical red.

### Page-scoped tokens

These tokens exist **only** in this page's own `<style>` block. They are not in the site CSS and must never be added to it.

| Token | Hex | Role |
|---|---|---|
| `--choirStall` | `#2A1708` | Ink — headings and body text |
| `--cassockRed` | `#7E1818` | Accent, **≤4 decorative uses**: 1px rules, small-caps labels — plus focus rings |
| `--organPipe` | `#5F544A` | Secondary text, captions, meta |
| `--naveStone` | `#9A8F7F` | **Decorative only** — fails contrast as text |
| `--limestone` | `#C8BFA9` | Hairlines |
| `--parchment` | `#F0E9DC` | Alternating section field |
| `--parchmentLight` | `#FAF6EE` | Alternating section field; page ground |
| `--candle` | `#C89A3C` | **Decorative only** — hairlines and waveform |

No pure black or white anywhere.

### Contrast (computed, WCAG 2.1)

| Pairing | Ratio | Verdict |
|---|---|---|
| choirStall on parchmentLight | **15.91** | AAA |
| organPipe on the light fields | **6.83** | AA |
| cassockRed on the light fields | **9.59** | AAA — and passes 3:1 non-text, so it may carry focus rings |
| limestone / candle on the light fields | **2.39–2.95** | **FAIL** — never text, never focus indicators |
| naveStone on the light fields | within **2.39–2.95** | **FAIL** — never text, never focus indicators |

The failing pairings are recorded here precisely so nobody "promotes" a hairline colour into a caption. **Per-field colour rules:** no candle, limestone, or naveStone text on the light fields, ever — captions and meta use `--organPipe`; the failing tokens are decorative hairlines and the waveform only (decorative elements are contrast-exempt). Focus: `:focus-visible { outline: 2px solid var(--cassockRed); outline-offset: 3px }`.

### theme-color

`<meta name="theme-color" content="#FAF6EE">` — a **deliberate deviation** from the site's `#F7F3EE`. It matches this page's own ground. Site-wide meta sweeps must not "correct" it.

## Voicing selector

The page's signature component: the enquirer explores the ensemble at four sizes before being asked for anything.

- **Four sizes, always written as words** — Eight, Twelve, Sixteen, Twenty-four voices. Digit forms ("a choir of 24") are banned by the house-claims validator (see Copy rules). Default selection: Twelve.
- **Native radio semantics.** Four radio cards, `name="voicing-choice"`, values `eight | twelve | sixteen | twenty-four`, inside a fieldset with a screen-reader-only legend. Native radios give the radiogroup and arrow-key behaviour for free; no ARIA re-implementation.
- **On change**, three things happen: the prose note in an `aria-live="polite"` region swaps to that voicing's description; the enquiry form's ensemble-size select syncs to match; and the media slot swaps to that voicing's video.
- **Media is YouTube, not audio files** (owner's correction to the brief). The site's existing click-to-load pattern: a poster button that swaps in a `youtube-nocookie.com` iframe only on click, restyled for this register. Nothing third-party loads before a click.
- **Video IDs come only from `data/seo-fix-discovered-urls.yml`** — the single source of truth for video identities and dates. A new video is added to that file first, with verified dates, before its ID may appear in the page's config.
- **`null` means no player.** A voicing with no mapped video renders prose and form-sync only — no dead play button, no empty frame. Until the owner maps videos (a `MANUAL-ACTIONS` item), the whole component ships in this state and reads as designed, not broken.

## Enquiry form

Application-style: the form's register does some of the qualifying before the budget question does the rest.

**Fields:** Name*, Email*, Telephone, Enquiring as* (planner / venue or hotel / private client — reveals a conditional Company field), Event date with a "date not yet fixed" checkbox, Venue and location*, Occasion*, Ensemble size (Eight / Twelve / Sixteen / Twenty-four voices / Guidance welcome — synced from the voicing selector), Indicative budget for music*, free-text message, How did you hear about us (with a referral follow-up field). Hidden: access key, subject line, UTM ×5, gclid, `voicing_explored`, `time_on_page`, honeypot.

**Budget bands:** Under £5,000 · £5,000–£10,000 · £10,000–£25,000 · £25,000+ · Prefer to discuss. **"Under £5,000" stays, and stays first** — owner's decision. No routing by band: every enquiry lands in the same inbox and gets the same reply. The bands are the only £ figures on the page, and they are the client's budget, not our prices.

**hCaptcha, matching the rest of the site.** The page was first specified without one, on the argument that a challenge box between a luxury planner and the send button costs conversions that are individually worth thousands, and that the honeypot plus a timing check would carry the load. That argument was weighed and set aside on 2026-08-26: the shared Web3Forms access key rejects token-less submissions, and a form that silently fails is worse than a form with friction. The guard mirrors `js/form.js` — it blocks only when the widget actually rendered, so a blocked or failed captcha script still lets the request through to the generic error with the email and phone fallback, and the token is reset after a failed send. The `botcheck` honeypot and the minimum-seconds timing check remain in place alongside it; both are client-side deterrents only, and Web3Forms is the only server involved.

**Honest note on what that protection is:** the honeypot and timing check are **client-side deterrents only**. Web3Forms is the only server in the pipeline and there is no server-side validation under our control — a bot that posts directly to the endpoint bypasses both. Accepted risk: possible spam rise on the shared access key; the distinct subject line enables inbox filtering. This paragraph exists so nobody later mistakes the deterrents for security.

**Submission:** inline confirmation — the success message replaces the form in place and receives focus. **No thank-you redirect**; the page stays alive so the conversion can fire. The Ads conversion fires inline via `gtag` on successful submit, using the **existing generic Contact conversion label** — tracking works from day one — to be swapped for a dedicated "Private events enquiry" conversion action once the owner creates one (`MANUAL-ACTIONS`).

## Structured data

One script, strict JSON, one `@graph`:

- **`Service`** — `@id …/private-events.html#service`, serviceType "Private and international choral engagements", `provider` referencing the existing `https://londonchoralservice.com/#organization` node. That node already carries `legalName: "Alma Consort Ltd"`, so the legal relationship rides the existing graph; nothing is redefined.
- **`PerformingGroup`** — `@id …/#alma-consort`, name "Alma Consort", `url` and `sameAs` pointing at `https://www.almaconsort.com`, `parentOrganization` referencing the same `#organization` stub.

**No `BreadcrumbList`** — deliberate. Under full insulation the page has no visible breadcrumb trail, and breadcrumb schema without a visible trail misdescribes the page. **No `AggregateRating` or `Review`, ever** — prohibited site-wide.

## Copy rules

Every visible string — headlines, body, form labels and microcopy, meta description, OG text, alt text, JSON-LD description strings, the llms.txt line — passes **both** the `writing-site-copy` skill and the `stop-slop` skill before commit. UK English throughout.

Banned outright, enforced by the house-claims validator:

- **"five-star"** in any form — write "luxury hotels".
- **Digit-form voicings** — "roster of 24", "a choir of 16"; sizes are words, and "roster" itself is avoided.
- **Any VAT-registration wording.** Alma Consort Ltd is not VAT-registered; the page says nothing about VAT either way.
- **"over 150"** or any roster-scale claim — the site's positioning is hand-picked, not big-book.

## Non-goals

- **A named-singer roster.** Standing owner decision, site-wide. Proof of quality is the credential, the recordings, and the fixed-ensemble argument.
- **Prices anywhere on the page.** The budget bands are the enquirer's figures, not ours; nothing on this page quotes or implies a fee.
- **Review or rating schema.** Prohibited site-wide.
- **A form without a captcha.** Specified, then reversed on 2026-08-26 — see above.
- **The standard nav/footer partials.** The insulation rationale above is the decision record.
- **A dark design.** Considered and dropped by the owner; the light parchment register is the decision.
- **An on-site `/alma-consort` page.** The ensemble's home is the external, owner-controlled `almaconsort.com`; a second home on this domain would split it.
- **Links from `compare/` or any `for-*.html` page.** Those funnels stay priced and B2B; this page is neither.
