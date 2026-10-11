# OpenTTD Playgama V2 — based on verified Yandex V29

This is **not** the old Playgama v10 runtime. The active release pipeline is
`.github/workflows/build-playgama-from-yandex-v29.yml`, running on branch
`port/playgama-v2-from-yandex-v29-storage-fix`.

## Immutable gameplay baseline

- Source: successful Yandex V29 action run [35286380038](https://github.com/kalandos240/openttd-yandexgames/actions/runs/35286380038).
- Source artifact ID: `10524282138` (expires 2026-12-16). Source commit:
  `646b534248c8984c5cac97fbdf5c63f14e5d09ed`.
- The action downloads that exact artifact, validates the original V29 QA
  report and verifies unchanged runtime, fullscreen, cursor, touch,
  localization, AI and OpenTTD shell files with `cmp`.
- The Playgama packaging script changes only the SDK bootstrap and adds the
  adapter/config. It removes `yandex-bootstrap.js` and the Yandex-only
  integration notice. A missing Yandex V29 source artifact **fails the build**
  instead of substituting an older runtime.

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

Browser-local OpenTTD persistence is inherited from the V29 runtime. The
automated tests verify SDK API compatibility, **not** that a real Playgama
account has cloud-save capacity for every possible large `.sav` file. Check
large save files, reload and cross-device restores with the Playgama QA tool.

### Ads and ranking

Interstitial minimum/initial delays are both 150 seconds. Ads may only be
requested at the game's natural pauses. Pause/resume/audio restoration must
be verified during Playgama QA. Rewarded ads and in-game banners are disabled.
The adapter reports leaderboard methods as available only if the active
platform supports the relevant leaderboard type. Playgama's native
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

CI runs `node playgama/test-playgama-bridge-v2.cjs` and creates the
`OpenTTD-v14-Playgama-Desktop-Mobile-V2-from-Yandex-V29.zip` archive plus
SHA-256 and results report. **A successful CI run is not equivalent to
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
