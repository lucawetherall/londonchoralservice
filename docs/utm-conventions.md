# UTM conventions

How we tag links that point at londonchoralservice.com from outside the site, so GA4 can tell each source apart. Rules adapted from the `utm-attribution-strategy` skill in thatrebeccarae/claude-marketing (MIT, commit `a8a63ec`), cut down to the channels we use.

## Rules

- Lower case, words joined by hyphens. GA4 treats `Email` and `email` as two sources.
- Every tagged link carries `utm_source`, `utm_medium` and `utm_campaign`. `utm_content` only when one message holds two links worth telling apart.
- `utm_medium` uses GA4's own channel words (`cpc`, `email`, `referral`, `organic`), or the visit lands in "Unassigned".
- Never tag links between our own pages: a tagged internal link starts a new session and wipes the real source.
- Never put a name, email address, booking ref or venue in a tag. A firm's name in `utm_source` is fine only in the `partner-<slug>` form below, for a partner that has agreed to work with us.
- Tag the final URL (the `.html` page), not a redirect stub, so nothing is lost on the way.

## Values

| Where the link lives | `utm_source` | `utm_medium` | `utm_campaign` |
|---|---|---|---|
| Google Ads (final URL suffix, already set) | `google` | `cpc` | `funeral-expert`, `wedding-leads`, `christmas-carol-singers-2026` |
| Google Business Profile website link | `google` | `organic` | `gbp` |
| First-contact email to a firm (Zoho draft) | `outreach` | `email` | `<audience>-<yyyy-mm>`, e.g. `funeral-directors-2026-12`, `event-managers-2026-10` |
| Follow-up in the same outreach thread | `outreach` | `email` | same campaign as the first email |
| A partner's own website or referral sheet | `partner-<slug>` | `referral` | `partner-programme` |
| Marketplace or directory listing (Hitched, Bridebook, Yell, Bing Places, Apple Business) | `<site>` e.g. `hitched` | `referral` | `listing` |
| Printed material with a short URL or QR code | `print` | `referral` | `<item>-<yyyy>`, e.g. `order-of-service-insert-2026` |

`utm_content`, when needed: `<link-position>`, e.g. `prices-link`, `contact-link`.

## Example

`https://londonchoralservice.com/for-funeral-directors.html?utm_source=outreach&utm_medium=email&utm_campaign=funeral-directors-2026-12`

## How the site uses them

`partials/analytics.html` keeps the five UTM values for the tab once the visitor has allowed cookies, and the web form sends them with the enquiry, so a booking can be traced to its campaign in the pipeline. Without consent nothing is kept. `robots.txt` already disallows `?utm_` URLs, so tagged links don't create duplicate pages in search.
