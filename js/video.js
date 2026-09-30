(function () {
  'use strict';

  // ── Click-to-play films ──
  // A .video-thumb button (data-video = YouTube id) is swapped for the
  // youtube-nocookie player only when pressed. YouTube's own overlay stays
  // out of sight:
  //  - the player runs without controls, and a .video-shield button lies
  //    over it, so YouTube never sees the mouse and shows no hover UI;
  //  - the player (.video-frame) is taller than the 16:9 frame, which clips
  //    it, so the title bar at its top and the logo and "Watch on YouTube"
  //    bar at its bottom fall outside the frame (see components.css);
  //  - the shield shows the thumbnail until the film is playing, covering
  //    YouTube's loading screen, and again whenever it is paused, covering
  //    the pause screen. At the end the original button returns.
  //  - YouTube draws a small pause icon in the middle of the picture for a
  //    few seconds whenever playback starts other than by an immediate muted
  //    autoplay, so the film autoplays muted and is unmuted on its first
  //    frame. After a resume or a slow start the icon can still show
  //    briefly: the film is shown straight away rather than held behind the
  //    thumbnail (owner's choice, 30 Sep 2026).
  //    iPhones and iPads start unmuted instead, because iOS can refuse to
  //    unmute an embedded player, which would leave the film silent.
  // The shield pauses and resumes the film through the player's postMessage
  // API; double-click goes full screen.
  //
  // If the browser blocks autoplay (some phones do, with sound on), the
  // shield steps aside after a few seconds so the visitor can start the
  // film with YouTube's own play button, and returns once it plays.
  var ORIGIN = 'https://www.youtube-nocookie.com';
  var ENDED = 0, PLAYING = 1, PAUSED = 2;
  var AUTOPLAY_WAIT = 5000;
  var IOS = /iP(hone|ad|od)/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var players = [];

  function post(iframe, msg) {
    if (iframe.contentWindow) iframe.contentWindow.postMessage(JSON.stringify(msg), ORIGIN);
  }

  function send(iframe, func) {
    post(iframe, { event: 'command', func: func, args: [] });
  }

  function playFilm(btn, id, label, titleSuffix) {
    var wrap = btn.parentNode;
    var name = label ? label.charAt(0).toUpperCase() + label.slice(1) : '';
    var thumb = btn.querySelector('img');

    var iframe = document.createElement('iframe');
    iframe.className = 'video-frame';
    iframe.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(id) +
      '?autoplay=1&rel=0&controls=0&playsinline=1&iv_load_policy=3&disablekb=1&enablejsapi=1' +
      (IOS ? '' : '&mute=1') +
      '&origin=' + encodeURIComponent(location.origin);
    iframe.title = name ? name + ' — ' + titleSuffix : titleSuffix;
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen';
    iframe.allowFullscreen = true;
    iframe.style.border = '0';

    var shield = document.createElement('button');
    shield.type = 'button';
    shield.className = 'video-shield is-loading';
    if (thumb) {
      var poster = thumb.cloneNode();
      poster.removeAttribute('fetchpriority');
      poster.removeAttribute('loading');
      poster.alt = '';
      shield.appendChild(poster);
    }
    var icon = btn.querySelector('.play-btn');
    if (icon) shield.appendChild(icon.cloneNode(true));

    // state: the player's last reported state (null until it reports).
    var player = { iframe: iframe, shield: shield, state: null, heard: false, started: false };
    players.push(player);

    function setLabel() {
      shield.setAttribute('aria-label', (player.state === PLAYING ? 'Pause ' : 'Play ') + (name || 'film'));
    }

    function cover(paused) {
      shield.classList.toggle('is-paused', paused);
      shield.classList.toggle('is-loading', !paused);
    }

    function finish() {
      clearTimeout(player.autoplayTimer);
      clearInterval(player.listenTimer);
      clearInterval(player.kickTimer);
      players.splice(players.indexOf(player), 1);
    }

    player.onState = function (state) {
      player.state = state;
      if (state === PLAYING) {
        if (!shield.parentNode) {
          // Back after autoplay was blocked and YouTube's button was pressed.
          var hadFocus = document.activeElement === iframe;
          wrap.appendChild(shield);
          if (hadFocus) shield.focus({ preventScroll: true });
        }
        shield.classList.remove('is-paused', 'is-loading');
        if (!player.started) {
          player.started = true;
          if (!IOS) send(iframe, 'unMute');
        }
      } else if (state === PAUSED) {
        cover(true);
      } else if (state === ENDED) {
        var hadShieldFocus = document.activeElement === shield;
        finish();
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
      if (!player.started) {
        send(iframe, 'playVideo');
        return;
      }
      if (player.state === PLAYING) {
        send(iframe, 'pauseVideo');
        player.state = PAUSED;
        cover(true);
      } else {
        send(iframe, 'playVideo');
        player.state = PLAYING;
        shield.classList.remove('is-paused', 'is-loading');
      }
      setLabel();
    });
    shield.addEventListener('dblclick', function () {
      var fs = wrap.requestFullscreen || wrap.webkitRequestFullscreen;
      if (fs) fs.call(wrap);
    });

    // Ask the player for state events, repeating until it answers: it only
    // hears the request once its own script has started.
    iframe.addEventListener('load', function () {
      var tries = 0;
      clearInterval(player.listenTimer);
      player.listenTimer = setInterval(function () {
        if (player.heard || ++tries > 40) return clearInterval(player.listenTimer);
        post(iframe, { event: 'listening', id: players.indexOf(player), channel: 'widget' });
      }, 250);
    });

    // The player sometimes loads without starting. Muted play is always
    // allowed, so nudge it until it starts.
    player.kickTimer = setInterval(function () {
      if (player.started || !shield.parentNode) return clearInterval(player.kickTimer);
      if (player.heard) send(iframe, 'playVideo');
    }, 750);

    // Autoplay blocked: step aside so YouTube's play button can be pressed.
    player.autoplayTimer = setTimeout(function () {
      if (!player.started && shield.parentNode) {
        var hadFocus = document.activeElement === shield;
        shield.parentNode.removeChild(shield);
        if (hadFocus) iframe.focus({ preventScroll: true });
      }
    }, AUTOPLAY_WAIT);

    wrap.innerHTML = '';
    wrap.appendChild(iframe);
    wrap.appendChild(shield);
    setLabel();
    // The focused button is gone: keep keyboard users on the film rather than
    // dropping them back to the top of the page.
    shield.focus({ preventScroll: true });
  }

  window.addEventListener('message', function (e) {
    if (e.origin !== ORIGIN || typeof e.data !== 'string') return;
    var data;
    try { data = JSON.parse(e.data); } catch (err) { return; }
    var state = data.event === 'onStateChange' ? data.info
      : (data.event === 'infoDelivery' && data.info ? data.info.playerState : undefined);
    for (var i = 0; i < players.length; i++) {
      if (players[i].iframe.contentWindow === e.source) {
        players[i].heard = true;
        if (typeof state === 'number' && players[i].state !== state) players[i].onState(state);
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
