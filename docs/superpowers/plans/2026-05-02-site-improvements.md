# Site Improvements — Implementation Plan (Reviewed v2)

## Context

The London Choral Service site is in good shape after a comprehensive March 2026 SEO/conversion overhaul (`docs/superpowers/plans/2026-03-28-seo-and-conversion-improvements.md` — fully implemented). An audit of that work surfaced one gap (`christmas.html` missing AggregateRating, added 2026-04-11 after the propagation commit) and one limitation (the OG image at `assets/og-image.png` is still the placeholder created in `ca4ae4b`).

This plan covers improvements that **Claude Code can complete autonomously through code changes** — no real-world action required. Items needing photography, recording sessions, Google account access, or business decisions are listed at the end as out-of-scope.

**Reviewer's note (v2):** This revision tightens scope vs the original draft. Several speculative tasks (dark mode, share buttons, micro-interactions) moved to "Consider with user input" because they carry aesthetic risk for a funeral service brand. Task 5 reduced from 5 hymn pages to 2 to protect content quality. Task 7 reframed as an audit (existing FAQs are mostly already well-optimized).

**Tech stack:** Static HTML (93+ pages), CSS custom properties, vanilla JS, Web3Forms, GA4. Build script (`build.sh`) concatenates 5 CSS files and inlines them into HTML. No templating engine — every page is hand-edited.

---

## Shared Patterns (use these throughout)

### Section wrapper
```html
<section class="section">
  <div class="prose"><!-- content --></div>
</section>
```

### Testimonial
```html
<figure class="pull-quote">
  <blockquote><p>"Quote"</p></blockquote>
  <figcaption>&mdash;&ensp;Name, Location</figcaption>
</figure>
```

### CTA pair
```html
<p><a href="contact.html" class="btn-link">CTA text</a></p>
<p class="text-sm text-mid">Or call us on <a href="tel:+447356042468">07356 042468</a>.</p>
```

### Breadcrumb
```html
<nav class="breadcrumb" aria-label="Breadcrumb">
  <ol>
    <li><a href="index.html">Home</a></li>
    <li>Page Name</li>
  </ol>
</nav>
```

### YouTube embed (lazy-loaded thumbnail)
Copy the existing pattern from `listen.html` lines 1401-1411. Replace `data-video` and ID in image src.

### Relative paths by depth
- Root (`./`): `href="contact.html"`, `href="music-guides/"`
- `music-guides/`: `href="../contact.html"`, `href="../music-guides/"` for siblings
- `areas/london/`: `href="../../contact.html"`

### Schema pattern for new pages
LocalBusiness with AggregateRating must be present in the `@graph` array:
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
Plus a `BreadcrumbList` node and a primary type (`Service`, `Article`, etc.) appropriate to the page.

### Stop-slop writing rules
- No filler openers ("In today's world...", "When it comes to...")
- Active voice with human subjects
- No adverbs
- Specific over vague (name the venue, state the number)
- Vary sentence length
- No em dashes (use full stops or restructure)
- Trust the reader

### After every change
```bash
./build.sh
```

---

## Task 1: Audit & Fix Schema Gaps from Late-Added Pages

**Priority:** Highest (active SEO bug)
**Risk:** Low

**Problem:** `christmas.html` was added 2026-04-11, after the AggregateRating propagation commit (2026-03-28, `39810c0`). It lacks the LocalBusiness/AggregateRating node. Other pages added after that date may have the same issue.

- [ ] **Step 1: Identify all pages added or substantially modified after 2026-03-28**

```bash
git log --since="2026-03-28" --diff-filter=AM --name-only --pretty=format: | \
  grep '\.html$' | sort -u
```

For each file in the result, check whether it has `aggregateRating` in its JSON-LD:
```bash
for f in $(git log --since="2026-03-28" --diff-filter=AM --name-only --pretty=format: | grep '\.html$' | sort -u); do
  if [ -f "$f" ] && grep -q 'application/ld+json' "$f" && ! grep -q 'aggregateRating' "$f"; then
    echo "MISSING: $f"
  fi
done
```

Already confirmed missing: `christmas.html`. Verify nothing else.

- [ ] **Step 2: Add LocalBusiness + AggregateRating node to each affected page**

Use the schema pattern shown above. Insert into the `@graph` array. Reference `weddings.html` line ~1320 for the exact pattern that's already proven correct.

- [ ] **Step 3: Validate JSON-LD across the full site**

```bash
for f in $(find . -name '*.html' -not -path '*/.git/*'); do
  if grep -q 'application/ld+json' "$f"; then
    python3 -c "
import re, json, sys
with open('$f') as fh: html = fh.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    try: json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f'INVALID: $f - {e}'); sys.exit(1)
" || echo "FAILED: $f"
  fi
done
```

- [ ] **Step 4: Build and commit**
```bash
./build.sh
git add -A
git commit -m "fix(seo): add missing aggregateRating schema to pages added post-propagation"
```

---

## Task 2: Add JSON-LD Validation to Build Script

**Priority:** High (prevents recurrence of the bug Task 1 fixes)
**Risk:** Very low

**Why before content tasks:** This catches schema mistakes in the new pages we're about to create (Tasks 4-6).

**File:** `build.sh`

- [ ] **Step 1: Append validation step after the existing CSS inlining loop (after line 41)**

```bash
echo "Validating JSON-LD..."
errors=0
for file in $(find "$SCRIPT_DIR" -name '*.html' -not -path '*/.git/*'); do
  if grep -q 'application/ld+json' "$file"; then
    python3 -c "
import re, json, sys
with open('$file') as fh: html = fh.read()
for m in re.finditer(r'<script type=\"application/ld\+json\">(.*?)</script>', html, re.DOTALL):
    try: json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print(f'INVALID: $file - {e}', file=sys.stderr); sys.exit(1)
" || errors=$((errors + 1))
  fi
done
if [ "$errors" -gt 0 ]; then
  echo "ERROR: $errors files have invalid JSON-LD"
  exit 1
fi
echo "All JSON-LD valid"
```

- [ ] **Step 2: Run `./build.sh` to confirm clean baseline, then commit**
```bash
git add build.sh
git commit -m "feat(build): add JSON-LD validation to build script"
```

---

## Task 3: Quick-Win Conversion Copy

**Priority:** High (low effort, immediate impact)
**Risk:** Very low

Three small copy additions to high-intent pages.

- [ ] **Step 1: Booking lead time on `funerals.html`**

Find the section before the contact form (around the "How it works" or final CTA). Add:
```html
<p class="text-sm text-mid">We can often arrange musicians within 48 hours. Most families contact us two to five days before the service.</p>
```

- [ ] **Step 2: Booking lead time on `weddings.html`**

Add near the CTA section:
```html
<p class="text-sm text-mid">We recommend booking three to six months ahead. Shorter timelines are usually possible too.</p>
```

- [ ] **Step 3: Value framing on `pricing.html` (3 specific cells)**

In the `.pricing-detail` cells (lines ~1526-1586), append one sentence to three tiers. Stop-slop rules — state what happens, no "perfect for any occasion" filler.

- **Soloist (~line 1527):** "Most families spend more on flowers than on a singer who carries the entire service."
- **Small Choir (~line 1538):** "Couples and families often tell us afterwards that the music was the moment they remember most."
- **Full Choir (~line 1571):** "Eight voices in a cathedral acoustic produce a sound people describe years later."

- [ ] **Step 4: Build and commit**
```bash
./build.sh
git add funerals.html weddings.html pricing.html
git commit -m "content: add booking lead times and pricing value context"
```

---

## Task 4: Funeral Director Resource Page

**Priority:** High (opens primary referral channel)
**Risk:** Low

**File to create:** `for-funeral-directors.html`

**Why no nav placement:** B2B pages don't belong in primary nav (would confuse end-consumer visitors). Cross-link from `services.html` and the footer instead.

- [ ] **Step 1: Create the page**

Model on `funerals.html` for layout (full HTML head, header, breadcrumb, hero, sections, footer, mobile CTA, scripts). Use root-level relative paths.

Page sections (target 600-800 words total):
1. **Hero:** h1 "For funeral directors", lede about how LCS partners with FDs
2. **"How we work with funeral directors":** Process, timelines, last-minute capability (48 hours typical, 24-hour possible)
3. **"What families receive":** Music consultation with Luca, ensemble options, on-the-day coordination, written running order
4. **"Logistics we handle":** Arrival 45 minutes early, coordination with clergy/officiants, repertoire planning, post-service music
5. **Pull-quote:** A relevant testimonial (the "Luca rang us back within an hour" quote from Sarah, Bromley already on `funerals.html` would suit)
6. **FAQ section** (3-4 questions): pricing, availability windows, last-minute bookings, geographic coverage. Match visible Q/A to FAQPage schema.
7. **CTA:** "Refer a family to us" with contact link and phone

Schema (`@graph`): `Service` (audience: FuneralDirectors) + `BreadcrumbList` + `LocalBusiness` with AggregateRating.

Meta: title `"For Funeral Directors — London Choral Service"`. Description targets FDs who need professional musicians on short notice.

**Quality bar:** Read the page aloud. If any sentence feels generic ("we pride ourselves on...", "our experienced team..."), rewrite it. Real specifics or cut.

- [ ] **Step 2: Cross-link from existing pages**

- `services.html`: in or after the funerals service section, add: "Funeral directors arranging music for a service: see <a href='for-funeral-directors.html'>our funeral director resource page</a>."
- `funerals.html`: at the end, add a discreet line: "Funeral director? <a href='for-funeral-directors.html'>How we work with funeral directors</a>."

- [ ] **Step 3: Add to sitemap**
```xml
<url>
  <loc>https://londonchoralservice.com/for-funeral-directors.html</loc>
  <lastmod>2026-05-02</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.7</priority>
</url>
```

- [ ] **Step 4: Add line to `llms.txt`**

- [ ] **Step 5: Build, validate, commit**
```bash
./build.sh
git add for-funeral-directors.html services.html funerals.html sitemap.xml llms.txt
git commit -m "feat: add funeral director resource page for B2B referrals"
```

---

## Task 5: Wedding Planner Resource Page

**Priority:** Medium (B2B, longer sales cycle than funerals)
**Risk:** Low

Mirror Task 4 structure for wedding planners.

**File to create:** `for-wedding-planners.html`

- [ ] **Step 1: Create the page**

Model on `weddings.html`. Sections (600-800 words):
1. **Hero:** h1 "For wedding planners and venue coordinators"
2. **"How we work with planners":** Booking timelines (3-6 months ideal, shorter possible), repertoire consultation, recordings shared with couples
3. **"What your couples receive":** Custom arrangements at no extra charge, music consultation with Luca, coordination with planner before the day
4. **"On the day":** Arrival, rehearsal in venue, coordination with planner/venue manager, technical needs (power for keyboard if no piano)
5. **Pull-quote:** Wedding testimonial (e.g., the "Sophie & James, Richmond" quote from `weddings.html` line 1426)
6. **FAQ** (3-4 Qs): pricing, repertoire flexibility, outdoor ceremonies, instrument availability
7. **CTA**

Schema: `Service` (audience: wedding planners) + `BreadcrumbList` + `LocalBusiness` with AggregateRating.

Quality bar: same as Task 4.

- [ ] **Step 2: Cross-link from `services.html` and `weddings.html`**

- [ ] **Step 3: Add to sitemap and `llms.txt`**

- [ ] **Step 4: Build, validate, commit**
```bash
./build.sh
git add for-wedding-planners.html services.html weddings.html sitemap.xml llms.txt
git commit -m "feat: add wedding planner resource page for B2B referrals"
```

---

## Task 6: Year-Round Corporate Events Page

**Priority:** Medium
**Risk:** Low

`christmas.html` only captures seasonal corporate demand. A year-round page captures queries like "choir hire for corporate event" or "live music for awards dinner."

**File to create:** `corporate.html`

- [ ] **Step 1: Create the page**

Model on `christmas.html` for landing-page structure (hero, 3-step "How it works", content sections, contact form). Include the Web3Forms contact form with `data-redirect="thank-you.html?from=corporate"`.

Sections:
1. **Hero:** h1 "Live music for corporate events"
2. **3-step process** (consistent with other landing pages)
3. **"Events we perform at":** Awards dinners, product launches, charity galas, conferences, summer parties, client entertainment
4. **"What we provide":** Ensemble options, repertoire range (classical to popular arrangements), technical requirements, sound checks
5. **Pull-quote**
6. **Pricing summary** linking to `pricing.html`
7. **FAQ** (3-4 Qs about corporate bookings)
8. **Contact form** (using `js/landing-form.js`)

Schema: `Service` (corporate events) + `BreadcrumbList` + `LocalBusiness` with AggregateRating.

- [ ] **Step 2: Update `thank-you.html` to handle `?from=corporate`**

Reference how `?from=wedding`, `?from=funeral`, `?from=christmas` are handled (lines ~1370 in `thank-you.html`). Add a corporate variant with appropriate messaging and conversion tracking event.

- [ ] **Step 3: Cross-link from `services.html` corporate section**

- [ ] **Step 4: Add to sitemap and `llms.txt`**

- [ ] **Step 5: Build, validate, commit**
```bash
./build.sh
git add corporate.html thank-you.html services.html sitemap.xml llms.txt
git commit -m "feat: add year-round corporate events landing page"
```

---

## Task 7: Two Individual Hymn Pages (Quality-First Pilot)

**Priority:** Medium
**Risk:** Medium (content quality)

**Why only 2, not 5:** The Be Thou My Vision pages succeed because they reflect Luca's voice and real performance experience. Producing 5 generic hymn pages would dilute the brand and signal AI-generated content to discerning readers (the target audience includes funeral directors, clergy, and educated families). Start with 2 of the highest-value pages, validate quality, then decide whether to expand.

**Pages to create (in this order):**
1. `music-guides/abide-with-me.html` — funeral focus. **YouTube video exists** (`G9-R6k5n7Io`), which makes this the most credible new page.
2. `music-guides/jerusalem.html` — wedding/memorial focus. No video, but "Jerusalem wedding" is a high-volume query.

**Template:** `music-guides/be-thou-my-vision-funeral-hymn.html` (follow structure exactly)

- [ ] **Step 1: Create `abide-with-me.html`**

Sections (target 1,200-1,500 words):
1. `<article>` wrapper
2. Hero: h1 like "Abide With Me — the most-requested funeral hymn", published date, accent rule
3. Lede: emotional opening paragraph, specific to this hymn
4. "The words" — what the text means, why it lands at funerals
5. "The melody" — Eventide tune, William Henry Monk, character, emotional arc, why congregations can sing through tears
6. "It suits every kind of funeral" — Anglican, Catholic, Free Church, secular memorial
7. "It sounds like this" — embed the YouTube video (`G9-R6k5n7Io`) using the standard pattern
8. "It sits well alongside other music" — pairing suggestions, placement (often the final hymn)
9. Brief social proof / what families say
10. CTA section linking to `../funerals.html` and related guides

Schema: `Article` + `BreadcrumbList` (Home > Music Guides > Abide With Me) + `LocalBusiness` with AggregateRating. Copy the exact JSON-LD structure from the Be Thou My Vision page.

Meta: title `"Abide With Me — the most-requested funeral hymn | London Choral Service"`. Description targets "Abide With Me funeral" search.

**Quality bar (mandatory before commit):**
- Read the full page aloud. If any paragraph could be dropped without loss, drop it.
- Every section must contain at least one specific detail (a tune name, a date, a venue type, a sensory description).
- No phrases that sound AI-generated: "tapestry of...", "delve into...", "rich heritage", "stands the test of time", "in today's world".
- The voice must match the Be Thou My Vision pages — first person plural ("we"), professional but warm, never breathless.

- [ ] **Step 2: Create `jerusalem.html`** following the same pattern (no video; link to `../listen.html` for recordings).

- [ ] **Step 3: Cross-link from existing guides**

- `popular-funeral-hymns.html`: link inline where Abide With Me is first mentioned
- `funeral-music-guide.html`: same
- `wedding-ceremony-music.html`: link inline where Jerusalem is mentioned
- `wedding-music-ideas.html`: same

- [ ] **Step 4: Add both to `music-guides/index.html`** ItemList schema and visible listing

- [ ] **Step 5: Add to sitemap and `llms.txt`**

- [ ] **Step 6: Build, validate, commit**
```bash
./build.sh
git add music-guides/ sitemap.xml llms.txt
git commit -m "feat: add Abide With Me and Jerusalem individual hymn guide pages"
```

**After this task: pause and assess.** If the two pages match the Be Thou My Vision quality bar, plan a follow-up batch (Ave Maria, The Lord's My Shepherd, Amazing Grace). If quality falls short, revise the approach before producing more.

---

## Task 8: Embed Existing YouTube Videos in Music Guides

**Priority:** Medium (low effort, immediate UX win)
**Risk:** Very low

Three YouTube videos already exist on `listen.html`. Embed them inline in the music guides where the relevant pieces are first discussed.

**Available videos:**
- Abide With Me: `G9-R6k5n7Io`
- He Shall Feed His Flock: `nasqXWlbf1g`
- Be Thou My Vision: `SaLTS_-I-q4`

- [ ] **Step 1: Add embeds**

Use the standard `video-embed` pattern (see Shared Patterns above). One video per page maximum (page weight, attention budget).

- `music-guides/funeral-music-guide.html`: embed Abide With Me where it's first discussed by name
- `music-guides/popular-funeral-hymns.html`: embed Be Thou My Vision in its section
- `music-guides/celebration-of-life-music.html`: skip if Be Thou My Vision isn't substantively discussed

After each embed, add:
```html
<p class="text-sm text-mid"><a href="../listen.html">Hear more recordings</a>.</p>
```

If Task 7 has been completed, also link from the embed caption to the relevant individual hymn page.

- [ ] **Step 2: Build and commit**
```bash
./build.sh
git add music-guides/
git commit -m "feat: embed YouTube recordings in priority music guides"
```

---

## Task 9: Featured Snippet Audit (Surgical Fixes Only)

**Priority:** Medium
**Risk:** Low (only edit FAQs that need it)

**Reframe from original plan:** A spot-check of `pricing.html` and `funeral-music-guide.html` shows their FAQ first sentences are already snippet-friendly ("A solo funeral singer starts from £215.", "Two or three hymns is standard..."). Don't rewrite what works.

- [ ] **Step 1: Audit FAQ first sentences**

For each page with `<h3>` FAQ questions, identify FAQs where the first sentence:
- Doesn't directly answer the question
- Begins with context rather than a verdict
- Exceeds 60 words before reaching the answer

Prioritise auditing: all `music-guides/*.html`, `services.html`, all `areas/london/*.html` (which were template-generated and may have repetitive answers).

- [ ] **Step 2: Rewrite only the FAQs that fail the audit**

For each, ensure the first sentence is a complete, extractable answer in under 60 words. Keep the rest of the answer as elaboration.

Also ensure the JSON-LD `FAQPage` `acceptedAnswer.text` matches the visible answer's first sentence (Google cross-references these).

- [ ] **Step 3: Build and commit**
```bash
./build.sh
git add -A
git commit -m "fix(seo): tighten FAQ answers for featured snippet extraction"
```

---

## Task 10: Enrich 5 Non-London City Pages

**Priority:** Medium-High (untapped local SEO)
**Risk:** Low

The London borough pages were enriched in the March plan. The 17 non-London city pages weren't. Birmingham, Manchester, Oxford, Cambridge, and Brighton likely have meaningful search volume and currently use lighter, more templated content.

**Files:** `areas/birmingham.html`, `areas/manchester.html`, `areas/oxford.html`, `areas/cambridge.html`, `areas/brighton.html`

- [ ] **Step 1: Read each page and identify gaps vs Westminster**

`areas/london/westminster.html` is the gold-standard reference — ~1,200 words, named venues with one-sentence acoustic notes, local logistics, cross-links to adjacent areas, a testimonial, expanded FAQ.

For each non-London page, list what's missing.

- [ ] **Step 2: Expand each page with:**

1. **Named venues:** specific churches, crematoriums, registry offices, hotels licensed for civil ceremonies. One sentence per venue (acoustic, capacity, or character).
2. **Local logistics:** parking, transport, arrival procedure for that city
3. **Cross-links:** 2-3 relevant music guides, 1-2 nearby area pages
4. **Pull-quote testimonial** if missing
5. **Expanded FAQ:** 3-4 city-specific questions matching the FAQPage schema

Target: 1,000-1,200 words of distinct (not template-rewrite) content per page. Stop-slop rules.

- [ ] **Step 3: Update FAQPage schema to match visible FAQs word-for-word**

- [ ] **Step 4: Build, validate, commit**
```bash
./build.sh
git add areas/
git commit -m "content(areas): enrich Birmingham, Manchester, Oxford, Cambridge, Brighton with venue-specific content"
```

---

## Task 11: Final Sitemap & Validation Pass

**Priority:** Required (run last)
**Risk:** Very low

- [ ] **Step 1: Update `<lastmod>` for every page modified in Tasks 1-10 to `2026-05-02`**

- [ ] **Step 2: Verify new pages are in the sitemap**

- [ ] **Step 3: Run full build**
```bash
./build.sh
```
(With Task 2 complete, this also validates JSON-LD.)

- [ ] **Step 4: Internal link check**
```bash
for f in $(find . -name '*.html' -not -path '*/.git/*'); do
  grep -oP 'href="([^"#]+\.html)"' "$f" | while read -r link; do
    href=$(echo "$link" | grep -oP '"[^"]*"' | tr -d '"')
    dir=$(dirname "$f")
    target=$(cd "$dir" && realpath -m "$href" 2>/dev/null)
    [ ! -f "$target" ] && echo "BROKEN: $f -> $href"
  done
done
```

- [ ] **Step 5: Commit**
```bash
git add sitemap.xml
git commit -m "chore: update sitemap lastmod dates"
```

---

## Recommended Execution Order

```
Day 1 (low-risk foundations):
  Task 1 — Schema gap fix (5 min)
  Task 2 — Build script JSON-LD validation (10 min)
  Task 3 — Quick-win conversion copy (15 min)

Day 2 (B2B pages, can be parallel):
  Task 4 — Funeral director page
  Task 5 — Wedding planner page
  Task 6 — Corporate page

Day 3 (content-heavy, requires care):
  Task 7 — Two hymn pages (write, review, polish)
  Task 8 — Video embeds (quick polish)
  Task 9 — FAQ snippet audit

Day 4:
  Task 10 — Non-London area enrichment

Day 5:
  Task 11 — Sitemap + final validation
```

---

## Tasks Removed from the Original Draft

These were in the v1 plan but dropped on review:

| Task | Why removed |
|------|-------------|
| **Dark mode CSS** | A funeral service brand depends on a specific reverent aesthetic (warm cream, burgundy). Auto-flipping to dark could feel jarring or wrong. Worth raising with the user before implementing — don't assume. |
| **Share buttons on guides** | Funeral content isn't typically shared the way recipes or news articles are. Adds visual clutter without clear benefit for this specific content type. |
| **Micro-interaction polish (pricing row hover)** | Marginal value, risks feeling fidgety on a service where stillness is the brand. Better left alone. |
| **Hymn pages 3, 4, 5** (Ave Maria, Lord's My Shepherd, Amazing Grace) | Dropped from initial batch. Re-add as a follow-up plan only after Task 7 confirms the quality bar can be hit. |

---

## Out of Scope (Require Real-World Action)

| Item | Why Claude Code can't do it |
|------|----------------------------|
| Replace placeholder OG image (`assets/og-image.png`) | Image design — no image generation tool available |
| Page-specific OG images | Same |
| Google Business Profile optimisation | Requires Google account access |
| Closing the 4-vs-45 review gap | Requires emailing past clients |
| New YouTube recordings (beyond the existing 3) | Requires musicians, venue, recording session |
| Spotify curated playlists | Requires Spotify account |
| WhatsApp contact button | Requires business decision from Luca |
| Photography of musicians/venues | Requires photographer |
| Interactive repertoire browser | Requires Luca's expert curation of 100+ piece metadata |
| Build script HTML templating | High risk of breaking 93 pages; needs careful manual testing |
| Multi-step enquiry form | Possible but adds JS complexity for uncertain conversion gain on a site that already has good form completion |

---

## Verification

After completing all tasks:

1. **JSON-LD validation:** `./build.sh` (now includes validation per Task 2) must complete with "All JSON-LD valid"
2. **Internal links:** broken-link script in Task 11 returns no output
3. **New pages render:** open `for-funeral-directors.html`, `for-wedding-planners.html`, `corporate.html`, and the two hymn pages in a browser. Verify navigation, breadcrumbs, hero, and footer all render correctly at mobile (375px) and desktop (1440px) widths.
4. **Schema rich results:** paste the homepage and one new page into Google's Rich Results Test (https://search.google.com/test/rich-results) and confirm AggregateRating, FAQPage (where present), and BreadcrumbList are detected.
5. **Conversion tracking:** submit the corporate page form in dev/staging and confirm `thank-you.html?from=corporate` triggers the correct GA4 event.
6. **Sitemap:** `sitemap.xml` includes all new pages with `lastmod=2026-05-02`.
7. **Content quality (manual review):** read every new page (Tasks 4, 5, 6, 7) aloud. If any sentence sounds AI-generated, rewrite it before considering the task complete.
