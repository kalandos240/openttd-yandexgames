#!/usr/bin/env python3
"""Remove Playgama-specific runtime naming and stale platform notices from Yandex.

The Yandex package reuses the verified browser platform baseline, but must not
ship executable Playgama integration or misleading Playgama-facing release
notices. Keep all third-party/full license texts and source-offer information,
while removing the inactive Playgama integration section and neutralising stale
platform labels in human-readable release documents.
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


def neutralize_release_docs(dist: Path) -> None:
    """Remove inactive Playgama release notes without touching license bodies."""
    license_bundle = dist / NEW_LICENSE_NAME
    text = license_bundle.read_text(encoding="utf-8")

    # The baseline legal bundle concatenates a Playgama integration changelog
    # before the full license texts. It is not a license and is false for the
    # Yandex package, so remove exactly that section. Everything from
    # '# Full license texts' onwards remains byte-for-byte identical.
    integration = re.compile(
        r"\n## PLAYGAMA-INTEGRATION\.txt\n.*?(?=\n# Full license texts\n)",
        re.S,
    )
    text, removed = integration.subn("\n", text, count=1)
    if removed != 1:
        raise SystemExit(f"Expected one stale Playgama integration section, removed {removed}")

    # Only the release/index prose before the immutable full-license corpus has
    # stale platform naming. Rebrand that prefix, leaving legal texts untouched.
    marker = "\n# Full license texts\n"
    if marker not in text:
        raise SystemExit("Combined license bundle lost '# Full license texts' marker")
    prefix, license_texts = text.split(marker, 1)
    prefix = prefix.replace("Playgama", "Yandex Games")
    prefix = prefix.replace("PLAYGAMA", "YANDEX GAMES")
    text = prefix + marker + license_texts
    license_bundle.write_text(text, encoding="utf-8")

    replacements = {
        "NOTICE.txt": (
            ("OpenTTD 15.3 - Playgama WebAssembly edition", "OpenTTD 15.3 - Yandex Games WebAssembly edition"),
            ("Playgama integration and WebAssembly build modifications", "Yandex Games integration and WebAssembly build modifications"),
        ),
        "SOURCE_CODE.txt": (
            ("OpenTTD 15.3 - Playgama WebAssembly edition", "OpenTTD 15.3 - Yandex Games WebAssembly edition"),
            ("Web/Playgama port source, patches and reproducible build scripts:", "Web/Yandex Games port source, patches and reproducible build scripts:"),
        ),
        "BUNDLED-ADDONS.md": (
            ("Optional bundled add-ons for the Playgama build", "Optional bundled add-ons for the Yandex Games build"),
            ("The Playgama build ships", "The Yandex Games build ships"),
            ("in the Playgama package", "in the Yandex Games package"),
            ("the Playgama 300 MB unpacked-size ceiling", "the platform package-size ceiling"),
        ),
    }
    for name, pairs in replacements.items():
        path = dist / name
        if not path.is_file():
            raise SystemExit(f"Expected Yandex release document is missing: {name}")
        body = path.read_text(encoding="utf-8")
        for old, new in pairs:
            body = body.replace(old, new)
        path.write_text(body, encoding="utf-8")

    # No Yandex-facing human-readable document may claim this is a Playgama
    # release. Source/license URLs for actual upstream components remain intact.
    for name in (NEW_LICENSE_NAME, "NOTICE.txt", "SOURCE_CODE.txt", "BUNDLED-ADDONS.md"):
        body = (dist / name).read_text(encoding="utf-8")
        if re.search(r"playgama", body, re.I):
            raise SystemExit(f"Stale Playgama release text remains in Yandex document: {name}")


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

    neutralize_release_docs(dist)

    if not new_license.is_file() or new_license.stat().st_size < 100_000:
        raise SystemExit("Neutral Yandex license bundle is missing or unexpectedly small")

    print(f"Yandex runtime and release notices neutralized; full license texts preserved: {new_license}")


if __name__ == "__main__":
    main()
