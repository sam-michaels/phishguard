// Updates the extension icon's badge based on verdict.

(function () {
  const PG = (globalThis.PG = globalThis.PG || {});

  PG.setBadge = async function (tabId, verdict) {
    const color = PG.VERDICT_COLORS[verdict] ?? PG.VERDICT_COLORS.error;
    const text  = PG.VERDICT_BADGE_TEXT[verdict] ?? '?';

    try {
      await browser.action.setBadgeBackgroundColor({ color, tabId });
      await browser.action.setBadgeText({ text, tabId });
    } catch (e) {
      // Tab may have been closed before the badge update lands — non-fatal
      console.debug('[PhishGuard] Badge update failed:', e.message);
    }
  };

  PG.clearBadge = async function (tabId) {
    try {
      await browser.action.setBadgeText({ text: '', tabId });
    } catch {
      // ignore
    }
  };
})();
