(function () {
  var form = document.querySelector('.contact-form');
  if (!form) return;

  var successBox = document.querySelector('.form-status--success');
  var errorBox   = document.querySelector('.form-status--error');
  var submitBtn  = form.querySelector('[type="submit"]');
  var btnLabel   = submitBtn ? submitBtn.textContent : 'Send enquiry';
  var redirectUrl = form.getAttribute('data-redirect') || 'thank-you.html';

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var invalid = form.querySelectorAll(':invalid');
    if (invalid.length) {
      invalid[0].focus();
      return;
    }

    if (successBox) successBox.setAttribute('data-visible', 'false');
    if (errorBox)   errorBox.setAttribute('data-visible', 'false');

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending…';
    }

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
        if (errorBox) errorBox.setAttribute('data-visible', 'true');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = btnLabel;
        }
      });
  });
})();
