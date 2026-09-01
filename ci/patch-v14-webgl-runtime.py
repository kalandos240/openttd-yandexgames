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
