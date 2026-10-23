# Ad source without cookies: the campaign, carried from page to page

**Date:** 2026-10-23
**Status:** Implemented on branch `claude/cookieless-ad-source-2026-10-23` (PR for the owner's review). Builds on `2026-10-14-cookieless-ad-attribution.md`.

## Problem

The ad-visit tag from 14 Oct named only the landing page, and only on that page. 10 of 25 measured ad visits started on `pricing.html`, which has no form, so a visitor who went on to `contact.html` arrived with nothing. The tag never named the campaign either, although every ad click carries `utm_source=google&utm_medium=cpc&utm_campaign=<funeral-expert | wedding-leads | christmas-carol-singers-2026>` in its final URL suffix (sitelinks included). The forms' "How did you hear of us?" was optional and mixed "Searching on Google" with "A Google ad", which people confuse.

## Design

### 1. The label (partials/analytics.html)

- On an ad landing (a `gclid`, `gbraid` or `wbraid` in the URL) without cookie consent, `LCS_AD_VISIT` is `<landing slug> (<utm_campaign>)`, e.g. `pricing (wedding-leads)`. A `utm_campaign` outside `[a-z0-9-]{1,40}` is ignored: the label is the slug alone.
- At run time, for ad visitors only, every same-site page link (same origin, a `.html` or folder path) gets `lcs_av=<label>`. Never `tel:`, `mailto:`, WhatsApp, other sites, `#` links or downloads. Links are rewritten on DOMContentLoaded and again as each is clicked, middle-clicked or right-clicked (links added later; a cookie choice made since). Crawlers never see it.
- The next page takes `lcs_av` only if it matches the same strict pattern (page at most 80 characters, campaign at most 40) and the visitor came from one of our pages (`document.referrer` has our origin), so a typed, bookmarked or shared address is not an ad visit. A new click ID outranks it.
- Nothing is stored on the device. Once the visitor allows cookies, `lcsAdVisit()` returns nothing and links drop `lcs_av` as they are used; the existing Ref/`lcs-attr` flow takes over.
- Canonical tags were already absolute (`https://londonchoralservice.com/…`) on every served page but `404.html`, which has none, so `lcs_av` addresses never compete in search.
- Output everywhere: `Ad visit: <page>` or `Ad visit: <page> (<campaign>)` in WhatsApp text and the email body, and the form field `ad_visit` = `<page>` or `<page> (<campaign>)`. A message from a later page also says "via a Google ad".

### 2. Consumers

- `scripts/bookings/pipeline.py`: `AD_VISIT_RE` accepts the optional campaign; `ad_visit_parts`, `ad_visit_from_notes` and `ad_visit_campaign` read it (the campaign named outranks the page's; `PAGE_CAMPAIGNS` covers old notes); `CAMPAIGN_IDS` maps each slug to its Ads campaign id. `heard_from_notes` and `heard_kind` classify the client's answer. "ad ref" handling is unchanged.
- `.claude/agents/lcs-reply-drafter.md`, `lcs-review-bookings.md`, the handover's Appendix A (the dispatcher's enquiry-source rule) and Appendix B/E notes.

### 3. "How did you hear about us?" (every enquiry form)

- Required, with its own message ("Please choose how you heard about us.", linked by `aria-describedby`; `js/form.js` already marks and focuses an invalid field, and `js/private-events.js` now does the same for the register).
- Options: "A Google ad (marked Sponsored)", "A Google search result", then the page's other answers, then "Prefer not to say". The field name stays `hear`. The register's generic "Search" goes (Bing and others pick "Other").
- On `christmas.html` and `christmas-carol-services.html` the select's id was a duplicate of the films section's `id="hear"`, so its label named the section; the select is now `id="hear-from"`.
- Reading answers: "A Google ad" and "A Google ad (marked Sponsored)" are from an ad (client says); "A Google search result" is not an ad; the older "Searching on Google", the register's older "Search", "Google, not said which" and "Prefer not to say" keep the click-match verdict.

### 4. The reply drafter asks when nothing says

In its first reply to an email or WhatsApp enquiry that carries no source (no form answer, Ref or ad visit, and no word of how they found us), the reply drafter adds one short sentence asking how they found us. Never for a funeral enquiry, never in a follow-up. The answer, when it comes, goes in the pipeline notes with `pipeline.py heard <threadId> '<answer>'` (one line, no email address or phone number, once per enquiry).

## Testing

- `tests/test_ad_attribution.py`: the label under node (campaign, bad campaigns, `lcs_av` only from our own pages, length limits, a new click winning), link decoration, every form's required source field, the privacy text.
- `tests/test_pipeline.py`: ad visits with a campaign, the parsers, `heard_kind`, the `heard` command and its refusals.
- `tests/test_lead_tracking.mjs` (headless Chromium through Playwright, every external endpoint stubbed; skips without Playwright): leads after Accept for all 39 forms, Reject leaves no cookies and consent denied, and the ad-visit label in WhatsApp, email and the form, one click later too.
