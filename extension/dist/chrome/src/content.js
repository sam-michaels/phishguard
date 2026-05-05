// Runs in the context of every page (per the manifest's content_scripts entry).
// The webextension-polyfill is loaded right before this script in both
// Chrome and Firefox manifests, so `browser.*` is available identically.
//
// Job: extract signals about the page that the URL alone can't tell us, then
// hand them off to the background service worker.
//
// Critical constraint: content scripts CANNOT directly call our backend
// (CORS + extension-isolation rules). They communicate only via
// browser.runtime.sendMessage. The background worker does the network call.

(function () {
  function getFormFieldTypes() {
    const inputs = document.querySelectorAll('input');
    const types = new Set();
    inputs.forEach((el) => {
      // type="password" is the most important signal — credential collection
      if (el.type) types.add(el.type.toLowerCase());

      // autocomplete tells us about credit card / payment fields, useful for
      // Phase 4 buy-scanner without changing this code
      const ac = el.getAttribute('autocomplete');
      if (ac) types.add(`ac:${ac.toLowerCase()}`);
    });
    return Array.from(types);
  }

  function reportPageContext() {
    try {
      browser.runtime.sendMessage({
        type: 'PAGE_CONTEXT',
        pageTitle: document.title || null,
        formFields: getFormFieldTypes(),
        url: window.location.href,
      });
    } catch (e) {
      // sendMessage throws if the extension was reloaded mid-session.
      // Silently ignoring — next navigation will retry.
    }
  }

  reportPageContext();
})();
