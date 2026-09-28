# GA4 change log

Every change applied to GA4 property 527915578, newest first.

| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |
|---|---|---|---|---|---|
| 2026-09-28 11:32 | Data filter "Internal Traffic" | state | testing → active | Excludes the owner's own devices (tagged with ?lcs_internal=1) from GA4 | GA4 UI, by the owner |
| 2026-09-28 11:32 | Data collection | Google signals | off → on (reporting identity Blended) | Owner's choice: demographics and cross-device data. Privacy policy updated the same day; the Monday report flags GA4 data thresholds | GA4 UI, by the owner |
| 2026-09-28 01:10 | Search Console link | product link | none → sc-domain:londonchoralservice.com associated with web stream londonchoralservice.com | Organic queries and landing pages in GA4 reports | Search Console UI via Claude in Chrome, owner approved |
| 2026-09-28 00:54 | reportingDataAnnotation "Lead tracking rebuilt" | annotation | none → 2026-09-26 note | Explain the 26 Sep break in the charts | `scripts/ga4/annotations_2026_09.py` |
| 2026-09-28 00:54 | reportingDataAnnotation "Ads: choir-only, Christmas campaign live" | annotation | none → 2026-09-26 note | Explain the 26 Sep break in the charts | `scripts/ga4/annotations_2026_09.py` |
| 2026-09-27 15:39 | eventCreateRule contact_click[whatsapp] → contact_message | rule | none → contact_click with method=whatsapp also recorded as contact_message | WhatsApp and email are the owner's preferred contact routes (primary in Google Ads) | `scripts/ga4/contact_message_key_event_2026_09.py` |
| 2026-09-27 15:39 | eventCreateRule contact_click[email] → contact_message | rule | none → contact_click with method=email also recorded as contact_message | WhatsApp and email are the owner's preferred contact routes (primary in Google Ads) | `scripts/ga4/contact_message_key_event_2026_09.py` |
| 2026-09-27 15:39 | keyEvent contact_message | key event | not a key event → key event, once per session | GA4 key events now match the Google Ads primary goals | `scripts/ga4/contact_message_key_event_2026_09.py` |
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
