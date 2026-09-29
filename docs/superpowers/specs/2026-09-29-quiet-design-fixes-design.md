# Quiet design fixes: header alignment and video heroes

**Date:** 2026-09-29
**Status:** Approved for implementation. The owner chose direction A (quiet fixes) with a bare play button, approved the header section, then asked for the work to run to completion without further check-ins.

## Problem

Measured at 1440×900 on the local build:

1. **The site name and the menu are not on one baseline.** `.site-nav` centres its children as boxes. The site name is 25px Cormorant in a 40px line box; the menu links are 14px in a 22.4px line box. Centring the boxes puts the name's baseline at 52px and the menu's at 45.6px, a 6.4px step. Horizontally the header is already right: the name lines up with the hero h1 (160.5px) and the menu's right edge with the film's (1264.5px).
2. **The hero film sits above the heading.** On pages with a breadcrumb the breadcrumb is inside `.hero-text`, so the film's top edge lines up with the breadcrumb (190px) rather than the h1 (244px), 54px high.
3. **The play button covers the film's own title.** Every thumbnail uses a YouTube-style black pill in the centre. The promo film `Lov_NegzVhM` has its title burned into the middle of the frame, so the pill reads "THE LONDON C▶ORAL SERVICE".
4. **Twelve heroes show the same film,** `Lov_NegzVhM`, with no caption saying what it is.
5. **Phones never see the film on the first screen.** Below 806px the film follows the whole text column. On funerals.html at 375×812 it starts 1,061px down.
6. **The footer's site name wraps** onto two lines at 1440px ("The London Choral / Service") because it is set at `--text-xl` in a narrow brand column.

## Direction

Three directions were mocked up in the brainstorm:

- **A. Quiet fixes** (chosen). Alignment, a quieter play control, the right film per page with a caption, the film first on phones. No new visual language.
- **B. Order of service.** A plus a typographic motif from printed service sheets: rubric red for notes, a versal on the lede, programme lines with dot leaders. Kept in the idea bank below.
- **C. Film first.** Centred heading, a wide letterboxed film, text below. Rejected: pushes the lede and the enquiry button below the fold on desktop, and the YouTube thumbnails (1280px) are soft at that width.

A full-bleed dark "concert poster" hero was also considered and dropped for the same thumbnail-resolution reason, and because the promo film's burned-in title would fight the h1.

Constraint from the owner: **YouTube uploads only.** No self-hosted loops or stills.

## Design

### 1. Header (partials/nav.html, css/layout.css, css/components.css)

- **Shared baseline.** `.site-nav { align-items: baseline; }`. Baseline alignment alone grows the header from 89px to 94px, because each menu item's 8px bottom margin then hangs below the baseline; `.nav-links li { margin-bottom: 0 }` removes it and the header stays at 89px with no padding change. Below 1081px the menu is absolutely positioned, so the mobile block sets `.site-nav { align-items: center; }` to keep the hamburger centred on the name.
- **Narrow desktop.** The chevrons are wider than the old glyph, which pushed the menu into the page gutter just above the breakpoint. From 1081 to 1119px the menu gap tightens to 0.8rem; from 1120px the default gap fits (measured with a 15px classic scrollbar).
- **Hairline chevrons.** The `&#9662;` glyph inside `.dropdown-caret` is removed from the partial; the caret becomes an empty span drawn as a 1px chevron in CSS (two borders, rotated 45°), in `currentColor`, so it turns oxblood on hover with its word. The open state rotates it to point up, replacing today's 180° flip. Reduced motion: no transition.
- **Lighter current-page mark.** `.nav-links a[aria-current="page"]` loses its 2px `border-bottom` (which ran under the word and the caret) and gains a 1px oxblood underline under the word only: `text-decoration-line: underline; text-decoration-thickness: 1px; text-decoration-color: var(--color-accent); text-underline-offset: 0.45em`. The caret is an inline-block, so the underline does not reach it. The mobile menu keeps its row rules; the underline also reads there.
- **Dropdown alignment.** Dropdown items are padded `--space-lg` inside a 1px border, so their text starts about 25px right of the trigger's first letter. The desktop `.dropdown-menu` moves left by `calc(var(--space-lg) + 1px)` so item text starts under the trigger text. The mobile (static) menu is unchanged.

### 2. Video heroes (css/components.css, the 15 hero pages)

The 15 pages with `class="page-wrap hero"`: index, weddings, funerals, christmas, carol-singers, christmas-pricing, corporate, pricing, and the seven `for-*.html` pages.

**Layout.** `.hero` changes from flex to a grid so the breadcrumb can span both columns and the film can move between the heading and the lede on phones:

```
desktop (≥806px)                     phone (≤805px)
┌──────────── crumb ────────────┐    crumb
│ head (h1)      │              │    head (h1)
├────────────────┤    video     │    video
│ body           │   (sticky)   │    body
│ (lede, CTAs)   │              │
└────────────────┴──────────────┘
columns minmax(0,2fr) minmax(0,3fr), column gap --space-3xl
rows auto auto 1fr
```

Markup: in each hero, the `nav.breadcrumb` and the `h1` move out of `.hero-text` to become direct children of `.hero`, followed by `.hero-video` and then `.hero-text`. Everything else in `.hero-text` stays in order. Putting the film before the text in the source makes the reading and tab order (heading, film, text) match the phone layout. Grid areas are assigned by selector (`.hero > .breadcrumb`, `.hero > h1`, `.hero-text`, `.hero-video`), so no new classes are needed. index.html has no breadcrumb; its crumb row collapses.

- **Film aligned to the heading.** The film's top edge lines up with the top of the h1's capitals, not the h1's line box. The offset is one `margin-top` on `.hero-video`, written as `calc(var(--text-display) * k)` with `k` measured from Cormorant Garamond's cap height and the h1's line height, so it follows the h1 across the responsive type scale. Verified to within 2px at 1440 and 1024px.
- **Sticky film kept** on desktop (`position: sticky; top: var(--space-2xl)`); static on phones.
- **Phones:** order is crumb, h1, film, then the rest. On funerals.html at 375×812 the film starts at about 400px and ends above the 57px `.mobile-cta` bar.
- **`.video-embed`** uses `aspect-ratio: 16 / 9` instead of the padding-bottom hack (no visual change; applies site-wide).

**Play button (site-wide, every `.video-thumb` on the main site).** The YouTube pill SVG (72 identical instances in 52 pages) is replaced with a plain circle and triangle:

```html
<svg class="play-btn" viewBox="0 0 56 56" aria-hidden="true"><circle cx="28" cy="28" r="27"/><path d="M23 19v18l15-9z"/></svg>
```

- Placed in the **bottom-left corner**, clear of any burned-in title: `left` and `bottom` `--space-md` (`--space-sm` below 600px).
- 56px (48px below 600px, still a comfortable target inside a full-width button).
- At rest: circle filled `rgba(28, 22, 20, .45)` with a 1.5px `--color-bg` ring; triangle `--color-bg`.
- Hover and keyboard focus: circle and ring fill `--color-accent` (150ms; none under reduced motion). The existing inset focus ring on `.video-thumb:focus-visible` stays.
- No visible text. The button's `aria-label` carries the name, as today.
- Out of scope: the private register (private-events.html, planners-and-venues.html, destinations/) has its own stylesheet and player markup (`partials/private-register.css.html`, `js/private-events.js`) and does not load the main CSS. It keeps its current player.

**Caption.** Each hero film gets a one-line caption under it, `<p class="video-caption">`, set in `--text-sm` italic, `--color-text-mid`, `margin-top: var(--space-sm)`:

| Film | Caption |
|---|---|
| `Lov_NegzVhM` (promo) | A 43-second film of our singers |
| `G9-R6k5n7Io` | Abide With Me, sung by our full choir |
| `-GQaQEGhYEs` | Ubi Caritas by Ola Gjeilo, sung by a quintet |
| `dGYqQf6BDAk` | Carol of the Bells, sung by our full choir |

Running times are stated only where `data/seo-fix-discovered-urls.yml` holds a verified duration (the promo's PT43S); Carol of the Bells has none, so no caption gives a time.

**The right film per page.** Pages whose body already has a "Hear our musicians" list (funerals, weddings, christmas, carol-singers) keep their current hero film, so the hero does not repeat a track below it. Two B2B pages with no other film change:

| Page | Hero film today | New hero film |
|---|---|---|
| for-funeral-directors.html | `Lov_NegzVhM` | `G9-R6k5n7Io` (Abide With Me) |
| for-wedding-planners.html | `Lov_NegzVhM` | `-GQaQEGhYEs` (Ubi Caritas) |

Each swap updates `data-video`, the thumbnail `src` (maxresdefault, which exists for all eight films: HTTP 206 checked 29 Sep 2026), `alt` in the site's existing form ("Abide With Me — The London Choral Service"), and `aria-label` ("Play Abide With Me"). Neither page carries `VideoObject` schema, so no JSON-LD changes.

### 3. Small polish

- **Footer site name** drops from `--text-xl` to `--text-lg`, the header's size, so it sits on one line in the brand column at 1440px and matches the header.

## Idea bank (not in this pass)

Ideas from the brainstorm for later passes, each small and independent:

**Typography and detail**
- Rubric red (direction B): use the oxblood only for short practical notes ("Text us on WhatsApp for the fastest reply"), the way service books print instructions in red.
- A versal (drop capital) in oxblood on the lede of the four occasion pages.
- Programme lines for repertoire lists in the music guides: title left, composer right in italic, dot leaders between.
- Link underlines at 1px with a 0.2em offset, rule-coloured, turning oxblood on hover.
- Oldstyle figures (`font-variant-numeric: oldstyle-nums`) in running prose, lining figures kept in price grids. Needs a check that the subsetted Source Serif 4 file keeps the `onum` feature.
- `text-wrap: pretty` on paragraphs to avoid one-word last lines.
- Hanging punctuation on pull quotes so the text, not the opening quote mark, aligns with the column.
- An oxblood-tinted `::selection`.

**Layout**
- One left edge down the page: after the hero (left edge 160px at 1440) the prose column is centred (left edge 401px). Aligning the prose to the hero's left edge would give the page a single axis, with the right-hand space free for short margin notes or pull quotes.
- Rules between sections only at real changes of subject; today every section has a full-width rule and 96px padding, which makes long pages read as a stack of equal boxes.
- The short red rule at the foot of the home hero text sits alone once the film is sticky; drop it or align it with the film's lower edge.

**Navigation**
- Contact as a quiet outlined button at the end of the menu, so the main action is always visible.
- Christmas as a top-level item from September to December only (it is also under Services). Business call for the owner.
- A fuller mobile menu: services listed directly rather than behind a tap, phone and WhatsApp at the foot.

**Film and listening**
- Remove the duplicate Carol of the Bells player on christmas.html and carol-singers.html (hero and "Hear our musicians" both play `dGYqQf6BDAk`).
- A "Hear more" link under each hero caption to listen.html.
- A second film per B2B page (for-hotels and for-livery-companies could carry Carol of the Bells from September to December).

## Verification

- `./build.sh` exits 0; `python3 tests/test_stage_site.py`, `.venv/bin/python tests/test_register_generators.py` and `.venv/bin/python tests/test_competitor_claims.py` pass.
- Header at 1440, 1200 and 1100px on index, weddings and a music guide: name and first menu link baselines equal within 0.5px; header height 89px ±1px. Below 1081px the hamburger is vertically centred against the name.
- Hero on all 15 pages at 1440 and 1024px: film top within 2px of the h1 cap top; breadcrumb above both columns; no horizontal scroll.
- Phone (375×812) on funerals, weddings and index: order crumb, h1, film, lede; the film's bottom edge above 755px (812 − the 57px CTA bar).
- `grep -rl 'M66.52' --include='*.html' .` returns no files (the private register builds its player in `js/private-events.js`, which is unchanged).
- Keyboard: Tab to a film shows the inset focus ring and the oxblood circle; Enter plays the film.
- `prefers-reduced-motion: reduce`: no caret or play-button transitions.
- Live check after merge: `python3 scripts/check_live_site.py`.
