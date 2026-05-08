(function () {
  'use strict';

  var VALID = ['weddings', 'funerals', 'christmas'];

  function getCategoryFromURL() {
    var params = new URLSearchParams(window.location.search);
    var cat = params.get('category');
    if (cat && VALID.indexOf(cat) !== -1) return cat;
    return 'all';
  }

  function applyFilter(category) {
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
      chip.setAttribute('aria-pressed', chipCat === category ? 'true' : 'false');
    });
  }

  function onChipClick(e) {
    e.preventDefault();
    var chip = e.currentTarget;
    var category = chip.getAttribute('data-category');
    var newURL;
    if (category === 'all') {
      newURL = window.location.pathname;
    } else {
      newURL = window.location.pathname + '?category=' + category;
    }
    history.pushState({ category: category }, '', newURL);
    applyFilter(category);
  }

  function onPopState() {
    applyFilter(getCategoryFromURL());
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
