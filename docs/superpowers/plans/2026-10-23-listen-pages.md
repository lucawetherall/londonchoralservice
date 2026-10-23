# Plan: listen pages (2026-10-23)

Spec: `docs/superpowers/specs/2026-10-23-listen-pages-design.md`.

1. **Film grid CSS.** Add `.film-grid`, `.film-card`, `.section-intro`, `.repertoire-list`, `.piece-list` and `.start-here__films` to `css/components.css`.
2. **Pages.** Rewrite listen.html's head, JSON-LD and `<main>`. Create christmas-listen.html from the same head: its own title, description, canonical, OG card and JSON-LD; its mobile "Enquire" goes to christmas.html#enquiry. The six Christmas VideoObjects move with their films.
3. **Wiring.** Done in parallel by a subagent that did not run the build:
   - Christmas "Hear more recordings" links go to christmas-listen.html (christmas.html, christmas-carol-services.html, 24 guides).
   - faq.html answer, visible and in JSON-LD.
   - llms.txt: the Listen line is rewritten, and the new page sits with the Christmas pages in Main Pages.
   - OG script entries.
   - `page:` notes in `data/seo-fix-discovered-urls.yml`.
4. **OG cards.** Run `node scripts/og/generate_og_images.mjs --wire`. Commit only `assets/og/listen.png` and the new `assets/og/christmas-listen.png`. The run redraws every card; restore the rest.
5. **Build.** Run `./build.sh`. Expect the CSS block to change on every page; the Christmas guides also get the link and their build-set "Updated" date.
6. **Browser check.** At 1100px and 375px: grid columns, the Christmas card, no horizontal scroll, a film playing in its card, no console errors.
7. **Ship.** Open a PR, merge, then run `python3 scripts/check_live_site.py`.
