// Per-tab verdict store. The popup and the badge both need to know "what was
// the verdict for the page in this tab?" — they ask through here.
//
// Uses browser.storage.session (in-memory, wiped when browser closes).
// `browser` is provided by the webextension-polyfill and works identically
// in Chrome and Firefox, returning native Promises.

(function () {
  const PG = (globalThis.PG = globalThis.PG || {});
  const STORAGE_KEY_PREFIX = 'verdict:';

  PG.setTabVerdict = async function (tabId, verdict) {
    await browser.storage.session.set({
      [STORAGE_KEY_PREFIX + tabId]: { ...verdict, cachedAt: Date.now() },
    });
  };

  PG.getTabVerdict = async function (tabId) {
    const key = STORAGE_KEY_PREFIX + tabId;
    const result = await browser.storage.session.get(key);
    return result[key] ?? null;
  };

  PG.clearTabVerdict = async function (tabId) {
    await browser.storage.session.remove(STORAGE_KEY_PREFIX + tabId);
  };
})();
