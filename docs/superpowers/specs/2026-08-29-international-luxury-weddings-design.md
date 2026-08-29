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
| **D** | Destination pages | `/destinations/` — index plus twenty-two country pages |

**Success metric, unchanged from the private-events spec: cost per qualified enquiry.** Twenty-two destination pages producing five serious conversations a month have done their job. Twenty-two pages producing two hundred tyre-kickers have made the inbox worse, and at this page count that is the live risk rather than a theoretical one.

## The one architectural decision: the register becomes a partial

`private-events.html` carries its own hand-authored 545-line `<style>` block (lines 64–609) because the private register must not enter `css/pages.css`, which the build would inline into every other page on the site. That reasoning is correct and stands.

It does not survive being copied twenty-five times. Twenty-five hand-maintained duplicates of the same stylesheet is the kind of drift that produces a page in the wrong red eighteen months from now, and every one of them is a fresh chance to delete the Pass A comment.

**The existing partial mechanism solves this with no change to `build.sh`.** Partial expansion (build.sh:27–63) runs *before* Pass A (build.sh:75–112). A `<style>` block delivered by a partial is materialised into the page, then examined by Pass A exactly like a hand-authored one — and skipped, because its first inner line is a comment rather than `:root {`. So:

- **`partials/private-register.css.html`** — the `<style>` block, comment first, becomes the single source of truth for the register.
- **`partials/private-footer.html`** — the two-line private footer, identical on every page in the register.
- **Headers stay hand-authored per page.** They differ (the destination pages carry a visible breadcrumb; the hub does not) and they are six lines each. A partial with three variants would cost more than it saves.

`private-events.html` migrates onto the style partial in the same change. **The migration must produce a byte-identical built page** — `git diff private-events.html` after the migration build shows only the two include markers appearing around an otherwise unchanged block. That is the acceptance test, and it is cheap to run.

Two invariants carry over unchanged and now apply to the partial:

- **Never remove the comment line at the top of the `<style>` block.** Without it the next build replaces the whole register with the site bundle.
- **No page in the private register may contain a `style.css` link.** Pass B inlines the site bundle wherever that link appears.

## The destinations

Twenty-two countries, confirmed by the owner on 2026-08-29.

| Group | Countries | Regions |
|---|---|---|
| **Europe, short-haul** | Italy | Tuscany, Amalfi Coast, Lake Como, Puglia, Florence |
| | Spain | Ibiza, Mallorca, Marbella, Tenerife |
| | Portugal | The Algarve, Sintra, Porto, Lisbon |
| | France | Dordogne, Loire Valley, French Riviera (Côte d'Azur), Provence |
| | Greece | Santorini, Rhodes, Crete, Zakynthos, Mykonos |
| | Cyprus | Paphos, Ayia Napa, Protaras |
| | Malta | Valletta, Mdina, Gozo |
| | Croatia | Dubrovnik, Hvar, Split, Istria |
| | Gibraltar | The Rock, Botanical Gardens |
| | Ireland | To be set with the owner |
| | Scotland | To be set with the owner |
| **Americas** | United States | Las Vegas, New York City, Florida (Orlando and Miami) |
| | Mexico | Riviera Maya, Cancún, Tulum |
| | Barbados | St James, Christ Church, St Peter |
| | St Lucia | Soufrière, Rodney Bay |
| | Jamaica | Montego Bay, Negril, Ocho Rios |
| **Indian Ocean** | Mauritius | Belle Mare, Le Morne, Grand Baie |
| | Maldives | North Malé Atoll, South Ari Atoll |
| | Seychelles | Mahé, Praslin, La Digue |
| **Asia-Pacific** | Thailand | Phuket, Koh Samui |
| | Indonesia (Bali) | Uluwatu, Ubud, Seminyak |
| **Africa** | South Africa | Cape Town, Franschhoek (Cape Winelands), the Kruger area |

**Scotland is the odd one out and should read that way.** It carries no flights, no permits and no overnight premium beyond the ordinary, so its page is the one that says the published UK rates apply — on the same deliberate exception as the hub's cost FAQ linking `/pricing.html`. Ireland is the short-haul, no-permit case.

## Two page shapes, not one

The differentiating material is not the same across twenty-two countries, and a spec that pretends otherwise produces twenty-two pages with the same headings and different nouns.

**Shape 1 — the rite spine.** Italy, Spain, Portugal, France, Malta, Croatia, Ireland, and, genuinely, **Barbados, Jamaica and St Lucia**: deep Anglican traditions in the first two and a Catholic one in the third mean an English choral consort is culturally coherent there rather than incongruous, and that is worth saying plainly. These pages are built on the rite and running order, which parts are sung in Latin and which in the vernacular, what a bilingual congregation needs, and what the buildings do to the voicing.

**Shape 2 — the no-building spine.** Maldives, Bali, Thailand, Seychelles, Mauritius, Mexico, and the resort end of Greece, Cyprus and the United States. There is no rite and often no building. The page is built on what changes without one: singing outdoors with no stone acoustic and no organ, what heat and humidity do to voices and to a schedule, what a consort actually does at a civil or beach ceremony, and why the voicing recommendation moves.

Greece, Cyprus, the United States and Mexico straddle both and need the split handled inside the page, not fudged.

## Work permits are a content pillar, not a footnote

This is the strongest trust content available on these pages and simultaneously the most useful qualifying fact, so it is specified rather than left to the writer.

- **The United States is the hard case.** Paid performance requires a P-1/P-2 or O petition — months of lead time and real cost, for every singer. A US page that implies a quick booking is both wrong and commercially damaging. It says the lead time plainly.
- **The Schengen area** for a group of twelve to twenty-four British musicians post-Brexit: A1 certificates, the 90/180 rule, ETIAS, and per-country practice that genuinely differs.
- **Mexico, Thailand, Indonesia, the Maldives** each carry their own permit questions for paid performers.

Facts must be checked at the time of writing and carry a **visible checked date**, on the pattern the `compare/` pages already use for competitor pricing. Anything uncertain is written as "ask us", never guessed. Re-check quarterly.

## Non-negotiable: these must not be doorway pages

Twenty-two pages of the shape "Hire a British choir for your wedding in *[country]*", differing by a find-and-replace, are doorway pages under Google's spam policies. They are also the obvious way to build this, which is why the constraint is written down here rather than left to judgement. At twenty-two pages the risk is materially higher than it was at four.

**Ship test:** at least 60% of each destination page's body copy must be unique to that page, and a reader comparing any two pages must find country-specific answers, not synonyms. A page that fails this does not ship — it is better to launch fifteen destinations than twenty-two.

## Granularity: country pages, regions as sections

Region queries carry the intent ("wedding choir Lake Como"); country-level facts carry the substance (rite, sung language, work permits, invoicing). Sixty-four region pages built now would each restate the same country legal content — precisely the failure above.

**The site already solves this shape.** `areas/` holds twenty city pages and `areas/london/` holds thirty-three borough pages: an established two-tier local-SEO pattern in this repo. Destinations mirror it.

- **`/destinations/<country>.html`** is the substantive page. Every region in the table above gets a real anchored section within it, so "Lake Como" is indexed from day one.
- **`/destinations/<country>/<region>.html` is a later phase**, and only where region-specific substance genuinely exists: the venue types and their acoustics, the airport and transfer, the shape of ceremonies there. **A region page that would restate its country's rite or permit content does not ship as a page — it stays a section.** A region page links up to its country page for that material rather than repeating it.

Twenty-two excellent country pages that rank beat eighty-six mediocre ones that get filtered, and region pages built on top of solid country pages start from a better position than region pages alone.

## Package markets: build them, let the economics qualify

The destination list mixes luxury markets (Como, Amalfi, Tuscany, Côte d'Azur, Ibiza, Mallorca, Santorini, Mykonos, Franschhoek) with volume and package markets (Ayia Napa, Zante, Tenerife, Las Vegas, Orlando) where the whole wedding often costs less than flying the consort out.

Both are built. Every destination page carries an honest cost-drivers section — the hub's own three, singers, distance and nights, with no prices — plain enough that an unaffordable enquiry self-selects out before it reaches the inbox. Reach, without wrecking the metric.

**Consequence: the budget bands need a higher ceiling.** They currently stop at "£25,000+", which for a Maldives or Bali engagement is the floor rather than the ceiling, and so stop discriminating exactly where these engagements begin. The private register moves to:

> Under £5,000 · £5,000–£10,000 · £10,000–£25,000 · £25,000–£50,000 · £50,000+ · Prefer to discuss

**"Under £5,000" stays, and stays first.** That was an explicit owner decision about the bottom band and adding to the top does not disturb it. Bands are the enquirer's figures, never ours, and every form now **labels them as pounds sterling** — defensible when unlabelled on a page a UK reader lands on, wrong on a page written for someone marrying in Tulum.

## Truthfulness constraint

The site must not claim engagements it has not performed. Every workstream here is written in the register of *capability and process* — what we do, how we do it, what it depends on — never invented history.

- **The twenty-two-country footprint is confirmed by the owner, 2026-08-29**, including the ultra-long-haul destinations (Maldives, Seychelles, Mauritius, Bali, Thailand). These pages may assert that we travel there. **This confirmation is recorded here so a later reader does not strip the long-haul pages as over-claims** — the hub's own FAQ still named only four countries when it was written, and that is now out of date rather than a limit.
- No "we have sung at" for a venue where we have not sung. The hub's London venue list (private-events.html:782–791) is vetted; the destination pages get no equivalent list until there is one to write.
- No named clients, no invented case studies. The hub already commits to not naming private clients; a destination page inventing one would contradict its own hub.

## The hub is now out of date and in scope

`private-events.html` was written for a four-country world:

- **Line 708** — "Europe, North America, and the Gulf" no longer describes the footprint.
- **Line 852** — the "Where do you travel?" answer names only Italy, France, Ireland and Scotland.
- **Its JSON-LD `areaServed`** carries `United Kingdom` plus a generic `International` place.

All three are rewritten in the same change that ships the destinations index, so the hub and its children never contradict each other. The rewrite must not turn the FAQ answer into a list of twenty-two countries — it points at the index.

## URL and register decisions

| Path | Register | Reasoning |
|---|---|---|
| `/private-events.html` | Private | Stays. Has inbound links, a sitemap entry, and a live Ads conversion. Do not move it. |
| `/destinations/index.html` | Private | Hub for the country pages; linked from the private-events "Where do you travel?" answer. |
| `/destinations/<country>.html` | Private | Twenty-two pages. Country in the path; keyword work happens in the title and H1. |
| `/destinations/<country>/<region>.html` | Private | Later phase, on the `areas/london/` precedent. |
| `/planners-and-venues.html` | Private | **Deliberately not `for-planners-and-venues.html`.** The `for-*.html` prefix is the LCS B2B register — priced, nav-linked, VAT-reclaiming business buyers. This page is the opposite audience and must not be mistaken for one. |
| `music-guides/destination-wedding-choir.html` | LCS | The only public-register asset here. It earns the search traffic and hands it up. |

**Link direction stays one-way.** The LCS site may point into the private register; the private register does not point back out into the priced funnel. The two deliberate exceptions are the hub's cost FAQ linking `/pricing.html` and the Scotland page doing the same.

**No page here is linked from any `for-*.html` page or from `compare/`.**

## Nav: no change

No new page enters `partials/nav.html`. Two reasons: the Services dropdown is already long, and every page added to it is another priced-context neighbour for the private register. This also keeps each shipment's diff readable — no site-wide nav rebuild across ~130 files.

Reachability without nav: hub → destinations index → country pages → region pages, and back up at every level; hub ↔ planners-and-venues; the existing `weddings.html` and `about.html` links into the hub; the eighteen wedding guides (Workstream C); and the new guide.

## Workstream A — the guide

`music-guides/destination-wedding-choir.html`, in the LCS register, `weddings` category, built by the `new-page` clone-an-exemplar workflow from an existing wedding guide.

It answers the question a couple actually types: **can we bring a British choir to our wedding abroad, and what does that involve?** Cost drivers honestly (singers, distance, nights), lead times including the US permit reality, what travels and what does not, what the venue needs to provide, and the rite-and-language question in outline. It hands off to `/private-events.html` and `/destinations/`.

Search intent currently unserved by this site: *uk choir destination wedding*, *hire british choir wedding abroad*, *english choir italy wedding*, *choir for wedding in tuscany*, *british singers wedding france*.

**One guide, written properly, not five thin ones.** The site already has eighteen wedding guides; the marginal value of a nineteenth is in depth.

## Workstream B — planners and venues

`/planners-and-venues.html` expands what is currently three paragraphs on the hub (private-events.html:836–839) into the page a planner can send to a client or file as a supplier record.

Content: how a standing arrangement works; what we need from a planner and by when; what we provide unprompted (insurance, risk assessments, method statements, confidentiality agreement); the running order and the day-before rehearsal; invoicing in pounds sterling, euros or US dollars; and what a venue's events team specifically needs to know — where the consort stands, what the acoustic does, what we do not need (no stage, no PA, no piano).

It carries the same enquiry form as the hub, with "Enquiring as" defaulting to planner.

**Deliberately a second page rather than a longer hub.** The hub serves private principals as much as planners; a hub that opens with insurance certificates loses the principal, and a planner who has to scroll past a voicing selector to find the supplier facts loses patience. Two audiences, two entry points, one form.

## Workstream C — feeding the hub

Each of the eighteen wedding music-guides gains **one** in-copy sentence linking into the private register — to `/destinations/` where the guide's subject suggests a destination, otherwise to `/private-events.html`. It sits in the existing closing CTA section (the `<h2>Let us help you plan your wedding music</h2>` block, e.g. music-guides/wedding-ceremony-music.html:2527) or the `related-guides` block below it.

Constraints that make this a content edit rather than a find-and-replace:

- **The sentence must fit the guide it sits in.** A hymn-choice guide and an organ-repertoire guide reach the international question by different routes. Eighteen identical sentences would read as boilerplate to a human and as a template to a crawler.
- **It must not undercut the LCS funnel.** The guides serve UK couples on the published rates; the international line is an aside for the minority marrying abroad, not a redirect. Model it on the existing weddings.html hand-off (weddings.html:2404), which does exactly this in one sentence.
- **Wedding guides only** — never a funeral or Christmas guide.

## Enquiry attribution

Every page's form carries a static hidden input `source_page` with the page's own path as its value. Without it, twenty-five pages feed one inbox and the metric — cost per qualified enquiry, per page — cannot be computed, which makes the whole programme unmeasurable.

`js/private-events.js` needs **no change**. It is already null-guarded throughout (the voicing selector, media slot and ensemble select are all optional, js/private-events.js:56–64), so a page without a voicing selector runs it safely, and a static hidden input is submitted by `FormData` without any script. New pages reuse the same element IDs (`pe-enquiry`, `pe-form-success`, `ensemble-size`, and the rest) so the existing handler binds unchanged.

The Ads conversion continues to fire on the existing generic Contact label. Segmenting it is an owner action.

## Structured data

Each private-register page carries one `@graph`:

- **`Service`** — `@id <page>#service`, `provider` referencing the existing `https://londonchoralservice.com/#organization` node, `areaServed` naming the country as a `Country` node. Nothing about the organisation is redefined.
- **`FAQPage`** — the page's own visible questions, text matching the rendered copy verbatim. 126 pages on this site already do this.
- **`BreadcrumbList`** — **yes on the destination pages**, because unlike the hub they carry a *visible* trail (Private Events › Destinations › Italy). The hub's spec omits breadcrumb schema precisely because it has no visible trail; the rule was never "no breadcrumbs in this register", it was "no schema without the trail it describes".

The guide follows the existing music-guide schema pattern. **No `AggregateRating` or `Review`, anywhere, ever.**

## Copy rules

Every visible string passes **both** the `writing-site-copy` and `stop-slop` skills before commit. UK English throughout — including for the United States page. The house-claims validator (`validate_house_claims.py`) enforces:

- **"five-star"** in any form — write "luxury hotels".
- **Digit-form voicings** — sizes are words; "roster" is avoided.
- **Any VAT-registration wording.** Alma Consort Ltd is not VAT-registered.
- **"over 150"** or any roster-scale claim.

Register-specific, carried over from the hub: **"elite" is banned outright**, and the private register never describes itself as a premium tier of LCS — both invite the reader to re-price the rest of the site downwards.

Twenty-two pages is enough repetition for house-voice drift to become invisible from inside. The copy audit is run per page against a fresh reading, not per batch.

## Non-goals

- **Region pages in the first shipments.** Country pages first; regions are anchored sections until a region earns its own page.
- **Prices on any private-register page.** The budget bands are the enquirer's figures. The hub's `/pricing.html` link in its cost FAQ, and the Scotland page's equivalent, are the only exceptions.
- **Nav entries for any new page.**
- **Links from `compare/` or any `for-*.html` page.**
- **Named clients, invented case studies, or venue lists we cannot vouch for.**
- **Review or rating schema.** Prohibited site-wide.
- **A second CSS bundle or any change to `build.sh`.** The partial mechanism already does what is needed; changing the build to solve a problem partials solve is the expensive wrong answer.
- **Moving or renaming `/private-events.html`.** It has inbound links, a sitemap entry, and a live conversion action.
