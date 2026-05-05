# Phase 2 — Cross-Browser Extension (Chrome + Firefox)

## Goal

A WebExtension that auto-scans every page you visit and notifies you only on
`caution`/`danger` verdicts. Works identically in Chrome and Firefox via the
Mozilla `webextension-polyfill`.

## How to load it

The backend must be running first (`docker compose up` from project root).

### Build

```bash
cd extension
python3 build.py both
```

This produces:

- `extension/dist/chrome/` — load in Chrome
- `extension/dist/firefox/` — load in Firefox
- `extension/dist/phishguard-chrome.zip` — for Chrome Web Store submission
- `extension/dist/phishguard-firefox.zip` — for Firefox AMO submission

### Load in Chrome

1. Open `chrome://extensions/`
2. Toggle **Developer mode** on (top-right)
3. Click **Load unpacked** → select `extension/dist/chrome/`
4. Pin the shield icon from the puzzle-piece menu

### Load in Firefox

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…**
3. Select `extension/dist/firefox/manifest.json` (the file, not the folder)
4. Pin the shield icon to the toolbar (right-click → Pin to Toolbar)

> **Note on Firefox temporary add-ons:** they're removed when Firefox closes.
> For permanent local installation use `web-ext run` (see below).

## Why two manifests

Chrome and Firefox both implement WebExtensions MV3 but with one meaningful
difference in the background script:

| Browser | Background type     | Manifest config                      |
| ------- | ------------------- | ------------------------------------ |
| Chrome  | Pure service worker | `"service_worker": "..."`            |
| Firefox | Event page          | `"scripts": [...]` (loaded in order) |

Maintaining two parallel manifests by hand is a bug-magnet. Instead, we keep
them in `manifests/manifest.{chrome,firefox}.json` and the build script picks
the right one. All actual _code_ is shared.

## Why the polyfill

Chrome's API namespace is `chrome.*` (callback-style by default).
Firefox's is `browser.*` (Promise-based by default).

The `webextension-polyfill` (Mozilla, ~10kb minified) provides a unified
`browser.*` namespace returning native Promises in both browsers. Every
source file uses `browser.*` and works identically. Without this polyfill
you'd need either dual code paths or to wrap every API call manually.

## Why the source files use IIFEs and a global `PG` namespace

We don't use ES modules. Three reasons:

1. **Firefox MV3 event pages don't support `"type": "module"`** for background
   scripts.
2. **Chrome MV3 service workers** support modules OR `importScripts()`, but
   not both. To share one code path with Firefox, we use classic scripts and
   `importScripts()` in the Chrome service worker.
3. **Popup pages** could use modules, but mixing module-style popups with
   classic-style background scripts would mean duplicating each helper.

So every helper file does:

```js
(function () {
  const PG = (globalThis.PG = globalThis.PG || {});
  PG.someFunction = ...;
})();
```

Each browser ends up with the same `globalThis.PG` populated, just loaded by
slightly different machinery — `importScripts` for Chrome SW, manifest
scripts array for Firefox event page, `<script>` tags for popup.

## File-by-file

| File                              | Purpose                                                    |
| --------------------------------- | ---------------------------------------------------------- |
| `manifests/manifest.chrome.json`  | Chrome MV3 manifest (service_worker)                       |
| `manifests/manifest.firefox.json` | Firefox MV3 manifest (scripts + gecko ID)                  |
| `vendor/browser-polyfill.min.js`  | Mozilla's WebExtension polyfill                            |
| `src/config.js`                   | Backend URL, skip lists, badge colors                      |
| `src/api.js`                      | `PG.scanURL()`                                             |
| `src/storage.js`                  | Per-tab verdict store                                      |
| `src/badge.js`                    | Sets icon badge color/text                                 |
| `src/notify.js`                   | Desktop notifications, caution+ only                       |
| `src/background.js`               | Service worker / event page entry point                    |
| `src/content.js`                  | Per-page DOM scraper                                       |
| `src/popup.html/css/js`           | UI shown on icon click                                     |
| `build.py`                        | Picks the correct manifest, bundles into `dist/{browser}/` |

## Permanent Firefox install (when ready)

Firefox's "Load Temporary Add-on" only lasts until you close the browser. For
permanent local install during development:

```bash
npm install --global web-ext
cd extension/dist/firefox
web-ext run            # launches Firefox with extension loaded
web-ext build          # creates an installable .zip
```

For distribution via Mozilla AMO (free, official):

1. Submit `dist/phishguard-firefox.zip` at https://addons.mozilla.org/developers/
2. Wait for review (usually 1–3 days for a small extension)
3. Once approved, users install with one click from AMO

## "Phase 2 is complete when..."

- [ ] `python3 build.py both` produces both `dist/` folders without error
- [ ] Extension loads in Chrome with no console errors
- [ ] Extension loads in Firefox with no console errors
- [ ] Visiting any normal site sets the badge in both browsers
- [ ] `http://192.168.1.1/login` triggers caution + notification in both
- [ ] Popup renders verdict correctly in both
- [ ] Backend logs show requests coming from both browsers

## Test URLs

| URL                        | Expected verdict | Why                                |
| -------------------------- | ---------------- | ---------------------------------- |
| `https://www.google.com/`  | safe             | Established, no triggers           |
| `https://github.com/`      | safe             | Same                               |
| `https://paypa1.com/login` | caution          | Typosquat (1 edit from paypal.com) |
| `http://192.168.1.1/login` | caution          | IP-as-host                         |
| `https://my-bank.tk/login` | caution          | Suspicious TLD                     |

If any of these don't match, flush Redis:
`docker compose exec redis redis-cli FLUSHALL` — earlier scans may be cached.

## Phase 3 preview

LLM content analysis. The data is already flowing — `content.js` sends
`page_title` and `form_fields`, the schema accepts them, the orchestrator
already passes them through. Phase 3 adds a new signal module that calls
Claude/GPT with the page metadata, grounded by RAG over your existing
ChromaDB corpus.
