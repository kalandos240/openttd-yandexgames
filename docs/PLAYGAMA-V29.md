# OpenTTD Playgama V5 — based on verified Yandex V29

This is **not** the old Playgama v10 runtime. The active release pipeline is
`.github/workflows/build-playgama-from-yandex-v29.yml`, running on branch
`port/playgama-v2-from-yandex-v29-storage-fix`.

## Immutable gameplay baseline

- Source: successful Yandex V29 action run [35286380038](https://github.com/kalandos240/openttd-yandexgames/actions/runs/35286380038).
- Source artifact ID: `10524282138` (expires 2026-12-16). Source commit:
  `646b534248c8984c5cac97fbdf5c63f14e5d09ed`.
- The action downloads that exact artifact, validates the original V29 QA
  report and verifies fullscreen, cursor, touch, localization, AI and shell
  gameplay files byte-for-byte with `cmp`. The large Emscripten runtime
  differs in **exactly two literal startup timeouts**, checked against the
  original source by `playgama/patch_v29_startup_timeout.py`. Gameplay,
  rendering logic and WASM content remain unchanged.
- Playgama packaging replaces the Yandex SDK bootstrap, adds the
  Bridge adapter/config/cloud-save module, and narrowly patches the ad policy,
  unsupported leaderboard response, and two runtime startup timeouts.
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

**V5 cloud save upgrade (experimental):** the new module is loaded
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
filesystem/watchdog timeout from 8 to **14 seconds**. Both edits are
mechanically verified as the ONLY compiled JS runtime differences from V29.
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

Interstitial minimum/initial delays are both 150 seconds. The Playgama V5
package removes the Yandex V29 timer that could interrupt active gameplay
after 150 seconds. Instead, after sufficient gameplay, the existing
`yandexGameSetGameplay(false)` path requests ads only when returning to
a menu or other natural game pause. The exact patch is mechanically verified
against the Yandex V29 source and dynamically tested in Node VM.
Pause/resume/audio restoration must
be verified during Playgama QA. Rewarded ads and in-game banners are disabled.
The adapter reports leaderboard methods as available only if the active
platform supports the relevant leaderboard type. The V5 shell displays an
offline status instead of attempting an unsupported leaderboard fetch. Playgama's native
`playgama` adapter does not provide ordinary `in_game` leaderboards by
default; optional SaaS leaderboards require separate configuration.

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
The byte-exact native timeout patch is also validated by Python in CI.
It creates `OpenTTD-v14-Playgama-Desktop-Mobile-V5-from-Yandex-V29.zip`
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
