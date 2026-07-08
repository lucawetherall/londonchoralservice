# JSON-LD by page type

Every page carries one `<script type="application/ld+json">` block containing an `@graph` array. `python3 validate_jsonld.py` (run by `./build.sh`) checks it parses — but parsing is not correctness: the blocks below define what each page type must contain.

## Hard rules

1. **Never add `AggregateRating`, `Review`, or any star-rating markup.** Self-serving review schema on your own organisation violates Google's structured-data policy and risks manual action. This applies even if asked to "add our reviews to the schema" — surface the policy instead.
2. **Never invent values.** Unresolved facts (Google Business Profile canonical URL, LinkedIn URL, video upload dates/durations) live in `data/seo-fix-discovered-urls.yml`. If a value is still a TODO there, leave a matching TODO comment, don't fabricate.
3. The organisation is referenced by `@id`: `https://londonchoralservice.com/#organization`. Reuse that `@id`; don't redefine the full LocalBusiness on subpages — a stub `{"@type": "LocalBusiness", "@id": "...", "name": "The London Choral Service"}` is the site pattern.
4. FAQ answers in `FAQPage` must match visible on-page FAQ content (Google requires parity). Prices in answers come from `pricing.html`.

## Graph composition per page type (from real pages)

| Page type | Exemplar | `@graph` contents |
|---|---|---|
| City/area page | `areas/manchester.html` | `Service`, `LocalBusiness` (stub), `BreadcrumbList`, `FAQPage` |
| London borough page | `areas/london/camden.html` | `Service`, `LocalBusiness` (stub), `BreadcrumbList`, `FAQPage` |
| Music guide | `music-guides/wedding-pop-songs-choir.html` | `Article`, `LocalBusiness` (stub), `BreadcrumbList`, `FAQPage` |
| Service page | `weddings.html` | `Service`, `BreadcrumbList` |
| B2B landing page | `for-event-managers.html` | `ProfessionalService`, `BreadcrumbList`, `FAQPage`, `LocalBusiness` (stub) |
| Hub/index page | `music-guides/index.html` | `CollectionPage`, `LocalBusiness` (stub), `BreadcrumbList` |

## Skeleton: area/borough page `Service` node

Copied from `areas/london/camden.html` — replace the CAPITALISED values:

```json
{
  "@type": "Service",
  "name": "Funeral Singers & Wedding Choirs in PLACE",
  "url": "https://londonchoralservice.com/PATH.html",
  "description": "MATCHES-THE-META-DESCRIPTION-INTENT",
  "provider": { "@type": "LocalBusiness", "@id": "https://londonchoralservice.com/#organization" },
  "areaServed": {
    "@type": "AdministrativeArea",
    "name": "FULL-OFFICIAL-AREA-NAME",
    "containedInPlace": { "@type": "City", "name": "PARENT-CITY", "addressCountry": "GB" }
  },
  "serviceType": ["Funeral Music", "Wedding Music", "Memorial Music", "Ceremony Music"],
  "geo": { "@type": "GeoCoordinates", "latitude": REAL-LAT, "longitude": REAL-LNG }
}
```

Use real coordinates for the place (look them up; don't reuse the exemplar's).

## BreadcrumbList

Positions mirror the real click path; the final item has `name` but no `item` URL. Borough pages have 4 levels (Home → Areas We Serve → London → Borough); city pages 3; guides 3 (Home → Music Guides → Article title).

## Checks

- `./build.sh` (or `python3 validate_jsonld.py`) passes.
- No `AggregateRating`/`Review` introduced: `grep -n 'AggregateRating\|"Review"' <newfile>` → empty.
- All URLs in the block are absolute and match the page's canonical.
