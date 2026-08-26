(function () {
  'use strict';

  // Stamp as early as possible: the timing check measures from script start.
  var pageLoadTs = Date.now();

  // ── Config ──
  var PE = {
    // YouTube IDs keyed by voicing. IDs MUST come from
    // data/seo-fix-discovered-urls.yml — never invent them. To map a new
    // video, add it to that file first (with a verified upload date), then
    // paste its ID here. null = no player rendered for that voicing.
    VOICING_VIDEOS: {
      'eight': null,
      'twelve': null,
      'sixteen': null,
      'twenty-four': null
    },
    // The site's existing generic Contact conversion label (as fired on
    // thank-you.html). Swap for the dedicated "Private events enquiry"
    // label once it exists in Google Ads — see MANUAL-ACTIONS-REQUIRED.md.
    ADS_CONVERSION: 'AW-17988388404/RjhECKGP7akcELSMxIFD',
    MIN_SECONDS: 5
  };

  // ── Motion ──
  // Entrance styles are gated on .pe-motion so reduced-motion users get the
  // page with no opacity:0 rules ever applied. scrollIntoView calls below
  // deliberately omit behavior: the CSS scroll-behavior rule, itself gated
  // on reduced-motion, decides whether scrolling is smooth.
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
    document.documentElement.classList.add('pe-motion');
  }

  var fadeEls = document.querySelectorAll('[data-fade]');
  if (fadeEls.length) {
    if ('IntersectionObserver' in window) {
      var fadeObserver = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('pe-in');
            fadeObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15 });
      fadeEls.forEach(function (el) { fadeObserver.observe(el); });
    } else {
      fadeEls.forEach(function (el) { el.classList.add('pe-in'); });
    }
  }

  // ── Voicing selector ──
  var form = document.getElementById('pe-enquiry');
  var voicingRadios = document.querySelectorAll('input[name="voicing-choice"]');
  var voicingNote = document.getElementById('voicing-note');
  var voicingMedia = document.getElementById('voicing-media');
  var ensembleSelect = document.getElementById('ensemble-size');
  var voicingExplored = document.querySelector('input[name="voicing_explored"]');

  function renderVoicingMedia(value, radio) {
    if (!voicingMedia) return;
    voicingMedia.innerHTML = '';
    var videoId = PE.VOICING_VIDEOS[value];
    if (!videoId) return; // no mapped video — render nothing, no dead buttons

    var playLabel = (radio && radio.getAttribute('data-play-label')) || 'Play recording';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'video-thumb';
    btn.setAttribute('aria-label', playLabel);
    btn.innerHTML =
      '<img src="https://i.ytimg.com/vi/' + videoId + '/hqdefault.jpg" alt="" loading="lazy" width="480" height="360">' +
      '<svg class="play-btn" viewBox="0 0 68 48" aria-hidden="true">' +
      '<path d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55c-2.93.78-4.63 3.26-5.42 6.19C.06 13.05 0 24 0 24s.06 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.63-3.26 5.42-6.19C67.94 34.95 68 24 68 24s-.06-10.95-1.48-16.26z" fill="rgba(42, 23, 8, .72)"/>' +
      '<path d="M45 24 27 14v20z" fill="#FAF6EE"/>' +
      '</svg>';

    // Third-party embed loads only on click (site-wide pattern).
    btn.addEventListener('click', function () {
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1';
      iframe.title = playLabel.replace(/^Play /, '') + ' — Alma Consort';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      iframe.allowFullscreen = true;
      iframe.style.border = '0';
      voicingMedia.innerHTML = '';
      voicingMedia.appendChild(iframe);
    });

    voicingMedia.appendChild(btn);
  }

  // syncForm is false on page load: the enquiry form must keep its
  // "Guidance welcome" default, and voicing_explored must only record a
  // choice the visitor actually made.
  function applyVoicing(radio, syncForm) {
    var value = radio.value;

    // The prose lives in the markup, not here: each radio's parent label
    // carries the note as a data-note attribute.
    if (voicingNote) {
      var label = radio.closest ? radio.closest('label') : null;
      var note = label && label.getAttribute('data-note');
      if (note) voicingNote.textContent = note;
    }

    if (syncForm) {
      if (ensembleSelect) ensembleSelect.value = value + '-voices';
      if (voicingExplored) voicingExplored.value = value;
    }

    renderVoicingMedia(value, radio);
  }

  voicingRadios.forEach(function (radio) {
    radio.addEventListener('change', function () {
      if (radio.checked) applyVoicing(radio, true);
    });
    if (radio.checked) applyVoicing(radio, false);
  });

  // ── UTM / click-ID capture ──
  // Same-named hidden inputs exist empty in the markup; fill any present
  // in the query string so the enquiry email carries its source.
  try {
    var params = new URLSearchParams(window.location.search);
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'gclid'].forEach(function (key) {
      var value = params.get(key);
      if (!value) return;
      var input = document.querySelector('input[name="' + key + '"]');
      if (input) input.value = value;
    });
  } catch (_) { /* URLSearchParams unsupported — non-fatal */ }

  // ── Conditional fields ──
  // Hidden wrappers also disable their fields so FormData excludes them.
  // Sync functions are re-run on pageshow: browsers restore form state on
  // back/forward navigation without firing change events.
  var syncFns = [];

  function setFieldVisible(wrapper, visible) {
    if (!wrapper) return;
    wrapper.hidden = !visible;
    wrapper.querySelectorAll('input, select, textarea').forEach(function (field) {
      field.disabled = !visible;
    });
  }

  var enquiringAs = document.getElementById('enquiring-as');
  var companyField = document.querySelector('.pe-field--company');
  if (enquiringAs && companyField) {
    var syncCompany = function () {
      var v = enquiringAs.value;
      setFieldVisible(companyField, v === 'Planner or agency' || v === 'Venue or hotel');
    };
    enquiringAs.addEventListener('change', syncCompany);
    syncFns.push(syncCompany);
  }

  var dateFlexible = document.getElementById('date-flexible');
  var eventDate = document.getElementById('event-date');
  if (dateFlexible && eventDate) {
    var syncDate = function () {
      eventDate.disabled = dateFlexible.checked;
      if (dateFlexible.checked) eventDate.value = '';
    };
    dateFlexible.addEventListener('change', syncDate);
    syncFns.push(syncDate);
  }

  var hearSelect = document.getElementById('hear');
  var hearDetailField = document.querySelector('.pe-field--hear-detail');
  if (hearSelect && hearDetailField) {
    var syncHear = function () {
      // "Who referred you?" applies to every referral-type answer.
      setFieldVisible(hearDetailField, /^(Referred|Recommended) /.test(hearSelect.value));
    };
    hearSelect.addEventListener('change', syncHear);
    syncFns.push(syncHear);
  }

  function runSyncs() { syncFns.forEach(function (fn) { fn(); }); }
  runSyncs();
  window.addEventListener('pageshow', runSyncs);

  // ── Conversion tracking ──
  // The GA head snippet defines global gtag() (a dataLayer queue, live
  // before the gtag.js library loads) and global loadGA() (idempotent lazy
  // loader). Both are typeof-guarded so a blocked or stripped analytics
  // snippet can never break the submission flow.
  function fireConversion() {
    try {
      if (typeof window.loadGA === 'function') window.loadGA();
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'conversion', { send_to: PE.ADS_CONVERSION });
        window.gtag('event', 'ads_conversion_PrivateEvents_1', {});
      }
    } catch (_) { /* analytics must never block the enquiry */ }
  }

  // ── Form submit ──
  if (form) {
    // The markup omits novalidate so no-JS visitors keep native browser
    // validation on the plain HTML POST fallback; with JS running, the
    // custom flow below takes over.
    form.setAttribute('novalidate', '');

    var successBox = document.getElementById('pe-form-success');
    var errorBox = document.querySelector('.pe-form-error:not(.pe-captcha-error)');
    var captchaError = document.getElementById('captcha-error');
    var submitBtn = form.querySelector('[type="submit"]');
    var btnLabel = submitBtn ? submitBtn.textContent : 'Send enquiry';

    // The error box holds one message per failure mode; showError reveals
    // the box with only the relevant message visible.
    function showError(kind, scroll) {
      if (!errorBox) return;
      errorBox.querySelectorAll('[data-error-msg]').forEach(function (msg) {
        msg.hidden = msg.getAttribute('data-error-msg') !== kind;
      });
      errorBox.setAttribute('data-visible', 'true');
      if (scroll) errorBox.scrollIntoView({ block: 'center' });
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Required-field guard: focus the first invalid field and name the
      // problem (the CSS :user-invalid rule marks the fields themselves).
      var invalid = form.querySelectorAll(':invalid');
      if (invalid.length) {
        showError('incomplete', false);
        invalid[0].focus();
        return;
      }

      // Honeypot: a checked botcheck means a bot filled the form —
      // silently do nothing.
      var honeypot = form.querySelector('input[name="botcheck"]');
      if (honeypot && honeypot.checked) return;

      // hCaptcha guard (mirrors js/form.js): Web3Forms rejects submissions
      // without a token, so block early and name the reason. Only block when
      // the widget actually rendered — if the captcha script was blocked or
      // failed to load, let the request through so the visitor sees the
      // generic error with the email and phone fallback rather than a
      // message about a checkbox that is not on the page.
      if (captchaError) captchaError.setAttribute('data-visible', 'false');
      var captchaResponse = form.querySelector('[name=h-captcha-response]');
      var captchaWidget = form.querySelector('.h-captcha iframe');
      if (captchaWidget && (!captchaResponse || !captchaResponse.value)) {
        if (captchaError) {
          captchaError.setAttribute('data-visible', 'true');
          captchaError.scrollIntoView({ block: 'center' });
        }
        return;
      }

      if (errorBox) errorBox.setAttribute('data-visible', 'false');

      // Timing check: a submit within seconds of page load is not a person.
      var elapsed = (Date.now() - pageLoadTs) / 1000;
      if (elapsed < PE.MIN_SECONDS) {
        showError('timing', true);
        return;
      }

      var timeOnPage = form.querySelector('input[name="time_on_page"]');
      if (timeOnPage) timeOnPage.value = String(Math.round(elapsed));

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending…';
      }

      // Collect form data as a plain object (disabled fields excluded)
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
            fireConversion();
            // Inline confirmation — the page stays open, no redirect.
            form.hidden = true;
            if (successBox) {
              successBox.hidden = false;
              successBox.focus();
              successBox.scrollIntoView({ block: 'center' });
            }
          } else {
            throw new Error(payload.result.message || 'Submission failed');
          }
        })
        .catch(function () {
          // hCaptcha tokens are single-use — reset so a retry can succeed.
          try {
            if (window.hcaptcha && typeof window.hcaptcha.reset === 'function') window.hcaptcha.reset();
          } catch (_) { /* widget absent or blocked */ }
          showError('network', true);
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = btnLabel;
          }
        });
    });
  }
})();
