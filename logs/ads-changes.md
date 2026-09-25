# Google Ads change log

Every change applied to the Google Ads account (customer 8733881378) is logged here, newest first. Nothing is logged until it has been validated (`validate_only=True`), shown as current value → new value with a reason, and explicitly approved.

| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |
|---|---|---|---|---|---|
| 2026-09-26 00:47 | conversion_action "Contact (1)" (7566867509) | primary_for_goal | primary (counts in Conversions, drives bidding) → secondary (reported only) | GA4 import of ads_conversion_Contact_1, which fired twice per thank-you view; the same enquiry again | `scripts/ads/conversion_actions_2026_09.py` |
| 2026-09-26 00:47 | conversion_action "Call click" | (new) | does not exist → created: PHONE_CALL_LEAD, one per click, secondary, £1 | Taps on the phone number were counted as full leads via a thank-you redirect; now observed separately | `scripts/ads/conversion_actions_2026_09.py` |
| 2026-09-26 00:47 | conversion_action "WhatsApp or email click" | (new) | does not exist → created: CONTACT, one per click, secondary, £1 | Taps on WhatsApp/email links were counted as full leads via a thank-you redirect; now observed separately | `scripts/ads/conversion_actions_2026_09.py` |
