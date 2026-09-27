(function () {
  'use strict';

  // ── Hamburger toggle ──
  var toggle = document.querySelector('.nav-toggle');
  var menu = document.getElementById('nav-menu');
  function setMenuOpen(open) {
    toggle.setAttribute('aria-expanded', String(open));
    menu.classList.toggle('is-open', open);
    // When closing the hamburger, also collapse any expanded dropdowns
    if (!open) {
      document.querySelectorAll('.has-dropdown').forEach(function (item) {
        item.setAttribute('data-open', 'false');
        var trig = item.querySelector('.dropdown-trigger');
        if (trig) trig.setAttribute('aria-expanded', 'false');
      });
    }
  }

  if (toggle && menu) {
    toggle.addEventListener('click', function () {
      setMenuOpen(toggle.getAttribute('aria-expanded') !== 'true');
    });

    // Keyboard: ESC closes the open mobile menu and returns focus to the toggle.
    // An open dropdown inside the menu consumes the first ESC (below).
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || !menu.classList.contains('is-open')) return;
      setMenuOpen(false);
      toggle.focus();
    });
  }

  // ── Dropdowns (Services, Professionals, Music Guides) ──
  var mobileQuery = window.matchMedia('(max-width: 1080px)');
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
      if (!mobileQuery.matches) return; // desktop: hover handles it
      var isOpen = item.getAttribute('data-open') === 'true';
      if (!isOpen) {
        e.preventDefault();
        setOpen(true);
      }
      // If already open, the click navigates to the trigger's href.
    });

    // Desktop: CSS :hover and :focus-within open the menu — keep aria-expanded
    // in sync for assistive tech, since the click handler above only runs on
    // mobile. data-dismissed (set by ESC) hides the menu while the pointer or
    // focus is still inside it; leaving the item clears it.
    item.addEventListener('mouseenter', function () {
      if (!mobileQuery.matches) setOpen(true);
    });
    item.addEventListener('mouseleave', function () {
      item.removeAttribute('data-dismissed');
      if (!mobileQuery.matches && !item.contains(document.activeElement)) setOpen(false);
    });
    item.addEventListener('focusin', function () {
      if (!mobileQuery.matches && !item.hasAttribute('data-dismissed')) setOpen(true);
    });
    item.addEventListener('focusout', function (e) {
      if (item.contains(e.relatedTarget)) return;
      item.removeAttribute('data-dismissed');
      if (!mobileQuery.matches) setOpen(false);
    });

    // Keyboard: ESC closes the dropdown and returns focus to the trigger.
    item.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        // In the mobile menu an open dropdown consumes this ESC; a second one
        // closes the menu itself.
        if (mobileQuery.matches && item.getAttribute('data-open') === 'true') e.stopPropagation();
        setOpen(false);
        if (!mobileQuery.matches) item.setAttribute('data-dismissed', '');
        trigger.focus();
      }
    });

    // ESC also dismisses a menu opened by mouse hover, where focus is elsewhere
    // (WCAG 1.4.13: content shown on hover must be dismissible).
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !mobileQuery.matches && item.matches(':hover')) {
        setOpen(false);
        item.setAttribute('data-dismissed', '');
      }
    });

    // Close on click outside (desktop convenience).
    document.addEventListener('click', function (e) {
      if (!item.contains(e.target)) {
        setOpen(false);
      }
    });
  });

  // Crossing the mobile/desktop breakpoint resets every dropdown, so one opened
  // inline on a phone-width window is not left pinned open on desktop.
  function resetDropdowns() {
    dropdownItems.forEach(function (item) {
      item.setAttribute('data-open', 'false');
      item.removeAttribute('data-dismissed');
      var trig = item.querySelector('.dropdown-trigger');
      if (trig) trig.setAttribute('aria-expanded', 'false');
    });
  }
  if (mobileQuery.addEventListener) mobileQuery.addEventListener('change', resetDropdowns);
  else if (mobileQuery.addListener) mobileQuery.addListener(resetDropdowns);

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

    // One current link at most: if a top-level link already matched (e.g.
    // Christmas, which is also listed under Services), leave the triggers alone.
    if (document.querySelector('#nav-menu > li > a[aria-current]')) return;

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
  if (cta && footer && 'IntersectionObserver' in window) {
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

  // Phone, email and WhatsApp taps are tracked as contact_click events by the
  // analytics snippet (partials/analytics.html); the visitor stays on the page.
})();
