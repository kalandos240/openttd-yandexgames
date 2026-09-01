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

    # Legal notices remain static files in the ZIP. The runtime must not fetch,
    # install or expose them through browser globals anymore.
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


def patch_yandex_network_efficiency(dist: Path) -> None:
    """Avoid redundant platform API traffic without changing save semantics.

    The bridge already debounces cloud writes, but the old implementation still
    sent the same configuration/save payload again whenever another persistence
    callback arrived after the minimum interval. Yandex Player setData() is a
    real platform request, so keep per-key fingerprints from the cloud restore
    and suppress unchanged keys. If both keys are unchanged, no request is made.
    """
    path = dist / "yandex-bridge.js"
    if not path.is_file():
        raise SystemExit(f"Yandex bridge is missing: {path}")
    text = path.read_text(encoding="utf-8")

    state_anchor = "  let lastCloudWriteAt = 0;\n"
    state_block = """  let lastCloudWriteAt = 0;
  let lastCloudConfigFingerprint = '';
  let lastCloudSaveFingerprint = '';
  const cloudNetworkStats = window.__openttdYandexCloudNetworkStats = {
    dedupEnabled: true,
    uploads: 0,
    skippedUnchanged: 0,
  };
"""
    if text.count(state_anchor) != 1:
        raise SystemExit("Could not find Yandex cloud write state anchor")
    text = text.replace(state_anchor, state_block, 1)

    restore_anchor = "  window.yandexRestoreOpenTTDCloud = async function(FS, personalDir) {\n"
    fingerprint_helpers = """  function cloudConfigFingerprint(value) {
    if (!value || value.version !== CLOUD_VERSION || typeof value.config !== 'string') return '';
    return JSON.stringify([value.version, value.config]);
  }

  function cloudSaveFingerprint(value) {
    if (!value || value.version !== CLOUD_VERSION || !value.name || !value.data) return '';
    return JSON.stringify([
      value.version,
      String(value.name),
      Number(value.mtime || 0),
      String(value.data),
    ]);
  }

""" + restore_anchor
    if text.count(restore_anchor) != 1:
        raise SystemExit("Could not find Yandex cloud restore anchor")
    text = text.replace(restore_anchor, fingerprint_helpers, 1)

    restore_old = """      const data = await player.getData([CLOUD_CONFIG_KEY, CLOUD_SAVE_KEY]);
      restoreCloudConfig(FS, personalDir, data && data[CLOUD_CONFIG_KEY]);
      const restored = restoreCloudSave(FS, personalDir, data && data[CLOUD_SAVE_KEY]);
"""
    restore_new = """      const data = await player.getData([CLOUD_CONFIG_KEY, CLOUD_SAVE_KEY]);
      lastCloudConfigFingerprint = cloudConfigFingerprint(data && data[CLOUD_CONFIG_KEY]);
      lastCloudSaveFingerprint = cloudSaveFingerprint(data && data[CLOUD_SAVE_KEY]);
      restoreCloudConfig(FS, personalDir, data && data[CLOUD_CONFIG_KEY]);
      const restored = restoreCloudSave(FS, personalDir, data && data[CLOUD_SAVE_KEY]);
"""
    if text.count(restore_old) != 1:
        raise SystemExit("Could not find Yandex cloud restore read block")
    text = text.replace(restore_old, restore_new, 1)

    flush_old = """      const payload = buildCloudPayload(FS, personalDir);

      /* If the newest save is too large, CLOUD_SAVE_KEY is intentionally
         omitted so the last valid cloud save is not erased. */
      if (JSON.stringify(payload).length > 195000) delete payload[CLOUD_SAVE_KEY];
      await player.setData(payload, true);
      lastCloudWriteAt = Date.now();
"""
    flush_new = """      const payload = buildCloudPayload(FS, personalDir);

      /* If the newest save is too large, CLOUD_SAVE_KEY is intentionally
         omitted so the last valid cloud save is not erased. */
      if (JSON.stringify(payload).length > 195000) delete payload[CLOUD_SAVE_KEY];

      const configFingerprint = cloudConfigFingerprint(payload[CLOUD_CONFIG_KEY]);
      const saveFingerprint = cloudSaveFingerprint(payload[CLOUD_SAVE_KEY]);
      if (configFingerprint && configFingerprint === lastCloudConfigFingerprint) delete payload[CLOUD_CONFIG_KEY];
      if (saveFingerprint && saveFingerprint === lastCloudSaveFingerprint) delete payload[CLOUD_SAVE_KEY];

      if (Object.keys(payload).length === 0) {
        cloudNetworkStats.skippedUnchanged++;
        return;
      }

      await player.setData(payload, true);
      cloudNetworkStats.uploads++;
      if (payload[CLOUD_CONFIG_KEY]) lastCloudConfigFingerprint = configFingerprint;
      if (payload[CLOUD_SAVE_KEY]) lastCloudSaveFingerprint = saveFingerprint;
      lastCloudWriteAt = Date.now();
"""
    if text.count(flush_old) != 1:
        raise SystemExit("Could not find Yandex cloud upload block")
    text = text.replace(flush_old, flush_new, 1)

    for marker in (
        "__openttdYandexCloudNetworkStats",
        "dedupEnabled: true",
        "skippedUnchanged++",
        "lastCloudConfigFingerprint",
        "lastCloudSaveFingerprint",
    ):
        if marker not in text:
            raise SystemExit(f"Yandex network-efficiency marker missing after patch: {marker}")

    path.write_text(text, encoding="utf-8")
    print("Yandex cloud traffic dedup enabled: unchanged config/save keys no longer call Player.setData().")


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
        # Rename without altering license/notices content.
        old_bytes = old_license.read_bytes()
        new_license.write_bytes(old_bytes)
        if new_license.read_bytes() != old_bytes:
            raise SystemExit("Yandex legal bundle changed while being renamed")
        old_license.unlink()
    elif not new_license.is_file():
        raise SystemExit("Combined license bundle is missing from Yandex package")

    patch_loader(loader)
    patch_yandex_network_efficiency(dist)

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
        raise SystemExit("Neutral Yandex legal bundle is missing or unexpectedly small")

    audit_manifest_assets(dist)
    audit_executable_network_sinks(dist)

    print(f"Yandex runtime naming neutralized; static legal text preserved: {new_license}")
    print("No in-game licenses UI or license-bundle runtime installer remains.")
    print("All bundled game payloads are local; direct remote HTTP(S)/WebSocket/script/media sinks are forbidden in executable package files.")


if __name__ == "__main__":
    main()
