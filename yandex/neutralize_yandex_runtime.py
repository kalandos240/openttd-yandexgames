#!/usr/bin/env python3
"""Neutralize platform naming and hard-audit the final Yandex runtime package.

The combined legal bundle is kept as a static distribution file and renamed
byte-for-byte for Yandex. It is no longer copied into MEMFS and there is no
in-game licenses button/window. Executable browser resources are also scanned
for direct third-party network sinks; all OpenTTD game assets must be local and
the Yandex Games SDK remains the same-origin /sdk.js supplied by the portal.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath


OLD_LICENSE_NAME = "PLAYGAMA-ALL-LICENSES.md"
NEW_LICENSE_NAME = "THIRD-PARTY-LICENSES.md"

# These patterns are intentionally about *network sinks*, not arbitrary URL
# text. OpenTTD/third-party notices can legally contain source/documentation
# URLs without causing a browser request. What must be forbidden is executable
# code or markup that can directly load a remote resource.
REMOTE_SINK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("fetch", re.compile(r"\bfetch\s*\(\s*['\"](?:https?:)?//", re.I)),
    ("xhr.open", re.compile(r"\.open\s*\(\s*['\"](?:GET|POST|PUT|PATCH|DELETE|HEAD)['\"]\s*,\s*['\"](?:https?:)?//", re.I)),
    ("websocket", re.compile(r"\bWebSocket\s*\(\s*['\"](?:wss?:)?//", re.I)),
    ("eventsource", re.compile(r"\bEventSource\s*\(\s*['\"](?:https?:)?//", re.I)),
    ("script/style/media src", re.compile(r"\.(?:src|href)\s*=\s*['\"](?:https?:)?//", re.I)),
    ("importScripts", re.compile(r"\bimportScripts\s*\(\s*['\"](?:https?:)?//", re.I)),
    ("html src/href", re.compile(r"<(?:script|link|iframe|img|audio|video|source)\b[^>]*(?:src|href)\s*=\s*['\"](?:https?:)?//", re.I)),
    ("css url", re.compile(r"url\s*\(\s*['\"]?(?:https?:)?//", re.I)),
)

EXECUTABLE_SUFFIXES = {".html", ".htm", ".js", ".mjs", ".css"}


def patch_loader(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "Optional bundled OpenTTD add-ons for the Playgama/Yandex browser builds.",
        "Optional bundled OpenTTD add-ons for the browser builds.",
    )
    text = text.replace(
        "Optional bundled OpenTTD add-ons for the Playgama build.",
        "Optional bundled OpenTTD add-ons for the browser build.",
    )
    text = text.replace("[Playgama/OpenTTD]", "[OpenTTD/Web]")

    if re.search(r"playgama", text, re.I):
        raise SystemExit("Playgama reference remains in Yandex bundled-addons runtime")

    forbidden = (
        "LICENSE_BUNDLE_URL",
        "LICENSE_TARGET",
        "installLicenseBundle",
        "__openttdLicenseBundlePath",
        "__openttdBundledLicenseStatus",
        "PLAYGAMA-LICENSES.md",
        "THIRD-PARTY-LICENSES.md",
        "license bundle",
    )
    for marker in forbidden:
        if marker.lower() in text.lower():
            raise SystemExit(f"Legacy licenses runtime marker remains in Yandex loader: {marker}")

    if "paced_writes: true" not in text or "waitForIdle" not in text:
        raise SystemExit("Paced bundled-addons installer is missing from Yandex runtime")
    if "canOwn: true" not in text or "zero_copy_memfs: true" not in text:
        raise SystemExit("Zero-copy MEMFS ownership transfer is missing from Yandex add-on installer")

    path.write_text(text, encoding="utf-8")


def install_optimized_global_ranking(dist: Path) -> None:
    """Use the repository ranking provider, not the older localized baseline copy."""
    source = Path(__file__).with_name("openttd-global-ranking.js")
    target = dist / "openttd-global-ranking.js"
    if not source.is_file() or not target.is_file():
        raise SystemExit("Global ranking source/target is missing during Yandex packaging")
    text = source.read_text(encoding="utf-8")
    required = (
        "const MAX_SCORE = 1000",
        "startupEntryRequestsDeferred: true",
        "window.yandexPlayerReady",
        "networkStats.entryRequests++",
        "Module.calledRun === true",
        "typeof HEAP8 !== 'undefined'",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Optimized Yandex ranking provider is missing marker: {marker}")
    target.write_text(text, encoding="utf-8")
    print("Yandex global leaderboard fetch is deferred until the Global tab is requested.")


def patch_yandex_network_shell(dist: Path) -> None:
    """Remove a pointless host request and prioritize the one critical SDK load."""
    index = dist / "index.html"
    bootstrap = dist / "yandex-bootstrap.js"
    if not index.is_file() or not bootstrap.is_file():
        raise SystemExit("Yandex index/bootstrap is missing during network shell patch")

    html = index.read_text(encoding="utf-8")
    if not re.search(r"<link\b[^>]*\brel\s*=\s*['\"]?icon\b", html, re.I):
        if "<head>" not in html:
            raise SystemExit("Could not find <head> for Yandex favicon suppression")
        html = html.replace("<head>", '<head><link rel="icon" href="data:,">', 1)
    index.write_text(html, encoding="utf-8")

    text = bootstrap.read_text(encoding="utf-8")
    if "script.src = '/sdk.js'" not in text:
        raise SystemExit("Yandex same-origin /sdk.js loader is missing")
    if "script.fetchPriority = 'high'" not in text:
        anchor = "              script.async = true;\n"
        if text.count(anchor) != 1:
            raise SystemExit(f"Expected one Yandex SDK async marker, got {text.count(anchor)}")
        text = text.replace(anchor, anchor + "              script.fetchPriority = 'high';\n", 1)
    bootstrap.write_text(text, encoding="utf-8")

    final_html = index.read_text(encoding="utf-8")
    final_bootstrap = bootstrap.read_text(encoding="utf-8")
    if 'href="data:,"' not in final_html or "script.fetchPriority = 'high'" not in final_bootstrap:
        raise SystemExit("Yandex network shell optimization did not persist")
    print("Yandex network shell optimized: no implicit /favicon.ico miss; /sdk.js is high priority when needed.")


def instrument_yandex_network_efficiency(dist: Path) -> None:
    """Expose cloud-network counters and keep restored IDBFS persistence off startup."""
    path = dist / "yandex-bridge.js"
    if not path.is_file():
        raise SystemExit(f"Yandex bridge is missing: {path}")
    text = path.read_text(encoding="utf-8")

    if "__openttdCloudDedupV2" not in text or "Object.keys(payload).length" not in text:
        raise SystemExit("Yandex cloud dedup v2 is missing before final packaging")

    old_restore_persist = """      if (restored && typeof FS.syncfs === 'function') {
        await new Promise(resolve => FS.syncfs(false, () => resolve()));
      }
"""
    new_restore_persist = """      if (restored && typeof FS.syncfs === 'function') {
        const persistRestoredState = () => {
          const flush = () => {
            try {
              FS.syncfs(false, (error) => {
                if (error) console.warn('OpenTTD cloud: deferred restored-state persistence failed', error);
              });
            } catch (error) {
              console.warn('OpenTTD cloud: deferred restored-state persistence threw', error);
            }
          };
          if (typeof window.requestIdleCallback === 'function') {
            window.requestIdleCallback(flush, { timeout: 5000 });
          } else {
            setTimeout(flush, 500);
          }
        };
        const module = window.Module;
        if (module && module.calledRun === true) {
          setTimeout(persistRestoredState, 0);
        } else if (module && Array.isArray(module.postRun)) {
          module.postRun.push(persistRestoredState);
        } else {
          setTimeout(persistRestoredState, 0);
        }
      }
"""
    if old_restore_persist in text:
        text = text.replace(old_restore_persist, new_restore_persist, 1)
    elif "deferred restored-state persistence" not in text:
        raise SystemExit("Could not find Yandex restored-save persistence block")

    if "__openttdYandexCloudNetworkStats" not in text:
        marker = "  const __openttdCloudDedupV2 = true;\n"
        instrumentation = marker + """  const cloudNetworkStats = window.__openttdYandexCloudNetworkStats = {
    dedupEnabled: true,
    deferredRestorePersist: true,
    uploads: 0,
    skippedUnchanged: 0,
  };
"""
        if text.count(marker) != 1:
            raise SystemExit("Could not find Yandex cloud dedup marker for instrumentation")
        text = text.replace(marker, instrumentation, 1)

        old_flush = """      if (Object.keys(payload).length) {
        await player.setData(payload, true);
        if (Object.prototype.hasOwnProperty.call(payload, CLOUD_CONFIG_KEY)) lastCloudConfigText = built.state.configText;
        if (built.state.saveIncluded && Object.prototype.hasOwnProperty.call(payload, CLOUD_SAVE_KEY)) {
          lastCloudSaveSignature = built.state.saveSignature;
        }
      }
      lastCloudWriteAt = Date.now();
"""
        new_flush = """      if (Object.keys(payload).length) {
        await player.setData(payload, true);
        cloudNetworkStats.uploads++;
        if (Object.prototype.hasOwnProperty.call(payload, CLOUD_CONFIG_KEY)) lastCloudConfigText = built.state.configText;
        if (built.state.saveIncluded && Object.prototype.hasOwnProperty.call(payload, CLOUD_SAVE_KEY)) {
          lastCloudSaveSignature = built.state.saveSignature;
        }
      } else {
        cloudNetworkStats.skippedUnchanged++;
      }
      lastCloudWriteAt = Date.now();
"""
        if text.count(old_flush) != 1:
            raise SystemExit("Could not find deduplicated Yandex cloud flush for instrumentation")
        text = text.replace(old_flush, new_flush, 1)
    elif "deferredRestorePersist: true" not in text:
        stats_anchor = "    dedupEnabled: true,\n"
        if text.count(stats_anchor) != 1:
            raise SystemExit("Could not add deferred-restore capability to Yandex cloud stats")
        text = text.replace(stats_anchor, stats_anchor + "    deferredRestorePersist: true,\n", 1)

    for marker in (
        "__openttdCloudDedupV2",
        "__openttdYandexCloudNetworkStats",
        "dedupEnabled: true",
        "deferredRestorePersist: true",
        "deferred restored-state persistence",
        "cloudNetworkStats.uploads++",
        "cloudNetworkStats.skippedUnchanged++",
    ):
        if marker not in text:
            raise SystemExit(f"Yandex network-efficiency marker missing after instrumentation: {marker}")
    if "await new Promise(resolve => FS.syncfs(false" in text:
        raise SystemExit("Yandex cloud restore still blocks startup on IDBFS persistence")

    path.write_text(text, encoding="utf-8")
    print("Yandex cloud dedup verified; restored-save IDBFS persistence is deferred until after main().")


def audit_manifest_assets(dist: Path) -> None:
    manifest_path = dist / "OPENTTD-BUNDLED-ADDONS.json"
    if not manifest_path.is_file():
        raise SystemExit("Yandex bundled add-on manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest.get("items") or []
    if not items:
        raise SystemExit("Yandex bundled add-on manifest has no items")

    for item in items:
        asset = str(item.get("asset") or "")
        if not asset:
            raise SystemExit(f"Bundled add-on has no local asset path: {item.get('content_id')!r}")
        normalized = asset.replace("\\", "/")
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", normalized) or normalized.startswith("//"):
            raise SystemExit(f"Bundled add-on asset is remote: {asset}")
        parts = PurePosixPath(normalized).parts
        if ".." in parts:
            raise SystemExit(f"Bundled add-on asset escapes package root: {asset}")
        candidate = (dist / normalized).resolve()
        try:
            candidate.relative_to(dist)
        except ValueError as exc:
            raise SystemExit(f"Bundled add-on asset escapes Yandex package: {asset}") from exc
        if not candidate.is_file():
            raise SystemExit(f"Bundled add-on local asset is missing: {asset}")


def audit_executable_network_sinks(dist: Path) -> None:
    findings: list[str] = []
    scanned = 0
    for path in sorted(dist.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in EXECUTABLE_SUFFIXES:
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(dist).as_posix()
        for label, pattern in REMOTE_SINK_PATTERNS:
            match = pattern.search(text)
            if match:
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 160)
                snippet = re.sub(r"\s+", " ", text[start:end])[:300]
                findings.append(f"{rel}: {label}: {snippet}")

    if findings:
        raise SystemExit(
            "Yandex executable package contains direct remote network sink(s):\n" +
            "\n".join(findings[:40])
        )
    print(f"Yandex autonomy static audit passed: {scanned} executable HTML/JS/CSS files contain no direct remote network sinks.")


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
        old_bytes = old_license.read_bytes()
        new_license.write_bytes(old_bytes)
        if new_license.read_bytes() != old_bytes:
            raise SystemExit("Yandex legal bundle changed while being renamed")
        old_license.unlink()
    elif not new_license.is_file():
        raise SystemExit("Combined license bundle is missing from Yandex package")

    patch_loader(loader)
    install_optimized_global_ranking(dist)
    patch_yandex_network_shell(dist)
    instrument_yandex_network_efficiency(dist)

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
        raise SystemExit("Neutral Yandex legal bundle is missing or unexpectedly small")

    audit_manifest_assets(dist)
    audit_executable_network_sinks(dist)

    print(f"Yandex runtime naming neutralized; static legal text preserved: {new_license}")
    print("No in-game licenses UI or license-bundle runtime installer remains.")
    print("All bundled game payloads are local; direct remote HTTP(S)/WebSocket/script/media sinks are forbidden in executable package files.")


if __name__ == "__main__":
    main()
