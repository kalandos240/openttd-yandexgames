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


def install_optimized_global_ranking(dist: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "playgama" / "openttd-global-ranking.js"
    target = dist / "openttd-global-ranking.js"
    if not source.is_file() or not target.is_file():
        raise SystemExit("Optimized global ranking source/target is missing for Playgama")
    text = source.read_text(encoding="utf-8")
    for marker in (
        "const MAX_SCORE = 1000",
        "playgamaBridgeProvider: true",
        "startupEntryRequestsDeferred: true",
        "window.playgamaBridgeReady",
        "bridge.leaderboards.getEntries",
        "bridge.leaderboards.setScore",
        "networkStats.entryRequests++",
        "Module.calledRun === true",
        "typeof HEAP8 !== 'undefined'",
    ):
        if marker not in text:
            raise SystemExit(f"Optimized Playgama ranking provider is missing marker: {marker}")
    target.write_text(text, encoding="utf-8")


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

    /* The compatibility adapter historically performed an unconditional
       storage get+set marker on every launch. Cloud saves already probe and
       cache storage availability lazily, so this marker creates pure startup
       traffic and a write with no gameplay value. */
    storage_probe = """    // Storage availability must never be a startup gate.
    try {
      const markerKey = '__openttd_playgama_bridge';
      await Promise.race([
        (async () => {
          await bridge.storage?.get?.(markerKey);
          await bridge.storage?.set?.(markerKey, { updatedAt: Date.now() });
        })(),
        new Promise((resolve) => setTimeout(resolve, 1000)),
      ]);
    } catch (error) {
      console.info('[Playgama] storage marker unavailable; local persistence will still work.', error);
    }

"""
    storage_probe_replacement = """    // Cloud storage is checked lazily by the cloud-save layer. Avoid an
    // unconditional startup read+write that cannot affect core game startup.
    window.__openttdPlaygamaStartupStorageProbeDisabled = true;

"""
    if storage_probe in text:
        text = text.replace(storage_probe, storage_probe_replacement, 1)
    elif "window.__openttdPlaygamaStartupStorageProbeDisabled = true;" not in text:
        raise SystemExit("Playgama startup storage probe block was not found")

    if "__openttd_playgama_bridge" in text:
        raise SystemExit("Redundant Playgama startup storage marker remains in compatibility adapter")
    path.write_text(text, encoding="utf-8")


def patch_cloud_network(dist: Path) -> None:
    """Suppress unchanged Playgama storage reads/writes between real save changes."""
    path = dist / "openttd-playgama-cloud-saves.js"
    text = path.read_text(encoding="utf-8")
    if "__openttdPlaygamaCloudNetworkStats" in text:
        return

    state_anchor = "  let latestRemoteMeta = null;\n"
    state_new = state_anchor + """  let latestRemoteConfigText = null;
  const cloudNetworkStats = window.__openttdPlaygamaCloudNetworkStats = {
    configDedupEnabled: true,
    saveMetadataFastPath: true,
    skippedConfigWrites: 0,
    skippedSaveMetadataReads: 0,
  };
"""
    if text.count(state_anchor) != 1:
        raise SystemExit("Playgama cloud state anchor was not found")
    text = text.replace(state_anchor, state_new, 1)

    old_config = """  async function writeConfig(FS, personalDir) {
    const config = {
      version: CLOUD_VERSION,
      updatedAt: Date.now(),
      config: readConfig(FS, personalDir),
    };
    await storageSet(CONFIG_KEY, config);
  }
"""
    new_config = """  async function writeConfig(FS, personalDir) {
    const configText = readConfig(FS, personalDir);
    if (configText === latestRemoteConfigText) {
      cloudNetworkStats.skippedConfigWrites++;
      return { state: 'unchanged' };
    }
    const config = {
      version: CLOUD_VERSION,
      updatedAt: Date.now(),
      config: configText,
    };
    await storageSet(CONFIG_KEY, config);
    latestRemoteConfigText = configText;
    return { state: 'uploaded' };
  }
"""
    if text.count(old_config) != 1:
        raise SystemExit("Playgama config upload block was not found")
    text = text.replace(old_config, new_config, 1)

    old_save_prefix = """  async function writeSave(FS, personalDir) {
    const save = newestSave(FS, personalDir);
    if (!save) return { state: 'no-save' };

    let bytes;
    try { bytes = FS.readFile(save.path); }
    catch (error) { throw new Error(`Could not read local save: ${error}`); }
    if (!bytes?.length) return { state: 'empty-save' };
    if (bytes.length > MAX_SAVE_BYTES) {
      console.warn(`[Playgama/OpenTTD] Save is ${bytes.length} bytes; cloud upload skipped above ${MAX_SAVE_BYTES} byte browser safety guard.`);
      return { state: 'too-large', bytes: bytes.length };
    }

    const metas = await readSlotMetas();
    const current = metas[0] || latestRemoteMeta;
    if (metaMatchesLocal(current, save, bytes.length)) {
      return { state: 'unchanged', bytes: bytes.length };
    }

    const targetSlot = current?.slot === 'a' ? 'b' : 'a';
    const base64 = bytesToBase64(bytes);
"""
    new_save_prefix = """  async function writeSave(FS, personalDir) {
    const save = newestSave(FS, personalDir);
    if (!save) return { state: 'no-save' };

    const localSize = Number(save.stat && save.stat.size) || 0;
    if (latestRemoteMeta && metaMatchesLocal(latestRemoteMeta, save, localSize)) {
      cloudNetworkStats.skippedSaveMetadataReads++;
      return { state: 'unchanged', bytes: localSize };
    }

    /* Only ask platform storage for slot metadata after the local save has
       actually diverged from the last known cloud generation. This keeps the
       no-change backup path entirely local. */
    const metas = await readSlotMetas();
    const current = metas[0] || latestRemoteMeta;
    if (metaMatchesLocal(current, save, localSize)) {
      return { state: 'unchanged', bytes: localSize };
    }

    let bytes;
    try { bytes = FS.readFile(save.path); }
    catch (error) { throw new Error(`Could not read local save: ${error}`); }
    if (!bytes?.length) return { state: 'empty-save' };
    if (bytes.length > MAX_SAVE_BYTES) {
      console.warn(`[Playgama/OpenTTD] Save is ${bytes.length} bytes; cloud upload skipped above ${MAX_SAVE_BYTES} byte browser safety guard.`);
      return { state: 'too-large', bytes: bytes.length };
    }

    const targetSlot = current?.slot === 'a' ? 'b' : 'a';
    const base64 = bytesToBase64(bytes);
"""
    if text.count(old_save_prefix) != 1:
        raise SystemExit("Playgama save upload prefix was not found")
    text = text.replace(old_save_prefix, new_save_prefix, 1)

    restore_anchor = """      const configValues = await storageGet([CONFIG_KEY, LEGACY_CONFIG_KEY]);
      if (Array.isArray(configValues)) {
"""
    restore_new = """      const configValues = await storageGet([CONFIG_KEY, LEGACY_CONFIG_KEY]);
      if (Array.isArray(configValues)) {
        const remoteConfig = configValues[0] || configValues[1] || null;
        if (remoteConfig && typeof remoteConfig.config === 'string') {
          latestRemoteConfigText = sanitizeConfig(remoteConfig.config);
        }
"""
    if text.count(restore_anchor) != 1:
        raise SystemExit("Playgama config restore anchor was not found")
    text = text.replace(restore_anchor, restore_new, 1)

    flush_old = """      await writeConfig(FS, personalDir);
      const result = await writeSave(FS, personalDir);
      lastCloudWriteAt = Date.now();
      window.__openttdPlaygamaCloudStatus = {
        available: true,
        version: CLOUD_VERSION,
        backup: result,
        latest: latestRemoteMeta,
      };
"""
    flush_new = """      const configResult = await writeConfig(FS, personalDir);
      const result = await writeSave(FS, personalDir);
      lastCloudWriteAt = Date.now();
      window.__openttdPlaygamaCloudStatus = {
        available: true,
        version: CLOUD_VERSION,
        configBackup: configResult,
        backup: result,
        latest: latestRemoteMeta,
      };
"""
    if text.count(flush_old) != 1:
        raise SystemExit("Playgama cloud flush block was not found")
    text = text.replace(flush_old, flush_new, 1)

    for marker in (
        "__openttdPlaygamaCloudNetworkStats",
        "configDedupEnabled: true",
        "saveMetadataFastPath: true",
        "skippedConfigWrites++",
        "skippedSaveMetadataReads++",
    ):
        if marker not in text:
            raise SystemExit(f"Playgama network-efficiency marker missing: {marker}")

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
    cloud = (dist / "openttd-playgama-cloud-saves.js").read_text(encoding="utf-8")

    if "window.__openttdPlatformStartupIndependent===true" not in runtime:
        raise SystemExit("Runtime still waits on the platform SDK before core startup")
    if "https://bridge.playgama.com" in html:
        raise SystemExit("Parser-active external Playgama Bridge remains in index.html")
    if PLAYGAMA_BRIDGE_URL not in loader or "script.async = true" not in loader:
        raise SystemExit("Pinned non-blocking Playgama Bridge loader is missing")
    if "await window.playgamaBridgeScriptReady" not in adapter:
        raise SystemExit("Playgama compatibility adapter does not await optional Bridge initialization")
    if "window.__openttdPlaygamaStartupStorageProbeDisabled = true;" not in adapter or "__openttd_playgama_bridge" in adapter:
        raise SystemExit("Redundant Playgama startup storage get/set probe was not removed")
    if "Module.calledRun === true" not in ranking or "typeof HEAP8 !== 'undefined'" not in ranking:
        raise SystemExit("Playgama ranking runtime-ready guard is missing")
    for marker in (
        "const MAX_SCORE = 1000",
        "playgamaBridgeProvider: true",
        "startupEntryRequestsDeferred: true",
        "window.playgamaBridgeReady",
        "bridge.leaderboards.getEntries",
        "bridge.leaderboards.setScore",
    ):
        if marker not in global_ranking:
            raise SystemExit(f"Playgama direct global leaderboard provider is missing marker: {marker}")
    if "window.yandexGamesSDKReady" in global_ranking:
        raise SystemExit("Yandex leaderboard provider was accidentally installed into Playgama package")
    if "__openttdPlaygamaCloudNetworkStats" not in cloud or "skippedSaveMetadataReads++" not in cloud:
        raise SystemExit("Playgama cloud network dedup/fast-path is missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()

    shared = load_shared()
    shared.patch_ranking(dist / "openttd-ranking-core.js", False)
    shared.patch_ranking(dist / "openttd-global-ranking.js", True)
    install_optimized_global_ranking(dist)
    patch_index(dist)
    write_loader(dist)
    patch_adapter(dist)
    patch_cloud_network(dist)
    patch_runtime_startup(dist)
    validate(dist)
    print("v14 single-file Playgama hardening applied")


if __name__ == "__main__":
    main()
