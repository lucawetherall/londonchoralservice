# Music Guides: Clusters and the AI-Answer Pass (round 3)

> **For agentic workers:** load `writing-site-copy` and `stop-slop` before any copy, and `build-and-verify` before committing. Prices come from `pricing.html`; FAQ JSON-LD mirrors the visible FAQ text word for word; no `AggregateRating`/`Review` schema; no Markdown copies of pages. The London cathedral rule in CLAUDE.md applies to every guide that names a London cathedral or Westminster Abbey.

**Goal:** every guide in `music-guides/` answers its main question in one self-contained paragraph near the top, routes readers to the hiring page and to its cluster's lead guide, and does not compete with a sibling guide for the same search. Rounds 1 and 2 (PRs #309, #317) did this for ten guides; #324 changed titles and anchors only.

**Data:** Search Console, 24 Jul – 21 Oct 2026, pages under `/music-guides/` (read-only, `scripts/reports/weekly_review.py`'s session), plus URL Inspection for each guide.

## Clusters and lead guides

Each guide links to its lead guide once in the body (the lead itself links to the hiring page and the other leads).

| Cluster | Lead guide | Hiring page | Guides |
|---|---|---|---|
| Funeral hymns and music | `funeral-music-guide` | `funerals.html` | popular-funeral-hymns, abide-with-me, be-thou-my-vision-funeral-hymn, anima-christi-catholic-funeral, catholic-funeral-hymns, funeral-songs, crematorium-music, non-religious-funeral-music, celebration-of-life-music, memorial-service-planning |
| Wedding music | `wedding-ceremony-music` | `weddings.html` | choosing-wedding-hymns, be-thou-my-vision-wedding-hymn, jerusalem, ubi-caritas-wedding, anima-christi-catholic-wedding, humanist-wedding-music, wedding-choral-repertoire, lesser-known-wedding-choral-pieces, wedding-pop-songs-choir, popular-wedding-organ-music, wedding-organ-pop-songs, wedding-readings-and-music, wedding-music-ideas |
| Christmas and carol services | `christmas-carols-guide` | `christmas-carol-services.html` (services), `christmas.html` (carol singers at events) | nine-lessons-and-carols, a-cappella-christmas-songs, advent-carols-vs-christmas-carols, christmas-carol-lyrics-meanings, best-carols-for-four-voices, carols-by-candlelight, church-carol-service-choir-hire, corporate-carol-service, charity-carol-concert, carol-singers-law-firms, company-christmas-party-entertainment, hotel-christmas-entertainment, christmas-drinks-reception-music, christmas-gala-dinner-music, residents-christmas-carol-event, outdoor-carol-singing |
| Booking and cost | `hiring-a-choir` | the occasion's page | funerals: funeral-choir-guide, funeral-music-costs, best-funeral-singers-london, last-minute-funeral-singers · weddings: wedding-choir-guide, wedding-music-costs, best-wedding-choirs-london, wedding-organist-guide, destination-wedding-choir · Christmas: christmas-choir-hire, carol-singers-cost, how-many-carol-singers, best-christmas-carol-singers, booking-carol-singers-agency-vs-direct, when-to-book-christmas-entertainment |

## Guides that compete, and the decision

| Query or intent | Guides | Decision |
|---|---|---|
| Wedding organ music (same 14 pieces, same three sections) | popular-wedding-organ-music (351 impr), wedding-organ-repertoire (148) | **Merge** into popular-wedding-organ-music; its unique pieces (Satie, Bach's Toccata in F, the "hidden gems" section) and two FAQs move across; wedding-organ-repertoire becomes a redirect stub like `carol-singers.html`. |
| Planning a workplace carol service | corporate-carol-service (22), office-carol-service-planning (27) | **Merge** into corporate-carol-service (more inbound links, and the `for-*` and corporate pages already point to it); the step-by-step, sample running order and "how long" FAQ move across; office-carol-service-planning becomes a redirect stub. |
| "how to book a choir" | hiring-a-choir (163 @ 14), wedding-choir-guide (34 @ 46), church-carol-service-choir-hire (18 @ 78) | **Split** (set in #324): hiring-a-choir is the one target. The other two keep their occasion in the title and link to it. |
| "wedding hymns" | choosing-wedding-hymns (23 @ 42), be-thou-my-vision-wedding-hymn (14 @ 3) | **Split:** choosing-wedding-hymns becomes the "wedding hymns" answer (title, answer block, list); the Be Thou My Vision page links to it as "wedding hymns". |
| "funeral singers near me" | best-funeral-singers-london (11 @ 13), last-minute-funeral-singers (7 @ 10) | **Split:** choosing a provider vs short notice; both send the booking intent to `funerals.html`. |
| Hymns vs songs at a funeral | popular-funeral-hymns, funeral-songs | **Split** already stated in both: sung by the congregation vs listened to. |
| Choir vs organ pop songs | wedding-pop-songs-choir, wedding-organ-pop-songs | **Split** by instrument; each links to the other. |
| Well-known vs lesser-known choral pieces | wedding-choral-repertoire, lesser-known-wedding-choral-pieces | **Split:** the first answers "best choral pieces", the second links back for the standards. |
| Christmas choir timing | christmas-choir-hire, when-to-book-christmas-entertainment | **Split:** what to book (sizes, sets) vs when (dates fill from mid-September). |

## Indexing found on the way

URL Inspection, 24 Oct, all 60 guides: 58 are indexed. `popular-funeral-hymns` is "discovered, currently not indexed" (never crawled) and `wedding-ceremony-music` (the wedding lead) is "crawled, currently not indexed". The hub and the cluster links give both more internal links; an indexing request in Search Console is a manual step for Luca (MANUAL-ACTIONS §12).

## The pass, per guide

1. Under the lede, a bold question and a 40–70 word answer that stands alone (names the piece, composer, date or price it needs).
2. One short line linking the hiring page, with a price from `pricing.html` where it fits, and one in-body link to the cluster's lead guide.
3. Facts checked against a source; a `Sources:` line (`<p class="text-sm text-mid">Sources: …</p>`) for dates, attributions and figures.
4. One to three new FAQs where a real question is unanswered; FAQ JSON-LD mirrors the visible FAQ text.
5. Organist costs point only to hiring our organist at £250 (owner, 24 Oct): no church or parish organist fees, statutory church fees or fee scales.
6. Copy passes `writing-site-copy` and `stop-slop`; meta descriptions stay 141–161 characters.

## Batches (highest impressions first)

Skipped (done in #309/#317): nine-lessons-and-carols, be-thou-my-vision-wedding-hymn, funeral-music-guide, hiring-a-choir, abide-with-me, anima-christi-catholic-funeral, christmas-carols-guide, a-cappella-christmas-songs, be-thou-my-vision-funeral-hymn, popular-funeral-hymns.

1. choosing-wedding-hymns, popular-wedding-organ-music (+ merge), christmas-carol-lyrics-meanings, ubi-caritas-wedding, non-religious-funeral-music, wedding-music-costs, wedding-organ-pop-songs, catholic-funeral-hymns, wedding-pop-songs-choir, anima-christi-catholic-wedding
2. advent-carols-vs-christmas-carols, wedding-choral-repertoire, carols-by-candlelight, funeral-choir-guide, jerusalem, best-wedding-choirs-london, lesser-known-wedding-choral-pieces, how-many-carol-singers, wedding-choir-guide, funeral-music-costs
3. crematorium-music, best-funeral-singers-london, charity-carol-concert, best-carols-for-four-voices, humanist-wedding-music, christmas-choir-hire, funeral-songs, when-to-book-christmas-entertainment, wedding-readings-and-music, hotel-christmas-entertainment
4. church-carol-service-choir-hire, memorial-service-planning, company-christmas-party-entertainment, corporate-carol-service (+ merge), last-minute-funeral-singers, carol-singers-cost, booking-carol-singers-agency-vs-direct, destination-wedding-choir, celebration-of-life-music, outdoor-carol-singing
5. residents-christmas-carol-event, best-christmas-carol-singers, wedding-music-ideas, carol-singers-law-firms, christmas-gala-dinner-music, wedding-organist-guide, christmas-drinks-reception-music, wedding-ceremony-music; then the hub (`music-guides/index.html`) grouped by cluster

One PR per two batches (`copy(guides): …`): 1+2, 3+4, 5 + hub.

## Outcome (24 Oct 2026)

All 58 live guides have now had the pass: the 10 from #309/#317, batches 1–2 in #339, batches 3–4 in #349, and batch 5 with the hub in the PR that adds this section. Two guides became redirect stubs (wedding-organ-repertoire, office-carol-service-planning). In the same PR every guide `<title>` moved from "| LCS" to "| London Choral Service" (at most 60 characters, shorter fronts where needed; og/twitter titles keep the full front), following the rule from #332.

The hub groups the guides by the four clusters above, each section opening with its lead guide, with a fourth filter ("Booking & cost").

**For Luca (manual):**
- Search Console → URL Inspection → Request indexing for `music-guides/wedding-ceremony-music.html` (crawled, not indexed) and `music-guides/popular-funeral-hymns.html` (discovered, not crawled).
- Testimonials left untouched under R12 that no other page carries, in case any should go: "David R., Battersea" (celebration-of-life-music), "Eleanor M., Hampstead" (funeral-songs), "Margaret K., Islington" (catholic-funeral-hymns), "Sophie and Tom W., Greenwich" (wedding-ceremony-music).

**Not worth more work now:** the guides under ~20 impressions in 90 days (outdoor-carol-singing, residents-christmas-carol-event, carol-singers-law-firms, christmas-gala-dinner-music, christmas-drinks-reception-music, wedding-organist-guide, wedding-music-ideas, best-christmas-carol-singers, last-minute-funeral-singers, destination-wedding-choir, celebration-of-life-music) have had one pass; look again only if Search Console shows them picking up queries.
