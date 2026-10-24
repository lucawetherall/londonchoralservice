(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;

  var successBox = document.querySelector('.form-status--success');
  var errorBox   = document.querySelector('.form-status--error');
  var submitBtn  = form.querySelector('[type="submit"]');
  var btnLabel   = submitBtn ? submitBtn.textContent : 'Send enquiry';
  var redirectUrl = form.getAttribute('data-redirect') || '/thank-you.html';

  // hCaptcha's normal checkbox is a fixed 302px iframe; on a 320px phone the
  // form is narrower and the page scrolls sideways. Ask for the compact
  // widget (158px) wherever the normal one won't fit. hCaptcha reads
  // data-size when it renders, so set it only while its script has yet to
  // run; css/components.css shrinks a full-size widget that got there first.
  var captchaBox = form.querySelector('.h-captcha');
  if (captchaBox && !window.hcaptcha && captchaBox.clientWidth < 302) {
    captchaBox.setAttribute('data-size', 'compact');
  }

  // Web3Forms' client script only adds the hCaptcha widget, whose scripts and
  // images come to about 1 MB. Fetch it as the form comes within 800px of the
  // screen, or as soon as the visitor clicks or tabs into the form, so it stays
  // out of the page's first paint. Pages still carrying the script tag skip it.
  var CAPTCHA_LOADER = 'https://web3forms.com/client/script.js';
  var captchaRequested = false;
  function loadCaptcha() {
    if (captchaRequested) return;
    captchaRequested = true;
    if (document.querySelector('script[src="' + CAPTCHA_LOADER + '"]')) return;
    var s = document.createElement('script');
    s.src = CAPTCHA_LOADER;
    s.async = true;
    document.body.appendChild(s);
  }
  if (captchaBox) {
    form.addEventListener('focusin', loadCaptcha);
    form.addEventListener('pointerdown', loadCaptcha);
    if ('IntersectionObserver' in window) {
      var captchaWatch = new IntersectionObserver(function (entries) {
        if (entries.some(function (en) { return en.isIntersecting; })) {
          captchaWatch.disconnect();
          loadCaptcha();
        }
      }, { rootMargin: '800px 0px' });
      captchaWatch.observe(form);
    } else {
      loadCaptcha();
    }
  }

  // The visitor's own occasion choice beats the page's default (?from= on the
  // redirect), so a hotel enquiry about a switch-on isn't logged as "christmas".
  function leadOccasion() {
    var select = form.querySelector('[name="occasion"]');
    if (select && select.value) return select.value;
    var m = /[?&]from=([^&]+)/.exec(redirectUrl);
    return m ? m[1] : 'general';
  }

  var guideSource = '';

  function trackError(type) {
    try {
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'form_error', { error_type: type, lead_source: window.location.pathname });
      }
    } catch (_) { /* analytics must never block the enquiry */ }
  }

  // Pre-fill the occasion select from a ?occasion= URL parameter so traffic
  // arriving from /weddings.html, /funerals.html, etc. lands with the right
  // option already chosen. No-op on forms without an #occasion select.
  try {
    var params = new URLSearchParams(window.location.search);
    var occasionParam = params.get('occasion');
    if (occasionParam) {
      var select = form.querySelector('#occasion');
      if (select) {
        var match = Array.prototype.find.call(select.options, function (o) {
          return o.value === occasionParam;
        });
        if (match) select.value = occasionParam;
      }
    }
    // ?msg= starts the message (plain text, only into an empty box); ?from=guide-<slug>
    // records the music guide the visitor came from as the lead source.
    var msgParam = params.get('msg');
    var msgBox = form.querySelector('#message');
    if (msgParam && msgBox && !msgBox.value) msgBox.value = msgParam.slice(0, 300);
    var fromParam = params.get('from');
    if (fromParam && /^guide-[a-z0-9-]{1,80}$/.test(fromParam)) guideSource = fromParam;
  } catch (_) { /* URLSearchParams unsupported — non-fatal */ }

  // Show or clear a field's own message (the <p class="form-error"> named by
  // aria-describedby) so a blocked submit says what is missing.
  function setFieldError(el, on) {
    if (on) el.setAttribute('aria-invalid', 'true');
    else el.removeAttribute('aria-invalid');
    var ids = (el.getAttribute('aria-describedby') || '').split(/\s+/);
    ids.forEach(function (id) {
      var msg = id && document.getElementById(id);
      if (msg && msg.classList.contains('form-error')) msg.setAttribute('data-visible', on ? 'true' : 'false');
    });
  }

  form.addEventListener('input', function (e) {
    var el = e.target;
    if (el.getAttribute('aria-invalid') === 'true' && el.validity && el.validity.valid) setFieldError(el, false);
  });
  form.addEventListener('change', function (e) {
    var el = e.target;
    if (el.getAttribute('aria-invalid') === 'true' && el.validity && el.validity.valid) setFieldError(el, false);
  });

  // Back from /thank-you.html restores this page from the back/forward cache
  // with the button still disabled on "Sending…" and a spent captcha token.
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = btnLabel;
    }
    if (window.hcaptcha) {
      try { window.hcaptcha.reset(); } catch (_) { /* non-fatal */ }
    }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    // Honeypot: a bot ticked the hidden box. Drop the submission silently.
    var honeypot = form.querySelector('input[name=botcheck]');
    if (honeypot && honeypot.checked) return;

    // Required-field guard. Filter form.elements rather than querying
    // :invalid, which also matches a <fieldset> holding an invalid field
    // (contact.html) — and a fieldset cannot take focus.
    var invalid = Array.prototype.filter.call(form.elements, function (el) {
      return el.willValidate && !el.validity.valid;
    });
    if (invalid.length) {
      invalid.forEach(function (el) { setFieldError(el, true); });
      trackError('incomplete');
      invalid[0].focus();
      return;
    }

    // Reset previous status
    if (successBox) successBox.setAttribute('data-visible', 'false');
    if (errorBox)   errorBox.setAttribute('data-visible', 'false');

    // hCaptcha guard — Web3Forms rejects submissions without a token,
    // so block early and surface a specific inline message instead of
    // letting the user see the generic "something went wrong" box.
    // Only block when the widget actually rendered; if the captcha script
    // failed to load (blocked, offline) let the request through so the
    // user sees the generic error with phone/email fallback rather than
    // a message about a checkbox that isn't on the page.
    var captchaError = document.getElementById('captcha-error');
    if (captchaError) captchaError.setAttribute('data-visible', 'false');
    var captchaResponse = form.querySelector('[name=h-captcha-response]');
    var captchaWidget = form.querySelector('.h-captcha iframe');
    if (captchaWidget && (!captchaResponse || !captchaResponse.value)) {
      trackError('captcha');
      if (captchaError) {
        captchaError.setAttribute('data-visible', 'true');
        captchaError.scrollIntoView({ block: 'center' });
      }
      return;
    }

    // Loading state
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending…';
    }

    // Collect form data as a plain object
    var data = {};
    var fd = new FormData(form);
    fd.forEach(function (value, key) {
      data[key] = value;
    });
    if (guideSource) data.lead_from = guideSource;
    // Ad click ID and UTM tags ride along in the enquiry email, so a booking
    // can later be reported back to Google Ads against the click that won it.
    // Only for visitors who allowed cookies, as the privacy policy says.
    var consented = false;
    try { consented = localStorage.getItem('lcs-consent') === 'granted'; } catch (_) {}
    if (consented && typeof window.lcsAttribution === 'function') {
      var attr = window.lcsAttribution();
      Object.keys(attr).forEach(function (k) { if (!data[k]) data[k] = attr[k]; });
    }
    // Without consent: the ad visit label when this visit came from an ad
    // (the landing page and campaign, "pricing (wedding-leads)", never the
    // click ID), and the click ID itself only if the sender ticked the
    // ad-measurement box (ad_measurement=yes). Nothing is stored.
    if (!consented) {
      try {
        if (typeof window.lcsAdVisit === 'function') {
          var visit = window.lcsAdVisit();
          if (visit) data.ad_visit = visit;
        }
        if (data.ad_measurement === 'yes' && typeof window.lcsClickIds === 'function') {
          var ids = window.lcsClickIds();
          Object.keys(ids).forEach(function (k) { if (!data[k]) data[k] = ids[k]; });
        }
      } catch (_) { /* attribution must never block the enquiry */ }
    }

    // A hung request must fall through to the error path, not leave the button on "Sending…".
    var ctrl = typeof AbortController === 'function' ? new AbortController() : null;
    var abortTimer = ctrl ? setTimeout(function () { ctrl.abort(); }, 20000) : null;
    var fetchOpts = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(data)
    };
    if (ctrl) fetchOpts.signal = ctrl.signal;
    fetch('https://api.web3forms.com/submit', fetchOpts)
      .then(function (response) {
        if (abortTimer) clearTimeout(abortTimer);
        return response.json().then(function (result) {
          return { ok: response.ok, result: result };
        });
      })
      .then(function (payload) {
        if (payload.ok && payload.result.success) {
          var go = function () { window.location.href = redirectUrl; };
          if (typeof window.lcsLead === 'function') {
            try { window.lcsLead({ source: guideSource || window.location.pathname, occasion: leadOccasion(), email: data.email, phone: data.phone }, go); }
            catch (_) { go(); }
          } else {
            go();
          }
        } else {
          throw new Error(payload.result.message || 'Submission failed');
        }
      })
      .catch(function (err) {
        if (abortTimer) clearTimeout(abortTimer);
        console.error('Form submission error:', err);
        trackError('submit');
        if (errorBox) {
          // A timed-out request may still have reached Web3Forms: say so, to head off a duplicate.
          if (err && err.name === 'AbortError' && !errorBox.querySelector('[data-timeout-note]')) {
            var note = document.createElement('p');
            note.setAttribute('data-timeout-note', '');
            note.textContent = 'It may still have reached us. If you have no reply within one working day, send it again.';
            errorBox.appendChild(note);
          }
          errorBox.setAttribute('data-visible', 'true');
          errorBox.scrollIntoView({ block: 'center' });
        }
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = btnLabel;
        }
        // hCaptcha tokens are single-use; reset so a retry gets a fresh one.
        if (window.hcaptcha) {
          try { window.hcaptcha.reset(); } catch (_) { /* non-fatal */ }
        }
      });
  });
})();
