# Optional bundled add-ons for the Playgama build

The Playgama build ships selected OpenTTD content locally so the player can use it without relying on the in-game Online Content downloader. **Nothing is enabled automatically.** The base game remains playable even if optional-content installation fails.

## How the player enables content

- **NewGRFs:** from the OpenTTD main menu open **NewGRF Settings**, add only the packages you want, configure their parameters if desired, then start a **new game**.
- **OpenGFX2 Classic:** open **Game Options → Base graphics set** and choose **OpenGFX2 Classic**. This is a base-graphics choice and is separate from NewGRFs.
- Existing savegames keep the NewGRF configuration they were created with. Do not add or remove gameplay NewGRFs from an existing game unless OpenTTD explicitly indicates the change is safe.

## Bundled catalog

| Content | Pinned version | Content ID | License | Purpose |
|---|---:|---|---|---|
| Iron Horse 4 (Trains) | 4.29.0 | `newgrf/43411223` | GPL-2.0 | Large train roster |
| FIRS Industries 5 | 5.2.0 | `newgrf/f1250009` | GPL-2.0 | Alternative industry/economy chains |
| Road Hog | 1.4.1 | `newgrf/9787eafe` | GPL-2.0 | Buses, trucks and trams |
| GIST – German Industries Set | 0.21.10 | `newgrf/55440100` | GPL-2.0 | Alternative German-focused industry set |
| Early Vehicle Set | 0.0.2 | `newgrf/474c0501` | GPL-2.0 | Earlier trains and road vehicles |
| OpenGFX2 Settings | 0.7 | `newgrf/4f475a01` | GPL-2.0 | Optional OpenGFX2 graphics parameters |
| OpenGFX2 Classic | 0.8.1 | `base-graphics/6f676678` | GPL-2.0 upstream | Alternative classic base graphics set |

### Compatibility

**FIRS Industries 5 and GIST are alternative industry sets. Do not enable both in the same new game.** Pick one of them or use vanilla industries.

Iron Horse, Road Hog and Early Vehicle Set can be selected independently. Enabling several vehicle sets naturally increases the number of vehicles in the purchase lists.

## Reproducibility and provenance

The v6 build no longer depends on the legacy BaNaNaS TCP protocol.

- **Iron Horse 4.29.0** is built from pinned source commit `ec0523c6f80459ec40cb4488e9a23e5aaa3705c3`.
- **FIRS 5.2.0** is built from pinned source commit `8844b7da36e919690322dcd69ffd9977e4e9a9c4`.
- **Early Vehicle Set 0.0.2** is built from pinned source commit `ae1a35b127cf089bce697afee1bc7cb6a0608b2a`.
- **Road Hog 1.4.1**, **GIST 0.21.10**, **OpenGFX2 Settings 0.7** and **OpenGFX2 Classic 0.8.1** are retrieved from pinned HTTPS release locations.
- Source-built packages record their exact source commit and generated binary hashes.
- HTTPS release packages record the upstream download SHA-256 plus the installed payload MD5/SHA-256.
- Road Hog's release ZIP contains a nested TAR; the packager safely extracts it and verifies the actual `road-hog.grf` binary (`MD5 5b42f9b677d76724cf5265c3bb337ae1`).

The complete machine-readable provenance is stored in `OPENTTD-BUNDLED-ADDONS.json` inside the release ZIP.

## Performance / browser storage design

The release ZIP stores the seven optional payloads as deterministic **gzip-compressed files under `addons/`**. They are not embedded as base64 JavaScript.

Before OpenTTD `main()` starts, `openttd-bundled-addons.js` reads the manifest and installs the local content into OpenTTD's persistent browser filesystem:

- NewGRFs → `<personal-dir>/newgrf/`
- OpenGFX2 Classic → `<personal-dir>/baseset/`

Installation is deliberately **serial (`concurrency = 1`)** to limit peak browser memory while inflating large NewGRFs. On later launches the installer compares the existing file size with the manifest and skips fetching/decompressing content that is already installed. The compressed assets use browser `force-cache`, and newly installed files are persisted through the existing IDBFS sync hook.

If an optional package cannot be installed, the error is logged and OpenTTD continues booting without making the base game unavailable.

OpenGFX2 Classic remains a TAR after gzip decompression. This is intentional: OpenTTD natively scans TAR archives in the base-graphics directory.

## Saves and cloud data

Bundled add-ons are local game content; they are not copied into Playgama cloud saves. The existing cloud bridge continues to synchronize only the OpenTTD configuration and the newest supported savegame, so the `newgrf/` and `baseset/` directories do not inflate cloud-save payloads.

## Release QA

The authoritative workflow is **`Final QA OpenTTD Playgama v6 add-ons`** (`.github/workflows/qa-v6-final-package.yml`). It verifies the pinned source builds and HTTPS releases, archive extraction, hashes/provenance, license/notices, opt-in-only behavior, FIRS/GIST conflict metadata, runtime integration, ASCII-safe package paths and the Playgama 300 MB unpacked-size ceiling before publishing the final ZIP artifact.

The superseded experimental v6 packaging/probe workflows were removed after the final workflow passed.