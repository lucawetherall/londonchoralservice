# Listen pages: a Christmas page of its own, and a listen page you can browse

**Date:** 2026-10-23
**Status:** Approved for implementation. Owner, live in chat on 23 Oct 2026: "create a christmas specific 'Listen' page. redesign existing listen page so it works better, and so that people can find the new christmas listen page from it." Standing mandate (14 Oct 2026): make the calls and carry the work through. Every call below is ours unless quoted.

## Why

What the audit found (23 Oct 2026, origin/main 104201df):

- **listen.html is one long column.** Eleven full-width films (about 450px each on a desktop) run in a single list, then fourteen pieces with no recording. Abide With Me sits beside Blue Christmas. A funeral family scrolls past five Christmas songs; a Christmas buyer scrolls past five funeral pieces. GA4 (90 days to 22 Oct): 73 views, 18 scroll events, so about a quarter of visitors reach the end.
- **The visitors are mostly wedding and funeral buyers.** The page's referrers are Google (23), the home page, about, funerals and weddings (including wedding ad clicks). Christmas visitors arrive through christmas.html and about 25 Christmas guides, whose "Hear more recordings" links all point at listen.html and land them among funeral hymns.
- **The copy promises what the page lacks.** The meta description says "Samples from Ave Maria to Jerusalem"; neither is recorded. The lede counts "Eleven recordings". faq.html says the page has "instrumental pieces"; it has none.
- **There is one call to action**, a text link at the very bottom.

## Goals

1. **A new `christmas-listen.html`**: every Christmas film in one place, grouped as carols and Christmas songs, leading to the two Christmas landing pages (christmas.html for events, christmas-carol-services.html for churches). It becomes the target of every Christmas "Hear more recordings" link.
2. **listen.html becomes the wedding and funeral listening page**, organised so a visitor finds the right kind of piece fast: a hero film, hymns, pieces the choir or a soloist sings alone, and the repertoire without a film in a compact list.
3. **The Christmas page is easy to find from listen.html**: a chip in the hero, and a Christmas card with thumbnails straight after the hero.
4. Fewer, shorter films per screen: films sit in a grid of cards, two or three across on a desktop, one on a phone.

## Non-goals

- No new films, no new prices, no new testimonials. Figures come from pricing.html and christmas-pricing.html as they stand.
- No form on either listen page. Their calls to action go to the existing forms (contact.html; christmas.html#enquiry and christmas-carol-services.html#enquiry), so the enquiry pipeline sees no new `page` value.
- No nav or footer change. "Listen" in the nav still goes to listen.html, which now opens onto the Christmas card.
- No change to js/video.js. The cards use the existing click-to-play button.

## Anti-goals

- A non-Christmas piece on the Christmas page (owner, 19 Oct 2026, spec christmas-landing-pages).
- Carol of the Bells presented as a church carol service piece (owner, 19 Oct 2026).
- A VideoObject for a film the page does not embed. The Christmas VideoObjects move from listen.html to christmas-listen.html with the films.
- A count of films in visible copy ("Eleven recordings"): it goes stale the day a film is added.

## Shared component: the film grid

New in `css/components.css` (built into every page by `./build.sh`):

- `.film-grid`: a `ul`, `grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr))`. Inside `.wide` (60rem) three cards fit a row and two cards share it at full width; on a phone, one per row.
- `.film-card`: an `li` holding the existing `.video-embed > .video-thumb` button, an `h3` title, a `.film-card__meta` line (ensemble, then where it suits), a one- or two-sentence description and an optional `.film-card__link`.
- `.section-intro`: a paragraph inside `.wide` held to prose width.
- `.repertoire-list`: a `dl` of pieces without a film, two columns on a desktop.
- `.piece-list`: a plain two-column `ul` of titles.
- `.start-here__films`: a strip of three thumbnails inside the existing `.start-here` card, for the Christmas card on listen.html.

## Page 1: christmas-listen.html (new)

- **Head:** title "Hear Our Carol Singers: Christmas Recordings | LCS"; unique meta description (141–161 characters); canonical, hreflang, OG and Twitter tags; its own OG card (`node scripts/og/generate_og_images.mjs --wire`).
- **JSON-LD:** WebPage with an ItemList of the films; BreadcrumbList Home › Listen › Christmas; one VideoObject per film, with the dates and durations in `data/seo-fix-discovered-urls.yml`; the organisation stub.
- **Hero** (`.hero` grid): breadcrumb; h1 "Hear our carol singers" with a sub; lede; "Check your date" (to christmas.html#enquiry) and WhatsApp buttons; the price line "four carol singers from £1,150"; film It's the Most Wonderful Time of the Year (the owner's lead Christmas film).
- **Carols:** Once in Royal David's City (carol services), Ding Dong! Merrily on High (events and carol services), Carol of the Bells (parties and receptions only).
- **Christmas songs:** Winter Wonderland, Blue Christmas.
- **Proof:** James's quote, unchanged.
- **Book the singers you heard:** two cards, carol singers for events (christmas.html) and a choir for a church carol service (christmas-carol-services.html), then the Christmas prices link.
- **Carols and songs not yet filmed:** titles the Christmas guides already cover, in two lists, linking to those guides.
- **Further reading** and a link back to listen.html for weddings and funerals.
- Mobile bar "Enquire" goes to christmas.html#enquiry.

## Page 2: listen.html (redesign)

- **Head:** title "Hear Our Singers: Wedding & Funeral Recordings | LCS"; a new meta description that names only pieces with a film; JSON-LD loses the six Christmas VideoObjects and its ItemList lists the films on the page.
- **Hero:** h1 "Hear our singers" with the sub "Hymns, anthems and solos for weddings and funerals"; lede; chips Hymns · Sung by the choir or a soloist · More pieces · Christmas recordings →; film Ubi Caritas (asked for at weddings and funerals alike), with its description under the lede.
- **Christmas card:** `.start-here` with three Christmas thumbnails, linking to christmas-listen.html.
- **Hymns:** Abide With Me, Be Thou My Vision.
- **Sung by the choir or a soloist:** Anima Christi, He Shall Feed His Flock.
- **More pieces we are asked for:** the fourteen unrecorded pieces as two `.repertoire-list`s, hymns and solos/choir pieces, each one line, then links to the funeral hymns, funeral songs and wedding hymns guides.
- **Proof:** David's quote, unchanged.
- **Ask for a piece:** the existing bespoke-arrangement paragraph, "Tell us about your occasion" and WhatsApp buttons, the soloist and Small Choir starting prices (£250, £1,150) linking to pricing.html, the areas line.

## Wiring

- Every "Hear more recordings" link under a Christmas film (christmas.html, christmas-carol-services.html and the Christmas music guides) points to christmas-listen.html. Links under wedding and funeral films stay on listen.html.
- `llms.txt`: add christmas-listen.html; rewrite the listen.html line.
- `scripts/og/generate_og_images.mjs`: an entry for christmas-listen.html; regenerate both cards.
- faq.html: the "Can I hear your singers" answer (visible and FAQPage JSON-LD) drops "instrumental pieces" and names the Christmas page.
- `data/seo-fix-discovered-urls.yml`: the `page:` notes for the six Christmas films say christmas-listen.html.
- sitemap.xml, page dates and llms-full.txt are generated by `./build.sh`.

## Verification

- `./build.sh` exits 0 (JSON-LD, allowlist, internal links).
- `grep -rl 'christmas-listen.html' --include='*.html' .` lists listen.html, christmas.html, christmas-carol-services.html and the Christmas guides.
- No Christmas `data-video` id left on listen.html; no non-Christmas id on christmas-listen.html.
- Browser preview at 1280px and 375px: films play in their cards, the grid wraps, no horizontal scroll, the Christmas card links through.
- After merge: `python3 scripts/check_live_site.py` serves christmas-listen.html.
