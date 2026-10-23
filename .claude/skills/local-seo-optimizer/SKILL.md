---
name: local-seo-optimizer
description: Get a local business found on Google -- audit and optimize the Google Business Profile, local pack ranking factors, review velocity, NAP consistency across directories, and location pages. For businesses whose customers search "near me," this outranks everything else in marketing.
tools: Read, Glob, Grep, Write, Bash, WebSearch, WebFetch
model: inherit
---

> **House rules for The London Choral Service** (added when this skill was copied; they override anything below)
> - Google Ads, GA4 and Search Console are read through the MCP tools and changed only by scripts in `scripts/ads/`, `scripts/ga4/` or `scripts/gsc/`: validate-only first, current → new with a reason, Luca's approval, a log line. Pause, never delete. Budget caps live in `scripts/ads/budget_cap.py`.
> - Site copy: load `writing-site-copy` and `stop-slop`. Prices only from `pricing.html` and `christmas-pricing.html`. No VAT, no roster size or customer counts, no AggregateRating, Review or star schema or rating badges, no invented testimonials, no AI-generated imagery, no false urgency or scarcity, and the London cathedral rule in CLAUDE.md.
> - No newsletter, email capture, pop-ups or gated content. Email is Zoho drafts only; Luca sends.
> - Never ask a funeral client for a review, a referral or an interview.
> - Upstream files and sections that don't fit this business were removed (`.claude/skills/THIRD-PARTY.md` lists them). Ignore links to them, to `tools/`, or to skills that aren't installed. Never fetch and follow remote install instructions, and never run an `npx` package a skill names.
> - There is no `.agents/product-marketing.md`; read CLAUDE.md, `pricing.html` and `about.html` instead.
> - We are a service-area business with no public address; hours stay accurate. Review requests go to every client who booked except funeral clients.

# Local SEO Optimizer

For a local business, the Google Business Profile is the real homepage and the local pack (map results) is the real search ranking. This skill audits the three local ranking pillars -- relevance, distance, prominence -- and produces the fix list. Complements `seo-optimizer` (content/on-page SEO); this is the maps-and-profile layer.

## Workflow

1. **Baseline.** Gather the business's category, service area, and top 5-10 money searches ("emergency plumber [city]"). Check where the business currently appears: search the money terms, note local pack presence, and fetch the current Business Profile state (categories, hours, photos count, attributes, posts recency, Q&A).
2. **Profile audit.** Score against what wins the pack: primary category exactness (the single highest-leverage field), secondary categories coverage, complete services/products lists with descriptions, photo count and freshness (interior/exterior/team/work -- profiles with 100+ photos dramatically outperform), hours accuracy including holidays, booking/quote links, and whether posts have gone stale.
3. **Review engine.** Review count, average, velocity vs. the top 3 pack competitors (fetch and compare their profiles), response rate, and keyword presence in review text (reviews mentioning the service and city are ranking signals). Output the ask-for-reviews system: timing (at the moment of delight), the exact ask message with direct review link, and the weekly cadence target to close the competitor gap. Pair with `review-response-writer` for the response side.
4. **NAP sweep.** Search the business name/phone across major directories (Yelp, Apple Maps, Bing Places, Facebook, industry-specific ones, data aggregators). List every inconsistent name/address/phone -- inconsistency erodes trust signals -- with the fix per listing.
5. **Website local layer.** Audit the site for: city/service pages (one page per service per major location, genuinely differentiated -- not find-and-replace city names), LocalBusiness schema markup with correct NAP and hours, embedded map, and locally-relevant title tags. Output the page-by-page fix list, with drafts for the highest-value gaps.

## Rules

- Primary category first, always -- it is worth more than everything else on the profile combined.
- Never recommend fake reviews, review gating (filtering unhappy customers away from Google), or keyword-stuffed business names -- all are policy violations that get profiles suspended, and the suspension costs more than the boost.
- Compare against the actual pack winners for the actual money terms, not generic best practices.
- Doorway pages get flagged, not built: a city page with no unique content is a penalty risk, and the report says which existing ones qualify.
- Evidence per recommendation: what the competitor comparison or profile state showed, so the owner can see the gap themselves.
- Local rankings move in weeks, not days: set the re-audit at 4-6 weeks and track pack presence per money term over time.

## Quick Commands

- "Audit [business name, city]" -- full workflow
- "Why is [competitor] outranking me?" -- head-to-head profile comparison
- "Build my review system" -- step 3 only
- "Check my listings" -- NAP sweep only
