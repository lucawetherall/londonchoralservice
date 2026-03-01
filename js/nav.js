(function () {
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.getElementById('nav-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      menu.classList.toggle('is-open');
    });
  }

  var yearEl = document.querySelector('[data-year]');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // ── Mobile CTA: hide on scroll-up, show on scroll-down ──
  var cta = document.querySelector('.mobile-cta');
  if (cta) {
    var lastY = window.scrollY;
    var threshold = 10;

    window.addEventListener('scroll', function () {
      var currentY = window.scrollY;
      if (Math.abs(currentY - lastY) < threshold) return;

      if (currentY > lastY) {
        cta.classList.remove('is-hidden');
      } else {
        cta.classList.add('is-hidden');
      }
      lastY = currentY;
    }, { passive: true });
  }
})();
