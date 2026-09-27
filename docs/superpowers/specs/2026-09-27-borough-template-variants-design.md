# Borough template variants (R13) — design doc

**Date:** 2026-09-27
**Status:** Implemented 2026-09-27 (`scripts/r13_borough_variants.py`, plan in `data/r13-borough-plan.json`)
**Related:** [docs/ROADMAP.md](../../ROADMAP.md) R12, R13; [2026-09-04 whole-site audit and growth plan](../plans/2026-09-04-whole-site-audit-and-growth-plan.md) P13.3, P3, G2; machine-readable plan `data/r13-borough-plan.json`

---

## Owner decisions (2026-09-27)

- **Testimonials:** keep every quote where it is (R12 stays open). Figures only move within their own page; the `--omit-mismatched-quotes` option was not built.
- **Variant B H1:** approved. The nine wedding-led pages read "Wedding and funeral choirs in X" in the H1, title, og:title, twitter:title and share card.
- **Richmond:** the Chapel Royal at Hampton Court Palace takes weddings with us only with the chapel clergy's permission. The page says so, and no heading names Hampton Court.
- **Lewisham:** Hither Green Crematorium and Lewisham Crematorium are one venue (Verdant Lane). The page now says so.
- **Westminster:** the claim that several of our singers hold posts in the Abbey's choral foundation is confirmed.

## Problem

The prose on the 33 `areas/london/*.html` pages is local; the container is identical. Measured on current `main`, borough name masked:

| Signal | Finding |
|---|---|
| H2 sequence | 28 pages: *Funeral music in X / Wedding choirs in X / Ensembles for weddings, funerals, and memorials / Christmas carol singers in X / Frequently asked questions*. The other 5 (Camden, Kensington & Chelsea, Lambeth, Southwark, Westminster) add 2–3 H2s around the same spine. |
| H1 | "Funeral and wedding choirs in X" on all 33. |
| FAQ | 5 questions everywhere, same topic order (price, wedding, music, crematorium, Christmas) on 28; the other 5 swap a named venue into slot 2 or 4. (The audit's "3 questions" is out of date.) |
| Body sections | Mean pairwise 5-gram Jaccard: funeral 0.016, wedding 0.019, ensembles 0.020, Christmas 0.009. **Local, keep.** |
| Boilerplate | "For more guidance, explore our…" tail paragraph identical on 28 pages (Jaccard 1.0). CTA line 0.97. Christmas FAQ 0.137 (SequenceMatcher 0.66; "dates usually start to fill by mid-September" on all 33). Price FAQ 0.108 (0.64). Standalone "For practical guidance on music at crematorium services…" paragraph verbatim on 14 pages. |
| Testimonials | 4 quotes fill 28 pages (Tony, Surrey 8; Margaret, Dulwich 8; Pamela, Hampshire 7; Helen, Buckinghamshire 6). |
| G2 residue | "half-remember" (Haringey funeral block) and "half-know" (Croydon wedding block) remain. |

## Current markup (what the script edits)

`<main>` holds three `<section class="section"><div class="prose">` wrappers:

1. **Hero:** breadcrumb, `<h1>`, `guide-meta`, `lede`, `<hr class="rule">`. Not moved.
2. **Body:** every H2 block, the `<figure class="pull-quote">`, the FAQ (`<h3>` + `<p>` pairs), the tail paragraphs and the `btn-link` CTA, all in **one** `div.prose`. No per-section wrappers and no HTML comments delimit blocks. A block runs from its `<h2>` to the next `<h2>`, `<figure>` or FAQ tail.
3. **Nearby:** one `<p class="text-sm text-mid">Nearby boroughs…`. Not moved.

No `@include` markers fall inside `<main>`; the inlined `<style>` is in `<head>`. JSON-LD is one `@graph` in `<head>` (Service, LocalBusiness, BreadcrumbList, FAQPage). FAQPage mirrors the visible FAQ in order: tags stripped, entities decoded to plain text (straight apostrophes, plain spaces, literal £), link-only trailing sentences removed (Camden: "Our crematorium music guide has more detail."). All 33 blocks round-trip byte-identically through `json.loads` → `json.dumps(indent=2, ensure_ascii=False)` with a 2-space prefix.

## Section keys

`funeral`, `wedding`, `ensembles` (both "Ensembles for…" and "Ensemble sizes and pricing"), `christmas`, `memorial`, `neighbours`, `logistics` (Westminster, K&C), `crematoria` (Lambeth only), `quote` (the figure), `faq` (H2 + all Q/A pairs), `guides` (the "For more guidance, explore our…" paragraph), `cta` (the `btn-link` paragraph). Paragraph-level drop key: `crem_link` (the standalone crematorium-guide paragraph inside `funeral`). Hero and nearby are fixed and never listed.

## Variants

Each variant follows from what the borough's own page already says; nothing is shuffled at random.

| Variant | Rule for assignment (evidence from the page) | Order | Pages |
|---|---|---|---|
| **A: Crematorium first** | Funeral block opens on a crematorium or cemetery the page calls "principal", "busiest" or sings at "regularly", with specifics (slot length, chapel size). | funeral → ensembles → quote → **faq** → guides → wedding → christmas → cta. The FAQ sits straight after the sizes because funeral enquirers arrive with price and slot questions. Weddings and Christmas close the page. | 11 |
| **B: Wedding church first** | The wedding block names a venue with a concrete draw (Pitzhanger Manor, Old Royal Naval College, Union Chapel, Blake at St Mary's Battersea, Wanstead) or the page calls the borough a wedding destination. | wedding → ensembles → quote → funeral → christmas → faq → cta. `guides` is dropped (it lists four funeral guides), and so is `crem_link` where present. | 9 |
| **C: Landmark church first** | One or two buildings carry funerals, weddings and memorials (Croydon Minster, St Margaret's Barking, the Hawksmoor churches, Southwark Cathedral). | funeral (retitled after the church) → [memorial] → wedding → ensembles → quote → faq → guides → **christmas** → [neighbours] → cta. Christmas follows the FAQ as a seasonal coda, so year-round content stays together. | 10 |
| **D: Central ceremonial** | City of London, Westminster, Kensington & Chelsea: logistics, livery, hotels and clubs. | funeral → quote → logistics → [memorial/wedding] → **christmas** → ensembles → faq → cta. Christmas and corporate content moves above sizes. The City of London's thin generic `ensembles` block is dropped and livery Christmas sits second. | 3 |

**Quote placement:** the figure follows the block its words describe: Tony ("our wedding") after `wedding`; Margaret, David, Caroline, Susan and Richard (funerals) after `funeral`; Helen and Pamela name no occasion and keep the variant default. The figure moves; its text never changes.

Result, validated against the live files: 15 distinct section orders, no order used by more than 8 pages, no two pages with the same H2 sequence, and no H2 string on more than 5 pages ("Frequently asked questions", kept on 5 deliberately).

**Venue-first and P3.** No `/venues/` pages exist yet. A and C already name the venue in the lead H2; when a P3 page ships, link that first mention (P3.3). Not part of this change.

**Rejected:** leading the City of London with Christmas. Livery is the City's distinctive trade, but a December-first page misreads for eleven months, so it goes second.

## FAQ rules

- **Count 2–4** (17 pages have 3, 14 have 4, 2 have 2), and exactly one new question per page. `faq_keep` in the JSON gives the final order, with `"NEW"` marking the new question's slot.
- **Drop first:** the Christmas FAQ (its section already covers it, and it is the most templated answer). Drop "What types of music…" unless the answer names local venues. On B pages drop the wedding question when the new FAQ covers the same church. Drop the crematorium answer where it only says "crematoriums in neighbouring boroughs… we sing at all of them" (Barking, Brent). That claim can't be checked.
- **Price** is kept on A, C and D pages. B pages drop the funeral-price question, and their new answer carries the relevant tier price instead.
- **New FAQ:** 1–3 sentences, built only from sentences already on that page (quoted in `source_quote`, each verified verbatim). Prices are "from £N" and match `pricing.html`: £250 soloist, £1,150 four, £1,400 five, £1,600 six, £2,000 eight, £3,000 twelve. Every answer has been checked for dashes, "not X but Y" and the adverb list in `writing-site-copy`.
- **FAQ heading** varies per page (for example "Questions about Waterloo and West Norwood" or "What Enfield families ask"). It stays "Frequently asked questions" on 5 pages.

## Boilerplate dropped or merged

| Block | Action | Pages |
|---|---|---|
| `guides` tail paragraph | Drop on B pages (9). Keep elsewhere: it is the only link to `popular-funeral-hymns` and `funeral-music-costs` on these pages. | ealing, greenwich, hackney, hammersmith-fulham, harrow, islington, redbridge, richmond, wandsworth |
| `crem_link` paragraph | Drop on B pages where present. Leaves 9 copies: the 8 variant-A pages that carry it, plus Kingston. | ealing, greenwich, redbridge, richmond, wandsworth |
| `ensembles` (≤60 words, generic "we can provide the right ensemble") | Drop | city-of-london, islington |
| Sentence repeats ("Our pricing page sets out the costs" ×18, "Browse our guide to choosing wedding hymns for inspiration" ×9, "You can learn more about our approach on our services page" ×8) and G2 residue | **Not scripted.** These are copy edits for a `writing-site-copy` pass after the structural change lands. | — |

## Testimonials (R12)

R12 is still `DECISION-NEEDED`. This spec does not remove, reattribute or rewrite any quote. It only repositions figures within their own page. The place matches the borough on **5 pages**: Camden (David, Hampstead), Kensington & Chelsea (Caroline, Chelsea), Lambeth (Susan, Streatham), Southwark (Margaret, Dulwich) and Westminster (Richard, Westminster). The other **28 do not match**:

- Tony, Surrey: barnet, city-of-london, greenwich, harrow, hounslow, merton, redbridge, tower-hamlets
- Margaret, Dulwich: croydon, ealing, hackney, islington, kingston, newham, wandsworth
- Pamela, Hampshire: bexley, enfield, havering, hillingdon, lewisham, sutton, waltham-forest
- Helen, Buckinghamshire: barking-dagenham, brent, bromley, hammersmith-fulham, haringey, richmond

P13.3's "testimonials only where geography matches" would remove 28 of 33 quotes. That is a fourth R12 option, and only the owner can choose it. The owner chose to keep every quote (2026-09-27), so the script does not remove any.

## Implementation

`scripts/r13_borough_variants.py`, kept in the repo for the record (it refuses to run twice: a restructured page no longer matches its plan). It reads `data/r13-borough-plan.json`.

1. Assert one `<main id="main">` with three `section.section` wrappers; work on the body `div.prose` inner HTML only.
2. Split at `\n\n        <h2` and the figure boundaries into keyed chunks; split the FAQ chunk into its H2, the Q/A pairs (keyed by question text normalised: unescape, nbsp→space, ’→') and the tail (`guides`, `cta`).
3. Assert chunk keys equal `section_order` ∪ `drop_blocks`; on mismatch fail and leave the file untouched.
4. Rewrite H2 text using the page's entity conventions: `&amp;`, `&rsquo;`, `St&nbsp;`, `&nbsp;` inside venue names that already carry it.
5. Remove `drop_blocks`. Reassemble the chunks in `section_order` with the existing blank-line and 8-space indentation.
6. Rebuild the FAQ from the kept pairs, copied byte-for-byte, plus the new pair as `<h3>…</h3>\n        <p>…</p>`.
7. JSON-LD: parse the `@graph`. Rebuild `FAQPage.mainEntity` in the same order, reusing the existing Question objects unchanged. The new one uses plain text (straight apostrophes, plain spaces). Re-serialise with `json.dumps(indent=2, ensure_ascii=False)` plus a 2-space prefix. Nothing else in the graph changes.
8. Assert the head (minus JSON-LD), the nav and footer include regions and the nearby section are byte-identical before and after.
9. H1 on B pages becomes "Wedding and funeral choirs in X" (owner-approved), with the title, og:title, twitter:title and share card to match.

**Dates and generated files.** `scripts/generate_sitemap.py` hashes the body after `</head>`, so JSON-LD alone would not move `lastmod`, but the visible edits will: all 33 `lastmod` values and `data/page-dates.json` entries move to the build date (a truthful signal of a material change), and `llms-full.txt` regenerates. `llms.txt` needs no edit. Refresh `graphify-out/` with `/graphify --update` in the same commit.

## Verification

```sh
python3 scripts/r13_borough_variants.py --check     # dry run: prints per-page diff summary, writes nothing
python3 scripts/r13_borough_variants.py
./build.sh                                           # must exit 0 (runs validate_jsonld.py and house claims)
python3 - <<'EOF'
import re, glob, json, html, collections
n = lambda s: ' '.join(html.unescape(re.sub('<[^>]+>', '', s)).replace('\xa0', ' ').replace('’', "'").split())
seqs = collections.Counter(); h2s = collections.Counter(); bad = []
for f in sorted(glob.glob('areas/london/*.html')):
    c = open(f, encoding='utf-8').read()
    main = re.search(r'<main id="main">(.*?)</main>', c, re.S).group(1)
    h2 = tuple(n(x) for x in re.findall(r'<h2[^>]*>(.*?)</h2>', main)); seqs[h2] += 1; h2s.update(h2)
    vis = [n(q) for q in re.findall(r'<h3>(.*?)</h3>', main)]
    g = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', c, re.S).group(1))['@graph']
    ld = [n(q['name']) for x in g if x['@type'] == 'FAQPage' for q in x['mainEntity']]
    if vis != ld or not 2 <= len(vis) <= 4: bad.append(f)
assert all(v == 1 for v in seqs.values()), 'two pages share an H2 sequence'
assert max(h2s.values()) <= 5, h2s.most_common(3)
assert not bad, bad
print('ok: 33 unique H2 sequences, FAQ parity, 2-4 FAQs each')
EOF
git diff --stat   # expect: 33 borough pages, sitemap.xml, data/page-dates.json, llms-full.txt, graphify-out/
```

Then preview five pages at 375 px, one per variant plus Lambeth, and check that the figure never sits directly after the FAQ H2.

## Risks and open items

- **Existing facts (resolved 2026-09-27).** Lewisham's two-crematoria wording is corrected (one venue); Richmond's Hampton Court claim is corrected (clergy permission); the Westminster Abbey claim is confirmed by the owner. The new FAQs on Southwark (supplementing the Cathedral choir) and Kensington & Chelsea (Royal Hospital Chelsea Chapel, by arrangement with the chaplain) repeat claims already on those pages; the owner should keep them in mind if either arrangement changes.
- **Internal links.** Dropping `guides` on B pages removes 9 links each to `popular-funeral-hymns` and `funeral-music-costs`. 19 pages still link to both.
- **Existing copy** still breaks house rules in places ("Absolutely", "privileged", "timed perfectly"). This spec is structural; queue a `writing-site-copy` sweep of `areas/london/` afterwards.
- **`llms.txt`** said "Holy Trinity Brompton" for Kensington & Chelsea; corrected to Holy Trinity Sloane Square.

## Per-borough assignment

FAQ codes: P = price, W = wedding, M = music types, C = crematorium, N = new (in final order). ✓ means the quote's place matches the borough.

| Borough | Var | Lead H2 | FAQs | Drops | Quote |
|---|---|---|---|---|---|
| Barking & Dagenham | C | Funerals at St Margaret's Barking and the borough's cemeteries | P N M | — | Helen, Bucks |
| Barnet | A | Funeral singers at Hendon and Golders Green crematoria | P C N | — | Tony, Surrey |
| Bexley | C | Funerals at St Mary the Virgin and Eltham Crematorium | N P C | — | Pamela, Hants |
| Brent | C | Funerals at St Mary's Willesden and Willesden New Cemetery | P N M | — | Helen, Bucks |
| Bromley | A | Funeral music at Beckenham Crematorium and Bromley's churches | P C N | — | Helen, Bucks |
| Camden | C | Funerals from St Pancras Old Church to Hampstead | P C(Golders Green) N W | — | David, Hampstead ✓ |
| City of London | D | Funerals at St Paul's, Temple Church and the City's parish churches | P N C | ensembles | Tony, Surrey |
| Croydon | C | Funerals at Croydon Minster and Croydon Crematorium | N P C M | — | Margaret, Dulwich |
| Ealing | B | Weddings at St Mary's Ealing and Pitzhanger Manor | N W C | guides, crem_link | Margaret, Dulwich |
| Enfield | A | Funerals at Enfield Crematorium and Edmonton Cemetery | P N C | — | Pamela, Hants |
| Greenwich | B | Weddings at St Alfege and the Old Royal Naval College | W N C | guides, crem_link | Tony, Surrey |
| Hackney | B | Weddings at St John at Hackney and in converted warehouses | W N M C | guides | Margaret, Dulwich |
| Hammersmith & Fulham | B | Weddings at St Paul's Hammersmith and Fulham Palace | N C | guides | Helen, Bucks |
| Haringey | C | Funerals at St Augustine's Highgate and Tottenham Cemetery | P M N C | — | Helen, Bucks |
| Harrow | B | Weddings at St Mary's Harrow-on-the-Hill | N C M | guides | Tony, Surrey |
| Havering | A | Funerals at South Essex Crematorium and St Andrew's Hornchurch | C P N M | — | Pamela, Hants |
| Hillingdon | A | Funerals at Breakspear Crematorium and St John's Hillingdon | N P C | — | Pamela, Hants |
| Hounslow | A | Funerals at South West Middlesex Crematorium and St Mary's Hounslow | P C M N | — | Tony, Surrey |
| Islington | B | Weddings at Union Chapel and St Mary's Upper Street | W N P C | ensembles, guides | Margaret, Dulwich |
| Kensington & Chelsea | D | Funerals at Brompton Oratory, Holy Trinity and St Mary Abbots | P M N C | — | Caroline, Chelsea ✓ |
| Kingston | C | Funerals at All Saints Kingston and Kingston Crematorium | P C N | — | Margaret, Dulwich |
| Lambeth | C | Funerals from St John's Waterloo to West Norwood | P C(West Norwood) N W | — | Susan, Streatham ✓ |
| Lewisham | A | Funerals at Hither Green and St Mary's Lewisham | P C N | — | Pamela, Hants |
| Merton | A | Funerals at South London Crematorium and Morden Cemetery | P N C | — | Tony, Surrey |
| Newham | A | Funerals at East London Crematorium and the City of London Cemetery | C P N | — | Margaret, Dulwich |
| Redbridge | B | Weddings at St Mary the Virgin, Wanstead | N C M | guides, crem_link | Tony, Surrey |
| Richmond | B | Weddings at St Mary Magdalene and in Kew | N C | guides, crem_link | Helen, Bucks |
| Southwark | C | Funerals at Southwark Cathedral and Honor Oak | P N C W | — | Margaret, Dulwich ✓ |
| Sutton | A | Funerals at North East Surrey Crematorium and All Saints Carshalton | P C N M | — | Pamela, Hants |
| Tower Hamlets | C | Funerals at St Dunstan's, Christ Church Spitalfields and St Anne's Limehouse | W N P C | — | Tony, Surrey |
| Waltham Forest | A | Funerals at Chingford Mount, Queens Road and St Mary's Walthamstow | N P M C | — | Pamela, Hants |
| Wandsworth | B | Weddings at St Mary's Battersea, where William Blake married | W N C | guides, crem_link | Margaret, Dulwich |
| Westminster | D | Funerals at the Abbey, St Margaret's and the Guards' Chapel | P N W C | — | Richard, Westminster ✓ |

Every heading rewrite, new question, answer and source sentence is in `data/r13-borough-plan.json`.
