# Head block checklist

Every page's `<head>` follows the same structure. When cloning an exemplar, walk this list top to bottom. "Invariant" = keep exactly as cloned; "Variable" = must be updated for the new page.

| # | Element | Status | Notes |
|---|---|---|---|
| 1 | `<meta charset="UTF-8">` | Invariant | |
| 2 | `@include-start/end partials/head-extras.html` markers + content | Invariant | Font preloads; build.sh refreshes the content |
| 3 | `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">` | Invariant | |
| 4 | GA4/Ads deferred-load `<script>` | Invariant | IDs `G-9FENN7VS0E` and `AW-17988388404`. Never modify per-page; site-wide analytics changes are a scripted sweep (see build-and-verify skill) |
| 5 | `<title>` | **Variable** | Unique. Pattern: primary keyword first, brand optional. ~50–60 chars |
| 6 | `<meta name="description">` | **Variable** | Unique, **141–161 chars**: `python3 -c "print(len('TEXT'))"`. No rating claims. UK English |
| 7 | `<meta name="theme-color" content="#F7F3EE">` | Invariant | |
| 8 | `<meta name="robots" content="index, follow">` | Invariant | |
| 9 | `<link rel="canonical">` | **Variable** | Absolute URL: `https://londonchoralservice.com/<path>.html` (homepage is `/`) |
| 10 | `<link rel="alternate" hreflang="en-gb">` + `hreflang="x-default"` | **Variable** | Both identical to the canonical URL |
| 11 | `og:title`, `og:description` | **Variable** | Usually mirror title/description |
| 12 | `og:type` | Semi | `website` for most pages; `article` for music guides |
| 13 | `og:url` | **Variable** | = canonical |
| 14 | `og:locale` (`en_GB`), `og:site_name` (`London Choral Service`) | Invariant | |
| 15 | `og:image` | Invariant | `https://londonchoralservice.com/assets/og-image.png` (shared site-wide) |
| 16 | `twitter:card` (`summary_large_image`), `twitter:title`, `twitter:description`, `twitter:image` | **Variable** | Mirror the OG fields |
| 17 | `dns-prefetch` links (googletagmanager.com, api.web3forms.com) | Invariant | |
| 18 | Inlined `<style>` block | Invariant | Generated — never hand-edit; build.sh refreshes |
| 19 | JSON-LD `<script type="application/ld+json">` | **Variable** | See `jsonld-by-page-type.md` |
| 20 | Favicon/apple-touch-icon links | Invariant | |

## Common mistakes

- Meta description outside 141–161 chars (count *after* final wording, including punctuation).
- Canonical/hreflang/og:url disagreeing with each other or with the real file path.
- Leaving the exemplar's title/description in any of the six places it appears (title, description, og:title, og:description, twitter:title, twitter:description).
- Editing the inlined `<style>` block or the GA4 snippet.
