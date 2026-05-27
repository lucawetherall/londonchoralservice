(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;

  var successBox = document.querySelector('.form-status--success');
  var errorBox   = document.querySelector('.form-status--error');
  var submitBtn  = form.querySelector('[type="submit"]');
  var btnLabel   = submitBtn ? submitBtn.textContent : 'Send enquiry';

  // Pre-fill the occasion select from a ?occasion= URL parameter so traffic
  // arriving from /weddings.html, /funerals.html, etc. lands with the right
  // option already chosen.
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

  var captchaError = document.getElementById('captcha-error');

  function showCaptchaError() {
    if (!captchaError) return;
    captchaError.setAttribute('data-visible', 'true');
    captchaError.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    // Clear all prior status messages so previous attempts don't linger
    if (successBox)   successBox.setAttribute('data-visible', 'false');
    if (errorBox)     errorBox.setAttribute('data-visible', 'false');
    if (captchaError) captchaError.setAttribute('data-visible', 'false');

    // Basic required-field guard (CSS :user-invalid handles visual state)
    var invalid = form.querySelectorAll(':invalid');
    if (invalid.length) {
      invalid[0].focus();
      return;
    }

    // hCaptcha guard — Web3Forms rejects submissions without a token,
    // so block early and surface a specific inline message instead of
    // letting the user see the generic "something went wrong" box.
    var captchaResponse = form.querySelector('textarea[name=h-captcha-response]');
    if (!captchaResponse || !captchaResponse.value) {
      showCaptchaError();
      return;
    }

    // Loading state
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending\u2026';
    }

    // Collect form data as a plain object
    var data = {};
    var fd = new FormData(form);
    fd.forEach(function (value, key) {
      data[key] = value;
    });

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
          window.location.href = 'thank-you.html';
        } else {
          throw new Error(payload.result.message || 'Submission failed');
        }
      })
      .catch(function (err) {
        console.error('Form submission error:', err);
        // hCaptcha tokens are single-use, so any submission attempt may
        // have consumed it. Clear the response field and reset the widget
        // so the user gets a fresh challenge on retry — otherwise their
        // next submit would resend the same stale token and loop on the
        // same error.
        if (captchaResponse) captchaResponse.value = '';
        if (window.hcaptcha && typeof window.hcaptcha.reset === 'function') {
          try { window.hcaptcha.reset(); } catch (_) { /* non-fatal */ }
        }
        // If the server rejected for a captcha-related reason (e.g. token
        // expired between tick and submit), point the user at the captcha
        // instead of showing the generic "something went wrong" box.
        var msg = String(err && err.message || '').toLowerCase();
        if (msg.indexOf('captcha') !== -1) {
          showCaptchaError();
        } else if (errorBox) {
          errorBox.setAttribute('data-visible', 'true');
        }
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = btnLabel;
        }
      });
  });
})();
