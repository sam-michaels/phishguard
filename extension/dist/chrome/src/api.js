// Thin wrapper around the backend scan endpoint.

(function () {
  const PG = (globalThis.PG = globalThis.PG || {});
  const SCAN_TIMEOUT_MS = 8000;

  PG.scanURL = async function ({ url, pageTitle, formFields }) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), SCAN_TIMEOUT_MS);

    try {
      const response = await fetch(
        `${PG.CONFIG.API_BASE_URL}${PG.CONFIG.SCAN_ENDPOINT}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url,
            page_title: pageTitle ?? null,
            form_fields: formFields ?? [],
          }),
          signal: controller.signal,
        }
      );

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      return await response.json();
    } finally {
      clearTimeout(timeoutId);
    }
  };
})();
