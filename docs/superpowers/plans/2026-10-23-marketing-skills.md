# Marketing Skills Plan

> **For agentic workers:** load `writing-site-copy` and `stop-slop` before writing any visible text and `build-and-verify` before any build. Which skills exist, at which version and with what removed: `.claude/skills/THIRD-PARTY.md`. Business figures behind this plan are in the private Monday reports, not here.

**Goal:** Install the marketing, tracking, outreach and local-SEO skills that pass a line-by-line read, put them on the Monday review where they add something, and use them in order of money and urgency: measurement, Christmas, organic, local, partnerships.

**Owner decisions (23 Oct 2026):** claude-marketing and seo-geo-claude-skills are not installed; their useful rules are borrowed (`docs/utm-conventions.md`, the entity checklist). Outreach emails go to limited companies, LLPs and other incorporated bodies only (PECR); see "Outreach" in CLAUDE.md.

## What is installed

- **claude-ads** plugin (AgriciDaniel), v2.1.0, user scope, auto-update off: read-only, Google only. Findings with evidence; v2.1.0 gives no numeric score. Never its `--apply` paths. Run files in `.claude-ads/` (gitignored).
- **Copied into `.claude/skills/`:** `analytics`, `conversion-tracking`, `cro`, `ad-creative`, `ai-seo`, `programmatic-seo`, `co-marketing`, `referrals`, `cold-email`, `customer-research` (marketingskills v2.13.0), `local-seo-optimizer` (onewave-ai), `gbp-optimization`, `gbp-posts` (localseoskills). Each carries a house-rules block.
- **claude-seo** v2.4.0 (already installed) stays the SEO suite. The old v1.7.0 standalone copies in `~/.claude` were moved to `~/.claude/backup-2026-10-23-claude-seo-1.7.0/`, so plain `seo-audit` now resolves to the project copy.

## Monday review (pending: lands after the independent review of the weekly task now in progress)

- **Every Monday, `lcs-review-ads`:** refresh "THE ACCOUNT AS THE OWNER SET IT" (home counties, christmas.html and christmas-pricing.html landing pages, Christmas bids and the £8 window). Add four checks distilled from claude-ads' Google controls: a TRACKING ALARM when a primary conversion is unseen for 14 days while the pipeline shows enquiries from that channel; a primary/secondary sanity check including the legacy "Contact" actions; replacement copy for any ad below GOOD or short of unique headlines or sitelinks; when lost-to-rank exceeds 40%, a bid or relevance fix, never a budget rise. Any missing field goes into section 4 of `weekly_review.py` as a read-only GAQL field.
- **First Monday of the month, new `lcs-review-growth`** (Sonnet, read-only, text only): claude-ads `ads-google` on the saved report as an export; `cro` on one ad landing page in rotation; `local-seo-optimizer` + `gbp-optimization` NAP check of the live listings in `docs/off-site-listings-pack.md`; two GBP post drafts for Luca to post; `ai-seo` on the top three organic pages; the entity checklist (sameAs, consistent naming of Alma Consort Ltd and The London Choral Service). Its proposals join the dispatcher's single numbered list and approval question. Dispatcher prompt, Appendix A of `docs/HANDOVER-2026-09-27-ads-analytics.md` and the CLAUDE.md weekly-review bullet change together.
- **Quarterly, live session:** full `/claude-ads:ads audit google` with the read-only Ads MCP; `claude-seo:seo-programmatic` on the area and borough pages (feeds R13); `claude-seo:seo-audit`. First one alongside the MANUAL §11 competitor price check in mid-November.
- **Never in a scheduled run:** page or copy edits, outreach drafts, Ads changes, schema changes.

## Work, in order

1. **Measurement (by 30 Oct).** `conversion-tracking`, `analytics`, `claude-ads:ads-attribution`. "Submit lead form" and GA4 `generate_lead` have not registered since the 26–27 Sep tracking rebuild although web-form enquiries keep arriving; find the cause (likely the conversion racing the redirect to `thank-you.html`), fix it in `partials/analytics.html` and `js/form.js`, verify on the live site with Luca's OK. Running in its own session.
2. **Christmas (to 6 Nov).** `claude-ads:ads-creative`, `ads-landing`, `ad-creative`, `cro`. New headlines, descriptions and two sitelinks per campaign in a dated `scripts/ads/` script modelled on `ad_strength_sitelinks_2026_09_28.py` (validate-only, approval, log; price pins stay). CRO pass on `christmas.html`, `christmas-pricing.html`, `for-event-managers.html`.
3. **Organic (November).** `claude-seo:seo-page`, `seo-programmatic`, `seo-geo`, `seo-schema`, plus `ai-seo` and `programmatic-seo`. Page-one pushes for the homepage, "hire a choir" and "how to book a choir"; links from high-traffic guides (Nine Lessons first) to the hiring pages; the area/borough thin-content and overlap audit; a Person, Service and FAQPage schema check.
4. **Local (November).** `gbp-optimization`, `local-seo-optimizer`, `claude-seo:seo-local`. GBP audit and the steps to close MANUAL §1; the review link for §23; the listings round from the listings pack (Luca creates accounts and presses Publish).
5. **Partnerships and outreach (corporate now; funeral and wedding trade from late November).** `co-marketing`, `referrals`, `cold-email`, `customer-research`. Companies House check, one Zoho draft per firm to its published address, opt-out line, UTMs from `docs/utm-conventions.md`; prospect and opt-out lists in `~/lcs-private/outreach.csv`.

## Verification

- A fresh session lists `claude-ads:*` and the 13 copied skills; `/claude-ads:ads setup` records Google only, the budget ceilings and no change authority.
- `./build.sh`, `python3 scripts/stage_site.py` and `python3 tests/test_stage_site.py` pass.
- The growth agent, once written, is dry-run in a live session against a saved report (`report_sections.py --date <date>`) before its first scheduled run: a GROWTH block, no files written.
- After step 1, section 3 of the Monday report shows "Submit lead form" seen again.
