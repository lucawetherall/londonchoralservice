# CLAUDE.md

The website of The London Choral Service (Alma Consort Ltd) — a choir-for-hire business selling professional singers for funerals, weddings, corporate events, and Christmas across the UK. ~106 hand-authored static HTML pages served directly by GitHub Pages. No framework, no package.json, no CI.

## Critical: the build pipeline

- **Never hand-edit the inlined `<style>` block in any page** — edit `css/tokens|base|layout|components|pages.css` and run `./build.sh`. `css/style.css` is generated too.
- **Never hand-edit content between `<!-- @include-start … -->` / `@include-end` markers** — edit `partials/*.html` and run `./build.sh`.
- Run `./build.sh` after any `css/` or `partials/` change or new page; a ~106-file diff afterwards is normal. **Load the `build-and-verify` skill before touching styles, nav, footer, or doing any bulk edit.**
- The built output is what gets committed and deployed — there is no CI build step.

## Repo map

- Root `*.html` — core pages (index, services, weddings, funerals, corporate, christmas, pricing, listen, about, contact, privacy, thank-you, 404) + 3 B2B landing pages (`for-*.html`)
- `areas/` — 20 city pages; `areas/london/` — 33 borough pages (programmatic local SEO)
- `music-guides/` — 37 long-form SEO articles + index
- `partials/` — nav, footer, head-extras (**sources of truth** for shared markup)
- `css/` — five source files → generated `style.css` (never edit generated output)
- `js/` — contact.js, landing-form.js (Web3Forms + hCaptcha), nav.js, music-guides.js
- `data/seo-fix-discovered-urls.yml` — **single source of truth** for unresolved schema values (GBP URL, video dates); never invent these
- `docs/ROADMAP.md` — prioritised backlog with self-contained items; `docs/superpowers/` — dated specs and plans
- `MANUAL-ACTIONS-REQUIRED.md` — human-only dashboard tasks. **Never attempt these**
- `SITE-STOP-SLOP-PLAN.md` — house copy-style audit (distilled into the `writing-site-copy` skill)

## Commands

- Build + validate: `./build.sh`
- JSON-LD check alone: `python3 validate_jsonld.py`
- Competitor claim check alone: `python3 validate_competitor_claims.py`
- Validator tests: `python3 tests/test_competitor_claims.py`
- Local preview: `python3 -m http.server 8000`

## Conventions

- Meta descriptions: unique, 141–161 chars. Every page: canonical + hreflang (en-gb, x-default) + full OG/Twitter tags.
- `sitemap.xml` and `llms.txt` are hand-maintained — update both (fresh `lastmod`) when adding or materially editing a page.
- **Never add `AggregateRating`/`Review`/star-rating schema** — self-serving review markup violates Google policy.
- UK English everywhere. All visible copy must pass the `writing-site-copy` skill.
- GA4/Ads IDs `G-9FENN7VS0E` / `AW-17988388404`: the snippet is duplicated per page, *not* a partial — analytics changes are scripted site-wide sweeps (see `build-and-verify`).
- Prices quoted anywhere must match `pricing.html`.
- Competitor figures must match `data/competitor-pricing.yml`, quote the source verbatim, and carry a visible checked date. `build.sh` fails if a price on a `compare/` page is not derivable from that file. Re-check quarterly (`MANUAL-ACTIONS-REQUIRED.md` §11).
- `compare/` addresses families. Never link to it from a `for-*.html` page or reuse its inc-VAT figures there — a VAT-registered business buyer reclaims VAT, so those figures do not describe their position.
- **Alma Consort Ltd is not VAT-registered.** Never state or imply otherwise.
- Forms POST to Web3Forms with an hCaptcha guard — don't remove the `h-captcha-response` check or the `botcheck` honeypot.

## Workflow

- Small tasks: pick from `docs/ROADMAP.md` — items are self-contained with verification commands; don't re-derive the analysis. Respect `BLOCKED-ON-HUMAN` and `SPEC-FIRST` labels.
- Larger features: write a spec in `docs/superpowers/specs/` and a plan in `docs/superpowers/plans/`, named `YYYY-MM-DD-<name>.md`, matching the existing documents' style.
- Before committing: run the `build-and-verify` checklist. Commit messages follow the existing history style (`fix(scope): …`, `copy: …`, `chore: …`).

## Project skills

- `build-and-verify` — the build pipeline, diff shapes, verification checklist. Load before any style/partial/bulk change.
- `new-page` — clone-an-exemplar workflow, head checklist, JSON-LD per page type, wiring checklist.
- `writing-site-copy` — house anti-slop copy rules. Load before writing any visible text.

(Generic skills also installed: copy-editing, seo-audit, site-architecture.)
