#!/usr/bin/env python3
"""Make Playgama's mandatory bundled-AI restore wrapper the final cloud provider wrapper.

The Playgama package loads openttd-playgama-fixes.js (which installs SimpleAI
and the API compatibility chain) and openttd-playgama-cloud-saves.js (which
replaces the legacy Yandex cloud provider). If cloud-saves loads after fixes it
replaces the mandatory AI wrapper entirely, so OpenTTD can create dummy AI
companies even while native telemetry still reports 14 AI instances.

The minimal safe fix is script ordering only: load the Playgama cloud provider
first, then load openttd-playgama-fixes.js so its synchronous AI installation
wraps the final cloud restore implementation. Optional bundled add-ons remain
the outermost wrapper and may keep their bounded cloud wait.
"""
from __future__ import annotations

import argparse
from pathlib import Path

CLOUD = '<script src="openttd-playgama-cloud-saves.js"></script>'
FIXES = '<script src="openttd-playgama-fixes.js"></script>'
CLASSIC_AI = '<script src="openttd-classic-ai.js"></script>'
ADDONS = '<script src="openttd-bundled-addons.js"></script>'
RUNTIME = '<script src="openttd-runtime.js"></script>'


def patch_index(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for token in (CLOUD, FIXES, CLASSIC_AI, ADDONS, RUNTIME):
        if text.count(token) != 1:
            raise SystemExit(f"Expected exactly one {token}, got {text.count(token)}")

    if text.index(CLOUD) > text.index(FIXES):
        text = text.replace(CLOUD, "", 1)
        fixes_at = text.index(FIXES)
        text = text[:fixes_at] + CLOUD + text[fixes_at:]

    order = [text.index(CLASSIC_AI), text.index(CLOUD), text.index(FIXES), text.index(ADDONS), text.index(RUNTIME)]
    if order != sorted(order):
        raise SystemExit(
            "Unsafe Playgama startup order; required classic-ai < cloud-saves < fixes < bundled-addons < runtime"
        )

    path.write_text(text, encoding="utf-8")


def validate_scripts(dist: Path) -> None:
    fixes = (dist / "openttd-playgama-fixes.js").read_text(encoding="utf-8")
    cloud = (dist / "openttd-playgama-cloud-saves.js").read_text(encoding="utf-8")
    addons = (dist / "openttd-bundled-addons.js").read_text(encoding="utf-8")

    required_fixes = (
        "const originalRestore = window.yandexRestoreOpenTTDCloud;",
        "installClassicAI(FS, personalDir);",
        "installAICompatibility(FS, personalDir);",
        "window.__openttdAICompatInstalled = installed;",
    )
    for token in required_fixes:
        if token not in fixes:
            raise SystemExit(f"Mandatory AI wrapper invariant missing: {token}")

    if "window.yandexRestoreOpenTTDCloud = async function(FS, personalDir)" not in cloud:
        raise SystemExit("Playgama cloud provider override is missing")
    if "const previousRestore = window.yandexRestoreOpenTTDCloud;" not in addons:
        raise SystemExit("Bundled-addons outer restore wrapper is missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    patch_index(dist / "index.html")
    validate_scripts(dist)
    print("Playgama AI startup order fixed: classic AI data -> cloud provider -> mandatory AI wrapper -> optional add-ons -> runtime.")


if __name__ == "__main__":
    main()
