#!/usr/bin/env python3
"""Trim assets that are not needed for CrazyGames startup/gameplay.

This mutates the checked-out verified browser pipeline before build-v2-fixed.sh
runs. Runtime/gameplay data stays unchanged; only upstream in-game documentation
preloads and the redundant OpenMSX tar archive are removed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DOC_TOKENS = (
    "README.md@/README.md",
    "CREDITS.md@/CREDITS.md",
    "CONTRIBUTING.md@/CONTRIBUTING.md",
    "COPYING.md@/COPYING.md",
    "known-bugs.md@/known-bugs.md",
    "changelog.md@/changelog.md",
    "docs/admin_network.md@/docs/admin_network.md",
    "docs/debugging_desyncs.md@/docs/debugging_desyncs.md",
    "docs/desync.md@/docs/desync.md",
    "docs/directory_structure.md@/docs/directory_structure.md",
    "docs/eints.md@/docs/eints.md",
    "docs/fonts.md@/docs/fonts.md",
    "docs/linkgraph.md@/docs/linkgraph.md",
    "docs/logging_and_performance_metrics.md@/docs/logging_and_performance_metrics.md",
    "docs/multiplayer.md@/docs/multiplayer.md",
    "docs/savegame_format.md@/docs/savegame_format.md",
    "docs/symbol_server.md@/docs/symbol_server.md",
)


def patch_build_final(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    marker = "cmake.write_text(s)\n"
    if marker not in text:
        raise SystemExit("Could not find OpenTTD CMake write marker")

    code = """# CrazyGames mobile-homepage payload trim: the browser port never opens
# upstream developer/documentation files during normal gameplay. Keep them in
# repository/source notices, but do not preload them into openttd.data.
_doc_preload_tokens = %r
_before = s
s = '\\n'.join(
    line for line in s.split('\\n')
    if not any(token in line for token in _doc_preload_tokens)
)
if s == _before:
    raise SystemExit('CrazyGames documentation preload trim matched nothing')
cmake.write_text(s)
""" % (DOC_TOKENS,)
    text = text.replace(marker, code, 1)

    asset_marker = "echo 'Bundled base-set files:'\n"
    if asset_marker not in text:
        raise SystemExit("Could not find base-set listing marker")
    remove_tar = """# OpenTTD does not discover music sets from tar archives. The direct-file
# wrapper below unpacks OpenMSX .obm + MIDI files for detection and renders MP3
# files separately, so the original OpenMSX tar would only duplicate bytes in
# the initial Emscripten data package.
rm -f openttd/build/yandex_baseset/openmsx-*.tar
! find openttd/build/yandex_baseset -maxdepth 1 -type f -name 'openmsx-*.tar' -print -quit | grep -q .

"""
    text = text.replace(asset_marker, remove_tar + asset_marker, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy", type=Path)
    args = parser.parse_args()
    build_final = args.legacy / "ci" / "build-final.sh"
    if not build_final.is_file():
        raise SystemExit(f"Missing verified legacy build script: {build_final}")
    patch_build_final(build_final)
    print("CrazyGames mobile-homepage payload trim installed: docs + redundant OpenMSX tar")


if __name__ == "__main__":
    main()
