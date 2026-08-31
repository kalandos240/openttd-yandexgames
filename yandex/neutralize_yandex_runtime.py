#!/usr/bin/env python3
"""Remove Playgama-specific runtime naming and unused external URLs from Yandex.

The combined legal bundle is renamed byte-for-byte; its contents are not edited.
Executable/runtime-facing references and obsolete platform integration files are
neutralized or removed. The bundled-addons manifest also drops provenance URL
fields that the runtime loader never reads, while retaining local assets,
licenses, versions, source commits and integrity hashes.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


OLD_LICENSE_NAME = "PLAYGAMA-ALL-LICENSES.md"
NEW_LICENSE_NAME = "THIRD-PARTY-LICENSES.md"
ADDON_MANIFEST_NAME = "OPENTTD-BUNDLED-ADDONS.json"


def patch_loader(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "Optional bundled OpenTTD add-ons for the Playgama/Yandex browser builds.",
        "Optional bundled OpenTTD add-ons for the browser build.",
    )
    text = text.replace(
        "Optional bundled OpenTTD add-ons for the Playgama build.",
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
    text = text.replace(
        "const LICENSE_TARGET_NAME = 'PLAYGAMA-LICENSES.md';",
        "const LICENSE_TARGET_NAME = 'THIRD-PARTY-LICENSES.md';",
    )
    text = text.replace("[Playgama/OpenTTD]", "[OpenTTD/Web]")

    if re.search(r"playgama", text, re.I):
        raise SystemExit("Playgama reference remains in Yandex bundled-addons runtime")
    if NEW_LICENSE_NAME not in text:
        raise SystemExit("Neutral Yandex license bundle path was not installed")
    if "THIRD-PARTY-LICENSES.md" not in text:
        raise SystemExit("Neutral Yandex installed-license target was not installed")
    path.write_text(text, encoding="utf-8")


def scrub_unused_manifest_urls(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("Bundled add-on manifest has no items")

    removed = 0
    for item in items:
        if not isinstance(item, dict):
            raise SystemExit("Bundled add-on manifest item is not an object")
        # Runtime openttd-bundled-addons.js installs only item.asset. These URL
        # fields are provenance/download hints used during package preparation,
        # not runtime inputs. Keep source_commit and all integrity/license data.
        if "source" in item:
            item.pop("source")
            removed += 1
        upstream = item.get("upstream_release")
        if isinstance(upstream, dict) and "download_url" in upstream:
            upstream.pop("download_url")
            removed += 1
            if not upstream:
                item.pop("upstream_release", None)

    encoded = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if re.search(r"https?://", encoded, re.I):
        raise SystemExit("External URL remains in Yandex bundled-addons manifest")
    for item in data["items"]:
        if not item.get("asset") or not item.get("license") or not item.get("sha256"):
            raise SystemExit("Manifest cleanup removed a required local asset/license/hash field")
    path.write_text(encoded, encoding="utf-8")
    print(f"Removed {removed} unused external URL fields from {path.name}.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    loader = dist / "openttd-bundled-addons.js"
    manifest = dist / ADDON_MANIFEST_NAME
    if not loader.is_file():
        raise SystemExit(f"Missing Yandex bundled-addons runtime: {loader}")
    if not manifest.is_file():
        raise SystemExit(f"Missing Yandex bundled-addons manifest: {manifest}")

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
    scrub_unused_manifest_urls(manifest)

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
