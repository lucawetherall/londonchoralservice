# SEO & Lead Conversion Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Use @anthropic-skills:stop-slop for ALL copy written in this plan. Use @anthropic-skills:seo-audit principles when validating schema changes.

**Goal:** Close the ranking gap with The London Funeral Singers by propagating schema markup sitewide, enriching content on priority pages, and improving the conversion path from reading to enquiry.

**Architecture:** Static HTML site with 98 hand-crafted pages. CSS is concatenated from 5 source files and inlined via `build.sh`. No templating engine. All changes are direct HTML edits. JSON-LD structured data uses `@graph` arrays. Content follows stop-slop writing principles: no filler, active voice, specific details, varied rhythm.

**Tech Stack:** Static HTML, CSS custom properties (design tokens), vanilla JS, Web3Forms, hCaptcha, Google Analytics 4

**Spec:** `docs/superpowers/specs/2026-03-28-seo-and-conversion-improvements-design.md`

---

## Important Context for Implementers

### What Already Exists (Don't Duplicate)

The site already has significant SEO infrastructure. Read before changing:

- **Homepage** (`index.html`): AggregateRating (5 stars, 4 reviews), 4 Review objects, WebSite + LocalBusiness/PerformingGroup schemas
- **Music guides** (`music-guides/*.html`): Article schema, BreadcrumbList, FAQPage schema, HowTo schema. Content ranges 1,400-1,900 words with CTAs and internal links. BUT: FAQPage schema exists without matching visible FAQ sections on some guides — this violates Google's guidelines and must be fixed
- **Area pages** (`areas/**/*.html`): Service schema, BreadcrumbList, FAQPage schema with visible FAQ sections. Content ~700 words with testimonials, CTAs, internal links
- **Pricing** (`pricing.html`): OfferCatalog + FAQPage schema. Only 436 words of visible content
- **Services** (`services.html`): Service + FAQPage schema. Only 733 words
- **About** (`about.html`): No schema beyond meta tags. Only 495 words
- **Contact** (`contact.html`): ContactPage schema. Form works well via Web3Forms

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
  <figcaption>&mdash; Name, Location</figcaption>
</figure>
```

CTAs use:
```html
<p><a href="../contact.html" class="btn-link">CTA text</a></p>
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

### File Paths

- Root pages: `index.html`, `about.html`, `services.html`, `pricing.html`, `contact.html`, `thank-you.html`
- Music guides: `music-guides/*.html` (28 files + index)
- Area pages: `areas/*.html` (hub + 17 cities), `areas/london/*.html` (32 boroughs)
- CSS source: `css/tokens.css`, `css/base.css`, `css/layout.css`, `css/components.css`, `css/pages.css`
- JS: `js/nav.js`, `js/contact.js`
- Build: `build.sh`
- Sitemap: `sitemap.xml`

### Content Writing Rules

All new or revised copy MUST follow stop-slop rules (@anthropic-skills:stop-slop):
- No filler phrases, no throat-clearing openers
- Active voice — every sentence has a human subject doing something
- No adverbs
- Specific details over vague claims
- Vary sentence length; two items beat three
- No em dashes (use full stops or restructure)
- No inanimate objects performing human actions
- Trust readers — state facts directly, skip softening

### Phone Number Placement

- Footer: YES (already present on every page)
- Within content on high-intent pages: YES
- Header: NO (per client requirement)

### Build & Validation

After editing HTML files, run:
```bash
./build.sh
```
This re-concatenates CSS and inlines it into all HTML files. Any HTML file with a `<link rel="stylesheet" href=...style.css">` tag gets updated.

Validate JSON-LD by checking that it parses as valid JSON (no trailing commas, proper escaping).

---

## Task 1: Propagate AggregateRating Schema Sitewide

The homepage already has AggregateRating (5 stars, 4 reviews) in its LocalBusiness node. The competitor puts their rating on every page. We need to add AggregateRating to pages that reference the organization but don't yet include it.

**Files to modify:** All pages that have JSON-LD with an `@graph` array but lack `aggregateRating`. This includes:
- `services.html`
- `pricing.html`
- `contact.html`
- `about.html`
- `listen.html`
- All `music-guides/*.html` (28 files)
- All `areas/**/*.html` (49 files)

**What NOT to touch:** `index.html` (already has it), `thank-you.html`, `privacy.html`, `404.html`.

- [ ] **Step 1: Identify which pages need AggregateRating**

Read each page's JSON-LD block. Pages that have a LocalBusiness `@id` reference or a Service/Article type should get AggregateRating added to whichever node represents the organization or provider.

For pages with a `Service` type (area pages), add to the `provider` or add a separate LocalBusiness reference. For pages with `Article` type (music guides), add a separate LocalBusiness node. For pages with their own schemas (pricing has OfferCatalog, services has Service), add as a sibling node in `@graph`.

- [ ] **Step 2: Add AggregateRating to core pages**

For `services.html`, `pricing.html`, `contact.html`, `about.html`, `listen.html`: add a LocalBusiness node to the `@graph` array with `aggregateRating` and `review` data matching the homepage pattern:

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

If the page already references `@id: "https://londonchoralservice.com/#organization"`, add `aggregateRating` to that existing node instead of creating a duplicate.

- [ ] **Step 3: Add AggregateRating to all music guide pages**

For each file in `music-guides/*.html` (excluding `index.html`): add a LocalBusiness node with AggregateRating to the `@graph` array, referencing `@id: "https://londonchoralservice.com/#organization"`.

- [ ] **Step 4: Add AggregateRating to all area pages**

For each file in `areas/*.html` and `areas/london/*.html`: add the AggregateRating to the existing provider reference or add a LocalBusiness node with the `@id` reference.

- [ ] **Step 5: Validate JSON-LD across all modified files**

Run a check that every modified file's JSON-LD block parses as valid JSON. Check for:
- No trailing commas
- Proper string escaping
- Valid `@graph` array structure
- `aggregateRating` present with correct values

```bash
# Quick validation: extract and parse JSON-LD from all HTML files
for f in $(find . -name '*.html' -not -path '*/.git/*'); do
  if grep -q 'application/ld+json' "$f"; then
    python3 -c "
import re, json, sys
with open('$f') as fh:
    html = fh.read()
m = re.search(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL)
if m:
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

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(seo): propagate AggregateRating schema to all pages"
```

---

## Task 2: Add Visible FAQ Sections to Music Guides

Several music guides have FAQPage schema in their JSON-LD but no matching visible FAQ section in the HTML. Google requires FAQ content to be user-visible. Fix by adding visible FAQ sections that match the existing schema content.

**Files:** All `music-guides/*.html` files that have FAQPage schema but no `<h2>Frequently asked questions</h2>` in the visible HTML.

- [ ] **Step 1: Audit which guides need visible FAQs**

For each music guide, check:
1. Does the JSON-LD contain `"@type": "FAQPage"`?
2. Does the visible HTML contain an FAQ section (`<h2>Frequently asked questions</h2>` or similar)?

If (1) is yes and (2) is no, the guide needs a visible FAQ section added.

- [ ] **Step 2: Add visible FAQ sections**

For each guide identified in Step 1, add a visible FAQ section before the final CTA section. The content must match the JSON-LD FAQPage questions and answers exactly. Use the existing pattern from area pages:

```html
<section class="section">
  <div class="prose">
    <h2>Frequently asked questions</h2>
    <h3>[Question from JSON-LD]</h3>
    <p>[Answer from JSON-LD]</p>
    <!-- repeat for each Q&A pair -->
  </div>
</section>
```

Place this section before the "You don't have to do this alone" / final CTA section.

- [ ] **Step 3: Validate alignment between schema and visible content**

For each modified guide, confirm the visible FAQ questions match the JSON-LD FAQPage `mainEntity` questions word-for-word.

- [ ] **Step 4: Commit**

```bash
git add music-guides/
git commit -m "fix(seo): add visible FAQ sections to music guides matching schema"
```

---

## Task 3: Add BreadcrumbList Schema to Core Pages

Music guides and area pages already have BreadcrumbList schema. Core pages (services, pricing, about, contact, listen) have visible breadcrumb nav but no matching schema. Add it.

**Files:** `services.html`, `pricing.html`, `about.html`, `contact.html`, `listen.html`

- [ ] **Step 1: Add BreadcrumbList to each core page's JSON-LD**

For each file, add a `BreadcrumbList` node to the `@graph` array:

```json
{
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://londonchoralservice.com/" },
    { "@type": "ListItem", "position": 2, "name": "[Page Name]" }
  ]
}
```

Use appropriate page names: "Services", "Pricing", "About", "Contact", "Listen".

- [ ] **Step 2: Add visible breadcrumb nav to pages missing it**

Check each core page for a `<nav class="breadcrumb">` element. If missing, add it at the top of `<main>` inside the first `<section class="section"><div class="prose">`, before the `<h1>`:

```html
<nav class="breadcrumb" aria-label="Breadcrumb">
  <ol>
    <li><a href="index.html">Home</a></li>
    <li>[Page Name]</li>
  </ol>
</nav>
```

- [ ] **Step 3: Validate and commit**

Validate JSON-LD parses correctly. Commit:

```bash
git add services.html pricing.html about.html contact.html listen.html
git commit -m "feat(seo): add BreadcrumbList schema and visible breadcrumbs to core pages"
```

---

## Task 4: Enrich Pricing Page

Currently 436 words. Needs expansion with FAQ content, value clarification, and testimonials. The page already has FAQPage schema with 4 Q&As and OfferCatalog schema.

**File:** `pricing.html`

- [ ] **Step 1: Read the current page content**

Read `pricing.html` fully. Note the existing structure, pricing tiers, and FAQ schema content.

- [ ] **Step 2: Expand pricing descriptions**

For each pricing tier, add a brief description of what the client gets. Not a feature list. Practical information: what the ensemble sounds like, what occasions it suits, what the experience is like on the day. 2-3 sentences per tier.

Follow stop-slop rules. No "whether you're looking for..." openers. No "perfect for any occasion" filler. State what happens.

- [ ] **Step 3: Add visible FAQ section**

The page has FAQPage schema with 4 Q&As. Add a visible FAQ section matching the schema content. Check if a visible FAQ section already exists. If not, add one using the standard pattern:

```html
<section class="section">
  <div class="prose">
    <h2>Frequently asked questions</h2>
    <h3>[Question from schema]</h3>
    <p>[Answer from schema]</p>
    <!-- repeat for each -->
  </div>
</section>
```

Expand the FAQ answers beyond the schema minimum to provide genuinely useful detail (the schema text can be a summary; the visible text can be longer).

- [ ] **Step 4: Add testimonial relevant to pricing**

Add a pull-quote from someone who found the pricing fair or the value good. Use the existing pattern:

```html
<figure class="pull-quote">
  <blockquote><p>"[testimonial text]"</p></blockquote>
  <figcaption>&mdash; [Name], [Location]</figcaption>
</figure>
```

Place near the pricing section to reduce price anxiety.

- [ ] **Step 5: Add phone number in content**

Add a line below the main CTA with the phone number:

```html
<p class="text-sm text-mid">Or call us on <a href="tel:+447356042468">07356 042468</a> to talk through options.</p>
```

- [ ] **Step 6: Validate and commit**

Run `./build.sh`. Validate JSON-LD. Commit:

```bash
git add pricing.html
git commit -m "content(pricing): expand descriptions, add visible FAQs and testimonial"
```

---

## Task 5: Enrich Services Page

Currently 733 words. Needs expansion with process detail, testimonials per service type, and FAQ content.

**File:** `services.html`

- [ ] **Step 1: Read the current page content**

Read `services.html` fully. Note existing service categories and structure.

- [ ] **Step 2: Expand each service type section**

For each service type (funerals, weddings, memorials, celebrations of life, corporate), add:
- What's included at a practical level
- What the process looks like from first contact to the day
- A testimonial snippet relevant to that service type

Target: 200-300 words per service type. Stop-slop rules apply.

- [ ] **Step 3: Add visible FAQ section**

The page has FAQPage schema. Add matching visible FAQ section if not present. Expand answers to be genuinely helpful.

- [ ] **Step 4: Add phone number in content**

Add phone number near the main CTA, following the same pattern as Task 4.

- [ ] **Step 5: Strengthen internal links**

Add contextual links to:
- Relevant music guides (funeral music guide from funeral section, wedding guides from wedding section)
- Pricing page
- Area pages (brief "We serve [areas]" with links)

- [ ] **Step 6: Validate and commit**

Run `./build.sh`. Validate JSON-LD. Commit:

```bash
git add services.html
git commit -m "content(services): expand service descriptions, add FAQs and testimonials"
```

---

## Task 6: Enrich About Page

Currently 495 words with minimal trust signals. Needs to compete with the competitor's trust signal density (BBC, Royal Albert Hall, named founders with credentials).

**File:** `about.html`

- [ ] **Step 1: Read the current page content**

Read `about.html` fully. Note existing content about the founder and musicians.

- [ ] **Step 2: Add schema markup**

The about page currently has no JSON-LD beyond meta tags. Add an `@graph` with:
- `AboutPage` type
- `BreadcrumbList`
- Reference to the Organization `@id`

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "AboutPage",
      "mainEntity": {
        "@id": "https://londonchoralservice.com/#organization"
      }
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        { "@type": "ListItem", "position": 1, "name": "Home", "item": "https://londonchoralservice.com/" },
        { "@type": "ListItem", "position": 2, "name": "About" }
      ]
    },
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
  ]
}
```

- [ ] **Step 3: Expand trust signals**

Add concrete credentials and social proof:
- Founder's Oxford affiliation and relevant background
- Number of services performed (if known)
- Notable venues performed at (name them specifically)
- Years of experience
- Size of the singer roster ("Over 150 auditioned singers" or similar)

No vague claims. Specific numbers and names. Stop-slop rules apply.

- [ ] **Step 4: Add testimonials**

Add 2-3 pull-quote testimonials distributed through the page, not clustered at the bottom.

- [ ] **Step 5: Validate and commit**

Run `./build.sh`. Validate JSON-LD. Commit:

```bash
git add about.html
git commit -m "content(about): add schema, expand trust signals and testimonials"
```

---

## Task 7: Strengthen Homepage Trust Signals

The homepage is the most-visited page. It already has good schema, a video embed, testimonials, and CTAs. But the trust signals need to be more prominent and specific to compete.

**File:** `index.html`

- [ ] **Step 1: Read the current homepage content**

Read `index.html` main content fully. Note existing sections and their order.

- [ ] **Step 2: Add trust signals above the fold**

In the hero section or immediately after it, add specific credibility markers:
- Review rating (e.g. "Rated 5 stars by every family we've worked with")
- Experience quantifier (years, number of services)
- Notable venue or credential reference

Keep it brief. One or two lines. Not a trust badge wall.

- [ ] **Step 3: Tighten the value proposition**

Review the hero text (`<h1>` and `.lede`). Does it differentiate from competitors or state something generic? If generic, rewrite to lead with what makes this service different. Stop-slop rules apply.

- [ ] **Step 4: Strengthen the CTA section**

The final CTA section currently reads: "A ten-minute conversation..." Review and sharpen. The CTA should connect emotionally without being manipulative. Add phone number alongside the contact link.

- [ ] **Step 5: Validate and commit**

Run `./build.sh`. Validate JSON-LD. Commit:

```bash
git add index.html
git commit -m "content(homepage): strengthen trust signals and value proposition"
```

---

## Task 8: Add Testimonials to Priority Music Guides

Music guides have strong content and CTAs but no testimonials. Adding 1-2 pull-quotes per guide builds trust at the point where researchers are evaluating whether to get in touch.

**Files (priority guides):**
- `music-guides/funeral-music-guide.html`
- `music-guides/popular-funeral-hymns.html`
- `music-guides/funeral-songs.html`
- `music-guides/catholic-funeral-hymns.html`
- `music-guides/celebration-of-life-music.html`
- `music-guides/wedding-ceremony-music.html`

- [ ] **Step 1: Add one testimonial per priority guide**

Insert a `<figure class="pull-quote">` after the second or third content section (not at the top, not at the very end). Choose testimonials that relate to the guide's topic:
- Funeral guides: testimonials about funeral music experience
- Wedding guides: testimonials about wedding music experience

Use the existing testimonials from the homepage schema or ask for new ones. Each testimonial should feel connected to what the reader just read about.

- [ ] **Step 2: Validate and commit**

```bash
git add music-guides/
git commit -m "content(guides): add testimonials to priority music guides"
```

---

## Task 9: Enrich Priority Area Pages

Area pages average ~700 words with templated content. Priority boroughs need unique, specific content that Google can distinguish from each other.

**Files (5 priority boroughs):**
- `areas/london/westminster.html`
- `areas/london/kensington-chelsea.html`
- `areas/london/camden.html`
- `areas/london/southwark.html`
- `areas/london/lambeth.html`

- [ ] **Step 1: Read all 5 pages and identify shared/templated content**

Read each page. Note which paragraphs are identical or near-identical across pages (the boilerplate). Note which content is genuinely unique (venue names, local details).

- [ ] **Step 2: Expand unique content for each borough**

For each page, add genuinely borough-specific information:
- Name specific churches, crematoriums, and ceremony venues in that borough
- Mention any logistics relevant to the area (e.g. central London parking, venue access)
- Reference nearby boroughs with links (internal linking)
- If possible, add a testimonial from a client in or near that borough

Target: expand from ~700 words to 1,000-1,200 words of genuinely distinct content. Stop-slop rules apply. No "nestled in the heart of..." filler.

- [ ] **Step 3: Add cross-links to music guides**

Each area page should link to 2-3 relevant music guides contextually within the content. For example: "Choosing hymns for a funeral at [Venue]? Our [funeral hymns guide](../music-guides/popular-funeral-hymns.html) covers the most popular options."

- [ ] **Step 4: Add cross-links to adjacent boroughs**

Add a brief "Nearby areas" section or inline mentions linking to adjacent borough pages.

- [ ] **Step 5: Validate and commit**

Run `./build.sh`. Validate JSON-LD. Commit:

```bash
git add areas/london/
git commit -m "content(areas): enrich 5 priority London borough pages"
```

---

## Task 10: Internal Linking Improvements

Strengthen the link graph between pages with contextual (in-content) links. Focus on high-value connections that aren't already made.

**Files:** Core pages, priority music guides, priority area pages.

- [ ] **Step 1: Map existing internal links**

For each priority page, list all internal links currently present. Identify gaps:
- Do music guides link to area pages? (Currently: minimal — funeral-music-guide.html has a brief area links section at the bottom)
- Do area pages link to specific music guides? (Currently: some but could be more contextual)
- Do core pages cross-link effectively?

- [ ] **Step 2: Add contextual internal links to music guides**

For each priority music guide, add 2-3 contextual links to area pages within the content. Not a separate "areas" section (that exists), but inline links like: "Families in [area] often choose [piece] for services at [venue] — see our [area page]."

- [ ] **Step 3: Add contextual internal links to core pages**

- Services page: link to specific music guides from each service type section
- Pricing page: link to relevant guides that discuss costs in more detail
- About page: link to listen page and services page contextually

- [ ] **Step 4: Validate no broken links**

Check that all added links resolve to existing pages:

```bash
# Quick broken link check for internal links
for f in $(find . -name '*.html' -not -path '*/.git/*'); do
  grep -oP 'href="([^"#]+\.html)"' "$f" | while read -r link; do
    href=$(echo "$link" | grep -oP '"[^"]*"' | tr -d '"')
    dir=$(dirname "$f")
    target="$dir/$href"
    target=$(cd "$dir" && realpath -m "$href" 2>/dev/null || echo "$href")
    if [ ! -f "$target" ]; then
      echo "BROKEN: $f -> $href"
    fi
  done
done
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(seo): strengthen internal linking across priority pages"
```

---

## Task 11: Contact Page & Thank-You Page Refinements

Small improvements to reduce friction at the point of conversion.

**Files:** `contact.html`, `thank-you.html`

- [ ] **Step 1: Add reassurance line near the form**

In `contact.html`, add a brief line near the submit button that sets expectations:

```html
<p class="text-sm text-mid">We reply personally within 24 hours, usually the same day.</p>
```

Place it between the hCaptcha and the submit button, or immediately after the submit button.

- [ ] **Step 2: Consider occasion dropdown refinement**

Review the current dropdown options:
```
Funeral | Wedding | Memorial service | Celebration of life | Corporate event | Other
```

Consider whether splitting "Funeral" into "Church funeral" and "Crematorium service" adds useful specificity. If it adds complexity without clear benefit, leave it as is.

- [ ] **Step 3: Improve thank-you page**

Read `thank-you.html`. It already has good content ("We'll be in touch within 24 hours"). Add:
- Who will respond (e.g. "Luca or a member of our team")
- What happens next in practical terms (e.g. "We'll suggest some music options and answer any questions")

Keep it concise. 1-2 additional sentences.

- [ ] **Step 4: Validate and commit**

Run `./build.sh`. Commit:

```bash
git add contact.html thank-you.html
git commit -m "content(contact): add reassurance line and improve thank-you page"
```

---

## Task 12: Update Sitemap and Run Final Build

Update lastmod dates in the sitemap for all modified pages and run the full build.

**File:** `sitemap.xml`

- [ ] **Step 1: Update lastmod dates**

For every page modified in Tasks 1-11, update the `<lastmod>` value in `sitemap.xml` to today's date (YYYY-MM-DD format).

- [ ] **Step 2: Run full build**

```bash
./build.sh
```

Verify output shows the expected number of files processed.

- [ ] **Step 3: Validate all JSON-LD sitewide**

Run the JSON validation script from Task 1 Step 5 across all HTML files. Fix any errors.

- [ ] **Step 4: Spot-check key pages visually**

Open in a browser and verify:
- Homepage trust signals display correctly
- Pricing page FAQ section renders properly
- Music guide testimonials appear in correct position
- Area page cross-links work
- Contact page reassurance line appears near form
- Thank-you page updates display

- [ ] **Step 5: Final commit**

```bash
git add sitemap.xml
git commit -m "chore: update sitemap lastmod dates"
```

---

## Task Dependencies

Tasks 1-3 (schema/technical) are independent of each other and can run in parallel.

Tasks 4-9 (content enrichment) are independent of each other and can run in parallel, but each depends on Task 1 being complete (so AggregateRating is already propagated before content changes touch the same files).

Task 10 (internal linking) should run after Tasks 4-9, as it references the enriched content.

Task 11 (contact/thank-you) is independent of all other tasks.

Task 12 (sitemap/build) runs last.

```
Parallel group 1: Tasks 1, 2, 3, 11
         ↓
Parallel group 2: Tasks 4, 5, 6, 7, 8, 9
         ↓
Task 10
         ↓
Task 12
```
