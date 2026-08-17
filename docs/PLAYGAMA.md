# OpenTTD — Playgama publication notes

This document describes the Playgama package generated from the already-tested OpenTTD 15.3 WebAssembly/Yandex build.

## Package

- Engine: **Plain JS** (Emscripten/WebAssembly runtime behind a browser shell)
- SDK: **Playgama Bridge JS Core v2 stable**
- Supported devices: **Desktop**
- Orientation: **Landscape**
- Languages: **English, Russian**
- In-app purchases: **No**
- Leaderboards: **No**
- Multiplayer: **No** for this packaged browser port
- Social sharing: **No**
- Authorization: **No**
- Rewarded ads: **Disabled**
- Banner ads: **Disabled**
- Interstitial ads: **Enabled**, requested only at safe pauses by the existing game integration

The package root contains `index.html` and stays under Playgama's 300 MB unpacked limit.

## SDK mapping

The browser build already uses a small Yandex-style integration layer. `playgama-yandex-compat.js` provides a compatibility facade so the game code itself does not need to be rewritten:

- `ysdk.environment.i18n.lang` -> Playgama platform language
- `ysdk.getPlayer().getData/setData` -> Playgama Bridge storage
- `LoadingAPI.ready()` -> Playgama game-ready platform message
- `GameplayAPI.start/stop()` -> Playgama gameplay lifecycle messages
- `showFullscreenAdv()` -> Playgama interstitial advertising
- Yandex pause/resume events -> Playgama pause-state events
- audio suspension/resume -> Playgama platform audio state and page visibility

The OpenTTD runtime files are pinned by SHA-256 in the packaging workflow so Playgama packaging cannot silently replace the tested game runtime.

## Game description (English)

OpenTTD is a transport management simulation where you build and operate a growing transportation company. Create railways, roads, shipping routes and air networks, connect towns and industries, move passengers and cargo, purchase vehicles, expand infrastructure and develop an efficient transport empire across a large dynamic map.

## How to play (English)

Use the mouse to navigate menus, build infrastructure and manage vehicles. Start a new game, connect towns and industries with roads, railways, airports or docks, then purchase suitable vehicles and create routes for passengers and cargo. Earn money from successful deliveries, expand your network and keep your company profitable. Keyboard shortcuts can be used for faster management and can be viewed or changed in the game settings.

## Description (Russian)

OpenTTD — транспортно-экономическая стратегия, в которой вы строите и развиваете собственную транспортную компанию. Прокладывайте железные и автомобильные дороги, создавайте морские и воздушные маршруты, соединяйте города и предприятия, перевозите пассажиров и грузы, покупайте транспорт и расширяйте инфраструктуру на большой динамической карте.

## How to play (Russian)

Используйте мышь для управления меню, строительства инфраструктуры и настройки транспорта. Начните новую игру, соединяйте города и предприятия дорогами, железными дорогами, аэропортами или портами, покупайте подходящий транспорт и создавайте маршруты для пассажиров и грузов. Получайте прибыль от перевозок, расширяйте сеть и следите за экономикой компании. Для быстрого управления доступны горячие клавиши, которые можно посмотреть и изменить в настройках игры.

## Certification notes

- Save test: make a manual save in OpenTTD, reload the QA build and verify that the saved game remains available.
- Rewarded Ads: the game has no rewarded-ad mechanic and the SDK config disables rewarded ads.
- Interstitial Ads: the existing game integration only requests fullscreen advertising after sufficient gameplay time and at a safe pause.
- Authorization: select **No**.
- Sensitive content: standard OpenTTD gameplay does not contain realistic violence, blood, gambling, alcohol/tobacco use or sexual content.
- Scale test: the Emscripten canvas and loading background already use the complete browser viewport; do not intentionally crop UI elements.

## Licensing

OpenTTD is licensed under the **GNU General Public License version 2**. Bundled OpenGFX, OpenSFX and OpenMSX assets retain their own licenses. The generated package keeps the repository's source-code and third-party notice files. See the repository `LICENSE`, `THIRD_PARTY_NOTICES.md`, package `SOURCE_CODE.txt`, and bundled license directory before redistribution.
