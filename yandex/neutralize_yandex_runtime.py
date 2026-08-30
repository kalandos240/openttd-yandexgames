#!/usr/bin/env python3
"""Remove Playgama-specific runtime naming from the final Yandex package.

The combined legal bundle is renamed byte-for-byte; its contents are not edited.
Only executable/runtime-facing references and obsolete platform integration files
are neutralized or removed.
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
        "Optional bundled OpenTTD add-ons for the browser build.",
    )
    text = text.replace(
        "const LICENSE_BUNDLE_URL = './PLAYGAMA-ALL-LICENSES.md';",
        "const LICENSE_BUNDLE_URL = './THIRD-PARTY-LICENSES.md';",
    )
    text = text.replace(
        "const LICENSE_TARGET = '/docs/PLAYGAMA-LICENSES.md';",
        "const LICENSE_TARGET = '/docs/THIRD-PARTY-LICENSES.md';",
    )
    if re.search(r"playgama", text, re.I):
        raise SystemExit("Playgama reference remains in Yandex bundled-addons runtime")
    if NEW_LICENSE_NAME not in text or "/docs/THIRD-PARTY-LICENSES.md" not in text:
        raise SystemExit("Neutral Yandex license path was not installed in bundled-addons runtime")
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
        raise SystemExit("Neutral Yandex license bundle is missing or unexpectedly small")

    print(f"Yandex runtime naming neutralized; legal text preserved: {new_license}")


if __name__ == "__main__":
    main()
