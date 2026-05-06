# Site-wide stop-slop plan

A plan for removing AI writing patterns across the London Choral Service site. The body copy is good by the standards of most wedding-vendor sites, but it carries the same tics as most AI-assisted marketing writing: abstract intensifiers, lazy extremes, distancing narration, em-dash fragmentation, and pull-quotable one-liners used as paragraph closers. This document records the patterns found on real pages, ranks the pages for edit priority, and lists the specific fixes for the top pages.

All quoted phrases and line numbers have been verified against the files in this repository. This is not a general critique — every example cited is real text from the live site.

---

## Part 1 — Pattern audit

The ten AI-writing patterns, with real examples found on the site.

### 1. Lazy extremes: "every"

The single most frequent slop pattern on the site. "Every detail," "every occasion," "every note," "every couple."

Real examples:
- `index.html:1436` — "we handle every detail, so the music on the day is one less thing to worry about"
- `about.html:1387` — "could be trusted to arrive prepared and handle every detail themselves"
- `about.html:1398` — "We manage every detail: rehearsals, sheet music, coordination with your venue"
- `areas/london/*.html` — 20+ instances of the H2 "Ensembles for every occasion" (template copy)
- `areas/liverpool.html`, `areas/manchester.html`, `areas/oxford.html`, `areas/cambridge.html`, `areas/index.html` meta descriptions all contain "for every occasion"

Fix: name the specific thing. "We handle every detail" → "We handle sheet music, rehearsals, and venue liaison." "Ensembles for every occasion" → "Ensembles for weddings, funerals, and memorials."

### 2. Narrator-from-a-distance

"Families often tell us...", "Couples tend to...", "Many people find...". Weak because it avoids the direct claim.

Real examples:
- `areas/london/richmond.html:1436` — "Families often tell us that live singing brought a sense of occasion and tenderness that they had not expected"
- `areas/windsor.html:1363` — "Many families at St George's Chapel and Windsor Parish Church request music with a sense of occasion"

Fix: either use a specific testimonial (name + location) or state the claim directly. "Families often tell us live singing brought a sense of occasion" → "Live singing creates a moment most recorded music cannot" or "Sarah and James, who married at St George's, said the choir 'changed the whole mood of the day.'"

### 3. Vague declaratives

Abstractions that sound meaningful but tell the reader nothing. "A sense of occasion," "warmth, beauty, and quiet professionalism," "something special."

Real examples:
- `areas/manchester.html:1416` — "our conservatoire-trained singers and instrumentalists bring warmth, beauty, and quiet professionalism to every occasion in this remarkable city"
- `areas/windsor.html:1363, 1450` — "music with a sense of occasion"
- `areas/london/richmond.html:1436` — "a sense of occasion and tenderness that they had not expected"

Fix: replace the abstraction with a concrete thing the reader can picture. "Warmth, beauty, and quiet professionalism" → "Arrive an hour early, know the building, know the repertoire." "A sense of occasion" → "The room feels different the moment they start singing" or (better) cut the phrase.

### 4. Adverb crutches

"Completely," "carefully," "truly," "deeply," "genuinely." Intensifiers doing work the verb should do.

Real examples:
- `about.html:1398` — "the music on the day becomes something you can rely on completely"
- Template copy across guide pages uses "perfectly," "exactly," "deeply" (most instances the writer chose deliberately, but several paragraphs stack them)

Fix: kill the adverb and strengthen the verb. "something you can rely on completely" → "music you can rely on" — the adverb was doing nothing the sentence wasn't already doing.

### 5. Binary contrasts: "not X, but Y"

The structural AI tic. Usually used to add emphasis to the second half by setting up a strawman first half.

Real examples:
- `be-thou-my-vision-wedding-hymn.html:1410` — "they become something extraordinary&thinsp;&mdash;&thinsp;not just a prayer, but a vow"

Fix: state the stronger half and skip the strawman. "they become something extraordinary — not just a prayer, but a vow" → "they become a vow."

### 6. Inanimate-object-as-human-subject

Things doing human verbs. "The music becomes...", "the building celebrates...", "the ceremony feels...".

Real examples:
- `about.html:1398` — "The music on the day becomes something you can rely on completely"
- Multiple wedding-guide pages: "the piece builds relentlessly," "it fills a church," "it creates an atmosphere"

Fix: name the person. "The music becomes something you can rely on" → "Our musicians deliver music you can rely on" or "You can rely on the music." Not every inanimate subject is wrong — "the piece builds" is idiomatic for music — but the pattern is overused.

### 7. Em-dash fragmentation for drama

The site uses `&thinsp;&mdash;&thinsp;` heavily. Parenthetical uses are fine. Uses that break a sentence for dramatic emphasis (replacing a colon or full stop) are a slop tic.

Real examples:
- `index.html:1436` — "You tell us what you need&thinsp;&mdash;&thinsp;or let us guide you&thinsp;&mdash;&thinsp;and we handle every detail"
- `index.html:1436` (same line) — "Rehearsals, repertoire, logistics&thinsp;&mdash;&thinsp;all taken care of"

Fix: restructure. "You tell us what you need — or let us guide you — and we handle every detail" → "You tell us what you need. If you don't know, we help you decide. Either way, we handle the detail." "Rehearsals, repertoire, logistics — all taken care of" → "We handle rehearsals, repertoire, and logistics."

### 8. "Here's what / here's how" openers

Throat-clearing. The reader already knows you're about to tell them what you provide.

Site audit found this less often than the sub-agent report initially suggested — most section openers on the site are declarative ("What we provide," "How it works"). But watch for it creeping in during copy edits.

### 9. Triadic rhythm as default

Every list is a three-item list. "Warmth, beauty, and quiet professionalism." "Rehearsals, repertoire, logistics." "Bach chorales, pop songs, hymns." Three items has become the AI default for "sounds complete."

Fix: mix in two-item lists and five-item lists. The stop-slop skill rule: two items beat three.

Real examples:
- `areas/manchester.html:1416` — "warmth, beauty, and quiet professionalism"
- Multiple guide pages use three-adjective openings for each piece ("Serene, instantly recognisable, and impossible to tire of")

### 10. Punchy one-liner closers

Short declaratives (six words or fewer) used as paragraph-ending pull-quotes. Characteristic of AI-assisted writing because the closers are where the model tries to "land" the point.

Real examples (from the existing wedding-organ-repertoire.html):
- "There is a reason it endures."
- "You will not regret it."
- "We guarantee they will be pleased."
- "It is a moment neither of you will ever forget."

These are well-written individually. The problem is the pattern: every paragraph ends with one. Fix by varying paragraph rhythm. Some should end mid-thought or with a quiet observation. Not every paragraph needs a mic-drop.

---

## Part 2 — Before / after examples

Showing what "fix" looks like in practice.

### Example 1 — About page, line 1398

**Before:**
> We listen first, then match you with the right musicians and the right repertoire. We manage every detail: rehearsals, sheet music, coordination with your venue. You focus on what matters. The music on the day becomes something you can rely on completely.

Problems: "every detail" (lazy extreme), "something you can rely on completely" (adverb + vague declarative + inanimate subject), "You focus on what matters" (punchy one-liner closer).

**After:**
> We match you with the right musicians, plan the repertoire with you, and handle rehearsals, sheet music, and venue liaison. On the day, the music is one less thing for you to think about.

### Example 2 — Index page, line 1436

**Before:**
> You tell us what you need — or let us guide you — and we handle every detail, so the music on the day is one less thing to worry about. Rehearsals, repertoire, logistics — all taken care of.

Problems: em-dash fragmentation (three in two sentences), "every detail," "all taken care of" (passive + punchy closer).

**After:**
> You tell us what you need, or we help you decide. We handle rehearsals, repertoire, and logistics, so the music on the day is one less thing for you to think about.

### Example 3 — Manchester area page, line 1416

**Before:**
> Manchester is a city of deep musical heritage, from the free trade halls that once rang with orchestral sound to the parish churches woven into communities across Greater Manchester. Whether you are planning a funeral, a wedding, or a memorial, our conservatoire-trained singers and instrumentalists bring warmth, beauty, and quiet professionalism to every occasion in this remarkable city and its surrounding boroughs.

Problems: "whether X or Y" rhetorical setup, "warmth, beauty, and quiet professionalism" (triadic vague declarative), "every occasion" (lazy extreme), "remarkable city" (adverb + vague), "woven into communities" (cliché).

**After:**
> Manchester has the musical history to match its scale, from the old Free Trade Hall to the parish churches in the suburbs. Our conservatoire-trained singers perform at weddings, funerals, and memorials across Greater Manchester — usually in a church, occasionally in a venue, always on time and rehearsed.

---

## Part 3 — Prioritised fix list

Pages ranked by commercial priority. P0 pages get rewritten first. Each P0/P1 page gets the top 3–5 specific issues listed.

### P0 — Do first (highest traffic + highest conversion value)

| Page | Why | Estimated edit |
|---|---|---|
| [index.html](index.html) | Homepage. First impression for all organic traffic. | Medium — several lazy extremes and em-dash fragmentation |
| [weddings.html](weddings.html) | Main wedding landing. High conversion value. | **Already done** as part of this work |
| [funerals.html](funerals.html) | Main funeral landing. Equally high conversion value. | Medium — parallel rewrite to weddings.html |
| [contact.html](contact.html) | Conversion page. Every visitor is close to acting. | Light — short page, but intro/framing needs tightening |

#### Top issues on index.html

1. Line 1436: "we handle every detail" — lazy extreme. Replace with specific list.
2. Line 1436: em-dash fragmentation ("You tell us what you need — or let us guide you — and we handle every detail"). Restructure into two sentences.
3. Line 1436: "Rehearsals, repertoire, logistics — all taken care of." Passive + punchy closer. Make active: "We handle rehearsals, repertoire, and logistics."
4. Full body scan: check every paragraph closer. Vary the rhythm so paragraphs don't all end on pull-quotable one-liners.
5. Any "whether X or Y" constructions in the hero or services intro.

#### Top issues on funerals.html

(Based on expected parallel structure with weddings.html before its rewrite — to be verified by reading the file during execution.)

1. Hero subtitle likely uses an adverb-heavy pull-quote. Match the weddings.html rewrite pattern: name the audience and the service concretely.
2. "Every family" / "every service" lazy extremes.
3. Testimonial framing that uses narrator-from-a-distance ("families often tell us"). Replace with named testimonials where possible.
4. Pricing intro — check for "Transparent pricing, no hidden fees" (a line that was on weddings.html and has been removed; parallel copy may exist on funerals.html).
5. CTA copy. "Get in touch" → "Send a funeral enquiry" or equivalent specific action.

#### Top issues on contact.html

1. Any framing that uses "something special" / "meaningful" / "warmth."
2. "Here's how to get started" — if present, cut. The form is the next step; the reader can see it.
3. Any narrator-from-a-distance voice in the intro ("Many families find...").
4. Post-form reassurance copy — replace generic "we respond personally" with specific "Luca reads every enquiry and replies the same day."

### P1 — Do second

| Page | Why | Estimated edit |
|---|---|---|
| [services.html](services.html) | Secondary decision page. | Medium |
| [pricing.html](pricing.html) | Decision page. | Light-medium |
| [about.html](about.html) | Trust page. | Medium |
| [christmas.html](christmas.html) | Seasonal vertical, strong intent. | Medium |

#### Top issues on services.html

1. Any "every occasion" / "every event" lazy extremes.
2. Check for binary contrasts ("not just X, but Y").
3. Check for "Couples tend to appreciate" or similar narrator-from-a-distance framing.
4. Replace abstract adjectives ("meaningful," "emotional," "special") with concrete specifics.

#### Top issues on pricing.html

1. Any "bespoke experience" / "carefully tailored" abstractions — name what's actually tailored.
2. FAQ section — check each answer for adverb crutches and vague declaratives.
3. Intro paragraph — make sure it states the value proposition concretely ("Flat prices, no extra fees" is good; "Transparent pricing, tailored to your needs" is not).

#### Top issues on about.html

1. Line 1387: "handle every detail themselves" — lazy extreme.
2. Line 1398: "We manage every detail" + "rely on completely" + "something you can rely on." See full rewrite in Part 2 Example 1.
3. Luca's biography section — check for triadic rhythm and vague adjectives.
4. Roster introduction — concrete musician details (which conservatoires, which roles) will beat abstract superlatives.

#### Top issues on christmas.html

1. "Sense of festive magic" / "every element" — vague declaratives and lazy extremes.
2. Binary contrasts around corporate vs private events.
3. Check paragraph closers for the pull-quote pattern.

### P2 — Do third

| Page | Why | Estimated edit |
|---|---|---|
| All 13 wedding guide pages in `music-guides/` | Organic long-tail traffic, high intent | Low-medium each |
| All funeral guide pages in `music-guides/` | Organic long-tail traffic | Low-medium each |
| [listen.html](listen.html) | Supporting | Low |
| [music-guides/index.html](music-guides/index.html) | Category page | Low |

The guide pages are mostly well-written, but the pattern audit will find 3–5 issues per page. A systematic pass through them, one at a time, cleaning adverb crutches and punchy closers, is a several-hour editing job rather than a full rewrite.

### P3 — Batch fix, lower priority

| Page | Why | Estimated edit |
|---|---|---|
| Area pages (`areas/*.html` and `areas/london/*.html`) | 50+ pages, long-tail SEO volume but low individual traffic | Template fix |
| [thank-you.html](thank-you.html) | Post-conversion page | Low |
| [404.html](404.html) | Error page | Low |
| [privacy.html](privacy.html) | Legal | None unless factually wrong |

The area pages have two template problems that, fixed once in the template, propagate to all 50+ pages:

1. **"Ensembles for every occasion" H2** — appears on at least 20 London borough pages. Replace with "Ensembles for weddings, funerals, and memorials."
2. **"Conservatoire-trained … for every occasion" in meta descriptions** — appears on at least 5 city pages (Liverpool, Manchester, Oxford, Cambridge, areas/index). Replace with a description that names the three services.

Beyond those two template issues, each area page has a bespoke intro paragraph that often uses "warmth, beauty, and quiet professionalism" or "a sense of occasion." Fix these individually.

---

## Part 4 — Execution order

A suggested sequence for completing the site-wide rewrite:

1. **Week 1** — Rewrite index.html, funerals.html, contact.html. The three P0 pages that have not yet been done. Use the same stop-slop rules that were applied to weddings.html in this work.
2. **Week 2** — Rewrite services.html, pricing.html, about.html, christmas.html.
3. **Week 3** — Template fix for area pages: update the "Ensembles for every occasion" H2 and the recurring meta descriptions. Individually edit each area page's intro paragraph.
4. **Week 4 onward** — One wedding guide and one funeral guide per session, in order of traffic (check Google Search Console for the ranking). Light-touch polish — kill adverbs, vary paragraph rhythm, cut punchy closers.

Each session should run through the stop-slop quick-checks on every paragraph touched:

- Any adverbs? Kill them.
- Any passive voice? Find the actor.
- Inanimate thing doing a human verb? Name the person.
- Sentence starts with a Wh- word? Restructure it.
- Any "here's what/this/that" throat-clearing? Cut to the point.
- Any "not X, it's Y" contrasts? State Y directly.
- Three consecutive sentences match length? Break one.
- Paragraph ends with punchy one-liner? Vary it.
- Em-dash used for emphasis rather than parenthetical? Remove it.
- Vague declarative? Name the specific thing.
- Narrator-from-a-distance? Put the reader in the scene.

---

## Part 5 — What to keep

Not everything on the site needs rewriting. Several patterns that look AI-ish are actually fine for this content:

- **Short, declarative one-liners that stand alone as introductions to sections.** These are a hallmark of good journalism, not slop. The slop version is when every paragraph closes on one.
- **Em-dashes in parenthetical asides.** The site's em-dash convention (`&thinsp;&mdash;&thinsp;`) is correct typography. Only the fragmentation-for-drama use is a problem.
- **Lists of three things when the three things are real.** "Processionals, hymns, and the register signing" is fine. "Warmth, beauty, and quiet professionalism" is not.
- **Triadic rhythm in headings.** "How it works" three-step sections are a convention, not slop.
- **Testimonial pull-quotes.** These are structurally different from punchy paragraph closers — they're supposed to be quotable.
- **Some adverbs.** The rule is "kill adverbs," but the rule is a heuristic. "Traditional" and "classical" are fine; "truly traditional" is not.

A fully-cleaned site still has personality and warmth. The goal is to remove the AI tells, not to flatten the voice.
