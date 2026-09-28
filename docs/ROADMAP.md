# Site improvement roadmap

Prioritised backlog from the July 2026 site audit. Each item is **self-contained**: the analysis is finished — do not re-derive it, just execute and verify.

## How to work this list (agents, read first)

- Locate code with the **grep anchors** given per item, never line numbers — they drift.
- **`[BLOCKED-ON-HUMAN]`** items depend on `MANUAL-ACTIONS-REQUIRED.md` tasks only a person with dashboard access can do. Do not attempt them; do not fake the missing values.
- **`[SPEC-FIRST]`** items need a design spec in `docs/superpowers/specs/` (named `YYYY-MM-DD-<name>-design.md`, matching existing files) approved before implementation.
- **`[DECISION-NEEDED]`** items are for the site owner to decide, not an agent.
- Load the skills named per item before starting. Always finish with the `build-and-verify` checklist.
- When an item is done, change its status to `[done <date>]` and note the commit.

Statuses: `[ready]` `[BLOCKED-ON-HUMAN]` `[SPEC-FIRST]` `[DECISION-NEEDED]` `[done]`

---

## R1 — Remove self-serving review schema and rating claims  [P1] [done 2026-07-29 — Christmas expansion]

Completed as part of the Christmas expansion (see `docs/superpowers/plans/2026-07-29-christmas-expansion.md`): AggregateRating/Review removed from index.html and about.html JSON-LD, "Rated 5 stars" meta claims removed from weddings.html, services.html star row replaced with the verifiable 150-musician trust line. Original item preserved below for the verify commands.

## R1 (original) — Remove self-serving review schema and rating claims  [P1] [ready] [S]

**Why:** `index.html` carries `AggregateRating` (ratingValue 5, reviewCount 4) plus four `Review` objects with first-name-only authors inside the LocalBusiness JSON-LD. Google's structured-data policy treats reviews marked up by the entity being reviewed as self-serving: they are ignored at best and can trigger a manual action. The claim leaks into visible copy ("Rated 5 stars" in weddings.html meta descriptions; a ★★★★★ row on services.html), where it is unverifiable and a trust exposure. This is the highest-priority fix on the site.

**Files & anchors:**
- `grep -n 'AggregateRating' index.html` — the rating + review block to remove
- `grep -n 'Rated 5 stars' weddings.html` — 3 occurrences (meta description, og:description, twitter:description)
- `grep -n 'hero-trust__stars' services.html` — the visible star row

**Do:** Delete the `AggregateRating` property and the four `Review` objects from index.html's JSON-LD (keep the rest of the LocalBusiness node intact; re-validate). Rewrite the weddings.html description without the rating claim — all three copies must stay identical and the meta description must stay **141–161 chars**. Replace or remove the services.html star row; if keeping a trust element, reference something verifiable (e.g. "150+ conservatoire-trained musicians") instead of a rating.

**Do not:** Move the reviews elsewhere in the schema, convert them to `Testimonial`-style markup, or "fix" them by adding surnames — the policy problem is self-serving review markup itself. Do not let the meta description fall outside 141–161 chars.

**Acceptance:** No review/rating structured data anywhere; no "Rated 5 stars" text anywhere; visible testimonial *quotes* in body copy (if any) may remain — they're content, not schema.

**Verify:**
```sh
grep -rn 'AggregateRating\|"@type": "Review"' --include='*.html' . | grep -v node_modules   # → empty
grep -rn 'Rated 5 stars' --include='*.html' .                                              # → empty
./build.sh                                                                                  # exits 0
python3 -c "import re;d=re.search(r'name=\"description\" content=\"([^\"]*)\"',open('weddings.html').read()).group(1);print(len(d),140<len(d)<162)"
```
**Skills:** build-and-verify, writing-site-copy

---

## R2 — Refresh stale sitemap lastmod dates  [P2] [done 2026-08-15] [S]

**Why:** 82 of 103 `<url>` entries say `<lastmod>2026-05-14` while the underlying files were last edited 2026-07-08 (several copy sweeps since). Stale lastmod misrepresents freshness to crawlers and erodes trust in the whole sitemap signal.

**Update 2026-07-29:** the Christmas expansion refreshed lastmod for ~65 entries (12 new pages, christmas.html, and all 52 area pages). The scripted git-date sweep below is still worth running for the remaining untouched entries.

**Files & anchors:** `grep -c '2026-05-14' sitemap.xml` (82 at time of writing)

**Do:** One-off sweep setting each URL's `<lastmod>` from git: for each `<loc>`, map URL path → file path (`/` → `index.html`; `/areas/bath.html` → `areas/bath.html`) and set lastmod to `git log -1 --format=%as -- <file>`. Script it in Python; don't hand-edit 103 entries. Going forward the convention (already in CLAUDE.md) is to bump lastmod whenever a page is added or materially edited.

**Do not:** Set everything to today — that's the same lie in the other direction.

**Acceptance:** Every lastmod equals the file's last commit date; sitemap still parses; URL count unchanged (103).

**Verify:**
```sh
python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('sitemap.xml'); print('parses')"
grep -c '<loc>' sitemap.xml    # unchanged vs before (103)
grep -c '2026-05-14' sitemap.xml   # ≈0 (only files genuinely last touched that day)
```
**Stretch:** [done 2026-09-04] `scripts/generate_sitemap.py` runs inside `build.sh`; `lastmod` is content-hash driven (`data/page-dates.json`), seeded from git history. `scripts/sync_dates.py` keeps article `dateModified`, OG modified time and the visible date line on the same value.

**Skills:** build-and-verify

---

## R3 — Real VideoObject dates/durations + missing sameAs  [P2] [done 2026-08-15 (video dates); sameAs still BLOCKED-ON-HUMAN]

All seven VideoObject nodes now carry real `uploadDate` and `duration` values, verified via `ytInitialPlayerResponse` on the YouTube watch pages. Zero placeholder dates remain (`grep -rn '2025-01-01' --include='*.html' .` → empty). Updated files: listen.html (6 videos), pricing.html (1), music-guides/anima-christi-catholic-wedding.html, music-guides/anima-christi-catholic-funeral.html, music-guides/ubi-caritas-wedding.html, christmas.html, carol-singers.html. `data/seo-fix-discovered-urls.yml` updated with all values.

**Still blocked:** GBP canonical Maps URL, LinkedIn company page, and ORCID for sameAs fields — see MANUAL-ACTIONS-REQUIRED.md.

**Skills:** build-and-verify

---

## R4 — Cookie consent / Google Consent Mode v2  [P4] [done 2026-09-04] [L]

Done in the 2026-09-04 audit follow-up: snippet extracted to `partials/analytics.html` (swept into 163 pages), Consent Mode v2 defaults denied before gtag loads, `js/consent.js` banner with Allow/Decline stored under `lcs-consent`, reopenable from the footer; `privacy.html` cookie section rewritten. Human follow-up: MANUAL §16. Original item preserved below.

## R4 (original) — Cookie consent / Google Consent Mode v2  [P4] [SPEC-FIRST] [L]

**Why:** GA4 + Google Ads load (deferred, but unconditionally) with no consent mechanism. For a UK-audience business this is a PECR/GDPR gap — analytics cookies require prior consent. Also a commercial concern: Google Ads conversion tracking without Consent Mode v2 loses modelling eligibility.

**Sequencing insight (the important part):** the GA4 snippet is duplicated inline in every page's `<head>` — it is **not** a partial. Implementing consent as a 106-file inline edit would be unmaintainable. **Step 1 of any implementation: extract the analytics snippet into a new `partials/analytics.html` with `@include-start/@include-end` markers swept into all pages via script** (see build-and-verify → site-wide sweeps), verify that no-behaviour-change refactor alone, and only then implement consent logic once, inside the partial.

**Files & anchors:** `grep -rln 'G-9FENN7VS0E' --include='*.html' . | wc -l` (~106 pages); `build.sh` (partial expansion); `privacy.html` (policy text will need updating).

**Spec must cover:** banner UX (self-built vs CMP), Consent Mode v2 default-denied config, storage of choice, effect on the existing lazy-load pattern, privacy-policy updates.

**Skills:** build-and-verify

---

## R5 — Merge duplicate form scripts  [P4] [done 2026-08-18 — site audit] [M]

Merged into `js/form.js` (occasion pre-fill from contact.js + `data-redirect` support from landing-form.js, default `/thank-you.html`); all 13 referencing pages updated; `js/contact.js` and `js/landing-form.js` deleted. hCaptcha guard, botcheck honeypot, and Web3Forms behaviour unchanged. Original item preserved below.

## R5 (original) — Merge duplicate form scripts  [P4] [ready] [M]

**Why:** `js/contact.js` (109 lines, used by 1 page) and `js/landing-form.js` (87 lines, used by 7 pages) are near-duplicates: both POST JSON to Web3Forms, guard on hCaptcha, reset the captcha on retry, redirect on success. Two copies means bugs get fixed in one and not the other (this has already happened historically with the hCaptcha guard).

**Files & anchors:** `grep -rln 'landing-form.js\|js/contact.js' --include='*.html' .` — the 8 referencing pages.

**Do:** Enumerate the real deltas first (contact.js: `?occasion=` select pre-fill; landing-form.js: `data-redirect` attribute; confirm the rest by diff). Merge into one module (keep the name `js/contact.js` or introduce `js/forms.js`) driven by data-attributes/feature detection, update the 8 script references, delete the dead file.

**Do not:** Change form behaviour, remove the hCaptcha guard or `botcheck` honeypot, or alter the Web3Forms access key.

**Acceptance:** One form script; both form variants work.

**Verify:** `python3 -m http.server 8000`; on `contact.html?occasion=wedding` the occasion select pre-fills; on a landing page the form renders hCaptcha and (with captcha unsolved) refuses submit; `grep -rn 'landing-form.js' --include='*.html' .` → empty if the file was removed; `./build.sh` green.

**Skills:** build-and-verify

---

## R6 — Revisit CSS inlining vs cached stylesheet  [P3] [DECISION-NEEDED]

**Why:** `build.sh` inlines the full ~40KB CSS into every page: zero render-blocking requests (great first paint) but zero cross-page caching — a visitor browsing 3 pages downloads the same CSS 3 times, and every page weighs 55–78KB. For a site whose funnel is multi-page (area page → pricing → contact), a single cached `<link rel="stylesheet">` is likely a net win after the first page.

**The trade:** inlining wins on single-page bounce traffic (most SEO landings); linking wins on multi-page sessions and cuts repo churn (style edits stop rewriting 106 files). Data that would settle it: GA4 pages-per-session for organic landings.

**If approved:** the change is small — remove build.sh pass B (keep pass A as a one-off migration that restores `<link>` tags), keep CSS concat + partials + validation. Consider `<link rel="preload" as="style">` to soften the request cost.

**Owner decides.** An agent should not make this call unilaterally.

---

## R7 — Listen page audio, FAQ hub, per-page OG images  [P5] [ready, image assets BLOCKED-ON-HUMAN] [M]

Three smaller content gaps, workable independently:

1. **[part done 2026-09-04]** The dead `.audio-placeholder` CSS is deleted, and `listen.html` is now split into **Recordings** (the six pieces with a player) and **Repertoire we are asked for most** (the other fourteen), so the page no longer describes sound a visitor cannot hear. What remains is BLOCKED-ON-HUMAN: real recordings from the owner, including the comparison set in the 2026-09-04 plan (P1.2 — one hymn and one anthem sung as soloist, four voices and eight voices in the same acoustic). Original text: **listen.html has no audio.** CSS defines `.audio-placeholder` but no `<audio>` element exists anywhere. Either add real `<audio>` elements with self-hosted samples or delete the dead CSS.
2. **[done 2026-08-18]** `faq.html` exists and is linked from the footer and from every service page's FAQ block (2026-09-04). Original text: **No consolidated FAQ page.** FAQ content exists as per-page `FAQPage` JSON-LD + visible accordions. A `/faq.html` hub aggregating the best questions (linked from footer) captures long-tail question queries. Use the `new-page` skill; dedupe against existing per-page FAQs — don't duplicate the same Q&A schema on two pages.
3. **[partly done 2026-08-18]** seven branded OG images exist and are wired on the money pages and guides; area, borough, destination and B2B pages still use the generic card (see the 2026-09-04 plan, P10.5, for generating the rest in the build). Original text: **Single generic og-image for all ~106 pages** (`grep -rln 'assets/og-image.png' --include='*.html' . | wc -l`). Per-service images (weddings, funerals, christmas, corporate + one per major hub) would lift social CTR. Image creation BLOCKED-ON-HUMAN; the wiring (og:image/twitter:image per page) is agent work once assets land in `assets/`.

**Skills:** new-page, build-and-verify, writing-site-copy

---

## R8 — Text contrast  [P6] [done 2026-07-08 — verified non-issue]

An earlier audit pass flagged `--color-text-mid: #6B5E56` on `--color-bg: #F7F3EE` as borderline (~4.3:1). Measured properly it is **5.66:1**, comfortably above the WCAG AA 4.5:1 threshold at all sizes. **No change needed.** Keep this script for checking any future palette change in `css/tokens.css`:

```sh
python3 - <<'EOF'
def lum(h):
    c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    c=[x/12.92 if x<=0.03928 else ((x+0.055)/1.055)**2.4 for x in c]
    return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
l1,l2=lum('6B5E56'),lum('F7F3EE')   # foreground, background (no #)
print(round((max(l1,l2)+0.05)/(min(l1,l2)+0.05),2))   # must be >= 4.5
EOF
```
Remember any `css/tokens.css` edit requires `./build.sh` (see build-and-verify).

---

## R9 — January: demote seasonal Christmas nav + annual price date bump  [P3] [scheduled Jan 2027] [S]

**Why:** The Christmas expansion (July 2026) promoted Christmas to a top-level nav item in `partials/nav.html` for the booking season. After the season it should return to the Services dropdown only. The same pass should bump `priceValidUntil` (currently `2027-12-31` on christmas.html and carol-singers.html) each January.

**Do (in January):** Remove the top-level `<li><a href="/christmas.html">Christmas</a></li>` from `partials/nav.html` (keep the Services-dropdown entry), run `./build.sh` (expect the ~106-file diff), and check `grep -rn 'priceValidUntil'` dates are next-Dec-31. Consider whether the index.html "Christmas 2026" section and footer link should also be softened out of season.

**Update 2026-07-31:** the Christmas content overhaul added 11 guides (24 Christmas guides in total). The January pass should also refresh the "Last updated" byline and `dateModified` on the Christmas guide set, and re-check the four-group guide block on `christmas.html` still reads well if any guides are added or retired.

**Verify:** `./build.sh` exits 0; nav renders correctly at 375px; sitemap untouched.

**Skills:** build-and-verify

---

## Explicitly not on the list

- **Copy rewrites** — tracked separately in `SITE-STOP-SLOP-PLAN.md` (Parts 3–4 are its own prioritised backlog).
- **Off-site SEO / listings / GBP** — human-only, in `MANUAL-ACTIONS-REQUIRED.md`.
- Strengths to leave alone: semantic HTML + skip links + labelled forms, complete sitemap coverage, disciplined meta/canonical/hreflang/OG, deferred GA4 loading, self-hosted preloaded fonts.

---

## R10 — Two duplicate FAQ questions site-wide  [P3] [done 2026-08-15] [S]

**Why:** Two `FAQPage` question strings appear on two pages each, which splits the rich-result signal between them. Found during the July 2026 Christmas overhaul; neither pair is Christmas content, so it was left out of scope at the time.

**Files & anchors:**
- `grep -rn 'How much does a funeral singer cost?' --include='*.html' .` — `music-guides/funeral-music-costs.html` and `pricing.html`
- `grep -rn 'How far ahead should we book?' --include='*.html' .` — `corporate.html` and `for-wedding-planners.html`

**Do:** Keep the question on the page that best owns the intent and reword the other so both the visible text and the schema answer differ. The visible FAQ text and the `FAQPage` answer text must stay identical strings on each page.

**Verify:**
```sh
python3 -c "
import re,glob,collections
q=[]
for f in glob.glob('**/*.html',recursive=True):
    q += re.findall(r'\"@type\": \"Question\",\s*\"name\": \"([^\"]+)\"', open(f).read())
print([k for k,v in collections.Counter(q).items() if v>1] or 'unique')"   # -> unique
```
**Skills:** writing-site-copy, build-and-verify

---

## R11 — Replace the "Victorian" verification grep with an allowlist  [P4] [done 2026-09-04]

**Why:** The July 2026 Christmas spec set `grep -rn -i 'Victorian' --include='*.html' .` → empty as an acceptance check, enforcing the rule that Victorian costume is never offered or claimed. Three legitimate uses now exist and no regex distinguishes them from a violation, because the difference is whether the sentence *offers* the thing:

- `music-guides/best-christmas-carol-singers.html` describes Victorian costume as a market option a buyer will encounter, then states plainly "London Choral Service sings in concert dress, all black, casual wear, or Christmas jumpers &hellip; we do not perform in period costume". That is the rule being honoured, not broken.
- `music-guides/christmas-carol-lyrics-meanings.html` uses "Victorian" twice in its historical sense — Victorian schoolroom morality in the text of *Once in Royal David&rsquo;s City*, and Victorian critics of J. M. Neale.

**Do:** Replace the empty-grep check in `docs/superpowers/specs/2026-07-29-christmas-expansion-design.md` §2 with: list every `Victorian` hit and confirm each either (a) sits on one of the two allowlisted files above, or (b) carries an explicit statement that we do not perform in costume. The underlying rule is unchanged and unweakened: costume is not offered.

**Skills:** none

---

## R9b — Competitive capture: The London Funeral Singers  [P1] [done 2026-08-18]

(Renumbered from a duplicate R9 on 2026-09-04; the January nav item above keeps R9.)

**What shipped:** a sourced, family-facing comparison page at `compare/london-funeral-singers.html`, backed by a build gate so quoted competitor figures cannot go stale or be invented.

- `data/competitor-pricing.yml` — every competitor figure with the verbatim published string it came from and a `checked_date`.
- `validate_competitor_claims.py` + `tests/test_competitor_claims.py` — the repo's first test. `build.sh` hard-fails on any money figure under `compare/` not declared in the YAML, and warns once the data passes 120 days. Allowed figures are declared explicitly; deriving them arithmetically admitted thousands of values and would have let a wrong figure through by coincidence.
- `validate_jsonld.py` now globs `compare/` too — it previously did not, so JSON-LD there went unchecked.
- Cost guide gained a sourced market comparison; `best-funeral-singers-london.html` market table corrected upward (its quartet range topped out below the one published London price list).
- `pricing.html` gained a named inclusions block; `funerals.html` gained the fixed-ensemble argument and on-the-day service standards.

**Two site-wide corrections this surfaced, both shipped separately:**
- Six B2B pages stated "We are VAT-registered" in 13 places including two JSON-LD answers. Alma Consort Ltd is not VAT-registered. A finance team reading that would expect a VAT number on the invoice.
- The site advertised "over 150 auditioned singers and instrumentalists" in 13 places — near-verbatim the competitor's own line — while the actual positioning is a small hand-picked team. 43 edits across 23 files.

**Not done, deliberately:** no named-singer roster page (owner's decision); crematorium and borough landing pages deferred as a separate programmatic project; Google Ads recorded in `MANUAL-ACTIONS-REQUIRED.md` §11 as human-only.

**Blocked on merge order:** `site-audit-improvements-47d735` must land first — it is the authority on LCS prices and raises the soloist rate to £250, which this work assumes throughout. See "Before merging this branch" in the plan.

**Spec:** `docs/superpowers/specs/2026-08-18-competitive-capture-design.md`
**Plan:** `docs/superpowers/plans/2026-08-18-competitive-capture.md`

**Verify:**
```sh
./build.sh                                    # ends "Competitor claims valid across 1 compare/ page(s)."
python3 tests/test_competitor_claims.py       # 0 failure(s)
grep -rn 'VAT' --include='for-*.html' .       # empty
grep -rn 'over 150\|150 auditioned' --include='*.html' --include='*.txt' .   # empty
```

---

## R12 — Testimonial pool reused across geographically mismatched pages  [P2] [DECISION-NEEDED]

**Why:** A 2026-08-30 content audit found a small pool of ~16 distinct testimonials (no `AggregateRating`/`Review` schema involved — these are plain pull-quotes in body copy) reused across the 53 area/borough pages, several with the same first name but a different quote *and* a different named location depending which page they land on. E.g. "Tony, Surrey" (8 pages, all in London boroughs — none in Surrey) and "Tony, Battersea" (6 pages, none in Battersea) are two different quotes; the same pattern repeats for "Pamela" (Hampshire/Richmond) and "Helen" (Buckinghamshire/Wimbledon). Separately, the single "Margaret, Dulwich" quote is repeated verbatim, unmodified, on 17 pages. Full attribution counts: `grep -rho '<figcaption>&mdash;&ensp;[^<]*</figcaption>' areas/*.html areas/london/*.html index.html funerals.html weddings.html | sort | uniq -c | sort -rn`.

This is a business-integrity question, not a copy-quality one — an agent doesn't know whether "Tony" is one real client whose quote is being redistributed to unrelated pages (which would misrepresent a real person's words as being about a place they weren't), two real clients who happen to share a first name, or a placeholder pattern. Do not let an agent guess: whether to (a) source enough distinct real per-area testimonials to stop the cross-contamination, (b) strip the specific location from the attribution wherever it doesn't match the page, or (c) leave as-is and accept the trust cost. No new testimonial text should ever be invented to fill the gap — CLAUDE.md already forbids invented testimonials.

**Files & anchors:** all `<figure class="pull-quote">` blocks under `areas/*.html` and `areas/london/*.html`.

**Skills:** writing-site-copy (once a direction is chosen)


**Update 2026-09-04:** the "Tony, Battersea" quote ("she just took the music completely off our hands") was replaced on its seven pages. Two quotes still say "she" ("Pamela, Richmond", 9 pages; "Helen, Wimbledon", 4 pages). If a colleague handles the phone, say so on `about.html` and `contact.html` and keep them; otherwise replace them too. Owner decision.
---

## R13 — Borough page template is a rigid, visible mould across all 33 pages  [P3] [done 2026-09-27]

**Done:** spec `docs/superpowers/specs/2026-09-27-borough-template-variants-design.md`, plan `data/r13-borough-plan.json`, applied by `scripts/r13_borough_variants.py`. Four variants, 15 section orders, no two pages with the same H2 sequence, 2–4 FAQs each with one borough-specific question, FAQPage JSON-LD kept in step. Testimonials unchanged (R12). Follow-up: a `writing-site-copy` pass on the repeated sentences the spec lists.

**Original text:**

**Why:** The 2026-08-30 content audit found every one of the 33 `areas/london/*.html` pages follows the identical H2 sequence (funeral music / wedding choirs / ensembles / Christmas carols / FAQ) with the same 3-question FAQ topic order every time. The prose itself is genuinely localised (real named churches, crematoria, historical detail), and the price-ladder FAQ answer's repeated sentence construction was already fixed site-wide (see verify command below) — what's left is the structural sameness of the container itself, which is exactly the kind of programmatic-SEO pattern current Google quality guidance is trained to flag, independent of how good the sentence-level writing is.

**Do:** This needs a template-level design decision before any agent touches it — e.g. vary section presence/order/count per borough (not every borough needs all 5 sections; the FAQ set could vary in count or topic per borough), rather than a per-page copy fix. Route through the `new-page`/`site-architecture` skills for the redesign, write a spec first.

**Do not:** Reshuffle section order randomly without a template rationale — that just trades one mechanical pattern for another.

**Verify (confirms the already-fixed sub-issue, not this item):**
```sh
python3 -c "
import re, glob
seen = {}
for f in sorted(glob.glob('areas/*.html')) + sorted(glob.glob('areas/london/*.html')):
    if f.endswith('index.html') or f.endswith('areas/london.html'): continue
    c = open(f, encoding='utf-8').read()
    m = re.search(r'\"acceptedAnswer\": \{\s*\"@type\": \"Answer\",\s*\"text\": \"([^\"]*£1,150[^\"]*)\"', c)
    if m: seen.setdefault(re.sub(r'£[\d,]+', '£N', m.group(1)), []).append(f)
dupes = {k: v for k, v in seen.items() if len(v) > 1}
print('duplicate price-ladder constructions:', len(dupes))  # → 0
"
```
**Skills:** new-page, site-architecture

---

## R14 — Owner facts the 2026-09-27 audit could not settle  [P2] [DECISION-NEEDED]

**Why:** The 2026-09-27 full-site audit fixed every contradiction with a checkable answer (see commit `copy: correct contradictions and music-history errors…`). These remain because only the owner knows which figure is true. Do not let an agent pick one.

1. **[done 2026-09-27: one or two weeks usual, short notice fine]** **Funeral notice.** `funerals.html` (hero FAQ) and `services.html` say most families contact us "two to five days before the service"; `funerals.html` (FAQ) and `music-guides/last-minute-funeral-singers.html` say "one or two weeks' notice". Both arrived in the same commit. `grep -rn "two to five days\|one or two weeks" --include=*.html . | grep -v graphify`
2. **[done 2026-09-27: around six months ideal, last-minute fine]** **Wedding lead time.** `pricing.html` and `music-guides/wedding-choir-guide.html` say book "at least six months" ahead; `weddings.html` and `for-wedding-planners.html` say "three to six months".
3. **[done 2026-09-27: around five minutes; one piece suits it best, two if both are short or the music may run on after the signing]** **Register-signing length** varied by page: two or three minutes (`weddings.html`), three or four (`anima-christi-catholic-wedding`), four or five (`wedding-readings-and-music`), five to eight (`lesser-known-wedding-choral-pieces`), five to ten (`wedding-choral-repertoire`). Pick one range for a typical church and use it everywhere. `grep -rnoiE "[^.>]*(signing|register)[^.<]{0,80}minutes" --include=*.html music-guides weddings.html`
4. **[done 2026-09-27: now "one of the most-requested"]** **"Abide With Me — the most-requested funeral hymn"** (title, h1, meta). The page body, `funerals.html` and `listen.html` now say it shares the top place with The Lord's My Shepherd. Either cite a source for the title claim or retitle ("one of the two most-requested funeral hymns").
5. **[done 2026-09-27]** "December dates go by mid-September" (about 60 pages) now reads "starts to fill by mid-September", at the owner's request, so late visitors are not put off enquiring.
6. **[done 2026-09-27: role=group added; lastmod kept for markup-only pages]** **Mobile call bar `aria-label`** sits on a plain `<div>` in 139 hand-written copies, where screen readers ignore it. Adding `role="group"` by sweep bumps `lastmod` on every page (the sitemap hashes body markup), so it was left out of the audit. Best done by moving the bar into a partial, which also removes the duplication.

**Skills:** writing-site-copy

---

## R15 — Run the 2026 Zoho Books import  [P2] [BLOCKED-ON-HUMAN]

**Why:** the Zoho Books design (`docs/superpowers/specs/2026-09-28-zoho-books-design.md`, flow D) prepared a private dry-run list of this year's bookings at `~/lcs-private/books-import-2026.json` (seven bookings), ready to become draft invoices in Books. It has not run: the owner has to look at the list and say the word first (see `MANUAL-ACTIONS-REQUIRED.md` §20).

**Do:** once the owner says "approve the Books import" in chat, create one draft invoice per booking in Books via `ZohoBooks_create_invoice`, dated at each booking's own invoice date, following the allowlisted keys and checks in the Zoho Books design's "Approved write tools" table. Leave `send` absent/false: the owner sends from Books himself.

**Do not:** create anything before the owner's explicit approval line, or touch any of the still-denied tools (payments, `mark_invoice_sent`, anything that emails a client).

**Skills:** none beyond what the guard already enforces

---

## R16 — `check_payments.py` can misread an unpaid arrangement as fully paid  [P3] [done 2026-09-28 — tests/test_check_payments.py]

**Why:** `full_paid()` (via the `REST_PAID` regex) flags a clause as "the whole fee is paid" whenever a rest-of-fee word (`balance`, `rest`, `remainder`, `remaining`, `total`) sits within 30 characters of `paid`/`received`/`settled`, with no check that the clause is actually past tense. A note like "rest will be paid by the best man on the day" matches `REST_PAID` (`rest … will be paid`) and returns `True` from `full_paid()`, landing the booking in `NOTED_PAID` rather than `ARRANGED`. `arranged_notes()` already does the harder version of this (it treats "will be", "to be", "payable", "due" as not-yet-paid and only a genuine `paid` word as done); `full_paid()`/`REST_PAID` never learned the same distinction. Not urgent: `NOTED_PAID`, like `ARRANGED`, always stays on the Monday hand-check list (`money_report.py`), so nothing is silently dropped or chased wrongly, but the label undersells that the money hasn't actually arrived yet, and a future-tense note happens to read identically to a genuine "balance paid in cash" one.

**Files & anchors:** `grep -n 'REST_PAID = re.compile' scripts/bookings/check_payments.py`; `def full_paid` in the same file; `tests/test_check_payments.py`.

**Do:** give `REST_PAID` the same future-tense/negation discipline `ARRANGED_NOTE`/`ARRANGED_PAID` already use, so a clause only counts as "the whole fee is paid" when the paid word is not itself inside a "will be"/"to be"/"payable"/"due" construction. Add a case to `tests/test_check_payments.py` for "rest will be paid by the best man" (expect `ARRANGED`, not `NOTED_PAID`) alongside the existing genuine "balance paid in cash" case (still `NOTED_PAID`).

**Skills:** systematic-debugging

---

## R17 — Dashboard should read invoice status from Zoho Books, not Starling alone  [P3] [done 2026-09-28 — Command Centre phase 6]

**Status:** `scripts/reports/cc_sync.py books` (run by the enquiry assistant's daily pass, `.claude/agents/lcs-daily-pass.md`) writes `~/lcs-private/command-centre/cache/books.json` through `lcs_mcp`'s Books read client (only the tools on the guard's READ_ALLOW); `command_centre/books_cache.py` reads it. **Done (phase 6):** the Command Centre's Money page has a Books panel (receivables, overdue, drafts not yet sent, unpaid bills, freshness); each booking's timeline shows its Books invoice by number; Today flags a Books draft more than 2 days old and Books/Starling disagreements by Appendix A step 6g's rules (`models.books_flags`, `tests/test_cc_final.py`); a background job refreshes the cache every 30 minutes from 07:00 to 22:00. The static `dashboard.py` is left without Books: the Command Centre replaces it (R21).

**Why:** `scripts/reports/dashboard.py` (`gather()`) currently builds every payment state from `check_payments.assess()` against the Starling feed only. Since Books is now the system of record for invoice status (the owner confirms bank-feed matches in Books, per the Zoho Books design's flow B), the dashboard can show a stale or disagreeing picture next to what the owner sees in Books. The Monday report already gets a Books line for this (design §"Flows", flow E, section 11: receivables, overdue invoices, unpaid bills, disagreements with the Starling check); the dashboard never picked up the equivalent.

**Files & anchors:** `scripts/reports/dashboard.py` (`gather`/`render`); the read-only `zoho-books`/`zoho-books-invoices` MCP tools (`list_invoices`, `list_bills`) already used by the Monday review for the same purpose.

**Do:** add a Books-sourced invoice/bill status pull to `gather()`, alongside the existing Starling-derived state, and show both on the dashboard when they disagree (mirroring the Monday report's "needs a hand check" treatment) rather than only the Starling view. Read-only calls only; the dashboard writes nothing back to Books.

**Skills:** none beyond the existing dashboard test pattern (`tests/test_dashboard.py`)

---

## R18 — Automation Phase 4 is now mostly covered by Zoho Books  [P3] [done 2026-09-28 — Command Centre phase 6]

**Status:** Phase 4 marked done-by-Books in the business-automation spec. Per-event margin: `singer_invoices.py link <message id> <booking ref>` (and an automatic link at scan/rescan when the invoice's date matches exactly one ledger booking) writes a `booking_ref` column; `singer_invoices.py margins` and the pure `margins(ledger_rows, singer_rows)` (also `command_centre/books_cache.margins()`) give fee, singer costs, margin and margin % per booking. **Done (phase 6):** the Bookings list and each timeline show fee, singer costs, margin and margin %, the timeline lists the linked singers (first names), and Money shows the season total from `season_start` (`tests/test_cc_final.py`).

**Why:** `docs/superpowers/specs/2026-09-28-zoho-books-design.md` states plainly that it "replaces most of [the business-automation spec's] Phase 4 (per-event margin, bookkeeping export), which Books now provides": Books' own reports give the monthly bookkeeping export (feature 15 of the business-automation spec) for free once invoices and bills live there, so that half of Phase 4 needs no bespoke script. **Feature 14, per-event margin, is not covered yet**: Books has no native concept of "this booking's client invoice minus this booking's singer bills", because that link runs through the booking ref, which lives in the private ledger and in bill/invoice notes, not as a first-class Books field.

**Do:** mark Phase 4 done-by-Books in `docs/superpowers/specs/2026-09-28-business-automation-design.md`'s phase table (a one-line note, not a rewrite) and write the per-event margin piece as its own small plan: pull each booking's client invoice total and its linked singer/organist bills (matched on event date and `booking_ref`, per the original feature-14 description), compute margin, and surface it once R17's dashboard work lands. The owner confirms any ambiguous booking-ref link, as the original spec already says.

**Skills:** none yet; write a plan under `docs/superpowers/plans/` before starting

---

## R19 — Lint that the Monday review and enquiry-assistant prompts only use allowlisted commands  [P4] [done 2026-09-28 — tests/test_prompt_allowlist.py]

**Why:** the Monday review (Appendix A) and enquiry assistant (Appendix E) prompts in `docs/HANDOVER-2026-09-27-ads-analytics.md` are free text describing which scripts to run; the actual permission boundary is the `Bash(...)` entries under `.claude/settings.json`'s `allow` list. Nothing currently checks that every command the two prompts tell Claude to run is actually on that list, or flags a prompt edit that introduces a command the settings file doesn't cover (or a settings entry for a command the prompt no longer uses). Today the two happen to agree; there's no test guarding that they keep agreeing as both documents change.

**Files & anchors:** `docs/HANDOVER-2026-09-27-ads-analytics.md` §"Appendix A" and §"Appendix E"; `.claude/settings.json` `permissions.allow`.

**Do:** add a small stdlib test (e.g. `tests/test_appendix_commands_allowlisted.py`) that extracts each literal shell command named in Appendix A and Appendix E (parsing fenced code blocks / backtick-quoted commands for the known script paths), normalises it the way `Bash(...)` patterns do (exact match or the trailing-`*` wildcard form), and asserts each one matches an entry in `.claude/settings.json`'s allow list. Fail loudly, naming the missing command, rather than silently skipping anything unparseable.

**Skills:** none

---

## R20 — Back-fill enquiries from before the pipeline existed  [P4] [DECISION-NEEDED]

**Why:** per `docs/superpowers/plans/2026-09-28-automation-phase-2-pipeline.md` ("Older threads") and `MANUAL-ACTIONS-REQUIRED.md` §26, only enquiries first seen from 28 September 2026 are tracked in `~/lcs-private/enquiries.csv`; anything older gets no automatic follow-up, quote-chase, or loss marking. This was a deliberate scope cut for the initial rollout, not an oversight, so whether it's worth doing is the owner's call, not an agent's.

**Do:** nothing until the owner asks for a back-fill and gives a start date. If asked, write a one-off script that scans Zoho Mail threads before 28 Sep 2026 for enquiry-shaped messages, seeds `enquiries.csv` rows at whatever status the thread history shows (quoted/confirmed/lost), and never re-drafts a reply for a thread that already got a human one.

**Skills:** none yet

---

## R21 — Command Centre loose ends after phase 6  [P4]

**Why:** phase 6 (`docs/superpowers/plans/2026-09-28-command-centre.md`) wired Books, margins, the diary, the drafts inbox, the quote calculator and the background refresh. These pieces were left out on purpose and are recorded here so they aren't lost.

**Do (each is small and independent):**
- *Drafts from Zoho itself.* The inbox lists only the drafts the assistant records (`cc_sync.py drafts-put`). A read-only Zoho Mail drafts listing (folder 6133510000000008016) in the daily pass would also catch drafts saved by hand and drop ones deleted in Zoho. Needs a tool on the zoho-mail read allowlist and a `drafts-sync` writer that replaces rather than merges.
- *Per-draft "open in Zoho".* The page links to the Drafts folder (`https://mail.zoho.com/zm/#mail/folder/drafts`, the .com data centre). A per-message link needs Zoho's message URL form confirmed on the owner's account first.
- *Static dashboard.* `scripts/reports/dashboard.py` shows no Books panel or margins. Only worth doing if the owner still opens the static page; otherwise retire it once the Command Centre has run a month.
- *Unlinked singer invoices.* Margins count only invoices linked to a booking; `singer_invoices.py margins` prints the unlinked total, the pages don't. Add an "unlinked: n, £x" line to Money's season margin.
- *Quote extras.* The calculator states the Christmas Eve/Day premium and leaves longer programmes and keyboard hire "quoted upfront", as the pages do; it never prices them.

**Skills:** none

---

## R22 — Barbershop Grams product line  [P1] [done 2026-09-03]

**What shipped:** a second product line at `/barbershop-grams/` (hub + repertoire page), a self-contained mini-site in its own visual register — a scoped `bs-` stylesheet plus its own nav and footer partials, insulated from the main site's CSS bundle and never including `partials/nav.html` or `partials/footer.html`. A `barbershop-gram` `<option>` on `contact.html` wiring the enquiry pre-fill, and `barbershop-grams/*.html` added to both claim validators (`validate_jsonld.py`, `validate_house_claims.py`), which previously could not see the directory at all. Sitemap and `llms.txt` entries for both pages.

Inbound links from the main site: `services.html` gets a note after the ensemble grid plus a "Gifts & Surprises" `Offer` inside its `OfferCatalog` JSON-LD; `weddings.html` and `corporate.html` each get one contextual paragraph link. `sitemap.xml` now lists 165 URLs.

**Deliberately not done, and why:**
- **No gram prices on `pricing.html`.** A section was added there (`a3dad63`) and reverted by owner decision (`10abc0d`): barbershop is sold separately from the choral service and its bookings are almost always a quartet, so listing its rates in the choral price table works against the separation the mini-site exists to maintain. `barbershop-grams/index.html` is the source of truth for the five gram prices; `pricing.html` stays the source of truth for choral prices. The `CLAUDE.md` convention was rewritten to carve this out.
- **No nav entry.** The original plan (and the task's own first draft) added a Services-dropdown item. It shipped in `e4ebdad`, then was **removed by owner decision** in `28e0e83`: `partials/nav.html` expands into every page via the build, so a dropdown item for a birthday-gram product appeared on `funerals.html`, every funeral music guide, all three `for-*.html` B2B pages, and `compare/london-funeral-singers.html` — a birthday-gift product surfaced to a bereaved visitor or a corporate buyer mid-funeral-enquiry. The spec's "dropdown only, never on funeral pages" constraint is unsatisfiable with one shared nav partial. The spec and plan were corrected in `c757d31` to record this rather than leave the stale intent standing.
- Comparison page (`compare/barbershopogram.html`) and a barbershop listen page — Phase 2, gated on a barbershop recording existing (`MANUAL-ACTIONS-REQUIRED.md` §28.1).
- Per-occasion pages — Phase 3, gated on Search Console evidence after a season live.
- Ads, directories, partnerships, and PR — Phase 4, human-only (`MANUAL-ACTIONS-REQUIRED.md` §28).

**Spec:** `docs/superpowers/specs/2026-09-03-barbershop-grams-design.md`
**Plan:** `docs/superpowers/plans/2026-09-03-barbershop-grams.md`

**Verify:**
```sh
./build.sh                                 # ends "Done." — House claims clean across 169 files checked.
python3 tests/test_competitor_claims.py    # 0 failure(s)
grep -c '<loc>' sitemap.xml                # 165
grep -n 'barbershop' validate_jsonld.py validate_house_claims.py   # both glob barbershop-grams/*.html
ls barbershop-grams/                       # index.html  repertoire.html
grep -rln 'barbershop-grams/' services.html weddings.html corporate.html   # all three
grep -n 'partials/nav.html\|partials/footer.html' barbershop-grams/*.html  # empty — mini-site never includes the main-site partials
```
