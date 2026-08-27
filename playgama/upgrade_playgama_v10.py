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
RANKING_SCRIPT = '<script src="openttd-ranking-core.js"></script>'
GLOBAL_RANKING_SCRIPT = '<script src="openttd-global-ranking.js"></script>'
ADDONS_SCRIPT = '<script src="openttd-bundled-addons.js"></script>'
LEADERBOARD_NAME = "companyrating"


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
     on wide platform viewports. openttd-full-viewport.js also resizes the
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


def patch_playgama_adapter(dist: Path) -> None:
    """Keep the game launchable if Bridge is unavailable and respect autoplay policy."""
    path = dist / "playgama-yandex-compat.js"
    if not path.is_file():
        raise SystemExit("playgama-yandex-compat.js is missing")
    text = path.read_text(encoding="utf-8")

    old_audio = "if (context?.state === 'suspended') context.resume?.().catch?.(() => {});"
    new_audio = (
        "if (context?.state === 'suspended' && (navigator.userActivation?.hasBeenActive ?? true)) "
        "context.resume?.().catch?.(() => {});"
    )
    if new_audio not in text:
        if text.count(old_audio) != 1:
            raise SystemExit(f"Unexpected Playgama adapter AudioContext resume count: {text.count(old_audio)}")
        text = text.replace(old_audio, new_audio, 1)

    old_init = """  window.YaGames = {
    init() {
      return window.playgamaBridgeReady.then((bridge) => {
        if (!bridge) throw new Error('Playgama Bridge initialization failed');
        return createSdk(bridge);
      });
    }
  };
"""
    new_init = """  window.YaGames = {
    init() {
      return window.playgamaBridgeReady.then((bridge) => {
        if (!bridge) {
          console.warn('[Playgama] Bridge unavailable; starting OpenTTD with offline platform fallback.');
          return createSdk({});
        }
        return createSdk(bridge);
      });
    }
  };
"""
    if new_init not in text:
        if text.count(old_init) != 1:
            raise SystemExit(f"Unexpected Playgama YaGames.init block count: {text.count(old_init)}")
        text = text.replace(old_init, new_init, 1)

    required = (
        "navigator.userActivation?.hasBeenActive",
        "starting OpenTTD with offline platform fallback",
        "return createSdk({});",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Playgama adapter launch-safety marker missing: {marker}")
    path.write_text(text, encoding="utf-8")


def install_shared_helpers(dist: Path) -> None:
    root = Path(__file__).resolve().parent
    for filename in ("openttd-full-viewport.js", "openttd-ranking-core.js", "openttd-global-ranking.js"):
        source = root / filename
        if not source.is_file():
            raise SystemExit(f"Shared browser helper is missing: {source}")
        shutil.copy2(source, dist / filename)


def validate_global_ranking_provider(dist: Path) -> None:
    """Fail packaging if the Playgama leaderboard bridge silently regresses."""
    path = dist / "openttd-global-ranking.js"
    if not path.is_file():
        raise SystemExit("Playgama global ranking provider is missing from package")
    text = path.read_text(encoding="utf-8")

    required = (
        f"LEADERBOARD_NAME = '{LEADERBOARD_NAME}'",
        "Number.MAX_SAFE_INTEGER",
        "playgamaBridgeReady",
        "leaderboards.getEntries",
        "leaderboards.setScore",
        "player.authorize",
        "isAuthorizationSupported",
        "FETCH_FAILURE_BACKOFF_MS",
        "window.OpenTTDGlobalRanking",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Playgama global ranking provider is missing required marker: {marker}")

    forbidden = (
        "LEADERBOARD_NAME = 'company_rating'",
        "leaderboards.showNativePopup(",
    )
    for marker in forbidden:
        if marker in text:
            raise SystemExit(f"Unsafe/stale Playgama ranking marker remains: {marker}")

    # Startup polling must remain passive: authorization is only available via
    # the explicit requestAuth() entry point invoked by the native ranking UI.
    request_auth_pos = text.find("const requestAuth = async () =>")
    authorize_pos = text.find("bridge.player.authorize({})")
    if request_auth_pos < 0 or authorize_pos < request_auth_pos:
        raise SystemExit("Playgama authorization is not confined to explicit requestAuth()")


def patch_index(dist: Path) -> None:
    path = dist / "index.html"
    html = normalize_doctype(path.read_text(encoding="utf-8"))

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
    html = html.replace(RANKING_SCRIPT, "")
    html = html.replace(GLOBAL_RANKING_SCRIPT, "")
    if FIXES_SCRIPT in html:
        html = html.replace(FIXES_SCRIPT, FIXES_SCRIPT + VIEWPORT_SCRIPT + RANKING_SCRIPT + GLOBAL_RANKING_SCRIPT + CLOUD_SCRIPT, 1)
    elif ADDONS_SCRIPT in html:
        html = html.replace(ADDONS_SCRIPT, VIEWPORT_SCRIPT + RANKING_SCRIPT + GLOBAL_RANKING_SCRIPT + CLOUD_SCRIPT + ADDONS_SCRIPT, 1)
    else:
        raise SystemExit("Could not find Playgama runtime script insertion point")
    if html.count(CLOUD_SCRIPT) != 1:
        raise SystemExit("Cloud save script insertion is not unique")
    if html.count(VIEWPORT_SCRIPT) != 1:
        raise SystemExit("Full-viewport helper insertion is not unique")
    if html.count(RANKING_SCRIPT) != 1:
        raise SystemExit("Ranking core insertion is not unique")
    if html.count(GLOBAL_RANKING_SCRIPT) != 1:
        raise SystemExit("Global ranking provider insertion is not unique")
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
    patch_playgama_adapter(dist)
    install_shared_helpers(dist)
    validate_global_ranking_provider(dist)
    patch_runtime_fixes(dist)
    patch_index(dist)

    (dist / "PLAYGAMA-V10-CHANGES.txt").write_text(
        "OpenTTD browser v12 ranking-ready base\n"
        "======================================\n"
        "- Uses the documented stable platform bridge.\n"
        "- Bridge failure no longer blocks OpenTTD startup; an offline platform fallback is used.\n"
        "- Optional NewGRF/license downloads never block OpenTTD startup.\n"
        "- Uses the entire browser viewport instead of forcing a 16:9 letterbox.\n"
        "- Resizes the SDL backing surface to viewport CSS pixels, avoiding stretched graphics.\n"
        "- Uses standards-mode HTML with a valid <!DOCTYPE html>.\n"
        "- Native pause calls wait until the Emscripten runtime has started.\n"
        "- AudioContext resume is only attempted after user activation, including the Playgama adapter.\n"
        f"- Includes local and global ranking; Playgama leaderboard id is {LEADERBOARD_NAME}.\n"
        "- Global leaderboard polling never opens authorization or native popups automatically.\n"
        "- Keeps local IDBFS/IndexedDB persistence as a fallback.\n"
        "- Uses neutral .bin delivery names for gzip-compressed bundled add-ons.\n",
        encoding="utf-8",
    )

    print("Browser ranking-ready Playgama base applied:", dist)


if __name__ == "__main__":
    main()
