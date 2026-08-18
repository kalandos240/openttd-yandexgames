# OpenTTD — Playgama publication and integration notes

This document describes the current **Playgama v10** package for the OpenTTD 15.3 WebAssembly browser port.

## Package profile

- Engine: **Plain JS / WebAssembly** (Emscripten runtime)
- SDK: **Playgama Bridge JS Core v2 stable**
- Supported devices: **Desktop**
- Orientation: **Landscape**
- Languages: **English, Russian**
- In-app purchases: **No**
- Leaderboards: **No**
- Multiplayer: **No** for this packaged browser edition
- Rewarded ads: **Disabled**
- Banner ads: **Disabled**
- Interstitial ads: **Enabled**, requested only at safe pauses

The release root contains `index.html` and is validated below Playgama's 300 MB unpacked package ceiling.

## SDK mapping

The original browser shell uses a Yandex-style compatibility API. `playgama-yandex-compat.js` maps that interface onto Playgama Bridge v2 so the OpenTTD runtime does not need a broad platform rewrite:

- language -> Playgama platform locale;
- loading-ready -> Playgama game-ready message;
- gameplay start/stop -> Playgama lifecycle messages;
- fullscreen advertisement -> Playgama interstitial API;
- pause/resume -> Playgama pause-state events;
- platform mute -> Playgama audio-state events.

## Cloud saves — v10

`openttd-playgama-cloud-saves.js` provides the active cloud-save implementation.

### Local persistence

OpenTTD continues to use Emscripten **IDBFS / IndexedDB** for the browser-local profile, configuration and `.sav` files. Local persistence remains available even when platform cloud storage cannot be used.

### Platform storage

When supported and available, the port uses Playgama Bridge v2 **`platform_internal`** storage.

The active cloud path does **not** use the previous ~120 KB player-data limit. Instead:

- the newest `.sav` file is encoded and split into **64 KiB text chunks**;
- cloud data alternates between **slot A and slot B**;
- chunk data is written first and slot metadata is committed last;
- an interrupted upload therefore leaves the previous cloud generation recoverable;
- restored bytes are checked against the exact expected size and **CRC32**;
- a cloud save is restored only when it is newer than the newest local save;
- unchanged saves are not uploaded repeatedly;
- writes are serialized, debounced and throttled;
- legacy `openttdSaveV1` data is imported when no v2 slot exists;
- a **64 MiB per-save browser safety guard** prevents pathological memory usage. This is a client-side safety guard, not a claimed Playgama storage quota.

### Required QA save test

1. Start a game and create a manual OpenTTD save.
2. Wait for the local filesystem/cloud sync to complete.
3. Reload the QA build and confirm the save remains visible.
4. For a real cloud test, open the game on a different browser/device under the same platform user context and verify that the newer cloud save is restored.
5. Confirm that local saves still work when platform cloud storage is unavailable.

## Bundled AI and optional content

The package includes SimpleAI and required AI libraries. It also ships seven optional local add-on/base-graphics packages:

- Iron Horse 4
- FIRS Industries 5
- Road Hog
- GIST — German Industries Set
- Early Vehicle Set
- OpenGFX2 Settings
- OpenGFX2 Classic

NewGRFs remain **disabled by default** and are enabled by the player for a new game. FIRS and GIST are alternatives and should not be enabled together.

The distribution uses neutral `.bin` asset filenames for gzip-compressed add-on payloads to avoid CDN/content-encoding ambiguity. The manifest still verifies packaged and installed hashes.

## Playgama console text

### Game description

OpenTTD is an open-source transport management simulation game. Build and manage railways, roads, airports and shipping routes, transport passengers and cargo, develop an efficient transport company, and expand your network across a living world. This browser edition includes computer-controlled competitors and optional additional vehicle, industry and graphics content.

### How to play

Use the mouse to navigate menus, select tools and build your transport network. Create railway tracks, roads, stations, airports and docks, then purchase vehicles and assign routes to transport passengers and cargo. Earn money from successful deliveries, improve your infrastructure and expand into new cities and industries. You can zoom and move around the map with the mouse and use keyboard shortcuts for faster control. The goal is to build a profitable and efficient transport company and continue developing it over time.

## Publishing artwork

Exact-size images are stored in `assets/playgama/`:

- `cover-square-800x800.jpg`
- `cover-portrait-1080x1920.jpg`
- `cover-landscape-1920x1080.jpg`

## Certification notes

- Authorization: select **No** unless a platform-specific publication flow later requires it.
- Rewarded Ads: there is no rewarded-ad mechanic and the Bridge config disables rewarded ads.
- Interstitial Ads: requested only at safe pauses by the integration layer.
- Sensitive content: standard OpenTTD gameplay does not contain realistic violence, blood, gambling, sexual content or drug use.
- Scale: the native 16:9 game surface is centered on square/tall QA viewports without stretching the OpenTTD canvas.
- Add-ons: verify that the NewGRF menu lists the bundled optional NewGRFs; OpenGFX2 Classic is selected through the base-graphics setting rather than the NewGRF list.

## Licensing

OpenTTD is licensed under the **GNU General Public License version 2**. Bundled base sets, AI packages and optional add-ons retain their upstream licenses. The package includes a combined in-game license document plus source-code and third-party notices.

The Playgama-facing legal bundle is normalized so obsolete platform branding from earlier package stages is not exposed in `NOTICE.txt`, `SOURCE_CODE.txt` or `PLAYGAMA-ALL-LICENSES.md`.
