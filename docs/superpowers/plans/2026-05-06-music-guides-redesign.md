# Music Guides Index Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `/music-guides/` into a filterable card-grid with category chips, add a global nav dropdown for "Music Guides", and extract the global nav and footer into shared HTML partials assembled by `build.sh`.

**Architecture:** Static-site, no framework. Add an HTML-include pass to the existing `build.sh` (paired `<!-- @include-start partials/X.html -->` / `<!-- @include-end partials/X.html -->` markers). One source of truth for nav and footer, deployed via GitHub Pages. Filter UX is a progressive-enhancement layer over a single canonical URL — works without JS via real `<a href="?category=…">` links; JS upgrades it to in-page toggle with `pushState`.

**Tech Stack:** HTML, CSS (modular files concatenated by `build.sh`), vanilla JS, Python 3 (existing one-time migration + JSON-LD validation), Bash, GitHub Pages.

**Reference spec:** [docs/superpowers/specs/2026-05-06-music-guides-redesign-design.md](../specs/2026-05-06-music-guides-redesign-design.md)

---

## File structure

**Created:**

| Path | Purpose |
|---|---|
| `partials/nav.html` | The `<header class="site-header">…</header>` block, single source of truth for site navigation. |
| `partials/footer.html` | The `<footer class="site-footer">…</footer>` block plus the `<div class="mobile-cta">…</div>` block (both are bottom-of-body site chrome). |
| `js/music-guides.js` | Filter-chip logic for the music-guides index: read `?category=` on load, toggle category sections on click, `pushState`, no-JS fallback. Loaded only on `/music-guides/`. |
| `migrate_partials.py` | One-time Python script to replace existing nav/footer/mobile-cta blocks across all 102 HTML files with include markers. Deleted after the migration commit. |

**Modified:**

| Path | What changes |
|---|---|
| `build.sh` | New pass before CSS-inlining: for every `.html` file, replace content between `@include-start path` / `@include-end path` markers with the file at `path`. |
| `css/components.css` | Add styles for filter chips, guide cards, "Start Here" feature card, nav dropdown. |
| `css/layout.css` | Add `.guide-grid` (2-column responsive), wider container for the music-guides index. |
| `js/nav.js` | Add: (1) mobile dropdown expand/collapse, (2) ESC closes dropdown, (3) `aria-current="page"` set dynamically based on `location.pathname`. |
| `music-guides/index.html` | Restructure: keep H1+lede, add Start Here card, filter chips, three category sections with the new card grid markup. Remove the "General" section. Add the 2 missing guides. Update JSON-LD `ItemList` to all 33 guides. Wider container. |
| `weddings.html` | Update "Browse all wedding guides" CTA to point to `/music-guides/?category=weddings`. |
| `funerals.html` | Update "Browse all funeral guides" CTA to point to `/music-guides/?category=funerals`. |
| All 102 HTML files | Existing nav/footer/mobile-cta blocks replaced with include markers (one-time migration). All nav and footer URLs become absolute paths (root-relative) in the partials. |

---

## Stage A — Partials infrastructure

End state: every HTML file uses `@include-start` / `@include-end` markers for nav and footer; `build.sh` populates them; the rendered HTML is byte-equivalent to the current site (modulo absolute URLs).

### Task A1: Add HTML-include pass to `build.sh`

**Files:**
- Modify: `build.sh`

- [ ] **Step 1: Read current `build.sh`**

Open `build.sh` and identify the line `echo "Inlining CSS into HTML files..."`. The new include pass goes immediately before that line (so includes are populated before CSS gets inlined into the result).

- [ ] **Step 2: Insert the include pass**

Replace the current contents of `build.sh` with:

```bash
#!/usr/bin/env bash
# Build script for The London Choral Service website
# 1) Concatenates CSS source files
# 2) Populates HTML partials between @include-start / @include-end markers
# 3) Inlines the concatenated CSS into HTML files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSS_DIR="$SCRIPT_DIR/css"

echo "Building CSS..."

cat \
  "$CSS_DIR/tokens.css" \
  "$CSS_DIR/base.css" \
  "$CSS_DIR/layout.css" \
  "$CSS_DIR/components.css" \
  "$CSS_DIR/pages.css" \
  > "$CSS_DIR/style.css"

echo "Created css/style.css ($(wc -c < "$CSS_DIR/style.css") bytes)"

echo "Populating HTML partials..."

include_count=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*' -not -path '*/partials/*'); do
  if grep -q '@include-start' "$file"; then
    awk -v root="$SCRIPT_DIR" '
      /<!-- @include-start [^ ]+ -->/ {
        match($0, /@include-start [^ ]+/)
        partial = substr($0, RSTART + 15, RLENGTH - 15)
        partial_path = root "/" partial
        print
        skipping = 1
        # Emit the partial contents
        while ((getline line < partial_path) > 0) print line
        close(partial_path)
        next
      }
      /<!-- @include-end [^ ]+ -->/ {
        skipping = 0
        print
        next
      }
      skipping == 1 { next }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    include_count=$((include_count + 1))
  fi
done

echo "Populated partials in $include_count HTML files"

echo "Inlining CSS into HTML files..."

count=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*' -not -path '*/partials/*'); do
  if grep -q '<link rel="stylesheet" href=.*style\.css">' "$file"; then
    awk -v css="$CSS_DIR/style.css" '
      /<link rel="stylesheet" href=.*style\.css">/ {
        print "  <style>"
        while ((getline line < css) > 0) print "    " line
        close(css)
        print "  </style>"
        next
      }
      { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    count=$((count + 1))
  fi
done

echo "Inlined CSS into $count HTML files"

echo "Validating JSON-LD..."
python3 validate_jsonld.py

echo "Done."
```

- [ ] **Step 3: Verify it parses**

Run: `bash -n build.sh`
Expected: no output (syntax OK).

- [ ] **Step 4: Commit**

```bash
git add build.sh
git commit -m "build: add HTML partial-include pass to build.sh"
```

---

### Task A2: Smoke-test the include pass with a fixture

We test the build.sh pass before relying on it across 102 real files.

**Files:**
- Create (temporarily): `partials/_smoketest.html`, `_smoketest.html`

- [ ] **Step 1: Create the fixture partial**

```bash
mkdir -p partials
cat > partials/_smoketest.html <<'EOF'
<p>HELLO FROM PARTIAL</p>
EOF
```

- [ ] **Step 2: Create a fixture page**

```bash
cat > _smoketest.html <<'EOF'
<!DOCTYPE html>
<html><body>
  <!-- @include-start partials/_smoketest.html -->
  <p>OLD CONTENT THAT SHOULD BE WIPED</p>
  <!-- @include-end partials/_smoketest.html -->
</body></html>
EOF
```

- [ ] **Step 3: Run build.sh**

Run: `./build.sh`
Expected: Output includes "Populated partials in N HTML files" with N >= 1.

- [ ] **Step 4: Verify the fixture got populated correctly**

Run: `cat _smoketest.html`
Expected output (the OLD CONTENT line is gone, the partial's content is between the markers):

```
<!DOCTYPE html>
<html><body>
  <!-- @include-start partials/_smoketest.html -->
<p>HELLO FROM PARTIAL</p>
  <!-- @include-end partials/_smoketest.html -->
</body></html>
```

- [ ] **Step 5: Run build.sh again to verify idempotency**

Run: `./build.sh && diff <(cat _smoketest.html) <(cat _smoketest.html)`
Expected: no diff. The second run should leave the file unchanged (already-populated partials get re-populated to the same content).

- [ ] **Step 6: Clean up the fixture**

```bash
rm _smoketest.html partials/_smoketest.html
```

(Note: don't `rmdir partials` — we'll create real partials in the next task.)

- [ ] **Step 7: No commit**

This task verifies behaviour but creates no committed artifacts. Move to A3.

---

### Task A3: Create `partials/nav.html`

**Files:**
- Create: `partials/nav.html`

- [ ] **Step 1: Create the nav partial with absolute URLs**

```bash
mkdir -p partials
cat > partials/nav.html <<'EOF'
  <header class="site-header">
    <nav class="site-nav page-wrap" aria-label="Main navigation">
      <a href="/" class="site-name">The London Choral Service</a>
      <button class="nav-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Menu">
        <span class="nav-toggle-bar"></span>
      </button>
      <ul id="nav-menu" class="nav-links" role="list">
        <li><a href="/">Home</a></li>
        <li><a href="/about.html">About</a></li>
        <li><a href="/services.html">Services</a></li>
        <li><a href="/listen.html">Listen</a></li>
        <li><a href="/music-guides/">Music Guides</a></li>
        <li><a href="/pricing.html">Pricing</a></li>
        <li><a href="/contact.html">Contact</a></li>
      </ul>
    </nav>
  </header>
EOF
```

- [ ] **Step 2: Verify the file was written**

Run: `wc -l partials/nav.html`
Expected: 16 lines.

- [ ] **Step 3: No commit yet**

Commit happens after A4.

---

### Task A4: Create `partials/footer.html`

**Files:**
- Create: `partials/footer.html`

- [ ] **Step 1: Create the footer partial with absolute URLs**

```bash
cat > partials/footer.html <<'EOF'
  <footer class="site-footer">
    <div class="prose">
      <hr>
      <p class="footer-name">The London Choral Service</p>
      <p class="text-sm text-mid">Exceptional singers, choirs, and instrumentalists for funerals, weddings, memorials, and ceremonies across the United Kingdom.</p>
      <p class="text-sm text-mid">
        <a href="mailto:office@londonchoralservice.com">office@londonchoralservice.com</a>
        &ensp;|&ensp;
        <a href="tel:+447356042468">07356 042468</a>
      </p>
      <p class="text-xs text-mid">
        Areas we serve: <a href="/areas/london.html">London</a> &middot; <a href="/areas/birmingham.html">Birmingham</a> &middot; <a href="/areas/manchester.html">Manchester</a> &middot; <a href="/areas/liverpool.html">Liverpool</a> &middot; <a href="/areas/oxford.html">Oxford</a> &middot; <a href="/areas/cambridge.html">Cambridge</a> &middot; <a href="/areas/reading.html">Reading</a> &middot; <a href="/areas/slough-maidenhead.html">Slough &amp; Maidenhead</a> &middot; <a href="/areas/guildford.html">Guildford</a> &middot; <a href="/areas/brighton.html">Brighton</a> &middot; <a href="/areas/chester.html">Chester</a> &middot; <a href="/areas/st-albans.html">St Albans</a> &middot; <a href="/areas/canterbury.html">Canterbury</a> &middot; <a href="/areas/windsor.html">Windsor</a> &middot; <a href="/areas/winchester.html">Winchester</a> &middot; <a href="/areas/salisbury.html">Salisbury</a> &middot; <a href="/areas/bath.html">Bath</a> &middot; <a href="/areas/chelmsford.html">Chelmsford</a> &middot; <a href="/areas/rochester.html">Rochester</a>
      </p>
      <p class="text-xs text-mid">
        <a href="/privacy.html">Privacy policy</a>
      </p>
      <p class="text-xs text-mid">The London Choral Service is the operating name of Alma Consort Ltd. Based in London, serving the whole of the United Kingdom.</p>
      <p class="text-xs text-mid">&copy; <span data-year>2026</span> The London Choral Service. All rights reserved.</p>
    </div>
  </footer>

  <div class="mobile-cta" aria-label="Quick contact">
    <a href="/contact.html" class="mobile-cta-enquire">Enquire</a>
  </div>
EOF
```

- [ ] **Step 2: Verify the file was written**

Run: `grep -c '<a href' partials/footer.html`
Expected: 23 (1 mailto + 1 tel + 19 areas + 1 privacy + 1 mobile-cta).

- [ ] **Step 3: Commit partials**

```bash
git add partials/nav.html partials/footer.html
git commit -m "build: add nav and footer partials with absolute URLs"
```

---

### Task A5: Write the migration script

This script replaces the existing inline nav and footer/mobile-cta blocks across all 102 HTML files with `@include-start` / `@include-end` markers. It runs once and is then deleted.

**Files:**
- Create: `migrate_partials.py`

- [ ] **Step 1: Write the migration script**

```python
#!/usr/bin/env python3
"""One-time migration: replace existing nav/footer/mobile-cta blocks
with @include-start / @include-end markers across all .html files.

Idempotent: if a file already contains markers, it is skipped."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Match the entire <header class="site-header">…</header> block.
NAV_RE = re.compile(r'<header class="site-header">.*?</header>\s*\n', re.DOTALL)

# Match the <footer class="site-footer">…</footer> block AND the
# <div class="mobile-cta">…</div> block that follows it (with any
# whitespace between them).
FOOTER_RE = re.compile(
    r'<footer class="site-footer">.*?</footer>\s*\n'
    r'\s*<div class="mobile-cta"[^>]*>.*?</div>\s*\n',
    re.DOTALL,
)

NAV_REPLACEMENT = (
    '  <!-- @include-start partials/nav.html -->\n'
    '  <!-- @include-end partials/nav.html -->\n'
)

FOOTER_REPLACEMENT = (
    '  <!-- @include-start partials/footer.html -->\n'
    '  <!-- @include-end partials/footer.html -->\n'
)


def migrate(path: Path) -> str:
    """Migrate a single file. Returns 'migrated', 'skipped', or 'no-match'."""
    text = path.read_text()

    if '@include-start' in text:
        return 'skipped'

    new_text, nav_count = NAV_RE.subn(NAV_REPLACEMENT, text, count=1)
    new_text, footer_count = FOOTER_RE.subn(FOOTER_REPLACEMENT, new_text, count=1)

    if nav_count == 0 and footer_count == 0:
        return 'no-match'

    if nav_count != 1 or footer_count != 1:
        print(
            f'WARNING: {path.relative_to(ROOT)} — '
            f'nav_count={nav_count}, footer_count={footer_count}',
            file=sys.stderr,
        )

    path.write_text(new_text)
    return 'migrated'


def main():
    counts = {'migrated': 0, 'skipped': 0, 'no-match': 0}
    for html_file in sorted(ROOT.rglob('*.html')):
        rel = html_file.relative_to(ROOT)
        if any(part in {'.git', 'node_modules', 'partials'} for part in rel.parts):
            continue
        result = migrate(html_file)
        counts[result] += 1
        if result == 'migrated':
            print(f'migrated: {rel}')
        elif result == 'no-match':
            print(f'NO MATCH: {rel}', file=sys.stderr)

    print()
    print(f"Migrated: {counts['migrated']}")
    print(f"Skipped (already migrated): {counts['skipped']}")
    print(f"No match: {counts['no-match']}")

    if counts['no-match'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: No commit**

The script is a temporary tool. Commit it now would be premature; we run it next, verify, then commit the result and delete the script in Task A7.

---

### Task A6: Run the migration script and verify

**Files:**
- Modify (en masse): all 102 HTML files

- [ ] **Step 1: Dry-run on one file (sanity check)**

Run a quick spot-check on one file to confirm the regex matches before migrating en masse:

```bash
python3 -c "
import re
text = open('weddings.html').read()
nav_re = re.compile(r'<header class=\"site-header\">.*?</header>\s*\n', re.DOTALL)
footer_re = re.compile(r'<footer class=\"site-footer\">.*?</footer>\s*\n\s*<div class=\"mobile-cta\"[^>]*>.*?</div>\s*\n', re.DOTALL)
print('nav matches:', len(nav_re.findall(text)))
print('footer matches:', len(footer_re.findall(text)))
"
```
Expected: `nav matches: 1` and `footer matches: 1`.

- [ ] **Step 2: Run the migration**

Run: `python3 migrate_partials.py`
Expected: ~102 lines of `migrated: <path>`, then a summary like `Migrated: 102, Skipped: 0, No match: 0`. If any "NO MATCH" appears, **STOP** — the script needs adjustment for that file's structure before continuing.

- [ ] **Step 3: Run `build.sh` to populate the markers**

Run: `./build.sh`
Expected: Output includes `Populated partials in 102 HTML files` (or whatever count matches the migrated total).

- [ ] **Step 4: Spot-check three pages at different depths**

Verify the populated nav/footer is identical in shape across the three depth tiers.

```bash
grep -A 1 '@include-start partials/nav' index.html | head -3
grep -A 1 '@include-start partials/nav' music-guides/index.html | head -3
grep -A 1 '@include-start partials/nav' areas/london.html | head -3
```
Expected: each prints the marker followed by `  <header class="site-header">`.

- [ ] **Step 5: Validate JSON-LD still parses**

Run: `python3 validate_jsonld.py`
Expected: no errors.

- [ ] **Step 6: Visual smoke-test in the preview**

Use the preview tooling (preview_start, then preview_screenshot) to check that:
- `/` renders with the nav
- `/music-guides/` renders with the nav
- `/areas/london.html` renders with the nav
- `/areas/london/camden.html` renders with the nav (deepest path)

All nav links should be clickable; the footer should appear; the mobile CTA should appear at narrow widths. **Do not proceed if any page is visibly broken.**

---

### Task A7: Commit migration and delete the script

- [ ] **Step 1: Stage the migrated files and the now-built artefacts**

```bash
git add -A
git status
```
Expected: ~102 modified `.html` files, plus `css/style.css` (rebuilt). No surprises.

- [ ] **Step 2: Delete the migration script**

```bash
rm migrate_partials.py
git add migrate_partials.py
```

- [ ] **Step 3: Commit**

```bash
git commit -m "build: migrate all pages to nav/footer partials, switch to absolute URLs"
```

---

## Stage B — Music-guides index redesign

End state: `/music-guides/` has a Start Here card, filter chips, three category sections in a responsive 2-column card grid, JSON-LD lists all 33 guides, and the `?category=` URL parameter filters the visible categories with a no-JS fallback.

### Task B1: Add new CSS for the index page

**Files:**
- Modify: `css/components.css`
- Modify: `css/layout.css`

- [ ] **Step 1: Append the guide-index components to `css/components.css`**

At the end of `css/components.css`, append:

```css
/* ═══════════════════════════════════
   Guide Index — Filter Chips
   ═══════════════════════════════════ */
.filter-bar {
  margin-block: var(--space-xl) var(--space-2xl);
}

.filter-bar-label {
  font-family: var(--font-heading);
  font-size: var(--text-sm);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-mid);
  margin-bottom: var(--space-md);
  display: block;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  list-style: none;
  padding: 0;
  margin: 0;
}

.filter-chips li {
  margin: 0;
}

.filter-chip {
  display: inline-block;
  font-family: var(--font-heading);
  font-size: var(--text-sm);
  font-weight: 500;
  letter-spacing: 0.04em;
  padding: var(--space-sm) var(--space-lg);
  border: 1px solid var(--color-rule);
  background-color: transparent;
  color: var(--color-text);
  text-decoration: none;
  cursor: pointer;
  transition: background-color var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast);
}

.filter-chip:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.filter-chip[aria-pressed="true"] {
  background-color: var(--color-accent);
  color: var(--color-bg);
  border-color: var(--color-accent);
}

.filter-chip[aria-pressed="true"]:hover {
  background-color: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
  color: var(--color-bg);
}

/* ═══════════════════════════════════
   Guide Index — Start Here Card
   ═══════════════════════════════════ */
.start-here {
  position: relative;
  padding: var(--space-xl);
  background-color: var(--color-bg-alt);
  border-left: 3px solid var(--color-accent);
  margin-block: var(--space-xl) var(--space-2xl);
}

.start-here__eyebrow {
  display: block;
  font-family: var(--font-heading);
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-accent);
  margin-bottom: var(--space-sm);
}

.start-here h2 {
  font-size: var(--text-xl);
  font-weight: 500;
  margin-bottom: var(--space-sm);
}

.start-here h2 a {
  color: var(--color-text);
  text-decoration: none;
}

.start-here h2 a::before {
  content: "";
  position: absolute;
  inset: 0;
}

.start-here:hover h2 a {
  color: var(--color-accent);
}

.start-here p {
  color: var(--color-text-mid);
  margin-bottom: 0;
}

.start-here__cta {
  display: inline-block;
  margin-top: var(--space-md);
  font-family: var(--font-heading);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-accent);
}

/* ═══════════════════════════════════
   Guide Index — Card Grid
   ═══════════════════════════════════ */
.guide-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-lg);
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-3xl);
}

@media (max-width: 599px) {
  .guide-grid {
    grid-template-columns: 1fr;
  }
}

.guide-card {
  position: relative;
  padding: var(--space-xl);
  background-color: var(--color-bg-alt);
  border: 1px solid transparent;
  transition: border-color var(--transition-fast), background-color var(--transition-fast);
  margin: 0;
}

.guide-card:hover {
  border-color: var(--color-accent);
}

.guide-card h3 {
  font-size: var(--text-lg);
  font-weight: 500;
  margin-bottom: var(--space-sm);
}

.guide-card h3 a {
  color: var(--color-text);
  text-decoration: none;
}

.guide-card h3 a::before {
  content: "";
  position: absolute;
  inset: 0;
}

.guide-card:hover h3 a {
  color: var(--color-accent);
}

.guide-card p {
  color: var(--color-text-mid);
  margin-bottom: var(--space-md);
}

.guide-card__cta {
  display: inline-block;
  font-family: var(--font-heading);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-accent);
}

/* Anchor card — full width, slightly different background */
.guide-card--anchor {
  grid-column: 1 / -1;
  background-color: var(--color-bg);
  border: 1px solid var(--color-rule);
}

.guide-card--anchor h3 {
  font-size: var(--text-xl);
}

/* ═══════════════════════════════════
   Guide Index — Category Section
   ═══════════════════════════════════ */
.guide-category-section {
  margin-block: var(--space-3xl);
}

.guide-category-section:first-of-type {
  margin-top: var(--space-xl);
}

.guide-category-section h2 {
  font-size: var(--text-2xl);
  font-weight: 400;
  margin-bottom: var(--space-md);
}

.guide-category-section .category-rule {
  border: none;
  border-top: 2px solid var(--color-accent);
  width: 3rem;
  margin: 0 0 var(--space-xl) 0;
}

/* Hidden state via JS or no-JS fallback */
.guide-category-section[hidden] {
  display: none;
}
```

- [ ] **Step 2: Verify CSS lints (no syntax errors)**

Run: `npx --yes css-validator-cli css/components.css 2>/dev/null || true`

This is a soft check; if `npx` isn't available, just visually confirm no obviously unmatched braces. The real verification is build.sh succeeding in the next step.

- [ ] **Step 3: Run build.sh to verify the CSS still concatenates and inlines**

Run: `./build.sh`
Expected: succeeds, prints byte count, no errors.

- [ ] **Step 4: Commit**

```bash
git add css/components.css
git commit -m "feat(css): add filter chips, guide cards, start-here card, category sections"
```

---

### Task B2: Restructure `music-guides/index.html` — replace listing markup

This is the largest single edit. We replace the entire `<main>` body and the `<style>`-inlined-listing-section with the new structure.

**Files:**
- Modify: `music-guides/index.html`

- [ ] **Step 1: Read the current file**

Already familiar. The relevant span is `<main id="main">` to `</main>` (currently lines 1517–1687). Also the JSON-LD ItemList in the head.

- [ ] **Step 2: Replace the `<main>` body**

Find the existing block:

```html
<main id="main">

    <section class="section" style="padding-block-end: var(--space-2xl)">
      <div class="prose">
        <nav class="breadcrumb" aria-label="Breadcrumb">
          <ol>
            <li><a href="../index.html">Home</a></li>
            <li>Music Guides</li>
          </ol>
        </nav>
        <h1>Music guides</h1>
…all the way through…
      </div>
    </section>

  </main>
```

Replace it with:

```html
<main id="main">

    <section class="section" style="padding-block-end: var(--space-xl)">
      <div class="prose">
        <nav class="breadcrumb" aria-label="Breadcrumb">
          <ol>
            <li><a href="/">Home</a></li>
            <li>Music Guides</li>
          </ol>
        </nav>
        <h1>Music guides</h1>
        <p class="lede">Honest, practical advice on choosing music for the occasions that matter most&thinsp;&mdash;&thinsp;from the musicians who perform at them every week.</p>
        <hr class="rule">
      </div>
    </section>

    <section class="section" style="padding-block: var(--space-xl)">
      <div class="wide">

        <article class="start-here">
          <span class="start-here__eyebrow">Start here</span>
          <h2><a href="hiring-a-choir.html">What to expect when you hire a choir</a></h2>
          <p>Everything you need to know about booking professional singers for a funeral, wedding, or ceremony&thinsp;&mdash;&thinsp;from first enquiry to the day itself.</p>
          <span class="start-here__cta" aria-hidden="true">Read the overview &rarr;</span>
        </article>

        <div class="filter-bar">
          <span class="filter-bar-label" id="filter-label">Browse by occasion</span>
          <ul class="filter-chips" role="list" aria-labelledby="filter-label">
            <li><a class="filter-chip" href="./" data-category="all" aria-pressed="true">All</a></li>
            <li><a class="filter-chip" href="?category=weddings" data-category="weddings" aria-pressed="false">Weddings</a></li>
            <li><a class="filter-chip" href="?category=funerals" data-category="funerals" aria-pressed="false">Funerals</a></li>
            <li><a class="filter-chip" href="?category=christmas" data-category="christmas" aria-pressed="false">Christmas</a></li>
          </ul>
        </div>

        <section class="guide-category-section" data-category="weddings" aria-labelledby="cat-weddings">
          <h2 id="cat-weddings">Wedding music</h2>
          <hr class="category-rule">
          <ul class="guide-grid">
            <li class="guide-card guide-card--anchor">
              <h3><a href="wedding-ceremony-music.html">A complete guide to wedding ceremony music</a></h3>
              <p>Every musical moment from processional to recessional&thinsp;&mdash;&thinsp;what to choose, when it happens, and how to make it work.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="choosing-wedding-hymns.html">Choosing hymns for your wedding</a></h3>
              <p>How to pick wedding hymns your guests will actually sing, with suggestions for every style of ceremony.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-choir-guide.html">How to hire a choir for your wedding</a></h3>
              <p>Everything you need to know about booking professional singers for your wedding&thinsp;&mdash;&thinsp;ensemble sizes, what they sing, and how to book.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-organist-guide.html">Hiring an organist for your wedding</a></h3>
              <p>How to find and book the right organist, what they play at each point in the ceremony, and what it costs.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-readings-and-music.html">Pairing readings with music at your wedding</a></h3>
              <p>How to coordinate readings and musical selections for emotional flow&thinsp;&mdash;&thinsp;with popular pairings and practical timing advice.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-music-costs.html">How much does wedding music cost?</a></h3>
              <p>What wedding organists, singers, choirs, and instrumentalists actually cost&thinsp;&mdash;&thinsp;a clear breakdown with no hidden fees.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="popular-wedding-organ-music.html">Popular wedding organ music</a></h3>
              <p>A ranked guide to the organ pieces couples book most often&thinsp;&mdash;&thinsp;classical and modern combined, with notes on which one suits which church.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-organ-repertoire.html">The best organ pieces for a wedding</a></h3>
              <p>The organ pieces that make a church wedding unforgettable&thinsp;&mdash;&thinsp;processionals, register-signing music, and triumphant recessionals.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-organ-pop-songs.html">Popular songs on the organ at your wedding</a></h3>
              <p>Pop, film, and musical theatre songs that work on a church organ&thinsp;&mdash;&thinsp;what to choose, what falls flat, and how to brief your organist on a bespoke arrangement.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-pop-songs-choir.html">Pop songs for a wedding choir to sing</a></h3>
              <p>Pop songs arranged for four-part voices for a church wedding&thinsp;&mdash;&thinsp;modern love ballads, classic standards, and practical advice on bespoke choral arrangements.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-choral-repertoire.html">The best choral pieces for a wedding</a></h3>
              <p>The choral anthems, motets, and solo pieces that make a wedding ceremony extraordinary&thinsp;&mdash;&thinsp;from Ave Maria to Ubi Caritas.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="lesser-known-wedding-choral-pieces.html">Lesser-known choral pieces for a wedding</a></h3>
              <p>Beyond Ave Maria&thinsp;&mdash;&thinsp;Renaissance motets, English cathedral anthems, and modern choral works that make a ceremony feel distinctive without feeling obscure.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="wedding-music-ideas.html">How to make your wedding musically unforgettable</a></h3>
              <p>Going beyond the standard formula&thinsp;&mdash;&thinsp;creative ideas for wedding music that will genuinely surprise and move your guests.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="be-thou-my-vision-wedding-hymn.html">Why Be Thou My Vision is the best wedding hymn</a></h3>
              <p>Why this ancient Irish hymn is the finest choice for a wedding&thinsp;&mdash;&thinsp;words that read like a love poem, a melody everyone can sing, and a sound that fills any church.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="jerusalem.html">Jerusalem &mdash; the most British of wedding hymns</a></h3>
              <p>Why Parry&rsquo;s 1916 setting of Blake&rsquo;s poem opens or closes a wedding like nothing else, where to place it, and what it sounds like with brass and a soprano descant.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
          </ul>
        </section>

        <section class="guide-category-section" data-category="funerals" aria-labelledby="cat-funerals">
          <h2 id="cat-funerals">Funeral &amp; memorial music</h2>
          <hr class="category-rule">
          <ul class="guide-grid">
            <li class="guide-card guide-card--anchor">
              <h3><a href="funeral-music-guide.html">How to choose music for a funeral</a></h3>
              <p>A practical, step-by-step guide to selecting hymns, solo pieces, and instrumental music for a funeral service.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="popular-funeral-hymns.html">The most popular funeral hymns</a></h3>
              <p>The hymns families choose most often, what makes each one work, and how to decide which are right for your service.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="funeral-songs.html">The most popular funeral songs</a></h3>
              <p>The non-hymn songs families choose most often, from Time to Say Goodbye to My Way&thinsp;&mdash;&thinsp;with advice on live performance vs recordings.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="crematorium-music.html">Choosing music for a crematorium service</a></h3>
              <p>A practical guide to music at a crematorium funeral&thinsp;&mdash;&thinsp;timing constraints, acoustics, live vs recorded, and making a shorter service feel complete.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="funeral-music-costs.html">How much does funeral music cost?</a></h3>
              <p>A clear breakdown of what funeral singers, choirs, and instrumentalists actually cost&thinsp;&mdash;&thinsp;with no hidden fees.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="celebration-of-life-music.html">Music for a celebration of life</a></h3>
              <p>How music at a celebration of life differs from a traditional funeral, and how to choose pieces that honour someone&rsquo;s personality.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="catholic-funeral-hymns.html">Best hymns for a Catholic funeral</a></h3>
              <p>The hymns and sacred music most often chosen for a Catholic funeral Mass&thinsp;&mdash;&thinsp;what works at each point in the liturgy, and how to choose well.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="non-religious-funeral-music.html">Non-religious funeral music</a></h3>
              <p>A practical guide to choosing music for a non-religious, secular, or humanist funeral&thinsp;&mdash;&thinsp;from popular songs and classical pieces to live performance.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="funeral-choir-guide.html">What to expect from a funeral choir</a></h3>
              <p>Everything you need to know about having a choir at a funeral&thinsp;&mdash;&thinsp;what they do, what they sing, and what difference it makes.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="memorial-service-planning.html">How to plan a memorial service</a></h3>
              <p>A step-by-step guide to planning a memorial service&thinsp;&mdash;&thinsp;from choosing the format and venue to selecting music and readings.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="be-thou-my-vision-funeral-hymn.html">Why Be Thou My Vision is the best funeral hymn</a></h3>
              <p>Why this ancient Irish hymn offers comfort without clich&eacute;&thinsp;&mdash;&thinsp;and sounds extraordinary with a choir at any funeral or memorial service.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="abide-with-me.html">Abide With Me &mdash; the most-requested funeral hymn</a></h3>
              <p>Why Henry Francis Lyte&rsquo;s 1847 hymn moves congregations like nothing else, why William Henry Monk&rsquo;s tune is built for grief, and what it sounds like with a professional choir.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
          </ul>
        </section>

        <section class="guide-category-section" data-category="christmas" aria-labelledby="cat-christmas">
          <h2 id="cat-christmas">Christmas &amp; corporate events</h2>
          <hr class="category-rule">
          <ul class="guide-grid">
            <li class="guide-card guide-card--anchor">
              <h3><a href="corporate-carol-service.html">Planning a corporate carol service</a></h3>
              <p>How to organise a carol service for your company&thinsp;&mdash;&thinsp;venue, choir, carols, readings, and logistics.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="christmas-choir-hire.html">Hiring a choir for your Christmas event</a></h3>
              <p>Carol singers for parties, dinners, and receptions&thinsp;&mdash;&thinsp;what they do, what they sing, and what it costs.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="company-christmas-party-entertainment.html">Live choral music for company Christmas parties</a></h3>
              <p>How live choral music transforms a corporate Christmas celebration&thinsp;&mdash;&thinsp;formats, repertoire, and booking.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="christmas-carols-guide.html">The best Christmas carols for a carol service</a></h3>
              <p>The crowd-pleasers, the hidden gems, and how to build a programme everyone will enjoy.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
            <li class="guide-card">
              <h3><a href="office-carol-service-planning.html">How to organise an office carol service</a></h3>
              <p>A step-by-step planning guide for a workplace carol service&thinsp;&mdash;&thinsp;from venue to running order.</p>
              <span class="guide-card__cta" aria-hidden="true">Read guide &rarr;</span>
            </li>
          </ul>
        </section>

        <p style="margin-top: var(--space-3xl)">When you&rsquo;re ready to discuss music for your occasion, <a href="/contact.html">get in touch</a> or view our <a href="/services.html">services</a> and <a href="/pricing.html">pricing</a>.</p>

        <figure class="pull-quote" style="max-width: 36rem">
          <blockquote>
            <p>&ldquo;I had no idea where to start with the music &mdash; it all felt a bit overwhelming. She talked me through a few options and within ten minutes we had it sorted. Such a weight off my mind.&rdquo;</p>
          </blockquote>
          <figcaption>&mdash;&ensp;Helen, Wimbledon</figcaption>
        </figure>
      </div>
    </section>

  </main>
```

- [ ] **Step 3: Verify the file still parses as HTML**

Run: `python3 -c "import xml.etree.ElementTree as ET; ET.parse('music-guides/index.html')" 2>&1 | head` (HTML isn't strictly XML so this may complain; it's a sanity sniff, not a hard check). Better: load the page in the preview browser (next task).

- [ ] **Step 4: Commit**

```bash
git add music-guides/index.html
git commit -m "feat(music-guides): restructure index into Start Here + filter + card grid"
```

---

### Task B3: Update JSON-LD `ItemList` to all 33 guides

**Files:**
- Modify: `music-guides/index.html` (the `<script type="application/ld+json">` block)

- [ ] **Step 1: Locate the block**

In `music-guides/index.html`, find the `<script type="application/ld+json">` block. The `mainEntity.itemListElement` array has 28 entries.

- [ ] **Step 2: Replace the entire `itemListElement` array**

Replace the existing 28-entry array with this 33-entry array (preserves all existing items and adds the missing five):

```json
"itemListElement": [
  { "@type": "ListItem", "position": 1, "url": "https://londonchoralservice.com/music-guides/funeral-music-guide.html", "name": "How to choose music for a funeral" },
  { "@type": "ListItem", "position": 2, "url": "https://londonchoralservice.com/music-guides/popular-funeral-hymns.html", "name": "The most popular funeral hymns" },
  { "@type": "ListItem", "position": 3, "url": "https://londonchoralservice.com/music-guides/funeral-songs.html", "name": "The most popular funeral songs" },
  { "@type": "ListItem", "position": 4, "url": "https://londonchoralservice.com/music-guides/crematorium-music.html", "name": "Choosing music for a crematorium service" },
  { "@type": "ListItem", "position": 5, "url": "https://londonchoralservice.com/music-guides/funeral-music-costs.html", "name": "How much does funeral music cost?" },
  { "@type": "ListItem", "position": 6, "url": "https://londonchoralservice.com/music-guides/celebration-of-life-music.html", "name": "Music for a celebration of life" },
  { "@type": "ListItem", "position": 7, "url": "https://londonchoralservice.com/music-guides/catholic-funeral-hymns.html", "name": "Best hymns for a Catholic funeral" },
  { "@type": "ListItem", "position": 8, "url": "https://londonchoralservice.com/music-guides/non-religious-funeral-music.html", "name": "Non-religious funeral music" },
  { "@type": "ListItem", "position": 9, "url": "https://londonchoralservice.com/music-guides/funeral-choir-guide.html", "name": "What to expect from a funeral choir" },
  { "@type": "ListItem", "position": 10, "url": "https://londonchoralservice.com/music-guides/memorial-service-planning.html", "name": "How to plan a memorial service" },
  { "@type": "ListItem", "position": 11, "url": "https://londonchoralservice.com/music-guides/be-thou-my-vision-funeral-hymn.html", "name": "Why Be Thou My Vision is the best funeral hymn" },
  { "@type": "ListItem", "position": 12, "url": "https://londonchoralservice.com/music-guides/abide-with-me.html", "name": "Abide With Me — the most-requested funeral hymn" },
  { "@type": "ListItem", "position": 13, "url": "https://londonchoralservice.com/music-guides/wedding-ceremony-music.html", "name": "A complete guide to wedding ceremony music" },
  { "@type": "ListItem", "position": 14, "url": "https://londonchoralservice.com/music-guides/choosing-wedding-hymns.html", "name": "Choosing hymns for your wedding" },
  { "@type": "ListItem", "position": 15, "url": "https://londonchoralservice.com/music-guides/wedding-choir-guide.html", "name": "How to hire a choir for your wedding" },
  { "@type": "ListItem", "position": 16, "url": "https://londonchoralservice.com/music-guides/wedding-organist-guide.html", "name": "Hiring an organist for your wedding" },
  { "@type": "ListItem", "position": 17, "url": "https://londonchoralservice.com/music-guides/wedding-readings-and-music.html", "name": "Pairing readings with music at your wedding" },
  { "@type": "ListItem", "position": 18, "url": "https://londonchoralservice.com/music-guides/wedding-music-costs.html", "name": "How much does wedding music cost?" },
  { "@type": "ListItem", "position": 19, "url": "https://londonchoralservice.com/music-guides/popular-wedding-organ-music.html", "name": "Popular wedding organ music" },
  { "@type": "ListItem", "position": 20, "url": "https://londonchoralservice.com/music-guides/wedding-organ-repertoire.html", "name": "The best organ pieces for a wedding" },
  { "@type": "ListItem", "position": 21, "url": "https://londonchoralservice.com/music-guides/wedding-organ-pop-songs.html", "name": "Popular songs on the organ at your wedding" },
  { "@type": "ListItem", "position": 22, "url": "https://londonchoralservice.com/music-guides/wedding-pop-songs-choir.html", "name": "Pop songs for a wedding choir to sing" },
  { "@type": "ListItem", "position": 23, "url": "https://londonchoralservice.com/music-guides/wedding-choral-repertoire.html", "name": "The best choral pieces for a wedding" },
  { "@type": "ListItem", "position": 24, "url": "https://londonchoralservice.com/music-guides/lesser-known-wedding-choral-pieces.html", "name": "Lesser-known choral pieces for a wedding" },
  { "@type": "ListItem", "position": 25, "url": "https://londonchoralservice.com/music-guides/wedding-music-ideas.html", "name": "How to make your wedding musically unforgettable" },
  { "@type": "ListItem", "position": 26, "url": "https://londonchoralservice.com/music-guides/be-thou-my-vision-wedding-hymn.html", "name": "Why Be Thou My Vision is the best wedding hymn" },
  { "@type": "ListItem", "position": 27, "url": "https://londonchoralservice.com/music-guides/jerusalem.html", "name": "Jerusalem — the most British of wedding hymns" },
  { "@type": "ListItem", "position": 28, "url": "https://londonchoralservice.com/music-guides/corporate-carol-service.html", "name": "Planning a corporate carol service" },
  { "@type": "ListItem", "position": 29, "url": "https://londonchoralservice.com/music-guides/christmas-choir-hire.html", "name": "Hiring a choir for your Christmas event" },
  { "@type": "ListItem", "position": 30, "url": "https://londonchoralservice.com/music-guides/company-christmas-party-entertainment.html", "name": "Live choral music for company Christmas parties" },
  { "@type": "ListItem", "position": 31, "url": "https://londonchoralservice.com/music-guides/christmas-carols-guide.html", "name": "The best Christmas carols for a carol service" },
  { "@type": "ListItem", "position": 32, "url": "https://londonchoralservice.com/music-guides/office-carol-service-planning.html", "name": "How to organise an office carol service" },
  { "@type": "ListItem", "position": 33, "url": "https://londonchoralservice.com/music-guides/hiring-a-choir.html", "name": "What to expect when you hire a choir" }
]
```

- [ ] **Step 3: Run the JSON-LD validator**

Run: `python3 validate_jsonld.py`
Expected: passes with no errors. If it complains, the most likely issue is a stray comma or unescaped Unicode em-dash — fix and re-run.

- [ ] **Step 4: Commit**

```bash
git add music-guides/index.html
git commit -m "feat(seo): list all 33 guides in JSON-LD ItemList"
```

---

### Task B4: Create `js/music-guides.js` (filter logic)

**Files:**
- Create: `js/music-guides.js`

- [ ] **Step 1: Write the filter script**

```javascript
(function () {
  'use strict';

  var VALID = ['weddings', 'funerals', 'christmas'];

  function getCategoryFromURL() {
    var params = new URLSearchParams(window.location.search);
    var cat = params.get('category');
    if (cat && VALID.indexOf(cat) !== -1) return cat;
    return 'all';
  }

  function applyFilter(category) {
    var sections = document.querySelectorAll('.guide-category-section[data-category]');
    sections.forEach(function (section) {
      var sectionCat = section.getAttribute('data-category');
      if (category === 'all' || sectionCat === category) {
        section.removeAttribute('hidden');
      } else {
        section.setAttribute('hidden', '');
      }
    });

    var chips = document.querySelectorAll('.filter-chip[data-category]');
    chips.forEach(function (chip) {
      var chipCat = chip.getAttribute('data-category');
      chip.setAttribute('aria-pressed', chipCat === category ? 'true' : 'false');
    });
  }

  function onChipClick(e) {
    e.preventDefault();
    var chip = e.currentTarget;
    var category = chip.getAttribute('data-category');
    var newURL;
    if (category === 'all') {
      newURL = window.location.pathname;
    } else {
      newURL = window.location.pathname + '?category=' + category;
    }
    history.pushState({ category: category }, '', newURL);
    applyFilter(category);
  }

  function onPopState() {
    applyFilter(getCategoryFromURL());
  }

  function init() {
    var chips = document.querySelectorAll('.filter-chip[data-category]');
    if (chips.length === 0) return;
    chips.forEach(function (chip) {
      chip.addEventListener('click', onChipClick);
    });
    window.addEventListener('popstate', onPopState);
    applyFilter(getCategoryFromURL());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
```

- [ ] **Step 2: Verify the file is valid JavaScript**

Run: `node --check js/music-guides.js`
Expected: no output (syntax OK). If `node` isn't installed, run: `python3 -c "import re; open('js/music-guides.js').read(); print('readable')"` (weak check).

- [ ] **Step 3: Wire the script into `music-guides/index.html`**

Locate the line `<script src="../js/nav.js" defer></script>` near the end of `music-guides/index.html`. Add a sibling line right after it:

```html
  <script src="../js/music-guides.js" defer></script>
```

- [ ] **Step 4: Run build.sh**

Run: `./build.sh`
Expected: succeeds.

- [ ] **Step 5: Commit**

```bash
git add js/music-guides.js music-guides/index.html
git commit -m "feat(music-guides): client-side filter for category chips"
```

---

### Task B5: Verify the redesigned index in the preview

**Files:**
- (no edits — verification only)

- [ ] **Step 1: Start the preview server**

Use `preview_start` (the static-site preview tool).

- [ ] **Step 2: Navigate to `/music-guides/`**

Take a screenshot at desktop width (1280px). Verify visually:
- H1 "Music guides" + lede at top
- "Start Here" card with the hire-a-choir overview, accent rule on the left
- "Browse by occasion" label + 4 filter chips ("All" pressed)
- Three category sections in order: Wedding music, Funeral & memorial music, Christmas & corporate events
- Each category has an anchor card spanning full width, then 2-column grid of regular cards
- Pull-quote and footer at bottom

- [ ] **Step 3: Click "Weddings" chip — verify filter**

After click, verify:
- URL is `/music-guides/?category=weddings`
- Only Wedding music section is visible
- "Weddings" chip is highlighted; others are not
- Browser back button returns to "All" view

- [ ] **Step 4: Repeat for Funerals and Christmas**

Same expectations. Verify each chip filters correctly.

- [ ] **Step 5: Test deep link**

Navigate directly to `/music-guides/?category=funerals` (fresh load). Verify:
- Only Funerals section visible from the start
- "Funerals" chip is pressed

- [ ] **Step 6: Test no-JS fallback**

In the preview tools, disable JavaScript (or `preview_eval` to set window-level flag, or simulate by removing the script src). Reload `/music-guides/?category=weddings`. Verify:
- All sections still visible (no JS to hide them) — this is acceptable since the visitor sees more, not less
- Clicking a filter chip performs a full-page navigation to the filtered URL

- [ ] **Step 7: Test mobile width**

Use `preview_resize` to 375×667 (iPhone SE). Verify:
- Card grid collapses to 1 column
- Filter chips wrap if needed
- "Start Here" card still readable

- [ ] **Step 8: Test the hidden no-JS fallback for filter URLs**

We need server-side filtering to support `/music-guides/?category=…` properly without JS. But this is a static site — the URL parameter is invisible to the server. Without JS, all categories show regardless of URL. **This is acceptable per the spec's progressive-enhancement stance.** Verify the doc captures this and move on.

- [ ] **Step 9: No commit (verification only)**

If anything was visibly broken in steps 2–7, fix it before continuing. Otherwise move to Stage C.

---

## Stage C — Nav dropdown

End state: every page's nav has a "Music Guides ▾" dropdown with 4 sub-items linking to filtered/unfiltered index URLs. Desktop opens on hover/focus; mobile expands inline within the hamburger panel. ESC closes; arrow-keys traverse; `aria-current="page"` is set dynamically.

### Task C1: Update `partials/nav.html` with dropdown markup

**Files:**
- Modify: `partials/nav.html`

- [ ] **Step 1: Replace the entire file**

Replace the current contents of `partials/nav.html` with:

```html
  <header class="site-header">
    <nav class="site-nav page-wrap" aria-label="Main navigation">
      <a href="/" class="site-name">The London Choral Service</a>
      <button class="nav-toggle" aria-expanded="false" aria-controls="nav-menu" aria-label="Menu">
        <span class="nav-toggle-bar"></span>
      </button>
      <ul id="nav-menu" class="nav-links" role="list">
        <li><a href="/">Home</a></li>
        <li><a href="/about.html">About</a></li>
        <li><a href="/services.html">Services</a></li>
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

- [ ] **Step 2: Run build.sh to propagate**

Run: `./build.sh`
Expected: succeeds; "Populated partials in 102 HTML files".

- [ ] **Step 3: Spot-check one page**

Run: `grep -A 3 'has-dropdown' index.html | head -10`
Expected: shows the dropdown markup populated in the built file.

---

### Task C2: Add dropdown CSS

**Files:**
- Modify: `css/components.css`

- [ ] **Step 1: Append to `css/components.css`**

At the end of `css/components.css`, append:

```css
/* ═══════════════════════════════════
   Nav Dropdown (Music Guides)
   ═══════════════════════════════════ */
.has-dropdown {
  position: relative;
}

.dropdown-caret {
  display: inline-block;
  margin-left: 0.25em;
  font-size: 0.75em;
  transition: transform var(--transition-fast);
}

.dropdown-menu {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 12rem;
  list-style: none;
  padding: var(--space-sm) 0;
  margin: 0;
  background-color: var(--color-bg);
  border: 1px solid var(--color-rule);
  z-index: 150;
}

.dropdown-menu li {
  margin: 0;
}

.dropdown-menu a {
  display: block;
  padding: var(--space-sm) var(--space-lg);
  font-family: var(--font-heading);
  font-size: var(--text-sm);
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text);
  text-decoration: none;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.dropdown-menu a:hover,
.dropdown-menu a:focus-visible {
  background-color: var(--color-bg-alt);
  color: var(--color-accent);
  outline: none;
}

.dropdown-separator {
  height: 1px;
  background-color: var(--color-rule);
  margin: var(--space-sm) var(--space-md);
}

/* Open on hover / keyboard focus / explicit aria-expanded */
.has-dropdown:hover > .dropdown-menu,
.has-dropdown:focus-within > .dropdown-menu,
.has-dropdown[data-open="true"] > .dropdown-menu {
  display: block;
}

.has-dropdown:hover > .dropdown-trigger .dropdown-caret,
.has-dropdown:focus-within > .dropdown-trigger .dropdown-caret,
.has-dropdown[data-open="true"] > .dropdown-trigger .dropdown-caret {
  transform: rotate(180deg);
}

/* Mobile: dropdown becomes an inline expandable block inside the hamburger */
@media (max-width: 767px) {
  .dropdown-menu {
    display: none;
    position: static;
    border: none;
    border-top: 1px solid var(--color-rule);
    padding: 0;
    background: transparent;
  }

  .has-dropdown[data-open="true"] > .dropdown-menu {
    display: block;
  }

  /* Disable hover-open on touch devices — only the explicit toggle opens it */
  .has-dropdown:hover > .dropdown-menu,
  .has-dropdown:focus-within > .dropdown-menu {
    display: none;
  }

  .has-dropdown[data-open="true"] > .dropdown-menu {
    display: block;
  }

  .dropdown-menu a {
    padding-left: var(--space-2xl);
    text-transform: none;
    font-size: var(--text-base);
    border-bottom: 1px solid var(--color-rule);
  }

  .dropdown-menu li:last-child a {
    border-bottom: none;
  }

  .dropdown-separator {
    display: none;
  }
}
```

- [ ] **Step 2: Run build.sh**

Run: `./build.sh`
Expected: succeeds.

- [ ] **Step 3: Commit**

```bash
git add partials/nav.html css/components.css
git commit -m "feat(nav): add Music Guides dropdown to global nav"
```

---

### Task C3: Extend `js/nav.js` — mobile dropdown + ESC + aria-current

**Files:**
- Modify: `js/nav.js`

- [ ] **Step 1: Replace the contents of `js/nav.js`**

Replace the entire file with:

```javascript
(function () {
  'use strict';

  // ── Hamburger toggle ──
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.getElementById('nav-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      menu.classList.toggle('is-open');
    });
  }

  // ── Dropdown (Music Guides) ──
  var dropdownItems = document.querySelectorAll('.has-dropdown');
  dropdownItems.forEach(function (item) {
    var trigger = item.querySelector('.dropdown-trigger');
    if (!trigger) return;

    function setOpen(open) {
      item.setAttribute('data-open', open ? 'true' : 'false');
      trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    // Mobile: tap on the caret area expands inline; tapping the link
    // navigates as normal. We treat any tap on a touch device that
    // hits the trigger AND the menu is currently closed as "open
    // first, navigate next time".
    trigger.addEventListener('click', function (e) {
      var isMobile = window.matchMedia('(max-width: 767px)').matches;
      if (!isMobile) return; // desktop: hover handles it
      var isOpen = item.getAttribute('data-open') === 'true';
      if (!isOpen) {
        e.preventDefault();
        setOpen(true);
      }
      // If already open, the click navigates to the trigger's href.
    });

    // Keyboard: ESC closes the dropdown and returns focus to the trigger.
    item.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        setOpen(false);
        trigger.focus();
      }
    });

    // Close on click outside (desktop convenience).
    document.addEventListener('click', function (e) {
      if (!item.contains(e.target)) {
        setOpen(false);
      }
    });
  });

  // ── aria-current on the matching nav link ──
  // Set aria-current="page" on the nav link whose href matches
  // the current document path. Handles "/" matching index.html.
  (function setAriaCurrent() {
    var navLinks = document.querySelectorAll('#nav-menu > li > a');
    var here = window.location.pathname.replace(/\/index\.html$/, '/');
    navLinks.forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href || href.indexOf('://') !== -1) return;
      var linkPath = href.replace(/\/index\.html$/, '/');
      if (linkPath === here || (linkPath !== '/' && here.indexOf(linkPath) === 0)) {
        link.setAttribute('aria-current', 'page');
      }
    });
  })();

  // ── Year stamp ──
  var yearEl = document.querySelector('[data-year]');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // ── Mobile CTA: hide when footer is on-screen ──
  var cta = document.querySelector('.mobile-cta');
  var footer = document.querySelector('.site-footer');
  if (cta && footer) {
    var footerObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          cta.classList.add('is-hidden');
        } else {
          cta.classList.remove('is-hidden');
        }
      });
    }, { threshold: 0 });
    footerObserver.observe(footer);
  }

  // ── Conversion tracking: redirect to thank-you after tel:/mailto: clicks ──
  if (!/thank-you\.html/.test(window.location.pathname)) {
    var thankYouBase = '/thank-you.html';

    var isMobile = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (isMobile) {
      var telLinks = document.querySelectorAll('a[href^="tel:"]');
      for (var i = 0; i < telLinks.length; i++) {
        telLinks[i].addEventListener('click', function () {
          setTimeout(function () {
            window.location.href = thankYouBase + '?from=call';
          }, 300);
        });
      }
    }

    var mailLinks = document.querySelectorAll('a[href^="mailto:"]');
    for (var j = 0; j < mailLinks.length; j++) {
      mailLinks[j].addEventListener('click', function () {
        setTimeout(function () {
          window.location.href = thankYouBase + '?from=email';
        }, 300);
      });
    }
  }
})();
```

The key changes from the previous nav.js:
- Added dropdown handling (tap-to-open on mobile, ESC closes, click-outside closes).
- Added `setAriaCurrent` IIFE at top of the file's main flow — sets `aria-current="page"` on the matching nav link based on the current path. Replaces the per-page `aria-current` attribute that was previously hand-coded into the nav.
- Simplified `thankYouBase` to `/thank-you.html` (absolute root path) — this works because all paths in the site are now absolute.

- [ ] **Step 2: Verify JS syntax**

Run: `node --check js/nav.js`
Expected: no output.

- [ ] **Step 3: Run build.sh**

Run: `./build.sh`
Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
git add js/nav.js
git commit -m "feat(nav): mobile dropdown + ESC + dynamic aria-current; absolute thank-you path"
```

---

### Task C4: Verify the dropdown across page types

**Files:**
- (no edits — verification only)

- [ ] **Step 1: Start preview, open `/`**

Verify in the preview:
- "Music Guides ▾" appears in the nav with a small caret
- Hovering the item opens the dropdown with the four sub-items
- Caret rotates 180° on hover
- Clicking "Weddings" navigates to `/music-guides/?category=weddings`
- The "Music Guides" link itself (when clicked) navigates to `/music-guides/`

- [ ] **Step 2: Test on `/music-guides/`**

The dropdown should still work. Additionally, the nav's "Music Guides" link should display with `aria-current="page"` (verify via DevTools or `preview_inspect`).

- [ ] **Step 3: Test on `/areas/london/camden.html`** (deepest path)

Dropdown should still work; absolute URLs resolve correctly; `aria-current` should NOT be set on Music Guides for this page.

- [ ] **Step 4: Keyboard navigation**

- Tab into the nav. Focusing on the "Music Guides" link should open the dropdown (via `:focus-within`).
- Tab into the dropdown. ESC should close it and return focus to the "Music Guides" trigger.
- Shift+Tab back out of the dropdown closes it.

- [ ] **Step 5: Mobile behaviour (375px width)**

- Open hamburger.
- Tap "Music Guides" → it should expand inline, showing the four sub-items.
- Tap a sub-item → it navigates as normal.
- Tap "Music Guides" again with the menu open → it should navigate to `/music-guides/` (since it's already open).

- [ ] **Step 6: Run JSON-LD validation again**

Run: `python3 validate_jsonld.py`
Expected: passes.

- [ ] **Step 7: No commit (verification only)**

If anything failed in steps 1–6, fix and re-verify. Otherwise proceed to Stage D.

---

## Stage D — Internal-link updates

End state: a "Browse all wedding guides →" / "Browse all funeral guides →" CTA appears at the end of the existing music-guides section on `/weddings.html` and `/funerals.html`, and the link lands users directly on the filtered index.

Note: after Stage A, the only `music-guides/` link in each source file's nav block lives inside the `@include-start partials/nav.html` block — that block is regenerated from the partial on every build, so we don't edit it. We add a new in-content CTA after the existing list of specific-guide links.

### Task D1: Locate the existing music-guides section on each page

**Files:**
- (read-only investigation)

- [ ] **Step 1: Find the music-guides section in `weddings.html`**

Run: `grep -n 'music-guides/' weddings.html | grep -v 'partials/nav'`
Expected: a list of line numbers — the specific guide links in the in-content section. Note the LAST line number (the file's last in-content `music-guides/` link).

- [ ] **Step 2: Read 5 lines around that last reference to understand the surrounding HTML**

Run: `awk 'NR>='"$LAST_LINE - 2"' && NR<='"$LAST_LINE + 5"'' weddings.html` (replace `$LAST_LINE` with the actual line number).

You're looking for the closing tag of the link list (likely `</div>` or `</ul>`). The "Browse all" CTA goes immediately before that closing tag.

- [ ] **Step 3: Same for `funerals.html`**

Run: `grep -n 'music-guides/' funerals.html | grep -v 'partials/nav'`
Note the last line and inspect the closing tag.

- [ ] **Step 4: No commit (investigation only)**

You now know exactly where to insert the CTA in each file. Move to D2.

---

### Task D2: Add "Browse all wedding guides" CTA to `weddings.html`

**Files:**
- Modify: `weddings.html`

- [ ] **Step 1: Insert the CTA**

Immediately after the LAST in-content `music-guides/` link found in D1 (and inside the same containing element), insert this on its own line, indented to match the surrounding markup:

```html
          <a href="music-guides/?category=weddings" class="btn-link" style="margin-top: var(--space-lg)">Browse all wedding guides &rarr;</a>
```

Use the existing `.btn-link` class so the styling matches existing CTAs on the page. The inline `margin-top` matches the spacing rhythm used in adjacent CTAs.

If the surrounding container is a `<div>` of inline links (as opposed to a `<ul>` list of links), a plain inline anchor is fine — drop the `class="btn-link"` if a button-style CTA looks visually heavy in context. Use editorial judgement at this step: the goal is "obvious next step", not "loud button".

- [ ] **Step 2: Run build.sh**

Run: `./build.sh`
Expected: succeeds.

- [ ] **Step 3: Verify in preview**

Visit `/weddings.html`. Scroll to the music-guides section. Verify:
- The "Browse all wedding guides →" CTA appears at the end of the section.
- Clicking it lands on `/music-guides/?category=weddings` with the Weddings filter active.

- [ ] **Step 4: Commit**

```bash
git add weddings.html
git commit -m "feat(weddings): add Browse all wedding guides CTA to filtered index"
```

---

### Task D3: Add "Browse all funeral guides" CTA to `funerals.html`

**Files:**
- Modify: `funerals.html`

- [ ] **Step 1: Insert the CTA**

Immediately after the last in-content `music-guides/` link in `funerals.html` (and inside the same containing element), insert this on its own line, indented to match the surrounding markup:

```html
          <a href="music-guides/?category=funerals" class="btn-link" style="margin-top: var(--space-lg)">Browse all funeral guides &rarr;</a>
```

If the surrounding container is a `<div>` of inline links (as opposed to a `<ul>` list of links), a plain inline anchor is fine — drop the `class="btn-link"` if a button-style CTA looks visually heavy in context. The goal is "obvious next step", not "loud button".

- [ ] **Step 2: Run build.sh**

Run: `./build.sh`
Expected: succeeds.

- [ ] **Step 3: Verify in preview**

Visit `/funerals.html`. Scroll to the music-guides section. Click the new CTA. Verify it lands on `/music-guides/?category=funerals` with the Funerals filter active.

- [ ] **Step 4: Commit**

```bash
git add funerals.html
git commit -m "feat(funerals): add Browse all funeral guides CTA to filtered index"
```

---

## Stage E — Final verification

End state: the full site is clean, build is repeatable, JSON-LD validates, every page renders correctly.

### Task E1: Full-site sanity sweep

- [ ] **Step 1: Run `./build.sh` from a clean state**

Run: `./build.sh`
Expected: full success.

- [ ] **Step 2: Run JSON-LD validation across the site**

Run: `python3 validate_jsonld.py`
Expected: passes.

- [ ] **Step 3: Spot-check pages in the preview**

Visit each of:
- `/`
- `/weddings.html`
- `/funerals.html`
- `/music-guides/` (no filter)
- `/music-guides/?category=weddings`
- `/music-guides/?category=funerals`
- `/music-guides/?category=christmas`
- `/music-guides/funeral-music-guide.html` (a representative individual guide)
- `/areas/london.html`
- `/areas/london/camden.html`

For each, verify:
- Nav renders with the dropdown
- Footer renders with full areas list
- Mobile CTA present at narrow widths
- No broken images, no console errors (`preview_console_logs`)

- [ ] **Step 4: Final commit if any minor fixes were applied during the sweep**

```bash
git status
```
If clean, no commit needed. If anything was tweaked, commit with a descriptive message.

---

## Done

The redesign is complete. Summary of what shipped:

- A reusable `partials/` system in `build.sh` for nav and footer.
- A redesigned `/music-guides/` index with Start Here card, filter chips, card grid, and `?category=` deep-linking.
- A "Music Guides ▾" dropdown across the entire global nav, on every page.
- Absolute URLs throughout the nav and footer (a side effect of the partials work that simplifies future maintenance).
- All 33 guide files reconciled into both the visible index and the JSON-LD `ItemList`.
- `/weddings.html` and `/funerals.html` link directly to their filtered views.

If you'd like to iterate on the visual treatment afterwards, the cleanest next steps are:
- Anchor-card visual variations.
- Optional category icons on the chips.
- A11y audit with a real screen reader.
