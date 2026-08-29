#!/usr/bin/env python3
"""Scaffold builder for pages in the private register (Alma Consort).

The register's look comes from partials/private-register.css.html; this module
only assembles the parts every register page must carry identically — the head,
the GA4/Ads snippet, the bespoke header and breadcrumb, the enquiry form, and
the closing scripts. Page prose is hand-authored and passed in, never generated.

Why this exists: the register is insulated from the site nav/footer partials and
from css/style.css, so a register page cannot be cloned from an ordinary page.
Without a single scaffold the Web3Forms client script, the gtag snippet, or the
absolute asset paths get dropped from one page in twenty and the form fails
silently on it. See docs/superpowers/specs/2026-08-29-international-luxury-weddings-design.md
"""

SITE = 'https://londonchoralservice.com'
ACCESS_KEY = 'dc1af546-26ac-45b3-a85d-064a3a59886d'
OG_IMAGE = f'{SITE}/assets/og-private-events.png'
OG_ALT = ('Alma Consort, London: the sound of an English cathedral, wherever you are '
          '&mdash; private and international choral engagements')

GA_SNIPPET = '''  <!-- Google Analytics (GA4) — deferred until after load -->
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    function loadGA() {
      if (loadGA.done) return;
      loadGA.done = true;
      gtag('js', new Date());
      gtag('config', 'G-9FENN7VS0E');
      gtag('config', 'AW-17988388404');
      var s = document.createElement('script');
      s.src = 'https://www.googletagmanager.com/gtag/js?id=G-9FENN7VS0E';
      document.head.appendChild(s);
    }
    if ('requestIdleCallback' in window) {
      requestIdleCallback(loadGA, { timeout: 3000 });
    } else {
      window.addEventListener('load', function() { setTimeout(loadGA, 100); });
    }
    if (/[?&](gclid|gbraid|wbraid)=/.test(location.search)) loadGA();
    ['scroll', 'click', 'touchstart', 'keydown'].forEach(function(evt) {
      window.addEventListener(evt, loadGA, { once: true, passive: true });
    });
  </script>'''


def head(title, description, path):
    """path is site-relative with no leading slash, e.g. 'destinations/italy.html'."""
    url = f'{SITE}/{path}'
    if len(description) < 141 or len(description) > 161:
        raise ValueError(f'meta description for {path} is {len(description)} chars, need 141-161')
    return f'''<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="UTF-8">
  <!-- @include-start partials/head-extras.html -->
  <!-- @include-end partials/head-extras.html -->
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">

{GA_SNIPPET}

  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="theme-color" content="#FAF6EE">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="en-gb" href="{url}">
  <link rel="alternate" hreflang="x-default" href="{url}">

  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{url}">
  <meta property="og:locale" content="en_GB">
  <meta property="og:site_name" content="London Choral Service">
  <meta property="og:image" content="{OG_IMAGE}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{OG_ALT}">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="{OG_IMAGE}">
  <meta name="twitter:image:alt" content="{OG_ALT}">
  <link rel="dns-prefetch" href="https://www.googletagmanager.com">
  <link rel="dns-prefetch" href="https://api.web3forms.com">
  <link rel="dns-prefetch" href="https://hcaptcha.com">

  <!-- @include-start partials/private-register.css.html -->
  <!-- @include-end partials/private-register.css.html -->
'''


def head_close(jsonld):
    # Favicon paths are ABSOLUTE. The hub's are relative and would 404 one
    # directory down in destinations/.
    return f'''
  <script type="application/ld+json">
{jsonld}
  </script>

  <link rel="icon" href="/assets/favicon.ico" sizes="any">
  <link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
</head>
<body>
'''


def header(crumbs):
    """crumbs: list of (label, href) with href None for the current page."""
    if not crumbs:
        return '''
  <header class="pe-header">
    <nav class="pe-nav" aria-label="Page">
      <a class="pe-wordmark" href="/">The London Choral Service</a>
      <a class="pe-nav-enquire" href="#enquire">Enquire</a>
    </nav>
  </header>
'''
    parts = []
    for label, href in crumbs:
        if href:
            parts.append(f'<a href="{href}">{label}</a>')
        else:
            parts.append(f'<span aria-current="page">{label}</span>')
    trail = '\n        <span class="pe-crumb-sep" aria-hidden="true">&rsaquo;</span>\n        '.join(parts)
    return f'''
  <header class="pe-header">
    <nav class="pe-nav" aria-label="Page">
      <a class="pe-wordmark" href="/">The London Choral Service</a>
      <a class="pe-nav-enquire" href="#enquire">Enquire</a>
    </nav>
    <nav class="pe-breadcrumb" aria-label="Breadcrumb">
      <p>
        {trail}
      </p>
    </nav>
  </header>
'''


def enquiry_form(source_page, subject, enquiring_as_default=None, intro=None):
    """The register's shared enquiry form.

    source_page is the attribution value: without it every page feeds one inbox
    and cost per qualified enquiry cannot be computed per page.
    """
    intro_html = intro or 'We take a small number of engagements each year. Tell us about yours.'

    def opt(value):
        sel = ' selected' if value == enquiring_as_default else ''
        return f'                <option{sel}>{value}</option>'

    enquiring = '\n'.join(opt(v) for v in
                          ['Private client', 'Planner or agency', 'Venue or hotel', 'Other'])
    placeholder_sel = '' if enquiring_as_default else ' selected'

    return f'''
    <!-- Enquiry -->
    <section class="pe-section pe-section--mid" id="enquire">
      <div class="pe-rail">
        <p class="pe-rail-label" aria-hidden="true">Enquire</p>
        <div class="pe-body" data-fade>
          <h2>Enquire</h2>
          <p>{intro_html}</p>
          <p class="pe-caption">Fields marked * are required.</p>

          <form id="pe-enquiry" class="pe-form" method="post" action="https://api.web3forms.com/submit">
            <input type="hidden" name="access_key" value="{ACCESS_KEY}">
            <input type="hidden" name="subject" value="{subject}">
            <!-- No-JS fallback only: the plain HTML POST lands here and Web3Forms
                 redirects to the site thank-you page. The JS flow ignores it. -->
            <input type="hidden" name="redirect" value="{SITE}/thank-you.html">
            <input type="hidden" name="source_page" value="/{source_page}">
            <input type="hidden" name="utm_source" value="">
            <input type="hidden" name="utm_medium" value="">
            <input type="hidden" name="utm_campaign" value="">
            <input type="hidden" name="utm_term" value="">
            <input type="hidden" name="utm_content" value="">
            <input type="hidden" name="gclid" value="">
            <input type="hidden" name="time_on_page" value="">
            <input type="checkbox" name="botcheck" class="sr-only" tabindex="-1" aria-hidden="true" autocomplete="off">

            <div class="pe-field">
              <label for="pe-name">Your name <span aria-hidden="true">*</span></label>
              <input type="text" id="pe-name" name="name" autocomplete="name" required>
            </div>
            <div class="pe-field">
              <label for="pe-email">Email <span aria-hidden="true">*</span></label>
              <input type="email" id="pe-email" name="email" autocomplete="email" required>
            </div>
            <div class="pe-field">
              <label for="pe-phone">Telephone</label>
              <input type="tel" id="pe-phone" name="phone" autocomplete="tel">
            </div>
            <div class="pe-field">
              <label for="enquiring-as">Enquiring as <span aria-hidden="true">*</span></label>
              <select id="enquiring-as" name="enquiring-as" required>
                <option value=""{placeholder_sel}>Please choose</option>
{enquiring}
              </select>
            </div>
            <div class="pe-field pe-field--company" hidden>
              <label for="pe-company">Company or agency</label>
              <input type="text" id="pe-company" name="company" autocomplete="organization" disabled>
            </div>
            <div class="pe-field">
              <label for="event-date">Date of the event</label>
              <input type="date" id="event-date" name="event-date">
              <label class="pe-check-label">
                <input type="checkbox" id="date-flexible" name="date-flexible" value="yes">
                <span>The date is not yet fixed</span>
              </label>
            </div>
            <div class="pe-field">
              <label for="pe-venue">Venue and location <span aria-hidden="true">*</span></label>
              <input type="text" id="pe-venue" name="venue" required>
            </div>
            <div class="pe-field">
              <label for="pe-occasion">Occasion <span aria-hidden="true">*</span></label>
              <select id="pe-occasion" name="occasion" required>
                <option value="" selected>Please choose</option>
                <option>Wedding</option>
                <option>Memorial or funeral</option>
                <option>Private concert</option>
                <option>Corporate or civic</option>
                <option>Other</option>
              </select>
            </div>
            <div class="pe-field">
              <label for="ensemble-size">Ensemble size</label>
              <select id="ensemble-size" name="ensemble-size">
                <option value="eight-voices">Eight voices</option>
                <option value="twelve-voices">Twelve voices</option>
                <option value="sixteen-voices">Sixteen voices</option>
                <option value="twenty-four-voices">Twenty-four voices</option>
                <option value="guidance-welcome" selected>Guidance welcome</option>
              </select>
            </div>
            <div class="pe-field">
              <label for="pe-budget">Indicative budget for music (pounds sterling)</label>
              <select id="pe-budget" name="budget">
                <option value="" selected>Please choose</option>
                <option>Under &pound;5,000</option>
                <option>&pound;5,000&ndash;&pound;10,000</option>
                <option>&pound;10,000&ndash;&pound;25,000</option>
                <option>&pound;25,000&ndash;&pound;50,000</option>
                <option>&pound;50,000+</option>
                <option>Prefer to discuss</option>
              </select>
            </div>
            <div class="pe-field">
              <label for="pe-message">About the occasion</label>
              <textarea id="pe-message" name="message" rows="5"></textarea>
            </div>
            <div class="pe-field">
              <label for="hear">How did you hear of us?</label>
              <select id="hear" name="hear">
                <option value="" selected>Please choose</option>
                <option>Referred by a planner</option>
                <option>Referred by a venue</option>
                <option>Recommended by a past client</option>
                <option>Search</option>
                <option>Press or social media</option>
                <option>Other</option>
              </select>
            </div>
            <div class="pe-field pe-field--hear-detail" hidden>
              <label for="hear-detail">Who referred you?</label>
              <input type="text" id="hear-detail" name="hear-detail" disabled>
            </div>

            <div class="h-captcha" data-captcha="true"></div>
            <p class="pe-form-error pe-captcha-error" id="captcha-error" data-visible="false" role="alert">Please tick the box above to confirm you&rsquo;re not a robot, then send again.</p>

            <div class="pe-form-error" data-visible="false" role="alert">
              <p data-error-msg="incomplete" hidden>Please check the highlighted fields, then send again.</p>
              <p data-error-msg="timing" hidden>Please take a moment over the form, then press Send enquiry again.</p>
              <p data-error-msg="network">We could not send your enquiry. Email <a href="mailto:office@londonchoralservice.com">office@londonchoralservice.com</a> or call <a href="tel:+447356042468">+44 7356 042468</a> and we will take it from there.</p>
            </div>

            <button type="submit" class="pe-btn">Send enquiry</button>
          </form>

          <div id="pe-form-success" role="status" tabindex="-1" hidden>
            <p>Thank you. Luca Wetherall will reply personally within one working day.</p>
          </div>
        </div>
      </div>
    </section>
'''


FOOT = '''
  <!-- @include-start partials/private-footer.html -->
  <!-- @include-end partials/private-footer.html -->

  <script src="https://web3forms.com/client/script.js" async defer></script>
  <script src="/js/private-events.js" defer></script>
</body>
</html>
'''


def page(title, description, path, jsonld, crumbs, body, source_page=None,
         subject=None, enquiring_as_default=None, form_intro=None):
    return (head(title, description, path)
            + head_close(jsonld)
            + header(crumbs)
            + '\n  <main>\n'
            + body
            + enquiry_form(source_page or path,
                           subject or 'Private events enquiry — Alma Consort / LCS',
                           enquiring_as_default, form_intro)
            + '\n  </main>\n'
            + FOOT)
