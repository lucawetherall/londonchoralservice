# Barbershop Grams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Barbershop Grams product line — a hub page and a repertoire page in a new `/barbershop-grams/` directory with its own visual register, priced to match Barbershop-o-gram's £600 ten-minute gram — and wire it into pricing, nav, sitemap, and the claim validators.

**Architecture:** A second insulated register, built the same way as the private register: a scoped `<style>` partial plus its own nav and footer partials, carried by pages that never include `partials/nav.html`, `partials/footer.html`, or a `style.css` link. The main site links in from the Services dropdown, `services.html`, `pricing.html`, `weddings.html`, and `corporate.html`; the mini-site links back only from its footer. `pricing.html` stays the source of truth for every price.

**Tech Stack:** Hand-authored static HTML, `build.sh` (bash + awk) for CSS concat / partial expansion / CSS inlining, Python 3 validators (`validate_jsonld.py`, `validate_competitor_claims.py`, `validate_house_claims.py`), PyYAML, `python3 -m http.server` for preview.

**Spec:** `docs/superpowers/specs/2026-09-03-barbershop-grams-design.md`. Read it before Task 1. Where this plan says "spec §X", the copy or table lives there and must not be re-invented here.

**Skills to load before starting:** `build-and-verify` (mandatory — this plan touches `partials/`, which rewrites ~106 files), `writing-site-copy` and `anthropic-skills:stop-slop` (mandatory before writing any visible text), `new-page` (for the head checklist).

---

## Scope

**This plan implements spec Phase 1 and Phase 2.**

- **Phase 1 (Tasks 1–12)** ships the product line and can be merged on its own. No dependency on owner actions.
- **Phase 2 (Tasks 13–15)** is **gated on the barbershop recording existing** (spec Phase 0.1, an owner action in `MANUAL-ACTIONS-REQUIRED.md`). Do not start Task 13 until a YouTube ID for a barbershop recording is in `data/seo-fix-discovered-urls.yml`. If it is not there, stop after Task 12 and report.
- **Phase 3** (per-occasion pages) is triggered by Search Console evidence after a season live, not by this plan.
- **Phase 4** (ads, directories, partnerships, PR) is human-only and lives in `MANUAL-ACTIONS-REQUIRED.md`.

## File structure

| File | Responsibility | Task |
|---|---|---|
| `partials/barbershop-register.css.html` | Every style the mini-site uses. Scoped `bs-` prefix. Never the site bundle. | 1 |
| `partials/barbershop-nav.html` | Mini-site header: wordmark, three anchors, WhatsApp button | 2 |
| `partials/barbershop-footer.html` | Mini-site footer, including the one link back to `/` | 2 |
| `barbershop-grams/index.html` | The hub. Birthday-led. Carries `Service` + `Offer` + `FAQPage` + `BreadcrumbList` | 4, 5 |
| `barbershop-grams/repertoire.html` | The published song list. `ItemList` + `BreadcrumbList` | 6 |
| `validate_house_claims.py` | Extend `FILES` to cover the new directory | 3 |
| `validate_jsonld.py` | Extend `FILES` to cover the new directory | 3 |
| `pricing.html` | New "Barbershop Grams" section — source of truth for the five prices | 7 |
| `contact.html` | New `<option value="barbershop-gram">` so the enquiry pre-fill works | 8 |
| `partials/nav.html` | Services-dropdown entry (partial edit → mandatory rebuild) | 9 |
| `services.html` | One card in the ensemble grid + one `Offer` in the `OfferCatalog` | 9 |
| `weddings.html`, `corporate.html` | One in-copy sentence each, for the "barbershop quartet hire London" head term | 9 |
| `sitemap.xml`, `llms.txt` | Wiring | 10 |
| `docs/ROADMAP.md` | Record the shipped item | 11 |
| `data/competitor-pricing.yml` | The one sourced competitor figure | 13 |
| `validate_competitor_claims.py` | Support `price_inc_vat`; it currently crashes on any package without `price_ex_vat` | 13 |
| `tests/test_competitor_claims.py` | Test that an unlisted competitor tier fails the build | 13 |
| `compare/barbershopogram.html` | The one-number comparison page | 14 |
| `barbershop-grams/listen.html` | Recordings, once they exist | 15 |

**Never touched by this plan:** `funerals.html`, `music-guides/funeral-*`, `compare/london-funeral-singers.html`, any `for-*.html`, `private-events.html`, `destinations/`, `index.html`. Spec §Non-goals: a bereaved family must never meet a birthday gram.

---

## Task 1: The register partial

**Files:**
- Create: `partials/barbershop-register.css.html`
- Reference (read, do not modify): `partials/private-register.css.html`

The private register is 639 lines and already solves the fonts, the reset, the section rhythm, the type scale, the button, and the reduced-motion block. Copy it and transform, rather than authoring from scratch — but the token block and the comment header must be rewritten, and the `pe-` prefix must become `bs-` so nothing collides.

- [ ] **Step 1: Copy the private register as the starting skeleton**

```bash
cp partials/private-register.css.html partials/barbershop-register.css.html
```

- [ ] **Step 2: Rename the class prefix**

Rename **every** `pe-` occurrence, not just class selectors. The file also carries `#pe-form-success`, `@keyframes pe-rise`, `@keyframes pe-draw`, and the `animation:` properties that reference them; a selector-only rename leaves those pointing at nothing. This was verified against the real file — the broad substitution is the correct one:

```bash
sed -i '' 's/pe-/bs-/g' partials/barbershop-register.css.html
grep -c 'pe-' partials/barbershop-register.css.html
```

Expected: `0`. A stray `pe-` would silently inherit nothing, because the site bundle is not on these pages.

- [ ] **Step 3: Replace the comment header**

Replace the first nine lines of the file (the `/* Private register … */` comment, keeping `  <style>` as line 1) with exactly this. **The first inner line of the block must stay a comment** — that is what stops `build.sh` Pass A from mistaking this block for the generated bundle and replacing it with a `style.css` link.

```html
  <style>
    /* Barbershop register — bespoke scoped styles for barbershop-grams/ and
       compare/barbershopogram.html. NOT the generated site bundle.
       Never replace this block with the site's generated CSS bundle: the first
       inner line of this block being a comment is what stops build.sh Pass A
       from converting it. A page carrying this partial must never also link the
       generated site stylesheet: Pass B would inline the whole site bundle on top.
       See docs/superpowers/specs/2026-09-03-barbershop-grams-design.md */
```

- [ ] **Step 4: Replace the token block**

Find the `:root {` block (it follows the four `@font-face` rules) and replace the whole block, including the private register's COLOUR LAW comment above it, with this. Contrast ratios are computed, not estimated.

```css
    /* ── Page tokens (gift register) ──
       COLOUR LAW (computed WCAG contrast):
                        on --bs-paper   on --bs-cream
         --bs-ink            16.13 AAA      14.29 AAA   body and headings
         --bs-navy           10.75 AAA       9.52 AAA   occasion labels, table heads
         --bs-red             6.12 AA        5.42 AA    accents, buttons, small caps — NOT long body text
         --bs-mid             5.85 AA        5.18 AA    captions, secondary text
       Reversed (paper on red, paper on navy) is symmetric: 6.12 and 10.75 — both fine for buttons.
       --bs-rule is a hairline only: never text, never a focus outline. */
    :root {
      --bs-ink:    #1F1A17;
      --bs-mid:    #6B5E56;
      --bs-red:    #B3261E;
      --bs-navy:   #1F3A5F;
      --bs-paper:  #FBF7EF;
      --bs-cream:  #F1E9DA;
      --bs-rule:   #DCD2C2;
      --font-display: 'Cormorant Garamond', 'Iowan Old Style', Georgia, serif;
      --font-body:    'Source Serif 4', Georgia, 'Times New Roman', serif;
      --font-ui:      'Source Serif 4', Georgia, 'Times New Roman', serif;
    }
```

- [ ] **Step 5: Repoint every old token name at the new ones**

Run this **after** Step 4, not before: Step 4 deletes the old declarations and the old COLOUR LAW comment, which is where most of the old names live.

```bash
sed -i '' \
  -e 's/var(--parchmentLight)/var(--bs-paper)/g' \
  -e 's/var(--parchment)/var(--bs-cream)/g' \
  -e 's/var(--choirStall)/var(--bs-ink)/g' \
  -e 's/var(--organPipe)/var(--bs-mid)/g' \
  -e 's/var(--cassockRed)/var(--bs-red)/g' \
  -e 's/var(--limestone)/var(--bs-rule)/g' \
  -e 's/var(--naveStone)/var(--bs-rule)/g' \
  -e 's/var(--candle)/var(--bs-navy)/g' \
  partials/barbershop-register.css.html
grep -n 'parchment\|choirStall\|organPipe\|cassockRed\|limestone\|naveStone\|candle' partials/barbershop-register.css.html
```

Expected: **9 hits, all cosmetic** — verified against the real file. Six are stale comments from the private register's colour law (`/* cassockRed use 1 of 4: rail small-caps labels */`, `/* ── Buttons: outline only, never a candle fill ── */`, and similar), and three are the class name `.bs-hairline--candle`. No `var(--…)` reference should remain. Delete the stale comments (they describe a colour law that no longer applies — the new one is in Step 4) and rename `.bs-hairline--candle` to `.bs-hairline--accent` throughout:

```bash
sed -i '' 's/bs-hairline--candle/bs-hairline--accent/g' partials/barbershop-register.css.html
grep -c 'var(--parchment\|var(--choirStall\|var(--organPipe\|var(--cassockRed\|var(--limestone\|var(--naveStone\|var(--candle' partials/barbershop-register.css.html
```

Expected: `0`.

- [ ] **Step 5b: Delete the CSS the gram pages cannot use**

The private register carries an enquiry form, a voicing selector, and a video play button. Gram pages have none of those: they CTA to WhatsApp and `contact.html`, and the listen page (Task 15) is not built yet. Shipping the rules would put roughly 100 lines of dead CSS into every page carrying this partial.

Delete these rule groups: `.bs-form`, `.bs-form-error`, `#bs-form-success`, `.bs-voicing` and its children, `.play-btn` and its children, and the `@keyframes bs-rise` / `@keyframes bs-draw` pair together with the `html.bs-motion` hero-animation block that drives them.

```bash
grep -c 'bs-form\|bs-voicing\|play-btn\|bs-rise\|bs-draw\|form-success' partials/barbershop-register.css.html
```

Expected: `0` when the deletion is complete (it is `16` before). Keep `.bs-hero__inner` and `.bs-hero__cta` themselves — the hero layout stays; only the animation that referenced the deleted keyframes goes.

Delete four more carried-over groups in the same pass, for the same reason — no planned page produces their markup:

- **`.bs-group`, `.bs-dests` (and children), `.bs-region`** — destination-card and country-page components. The hub uses `.bs-occasions`; the repertoire page uses `.bs-rep`. Deleting `.bs-dests` also removes the file's only hardcoded colour literal, `rgba(126, 24, 24, .045)`, which is the *old* palette's red and which no `var()` substitution in Step 5 can reach.
- **`.bs-venues` and its `40rem` media query** — a near-duplicate of the `.bs-rep` added in Step 7, and the source of a third mobile breakpoint that serves nothing.

**Keep `.bs-breadcrumb` and `.bs-crumb-sep`:** `repertoire.html` carries a three-level `BreadcrumbList` and a visible trail is a plausible addition. But repoint the separator — `.bs-crumb-sep { color: var(--bs-rule); }` uses the hairline token as text at 1.40:1, which this file's own colour law forbids. Change it to `var(--bs-mid)` (5.85:1).

Delete the `html.bs-motion [data-fade]` entrance-animation rules and any paired `.bs-in` rules too. Nothing sets `html.bs-motion`: `js/private-events.js` sets `pe-motion`/`pe-in`, and no barbershop JS exists or is planned (Task 4 strips that script). The gram pages get no fade-in, deliberately. **Keep the `scroll-behavior: smooth` rule and its `prefers-reduced-motion: no-preference` wrapper** — the hub's occasion strip is all in-page anchors, so that one is live.

Finally, fix three comments that the clone made false: the buttons heading says "outline only" though Step 7 adds `.bs-btn--fill`; a `background: var(--bs-navy)` rule carries a "never text" caveat that applied to the old `--candle` (2.39:1) and not to navy (10.75:1); and the breadcrumb heading plus any remaining comments name "destinations" and "country pages" that do not exist here.

**Placement matters.** Append the Step 7 components **before** the "Focus & utilities" section, not at the end of the file, so the `prefers-reduced-motion: reduce` block stays the file's tail as in the precedent. Appending at the tail splits `.bs-btn--fill` from `.bs-btn` by ~224 lines and creates a live cascade trap: `.bs-occasions a` would declare its `transition` *after* the reduce block, so later adding that selector to the block would silently fail on equal specificity. While there, add `.bs-occasions a` to the reduce block's `transition: none` rule alongside `.bs-btn`.

- [ ] **Step 6: Warm the type scale**

The private register's `h1` is `clamp(3.2rem, 7vw, 4.75rem)` at weight 300 — a cathedral. This product is a gift. Replace the `h1` rule with:

```css
    h1 {
      font-family: var(--font-display);
      font-size: clamp(2.5rem, 5.5vw, 3.75rem);
      font-weight: 500;
      line-height: 1.15;
    }
```

- [ ] **Step 7: Append the gram-specific components**

Add before the closing `</style>`. These are the components the private register has no equivalent for.

```css
    /* ── Occasion strip ── */
    .bs-occasions {
      display: flex;
      flex-wrap: wrap;
      gap: .625rem;
      list-style: none;
      margin-top: 2rem;
    }
    .bs-occasions a {
      display: inline-block;
      font-family: var(--font-ui);
      font-size: .8125rem;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--bs-navy);
      text-decoration: none;
      border: 1px solid var(--bs-rule);
      padding: .5rem 1rem;
      transition: border-color .2s, color .2s;
    }
    .bs-occasions a:hover { border-color: var(--bs-navy); }
    .bs-occasions .bs-occasions__lead a {
      color: var(--bs-paper);
      background: var(--bs-navy);
      border-color: var(--bs-navy);
    }

    /* ── Price table ── */
    .bs-prices {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1.5rem;
    }
    .bs-prices th {
      font-family: var(--font-ui);
      font-size: .6875rem;
      font-weight: 600;
      letter-spacing: .18em;
      text-transform: uppercase;
      color: var(--bs-navy);
      text-align: left;
      border-bottom: 1px solid var(--bs-rule);
      padding: 0 1rem .75rem 0;
    }
    .bs-prices td {
      border-bottom: 1px solid var(--bs-rule);
      padding: 1.125rem 1rem 1.125rem 0;
      vertical-align: top;
    }
    .bs-prices td:last-child {
      white-space: nowrap;
      text-align: right;
      padding-right: 0;
      font-variant-numeric: tabular-nums;
    }
    .bs-prices .bs-prices__flag {
      display: block;
      font-family: var(--font-ui);
      font-size: .6875rem;
      letter-spacing: .12em;
      text-transform: uppercase;
      color: var(--bs-red);
      margin-top: .35rem;
    }
    @media (max-width: 39.9375rem) {
      .bs-prices thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
      .bs-prices tr { display: block; border-bottom: 1px solid var(--bs-rule); padding-block: 1rem; }
      .bs-prices td { display: block; border: 0; padding: 0 0 .35rem 0; }
      .bs-prices td:last-child { text-align: left; font-weight: 600; }
    }

    /* ── Checklist ── */
    .bs-check { list-style: none; margin-top: 1.5rem; }
    .bs-check li {
      position: relative;
      padding-left: 1.75rem;
      margin-top: .875rem;
    }
    .bs-check li::before {
      content: "";
      position: absolute;
      left: 0;
      top: .55em;
      width: .5rem;
      height: .5rem;
      border: 1px solid var(--bs-red);
    }

    /* ── FAQ ── */
    .bs-faq { margin-top: 1.5rem; }
    .bs-faq details {
      border-bottom: 1px solid var(--bs-rule);
      padding-block: 1.125rem;
    }
    .bs-faq summary {
      font-family: var(--font-display);
      font-size: 1.3125rem;
      cursor: pointer;
      list-style: none;
    }
    .bs-faq summary::-webkit-details-marker { display: none; }
    .bs-faq summary::after {
      content: "+";
      float: right;
      color: var(--bs-red);
      font-family: var(--font-ui);
    }
    .bs-faq details[open] summary::after { content: "\2013"; }
    .bs-faq details > p { margin-top: .875rem; }

    /* ── Repertoire groups ── */
    .bs-rep { columns: 2; column-gap: 2.5rem; list-style: none; margin-top: 1rem; }
    .bs-rep li { break-inside: avoid; padding-block: .28rem; }
    @media (max-width: 39.9375rem) { .bs-rep { columns: 1; } }

    /* ── Filled button variant, for the primary CTA ── */
    .bs-btn--fill {
      color: var(--bs-paper);
      background: var(--bs-ink);
      border-color: var(--bs-ink);
    }
    .bs-btn--fill:hover {
      background: var(--bs-red);
      border-color: var(--bs-red);
      color: var(--bs-paper);
    }
```

- [ ] **Step 7b: Give the hero CTA row a gap**

The inherited `.bs-hero__cta` is `margin-top: 2.5rem` and nothing else, because the exemplar's hero carried a single button. The hub's hero has two, which would sit against each other with only a space between them and get no vertical gap when they stack. **Modify the existing rule in place** — do not append a second `.bs-hero__cta` block, which would leave one selector defined in two places:

```css
    .bs-hero__cta {
      display: flex;
      flex-wrap: wrap;
      gap: .75rem;
      margin-top: 2.5rem;
    }
```

```bash
grep -c '\.bs-hero__cta {' partials/barbershop-register.css.html
```

Expected: `1`.

- [ ] **Step 8: Verify Pass A cannot eat this block**

```bash
grep -n '^  <style>$' -A 1 partials/barbershop-register.css.html | head -3
```

Expected: line 1 is `  <style>`, line 2 is the `/* Barbershop register …` comment — **not** `:root {`. Pass A only converts a `  <style>` whose next line matches `:root {` (`build.sh` Pass A). If line 2 is `:root {`, the next build destroys this file's effect on every page carrying it.

- [ ] **Step 9: Commit**

```bash
git add partials/barbershop-register.css.html
git commit -m "feat(barbershop): scoped register stylesheet for the grams mini-site"
```

---

## Task 2: Nav and footer partials

**Files:**
- Create: `partials/barbershop-nav.html`
- Create: `partials/barbershop-footer.html`

- [ ] **Step 1: Write the nav partial**

```html
  <header class="bs-header">
    <nav class="bs-nav" aria-label="Barbershop Grams">
      <a class="bs-wordmark" href="/barbershop-grams/">Barbershop Grams</a>
      <a class="bs-nav-enquire" href="/barbershop-grams/repertoire.html">Repertoire</a>
      <a class="bs-nav-enquire" href="/barbershop-grams/#prices">Prices</a>
      <a class="bs-nav-enquire" href="https://wa.me/447356042468?text=Hello%20London%20Choral%20Service%2C%20I%27d%20like%20to%20send%20a%20Barbershop%20Gram.%20Date%3A%20%2F%20Place%3A%20%2F%20Who%20it%27s%20for%3A" target="_blank" rel="noopener" data-whatsapp>WhatsApp</a>
    </nav>
  </header>
```

The `?text=` pre-fill is gram-specific on purpose: it is how gram WhatsApp clicks are told apart from site-wide ones in GA4 (spec §Measurement). `data-whatsapp` matches the attribute the site already uses on WhatsApp links.

- [ ] **Step 2: Write the footer partial**

```html
  <footer class="bs-footer">
    <p><a href="mailto:office@londonchoralservice.com">office@londonchoralservice.com</a> &middot; <a href="tel:+447356042468">07356 042468</a> &middot; London</p>
    <p>Barbershop Grams is a product of <a href="/">The London Choral Service</a>, the operating name of Alma Consort Ltd, registered in England and Wales, company no. 16785727. <a href="/privacy.html">Privacy policy</a></p>
  </footer>
```

That link to `/` is the only **funnel** link from the mini-site back into the main site (spec §Linking): the main site points inward from its Services dropdown, but the mini-site does not lead a gift buyer onward into funeral and wedding content. Do not add more of those.

`/privacy.html` in the same line is not a funnel link and is required: these pages carry the site-wide GA4/Google Ads snippet, the site has no cookie banner, and `privacy.html` is where every other footer points for cookie disclosure. Keep it.

- [ ] **Step 3: Add the header and footer styles to the register**

Append to `partials/barbershop-register.css.html` before `</style>`. The copied private register has `.bs-header`, `.bs-nav`, `.bs-wordmark`, `.bs-nav-enquire`, and `.bs-footer` rules already (renamed in Task 1); this only adjusts the nav to hold four links instead of two.

```css
    .bs-nav { flex-wrap: wrap; gap: 1.25rem; }
    .bs-nav .bs-wordmark { margin-right: auto; }
```

- [ ] **Step 4: Commit**

```bash
git add partials/barbershop-nav.html partials/barbershop-footer.html partials/barbershop-register.css.html
git commit -m "feat(barbershop): nav and footer partials for the grams mini-site"
```

---

## Task 3: Extend the claim validators to cover the new directory

Both validators use an explicit `FILES` list. A new directory is invisible to them, which means a banned claim could ship in the new pages and the build would still pass. Prove the gap with a probe file before fixing it.

**Files:**
- Modify: `validate_house_claims.py:47-56`
- Modify: `validate_jsonld.py:9-17`

- [ ] **Step 1: Write the failing probe**

```bash
mkdir -p barbershop-grams
cat > barbershop-grams/_probe.html <<'EOF'
<!DOCTYPE html>
<html lang="en-GB"><head><title>probe</title>
<script type="application/ld+json">{ "broken": }</script>
</head><body><p>We are VAT-registered and rated 5 stars.</p></body></html>
EOF
```

- [ ] **Step 2: Run both validators to verify they miss it**

```bash
python3 validate_house_claims.py; echo "house exit=$?"
python3 validate_jsonld.py; echo "jsonld exit=$?"
```

Expected: **both exit 0**, and neither names `barbershop-grams/_probe.html`. That is the bug — a page with a VAT claim, a star-rating claim, and invalid JSON-LD passes the build.

- [ ] **Step 3: Extend `validate_house_claims.py`**

Replace the `FILES` tuple at `validate_house_claims.py:47`:

```python
FILES = (
    glob.glob('*.html')
    + glob.glob('areas/*.html')
    + glob.glob('areas/**/*.html')
    + glob.glob('music-guides/*.html')
    + glob.glob('compare/*.html')
    + glob.glob('destinations/*.html')
    + glob.glob('destinations/**/*.html')
    + glob.glob('barbershop-grams/*.html')
    + ['llms.txt']
)
```

- [ ] **Step 4: Extend `validate_jsonld.py`**

Add one line to its `FILES` expression (after the `compare/*.html` line at `validate_jsonld.py:14`):

```python
    glob.glob('compare/*.html') +
    glob.glob('barbershop-grams/*.html') +
```

- [ ] **Step 5: Run both validators to verify they now catch it**

```bash
python3 validate_house_claims.py; echo "house exit=$?"
python3 validate_jsonld.py; echo "jsonld exit=$?"
```

Expected: **both exit 1**. `validate_house_claims.py` names `barbershop-grams/_probe.html` twice (VAT-registration claim, self-reported rating claim). `validate_jsonld.py` names it for the unparseable block.

- [ ] **Step 6: Delete the probe and confirm the build is clean again**

```bash
rm barbershop-grams/_probe.html
python3 validate_house_claims.py && python3 validate_jsonld.py && echo BOTH_CLEAN
```

Expected: `BOTH_CLEAN`.

- [ ] **Step 7: Commit**

```bash
git add validate_house_claims.py validate_jsonld.py
git commit -m "fix(validators): cover barbershop-grams/ in house-claim and JSON-LD checks"
```

---

## Task 4: The hub page — head, chrome, and schema

**Files:**
- Create: `barbershop-grams/index.html`
- Reference: `private-events.html` (the only existing exemplar of a register-carrying page)

Build the page in two tasks: the shell and schema here, the body copy in Task 5. Both commit.

- [ ] **Step 1: Copy the exemplar's shell**

```bash
cp private-events.html barbershop-grams/index.html
```

- [ ] **Step 2: Swap the register, nav, and footer includes**

In `barbershop-grams/index.html`, change the three marker pairs. The content between markers can stay stale — `./build.sh` re-expands it — but the **marker names** must be right or the build expands the wrong partial.

```bash
sed -i '' \
  -e 's|partials/private-register.css.html|partials/barbershop-register.css.html|g' \
  -e 's|partials/private-footer.html|partials/barbershop-footer.html|g' \
  barbershop-grams/index.html
grep -c 'partials/private' barbershop-grams/index.html
```

Expected: `0`.

`private-events.html` has a hand-written `<header>` rather than a nav partial. Replace its `<header class="pe-header">…</header>` block (opens around `private-events.html:917`) with a marker pair:

```html
  <!-- @include-start partials/barbershop-nav.html -->
  <!-- @include-end partials/barbershop-nav.html -->
```

- [ ] **Step 2b: Strip the two inherited script tags**

The exemplar ends with two `<script src="…">` tags (`private-events.html:1245-1246`) and the clone carries both. Neither belongs on a gram page:

```html
  <script src="https://web3forms.com/client/script.js" async defer></script>
  <script src="/js/private-events.js" defer></script>
```

The Web3Forms script serves that page's embedded enquiry form; gram pages have no form and send people to WhatsApp or `contact.html`, so keeping it is a third-party request for nothing. `js/private-events.js` sets `pe-motion` and `pe-in` on the document element, which the barbershop register does not style — and Task 1 deleted the `[data-fade]` rules on exactly that basis. Delete both lines.

```bash
grep -c 'private-events.js\|web3forms.com/client' barbershop-grams/index.html
```

Expected: `0`. The GA4/Google Ads snippet in the `<head>` stays — that is site-wide and unrelated.

Stripping those scripts orphans two `<link rel="dns-prefetch">` hints in the head, since nothing on the page will contact either host any more. Delete them in the same step:

```html
  <link rel="dns-prefetch" href="https://api.web3forms.com">
  <link rel="dns-prefetch" href="https://hcaptcha.com">
```

Keep the `googletagmanager` prefetch — the GA4 snippet still uses it.

- [ ] **Step 2c: Fix the inherited relative asset paths**

The exemplar sits at the site root, so its favicon and apple-touch-icon links are relative (`href="assets/favicon.ico"`). This page is one directory down, where those resolve to `/barbershop-grams/assets/…` and 404. Change them to absolute (`/assets/…`), matching `destinations/*.html`, which is the site's other subdirectory page on this pattern.

```bash
grep -n 'href="assets/' barbershop-grams/index.html
```

Expected: no output. Every asset reference in the head should be absolute or already partial-sourced.

- [ ] **Step 3: Replace the head metadata**

Replace the title through `twitter:image:alt` block with exactly this. Both descriptions are the same string, 154 characters, verified below. `og-barbershop-grams.png` does not exist yet (owner action, spec Phase 0.5), so the shared `og-image.png` is used until it does.

```html
  <title>Barbershop Grams | Surprise Barbershop Quartet in London</title>
  <meta name="description" content="Send a surprise barbershop quartet to someone in London: Happy Birthday in four-part harmony at their desk, door, or table. &pound;600 all in, 48 hours' notice.">
  <meta name="theme-color" content="#FBF7EF">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://londonchoralservice.com/barbershop-grams/">
  <link rel="alternate" hreflang="en-gb" href="https://londonchoralservice.com/barbershop-grams/">
  <link rel="alternate" hreflang="x-default" href="https://londonchoralservice.com/barbershop-grams/">

  <meta property="og:title" content="Barbershop Grams | Surprise Barbershop Quartet in London">
  <meta property="og:description" content="Send a surprise barbershop quartet to someone in London: Happy Birthday in four-part harmony at their desk, door, or table. &pound;600 all in, 48 hours' notice.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://londonchoralservice.com/barbershop-grams/">
  <meta property="og:locale" content="en_GB">
  <meta property="og:site_name" content="London Choral Service">
  <meta property="og:image" content="https://londonchoralservice.com/assets/og-image.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Barbershop Grams: four singers sent to surprise someone in London">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Barbershop Grams | Surprise Barbershop Quartet in London">
  <meta name="twitter:description" content="Send a surprise barbershop quartet to someone in London: Happy Birthday in four-part harmony at their desk, door, or table. &pound;600 all in, 48 hours' notice.">
  <meta name="twitter:image" content="https://londonchoralservice.com/assets/og-image.png">
  <meta name="twitter:image:alt" content="Barbershop Grams: four singers sent to surprise someone in London">
```

- [ ] **Step 4: Verify the meta description length**

```bash
python3 -c "print(len(\"Send a surprise barbershop quartet to someone in London: Happy Birthday in four-part harmony at their desk, door, or table. £600 all in, 48 hours' notice.\"))"
```

Expected: `154` — inside the required 141–161 (CLAUDE.md). Count the decoded `£`/`'`, not the entities.

- [ ] **Step 5: Replace the JSON-LD**

Delete every `application/ld+json` block inherited from `private-events.html` and insert **one** block containing an `@graph` of three nodes. House convention, verified across `weddings.html`, `funerals.html`, `corporate.html`, `carol-singers.html` and `private-events.html`: one script tag, one `@context`, `Service` + `BreadcrumbList` + `FAQPage` as siblings in `@graph`. Three separate script islands would work but would diverge from every comparable page for no reason.

`provider` is an `@id` reference to the canonical Organization node defined in `index.html`, **never an inlined copy** — `weddings.html:2206`, `funerals.html:2206` and `carol-singers.html:2207` all use this exact shape. An inlined duplicate creates a second unlinked representation of the same business, works against entity resolution, and would be strictly worse than the canonical node because it omits its `postalCode` and `geo`.

The `Offer` carries only the £600 gram: a "from" price is not an offer, so the other four tiers get no `Offer` (spec §Page 1).

```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Service",
        "name": "Barbershop Grams",
        "serviceType": "Singing telegram",
        "description": "A barbershop quartet sent to surprise one person in London with Happy Birthday in four-part harmony and a song chosen for them.",
        "url": "https://londonchoralservice.com/barbershop-grams/",
        "provider": {
          "@type": "LocalBusiness",
          "@id": "https://londonchoralservice.com/#organization"
        },
        "areaServed": {
          "@type": "AdministrativeArea",
          "name": "Greater London"
        },
        "offers": {
          "@type": "Offer",
          "name": "Surprise Barbershop Gram",
          "description": "Up to ten minutes. Four singers sing Happy Birthday in four-part harmony and one song from the repertoire, chosen for the recipient.",
          "price": "600",
          "priceCurrency": "GBP",
          "priceValidUntil": "2027-12-31",
          "availability": "https://schema.org/InStock",
          "url": "https://londonchoralservice.com/barbershop-grams/#prices"
        }
      },
      {
        "@type": "BreadcrumbList",
        "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://londonchoralservice.com/" },
          { "@type": "ListItem", "position": 2, "name": "Barbershop Grams", "item": "https://londonchoralservice.com/barbershop-grams/" }
        ]
      },
      {
        "@type": "FAQPage",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "How much notice do you need?",
            "acceptedAnswer": { "@type": "Answer", "text": "48 hours. Valentine's week and December book up well before that, so ask early for those." }
          },
          {
            "@type": "Question",
            "name": "Where will you sing?",
            "acceptedAnswer": { "@type": "Answer", "text": "Anywhere in Greater London we can get four singers into: offices, homes, restaurants, pubs, parks, and care homes. Hospital wards need the ward's permission first, which we will ask for." }
          },
          {
            "@type": "Question",
            "name": "What happens if they are not there?",
            "acceptedAnswer": { "@type": "Answer", "text": "Tell us before the singers set off and we rearrange once at no charge. After they have set off the fee stands, because four singers have given up the slot." }
          },
          {
            "@type": "Question",
            "name": "How do you keep it a surprise?",
            "acceptedAnswer": { "@type": "Answer", "text": "We only ever contact the number you give us. We never ring or email the recipient, and we do not post anything about a booking before it happens." }
          },
          {
            "@type": "Question",
            "name": "Can you sing a song that is not on your repertoire list?",
            "acceptedAnswer": { "@type": "Answer", "text": "Yes. We arrange your song for four voices from £200. Allow a week so the singers can rehearse it properly." }
          },
          {
            "@type": "Question",
            "name": "Can we film it?",
            "acceptedAnswer": { "@type": "Answer", "text": "Yes, and we would like a copy. We ask the person who was surprised for permission before we post anything ourselves." }
          },
          {
            "@type": "Question",
            "name": "Is there a cheaper version?",
            "acceptedAnswer": { "@type": "Answer", "text": "No. A Barbershop Gram is four voices, because four is what makes the harmony. We do hire single singers from £250, but that is a different thing and we do not sell it as a gram." }
          },
          {
            "@type": "Question",
            "name": "Who will be singing?",
            "acceptedAnswer": { "@type": "Answer", "text": "Four singers chosen for your booking by Luca Wetherall, our Artistic Director and Tutor in Music at the University of Oxford, who auditions every musician on the team himself." }
          }
        ]
      }
    ]
  }
  </script>
```

- [ ] **Step 6: Build, then verify the page did not get the site bundle**

Cloning the exemplar copies the *expanded* content sitting between its include markers — the private register's CSS and the private footer. Renaming the markers does not change that; only a build does. So build here rather than deferring it, or the commit captures a page carrying the wrong register.

The build is idempotent, so with no CSS or partial source changes the diff must show only this new file:

```bash
./build.sh
git status --short
```

Expected: only `barbershop-grams/index.html`. **Any other modified file means something upstream is wrong — stop and investigate before committing.**

Then confirm Pass A did not swap in the site bundle:

```bash
grep -c 'color-bg:' barbershop-grams/index.html      # 0
grep -c 'style.css' barbershop-grams/index.html      # 0
grep -c 'bs-ink' barbershop-grams/index.html         # non-zero: the barbershop register
grep -c 'choirStall' barbershop-grams/index.html     # 0: not the private one
python3 validate_jsonld.py && python3 validate_house_claims.py
```

A non-zero `color-bg:` or `style.css` means the page received the generated bundle and the register is defeated — see Task 1 Step 8.

- [ ] **Step 7: Commit**

```bash
git add barbershop-grams/index.html
git commit -m "feat(barbershop): hub page shell, head, and schema"
```

---

## Task 5: The hub page — body copy

**Files:**
- Modify: `barbershop-grams/index.html`

**Load `writing-site-copy` and `anthropic-skills:stop-slop` before this task.** Draft copy for sections 3–6 is in spec §Page 1; it is a draft of the register to hit, and every line goes through both skills before it lands. The strings below are load-bearing and must be used verbatim: the eight FAQ answers must match the `FAQPage` text character for character, and the price figures must match `pricing.html` (Task 7).

- [ ] **Step 1: Replace everything between `<main>` and `</main>`**

Sections, in order. Use `bs-section`, `bs-section--light` / `bs-section--mid` alternating, `bs-rail` + `bs-rail-label` + `bs-body` for the inner grid — the same structures the register inherited from the private register.

1. **Hero** (`bs-hero bs-section`) — `<h1>A barbershop quartet at the door, singing Happy Birthday to someone who had no idea.</h1>`, one lede paragraph (spec §Page 1.1), then two CTAs: `<a class="bs-btn bs-btn--fill" href="[the WhatsApp URL from partials/barbershop-nav.html]">Send a gram</a>` and `<a class="bs-btn" href="/barbershop-grams/repertoire.html">See the repertoire</a>`.
2. **Occasion strip** — `<ul class="bs-occasions">` with six items linking to the anchors below. First `<li>` carries `class="bs-occasions__lead"`: Birthday (`#birthday`) · Valentine's (`#love`) · Proposal (`#proposals`) · Leaving do (`#office`) · Anniversary (`#love`) · Just because (`#love`).
3. **`id="birthday"`** — the flagship, the longest section on the page. Spec §Page 1.3.
4. **`id="love"`** — spec §Page 1.4. Name the three love songs from the repertoire; do not quote lyrics.
5. **`id="proposals"`** — spec §Page 1.5.
6. **`id="office"`** — spec §Page 1.6. This is where the eight-or-twelve-voices offer goes; a fixed quartet cannot make it.
7. **How it works** — `<ol>`, the four steps from spec §Page 1.7, verbatim.
8. **Making sure the surprise lands** — `<ul class="bs-check">`, the five items from spec §Page 1.8, verbatim.
9. **`id="prices"`** — the table in Step 2 below.
10. **Repertoire teaser** — six titles and a link to `repertoire.html`.
11. **`id="faq"`** — `<div class="bs-faq">` of eight `<details>`, each `<summary>` and `<p>` matching a `FAQPage` entry from Task 4 Step 5 exactly.
12. **`id="enquire"`** — WhatsApp button, `<a href="tel:+447356042468">07356 042468</a>`, and `<a href="/contact.html?occasion=barbershop-gram">the enquiry form</a>`.

- [ ] **Step 2: The price table**

```html
The `role` attributes are deliberate. At the `39.9375rem` breakpoint the register sets `display: block` on `tr`/`td` to stack the rows, which drops the native row and cell roles from the accessibility tree in Chrome, Safari, and Firefox. Explicit roles restore them, and `pricing.html` already uses `role="table"` on its own tables, so this matches the house pattern rather than inventing one.

```html
        <table class="bs-prices" role="table">
          <thead>
            <tr role="row"><th scope="col" role="columnheader">What you are sending</th><th scope="col" role="columnheader">Price</th></tr>
          </thead>
          <tbody>
            <tr role="row">
              <td role="cell"><strong>Surprise Barbershop Gram</strong><br>Up to ten minutes. Four singers find the person, sing Happy Birthday in four-part harmony, then one song from the repertoire chosen for them, with their name worked in.<span class="bs-prices__flag">Our flagship</span></td>
              <td role="cell">&pound;600</td>
            </tr>
            <tr role="row">
              <td role="cell"><strong>Half-hour set</strong><br>Three or four songs for one occasion, or a roaming set that reaches several people across an office or a party.</td>
              <td role="cell">From &pound;800</td>
            </tr>
            <tr role="row">
              <td role="cell"><strong>One-hour set</strong><br>A programme of eight to ten songs with a break. Drinks receptions, garden parties, company summer parties.</td>
              <td role="cell">From &pound;1,200</td>
            </tr>
            <tr role="row">
              <td role="cell"><strong>Bespoke arrangement</strong><br>Your song, arranged for four voices. Allow a week. Add it to any of the above.</td>
              <td role="cell">From &pound;200</td>
            </tr>
            <tr role="row">
              <td role="cell"><strong>Video recording session</strong><br>A filmed performance for someone who is not in London, or for a company video. We agree the licence with you for the use you have in mind.</td>
              <td role="cell">From &pound;1,000</td>
            </tr>
          </tbody>
        </table>
        <p>Every price is the whole price. We do not add VAT. Travel within Greater London is included; outside Greater London we quote travel in your written quote before you commit. Eight or twelve voices instead of four, quoted on request.</p>
```

The £600 is flat, not "from" — it is the matched figure and a "from" would not be a match (spec §Product).

- [ ] **Step 3: Verify the FAQ strings match the schema**

```bash
python3 - <<'EOF'
import json, re, html
c = open('barbershop-grams/index.html', encoding='utf-8').read()
blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', c, re.S)
doc = json.loads(blocks[0])
nodes = doc.get('@graph', [doc])
faq = next(n for n in nodes if n.get('@type') == 'FAQPage')
schema = [(q['name'], q['acceptedAnswer']['text']) for q in faq['mainEntity']]
vis = re.findall(r'<summary>(.*?)</summary>\s*<p>(.*?)</p>', c, re.S)
def norm(s):
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    for a, b in [('\u2019', "'"), ('\u2018', "'"), ('\u201c', '"'), ('\u201d', '"')]:
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()
assert len(schema) == len(vis) == 8, f"expected 8 each, got schema={len(schema)} visible={len(vis)}"
bad = [(q, norm(vq)) for (q, a), (vq, va) in zip(schema, vis)
       if norm(q) != norm(vq) or norm(a) != norm(va)]
print("MISMATCHES:", bad or "none")
EOF
```

Two things this check gets right that a naive version does not. It reads the `FAQPage` out of the `@graph` rather than assuming a top-level object, because Task 4 puts all three nodes in one graph. And it **normalises apostrophes before comparing**, because the house convention — verified across `pricing.html`, `weddings.html`, `funerals.html`, `contact.html` and `compare/london-funeral-singers.html` — is straight apostrophes inside JSON-LD and `&rsquo;` in visible copy. Keep the visible text typographic and the schema straight; Google requires the answers to match in substance, not in glyph encoding.

Expected: `MISMATCHES: none`. A visible answer that differs from its schema answer in *substance* is a rich-result risk.

- [ ] **Step 4: Confirm no house-claim or price drift**

```bash
python3 validate_house_claims.py && python3 validate_jsonld.py && echo CLEAN
grep -o '&pound;[0-9,]*' barbershop-grams/index.html | sort -u
```

Expected: `CLEAN`, and the figures are exactly `&pound;1,000 &pound;1,200 &pound;200 &pound;250 &pound;600 &pound;800`. Any other number is a drift from spec §Product.

- [ ] **Step 5: Commit**

```bash
git add barbershop-grams/index.html
git commit -m "feat(barbershop): hub page body copy, prices, and FAQ"
```

---

## Task 6: The repertoire page

**Files:**
- Create: `barbershop-grams/repertoire.html`

**Titles only, never lyrics.** The spec's list is a draft pending the Artistic Director's confirmation (spec §Page 2). Ship it with the groups as given; if the owner has struck titles by the time this runs, use their list.

- [ ] **Step 1: Clone the hub as the shell**

```bash
cp barbershop-grams/index.html barbershop-grams/repertoire.html
```

- [ ] **Step 2: Replace the head metadata**

```html
  <title>Barbershop Gram Repertoire | Songs for a Surprise Quartet</title>
  <meta name="description" content="The songs our barbershop quartet sings on a surprise gram in London: birthday numbers, love songs, barbershop standards, doo-wop, and Christmas.">
  <meta name="theme-color" content="#FBF7EF">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://londonchoralservice.com/barbershop-grams/repertoire.html">
  <link rel="alternate" hreflang="en-gb" href="https://londonchoralservice.com/barbershop-grams/repertoire.html">
  <link rel="alternate" hreflang="x-default" href="https://londonchoralservice.com/barbershop-grams/repertoire.html">
```

Update all `og:*` and `twitter:*` title/description/url fields to match, keeping `og:type` as `website` and the `og:image` unchanged.

- [ ] **Step 3: Verify the description length**

```bash
python3 -c "print(len('The songs our barbershop quartet sings on a surprise gram in London: birthday numbers, love songs, barbershop standards, doo-wop, and Christmas.'))"
```

Expected: `144` — inside 141–161.

- [ ] **Step 4: Replace the schema with `ItemList` + `BreadcrumbList`**

Delete the `Service` and `FAQPage` blocks. Keep a breadcrumb with a third level, and add an `ItemList` whose `itemListElement` entries are the song titles as plain strings in the order they appear on the page.

```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://londonchoralservice.com/" },
      { "@type": "ListItem", "position": 2, "name": "Barbershop Grams", "item": "https://londonchoralservice.com/barbershop-grams/" },
      { "@type": "ListItem", "position": 3, "name": "Repertoire", "item": "https://londonchoralservice.com/barbershop-grams/repertoire.html" }
    ]
  }
  </script>
```

- [ ] **Step 5: Write the body**

`<h1>What the quartet sings</h1>`, one short intro paragraph, then six `<section>`s — Birthday and celebration · Love songs · Barbershop classics · Doo-wop and later · Leaving dos · Christmas — each with `<ul class="bs-rep">` of the titles from spec §Page 2. Close with: "Not here? We arrange any song for four voices from £200." and a link back to `/barbershop-grams/#prices`.

- [ ] **Step 6: Verify**

```bash
python3 validate_jsonld.py && python3 validate_house_claims.py && echo CLEAN
grep -c 'lyrics' barbershop-grams/repertoire.html
```

Expected: `CLEAN` and `0`.

- [ ] **Step 7: Commit**

```bash
git add barbershop-grams/repertoire.html
git commit -m "feat(barbershop): published repertoire page"
```

---

## Task 7: The `pricing.html` section

`pricing.html` is the source of truth for every LCS price (CLAUDE.md). The five gram prices must exist here or they are unsourced everywhere else.

**Files:**
- Modify: `pricing.html` (insert after the "Christmas &amp; carol singers" section, which closes just before the `pull-quote` figure — find it with `grep -n 'Christmas &amp; carol singers' pricing.html`)

- [ ] **Step 1: Insert the new section**

```html
    <section class="section">
      <div class="prose">
        <h2>Barbershop Grams</h2>
        <p>A <a href="/barbershop-grams/">Barbershop Gram</a> is four singers sent to surprise one person: Happy Birthday in four-part harmony and one song chosen for them. It is priced as its own thing rather than off the table above, because a ten-minute surprise and a full service are not the same booking.</p>
        <table class="pricing-table" role="table">
          <thead class="sr-only">
            <tr>
              <th scope="col">Booking</th>
              <th scope="col">Details</th>
              <th scope="col">Price</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="pricing-name"><strong>Surprise Barbershop Gram</strong><span class="pricing-sub">up to 10 minutes</span></td>
              <td class="pricing-detail">Four singers find the person, sing Happy Birthday in four-part harmony, then one song from the <a href="/barbershop-grams/repertoire.html">repertoire</a> chosen for them, with their name worked in. Offices, homes, restaurants, and parks across Greater London. 48 hours&rsquo; notice.</td>
              <td class="pricing-price">&pound;600</td>
            </tr>
            <tr>
              <td class="pricing-name"><strong>Half-hour set</strong></td>
              <td class="pricing-detail">Three or four songs for one occasion, or a roaming set that reaches several people across an office or a party.</td>
              <td class="pricing-price">From &pound;800</td>
            </tr>
            <tr>
              <td class="pricing-name"><strong>One-hour set</strong></td>
              <td class="pricing-detail">A programme of eight to ten songs with a break. Drinks receptions, garden parties, company summer parties.</td>
              <td class="pricing-price">From &pound;1,200</td>
            </tr>
            <tr>
              <td class="pricing-name"><strong>Bespoke arrangement</strong></td>
              <td class="pricing-detail">Your song, arranged for four voices. Allow a week. Add it to any booking above.</td>
              <td class="pricing-price">From &pound;200</td>
            </tr>
            <tr>
              <td class="pricing-name"><strong>Video recording session</strong></td>
              <td class="pricing-detail">A filmed performance for someone who is not in London, or for a company video. We agree the licence with you for the use you have in mind.</td>
              <td class="pricing-price">From &pound;1,000</td>
            </tr>
          </tbody>
        </table>
        <p>Travel within Greater London is included. Eight or twelve voices instead of four, quoted on request.</p>
      </div>
    </section>
```

- [ ] **Step 2: Verify the figures agree with the hub page**

```bash
python3 - <<'EOF'
import re
def figs(p):
    body = open(p, encoding='utf-8').read().split('Barbershop Gram', 1)[1]
    return sorted(set(re.findall(r'&pound;([\d,]+)', body)))
print('pricing.html :', figs('pricing.html'))
print('hub          :', sorted(set(re.findall(r'&pound;([\d,]+)', open('barbershop-grams/index.html', encoding='utf-8').read()))))
EOF
```

Expected: the gram figures on both sides are `200, 600, 800, 1,000, 1,200` (the hub also shows `250`, from the "is there a cheaper version" answer, which is the soloist price already on `pricing.html`). Any disagreement breaks the CLAUDE.md rule that prices match `pricing.html`.

- [ ] **Step 3: Leave `pricing.html`'s JSON-LD alone**

Its `@graph` carries an `OfferCatalog` of eight `Offer` nodes covering the choirs and accompaniment tables. The five gram tiers are deliberately **not** added to it, for three reasons:

- Task 4 established that only the flat £600 carries an `Offer`, because a "from" price is not an offer. Adding four `minPrice` offers here would contradict a decision already made and reviewed.
- That £600 `Offer` already exists on `barbershop-grams/index.html`, which is the product's own page and the right home for it. Duplicating it here would leave two nodes competing to describe one price.
- The existing "Christmas &amp; carol singers" section is likewise a table with no `Offer` nodes, so a pricing section without them is the established pattern, not an omission.

Use relative links in the section's body copy (`barbershop-grams/`, not `/barbershop-grams/`) — every other in-content link on this page is relative, and the absolute form belongs only in the partials, which are injected at varying directory depths.

- [ ] **Step 4: Commit**

```bash
git add pricing.html llms-full.txt
git commit -m "feat(pricing): Barbershop Grams pricing section"
```

`llms-full.txt` is regenerated by `build.sh` from the built pages, so it changes alongside and is committed with it. Never hand-edit it.

---

## Task 8: Wire the enquiry pre-fill

`js/form.js` only pre-fills the occasion select when a matching `<option>` exists. The existing `compare/` page's `?occasion=quote-check` link has no option and silently does nothing; do not repeat that.

**Files:**
- Modify: `contact.html` (the select at `contact.html:2396`)

- [ ] **Step 1: Reproduce the existing bug, to know what fixed looks like**

```bash
python3 -m http.server 8000 &
sleep 1
```

Open `http://localhost:8000/contact.html?occasion=barbershop-gram`. The "Type of occasion" select shows "Please select" — no match, no pre-fill.

- [ ] **Step 2: Add the option**

Insert before `<option value="other">Other</option>`:

```html
                <option value="barbershop-gram">Barbershop Gram / surprise</option>
```

- [ ] **Step 3: Verify the pre-fill works**

Reload `http://localhost:8000/contact.html?occasion=barbershop-gram`. The select now shows "Barbershop Gram / surprise". Then stop the server:

```bash
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add contact.html
git commit -m "feat(contact): barbershop-gram occasion option for the enquiry pre-fill"
```

---

## Task 9: Link the mini-site from the main site

Inbound links only, and never from a funeral surface (spec §Linking). This task edits `partials/nav.html`, so **`./build.sh` is mandatory** and the diff will touch ~106 files.

**Files:**
- Modify: `partials/nav.html` (the Services dropdown, `partials/nav.html:11-20`)
- Modify: `services.html` (ensemble grid at `services.html:2520`, `OfferCatalog` at `services.html:2215`)
- Modify: `weddings.html`, `corporate.html` (one sentence each)

- [ ] **Step 1: Add the Services-dropdown entry**

In `partials/nav.html`, after the Private Events line and before the separator:

```html
            <li role="none"><a role="menuitem" href="/barbershop-grams/">Barbershop Grams</a></li>
```

Dropdown only. Not a top-level `<li>` — spec §Architecture: a birthday gram must not sit in the main nav above funeral content.

- [ ] **Step 2: Add the services.html card**

Inside `<ul class="ensemble-grid">`, following the existing `ensemble-card` pattern exactly:

```html
          <li>
            <article class="ensemble-card">
              <h3>Barbershop Grams</h3>
              <p>Four singers sent to surprise one person: Happy Birthday in four-part harmony and a song chosen for them, at a desk, a door, or a restaurant table. &pound;600 across Greater London, 48 hours&rsquo; notice. <a href="/barbershop-grams/">See how a gram works</a>.</p>
            </article>
          </li>
```

- [ ] **Step 3: Add the services.html catalogue entry**

In the `OfferCatalog` `itemListElement` array, following the existing `Offer`/`Service` shape:

```json
                {
                  "@type": "Offer",
                  "itemOffered": {
                    "@type": "Service",
                    "name": "Barbershop Gram",
                    "description": "Four singers sent to surprise one person with Happy Birthday in four-part harmony and a song chosen for them, anywhere in Greater London."
                  }
                },
```

- [ ] **Step 4: Add the two in-copy links**

These target the "barbershop quartet hire London" head term, which the competitor's own title tag targets and which the hub should also win.

In `weddings.html`, in a drinks-reception or after-ceremony paragraph:

> A barbershop quartet works well for the drinks reception, when guests are moving and the singing can move with them. See <a href="/barbershop-grams/">Barbershop Grams</a>.

In `corporate.html`, in a party or celebration paragraph:

> For one person&rsquo;s milestone rather than a whole event, we also send <a href="/barbershop-grams/">Barbershop Grams</a>: four singers, one surprise, ten minutes.

Run both sentences through `writing-site-copy` and `stop-slop` before committing; adapt the wording to the surrounding paragraph rather than dropping them in cold.

- [ ] **Step 5: Confirm no funeral surface was touched**

```bash
git diff --name-only | grep -E 'funeral|for-|private-events|destinations' || echo "NO_FUNERAL_OR_B2B_SURFACES"
```

Expected: `NO_FUNERAL_OR_B2B_SURFACES`.

- [ ] **Step 6: Build**

```bash
./build.sh
```

Expected: exits 0, ending with `House claims clean across N files checked.` The nav change re-expands into every page, so the diff is large by design.

- [ ] **Step 7: Check the diff shape**

```bash
git diff --stat | tail -3
git diff -- index.html | head -30
```

Expected: ~106 HTML files, and the `index.html` change confined to the nav marker region. Anything outside a marker region or a `<style>` block means stop and investigate (build-and-verify skill).

- [ ] **Step 8: Confirm the register pages did not get the site bundle**

```bash
for f in barbershop-grams/index.html barbershop-grams/repertoire.html; do
  echo "$f: style-blocks=$(grep -c '^  <style>$' $f) sitecss=$(grep -c 'style\.css' $f) bundle=$(grep -c 'color-bg:' $f)"
done
```

Expected for both: `style-blocks=1 sitecss=0 bundle=0`. A non-zero `sitecss` or `bundle` means Pass B inlined the whole site stylesheet onto a register page — revert and re-check Task 1 Step 8.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(barbershop): link grams from nav, services, weddings, and corporate"
```

---

## Task 10: Sitemap and llms.txt

**Files:**
- Modify: `sitemap.xml` (160 `<loc>` entries; core pages first, then areas, then guides)
- Modify: `llms.txt` (`## Main Pages`)

- [ ] **Step 1: Add both sitemap entries**

After the `private-events.html` entry (`sitemap.xml:82`), keeping the file's existing ordering:

```xml
  <url>
    <loc>https://londonchoralservice.com/barbershop-grams/</loc>
    <lastmod>2026-09-03</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://londonchoralservice.com/barbershop-grams/repertoire.html</loc>
    <lastmod>2026-09-03</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
```

Use the real date the task runs, not `2026-09-03`, if that is later.

- [ ] **Step 2: Add the llms.txt entries**

Under `## Main Pages`, following the existing `- [Name](url): description` format:

```
- [Barbershop Grams](https://londonchoralservice.com/barbershop-grams/): Four singers sent to surprise one person in London — Happy Birthday in four-part harmony and a song chosen for them. £600 for up to ten minutes, 48 hours' notice, travel within Greater London included
- [Barbershop Gram Repertoire](https://londonchoralservice.com/barbershop-grams/repertoire.html): The songs the quartet sings — birthday numbers, love songs, barbershop standards, doo-wop, leaving-do songs, and Christmas
```

- [ ] **Step 3: Verify the sitemap parses and the count rose by two**

```bash
python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('sitemap.xml'); print('parses')"
grep -c '<loc>' sitemap.xml
```

Expected: `parses`, then `162`.

- [ ] **Step 4: Rebuild so llms-full.txt picks up the new pages**

`scripts/generate_llms_full.py` walks `sitemap.xml`, so the new pages only enter `llms-full.txt` after the sitemap has them.

```bash
./build.sh
grep -c 'Barbershop Grams' llms-full.txt
```

Expected: non-zero. If it is `0`, the generator could not open the file — check the sitemap path resolves (`/barbershop-grams/` maps to `barbershop-grams/index.html`).

- [ ] **Step 5: Commit**

```bash
git add sitemap.xml llms.txt llms-full.txt
git commit -m "chore(barbershop): sitemap, llms.txt, and llms-full.txt entries"
```

---

## Task 11: Record the work and refresh the graph

**Files:**
- Modify: `docs/ROADMAP.md`
- Modify: `graphify-out/` (generated)

- [ ] **Step 1: Add the roadmap entry**

At the end of `docs/ROADMAP.md`, matching the style of the existing "Competitive capture" entry:

```markdown
## R14 — Barbershop Grams product line  [P1] [done 2026-09-03]

**What shipped:** a second product line at `/barbershop-grams/` (hub + repertoire page) in its own visual register, priced to match Barbershop-o-gram's £600 ten-minute gram on that tier only. New `pricing.html` section, Services-dropdown entry, `barbershop-gram` occasion option, and `barbershop-grams/*.html` added to both claim validators, which previously could not see the directory.

**Deliberately not done:** the comparison page and listen page (Phase 2, gated on a barbershop recording existing); per-occasion pages (Phase 3, gated on Search Console evidence); ads, directories, partnerships, and PR (Phase 4, human-only, `MANUAL-ACTIONS-REQUIRED.md`).

**Spec:** `docs/superpowers/specs/2026-09-03-barbershop-grams-design.md`
**Plan:** `docs/superpowers/plans/2026-09-03-barbershop-grams.md`

**Verify:**
```sh
./build.sh                                 # exits 0
python3 tests/test_competitor_claims.py    # 0 failure(s)
grep -c '<loc>' sitemap.xml                # 162
```
```

- [ ] **Step 2: Refresh the knowledge graph**

Two new pages plus nav changes is new-page work, so the graph must not be left stale (CLAUDE.md).

```
/graphify --update
```

- [ ] **Step 3: Commit**

```bash
git add docs/ROADMAP.md graphify-out/
git commit -m "docs(roadmap): record the Barbershop Grams launch; refresh graph"
```

---

## Task 12: Phase 1 verification

- [ ] **Step 1: Full build from clean**

```bash
./build.sh && git diff --stat
```

Expected: build exits 0, and the diff is **empty**. A second build with no source changes must leave a clean tree — that is the idempotency tripwire for the register partials (spec §Architecture).

- [ ] **Step 2: All validators and tests**

```bash
python3 validate_jsonld.py && python3 validate_competitor_claims.py && python3 validate_house_claims.py && python3 tests/test_competitor_claims.py
```

Expected: all pass. `validate_competitor_claims.py` still reports only `london-funeral-singers` at this point; the barbershop provider arrives in Task 13.

- [ ] **Step 3: Preview at both widths**

```bash
python3 -m http.server 8000
```

Check `http://localhost:8000/barbershop-grams/` and `/barbershop-grams/repertoire.html`:
- The gift register renders (warm paper ground, no cathedral typography, no site nav or footer).
- No raw `@include` marker text is visible on the page.
- The mini-site nav's four links work; the footer's single link to `/` works.
- The price table collapses to stacked rows at 375px.
- The FAQ `<details>` open and close.
- `http://localhost:8000/pricing.html` shows the new section, and `http://localhost:8000/services.html` shows the new card.

- [ ] **Step 4: Confirm the separation held**

```bash
grep -rn 'barbershop' --include='*.html' . | grep -E 'funerals\.html|music-guides/(funeral|best-funeral)|for-[a-z-]*\.html|private-events\.html|destinations/' || echo "SEPARATION_HELD"
```

Expected: `SEPARATION_HELD`.

**Stop here if the barbershop recording does not yet exist.** Report Phase 1 complete and name Phase 0.1 as the blocker for Tasks 13–15.

---

## Task 13: Competitor data and the enforcement test  *(Phase 2 — gated)*

**Gate:** a barbershop recording exists and its YouTube ID is in `data/seo-fix-discovered-urls.yml`.

**Files:**
- Modify: `data/competitor-pricing.yml`
- Modify: `tests/test_competitor_claims.py`

- [ ] **Step 1: Write the failing test first**

Add to `tests/test_competitor_claims.py`, before the `__main__` block. It runs against the **real** YAML, not the sandbox fixture, because the thing being protected is the real file's deliberate omission of their other tiers.

```python
def test_barbershopogram_unlisted_tier_fails():
    """Their non-entry tiers are deliberately absent from the YAML (owner's
    instruction: only the £600 gram is ever discussed). Printing one must fail."""
    real_yaml = open(os.path.join(ROOT, "data", "competitor-pricing.yml"), encoding="utf-8").read()
    code, out = run_in_sandbox(real_yaml, "<p>Their half-hour set is &pound;750.</p>")
    assert code == 1, f"unlisted competitor tier £750 must fail the build, got {code}: {out}"
    assert "750" in out, f"error should name the offending figure: {out}"

def test_barbershopogram_entry_price_passes():
    real_yaml = open(os.path.join(ROOT, "data", "competitor-pricing.yml"), encoding="utf-8").read()
    code, out = run_in_sandbox(real_yaml, "<p>Both quartets charge &pound;600.</p>")
    assert code == 0, f"the matched £600 figure must pass: {out}"
```

- [ ] **Step 2: Run the tests and watch the second one fail**

```bash
python3 tests/test_competitor_claims.py
```

Expected: `test_barbershopogram_unlisted_tier_fails` **passes** (£750 is not in the YAML yet, so it correctly fails the build) and `test_barbershopogram_entry_price_passes` **fails** — £600 is not declared yet either. That failure is the one Step 3c fixes.

- [ ] **Step 3: Teach the validator that not every provider quotes ex-VAT**

**Do this before Step 3c, not after.** `allowed_figures()` reads `pkg["price_ex_vat"]` unconditionally (`validate_competitor_claims.py:30`), so a package without that key raises `KeyError: 'price_ex_vat'` and takes the whole build down — not a rejected figure, a traceback. Verified: adding a `price_inc_vat`-only provider to the unpatched validator crashes it even on figures that should pass. Land the YAML entry first and `./build.sh` stops working.

Beyond the crash, the derivation is also wrong for this provider. The unconditional inc-VAT twin is right for the funeral singers, who print "+ VAT" against every figure. Barbershop-o-gram print a bare "£600" to consumers, and UK price-marking rules require consumer-facing prices to include VAT — so £600 is the buyer's cost and a derived £720 would describe nothing real.

Replace the package loop inside `allowed_figures()`:

```python
    for provider in cfg.get("providers", {}).values():
        for pkg in provider.get("packages", {}).values():
            if "price_ex_vat" in pkg:              # provider quotes excluding VAT
                ex = pkg["price_ex_vat"]
                allowed.add(ex)
                allowed.add(round(ex * (1 + vat)))  # what a family actually pays
            if "price_inc_vat" in pkg:             # already the buyer's cost
                allowed.add(pkg["price_inc_vat"])   # no twin: nothing to add
```

A mistyped key then allows no figure and fails the build loudly, which is the right failure direction. Funeral-singers behaviour is unchanged: every one of its packages uses `price_ex_vat`.

- [ ] **Step 3b: Prove the old behaviour is gone**

```bash
python3 - <<'EOF'
import subprocess, sys, tempfile, os, shutil
YAML = """vat_rate: 0.20
providers:
  incprov:
    name: "Inc Provider"
    pricing_url: "https://example.com/prices"
    checked_date: "2026-09-03"
    packages:
      gram:
        price_inc_vat: 600
        source_quote: "£600"
lcs_prices:
  gram: 600
"""
tmp = tempfile.mkdtemp()
os.makedirs(tmp + "/data"); os.makedirs(tmp + "/compare")
open(tmp + "/data/competitor-pricing.yml", "w").write(YAML)
open(tmp + "/compare/x.html", "w").write("<p>Their gram is &pound;720.</p>")
shutil.copy("validate_competitor_claims.py", tmp)
p = subprocess.run([sys.executable, "validate_competitor_claims.py"], cwd=tmp, capture_output=True, text=True)
print("exit:", p.returncode); print(p.stdout)
assert p.returncode == 1 and "720" in p.stdout, "£720 must NOT be derivable from an inc-VAT price"
print("PASS: no phantom inc-VAT twin")
shutil.rmtree(tmp)
EOF
```

Expected: `PASS: no phantom inc-VAT twin`. Run it before the edit too: it fails with `KeyError: 'price_ex_vat'`, which is the crash being fixed. Also confirm the funeral-singers behaviour is untouched — with the patch applied, `£275` and `£330` are still allowed and `£720` is still rejected.

- [ ] **Step 3c: Add the provider entry**

Append to the `providers:` map in `data/competitor-pricing.yml`, after `london-funeral-singers`:

```yaml
  barbershopogram:
    name: "Barbershop-o-gram"
    url: "https://www.barbershopogram.co.uk/"
    pricing_url: "https://www.barbershopogram.co.uk/prices"
    checked_date: "2026-09-03"
    vat_treatment: "consumer-inclusive; no VAT statement or VAT number anywhere on their site (checked 2026-09-03). £600 is what a buyer pays, so this comparison makes no VAT argument."
    travel: "All fees include music from our standard repertoire and include travel within London zone 5 unless otherwise stated."
    packages:
      ten_minute_gram:
        price_inc_vat: 600
        source_quote: "Up to 10 minutes (including Happy Birthdays) £600"
        includes: "All fees include music from our standard repertoire"
    # Their other published tiers (half-hour, one-hour, bespoke, audio and video
    # sessions, travel formula) are DELIBERATELY absent. The owner's instruction is
    # that only the £600 entry gram is ever discussed. Because the validator allows
    # only figures declared here, leaving them out makes the build reject any
    # compare/ page that prints one. tests/test_competitor_claims.py locks this in.
    # The full snapshot for the quarterly re-check is in the spec's appendix.
```

Then add to `lcs_prices`:

```yaml
  barbershop_gram: 600
```

- [ ] **Step 4: Run the tests again**

```bash
python3 tests/test_competitor_claims.py
```

Expected: `0 failure(s)`, with both new tests passing.

- [ ] **Step 5: Extend the quarterly re-check**

In `MANUAL-ACTIONS-REQUIRED.md` §11, note that the re-check now covers two providers: `londonfuneralsingers.co.uk/pricing` and `barbershopogram.co.uk/prices`, updating each `checked_date` and any affected page in the same commit.

- [ ] **Step 6: Commit**

```bash
git add data/competitor-pricing.yml tests/test_competitor_claims.py MANUAL-ACTIONS-REQUIRED.md
git commit -m "feat(compare): source Barbershop-o-gram's entry price; test that unlisted tiers fail"
```

---

## Task 14: The comparison page  *(Phase 2 — gated)*

**Files:**
- Create: `compare/barbershopogram.html`

Claim rules are binding: spec §Page 3 plus the seven rules in `docs/superpowers/specs/2026-08-18-competitive-capture-design.md` §3. Verbatim quotes only, no adjectives about them, nothing about their responsiveness or their other tiers.

- [ ] **Step 1: Clone the hub for the register**

```bash
cp barbershop-grams/index.html compare/barbershopogram.html
```

A reader arriving from a search for the competitor's name is a gift buyer, so they land in the gift register, not the site chrome.

- [ ] **Step 2: Replace the head metadata**

```html
  <title>Barbershop-o-gram vs London Choral Service: Prices</title>
  <meta name="description" content="Comparing barbershop quartet prices in London? Barbershop-o-gram's ten-minute gram and ours cost the same, &pound;600. Here is what each one includes.">
  <meta name="theme-color" content="#FBF7EF">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://londonchoralservice.com/compare/barbershopogram.html">
  <link rel="alternate" hreflang="en-gb" href="https://londonchoralservice.com/compare/barbershopogram.html">
  <link rel="alternate" hreflang="x-default" href="https://londonchoralservice.com/compare/barbershopogram.html">
  <meta property="article:published_time" content="2026-09-03">
  <meta property="article:modified_time" content="2026-09-03">
```

Update all `og:*`/`twitter:*` fields to match; set `og:type` to `article`.

- [ ] **Step 3: Verify the description length**

```bash
python3 -c "print(len(\"Comparing barbershop quartet prices in London? Barbershop-o-gram's ten-minute gram and ours cost the same, £600. Here is what each one includes.\"))"
```

Expected: `144`.

- [ ] **Step 4: Replace the schema with `Article` + `BreadcrumbList` + `FAQPage`**

No `Product`, `Offer`, or `AggregateOffer` containing the competitor's figure — offer markup would assert we sell at their price.

- [ ] **Step 5: Write the body — one number only**

Eight sections, per spec §Page 3:

1. Opening, two sentences. No hook.
2. The one-row table: their `"Up to 10 minutes (including Happy Birthdays)"` at `&pound;600`, quoted verbatim, against our Surprise Barbershop Gram at `&pound;600`. Directly beneath, in body text: *Price as published at barbershopogram.co.uk/prices, checked 3 September 2026.*
3. What £600 buys from us — the inclusions list from spec §Product. Facts, no adjectives.
4. How we work — 48 hours' notice; WhatsApp, usually the same day (hedge it: `services.html` says "within 48 hours, often the same day" and `contact.html` "usually the same day", and responsiveness is this product's central claim, so it is the worst place to over-promise); four voices as standard with eight or twelve by quotation; the published repertoire (link); the named Artistic Director. Each stated about us, none set against them.
5. Listen — the barbershop recording embedded.
6. Everything else we offer — **one sentence** linking to `/pricing.html`, with no figure.
7. Already got a quote? — link to `/contact.html?occasion=barbershop-gram`.
8. FAQ — four questions with matching `FAQPage` JSON-LD.

- [ ] **Step 6: Verify only £600 appears**

```bash
grep -o '&pound;[0-9,]*' compare/barbershopogram.html | sort -u
python3 validate_competitor_claims.py; echo "exit=$?"
```

Expected: `&pound;600` and nothing else, and `exit=0`. Any other figure either fails the validator or violates the one-number rule.

- [ ] **Step 7: Link it from the mini-site only**

Add a link from the hub's FAQ (an answer about comparing quotes) and from `partials/barbershop-footer.html`. **Not** from `partials/footer.html`, where it would sit beneath funeral content.

- [ ] **Step 8: Build and verify**

```bash
./build.sh && python3 tests/test_competitor_claims.py
```

Expected: build exits 0, ending with `Competitor claims valid across 2 compare/ page(s).`; tests report `0 failure(s)`.

- [ ] **Step 9: Commit**

```bash
git add compare/barbershopogram.html partials/barbershop-footer.html barbershop-grams/index.html
git commit -m "feat(compare): Barbershop-o-gram price comparison, entry gram only"
```

---

## Task 15: The barbershop listen page  *(Phase 2 — gated)*

**Files:**
- Create: `barbershop-grams/listen.html`
- Reference: `listen.html` (for the `VideoObject` pattern), `data/seo-fix-discovered-urls.yml` (for IDs, dates, durations)

- [ ] **Step 1: Clone the repertoire page for the register**

```bash
cp barbershop-grams/repertoire.html barbershop-grams/listen.html
```

- [ ] **Step 2: Head metadata**

```html
  <title>Hear a Barbershop Gram | Four-Part Harmony in London</title>
  <meta name="description" content="Recordings of our barbershop quartet: Happy Birthday in four-part harmony and the standards we sing on a surprise gram anywhere in Greater London.">
```

Verify: `python3 -c "print(len('...'))"` → must land in 141–161. Update canonical, hreflang, and all `og:`/`twitter:` fields.

- [ ] **Step 3: Embed the recordings with real `VideoObject` data**

Take `uploadDate` and `duration` from `data/seo-fix-discovered-urls.yml`. **Never invent them** (CLAUDE.md; ROADMAP R3). If the YAML has no entry for the new recording, stop and add it as an owner action rather than guessing.

- [ ] **Step 4: Wire it**

Mini-site nav link, sitemap entry with today's `lastmod`, `llms.txt` entry, and a link from the hub's hero proof slot.

- [ ] **Step 5: Build and verify**

```bash
./build.sh && python3 validate_jsonld.py
grep -c '<loc>' sitemap.xml
```

Expected: build exits 0; sitemap count is `163`.

- [ ] **Step 6: Commit**

```bash
git add barbershop-grams/listen.html barbershop-grams/index.html partials/barbershop-nav.html sitemap.xml llms.txt llms-full.txt
git commit -m "feat(barbershop): listen page with barbershop recordings"
```

---

## Self-review notes

**Spec coverage.** Every spec section maps to a task: §Product → 5, 7; §Architecture (directory, partials, register, tokens) → 1, 2; §Architecture (validators) → 3; §Architecture (linking) → 9, 14.7; §Page 1 → 4, 5; §Page 2 → 6; §Page 3 → 14; §Claims integrity → 13; §Go-to-market Phase 0 → owner actions, gate on Task 13; §Go-to-market search/ads/partnerships/directories/PR → `MANUAL-ACTIONS-REQUIRED.md`, outside this plan; §Measurement → the gram-specific WhatsApp pre-fill (Task 2) and the occasion option (Task 8); §Sequencing → task order and the Task 12 gate.

**Deliberately not in this plan.** The OG image (`og-barbershop-grams.png`) is an owner action; pages ship with `og-image.png` until it exists. GBP re-anchoring is `MANUAL-ACTIONS-REQUIRED.md` §16. Phase 3 occasion pages need Search Console evidence that does not exist yet, and inventing their content now would be building on speculation.

**Fixed in Task 13, not tolerated.** An earlier draft of this plan accepted that `allowed_figures()` would derive a phantom £720 from the declared £600, on the grounds that nothing would use it. Dry-running the change surfaced something worse: the function reads `pkg["price_ex_vat"]` unconditionally, so a `price_inc_vat`-only package raises `KeyError` and breaks `./build.sh` outright — the build stops working, it does not merely allow a wrong figure. Task 13 Step 3 fixes both, Step 3b is the regression test, and the funeral-singers figures (£275 allowed, £330 allowed, £720 rejected) were verified unchanged under the patch.
