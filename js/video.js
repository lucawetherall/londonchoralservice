(function () {
  'use strict';

  // ── Click-to-play films ──
  // A .video-thumb button (data-video = YouTube id) is swapped for the
  // youtube-nocookie player only when pressed. The player is titled from the
  // button's aria-label ("Play Abide With Me" → "Abide With Me — The London
  // Choral Service"), and focus moves onto it: the focused button is removed,
  // so without this keyboard users would be dropped back to the top of the page.
  document.querySelectorAll('.video-thumb').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-video');
      var wrap = btn.closest('.video-embed') || btn.parentNode;
      var label = (btn.getAttribute('aria-label') || '').replace(/^Play /, '');
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) + '?autoplay=1&rel=0';
      iframe.title = label
        ? label.charAt(0).toUpperCase() + label.slice(1) + ' — The London Choral Service'
        : 'The London Choral Service';
      iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
      iframe.allowFullscreen = true;
      iframe.style.border = '0';
      wrap.innerHTML = '';
      wrap.appendChild(iframe);
      iframe.focus({ preventScroll: true });
    });
  });
})();
