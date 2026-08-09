

[![Final package](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml)
![OpenTTD](https://img.shields.io/badge/OpenTTD-15.3-2f7d32?style=flat-square)
![WebAssembly](https://img.shields.io/badge/WebAssembly-Emscripten-654ff0?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Yandex%20Games-ffcc00?style=flat-square)

**English** · [Русский](README.ru.md)

*Unofficial community port and build/integration project.*

</div>

---

## About

This repository contains the integration layer and automated build pipeline used to prepare **OpenTTD 15.3** for the web and for distribution through **Yandex Games**.

The OpenTTD source code itself is not vendored here. During CI builds the pipeline fetches the official `OpenTTD/OpenTTD` repository at tag `15.3`, applies the web/Yandex-specific build adjustments, compiles the game with Emscripten and assembles the final ZIP package.

> This project is not an official OpenTTD release and is not affiliated with or endorsed by the OpenTTD team or Yandex.

## Port features

- **WebAssembly build** powered by Emscripten.
- **Yandex Games SDK** initialization in the generated web package.
- **Yandex Loading API** integration so the platform is notified after the OpenTTD runtime starts.
- **Russian and English localization** bundled into the web build.
- **Automatic first-launch language selection** based on the Yandex Games locale.
- **FreeType-enabled build** for proper Cyrillic font rendering.
- **Browser persistence** based on OpenTTD's Emscripten filesystem support.
- Bundled free base sets used by the current package: **OpenGFX**, **OpenSFX** and **OpenMSX**.
- Final distribution assembled as a **Yandex Games-ready ZIP**.
- Packaging pipeline check for the port's **100 MB uncompressed package target**.

## Quick build

The recommended build path is GitHub Actions:

1. Open the **Actions** tab.
2. Select **Final OpenTTD Package**.
3. Run the workflow manually with **Run workflow**.
4. Download the `openttd-yandexgames-final` artifact after a successful run.

The resulting package is:

```text
openttd-yandexgames.zip
```

For the full build notes, see **[docs/BUILDING.md](docs/BUILDING.md)**.

## Documentation

| Document | Purpose |
|---|---|
| [Build guide](docs/BUILDING.md) | Build environment, final workflow and troubleshooting |
| [Yandex Games integration](docs/YANDEX_GAMES.md) | SDK startup, locale flow, loading API and package layout |
| [Third-party notices](THIRD_PARTY_NOTICES.md) | OpenTTD and bundled third-party project notice overview |
| [Contributing](CONTRIBUTING.md) | Scope for issues and pull requests |

## Repository structure

```text
.
├── .github/
│   ├── ISSUE_TEMPLATE/  # Port-specific issue forms
│   └── workflows/       # GitHub Actions build/package pipelines
├── assets/              # Repository artwork
├── ci/                  # Build, patching and packaging scripts
├── docs/                # Build and Yandex Games documentation
├── CONTRIBUTING.md
├── THIRD_PARTY_NOTICES.md
├── README.md
└── README.ru.md
```

The repository intentionally focuses on the **porting layer and reproducible build automation** instead of maintaining a forked copy of the full OpenTTD source tree.

## Upstream

OpenTTD is an open-source transport simulation game maintained by the OpenTTD project.

- Upstream source: [`OpenTTD/OpenTTD`](https://github.com/OpenTTD/OpenTTD)
- Version currently targeted by this port: **15.3**

If you are looking for the original desktop game, upstream development, bug reports for OpenTTD itself, or official documentation, use the OpenTTD project rather than this port repository.

## Yandex Games integration

The packaging scripts adapt the generated Emscripten build for Yandex Games. The current integration includes SDK startup, locale hand-off and loading-state reporting while keeping the OpenTTD application itself as close to upstream as practical.

Platform-specific changes are applied by the build pipeline instead of permanently rewriting the upstream source tree. This makes the port easier to audit and rebuild against the exact OpenTTD release it targets.

See **[docs/YANDEX_GAMES.md](docs/YANDEX_GAMES.md)** for the integration flow.

## Licensing

**OpenTTD is licensed under the GNU General Public License version 2.** The OpenTTD source used for builds comes from the official upstream repository and retains its original copyright and license terms.

Bundled third-party base sets such as OpenGFX, OpenSFX and OpenMSX retain their own respective licenses and copyright notices. This repository does not claim ownership of OpenTTD or those third-party projects and does not relicense their content.

See **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)** before redistributing a compiled package.

## Project status

The repository contains an automated path for producing the Yandex Games web package of OpenTTD 15.3, including the FreeType/Cyrillic build path, bundled free base sets and Yandex Games startup integration.

---

<div align="center">

**OpenTTD → WebAssembly → Yandex Games**

</div>
