(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;

  var successBox = document.querySelector('.form-status--success');
  var errorBox   = document.querySelector('.form-status--error');
  var submitBtn  = form.querySelector('[type="submit"]');
  var btnLabel   = submitBtn ? submitBtn.textContent : 'Send enquiry';

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    // Basic required-field guard (CSS :user-invalid handles visual state)
    var invalid = form.querySelectorAll(':invalid');
    if (invalid.length) {
      invalid[0].focus();
      return;
    }

    // hCaptcha guard
    var captchaError = document.getElementById('captcha-error');
    if (captchaError) captchaError.style.display = 'none';
    var captchaResponse = form.querySelector('textarea[name=h-captcha-response]');
    if (!captchaResponse || !captchaResponse.value) {
      if (captchaError) captchaError.style.display = 'block';
      return;
    }

    // Reset previous status
    if (successBox) successBox.setAttribute('data-visible', 'false');
    if (errorBox)   errorBox.setAttribute('data-visible', 'false');

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
          form.hidden = true;
          if (successBox) successBox.setAttribute('data-visible', 'true');
        } else {
          throw new Error(payload.result.message || 'Submission failed');
        }
      })
      .catch(function () {
        if (errorBox) errorBox.setAttribute('data-visible', 'true');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = btnLabel;
        }
      });
  });
})();
