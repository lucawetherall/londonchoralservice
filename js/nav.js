(function () {
  'use strict';

  // ── Hamburger toggle ──
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.getElementById('nav-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      menu.classList.toggle('is-open');
    });
  }

  // ── Dropdown (Music Guides) ──
  var dropdownItems = document.querySelectorAll('.has-dropdown');
  dropdownItems.forEach(function (item) {
    var trigger = item.querySelector('.dropdown-trigger');
    if (!trigger) return;

    function setOpen(open) {
      item.setAttribute('data-open', open ? 'true' : 'false');
      trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    // Mobile: tap on the caret area expands inline; tapping the link
    // navigates as normal. We treat any tap on a touch device that
    // hits the trigger AND the menu is currently closed as "open
    // first, navigate next time".
    trigger.addEventListener('click', function (e) {
      var isMobile = window.matchMedia('(max-width: 767px)').matches;
      if (!isMobile) return; // desktop: hover handles it
      var isOpen = item.getAttribute('data-open') === 'true';
      if (!isOpen) {
        e.preventDefault();
        setOpen(true);
      }
      // If already open, the click navigates to the trigger's href.
    });

    // Keyboard: ESC closes the dropdown and returns focus to the trigger.
    item.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        setOpen(false);
        trigger.focus();
      }
    });

    // Close on click outside (desktop convenience).
    document.addEventListener('click', function (e) {
      if (!item.contains(e.target)) {
        setOpen(false);
      }
    });
  });

  // ── aria-current on the matching nav link ──
  // Set aria-current="page" on the nav link whose href matches
  // the current document path. Handles "/" matching index.html.
  (function setAriaCurrent() {
    var navLinks = document.querySelectorAll('#nav-menu > li > a');
    var here = window.location.pathname.replace(/\/index\.html$/, '/');
    navLinks.forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href || href.indexOf('://') !== -1) return;
      var linkPath = href.replace(/\/index\.html$/, '/');
      if (linkPath === here || (linkPath !== '/' && here.indexOf(linkPath) === 0)) {
        link.setAttribute('aria-current', 'page');
      }
    });
  })();

  // ── Year stamp ──
  var yearEl = document.querySelector('[data-year]');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // ── Mobile CTA: hide when footer is on-screen ──
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

  // ── Conversion tracking: redirect to thank-you after tel:/mailto: clicks ──
  if (!/thank-you\.html/.test(window.location.pathname)) {
    var thankYouBase = '/thank-you.html';

    var isMobile = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    if (isMobile) {
      var telLinks = document.querySelectorAll('a[href^="tel:"]');
      for (var i = 0; i < telLinks.length; i++) {
        telLinks[i].addEventListener('click', function () {
          setTimeout(function () {
            window.location.href = thankYouBase + '?from=call';
          }, 300);
        });
      }
    }

    var mailLinks = document.querySelectorAll('a[href^="mailto:"]');
    for (var j = 0; j < mailLinks.length; j++) {
      mailLinks[j].addEventListener('click', function () {
        setTimeout(function () {
          window.location.href = thankYouBase + '?from=email';
        }, 300);
      });
    }
  }
})();
