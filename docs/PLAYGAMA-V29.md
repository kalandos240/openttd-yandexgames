# OpenTTD Playgama V7 — based on verified Yandex V29

This is **not** the old Playgama v10 runtime. The active release pipeline is
`.github/workflows/build-playgama-from-yandex-v29.yml`, running on branch
`port/playgama-v2-from-yandex-v29-storage-fix`.

## Immutable gameplay baseline

- Source: successful Yandex V29 action run [35286380038](https://github.com/kalandos240/openttd-yandexgames/actions/runs/35286380038).
- Source artifact ID: `10524282138` (expires 2026-12-16). Source commit:
  `646b534248c8984c5cac97fbdf5c63f14e5d09ed`.
- The action downloads that exact artifact, validates the original V29 QA
  report and verifies fullscreen, cursor, touch, localization, AI and shell
  gameplay files byte-for-byte with `cmp`. The large Emscripten JS runtime differs in the **two startup timeouts**
  and one profile-driven framebuffer upload throttle, all byte-exact
  checked against original V29 with `playgama/patch_v29_startup_timeout.py`
  and `playgama/patch_v29_frame_upload.py`. Native WASM and game simulation
  remain unchanged.
- Playgama packaging replaces the Yandex SDK bootstrap, adds the
  Bridge adapter/config/cloud-save module, and narrowly patches the ad policy,
  unsupported leaderboard response, two runtime startup timeouts, and a
  WebGL texture upload throttling guard.
  A missing original Yandex V29 artifact **fails the build** instead of
  substituting an older runtime.

## Playgama SDK mapping

SDK: `https://bridge.playgama.com/v2/stable/playgama-bridge.js`.
`playgama-bridge-config.json` lives next to `index.html`.
The compatibility adapter maps the V29 Yandex-style host API to Bridge:

| Existing browser-game action | Bridge v2 action |
| --- | --- |
| Locale | `bridge.platform.language` |
| Loading ready | `bridge.platform.sendMessage('game_ready')` |
| Gameplay start/stop | Bridge platform lifecycle messages |
| Interstitial | `bridge.advertisement.showInterstitial()` and state events |
| Host pause/mute | Bridge platform pause/audio state listeners |
| Player data | `bridge.storage.get([keys])` / `bridge.storage.set([keys], [values])` |
| Global rankings | Bridge leaderboards, **only on supported platforms** |
| Authorization | Bridge player authorize, **only when supported** |

### Storage safety

The bridge SDK uses **arrays** for storage get/set calls. The adapter restores
the object-shaped data expected by the Yandex V29 cloud-save integration,
preserves falsy values such as `0`, omits absent keys, and **propagates
failed reads/writes** instead of quietly returning an empty save or pretending
that a failed upload succeeded.

**V7 cloud save upgrade (experimental):** the new module is loaded
after `yandex-bridge.js` and replaces ONLY the Yandex
`yandexRestoreOpenTTDCloud`/`yandexBackupOpenTTDCloud` hooks.
It removes the previous 120,000-byte client upload ceiling by encoding the
**most recent** OpenTTD `.sav` into Base64 and splitting it into 64 KiB text
chunks. It keeps two independent metadata generations (slots A/B),
writes all chunks before their commit marker, validates size and CRC32 on
restore, and falls back to the previous valid slot if the latest is corrupt.
Writes are debounced and serialized; unchanged files/config are not uploaded
again. The module refuses to overwrite a newer cloud save from an older
local session, bounds malformed cloud metadata, and retries storage-capability
detection when a player authorizes cloud storage after startup.
A 64 MiB **client memory-safety ceiling** applies (not a Playgama quota).

Startup cloud restore is limited to a **6.5-second budget**. The original
Yandex V29 Emscripten startup would give up on cloud restore after 2.5 seconds,
which could allow a slow cloud response to write into the already-running
game. V5 changes that outer timeout to **8.5 seconds** and the native
filesystem/watchdog timeout from 8 to **30 seconds**. Both timeout edits plus the separately verified framebuffer-upload guard
are the ONLY compiled JS runtime differences from V29.
An expired 6.5-second cloud request does not restore local files after
gameplay has started; the game instead continues with local IDBFS progress. Existing V29
`openttdSaveV1`, `openttdConfigV1`, and `openttdMobileConfigV1`
records can be imported. Cloud synchronization is attempted only when
Playgama `platform_internal` storage is both supported and available.
Some portals require player authorization. Total cloud storage limits,
per-value limits, real account authorization and cross-device persistence
must be checked in hosted Playgama QA: passing local tests cannot prove
that a portal accepts arbitrary large saves. If the cloud quota rejects an
upload, the **local** save must remain intact and an error is logged.

Browser-local OpenTTD persistence is inherited from the V29 runtime. The
automated tests verify SDK API compatibility, **not** that a real Playgama
account has cloud-save capacity for every possible large `.sav` file. Check
large save files, reload and cross-device restores with the Playgama QA tool.

### Ads and ranking

Interstitial minimum/initial delays are both **180 seconds**. The Playgama V7
package removes the Yandex V29 timer that could interrupt active gameplay
after 180 seconds. Instead, after at least three minutes of active gameplay, the existing
`yandexGameSetGameplay(false)` path requests ads only when returning to
a menu or other natural game pause. The exact patch is mechanically verified
against the Yandex V29 source and dynamically tested in Node VM.
Pause/resume/audio restoration must
be verified during Playgama QA. Rewarded ads and in-game banners are disabled.
The adapter reports leaderboard methods as available only if the active
platform supports the relevant leaderboard type. The V7 shell displays an
offline status instead of attempting an unsupported leaderboard fetch. Playgama's native
`playgama` adapter does not provide ordinary `in_game` leaderboards by
default; optional SaaS leaderboards require separate configuration.

### Performance diagnosis (Firefox profile from 2026-10-11)

- Recorded game tab: about **8.7 seconds** at 1 ms sample interval;
  **6.41 seconds of CPU time** on the game main thread.
- Around **2.22 seconds of CPU time** is observed in
  `WebGLRenderingContext.texSubImage2D → memcpy`, caused by full framebuffer
  texture upload every browser refresh tick, even on high-refresh monitors.
- V6 alters only the JS framebuffer presenter: **upload no more than about
  30 frames per second** in steady state, without slowing native simulation
  and input ticks; redraw is forced immediately on canvas resize or a new
  WebGL context. This limits browser/GPU copying cost but has **not** yet
  been benchmarked on the end-user system after redeployment.
- Re-measure CPU/frame time with Firefox Profiler after installing V6.
  Verify panning, native UI animation and hover feel before publishing.

### Advertisements and debugging

- The interstitial API was **already integrated** through the Playgama Bridge;
  it was not disabled. V6 switches both SDK min/initial cooldown and native
  ad eligibility to **180 seconds**. An actual ad is **requested at the next
  user-driven logical pause/menu** after this threshold, *not during active
  simulation*, because Playgama's policies prohibit interrupting gameplay.
- The SDK reports its interstitial support in the console via
  `[Playgama/OpenTTD] Interstitial SDK:` on init.
- User's Firefox console reported failure to load
  `https://playgama.com/ads/v0.3.js?clid=playgama_ai`. The profile also
  lists the Adblock Plus extension. Try QA with a browser profile without
  adblocking before treating absent ads as a game integration error.
  Sandbox/test ad inventory may differ from production; real show
  callbacks cannot be guaranteed locally.
- On a rejected Bridge `showInterstitial()` Promise, V6 clears its
  ad-pause state instead of leaving the game frozen.

### First-launch robustness (V7)

The initial visit in a Playgama iframe can require fresh IndexedDB creation,
CDN fetches, and WASM startup; the original 14-second filesystem startup
watchdog sometimes released native startup too early in cold conditions.
V7 increases the **filesystem startup guard from 14 to 30 seconds**.
The cloud storage deadline remains at **6.5 seconds** and the native cloud
race at **8.5 seconds**, so platform storage cannot block startup for 30 seconds.

V7 also uses a local non-parser-blocking `playgama-bridge-loader.js`
instead of a parser-blocking external SDK `<script>`. The SDK is fetched
asynchronously; when it loads, the existing compatibility layer initializes
it. A failed CDN download no longer prevents the native game JS from being
parsed and started. Playgama services still require a functional CDN/Bridge.

An empty local filesystem and empty cloud storage are covered by a separate
regression test. This cannot prove the exact failure case from the user's
device has been eliminated; verify a **fresh private browser profile /
first Playgama QA launch**, then reload and exercise cloud saves and ads.

## Publication requirements and QA

- ZIP with `index.html` at the root, **under 300 MB unpacked**.
- The game must initialize Bridge v2 and send `game_ready` **after** startup.
- Desktop and mobile with landscape orientation. Verify that UI, controls and
  pointer/touch coordinates stay aligned on dynamic viewport changes and
  fullscreen exit. The player must be able to return from fullscreen.
- Russian and English game texts; language taken from Bridge when available.
- Ads via Playgama Bridge only, no separate analytics SDK, no forced external
  login. No blocking third-party navigation.
- Load and save a large existing game, reload, reload after an ad, and
  verify saves both with and without platform storage access.
- Verify separate desktop (mouse + keyboard) and mobile (touch) sessions,
  including the tutorial, vehicle purchases, map scrolling, settings and
  sound state across tab switches.

CI runs `node playgama/test-playgama-bridge-v2.cjs`,
`node playgama/test-v29-natural-break-ads.cjs`, and
`node playgama/test-v29-chunked-cloud.cjs` (large-save round trip,
failed write, corrupted slot, malformed metadata, old-format import, stale
offline saves, timed-out responses, authorization recovery, and local fallback).
The byte-exact native timeout patch and frame-upload patch are validated by Python; an executable JavaScript test confirms high-refresh uploads are capped and window resizes bypass the cap.
It creates `OpenTTD-v14-Playgama-Desktop-Mobile-V7-from-Yandex-V29.zip`
plus SHA-256 and results report. **A successful CI run is not equivalent to
passing the hosted Playgama QA/moderation tests.**

## Licensing and source

OpenTTD and bundled open-source content retain their upstream licenses.
The complete matching port source and packaging scripts are available in
this GitHub repository. Review the notices already included in the V29 base
package before publishing.

Official references:

- https://wiki.playgama.com/playgama/submitting-a-game
- https://wiki.playgama.com/playgama/game-requirements/technical-requirements
- https://wiki.playgama.com/playgama/game-requirements/advertising-requirements
- https://wiki.playgama.com/playgama/bridge-sdk/api/storage
- https://wiki.playgama.com/playgama/bridge-sdk/api/leaderboards
- https://github.com/Playgama/bridge
