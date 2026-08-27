#!/usr/bin/env python3
"""Create a Yandex Games package from the already-fixed Playgama OpenTTD build."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PLAYGAMA_FILES = (
    "playgama-yandex-compat.js",
    "playgama-bridge-config.json",
    "openttd-playgama-cloud-saves.js",
    "PLAYGAMA-INTEGRATION.txt",
    "PLAYGAMA-V10-CHANGES.txt",
)

PLAYGAMA_SCRIPT_TAGS = (
    '<script src="playgama-yandex-compat.js"></script>',
    '<script src="openttd-playgama-cloud-saves.js"></script>',
    '<script src="https://bridge.playgama.com/v2/stable/playgama-bridge.js"></script>',
)


def patch_index(dist: Path) -> None:
    index = dist / "index.html"
    html = index.read_text(encoding="utf-8")
    for tag in PLAYGAMA_SCRIPT_TAGS:
        html = html.replace(tag, "")

    # The fixed Playgama package already contains the original Yandex bridge.
    # Replace only the bootstrap with our current documented, non-blocking loader.
    if '<script src="yandex-bootstrap.js"></script>' not in html:
        raise SystemExit("Yandex bootstrap script tag is missing from package")
    if '<script src="yandex-bridge.js"></script>' not in html:
        raise SystemExit("Yandex bridge script tag is missing from package")

    index.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    parser.add_argument("--bootstrap", type=Path, required=True)
    args = parser.parse_args()

    dist = args.dist.resolve()
    if not (dist / "index.html").is_file():
        raise SystemExit("index.html is missing")
    if not (dist / "yandex-bridge.js").is_file():
        raise SystemExit("yandex-bridge.js is missing")
    if not args.bootstrap.is_file():
        raise SystemExit("Yandex bootstrap source is missing")

    patch_index(dist)
    shutil.copy2(args.bootstrap, dist / "yandex-bootstrap.js")

    for name in PLAYGAMA_FILES:
        path = dist / name
        if path.is_file():
            path.unlink()

    # The optional add-on loader is platform-neutral at runtime after the launch
    # fix: it only wraps the existing cloud restore and installs local content in
    # the background. Keep it so Playgama and Yandex share the corrected base.
    addons = dist / "openttd-bundled-addons.js"
    if not addons.is_file():
        raise SystemExit("Fixed bundled add-on loader is missing")

    (dist / "YANDEX-BUILD.txt").write_text(
        "OpenTTD Yandex Games build\n"
        "==========================\n"
        "- Derived from the corrected Playgama v10 OpenTTD base.\n"
        "- Playgama SDK compatibility and Playgama cloud-save scripts removed.\n"
        "- Yandex Games SDK loaded asynchronously using /sdk.js on Yandex hosting.\n"
        "- Documented absolute Yandex SDK fallback is used on other domains.\n"
        "- SDK/network failure cannot block the OpenTTD runtime from starting.\n"
        "- Optional bundled add-ons install in the background and cannot block main().\n",
        encoding="utf-8",
    )

    print("Yandex package conversion applied:", dist)


if __name__ == "__main__":
    main()
