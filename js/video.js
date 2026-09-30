(function () {
  'use strict';

  // ── Click-to-play films ──
  // A .video-thumb button (data-video = YouTube id) is swapped for the
  // youtube-nocookie player only when pressed. The player runs without
  // YouTube's controls, and once it is playing a transparent .video-shield
  // button covers it, so YouTube's title bar, channel badge and hover
  // controls never show. The shield pauses and resumes the film (through
  // the player's postMessage API); while paused it shows the thumbnail
  // again, which also hides YouTube's pause screen. Double-click goes full
  // screen. At the end the original thumbnail button comes back.
  //
  // If the browser blocks autoplay (some phones do, with sound on), the
  // shield is not added until the film first plays, so the visitor can
  // start it with YouTube's own play button.
  var ORIGIN = 'https://www.youtube-nocookie.com';
  var PLAYING = 1, PAUSED = 2, ENDED = 0;
  var players = [];

  function send(iframe, func) {
    if (iframe.contentWindow) {
      iframe.contentWindow.postMessage(JSON.stringify({ event: 'command', func: func, args: [] }), ORIGIN);
    }
  }

  function playFilm(btn, id, label, titleSuffix) {
    var wrap = btn.parentNode;
    var name = label ? label.charAt(0).toUpperCase() + label.slice(1) : '';
    var thumb = btn.querySelector('img');

    var iframe = document.createElement('iframe');
    iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
      '?autoplay=1&rel=0&controls=0&playsinline=1&iv_load_policy=3&enablejsapi=1' +
      '&origin=' + encodeURIComponent(location.origin);
    iframe.title = name ? name + ' — ' + titleSuffix : titleSuffix;
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.style.border = '0';

    var shield = document.createElement('button');
    shield.type = 'button';
    shield.className = 'video-shield';
    if (thumb) {
      var poster = thumb.cloneNode();
      poster.removeAttribute('fetchpriority');
      poster.alt = '';
      shield.appendChild(poster);
    }
    var icon = btn.querySelector('.play-btn');
    if (icon) shield.appendChild(icon.cloneNode(true));

    var player = { iframe: iframe, shield: shield, state: -1 };
    players.push(player);

    function setLabel() {
      shield.setAttribute('aria-label', (player.state === PLAYING ? 'Pause ' : 'Play ') + (name || 'film'));
    }

    player.onState = function (state) {
      player.state = state;
      if (state === PLAYING) {
        if (!shield.parentNode) {
          var hadFocus = document.activeElement === iframe;
          wrap.appendChild(shield);
          if (hadFocus) shield.focus({ preventScroll: true });
        }
        shield.classList.remove('is-paused');
      } else if (state === PAUSED) {
        shield.classList.add('is-paused');
      } else if (state === ENDED) {
        var hadShieldFocus = document.activeElement === shield;
        players.splice(players.indexOf(player), 1);
        wrap.innerHTML = '';
        wrap.appendChild(btn);
        if (hadShieldFocus) btn.focus({ preventScroll: true });
        return;
      }
      setLabel();
    };

    // Show the new state straight away rather than waiting for the player to
    // report it, so a quick second press toggles back instead of repeating.
    shield.addEventListener('click', function () {
      var pause = player.state === PLAYING;
      send(iframe, pause ? 'pauseVideo' : 'playVideo');
      player.onState(pause ? PAUSED : PLAYING);
    });
    shield.addEventListener('dblclick', function () {
      send(iframe, 'playVideo');
      var fs = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
      if (fs) fs.call(wrap);
    });

    // Ask the player for state events once it has loaded.
    iframe.addEventListener('load', function () {
      if (iframe.contentWindow) {
        iframe.contentWindow.postMessage(JSON.stringify({ event: 'listening', id: players.indexOf(player), channel: 'widget' }), ORIGIN);
      }
    });

    wrap.innerHTML = '';
    wrap.appendChild(iframe);
    // The focused button is gone: keep keyboard users on the film rather than
    // dropping them back to the top of the page.
    iframe.focus({ preventScroll: true });
  }

  window.addEventListener('message', function (e) {
    if (e.origin !== ORIGIN || typeof e.data !== 'string') return;
    var data;
    try { data = JSON.parse(e.data); } catch (err) { return; }
    var state = data.event === 'onStateChange' ? data.info
      : (data.event === 'infoDelivery' && data.info ? data.info.playerState : undefined);
    if (typeof state !== 'number') return;
    for (var i = 0; i < players.length; i++) {
      if (players[i].iframe.contentWindow === e.source) {
        if (players[i].state !== state) players[i].onState(state);
        return;
      }
    }
  });

  // Also used by js/private-events.js for the buttons it builds.
  window.lcsPlayFilm = playFilm;

  document.querySelectorAll('.video-thumb[data-video]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var label = (btn.getAttribute('aria-label') || '').replace(/^Play /, '');
      playFilm(btn, btn.getAttribute('data-video'), label, 'The London Choral Service');
    });
  });
})();
