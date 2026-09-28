# Search Console change log

Every change applied in Search Console (sc-domain:londonchoralservice.com), newest first.

| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |
|---|---|---|---|---|---|
| 2026-09-28 01:10 | Google Ads link | Google Ads 873-388-1378 | not linked → linked (https://londonchoralservice.com) | Paid and organic report in Google Ads | Google Ads UI via Claude in Chrome, owner approved |
| 2026-09-28 01:10 | Settings → Associations | Google Analytics | not associated → GA4 property 527915578 (web stream londonchoralservice.com) | Search Console queries and landing pages show inside GA4 | Search Console UI via Claude in Chrome, owner approved |
| 2026-09-28 01:05 | URL https://londonchoralservice.com/christmas-pricing.html | indexing | URL unknown to Google → indexing requested (priority crawl queue) | The Christmas ads' landing page was not known to Google search | Search Console UI via Claude in Chrome, owner approved (no API for this) |
| 2026-09-28 00:58 | sitemap https://londonchoralservice.com/sitemap.xml | submission | submitted 2026-02-28, last read 2026-04-12 → resubmitted | Google had stopped re-reading the sitemap; new and changed pages were not being discovered | `scripts/gsc/submit_sitemap.py` |
