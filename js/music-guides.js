(function () {
  'use strict';

  var VALID = ['weddings', 'funerals', 'christmas', 'booking'];

  function getCategoryFromURL() {
    var params = new URLSearchParams(window.location.search);
    var cat = params.get('category');
    if (cat && VALID.indexOf(cat) !== -1) return cat;
    return 'all';
  }

  var status = null;
  var LABELS = { all: 'all guides', weddings: 'wedding guides', funerals: 'funeral guides', christmas: 'Christmas guides', booking: 'booking guides' };

  // Screen readers get no cue that the list changed when a chip filters it.
  function announce(category) {
    if (!status) {
      status = document.createElement('p');
      status.className = 'sr-only';
      status.setAttribute('role', 'status');
      status.setAttribute('aria-live', 'polite');
      document.body.appendChild(status);
    }
    status.textContent = 'Showing ' + (LABELS[category] || 'all guides');
  }

  function applyFilter(category, announceIt) {
    if (announceIt) announce(category);
    var sections = document.querySelectorAll('.guide-category-section[data-category]');
    sections.forEach(function (section) {
      var sectionCat = section.getAttribute('data-category');
      if (category === 'all' || sectionCat === category) {
        section.removeAttribute('hidden');
      } else {
        section.setAttribute('hidden', '');
      }
    });

    var chips = document.querySelectorAll('.filter-chip[data-category]');
    chips.forEach(function (chip) {
      var chipCat = chip.getAttribute('data-category');
      // Chips are links to filtered URLs, so mark the active one as the
      // current page (aria-pressed is not valid on links).
      if (chipCat === category) chip.setAttribute('aria-current', 'page');
      else chip.removeAttribute('aria-current');
    });
  }

  function onChipClick(e) {
    // Let modified clicks (new tab/window) follow the link as normal.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    var chip = e.currentTarget;
    var category = chip.getAttribute('data-category');
    if (category === getCategoryFromURL()) return;
    var newURL;
    if (category === 'all') {
      newURL = window.location.pathname;
    } else {
      newURL = window.location.pathname + '?category=' + category;
    }
    history.pushState({ category: category }, '', newURL);
    applyFilter(category, true);
  }

  function onPopState() {
    applyFilter(getCategoryFromURL(), true);
  }

  function init() {
    var chips = document.querySelectorAll('.filter-chip[data-category]');
    if (chips.length === 0) return;
    chips.forEach(function (chip) {
      chip.addEventListener('click', onChipClick);
    });
    window.addEventListener('popstate', onPopState);
    applyFilter(getCategoryFromURL());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
