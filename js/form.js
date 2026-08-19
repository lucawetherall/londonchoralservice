(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;

  var successBox = document.querySelector('.form-status--success');
  var errorBox   = document.querySelector('.form-status--error');
  var submitBtn  = form.querySelector('[type="submit"]');
  var btnLabel   = submitBtn ? submitBtn.textContent : 'Send enquiry';
  var redirectUrl = form.getAttribute('data-redirect') || '/thank-you.html';

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
          window.location.href = redirectUrl;
        } else {
          throw new Error(payload.result.message || 'Submission failed');
        }
      })
      .catch(function (err) {
        console.error('Form submission error:', err);
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
