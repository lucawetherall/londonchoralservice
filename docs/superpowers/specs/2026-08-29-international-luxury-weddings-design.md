# International and destination wedding engagements — design doc

**Date:** 2026-08-29
**Author:** Luca Wetherall (with Claude)
**Status:** Draft for review
**Related:** [docs/superpowers/plans/2026-08-29-international-luxury-weddings.md](../plans/2026-08-29-international-luxury-weddings.md), [2026-08-26-private-events-design.md](2026-08-26-private-events-design.md), [private-events.html](../../../private-events.html), [MANUAL-ACTIONS-REQUIRED.md](../../../MANUAL-ACTIONS-REQUIRED.md)

---

## Goal

Win more international and destination wedding engagements for Alma Consort by building out the demand side of a page that already exists. `/private-events.html` converts the enquiries that reach it. Almost nothing sends enquiries to it: outside the shared nav, exactly **two** pages on this site carry an in-copy link to it — `about.html` and `weddings.html`. Eighteen wedding music-guides, the traffic the site actually earns, point nowhere near it.

Four workstreams, in the owner's priority order:

| # | Workstream | Deliverable |
|---|---|---|
| **A** | Search intent nobody targets | One guide: `music-guides/destination-wedding-choir.html` |
| **B** | Planners, venues and estates | One private-register page: `/planners-and-venues.html` |
| **C** | Feed the hub from existing traffic | In-copy links from the eighteen wedding guides |
| **D** | Destination pages | `/destinations/` — index plus Italy, France, Ireland, Scotland |

**Success metric, unchanged from the private-events spec: cost per qualified enquiry.** Four destination pages producing two serious conversations a month have done their job. Four pages producing forty tyre-kickers have made the inbox worse.

## The one architectural decision: the register becomes a partial

`private-events.html` carries its own hand-authored 545-line `<style>` block (lines 64–609) because the private register must not enter `css/pages.css`, which the build would inline into every other page on the site. That reasoning is correct and stands.

It does not survive being copied six times. Six hand-maintained duplicates of the same stylesheet is the kind of drift that produces a page in the wrong red eighteen months from now, and every one of them is a fresh chance to delete the Pass A comment.

**The existing partial mechanism solves this with no change to `build.sh`.** Partial expansion (build.sh:27–63) runs *before* Pass A (build.sh:75–112). A `<style>` block delivered by a partial is materialised into the page, then examined by Pass A exactly like a hand-authored one — and skipped, because its first inner line is a comment rather than `:root {`. So:

- **`partials/private-register.css.html`** — the `<style>` block, comment first, becomes the single source of truth for the register.
- **`partials/private-footer.html`** — the two-line private footer, identical on every page in the register.
- **Headers stay hand-authored per page.** They differ (the destination pages carry a visible breadcrumb; the hub does not) and they are six lines each. A partial with three variants would cost more than it saves.

`private-events.html` migrates onto the style partial in the same change. **The migration must produce a byte-identical built page** — `git diff private-events.html` after the migration build shows only the two include markers appearing around an otherwise unchanged block. That is the acceptance test, and it is cheap to run.

Two invariants carry over unchanged and now apply to the partial:

- **Never remove the comment line at the top of the `<style>` block.** Without it the next build replaces the whole register with the site bundle.
- **No page in the private register may contain a `style.css` link.** Pass B inlines the site bundle wherever that link appears.

## Non-negotiable: these must not be doorway pages

Four pages of the shape "Hire a British choir for your wedding in *[country]*", differing by a find-and-replace, are doorway pages under Google's spam policies. They are also the obvious way to build this, which is why the constraint is written down here rather than left to judgement.

**Every destination page must carry material that appears nowhere else on this site**, and the material must be the reason a planner reads the page:

- **The rite.** A Catholic nuptial Mass in Italy is not a Church of Ireland service is not a humanist ceremony in a château. What the choir sings, and when, differs by rite — the ordinary, the acclamations, whether there is a Mass at all.
- **The language.** Which parts are sung in Latin, which in the local vernacular, what a bilingual congregation actually needs.
- **The building.** Tuscan stone churches, château salons and marquees, castle chapels and great halls each have a different acoustic, and that changes the voicing we recommend. This connects the page to the hub's voicing selector rather than restating it.
- **The logistics that are genuinely different.** Post-Brexit travel for a group of twelve to twenty-four British musicians into the Schengen area is not the same problem as flying to Ireland or driving to Scotland. A1 certificates, the 90/180 rule, and per-country permit practice are real buyer anxieties that nobody in this market writes about honestly.

**Ship test:** at least 60% of each destination page's body copy must be unique to that page, and a reader comparing any two pages must find country-specific answers, not synonyms. A page that fails this does not ship — it is better to launch three destinations than four.

## Truthfulness constraint

The site must not claim engagements it has not performed. Every workstream here is written in the register of *capability and process* — what we do, how we do it, what it depends on — never invented history.

- No "we have sung at" for a venue where we have not sung. The hub's London venue list (private-events.html:782–791) is vetted; the destination pages get no equivalent list until there is one to write.
- No named clients, no invented case studies. The hub already commits to not naming private clients; a destination page inventing one would contradict its own hub.
- The launch destinations are **Italy, France, Ireland, Scotland** because those are the four the hub's own FAQ already names ("Italy, France, Ireland, and Scotland come up most often", private-events.html:852). Adding Spain, Greece or the Gulf later is a documented pattern, not a launch scramble, and requires the owner to confirm the capability claim first.

## URL and register decisions

| Path | Register | Reasoning |
|---|---|---|
| `/private-events.html` | Private | Unchanged. Has inbound links, a sitemap entry, and a live Ads conversion. Do not move it. |
| `/destinations/index.html` | Private | Hub for the four country pages; linked from the private-events "Where do you travel?" answer. |
| `/destinations/{italy,france,ireland,scotland}.html` | Private | Country in the path; the keyword work happens in the title and H1. |
| `/planners-and-venues.html` | Private | **Deliberately not `for-planners-and-venues.html`.** The `for-*.html` prefix is the LCS B2B register — priced, nav-linked, VAT-reclaiming business buyers. This page is the opposite audience and must not be mistaken for one. |
| `music-guides/destination-wedding-choir.html` | LCS | The only public-register asset here. It earns the search traffic and hands it up. |

**Link direction stays one-way.** The LCS site may point into the private register; the private register does not point back out into the priced funnel. The one existing exception — the hub's cost FAQ linking `/pricing.html` — is deliberate and stays.

**No page here is linked from any `for-*.html` page or from `compare/`.**

## Nav: no change

None of the new pages enter `partials/nav.html`. Two reasons: the Services dropdown is already long, and every page added to it is another priced-context neighbour for the private register. This also means **the whole change touches ~25 files rather than ~130** — no site-wide nav rebuild, a diff a human can actually read.

Reachability without nav:
- Hub → destinations index → country pages (and back).
- Hub → planners-and-venues, and the reverse.
- `weddings.html` and `about.html` keep their existing in-copy links to the hub.
- The eighteen wedding guides gain one link each (Workstream C).
- The new guide links to the hub and to the destinations index.

## Workstream A — the guide

`music-guides/destination-wedding-choir.html`, in the LCS register, `weddings` category, built by the `new-page` clone-an-exemplar workflow from an existing wedding guide.

It answers the question a couple actually types: **can we bring a British choir to our wedding abroad, and what does that involve?** Cost drivers honestly (singers, distance, nights — the hub's own three), lead times, what travels and what does not, what the venue needs to provide, and the rite-and-language question in outline. It hands off to `/private-events.html` and `/destinations/`.

Search intent currently unserved by this site or, as far as the SERP work in `MANUAL-ACTIONS-REQUIRED.md` §12 shows, well served by anyone: *uk choir destination wedding*, *hire british choir wedding abroad*, *english choir italy wedding*, *choir for wedding in tuscany*, *british singers wedding france*.

**One guide, written properly, not five thin ones.** The site already has eighteen wedding guides; the marginal value of a twenty-first is in depth, and five would trip the same doorway problem as the destination pages.

## Workstream B — planners and venues

`/planners-and-venues.html` expands what is currently three paragraphs on the hub (private-events.html:836–839) into the page a planner can send to a client or file as a supplier record.

Content: how a standing arrangement works; what we need from a planner and by when; what we provide unprompted (insurance, risk assessments, method statements, confidentiality agreement); the running order and the day-before rehearsal; invoicing in pounds sterling, euros or US dollars; and what a venue's events team specifically needs to know — where the consort stands, what the acoustic does, what we do not need (no stage, no PA, no piano).

It carries the same enquiry form as the hub, with the "Enquiring as" default set to planner.

**Deliberately a second page rather than a longer hub.** The hub serves private principals as much as planners; a hub that opens with insurance certificates loses the principal, and a planner who has to scroll past a voicing selector to find the supplier facts loses patience. Two audiences, two entry points, one form.

## Workstream C — feeding the hub

Each of the eighteen wedding music-guides gains **one** in-copy sentence linking to `/private-events.html`, placed in the existing closing CTA section (the `<h2>Let us help you plan your wedding music</h2>` block, e.g. music-guides/wedding-ceremony-music.html:2527) or the `related-guides` block below it.

Constraints that make this a content edit rather than a find-and-replace:

- **The sentence must fit the guide it sits in.** A hymn-choice guide and an organ-repertoire guide reach the international question by different routes. Eighteen identical sentences would read as boilerplate to a human and as a template to a crawler.
- **It must not undercut the LCS funnel.** The guides serve UK couples on the published rates; the international line is an aside for the minority marrying abroad, not a redirect. Model it on the existing weddings.html hand-off (weddings.html:2404), which does exactly this in one sentence.
- **Never from a funeral or Christmas guide.** Scope is the eighteen wedding guides only.

## Enquiry attribution

Every new page's form carries a static hidden input `source_page` with the page's own path as its value. Without it, five pages feed one inbox and the metric — cost per qualified enquiry, per page — cannot be computed, which makes the whole programme unmeasurable.

`js/private-events.js` needs **no change**. It is already null-guarded throughout (the voicing selector, media slot and ensemble select are all optional, js/private-events.js:56–64), so a page without a voicing selector runs it safely, and a static hidden input is submitted by `FormData` without any script. The new pages reuse the same element IDs (`pe-enquiry`, `pe-form-success`, `ensemble-size`, and the rest) so the existing handler binds unchanged.

The Ads conversion continues to fire on the existing generic Contact label. Segmenting it is an owner action, not a code change.

## Structured data

Each new private-register page carries one `@graph`:

- **`Service`** — `@id <page>#service`, `provider` referencing the existing `https://londonchoralservice.com/#organization` node, and `areaServed` naming the country as a `Country` node. The hub's Service node (private-events.html) is the model; nothing about the organisation is redefined.
- **`FAQPage`** — the page's own visible questions, text matching the rendered copy verbatim. 126 pages on this site already do this.
- **`BreadcrumbList`** — **yes on the destination pages**, because unlike the hub they carry a *visible* trail (Private Events › Destinations › Italy). The hub's spec omits breadcrumb schema precisely because it has no visible trail; the rule was never "no breadcrumbs in this register", it was "no schema without the trail it describes".

The guide follows the existing music-guide schema pattern. **No `AggregateRating` or `Review`, anywhere, ever.**

## Copy rules

Every visible string passes **both** the `writing-site-copy` and `stop-slop` skills before commit. UK English throughout. The house-claims validator (`validate_house_claims.py`) enforces:

- **"five-star"** in any form — write "luxury hotels".
- **Digit-form voicings** — sizes are words; "roster" is avoided.
- **Any VAT-registration wording.** Alma Consort Ltd is not VAT-registered.
- **"over 150"** or any roster-scale claim.

Register-specific, carried over from the hub: **"elite" is banned outright**, and the private register never describes itself as a premium tier of LCS — both invite the reader to re-price the rest of the site downwards.

**Budget bands are in pounds sterling and must say so** on any new form. The hub's bands are unlabelled, which is defensible on a page a UK reader lands on and wrong on a page written for someone marrying in Tuscany.

## What else is worth doing

Considered and **folded into the workstreams above**, because they are what stop the destination pages being thin:

- **Post-Brexit touring logistics** — A1 certificates, the Schengen 90/180 rule, ETIAS, per-country permit practice for a group this size. A real anxiety, honestly answered nowhere in this market. Facts must be checked at time of writing and carry a visible checked date, on the pattern the `compare/` pages already use for competitor pricing; nothing here is invented, and anything uncertain is written as "ask us" rather than guessed.
- **Multilingual repertoire** — the Latin ordinary, Italian and French motets, local hymnody. Answers "will this feel foreign to our guests?"
- **Currency clarity** on budget bands, above.

Considered and **out of scope for this change**, recorded so they are not re-derived:

- **Paid search on destination terms.** The hub already carries a reserved H1 variant for wedding-targeted paid traffic (private-events.html:711–716). Pairing it with these pages is the natural next step and an owner action.
- **Luxury planner-network and directory outreach**, and wedding-press placement. Business development, not site work — and the pages should exist before the outreach points at them.
- **A one-page planner PDF.** Worth doing once `/planners-and-venues.html` has settled; the LCS house-document style already exists to build it from.
- **Photography or video from an actual overseas engagement.** The single highest-value asset for this audience, and the one thing here that cannot be written. Owner action.

## Non-goals

- **A fifth, sixth or seventh destination at launch.** Four, each genuinely differentiated, beats eight thin ones. Adding a fifth is a documented pattern for later.
- **Prices on any private-register page.** The budget bands are the enquirer's figures, not ours. The hub's link to `/pricing.html` in the cost FAQ is the one deliberate exception and is not repeated.
- **Nav entries for any new page.** See above.
- **Links from `compare/` or any `for-*.html` page.**
- **Named clients, invented case studies, or venue lists we cannot vouch for.**
- **Review or rating schema.** Prohibited site-wide.
- **A second CSS bundle or any change to `build.sh`.** The partial mechanism already does what is needed; changing the build to solve a problem partials solve is the expensive wrong answer.
- **Moving or renaming `/private-events.html`.** It has inbound links, a sitemap entry, and a live conversion action.
