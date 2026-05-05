// User-facing warning notifications. Per the product decision, these only
// fire on caution+ verdicts so we never interrupt the user on safe pages.

(function () {
  const PG = (globalThis.PG = globalThis.PG || {});

  PG.notifyVerdict = async function (verdict, url) {
    if (!PG.CONFIG.NOTIFY_ON.includes(verdict.verdict)) return;

    const titleByVerdict = {
      caution: '⚠️ PhishGuard: Caution',
      danger:  '🚨 PhishGuard: Danger',
    };

    try {
      await browser.notifications.create(`phishguard-${Date.now()}`, {
        type: 'basic',
        iconUrl: browser.runtime.getURL('icons/icon128.png'),
        title: titleByVerdict[verdict.verdict] ?? 'PhishGuard',
        message: `${truncate(url, 60)}\nRisk score: ${verdict.risk_score}/100\n${verdict.summary}`,
        priority: verdict.verdict === 'danger' ? 2 : 1,
      });
    } catch (e) {
      console.debug('[PhishGuard] Notification failed:', e.message);
    }
  };

  function truncate(s, n) {
    return s.length <= n ? s : s.slice(0, n - 1) + '…';
  }
})();
