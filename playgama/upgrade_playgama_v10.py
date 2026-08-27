#!/usr/bin/env python3
"""Upgrade an assembled OpenTTD Playgama package to the v10 delivery layout."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

BRIDGE_URL = "https://bridge.playgama.com/v1/stable/playgama-bridge.js"
BRIDGE_SCRIPT = f'<script src="{BRIDGE_URL}"></script>'
CLOUD_SCRIPT = '<script src="openttd-playgama-cloud-saves.js"></script>'
FIXES_SCRIPT = '<script src="openttd-playgama-fixes.js"></script>'
VIEWPORT_SCRIPT = '<script src="openttd-full-viewport.js"></script>'
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

    manifest["manifest_version"] = "2026-08-27-v11-ui-polish"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_doctype(html: str) -> str:
    """Force standards mode even for historical minified <!doctypehtml> shells."""
    normalized, count = re.subn(
        r"^\s*<!doctype\s*html\s*>",
        "<!DOCTYPE html>",
        html,
        count=1,
        flags=re.I,
    )
    if count == 0:
        normalized = "<!DOCTYPE html>" + html.lstrip()
    return normalized


def patch_runtime_fixes(dist: Path) -> None:
    """Remove the forced 16:9 letterbox and avoid pre-runtime native/audio calls."""
    path = dist / "openttd-playgama-fixes.js"
    if not path.is_file():
        raise SystemExit("openttd-playgama-fixes.js is missing")
    text = path.read_text(encoding="utf-8")

    scale_pattern = re.compile(
        r"\n  /\* Keep the native 16:9 OpenTTD surface intact.*?\n  document\.head\.appendChild\(style\);\n",
        re.S,
    )
    full_bleed = r'''
  /* Use the complete platform viewport. OpenTTD/SDL handles arbitrary browser
     aspect ratios; forcing a centred 16:9 CSS surface created visible side bars
     on wide Yandex/Playgama viewports. openttd-full-viewport.js also resizes the
     backing SDL canvas, so this CSS does not stretch or distort a 16:9 surface. */
  const style = document.createElement('style');
  style.id = 'openttd-playgama-scale-fix';
  style.textContent = `
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: #000; }
    body { position: relative; }
    div.background { position: fixed !important; inset: 0 !important; width: 100vw !important; height: 100vh !important; background-size: cover !important; background-position: center !important; }
    canvas.emscripten {
      position: fixed !important;
      inset: 0 !important;
      left: 0 !important;
      top: 0 !important;
      transform: none !important;
      width: 100vw !important;
      height: 100vh !important;
      max-width: none !important;
      max-height: none !important;
      aspect-ratio: auto !important;
    }
  `;
  document.head.appendChild(style);
'''
    text, scale_count = scale_pattern.subn("\n" + full_bleed.lstrip("\n"), text, count=1)
    if scale_count != 1:
        raise SystemExit(f"Could not replace 16:9 viewport fix (matches={scale_count})")

    old_pause = "if (Module?._em_openttd_set_platform_pause) Module._em_openttd_set_platform_pause(paused ? 1 : 0);"
    new_pause = (
        "if (typeof Module !== 'undefined' && Module.calledRun === true && "
        "typeof Module._em_openttd_set_platform_pause === 'function') "
        "Module._em_openttd_set_platform_pause(paused ? 1 : 0);"
    )
    if text.count(old_pause) != 1:
        raise SystemExit("Unexpected native pause call count in Playgama fixes")
    text = text.replace(old_pause, new_pause, 1)

    old_resume = "if (ctx?.state === 'suspended') ctx.resume().catch(() => {});"
    new_resume = (
        "if (ctx?.state === 'suspended' && (navigator.userActivation?.hasBeenActive ?? true)) "
        "ctx.resume().catch(() => {});"
    )
    if text.count(old_resume) != 1:
        raise SystemExit("Unexpected AudioContext resume call count in Playgama fixes")
    text = text.replace(old_resume, new_resume, 1)

    path.write_text(text, encoding="utf-8")


def install_viewport_helper(dist: Path) -> None:
    source = Path(__file__).resolve().with_name("openttd-full-viewport.js")
    if not source.is_file():
        raise SystemExit(f"Full-viewport helper is missing: {source}")
    shutil.copy2(source, dist / "openttd-full-viewport.js")


def patch_index(dist: Path) -> None:
    path = dist / "index.html"
    html = normalize_doctype(path.read_text(encoding="utf-8"))

    # Old v8/v10 artifacts can contain the accidental /v2/stable reference.
    # Normalize all historical CDN forms to the documented stable JS Core URL.
    html = re.sub(
        r'<script\s+src=["\']https://bridge\.playgama\.com/(?:v1/(?:stable|latest)|v2/(?:stable|latest)|latest)/playgama-bridge\.js["\']\s*></script>',
        BRIDGE_SCRIPT,
        html,
        flags=re.I,
    )
    if BRIDGE_URL not in html:
        raise SystemExit("Could not normalize Playgama Bridge bootstrap")
    if "bridge.playgama.com/v2/" in html:
        raise SystemExit("Legacy/invalid Playgama Bridge v2 reference remains")

    html = html.replace(CLOUD_SCRIPT, "")
    html = html.replace(VIEWPORT_SCRIPT, "")
    if FIXES_SCRIPT in html:
        html = html.replace(FIXES_SCRIPT, FIXES_SCRIPT + VIEWPORT_SCRIPT + CLOUD_SCRIPT, 1)
    elif ADDONS_SCRIPT in html:
        html = html.replace(ADDONS_SCRIPT, VIEWPORT_SCRIPT + CLOUD_SCRIPT + ADDONS_SCRIPT, 1)
    else:
        raise SystemExit("Could not find Playgama runtime script insertion point")
    if html.count(CLOUD_SCRIPT) != 1:
        raise SystemExit("Cloud save script insertion is not unique")
    if html.count(VIEWPORT_SCRIPT) != 1:
        raise SystemExit("Full-viewport helper insertion is not unique")
    if not html.startswith("<!DOCTYPE html>"):
        raise SystemExit("index.html did not enter standards mode")
    path.write_text(html, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--loader", type=Path, required=True)
    ap.add_argument("--cloud-saves", type=Path, required=True)
    ap.add_argument("--adapter", type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    if not (dist / "index.html").is_file():
        raise SystemExit("index.html is missing from package root")
    if not (dist / "OPENTTD-BUNDLED-ADDONS.json").is_file():
        raise SystemExit("OPENTTD-BUNDLED-ADDONS.json is missing")

    normalize_addon_assets(dist)
    shutil.copy2(args.loader, dist / "openttd-bundled-addons.js")
    shutil.copy2(args.cloud_saves, dist / "openttd-playgama-cloud-saves.js")
    shutil.copy2(args.adapter, dist / "playgama-yandex-compat.js")
    install_viewport_helper(dist)
    patch_runtime_fixes(dist)
    patch_index(dist)

    (dist / "PLAYGAMA-V10-CHANGES.txt").write_text(
        "OpenTTD Playgama v11 launch-safe UI refresh\n"
        "============================================\n"
        "- Uses the documented Playgama Bridge JS Core stable v1 CDN.\n"
        "- Optional NewGRF/license downloads never block OpenTTD startup.\n"
        "- Uses the entire browser viewport instead of forcing a 16:9 letterbox.\n"
        "- Resizes the SDL backing surface to viewport CSS pixels, avoiding stretched graphics.\n"
        "- Uses standards-mode HTML with a valid <!DOCTYPE html>.\n"
        "- Native pause calls wait until the Emscripten runtime has started.\n"
        "- AudioContext resume is only attempted after user activation.\n"
        "- Uses Playgama Bridge platform_internal storage for cloud saves when available.\n"
        "- Splits .sav data into 64 KiB text chunks and alternates A/B generations.\n"
        "- Keeps local IDBFS/IndexedDB persistence as a fallback.\n"
        "- Uses neutral .bin delivery names for gzip-compressed bundled add-ons.\n",
        encoding="utf-8",
    )

    print("Playgama v11 launch-safe UI refresh applied:", dist)


if __name__ == "__main__":
    main()
