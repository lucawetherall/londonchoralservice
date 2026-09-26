# Google Ads change log

Every change applied to the Google Ads account (customer 8733881378) is logged here, newest first. Nothing is logged until it has been validated (`validate_only=True`), shown as current value → new value with a reason, and explicitly approved.

| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |
|---|---|---|---|---|---|
| 2026-09-26 01:43 | campaign "Christmas carol singers – events 2026" (24295921372) | (new) | does not exist → created PAUSED: Search, £5.00/day, max CPC £3.50, Greater London, 4 ad groups, exact+phrase only, ends 2026-12-20 | Hyper-targeted Christmas carol singers for events, landing on christmas-pricing.html | `scripts/ads/create_christmas_carol_campaign_2026.py` |
| 2026-09-26 01:12 | Account conversion settings | Enhanced conversions (web) | not configured → on, managed through Google tag | Recover leads lost to cross-device journeys and cookie loss; site sends hashed email/phone via gtag user_data on consent | Google Ads UI (API cannot change it) |
| 2026-09-26 01:12 | conversion_action "Contact" (7566855536) | primary_for_goal | primary (counts in Conversions, drives bidding) → secondary (reported only) | Page-load rule on thank-you.html counted the same enquiry the site tag already counts | Google Ads UI (API refuses: MUTATE_NOT_ALLOWED) |
| 2026-09-26 00:57 | conversion_action "WhatsApp or email click" (7796284061) | primary_for_goal | secondary (reported only) → primary (counts in Conversions, drives bidding) | WhatsApp and email are the preferred contact routes (owner, 2026-09-26); one per ad click caps accidental taps | `scripts/ads/set_conversion_primary.py` |
| 2026-09-26 00:47 | conversion_action "Contact (1)" (7566867509) | primary_for_goal | primary (counts in Conversions, drives bidding) → secondary (reported only) | GA4 import of ads_conversion_Contact_1, which fired twice per thank-you view; the same enquiry again | `scripts/ads/conversion_actions_2026_09.py` |
| 2026-09-26 00:47 | conversion_action "Call click" | (new) | does not exist → created: PHONE_CALL_LEAD, one per click, secondary, £1 | Taps on the phone number were counted as full leads via a thank-you redirect; now observed separately | `scripts/ads/conversion_actions_2026_09.py` |
| 2026-09-26 00:47 | conversion_action "WhatsApp or email click" | (new) | does not exist → created: CONTACT, one per click, secondary, £1 | Taps on WhatsApp/email links were counted as full leads via a thank-you redirect; now observed separately | `scripts/ads/conversion_actions_2026_09.py` |
