// The Refresh link and htmx swap errors. Same-origin requests only; no inline code.
//
// Refresh: POST /refresh first (it drops the app's ten-minute bank cache, so the page really re-reads Starling), then
// fire "cc-refresh" on the link, whose hx-get re-renders #main. Without htmx the link is a plain reload.
// A swap answered with an error (4xx or 5xx), or no answer at all, leaves the page as it was and says so in
// #cc-swap-error, which sits outside #main so a later swap never hides it.
(function () {
  "use strict";

  function box() { return document.getElementById("cc-swap-error"); }

  function say(text) {
    var b = box();
    if (!b) return;
    b.textContent = text;
    b.hidden = !text;
  }

  document.addEventListener("click", function (ev) {
    var link = ev.target && ev.target.closest ? ev.target.closest("a.cc-refresh") : null;
    if (!link || ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    if (!window.htmx) return;  // a plain reload
    ev.preventDefault();
    say("");
    fetch("/refresh", { method: "POST", credentials: "same-origin", cache: "no-store" }).then(function (res) {
      if (!res.ok) say("Couldn't clear the bank cache (the Mac answered " + res.status + "): the page may show the bank as it was.");
    }, function () {
      say("Couldn't reach the Mac: the page may show the bank as it was.");
    }).then(function () {
      window.htmx.trigger(link, "cc-refresh");
    });
  });

  document.addEventListener("htmx:responseError", function (ev) {
    var status = ev.detail && ev.detail.xhr ? ev.detail.xhr.status : "?";
    say("Couldn't refresh this page (the Mac answered " + status + "): what you see is from before.");
  });

  document.addEventListener("htmx:sendError", function () {
    say("Couldn't reach the Mac: what you see is from before.");
  });

  // The header nav scrolls sideways on medium widths: bring the current page's item into view, so a page far down
  // the list (Activity, say) isn't hidden past the edge.
  function showCurrent() {
    var nav = document.querySelector(".top .nav");
    var item = nav ? nav.querySelector('[aria-current="page"]') : null;
    if (!item || nav.scrollWidth <= nav.clientWidth) return;
    var n = nav.getBoundingClientRect(), r = item.getBoundingClientRect();
    nav.scrollLeft += (r.left + r.width / 2) - (n.left + n.width / 2);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", showCurrent);
  else showCurrent();
})();
