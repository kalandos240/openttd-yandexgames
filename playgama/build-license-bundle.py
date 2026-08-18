#!/usr/bin/env python3
"""Build one native-viewable Markdown document containing all distributed licenses."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--repo-license", type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    licenses = dist / "licenses"
    licenses.mkdir(parents=True, exist_ok=True)

    if not args.repo_license.is_file():
        raise SystemExit(f"Repository LICENSE not found: {args.repo_license}")
    port_dir = licenses / "Port"
    port_dir.mkdir(parents=True, exist_ok=True)
    (port_dir / "LICENSE-GPL-2.0.txt").write_bytes(args.repo_license.read_bytes())

    ai_manifest_path = dist / "OPENTTD-CLASSIC-AI-MANIFEST.json"
    addon_manifest_path = dist / "OPENTTD-BUNDLED-ADDONS.json"
    if not ai_manifest_path.is_file() or not addon_manifest_path.is_file():
        raise SystemExit("AI/add-on manifests are required before building licenses")

    ai_manifest = json.loads(read_text(ai_manifest_path))
    addons = json.loads(read_text(addon_manifest_path))

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
        raise SystemExit(f"License bundle cannot be complete; missing add-ons: {sorted(missing)}")

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
        raise SystemExit(f"Required license files are missing: {missing_files}")

    out: list[str] = []
    out.append("# OpenTTD Playgama — licenses and third-party notices")
    out.append("")
    out.append("This document is bundled with the game and can be opened from the main menu using the Licenses / Лицензии button.")
    out.append("It lists the license of the port, OpenTTD, bundled base sets, AI packages, AI libraries and every optional NewGRF/base-graphics add-on shipped in this build.")
    out.append("")

    out.append("# Component index")
    out.append("")
    out.append("## Core and port")
    out.append("- OpenTTD 15.3 browser/Playgama port — GNU GPL v2; see licenses/Port/LICENSE-GPL-2.0.txt and licenses/OpenTTD/COPYING.md.")
    out.append("- OpenTTD third-party libraries — see the individual Catch2, fmt, ICU, LLVM CMake, nlohmann/json, social-integration API and Squirrel notices below.")
    out.append("- OpenGFX 8.0, OpenSFX 1.0.3 and OpenMSX 0.4.2 — see their complete bundled license files below.")
    out.append("")

    out.append("## Bundled AI and AI libraries")
    seen_ai = set()
    for row in ai_manifest:
        key = (row.get("content_id"), row.get("filename"), row.get("license"))
        if key in seen_ai:
            continue
        seen_ai.add(key)
        out.append(f"- {row.get('filename')} ({row.get('content_id')}) — {row.get('license')}; GNU GPL v2 text is included below.")
    out.append("")

    out.append("## Optional add-ons (disabled by default)")
    for cid in sorted(required_addons):
        row = addon_rows[cid]
        source = row.get("source", "")
        out.append(f"- {row.get('name')} {row.get('version', '')} ({cid}) — {row.get('license')}; source: {source}")
    out.append("")
    out.append("FIRS Industries 5 and GIST are alternative industry sets and should not be enabled together in the same new game.")
    out.append("")

    out.append("# Source-code and distribution notices")
    for name in ("SOURCE_CODE.txt", "THIRD-PARTY-ADDONS.md", "NOTICE.txt", "PLAYGAMA-INTEGRATION.txt"):
        path = dist / name
        if path.is_file():
            out.append(f"## {name}")
            out.append("")
            out.append(read_text(path).strip())
            out.append("")

    out.append("# Full license texts")
    out.append("")
    for path in required_legal_files:
        rel = path.relative_to(dist).as_posix()
        out.append(f"## {rel}")
        out.append("")
        out.append(read_text(path).strip())
        out.append("")

    output = "\n".join(out).rstrip() + "\n"
    target = dist / "PLAYGAMA-ALL-LICENSES.md"
    target.write_text(output, encoding="utf-8")

    if target.stat().st_size < 100_000:
        raise SystemExit(f"Combined license document is suspiciously small: {target.stat().st_size} bytes")

    text = read_text(target)
    required_names = [addon_rows[cid]["name"] for cid in required_addons]
    required_names += ["SimpleAI", "OpenTTD", "OpenGFX", "OpenSFX", "OpenMSX"]
    absent = [name for name in required_names if name not in text]
    if absent:
        raise SystemExit(f"Combined license index is incomplete: {absent}")

    print(f"Complete in-game license bundle: {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
