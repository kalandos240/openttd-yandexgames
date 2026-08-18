<div align="center">

<img src="assets/banner.jpg" alt="OpenTTD WebAssembly — Yandex Games and Playgama" width="800">

# OpenTTD · WebAssembly port for Yandex Games and Playgama

**OpenTTD 15.3 in the browser through WebAssembly, with separate and independent integrations for Yandex Games and Playgama.**

[![Yandex Games build](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml)
[![Playgama v10](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml)
![OpenTTD](https://img.shields.io/badge/OpenTTD-15.3-2f7d32?style=flat-square)
![WebAssembly](https://img.shields.io/badge/WebAssembly-Emscripten-654ff0?style=flat-square)
![Yandex Games](https://img.shields.io/badge/Yandex%20Games-SDK-ffcc00?style=flat-square)
![Playgama](https://img.shields.io/badge/Playgama-Bridge%20v2-7c3aed?style=flat-square)

**English** · [Русский](README.ru.md)

*Unofficial community port and reproducible browser-build project.*

</div>

---

## About

This repository was originally created to port **OpenTTD 15.3 to Yandex Games** and now also contains a separate **Playgama** integration.

The full OpenTTD source tree is not vendored here. GitHub Actions fetches the official `OpenTTD/OpenTTD` release, applies platform-specific web patches, builds the game with Emscripten and assembles distributable ZIP packages.

**Yandex Games and Playgama are separate build paths.** Playgama changes should not silently modify the Yandex package, and Yandex-specific changes should not be mixed into the Playgama distribution.

> This is not an official OpenTTD release and is not affiliated with or endorsed by the OpenTTD project, Yandex or Playgama.

## Supported platforms

| Capability | Yandex Games | Playgama |
|---|---|---|
| OpenTTD 15.3 WebAssembly | ✅ | ✅ |
| Emscripten + FreeType | ✅ | ✅ |
| English and Russian | ✅ | ✅ |
| Platform locale hand-off | ✅ | ✅ |
| Browser-local persistence | ✅ | ✅ |
| Platform integration | Yandex Games SDK | Playgama Bridge v2 |
| Separate distributable ZIP | `openttd-yandexgames.zip` | `openttd-playgama-v10-cloud-saves.zip` |
| Current cloud-save path | Yandex integration / local persistence | v10 chunked cloud saves |
| Bundled optional NewGRF/OpenGFX2 | not part of the main Yandex package | ✅ |

---

# Yandex Games

## Yandex Games port features

The Yandex Games path remains a first-class part of this repository.

- **OpenTTD 15.3 WebAssembly build** powered by Emscripten.
- **Yandex Games SDK** loaded from `/sdk.js`.
- `YaGames.init()` performed before platform-dependent startup work.
- **Yandex Loading API** integration so the platform is notified when the OpenTTD runtime is ready.
- Yandex Games locale detection for first-launch Russian/English language selection.
- **FreeType-enabled build** for correct Cyrillic rendering.
- Persistent OpenTTD browser data through the Emscripten filesystem/browser storage layer.
- Free base sets **OpenGFX, OpenSFX and OpenMSX** included in the primary package.
- `index.html` placed at the ZIP root for direct upload to the Yandex Games console.
- Platform-specific patches applied during CI instead of maintaining a permanently diverged OpenTTD source fork.

See **[docs/YANDEX_GAMES.md](docs/YANDEX_GAMES.md)** for the full integration flow.

## Build for Yandex Games

Primary workflow:

**Final OpenTTD Package** → `.github/workflows/final-package.yml`

1. Open the **Actions** tab.
2. Select **Final OpenTTD Package**.
3. Run the workflow manually.
4. Download the `openttd-yandexgames-final` artifact after a successful build.

The resulting package is:

```text
openttd-yandexgames.zip
```

The archive contains `index.html` at its root and is intended for **Yandex Games** publication.

---

# Playgama

## Current Playgama build — v10

Playgama is maintained as a separate platform layer on top of the same OpenTTD WebAssembly base.

The current build includes:

- **Playgama Bridge JS Core v2**;
- desktop / landscape packaging;
- English and Russian localization;
- local persistence through IDBFS / IndexedDB;
- cloud saves through `platform_internal`;
- 64 KiB `.sav` text chunks;
- alternating A/B cloud generations;
- size and CRC32 verification before restore;
- migration from legacy `openttdSaveV1` data;
- local fallback when cloud storage is unavailable;
- bundled SimpleAI and required AI libraries;
- optional local NewGRF/OpenGFX2 packages;
- complete license bundle and native licenses viewer;
- interstitial ads requested only at safe pauses.

The active v10 cloud-save implementation no longer uses the previous ~120 KB `.sav` restriction. A 64 MiB per-save client safety guard remains.

Details:

- **[docs/PLAYGAMA.md](docs/PLAYGAMA.md)**
- **[docs/PLAYGAMA_ADDONS.md](docs/PLAYGAMA_ADDONS.md)**

## Playgama optional content

The Playgama package ships these optional local packages:

- Iron Horse 4
- FIRS Industries 5
- Road Hog
- GIST — German Industries Set
- Early Vehicle Set
- OpenGFX2 Settings
- OpenGFX2 Classic

NewGRFs are not enabled automatically. FIRS and GIST are alternative industry sets and should not be enabled together in the same new game.

## Build Playgama v10

1. Open **Actions**.
2. Select **Build Playgama v10 cloud saves**.
3. Run the workflow.
4. Download `openttd-playgama-v10-cloud-saves`.

## Playgama publishing artwork

| Format | File |
|---|---|
| 800×800 | [`assets/playgama/cover-square-800x800.jpg`](assets/playgama/cover-square-800x800.jpg) |
| 1080×1920 | [`assets/playgama/cover-portrait-1080x1920.jpg`](assets/playgama/cover-portrait-1080x1920.jpg) |
| 1920×1080 | [`assets/playgama/cover-landscape-1920x1080.jpg`](assets/playgama/cover-landscape-1920x1080.jpg) |

---

## Documentation

| Document | Purpose |
|---|---|
| [Build guide](docs/BUILDING.md) | General build environment and troubleshooting |
| [Yandex Games integration](docs/YANDEX_GAMES.md) | SDK startup, locale flow, Loading API and ZIP layout |
| [Playgama integration](docs/PLAYGAMA.md) | Bridge v2, lifecycle, ads and cloud saves |
| [Playgama add-ons](docs/PLAYGAMA_ADDONS.md) | NewGRF/OpenGFX2 versions and licensing |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | OpenTTD and bundled third-party projects |
| [Contributing](CONTRIBUTING.md) | Issues and pull requests |

## Repository structure

```text
.
├── .github/workflows/      # Yandex + Playgama build pipelines
├── assets/                 # Banner and publishing artwork
│   └── playgama/           # Playgama cover assets
├── ci/                     # Core WebAssembly/Yandex build scripts
├── docs/                   # Documentation for both platforms
├── playgama/               # Playgama Bridge, saves, add-ons and packaging
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── README.md
└── README.ru.md
```

## Upstream and licensing

OpenTTD is an open-source transport simulation game maintained by the OpenTTD project.

- Upstream source: [`OpenTTD/OpenTTD`](https://github.com/OpenTTD/OpenTTD)
- Target version: **15.3**
- OpenTTD license: **GNU GPL v2**

OpenGFX, OpenSFX, OpenMSX, AI packages and optional NewGRF/OpenGFX2 content retain their respective upstream licenses and notices. Platform packaging does not change the license of upstream OpenTTD.

---

<div align="center">

**OpenTTD → WebAssembly → Yandex Games + Playgama**

</div>
