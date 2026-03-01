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

  // ── Mobile CTA: always visible, hide only when footer is on-screen ──
  var cta = document.querySelector('.mobile-cta');
  var footer = document.querySelector('.site-footer');
  if (cta && footer) {
    var footerObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          cta.classList.add('is-hidden');
        } else {
          cta.classList.remove('is-hidden');
        }
      });
    }, { threshold: 0 });
    footerObserver.observe(footer);
  }
})();
