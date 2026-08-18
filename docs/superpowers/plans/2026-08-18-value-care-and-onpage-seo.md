# Value, Bespoke Care & On-Page SEO — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the site's real value and bespoke care as two reusable components across the money pages, then close the verified on-page SEO gaps.

**Architecture:** Static hand-authored HTML built by `./build.sh` (CSS inlining + partial expansion + JSON-LD validation). Component styling goes in `css/components.css` (inlined site-wide by the build). The **care strip** is identical everywhere, so it becomes a partial (`partials/care-strip.html`); the **value block** varies per service, so it is per-page HTML using shared classes. No framework, no unit tests — verification is `./build.sh`, `validate_jsonld.py`, targeted `grep` counts, meta-length checks, and local preview.

**Tech Stack:** HTML5, CSS custom properties (design tokens in `css/tokens.css`), Schema.org JSON-LD, `build.sh` (bash), `validate_jsonld.py` (python3). Source spec: `docs/superpowers/specs/2026-08-18-value-care-and-onpage-seo-design.md`.

---

## How to work this plan (read first — this is not a unit-tested codebase)

- **The "test" for each task is a verification command**, not a unit test. Every task states the check to run and the expected output. Run it *before* the change to see the current state where useful, and *after* to confirm.
- **Load `build-and-verify` before any `css/` or `partials/` change or bulk edit.** Load `writing-site-copy` before editing any visible text. Load `new-page` before creating `faq.html`.
- **`./build.sh` rewrites ~106 files** whenever CSS or a partial changes (it re-inlines CSS and re-expands markers). That large diff is expected for Tasks 1–2; each change must be confined to the inlined `<style>` block or the partial's marker region. Content-only page edits (Tasks 3–11) do **not** require a rebuild *unless* they add a `@include` marker (Tasks 4–9 add the care-strip marker, so they do).
- **Never hand-edit** an inlined `<style>` block or content between `@include-start/@include-end` markers — edit the source and rebuild.
- **Locate insertion points with the grep anchors given**, never line numbers.
- **After editing any page, bump its `<lastmod>` in `sitemap.xml`** to the edit date (house convention). A helper is in Task 12.
- **Commit style:** `feat(...)`, `fix(...)`, `copy: …`, `chore: …`, ending every message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Prices** anywhere must match `pricing.html`: soloist/organist/instrumentalist £250; small choir of four £1,150.

## File structure

| File | Action | Responsibility |
|---|---|---|
| `css/components.css` | Modify (append) | `.included-list` (value block) + `.care-steps` (care strip) styles |
| `partials/care-strip.html` | Create | The care strip markup — single source of truth, inlined into 7 pages |
| `pricing.html` | Modify | Value block by the tables; care strip absorbs "What happens next" |
| `funerals.html` | Modify | Value block + care strip + FAQ/FAQPage (Phase 2) |
| `weddings.html` | Modify | Value block + care strip + FAQ/FAQPage (Phase 2) |
| `corporate.html` | Modify | Value block + care strip |
| `christmas.html` | Modify | Value block + care strip |
| `services.html` | Modify | Value block + care strip |
| `index.html` | Modify | Care strip only |
| `faq.html` | Create | Consolidated FAQ hub (Phase 2) |
| `partials/footer.html` | Modify | Footer link to `/faq.html` (Phase 2) |
| `sitemap.xml`, `llms.txt` | Modify | New `/faq.html` entry + lastmod bumps |

---

## Reusable snippets (referenced by the page tasks below)

### SNIPPET A — Value block (per-page HTML)

Insert as its own top-level section (between other `<section>`s, not inside one). Replace `[[COORD]]` and `[[PRICE]]` from the variant table (SNIPPET C). Copy is final and stop-slop-clean; do not re-slop it.

```html
        <section class="section">
          <div class="prose">
            <h2>Included with every booking</h2>
            <p class="lede">One flat price, and a team chosen for your occasion.</p>
            <ul class="included-list">
              <li><span class="tick" aria-hidden="true">&#10003;</span><span>A one-to-one music consultation with our Artistic Director, Luca Wetherall (Tutor in Music, University of Oxford), who plans your repertoire with you.</span></li>
              <li><span class="tick" aria-hidden="true">&#10003;</span><span>A handpicked ensemble, matched to your occasion. We choose every singer for you, never send whoever is free from a rota.</span></li>
              <li><span class="tick" aria-hidden="true">&#10003;</span><span>All rehearsals, preparation, and sheet music.</span></li>
              <li><span class="tick" aria-hidden="true">&#10003;</span><span>[[COORD]]</span></li>
              <li><span class="tick" aria-hidden="true">&#10003;</span><span>A written quote, confirmed before you commit. No hidden fees.</span></li>
            </ul>
            <p class="included-price"><strong>[[PRICE]]</strong>, all in. Travel within Greater London included.</p>
          </div>
        </section>
```

### SNIPPET B — Care strip (marker pair only; build.sh fills it from the partial)

**Placement rule:** put the marker pair at the **top level, between two `<section>`s** — never inside an existing `<section>`/`.prose`, because the partial supplies its own `<section class="section">`. Nesting sections would produce invalid, double-padded markup.

```html
        <!-- @include-start partials/care-strip.html -->
        <!-- @include-end partials/care-strip.html -->
```

### SNIPPET C — Per-service variants

| Page | `[[COORD]]` (value block item 4) | `[[PRICE]]` (value block price line) |
|---|---|---|
| `funerals.html` | We coordinate with your venue and funeral director. | From &pound;250 for a solo singer |
| `weddings.html` | We coordinate with your venue, celebrant, and wedding planner. | From &pound;1,150 for a small choir of four |
| `corporate.html` | We coordinate with your venue and event organiser. | From &pound;1,150 for a small choir of four |
| `christmas.html` | We coordinate with your venue or office. | From &pound;1,150 for a small choir of four |
| `services.html` | We coordinate with your venue, funeral director, or wedding planner. | From &pound;250 for a soloist |
| `pricing.html` | We coordinate with your venue, funeral director, or wedding planner. | *(omit the `.included-price` line — the price table is adjacent)* |

### SNIPPET D — Testimonial pull-quote (existing quotes only — never invent)

Uses the existing `.pull-quote` component. Place **one** real, already-on-site quote per money page that lacks one. Verified quotes available to reuse:
- Pamela, Richmond — *"I rang up not really knowing what I wanted and she couldn't have been kinder…"* (currently on `pricing.html`)
- Tony, Battersea — *"…she just took the music completely off our hands. On the day it was honestly the most beautiful thing I've ever heard."* (currently on `pricing.html`)
- Margaret, Dulwich — *"…The moment they started singing, the whole room just fell silent. Dad would have been so chuffed."* (currently on area pages)

If none fits a page's tone (e.g. corporate), **leave the page without a quote** rather than invent one, and note it for the owner to supply a real corporate testimonial. Markup:

```html
        <figure class="pull-quote">
          <blockquote><p>&ldquo;QUOTE TEXT&rdquo;</p></blockquote>
          <figcaption>&mdash;&ensp;NAME, PLACE</figcaption>
        </figure>
```

---

## Phase 1 — Value & bespoke-care components (W1)

### Task 1: Component CSS

**Files:**
- Modify: `css/components.css` (append at end of file)

- [ ] **Step 1: Append the component styles**

Add to the end of `css/components.css`:

```css

/* ── Value block: "Included with every booking" ───────────────────── */
.included-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.included-list li {
  display: flex;
  gap: var(--space-sm);
  align-items: flex-start;
  padding-block: var(--space-sm);
  border-block-end: 1px solid var(--color-rule);
}
.included-list li:last-child {
  border-block-end: 0;
}
.included-list .tick {
  flex: none;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 50%;
  background: var(--color-bg-alt);
  color: var(--color-accent);
  display: grid;
  place-items: center;
  font-size: 0.8rem;
  margin-block-start: 0.15rem;
}
.included-price {
  margin-block-start: var(--space-lg);
  color: var(--color-text-mid);
}
.included-price strong {
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 1.2rem;
  color: var(--color-accent);
}

/* ── Care strip: "We take the whole thing off your hands" ──────────── */
.care-steps {
  list-style: none;
  padding: 0;
  margin-block: var(--space-lg);
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-lg);
}
.care-steps .n {
  display: block;
  font-family: var(--font-heading);
  font-weight: 600;
  font-size: 2rem;
  line-height: 1;
  color: var(--color-accent);
}
.care-steps h3 {
  font-size: 1.15rem;
  margin-block: var(--space-xs) var(--space-xs);
}
.care-steps p {
  margin: 0;
  color: var(--color-text-mid);
}
@media (max-width: 599px) {
  .care-steps {
    grid-template-columns: 1fr 1fr;
  }
}
```

- [ ] **Step 2: Rebuild**

Run: `./build.sh`
Expected: exits 0; prints CSS byte count, partials populated, files inlined, and ends with `JSON-LD valid in NNN files checked.`

- [ ] **Step 3: Verify the diff shape**

Run: `git diff --stat | tail -5`
Expected: `css/style.css` + `css/components.css` + ~106 HTML files changed. Spot-check one page is confined to its `<style>` block:
Run: `git diff -- index.html | grep -E '^[-+]' | grep -viE 'included|care-steps|--space|--color|border-block|place-items|grid-template' | grep -vE '^(\+\+\+|---)'`
Expected: empty (every changed line is inside the CSS block).

- [ ] **Step 4: Commit**

```bash
git add css/components.css css/style.css '*.html'
git commit -m "feat(components): add value-block and care-strip styles

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 2: Care-strip partial

**Files:**
- Create: `partials/care-strip.html`

- [ ] **Step 1: Create the partial**

Create `partials/care-strip.html` containing exactly:

```html
        <section class="section">
          <div class="prose">
            <h2>We take the whole thing off your hands</h2>
            <p class="lede">From your first message to the last note.</p>
            <ol class="care-steps">
              <li><span class="n">1</span><h3>You get in touch</h3><p>A message, a call, or WhatsApp. Just the date and the occasion.</p></li>
              <li><span class="n">2</span><h3>We plan the music</h3><p>Luca chooses the voices and repertoire with you.</p></li>
              <li><span class="n">3</span><h3>We do the rest</h3><p>Rehearsals, sheet music, and coordination with your venue.</p></li>
              <li><span class="n">4</span><h3>You just listen</h3><p>We arrive early, set up quietly, and sing.</p></li>
            </ol>
          </div>
        </section>
```

- [ ] **Step 2: Verify it is valid HTML and will be picked up**

Run: `test -f partials/care-strip.html && echo exists`
Expected: `exists`. (It is inlined into pages only where the marker pair is added — Tasks 3–9. No page references it yet, so `./build.sh` now is a no-op beyond confirming health.)

- [ ] **Step 3: Commit**

```bash
git add partials/care-strip.html
git commit -m "feat(components): add care-strip partial (single source of truth)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 3: pricing.html — value block + care strip (worked example)

**Files:**
- Modify: `pricing.html`

- [ ] **Step 1: Add the value block** immediately after the "Accompaniment & instruments" table closes, before the "Christmas & carol singers" section.

Anchor: `grep -n 'Accompaniment &amp; instruments' pricing.html` → the `</table></div></section>` that follows it. Insert SNIPPET A there (top level, between sections), using the `pricing.html` row of SNIPPET C (**omit** the `.included-price` line). It is additive.

- [ ] **Step 2: Replace the whole "What happens next" `<section>` with the care strip, preserving its facts.**

Anchor: `grep -n 'What happens next' pricing.html`. Replace the entire `<section>…</section>` containing `<h2>What happens next</h2>` with the block below — the marker pair (build fills it with the partial's own `<section>`), then a small section carrying the two facts the generic strip does not:

```html
        <!-- @include-start partials/care-strip.html -->
        <!-- @include-end partials/care-strip.html -->
        <section class="section">
          <div class="prose">
            <p class="text-sm text-mid">Most funeral bookings come at short notice; contact us and we will confirm availability the same day. For funerals and weddings in London, there are no travel costs.</p>
          </div>
        </section>
```

- [ ] **Step 3: Rebuild** (a marker was added).

Run: `./build.sh`
Expected: exits 0, JSON-LD valid.

- [ ] **Step 4: Verify care strip inlined and value block present**

Run: `grep -c 'care-steps' pricing.html; grep -c 'included-list' pricing.html`
Expected: `1` and `1`.
Run: `grep -c 'What happens next' pricing.html`
Expected: `0` (prose replaced).

- [ ] **Step 5: Preview**

Run: `python3 -m http.server 8000` (from repo root), open `http://localhost:8000/pricing.html`. Confirm: value block renders as a ticked list beside the pricing; the care strip shows four numbered steps; no raw `@include` comments visible; layout holds at 375px and 1280px.

- [ ] **Step 6: Bump lastmod + commit**

Set `pricing.html`'s `<lastmod>` in `sitemap.xml` to today. Then:

```bash
git add pricing.html sitemap.xml
git commit -m "feat(pricing): surface value block and care strip

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 4: funerals.html — value block + care strip + testimonial

**Files:**
- Modify: `funerals.html`

- [ ] **Step 1: Insert the value block.** Anchor: `grep -n '</h1>\|class="lede"\|<h2' funerals.html` — place SNIPPET A after the intro/hero section and before the first deep-content `<h2>`. Use the `funerals.html` row of SNIPPET C (`[[COORD]]` = "We coordinate with your venue and funeral director."; `[[PRICE]]` = "From &pound;250 for a solo singer").
- [ ] **Step 2: Insert the care strip** (SNIPPET B) lower down, before the closing CTA/contact section. Anchor: `grep -n 'contact.html\|Tell us about' funerals.html` — place it just above that CTA block.
- [ ] **Step 3: Add a testimonial** (SNIPPET D) using the Margaret/Dulwich quote, placed after the care strip.
- [ ] **Step 4: Rebuild** — `./build.sh` (exits 0, JSON-LD valid).
- [ ] **Step 5: Verify** — `grep -c 'care-steps\|included-list\|pull-quote' funerals.html` → each ≥ 1. Preview `http://localhost:8000/funerals.html` at 375px + 1280px.
- [ ] **Step 6: Bump `funerals.html` lastmod in `sitemap.xml`; commit** `feat(funerals): add value block, care strip, testimonial`.

### Task 5: weddings.html — value block + care strip

**Files:** Modify `weddings.html`

- [ ] **Step 1:** Insert SNIPPET A after the hero, before the first content `<h2>`. Variant: `[[COORD]]` = "We coordinate with your venue, celebrant, and wedding planner."; `[[PRICE]]` = "From &pound;1,150 for a small choir of four".
- [ ] **Step 2:** Insert SNIPPET B before the closing CTA (anchor `grep -n 'contact.html' weddings.html`).
- [ ] **Step 3:** Testimonial — **only if** the owner supplies a real wedding quote (do not repurpose the funeral quote); otherwise leave weddings without one. See SNIPPET D.
- [ ] **Step 4:** Rebuild — `./build.sh`.
- [ ] **Step 5:** Verify `grep -c 'care-steps\|included-list' weddings.html` → each 1; preview at 375px + 1280px.
- [ ] **Step 6:** Bump lastmod; commit `feat(weddings): add value block and care strip`.

### Task 6: corporate.html — value block + care strip

**Files:** Modify `corporate.html`

- [ ] **Step 1:** Insert SNIPPET A. Variant: `[[COORD]]` = "We coordinate with your venue and event organiser."; `[[PRICE]]` = "From &pound;1,150 for a small choir of four".
- [ ] **Step 2:** Insert SNIPPET B before the closing CTA. **No testimonial** (no real corporate quote exists — leave for the owner to supply).
- [ ] **Step 3:** Rebuild; **Step 4:** verify + preview; **Step 5:** bump lastmod; commit `feat(corporate): add value block and care strip`.

### Task 7: christmas.html — value block + care strip

**Files:** Modify `christmas.html`

- [ ] **Step 1:** Insert SNIPPET A. Variant: `[[COORD]]` = "We coordinate with your venue or office."; `[[PRICE]]` = "From &pound;1,150 for a small choir of four".
- [ ] **Step 2:** Insert SNIPPET B before the closing CTA.
- [ ] **Step 3:** Rebuild; **Step 4:** verify + preview; **Step 5:** bump lastmod; commit `feat(christmas): add value block and care strip`.

### Task 8: services.html — value block + care strip

**Files:** Modify `services.html`

- [ ] **Step 1:** Insert SNIPPET A. Variant: `[[COORD]]` = "We coordinate with your venue, funeral director, or wedding planner."; `[[PRICE]]` = "From &pound;250 for a soloist".
- [ ] **Step 2:** Insert SNIPPET B before the closing CTA.
- [ ] **Step 3:** Rebuild; **Step 4:** verify + preview; **Step 5:** bump lastmod; commit `feat(services): add value block and care strip`.

### Task 9: index.html — care strip only

**Files:** Modify `index.html`

- [ ] **Step 1:** Insert SNIPPET B **only** (no value block) between the "Who we are" section and the "What families tell us" section. Anchor: `grep -n 'Who we are\|What families tell us' index.html`.
- [ ] **Step 2:** Rebuild — `./build.sh`.
- [ ] **Step 3:** Verify `grep -c 'care-steps' index.html` → 1; `grep -c 'included-list' index.html` → 0. Preview the homepage at 375px + 1280px; confirm the strip sits cleanly between the two sections.
- [ ] **Step 4:** Bump lastmod; commit `feat(home): add care strip between about and testimonials`.

### Task 10: Phase 1 site-wide checks

- [ ] **Step 1:** `./build.sh` with no source change → clean tree (pipeline healthy). Run: `./build.sh && git diff --stat` → expect no output.
- [ ] **Step 2:** No rating/review schema was introduced. Run: `grep -rn 'AggregateRating\|"@type": "Review"' --include='*.html' . | grep -v node_modules` → empty.
- [ ] **Step 3:** Value block present on exactly 6 pages. Run: `grep -rl 'included-list' --include='*.html' . | wc -l` → `6`.
- [ ] **Step 4:** Care strip present on exactly 7 pages. Run: `grep -rl 'care-steps' --include='*.html' . | wc -l` → `7`.
- [ ] **Step 5:** JSON-LD valid — `python3 validate_jsonld.py` → `JSON-LD valid in NNN files checked.`

---

## Phase 2 — On-page SEO gaps (W2)

### Task 11: FAQPage schema + visible FAQ on funerals.html and weddings.html

**Files:** Modify `funerals.html`, `weddings.html`. Load `writing-site-copy` first.

- [ ] **Step 1: funerals.html — add a visible FAQ section** before the closing CTA. Each answer's visible text must match the schema `text` **exactly**.

```html
        <section class="section">
          <div class="prose">
            <h2>Funeral music questions</h2>
            <h3>How much notice do you need for a funeral?</h3>
            <p>We take bookings at short notice and confirm availability the same day. Most funerals come to us with one or two weeks' notice, and we have covered services booked within forty-eight hours. Tell us the date and we will tell you straight away whether we can be there.</p>
            <h3>Can you sing at a crematorium as well as a church?</h3>
            <p>Yes. We sing at crematoria, churches, cemetery chapels, and woodland burial sites across the UK. A soloist or small group suits the shorter crematorium slot; a larger choir suits a church service with hymns. We match the ensemble to the venue and the time you have.</p>
            <h3>Can you learn a song the family has asked for?</h3>
            <p>Yes. If a piece mattered to the person who died, we prepare it, whether it is a hymn, a pop song, or something from the classical repertoire. Send us the song and we arrange it for the voices you have booked.</p>
            <h3>Will the singers lead the hymns so guests feel confident?</h3>
            <p>That is one of the main reasons families book us. Trained voices carry the melody, so a congregation that half-remembers a hymn will still join in. It is the difference between a silent room and one that sings.</p>
          </div>
        </section>
```

- [ ] **Step 2: funerals.html — add the FAQPage node** to the page's existing `@graph` JSON-LD array (match the pattern already on `corporate.html`: `grep -n 'FAQPage' corporate.html`). Answer `text` must be byte-identical to the visible answers above.

```json
      {
        "@type": "FAQPage",
        "mainEntity": [
          { "@type": "Question", "name": "How much notice do you need for a funeral?", "acceptedAnswer": { "@type": "Answer", "text": "We take bookings at short notice and confirm availability the same day. Most funerals come to us with one or two weeks' notice, and we have covered services booked within forty-eight hours. Tell us the date and we will tell you straight away whether we can be there." } },
        { "@type": "Question", "name": "Can you sing at a crematorium as well as a church?", "acceptedAnswer": { "@type": "Answer", "text": "Yes. We sing at crematoria, churches, cemetery chapels, and woodland burial sites across the UK. A soloist or small group suits the shorter crematorium slot; a larger choir suits a church service with hymns. We match the ensemble to the venue and the time you have." } },
          { "@type": "Question", "name": "Can you learn a song the family has asked for?", "acceptedAnswer": { "@type": "Answer", "text": "Yes. If a piece mattered to the person who died, we prepare it, whether it is a hymn, a pop song, or something from the classical repertoire. Send us the song and we arrange it for the voices you have booked." } },
          { "@type": "Question", "name": "Will the singers lead the hymns so guests feel confident?", "acceptedAnswer": { "@type": "Answer", "text": "That is one of the main reasons families book us. Trained voices carry the melody, so a congregation that half-remembers a hymn will still join in. It is the difference between a silent room and one that sings." } }
        ]
      }
```

- [ ] **Step 3: weddings.html — add the visible FAQ section** before the closing CTA:

```html
        <section class="section">
          <div class="prose">
            <h2>Wedding music questions</h2>
            <h3>When in the ceremony does the choir sing?</h3>
            <p>A choir can sing as guests arrive, during the processional, at the signing of the register, and for the recessional, as well as leading the hymns. The signing of the register is the moment couples most often want a standout piece, since it fills two or three minutes that would otherwise be silent.</p>
            <h3>Can you perform a song that isn't a traditional hymn?</h3>
            <p>Yes. Alongside hymns and classical repertoire, we arrange pop songs, musical-theatre numbers, and folk pieces for our voices. If a song means something to you, send it over and we will tell you how it works for the ensemble you have in mind.</p>
            <h3>Do you sing with our church's organist, or bring your own?</h3>
            <p>Either. Where a church has its own organist we sing with them; where it does not, or theirs is unavailable, we bring an organist who has played that instrument. Adding an organist to a choir is &pound;225.</p>
            <h3>How many singers do we need for our venue?</h3>
            <p>Four voices fill most parish churches and give you full harmony; six or eight suit a cathedral or a long guest list. We advise once we know the building and the numbers. Our <a href="music-guides/wedding-choir-guide.html">wedding choir guide</a> walks through the options.</p>
          </div>
        </section>
```

- [ ] **Step 4: weddings.html — add the FAQPage node** to its `@graph` (answers byte-identical to Step 3; note the visible `&pound;225` becomes `£225` in the JSON `text`):

```json
      {
        "@type": "FAQPage",
        "mainEntity": [
          { "@type": "Question", "name": "When in the ceremony does the choir sing?", "acceptedAnswer": { "@type": "Answer", "text": "A choir can sing as guests arrive, during the processional, at the signing of the register, and for the recessional, as well as leading the hymns. The signing of the register is the moment couples most often want a standout piece, since it fills two or three minutes that would otherwise be silent." } },
          { "@type": "Question", "name": "Can you perform a song that isn't a traditional hymn?", "acceptedAnswer": { "@type": "Answer", "text": "Yes. Alongside hymns and classical repertoire, we arrange pop songs, musical-theatre numbers, and folk pieces for our voices. If a song means something to you, send it over and we will tell you how it works for the ensemble you have in mind." } },
          { "@type": "Question", "name": "Do you sing with our church's organist, or bring your own?", "acceptedAnswer": { "@type": "Answer", "text": "Either. Where a church has its own organist we sing with them; where it does not, or theirs is unavailable, we bring an organist who has played that instrument. Adding an organist to a choir is £225." } },
          { "@type": "Question", "name": "How many singers do we need for our venue?", "acceptedAnswer": { "@type": "Answer", "text": "Four voices fill most parish churches and give you full harmony; six or eight suit a cathedral or a long guest list. We advise once we know the building and the numbers. Our wedding choir guide walks through the options." } }
        ]
      }
```

- [ ] **Step 5: Validate JSON-LD** — `python3 validate_jsonld.py` → valid. Then confirm both pages now carry it: `for f in funerals.html weddings.html; do printf '%s ' $f; grep -c FAQPage $f; done` → each `1`.
- [ ] **Step 6: Dedup check (R10)** — no question string may repeat site-wide:

```sh
python3 -c "
import re,glob,collections
q=[]
for f in glob.glob('**/*.html',recursive=True):
    if f.startswith('.superpowers'): continue
    q += re.findall(r'\"@type\": \"Question\",\s*\"name\": \"([^\"]+)\"', open(f).read())
print([k for k,v in collections.Counter(q).items() if v>1] or 'unique')"
```
Expected: `unique`. If a clash appears, reword the new question (and its visible copy) until unique.

- [ ] **Step 7:** Bump `funerals.html` + `weddings.html` lastmod in `sitemap.xml`; commit `feat(seo): add FAQ + FAQPage schema to funerals and weddings`.

### Task 12: FAQ hub — faq.html

**Files:** Create `faq.html`; Modify `partials/footer.html`, `sitemap.xml`, `llms.txt`. Load `new-page` first.

- [ ] **Step 1: Clone an exemplar.** Copy an existing simple page (e.g. `privacy.html`) as the skeleton so the `<head>` (GA snippet, canonical, hreflang, OG/Twitter, nav/footer markers) is correct. Set: `<title>` "Frequently asked questions | The London Choral Service"; canonical `https://londonchoralservice.com/faq.html`; a unique meta description of **141–161 chars** (verify: `python3 -c "print(len('...'))"`).
- [ ] **Step 2: Curate 8–12 questions that do NOT duplicate any per-page FAQ** (booking lead time, areas covered, travel costs, what's included, deposits/payment, a cappella vs organ, choosing repertoire, short-notice funerals). Write answers in house style (`writing-site-copy`).
- [ ] **Step 3: Schema decision to avoid signal-splitting.** The hub carries **one** `FAQPage` node covering **only** questions not already marked up on another page. Any question that overlaps a service page stays schema-only on that page and appears on the hub as plain text (no duplicate `Question` node). Re-run the Step 6 dedup script from Task 11 → `unique`.
- [ ] **Step 4: Footer link.** In `partials/footer.html`, add near the privacy link (`grep -n 'privacy.html' partials/footer.html`): `<a href="/faq.html">FAQ</a>`. Then `./build.sh` (partial change → ~106-file diff, confined to footer marker region).
- [ ] **Step 5: Register the page.** Add a `<url>` block for `https://londonchoralservice.com/faq.html` with today's `<lastmod>` to `sitemap.xml`; add an `llms.txt` line under the appropriate section.
- [ ] **Step 6: Verify** — `./build.sh` exits 0; `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('sitemap.xml'); print('ok')"`; preview `http://localhost:8000/faq.html` (nav, footer, accordions/sections render; footer FAQ link works).
- [ ] **Step 7: Commit** `feat(seo): add FAQ hub, footer link, sitemap and llms entries`.

- [ ] **Step 8: lastmod helper** (reuse for any page task above). For a single page:

```sh
python3 -c "
import re,sys
f,url='PAGE.html','https://londonchoralservice.com/PAGE.html'
s=open('sitemap.xml').read()
s=re.sub(r'(<loc>'+re.escape(url)+r'</loc>\s*<lastmod>)[0-9-]+',r'\g<1>2026-08-18',s)
open('sitemap.xml','w').write(s)"
```

### Task 13: Internal-linking audit → money pages

**Files:** Modify assorted `music-guides/*.html` (only where a link is genuinely missing).

- [ ] **Step 1: Map current inbound links.** For each money page, count contextual (in-content, non-nav/footer) links from the guide layer:

```sh
for t in pricing.html funerals.html weddings.html corporate.html christmas.html services.html; do
  printf '%-16s ' "$t"; grep -rl "\"[^\"]*$t\"\|/$t\"\|\.\./$t\"" music-guides/*.html | wc -l
done
```

- [ ] **Step 2: Fill the gaps.** For any money page with thin inbound linking, add a **contextual** in-content link from 2–3 topically relevant guides, with commercial anchor text (e.g. from `funeral-music-costs.html` → "our funeral singers" → `funerals.html`). PR #79 already did a pass — only add where genuinely missing; do not double-link. Copy passes `writing-site-copy` (no "click here").
- [ ] **Step 3: Verify** no broken links introduced: `./build.sh` (JSON-LD unaffected) and spot-check the edited guides in preview. Bump lastmod for each edited guide.
- [ ] **Step 4: Commit** `feat(seo): strengthen internal links from guides to money pages`.

### Task 14: Per-service OG images — BLOCKED-ON-HUMAN (document only)

**Do not implement.** All pages share `assets/og-image.png`. Per-service images require assets from the owner. When they land in `assets/`, the wiring is: set `og:image` + `twitter:image` (and `image` in the page's JSON-LD where present) per service page, at 1200×630, then rebuild and validate.

- [ ] **Step 1:** Add a one-line entry to `MANUAL-ACTIONS-REQUIRED.md` noting the needed images (funerals, weddings, corporate, Christmas + hubs) and that wiring is ready once supplied. Commit `docs: note per-service OG images as a pending human action`.

---

## Definition of done

- Value block on 6 money pages; care strip on 7 pages; `pricing.html` "What happens next" absorbed without losing the same-day / no-London-travel facts.
- One real testimonial on funerals + weddings (others only if the owner supplies real quotes).
- `funerals.html` + `weddings.html` carry valid `FAQPage` schema with visible, byte-matching Q&A; every FAQ question unique site-wide.
- `/faq.html` live, footer-linked, in `sitemap.xml` + `llms.txt`, no duplicate FAQ schema.
- Internal-linking gaps to money pages filled.
- `./build.sh` exits 0; `python3 validate_jsonld.py` valid; no `AggregateRating`/`Review` schema anywhere; all copy passes `writing-site-copy`.
- OG images documented as a pending human action, not faked.
