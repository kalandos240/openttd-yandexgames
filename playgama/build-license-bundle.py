#!/usr/bin/env python3
# Release trigger note: this validator is part of the optimized single-file v14 pipeline.
"""Validate the minimal static legal payload for browser releases.

Older builds generated one large PLAYGAMA-ALL-LICENSES.md document so a custom
native main-menu window could display every license inside OpenTTD. The runtime
window and its fetch/copy path have been removed. Keeping the combined document
would only duplicate texts already distributed under licenses/ and increase the
package/runtime surface.

This script therefore does *not* build an in-game document. It normalizes the
small platform notices, verifies that the legally required static license/source
files are still present, and deletes stale combined license documents left by an
older package base.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


PORT_SOURCE_POINTER = "https://api.github.com/repositories/1328069895"
LEGACY_PORT_SOURCE_URL = "https://github.com/kalandos240/openttd-yandexgames"
LEGAL_REPLACEMENTS = (
    ("Yandex Games WebAssembly edition", "Playgama WebAssembly edition"),
    (
        "Yandex Games port source, patches and reproducible build scripts:",
        "Web/Playgama port source, patches and reproducible build scripts:",
    ),
    (
        "Yandex Games integration and WebAssembly build modifications",
        "Playgama integration and WebAssembly build modifications",
    ),
    (LEGACY_PORT_SOURCE_URL, PORT_SOURCE_POINTER),
)

STALE_COMBINED_DOCUMENTS = (
    "PLAYGAMA-ALL-LICENSES.md",
    "THIRD-PARTY-LICENSES.md",
    "ALL-LICENSES.md",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def normalize_playgama_legal_text(text: str) -> str:
    for old, new in LEGAL_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def normalize_legacy_legal_files(dist: Path) -> None:
    """Remove obsolete platform branding without removing legal obligations."""
    for name in ("NOTICE.txt", "SOURCE_CODE.txt"):
        path = dist / name
        if not path.is_file():
            continue
        text = normalize_playgama_legal_text(read_text(path))
        lowered = text.lower()
        if "yandex" in lowered or "яндекс" in lowered:
            raise SystemExit(f"Legacy platform branding remains in {name}")
        path.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--repo-license", type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    licenses = dist / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)
    normalize_legacy_legal_files(dist)

    if not args.repo_license.is_file():
        raise SystemExit(f"Repository LICENSE not found: {args.repo_license}")
    port_dir = licenses / "Port"
    port_dir.mkdir(parents=True, exist_ok=True)
    (port_dir / "LICENSE-GPL-2.0.txt").write_bytes(args.repo_license.read_bytes())

    ai_manifest_path = dist / "OPENTTD-CLASSIC-AI-MANIFEST.json"
    addon_manifest_path = dist / "OPENTTD-BUNDLED-ADDONS.json"
    if not ai_manifest_path.is_file() or not addon_manifest_path.is_file():
        raise SystemExit("AI/add-on manifests are required before legal validation")

    ai_manifest = json.loads(read_text(ai_manifest_path))
    addons = json.loads(read_text(addon_manifest_path))
    if not isinstance(ai_manifest, list) or not ai_manifest:
        raise SystemExit("AI manifest is empty or invalid")

    required_addons = {
        "newgrf/43411223",
        "newgrf/f1250009",
        "newgrf/9787eafe",
        "newgrf/55440100",
        "newgrf/474c0501",
        "newgrf/4f475a01",
        "base-graphics/6f676678",
    }
    addon_rows = {row["content_id"]: row for row in addons["items"]}
    missing = required_addons - addon_rows.keys()
    if missing:
        raise SystemExit(f"Legal validation cannot be complete; missing add-ons: {sorted(missing)}")

    # These remain distribution-only files. Nothing in the browser runtime
    # reads them, mounts them into IDBFS, or copies them into MEMFS.
    required_legal_files = [
        licenses / "Port" / "LICENSE-GPL-2.0.txt",
        licenses / "OpenTTD" / "COPYING.md",
        licenses / "OpenTTD" / "CATCH2-LICENSE.txt",
        licenses / "OpenTTD" / "FMT-LICENSE.rst",
        licenses / "OpenTTD" / "ICU-LICENSE.txt",
        licenses / "OpenTTD" / "LLVM-CMAKE-LICENSE.txt",
        licenses / "OpenTTD" / "NLOHMANN-LICENSE.MIT",
        licenses / "OpenTTD" / "SOCIAL-INTEGRATION-API-LICENSE.txt",
        licenses / "OpenTTD" / "SQUIRREL-COPYRIGHT.txt",
        licenses / "OpenGFX" / "opengfx-8.0__license.txt",
        licenses / "OpenSFX" / "opensfx-1.0.3__license.txt",
        licenses / "OpenMSX" / "openmsx-0.4.2__license.txt",
        licenses / "addons" / "iron-horse-GPL-2.0.txt",
        licenses / "addons" / "firs-GPL-2.0.txt",
        licenses / "addons" / "road-hog-release-notice.txt",
        licenses / "addons" / "GIST-GPL-2.0.txt",
        licenses / "addons" / "EarlyVehicle-GPL-2.0.txt",
        licenses / "addons" / "OpenGFX2-upstream-license.txt",
    ]
    missing_files = [str(p.relative_to(dist)) for p in required_legal_files if not p.is_file()]
    if missing_files:
        raise SystemExit(f"Required static legal files are missing: {missing_files}")

    for required_notice in ("NOTICE.txt", "SOURCE_CODE.txt"):
        path = dist / required_notice
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Required distribution notice is missing: {required_notice}")

    removed = []
    for name in STALE_COMBINED_DOCUMENTS:
        path = dist / name
        if path.exists():
            path.unlink()
            removed.append(name)

    leftovers = [name for name in STALE_COMBINED_DOCUMENTS if (dist / name).exists()]
    if leftovers:
        raise SystemExit(f"Combined runtime license documents remain: {leftovers}")

    print(
        "Static legal payload validated; no in-game/combined license document generated. "
        f"Removed stale documents: {removed or 'none'}"
    )


if __name__ == "__main__":
    main()
