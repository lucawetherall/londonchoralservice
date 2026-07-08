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

## R1 — Remove self-serving review schema and rating claims  [P1] [ready] [S]

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

## R2 — Refresh stale sitemap lastmod dates  [P2] [ready] [S]

**Why:** 82 of 103 `<url>` entries say `<lastmod>2026-05-14` while the underlying files were last edited 2026-07-08 (several copy sweeps since). Stale lastmod misrepresents freshness to crawlers and erodes trust in the whole sitemap signal.

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
**Stretch (SPEC-FIRST if pursued):** generate sitemap.xml inside build.sh from the file tree + git dates, eliminating the hand-maintenance convention entirely.

**Skills:** build-and-verify

---

## R3 — Real VideoObject dates/durations + missing sameAs  [P2] [BLOCKED-ON-HUMAN]

**Why:** Four `VideoObject` nodes ship placeholder `"uploadDate": "2025-01-01"` and no `duration` (flagged by inline TODO comments); `LocalBusiness.sameAs` lacks the canonical Google Maps URL and LinkedIn, `Person.sameAs` lacks ORCID. Fake dates in production structured data undercut the credibility of everything else in the graph.

**Files & anchors:**
- `grep -n 'uploadDate' listen.html pricing.html` — placeholders
- `grep -n 'TODO' data/seo-fix-discovered-urls.yml` — the values awaiting human resolution
- `grep -n 'TODO' index.html about.html` — the sameAs insertion points

**Blocked on:** MANUAL-ACTIONS-REQUIRED.md §1 (GBP canonical URL) and the YAML's video-metadata lookups (YouTube consent gate blocks automated fetch). The human fills `data/seo-fix-discovered-urls.yml`.

**Do (once unblocked):** Copy each resolved value from the YAML into the matching JSON-LD field: `uploadDate` (YYYY-MM-DD) and `duration` (ISO 8601, e.g. `PT3M42S`) for the four videos in listen.html (3) and pricing.html (1); append GBP + LinkedIn URLs to `LocalBusiness.sameAs` in index.html (replacing the share.google short link); ORCID to `Person.sameAs` in about.html. Remove the corresponding TODO comments.

**Verify:** `grep -rn '2025-01-01' --include='*.html' .` → empty; `./build.sh` green; TODO comments gone from touched files.

**Skills:** build-and-verify

---

## R4 — Cookie consent / Google Consent Mode v2  [P4] [SPEC-FIRST] [L]

**Why:** GA4 + Google Ads load (deferred, but unconditionally) with no consent mechanism. For a UK-audience business this is a PECR/GDPR gap — analytics cookies require prior consent. Also a commercial concern: Google Ads conversion tracking without Consent Mode v2 loses modelling eligibility.

**Sequencing insight (the important part):** the GA4 snippet is duplicated inline in every page's `<head>` — it is **not** a partial. Implementing consent as a 106-file inline edit would be unmaintainable. **Step 1 of any implementation: extract the analytics snippet into a new `partials/analytics.html` with `@include-start/@include-end` markers swept into all pages via script** (see build-and-verify → site-wide sweeps), verify that no-behaviour-change refactor alone, and only then implement consent logic once, inside the partial.

**Files & anchors:** `grep -rln 'G-9FENN7VS0E' --include='*.html' . | wc -l` (~106 pages); `build.sh` (partial expansion); `privacy.html` (policy text will need updating).

**Spec must cover:** banner UX (self-built vs CMP), Consent Mode v2 default-denied config, storage of choice, effect on the existing lazy-load pattern, privacy-policy updates.

**Skills:** build-and-verify

---

## R5 — Merge duplicate form scripts  [P4] [ready] [M]

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

1. **listen.html has no audio.** CSS defines `.audio-placeholder` (`grep -n 'audio-placeholder' css/components.css css/pages.css`) but no `<audio>` element exists anywhere. Either add real `<audio>` elements with self-hosted samples (assets from owner — that part BLOCKED-ON-HUMAN) or delete the dead CSS. Deleting dead CSS = css/ edit = mandatory rebuild.
2. **No consolidated FAQ page.** FAQ content exists as per-page `FAQPage` JSON-LD + visible accordions. A `/faq.html` hub aggregating the best questions (linked from footer) captures long-tail question queries. Use the `new-page` skill; dedupe against existing per-page FAQs — don't duplicate the same Q&A schema on two pages.
3. **Single generic og-image for all ~106 pages** (`grep -rln 'assets/og-image.png' --include='*.html' . | wc -l`). Per-service images (weddings, funerals, christmas, corporate + one per major hub) would lift social CTR. Image creation BLOCKED-ON-HUMAN; the wiring (og:image/twitter:image per page) is agent work once assets land in `assets/`.

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

## Explicitly not on the list

- **Copy rewrites** — tracked separately in `SITE-STOP-SLOP-PLAN.md` (Parts 3–4 are its own prioritised backlog).
- **Off-site SEO / listings / GBP** — human-only, in `MANUAL-ACTIONS-REQUIRED.md`.
- Strengths to leave alone: semantic HTML + skip links + labelled forms, complete sitemap coverage, disciplined meta/canonical/hreflang/OG, deferred GA4 loading, self-hosted preloaded fonts.
