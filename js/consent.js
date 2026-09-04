/* Cookie consent banner for Google Analytics and Google Ads (Consent Mode v2).
 *
 * Defaults are set to "denied" in partials/analytics.html before gtag loads,
 * so no analytics or advertising cookie is written until the visitor chooses
 * Allow. The choice is stored in localStorage under "lcs-consent" and can be
 * changed from any link carrying data-consent-open (footer: Cookie choices).
 * ad_personalization stays denied whatever the choice: the site does not run
 * remarketing, and privacy.html says so.
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
  }

  var CSS = '' +
    '.consent{position:fixed;left:1rem;bottom:1rem;z-index:1000;max-width:21rem;' +
    'background:var(--color-bg,var(--parchment,#F7F3EE));color:var(--color-text-mid,var(--organPipe,#6B5E56));' +
    'border:1px solid var(--color-rule,var(--limestone,#D6CEC6));border-radius:3px;' +
    'font-family:var(--font-body,"Source Serif 4",Georgia,serif);font-size:.8125rem;line-height:1.45;' +
    'box-shadow:0 2px 12px rgba(44,36,32,.08)}' +
    '.consent__inner{padding:.7rem .85rem;display:flex;flex-wrap:wrap;gap:.5rem .75rem;align-items:center}' +
    '.consent__text{flex:1 1 12rem;margin:0}' +
    '.consent__text a{color:inherit}' +
    '.consent__actions{display:flex;gap:.4rem}' +
    '.consent__btn{font:inherit;font-size:.75rem;letter-spacing:.04em;text-transform:uppercase;' +
    'padding:.35rem .7rem;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;border-radius:2px}' +
    '.consent__btn--allow{color:var(--color-text,var(--choirStall,#2C2420))}' +
    '.consent__btn:hover{color:var(--color-accent,var(--cassockRed,#8B3A3A))}' +
    '.consent__btn:focus-visible{outline:2px solid currentColor;outline-offset:2px}' +
    '@media (max-width:805px){.consent{left:.75rem;right:.75rem;bottom:4.5rem;max-width:none}}' +
    '@media print{.consent{display:none}}';

  var banner = null;

  function build() {
    if (banner) return banner;
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    banner = document.createElement('section');
    banner.className = 'consent';
    banner.setAttribute('aria-label', 'Cookie choices');
    banner.hidden = true;
    banner.innerHTML =
      '<div class="consent__inner">' +
        '<p class="consent__text">Analytics and ad-measurement cookies, none set until you choose. ' +
        '<a href="/privacy.html#cookies">Details</a>.</p>' +
        '<div class="consent__actions">' +
          '<button type="button" class="consent__btn consent__btn--allow" data-consent="granted">Allow</button>' +
          '<button type="button" class="consent__btn" data-consent="denied">Decline</button>' +
        '</div>' +
      '</div>';
    banner.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-consent]');
      if (!btn) return;
      var choice = btn.getAttribute('data-consent');
      write(choice);
      apply(choice);
      banner.hidden = true;
    });
    document.body.appendChild(banner);
    return banner;
  }

  function show() {
    var b = build();
    b.hidden = false;
  }

  function init() {
    var stored = read();
    if (stored !== 'granted' && stored !== 'denied') show();

    document.addEventListener('click', function (e) {
      var opener = e.target.closest('[data-consent-open]');
      if (!opener) return;
      e.preventDefault();
      show();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
