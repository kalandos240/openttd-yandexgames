# OpenTTD CrazyGames V1

Base runtime: verified `OpenTTD-v14-Yandex-Adaptive-Desktop-Mobile-V28` / commit `53faaacfe26d5a73b3deec0fa03900ab1885c940`.

CrazyGames integration:

- HTML5 SDK v3 initialization
- `loadingStart` / `loadingStop`
- `gameplayStart` / `gameplayStop`
- Data module bridge for OpenTTD config and latest save
- `muteAudio` support
- CrazyGames `systemInfo` device-type support for adaptive desktop/mobile/tablet behavior
- no automatic fullscreen request
- no Yandex SDK, Yandex ads, or Yandex leaderboard dependency in the CrazyGames package
- no timed/interruption ads; CrazyGames ad bridge is exposed only for genuine logical breaks
- game remains playable when ads or the Data module are disabled during Basic Launch

The verified V28 WebAssembly runtime is kept unchanged. Compatibility aliases are intentionally provided because the compiled V28 glue still looks up the legacy platform hook names.

CrazyGames leaderboards are not enabled in V1 because that feature is invitation/configuration based and requires game-specific leaderboard keys.
