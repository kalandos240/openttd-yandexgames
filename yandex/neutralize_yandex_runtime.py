#!/usr/bin/env python3
"""Remove Playgama-specific runtime naming from the final Yandex package.

The combined legal bundle is kept as a static distribution file and renamed
byte-for-byte for Yandex. It is no longer copied into MEMFS and there is no
in-game licenses button/window. Only executable/runtime-facing references and
obsolete platform integration files are neutralized or removed.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


OLD_LICENSE_NAME = "PLAYGAMA-ALL-LICENSES.md"
NEW_LICENSE_NAME = "THIRD-PARTY-LICENSES.md"


def patch_loader(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "Optional bundled OpenTTD add-ons for the Playgama/Yandex browser builds.",
        "Optional bundled OpenTTD add-ons for the browser builds.",
    )
    text = text.replace(
        "Optional bundled OpenTTD add-ons for the Playgama build.",
        "Optional bundled OpenTTD add-ons for the browser build.",
    )
    text = text.replace("[Playgama/OpenTTD]", "[OpenTTD/Web]")

    if re.search(r"playgama", text, re.I):
        raise SystemExit("Playgama reference remains in Yandex bundled-addons runtime")

    # Legal notices remain static files in the ZIP. The runtime must not fetch,
    # install or expose them through browser globals anymore.
    forbidden = (
        "LICENSE_BUNDLE_URL",
        "LICENSE_TARGET",
        "installLicenseBundle",
        "__openttdLicenseBundlePath",
        "__openttdBundledLicenseStatus",
        "PLAYGAMA-LICENSES.md",
        "THIRD-PARTY-LICENSES.md",
        "license bundle",
    )
    for marker in forbidden:
        if marker.lower() in text.lower():
            raise SystemExit(f"Legacy licenses runtime marker remains in Yandex loader: {marker}")

    if "paced_writes: true" not in text or "waitForIdle" not in text:
        raise SystemExit("Paced bundled-addons installer is missing from Yandex runtime")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    loader = dist / "openttd-bundled-addons.js"
    if not loader.is_file():
        raise SystemExit(f"Missing Yandex bundled-addons runtime: {loader}")

    old_license = dist / OLD_LICENSE_NAME
    new_license = dist / NEW_LICENSE_NAME
    if old_license.is_file():
        # Rename without altering license/notices content.
        old_bytes = old_license.read_bytes()
        new_license.write_bytes(old_bytes)
        if new_license.read_bytes() != old_bytes:
            raise SystemExit("Yandex legal bundle changed while being renamed")
        old_license.unlink()
    elif not new_license.is_file():
        raise SystemExit("Combined license bundle is missing from Yandex package")

    patch_loader(loader)

    # These are obsolete integration/change-log files, not third-party licenses.
    for name in (
        "PLAYGAMA-INTEGRATION.txt",
        "PLAYGAMA-V10-CHANGES.txt",
        "PLAYGAMA-V8-CHANGES.txt",
        "PLAYGAMA-V7-CHANGES.txt",
        OLD_LICENSE_NAME,
    ):
        path = dist / name
        if path.exists():
            path.unlink()

    if not new_license.is_file() or new_license.stat().st_size < 100_000:
        raise SystemExit("Neutral Yandex legal bundle is missing or unexpectedly small")

    print(f"Yandex runtime naming neutralized; static legal text preserved: {new_license}")
    print("No in-game licenses UI or license-bundle runtime installer remains.")


if __name__ == "__main__":
    main()
