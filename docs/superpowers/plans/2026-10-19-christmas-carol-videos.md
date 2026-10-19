# Three New Christmas Films Implementation Plan

> **For agentic workers:** Load `writing-site-copy` and `stop-slop` before writing any visible text, and `build-and-verify` before the build. Steps use checkbox (`- [ ]`) syntax. No new pages, no CSS changes: every embed reuses the existing `.video-embed` / `.video-thumb` / `.track` markup.

**Goal:** Put three new recordings from the channel (uploaded 19 Oct 2026) on the pages where a buyer is already reading about that carol, without moving the lead Christmas films.

**Base:** `origin/main` at `d0936db9` (synced 2026-10-19).

## The films (verified 2026-10-19 via oEmbed + watch page)

| Title on site | YouTube ID | Duration | uploadDate | Thumbnail | Ensemble (from thumbnail) |
|---|---|---|---|---|---|
| Ding Dong! Merrily on High | `zDlSFb74p4E` | 105 s → `PT1M45S` | `2026-10-19` | `maxresdefault.jpg` 200 | eight voices, no organ visible |
| Winter Wonderland | `UaVhyyidlTs` | 69 s → `PT1M9S` | `2026-10-19` | `maxresdefault.jpg` 200 (close-up of one singer) | presumed the same eight |
| Once in Royal David&rsquo;s City | `SbvqWglsbMo` | 113 s → `PT1M53S` | `2026-10-19` | `maxresdefault.jpg` 200 | eight voices, no organ visible |

All three: author `@londonchoralservice`, empty YouTube description. Same venue and singers as the Carol of the Bells film (`dGYqQf6BDAk`), so the label is **Full Choir**. Upload times are 14:02–14:06 PDT = 22:02–22:06 BST, so the UK date is 19 Oct.

## Placement rules

1. **Leads stay.** Carol of the Bells leads the carol articles and It&rsquo;s the Most Wonderful Time leads the party/booking articles (memory: music-guide video near the top). New films go **inline, directly under the heading or paragraph that discusses that piece**, not near the top.
2. **At most one new film per music guide**, so no article becomes a video wall (two exceptions below where the article has a dedicated section for each carol).
3. Each page that shows a new film also gets a `VideoObject` for it in its `@graph`, in the existing shape (name `"<Title> — Full Choir"`, description `"Live performance by The London Choral Service."`, maxres thumbnail, `contentUrl` watch URL, `embedUrl` youtube-nocookie, publisher `#organization`).
4. Embed markup is copied from `music-guides/christmas-carols-guide.html:2949-2955` (inline guide embed + one-line caption with link to `../listen.html`) or `christmas.html` `.track` articles (hub pages). `loading="lazy"`, `width="1280" height="720"`.

## Placement map

### Hub pages (track list)

| Page | Change |
|---|---|
| `listen.html` | Three new `.track` articles in the Christmas run, after Blue Christmas: Once in Royal David&rsquo;s City, Ding Dong, Winter Wonderland. Three `VideoObject`s. |
| `christmas.html` | Add all three to "Hear our musicians" (after Carol of the Bells: Royal David&rsquo;s, Ding Dong; after Blue Christmas: Winter Wonderland). Intro line "The first three recordings are from our Christmas sets" → "first six". Three `VideoObject`s. Hero unchanged. |
| `carol-singers.html` | Add Ding Dong and Winter Wonderland (roaming / street-carolling repertoire); Royal David&rsquo;s too if the track list there already reads as a programme. Update any "first N recordings" line. `VideoObject`s to match. Hero unchanged. |
| `christmas-pricing.html` | No change (hero only). |

### Music guides (inline, under the matching section)

| Guide | Film | Anchor |
|---|---|---|
| `christmas-carols-guide.html` | Royal David&rsquo;s **and** Ding Dong (each has its own h3) | after the h3 paragraphs at ~2970 and ~3001 |
| `christmas-carol-lyrics-meanings.html` | Royal David&rsquo;s **and** Ding Dong (each has its own h2) | end of the sections at ~3006 and ~3022 |
| `nine-lessons-and-carols.html` | Royal David&rsquo;s | after the order-of-service list item "Processional hymn" (~3036) |
| `best-carols-for-four-voices.html` | Ding Dong | under h3 at ~2975 |
| `outdoor-carol-singing.html` | Ding Dong | after the repertoire paragraph at ~3008 |
| `a-cappella-christmas-songs.html` | Winter Wonderland | under h3 at ~2989 |
| `christmas-drinks-reception-music.html` | Winter Wonderland | after the close-harmony paragraph at ~3007 |
| `company-christmas-party-entertainment.html` | Winter Wonderland | after the close-harmony paragraph at ~3003 |

Considered and left out (one mention in passing, or already carrying two films): `advent-carols-vs-christmas-carols`, `charity-carol-concert`, `carols-by-candlelight`, `corporate-carol-service`, `residents-christmas-carol-event`, `hotel-christmas-entertainment`, `best-christmas-carol-singers`, `christmas-choir-hire`, `office-carol-service-planning`.

## Tasks

- [ ] **1. Data.** Add three entries to `videos:` in `data/seo-fix-discovered-urls.yml` (id, title, upload_date, duration, pages, "verified via watch page uploadDate 2026-10-19"). Backfill the missing Carol of the Bells entry (`dGYqQf6BDAk`, `2026-09-29`, `PT1M21S`, as already used in the pages&rsquo; schema).
- [ ] **2. Copy.** Load `writing-site-copy` + `stop-slop`. Draft three track descriptions (one or two sentences each, the house shape: what the piece is, where we sing it) and the one-line guide captions ("Eight of our singers performing &hellip; <a>Hear more recordings</a>."). Re-check against stop-slop.
- [ ] **3. Hub pages.** Edit `listen.html`, `christmas.html`, `carol-singers.html` (tracks + `VideoObject`s + intro counts).
- [ ] **4. Guides.** Eight guides per the map: inline embed + caption + `VideoObject`. Hand-edit only the body and the JSON-LD; never the inlined `<style>` or `@include` blocks.
- [ ] **5. Build + verify.** `./build.sh` (expect only the edited pages plus `sitemap.xml` / `data/page-dates.json` / `llms-full.txt` lastmod moves). `python3 validate_jsonld.py`. `python3 scripts/stage_site.py`. Grep: each new ID appears in exactly the pages in the map; every page with a new `data-video` carries a matching `VideoObject`.
- [ ] **6. Preview.** `python3 -m http.server 8000`; on `christmas.html`, `listen.html` and one guide, click each new thumbnail at 375 px and 1280 px and check it swaps to the nocookie iframe and plays; no console errors.
- [ ] **7. Ship.** Commit `feat(video): add Ding Dong, Winter Wonderland and Royal David's films`, PR, merge, then `python3 scripts/check_live_site.py`. No graph refresh needed (no pages added or removed).

## Open questions for the owner

1. Are all three the eight-voice Full Choir (same session as Carol of the Bells)? The Winter Wonderland thumbnail shows one singer only.
2. Winter Wonderland&rsquo;s auto thumbnail is a close-up of one face. Keep it, or set a group-shot custom thumbnail in YouTube Studio first (the site picks it up automatically)?
3. Should Once in Royal David&rsquo;s City replace Carol of the Bells as the lead film on `nine-lessons-and-carols.html`, since it opens that service? The plan keeps Carol of the Bells and adds Royal David&rsquo;s inline.

## As built (2026-10-19)

Owner answers: all three are the eight-voice Full Choir; keep the Winter Wonderland thumbnail; keep Carol of the Bells as lead on `nine-lessons-and-carols.html`. Two additions arrived during the work:

- **Most Wonderful Time re-upload.** `MyDf9cMp0gk` → `csFWUu-r85Y` (same 110 s film, uploaded 19 Oct 2026, has `maxresdefault.jpg`) on all 16 pages, so those embeds now use the 1280×720 thumbnail and `uploadDate` 2026-10-19. `tests/test_design_markup.py` no longer needs the `sddefault` exception.
- **"Make the new films more prominent where they fit better."** Changes beyond the map above:
  - `christmas.html` (carol services): hero is now **Once in Royal David&rsquo;s City**; tracks run Royal David&rsquo;s, Carol of the Bells, Ding Dong, Most Wonderful Time, Winter Wonderland, Blue Christmas.
  - `carol-singers.html` (parties, lobbies, markets): hero is now **Ding Dong! Merrily on High**; tracks run Ding Dong, Most Wonderful Time, Winter Wonderland, Carol of the Bells, Blue Christmas. Royal David&rsquo;s left off (a church processional, not a lobby piece).
  - `christmas-pricing.html` keeps Most Wonderful Time as its hero.
  - `outdoor-carol-singing.html`: Ding Dong **replaces** Carol of the Bells as the lead film (the article names it first among outdoor repertoire), rather than being added inline.
  - `listen.html` lede: "Seven recordings" → "Eleven recordings" (the count was already stale at eight).
