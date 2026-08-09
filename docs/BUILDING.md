# Building the OpenTTD Yandex Games port

This repository is designed around reproducible GitHub Actions builds. The OpenTTD source tree is fetched from the official upstream repository during the build instead of being vendored here.

## Recommended build

1. Open the repository's **Actions** tab.
2. Choose **Final OpenTTD Package**.
3. Click **Run workflow**.
4. Wait for the build to finish.
5. Download the `openttd-yandexgames-final` artifact.

The artifact contains the ready-to-upload package:

```text
openttd-yandexgames.zip
```

## Build environment

The final workflow uses:

- OpenTTD **15.3** from `OpenTTD/OpenTTD`;
- Emscripten SDK **3.1.57**;
- FreeType support for Cyrillic rendering;
- OpenGFX, OpenSFX and OpenMSX free base sets;
- the Yandex Games SDK integration applied during packaging.

The main final-build entry point is:

```text
ci/build-final-freetype.sh
```

## Package requirements

The packaging scripts assemble a browser-ready distribution with `index.html`, WebAssembly/runtime data and the files required by the bundled base sets. The final pipeline also verifies the uncompressed package size against the Yandex Games package-size target used by this port.

## Local builds

The CI workflow is the reference environment. A local build requires a compatible Linux toolchain, Emscripten, CMake and the additional packages installed by the scripts. For consistent results, use the workflow or reproduce the same container/tool versions locally.

## Troubleshooting

If a build fails, check the failing GitHub Actions step first. Common failure areas are upstream downloads, dependency installation, Emscripten configuration, FreeType configuration and final package assembly.

Do not report upstream OpenTTD gameplay bugs here unless the problem is specific to the browser/Yandex Games port.
