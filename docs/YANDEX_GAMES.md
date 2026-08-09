# Yandex Games integration

This document describes the platform-specific layer added around the OpenTTD WebAssembly build.

## What the port changes

The build pipeline keeps the upstream OpenTTD source as the base and applies Yandex Games-specific integration during CI packaging.

Current integration includes:

- loading the Yandex Games SDK from `/sdk.js`;
- initializing `YaGames` before platform-dependent startup work;
- exposing the SDK instance to the generated page;
- reading the platform locale and using it for the first-launch language choice;
- bundling Russian and English OpenTTD language files;
- calling the Yandex Loading API after the OpenTTD runtime is ready;
- using the Emscripten browser filesystem for persistent OpenTTD data;
- assembling a ZIP package with `index.html` at its root.

## Startup flow

```text
Yandex Games page
      ↓
/sdk.js
      ↓
YaGames.init()
      ↓
locale is read
      ↓
OpenTTD WebAssembly runtime starts
      ↓
OpenTTD configuration / browser storage is initialized
      ↓
LoadingAPI.ready()
```

The locale hand-off is intended to select Russian for Russian-language platform sessions and English otherwise on a fresh profile. A later language choice made by the player inside OpenTTD should remain the player's choice.

## Why patches are applied during CI

The repository is a porting/integration layer rather than a full permanent fork of OpenTTD. Keeping platform patches in the build process makes it easier to see what differs from upstream and to rebuild the same release from a clean OpenTTD source checkout.

## Yandex package

The final archive is produced as:

```text
openttd-yandexgames.zip
```

`index.html` is placed at the root of the archive so the package can be supplied to the Yandex Games console without an extra wrapper directory.

## Scope

Issues that only reproduce in this WebAssembly/Yandex Games version belong in this repository. Bugs that also reproduce in the original OpenTTD release should be checked against the upstream OpenTTD project.
