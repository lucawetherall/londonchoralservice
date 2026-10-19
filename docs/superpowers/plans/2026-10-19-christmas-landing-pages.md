# Christmas Landing Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Load `writing-site-copy` and `stop-slop` before writing any visible text, `new-page` before Task 3, and `build-and-verify` before any build.

**Goal:** Make christmas.html the single carolling landing page (films: It's the Most Wonderful Time + Ding Dong), add a church carol services page, merge carol-singers.html into christmas.html behind a click-ID-preserving redirect stub, and record which page each enquiry came from.

**Architecture:** Hand-authored static HTML on GitHub Pages; `./build.sh` inlines CSS and expands partials. Invariants are pinned by a new stdlib-only test script, `tests/test_christmas_pages.py`, in the style of `tests/test_design_markup.py` (collect failures, print `OK: …` or exit 1). No new JS; the forms keep `js/form.js`.

**Tech Stack:** HTML, CSS sources in `css/`, Python 3 tests and generators, Web3Forms + hCaptcha.

**Spec:** `docs/superpowers/specs/2026-10-19-christmas-landing-pages-design.md`

## Global Constraints

- Prices verbatim from `pricing.html` / `christmas-pricing.html`: Small Choir (4) £1,150 · Quintet £1,400 · Sextet £1,600 · Full Choir (8) £2,000 · Chorus (12) £3,000 · organist or pianist £250 · Christmas Eve/Day "around 25%" more · no Christmas uplift · never mention VAT.
- Films: christmas.html hero `csFWUu-r85Y` (It's the Most Wonderful Time of the Year), tracks `zDlSFb74p4E` (Ding Dong! Merrily on High) and `UaVhyyidlTs` (Winter Wonderland). Church page hero `SbvqWglsbMo` (Once in Royal David's City), track `zDlSFb74p4E`. Every embedded film has a matching `VideoObject`.
- No non-Christmas piece (no hymn) appears as a film or track on christmas.html or christmas-carol-services.html. No Carol of the Bells on the church page.
- Testimonials: reuse only James (christmas.html, events), Helen and Laura (church page). Never invent one. No `AggregateRating`/`Review`.
- Form: keep the Web3Forms endpoint, `access_key`, `botcheck`, the `h-captcha-response` check, `ad_measurement`, `data-redirect`. `occasion` stays a field named `occasion` with value `christmas`.
- Meta descriptions 141–161 chars, unique. Canonical + hreflang (en-gb, x-default) + full OG/Twitter on both pages.
- No roster size; no claim to supplement a London cathedral or Westminster Abbey choir; church page says nothing about church hire, verger or the church organist's fees.
- Never hand-edit inlined `<style>` or `@include` regions; edit `css/*` or `partials/*` and run `./build.sh`.
- UK English; parenthetical `&thinsp;&mdash;&thinsp;` is house typography.

## Review Focus

1. A paid visitor on `carol-singers.html?gclid=X&utm_source=google` must end on `christmas.html?gclid=X&utm_source=google` → Task 1 test `stub_preserves_query`.
2. A visitor without JavaScript on the stub still reaches christmas.html → Task 1 test `stub_has_noscript_refresh`.
3. After the sweep, no published page links to `carol-singers.html` (an internal hop through a noindex stub wastes the visit and the link) → Task 5 test `no_links_to_stub`.
4. The form email still carries everything the enquiry assistant reads (`occasion=christmas`, `botcheck`, captcha) plus the new `page` line, on both pages → Task 2/3 test `form_contract`.
5. At 375 px the h1, the price fact and the primary button sit above the fold on both pages, with no horizontal scroll → manual check in Task 6 (`document.documentElement.scrollWidth === 375`; button's `getBoundingClientRect().bottom < 812`).

---

### Task 1: Test harness + carol-singers.html redirect stub

**Files:**
- Create: `tests/test_christmas_pages.py`
- Modify (replace whole file): `carol-singers.html`
- Modify: `tests/test_design_markup.py` (HERO_FILMS: drop `carol-singers.html`; CAPTIONS keep `DINGDONG` only if still a hero elsewhere, else remove)

**Interfaces:**
- Produces: `tests/test_christmas_pages.py` with helpers `read(path) -> str`, `check(cond, msg)`, and one function per invariant; later tasks add functions to it. Run: `python3 tests/test_christmas_pages.py` → `OK: christmas pages` or exit 1.

- [ ] **Step 1: Write the failing tests** `stub_preserves_query`, `stub_has_noscript_refresh`, `stub_is_noindex_canonical`:

```python
s = read('carol-singers.html')
check("location.replace('/christmas.html' + location.search + location.hash)" in s, 'stub must forward query and hash')
check('<noscript><meta http-equiv="refresh" content="0; url=/christmas.html"></noscript>' in s, 'no-JS fallback')
check('<meta name="robots" content="noindex, follow">' in s, 'stub noindex')
check('<link rel="canonical" href="https://londonchoralservice.com/christmas.html">' in s, 'stub canonical')
check('<form' not in s and 'googletagmanager' not in s, 'stub stays minimal')
```

- [ ] **Step 2:** `python3 tests/test_christmas_pages.py` → FAIL on all four.
- [ ] **Step 3: Write the stub.** `<!doctype html>`, `lang="en-GB"`, charset, viewport, `<title>Hire Carol Singers | The London Choral Service</title>`, the canonical, robots, the inline script, the noscript refresh, and a body with one link: "Hire carol singers: continue to our Christmas page" → `/christmas.html`. No `@include` markers, no `<style>` block (the build must leave it alone; confirm `build.sh` skips a page with no markers and no stylesheet link).
- [ ] **Step 4:** test passes; `./build.sh` green; `python3 scripts/stage_site.py` OK; `grep -c carol-singers sitemap.xml` → `0`.
- [ ] **Step 5: Commit** `feat(christmas): turn carol-singers.html into a redirect to christmas.html`.

### Task 2: Rebuild christmas.html as the carolling landing page

**Files:**
- Modify: `christmas.html` (head, JSON-LD, `<main>`; not the inlined style or include regions)
- Modify if a new component is needed: `css/components.css` (e.g. `.hero-facts`, `.btn-primary` if no existing primary button class fits; check `css/components.css` first)
- Modify: `thank-you.html` only if `?from=christmas` copy mentions carol services
- Test: `tests/test_christmas_pages.py`

**Interfaces:**
- Consumes: Task 1 helpers.
- Produces: `#enquiry` form with hidden `page=christmas`; section order fixed below (Task 6 checks it).

- [ ] **Step 1: Write failing tests** `christmas_films`, `christmas_no_hymns`, `christmas_prices`, `form_contract('christmas.html', page='christmas', redirect='thank-you.html?from=christmas')`, `christmas_order`:

```python
c = read('christmas.html')
hero = c.split('class="hero-video"')[1][:1500]
check('csFWUu-r85Y' in hero, 'hero is Most Wonderful Time')
check(set(re.findall(r'data-video="([^"]+)"', c)) == {'csFWUu-r85Y','zDlSFb74p4E','UaVhyyidlTs'}, 'only the three event films')
for vid in ('csFWUu-r85Y','zDlSFb74p4E','UaVhyyidlTs'): check(f'embed/{vid}"' in c, f'VideoObject for {vid}')
for hymn in ('Be Thou My Vision','Guide Me, O Thou','All Things Bright','Carol of the Bells','Blue Christmas'): check(hymn not in c.split('<main')[1], f'{hymn} not on page')
for p in ('£1,150','£1,400','£1,600','£2,000','£3,000'): check(p in c, f'price {p}')
check('VAT' not in c.split('<main')[1], 'no VAT wording')
# form_contract(path, page, redirect):
#   name="occasion" value="christmas"; name="page" value=<page>; name="botcheck"; h-captcha;
#   name="ad_measurement"; data-redirect="<redirect>"; name="event_type"; name="guests"; name="postcode_or_venue";
#   and none of: >Funeral<, >Wedding<, >A funeral director<, >A wedding planner or venue<
# christmas_order: indexes of these markers strictly increase:
#   'class="hero-video"', 'James', 'href="#enquiry"' (mid-page CTA after the films), 'id="enquiry"'
check(c.count('href="/music-guides/') + c.count('href="music-guides/') <= 6 + NAV_FOOTER_GUIDE_LINKS, 'guide wall cut to six')
```

(`NAV_FOOTER_GUIDE_LINKS` = the count of music-guide links inside the nav/footer include regions; compute it by stripping `@include` regions before counting.)

- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Rewrite christmas.html** per spec "Page 1" sections 1–11, in that order. Head values: title "Hire Christmas Carol Singers in London & the UK | LCS" (copy skill may refine), new meta description (141–161 chars, verify with `python3 -c "print(len('…'))"`). JSON-LD: Service/OfferCatalog with the five ensembles + organist/pianist £250, FAQPage (6–8 event questions, none duplicated site-wide: `grep -rh '"name": "' --include='*.html' . | sort | uniq -d` must not list them), BreadcrumbList, three VideoObjects (copy the existing ones). Hero: `.hero-video` with `csFWUu-r85Y` + caption "It&rsquo;s the Most Wonderful Time of the Year, sung by our full choir"; three facts; primary button → `#enquiry`; WhatsApp link `<a href="https://wa.me/447356042468" target="_blank" rel="noopener" data-whatsapp>`; disambiguation line → `christmas-carol-services.html`. Form: `subject` "Christmas carol singers enquiry", hidden `occasion`=`christmas`, hidden `page`=`christmas`, `event_type` select (Office or staff party / Drinks reception / Hotel or venue lobby / Residents' event / Market or light switch-on / Outdoor event / Other), optional `guests` and `postcode_or_venue` inputs with labels, trimmed "How did you hear". Copy through `writing-site-copy` then `stop-slop`; take the best lines from carol-singers.html (now in git history: `git show HEAD~1:carol-singers.html`).
- [ ] **Step 4:** tests pass; `python3 tests/test_design_markup.py` passes (christmas.html hero → `WONDERFUL`, update its HERO_FILMS and remove `ROYAL` if unused); `./build.sh` green.
- [ ] **Step 5: Commit** `feat(christmas): rebuild christmas.html as the carol singers landing page`.

### Task 3: New page christmas-carol-services.html

**Files:**
- Create: `christmas-carol-services.html` (clone christmas.html's head/structure per the `new-page` skill)
- Modify: `scripts/stage_site.py` `PUBLIC` only if root pages are allowlisted by name (check; build fails if missing)
- Modify: `thank-you.html` (add `from=carol-service` copy alongside the existing `from` variants)
- Modify: `llms.txt` (add the page; rewrite the christmas.html line; remove the carol-singers line)
- Modify: `tests/test_design_markup.py` (HERO_FILMS add `christmas-carol-services.html: ROYAL`)
- Test: `tests/test_christmas_pages.py`

**Interfaces:**
- Consumes: `form_contract` from Task 2.
- Produces: URL `/christmas-carol-services.html`, form `page=christmas-carol-services`, redirect `thank-you.html?from=carol-service`.

- [ ] **Step 1: Write failing tests** `church_page`:

```python
g = read('christmas-carol-services.html')
check('SbvqWglsbMo' in g.split('class="hero-video"')[1][:1500], 'hero is Royal David\'s')
check(set(re.findall(r'data-video="([^"]+)"', g)) == {'SbvqWglsbMo','zDlSFb74p4E'}, 'church films')
check('dGYqQf6BDAk' not in g and 'Carol of the Bells' not in g, 'no Carol of the Bells')
for hymn in ('Be Thou My Vision','Guide Me, O Thou','All Things Bright'): check(hymn not in g.split('<main')[1], f'{hymn} not on page')
check('Helen' in g and 'Laura' in g, 'church testimonials moved here')
check('£250' in g, 'organist price')
check(not re.search(r'church (hire|fee)|verger.{0,20}fee', g, re.I), 'silent on church fees')
check('<link rel="canonical" href="https://londonchoralservice.com/christmas-carol-services.html">' in g, 'canonical')
# form_contract('christmas-carol-services.html', page='christmas-carol-services', redirect='thank-you.html?from=carol-service'),
#   with event_type options: Church carol service / School or community service / Other
check('christmas-carol-services.html' in read('llms.txt') and 'carol-singers.html' not in read('llms.txt'), 'llms.txt')
```

- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3: Build the page** per spec "Page 2" sections 1–7. Move Helen's and Laura's quotes and the church section from the pre-Task-2 christmas.html (`git show <base>:christmas.html`). FAQ topics: order of service, the church's permission, our organist (only what the site already says), rehearsal, congregational singing; questions unique site-wide. Title "Choir for a Christmas Carol Service | London & UK | LCS" (copy skill may refine). Run `./build.sh` (expands includes, inlines CSS, adds to sitemap). Then `node scripts/og/generate_og_images.mjs --wire` for both pages' new h1s.
- [ ] **Step 4:** tests pass; `python3 tests/test_design_markup.py`, `python3 tests/test_stage_site.py`, `./build.sh` green; `grep -c christmas-carol-services sitemap.xml` → `1`.
- [ ] **Step 5: Commit** `feat(christmas): add church carol services page`.

### Task 4: Nav, footer and homepage wiring

**Files:**
- Modify: `partials/nav.html:15-16` (Services dropdown → "Christmas carol singers" /christmas.html, "Church carol services" /christmas-carol-services.html; keep top-level "Christmas" :49)
- Modify: `partials/footer.html:22-23` (same two labels)
- Modify: `index.html` Christmas block (carolling first, both pages)
- Test: `tests/test_christmas_pages.py`

- [ ] **Step 1: Failing test** `nav_footer`: in `partials/nav.html` and `partials/footer.html`, `/christmas-carol-services.html` present, `/carol-singers.html` absent, and `Christmas carol singers` label present.
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** edit the partials and index.html; `./build.sh` (expect ~165-file diff confined to the nav/footer include regions; spot-check `git diff -- index.html areas/london/camden.html music-guides/index.html`).
- [ ] **Step 4:** tests + build green.
- [ ] **Step 5: Commit** `feat(nav): Christmas carol singers and church carol services`.

### Task 5: Repoint every body link, guide CTA and off-site doc

**Files:**
- Modify: every page linking `carol-singers.html` (68 pages: `grep -rl 'carol-singers.html' --include='*.html' . | grep -v graphify-out`), guide sticky-bar/body CTAs
- Modify: `docs/off-site-listings-pack.md:109`, `MANUAL-ACTIONS-REQUIRED.md` (new item), `data/seo-fix-discovered-urls.yml` video `page:` lists, `docs/superpowers/specs/2026-07-29-christmas-expansion-design.md` §1 (dated note pointing to the new spec), `.claude/agents/lcs-reply-drafter.md` and `docs/HANDOVER-2026-09-27-ads-analytics.md` Appendix E (new form fields `event_type`, `guests`, `postcode_or_venue`, `page`) and Appendix A / `.claude/agents/lcs-review-bookings.md` (ad-visit `christmas-carol-services` → Christmas)
- Create: `scripts/repoint_christmas_links.py` (one-off sweep; keep in repo for the record)
- Test: `tests/test_christmas_pages.py`

**Interfaces:**
- `scripts/repoint_christmas_links.py [--dry-run]`: rewrites `carol-singers.html` hrefs to `christmas.html` (same relative prefix), except in the church-service guides listed below, where Christmas CTAs go to `christmas-carol-services.html`. Skips `graphify-out/`, `docs/`, `tests/`, `partials/`, the stub itself. Prints per-file counts.
- Church-service guides (CTAs and sticky "Enquire" → church page): `music-guides/nine-lessons-and-carols.html`, `church-carol-service-choir-hire.html`, `carols-by-candlelight.html`, `advent-carols-vs-christmas-carols.html`, `christmas-carols-guide.html`, `corporate-carol-service.html`.

- [ ] **Step 1: Failing tests** `no_links_to_stub` (no published `*.html` outside the stub contains `carol-singers.html"`), `church_guides_point_to_church_page` (each of the six guides links `christmas-carol-services.html` from its sticky bar, i.e. the `mobile-cta` block), `anchor_text_matches` (no link to `christmas.html` with anchor text containing "carol service" outside the nav's seasonal link, and no link to `christmas-carol-services.html` with anchor "carol singers").
- [ ] **Step 2:** run → FAIL.
- [ ] **Step 3:** run the script with `--dry-run`, review counts (expect ~68 files), run it; fix anchor texts the test flags by hand (e.g. "book a carol service" on area pages → church page; "hire carol singers" → christmas.html); edit the docs listed above.
- [ ] **Step 4:** tests pass; `./build.sh` green (its broken-link check passes); `python3 scripts/stage_site.py` OK.
- [ ] **Step 5: Commit** `chore(christmas): repoint carol-singers links and guide CTAs`.

### Task 6: Verify, ship, check live

- [ ] **Step 1:** `python3 tests/test_christmas_pages.py && python3 tests/test_design_markup.py && python3 tests/test_stage_site.py && .venv/bin/python tests/test_register_generators.py && ./build.sh` → all OK. (`.venv` lives in the main checkout; build.sh finds it.)
- [ ] **Step 2: Preview** (`preview_start` "static-server"). At 375×812 and 1280 px on christmas.html and christmas-carol-services.html: `document.documentElement.scrollWidth` equals the viewport width; the primary button's `getBoundingClientRect().bottom < 812` at 375 px; hero film click swaps to the nocookie iframe; no console errors. Open `/carol-singers.html?gclid=TEST&utm_source=google` and confirm `location.href` ends `/christmas.html?gclid=TEST&utm_source=google`. Submit nothing (live Web3Forms).
- [ ] **Step 3:** `/graphify --update`, commit `graphify-out/`.
- [ ] **Step 4:** PR (`feat(christmas): carolling landing page, church services page, merge carol-singers`), merge after checks, confirm the deploy run exists for the merge SHA (dispatch `deploy-pages.yml` on main if no push run appears), then `git fetch origin && python3 scripts/check_live_site.py` and curl `https://londonchoralservice.com/carol-singers.html` contains `location.replace('/christmas.html'`.
- [ ] **Step 5:** Hand the owner the Ads follow-up prompt (final URL `carol-singers.html` → `christmas.html` in "Hire carol singers"; sitelinks), to run only after this is live.
