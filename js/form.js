(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;

  var successBox = document.querySelector('.form-status--success');
  var errorBox   = document.querySelector('.form-status--error');
  var submitBtn  = form.querySelector('[type="submit"]');
  var btnLabel   = submitBtn ? submitBtn.textContent : 'Send enquiry';
  var redirectUrl = form.getAttribute('data-redirect') || '/thank-you.html';

  // The visitor's own occasion choice beats the page's default (?from= on the
  // redirect), so a hotel enquiry about a switch-on isn't logged as "christmas".
  function leadOccasion() {
    var select = form.querySelector('[name="occasion"]');
    if (select && select.value) return select.value;
    var m = /[?&]from=([^&]+)/.exec(redirectUrl);
    return m ? m[1] : 'general';
  }

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
  } catch (_) { /* URLSearchParams unsupported — non-fatal */ }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    // Basic required-field guard (CSS :user-invalid handles visual state)
    var invalid = form.querySelectorAll(':invalid');
    if (invalid.length) {
      invalid[0].focus();
      return;
    }

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
        captchaError.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    // Reset previous status
    if (successBox) successBox.setAttribute('data-visible', 'false');
    if (errorBox)   errorBox.setAttribute('data-visible', 'false');

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
    // Ad click ID and UTM tags ride along in the enquiry email, so a booking
    // can later be reported back to Google Ads against the click that won it.
    if (typeof window.lcsAttribution === 'function') {
      var attr = window.lcsAttribution();
      Object.keys(attr).forEach(function (k) { if (!data[k]) data[k] = attr[k]; });
    }

    fetch('https://api.web3forms.com/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(data)
    })
      .then(function (response) {
        return response.json().then(function (result) {
          return { ok: response.ok, result: result };
        });
      })
      .then(function (payload) {
        if (payload.ok && payload.result.success) {
          var go = function () { window.location.href = redirectUrl; };
          if (typeof window.lcsLead === 'function') {
            try { window.lcsLead({ source: window.location.pathname, occasion: leadOccasion(), email: data.email, phone: data.phone }, go); }
            catch (_) { go(); }
          } else {
            go();
          }
        } else {
          throw new Error(payload.result.message || 'Submission failed');
        }
      })
      .catch(function (err) {
        console.error('Form submission error:', err);
        trackError('submit');
        if (errorBox) {
          errorBox.setAttribute('data-visible', 'true');
          errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
