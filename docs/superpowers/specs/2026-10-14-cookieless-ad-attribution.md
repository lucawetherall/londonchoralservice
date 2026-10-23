# Ad attribution for visitors who decline cookies

**Date:** 2026-10-14
**Status:** Approved for implementation. The owner, live in chat on 14 Oct 2026, approved both features below ("you have full permission to do all the best things").

## Problem

Most visitors ignore or reject the cookie sheet. From 16 Sep to 13 Oct, Google Ads counted 73 clicks and GA4 26 paid-search sessions, and no enquiry this month carried an ad reference. Under the current rules a click ID reaches us only with cookie consent: the web form's `gclid` line, or the "Ref: XXXX" that `lcsLabelMessage` adds to WhatsApp messages and emails. Without consent we can't tell which enquiries the ads produced, and `upload_bookings.py` can't report those bookings to Google.

## Design

### 1. Ad-visit tag from the landing URL (no device storage)

- `partials/analytics.html` reads the landing URL once. If it holds `gclid`, `gbraid` or `wbraid`, it keeps the page's slug in a JS variable (`LCS_AD_VISIT`). Nothing goes into localStorage, sessionStorage or a cookie, and the click ID itself is never shown or sent. `lcsAdVisit()` returns the slug only while consent is not `granted`. With consent, the existing Ref/gclid flow runs unchanged.
- The slug is the page path without `.html` (`weddings`, `areas/london/camden`, `home` for `/`), restricted to `a-z 0-9 / -`. It names a page. It never identifies a person.
- On that page only:
  - WhatsApp: `(Sent from your “Weddings” page, via a Google ad. Ad visit: weddings)`.
  - Email: the subject as now; the body gets `Ad visit: weddings`.
  - Web form (`js/form.js`, `js/private-events.js`): a field `ad_visit` = `weddings`, which Web3Forms prints as its own line in the notification.
  
  Another page opened later carries no ad visit. Since 2026-10-23 (`url_passthrough` in `partials/analytics.html`) a later page reached from the landing page has the click ID in its URL too, with a `_gl` marker and our own site as referrer; `lcsLandedHere()` tells it apart, so the tag still names the landing page only. On that later page a ticked ad-measurement box sends the click ID, and an Accept writes `_gcl_aw` and the Ref from its URL.
- Campaign mapping (in the handover's Appendix A and `lcs-review-bookings.md`): `weddings` → wedding-leads; `funerals` → funeral expert; `carol-singers`, `christmas-pricing`, `christmas` → Christmas. Any other page is "from an ad (landing URL)" with no campaign named.
- Recording: the reply drafter passes `ad_visit` to `pipeline.py add`, which checks the slug and writes `ad visit: <slug>` into notes. The enquiries sheet still holds no name or email. The Monday ENQUIRIES line shows `ad ref: no · ad visit: weddings`, and the enquiry-source cross-check counts an ad visit as "from an ad (landing URL)".

### 2. Optional ad-measurement consent on the enquiry forms

- Every enquiry form (14 main-site forms, `private-events.html`, `planners-and-venues.html` and the 23 destination pages) gets an unticked checkbox `ad_measurement` = `yes`:

  > Let us tell Google if your booking came from one of its ads. Google receives a scrambled (hashed) copy of your email address, never the address itself.

  It sits before the captcha, with a link to the privacy policy. It is optional and never pre-ticked, and the wording doesn't push either way.
- If it is ticked and the current URL holds a click ID, the submission also carries `gclid`/`gbraid`/`wbraid` from the URL. Nothing is stored.
- The reply drafter (and the Monday review, when it records a booking) sets the ledger's existing `consent` column to `form` when the client's first message is a web-form enquiry with `ad_measurement: yes`. `pipeline.py add` takes `"ad_measurement": "yes"` and notes `ad measurement: yes`. No new ledger column is needed.
- `upload_bookings.py`: `consent` = `form` counts as ad_user_data GRANTED, just as `granted` does.
  - **With a click ID**, the booking uploads as before (the hashed email too when enhanced conversions for leads is on).
  - **Without a click ID**, the booking uploads with the hashed email alone, but only when enhanced conversions for leads is on in the account. Otherwise it is skipped with that reason.
  - Verified 14 Oct 2026 against Google's Data Manager guide "Send events" (Google Ads offline conversions / enhanced conversions for leads): each event must set at least one of `adIdentifiers`, session attributes, `userData` or `eventDeviceInfo.ipAddress`, so `userData` alone is valid. Google matches the hashed email against signed-in accounts that clicked an ad.
  - Rows with `consent` = `granted` and no click ID still skip: cookie consent alone never sends an email-only upload.
- The weekly report's ledger line adds the count of bookings with the box ticked.

### 3. Privacy policy and banner

- `privacy.html#cookies` describes the ad-visit tag (what it contains, where it goes, that nothing is stored) and the checkbox (`#ad-measurement`: what Google receives, only for bookings, optional, how to withdraw). The "last updated" date moves to 14 October 2026.
- The cookie sheet on Alma Consort private-register pages (anything with `.pe-header`) says "see which Google ads lead to enquiries" instead of "our Google ads".

## Unchanged

The hCaptcha guard, the `botcheck` honeypot, Consent Mode defaults (denied), Web3Forms POSTs, the Ref/gclid flow for consenting visitors, Google Ads, GA4, Zoho and the private ledger files.

## Testing

- `tests/test_ad_attribution.py` covers:
  - the slug function under node;
  - the partial never writing the ad visit to storage;
  - every enquiry form having the unticked box;
  - both form scripts sending `ad_visit` and `ad_measurement`.
- `tests/test_upload_bookings.py`: `form` consent with and without a click ID, with enhanced conversions for leads on and off.
- `tests/test_pipeline.py`: `ad_visit`/`ad_measurement` written to notes; a bad slug is refused.
- Browser checks on a local server:
  - `weddings.html?gclid=TEST123` with consent unset shows the tag on WhatsApp, email and the form, writes nothing to storage or cookies, and never shows the click ID;
  - without a click ID there is no tag;
  - with consent accepted the old Ref appears;
  - a ticked box adds `ad_measurement`.
