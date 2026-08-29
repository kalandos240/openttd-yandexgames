# Optional bundled add-ons for the Playgama v10 build

The Playgama v10 package ships selected OpenTTD content locally so the player can use it without relying on the in-game Online Content downloader. **Nothing is enabled automatically.** The base game remains playable even if optional-content installation fails.

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

**FIRS Industries 5 and GIST are alternative industry sets. Do not enable both in the same new game.** Pick one of them or use the vanilla industry set.

Iron Horse, Road Hog and Early Vehicle Set can be selected independently. Enabling several vehicle sets naturally increases the number of vehicles in purchase lists.

## Reproducibility and provenance

The packaging path avoids the legacy BaNaNaS TCP metadata protocol for the optional NewGRF payloads.

- **Iron Horse 4.29.0** is built from pinned source commit `ec0523c6f80459ec40cb4488e9a23e5aaa3705c3`.
- **FIRS 5.2.0** is built from pinned source commit `8844b7da36e919690322dcd69ffd9977e4e9a9c4`.
- **Early Vehicle Set 0.0.2** is built from pinned source commit `ae1a35b127cf089bce697afee1bc7cb6a0608b2a`.
- **Road Hog 1.4.1**, **GIST 0.21.10**, **OpenGFX2 Settings 0.7** and **OpenGFX2 Classic 0.8.1** are retrieved from pinned HTTPS release locations.
- Source-built packages record their exact source commit and output hashes.
- HTTPS release packages record the upstream download SHA-256 plus installed-payload hashes.
- The complete machine-readable provenance is stored in `OPENTTD-BUNDLED-ADDONS.json` inside the release ZIP.

## v10 browser-delivery design

The seven optional payloads are gzip-compressed for distribution, but v10 gives the packaged assets neutral **`.bin` filenames** under `addons/` instead of serving them as `.gz` URLs. This avoids ambiguity when a hosting layer or CDN transparently applies HTTP gzip/content-encoding behavior.

`openttd-bundled-addons.js` accepts both of the situations that can occur in a browser host:

1. the fetched bytes are still gzip-compressed and must be inflated by the loader;
2. an intermediary already decoded the response and the fetched bytes are the final OpenTTD payload.

The manifest keeps hashes and expected installed sizes so the loader can verify what it installs.

Before OpenTTD `main()` starts, bundled content is made available in OpenTTD's persistent browser filesystem:

- NewGRFs → `<personal-dir>/newgrf/`
- OpenGFX2 Classic → `<personal-dir>/baseset/`

Installation is deliberately serial to keep peak browser memory lower while large NewGRFs are unpacked. Existing correctly sized files are skipped on later launches. A deferred IDBFS sync persists newly installed content without blocking the earliest startup frames.

If an optional package cannot be installed, the error is logged and OpenTTD continues booting instead of making the base game unavailable.

OpenGFX2 Classic remains a TAR after delivery decompression. This is intentional: OpenTTD natively scans TAR archives in the base-graphics directory.

## Saves and cloud data

Bundled add-ons are game content and are **not copied into cloud-save payloads**. The v10 cloud layer synchronizes the current OpenTTD `.sav` snapshot separately through Playgama storage, while local NewGRF/base-set files remain in IDBFS/IndexedDB.

The cloud-save implementation uses chunked A/B generations with metadata-last commits and CRC32/size verification. This keeps optional content from inflating cloud-save data and prevents a partially uploaded new generation from invalidating the previous complete one.

### AI-enabled dual-package compatibility

The current `build-playgama-ai-runtime.yml` pipeline uses `playgama-yandex-compat.js` for the Playgama platform bridge and does **not** require the older dedicated `openttd-playgama-cloud-saves.js` script tag. When the verified Playgama package is converted to the autonomous Yandex package, the converter therefore accepts the legacy cloud script as optional: zero copies is the normal current layout, while one copy is removed for backwards-compatible conversion of an older launch-safe base. Duplicate active cloud integrations remain a hard error.

This contract keeps the Yandex conversion strict about the active Playgama Bridge and adapter while avoiding a false packaging failure caused by a cloud module that the current AI-enabled Playgama build no longer injects.

## Licensing

Every bundled package retains its upstream license and notices. The Playgama build generates a combined `PLAYGAMA-ALL-LICENSES.md` plus `NOTICE.txt`, `SOURCE_CODE.txt` and the `licenses/` directory. The Playgama-facing legal files are normalized so obsolete platform branding from earlier package stages is not exposed.

## Release QA

The authoritative current workflow is **`Build Playgama v10 cloud saves`** (`.github/workflows/build-playgama-v10-cloud-saves.yml`). It verifies:

- all seven bundled items and their manifest entries;
- neutral `.bin` delivery names;
- gzip decoding and installed payload hashes;
- the complete legal bundle;
- absence of obsolete Yandex branding in Playgama-facing legal documents;
- chunked cloud-save round-trip behavior;
- Bridge v2/runtime integration;
- JavaScript/JSON syntax;
- and the Playgama unpacked-package size ceiling.

The AI-enabled dual-package branch additionally uses `.github/workflows/build-playgama-ai-runtime.yml` to validate the bundled AI/runtime state and build both Playgama and autonomous Yandex artifacts from the same tested browser runtime.

Older v6–v8 workflows remain historical build stages; **v10 is the current publication target**.
