# Third-party skills

Skills in this folder that came from other people's repositories, copied at a pinned version after a read of every file. Each copied `SKILL.md` starts with a "House rules for The London Choral Service" block that overrides the upstream text; the site's own rules in CLAUDE.md win over anything here. Licence texts are in `.claude/third-party-licenses/`.

To update one: clone the source at a new tag into a scratch folder (never into the repo), diff it against the copy here, read every changed file, keep the house-rules block and the removals below, and change the version on this page.

## coreyhaines31/marketingskills, MIT

| Skill | Version | Removed on copying |
|---|---|---|
| `copy-editing`, `seo-audit`, `site-architecture` | v1.1.0 (Feb 2026, commits `127b45e9`, `3b6c5690`) | Copied whole, before this page existed; no house-rules block |
| `analytics` | v2.13.0, commit `e85f3cb` | `evals/` |
| `conversion-tracking` | v2.13.0 | `evals/`, `scripts/`, `assets/gtm-recipes/` (the site has no Tag Manager), all platform snippets but the four generic ones, `references/server-side.md` (tells the agent to fetch and follow a vendor's remote install file), `ecommerce-platforms.md`, `meta.md`, `other-platforms.md` |
| `cro` | v2.13.0 | `evals/`, `references/experiments.md` (SaaS tests: review scores, exit-intent pop-ups, email capture) |
| `ad-creative` | v2.13.0 | `evals/`, `assets/`, the "Generating Ad Visuals" and "Creative Review Page" sections and the generative-tools, motion-video, iMessage-video, short-form-video, Meta-formats and creative-review-page references (AI imagery, staged chats), "Tool Integrations" (an ad-account CLI and the author's product) |
| `ai-seo` | v2.13.0 | `evals/`, `references/okf.md`, `agent-defaults.md`, `multilingual-and-commerce.md`; the `Review`/`AggregateRating` schema row; the `npx is-agentic` tool |
| `programmatic-seo` | v2.13.0 | `evals/`, `references/implementation-platforms.md` (CMS and partner-platform advice) |
| `co-marketing` | v2.13.0 | `evals/`, `references/partnership-types.md` (SaaS figures, giveaways, unlicensed brand use) |
| `referrals` | v2.13.0 | `evals/`, the "Email Sequences" and "Affiliate Programs" sections, the viral-mechanisms, program-examples and affiliate references (reward discounts, nurture emails, urgency) |
| `cold-email` | v2.13.0 | `evals/`, the "Before You Send", "Beyond Email", "When They Reply" and "Tool Integrations" sections, the deliverability, reply-handling, LinkedIn and multichannel references (sequencers, invented sender personas, automated sends, list uploads). Upstream compliance is US-only; the house block adds PECR |
| `customer-research` | v2.13.0 | `evals/`; the house block adds: say it is research, never interview funeral clients |

Not copied: `ads` (its name clashes with the claude-ads router and its advice assumes large budgets), `schema` (recommends review stars), `emails` (`marketing:email-sequence` covers it), `offers` (scarcity pricing, guarantees and instalments against a fixed price list), and `tools/clis/` (its Google Ads client changes accounts with no validate-only step).

## onewave-ai/claude-skills, MIT

| Skill | Version | Removed on copying |
|---|---|---|
| `local-seo-optimizer` | commit `b2267d9` (19 Oct 2026) | Nothing |

## garrettjsmith/localseoskills, MIT

| Skill | Version | Removed on copying |
|---|---|---|
| `gbp-optimization` | commit `405ce20` (15 Aug 2026) | Nothing; its pointer to the paid LocalSEOData routing file is left dangling on purpose |
| `gbp-posts` | commit `405ce20` | Nothing; the house block overrides the phone-number template and the "limited-time" framing |

## Read but not installed

- **AgriciDaniel/claude-ads** is a plugin at user scope, not a copy: v2.1.0, installed commit `fc3908e` (CI-only changes after the vetted tag `4a74a5a`), marketplace `ai-marketing-hub-claude-ads`, auto-update off. Read-only and Google only; never use its `--apply` paths. Its run files go to `.claude-ads/`, which `.gitignore` excludes.
- **thatrebeccarae/claude-marketing** (commit `a8a63ec`): its UTM rules became `docs/utm-conventions.md`.
- **aaron-he-zhu/seo-geo-claude-skills** (tag v9.9.12): its entity-signal checklist feeds the monthly growth review.
