// Copy-to-clipboard handoff prompts for Claude Code Remote Control.
//
// There is no in-app chat: the server writes a fixed prompt into a button's data-prompt (or an <option>'s,
// for the ref/thread pickers) and this file only copies that text to the clipboard. Nothing is sent to the
// server and nothing runs — the owner pastes the prompt into Remote Control on his phone himself.
//
// No inline code (CSP is script-src 'self' only); no network calls at all.
(function () {
  "use strict";

  function fallbackBox(btn) {
    var box = btn.nextElementSibling;
    if (!box || !box.classList || !box.classList.contains("cc-copy-fallback")) {
      box = document.createElement("textarea");
      box.className = "cc-copy-fallback";
      box.setAttribute("readonly", "readonly");
      box.setAttribute("aria-label", "Prompt text: select and copy");
      btn.insertAdjacentElement("afterend", box);
    }
    return box;
  }

  function showFallback(btn, text) {
    var box = fallbackBox(btn);
    box.value = text;
    box.hidden = false;
    box.focus();
    box.select();
  }

  function label(btn, text, revertAfter) {
    var was = btn.dataset.label || btn.textContent;
    btn.dataset.label = was;
    btn.textContent = text;
    if (revertAfter) {
      window.setTimeout(function () { btn.textContent = was; }, revertAfter);
    }
  }

  function copy(btn, text) {
    if (!text) return;
    if (window.isSecureContext && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { label(btn, "Copied", 2000); },
        function () { showFallback(btn, text); label(btn, "Couldn't copy — select the text below", 4000); }
      );
    } else {
      showFallback(btn, text);
      label(btn, "Select and copy the text below", 4000);
    }
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".cc-copy");
    if (btn) {
      copy(btn, btn.dataset.prompt || "");
      return;
    }
    var picked = ev.target.closest(".cc-copy-select");
    if (picked) {
      var select = document.getElementById(picked.dataset.select || "");
      var option = select && select.options[select.selectedIndex];
      copy(picked, (option && option.dataset.prompt) || "");
    }
  });
})();
