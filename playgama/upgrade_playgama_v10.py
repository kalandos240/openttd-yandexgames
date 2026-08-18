#!/usr/bin/env python3
"""Upgrade an assembled OpenTTD Playgama package to the v10 delivery layout."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

CLOUD_SCRIPT = '<script src="openttd-playgama-cloud-saves.js"></script>'
FIXES_SCRIPT = '<script src="openttd-playgama-fixes.js"></script>'
ADDONS_SCRIPT = '<script src="openttd-bundled-addons.js"></script>'


def normalize_addon_assets(dist: Path) -> None:
    manifest_path = dist / "OPENTTD-BUNDLED-ADDONS.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("Bundled add-on manifest is missing or empty")

    for row in items:
        asset = str(row.get("asset", ""))
        if not asset:
            raise SystemExit(f"Add-on has no asset path: {row!r}")
        source = dist / asset
        if asset.endswith(".gz"):
            target_rel = asset[:-3] + ".bin"
            target = dist / target_rel
            if not source.is_file():
                raise SystemExit(f"Manifest asset is missing: {source}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            source.replace(target)
            row["asset"] = target_rel
        elif asset.endswith(".bin"):
            if not source.is_file():
                raise SystemExit(f"Manifest asset is missing: {source}")
        else:
            raise SystemExit(f"Unexpected bundled asset extension: {asset}")

    manifest["manifest_version"] = "2026-08-18-v10"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_index(dist: Path) -> None:
    path = dist / "index.html"
    html = path.read_text(encoding="utf-8")
    html = html.replace(CLOUD_SCRIPT, "")
    if FIXES_SCRIPT in html:
        html = html.replace(FIXES_SCRIPT, FIXES_SCRIPT + CLOUD_SCRIPT, 1)
    elif ADDONS_SCRIPT in html:
        html = html.replace(ADDONS_SCRIPT, CLOUD_SCRIPT + ADDONS_SCRIPT, 1)
    else:
        raise SystemExit("Could not find Playgama runtime script insertion point")
    if html.count(CLOUD_SCRIPT) != 1:
        raise SystemExit("Cloud save script insertion is not unique")
    path.write_text(html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--loader", type=Path, required=True)
    ap.add_argument("--cloud-saves", type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    if not (dist / "index.html").is_file():
        raise SystemExit("index.html is missing from package root")
    if not (dist / "OPENTTD-BUNDLED-ADDONS.json").is_file():
        raise SystemExit("OPENTTD-BUNDLED-ADDONS.json is missing")

    normalize_addon_assets(dist)
    shutil.copy2(args.loader, dist / "openttd-bundled-addons.js")
    shutil.copy2(args.cloud_saves, dist / "openttd-playgama-cloud-saves.js")
    patch_index(dist)

    (dist / "PLAYGAMA-V10-CHANGES.txt").write_text(
        "OpenTTD Playgama v10\n"
        "====================\n"
        "- Uses Playgama Bridge v2 platform_internal storage for cloud saves.\n"
        "- Splits .sav data into 64 KiB text chunks and alternates A/B generations.\n"
        "- Commits metadata last and verifies restored saves with size + CRC32.\n"
        "- Migrates the legacy openttdSaveV1 snapshot when no v2 cloud slot exists.\n"
        "- Keeps local IDBFS/IndexedDB persistence as a fallback.\n"
        "- Uses neutral .bin delivery names for gzip-compressed bundled add-ons.\n",
        encoding="utf-8",
    )

    print("Playgama v10 package upgrade applied:", dist)


if __name__ == "__main__":
    main()
