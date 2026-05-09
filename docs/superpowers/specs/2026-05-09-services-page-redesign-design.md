# services.html — Hub Redesign Design Doc

**Date:** 2026-05-09
**Author:** Luca Wetherall (with Claude)
**Status:** Approved for implementation
**Page:** [services.html](../../../services.html)

---

## Goal

Reframe `services.html` as a **hub page** that quickly routes visitors to the dedicated commercial pages (`weddings.html`, `funerals.html`, `corporate.html`, `christmas.html`) and a contact CTA for memorials. Improve visual hierarchy, cut duplication with dedicated pages, push internal-link weight to the conversion pillars (per the SEO audit finding that `services.html` has 102 inbound links while `weddings.html` only has 17), and give the page its own editorial identity rather than mimicking the video-hero treatment used on weddings/funerals/index.

The page currently runs ~2,097 lines with four prose-heavy occasion sections that duplicate content already on the dedicated pages. Target: ~500–600 words of body copy, sharper visual rhythm, faster scan.

## Non-goals

- New photography or imagery (none exists in `assets/`).
- New JSON-LD changes beyond the two minor audit fixes already noted (`name` on the Service node; add `MusicGroup` to entity types).
- Changes to the global nav, footer, or shared partials.
- Changes to other pages — out of scope, even though `weddings.html` / `funerals.html` reference unstyled classes (`.steps`, `.step-num`, `.price-cards`, `.guide-links`) that are not defined in any CSS. That's a separate task.
- A dedicated memorials landing page — out of scope; for now the memorial card CTA goes to `contact.html`.

## Page architecture

Top-to-bottom structure:

1. **Hero** — marquee pull-quote, then H1 + lede, then primary CTA + phone. No video, no image.
2. **Intro** — one short paragraph stating what the service is and how it works.
3. **Occasions** — five horizontal entries: Funerals · Weddings · Memorials & celebrations of life · Corporate events · Christmas. Each entry: H3 + 2–3 sentence positioning + arrow CTA to the dedicated page (or contact for memorials).
4. **Ensembles** — 6-card grid: Soloist · Quartet · Quintet · Sextet · Full Choir · Chorus. Followed by an instrumentalists paragraph and links to pricing + listen pages.
5. **Where we perform** — one paragraph + the existing area-page link line.
6. **FAQ** — 4 Q&As, with one swap (see §6).
7. **Final CTA** — lede-styled paragraph + button + phone number.

Sections cut from the current page: the long "What we provide" / "From first contact to the day" subsections under each occasion (duplicate of dedicated pages); the standalone "Instrumentalists" section (folded into Ensembles); the per-section pull-quotes (the hero quote replaces them).

## 1. Hero

### Markup structure (semantic order)

```
<section class="section">
  <div class="prose">
    <nav class="breadcrumb">…</nav>

    <figure class="pull-quote pull-quote--marquee">
      <blockquote><p>"The moment they started singing, the whole room just fell silent."</p></blockquote>
      <figcaption>— Margaret, Dulwich  ·  Funeral</figcaption>
    </figure>

    <hr class="rule">

    <h1>Music for funerals, weddings, and ceremonies</h1>
    <p class="lede">From the most solemn farewells to the most joyful celebrations, we provide live music that rises to the occasion.</p>

    <p><a href="contact.html" class="btn-link">Tell us about your occasion</a></p>
    <p class="text-sm text-mid">Or call us on <a href="tel:+447356042468">07356 042468</a> to talk through options.</p>

    <p class="hero-trust">
      <span class="hero-trust__stars" aria-hidden="true">★★★★★</span>
      <span>5 stars from every family we've worked with.</span>
    </p>
  </div>
</section>
```

### Quote choice

Margaret's "the whole room just fell silent" — strongest line on the site. The figcaption explicitly attributes it to a funeral; the H1 immediately afterwards spans all five occasions, so context is unambiguous.

### New CSS — `.pull-quote--marquee`

A modifier on the existing `.pull-quote` for hero-scale typography. Use existing tokens (matching the project's existing pattern of viewport-based token overrides at the `:root` level rather than `clamp()`):

- Desktop: `font-size: var(--text-3xl)` (≈3.05rem, drops to 2.2rem at <600px via existing root override; bumps to 2.6rem in 600–899px range)
- Slightly tighter line-height than the lede (`--leading-tight`); the giant left quote glyph from the base `.pull-quote::before` is either removed for the marquee variant or scaled up proportionally
- Width capped to ~30rem so the quote holds together as a single visual shape (`max-width: 30rem`)
- Top margin reset (no `--space-3xl` block margin from the base `.pull-quote`); this is the first content in the hero

H1 / lede / button-link / hero-trust styles all reuse existing rules. No new layout primitives needed.

## 2. Intro

A single short paragraph in `.prose`, between the hero and the occasion entries:

> *Tell us the date, the venue, and the kind of occasion. Luca Wetherall, our Artistic Director, sends back music suggestions, recordings, and a quote — usually the same day. We handle repertoire, rehearsals, and logistics. You hear the music on the day.*

Function: states what booking the service actually involves, in plain language, before the cards. Keeps the page from jumping straight from hero to grid.

## 3. Occasion entries

### Visual treatment

Vertical stack of 5 entries. Each separated by `border-top: 1px solid var(--color-rule)`, padded with `--space-xl` block padding. Reuses the existing `.guide-list` styling pattern.

Two-column layout on desktop (≥768px): title H3 left, copy + CTA right.

```
.occasion-list { list-style: none; padding-left: 0; }
.occasion-list li {
  display: grid;
  grid-template-columns: minmax(0, 14rem) 1fr;
  gap: var(--space-2xl);
  padding-block: var(--space-xl);
  border-top: 1px solid var(--color-rule);
}
.occasion-list li:last-child { border-bottom: 1px solid var(--color-rule); }
.occasion-list h3 { margin-bottom: 0; font-size: var(--text-xl); }
.occasion-list p  { color: var(--color-text-mid); margin-bottom: var(--space-md); }
.occasion-list .occasion-cta {
  font-family: var(--font-heading);
  font-weight: 500;
  font-size: var(--text-base);
  color: var(--color-accent);
}

@media (max-width: 767px) {
  .occasion-list li { grid-template-columns: 1fr; gap: var(--space-sm); }
}
```

### Order and content

Order: **Funerals → Weddings → Memorials & celebrations of life → Corporate events → Christmas**.

#### 1. Funerals

> Our singers lead congregational hymns with warmth and authority, and perform solo and choral pieces between them. We perform in churches, crematoriums, and chapels across the UK. Most families reach us two to five days before the service.

CTA: **Funeral music →** → `funerals.html`

#### 2. Weddings

> Singers and instrumentalists for the processional, hymns, the register signing, and the recessional. We can carry on through the drinks reception and the wedding breakfast if you want music running across the whole day. Bespoke arrangements at no extra charge.

CTA: **Wedding music →** → `weddings.html`

#### 3. Memorials & celebrations of life

> Reflective, sacred, uplifting, personal — or all four. We shape the music around the person being remembered, in churches, halls, gardens, marquees, or wherever you're gathering.

CTA: **Talk to us about a memorial →** → `contact.html`

#### 4. Corporate events & ceremonies

> Award ceremonies, gala dinners, commemorative services, product launches. We perform regularly for City livery companies, law firms, banks, charities, and schools across London and the UK.

CTA: **Corporate music →** → `corporate.html`

#### 5. Christmas

> Carol services, December receptions, and Christmas concerts. A full choir with organist for a traditional service, or a vocal quartet for a drinks reception — Luca will recommend the right size for your venue.

CTA: **Christmas music →** → `christmas.html`

## 4. Ensembles

### Visual treatment

H2 "Our ensembles" + a single-line shared note below the H2:

> *Every booking includes one to three performance pieces and leading the congregation through up to three hymns. The chorus does up to four of each.*

Then a 6-card grid using the existing `.guide-grid` / `.guide-card` styling. New variant `.ensemble-grid` if needed for 3-column desktop layout (the existing `.guide-grid` is 2-column).

```
.ensemble-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
  list-style: none;
  padding: 0;
  margin: var(--space-xl) 0 var(--space-2xl);
}
@media (max-width: 899px) { .ensemble-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 599px) { .ensemble-grid { grid-template-columns: 1fr; } }

.ensemble-card {
  padding: var(--space-xl);
  background-color: var(--color-bg-alt);
  border: 1px solid transparent;
  transition: border-color var(--transition-fast);
}
.ensemble-card:hover { border-color: var(--color-accent); }
.ensemble-card h3 {
  font-size: var(--text-lg);
  font-weight: 500;
  margin-bottom: var(--space-xs);
}
.ensemble-card .voices {
  display: block;
  font-family: var(--font-body);
  font-size: var(--text-sm);
  color: var(--color-text-mid);
  margin-bottom: var(--space-md);
}
.ensemble-card p { color: var(--color-text-mid); margin-bottom: 0; }
```

### Card content

Names standardised to match `pricing.html` / `weddings.html`:

1. **Soloist** — *one voice* — A single, exceptional voice for intimate settings and moments that call for purity.
2. **Quartet** — *4 singers* — Four-part harmony that fills a room with warmth and depth without overwhelming the space. Mid-sized venues, 50–200 people.
3. **Quintet** — *5 singers* — A second soprano makes a real difference to the sound and opens up the repertoire. Helps lead the congregation more confidently.
4. **Sextet** — *6 singers* — Six voices give you the warmth of a choir at a price closer to a quartet. Carries beautifully in larger churches.
5. **Full Choir** — *8 singers* — A richer, more resonant sound for larger venues and occasions that need greater presence. Powerful without dominating.
6. **Chorus** — *12 singers* — The full choral experience: a powerful ensemble that can fill a cathedral and create moments people never forget.

(Naming change: rename "Small Choir" to "Quartet" to match the rest of the site.)

### Below the grid

One paragraph for instrumentalists:

> Pianists, organists, harpists, and string quartets perform alongside our singers or on their own. We tailor the instrumentation to your venue, your repertoire, and the character of the occasion.

Plus a link line: *View pricing →* (`pricing.html`) ` | ` *Listen to our musicians →* (`listen.html`).

## 5. Where we perform

Single paragraph naming the regions and venue types with the existing area-page links. Kept light — the full city list already lives in the footer.

> We are based in London and perform across the United Kingdom. Our singers travel to venues in [London](areas/london.html), [Oxford](areas/oxford.html), [Cambridge](areas/cambridge.html), [Birmingham](areas/birmingham.html), [Manchester](areas/manchester.html), [Brighton](areas/brighton.html), [Bath](areas/bath.html), [Winchester](areas/winchester.html), and beyond. [See all the areas we serve](areas/).

> Parish churches, cathedrals, crematoriums, chapels, synagogues, hotels, private homes, gardens, marquees, concert halls, and outdoor spaces. If your venue has specific acoustic or logistical needs, Luca will advise on the right ensemble size and setup.

## 6. FAQ

Four Q&As. Swap Q3 (funeral-specific "Do you perform at crematoriums?" — misplaced on a hub). Keep Q1, Q2, Q4 from the current page.

1. **What types of occasions do you provide music for?** — kept as-is.
2. **What ensemble sizes are available?** — kept as-is.
3. **How quickly can you respond?** — *new* — "Most enquiries get a reply from Luca the same day, often within a few hours. We've arranged singers at a few hours' notice when families had no other option. If your service is in the next 48 hours, call us on 07356 042468 — email may not be fast enough."
4. **Can you arrange any piece of music?** — kept as-is.

JSON-LD `FAQPage` schema needs the same swap.

## 7. Final CTA

```
<section class="section">
  <div class="prose">
    <p class="lede">Tell us about your occasion and we'll recommend the right musicians, repertoire, and ensemble for your venue.</p>
    <p><a href="contact.html" class="btn-link">Tell us about your occasion</a></p>
    <p class="text-sm text-mid">Or call us on <a href="tel:+447356042468">07356 042468</a> to talk through options.</p>
  </div>
</section>
```

Kept as-is from the current page.

## CSS / build strategy

`services.html` ships with a single inlined `<style>` block that's regenerated by `build.sh` from `css/*.css`. To make changes propagate cleanly:

1. Add new component rules (`.pull-quote--marquee`, `.occasion-list`, `.ensemble-grid`, `.ensemble-card`) to `css/components.css`.
2. Re-run `build.sh` to inline the updated CSS into all pages, including `services.html`.
3. Edit the body markup of `services.html` directly (the body isn't built — only the `<style>` block is).

Existing classes reused without change:
- `.section`, `.prose`, `.page-wrap` (containers)
- `.btn-link`, `.text-sm`, `.text-mid` (utilities)
- `.lede`, `.rule`, `.breadcrumb` (typographic)
- `.pull-quote` + new `--marquee` modifier (hero quote)
- `.hero-trust`, `.hero-trust__stars` (trust chip)
- `.mobile-cta` (sticky bottom bar — unchanged)

No JavaScript changes needed. No new files. No new images.

## JSON-LD fixes (in-scope)

Two audit-flagged fixes addressed while we're in the file:

1. **Service node missing `name`** — add `"name": "Live music for funerals, weddings, and ceremonies"` to the `Service` object in the JSON-LD block.
2. **Add `MusicGroup` to entity types** — change `"@type": "LocalBusiness"` on the primary entity to `"@type": ["LocalBusiness", "PerformingGroup", "MusicGroup"]`, mirroring the homepage convention.

Update FAQPage schema to reflect the swapped Q3.

## Accessibility

- Hero quote is wrapped in `<figure><blockquote>…<figcaption>` (already the convention on the site).
- Occasion entries use semantic `<ol>` / `<li>` (an ordered hub list) or `<ul>` — pick `<ul>` since order is presentation, not meaning.
- Ensemble grid uses semantic `<ul>` / `<li>`.
- All CTAs are real `<a>` tags with descriptive labels (no "click here").
- Card hover state is supplemented by focus-visible state for keyboard users.
- Heading hierarchy: H1 (page) → H2 (each section) → H3 (occasions, ensembles, FAQ).

## Out-of-scope follow-ups (flag for separate tasks)

- Sister pages (`weddings.html`, `funerals.html`) reference `.steps`, `.step-num`, `.price-cards`, `.price-card`, `.guide-links` in markup, but those classes have no CSS rules anywhere. Effectively unstyled. Should be either styled or replaced with existing patterns.
- Building a dedicated `memorials.html` landing page would let the Memorials card link to a real page rather than `contact.html`.
- The "Small Choir" → "Quartet" naming change should propagate to anywhere else on the site using the old name.

## Success criteria

- Body copy reduced from ~1,300 → ~500–600 words.
- Page passes the existing site lint / build (`build.sh` runs cleanly, no broken inline CSS).
- Lighthouse / Core Web Vitals at parity or better with current page (no new images, no new JS).
- Visual smoke test: page renders correctly at 320px, 768px, 1280px viewport widths.
- All five occasion CTAs route to the correct destinations.
- No regressions in JSON-LD (validated with `validate_jsonld.py`).
- Audit findings addressed: `Service.name` present, `MusicGroup` in entity types, FAQ Q3 reflected in schema.
