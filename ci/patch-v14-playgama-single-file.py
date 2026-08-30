#!/usr/bin/env python3
"""Apply Playgama hardening to the rebuilt OpenTTD 15.3 single-file runtime.

The rebuilt Emscripten bundle minifies the startup callback name, so this patch
matches the SDK wait gate structurally instead of relying on the historical
`finish_startup` identifier.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

PLAYGAMA_BRIDGE_URL = "https://bridge.playgama.com/v1.31.0/playgama-bridge.js"


def load_shared() -> object:
    path = Path(__file__).with_name("patch-v14-performance-package.py")
    spec = importlib.util.spec_from_file_location("v14_shared_hardening", path)
    if spec is None or spec.loader is None:
        raise SystemExit("Could not load shared v14 hardening module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patch_index(dist: Path) -> None:
    path = dist / "index.html"
    text = path.read_text(encoding="utf-8")
    stable = '<script src="https://bridge.playgama.com/v1/stable/playgama-bridge.js"></script>'
    loader_tag = '<script src="platform-bridge-loader.js"></script>'
    if stable in text:
        text = text.replace(stable, loader_tag, 1)
    elif loader_tag not in text:
        raise SystemExit("Playgama Bridge loader insertion point was not found")
    path.write_text(text, encoding="utf-8")


def write_loader(dist: Path) -> None:
    text = f'''/* Optional non-blocking Playgama Bridge loader. OpenTTD core is fully local. */
(() => {{
  'use strict';
  window.__openttdPlatformStartupIndependent = true;
  if (window.playgamaBridgeScriptReady) return;
  if (location.protocol === 'file:') {{
    window.__openttdDirectFileLaunch = true;
    window.playgamaBridgeScriptReady = Promise.resolve(null);
    return;
  }}
  window.playgamaBridgeScriptReady = new Promise((resolve) => {{
    const script = document.createElement('script');
    script.src = '{PLAYGAMA_BRIDGE_URL}';
    script.async = true;
    script.crossOrigin = 'anonymous';
    let done = false;
    const finish = (value) => {{ if (done) return; done = true; clearTimeout(timer); resolve(value); }};
    script.onload = () => finish(window.bridge || null);
    script.onerror = () => {{ console.warn('[Playgama/OpenTTD] Optional Bridge failed to load; the game remains available.'); finish(null); }};
    const timer = setTimeout(() => {{ console.warn('[Playgama/OpenTTD] Optional Bridge timed out; game startup is not blocked.'); finish(null); }}, 5000);
    document.head.appendChild(script);
  }});
}})();
'''
    (dist / "platform-bridge-loader.js").write_text(text, encoding="utf-8")


def patch_adapter(dist: Path) -> None:
    path = dist / "playgama-yandex-compat.js"
    text = path.read_text(encoding="utf-8")
    anchor = "  const initializeBridge = async () => {\n    if (!window.bridge || typeof window.bridge.initialize !== 'function') {\n"
    if "await window.playgamaBridgeScriptReady" not in text:
        if text.count(anchor) != 1:
            raise SystemExit("Playgama adapter initialization anchor was not found exactly once")
        text = text.replace(
            anchor,
            "  const initializeBridge = async () => {\n    if (window.playgamaBridgeScriptReady) {\n      try { await window.playgamaBridgeScriptReady; } catch (_) {}\n    }\n    if (!window.bridge || typeof window.bridge.initialize !== 'function') {\n",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_runtime_startup(dist: Path) -> None:
    path = dist / "openttd-runtime.js"
    text = path.read_text(encoding="utf-8")
    if "window.__openttdPlatformStartupIndependent===true" in text:
        return

    legacy = 'if(window.yandexGamesSDKReady){Promise.race([window.yandexGamesSDKReady,new Promise(resolve=>setTimeout(()=>resolve(null),3e3))]).then(finish_startup,finish_startup)}else{finish_startup()}'
    if legacy in text:
        replacement = 'if(window.__openttdPlatformStartupIndependent===true){finish_startup()}else if(window.yandexGamesSDKReady){Promise.race([window.yandexGamesSDKReady,new Promise(resolve=>setTimeout(()=>resolve(null),3e3))]).then(finish_startup,finish_startup)}else{finish_startup()}'
        text = text.replace(legacy, replacement, 1)
    else:
        # Current single-file Emscripten form, e.g.:
        # window.yandexGamesSDKReady?Promise.race([...]).then(Q,Q):Q()
        pattern = re.compile(
            r"window\.yandexGamesSDKReady\?Promise\.race\(\[window\.yandexGamesSDKReady,new Promise\(\((?P<resolver>[A-Za-z_$][\w$]*)=>setTimeout\(\(\(\)=>(?P=resolver)\(null\)\),3e3\)\)\)\]\)\.then\((?P<finish>[A-Za-z_$][\w$]*),(?P=finish)\):(?P=finish)\(\)"
        )
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise SystemExit(f"Expected one minified Playgama/Yandex startup SDK gate, found {len(matches)}")
        match = matches[0]
        finish = match.group("finish")
        original = match.group(0)
        replacement = f"window.__openttdPlatformStartupIndependent===true?{finish}():{original}"
        text = text[: match.start()] + replacement + text[match.end() :]

    if "window.__openttdPlatformStartupIndependent===true" not in text:
        raise SystemExit("Playgama startup independence marker was not installed")
    path.write_text(text, encoding="utf-8")


def validate(dist: Path) -> None:
    runtime = (dist / "openttd-runtime.js").read_text(encoding="utf-8")
    html = (dist / "index.html").read_text(encoding="utf-8")
    loader = (dist / "platform-bridge-loader.js").read_text(encoding="utf-8")
    adapter = (dist / "playgama-yandex-compat.js").read_text(encoding="utf-8")
    ranking = (dist / "openttd-ranking-core.js").read_text(encoding="utf-8")
    global_ranking = (dist / "openttd-global-ranking.js").read_text(encoding="utf-8")

    if "window.__openttdPlatformStartupIndependent===true" not in runtime:
        raise SystemExit("Runtime still waits on the platform SDK before core startup")
    if "https://bridge.playgama.com" in html:
        raise SystemExit("Parser-active external Playgama Bridge remains in index.html")
    if PLAYGAMA_BRIDGE_URL not in loader or "script.async = true" not in loader:
        raise SystemExit("Pinned non-blocking Playgama Bridge loader is missing")
    if "await window.playgamaBridgeScriptReady" not in adapter:
        raise SystemExit("Playgama compatibility adapter does not await optional Bridge initialization")
    if "Module.calledRun === true" not in ranking or "typeof HEAP8 !== 'undefined'" not in ranking:
        raise SystemExit("Playgama ranking runtime-ready guard is missing")
    if "const MAX_SCORE = 1000" not in global_ranking:
        raise SystemExit("Playgama global leaderboard score range is not bounded to 1000")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()

    shared = load_shared()
    shared.patch_ranking(dist / "openttd-ranking-core.js", False)
    shared.patch_ranking(dist / "openttd-global-ranking.js", True)
    patch_index(dist)
    write_loader(dist)
    patch_adapter(dist)
    patch_runtime_startup(dist)
    validate(dist)
    print("v14 single-file Playgama hardening applied")


if __name__ == "__main__":
    main()
