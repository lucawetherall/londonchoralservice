# Nav: Services dropdown + cramping fix

**Date:** 2026-05-09
**Status:** Approved for implementation

## Problem

The global nav has three issues that compound each other:

1. **Cramping in the 768–1100px viewport range.** The bar fits seven items (Home / About / Services / Listen / Music Guides ▾ / Pricing / Contact) plus the logo, and at narrower desktop widths it runs out of horizontal room.
2. **"Music Guides" can wrap onto two lines.** The label has no `white-space: nowrap`, so under flex-shrink pressure the two words can break, producing a visibly broken nav.
3. **The four occasion pages aren't in the global nav.** `weddings.html`, `funerals.html`, `corporate.html`, and `christmas.html` are commercial conversion pages but are reachable only via `services.html` and the homepage. This is a discoverability cost and means those pages don't benefit from the internal-link-equity distribution that top-nav links provide on every page.

These can't be solved independently. Fixing the cramping alone leaves the four pages buried; surfacing the four pages as new top-level items makes the cramping worse; surfacing them under a "Services" dropdown adds caret weight to the bar that has to be compensated for.

## Goals

- Top nav must never wrap to two lines at any viewport width.
- "Music Guides" must never break across two lines internally.
- The bar must never overflow horizontally at any width above the mobile breakpoint.
- The four occasion pages must be one click from any page on the site.
- Net cramping at the historical pain point (~800–1024px) must be **better** than today, not just no-worse.

## Non-goals

- Redesigning `services.html` itself. That hub page does need work (it's currently a thin "list of links" page that loses most of its job once the four occasion pages are surfaced in the nav), but that's a separate, larger project. This spec ships independently.
- Bumping the mobile breakpoint to a tablet-typical width (e.g., 1024px). A small bump (≤60px) is permitted as a mitigation if testing reveals overflow at the narrow end of desktop — see the Risks and Mitigations section. The rejected alternative was a *large* bump that would force every laptop user through the hamburger.
- Changing the Music Guides dropdown contents.
- Changing the hamburger UX itself (its appearance, animation, or behaviour).

## Approach

**Option A from the brainstorm: drop "Home" from the nav, add a "Services" dropdown, and apply CSS safety rules so the bar never wraps.**

Removing "Home" is justified because the logo "The London Choral Service" already links to `/`, making a separate "Home" link conventionally redundant. This frees a slot, which absorbs the new "Services ▾" caret without adding a net new top-level item — so the bar comes out of the change with **fewer** items than today (6 vs 7), giving real breathing room.

Two alternatives were considered and rejected:
- **Raise the mobile breakpoint to 1024px.** Eliminates the cramped zone but forces every laptop visitor between 768–1024px through the hamburger for every nav action. Meaningful UX regression for laptop viewports.
- **Tighten only, keep all 7 items.** Adds the Services dropdown without dropping Home. Smallest change but the bar would still feel busy with two carets competing for space.

## Final nav structure

```
[Logo: The London Choral Service]    About · Services ▾ · Listen · Music Guides ▾ · Pricing · Contact
```

Services dropdown contents (mirrors the Music Guides pattern):

```
Services ▾
  Weddings     → /weddings.html
  Funerals     → /funerals.html
  Corporate    → /corporate.html
  Christmas    → /christmas.html
  ──────────
  All services → /services.html
```

The trigger word "Services" itself links to `/services.html` (matches how "Music Guides" trigger links to `/music-guides/`). This means non-JS clients, middle-clicks, and right-click → "open in new tab" all work as expected. "All services" at the bottom of the dropdown gives an explicit JS-friendly path to the same page from within the menu.

The duplication of three labels across both dropdowns (Weddings / Funerals / Christmas appearing under both Services and Music Guides) is accepted. The intents are distinct and contextually clear: *Services > Weddings* = "I want to book a wedding choir" (commercial); *Music Guides > Weddings* = "I want to read about wedding music" (informational). This is a known and acceptable agency-site pattern.

## Files changed

### `partials/nav.html`

Replace the entire file with the final structure below. The two changes are: (a) the `<li><a href="/">Home</a></li>` is removed; (b) a new `<li class="has-dropdown">` for Services is inserted after the About item, structured identically to the existing Music Guides dropdown.

```html
  <header class="site-header">
    <nav class="site-nav page-wrap" aria-label="Main navigation">
      <a href="/" class="site-name">The London Choral Service</a>
      <button class="nav-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Menu">
        <span class="nav-toggle-bar"></span>
      </button>
      <ul id="nav-menu" class="nav-links" role="list">
        <li><a href="/about.html">About</a></li>
        <li class="has-dropdown">
          <a href="/services.html" aria-haspopup="true" aria-expanded="false" class="dropdown-trigger">Services<span class="dropdown-caret" aria-hidden="true">&#9662;</span></a>
          <ul class="dropdown-menu" role="menu">
            <li role="none"><a role="menuitem" href="/weddings.html">Weddings</a></li>
            <li role="none"><a role="menuitem" href="/funerals.html">Funerals</a></li>
            <li role="none"><a role="menuitem" href="/corporate.html">Corporate</a></li>
            <li role="none"><a role="menuitem" href="/christmas.html">Christmas</a></li>
            <li role="separator" class="dropdown-separator"></li>
            <li role="none"><a role="menuitem" href="/services.html">All services</a></li>
          </ul>
        </li>
        <li><a href="/listen.html">Listen</a></li>
        <li class="has-dropdown">
          <a href="/music-guides/" aria-haspopup="true" aria-expanded="false" class="dropdown-trigger">Music Guides<span class="dropdown-caret" aria-hidden="true">&#9662;</span></a>
          <ul class="dropdown-menu" role="menu">
            <li role="none"><a role="menuitem" href="/music-guides/?category=weddings">Weddings</a></li>
            <li role="none"><a role="menuitem" href="/music-guides/?category=funerals">Funerals</a></li>
            <li role="none"><a role="menuitem" href="/music-guides/?category=christmas">Christmas</a></li>
            <li role="separator" class="dropdown-separator"></li>
            <li role="none"><a role="menuitem" href="/music-guides/">Browse all</a></li>
          </ul>
        </li>
        <li><a href="/pricing.html">Pricing</a></li>
        <li><a href="/contact.html">Contact</a></li>
      </ul>
    </nav>
  </header>
```

### `css/layout.css`

In the existing `.nav-links` rule (around line 84):

- Add `flex-wrap: nowrap`. Guards against any future change that might allow wrapping.
- Change `gap: var(--space-xl)` to `gap: clamp(0.75rem, 1.6vw, var(--space-xl))`. Resolves to ~12px at 768px viewport, ~16px at 1024px, ~23px at 1440px, capped at 32px at viewports ≥ 2000px.

In the existing `.nav-links a` rule (around line 92):

- Add `white-space: nowrap`. The load-bearing rule for the "Music Guides" requirement — individual nav labels can no longer break across lines under any flex-shrink pressure.

No font-size, letter-spacing, or padding changes. No changes to dropdown CSS in `components.css` (the existing `.has-dropdown` rules already work for any number of dropdowns). No changes to mobile media queries unless mitigation is needed (see Risks and Mitigations).

### `js/nav.js`

Add a follow-up pass to the existing `setAriaCurrent` IIFE. The current logic only highlights nav links whose href matches the current path (or is a path-prefix of it). For the new Services dropdown, the children live at root level (`/weddings.html`, etc.) rather than under `/services/`, so the prefix-match logic won't catch "user is on a Services child page → highlight the Services trigger".

Add this generalised pass after the existing `navLinks.forEach`, **inside the same IIFE** so `here` remains in scope:

```js
document.querySelectorAll('.has-dropdown').forEach(function (item) {
  var trigger = item.querySelector('.dropdown-trigger');
  if (!trigger || trigger.getAttribute('aria-current') === 'page') return;
  var children = item.querySelectorAll('.dropdown-menu a');
  for (var i = 0; i < children.length; i++) {
    var raw = children[i].getAttribute('href');
    if (!raw || raw.indexOf('://') !== -1) continue;
    var clean = raw.split('?')[0].replace(/\/index\.html$/, '/');
    if (clean === here) {
      trigger.setAttribute('aria-current', 'page');
      break;
    }
  }
});
```

This generalises cleanly: any dropdown whose children include the current page lights up its trigger. The early-return on existing `aria-current` ensures we don't double-process the Music Guides case (which is already covered by the path-prefix logic above).

Behaviour by page:
- `/services.html` → existing logic sets aria-current on Services trigger directly (linkPath===here). New pass early-returns. ✓
- `/weddings.html` → existing logic finds no match. New pass iterates Services children, finds `/weddings.html`, sets aria-current on Services trigger. ✓
- `/music-guides/` → existing logic sets aria-current on Music Guides trigger. New pass early-returns. ✓
- `/music-guides/abide-with-me.html` → existing logic sets aria-current on Music Guides trigger via prefix match. New pass early-returns. ✓
- `/` → no nav item is marked current (the logo is the only home affordance now). Acceptable and standard.

## Build and propagation

Edits go to **source files only**: `partials/nav.html`, `css/layout.css`, `js/nav.js`. Running `./build.sh` after the edits will:

1. Concatenate the CSS source files into `css/style.css`.
2. Inline the new `partials/nav.html` into all **102 HTML files** that reference it via their `@include-start partials/nav.html` markers.
3. Restore inlined `<style>` blocks to `<link>` tags and re-inline the freshly-built CSS.
4. Validate JSON-LD.

No build script changes needed.

## Testing

Verify in the preview server at four viewport widths:

- **1440px (full desktop)** — both dropdowns sit comfortably; gap fully expanded; no crowding.
- **1024px (laptop)** — clamped gap absorbs tightness; bar still single-line; both dropdown labels render in full with carets visible.
- **800px (narrow desktop)** — historical pain point. Bar must remain single-line **and must not overflow horizontally** (no scrollbar, no items clipped by the page-wrap edge).
- **768px (just above mobile breakpoint)** — same constraints as 800px. This is the critical width.
- **375px (mobile)** — hamburger opens; both dropdowns expand inline using the existing tap-to-open pattern; ESC closes both.

Behavioural checks:
- Hovering "Services" on desktop opens the dropdown; clicking the trigger word still navigates to `/services.html`.
- On `/weddings.html`, the "Services ▾" trigger shows the `aria-current="page"` underline.
- On `/music-guides/abide-with-me.html`, the "Music Guides ▾" trigger still shows the underline (existing behaviour preserved by the early-return guard).
- On `/`, no nav item is marked current.
- Keyboard: tab-stops include both dropdown triggers and their items; ESC closes the dropdown and returns focus to the trigger.

## Risks and Mitigations

### Risk: Horizontal overflow at the very narrow end of desktop (768–810px)

**The numbers.** With six nav items in uppercase 14px (~395px content), five gaps at the 12px clamp minimum (~60px), the logo at 25px (~280px), the inter-flex gap (24px), and `.page-wrap` padding (48px total), the bar needs ~810px of viewport to fit. The current mobile breakpoint kicks in at 767px. Between 768 and 810px the bar may overflow horizontally even though it won't wrap.

**Detection.** The 768px and 800px viewport checks in the testing matrix exist specifically to catch this. Look for a horizontal scrollbar on the body, items clipped by the page-wrap edge, or items extending under/past the logo.

**Mitigation if overflow is observed.** Bump the mobile breakpoint up to the smallest width that fits cleanly (likely ~819px so it ends in `-1` of a round 820px boundary). Note that the breakpoint value is duplicated across **five locations** and all must be updated together to keep the desktop-vs-mobile transition consistent:

| File | Line(s) | Pattern |
| --- | --- | --- |
| `css/layout.css` | 176 | `@media (max-width: 767px)` |
| `css/components.css` | 527, 659, 968 | `@media (max-width: 767px)` |
| `js/nav.js` | 39 | `window.matchMedia('(max-width: 767px)')` |

If a bump is needed, change all five occurrences to the same new value in a single commit so mobile/desktop behaviour stays in lockstep.

### Risk: Removing "Home" causes user confusion

Low risk: the logo is a universally understood home affordance. Footer and breadcrumbs (where present) cover any residual cases.

### Risk: Two adjacent dropdowns crowd each other visually

Mitigated by the clamped gap and `nowrap` rules. Verified in the testing matrix above.

### Risk: `aria-current` regression on Music Guides children

The new JS pass has an explicit early-return when an `aria-current` is already set, so it cannot override the existing prefix-match behaviour for Music Guides. Worth a sanity-check at `/music-guides/abide-with-me.html` in testing nonetheless.
