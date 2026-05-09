# SEO audit fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address every actionable finding in `SEO-AUDIT-2026-05-08.md` (sections 1–13) on a single feature branch, single comprehensive PR, with items requiring user action documented in `MANUAL-ACTIONS-REQUIRED.md`.

**Architecture:** Static site (GitHub Pages on Fastly). 99 indexable HTML pages. Build pipeline (`build.sh`) inlines partials and CSS into every HTML. Sequential phases (P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8) avoid file-edit conflicts. P6 parallelises internally (5 new pages = 5 fully independent files).

**Tech Stack:** Bash + AWK + Python 3 build pipeline. `validate_jsonld.py` enforces JSON-LD parseability. No JS framework.

**Spec:** `docs/superpowers/specs/2026-05-08-seo-audit-fixes-design.md`

---

## File structure

### Created
- `data/seo-fix-discovered-urls.yml` — Phase 1 output, consumed by Phase 2
- `MANUAL-ACTIONS-REQUIRED.md` — Phase 1 output, top-level repo doc
- `for-event-managers.html` — Phase 6.1
- `music-guides/best-wedding-choirs-london.html` — Phase 6.2
- `music-guides/best-christmas-carol-singers.html` — Phase 6.3
- `music-guides/best-funeral-singers-london.html` — Phase 6.4
- `partials/head-extras.html` — Phase 7 (font preload partial)

### Modified (sweep across many files)
- All 99 indexable HTML files: schema (P2), titles/meta/H1 (P3), various content (P4), nav cross-links (P5), preload tags + img dimensions (P7)
- `partials/nav.html` — P5 (nav restructure), P7 (NAP if needed)
- `sitemap.xml` — P3 (typo fix), P6 (4 new entries)
- `llms.txt` — P3 (21 missing guides + freshness), P6 (4 new entries)
- `robots.txt` — P3 (utm/gclid/fbclid/msclkid disallows)
- `areas/index.html` — P6.5 (expansion)

### Deleted
- `scripts/audit-fix-checks.py` — created in P8 for verification, removed before final commit

---

## Phase 1 — Discovery & manual-actions doc

### Task 1: Run discovery subagent

**Files:**
- Create: `data/seo-fix-discovered-urls.yml`
- Create: `MANUAL-ACTIONS-REQUIRED.md`

- [ ] **Step 1: Dispatch general-purpose subagent with research brief**

The subagent must produce a YAML file in this exact shape:

```yaml
# Discovered URLs and data for SEO audit fix programme
# Generated 2026-05-08

luca_wetherall_linkedin: "https://www.linkedin.com/in/<slug>/"  # or TODO
luca_wetherall_oxford_faculty: "https://www.music.ox.ac.uk/people/<slug>"  # or TODO
luca_wetherall_orcid: "https://orcid.org/<id>"  # or TODO

lcs_linkedin_company: "https://www.linkedin.com/company/<slug>/"  # or TODO
lcs_youtube_channel: "https://www.youtube.com/@<handle>"  # or TODO

alma_consort_companies_house: "https://find-and-update.company-information.service.gov.uk/company/<number>"  # or TODO
alma_consort_registered_office_postcode: "<postcode>"  # or TODO

gbp_canonical_maps_url: "https://www.google.com/maps/place/..."  # or TODO

# VideoObject lookups: identify YouTube IDs in pricing.html (1 video) and listen.html (3 videos),
# then look up actual upload date and ISO 8601 duration for each.
videos:
  - page: "pricing.html"
    youtube_id: "<id>"
    upload_date: "YYYY-MM-DD"  # or TODO
    duration: "PTxMxxS"  # or TODO
  - page: "listen.html"
    position: 1
    youtube_id: "<id>"
    upload_date: "YYYY-MM-DD"  # or TODO
    duration: "PTxMxxS"  # or TODO
  - page: "listen.html"
    position: 2
    youtube_id: "<id>"
    upload_date: "YYYY-MM-DD"  # or TODO
    duration: "PTxMxxS"  # or TODO
  - page: "listen.html"
    position: 3
    youtube_id: "<id>"
    upload_date: "YYYY-MM-DD"  # or TODO
    duration: "PTxMxxS"  # or TODO

# Geo coordinates (5dp) — centroid for each area page
# London boroughs (33)
geo_areas:
  westminster: [51.49594, -0.13495]   # example — research per borough
  city-of-london: [51.51519, -0.09180]
  kensington-chelsea: [51.49955, -0.19094]
  camden: [51.54475, -0.16058]
  islington: [51.53620, -0.10288]
  barnet: [51.65292, -0.20011]
  enfield: [51.65223, -0.08079]
  haringey: [51.59099, -0.11193]
  hackney: [51.54487, -0.05538]
  tower-hamlets: [51.50975, -0.05954]
  waltham-forest: [51.59017, 0.00510]
  brent: [51.55883, -0.27148]
  harrow: [51.58046, -0.34254]
  newham: [51.52772, 0.03492]
  redbridge: [51.58915, 0.07823]
  havering: [51.58122, 0.18373]
  barking-dagenham: [51.55385, 0.13447]
  southwark: [51.50306, -0.08763]
  lambeth: [51.46125, -0.11665]
  lewisham: [51.45685, -0.01051]
  greenwich: [51.48205, 0.00569]
  bromley: [51.40585, 0.01464]
  croydon: [51.37214, -0.10222]
  bexley: [51.44127, 0.14860]
  hammersmith-fulham: [51.49260, -0.22360]
  ealing: [51.51308, -0.30496]
  hounslow: [51.46817, -0.36106]
  hillingdon: [51.53517, -0.44820]
  richmond: [51.46128, -0.30326]
  kingston: [51.41229, -0.30019]
  wandsworth: [51.45691, -0.19200]
  merton: [51.41068, -0.21003]
  sutton: [51.36172, -0.19449]

# Cities (20)
geo_cities:
  london: [51.50735, -0.12776]   # central
  birmingham: [52.48624, -1.89045]
  manchester: [53.48076, -2.24264]
  liverpool: [53.40805, -2.99169]
  oxford: [51.75201, -1.25758]
  cambridge: [52.20534, 0.12182]
  reading: [51.45427, -0.97813]
  slough-maidenhead: [51.51054, -0.59546]
  guildford: [51.23628, -0.57064]
  brighton: [50.82253, -0.13725]
  chester: [53.19046, -2.89195]
  st-albans: [51.75201, -0.33677]
  canterbury: [51.27986, 1.07869]
  windsor: [51.48333, -0.60417]
  winchester: [51.06281, -1.30877]
  salisbury: [51.06840, -1.79528]
  bath: [51.37510, -2.36174]
  chelmsford: [51.73575, 0.46850]
  rochester: [51.38820, 0.50537]
```

The subagent prompt (single message dispatched via Agent tool, `subagent_type: general-purpose`):

> Research the following for an SEO audit fix programme. The user is "The London Choral Service" (londonchoralservice.com), a UK choral-music agency operating as Alma Consort Ltd. Founder is Luca Wetherall.
>
> Output a YAML file at `/Users/luca/Documents/GitHub/londonchoralservice/.claude/worktrees/recursing-johnson-cfffdc/data/seo-fix-discovered-urls.yml` in the exact shape shown below. Use WebSearch + WebFetch to discover each item. Where you cannot discover an item with high confidence, write `TODO` (a string) as the value with a brief comment explaining what's missing. **Never fabricate URLs.**
>
> Items to research:
>
> 1. **Luca Wetherall** — LinkedIn personal URL, Oxford faculty page (likely under music.ox.ac.uk), ORCID. Search "Luca Wetherall University of Oxford Music".
>
> 2. **The London Choral Service / Alma Consort** — LinkedIn company page (search both names), YouTube channel URL.
>
> 3. **Alma Consort Ltd** — Companies House URL (search "Alma Consort Ltd" on https://find-and-update.company-information.service.gov.uk/), the registered office postcode (visible on the Companies House page). Strip to the canonical company-info URL with the company number, e.g. `https://find-and-update.company-information.service.gov.uk/company/12345678`.
>
> 4. **Google Business Profile canonical Maps URL** — search Google Maps for "The London Choral Service" or "London Choral Service". If a verified place exists, capture the canonical `https://www.google.com/maps/place/...` URL with the place ID.
>
> 5. **Video durations + upload dates** — read `pricing.html` and `listen.html` from the repo (paths: `/Users/luca/Documents/GitHub/londonchoralservice/.claude/worktrees/recursing-johnson-cfffdc/pricing.html` and `.../listen.html`). Find the YouTube video IDs (look for `youtube.com/embed/<ID>` or `youtu.be/<ID>` in `<iframe>` or `<a>` tags). Use WebFetch on `https://www.youtube.com/watch?v=<ID>` to read the upload date (YYYY-MM-DD) and duration. Convert duration to ISO 8601 (e.g. `PT3M42S`). Output one entry per video in the YAML `videos:` array.
>
> 6. **Geo coordinates** — for each of the 33 London boroughs and 20 cities listed in `data/seo-fix-discovered-urls.yml.example` (use the area-page filenames I'll list below as keys), look up the centroid lat/long at 5 decimal places. Sources: Wikipedia infobox coordinates for the borough/city, or the city/town hall location. The values must be precise enough to differ between adjacent boroughs.
>
> Area-page keys (use these exact strings in the YAML):
> ```
> Boroughs (areas/london/<key>.html): westminster, city-of-london, kensington-chelsea, camden, islington, barnet, enfield, haringey, hackney, tower-hamlets, waltham-forest, brent, harrow, newham, redbridge, havering, barking-dagenham, southwark, lambeth, lewisham, greenwich, bromley, croydon, bexley, hammersmith-fulham, ealing, hounslow, hillingdon, richmond, kingston, wandsworth, merton, sutton
> Cities (areas/<key>.html): london, birmingham, manchester, liverpool, oxford, cambridge, reading, slough-maidenhead, guildford, brighton, chester, st-albans, canterbury, windsor, winchester, salisbury, bath, chelmsford, rochester
> ```
>
> Also write `MANUAL-ACTIONS-REQUIRED.md` at `/Users/luca/Documents/GitHub/londonchoralservice/.claude/worktrees/recursing-johnson-cfffdc/MANUAL-ACTIONS-REQUIRED.md` with the following sections (full prose, with verification steps):
>
> 1. **GBP listing claim & category audit** — verify GBP exists and is verified; primary category should be "Choir" or "Music Service"; secondaries "Wedding Service" and "Funeral Service"; confirm or replace the share.google sameAs with the canonical Maps URL captured above.
> 2. **Third-party citation building** — claim/audit listings on Bark, Hitched, Bridebook, FuneralGuide, Yell. Provide free citation-checker URL: brightlocal.com/free-business-listings-scan/.
> 3. **Post-event review-request workflow** — outline a 30-day, 60-day, and 90-day review-request cadence targeting Google Business Profile + Trustpilot. Goal: 30+ reviews in 90 days.
> 4. **GSC + GA4 + CrUX credentials** — set `CRUX_API_KEY` env var; create a service-account JSON key with Search Console read access + GA4 Viewer; the queries to run once provisioned are listed in audit §9.
> 5. **Fastly VCL changes (host-level)** — security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), HSTS preload (`includeSubDomains; preload; max-age=63072000`), extensionless URL → `.html` 301, `Cache-Control: max-age=3600`. None of these are configurable on stock GitHub Pages; document as "host-level deferred".
> 6. **Per-page OG image generation infrastructure** — recommend Vercel OG / Cloudinary URL transformations for top 16 pages (12 pillars + 4 highest-traffic guides).
> 7. **IndexNow protocol** — generate key at indexnow.org; drop `<key>.txt` in repo root; POST changed URLs from `build.sh`.
> 8. **CSS extraction refactor** — audit-marked optional. Only worth doing if real CWV data shows the inline-CSS cost. Skip until then.
>
> Verification: confirm both files exist post-write; ensure the YAML parses (`python3 -c "import yaml; yaml.safe_load(open('data/seo-fix-discovered-urls.yml'))"`).

Dispatch with: `Agent({description: "SEO discovery + manual-actions doc", subagent_type: "general-purpose", prompt: <above>})`.

- [ ] **Step 2: Verify outputs**

Run:
```bash
test -f data/seo-fix-discovered-urls.yml && echo "yaml-ok" || echo "yaml-missing"
test -f MANUAL-ACTIONS-REQUIRED.md && echo "md-ok" || echo "md-missing"
python3 -c "import yaml; yaml.safe_load(open('data/seo-fix-discovered-urls.yml')); print('yaml-parses')"
```
Expected: all three "ok" / "parses".

- [ ] **Step 3: Spot-check the YAML for hallucinated URLs**

Read `data/seo-fix-discovered-urls.yml` directly. For every non-TODO URL, the URL must look plausibly real (proper domain, proper path structure). If any URL looks fabricated (random-looking slugs, non-real-looking paths), replace with `TODO: <reason>`. Better to TODO than to ship a fake URL.

- [ ] **Step 4: Commit**

```bash
git add data/seo-fix-discovered-urls.yml MANUAL-ACTIONS-REQUIRED.md
git commit -m "$(cat <<'EOF'
docs(seo-audit): add discovered URLs + manual-actions doc (P1)

Phase 1 of the SEO audit fix programme. data/seo-fix-discovered-urls.yml
is consumed by P2 schema work. MANUAL-ACTIONS-REQUIRED.md captures all
out-of-scope items (GBP claim, citations, review workflow, GSC/GA4 creds,
Fastly headers, OG image infra, IndexNow, CSS extraction).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 2 — Schema sweep

### Task 2a: AggregateRating sitewide cleanup (CRITICAL)

**Files:**
- Modify: 97 HTML files — every indexable page **except** `index.html` and `about.html`. List from `git ls-files '*.html'` minus those two and minus `404.html`, `thank-you.html`, `privacy.html`.

- [ ] **Step 1: Dispatch subagent with surgical schema-edit brief**

Dispatch via Agent (general-purpose). Brief:

> The site has a CRITICAL SEO issue: `AggregateRating` (`ratingValue: 5, reviewCount: 4`) is embedded in the `LocalBusiness` JSON-LD block on **all 99 indexable pages**, but only `index.html` and `about.html` actually display the 4 reviews in body content. Google's review-snippet policy explicitly prohibits site-wide AggregateRating. Risk: silent rich-snippet suppression to manual review-snippet action.
>
> Your job: remove the `aggregateRating` and `review` properties from the `LocalBusiness` (or any `Service` / `ProfessionalService`) JSON-LD blocks on **97 indexable HTML files** — every `.html` page in the repo except `index.html` and `about.html` (and excluding the noindex pages: `404.html`, `thank-you.html`, `privacy.html`).
>
> Specifically:
>
> 1. For each `<script type="application/ld+json">` block on each target page, parse the JSON, walk the entity tree, and:
>    - If you encounter an entity with `@type` equal to (or including, when @type is an array) `LocalBusiness`, `Choir`, `MusicGroup`, `Organization`, `ProfessionalService`, `Service`, or `Product`, delete its `aggregateRating` property and its `review` property.
>    - If after that deletion the only remaining property on a nested entity is `@type` and `@id` (i.e. it's a stub reference), that's fine — leave it.
> 2. Also: where the `LocalBusiness` block had a long inline definition (with name, address, etc.) and is **not** the canonical homepage one, replace the inline block with a `@id`-only stub:
>    ```json
>    {"@type": "LocalBusiness", "@id": "https://londonchoralservice.com/#organization"}
>    ```
>    Do this only when the page is *referencing* the LocalBusiness (e.g. as `provider`), not declaring it. The canonical declaration stays on `index.html`.
> 3. Re-serialise each modified JSON-LD block back into the HTML, preserving 2-space indentation if the original used it.
>
> Files to modify (relative to repo root): all `.html` files matching:
> ```
> $(git ls-files '*.html' | grep -v -E '^(index|about|404|thank-you|privacy)\.html$' | grep -v '^partials/')
> ```
>
> Verification before reporting back:
> 1. Run `python3 validate_jsonld.py` — must exit 0.
> 2. Run this Python script to count AggregateRating occurrences:
>    ```bash
>    python3 -c '
>    import glob, json, re
>    pattern = re.compile(r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>", re.DOTALL)
>    files = glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") + glob.glob("music-guides/*.html")
>    count_pages = 0
>    for fp in sorted(files):
>        with open(fp) as f:
>            html = f.read()
>        for m in pattern.finditer(html):
>            data = json.loads(m.group(1))
>            def walk(o):
>                if isinstance(o, dict):
>                    if "aggregateRating" in o: return True
>                    if "review" in o and isinstance(o["review"], list) and len(o["review"]) > 0: return True
>                    return any(walk(v) for v in o.values())
>                if isinstance(o, list):
>                    return any(walk(v) for v in o)
>                return False
>            if walk(data):
>                count_pages += 1
>                break
>    print(f"Pages still containing aggregateRating or non-empty review: {count_pages}")
>    '
>    ```
>    Expected output: `Pages still containing aggregateRating or non-empty review: 2` (only `index.html` and `about.html`).
> 3. If the count is anything other than 2, report which pages still contain it and stop.
>
> Report back: list of files modified (with line counts), verification command output.

- [ ] **Step 2: Verify subagent's claimed result independently**

Run the same Python script the subagent ran. Confirm output is exactly `Pages still containing aggregateRating or non-empty review: 2`.

```bash
python3 -c '
import glob, json, re
pattern = re.compile(r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>", re.DOTALL)
files = glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") + glob.glob("music-guides/*.html")
count = 0
for fp in sorted(files):
    with open(fp) as f: html = f.read()
    for m in pattern.finditer(html):
        data = json.loads(m.group(1))
        def walk(o):
            if isinstance(o, dict):
                if "aggregateRating" in o: return True
                if "review" in o and isinstance(o["review"], list) and len(o["review"]) > 0: return True
                return any(walk(v) for v in o.values())
            if isinstance(o, list):
                return any(walk(v) for v in o)
            return False
        if walk(data):
            count += 1
            break
print(count)
'
```
Expected: `2`

- [ ] **Step 3: Run build to confirm no regressions**

```bash
./build.sh
```
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(schema): remove sitewide AggregateRating from 97 pages (P2a)

Audit §3 CRITICAL — AggregateRating violated Google's review-snippet
self-serving rule. Reviews remain on index.html (where they're displayed)
and about.html (founder bio context). All other pages now reference
LocalBusiness by @id only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2b: Article + Service + provider/geo cleanup

**Files:**
- Modify: 33 music-guide HTML files (`music-guides/*.html` except `index.html`) — Article schema
- Modify: 53 area HTML files (`areas/*.html` except `index.html` + `areas/london/*.html`) — Service schema, geo, provider.@id
- Modify: `services.html` — Service.name, provider.@id
- Modify: `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html` — priceValidUntil, ratingCount→reviewCount where applicable

- [ ] **Step 1: Dispatch subagent**

Brief:

> Multiple schema fixes across the site. Read the YAML at `data/seo-fix-discovered-urls.yml` for geo coordinates.
>
> **A. Article schema fixes** on all 33 music guides (every `music-guides/*.html` except `music-guides/index.html`):
>
> 1. Remove the entire `HowTo` JSON-LD block (a separate `<script type="application/ld+json">` block whose root `@type` is `HowTo`) on these 9 files:
>    `music-guides/memorial-service-planning.html`, `music-guides/funeral-music-guide.html`, `music-guides/wedding-ceremony-music.html`, `music-guides/funeral-choir-guide.html`, `music-guides/hiring-a-choir.html`, `music-guides/corporate-carol-service.html`, `music-guides/office-carol-service-planning.html`, `music-guides/wedding-choir-guide.html`, `music-guides/choosing-wedding-hymns.html`.
>    HowTo rich results were deprecated by Google in late 2023 — these blocks deliver zero benefit.
>
> 2. On every Article JSON-LD block on every guide (33 guides), add three properties (after `author`):
>    ```json
>    "image": {
>      "@type": "ImageObject",
>      "url": "https://londonchoralservice.com/assets/og-image.png",
>      "width": 1200,
>      "height": 630
>    },
>    "wordCount": <auto>,
>    "speakable": {
>      "@type": "SpeakableSpecification",
>      "cssSelector": [".lede", ".guide-body p:first-of-type"]
>    }
>    ```
>    `wordCount` is auto-calculated: strip HTML from the article body (everything inside `<article>` or, if no `<article>` element, between the `<h1>` and the closing of the main content), count whitespace-separated tokens, round to nearest 100. The `.lede` and `.guide-body p:first-of-type` cssSelectors must exist literally on each guide — verify by grepping the page for `class="lede"` or the `.guide-body` container; if neither exists on a particular guide, use a more conservative selector that does (e.g. `article p:first-of-type`).
>
> **B. Service-schema fixes**:
>
> 3. On `services.html`: the `Service` JSON-LD entity has `serviceType` but no `name`. Add `"name": "Live Music for Ceremonies"` (immediately after `@type`). Also: the `provider` block on `services.html` is currently an inline `LocalBusiness` object — replace with `{"@type": "LocalBusiness", "@id": "https://londonchoralservice.com/#organization"}`.
>
> 4. On every area page's `Service` JSON-LD block (53 area files), the `provider` is currently `{name: "..."}` only. Standardise to:
>    ```json
>    "provider": {"@type": "LocalBusiness", "@id": "https://londonchoralservice.com/#organization"}
>    ```
>    The 53 area files are: `areas/*.html` (excluding `areas/index.html`) + all `areas/london/*.html`.
>
> 5. On each area page's `Service` JSON-LD block, add a `geo` property using the centroid from `data/seo-fix-discovered-urls.yml`. The structure:
>    ```json
>    "geo": {"@type": "GeoCoordinates", "latitude": <lat>, "longitude": <lng>}
>    ```
>    Match the YAML key by filename:
>    - `areas/<city>.html` → `geo_cities.<city>` (where `<city>` is the filename minus `.html`).
>    - `areas/london/<borough>.html` → `geo_areas.<borough>`.
>    If the YAML value is `TODO` for a particular area, skip the geo addition for that area and emit an HTML comment in the JSON-LD block: `<!-- TODO: add geo coords -->` next to the `provider` block.
>
> **C. AggregateOffer / AggregateRating fixes** on the 4 service pages:
>
> 6. `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`: each has an `AggregateOffer` block. Add `"priceValidUntil": "2026-12-31"` to each.
>
> 7. `weddings.html` and `funerals.html`: the Service-level `AggregateRating` uses `ratingCount` (deprecated for AggregateRating). Change `ratingCount` → `reviewCount` on both. Note: if Phase 2a has already removed the AggregateRating from these pages (it should not have — these are pillar pages and the audit treats them differently), skip; otherwise apply.
>    Check first: `grep -c '"aggregateRating"' weddings.html funerals.html` — if 0 on either, skip step 7 for that file. If 1+, the AggregateRating block needs the `ratingCount` → `reviewCount` rename.
>
> Verification:
> ```bash
> ./build.sh                      # must exit 0
> python3 validate_jsonld.py      # must exit 0
>
> # HowTo removed
> grep -l '"HowTo"' music-guides/*.html | wc -l   # expected 0
>
> # Article.image present on all 33 guides
> python3 -c '
> import glob, json, re
> pattern = re.compile(r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>", re.DOTALL)
> missing = []
> for fp in sorted(glob.glob("music-guides/*.html")):
>     if fp.endswith("index.html"): continue
>     with open(fp) as f: html = f.read()
>     has_article_image = False
>     for m in pattern.finditer(html):
>         data = json.loads(m.group(1))
>         def walk(o):
>             nonlocal has_article_image
>             if isinstance(o, dict):
>                 if (o.get("@type") == "Article" or (isinstance(o.get("@type"), list) and "Article" in o["@type"])) and "image" in o:
>                     has_article_image = True
>                 for v in o.values(): walk(v)
>             elif isinstance(o, list):
>                 for v in o: walk(v)
>         walk(data)
>     if not has_article_image: missing.append(fp)
> print("Missing Article.image:", missing)
> '
> # Expected: Missing Article.image: []
>
> # priceValidUntil on 4 service pages
> for f in weddings.html funerals.html corporate.html christmas.html; do
>   if ! grep -q '"priceValidUntil"' "$f"; then echo "MISSING: $f"; fi
> done
> # Expected: no output
>
> # services.html Service.name
> grep -A2 '"@type":\s*"Service"' services.html | grep -q '"name"' && echo "ok" || echo "MISSING name"
> # Expected: ok
> ```
>
> Report back files modified + line counts + verification output.

- [ ] **Step 2: Verify subagent's claimed result**

Run the verification block from the brief. All checks must pass.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(schema): Article + Service cleanup — image/wordCount/speakable, provider.@id, geo, priceValidUntil (P2b)

- Remove HowTo schema from 9 guides (deprecated by Google late 2023)
- Add Article.image, wordCount, speakable on 33 music guides
- services.html: add Service.name, fix provider to @id reference
- 53 area pages: standardise Service.provider to @id reference + add geo coords
- 4 service pages: add AggregateOffer.priceValidUntil
- weddings/funerals: ratingCount → reviewCount on AggregateRating

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2c: Person + Organization + LocalBusiness extras

**Files:**
- Modify: `index.html` — root LocalBusiness extras
- Modify: `about.html` — Person schema, MusicGroup/PerformingGroup
- Modify: `listen.html` — MusicGroup/PerformingGroup

- [ ] **Step 1: Dispatch subagent**

Brief:

> Read `data/seo-fix-discovered-urls.yml` for discovered URLs.
>
> **A. `index.html` root LocalBusiness extras**:
>
> 1. Add `"legalName": "Alma Consort Ltd"` to the canonical `LocalBusiness` (the one with `@id: "https://londonchoralservice.com/#organization"`).
>
> 2. To the `address` sub-object (`PostalAddress`), add `"addressRegion": "Greater London"`. If `alma_consort_registered_office_postcode` in the YAML is not TODO, add `"postalCode": "<value>"`. If TODO, emit an HTML comment immediately before the address block: `<!-- TODO: add postalCode (registered office) -->`.
>
> 3. Replace the existing `sameAs` array on the LocalBusiness with the discovered URLs. Construct the new array from these YAML keys (skip any that are TODO):
>    - `gbp_canonical_maps_url` (replaces the share.google shortener)
>    - `alma_consort_companies_house`
>    - `lcs_youtube_channel`
>    - `lcs_linkedin_company`
>    For any TODO, emit an HTML comment in the JSON-LD: `<!-- TODO: add <key> to sameAs once discovered -->`.
>    If ALL four are TODO, leave the existing share.google entry but add an HTML comment flagging that it's a placeholder.
>
> **B. `about.html` Person schema** (the founder Person node for Luca Wetherall):
>
> 4. Add three properties:
>    ```json
>    "alumniOf": {"@type": "Organization", "name": "University of Oxford"},
>    "worksFor": {"@id": "https://londonchoralservice.com/#organization"},
>    "sameAs": [<urls>]
>    ```
>    The `sameAs` array uses the discovered URLs (skip TODOs):
>    - `luca_wetherall_oxford_faculty`
>    - `luca_wetherall_linkedin`
>    - `luca_wetherall_orcid`
>    For any TODO, emit an HTML comment.
>
> **C. `about.html` and `listen.html` LocalBusiness `@type` array extension**:
>
> 5. On `about.html`: find the LocalBusiness block (probably `@type: "LocalBusiness"` — single string). Change it to `["LocalBusiness", "PerformingGroup", "MusicGroup"]`.
>
> 6. On `listen.html`: same change — extend the `@type` to include `PerformingGroup` and `MusicGroup`.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
>
> # legalName present
> grep -q '"legalName":\s*"Alma Consort Ltd"' index.html && echo "ok" || echo "MISSING"
>
> # MusicGroup on about + listen
> for f in about.html listen.html; do
>   grep -q '"MusicGroup"' "$f" && echo "$f: ok" || echo "$f: MISSING"
> done
>
> # Person sameAs / alumniOf
> grep -q '"alumniOf"' about.html && echo "alumniOf-ok" || echo "alumniOf-MISSING"
> ```
>
> Report files modified + verification output.

- [ ] **Step 2: Verify**

Run the verification block.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(schema): expand Person, Organization, LocalBusiness entity definitions (P2c)

- index.html LocalBusiness: add legalName, addressRegion, postalCode (or TODO),
  expand sameAs with discovered URLs (Companies House, YouTube, LinkedIn, GBP
  canonical Maps URL where available; TODO comments for the rest)
- about.html: add alumniOf + worksFor + sameAs to Person; extend LocalBusiness
  @type with PerformingGroup + MusicGroup
- listen.html: extend LocalBusiness @type with PerformingGroup + MusicGroup

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 2d: VideoObject + dateModified + openingHours

**Files:**
- Modify: `index.html`, `contact.html` — openingHoursSpecification
- Modify: `pricing.html` (1 video) + `listen.html` (3 videos) — VideoObject duration + uploadDate
- Modify: `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`, `services.html`, `pricing.html` — Service.dateModified

- [ ] **Step 1: Dispatch subagent**

Brief:

> **A. openingHours → openingHoursSpecification** on `index.html` and `contact.html`:
>
> Find the `LocalBusiness` block on each. Replace the legacy string `"openingHours": "Mo-Fr 09:00-18:00"` (or any variant of that string) with:
> ```json
> "openingHoursSpecification": [{
>   "@type": "OpeningHoursSpecification",
>   "dayOfWeek": ["Monday","Tuesday","Wednesday","Thursday","Friday"],
>   "opens": "09:00",
>   "closes": "18:00"
> }]
> ```
> Delete the old `openingHours` line.
>
> **B. VideoObject duration + uploadDate** on `pricing.html` (1 video) and `listen.html` (3 videos):
>
> Read `data/seo-fix-discovered-urls.yml` `videos:` array. For each entry:
> - Replace `"uploadDate": "2025-01-01"` (or whatever placeholder is currently there) with the discovered upload date in ISO 8601 (YYYY-MM-DD).
> - Add `"duration": "<ISO8601>"` next to it.
> - If the YAML entry is TODO for that video, emit an HTML comment: `<!-- TODO: replace placeholder uploadDate, add duration -->` and leave the schema unchanged.
>
> Identify videos by the YouTube ID present in the `embedUrl` or `contentUrl` field of each VideoObject block. Match against the YAML by `youtube_id`.
>
> **C. Service.dateModified** on 6 commercial pillars:
>
> Add `"dateModified": "2026-05-08"` to the `Service` JSON-LD block on:
> `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`, `services.html`, `pricing.html`.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
>
> # openingHoursSpecification
> for f in index.html contact.html; do
>   grep -q '"openingHoursSpecification"' "$f" && echo "$f: ok" || echo "$f: MISSING"
>   grep -q '"openingHours":\s*"Mo-Fr' "$f" && echo "$f: STILL HAS LEGACY"
> done
>
> # dateModified on 6 pillars
> for f in weddings.html funerals.html corporate.html christmas.html services.html pricing.html; do
>   grep -q '"dateModified":\s*"2026-05-08"' "$f" && echo "$f: ok" || echo "$f: MISSING"
> done
>
> # uploadDate placeholder eliminated (where YAML had real date)
> grep -c '"uploadDate":\s*"2025-01-01"' pricing.html listen.html
> # Expected: 0 unless the YAML had TODO for some videos
> ```
>
> Report files modified + verification output.

- [ ] **Step 2: Verify**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(schema): openingHours + VideoObject + Service.dateModified (P2d)

- index.html, contact.html: replace legacy openingHours string with
  OpeningHoursSpecification structured form
- pricing.html, listen.html: replace placeholder VideoObject uploadDate
  with real dates; add ISO 8601 duration (TODO comments where unknown)
- 6 commercial pillars: add Service.dateModified for AI/SEO recency signal

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 3 — Title / meta / H1 sweep

### Task 3: Templated metadata fixes across the site

**Files:**
- Modify: 67 HTML files for title-tag fixes (53 area + 34 music-guides + a few pillars over the cap)
- Modify: 53 area HTML files for H1 fix
- Modify: ~63 HTML files for meta-description trims
- Modify: `sitemap.xml` (typo)
- Modify: `robots.txt` (utm/gclid disallows)
- Modify: `llms.txt` (21 missing guides + freshness line)

- [ ] **Step 1: Dispatch subagent**

Brief:

> Five templated metadata fixes across the site.
>
> **A. Title-tag fix — drop brand suffix on local pages** (audit §2 HIGH):
>
> Current pattern on area pages: `<title>Funeral Singers & Wedding Choirs in [City] — London Choral Service</title>` (60–72 chars).
> New pattern on area pages: `<title>Funeral and wedding choirs in [City]</title>` (~38–47 chars).
>
> Apply to all 53 area pages:
> - `areas/<city>.html` for 20 cities: `birmingham, manchester, liverpool, oxford, cambridge, reading, slough-maidenhead, guildford, brighton, chester, st-albans, canterbury, windsor, winchester, salisbury, bath, chelmsford, rochester, london, bath` (use the actual filename list from the repo)
> - `areas/london/<borough>.html` for 33 boroughs.
>
> The exact city/borough name comes from the existing H1 on each page (capture it via grep before rewriting). Use the city's display name (e.g. "Slough & Maidenhead", "Kensington & Chelsea") not the kebab-case filename.
>
> For music guides (`music-guides/*.html` except `index.html`), drop the `— London Choral Service` (or `| London Choral Service`) brand tail from each `<title>`. Don't rewrite the title body — only strip the brand suffix.
>
> For the 12 pillar pages (`index.html`, `about.html`, `services.html`, `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`, `listen.html`, `pricing.html`, `contact.html`, `for-funeral-directors.html`, `for-wedding-planners.html`): keep the brand suffix where the title fits ≤60 chars. If over, shorten brand to ` | LCS`. Verify each.
>
> Final verification: every page's `<title>` ≤60 characters.
>
> **B. Area-page H1 fix** (audit §2 HIGH):
>
> Every area page (53 files) currently has `<h1>Funeral singers and choirs in [City]</h1>`. Change to `<h1>Funeral and wedding choirs in [City]</h1>` (lowercase preserved per house style; "and" rather than "&"; preserves City name).
>
> **C. Meta-description trims** (audit §2 MEDIUM):
>
> Every page's `<meta name="description" content="...">` must be ≤160 characters. Where over, trim at a sentence/clause boundary so the lead is preserved (don't truncate mid-sentence). The audit identified 63 over-length descriptions (worst: area pages 250–300 chars; pricing.html 214 chars).
>
> Workflow: for each `.html` file, read the description, count chars, if >160 rewrite to ≤155 chars (5-char buffer). Each rewrite must:
> - Preserve the lead unique-selling-point of the original.
> - Use the same tone (factual, no hype).
> - End on a complete clause.
>
> **D. Sitemap typo fix**:
>
> In `sitemap.xml`, find the `<url>` block for `popular-wedding-organ-music.html` (line 594 region). The `<lastmod>` is `2026-03-06` — change to `2026-05-06`.
>
> **E. robots.txt updates**:
>
> Append to `robots.txt`:
> ```
> Disallow: /*?utm_
> Disallow: /*?gclid=
> Disallow: /*?fbclid=
> Disallow: /*?msclkid=
> ```
> Each on its own line. Place these after any existing Allow/Disallow lines but before any closing comment.
>
> **F. llms.txt updates** (audit §6):
>
> 1. Under the existing top blockquote (the `> Professional singers...` line), add a new blockquote line:
>    ```
>    > Content last updated: May 2026. 34 music guides available.
>    ```
> 2. Under `## Music Guides`, add the 21 currently-missing guides. The current 13 guides listed are: funeral-music-guide, popular-funeral-hymns, choosing-wedding-hymns, celebration-of-life-music, hiring-a-choir, funeral-songs, crematorium-music, funeral-music-costs, memorial-service-planning, be-thou-my-vision-wedding-hymn, be-thou-my-vision-funeral-hymn, abide-with-me, jerusalem.
>
>    The missing 21 are: `wedding-ceremony-music`, `wedding-music-costs`, `wedding-music-ideas`, `wedding-readings-and-music`, `wedding-choir-guide`, `wedding-organist-guide`, `wedding-choral-repertoire`, `wedding-organ-pop-songs`, `wedding-organ-repertoire`, `wedding-pop-songs-choir`, `lesser-known-wedding-choral-pieces`, `popular-wedding-organ-music`, `corporate-carol-service`, `christmas-choir-hire`, `company-christmas-party-entertainment`, `christmas-carols-guide`, `office-carol-service-planning`, `catholic-funeral-hymns`, `non-religious-funeral-music`, `funeral-choir-guide`.
>
>    For each, write a one-line entry in the same style as existing entries:
>    ```
>    - [Title](https://londonchoralservice.com/music-guides/<slug>.html): <one-line description>
>    ```
>    Use the page's actual H1 / `<title>` for the title, and a 100-char-or-less summary based on the lede paragraph of each guide. Read each guide briefly to write a true description — don't fabricate.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
>
> # Title length scan
> python3 -c '
> import glob, re
> over = []
> for fp in sorted(glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") + glob.glob("music-guides/*.html")):
>     with open(fp) as f: html = f.read()
>     m = re.search(r"<title>([^<]+)</title>", html)
>     if not m: continue
>     # Decode HTML entities for length count
>     import html as htmllib
>     title = htmllib.unescape(m.group(1))
>     if len(title) > 60:
>         over.append((len(title), fp, title))
> for t in sorted(over, reverse=True)[:10]: print(t)
> print(f"Total over 60: {len(over)}")
> '
> # Expected: Total over 60: 0
>
> # Meta description scan
> python3 -c '
> import glob, re, html as htmllib
> over = []
> for fp in sorted(glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") + glob.glob("music-guides/*.html")):
>     with open(fp) as f: t = f.read()
>     m = re.search(r"<meta\s+name=\"description\"\s+content=\"([^\"]+)\"", t)
>     if not m: continue
>     d = htmllib.unescape(m.group(1))
>     if len(d) > 160: over.append((len(d), fp))
> for o in sorted(over, reverse=True)[:10]: print(o)
> print(f"Total over 160: {len(over)}")
> '
> # Expected: Total over 160: 0
>
> # H1 fix verification
> python3 -c '
> import glob, re
> bad = []
> for fp in glob.glob("areas/*.html") + glob.glob("areas/**/*.html"):
>     if fp.endswith("areas/index.html"): continue
>     with open(fp) as f: html = f.read()
>     m = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
>     if m and "Funeral and wedding choirs" not in m.group(1):
>         bad.append(fp)
> print("H1 not updated:", bad)
> '
> # Expected: H1 not updated: []
>
> # Sitemap typo fixed
> grep -A1 "popular-wedding-organ-music.html" sitemap.xml | grep -q "2026-05-06" && echo "ok" || echo "MISSING"
>
> # robots.txt
> grep -q "Disallow: /\\*?utm_" robots.txt && echo "ok" || echo "MISSING"
>
> # llms.txt freshness + 21 guides
> grep -q "Content last updated: May 2026" llms.txt && echo "freshness-ok" || echo "freshness-MISSING"
> for slug in wedding-ceremony-music wedding-music-costs wedding-music-ideas wedding-readings-and-music wedding-choir-guide wedding-organist-guide wedding-choral-repertoire wedding-organ-pop-songs wedding-organ-repertoire wedding-pop-songs-choir lesser-known-wedding-choral-pieces popular-wedding-organ-music corporate-carol-service christmas-choir-hire company-christmas-party-entertainment christmas-carols-guide office-carol-service-planning catholic-funeral-hymns non-religious-funeral-music funeral-choir-guide; do
>   grep -q "music-guides/$slug.html" llms.txt || echo "llms.txt missing: $slug"
> done
> # Expected: no "missing" lines
> ```
>
> Report files modified + line counts + verification output.

- [ ] **Step 2: Verify all checks pass**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(seo): title/meta/H1 sweep + sitemap/robots/llms updates (P3)

- Drop brand suffix on 87 local pages so all titles ≤60 chars
- Area-page H1: 'Funeral singers and choirs' → 'Funeral and wedding choirs'
  (now matches the dual-vertical title and target wedding-intent queries)
- Trim 63 over-length meta descriptions to ≤160 chars
- Sitemap typo: 2026-03-06 → 2026-05-06 on popular-wedding-organ-music
- robots.txt: disallow tracking-param URLs to protect crawl budget
- llms.txt: add 21 missing music guides + freshness signal line

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 4 — Content fixes

### Task 4a: Author byline + last-updated dates (templated)

**Files:**
- Modify: 33 individual music-guide HTML files (`music-guides/*.html` except `music-guides/index.html`)
- Modify: 6 commercial pillars: `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`, `services.html`, `pricing.html`

- [ ] **Step 1: Dispatch subagent**

Brief:

> Two visible-content additions, templated.
>
> **A. Author byline on 33 music guides** (audit §13.2.1):
>
> Insert immediately under the `<h1>` of each guide:
> ```html
> <p class="guide-meta">By Luca Wetherall, Artistic Director &amp; Tutor in Music, University of Oxford</p>
> ```
>
> The 33 files are every `.html` in `music-guides/` except `index.html`.
>
> Insertion logic: find the `<h1>...</h1>` line. If the next sibling is already a `<p class="guide-meta">Published ...</p>` line, insert the byline **before** it (so order is: H1 → byline → published date). If no existing guide-meta sibling, insert directly after H1.
>
> Idempotency: if the page already contains a `<p class="guide-meta">By Luca Wetherall` line under H1, skip.
>
> **B. Last-updated date on 6 commercial pillars**:
>
> Insert immediately under the `<h1>` of each:
> ```html
> <p class="guide-meta">Last updated: May 2026</p>
> ```
>
> Files: `weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`, `services.html`, `pricing.html`.
>
> Idempotency: if the page already contains a `<p class="guide-meta">Last updated:` line under H1, replace its date text with `May 2026`.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
>
> # Byline on 33 guides
> python3 -c '
> import glob
> missing = []
> for fp in sorted(glob.glob("music-guides/*.html")):
>     if fp.endswith("index.html"): continue
>     with open(fp) as f: t = f.read()
>     if "By Luca Wetherall" not in t or "guide-meta" not in t: missing.append(fp)
> print("Byline missing:", missing)
> '
> # Expected: Byline missing: []
>
> # Last-updated on 6 pillars
> for f in weddings.html funerals.html corporate.html christmas.html services.html pricing.html; do
>   grep -q "Last updated: May 2026" "$f" && echo "$f: ok" || echo "$f: MISSING"
> done
> ```

- [ ] **Step 2: Verify**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(content): author byline on guides + last-updated on pillars (P4a)

- 33 music guides: visible 'By Luca Wetherall, Artistic Director &
  Tutor in Music, University of Oxford' under each H1 (audit §13.2.1)
- 6 commercial pillars: 'Last updated: May 2026' under H1 for AI/SEO
  recency signal (audit §4 MEDIUM)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 4b: Pillar content additions (price summary, humanist para, area links, B2B resource lists)

**Files:**
- Modify: `weddings.html` — price summary paragraph, area-link sentence
- Modify: `funerals.html` — price summary paragraph, area-link sentence, humanist paragraph + 2-link cluster, cancellation statement
- Modify: `for-funeral-directors.html` — resource list of guide links, cancellation statement
- Modify: `for-wedding-planners.html` — resource list of guide links

- [ ] **Step 1: Dispatch subagent (with humanistic-writing skill invoked)**

Brief:

> Four content additions on the commercial pillars and B2B intermediary pages. All net-new prose must avoid AI writing tells — use the humanistic-writing skill principles: factual, specific, named entities, no hedging, no marketing tells. Match the existing site's register (look at `corporate.html`'s FAQ answers for the calibration).
>
> **A. Price-summary paragraph** on `weddings.html` and `funerals.html`:
>
> Insert one paragraph immediately before the existing `<div class="price-cards">` block (or whatever container holds the price cards — confirm by grep). Pattern (from corporate.html FAQ):
>
> Weddings:
> ```html
> <p class="lede-secondary">A small choir of four singers starts from £1,150; a quintet £1,400; a sextet £1,600; full choirs from £2,000. All ensemble sizes include preparation, travel within London, and a music director on the day.</p>
> ```
>
> Funerals:
> ```html
> <p class="lede-secondary">A soloist starts from £215; a quartet from £1,150; a quintet £1,400; a sextet £1,600; full choirs from £2,000. All ensemble sizes include preparation, travel within London, and a music director on the day. We can usually accommodate short-notice bookings from our roster of over 150 singers.</p>
> ```
>
> If `lede-secondary` is not an existing CSS class, fall back to `<p>` without a class (verify class existence with `grep "lede-secondary" css/style.css` first).
>
> **B. Funerals.html humanist paragraph + 2-link cluster** (audit §13.2.2):
>
> Find the `What we provide` section (or equivalent — look for an h2 about what's offered). Insert a paragraph addressing humanist / non-religious services:
>
> ```html
> <p>Many of our bookings are for non-religious or humanist services — celebrations of life held at crematoriums, woodland venues, or community halls. We adapt the music accordingly: secular songs and instrumental pieces work as well as hymns, and a soloist or small ensemble suits the more intimate format. See our guide to <a href="music-guides/non-religious-funeral-music.html">non-religious funeral music</a> and <a href="music-guides/celebration-of-life-music.html">celebration of life music</a> for fuller suggestions.</p>
> ```
>
> **C. Inline area-page link sentence** on `weddings.html` and `funerals.html` (audit §13.2.3):
>
> In the "How it works" / "What we provide" section, insert one sentence naming three areas with links:
>
> Weddings (insert near a "where we sing" or similar mention; if no such context, add to the end of the lede paragraph):
> ```html
> <p>We sing in churches, hotels, country houses, and registry offices across the UK — most often in <a href="areas/london.html">London</a>, <a href="areas/oxford.html">Oxford</a>, and <a href="areas/manchester.html">Manchester</a>, but we travel further when the booking warrants it.</p>
> ```
>
> Funerals: same shape, adjusted for funerals tone:
> ```html
> <p>We sing at churches, crematoriums, and chapels across the UK — most often in <a href="areas/london.html">London</a>, <a href="areas/oxford.html">Oxford</a>, and <a href="areas/manchester.html">Manchester</a>, but we travel further when families need us.</p>
> ```
>
> **D. Cancellation/replacement-cover statement** on `funerals.html` and `for-funeral-directors.html` (audit §13.2.7):
>
> Add a one-sentence reassurance somewhere visible (FAQ block on funerals; "what families can expect" section on for-funeral-directors):
>
> ```html
> <p>In the event of a musician's illness, we always have a replacement available from our roster of over 150 singers — bookings are never cancelled at short notice for our reasons.</p>
> ```
>
> **E. Resource list on `for-funeral-directors.html`** (audit §13.2.4):
>
> Add a "Useful resources for families" h2 + ul block:
> ```html
> <section class="useful-resources">
>   <h2>Useful resources for families</h2>
>   <ul>
>     <li><a href="music-guides/funeral-music-guide.html">How to choose music for a funeral</a> — step-by-step guide to hymns, solo pieces, and instrumental music</li>
>     <li><a href="music-guides/popular-funeral-hymns.html">The most popular funeral hymns</a> — what families choose most often, with notes on each</li>
>     <li><a href="music-guides/crematorium-music.html">Music for a crematorium service</a> — practical advice on timing, acoustics, and shorter services</li>
>     <li><a href="music-guides/celebration-of-life-music.html">Music for a celebration of life</a> — how non-religious services differ, with popular choices</li>
>   </ul>
> </section>
> ```
>
> **F. Resource list on `for-wedding-planners.html`**:
>
> Same shape, audience-adjusted:
> ```html
> <section class="useful-resources">
>   <h2>Useful resources for couples</h2>
>   <ul>
>     <li><a href="music-guides/wedding-ceremony-music.html">Choosing music for the wedding ceremony</a></li>
>     <li><a href="music-guides/choosing-wedding-hymns.html">How to choose wedding hymns your guests will sing</a></li>
>     <li><a href="music-guides/wedding-readings-and-music.html">Pairing readings with music</a></li>
>     <li><a href="music-guides/wedding-music-ideas.html">Wedding music ideas — beyond the obvious</a></li>
>   </ul>
> </section>
> ```
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
> grep -q "from £1,150" weddings.html && echo "weddings-price-ok" || echo "weddings-price-MISSING"
> grep -q "from £1,150" funerals.html && echo "funerals-price-ok" || echo "funerals-price-MISSING"
> grep -q "non-religious-funeral-music" funerals.html && echo "funerals-humanist-ok" || echo "funerals-humanist-MISSING"
> grep -q "areas/london.html" weddings.html && echo "weddings-areas-ok" || echo "weddings-areas-MISSING"
> grep -q "areas/london.html" funerals.html && echo "funerals-areas-ok" || echo "funerals-areas-MISSING"
> grep -q "replacement available from our roster" funerals.html && echo "funerals-cancel-ok" || echo "funerals-cancel-MISSING"
> grep -q "replacement available from our roster" for-funeral-directors.html && echo "ffd-cancel-ok" || echo "ffd-cancel-MISSING"
> grep -q "Useful resources for families" for-funeral-directors.html && echo "ffd-resources-ok" || echo "ffd-resources-MISSING"
> grep -q "Useful resources for couples" for-wedding-planners.html && echo "fwp-resources-ok" || echo "fwp-resources-MISSING"
> ```

- [ ] **Step 2: Verify**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(content): pillar + B2B page enrichments (P4b)

- weddings.html, funerals.html: extractable price-summary paragraph above
  price-cards (audit §4 MEDIUM); inline area-page link cluster (§13.2.3)
- funerals.html: humanist/non-religious paragraph + 2-link cluster (§13.2.2);
  cancellation/replacement-cover statement (§13.2.7)
- for-funeral-directors.html: 'Useful resources for families' guide list
  (§13.2.4); cancellation statement
- for-wedding-planners.html: 'Useful resources for couples' guide list

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 4c: Contact FAQ + Richmond/pricing area-links + funeral-hymns reconciliation

**Files:**
- Modify: `contact.html` — opening summary, 2–3-question FAQ, FAQPage JSON-LD
- Modify: `areas/london/richmond.html` — body link to areas/london.html
- Modify: `pricing.html` — body link to areas/london.html
- Modify: `music-guides/popular-funeral-hymns.html` — reconcile claim
- Modify: `music-guides/abide-with-me.html` — reconcile claim

- [ ] **Step 1: Dispatch subagent**

Brief:
>
> **A. `contact.html` opening + FAQ + FAQPage schema** (audit §13.2.5):
>
> 1. Insert a one-paragraph summary above the existing "By email" / first contact-method heading. Pattern:
>    ```html
>    <p class="lede">Contact The London Choral Service to enquire about singers, choirs, or instrumentalists for a funeral, wedding, memorial, or corporate event. We typically reply within one working day. Please include the date, venue, and approximate ensemble size if you know it; we'll come back with options and a quote.</p>
>    ```
>
> 2. Add a 3-question FAQ block (h2 + dl or h3+p pairs — match existing pattern on the site; check funerals.html or weddings.html for the exact markup convention) before the closing `</main>`:
>
>    Question 1: *How quickly do you reply?*
>    Answer: *Usually within one working day, often within a few hours during business hours. For short-notice funeral enquiries we reply same-day.*
>
>    Question 2: *What information should I include in my enquiry?*
>    Answer: *The date and time, the venue (with postcode if you have it), and the approximate ensemble size you're considering. If you don't know the size, that's fine — tell us the occasion and we'll suggest options.*
>
>    Question 3: *Can I phone instead of emailing?*
>    Answer: *Yes — call 07356 042468. Email is often faster because we can attach example recordings and a written quote, but for short-notice or sensitive enquiries the phone is best.*
>
> 3. Add a FAQPage JSON-LD block matching the visible FAQ. Place it inside `<head>` or directly before `</body>` (match existing site pattern — check funerals.html for placement).
>
>    ```json
>    {
>      "@context": "https://schema.org",
>      "@type": "FAQPage",
>      "mainEntity": [
>        {"@type": "Question", "name": "How quickly do you reply?", "acceptedAnswer": {"@type": "Answer", "text": "Usually within one working day, often within a few hours during business hours. For short-notice funeral enquiries we reply same-day."}},
>        {"@type": "Question", "name": "What information should I include in my enquiry?", "acceptedAnswer": {"@type": "Answer", "text": "The date and time, the venue (with postcode if you have it), and the approximate ensemble size you're considering. If you don't know the size, that's fine — tell us the occasion and we'll suggest options."}},
>        {"@type": "Question", "name": "Can I phone instead of emailing?", "acceptedAnswer": {"@type": "Answer", "text": "Yes — call 07356 042468. Email is often faster because we can attach example recordings and a written quote, but for short-notice or sensitive enquiries the phone is best."}}
>      ]
>    }
>    ```
>
> **B. Richmond hub link** (audit §13.2.8):
>
> On `areas/london/richmond.html`, the buried "nearby boroughs" line is the only path back to the London hub. Add an in-body sentence (place in the lede or just below the H1+meta block):
> ```html
> <p>Richmond is one of <a href="../london.html">over thirty London boroughs we cover</a> — see the full list, with named venues, on our London hub page.</p>
> ```
>
> **C. Pricing → London area link** (audit §13.2.9):
>
> On `pricing.html`, in the "What happens next" or equivalent section, add one sentence:
> ```html
> <p>For funerals and weddings in <a href="areas/london.html">London</a>, there are no travel costs.</p>
> ```
>
> **D. Funeral-hymns contradiction reconciliation** (audit §4 HIGH):
>
> On `music-guides/popular-funeral-hymns.html` and `music-guides/abide-with-me.html`:
>
> 1. Find the FAQ block on `popular-funeral-hymns.html` that claims "The Lord's My Shepherd is probably the single most requested funeral hymn" (or similar). Rewrite that FAQ answer (and the matching string in the FAQPage JSON-LD on the same page):
>
>    > Abide With Me and The Lord's My Shepherd are the two most-requested funeral hymns in the UK. Abide With Me is the most-commonly-chosen as a closing hymn; The Lord's My Shepherd is the most widely known.
>
> 2. On `abide-with-me.html`, find any visible claim that Abide With Me "comes up more often than any other" or similar. Rewrite to match the same language as above.
>
> 3. If the FAQPage JSON-LD on either page contains a string matching the original claim, rewrite it to match the new claim.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
>
> grep -q "We typically reply within one working day" contact.html && echo "contact-lede-ok" || echo "MISSING"
> grep -q "How quickly do you reply" contact.html && echo "contact-faq-ok" || echo "MISSING"
> grep -q '"FAQPage"' contact.html && echo "contact-schema-ok" || echo "MISSING"
> grep -q "over thirty London boroughs" areas/london/richmond.html && echo "richmond-link-ok" || echo "MISSING"
> grep -q 'href="areas/london.html"' pricing.html && echo "pricing-link-ok" || echo "MISSING"
> grep -q "two most-requested funeral hymns" music-guides/popular-funeral-hymns.html && echo "popular-funeral-ok" || echo "MISSING"
> grep -q "two most-requested funeral hymns" music-guides/abide-with-me.html && echo "abide-ok" || echo "MISSING"
> ```

- [ ] **Step 2: Verify**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(content): contact FAQ, area-link fixes, funeral-hymns reconcile (P4c)

- contact.html: lede summary + 3-Q FAQ + FAQPage JSON-LD (audit §13.2.5)
- areas/london/richmond.html: body link back to London hub (§13.2.8)
- pricing.html: body link to areas/london.html (§13.2.9)
- popular-funeral-hymns + abide-with-me: standardise the most-requested-hymn
  claim; eliminate cross-page contradiction (audit §4 HIGH)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

### Task 4d: "Ensembles" boilerplate replacement on 26 borough pages

**Files:**
- Modify: 26 borough HTML files identified by `grep -l "Not every occasion calls for the same size of ensemble" areas/london/*.html`

- [ ] **Step 1: Dispatch subagent (with humanistic-writing skill invoked)**

Brief:

> 26 London-borough pages currently share the same boilerplate paragraph beginning *"Not every occasion calls for the same size of ensemble…"*. Replace the shared paragraph on each with a borough-specific 100–150 word paragraph keyed to venues already named on the page.
>
> First, identify the 26 files:
> ```bash
> grep -l "Not every occasion calls for the same size of ensemble" areas/london/*.html
> ```
>
> For each file:
> 1. Read the page.
> 2. Find the "Not every occasion..." paragraph (and any sub-paragraph that's part of the shared block — sometimes spans 2 paragraphs).
> 3. Identify the named venues on the page (look at H1, the lede, and the page's specific local-context sentences). Examples:
>    - westminster.html names: Westminster Abbey, St Martin-in-the-Fields, etc.
>    - barnet.html names: Hendon and Golders Green Crematoriums, Chipping Barnet, Finchley.
> 4. Write a 100–150 word replacement paragraph that:
>    - Keeps the same structural intent (guidance on ensemble size for different occasions).
>    - Names at least 2 venues from the page in the new paragraph.
>    - Is unique — no two boroughs receive the same paragraph.
>    - Does not contradict any existing claim on the page.
>    - Uses the site's house style: factual, second-person where natural, no marketing tells.
>
>    Example (westminster.html):
>    > For Westminster Abbey or St Martin-in-the-Fields we typically suggest a sextet or larger — the volume of the building rewards more voices, and the acoustic carries even quiet passages to the back of the nave. For the smaller City of Westminster chapels and registry offices a quartet works well, particularly for shorter ceremonies. For a graveside or a small private service, two or three singers can be perfect. We're happy to help you decide once we know the venue.
>
>    Example (barnet.html):
>    > Crematorium services at Hendon or Golders Green run to a fixed length (often 30 minutes), so a quartet is usually the right call — large enough to carry a hymn, small enough to fit the room without crowding the family. For larger funeral services in the parish churches of Chipping Barnet or Finchley, a sextet or full choir suits the architecture and the volume of the space. For a graveside, a soloist or duo is often more fitting than a full ensemble.
>
> 5. Replace the original "Not every occasion..." paragraph (and any contiguous shared paragraph) with the new local paragraph. Preserve the surrounding HTML structure (the original is probably in `<p>` or inside a section).
>
> Avoid AI writing tells: no "we believe", no "stunning", no triple-noun lists, no "the perfect blend", no metaphors that don't earn their place. Match the existing high-quality borough page (westminster.html if it has good local prose) as the calibration.
>
> Verification:
> ```bash
> # The shared boilerplate must be gone
> grep -l "Not every occasion calls for the same size of ensemble" areas/london/*.html | wc -l
> # Expected: 0
>
> # All 26 still have an "ensembles" / size-guidance paragraph (semantic)
> # — manual eye check; verify by sampling 3 random files
> ```

- [ ] **Step 2: Verify**

```bash
test "$(grep -l 'Not every occasion calls for the same size of ensemble' areas/london/*.html | wc -l | tr -d ' ')" = "0" && echo "boilerplate-gone" || echo "STILL PRESENT"
./build.sh
```

Manual: read 3 random borough page files (e.g. westminster, barnet, hounslow) and confirm the new paragraphs are unique and venue-specific.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
fix(content): replace shared 'Ensembles' boilerplate on 26 boroughs (P4d)

Audit §4 HIGH — shared 100-word paragraph on 26 London-borough pages
created a 30–40% identical-content overlap across the cluster. Replaced
with borough-specific guidance keyed to venues already named on each
page (Hendon/Golders Green for Barnet, Westminster Abbey/St Martin's for
Westminster, etc).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 5 — Nav + link graph

### Task 5: Nav restructure + comprehensive cross-linking

**Files:**
- Modify: `partials/nav.html` — restructured nav
- Modify: 33 music-guide HTML files — Related guides component
- Modify: 33 borough HTML files — adjacency expansion
- Modify: `music-guides/crematorium-music.html` — borough cross-links section
- Modify: `christmas.html`, `music-guides/corporate-carol-service.html`, `music-guides/office-carol-service-planning.html`, `music-guides/company-christmas-party-entertainment.html` — corporate.html cross-links
- Modify: ~6 borough pages with named crematoria — back-link to crematorium guide

- [ ] **Step 1: Dispatch subagent**

Brief:
>
> Five linked changes. **Run `./build.sh` after each substep** so the nav partial gets re-inlined into all pages.
>
> **A. `partials/nav.html` restructure** (audit §7 CRITICAL):
>
> Current `<ul id="nav-menu">` items in order: Home, About, Services, Listen, Music Guides (with dropdown of weddings/funerals/christmas filter URLs and Browse all), Pricing, Contact.
>
> Restructure to: Home, About, Services, Weddings, Funerals, Corporate, Christmas, Listen, Music Guides (dropdown unchanged: weddings/funerals/christmas filters + Browse all), Pricing, Contact.
>
> Keep all existing aria attributes and the dropdown structure for Music Guides. Just add four new top-level direct-link items between Services and Listen:
> ```html
> <li><a href="/weddings.html">Weddings</a></li>
> <li><a href="/funerals.html">Funerals</a></li>
> <li><a href="/corporate.html">Corporate</a></li>
> <li><a href="/christmas.html">Christmas</a></li>
> ```
>
> Run `./build.sh`. Open one rebuilt page and confirm the nav structure inlined cleanly.
>
> **B. Corporate.html cross-links** (audit §7 CRITICAL):
>
> Add a body-content link to `corporate.html` from each of these pages — anchor text and surrounding sentence as below:
>
> 1. `christmas.html`: somewhere in the existing body, add a sentence: *"For company Christmas parties, awards dinners, and year-round corporate events, see also our <a href="corporate.html">corporate music page</a>."* (Place near a "for businesses" mention if one exists; else at the end of the lede.)
>
> 2. `music-guides/corporate-carol-service.html`: in the lede or first body section, link the phrase "corporate event music" or similar to `/corporate.html` directly.
>
> 3. `music-guides/office-carol-service-planning.html`: in the lede or first body section, link to `/corporate.html` (anchor: "live music for corporate events").
>
> 4. `music-guides/company-christmas-party-entertainment.html`: same — link to `/corporate.html` from a contextually appropriate phrase.
>
> Each must be a body-content link, not a footer or nav link. Each link must be on a unique page (4 new inbound links to corporate.html).
>
> **C. Related guides component** on 33 music guides (audit §7 MEDIUM):
>
> At the bottom of every guide (just before the closing `</main>` or before the footer-include partial marker), insert a "Related guides" section linking the relevant pillar + B2B page + 2–3 sibling guides. The pillar/B2B routing is by topic:
>
> - **Wedding-music guides** → pillar = `weddings.html`, B2B = `for-wedding-planners.html`
> - **Funeral-music guides** → pillar = `funerals.html`, B2B = `for-funeral-directors.html`
> - **Christmas/carol guides** → pillar = `christmas.html`, B2B = `for-event-managers.html` (Phase 6 will create this; if it doesn't exist yet at edit time, link to it anyway — Phase 6 ships in the same PR)
> - **General/hub guides** (`hiring-a-choir.html`) → pillar = `services.html`, B2B = both for-funeral-directors and for-wedding-planners
>
> Sibling guides (2–3 per guide) — use this static map (subagent must respect it exactly):
>
> ```
> abide-with-me → popular-funeral-hymns, be-thou-my-vision-funeral-hymn, funeral-music-guide
> be-thou-my-vision-wedding-hymn → choosing-wedding-hymns, jerusalem, wedding-ceremony-music
> be-thou-my-vision-funeral-hymn → abide-with-me, popular-funeral-hymns, funeral-music-guide
> catholic-funeral-hymns → popular-funeral-hymns, funeral-music-guide, abide-with-me
> celebration-of-life-music → non-religious-funeral-music, funeral-music-guide, memorial-service-planning
> choosing-wedding-hymns → be-thou-my-vision-wedding-hymn, jerusalem, wedding-ceremony-music
> christmas-carols-guide → christmas-choir-hire, corporate-carol-service, office-carol-service-planning
> christmas-choir-hire → christmas-carols-guide, corporate-carol-service, company-christmas-party-entertainment
> company-christmas-party-entertainment → corporate-carol-service, christmas-choir-hire, office-carol-service-planning
> corporate-carol-service → office-carol-service-planning, christmas-choir-hire, company-christmas-party-entertainment
> crematorium-music → funeral-music-guide, popular-funeral-hymns, funeral-music-costs
> funeral-choir-guide → funeral-music-guide, hiring-a-choir, popular-funeral-hymns
> funeral-music-costs → hiring-a-choir, funeral-music-guide, funeral-choir-guide
> funeral-music-guide → popular-funeral-hymns, funeral-songs, hiring-a-choir
> funeral-songs → popular-funeral-hymns, non-religious-funeral-music, celebration-of-life-music
> hiring-a-choir → wedding-choir-guide, funeral-choir-guide, funeral-music-costs
> jerusalem → choosing-wedding-hymns, be-thou-my-vision-wedding-hymn, wedding-ceremony-music
> lesser-known-wedding-choral-pieces → wedding-choral-repertoire, wedding-ceremony-music, choosing-wedding-hymns
> memorial-service-planning → celebration-of-life-music, funeral-music-guide, popular-funeral-hymns
> non-religious-funeral-music → celebration-of-life-music, funeral-songs, funeral-music-guide
> office-carol-service-planning → corporate-carol-service, christmas-choir-hire, company-christmas-party-entertainment
> popular-funeral-hymns → abide-with-me, be-thou-my-vision-funeral-hymn, funeral-music-guide
> popular-wedding-organ-music → wedding-organ-repertoire, wedding-organist-guide, wedding-ceremony-music
> wedding-ceremony-music → choosing-wedding-hymns, wedding-music-ideas, wedding-readings-and-music
> wedding-choir-guide → wedding-ceremony-music, hiring-a-choir, choosing-wedding-hymns
> wedding-choral-repertoire → wedding-ceremony-music, lesser-known-wedding-choral-pieces, choosing-wedding-hymns
> wedding-music-costs → wedding-ceremony-music, hiring-a-choir, wedding-choir-guide
> wedding-music-ideas → wedding-ceremony-music, choosing-wedding-hymns, wedding-readings-and-music
> wedding-organ-pop-songs → wedding-organ-repertoire, wedding-pop-songs-choir, popular-wedding-organ-music
> wedding-organ-repertoire → popular-wedding-organ-music, wedding-organist-guide, wedding-organ-pop-songs
> wedding-organist-guide → wedding-organ-repertoire, popular-wedding-organ-music, wedding-ceremony-music
> wedding-pop-songs-choir → wedding-music-ideas, wedding-organ-pop-songs, wedding-ceremony-music
> wedding-readings-and-music → wedding-ceremony-music, wedding-music-ideas, choosing-wedding-hymns
> ```
>
> The HTML pattern (insert at end of `<main>`):
> ```html
> <section class="related-guides">
>   <h2>Related</h2>
>   <p><strong>If you're planning a [wedding/funeral/etc]</strong> — see our <a href="../<pillar>.html"><pillar-name></a> page or <a href="../<b2b>.html">information for [planners/directors/event managers]</a>.</p>
>   <ul>
>     <li><a href="<sibling1>.html"><sibling1-title></a></li>
>     <li><a href="<sibling2>.html"><sibling2-title></a></li>
>     <li><a href="<sibling3>.html"><sibling3-title></a></li>
>   </ul>
> </section>
> ```
>
> Sibling-title comes from the sibling page's `<title>` tag (without brand suffix — Phase 3 should have already stripped it).
>
> If a sibling page has the section already from a previous run, replace it (idempotent).
>
> **D. Borough adjacency expansion** (audit §7 MEDIUM):
>
> Each London-borough page (33 files in `areas/london/`) has an existing "Nearby boroughs" block with 2–4 links. Expand any with fewer than 4 to have 4–6 links, using this static adjacency map:
>
> ```
> westminster → kensington-chelsea, camden, lambeth, southwark, city-of-london
> city-of-london → westminster, southwark, tower-hamlets, hackney, islington
> kensington-chelsea → westminster, hammersmith-fulham, wandsworth, lambeth, camden
> camden → westminster, islington, haringey, brent, city-of-london
> islington → camden, hackney, haringey, city-of-london, tower-hamlets
> barnet → enfield, harrow, brent, camden, haringey
> enfield → barnet, haringey, waltham-forest, hackney
> haringey → camden, islington, barnet, enfield, hackney, waltham-forest
> hackney → islington, tower-hamlets, haringey, waltham-forest, newham, city-of-london
> tower-hamlets → city-of-london, hackney, newham, southwark, islington
> waltham-forest → haringey, hackney, newham, redbridge, enfield
> brent → barnet, camden, harrow, ealing, westminster, kensington-chelsea
> harrow → barnet, brent, hillingdon, ealing
> newham → tower-hamlets, hackney, waltham-forest, redbridge, barking-dagenham, greenwich
> redbridge → waltham-forest, newham, havering, barking-dagenham
> havering → redbridge, barking-dagenham, newham
> barking-dagenham → newham, redbridge, havering, greenwich
> southwark → city-of-london, lambeth, lewisham, tower-hamlets, westminster
> lambeth → westminster, southwark, kensington-chelsea, wandsworth, lewisham, croydon
> lewisham → southwark, lambeth, greenwich, bromley, croydon
> greenwich → lewisham, bromley, bexley, newham, tower-hamlets
> bromley → lewisham, croydon, greenwich, bexley
> croydon → lambeth, lewisham, bromley, sutton, merton
> bexley → greenwich, bromley
> hammersmith-fulham → kensington-chelsea, ealing, hounslow, wandsworth, westminster
> ealing → brent, hammersmith-fulham, hounslow, hillingdon, harrow
> hounslow → ealing, hammersmith-fulham, richmond, hillingdon
> hillingdon → harrow, ealing, hounslow
> richmond → hounslow, kingston, wandsworth, hammersmith-fulham
> kingston → richmond, merton, sutton
> wandsworth → kensington-chelsea, lambeth, merton, richmond, hammersmith-fulham
> merton → wandsworth, kingston, croydon, sutton, lambeth
> sutton → merton, croydon, kingston
> ```
>
> For each borough, replace the existing "Nearby boroughs" block's link list with the full adjacency list above (4–6 entries each). Anchor text = display name from the page's H1 (e.g. "Kensington & Chelsea" not "kensington-chelsea").
>
> **E. Crematorium-music ↔ borough cross-links** (audit §7 MEDIUM):
>
> 1. On `music-guides/crematorium-music.html`, add a new section near the bottom (before "Related guides"):
>    ```html
>    <section class="local-coverage">
>      <h2>Crematoria we serve in London</h2>
>      <ul>
>        <li><a href="../areas/london/barnet.html">Hendon and Golders Green Crematoriums (Barnet)</a></li>
>        <li><a href="../areas/london/hounslow.html">West London Crematorium (Hounslow)</a></li>
>        <li><a href="../areas/london/havering.html">South Essex Crematorium (Havering)</a></li>
>        <li><a href="../areas/london/southwark.html">Honor Oak Crematorium (Southwark)</a></li>
>        <li><a href="../areas/london/lewisham.html">Hither Green Crematorium (Lewisham)</a></li>
>        <li><a href="../areas/london/greenwich.html">Eltham Crematorium (Greenwich)</a></li>
>        <li><a href="../areas/london/enfield.html">Enfield Crematorium (Enfield)</a></li>
>        <li><a href="../areas/london/redbridge.html">Forest Park Crematorium (Redbridge)</a></li>
>        <li><a href="../areas/london/newham.html">East London Crematorium (Newham)</a></li>
>        <li><a href="../areas/london/wandsworth.html">Putney Vale Crematorium (Wandsworth)</a></li>
>        <li><a href="../areas/london/ealing.html">South West Middlesex Crematorium (Ealing)</a></li>
>        <li><a href="../areas/london/richmond.html">Mortlake Crematorium (Richmond upon Thames)</a></li>
>        <li><a href="../areas/london/kingston.html">Kingston Crematorium (Kingston upon Thames)</a></li>
>        <li><a href="../areas/london/merton.html">South London Crematorium (Merton)</a></li>
>        <li><a href="../areas/london/sutton.html">North East Surrey Crematorium (Sutton)</a></li>
>      </ul>
>    </section>
>    ```
>
> 2. On each of the 15 borough pages named above, add one body-content sentence linking back to the guide. Place near the existing crematorium mention (each page already names its crematorium). Anchor text varies — example for Barnet:
>    ```html
>    <p>For practical guidance on music at crematorium services — timing, acoustics, and making a shorter service meaningful — see our <a href="../../music-guides/crematorium-music.html">guide to crematorium music</a>.</p>
>    ```
>    Adapt the surrounding sentence to flow naturally with the page's existing prose.
>
> Run `./build.sh` after all substeps complete.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
>
> # A. nav has all 4 commercial pillars as direct top-level links
> for href in /weddings.html /funerals.html /corporate.html /christmas.html; do
>   grep -q "<li><a href=\"$href\">" partials/nav.html && echo "nav-$href: ok" || echo "nav-$href: MISSING"
> done
>
> # B. corporate.html inbound count (target: ≥6 — services + 4 new + nav inline)
> grep -lE 'href="[^"]*corporate\.html"' --include="*.html" -r . | grep -v partials | grep -v node_modules | wc -l
> # Expected: ≥6 (every page now has nav-link to corporate via partial; raw inbound count from non-nav links should be ≥5: services.html + christmas.html + 3 corporate guides)
>
> # C. Related guides on 33 guides
> python3 -c '
> import glob
> missing = []
> for fp in glob.glob("music-guides/*.html"):
>     if fp.endswith("index.html"): continue
>     with open(fp) as f: t = f.read()
>     if "related-guides" not in t: missing.append(fp)
> print("Related guides missing:", missing)
> '
> # Expected: Related guides missing: []
>
> # E. Crematorium guide has the new section
> grep -q "Crematoria we serve in London" music-guides/crematorium-music.html && echo "ok" || echo "MISSING"
>
> # E. Borough back-links — 15 boroughs each link to crematorium-music guide
> for b in barnet hounslow havering southwark lewisham greenwich enfield redbridge newham wandsworth ealing richmond kingston merton sutton; do
>   grep -q "music-guides/crematorium-music.html" "areas/london/$b.html" && echo "$b: ok" || echo "$b: MISSING"
> done
> ```

- [ ] **Step 2: Verify all checks pass**

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(nav): nav restructure + comprehensive internal linking (P5)

- partials/nav.html: 4 commercial pillars (Weddings/Funerals/Corporate/
  Christmas) as first-class top-level links; Music Guides retains dropdown
- corporate.html: 4 new inbound links from christmas.html and the 3
  corporate-themed guides (audit §7 CRITICAL — was at 1 inbound link)
- 33 music guides: 'Related guides' component (pillar + B2B + 3 siblings)
- 33 borough pages: adjacency expanded to 4–6 nearby boroughs each
- crematorium-music.html: 'Crematoria we serve in London' section with
  15 borough links; reciprocal links from each borough page

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 6 — New pages (parallel)

This phase dispatches 5 subagents in parallel. They work on independent files — no overlap. After all 5 return, the main session updates `sitemap.xml` and `llms.txt` to register the 4 new pages.

### Task 6: Dispatch 5 parallel new-page subagents

**Files:**
- Create: `for-event-managers.html`
- Create: `music-guides/best-wedding-choirs-london.html`
- Create: `music-guides/best-christmas-carol-singers.html`
- Create: `music-guides/best-funeral-singers-london.html`
- Modify: `areas/index.html` (expansion)

- [ ] **Step 1: Read reference files (main session does this — context for spawning subagents)**

The main session reads each of these so the subagent prompts can quote concrete patterns:
- `for-wedding-planners.html` (template for Task 6.1's for-event-managers.html — same structure, different audience)
- `music-guides/abide-with-me.html` (template for buyer's guides — high-quality long-form guide structure)
- `music-guides/funeral-music-guide.html` (alternate template for buyer's guides)
- `areas/index.html` (current state for expansion)
- `data/seo-fix-discovered-urls.yml` (for any schema URLs)

- [ ] **Step 2: Dispatch all 5 subagents in a single message**

Each Agent call uses `subagent_type: general-purpose`. All 5 dispatched in one message for parallel execution.

**Subagent 6.1 brief — for-event-managers.html:**

> Create a new page at `for-event-managers.html` (repo root). Mirror the structure of `for-wedding-planners.html` (read it first for the template). Audience: corporate event managers booking choirs/singers for awards dinners, product launches, charity galas, conferences, summer parties, client entertainment.
>
> Required sections (in order):
> 1. `<head>`: title `For Event Managers — corporate music bookings | LCS`, meta description ≤160 chars, canonical, OG tags, hreflang. Use the existing for-wedding-planners.html as the pattern verbatim, just changing the title and description.
> 2. Build pipeline markers: `@include-start partials/nav.html` and `@include-end` for nav; same for footer. Match for-wedding-planners.html's marker placement.
> 3. H1 + visible byline (`<p class="guide-meta">By Luca Wetherall, Artistic Director &amp; Tutor in Music, University of Oxford</p>`) + last-updated meta.
> 4. Lede paragraph addressing event managers directly.
> 5. "How we work with event managers" section (lead times, format options, briefing process, public-liability evidence).
> 6. "What your delegates and clients receive" section.
> 7. "Booking and invoicing" section (PO process, late invoicing, terms).
> 8. "Useful resources for event managers" section with 3–4 guide links: corporate-carol-service, office-carol-service-planning, company-christmas-party-entertainment, christmas-choir-hire.
> 9. FAQ section (5 questions) — example questions:
>    - "Can you provide a quote on a PO basis?"
>    - "How far in advance do we need to book?"
>    - "Do you carry public liability insurance?"
>    - "Can you perform without amplification in large venues?"
>    - "What ensemble size is right for a 200-person awards dinner?"
> 10. CTA section linking to `contact.html`.
> 11. Related guides + pillar links (corporate.html, christmas.html).
> 12. Two JSON-LD blocks:
>     - `Service` with `@type: ProfessionalService`, name, provider (@id reference), areaServed, dateModified, plus `priceRange`.
>     - `FAQPage` matching the visible FAQ.
>
> Word count target: 900–1,200.
>
> Voice: humanistic. No AI tells (no "stunning", no "we believe", no triple-noun lists, no "the perfect blend"). Match the register of the existing for-wedding-planners.html.
>
> Verification (run yourself before reporting back):
> ```bash
> ./build.sh
> python3 validate_jsonld.py
> wc -w for-event-managers.html
> grep -c 'href="contact.html"' for-event-managers.html  # should be ≥1
> grep -q '"FAQPage"' for-event-managers.html && echo "FAQPage-ok" || echo "FAQPage-MISSING"
> grep -q '"ProfessionalService"' for-event-managers.html && echo "Service-ok" || echo "Service-MISSING"
> ```
>
> Report file size + verification output.

**Subagent 6.2 brief — best-wedding-choirs-london.html:**

> Create `music-guides/best-wedding-choirs-london.html` — a buyer's-guide editorial page targeting the directory-locked query "wedding choirs London". Use `music-guides/abide-with-me.html` as the structural template for guide pages.
>
> Required structure:
> 1. `<head>`: title `Best wedding choirs in London — what to look for`, meta description ≤160 chars (e.g. *"How to choose a wedding choir in London — what qualifications to look for, ensemble sizes, price ranges, and the questions to ask any provider before booking."*), canonical, OG, hreflang. Match the existing music-guide template.
> 2. Build markers (nav + footer partials).
> 3. H1: "Best wedding choirs in London — what to look for"
> 4. Visible byline + published date: `<p class="guide-meta">By Luca Wetherall, Artistic Director &amp; Tutor in Music, University of Oxford · Published May 2026</p>`.
> 5. Lede paragraph (a high-quality, citable opening — 100–150 words).
> 6. "What to look for in a wedding choir" — 4–5 paragraphs of qualifying criteria (training/credentials, repertoire breadth, ensemble cohesion, professionalism, references). Substantive, not platitudes.
> 7. "Ensemble size guidance" — match the size to the venue (Westminster Abbey vs registry office vs country house chapel).
> 8. "Price ranges across the market in 2026" — give honest market ranges, not just LCS pricing. *Solo singer £200–£300; quartet £900–£1,400; sextet £1,400–£2,000; full choir £2,000–£3,500.* Position LCS within these ranges (the credibility play).
> 9. "Six questions to ask any provider" — bullet list.
> 10. "How LCS approaches this" — restrained single section, links to weddings.html and for-wedding-planners.html. NOT the lead.
> 11. FAQ block (4–6 questions, e.g. *Should I hire a choir or just a soloist? · How early should I book? · Can a choir sing pop as well as classical? · Is amplification needed in a large church? · Do choirs travel outside London?*) + FAQPage JSON-LD.
> 12. Related guides section (siblings: choosing-wedding-hymns, wedding-choir-guide, jerusalem; pillar: weddings.html; B2B: for-wedding-planners.html).
> 13. Article JSON-LD with author, publisher (@id ref), datePublished `2026-05-08`, dateModified `2026-05-08`, image (use `/assets/og-image.png`), wordCount, speakable.
>
> Word count target: 1,800–2,200.
>
> Voice: humanistic. Cite specific named entities where possible (Royal Academy of Music, Royal College of Music, Westminster Abbey). No AI writing tells.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
> wc -w music-guides/best-wedding-choirs-london.html
> grep -q '"FAQPage"' music-guides/best-wedding-choirs-london.html && echo "FAQPage-ok"
> grep -q '"Article"' music-guides/best-wedding-choirs-london.html && echo "Article-ok"
> grep -q "weddings.html" music-guides/best-wedding-choirs-london.html && echo "pillar-link-ok"
> ```

**Subagent 6.3 brief — best-christmas-carol-singers.html:**

> Same shape as 6.2 but Christmas-vertical. Path: `music-guides/best-christmas-carol-singers.html`. Title: `Best Christmas carol singers — what to look for when hiring`. Audience: corporate event organisers + event managers. Pillar: `christmas.html`. B2B: `for-event-managers.html` (created in 6.1). Sibling guides: christmas-carols-guide, corporate-carol-service, christmas-choir-hire.
>
> Price-range section: solo £200–£300; carol-singing quartet £700–£1,200; sextet £1,200–£1,800; full carollers (8+) £1,800–£3,500.
>
> Same word-count target, same JSON-LD shape, same verification.

**Subagent 6.4 brief — best-funeral-singers-london.html:**

> Same shape, funeral vertical. Path: `music-guides/best-funeral-singers-london.html`. Title: `Best funeral singers in London — what to look for`. Pillar: `funerals.html`. B2B: `for-funeral-directors.html`. Sibling guides: popular-funeral-hymns, abide-with-me, funeral-music-guide.
>
> Price-range section: soloist £200–£300; quartet £900–£1,400; sextet £1,400–£2,000; full choir £2,000–£3,500.
>
> Tone: gentler than the wedding/christmas versions. Address grief context appropriately. No marketing tells; no "let us help you" phrasing — be useful and direct.
>
> Same word-count target, same JSON-LD shape, same verification.

**Subagent 6.5 brief — areas/index.html expansion:**

> Expand `areas/index.html` from ~670 to 1,000–1,200 words. The existing list-of-area-links must be retained verbatim — do not delete the link list.
>
> Insertions (above the link list):
> 1. New 400–600-word editorial introduction explaining how the service works geographically. Cover:
>    - The London-borough cluster: how the 33 boroughs are covered (hyper-local, named venues per borough).
>    - Outer cities: how lead times work for Manchester, Liverpool, Cambridge, Oxford, etc.
>    - Travel-cost logic: no travel cost within London; outside London, transparent travel fee structure.
>    - The relationship between borough and city pages.
>    - When to use the city page vs the borough page for SEO/booking purposes.
> 2. A 4-question FAQ:
>    - "How quickly can you arrange singers in cities outside London?"
>    - "Do you charge travel for outer cities?"
>    - "Can you cover venues outside the listed cities?"
>    - "How do you choose musicians for each location?"
> 3. FAQPage JSON-LD matching the FAQ.
>
> Below the link list (unchanged), preserve everything that exists.
>
> Verification:
> ```bash
> ./build.sh
> python3 validate_jsonld.py
> wc -w areas/index.html
> grep -q '"FAQPage"' areas/index.html && echo "FAQPage-ok"
> # All existing area-page links still present
> grep -c 'href="' areas/index.html  # should be ≥53 (existing area links + nav/footer + FAQ-internal)
> ```

- [ ] **Step 3: After all 5 subagents return, update sitemap.xml**

Add 4 new `<url>` entries (alphabetised by URL within the file's existing structure if possible):

```xml
<url>
  <loc>https://londonchoralservice.com/for-event-managers.html</loc>
  <lastmod>2026-05-08</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.7</priority>
</url>
<url>
  <loc>https://londonchoralservice.com/music-guides/best-christmas-carol-singers.html</loc>
  <lastmod>2026-05-08</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.6</priority>
</url>
<url>
  <loc>https://londonchoralservice.com/music-guides/best-funeral-singers-london.html</loc>
  <lastmod>2026-05-08</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.6</priority>
</url>
<url>
  <loc>https://londonchoralservice.com/music-guides/best-wedding-choirs-london.html</loc>
  <lastmod>2026-05-08</lastmod>
  <changefreq>monthly</changefreq>
  <priority>0.6</priority>
</url>
```

- [ ] **Step 4: Update llms.txt**

Under `## Main Pages`, add (alphabetised):
```
- [For Event Managers](https://londonchoralservice.com/for-event-managers.html): How we work with corporate event managers — booking lead times, public-liability cover, formal hire process, capacity for large-format venues
```

Under `## Music Guides`, add (alphabetised):
```
- [Best Christmas Carol Singers](https://londonchoralservice.com/music-guides/best-christmas-carol-singers.html): What to look for when hiring carol singers — qualifications, ensemble sizes, market price ranges, and the questions to ask any provider
- [Best Funeral Singers in London](https://londonchoralservice.com/music-guides/best-funeral-singers-london.html): How to choose funeral singers in London — what to look for, ensemble sizes, price ranges, and questions to ask
- [Best Wedding Choirs in London](https://londonchoralservice.com/music-guides/best-wedding-choirs-london.html): How to choose a wedding choir in London — qualifications, ensemble sizes, price ranges, and the questions to ask any provider
```

- [ ] **Step 5: Update music-guides/index.html ItemList**

Add the 3 new buyer's-guide pages to the `ItemList` JSON-LD block on `music-guides/index.html`. Preserve existing entries; add 3 new `ListItem` entries with sequential `position` values.

- [ ] **Step 6: Run build + verify**

```bash
./build.sh
python3 validate_jsonld.py

# All 4 new pages exist
for f in for-event-managers.html music-guides/best-wedding-choirs-london.html music-guides/best-christmas-carol-singers.html music-guides/best-funeral-singers-london.html; do
  test -f "$f" && echo "$f: exists" || echo "$f: MISSING"
done

# All 4 in sitemap
for f in for-event-managers.html music-guides/best-wedding-choirs-london.html music-guides/best-christmas-carol-singers.html music-guides/best-funeral-singers-london.html; do
  grep -q "$f" sitemap.xml && echo "$f: sitemap-ok" || echo "$f: sitemap-MISSING"
done

# All 4 in llms.txt
for f in for-event-managers best-wedding-choirs-london best-christmas-carol-singers best-funeral-singers-london; do
  grep -q "$f" llms.txt && echo "$f: llms-ok" || echo "$f: llms-MISSING"
done
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat(content): 4 new pages + areas/index expansion (P6)

- /for-event-managers.html: corporate B2B pillar mirroring
  for-wedding-planners + for-funeral-directors structure (audit §5 MEDIUM)
- /music-guides/best-wedding-choirs-london.html: editorial buyer's guide
  for the directory-locked 'wedding choirs London' query (audit §10)
- /music-guides/best-christmas-carol-singers.html: same, Christmas vertical
- /music-guides/best-funeral-singers-london.html: same, funeral vertical
- areas/index.html: expanded 670 → 1,000–1,200 words with editorial
  geography intro + 4-Q FAQ + FAQPage JSON-LD (audit §4 MEDIUM)
- sitemap.xml + llms.txt + music-guides/index.html ItemList: register
  4 new pages

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 7 — Performance + tech polish

### Task 7: Font preload + image dimensions + NAP standardisation

**Files:**
- Create: `partials/head-extras.html`
- Modify: All HTML files (insert head-extras include in `<head>`)
- Modify: All HTML files with `<img>` or `<picture>` (audit estimates ~18 img tags total)
- Modify: All HTML files + schema (NAP phone format)

- [ ] **Step 1: Dispatch subagent**

Brief:

> Three performance/polish fixes.
>
> **A. Font preload** (audit §13.3.1 HIGH):
>
> 1. Create `partials/head-extras.html` with two preload tags (the build pipeline supports `@include-start`/`@include-end` markers anywhere in a file):
>    ```html
>    <link rel="preload" href="/fonts/cormorant-garamond.woff2" as="font" type="font/woff2" crossorigin>
>    <link rel="preload" href="/fonts/source-serif-4.woff2" as="font" type="font/woff2" crossorigin>
>    ```
> 2. In every HTML file's `<head>`, add the include marker block. Find the existing `<meta charset>` tag (or `<title>`, whichever is first), and insert immediately after it:
>    ```html
>    <!-- @include-start partials/head-extras.html -->
>    <link rel="preload" href="/fonts/cormorant-garamond.woff2" as="font" type="font/woff2" crossorigin>
>    <link rel="preload" href="/fonts/source-serif-4.woff2" as="font" type="font/woff2" crossorigin>
>    <!-- @include-end partials/head-extras.html -->
>    ```
>    The build script will refresh the inline content on every build; the include markers ensure the partial stays canonical.
>
>    Files: every `*.html` in repo root, `areas/`, `areas/london/`, `music-guides/`. Skip `partials/` and noindex pages (`404.html`, `thank-you.html`, `privacy.html` — but actually do add to those too; preload doesn't hurt).
>
> **B. Image width and height attributes** (audit §13.3.2 HIGH):
>
> Find every `<img>` or `<picture><source>` element across all HTML files. For each one without explicit `width` and `height` attributes, add them.
>
> Workflow per image:
> - If the `src` attribute references a file in `assets/`, read the file at that path to determine intrinsic pixel dimensions. Use the Python `PIL`/`Pillow` library if available, or use `file <path>` + parsing as a fallback.
> - YouTube facade thumbs (`maxresdefault.jpg` URLs from `i.ytimg.com`) are 1280×720.
> - For SVG `src` references, omit width/height (vector — no CLS issue from layout).
>
> Verification: every `<img>` in a non-partial HTML must have both `width=` and `height=` attributes (or be an SVG).
>
> ```bash
> python3 -c '
> import glob, re
> bad = []
> img_pattern = re.compile(r"<img\b([^>]+)>", re.IGNORECASE)
> for fp in glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") + glob.glob("music-guides/*.html"):
>     with open(fp) as f: html = f.read()
>     for m in img_pattern.finditer(html):
>         attrs = m.group(1)
>         if 'src=".svg"' in attrs.lower() or '.svg"' in attrs.lower(): continue
>         if "width=" not in attrs or "height=" not in attrs:
>             bad.append((fp, m.group(0)[:120]))
> for b in bad: print(b)
> print(f"Total imgs without width/height: {len(bad)}")
> '
> # Expected: Total imgs without width/height: 0
> ```
>
> **C. NAP phone E.164 standardisation** (audit §5 HIGH):
>
> 1. In every JSON-LD block on every HTML file, the `telephone` property must be `"+447356042468"`. Replace any of `07356 042468`, `07356042468`, `+44 7356 042468` etc. inside JSON-LD with `+447356042468`.
> 2. Visible HTML phone numbers stay as `07356 042468` (UK-readability). Don't change them.
> 3. `llms.txt` line containing the phone: keep as `07356 042468` (matches visible site).
>
> Verification:
> ```bash
> # All schema phone is E.164
> python3 -c '
> import glob, json, re
> pattern = re.compile(r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>", re.DOTALL)
> bad = []
> for fp in sorted(glob.glob("*.html") + glob.glob("areas/*.html") + glob.glob("areas/**/*.html") + glob.glob("music-guides/*.html")):
>     with open(fp) as f: html = f.read()
>     for m in pattern.finditer(html):
>         data = json.loads(m.group(1))
>         def walk(o):
>             if isinstance(o, dict):
>                 t = o.get("telephone", "")
>                 if t and t != "+447356042468": bad.append((fp, t)); return
>                 for v in o.values(): walk(v)
>             elif isinstance(o, list):
>                 for v in o: walk(v)
>         walk(data)
> for b in bad: print(b)
> print(f"Bad telephone: {len(bad)}")
> '
> # Expected: Bad telephone: 0
> ```
>
> Run `./build.sh` after all substeps. Report files modified.

- [ ] **Step 2: Verify**

Run all three verification scripts.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
perf: font preload + img width/height + NAP E.164 schema (P7)

- Add font preload tags via new partials/head-extras.html partial
  (LCP improvement — fonts can fetch without waiting for CSS parse)
- Add explicit width/height attributes on all <img> tags (CLS prevention)
- Standardise schema telephone to E.164 (+447356042468); visible HTML
  retains UK-readable 07356 042468

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Phase 8 — Verification

### Task 8: Full-site verification + PR

**Files:**
- Create (then delete): `scripts/audit-fix-checks.py`

- [ ] **Step 1: Write the verification script**

```python
#!/usr/bin/env python3
# scripts/audit-fix-checks.py — comprehensive post-fix verification
import glob, json, re, sys
import html as htmllib

errors = []

def check(name, ok, detail=""):
    if ok:
        print(f"PASS  {name}")
    else:
        errors.append(name)
        print(f"FAIL  {name}: {detail}")

pattern_jsonld = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)

all_html = sorted(set(
    glob.glob("*.html") +
    glob.glob("areas/*.html") +
    glob.glob("areas/**/*.html", recursive=True) +
    glob.glob("music-guides/*.html")
))
indexable = [f for f in all_html if f not in ("404.html", "thank-you.html", "privacy.html") and not f.startswith("partials/")]

# 1. AggregateRating count = 2
ar_pages = []
for fp in indexable:
    with open(fp) as f: html = f.read()
    has = False
    for m in pattern_jsonld.finditer(html):
        try: data = json.loads(m.group(1))
        except: continue
        def walk(o):
            nonlocal has
            if isinstance(o, dict):
                if "aggregateRating" in o: has = True; return
                if "review" in o and isinstance(o["review"], list) and o["review"]: has = True; return
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(data)
        if has: break
    if has: ar_pages.append(fp)
check("AggregateRating limited to index + about", set(ar_pages) <= {"index.html", "about.html"}, f"Found on: {ar_pages}")

# 2. HowTo removed
howto_pages = [f for f in indexable if '"HowTo"' in open(f).read()]
check("HowTo schema removed from all pages", len(howto_pages) == 0, f"Still on: {howto_pages}")

# 3. priceValidUntil on 4 service pages
for f in ["weddings.html", "funerals.html", "corporate.html", "christmas.html"]:
    check(f"{f} has priceValidUntil", '"priceValidUntil"' in open(f).read())

# 4. Article.image on all 33 + 3 new buyer guides
guides = [f for f in glob.glob("music-guides/*.html") if not f.endswith("index.html")]
missing_img = []
for fp in guides:
    has_img = False
    html = open(fp).read()
    for m in pattern_jsonld.finditer(html):
        try: data = json.loads(m.group(1))
        except: continue
        def walk(o):
            nonlocal has_img
            if isinstance(o, dict):
                t = o.get("@type", "")
                if (t == "Article" or (isinstance(t, list) and "Article" in t)) and "image" in o:
                    has_img = True
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(data)
    if not has_img: missing_img.append(fp)
check("Article.image on all music guides", len(missing_img) == 0, f"Missing: {missing_img}")

# 5. Title length ≤60
over_title = []
for fp in indexable:
    m = re.search(r"<title>([^<]+)</title>", open(fp).read())
    if not m: continue
    t = htmllib.unescape(m.group(1))
    if len(t) > 60: over_title.append((fp, len(t), t))
check("All titles ≤60 chars", len(over_title) == 0, f"Over: {over_title[:5]}")

# 6. Meta description ≤160
over_meta = []
for fp in indexable:
    m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', open(fp).read())
    if not m: continue
    d = htmllib.unescape(m.group(1))
    if len(d) > 160: over_meta.append((fp, len(d)))
check("All meta descriptions ≤160 chars", len(over_meta) == 0, f"Over: {over_meta[:5]}")

# 7. Internal href integrity
import os, os.path
broken = []
EXTS = (".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".woff2", ".ico", ".xml", ".txt", ".pdf", ".webp", ".gif")
for fp in indexable:
    html = open(fp).read()
    for m in re.finditer(r'href="([^"#?]+)"', html):
        link = m.group(1).split("#")[0].split("?")[0]
        if not link: continue
        if link.startswith(("http://", "https://", "mailto:", "tel:", "javascript:")): continue
        # Absolute path: resolve from repo root
        if link.startswith("/"):
            target = link.lstrip("/")
        else:
            # Relative: resolve from file's directory
            target = os.path.normpath(os.path.join(os.path.dirname(fp), link))
        # Bare directories (e.g. "music-guides/") map to <dir>/index.html
        if target == "" or target == ".": continue
        if target.endswith("/") or os.path.isdir(target):
            target_check = os.path.join(target.rstrip("/"), "index.html")
        elif not target.endswith(EXTS):
            # Slug without extension → slug.html
            target_check = target + ".html"
        else:
            target_check = target
        if not os.path.exists(target_check):
            broken.append((fp, link, target_check))
check("All internal hrefs resolve", len(broken) == 0, f"Broken (first 10): {broken[:10]}")

# 8. Sitemap matches indexable files
with open("sitemap.xml") as f: sm = f.read()
sm_urls = re.findall(r"<loc>https://londonchoralservice\.com(/[^<]*)</loc>", sm)
sm_paths = set(u.lstrip("/") if u != "/" else "index.html" for u in sm_urls)
indexable_set = set(indexable)
missing_in_sitemap = indexable_set - sm_paths - {"music-guides/index.html"}  # index hub is already at /music-guides/
extra_in_sitemap = sm_paths - indexable_set - {"index.html"}
check("Sitemap matches indexable files", len(missing_in_sitemap) == 0, f"Missing: {missing_in_sitemap}")

# 9. llms.txt has all 4 new pages
llms = open("llms.txt").read()
for slug in ["for-event-managers", "best-wedding-choirs-london", "best-christmas-carol-singers", "best-funeral-singers-london"]:
    check(f"llms.txt has {slug}", slug in llms)

# 10. Img width/height
img_pat = re.compile(r"<img\b([^>]+)>", re.IGNORECASE)
img_bad = []
for fp in indexable:
    for m in img_pat.finditer(open(fp).read()):
        a = m.group(1)
        if ".svg" in a.lower(): continue
        if "width=" not in a or "height=" not in a:
            img_bad.append((fp, m.group(0)[:80]))
check("All <img> have width/height", len(img_bad) == 0, f"Bad: {img_bad[:5]}")

# 11. NAP phone E.164 in schema
bad_phone = []
for fp in indexable:
    for m in pattern_jsonld.finditer(open(fp).read()):
        try: data = json.loads(m.group(1))
        except: continue
        def walk(o):
            if isinstance(o, dict):
                t = o.get("telephone")
                if t and t != "+447356042468": bad_phone.append((fp, t))
                for v in o.values(): walk(v)
            elif isinstance(o, list):
                for v in o: walk(v)
        walk(data)
check("All schema telephone is +447356042468", len(bad_phone) == 0, f"Bad: {bad_phone[:5]}")

# 12. Font preload present
preload_missing = [f for f in indexable if "cormorant-garamond.woff2" not in open(f).read() or "rel=\"preload\"" not in open(f).read()]
check("Font preload tag on all pages", len(preload_missing) == 0, f"Missing: {preload_missing[:5]}")

# 13. corporate.html inbound link count (excluding nav partial)
import subprocess
inbound = subprocess.run(["grep", "-l", '-E', r'href="[^"]*corporate\.html"', "--include=*.html", "-r", "."], capture_output=True, text=True).stdout.split()
inbound = [f for f in inbound if "partials" not in f and f != "./corporate.html" and "node_modules" not in f]
check("corporate.html has ≥4 non-nav inbound links", len(inbound) >= 4, f"Inbound: {inbound}")

if errors:
    print(f"\n{len(errors)} CHECK(S) FAILED:")
    for e in errors: print(f"  - {e}")
    sys.exit(1)
else:
    print("\nAll checks passed.")
    sys.exit(0)
```

- [ ] **Step 2: Run the verification script**

```bash
mkdir -p scripts
# (write the script content from Step 1 to scripts/audit-fix-checks.py)
python3 scripts/audit-fix-checks.py
```
Expected: `All checks passed.` and exit 0.

- [ ] **Step 3: Run `./build.sh` and `validate_jsonld.py` one final time**

```bash
./build.sh
# Already runs validate_jsonld.py at the end.
```
Expected: exits 0.

- [ ] **Step 4: Visual smoke check**

Open these in a browser (file:// is fine — site is static):
- `index.html`
- `weddings.html`
- `corporate.html`
- `areas/london.html`
- `music-guides/abide-with-me.html`
- `music-guides/best-wedding-choirs-london.html`
- `for-event-managers.html`

Confirm: nav renders with all 4 commercial pillars at top level, no console errors, no obvious layout breaks. Spot-test at 768, 1024, 1280 px viewport widths (developer tools → device toolbar). If the nav wraps or overflows badly at 1024 px, the spec calls for grouping the 4 pillars under an "Occasions ▾" dropdown — implement that fallback in `partials/nav.html`, run `./build.sh`, and recommit.

- [ ] **Step 5: Delete the verification script (it was scaffolding)**

```bash
rm scripts/audit-fix-checks.py
rmdir scripts 2>/dev/null || true
```

- [ ] **Step 6: Final commit + push**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: remove verification scaffolding script (P8)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u origin claude/recursing-johnson-cfffdc
```

- [ ] **Step 7: Open the PR**

```bash
gh pr create --title "fix(seo): comprehensive 2026-05-08 audit fixes (55 findings)" --body "$(cat <<'EOF'
## Summary

Implements every actionable finding from `SEO-AUDIT-2026-05-08.md` (sections 1–13, 55 findings across 13 themes). Items requiring user action (GBP claim, citation building, GSC creds, Fastly headers, etc) are documented in the new `MANUAL-ACTIONS-REQUIRED.md`.

Spec: [docs/superpowers/specs/2026-05-08-seo-audit-fixes-design.md](docs/superpowers/specs/2026-05-08-seo-audit-fixes-design.md)
Plan: [docs/superpowers/plans/2026-05-08-seo-audit-fixes.md](docs/superpowers/plans/2026-05-08-seo-audit-fixes.md)

### Critical fixes (top 5 priorities from audit)

- ✅ Removed sitewide `AggregateRating` from 97 of 99 pages — was a Google review-snippet policy violation
- ✅ `corporate.html` now has 6+ inbound links (was 1) — added to nav + 4 corporate-themed guide cross-links + christmas.html
- ✅ Global nav restructured — Weddings, Funerals, Corporate, Christmas now first-class top-level links
- ⚠️ Review-volume gap: documented in MANUAL-ACTIONS-REQUIRED.md (post-event review workflow needs operational setup)
- ✅ Title-tag truncation fixed across 67+ pages — drop brand suffix on local pages

### High/Medium fixes

- 33 music guides: visible author byline + Article.image + wordCount + speakable + dateModified
- 9 guides: HowTo schema removed (deprecated by Google)
- 6 commercial pillars: visible last-updated date + Service.dateModified
- 4 service pages: AggregateOffer.priceValidUntil
- 53 area pages: H1 fix ("Funeral and wedding choirs in [City]"), Service.provider.@id reference, GeoCoordinates
- 4 video objects: real upload dates + ISO 8601 durations (where discoverable)
- 33 boroughs: 4–6 nearby-borough links each; "Ensembles" boilerplate replaced with venue-specific guidance
- crematorium-music guide ↔ 15 borough cross-links
- 33 guides: "Related guides" component (pillar + B2B + 3 siblings)
- contact.html: opening summary + 3-Q FAQ + FAQPage JSON-LD
- weddings/funerals: extractable price-summary paragraph + inline area links
- funerals.html: humanist paragraph + 2-link cluster + cancellation/replacement statement
- robots.txt: utm/gclid/fbclid/msclkid disallows
- llms.txt: 21 missing guides + freshness signal
- sitemap.xml: typo fix + 4 new entries
- partials/head-extras.html: font preload tags (LCP)
- All `<img>` tags: explicit width/height (CLS)
- All schema telephone: E.164 format

### New pages

- `/for-event-managers.html` (B2B corporate pillar)
- `/music-guides/best-wedding-choirs-london.html`
- `/music-guides/best-christmas-carol-singers.html`
- `/music-guides/best-funeral-singers-london.html`
- `/areas/index.html` expanded 670 → 1,000+ words

## Test plan

- [x] `./build.sh` exits 0
- [x] `python3 validate_jsonld.py` exits 0
- [x] Comprehensive Python verification script passes (13 checks: title/meta length, schema invariants, internal-link integrity, sitemap/llms registration, NAP, preload, img dims, corporate.html link count)
- [ ] Manual visual smoke test on key pages at 768/1024/1280 px (reviewer: please open homepage, corporate.html, music-guides/best-wedding-choirs-london.html and confirm)
- [ ] Run [Rich Results Test](https://search.google.com/test/rich-results?url=https://londonchoralservice.com/music-guides/abide-with-me.html) post-merge — should show no review-snippet eligibility errors
- [ ] Confirm with `pagespeed.web.dev` post-merge that CWV still passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-review checklist

After all 8 phases complete and the PR is open:

1. **Spec coverage** — every audit finding from §1–§13 either has a task that implements it or is in `MANUAL-ACTIONS-REQUIRED.md`. The mapping table in the spec (Appendix B) is the source of truth.
2. **No placeholders** — `data/seo-fix-discovered-urls.yml` may contain `TODO` strings for items not discoverable, and the schema may carry `<!-- TODO: ... -->` comments referencing those — that's the deliberate handling.
3. **Type/path consistency** — every cross-task reference (Phase 5 referring to Phase 6's new pages, Phase 4a referring to `.guide-meta` class which Phase 4 inserts) is consistent.

If any verification check fails, do not mark Phase 8 complete. Investigate, fix, re-run.
