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
      // When closing the hamburger, also collapse any expanded dropdowns
      if (expanded) {
        document.querySelectorAll('.has-dropdown').forEach(function (item) {
          item.setAttribute('data-open', 'false');
          var trig = item.querySelector('.dropdown-trigger');
          if (trig) trig.setAttribute('aria-expanded', 'false');
        });
      }
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
  // Second pass also lights up dropdown triggers whose children
  // include the current page (covers Services dropdown where
  // children sit at root level rather than under /services/).
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

    document.querySelectorAll('.has-dropdown').forEach(function (item) {
      var trigger = item.querySelector('.dropdown-trigger');
      if (!trigger || trigger.getAttribute('aria-current') === 'page') return;
      var children = item.querySelectorAll('.dropdown-menu a');
      for (var i = 0; i < children.length; i++) {
        var raw = children[i].getAttribute('href');
        if (!raw || raw.indexOf('://') !== -1) continue;
        var clean = raw.split('?')[0].replace(/\/index\.html$/, '/');
        if (clean === here) {
          trigger.setAttribute('aria-current', 'page');
          break;
        }
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

    var waLinks = document.querySelectorAll('a[href*="wa.me/"]');
    for (var k = 0; k < waLinks.length; k++) {
      waLinks[k].addEventListener('click', function () {
        setTimeout(function () {
          window.location.href = thankYouBase + '?from=whatsapp';
        }, 300);
      });
    }
  }
})();
