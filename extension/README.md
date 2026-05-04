# Extension (Phase 2)

Chrome WebExtension that calls the backend. Not yet built.

Planned files:
- `manifest.json` — permissions, MV3 service worker
- `background.js` — calls `POST /api/v1/scan/url` on navigation
- `content.js` — extracts page title, form fields, sends as scan payload
- `popup.html` / `popup.js` — extension button UI
- `badge.js` — sets icon color from verdict (`safe` → green, `caution` → yellow, `danger` → red)
