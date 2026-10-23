/* Cookie-free visit counter (GoatCounter), off until a site code is set.
 *
 * partials/analytics.html loads this file only when its LCS_COUNTER holds a
 * GoatCounter site code; while LCS_COUNTER is empty no page loads it. Once on,
 * it counts a page view on every page, and an event when an enquiry form is
 * accepted (enquiry-sent-form, from lcsLead in the partial) or a phone, email
 * or WhatsApp link is tapped (enquiry-sent-call, -email, -whatsapp). It runs
 * whatever the cookie choice: it sets no cookie and writes nothing to the
 * device, apart from the opt-out flag below when a visitor asks for it.
 *
 * Each hit goes to GoatCounter's documented /count endpoint
 * (goatcounter.com/help/pixel) and carries only: p, the page path (never the
 * query string, so never an ad click ID) or the event name; t, the page title
 * or a fixed event label; r, the referring site's origin when it is another
 * site (for an event, this page's address without its query string); e on
 * events. Nothing typed into a form, and no email address or phone number, is
 * ever sent. GoatCounter tells new visits from repeat views by IP address and
 * User-Agent, held in memory for up to 8 hours and never stored
 * (goatcounter.com/help/sessions).
 *
 * Not counted: any host but the live site (local previews, test copies),
 * automated browsers (navigator.webdriver), a Global Privacy Control or Do Not
 * Track signal, the owner's devices (lcs-internal, set by ?lcs_internal=1),
 * and a browser that opened a page with ?lcs_count=off (privacy.html links to
 * it; ?lcs_count=on undoes it).
 */
(function () {
  'use strict';
  var code = String(window.LCS_COUNTER || '');
  if (!/^[a-z0-9][a-z0-9-]{0,62}$/.test(code)) return;
  if (!/(^|\.)londonchoralservice\.com$/.test(location.hostname)) return;
  var off = false;
  try {
    var flag = new URLSearchParams(location.search).get('lcs_count');
    if (flag === 'off') localStorage.setItem('lcs-count-off', '1');
    if (flag === 'on') localStorage.removeItem('lcs-count-off');
    off = localStorage.getItem('lcs-count-off') === '1' || localStorage.getItem('lcs-internal') === '1';
  } catch (e) {}
  if (off || navigator.webdriver || navigator.globalPrivacyControl === true || navigator.doNotTrack === '1') return;

  var endpoint = 'https://' + code + '.goatcounter.com/count';
  var path = location.pathname.replace(/\/index\.html$/, '/') || '/';
  var here = location.origin + path;

  function send(hit) {
    var q = [];
    for (var k in hit) {
      if (hit[k]) q.push(k + '=' + encodeURIComponent(hit[k]));
    }
    var url = endpoint + '?' + q.join('&') + '&rnd=' + Math.random().toString(36).slice(2, 8);
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(url)) return;
    } catch (e) {}
    var img = new Image();
    img.referrerPolicy = 'no-referrer';
    img.src = url;
  }

  // Another site that sent the visitor, as its origin only (never its path or
  // query); nothing for a visit from one of our own pages.
  function referrer() {
    try {
      var r = new URL(document.referrer);
      var host = function (h) { return h.replace(/^www\./, ''); };
      if (/^https?:$/.test(r.protocol) && host(r.hostname) !== host(location.hostname)) return r.origin;
    } catch (e) {}
    return '';
  }

  var EVENTS = {
    'enquiry-sent-form': 'Enquiry form sent',
    'enquiry-sent-call': 'Phone link tapped',
    'enquiry-sent-email': 'Email link tapped',
    'enquiry-sent-whatsapp': 'WhatsApp link tapped'
  };
  window.lcsCount = function (name) {
    if (Object.prototype.hasOwnProperty.call(EVENTS, name)) {
      send({ p: name, t: EVENTS[name], r: here, e: 'true' });
    }
  };

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="tel:"], a[href^="mailto:"], a[href*="wa.me/"]');
    if (!a) return;
    var href = a.getAttribute('href');
    window.lcsCount(href.indexOf('tel:') === 0 ? 'enquiry-sent-call' :
      href.indexOf('mailto:') === 0 ? 'enquiry-sent-email' : 'enquiry-sent-whatsapp');
  });

  // The page view, once the title is parsed and the page is on screen (not a
  // prerender or a tab opened in the background that is never looked at).
  function pageView() {
    send({ p: path, t: document.title, r: referrer() });
  }
  function whenShown() {
    if (document.prerendering) {
      document.addEventListener('prerenderingchange', whenShown, { once: true });
    } else if (document.visibilityState === 'hidden') {
      document.addEventListener('visibilitychange', function onShow() {
        if (document.visibilityState !== 'visible') return;
        document.removeEventListener('visibilitychange', onShow);
        pageView();
      });
    } else {
      pageView();
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', whenShown);
  } else {
    whenShown();
  }
})();
