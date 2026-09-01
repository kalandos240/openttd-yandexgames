#!/usr/bin/env python3
"""Apply final-package browser runtime performance patches.

The heavy renderer implementation is kept in a dedicated module. This wrapper
also patches whichever platform fixes file is present so final Yandex and
Playgama archives both get the bundled-ClassicAI size fast path.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def load_module(filename: str, module_name: str) -> object:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load patch module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patch_playgama_restore_order(dist: Path) -> None:
    """Install native Playgama cloud first, then let the AI wrapper decorate it.

    The localized baseline historically loads openttd-playgama-fixes.js before
    openttd-playgama-cloud-saves.js. The latter then replaces
    yandexRestoreOpenTTDCloud and silently bypasses the fixes wrapper that installs
    SimpleAI/compatibility around cloud restore. Reordering these two parser-
    blocking scripts composes the wrappers in the intended direction:
      cloud restore -> AI/config wrapper -> bundled-addons wrapper.
    """
    index = dist / "index.html"
    if not index.is_file():
        raise SystemExit(f"Playgama index is missing: {index}")
    text = index.read_text(encoding="utf-8")
    cloud_tag = '<script src="openttd-playgama-cloud-saves.js"></script>'
    fixes_tag = '<script src="openttd-playgama-fixes.js"></script>'
    addons_tag = '<script src="openttd-bundled-addons.js"></script>'

    if text.count(cloud_tag) != 1 or text.count(fixes_tag) != 1 or text.count(addons_tag) != 1:
        raise SystemExit("Could not resolve unique Playgama cloud/fixes/add-ons script tags")

    if text.index(cloud_tag) > text.index(fixes_tag):
        text = text.replace(cloud_tag, "", 1)
        text = text.replace(fixes_tag, cloud_tag + fixes_tag, 1)

    if not (text.index(cloud_tag) < text.index(fixes_tag) < text.index(addons_tag)):
        raise SystemExit("Playgama restore wrapper order is invalid after patch")
    index.write_text(text, encoding="utf-8")
    print("Playgama restore chain ordered: native cloud -> AI/config -> bundled add-ons")


def patch_optional_ai_installer(runtime: Path) -> None:
    dist = runtime.parent
    targets = [
        dist / name
        for name in ("openttd-yandex-fixes.js", "openttd-playgama-fixes.js")
        if (dist / name).is_file()
    ]
    if not targets:
        return
    if len(targets) != 1:
        raise SystemExit(f"Expected one platform fixes file beside runtime, found {[p.name for p in targets]}")
    ai = load_module("patch-v14-ai-archive-install.py", "v14_ai_archive_install")
    ai.patch(targets[0])
    if targets[0].name == "openttd-playgama-fixes.js":
        patch_playgama_restore_order(dist)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime", type=Path)
    args = parser.parse_args()
    runtime = args.runtime.resolve()

    renderer = load_module("patch-v14-webgl-renderer.py", "v14_webgl_renderer")
    renderer.patch_renderer(runtime)
    patch_optional_ai_installer(runtime)


if __name__ == "__main__":
    main()
