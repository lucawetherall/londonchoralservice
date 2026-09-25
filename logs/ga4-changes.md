# GA4 change log

Every change applied to GA4 property 527915578, newest first.

| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |
|---|---|---|---|---|---|
| 2026-09-26 00:58 | property | timeZone | Etc/GMT → Europe/London | Match Google Ads; days were an hour off during BST | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | dataRetentionSettings | eventDataRetention | TWO_MONTHS → FOURTEEN_MONTHS | Year-on-year and seasonal analysis; data was deleted after 8 weeks | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | keyEvent generate_lead | key event | not a key event → key event, once per session | The one real lead event fired by js/form.js and js/private-events.js | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | keyEvent ads_conversion_Contact_1 | key event | key event → not a key event (event and history kept) | Duplicate lead count, fired twice per thank-you view | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | eventCreateRule 14333333685 | rule | page_view on /thank-you.html → ads_conversion_Contact_1 → removed (config only, no data) | Source of the double count; the site now records leads itself | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | customDimension occasion | event-scoped dimension | not registered → registered as "Occasion" | Occasion chosen on the enquiry form (generate_lead) | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | customDimension lead_source | event-scoped dimension | not registered → registered as "Lead source page" | Page path the enquiry was sent from (generate_lead, form_error) | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | customDimension method | event-scoped dimension | not registered → registered as "Contact method" | call, email or whatsapp (contact_click) | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | customDimension link_location | event-scoped dimension | not registered → registered as "Contact link location" | header, footer, mobile_bar or body (contact_click) | `scripts/ga4/setup_tracking_2026_09.py` |
| 2026-09-26 00:58 | customDimension error_type | event-scoped dimension | not registered → registered as "Form error type" | captcha, incomplete, timing, network or submit (form_error) | `scripts/ga4/setup_tracking_2026_09.py` |
