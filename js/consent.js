/* Cookie consent sheet for Google Analytics and Google Ads (Consent Mode v2).
 *
 * Defaults are set to "denied" in partials/analytics.html before gtag loads,
 * so no analytics or advertising cookie is written until the visitor chooses
 * Accept. The choice is stored in localStorage under "lcs-consent" ("granted"
 * or "denied") and can be changed from any link carrying data-consent-open
 * (footer: Cookie choices). Until a choice is stored the sheet shows on every
 * page. ad_personalization stays denied whatever the choice: the site does
 * not run remarketing, and privacy.html says so.
 *
 * The sheet is full width at the foot of the window, with Accept and Reject
 * the same size and style (PECR/ICO: rejecting is as easy as accepting). It
 * has no overlay and no scroll lock. On first view it takes keyboard focus
 * without scrolling the page. On phones it sits above the mobile CTA bar.
 * Styles: the "Cookie consent sheet" block in css/components.css and its twin
 * in partials/private-register.css.html.
 */
(function () {
  'use strict';
  var KEY = 'lcs-consent';
  var GRANTED = {
    'ad_storage': 'granted',
    'ad_user_data': 'granted',
    'ad_personalization': 'denied',
    'analytics_storage': 'granted'
  };
  var DENIED = {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied'
  };

  function read() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function write(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }

  function apply(choice) {
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', choice === 'granted' ? GRANTED : DENIED);
    }
    if (choice === 'granted' && typeof window.loadGA === 'function') window.loadGA();
    if (choice === 'granted' && typeof window.lcsKeepAttribution === 'function') window.lcsKeepAttribution();
    if (choice === 'denied') forget();
  }

  // Withdrawing consent removes what an earlier Accept left behind: the kept
  // ad click reference and the Google Analytics / Ads cookies (set on the bare
  // host or on the parent domain, so clear both).
  function forget() {
    try { sessionStorage.removeItem('lcs-attr'); } catch (e) {}
    var host = location.hostname.replace(/^www\./, '');
    document.cookie.split(';').forEach(function (c) {
      var name = c.split('=')[0].trim();
      if (!/^(_ga|_gid|_gcl_)/.test(name)) return;
      ['', '; domain=' + host, '; domain=.' + host].forEach(function (d) {
        document.cookie = name + '=; Max-Age=0; path=/' + d;
      });
    });
  }

  var banner = null;
  var cta = null;
  var returnFocus = null;
  var bodyPadding = '';

  // Keep the sheet above the mobile CTA bar while that bar is on screen
  // (nav.js slides it away when the footer comes into view), and pad the
  // page by the sheet's height so the last of the content can still be
  // scrolled into view while the sheet is open.
  function place() {
    if (!banner || banner.hidden) return;
    var lift = 0;
    if (cta && !cta.classList.contains('is-hidden') && getComputedStyle(cta).display !== 'none') {
      lift = cta.offsetHeight;
    }
    banner.style.setProperty('--consent-offset', lift + 'px');
    document.body.style.paddingBottom = (banner.offsetHeight + lift) + 'px';
  }

  function build() {
    if (banner) return banner;
    banner = document.createElement('section');
    banner.className = 'consent';
    banner.setAttribute('role', 'region');
    banner.setAttribute('aria-label', 'Cookie choices');
    banner.setAttribute('tabindex', '-1');
    banner.hidden = true;
    banner.innerHTML =
      '<div class="consent__inner">' +
        '<p class="consent__text">We&rsquo;d like to use cookies to count visits and see which of our ' +
        'Google ads lead to enquiries, and we set none unless you accept. ' +
        '<a href="/privacy.html#cookies">How we use cookies</a></p>' +
        '<div class="consent__actions">' +
          '<button type="button" class="consent__btn" data-consent="granted">Accept</button>' +
          '<button type="button" class="consent__btn" data-consent="denied">Reject</button>' +
        '</div>' +
      '</div>';
    banner.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-consent]');
      if (!btn) return;
      var choice = btn.getAttribute('data-consent');
      write(choice);
      apply(choice);
      hide(e.detail === 0);
    });
    document.body.appendChild(banner);

    cta = document.querySelector('.mobile-cta');
    window.addEventListener('resize', place);
    if (cta && 'MutationObserver' in window) {
      new MutationObserver(place).observe(cta, { attributes: true, attributeFilter: ['class'] });
    }
    return banner;
  }

  function show() {
    var b = build();
    if (b.hidden) bodyPadding = document.body.style.paddingBottom;
    b.hidden = false;
    place();
  }

  // byKeyboard: the choice came from Enter or Space (click detail 0). The
  // focused button is about to disappear, so hand focus back to whatever
  // reopened the sheet, or to the main content, so keyboard users are not
  // dropped at the end of the document.
  function hide(byKeyboard) {
    banner.hidden = true;
    document.body.style.paddingBottom = bodyPadding;
    if (returnFocus && document.contains(returnFocus)) {
      returnFocus.focus();
    } else if (byKeyboard) {
      var main = document.querySelector('main') || document.body;
      if (!main.hasAttribute('tabindex')) main.setAttribute('tabindex', '-1');
      main.focus({ preventScroll: true });
    } else if (banner.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    returnFocus = null;
  }

  function init() {
    var stored = read();
    if (stored !== 'granted' && stored !== 'denied') {
      show();
      // First view: move keyboard focus to the sheet, without scrolling, but
      // only if the visitor has not already started using the page.
      var active = document.activeElement;
      if (!active || active === document.body || active === document.documentElement) {
        banner.focus({ preventScroll: true });
      }
    }

    document.addEventListener('click', function (e) {
      var opener = e.target.closest('[data-consent-open]');
      if (!opener) return;
      e.preventDefault();
      returnFocus = opener;
      show();
      // Reopened from the footer link at the end of the page: move focus into
      // the sheet and mark the current choice.
      var current = read();
      Array.prototype.forEach.call(banner.querySelectorAll('[data-consent]'), function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-consent') === current));
      });
      banner.querySelector('[data-consent]').focus({ preventScroll: true });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
