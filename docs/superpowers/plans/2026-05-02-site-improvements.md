# Site Improvements — Implementation Plan

> **For agentic workers:** Use @anthropic-skills:stop-slop for ALL copy written in this plan. Use @anthropic-skills:seo-audit principles when validating schema changes. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the site's content footprint, fix outstanding gaps from prior work, improve conversion copy, and add technical polish — all through autonomous code changes.

**Architecture:** Static HTML site with 93+ hand-crafted pages. CSS is concatenated from 5 source files and inlined via `build.sh`. No templating engine. All changes are direct HTML edits. JSON-LD structured data uses `@graph` arrays. Content follows stop-slop writing principles.

**Tech Stack:** Static HTML, CSS custom properties (design tokens), vanilla JS, Web3Forms, hCaptcha, Google Analytics 4, GitHub Pages

**Prior work:** The SEO & Lead Conversion plan (`docs/superpowers/plans/2026-03-28-seo-and-conversion-improvements.md`) is fully implemented. All 12 tasks (AggregateRating propagation, visible FAQs, breadcrumbs, content enrichment, testimonials, internal linking, contact refinements) have been committed and merged to main.

---

## Important Context for Implementers

### What Already Exists (Don't Duplicate)

Read before changing:

- **All pages:** AggregateRating schema (5 stars, 4 reviews), visible breadcrumbs, internal links, meta tags, OG tags, canonical URLs — EXCEPT `christmas.html` which is missing AggregateRating (bug from Task 1)
- **Music guides** (`music-guides/*.html`): Article + FAQPage + BreadcrumbList schema, visible FAQ sections, testimonials on priority guides, cross-links to area pages and landing pages
- **Area pages** (`areas/**/*.html`): Service + FAQPage + BreadcrumbList schema, visible FAQs, testimonials, cross-links
- **Landing pages** (`weddings.html`, `funerals.html`, `christmas.html`): Service + BreadcrumbList schema, contact forms with Web3Forms, conversion tracking, how-it-works steps, testimonials, video embeds, track listings
- **Core pages:** Enriched content, testimonials, visible FAQs (pricing, services), breadcrumbs, internal links

### HTML Patterns to Follow

All content uses these wrappers:
```html
<section class="section">
  <div class="prose">
    <!-- content here -->
  </div>
</section>
```

Testimonials use:
```html
<figure class="pull-quote">
  <blockquote><p>"Quote text"</p></blockquote>
  <figcaption>&mdash;&ensp;Name, Location</figcaption>
</figure>
```

CTAs use:
```html
<p><a href="contact.html" class="btn-link">CTA text</a></p>
<p class="text-sm text-mid">Or call us on <a href="tel:+447356042468">07356 042468</a>.</p>
```

Breadcrumbs use:
```html
<nav class="breadcrumb" aria-label="Breadcrumb">
  <ol>
    <li><a href="index.html">Home</a></li>
    <li>Current Page</li>
  </ol>
</nav>
```

FAQs use:
```html
<h2>Frequently asked questions</h2>
<h3>Question text?</h3>
<p>Answer text.</p>
```

Video embeds use (lazy-load YouTube thumbnail):
```html
<div class="video-embed">
  <button class="video-thumb" aria-label="Play [piece name]" data-video="[YOUTUBE_ID]">
    <img src="https://img.youtube.com/vi/[YOUTUBE_ID]/maxresdefault.jpg"
         alt="[Piece Name] — The London Choral Service" loading="lazy">
    <svg class="play-btn" viewBox="0 0 68 48" aria-hidden="true">
      <path d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55c-2.93.78-4.63 3.26-5.42 6.19C.06 13.05 0 24 0 24s.06 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.63-3.26 5.42-6.19C67.94 34.95 68 24 68 24s-.06-10.95-1.48-16.26z" fill="rgba(0,0,0,.7)"/>
      <path d="M45 24 27 14v20z" fill="#fff"/>
    </svg>
  </button>
</div>
```

### Navigation links (relative paths vary by depth)

Root pages use:
```html
<a href="index.html">Home</a>
<a href="contact.html">Contact</a>
<a href="music-guides/">Music Guides</a>
```

Pages in `music-guides/` use:
```html
<a href="../index.html">Home</a>
<a href="../contact.html">Contact</a>
```

Pages in `areas/london/` use:
```html
<a href="../../index.html">Home</a>
<a href="../../contact.html">Contact</a>
```

### Content Writing Rules

All new or revised copy MUST follow stop-slop rules:
- No filler phrases, no throat-clearing openers
- Active voice — every sentence has a human subject doing something
- No adverbs
- Specific details over vague claims
- Vary sentence length; two items beat three
- No em dashes (use full stops or restructure)
- No inanimate objects performing human actions
- Trust readers — state facts directly, skip softening

### Build & Validation

After editing HTML or CSS files, run:
```bash
./build.sh
```

Validate JSON-LD:
```bash
for f in $(find . -name '*.html' -not -path '*/.git/*'); do
  if grep -q 'application/ld+json' "$f"; then
    python3 -c "
import re, json, sys
with open('$f') as fh:
    html = fh.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    try:
        json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f'INVALID: $f - {e}')
        sys.exit(1)
" || echo "FAILED: $f"
  fi
done
echo "All JSON-LD valid"
```

---

## Task 1: Fix christmas.html Missing AggregateRating Schema

**Problem:** `christmas.html` was created on 2026-04-11, after the AggregateRating propagation commit (2026-03-28). It has Service and BreadcrumbList schema but no LocalBusiness node with aggregateRating.

**File:** `christmas.html`

- [ ] **Step 1: Add LocalBusiness node with AggregateRating to the `@graph` array**

Read the existing JSON-LD in `christmas.html` (around lines 1299-1330). Add a LocalBusiness node matching the pattern from `weddings.html` line 1320:

```json
{
  "@type": "LocalBusiness",
  "@id": "https://londonchoralservice.com/#organization",
  "name": "The London Choral Service",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "5",
    "reviewCount": "4",
    "bestRating": "5"
  }
}
```

- [ ] **Step 2: Validate JSON-LD and commit**

```bash
./build.sh
git add christmas.html
git commit -m "fix(seo): add missing aggregateRating schema to christmas landing page"
```

---

## Task 2: Create Funeral Director Resource Page

**What:** New B2B page at `/for-funeral-directors.html` speaking directly to funeral directors: how to recommend LCS to families, coordination process, timelines, last-minute bookings, referral contact method.

**Why:** One FD who trusts the service sends 20-50 funerals per year. The site speaks only to end consumers. No page addresses the intermediary who refers most bookings.

**File to create:** `for-funeral-directors.html`

- [ ] **Step 1: Create the page**

Model on `funerals.html` for structure (hero section, content sections, CTA). Use root-level relative paths for nav links (`index.html`, `contact.html`, etc.).

Page structure:
1. Hero section: h1 "For funeral directors", lede explaining how LCS partners with FDs
2. Section: "How we work with funeral directors" — process from referral to performance day, timelines, last-minute capability (48 hours)
3. Section: "What families receive" — brief description of the music consultation, ensemble options, on-the-day coordination
4. Section: "Logistics we handle" — arrival times, venue coordination, working with clergy/officiants, repertoire planning
5. Pull-quote: testimonial from a family or FD
6. Section: FAQ (3-4 questions FDs would ask: pricing, availability, last-minute bookings, geographic coverage)
7. CTA section: "Refer a family" with contact link and phone number

Target: 600-800 words. Stop-slop rules apply throughout.

JSON-LD schema: Service type + BreadcrumbList + LocalBusiness with AggregateRating. Follow the `funerals.html` schema pattern.

Meta tags: title "For Funeral Directors — London Choral Service", description targeting FDs recommending professional musicians.

- [ ] **Step 2: Add to sitemap**

Add entry to `sitemap.xml`:
```xml
<url>
  <loc>https://londonchoralservice.com/for-funeral-directors.html</loc>
  <lastmod>2026-05-02</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.7</priority>
</url>
```

- [ ] **Step 3: Add to llms.txt**

Add the page description to `llms.txt`.

- [ ] **Step 4: Build, validate, and commit**

```bash
./build.sh
git add for-funeral-directors.html sitemap.xml llms.txt
git commit -m "feat: add funeral director resource page for B2B referrals"
```

---

## Task 3: Create Wedding Planner Resource Page

**What:** New B2B page at `/for-wedding-planners.html` — how far ahead to book, what musicians need from the venue, coordination process, credentials.

**Why:** Wedding planners recommend musicians for every wedding they plan. Same B2B logic as the FD page, extended to the wedding vertical.

**File to create:** `for-wedding-planners.html`

- [ ] **Step 1: Create the page**

Model on `weddings.html` for structure. Use root-level relative paths.

Page structure:
1. Hero: h1 "For wedding planners and venue coordinators", lede about partnering with planners
2. Section: "How we work with planners" — process from initial enquiry to performance day, booking timelines (3-6 months recommended, shorter possible)
3. Section: "What your couples receive" — music consultation, repertoire suggestions with recordings, custom arrangements, running order
4. Section: "On the day" — arrival, setup, coordination with planner/venue manager, technical requirements (power, space)
5. Pull-quote: wedding testimonial
6. Section: FAQ (3-4 questions: pricing, repertoire flexibility, outdoor events, instruments available)
7. CTA with contact link and phone

Target: 600-800 words. Stop-slop rules.

JSON-LD: Service + BreadcrumbList + LocalBusiness with AggregateRating.

- [ ] **Step 2: Add to sitemap and llms.txt**
- [ ] **Step 3: Build, validate, and commit**

```bash
./build.sh
git add for-wedding-planners.html sitemap.xml llms.txt
git commit -m "feat: add wedding planner resource page for B2B referrals"
```

---

## Task 4: Create Corporate Events Page

**What:** Year-round corporate page at `/corporate.html` covering awards dinners, product launches, charity galas, conferences — not just Christmas.

**Why:** The christmas.html landing page targets seasonal demand, but no page captures year-round corporate queries like "choir hire for corporate event" or "live music for awards dinner."

**File to create:** `corporate.html`

- [ ] **Step 1: Create the page**

Model on `christmas.html` for structure (hero, how-it-works steps, content, form). Include a contact form using `js/landing-form.js` with `data-redirect="thank-you.html?from=corporate"`.

Page structure:
1. Hero: h1 "Live music for corporate events", lede covering the range of corporate occasions
2. How it works: 3-step process (same pattern as other landing pages)
3. Section: "Events we perform at" — awards dinners, product launches, charity galas, conferences, summer parties, client entertainment
4. Section: "What we provide" — ensemble options (quartet to full chorus), repertoire range (classical to popular arrangements), technical requirements, sound checks
5. Pull-quote: testimonial (can reuse or adapt from existing)
6. Section: Pricing summary linking to pricing page
7. Section: FAQ (3-4 questions about corporate bookings)
8. Contact form

JSON-LD: Service type (for corporate events) + BreadcrumbList + LocalBusiness with AggregateRating.

Add conversion tracking: update `thank-you.html` to handle `?from=corporate` parameter with appropriate messaging.

- [ ] **Step 2: Add to sitemap, llms.txt, and nav where appropriate**

Add cross-link from `services.html` corporate section.

- [ ] **Step 3: Build, validate, and commit**

```bash
./build.sh
git add corporate.html thank-you.html services.html sitemap.xml llms.txt
git commit -m "feat: add year-round corporate events landing page"
```

---

## Task 5: Create Individual Hymn Pages — Batch 1 (5 pages)

**What:** Standalone pages for the 5 most-searched hymns, following the pattern established by `music-guides/be-thou-my-vision-funeral-hymn.html`.

**Why:** High-volume exact-match queries ("Abide with Me funeral", "Ave Maria wedding") with almost no SERP competition from ceremony music providers. The two Be Thou My Vision pages prove this pattern ranks.

**Template file:** `music-guides/be-thou-my-vision-funeral-hymn.html` — use this as the structural template for all new hymn pages.

**Pages to create:**
1. `music-guides/abide-with-me.html` — funeral focus (YouTube ID: `G9-R6k5n7Io`)
2. `music-guides/ave-maria.html` — both funeral and wedding (no YouTube video yet)
3. `music-guides/the-lords-my-shepherd.html` — funeral focus (no YouTube video)
4. `music-guides/amazing-grace.html` — funeral/celebration of life (no YouTube video)
5. `music-guides/jerusalem.html` — wedding/memorial/national occasions (no YouTube video)

These are the 5 most frequently mentioned pieces across the music guides and the Listen page (`listen.html` lines 1398-1474).

- [ ] **Step 1: Create each page**

For each hymn page, follow this structure (from Be Thou My Vision template):
1. `<article>` wrapper around main content
2. Hero section: h1 with the hymn name and a hook, published date, accent rule
3. Section: Lede paragraph (emotional, specific, stop-slop)
4. Section: "The words" — what the text means and why it resonates at the relevant ceremony type
5. Section: "The melody" — tune name, character, singability, emotional arc
6. Section: "It suits every kind of [funeral/wedding]" — versatility across venue types and traditions
7. Section: "It sounds beautiful with live musicians" — what choral/solo performance adds. Include YouTube video embed if available (use the existing `video-embed` pattern). Link to the Listen page for pieces without video.
8. Section: "It sits well alongside other music" — pairing suggestions, placement in the service. Cross-link to other hymn pages and the relevant music guide.
9. Section: "What families tell us" — brief social proof
10. Section: CTA — "We're here if you'd like a hand" with links to the relevant landing page (`funerals.html` or `weddings.html`) and related music guides

Target: 1,000-1,500 words per page. Stop-slop rules.

JSON-LD: Article + BreadcrumbList (Home > Music Guides > [Hymn Name]) + LocalBusiness with AggregateRating. Follow the Be Thou My Vision schema exactly.

Meta tags: title like "Abide with Me — Funeral Hymn Guide | London Choral Service". Description targeting "[hymn name] funeral/wedding" search queries.

Use `../` relative paths for nav links (pages are in `music-guides/`).

- [ ] **Step 2: Add to music guides index**

Add links to each new page in `music-guides/index.html`, in the appropriate category section (funeral hymns, wedding music). Also add to the ItemList schema in the index page's JSON-LD.

- [ ] **Step 3: Cross-link from existing guides**

Add contextual links to the new hymn pages from existing guides that mention these pieces:
- `funeral-music-guide.html` mentions Abide with Me, Ave Maria, The Lord's My Shepherd, Amazing Grace
- `popular-funeral-hymns.html` mentions all of these
- `wedding-ceremony-music.html` mentions Ave Maria, Jerusalem
- `celebration-of-life-music.html` mentions Amazing Grace

Add inline links where these pieces are first mentioned by name (e.g., change "Abide With Me" to `<a href="abide-with-me.html">Abide With Me</a>`).

- [ ] **Step 4: Add all 5 pages to sitemap**

```xml
<url>
  <loc>https://londonchoralservice.com/music-guides/abide-with-me.html</loc>
  <lastmod>2026-05-02</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.7</priority>
</url>
```
(Repeat for each page.)

- [ ] **Step 5: Update llms.txt**

- [ ] **Step 6: Build, validate, and commit**

```bash
./build.sh
git add music-guides/ sitemap.xml llms.txt
git commit -m "feat: add 5 individual hymn guide pages (Abide with Me, Ave Maria, The Lord's My Shepherd, Amazing Grace, Jerusalem)"
```

---

## Task 6: Add Video Embeds to Priority Music Guides

**What:** Embed existing YouTube videos inline in music guides where specific pieces are discussed by name. The Listen page and landing pages already have these embeds; the guides do not.

**Why:** The Listen page has 3 YouTube videos (Abide With Me `G9-R6k5n7Io`, He Shall Feed His Flock `nasqXWlbf1g`, Be Thou My Vision `SaLTS_-I-q4`) but no music guides embed them. Someone reading about "Abide With Me" cannot hear it without navigating away.

**Available YouTube IDs:**
- Abide With Me: `G9-R6k5n7Io`
- He Shall Feed His Flock: `nasqXWlbf1g`
- Be Thou My Vision: `SaLTS_-I-q4`

**Files to modify:**
- `music-guides/funeral-music-guide.html` — embed Abide With Me where it's first discussed
- `music-guides/popular-funeral-hymns.html` — embed Abide With Me and/or Be Thou My Vision where discussed
- `music-guides/celebration-of-life-music.html` — embed Be Thou My Vision if mentioned

- [ ] **Step 1: Add video embeds**

For each guide, find the first substantial mention of a piece that has a YouTube video. After the paragraph discussing it, insert the video embed using the standard pattern (see HTML Patterns above). Add a brief caption like:

```html
<p class="text-sm text-mid">Our singers perform Abide With Me. <a href="../listen.html">Hear more recordings</a>.</p>
```

Do NOT add more than one video per guide page (keeps page weight reasonable).

- [ ] **Step 2: Build and commit**

```bash
./build.sh
git add music-guides/
git commit -m "feat: embed YouTube recordings in priority music guides"
```

---

## Task 7: Featured Snippet Optimization

**What:** Tighten FAQ answers across the site so the first sentence of each answer is a complete, extractable response for Google's featured snippets and "People Also Ask" boxes.

**Why:** FAQ sections and FAQPage schema exist sitewide. But many answers start with context rather than a direct answer. Google extracts the first 40-60 words for featured snippets.

**Files:** All pages with `<h3>` FAQ questions — prioritize:
- `pricing.html` (4 FAQs)
- `services.html` (FAQs)
- `music-guides/funeral-music-guide.html`
- `music-guides/popular-funeral-hymns.html`
- `music-guides/wedding-ceremony-music.html`

- [ ] **Step 1: Audit and rewrite FAQ first sentences**

For each FAQ, ensure the answer's first sentence directly answers the question in under 60 words. Example:

Before: "This depends on several factors including the venue size and the type of service you're planning..."
After: "A solo funeral singer costs from £215. A quartet costs from £1,150, and a full choir of eight from £2,000. All prices include fees and taxes."

The rest of the answer can expand with detail. Only the first sentence needs to be a complete answer.

Also ensure the JSON-LD FAQPage `acceptedAnswer` text matches the first sentence of the visible answer (Google cross-references these).

- [ ] **Step 2: Build and commit**

```bash
./build.sh
git add pricing.html services.html music-guides/
git commit -m "fix(seo): optimise FAQ answers for featured snippet extraction"
```

---

## Task 8: Booking Lead Time Indicators

**What:** Add factual lines to high-intent pages addressing timing anxiety.

**Why:** "Is it too late to book?" (funerals) and "I'll do it later" (weddings) are real conversion barriers.

**Files and copy to add:**

- [ ] **Step 1: funerals.html** — near the CTA or "How it works" section, add:

```html
<p class="text-sm text-mid">We can often arrange musicians within 48 hours. Most families contact us two to five days before the service.</p>
```

- [ ] **Step 2: weddings.html** — near the CTA section, add:

```html
<p class="text-sm text-mid">We recommend booking three to six months ahead. Shorter timelines are usually possible too.</p>
```

- [ ] **Step 3: pricing.html** — after the pricing tables, before the FAQ section, add:

```html
<p>Not sure which ensemble suits your occasion? Call us on <a href="tel:+447356042468">07356 042468</a> and we can talk it through in ten minutes.</p>
```

- [ ] **Step 4: Build and commit**

```bash
./build.sh
git add funerals.html weddings.html pricing.html
git commit -m "content: add booking lead time indicators to high-intent pages"
```

---

## Task 9: Price Anchoring on Pricing Page

**What:** Add brief value-framing context within the pricing detail cells. Not sales copy — honest comparisons that help first-time buyers assess value.

**File:** `pricing.html`

- [ ] **Step 1: Add value context to pricing detail cells**

In the `.pricing-detail` cells (lines 1526-1586), append a short value-framing sentence to 3 key tiers:

**Soloist (line ~1527):** After the existing description, add:
"Most families spend more on flowers than on a singer who transforms the entire service."

**Small Choir / Quartet (line ~1538):** After existing description, add:
"Couples and families regularly tell us the music was the single most memorable part of the day."

**Full Choir (line ~1571):** After existing description, add:
"The sound of eight voices in a cathedral stays with people for years."

Stop-slop rules: no "whether you're looking for...", no "perfect for any occasion." State what happens.

- [ ] **Step 2: Build and commit**

```bash
./build.sh
git add pricing.html
git commit -m "content(pricing): add value-framing context to ensemble descriptions"
```

---

## Task 10: Enrich Top 5 Non-London Area Pages

**What:** Expand the 5 highest-value non-London city pages with venue-specific content, local logistics, and genuinely distinct detail — matching the depth already achieved for priority London boroughs.

**Why:** LCS has 17 non-London city pages vs the competitor's 8 county pages. But if these pages are thinner than the London borough pages, they don't compete for "[city] funeral singer" queries.

**Files:**
- `areas/birmingham.html`
- `areas/manchester.html`
- `areas/oxford.html`
- `areas/cambridge.html`
- `areas/brighton.html`

- [ ] **Step 1: Read each page and identify what's missing**

Compare content depth with the enriched London borough pages (e.g., `areas/london/westminster.html` at ~1,200 words with venue-specific content, logistics, cross-links, testimonials). Identify gaps.

- [ ] **Step 2: For each page, expand with:**

1. **Named venues:** Specific churches, crematoriums, and ceremony venues in that city. For each venue, a sentence about its acoustic character or practical logistics.
2. **Local logistics:** Parking, public transport, arrival procedures specific to that city.
3. **Cross-links to adjacent areas:** Link to nearby area pages.
4. **Cross-links to music guides:** Contextual links to 2-3 relevant guides.
5. **Testimonial:** Add a pull-quote if the page doesn't have one.
6. **Expanded FAQ:** Ensure visible FAQ section has 3-4 genuinely city-specific questions and answers matching the FAQPage schema.

Target: 1,000-1,200 words of genuinely distinct content per page. No find-and-replace template filler.

- [ ] **Step 3: Update FAQPage schema to match visible FAQs**

Ensure the JSON-LD FAQPage questions match the visible `<h3>` questions word-for-word.

- [ ] **Step 4: Build, validate, and commit**

```bash
./build.sh
git add areas/
git commit -m "content(areas): enrich 5 priority non-London city pages with venue-specific content"
```

---

## Task 11: Dark Mode CSS

**What:** Add `@media (prefers-color-scheme: dark)` rules to the design token system. The existing CSS custom property architecture makes this structurally simple — override 8-10 variables inside a media query.

**Why:** Funeral planning often happens late at night. A site that respects dark mode preferences feels considerate and on-brand for a service emphasizing sensitivity.

**File:** `css/tokens.css`

- [ ] **Step 1: Add dark mode variable overrides**

At the end of `css/tokens.css`, add:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg:         #1A1614;
    --color-bg-alt:     #231F1C;
    --color-text:       #E8E0D8;
    --color-text-mid:   #A89888;
    --color-accent:     #C46464;
    --color-accent-hover: #D47878;
    --color-rule:       #3A322C;

    --color-error:      #E07070;
    --color-error-bg:   #2C1A1A;
    --color-error-border: #5C2828;
    --color-success:    #7CB868;
    --color-success-bg: #1A2C14;
    --color-success-border: #2C5C1A;
  }
}
```

Ensure contrast ratios meet WCAG AA (4.5:1 for body text, 3:1 for large text). The accent colour (#C46464) on dark background (#1A1614) gives ~5.2:1 contrast.

- [ ] **Step 2: Handle specific component overrides if needed**

Check if any components use hardcoded colours instead of CSS variables. The `::selection` background in `base.css` uses `#8B3A3A30` — this should work in dark mode but verify. The `.skip-link` uses `var(--color-accent)` background with `var(--color-bg)` text — verify this combination works in dark mode.

- [ ] **Step 3: Build and commit**

```bash
./build.sh
git add css/tokens.css
git commit -m "feat: add dark mode support via prefers-color-scheme media query"
```

---

## Task 12: JSON-LD Validation in Build Script

**What:** Add a permanent validation step to `build.sh` that checks every JSON-LD block across all HTML files parses as valid JSON.

**Why:** Hand-edited JSON-LD across 93+ pages. A misplaced comma silently breaks structured data. This prevents silent regressions.

**File:** `build.sh`

- [ ] **Step 1: Add validation step after CSS inlining**

Append to `build.sh` after the CSS inlining loop:

```bash
echo "Validating JSON-LD..."
errors=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*'); do
  if grep -q 'application/ld+json' "$file"; then
    python3 -c "
import re, json, sys
with open('$file') as fh:
    html = fh.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    try:
        json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f'INVALID: $file - {e}', file=sys.stderr)
        sys.exit(1)
" || { errors=$((errors + 1)); }
  fi
done
if [ "$errors" -gt 0 ]; then
  echo "ERROR: $errors files have invalid JSON-LD"
  exit 1
fi
echo "All JSON-LD valid"
```

- [ ] **Step 2: Commit**

```bash
git add build.sh
git commit -m "feat(build): add JSON-LD validation step to build script"
```

---

## Task 13: Share Buttons on Music Guides

**What:** Add small "Share via WhatsApp" and "Copy link" buttons at the bottom of each music guide.

**Why:** When a family member finds a useful guide, they forward it to others involved in planning. WhatsApp is the most common channel for this audience.

**Files:** `js/share.js` (new), `css/components.css`, all `music-guides/*.html`

- [ ] **Step 1: Create `js/share.js`**

```javascript
(function () {
  var container = document.querySelector('.share-buttons');
  if (!container) return;

  var url = window.location.href;
  var title = document.title;

  var waBtn = container.querySelector('.share-wa');
  if (waBtn) {
    waBtn.href = 'https://wa.me/?text=' + encodeURIComponent(title + ' ' + url);
  }

  var copyBtn = container.querySelector('.share-copy');
  if (copyBtn) {
    copyBtn.addEventListener('click', function (e) {
      e.preventDefault();
      navigator.clipboard.writeText(url).then(function () {
        copyBtn.textContent = 'Copied';
        setTimeout(function () { copyBtn.textContent = 'Copy link'; }, 2000);
      });
    });
  }
})();
```

- [ ] **Step 2: Add CSS for share buttons**

Add to `css/components.css`:

```css
.share-buttons {
  display: flex;
  gap: var(--space-md);
  margin-top: var(--space-2xl);
}

.share-buttons a,
.share-buttons button {
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text-mid);
  text-decoration: none;
  border: 1px solid var(--color-rule);
  padding: var(--space-sm) var(--space-md);
  border-radius: 4px;
  background: none;
  cursor: pointer;
  transition: border-color var(--transition-fast);
}

.share-buttons a:hover,
.share-buttons button:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
```

- [ ] **Step 3: Add share buttons HTML to music guide pages**

In each `music-guides/*.html` file (excluding `index.html`), add before the final CTA section:

```html
<div class="share-buttons">
  <a href="#" class="share-wa" target="_blank" rel="noopener">Share via WhatsApp</a>
  <button class="share-copy" type="button">Copy link</button>
</div>
```

Add `<script src="../js/share.js" defer></script>` before `</body>` on each guide.

- [ ] **Step 4: Build and commit**

```bash
./build.sh
git add js/share.js css/components.css music-guides/
git commit -m "feat: add WhatsApp share and copy link buttons to music guides"
```

---

## Task 14: Micro-Interaction CSS Polish

**What:** Add subtle transitions and hover effects. Uses existing design tokens. Respects `prefers-reduced-motion`.

**File:** `css/components.css`

- [ ] **Step 1: Add hover effects**

```css
/* Pricing table row hover */
.pricing-table tr {
  transition: background-color var(--transition-fast);
}
.pricing-table tr:hover {
  background-color: var(--color-bg-alt);
}

/* Pull-quote subtle entrance */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(1rem); }
  to { opacity: 1; transform: translateY(0); }
}
```

Keep it minimal. No hero fade-ins (those feel gimmicky on a funeral service site). Only add effects that make interactive elements feel more responsive.

- [ ] **Step 2: Build and commit**

```bash
./build.sh
git add css/components.css
git commit -m "polish: add subtle hover transitions to pricing table"
```

---

## Task 15: Update Sitemap and Run Final Build

- [ ] **Step 1: Update lastmod dates**

For every page modified in Tasks 1-14, update the `<lastmod>` value in `sitemap.xml` to `2026-05-02`.

- [ ] **Step 2: Run full build and validate**

```bash
./build.sh
```

- [ ] **Step 3: Validate all JSON-LD sitewide**

Run the validation script from the Build & Validation section above.

- [ ] **Step 4: Check for broken internal links**

```bash
for f in $(find . -name '*.html' -not -path '*/.git/*'); do
  grep -oP 'href="([^"#]+\.html)"' "$f" | while read -r link; do
    href=$(echo "$link" | grep -oP '"[^"]*"' | tr -d '"')
    dir=$(dirname "$f")
    target=$(cd "$dir" && realpath -m "$href" 2>/dev/null)
    if [ ! -f "$target" ]; then
      echo "BROKEN: $f -> $href"
    fi
  done
done
```

- [ ] **Step 5: Commit**

```bash
git add sitemap.xml
git commit -m "chore: update sitemap lastmod dates for May 2026 improvements"
```

---

## Task Dependencies

```
Task 1 (christmas.html fix) — independent, do first
    ↓
Tasks 2, 3, 4 (new B2B + corporate pages) — independent of each other, parallel OK
    ↓
Task 5 (hymn pages) — after Tasks 2-4 so sitemap batch is cleaner
    ↓
Tasks 6, 7, 8, 9 (content improvements) — independent of each other, parallel OK
    ↓
Task 10 (area page enrichment) — independent
    ↓
Tasks 11, 12, 13, 14 (technical polish) — independent of each other, parallel OK
    ↓
Task 15 (sitemap + final build) — LAST
```

---

## Items NOT in This Plan (Require Non-Code Action)

These improvements were identified in the brainstorm but require real-world action beyond code changes:

| Item | Why it can't be automated |
|------|--------------------------|
| Replace placeholder OG image (`assets/og-image.png`) | Needs graphic design or photography |
| Page-specific OG images (funeral, wedding, christmas variants) | Needs image design |
| Google Business Profile optimization | Requires Google account access |
| Review collection (closing the 45 vs 4 gap) | Requires emailing past clients |
| YouTube channel expansion (recording new pieces) | Requires musicians, venue, recording session |
| Spotify curated playlists | Requires Spotify account |
| WhatsApp contact button | Requires business decision from owner |
| Photography of musicians | Requires photographer at events |
| Interactive repertoire browser | Requires expert-curated piece metadata from Luca |
| Build script templating (shared HTML fragments) | High risk of breaking 93 files; needs careful manual testing |
