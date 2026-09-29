# Quiet Design Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Approved, 29 Sep 2026. The owner chose direction A and asked for the work to run to completion unattended.

**Goal:** Put the header's site name and menu on one baseline, and make the video heroes line up with their headings, use a quiet corner play button, carry a caption, and show the film on a phone's first screen.

**Architecture:** Source edits only in `css/*.css` (never `css/style.css` or a page's inlined `<style>`) and `partials/nav.html`, plus scripted, counted edits to page bodies outside the build's marker regions. `./build.sh` then inlines the CSS and expands the nav into every page. A new stdlib test checks the markup contract.

**Tech Stack:** Static HTML and CSS; Python 3 stdlib for the test and the one-off sweep scripts; `./build.sh`.

**As built (29 Sep 2026).** Reviews changed four things; the committed code and `tests/test_design_markup.py` are the reference where they differ from the listings below:
- The caret lift is one custom property, `--caret-lift`, and the open state adds back 0.28em (Task 2 listing updated).
- From 1081 to 1119px the menu gap is 0.8rem, and below 1081px `.site-nav` centres its items (Task 2 listing updated).
- In each hero the film comes before the text in the markup (breadcrumb, h1, `.hero-video`, `.hero-text`), so the tab order matches the phone layout. `.hero-text` and `.hero-video` carry no `min-width` (the `minmax(0, …)` tracks cover it).
- The test's check functions are named `check_*`, it guards against missing hero markup, counts at least 72 play buttons, and skips every dot-directory and `command_centre`.
- The promo film (`Lov_NegzVhM`) carries no caption: the owner dropped "A 43-second film of our singers" after review, so the listings' `PROMO` caption no longer applies and the test expects none.

**Spec:** [docs/superpowers/specs/2026-09-29-quiet-design-fixes-design.md](../specs/2026-09-29-quiet-design-fixes-design.md).

---

## Read this before starting

- Load the `build-and-verify` skill first. Never hand-edit a page's inlined `<style>` block or anything between `@include-start` / `@include-end` markers.
- Work in the worktree `/Users/luca/Documents/GitHub/londonchoralservice/.claude/worktrees/site-design-brainstorm-ab7113`. Run every command from there.
- The private register (private-events.html, planners-and-venues.html, destinations/) has its own CSS and player (`partials/private-register.css.html`, `js/private-events.js`). Do not touch either.
- One-off sweep scripts go in the session scratchpad, not the repo.
- Do not run `./build.sh` while another agent is editing pages in this worktree: it rewrites every HTML file in place.

## File structure

| File | Change | Task |
|---|---|---|
| `tests/test_design_markup.py` | New. Markup contract for nav carets, play buttons, hero order, captions, hero films | 1 |
| `partials/nav.html` | Remove the `&#9662;` glyph from the three carets | 2 |
| `css/layout.css` | Baseline header, item margins, current-page underline, toggle centring, footer name size | 2, 5 |
| `css/components.css` | Chevron caret, dropdown offset; hero grid, film offset, play button, caption, `aspect-ratio` | 2, 3, 4 |
| `css/pages.css` | Hide `.video-caption` in print | 4 |
| 52 main-site pages with `class="play-btn"` | New play-button SVG | 3 |
| 15 hero pages | Breadcrumb and h1 move out of `.hero-text`; caption added; two film swaps | 4 |

---

### Task 1: Markup contract test

**Files:**
- Create: `tests/test_design_markup.py`

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Markup contract for the quiet design fixes (spec 2026-09-29).

Stdlib only — run with: python3 tests/test_design_markup.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', '.claude', 'partials', 'node_modules', 'graphify-out', '.venv', 'docs', 'tests'}

PROMO = 'Lov_NegzVhM'
ABIDE = 'G9-R6k5n7Io'
UBI = '-GQaQEGhYEs'
BELLS = 'dGYqQf6BDAk'

HERO_FILMS = {
    'index.html': PROMO,
    'weddings.html': PROMO,
    'funerals.html': PROMO,
    'corporate.html': PROMO,
    'pricing.html': PROMO,
    'for-charities.html': PROMO,
    'for-event-managers.html': PROMO,
    'for-hotels.html': PROMO,
    'for-livery-companies.html': PROMO,
    'for-property-managers.html': PROMO,
    'christmas.html': BELLS,
    'carol-singers.html': BELLS,
    'christmas-pricing.html': BELLS,
    'for-funeral-directors.html': ABIDE,
    'for-wedding-planners.html': UBI,
}

CAPTIONS = {
    PROMO: 'A 43-second film of our singers',
    ABIDE: 'Abide With Me, sung by our full choir',
    UBI: 'Ubi Caritas by Ola Gjeilo, sung by a quintet',
    BELLS: 'Carol of the Bells, sung by our full choir',
}

NEW_PLAY_BTN = ('<svg class="play-btn" viewBox="0 0 56 56" aria-hidden="true">'
                '<circle cx="28" cy="28" r="27"/><path d="M23 19v18l15-9z"/></svg>')

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def site_pages():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith('.html'):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


def test_nav_carets_are_empty():
    nav = read('partials/nav.html')
    check('&#9662;' not in nav, 'partials/nav.html still has the ▾ glyph')
    carets = re.findall(r'<span class="dropdown-caret" aria-hidden="true">(.*?)</span>', nav)
    check(len(carets) == 3, f'expected 3 dropdown carets, found {len(carets)}')
    check(all(c == '' for c in carets), 'dropdown carets must be empty spans')


def test_play_buttons():
    old = new = 0
    for rel in site_pages():
        html = read(rel)
        if 'M66.52' in html:
            old += 1
            failures.append(f'{rel}: old YouTube play pill still present')
        new += html.count(NEW_PLAY_BTN)
        check(html.count('class="play-btn"') == html.count(NEW_PLAY_BTN),
              f'{rel}: a play-btn does not use the new SVG')
    check(new == 72, f'expected 72 new play buttons, found {new}')


def test_hero_order_caption_and_film():
    for page, film in HERO_FILMS.items():
        html = read(page)
        start = html.find('<div class="page-wrap hero">')
        check(start != -1, f'{page}: no hero')
        if start == -1:
            continue
        text_at = html.find('<div class="hero-text">', start)
        video_at = html.find('<div class="hero-video">', start)
        section_end = html.find('</section>', start)
        head = html[start:text_at]
        text = html[text_at:video_at]
        video = html[video_at:section_end]

        check('<h1>' in head, f'{page}: h1 must sit before .hero-text')
        check('<h1>' not in text, f'{page}: h1 still inside .hero-text')
        check('class="breadcrumb"' not in text, f'{page}: breadcrumb still inside .hero-text')
        if page != 'index.html':
            check('class="breadcrumb"' in head, f'{page}: breadcrumb must sit before .hero-text')
            check(head.find('class="breadcrumb"') < head.find('<h1>'),
                  f'{page}: breadcrumb must come before the h1')

        check(f'data-video="{film}"' in video, f'{page}: hero film should be {film}')
        check(f'/vi/{film}/maxresdefault.jpg' in video, f'{page}: hero thumbnail should be {film}')
        caption = f'<p class="video-caption">{CAPTIONS[film]}</p>'
        check(video.count(caption) == 1, f'{page}: missing caption "{CAPTIONS[film]}"')


def main():
    test_nav_carets_are_empty()
    test_play_buttons()
    test_hero_order_caption_and_film()
    if failures:
        print(f'FAIL: {len(failures)} problem(s)')
        for f in failures[:40]:
            print('  -', f)
        sys.exit(1)
    print('OK: nav carets, 72 play buttons, 15 hero pages')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 tests/test_design_markup.py`
Expected: `FAIL:` with lines for the ▾ glyph, old play pills, and every hero page.

- [ ] **Step 3: Commit**

```bash
git add tests/test_design_markup.py
git commit -m "test(design): markup contract for the quiet design fixes"
```

---

### Task 2: Header on one baseline

**Files:**
- Modify: `partials/nav.html` (three carets)
- Modify: `css/layout.css` (`.site-nav`, `.nav-links`, `.nav-links a`, current page, `.nav-toggle`)
- Modify: `css/components.css` (Nav Dropdown section)

- [ ] **Step 1: Empty the carets in the partial**

In `partials/nav.html`, replace each of the three occurrences of

```html
<span class="dropdown-caret" aria-hidden="true">&#9662;</span>
```

with

```html
<span class="dropdown-caret" aria-hidden="true"></span>
```

- [ ] **Step 2: Baseline, item margins, current page and toggle in `css/layout.css`**

Change `.site-nav`:

```css
.site-nav {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-block: var(--space-lg);
  gap: var(--space-lg);
}
```

After the `.nav-links { … }` rule add:

```css
/* Base li margins would hang below the baseline and grow the header. */
.nav-links li {
  margin-bottom: 0;
}
```

In `.nav-links a`, delete the line `padding-bottom: 2px;` (it only made room for the old border).

Replace the current-page rule:

```css
.nav-links a[aria-current="page"] {
  text-decoration-line: underline;
  text-decoration-thickness: 1px;
  text-decoration-color: var(--color-accent);
  text-underline-offset: 0.45em;
}
```

The hamburger shows only at 1080px and below, where Step 3's mobile rule centres the row, so `.nav-toggle` itself needs no change.

- [ ] **Step 3: Chevron caret and dropdown offset in `css/components.css`**

Replace the `.dropdown-caret` rule:

```css
/* Two borders of a 0.4em box, rotated. The lift raises the closed chevron to
   the middle of the capitals. Open, the stroke is the box's top half, so the
   open rule adds back half the diagonal (0.28em) to keep it in the same place. */
.dropdown-caret {
  --caret-lift: -0.3em;
  display: inline-block;
  width: 0.4em;
  height: 0.4em;
  margin-left: 0.3em;
  border-right: 1px solid currentColor;
  border-bottom: 1px solid currentColor;
  transform: translateY(var(--caret-lift)) rotate(45deg);
  transition: transform var(--transition-fast);
}
```

In `css/layout.css`, next to the nav rules, keep the wider chevrons from pushing the menu past the content edge between the breakpoint and 1120px (the default gap fits from about 1110px with a 15px scrollbar):

```css
@media (min-width: 1081px) and (max-width: 1119px) {
  .nav-links {
    gap: 0.8rem;
  }
}
```

In the `@media (max-width: 1080px)` block, the menu is absolutely positioned, so centre the name and toggle there instead of the `align-self` on `.nav-toggle`:

```css
  .site-nav {
    position: relative;
    align-items: center;
  }
```

In `.dropdown-menu`, change `left: 0;` to:

```css
  /* Items are padded --space-lg inside a 1px border: pull the menu left so
     their text starts under the trigger's first letter. */
  left: calc(-1 * (var(--space-lg) + 1px));
```

Replace the open-state caret rule (`transform: rotate(180deg);`):

```css
.has-dropdown:hover > .dropdown-trigger .dropdown-caret,
.has-dropdown:focus-within > .dropdown-trigger .dropdown-caret,
.has-dropdown[data-open="true"] > .dropdown-trigger .dropdown-caret {
  transform: translateY(calc(var(--caret-lift) + 0.28em)) rotate(225deg);
}
```

Replace the dismissed-state caret rule (`transform: none;`):

```css
.has-dropdown[data-dismissed] > .dropdown-trigger .dropdown-caret {
  transform: translateY(var(--caret-lift)) rotate(45deg);
}
```

The mobile block's `.dropdown-menu { position: static; … }` ignores `left`, so the hamburger menu is unchanged.

- [ ] **Step 4: Build and run the nav part of the test**

Run: `./build.sh && python3 tests/test_design_markup.py`
Expected: build exits 0; the test no longer lists the ▾ glyph (other failures remain until Tasks 3–4).

- [ ] **Step 5: Measure**

Serve with `python3 -m http.server 8000` and, at 1440, 1200 and 1100px wide, on `/`, `/weddings.html` and `/music-guides/`, run in the page:

```js
function bl(el){const s=document.createElement('span');s.style.cssText='display:inline-block;width:0;height:0;vertical-align:baseline';el.appendChild(s);const y=s.getBoundingClientRect().top;s.remove();return y;}
[bl(document.querySelector('.site-name')), bl(document.querySelector('.nav-links > li > a')), document.querySelector('.site-header').getBoundingClientRect().height]
```

Expected: the first two numbers within 0.5px; height 89 (±1). At 1000px the hamburger's vertical centre is within 2px of the site name's.

- [ ] **Step 6: Commit**

```bash
git add partials/nav.html css/layout.css css/components.css
git commit -m "fix(nav): put the site name and menu on one baseline; hairline chevrons"
```

(Commit source files only here; the rebuilt pages are committed once, in Task 6.)

---

### Task 3: Corner play button

**Files:**
- Modify: `css/components.css` (Responsive Video Embed section)
- Modify: the 52 main-site pages with `class="play-btn"` (scripted)

- [ ] **Step 1: Replace the SVG in every main-site page**

Save as `<scratchpad>/sweep_play_btn.py` and run from the worktree root:

```python
import pathlib
import re

OLD = re.compile(
    r'<svg class="play-btn" viewBox="0 0 68 48" aria-hidden="true">\s*'
    r'<path d="M66\.52[^"]*" fill="rgba\(0,0,0,\.7\)"/>\s*'
    r'<path d="M45 24 27 14v20z" fill="#fff"/>\s*'
    r'</svg>'
)
NEW = ('<svg class="play-btn" viewBox="0 0 56 56" aria-hidden="true">'
       '<circle cx="28" cy="28" r="27"/><path d="M23 19v18l15-9z"/></svg>')
SKIP = {'.git', '.claude', 'partials', 'node_modules', 'graphify-out', '.venv'}

total = files = 0
for p in sorted(pathlib.Path('.').rglob('*.html')):
    if SKIP & set(p.parts):
        continue
    s = p.read_text(encoding='utf-8')
    s2, n = OLD.subn(NEW, s)
    if n:
        p.write_text(s2, encoding='utf-8')
        total += n
        files += 1
print(f'{total} buttons in {files} files')
```

Expected output: `72 buttons in 52 files`. Then `grep -rl 'M66.52' --include='*.html' . | grep -v '^./.claude'` prints nothing.

- [ ] **Step 2: Style it in `css/components.css`**

Replace the `.video-embed` rule (drop the padding hack):

```css
.video-embed {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
}
```

Replace the `.play-btn` rule and the `.video-thumb:hover .play-btn, .video-thumb:focus-visible .play-btn { opacity: 0.85; }` rule with:

```css
/* A plain circle in the corner, clear of any title burned into the film. */
.play-btn {
  position: absolute;
  left: var(--space-md);
  bottom: var(--space-md);
  width: 3.5rem;
  height: 3.5rem;
  overflow: visible;
}

.play-btn circle {
  fill: rgba(28, 22, 20, 0.45);
  stroke: var(--color-bg);
  stroke-width: 1.5;
  transition: fill var(--transition-fast), stroke var(--transition-fast);
}

.play-btn path {
  fill: var(--color-bg);
}

.video-thumb:hover .play-btn circle,
.video-thumb:focus-visible .play-btn circle {
  fill: var(--color-accent);
  stroke: var(--color-accent);
}

@media (max-width: 599px) {
  .play-btn {
    left: var(--space-sm);
    bottom: var(--space-sm);
    width: 3rem;
    height: 3rem;
  }
}
```

Keep the existing `.video-thumb:focus-visible { outline: …; box-shadow: … }` rule as it is.

- [ ] **Step 3: Commit (sources and page bodies)**

```bash
git add -u '*.html' css/components.css
git commit -m "feat(video): a quiet corner play button in place of the YouTube pill"
```

(If Task 2's build already ran, the pages also carry rebuilt CSS; that is fine because Task 6 rebuilds and commits the final state.)

---

### Task 4: Hero layout, captions and films

**Files:**
- Modify: `css/components.css` (Hero Banner Layout section)
- Modify: `css/pages.css` (print list)
- Modify: the 15 hero pages (scripted)

- [ ] **Step 1: Move the breadcrumb and h1, add captions, swap two films**

Save as `<scratchpad>/restructure_heroes.py` and run from the worktree root:

```python
import pathlib
import re

PROMO, ABIDE, UBI, BELLS = 'Lov_NegzVhM', 'G9-R6k5n7Io', '-GQaQEGhYEs', 'dGYqQf6BDAk'
PAGES = {
    'index.html': PROMO, 'weddings.html': PROMO, 'funerals.html': PROMO,
    'corporate.html': PROMO, 'pricing.html': PROMO, 'for-charities.html': PROMO,
    'for-event-managers.html': PROMO, 'for-hotels.html': PROMO,
    'for-livery-companies.html': PROMO, 'for-property-managers.html': PROMO,
    'christmas.html': BELLS, 'carol-singers.html': BELLS, 'christmas-pricing.html': BELLS,
    'for-funeral-directors.html': ABIDE, 'for-wedding-planners.html': UBI,
}
CAPTIONS = {
    PROMO: 'A 43-second film of our singers',
    ABIDE: 'Abide With Me, sung by our full choir',
    UBI: 'Ubi Caritas by Ola Gjeilo, sung by a quintet',
    BELLS: 'Carol of the Bells, sung by our full choir',
}
SWAPS = {
    ABIDE: ('Play Abide With Me', 'Abide With Me — The London Choral Service'),
    UBI: ('Play Ubi Caritas', 'Ubi Caritas by Ola Gjeilo — The London Choral Service'),
}
PROMO_LABEL = 'Play our film: singers for funerals, weddings and events'
PROMO_ALT = 'Still from our film of singers for funerals, weddings and events'


def dedent2(block):
    return '\n'.join(l[2:] if l.startswith('  ') else l for l in block.split('\n'))


for name, film in PAGES.items():
    p = pathlib.Path(name)
    s = p.read_text(encoding='utf-8')
    a = s.index('<div class="page-wrap hero">')
    t = s.index('        <div class="hero-text">\n', a)
    v = s.index('        <div class="hero-video">', a)
    inner = s[t:v]
    moved = []
    for pat in (r'\n          <nav class="breadcrumb".*?</nav>', r'\n          <h1>.*?</h1>'):
        m = re.search(pat, inner, re.S)
        if m:
            moved.append(dedent2(m.group(0)).lstrip('\n') + '\n')
            inner = inner[:m.start()] + inner[m.end():]
    assert moved and '<h1>' in moved[-1], name
    s = s[:t] + ''.join(moved) + inner + s[v:]

    v = s.index('        <div class="hero-video">', a)
    end = s.index('          </div>\n        </div>', v)
    video = s[v:end]
    if film in SWAPS:
        label, alt = SWAPS[film]
        assert f'data-video="{PROMO}"' in video, name
        video = (video.replace(f'aria-label="{PROMO_LABEL}"', f'aria-label="{label}"')
                      .replace(f'data-video="{PROMO}"', f'data-video="{film}"')
                      .replace(f'/vi/{PROMO}/', f'/vi/{film}/')
                      .replace(f'alt="{PROMO_ALT}"', f'alt="{alt}"'))
    caption = f'\n          <p class="video-caption">{CAPTIONS[film]}</p>'
    s = s[:v] + video + '          </div>' + caption + '\n        </div>' + s[end + len('          </div>\n        </div>'):]
    p.write_text(s, encoding='utf-8')
    print('ok', name)
```

Expected: 15 `ok` lines. `python3 tests/test_design_markup.py` then reports no hero failures (the play-button checks pass once Task 3 has run).

- [ ] **Step 2: Hero grid in `css/components.css`**

Replace the three rules `.hero`, `.hero-text`, `.hero-video` and the `@media (max-width: 805px) { .hero … .hero-video … }` block with:

```css
.hero {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
  grid-template-areas:
    "crumb crumb"
    "head  video"
    "body  video";
  grid-template-rows: auto auto 1fr;
  column-gap: var(--space-3xl);
  align-items: start;
}

.hero > .breadcrumb {
  grid-area: crumb;
}

.hero > h1 {
  grid-area: head;
}

.hero-text {
  grid-area: body;
  min-width: 0;
}

.hero-video {
  grid-area: video;
  min-width: 0;
  position: sticky;
  top: var(--space-2xl);
  /* Top edge level with the h1's capitals: Cormorant Garamond's cap top
     sits 0.28 of the font size below the top of an h1 line box. */
  margin-top: calc(var(--text-display) * 0.28);
}

.video-caption {
  margin-top: var(--space-sm);
  font-size: var(--text-sm);
  font-style: italic;
  color: var(--color-text-mid);
}
```

and, after the `.video-thumb:focus-visible` rule:

```css
/* Phones: the film comes straight after the heading. */
@media (max-width: 805px) {
  .hero {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "crumb"
      "head"
      "video"
      "body";
    grid-template-rows: none;
  }

  .hero-video {
    position: static;
    margin-top: 0;
    margin-bottom: var(--space-xl);
  }
}
```

- [ ] **Step 3: Print**

In `css/pages.css`, add `.video-caption,` to the print `display: none !important` list, after `.video-embed,`.

- [ ] **Step 4: Build and run the test**

Run: `./build.sh && python3 tests/test_design_markup.py`
Expected: build exits 0; `OK: nav carets, 72 play buttons, 15 hero pages`.

- [ ] **Step 5: Measure**

At 1440 and 1024px on all 15 hero pages:

```js
const h=document.querySelector('.hero > h1'), v=document.querySelector('.hero-video').getBoundingClientRect();
const cs=getComputedStyle(h), c=document.createElement('canvas').getContext('2d');
c.font=`${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`; const m=c.measureText('H');
const capTop=h.getBoundingClientRect().top+(parseFloat(cs.lineHeight)-(m.fontBoundingBoxAscent+m.fontBoundingBoxDescent))/2+(m.fontBoundingBoxAscent-m.actualBoundingBoxAscent);
[Math.round(v.top-capTop), document.documentElement.scrollWidth<=innerWidth]
```

Expected: first value between −2 and 2; second `true`. At 375×812 on funerals, weddings and index: film order after the h1, and `document.querySelector('.hero-video').getBoundingClientRect().bottom < 755`.

- [ ] **Step 6: Commit**

```bash
git add -u '*.html' css/components.css css/pages.css
git commit -m "feat(hero): align the film with the heading, caption it, show it first on phones"
```

---

### Task 5: Footer site name on one line

**Files:**
- Modify: `css/layout.css` (`.footer-name`)

- [ ] **Step 1: Match the header's size**

In `.footer-name`, change `font-size: var(--text-xl);` to `font-size: var(--text-lg);`.

- [ ] **Step 2: Build and check**

Run: `./build.sh`. At 1440px on `/`, `document.querySelector('.footer-name').getClientRects().length` is 1 and its height is under 45px.

- [ ] **Step 3: Commit**

```bash
git add css/layout.css
git commit -m "fix(footer): set the site name at the header's size so it holds one line"
```

---

### Task 6: Full verification, PR, merge, live check

- [ ] **Step 1: Rebuild and run every check**

```bash
./build.sh
python3 tests/test_design_markup.py
python3 tests/test_stage_site.py
.venv/bin/python tests/test_register_generators.py
.venv/bin/python tests/test_competitor_claims.py
python3 scripts/stage_site.py
```

Expected: all exit 0. `./build.sh && git status --short` after a second run shows no further changes.

- [ ] **Step 2: Diff shape**

`git diff --stat main...HEAD` touches ~165 pages (inlined CSS and nav partial) plus the 52 play-button pages and 15 hero pages. Spot-check `git diff main...HEAD -- areas/london/camden.html` (CSS and nav only) and `for-funeral-directors.html` (CSS, nav, play button, hero).

- [ ] **Step 3: Visual pass**

Screenshots at 1440, 1024 and 375 of index, funerals, for-funeral-directors and christmas; keyboard Tab to a film (inset ring, oxblood circle); hover a dropdown (chevron points up, item text under the trigger); reduced motion via emulation.

- [ ] **Step 4: Graph**

The change rewrites page bodies on 52 pages but adds no pages or links; skip `/graphify --update`.

- [ ] **Step 5: Commit the built output, push, PR, merge**

```bash
git add -A
git commit -m "chore(build): rebuild pages for the quiet design fixes"
git push -u origin claude/site-design-brainstorm-ab7113
gh pr create --title "Quiet design fixes: header baseline and video heroes" --body-file <scratchpad>/pr-body.md
gh pr merge --merge
```

- [ ] **Step 6: Live check**

After the deploy finishes: `git fetch origin && python3 scripts/check_live_site.py` (exit 2 means the CDN is still serving the old build; re-run after ten minutes), then load `https://londonchoralservice.com/funerals.html` and confirm the header baseline and the corner play button.
