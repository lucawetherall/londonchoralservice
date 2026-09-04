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

## R13 — Borough page template is a rigid, visible mould across all 33 pages  [P3] [SPEC-FIRST]

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
