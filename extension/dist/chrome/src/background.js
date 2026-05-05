// MV3 background script — works as a service worker (Chrome) or event page (Firefox).
//
// Lifecycle reality check: Chrome can kill the worker at any time when idle and
// respawn it on the next event. Anything it needs to remember between
// invocations MUST live in browser.storage, not in module-level variables.
//
// Cross-browser loading:
// - Firefox loads scripts in array order via manifest's background.scripts:
//     [vendor/browser-polyfill.min.js, src/background.js]
//   So the polyfill and our helper modules are NOT auto-loaded — we use
//   importScripts() (works in both Chrome service workers AND Firefox event pages)
//   to pull them in here.
// - Chrome's MV3 service worker only loads background.js by default;
//   importScripts() works in service worker context to load the rest.

// Cross-browser helper loading:
// - Chrome MV3 service worker: importScripts() loads polyfill + helpers
// - Firefox MV3 event page: manifest's background.scripts array loads everything
//   in order, so importScripts is unavailable AND unneeded
if (typeof importScripts === 'function') {
  importScripts(
    '../vendor/browser-polyfill.min.js',
    'config.js',
    'api.js',
    'storage.js',
    'badge.js',
    'notify.js'
  );
}

const PG = globalThis.PG;

// --- Helpers --------------------------------------------------------------

function isScannable(urlString) {
  let parsed;
  try {
    parsed = new URL(urlString);
  } catch {
    return false;
  }
  if (PG.CONFIG.SKIP_SCHEMES.includes(parsed.protocol)) return false;
  if (PG.CONFIG.SKIP_HOSTS.includes(parsed.hostname)) return false;
  return true;
}

// --- Core scan dispatcher -------------------------------------------------

async function performScan(tabId, url, contentSignals = {}) {
  if (!isScannable(url)) {
    await PG.clearBadge(tabId);
    await PG.clearTabVerdict(tabId);
    return;
  }

  await PG.setBadge(tabId, 'scanning');

  try {
    const verdict = await PG.scanURL({
      url,
      pageTitle: contentSignals.pageTitle,
      formFields: contentSignals.formFields,
    });

    await PG.setTabVerdict(tabId, verdict);
    await PG.setBadge(tabId, verdict.verdict);
    await PG.notifyVerdict(verdict, url);

    console.log(
      `[PhishGuard] ${verdict.verdict.toUpperCase()} (${verdict.risk_score}/100) — ${url}`
    );
  } catch (err) {
    console.error('[PhishGuard] Scan failed:', err.message, url);
    await PG.setBadge(tabId, 'error');
    await PG.setTabVerdict(tabId, {
      verdict: 'error',
      risk_score: 0,
      summary: `Scan failed: ${err.message}. Is the backend running on ${PG.CONFIG.API_BASE_URL}?`,
      signals: [],
      url,
    });
  }
}

// --- Event wiring ---------------------------------------------------------

// Top-frame navigations only — ignore iframes (frameId !== 0).
browser.webNavigation.onCommitted.addListener(async (details) => {
  if (details.frameId !== 0) return;
  await performScan(details.tabId, details.url);
});

// Content script reports back with page metadata after DOM is ready.
browser.runtime.onMessage.addListener((msg, sender) => {
  if (msg?.type !== 'PAGE_CONTEXT' || !sender.tab) return;
  performScan(sender.tab.id, sender.tab.url, {
    pageTitle: msg.pageTitle,
    formFields: msg.formFields,
  });
  return Promise.resolve({ ok: true });
});

// Clean up storage when tabs close
browser.tabs.onRemoved.addListener(async (tabId) => {
  await PG.clearTabVerdict(tabId);
});

browser.runtime.onInstalled.addListener(() => {
  console.log('[PhishGuard] Background script installed.');
});
