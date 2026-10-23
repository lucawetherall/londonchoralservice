#!/usr/bin/env node
// Headless lead-tracking test: the built site in Chromium, with every Google, Web3Forms and hCaptcha
// endpoint stubbed, so nothing reaches Google and no email is ever sent.
//
// It stages the site exactly as the deploy does (scripts/stage_site.py --out <temp folder>) and answers
// every request for https://londonchoralservice.com/ from that folder, in-process. The pages must
// believe they are on the live host: partials/analytics.html only loads gtag.js there. Then:
//   - googletagmanager.com/gtag/js is a local stub that records every gtag() call (and runs
//     event_callback, as gtag.js does);
//   - api.web3forms.com/submit answers {"success": true} and records the posted enquiry;
//   - web3forms.com/client/script.js (which renders hCaptcha) is a stub that puts a solved captcha in
//     each form, so the forms' h-captcha-response check passes;
//   - every other request is refused.
//
// Checks
//   (a) After Accept on the cookie sheet, every enquiry form sends generate_lead (lead_source, occasion)
//       and the "Submit lead form" conversion. The 14 main-site forms go to thank-you.html, which sends
//       the lead (since #278); the private-register forms confirm inline and send it at once.
//   (b) After Reject, no cookie is set, nothing but the choice is stored, and consent stays denied.
//   (c) Without a choice, an ad landing (gclid + utm_campaign) gives "Ad visit: <page> (<campaign>)" in
//       the WhatsApp text, the email body and the form's ad_visit, and one click later on another page
//       through lcs_av; nothing is stored and the click ID never appears.
//   Also: "How did you hear about us?" is required, with its own message.
//
// Run: node tests/test_lead_tracking.mjs
// Needs Playwright (npm i -g playwright && npx playwright install chromium, as for
// scripts/og/generate_og_images.mjs). Without it the test prints "skip: ..." and exits 0.
// LCS_PLAYWRIGHT=<path to a playwright package folder> uses another copy; LCS_CHROMIUM=<browser
// executable> another browser. Synthetic data only.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const require = createRequire(import.meta.url);
const HOST = 'https://londonchoralservice.com';
const LEAD = 'AW-17988388404/RjhECKGP7akcELSMxIFD';
const CLICK = 'TESTCLICKID0123456789';
const AD_QUERY = `?gclid=${CLICK}&utm_source=google&utm_medium=cpc&utm_campaign=wedding-leads`;

function skip(msg) {
  console.log(`skip: ${msg}`);
  process.exit(0);
}

let chromium;
try {
  ({ chromium } = require(process.env.LCS_PLAYWRIGHT || 'playwright'));
} catch (e) {
  skip(process.env.LCS_PLAYWRIGHT
    ? `LCS_PLAYWRIGHT=${process.env.LCS_PLAYWRIGHT} could not be loaded (${String(e.message).split('\n')[0]})`
    : 'Playwright is not installed (no "playwright" package). Install it with `npm i -g playwright && ' +
      'npx playwright install chromium`, or set LCS_PLAYWRIGHT to a playwright package folder.');
}

// ---------------------------------------------------------------- stubs

const GTAG_STUB = `(function () {
  if (window.__lcsGtagStub) return;
  window.__lcsGtagStub = true;
  var dl = window.dataLayer = window.dataLayer || [];
  function handle(args) {
    var a = Array.prototype.slice.call(args);
    try { window.__lcsRecord(JSON.stringify(a, function (k, v) { return typeof v === 'function' ? '[function]' : v; })); } catch (e) {}
    if (a[0] === 'event' && a[2] && typeof a[2].event_callback === 'function') setTimeout(a[2].event_callback, 0);
  }
  for (var i = 0; i < dl.length; i++) handle(dl[i]);
  var push = dl.push;
  dl.push = function () {
    for (var j = 0; j < arguments.length; j++) handle(arguments[j]);
    return push.apply(dl, arguments);
  };
})();`;

const CAPTCHA_STUB = `(function () {
  window.hcaptcha = { reset: function () {}, getResponse: function () { return 'test-captcha-token'; } };
  function render() {
    document.querySelectorAll('.h-captcha').forEach(function (box) {
      if (box.querySelector('iframe')) return;
      var f = document.createElement('iframe');
      f.title = 'captcha (test stub)';
      f.setAttribute('srcdoc', '<p>solved</p>');
      box.appendChild(f);
      var t = document.createElement('textarea');
      t.name = 'h-captcha-response';
      t.value = 'test-captcha-token';
      t.hidden = true;
      box.appendChild(t);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render); else render();
})();`;

// The register forms refuse a send within 5 s of load (a bot check); move this page's clock on
// instead of waiting.
const CLOCK_SHIFT = `(function () {
  var real = Date.now.bind(Date), ahead = 0;
  Date.now = function () { return real() + ahead; };
  window.__lcsSkipAhead = function (ms) { ahead += ms; };
})();`;

const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'content-type, accept',
  'access-control-allow-methods': 'POST, OPTIONS' };
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.avif': 'image/avif', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.txt': 'text/plain', '.xml': 'application/xml',
  '.webmanifest': 'application/manifest+json', '.mp4': 'video/mp4', '.pdf': 'application/pdf' };

// ---------------------------------------------------------------- results

let failures = 0, passes = 0;
function check(ok, name, detail) {
  if (ok) { passes++; console.log(`PASS ${name}`); }
  else { failures++; console.log(`FAIL ${name}${detail === undefined ? '' : ': ' + JSON.stringify(detail).slice(0, 600)}`); }
  return ok;
}

// ---------------------------------------------------------------- site

const tmp = fs.mkdtempSync(path.join(process.env.LCS_TEST_TMP || os.tmpdir(), 'lcs-lead-test-'));
const SITE = path.join(tmp, 'site');
const staged = spawnSync('python3', ['scripts/stage_site.py', '--out', SITE], { cwd: ROOT, encoding: 'utf8' });
if (staged.status !== 0) {
  console.log(`FAIL staging the site: ${(staged.stdout + staged.stderr).trim().split('\n').slice(-3).join(' | ')}`);
  process.exit(1);
}

function localFile(pathname) {
  let p = decodeURIComponent(pathname);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.normalize(path.join(SITE, p));
  if (!f.startsWith(SITE + path.sep)) return null;
  for (const c of [f, f + '.html', path.join(f, 'index.html')]) {
    if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
  }
  return null;
}

function formPages() {
  const out = [];
  const walk = (dir) => {
    for (const name of fs.readdirSync(dir)) {
      const full = path.join(dir, name);
      if (fs.statSync(full).isDirectory()) walk(full);
      else if (name.endsWith('.html')) {
        const s = fs.readFileSync(full, 'utf8');
        const kind = s.includes('class="contact-form"') ? 'main' : s.includes('id="pe-enquiry"') ? 'register' : null;
        if (kind) out.push({ path: '/' + path.relative(SITE, full).split(path.sep).join('/'), kind });
      }
    }
  };
  walk(SITE);
  return out.sort((a, b) => a.path.localeCompare(b.path));
}

// ---------------------------------------------------------------- browser

async function launch() {
  const tries = [{}, { channel: 'chrome' }];
  if (process.env.LCS_CHROMIUM) tries.unshift({ executablePath: process.env.LCS_CHROMIUM });
  let last;
  for (const t of tries) {
    try {
      const b = await chromium.launch({ headless: true, ...t });
      console.log(`browser: ${t.channel || (t.executablePath ? 'LCS_CHROMIUM' : 'playwright chromium')} ${b.version()}`);
      return b;
    } catch (e) { last = e; }
  }
  skip(`no browser Playwright can start (${String(last && last.message).split('\n')[0]}). ` +
       'Run `npx playwright install chromium` once, or set LCS_CHROMIUM.');
}

async function newContext(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: 'block' });
  const state = { calls: [], posts: [], blocked: new Set(), errors: [] };
  await ctx.exposeBinding('__lcsRecord', (source, json) => {
    state.calls.push({ url: source.frame.url(), call: JSON.parse(json) });
  });
  await ctx.addInitScript(CLOCK_SHIFT);
  await ctx.route('**/*', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (url.origin === HOST) {
      const f = localFile(url.pathname);
      if (!f) return route.fulfill({ status: 404, contentType: TYPES['.html'], body: fs.readFileSync(path.join(SITE, '404.html')) });
      return route.fulfill({ status: 200, contentType: TYPES[path.extname(f)] || 'application/octet-stream', body: fs.readFileSync(f) });
    }
    if (url.host === 'www.googletagmanager.com' && url.pathname === '/gtag/js') {
      return route.fulfill({ status: 200, contentType: 'text/javascript', body: GTAG_STUB });
    }
    if (url.host === 'web3forms.com' && url.pathname === '/client/script.js') {
      return route.fulfill({ status: 200, contentType: 'text/javascript', body: CAPTCHA_STUB });
    }
    if (url.host === 'api.web3forms.com' && url.pathname === '/submit') {
      if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS });
      let body = {};
      try { body = JSON.parse(req.postData() || '{}'); } catch (e) { body = { unparsed: req.postData() }; }
      state.posts.push({ from: req.headers()['referer'] || '', body });
      return route.fulfill({ status: 200, headers: CORS, contentType: 'application/json', body: '{"success": true}' });
    }
    state.blocked.add(url.origin);
    return route.abort('blockedbyclient');
  });
  ctx.on('page', (p) => p.on('pageerror', (e) => state.errors.push(`${p.url()}: ${e.message}`)));
  return { ctx, state };
}

const events = (state, from, name) => state.calls.slice(from).map((c) => ({ url: c.url, a: c.call }))
  .filter((c) => c.a[0] === 'event' && c.a[1] === name);

async function choose(page, button) {
  const b = page.locator(`.consent [data-consent="${button}"]`);
  await b.waitFor({ state: 'visible', timeout: 5000 });
  await b.click();
}

async function fillRequired(page, form, hear) {
  const fields = await page.$$eval(`${form} [required]`, (els) => els.filter((e) => !e.disabled)
    .map((e) => ({ tag: e.tagName.toLowerCase(), type: e.type, name: e.name })));
  for (const f of fields) {
    const loc = page.locator(`${form} [name="${f.name}"]`).first();
    if (f.tag === 'select') {
      if (f.name === 'hear') {
        if (hear) await loc.selectOption({ label: hear });
      } else {
        const v = await loc.evaluate((s) => [...s.options].find((o) => o.value && !o.disabled).value);
        await loc.selectOption(v);
      }
    } else if (f.type === 'email') await loc.fill('test.enquiry@example.com');
    else if (f.type === 'date') await loc.fill('2027-06-12');
    else if (f.type === 'checkbox') await loc.check();
    else if (f.tag === 'textarea') await loc.fill('Synthetic test enquiry from tests/test_lead_tracking.mjs.');
    else await loc.fill(f.name === 'name' ? 'Test Person' : 'Test value');
  }
  return fields.map((f) => f.name);
}

async function submit(page, form) {
  const btn = page.locator(`${form} [type="submit"]`);
  await btn.evaluate((b) => b.scrollIntoView({ block: 'center' }));
  await btn.click();
}

// Read the WhatsApp text and email body the site writes into a contact link when it is tapped,
// without leaving the page.
async function messageTags(page) {
  return page.evaluate(() => {
    document.addEventListener('click', (e) => {
      const a = e.target.closest && e.target.closest('a[href^="mailto:"], a[href*="wa.me/"]');
      if (a) e.preventDefault();
    }, true);
    const wa = document.querySelector('a[href*="wa.me/"]');
    const mail = document.querySelector('a[href^="mailto:"]');
    if (wa) wa.click();
    if (mail) mail.click();
    const waText = wa ? new URL(wa.getAttribute('href')).searchParams.get('text') : null;
    const mailHref = mail ? mail.getAttribute('href') : '';
    const q = mailHref.indexOf('?') === -1 ? '' : mailHref.slice(mailHref.indexOf('?') + 1);
    const mailParts = {};
    q.split('&').forEach((kv) => { const i = kv.indexOf('='); if (i > 0) mailParts[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); });
    return { wa: waText, subject: mailParts.subject || '', body: mailParts.body || '' };
  });
}

async function storage(page, ctx) {
  const s = await page.evaluate(() => ({
    local: Object.keys(localStorage).map((k) => [k, localStorage.getItem(k)]),
    session: Object.keys(sessionStorage).map((k) => [k, sessionStorage.getItem(k)]),
    cookie: document.cookie,
  }));
  s.cookies = (await ctx.cookies()).map((c) => c.name);
  return s;
}

// ---------------------------------------------------------------- tests

async function testHearIsRequired(browser) {
  const { ctx, state } = await newContext(browser);
  const page = await ctx.newPage();
  let first = true;
  for (const [url, form] of [['/contact.html', 'form.contact-form'], ['/private-events.html', '#pe-enquiry']]) {
    await page.goto(HOST + url);
    if (first) { await choose(page, 'denied'); first = false; }
    await fillRequired(page, form, null);
    await page.evaluate(() => window.__lcsSkipAhead(10000));
    const before = state.posts.length;
    await submit(page, form);
    await page.waitForTimeout(300);
    const r = await page.evaluate(() => {
      const sel = document.querySelector('select[name="hear"]');
      const msg = document.getElementById('hear-error');
      return { invalid: sel.getAttribute('aria-invalid'), focused: document.activeElement === sel,
        shown: msg && getComputedStyle(msg).display !== 'none', text: msg && msg.textContent,
        describedby: sel.getAttribute('aria-describedby'),
        label: sel.labels && sel.labels[0] ? sel.labels[0].textContent.trim() : '' };
    });
    check(state.posts.length === before, `${url}: no answer to "How did you hear about us?" sends nothing`);
    check(r.invalid === 'true' && r.focused && r.shown && r.describedby === 'hear-error' &&
          r.text === 'Please choose how you heard about us.' && /^How did you hear about us\?/.test(r.label),
          `${url}: the field is marked, focused and named by its own message`, r);
    await page.locator(`${form} select[name="hear"]`).selectOption({ label: 'Prefer not to say' });
    const cleared = await page.evaluate(() => [document.querySelector('select[name="hear"]').getAttribute('aria-invalid'),
      getComputedStyle(document.getElementById('hear-error')).display]);
    check(cleared[0] === null && cleared[1] === 'none', `${url}: choosing an answer clears the message`, cleared);
  }
  await ctx.close();
}

async function testAcceptEveryForm(browser) {
  const { ctx, state } = await newContext(browser);
  const page = await ctx.newPage();
  const pages = formPages();
  check(pages.length >= 39 && pages.filter((p) => p.kind === 'main').length === 14,
        `(a) found the enquiry forms (${pages.length})`, pages.map((p) => p.path));
  let first = true;
  for (const { path: url, kind } of pages) {
    await page.goto(HOST + url);
    if (first) { await choose(page, 'granted'); first = false; }
    const form = kind === 'main' ? 'form.contact-form' : '#pe-enquiry';
    await page.waitForSelector(`${form} .h-captcha iframe`, { state: 'attached', timeout: 5000 });
    await fillRequired(page, form, 'A Google ad (marked Sponsored)');
    await page.evaluate(() => window.__lcsSkipAhead(10000));
    const from = state.calls.length, posted = state.posts.length;
    await submit(page, form);
    let landed = true;
    if (kind === 'main') {
      landed = await page.waitForURL(/\/thank-you\.html/, { timeout: 10000 }).then(() => true, () => false);
      check(landed, `(a) ${url}: goes to thank-you.html`, page.url());
      if (landed) await page.waitForSelector('h1', { timeout: 5000 });
    } else {
      landed = await page.locator('#pe-form-success').waitFor({ state: 'visible', timeout: 10000 }).then(() => true, () => false);
      check(landed, `(a) ${url}: shows its inline confirmation`);
    }
    // the lead's hits: from thank-you.html for a main-site form (#278), from the page itself on the register
    const sentFrom = kind === 'main' ? /\/thank-you\.html/ : new RegExp(url.replace(/[.]/g, '\\.') + '$');
    let gl = [], conv = [];
    for (let i = 0; i < 40 && !(gl.length && conv.length); i++) {
      await page.waitForTimeout(100);
      gl = events(state, from, 'generate_lead');
      conv = events(state, from, 'conversion').filter((c) => c.a[2] && c.a[2].send_to === LEAD);
    }
    const p = gl[0] && gl[0].a[2];
    check(gl.length === 1 && sentFrom.test(gl[0].url.split('?')[0]) && p.lead_source === url &&
          typeof p.occasion === 'string' && p.occasion.length > 0 && p.currency === 'GBP',
          `(a) ${url}: one generate_lead with lead_source and occasion`, gl);
    const c = conv[0] && conv[0].a[2];
    check(conv.length === 1 && sentFrom.test(conv[0].url.split('?')[0]) && /^lead-[a-z0-9]+$/.test(c.transaction_id) &&
          c.value === 1 && c.currency === 'GBP', `(a) ${url}: one "Submit lead form" conversion`, conv);
    const post = state.posts[posted];
    check(state.posts.length === posted + 1 && post.body.hear === 'A Google ad (marked Sponsored)' &&
          post.body['h-captcha-response'] === 'test-captcha-token' && post.body.access_key && !('botcheck' in post.body) &&
          !('ad_visit' in post.body), `(a) ${url}: Web3Forms gets the enquiry (faked)`, post && post.body);
    if (kind === 'main') {
      const s = await storage(page, ctx);
      check(!s.session.some(([k]) => k === 'lcs-lead'), `(a) ${url}: thank-you.html clears the handed-over lead`, s.session);
    }
  }
  check(state.errors.length === 0, '(a) no script errors on any form page', state.errors);
  await ctx.close();
}

async function testReject(browser) {
  const { ctx, state } = await newContext(browser);
  const page = await ctx.newPage();
  await page.goto(HOST + '/weddings.html' + AD_QUERY);
  await choose(page, 'denied');
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(500);
  await page.locator('main a[href*="pricing.html"]').first().click();
  await page.waitForURL(/\/pricing\.html/);
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(500);
  const s = await storage(page, ctx);
  check(s.cookies.length === 0 && s.cookie === '', '(b) Reject: no cookies', s);
  check(JSON.stringify(s.local) === JSON.stringify([['lcs-consent', 'denied']]) && s.session.length === 0,
        '(b) Reject: nothing stored but the choice itself', s);
  const consent = await page.evaluate(() => Array.prototype.slice.call(window.dataLayer)
    .map((a) => Array.prototype.slice.call(a)).filter((a) => a[0] === 'consent'));
  const granted = consent.some((a) => Object.values(a[2] || {}).includes('granted'));
  check(consent.length >= 1 && consent[0][1] === 'default' && consent[0][2].ad_storage === 'denied' &&
        consent[0][2].analytics_storage === 'denied' && !granted, '(b) Reject: consent stays denied on the next page', consent);
  const recorded = state.calls.filter((c) => c.call[0] === 'consent' && Object.values(c.call[2] || {}).includes('granted'));
  check(recorded.length === 0, '(b) Reject: no gtag consent update ever grants anything', recorded);
  await ctx.close();
}

async function testAdVisit(browser) {
  const tag = 'Ad visit: pricing (wedding-leads)';
  {
    const { ctx, state } = await newContext(browser);
    const page = await ctx.newPage();
    await page.goto(HOST + '/pricing.html' + AD_QUERY);
    await page.waitForLoadState('domcontentloaded');
    const links = await page.evaluate(() => [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')));
    const contact = links.filter((h) => /contact\.html/.test(h));
    check(contact.length > 0 && contact.every((h) => h.includes('lcs_av=pricing+%28wedding-leads%29')),
          '(c) landing: same-site links carry lcs_av', contact);
    check(links.filter((h) => /^(tel:|mailto:|#)|wa\.me\/|^https?:\/\/(?!londonchoralservice\.com)/.test(h))
            .every((h) => !h.includes('lcs_av')), '(c) landing: tel, mailto, WhatsApp, in-page and other sites untouched');
    let m = await messageTags(page);
    check(m.wa && m.wa.includes(tag + ')') && m.wa.includes('via a Google ad'), '(c) landing: WhatsApp text', m.wa);
    check(m.body.includes(tag) && m.subject.includes('via a Google ad'), '(c) landing: email body', m);
    check(!JSON.stringify(m).includes(CLICK) && !JSON.stringify(links).includes(CLICK), '(c) landing: the click ID never shows');

    await page.locator('main a[href*="contact.html"]').first().click();
    await page.waitForURL(/\/contact\.html\?(.*&)?lcs_av=/);
    check(true, '(c) one click later: contact.html opens with lcs_av');
    m = await messageTags(page);
    check(m.wa && m.wa.includes(tag + ')') && m.wa.includes('via a Google ad'), '(c) next page: WhatsApp text', m.wa);
    check(m.body.includes(tag), '(c) next page: email body', m.body);
    await fillRequired(page, 'form.contact-form', 'A Google ad (marked Sponsored)');
    const from = state.calls.length, posted = state.posts.length;
    await submit(page, 'form.contact-form');
    const landed = await page.waitForURL(/\/thank-you\.html/, { timeout: 10000 }).then(() => true, () => false);
    const post = state.posts[posted];
    check(post && post.body.ad_visit === 'pricing (wedding-leads)' && !('gclid' in post.body) &&
          !JSON.stringify(post.body).includes(CLICK), "(c) next page: the form's ad_visit", post && post.body);
    check(landed && events(state, from, 'generate_lead').length === 1, '(c) next page: the lead still goes (cookieless)');
    const s = await storage(page, ctx);
    check(s.cookies.length === 0 && s.local.length === 0 && s.session.length === 0, '(c) nothing stored on the device', s);
    await ctx.close();
  }
  {
    const { ctx, state } = await newContext(browser);
    const page = await ctx.newPage();
    await page.goto(HOST + '/weddings.html' + AD_QUERY);
    const m = await messageTags(page);
    check(m.wa && m.wa.includes('Ad visit: weddings (wedding-leads)'), '(c) form landing page: WhatsApp text', m.wa);
    await fillRequired(page, 'form.contact-form', 'A Google search result');
    const posted = state.posts.length;
    await submit(page, 'form.contact-form');
    await page.waitForURL(/\/thank-you\.html/, { timeout: 10000 }).catch(() => {});
    const post = state.posts[posted];
    check(post && post.body.ad_visit === 'weddings (wedding-leads)' && post.body.hear === 'A Google search result' &&
          !('gclid' in post.body), "(c) form landing page: the form's ad_visit", post && post.body);
    await ctx.close();
  }
  {
    // an address with lcs_av typed, bookmarked or shared (no referrer from our pages) is not an ad visit
    const { ctx } = await newContext(browser);
    const page = await ctx.newPage();
    await page.goto(HOST + '/contact.html?lcs_av=pricing+%28wedding-leads%29');
    const m = await messageTags(page);
    check(m.wa && !m.wa.includes('Ad visit') && !m.body.includes('Ad visit'), '(c) a shared lcs_av address carries no tag', m);
    await ctx.close();
  }
  {
    // Accept on the landing page: the links drop the label as they are used; lcs-attr takes over
    const { ctx } = await newContext(browser);
    const page = await ctx.newPage();
    await page.goto(HOST + '/pricing.html' + AD_QUERY);
    await choose(page, 'granted');
    await page.locator('main a[href*="contact.html"]').first().click();
    await page.waitForURL(/\/contact\.html/);
    const m = await messageTags(page);
    check(!page.url().includes('lcs_av') && /Ref: [A-Z2-9]{4}/.test(m.wa || '') && !(m.wa || '').includes('Ad visit'),
          '(c) after Accept: no lcs_av, the Ref takes over', { url: page.url(), wa: m.wa });
    await ctx.close();
  }
}

// ---------------------------------------------------------------- main

const browser = await launch();
try {
  for (const t of [testHearIsRequired, testAcceptEveryForm, testReject, testAdVisit]) {
    try { await t(browser); } catch (e) { check(false, `${t.name} crashed`, String(e && e.stack || e).split('\n').slice(0, 4).join(' | ')); }
  }
} finally {
  await browser.close();
  fs.rmSync(tmp, { recursive: true, force: true });
}
console.log(`\n${passes} passed, ${failures} failure(s)`);
process.exit(failures ? 1 : 0);
