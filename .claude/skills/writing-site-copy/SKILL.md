---
name: writing-site-copy
description: "REQUIRED before writing or editing any visible text on this site — headlines, body copy, meta descriptions, FAQ answers, image alt text, JSON-LD answer text. Also when the user says 'rewrite this section', 'add copy', 'tighten this', 'write the intro'. Distils the house anti-slop rules from SITE-STOP-SLOP-PLAN.md so new copy doesn't reintroduce the AI-writing patterns already scrubbed from the site."
metadata:
  version: 1.0.0
---

# Writing Site Copy

The site went through a deliberate "stop-slop" programme (see `SITE-STOP-SLOP-PLAN.md` at the repo root for the full audit with real before/after examples). New copy that reintroduces these patterns undoes that work. Apply this to every sentence you write or edit.

## Register

Concrete, first-person-plural ("we handle rehearsals"), UK English throughout (organise, programme, practising). Funeral copy is restrained and practical, never saccharine. Wedding copy is warm but specific. Name real things: real venues, real prices (from `pricing.html`), real repertoire. Claims must be checkable — no invented testimonials, venues, or statistics.

## The ten banned patterns

| # | Pattern | Bad (real, pre-fix) | Fix |
|---|---|---|---|
| 1 | Lazy extremes ("every detail/occasion") | "we handle every detail" | Name the things: "we handle sheet music, rehearsals, and venue liaison" |
| 2 | Narrator-from-a-distance | "Families often tell us that live singing brought…" | State the claim directly, or use a named testimonial |
| 3 | Vague declaratives | "warmth, beauty, and quiet professionalism" | Something the reader can picture: "arrive an hour early, know the building, know the repertoire" |
| 4 | Adverb crutches | "rely on completely" | Kill the adverb: "music you can rely on" |
| 5 | Binary contrasts ("not X, but Y") | "not just a prayer, but a vow" | State the stronger half: "they become a vow" |
| 6 | Inanimate subject doing human verbs | "The music becomes something you can rely on" | Name the person: "You can rely on the music" |
| 7 | Em-dash fragmentation for drama | "Rehearsals, repertoire, logistics — all taken care of" | Restructure: "We handle rehearsals, repertoire, and logistics" |
| 8 | "Here's what/how" openers | "Here's how to get started" | Cut to the point |
| 9 | Triadic rhythm as default | Three-item lists everywhere | Two items beat three; vary list lengths |
| 10 | Punchy one-liner closers | "There is a reason it endures." | Fine occasionally; slop when every paragraph ends on one. Vary paragraph endings |

Nuances (from the plan's "what to keep"): parenthetical em-dashes (`&thinsp;&mdash;&thinsp;`) are house typography and fine; three-item lists of *real* things are fine; standalone declarative section intros are fine; testimonial pull-quotes are supposed to be quotable.

## Per-paragraph quick checks

Adverbs? Kill them. Passive voice? Find the actor. Inanimate thing doing a human verb? Name the person. "Not X, it's Y"? State Y. Three consecutive sentences the same length? Break one. Paragraph ends on a mic-drop? Vary it. Vague abstraction? Name the specific thing.

## Meta descriptions

- **141–161 characters**, verified: `python3 -c "print(len('TEXT'))"`
- No rating claims ("Rated 5 stars") — see docs/ROADMAP.md item R1.
- Name the service and place; front-load the search intent.

## Related

- Full pattern audit + page-by-page fix list: `SITE-STOP-SLOP-PLAN.md`
- Multi-pass editing process for existing copy: the generic **copy-editing** skill
- Creating a page (head/meta/wiring): the **new-page** skill
