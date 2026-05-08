# Music Guides Index Redesign

**Date:** 2026-05-06
**Page affected:** `/music-guides/` (`music-guides/index.html`)
**Site-wide change:** global nav (every `.html` file)

## Problem

The music-guides index has grown to 31 listed guides (33 files on disk; JSON-LD `ItemList` has only 28) in a single 42rem-wide column, ~2,600px tall. Three concrete problems:

1. **Overwhelming** — 31 dense entries in one scroll, every guide visually identical, no hierarchy.
2. **Irrelevant content visible** — a wedding client landing on the page sees a full block of funeral content above the fold (and vice versa). Emotionally jarring; commercially poor — visitors bounce instead of finding what they need.
3. **Hard to access specific sections quickly** — no filter, no jump-nav, no shortcut from elsewhere on the site. The "Music Guides" nav link goes to one place: the long list.

## Goals

1. A wedding client can land on the page (or arrive via the nav) and see only wedding content within one click.
2. The page reads as a curated, scannable browse experience rather than a dump of links.
3. Specific guides are reachable in two clicks from anywhere on the site (nav dropdown).
4. SEO behaviour is preserved or improved: every guide remains crawlable on a single canonical URL, structured data intact.
5. Visual language stays consistent with the rest of the site (Cormorant Garamond / Source Serif 4, parchment palette, prayer-book quietness).

## Non-goals

- Redesigning individual guide pages.
- Migrating the site to Jekyll, Eleventy, or any other framework.
- Changing the site's overall visual identity, typography, or colour palette.
- Server-side rendering of the filter (it stays a client-side toggle over a single URL).

---

## Design

### 1. Page architecture

Single-page layout at `/music-guides/`. All guides remain in the HTML; a JS-driven filter toggles category visibility. URL parameters drive the filter state, so links from elsewhere can land pre-filtered.

```
┌──────────────────────────────────────────────────────────┐
│  ← Home / Music Guides                                   │
│                                                          │
│  Music guides                                            │
│  Honest, practical advice…                               │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ START HERE                                         │  │
│  │ What to expect when you hire a choir            →  │  │  ← always visible
│  │ Everything you need to know about booking…         │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Browse by occasion                                      │
│  [ All ] [ Weddings ] [ Funerals ] [ Christmas ]         │  ← filter chips
│                                                          │
│  Wedding music                                           │
│  ─────────                                               │
│  ┌──────────┐  ┌──────────┐                              │
│  │ card     │  │ card     │                              │
│  └──────────┘  └──────────┘                              │
│  ┌──────────┐  ┌──────────┐                              │
│  │ card     │  │ card     │                              │
│  └──────────┘  └──────────┘                              │
│                                                          │
│  Funeral & memorial music                                │
│  ─────────                                               │
│  …                                                       │
│                                                          │
│  Christmas & corporate events                            │
│  ─────────                                               │
│  …                                                       │
└──────────────────────────────────────────────────────────┘
```

#### Filter behaviour

- **Chips:** `All · Weddings · Funerals · Christmas`. The "Christmas" label covers the existing "Christmas & corporate events" category — the heading on the page itself stays the longer form, but the filter chip is shortened for compactness.
- **Active state:** `aria-pressed="true"` on the active chip; visual treatment uses the accent colour fill.
- **Click behaviour:** clicking a chip:
  - Hides category sections that don't match (each section gets `hidden` attribute toggled).
  - Updates the URL via `history.pushState` (`?category=weddings`, etc.). `All` clears the param.
  - Updates `aria-pressed` on chips.
- **No-JS fallback:** chips are real `<a href="?category=…">` links. Without JS they perform a full-page navigation. The page reads URL params on load and applies the same filter — so the result is identical with or without JS.
- **Default state (no URL param):** "All" is active, every section visible.
- **Browser back/forward:** `popstate` listener re-reads the URL and re-applies the filter.

#### "Start here" feature card

The `/music-guides/hiring-a-choir.html` guide ("What to expect when you hire a choir") is currently the only entry in the vague "General" category. It is, in practice, an excellent overview for any visitor unsure where to start.

- It is promoted to a featured card pinned **above** the filter chips, **always visible** regardless of the active filter.
- It is removed from the category-grouped lists (so it doesn't appear twice).
- Visually distinct from the regular cards: small uppercase eyebrow text reading "START HERE", larger card, light accent border or fill.

#### Categories

Three top-level categories shown on the page (and in the dropdown):

1. **Wedding music**
2. **Funeral & memorial music**
3. **Christmas & corporate events**

The "General" category is dissolved. Its single member becomes the Start Here card.

#### File-vs-listing reconciliation

There are 33 guide HTML files on disk, 31 listed in the visible index, and only 28 in the JSON-LD `ItemList`. The redesign reconciles to a single source of truth: every guide file appears in both the visible index and the structured data.

**Missing from the visible index (2 files):**
- `lesser-known-wedding-choral-pieces.html` → Wedding music
- `wedding-pop-songs-choir.html` → Wedding music

**Missing from the JSON-LD `ItemList` (5 entries — the 2 above plus 3 already on the page):**
- `be-thou-my-vision-funeral-hymn.html`
- `be-thou-my-vision-wedding-hymn.html`
- `wedding-organ-pop-songs.html`
- `lesser-known-wedding-choral-pieces.html`
- `wedding-pop-songs-choir.html`

The implementation step inspects each missing-from-visible file's `<title>` / `<meta description>` to author appropriate card copy, then adds them to the index in the appropriate category and to the structured data.

### 2. Card grid layout

Replace the current single-column `<ul>` (42rem prose width) with a responsive 2-column grid in a wider container (60rem).

```
┌─────────────────────────────────────────────────┐
│ How to choose music for a funeral               │
│                                                 │
│ A practical, step-by-step guide to selecting    │
│ hymns, solo pieces, and instrumental music…     │
│                                                 │
│ Read guide  →                                   │
└─────────────────────────────────────────────────┘
```

**Card structure** (semantic):

```html
<li class="guide-card">
  <h3><a href="funeral-music-guide.html" class="guide-card__link">How to choose music for a funeral</a></h3>
  <p>A practical, step-by-step guide to selecting hymns, solo pieces, and instrumental music for a funeral service.</p>
  <span class="guide-card__cta" aria-hidden="true">Read guide →</span>
</li>
```

There is exactly one anchor per card (the H3 link). The visible "Read guide →" affordance is a non-interactive `<span>` (no second link, no extra tab stop, no double announcement to screen readers). The whole card is made clickable using a `::before` overlay on the H3 anchor that covers the entire card region:

```css
.guide-card { position: relative; }
.guide-card__link::before {
  content: "";
  position: absolute;
  inset: 0;
}
```

This is a well-established pattern: keyboard and screen-reader users get one link per card; pointer users can click anywhere on the card.

**Card visual treatment:**

- Subtle background (`var(--color-bg-alt)`) or a 1px border in `var(--color-rule)`.
- Generous padding: `var(--space-xl)`.
- On hover: the H3 link colour shifts to `var(--color-accent-hover)`; the card itself can subtly lift (e.g. background darkens by one tone).
- Card heading uses existing `--text-lg` (1.563rem) — slightly smaller than the current `--text-xl` H3 size, since cards are denser.

**Anchor / featured cards within a category:**

Each category has one or two "anchor" guides — the obvious starting point. They get a slightly enlarged or accented treatment so they're the first thing the eye lands on. Anchor guides per category:

- Weddings: *A complete guide to wedding ceremony music*
- Funerals: *How to choose music for a funeral*
- Christmas: *Planning a corporate carol service*

Anchor cards span the full grid width (or use a slightly different background) — they sit above the regular cards in their category section.

**Grid CSS:**

```css
.guide-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-lg);
}

@media (max-width: 599px) {
  .guide-grid {
    grid-template-columns: 1fr;
  }
}
```

**Container width:** the page wraps at 60rem (`--width-wide`) instead of 42rem (`--width-prose`). The lede stays narrow for readability — only the grid widens.

### 3. Nav dropdown

The "Music Guides" item in the global nav becomes a dropdown.

```
HOME  ABOUT  SERVICES  LISTEN  MUSIC GUIDES ▾  PRICING  CONTACT
                                  │
                                  ├─ Weddings
                                  ├─ Funerals
                                  ├─ Christmas
                                  ├─ ──────────
                                  └─ Browse all
```

**Desktop behaviour:**

- Opens on hover and on keyboard focus (`:hover`, `:focus-within`). CSS-only.
- Clicking "Music Guides" itself navigates to `/music-guides/` (the unfiltered index).
- Items link to the filtered URLs:
  - Weddings → `/music-guides/?category=weddings`
  - Funerals → `/music-guides/?category=funerals`
  - Christmas → `/music-guides/?category=christmas`
  - Browse all → `/music-guides/`

**Mobile (hamburger) behaviour:**

- "Music Guides" appears with a small chevron ("Music Guides ▾").
- Tapping it expands a sub-list inline within the hamburger panel.
- Tapping the chevron toggles the sub-list; the parent text remains tappable as a link to the index.
- A small JS addition to `js/nav.js` manages the sub-list state (`aria-expanded`).

**HTML pattern:**

```html
<li class="has-dropdown">
  <a href="/music-guides/" aria-haspopup="true" aria-expanded="false">Music Guides</a>
  <ul class="dropdown" role="menu">
    <li role="menuitem"><a href="/music-guides/?category=weddings">Weddings</a></li>
    <li role="menuitem"><a href="/music-guides/?category=funerals">Funerals</a></li>
    <li role="menuitem"><a href="/music-guides/?category=christmas">Christmas</a></li>
    <li role="separator"></li>
    <li role="menuitem"><a href="/music-guides/">Browse all</a></li>
  </ul>
</li>
```

**Accessibility:**

- ESC closes the dropdown and returns focus to the parent.
- Arrow keys (Up/Down) move between dropdown items when focus is inside.
- Tab moves out of the dropdown to the next nav item.
- `aria-expanded` updates on open/close.

### 4. Templating: extend `build.sh` with HTML partials

The site currently has no shared-HTML mechanism. Adding the dropdown means changing nav HTML in ~50 files; doing it again later is the same chore. We solve this once by extending `build.sh`.

**Approach:**

- Create a `partials/` directory with `nav.html` and `footer.html`.
  - These contain only the inner HTML for those regions (no `<!DOCTYPE>` etc.).
- In each `.html` page, replace the existing inline nav and footer markup with comment markers:

  ```html
  <!-- @include partials/nav.html -->
  <!-- @include partials/footer.html -->
  ```

- Extend `build.sh` to perform a pre-pass before the existing CSS-inlining pass: for every `.html` file, replace each `<!-- @include path -->` line with the contents of that file.
- The CSS-inlining pass continues to operate on the assembled output.

**Implementation in `build.sh`:**

The new pass iterates over every HTML file and runs an awk substitution that, for any line matching the include marker, reads and emits the contents of the named partial. Idempotent: running build.sh twice is safe (the marker is gone after first run, but we keep the source-of-truth pages with markers — see "Source vs build" below).

**Source vs build:**

There's a tension: if `build.sh` mutates the HTML files in place (replacing markers with content), then re-running it on already-built files would be a no-op for the includes pass — fine. But it means the source files no longer contain the `@include` marker; they contain the assembled nav. To change the nav, we'd have to revert manually.

Two options:

- **Option A (simpler):** keep markers in the source files, and `build.sh` writes assembled output to the same file. After the first build, the markers are gone. Editing the nav then means editing all 50 files again — no improvement.
- **Option B (correct):** introduce a `src/` vs deployed-root convention, or use a "between markers" approach where the build replaces only the section between `<!-- @include-start path -->` and `<!-- @include-end -->`, leaving the markers intact.

We adopt **Option B**, with paired markers:

```html
<!-- @include-start partials/nav.html -->
…content from partials/nav.html lives here after build…
<!-- @include-end partials/nav.html -->
```

`build.sh` finds each pair and replaces everything between the markers with the partial's current contents. The markers stay in place. Running `build.sh` repeatedly produces stable output.

**Workflow:**

1. Edit `partials/nav.html`.
2. Run `./build.sh`.
3. All 50 HTML files have their nav block updated.
4. Commit; push; GitHub Pages serves the assembled output.

**Why not Jekyll:** Jekyll is the "right" GH Pages answer in the abstract, but it requires restructuring every page (frontmatter, layouts) and learning Liquid. Extending `build.sh` solves the one problem we have (sharing nav/footer) with ~50 lines of bash. If the site outgrows this in future, Jekyll is a clean migration target.

### 5. CSS organisation

The redesigned index page introduces new components (filter chips, guide cards, "start here" feature card) and a new nav pattern (dropdown). New CSS goes into the existing modular files:

- `css/components.css` — filter chips, guide cards, feature card, nav dropdown
- `css/layout.css` — guide grid, nav adjustments

The build pipeline already concatenates these into `style.css` and inlines them into pages. No structural change to the CSS toolchain.

### 6. JavaScript

Two scripts touch the new behaviour:

**`js/nav.js`** (existing; extend):
- Adds support for the mobile dropdown: expanding/collapsing the "Music Guides" sub-list within the hamburger panel.
- Manages `aria-expanded` on the dropdown trigger.
- ESC closes the open dropdown.

**`js/music-guides.js`** (new; loaded only on the index page):
- Reads `?category=` from the URL on load and applies the filter.
- Wires up filter chip clicks: prevent default, hide non-matching category sections, push state, update aria attributes.
- `popstate` listener reapplies the filter on browser back/forward.
- All progressive-enhancement: the chips work as plain links if the script fails to load.

### 7. Internal-link updates

After the index supports `?category=…`, update the "Browse all guides" links on `weddings.html` and `funerals.html` to point to the filtered view:

- `weddings.html`: link to `/music-guides/?category=weddings`
- `funerals.html`: link to `/music-guides/?category=funerals`
- `christmas.html`: link to `/music-guides/?category=christmas` (verify file exists; otherwise skip)

Existing direct links to specific guides (e.g. `/music-guides/wedding-music-costs.html`) stay as-is.

### 8. SEO and structured data

- The page stays at `/music-guides/` (single canonical URL). All guides remain on this page; the filter is purely visual.
- `BreadcrumbList` JSON-LD unchanged.
- `ItemList` JSON-LD updated to include all 33 guides (currently 28). Position numbering is updated accordingly.
- `<link rel="canonical">` unchanged.
- The `?category=` parameter is purely client-side; we don't need separate canonicals for filtered states.

---

## Implementation order

The work breaks into independent stages that can be tested incrementally:

1. **Partials infrastructure**
   - Add include-pass logic to `build.sh` (with paired `@include-start` / `@include-end` markers).
   - Create `partials/nav.html` and `partials/footer.html` from one existing page.
   - Replace nav and footer in every `.html` file with the include markers.
   - Run `./build.sh`. Verify every page still renders correctly (preview tools).
   - Commit.

2. **Music-guides index redesign**
   - Update `music-guides/index.html`: add Start Here card, filter chips, restructure guide listings into category sections with the new card grid markup.
   - Reconcile the file-vs-listing gap: add the missing guides to both the visible index and the JSON-LD.
   - Add new component CSS to `css/components.css` and `css/layout.css`.
   - Add `js/music-guides.js` with the filter logic.
   - Run `./build.sh`. Verify the page looks right at desktop, tablet, mobile widths; verify `?category=…` deep-linking works; verify no-JS fallback works.
   - Commit.

3. **Nav dropdown**
   - Update `partials/nav.html` to add the dropdown structure.
   - Add dropdown CSS to `css/components.css`.
   - Extend `js/nav.js` for the mobile sub-list behaviour.
   - Run `./build.sh`. Verify dropdown works on every page (desktop hover, keyboard focus, mobile hamburger).
   - Commit.

4. **Internal-link updates**
   - Update "Browse all guides" links on `weddings.html` and `funerals.html` to filtered URLs.
   - Run `./build.sh`. Verify clicking through lands on the correctly-filtered index.
   - Commit.

Each stage commits a working site. If a later stage stalls, the earlier improvements still ship.

## Open questions / risks

- **Anchor-card visual:** the "anchor guide" treatment (slightly larger first card per category) is sketched but not finalised. The frontend-design skill will iterate on this during implementation.
- **JS bundle size:** `js/music-guides.js` is loaded only on the index page, so no impact on other pages. Total expected: ~50 lines, gzipped trivial.
- **Mobile dropdown UX:** native iOS/Android sometimes behaves unexpectedly with hover-revealed menus. The mobile path uses tap-to-expand explicitly to avoid this — implementation needs to verify on a real device.
- **Christmas chip label:** "Christmas" in the chip might confuse if a corporate-event visitor doesn't realise it includes corporate carol services. The on-page section heading stays as "Christmas & corporate events", which gives full context once filtered.

---

## Appendix: file inventory

Guides on disk (33 files), grouped by intended category:

**Funeral & memorial (12):**
- abide-with-me.html
- be-thou-my-vision-funeral-hymn.html
- catholic-funeral-hymns.html
- celebration-of-life-music.html
- crematorium-music.html
- funeral-choir-guide.html
- funeral-music-costs.html
- funeral-music-guide.html ⭐ anchor
- funeral-songs.html
- memorial-service-planning.html
- non-religious-funeral-music.html
- popular-funeral-hymns.html

**Wedding (15):**
- be-thou-my-vision-wedding-hymn.html
- choosing-wedding-hymns.html
- jerusalem.html
- lesser-known-wedding-choral-pieces.html *(new to listing)*
- popular-wedding-organ-music.html
- wedding-ceremony-music.html ⭐ anchor
- wedding-choir-guide.html
- wedding-choral-repertoire.html
- wedding-music-costs.html
- wedding-music-ideas.html
- wedding-organ-pop-songs.html
- wedding-organ-repertoire.html
- wedding-organist-guide.html
- wedding-pop-songs-choir.html *(new to listing)*
- wedding-readings-and-music.html

**Christmas & corporate events (5):**
- christmas-carols-guide.html
- christmas-choir-hire.html
- company-christmas-party-entertainment.html
- corporate-carol-service.html ⭐ anchor
- office-carol-service-planning.html

**Start Here (1):**
- hiring-a-choir.html
