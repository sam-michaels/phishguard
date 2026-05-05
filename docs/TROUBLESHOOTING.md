# Troubleshooting

## "Failed to fetch" / "NetworkError" in the popup

The extension can't reach the backend. Diagnose in this order.

### 1. Is the backend actually running?

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","redis":true}`. If this fails, your backend is
down — `docker compose up` from the project root.

If you see `redis: false`, scans still work but will be slow on repeat hits.
Restart with `docker compose down && docker compose up`.

### 2. Watch the backend logs

With logging enabled (it is, by default), you'll see every request hit:

```
INFO:phishguard:POST /api/v1/scan/url  origin=moz-extension://abc-123-...
INFO:phishguard:  → 200
```

If you DON'T see the request hitting the backend at all when you reload a page
in the browser, the request is being blocked client-side. Go to step 3.

If you see the request but with `→ 400` or `→ 4xx`, it's a CORS preflight or
schema issue. Look at the full error in the browser console.

### 3. Check the browser console for the real error

**Chrome:** `chrome://extensions/` → PhishGuard → "service worker" link →
Console tab. Reload a tab to trigger a scan. Look for red error messages.

**Firefox:** `about:debugging#/runtime/this-firefox` → PhishGuard → Inspect.
Reload a tab. Console tab.

Common errors and what they mean:

| Error message | Cause | Fix |
|---------------|-------|-----|
| `Cross-Origin Request Blocked` | CORS regex doesn't match origin | Check `cors_origin_regex` in `backend/app/config.py` against the origin shown in the browser console |
| `NetworkError when attempting to fetch resource` | Backend unreachable OR mixed-content blocking | Step 1; if backend is up, see "Mixed content" below |
| `405 Method Not Allowed` on OPTIONS | Backend not handling CORS preflight | Restart backend — middleware should handle this |
| `Loading mixed (insecure) display content blocked` | HTTPS page → HTTP backend blocked by browser | Use HTTPS backend OR add localhost exemption (see below) |

### 4. Mixed-content blocking (Firefox especially)

When you're browsing an HTTPS site and the extension calls a plain HTTP
backend, browsers may block the request as "mixed content."

**Chrome usually allows `http://localhost`** as a special exception.
**Firefox is stricter.** If you see this error:

**Workaround for development:** point the extension at `http://127.0.0.1:8000`
in `extension/src/config.js` instead of `localhost` — Firefox treats raw IPs
as "potentially trustworthy" and exempts them from mixed-content blocking.

```js
// In src/config.js
API_BASE_URL: 'http://127.0.0.1:8000',
```

Rebuild: `python3 build.py both` and reload the extension in both browsers.

**Long-term fix:** when you deploy the backend (Railway, Render, AWS), it'll
have HTTPS by default and this disappears entirely. This is purely a local
development annoyance.

### 5. Extension permission was denied

In Firefox MV3, `host_permissions` are not auto-granted — the user must
approve them per-site or globally. If you skipped this on first install:

1. Click the puzzle-piece icon in the Firefox toolbar
2. Click the gear next to PhishGuard → Manage Extension
3. Permissions tab → enable "Access your data for all websites"

Chrome usually grants `<all_urls>` on install but check
`chrome://extensions/` → PhishGuard → Details → Site access if scans aren't
firing.

## "Error" verdict on `chrome://newtab/` or similar

This is by design — extensions cannot scan browser-internal pages
(`chrome://`, `about:`, `edge://`, `view-source:`). The popup shows a friendly
message instead of attempting a doomed scan. Visit a regular HTTPS site to
test.

## Verdict doesn't update after a code change

Redis is caching old verdicts. Flush:

```bash
docker compose exec redis redis-cli FLUSHALL
```

Then reload the page.

## Extension service worker keeps "going to sleep"

This is normal MV3 behavior — Chrome aggressively reaps idle service workers.
The extension is designed to handle this (state lives in `browser.storage`,
not module variables). If you're inspecting the service worker for debugging
and it disappears, just trigger any extension event (reload a tab, click the
icon) and it'll respawn.

## Scans are slow (3-5+ seconds)

Most likely cause: the WHOIS lookup. Some TLDs respond slowly. Less likely:
VirusTotal API hitting rate limits (free tier = 4 req/min).

To verify: open the popup signal list and look at which signals took longest.
If one signal is dominating latency, you can disable it temporarily by
returning early in its module — useful for development, not for production.
