# Optional bundled add-ons for the Playgama build

The Playgama build ships selected OpenTTD content packages locally so the player can choose them without using Online Content. Nothing in this list is enabled automatically.

## How the player enables content

- **NewGRFs:** from the OpenTTD main menu open **NewGRF Settings**, add only the packages you want, configure their parameters if desired, then start a **new game**.
- **OpenGFX2 Classic:** open **Game Options → Base graphics set** and choose **OpenGFX2 Classic**. This is a graphics choice and is separate from NewGRFs.
- Existing savegames keep the NewGRF configuration they were created with. Do not add/remove gameplay NewGRFs in an existing game unless OpenTTD explicitly indicates that the change is safe.

## Bundled catalog

| Content | Pinned version | BaNaNaS content ID | License metadata | Purpose |
|---|---:|---|---|---|
| Iron Horse 4 (Trains) | 4.29.0 | `newgrf/43411223` | GPL v2 | Large train roster, 1860–2020 |
| FIRS Industries 5 | 5.2.0 | `newgrf/f1250009` | GPL v2 | Alternative industry/economy chains |
| Road Hog | 1.4.1 | `newgrf/9787eafe` | GPL v2 | Buses, trucks and trams |
| GIST – German Industries Set | 0.21.10 | `newgrf/55440100` | GPL v2 | Alternative German-focused industry set |
| Early Vehicle Set | 0.0.2 | `newgrf/474c0501` | GPL v2 | Earlier trains and road vehicles |
| OpenGFX2 Settings | 0.7 | `newgrf/4f475a01` | GPL v2 | Optional OpenGFX2 graphics parameters |
| OpenGFX2 Classic | 0.8.1 | `base-graphics/6f676678` | BaNaNaS: Custom; upstream repository: GPL-2.0 | Alternative classic base graphics set |

### Important compatibility note

**FIRS Industries 5 and GIST are alternative industry sets. Do not enable both in the same new game.** Pick one industry set, or use the vanilla industries.

Iron Horse, Road Hog and Early Vehicle Set all add vehicles. They can be selected independently, but enabling multiple vehicle sets naturally increases the number of vehicles in purchase lists.

## Upstream / source references

- OpenTTD / BaNaNaS package metadata: `https://bananas.openttd.org/`
- Iron Horse: `https://grf.farm/iron-horse/index.html`
- FIRS: `https://grf.farm/firs/index.html`
- Road Hog project thread: `https://www.tt-forums.net/viewtopic.php?f=26&t=70241`
- GIST source: `https://github.com/UweDomaratius/GermanIndustries`
- Early Vehicle Set source: `https://github.com/DonaldDuck313/OpenTTD-NewGRFs/tree/main/EarlyVehicleSet`
- OpenGFX2 source: `https://github.com/OpenTTD/OpenGFX2`

The build downloads the exact BaNaNaS package versions checked by the workflow and records their full MD5, byte size, license metadata and local package filename in `OPENTTD-BUNDLED-ADDONS.json` inside the release ZIP.

## Performance / packaging design

The add-on archives are stored as raw files under `addons/` in the Playgama package. They are **not** converted to base64 JavaScript. On first launch the installer copies missing packages into OpenTTD's virtual local content folders before `main()` starts. On later launches it checks the persistent IDBFS copy by byte size and skips already-installed content, so the large add-on payloads are normally not fetched or rewritten again. Installation uses a small concurrency limit to avoid large transient memory spikes.
