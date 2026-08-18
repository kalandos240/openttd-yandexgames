<div align="center">

<img src="assets/banner.jpg" alt="OpenTTD WebAssembly browser port" width="800">

# OpenTTD · WebAssembly browser ports

**OpenTTD 15.3 packaged for browser game platforms, with dedicated Yandex Games and Playgama integration paths.**

[![Yandex package](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml)
[![Playgama v10](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml)
![OpenTTD](https://img.shields.io/badge/OpenTTD-15.3-2f7d32?style=flat-square)
![WebAssembly](https://img.shields.io/badge/WebAssembly-Emscripten-654ff0?style=flat-square)
![Playgama](https://img.shields.io/badge/Playgama-Bridge%20v2-7c3aed?style=flat-square)

**English** · [Русский](README.ru.md)

*Unofficial community port and reproducible build/integration project.*

</div>

---

## About

This repository contains the integration layer, patches and automated build pipelines used to prepare **OpenTTD 15.3** for browser distribution.

The OpenTTD source tree is not vendored here. CI fetches the official `OpenTTD/OpenTTD` release, applies platform-specific web patches, builds with Emscripten and assembles distributable ZIP packages.

> This is not an official OpenTTD release and is not affiliated with or endorsed by the OpenTTD project, Yandex or Playgama.

## Current Playgama build — v10

The current Playgama path uses **Playgama Bridge JS Core v2** and includes:

- desktop / landscape browser packaging;
- English and Russian localization with FreeType/Cyrillic support;
- local OpenTTD persistence through Emscripten IDBFS / IndexedDB;
- **Playgama-native chunked cloud saves** through `platform_internal` storage;
- 64 KiB save chunks, alternating A/B cloud generations and metadata-last commits;
- size and CRC32 verification before a cloud save is restored;
- migration from the previous `openttdSaveV1` snapshot format;
- local-save fallback when platform cloud storage is unavailable;
- bundled **SimpleAI** and required AI libraries;
- optional bundled NewGRFs and OpenGFX2 content, disabled by default;
- a native in-game licenses viewer with the full legal bundle;
- interstitial advertising only at safe pauses; rewarded and banner ads disabled.

The active cloud-save implementation no longer uses the old ~120 KB player-data restriction. A **64 MiB per-save browser safety guard** remains to prevent pathological browser memory use.

See **[docs/PLAYGAMA.md](docs/PLAYGAMA.md)** and **[docs/PLAYGAMA_ADDONS.md](docs/PLAYGAMA_ADDONS.md)**.

## Bundled optional content

The Playgama package currently ships these optional local packages for player choice:

- Iron Horse 4
- FIRS Industries 5
- Road Hog
- GIST — German Industries Set
- Early Vehicle Set
- OpenGFX2 Settings
- OpenGFX2 Classic

NewGRFs are **not activated automatically**. FIRS and GIST are alternative industry sets and should not be enabled together in the same new game.

## Playgama publishing artwork

Ready-to-upload cover assets are stored in the repository:

| Format | File |
|---|---|
| Square 1:1 — 800×800 | [`assets/playgama/cover-square-800x800.jpg`](assets/playgama/cover-square-800x800.jpg) |
| Portrait 9:16 — 1080×1920 | [`assets/playgama/cover-portrait-1080x1920.jpg`](assets/playgama/cover-portrait-1080x1920.jpg) |
| Landscape 16:9 — 1920×1080 | [`assets/playgama/cover-landscape-1920x1080.jpg`](assets/playgama/cover-landscape-1920x1080.jpg) |

## Build

### Playgama v10

1. Open **Actions**.
2. Select **Build Playgama v10 cloud saves**.
3. Run the workflow.
4. Download the `openttd-playgama-v10-cloud-saves` artifact.

The workflow starts from the verified Playgama v8 package, applies the current add-on delivery fixes, installs the v10 cloud-save layer, rebuilds the legal bundle, runs save/add-on validation and creates the final ZIP.

### Yandex Games

The existing Yandex-specific build pipeline remains available through **Final OpenTTD Package**. Its source and integration documentation are kept separately so Playgama changes do not silently alter the Yandex release path.

## Documentation

| Document | Purpose |
|---|---|
| [Build guide](docs/BUILDING.md) | General build environment and troubleshooting |
| [Playgama integration](docs/PLAYGAMA.md) | Bridge v2, lifecycle, ads, cloud saves and publication fields |
| [Playgama add-ons](docs/PLAYGAMA_ADDONS.md) | Bundled NewGRF/OpenGFX2 content and licensing notes |
| [Yandex Games integration](docs/YANDEX_GAMES.md) | Yandex SDK startup, locale flow and package layout |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | OpenTTD and bundled third-party project notice overview |
| [Contributing](CONTRIBUTING.md) | Scope for issues and pull requests |

## Repository structure

```text
.
├── .github/workflows/      # Reproducible browser package pipelines
├── assets/                 # Repository and publishing artwork
│   └── playgama/           # Exact Playgama cover sizes
├── ci/                     # Core browser/Yandex build scripts
├── docs/                   # Build and platform documentation
├── playgama/               # Bridge v2, add-ons, cloud saves and packaging helpers
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── README.md
└── README.ru.md
```

## Upstream and licensing

OpenTTD is an open-source transport simulation game maintained by the OpenTTD project.

- Upstream source: [`OpenTTD/OpenTTD`](https://github.com/OpenTTD/OpenTTD)
- Version targeted by this port: **15.3**
- OpenTTD license: **GNU GPL v2**

Bundled base sets, AI packages and optional NewGRFs retain their own upstream licenses and notices. The generated Playgama package includes the complete license bundle and source-code notices required by the distributed components.

---

<div align="center">

**OpenTTD → WebAssembly → Yandex Games / Playgama**

</div>
