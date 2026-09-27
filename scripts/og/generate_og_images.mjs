#!/usr/bin/env node
// Generates the per-page social share cards (1200 x 630 PNG) in assets/og/
// and, with --wire, points each page's og:image / twitter:image at its card.
//
// Two designs, matching the existing hand-made cards:
//   lcs      - the framed parchment card of assets/og-weddings.png, for area,
//              borough, B2B and hub pages of The London Choral Service.
//   register - the left-aligned Alma Consort card of assets/og-private-events.png,
//              for the destinations/ pages of the private register.
//
// Card text comes from each page's own <h1> (and .h1-sub), or from the MANUAL
// table below, so a card never says anything the page does not.
//
// Run from the repo root (needs Node and Playwright with Chromium):
//   npm i -g playwright && npx playwright install chromium   (once)
//   node scripts/og/generate_og_images.mjs            # render cards
//   node scripts/og/generate_og_images.mjs --wire     # render and rewire pages
// Then run ./build.sh. The output PNGs are committed like every other artefact.
// Destination pages are also rewired by scripts/build_register_page.py, which
// picks up assets/og/destinations-<slug>.png when it exists.

import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = await import('playwright')); }

const ROOT = process.cwd();
const SITE = 'https://londonchoralservice.com';
const OUT = 'assets/og';
const WIRE = process.argv.includes('--wire');

const decode = s => s
  .replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]+>/g, '')
  .replace(/&amp;/g, '&').replace(/&rsquo;/g, '’').replace(/&lsquo;/g, '‘')
  .replace(/&mdash;/g, '—').replace(/&ndash;/g, '–').replace(/&eacute;/g, 'é')
  .replace(/&egrave;/g, 'è').replace(/&uacute;/g, 'ú').replace(/&nbsp;/g, ' ')
  .replace(/&thinsp;/g, '').replace(/\s+/g, ' ').trim();
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
const SMALL = new Set(['and', 'or', 'of', 'the', 'in', 'a', 'an', 'to', 'for', 'at', 'on', 'with', '&']);
const titleCase = s => s.split(' ').map((w, i) => (i && SMALL.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1))).join(' ');
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
const slug = f => f.replace(/\.html$/, '').replace(/\/index$/, '-index').replace(/\//g, '-');

function h1Parts(html) {
  const m = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/);
  if (!m) return [null, null];
  const sub = m[1].match(/<span class="h1-sub">([\s\S]*?)<\/span>/);
  const main = m[1].replace(/<span class="h1-sub">[\s\S]*?<\/span>/, '');
  return [decode(main), sub ? decode(sub[1]) : null];
}
const titleOf = html => decode((html.match(/<title>([^<]*)/) || [, ''])[1]).replace(/\s*\|\s*(LCS|Alma Consort)$/, '');

// Hand-written card text for pages whose h1 is not a good card on its own.
const MANUAL = {
  'index.html': ['Singers & Choirs', 'For funerals, weddings and Christmas, across the UK'],
  'about.html': ['About Our Musicians', 'Hand-picked professional singers and instrumentalists'],
  'luca-wetherall.html': ['Luca Wetherall', 'Artistic Director, The London Choral Service'],
  'contact.html': ['Contact Us', 'Send us the date and the venue'],
  'faq.html': ['Questions & Answers', 'Booking, repertoire, travel and prices'],
  'listen.html': ['Hear Our Singers', 'Hymns, anthems and carols, recorded by our musicians'],
  'accessibility.html': ['Accessibility', 'How this website works for every visitor'],
  'privacy.html': ['Privacy Policy', 'What we collect, and why'],
  'terms.html': ['Terms of Booking', 'The terms that govern every booking'],
  'compare/london-funeral-singers.html': ['Funeral Singers in London', 'Two providers compared, with sourced prices'],
  'music-guides/index.html': ['Music Guides', 'For weddings, funerals and Christmas'],
  'areas/index.html': ['Areas We Serve', 'Singers and choirs across the United Kingdom'],
};

function cards() {
  const out = [];
  for (const [f, [title, sub]] of Object.entries(MANUAL)) out.push({ f, style: 'lcs', title, sub });
  for (const f of fs.readdirSync('.').filter(n => /^for-.*\.html$/.test(n)).sort()) {
    const [main, sub] = h1Parts(read(f));
    out.push({ f, style: 'lcs', title: titleCase(main), sub });
  }
  const areas = ['areas/london.html',
    ...fs.readdirSync('areas').filter(n => n.endsWith('.html') && n !== 'index.html' && n !== 'london.html').map(n => 'areas/' + n),
    ...fs.readdirSync('areas/london').filter(n => n.endsWith('.html')).map(n => 'areas/london/' + n)].sort();
  for (const f of areas) {
    const [main] = h1Parts(read(f));
    const place = main.split(' in ').slice(1).join(' in ');
    out.push({ f, style: 'lcs', title: 'Funeral & Wedding Choirs', title2: 'in ' + place,
      sub: 'Live singers for churches, crematoria and carol services' });
  }
  for (const n of fs.readdirSync('destinations').filter(n => n.endsWith('.html')).sort()) {
    const f = 'destinations/' + n, html = read(f);
    const [main] = h1Parts(html);
    const country = n === 'index.html' ? 'Destination weddings'
      : (titleOf(html).match(/Choir in (?:the )?(.+?) —/) || [, ''])[1];
    out.push({ f, style: 'register', kicker: n === 'index.html' ? 'ALMA CONSORT · LONDON'
      : 'ALMA CONSORT · ' + (country || 'ABROAD').toUpperCase(), title: main, sub: titleOf(html) });
  }
  return out.map(c => ({ ...c, image: `${OUT}/${slug(c.f)}.png` }));
}

// Fonts are inlined as data URIs: a page built with setContent() cannot load file:// fonts.
const font = f => `url(data:font/woff2;base64,${fs.readFileSync(path.join(ROOT, 'fonts', f)).toString('base64')}) format('woff2')`;
const fontCss = `
@font-face{font-family:'CG';font-weight:300 600;src:${font('cormorant-garamond.woff2')}}
@font-face{font-family:'CG';font-style:italic;font-weight:400;src:${font('cormorant-garamond-italic.woff2')}}
@font-face{font-family:'SS';font-weight:400 600;src:${font('source-serif-4.woff2')}}
*{margin:0;padding:0;box-sizing:border-box}
h1,.sub{text-wrap:balance}
html,body{width:1200px;height:630px;overflow:hidden}`;

function lcsHtml(c) {
  return `<!doctype html><meta charset="utf-8"><style>${fontCss}
body{background:#F7F3EE;color:#2C2420;font-family:'CG',serif}
.frame{position:absolute;inset:38px;border:2px solid #8B3A3A}
.frame::after{content:'';position:absolute;inset:9px;border:1px solid #E3D6D0}
.inner{position:absolute;inset:48px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 90px}
.kicker{font-family:'SS';font-size:22px;letter-spacing:.36em;color:#8B3A3A;text-indent:.36em}
.rule{width:88px;height:2px;background:#8B3A3A;margin:26px 0 22px}
h1{font-weight:500;font-size:var(--fs,84px);line-height:1.08;letter-spacing:-.005em}
.sub{font-style:italic;font-size:36px;color:#6B5E56;margin-top:26px;line-height:1.25}
.url{position:absolute;bottom:34px;left:0;right:0;font-family:'SS';font-size:18px;letter-spacing:.32em;color:#6B5E56;text-indent:.32em}
</style><div class="frame"></div><div class="inner">
<div class="kicker">THE LONDON CHORAL SERVICE</div><div class="rule"></div>
<h1 id="t">${esc(c.title)}${c.title2 ? '<br>' + esc(c.title2) : ''}</h1>
${c.sub ? `<div class="sub">${esc(c.sub)}</div>` : ''}
<div class="url">LONDONCHORALSERVICE.COM</div></div>`;
}

function registerHtml(c) {
  return `<!doctype html><meta charset="utf-8"><style>${fontCss}
body{background:#FAF6EF;color:#2A1A10;font-family:'CG',serif;border-top:6px solid #2A1A10}
.wrap{position:absolute;left:96px;right:110px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center}
.kicker{font-family:'SS';font-weight:600;font-size:18px;letter-spacing:.2em;color:#7A1E1E}
h1{font-weight:400;font-size:var(--fs,72px);line-height:1.1;margin-top:26px}
.rule{width:88px;height:1px;background:#A99A8C;margin:36px 0 30px}
.sub{font-family:'SS';font-size:25px;color:#5C4E44;line-height:1.45}
.foot{position:absolute;left:96px;bottom:44px;font-family:'SS';font-size:15px;letter-spacing:.14em;color:#6B5E56}
</style><div class="wrap"><div class="kicker">${esc(c.kicker)}</div>
<h1 id="t">${esc(c.title)}</h1><div class="rule"></div><div class="sub">${esc(c.sub)}</div></div>
<div class="foot">THE LONDON CHORAL SERVICE</div>`;
}

// Shrink the heading until the whole card fits inside 630px.
async function fit(page, max, min) {
  for (let size = max; size >= min; size -= 2) {
    await page.evaluate(v => document.documentElement.style.setProperty('--fs', v + 'px'), size);
    const ok = await page.evaluate(() => {
      const box = (document.querySelector('.inner') || document.querySelector('.wrap'));
      const t = document.getElementById('t');
      const lines = Math.round(t.getBoundingClientRect().height / parseFloat(getComputedStyle(t).lineHeight));
      return box.scrollHeight <= box.clientHeight && lines <= 3;
    });
    if (ok) return size;
  }
  return min;
}

function wire(c) {
  const html = read(c.f);
  const url = `${SITE}/${c.image}`;
  const alt = c.style === 'register'
    ? `Alma Consort, London: ${c.title}`
    : `The London Choral Service: ${[c.title, c.title2].filter(Boolean).join(' ')}${c.sub ? '. ' + c.sub : ''}`;
  const a = esc(alt).replace(/—/g, '&mdash;').replace(/’/g, '&rsquo;');
  let out = html
    .replace(/(<meta property="og:image" content=")[^"]*(">)/, `$1${url}$2`)
    .replace(/(<meta name="twitter:image" content=")[^"]*(">)/, `$1${url}$2`)
    .replace(/(<meta property="og:image:alt" content=")[^"]*(">)/, `$1${a}$2`)
    .replace(/(<meta name="twitter:image:alt" content=")[^"]*(">)/, `$1${a}$2`);
  if (out !== html) fs.writeFileSync(path.join(ROOT, c.f), out);
  return out !== html;
}

const list = cards();
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
let wired = 0;
for (const c of list) {
  await page.setContent(c.style === 'register' ? registerHtml(c) : lcsHtml(c), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await fit(page, c.style === 'register' ? 72 : 84, 40);
  await page.screenshot({ path: c.image, type: 'png' });
  if (WIRE && wire(c)) wired++;
}
await browser.close();
console.log(`Rendered ${list.length} cards into ${OUT}/` + (WIRE ? `; rewired ${wired} pages` : ''));
