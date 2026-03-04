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

  // ── Phone call tracking (mobile only): redirect to thank-you after tel: tap ──
  var isMobile = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  if (isMobile && !/thank-you\.html/.test(window.location.pathname)) {
    var telLinks = document.querySelectorAll('a[href^="tel:"]');
    var thankYouBase = window.location.pathname.indexOf('/music-guides/') !== -1
      ? '../thank-you.html' : 'thank-you.html';
    for (var i = 0; i < telLinks.length; i++) {
      telLinks[i].addEventListener('click', function () {
        setTimeout(function () {
          window.location.href = thankYouBase + '?from=call';
        }, 300);
      });
    }
  }
})();
