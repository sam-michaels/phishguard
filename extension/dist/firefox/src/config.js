// Single source of truth for the extension. All other modules read from
// the global `PG` namespace populated below. We avoid ES modules because
// Firefox MV3 background scripts don't support them yet — using a shared
// global keeps the same source working in both browsers.

(function () {
  const PG = (globalThis.PG = globalThis.PG || {});

  PG.CONFIG = {
    // Backend URL — change to your deployed URL when you ship beyond localhost
    API_BASE_URL: 'http://localhost:8000',

    // Endpoints
    SCAN_ENDPOINT: '/api/v1/scan/url',

    // Skip scanning these schemes/hosts entirely. Hitting our API for them is
    // wasteful and meaningless.
    SKIP_SCHEMES: ['chrome:', 'chrome-extension:', 'moz-extension:', 'about:', 'edge:', 'file:', 'view-source:'],
    SKIP_HOSTS: ['localhost', '127.0.0.1'],

    // Notification behavior
    NOTIFY_ON: ['caution', 'danger'],
  };

  // Badge colors per verdict — also used for popup styling
  PG.VERDICT_COLORS = {
    safe:    '#16a34a',
    caution: '#eab308',
    danger:  '#dc2626',
    scanning:'#6b7280',
    error:   '#9333ea',
  };

  // Short labels for the badge — Chrome only renders ~4 chars
  PG.VERDICT_BADGE_TEXT = {
    safe:    '',
    caution: '!',
    danger:  '⚠',
    scanning:'…',
    error:   '?',
  };
})();
