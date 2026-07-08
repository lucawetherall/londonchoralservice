# Internal linking for new pages

Nav and footer links come free via `partials/nav.html` and `partials/footer.html` — do not duplicate them in the body. Body cross-links do NOT come free; a new page must be linked from its hub or it is orphaned (crawlers find it only via the sitemap, users never).

## Who must link to the new page

| New page type | Must be linked from |
|---|---|
| City/area page | `areas/index.html` (the areas hub list) |
| London borough page | `areas/index.html` London section (borough list) |
| Music guide | `music-guides/index.html` card grid, in the matching category (wedding / funeral / Christmas) |
| Service page | `services.html` hub, plus the nav Services dropdown (`partials/nav.html` — partial edit, so rebuild) and footer services list (`partials/footer.html`) if it's a primary service |
| B2B landing page | Usually not in nav (they're ad/referral targets); link from the most related service page |

## Links the new page must carry in its body

- At least one CTA to `contact.html` (area pages pass `?occasion=` where relevant — the contact form pre-fills from it).
- A pricing reference linking to `pricing.html` where prices are mentioned.
- Area pages: link sideways to 2–3 neighbouring area pages ("Nearby areas") — follow the exemplar's pattern.
- Music guides: link to the relevant service page (wedding guides → `weddings.html`, funeral guides → `funerals.html`, Christmas → `christmas.html`) and 2–3 related guides.

## Check

After wiring, confirm the page is reachable: `grep -rl 'NEW-PAGE-FILENAME' --include='*.html' . | grep -v NEW-PAGE-FILENAME` should list at least one hub page.
