// Popup script. Runs when the user clicks the extension icon. Pulls the
// stored verdict for the active tab and renders it. Also wires the "Re-scan"
// link, which sends a message to the service worker to redo the scan.
//
// Loaded as a classic script after the polyfill and helpers via popup.html,
// so `browser.*` and `globalThis.PG.*` are both available.

(function () {
  const PG = globalThis.PG;

  const VERDICT_ICONS = {
    safe:    '✓',
    caution: '!',
    danger:  '⚠',
    error:   '?',
  };

  const $ = (id) => document.getElementById(id);

  function show(stateId) {
    ['loading', 'verdict-card', 'empty'].forEach((id) => {
      $(id).classList.toggle('hidden', id !== stateId);
    });
  }

  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function renderVerdict(verdict) {
    const v = verdict.verdict ?? 'error';

    $('verdict-icon').textContent = VERDICT_ICONS[v] ?? '?';
    $('verdict-icon').className = `verdict-icon ${v}`;

    $('verdict-label').textContent = v;
    $('verdict-label').className = `verdict-label ${v}`;

    $('verdict-score').textContent =
      v === 'error' ? 'Scan unavailable' : `Risk score: ${verdict.risk_score} / 100`;

    $('verdict-url').textContent = verdict.url ?? '';
    $('verdict-summary').textContent = verdict.summary ?? '';

    const list = $('signals-list');
    list.innerHTML = '';
    const signals = Array.isArray(verdict.signals) ? verdict.signals : [];

    if (signals.length === 0) {
      $('signals-section').classList.add('hidden');
    } else {
      $('signals-section').classList.remove('hidden');
      signals.forEach((s) => {
        const li = document.createElement('li');
        if (s.triggered) li.classList.add('triggered');
        const score = s.triggered ? ` (+${s.score_contribution})` : '';
        li.innerHTML = `
          <div class="signal-name">${escapeHtml(s.name)}${score}</div>
          <div class="signal-explanation">${escapeHtml(s.explanation)}</div>
        `;
        list.appendChild(li);
      });
    }

    show('verdict-card');
  }

  async function getActiveTab() {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    return tab;
  }

  function isScannable(urlString) {
    if (!urlString) return false;
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

  async function loadCurrentVerdict() {
    show('loading');
    const tab = await getActiveTab();
    if (!tab) { show('empty'); return; }

    // Browser-internal pages can't be scanned — show the empty state instead
    // of a misleading "Error" verdict
    if (!isScannable(tab.url)) {
      $('empty').innerHTML = `
        <p class="muted">PhishGuard doesn't scan browser-internal pages.</p>
        <p class="muted small">Visit a regular website (https://...) to see verdicts.</p>
      `;
      show('empty');
      return;
    }

    const verdict = await PG.getTabVerdict(tab.id);
    if (!verdict) { show('empty'); return; }
    renderVerdict(verdict);
  }

  async function manualRescan(e) {
    e.preventDefault();

    const tab = await getActiveTab();
    if (!tab?.url || !isScannable(tab.url)) {
      // Don't even try — would just produce a confusing error
      return;
    }

    show('loading');
    try {
      const verdict = await PG.scanURL({ url: tab.url });
      renderVerdict(verdict);
    } catch (err) {
      renderVerdict({
        verdict: 'error',
        url: tab.url,
        risk_score: 0,
        summary: `Scan failed: ${err.message}. Is the backend running on ${PG.CONFIG.API_BASE_URL}?`,
        signals: [],
      });
    }
  }

  document.addEventListener('DOMContentLoaded', loadCurrentVerdict);
  document.getElementById('rescan').addEventListener('click', manualRescan);
})();
