#!/usr/bin/env python3
"""Turn the historical direct-file build into a platform-native split runtime.

The legacy pipeline intentionally used Emscripten SINGLE_FILE and --embed-file
so index.html could run from file:// with no server. Yandex Games and Playgama
serve ordinary same-origin files, so that mode is counterproductive: a ~57 MiB
Wasm binary becomes base64 inside a huge JavaScript file, increasing parse,
decode and peak-memory cost on every cold browser profile.

Patch only stable individual markers in the historical shell generator. Avoid
matching a large formatted block so harmless whitespace/quoting cannot break CI.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected one {label}, got {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('build_script', type=Path)
    args = ap.parse_args()

    path = args.build_script
    if not path.is_file():
        raise SystemExit(f'Legacy direct-file build script is missing: {path}')
    text = path.read_text(encoding='utf-8')

    # Keep Emscripten preload files external instead of converting them to
    # base64-embedded assets.
    text = replace_once(
        text,
        "s = s.replace('--preload-file', '--embed-file')\n",
        "# Platform delivery keeps --preload-file resources external.\n",
        'preload-to-embed mutation',
    )

    # Leave the old conditional structure intact but make its sentinel the
    # empty string. Empty string is always present in `s`, so the insertion
    # branch can never add SINGLE_FILE=1.
    text = replace_once(
        text,
        "single_file = '    target_link_libraries(WASM::WASM INTERFACE \"-s SINGLE_FILE=1\")\\n'\n",
        "single_file = ''  # Platform build: never add SINGLE_FILE.\n",
        'SINGLE_FILE linker marker',
    )

    # build-final.sh already copies all normal Emscripten outputs. Remove the
    # historical post-processing that deliberately discarded wasm/data.
    for old, label in (
        ("s = s.replace('cp openttd/build/openttd.wasm dist/\\n', '')\n", 'wasm output stripping'),
        ("s = s.replace('cp openttd/build/openttd.data dist/\\n', '')\n", 'data output stripping'),
        ("s = s.replace('cp openttd/build/openttd.js dist/\\n', '[ ! -f openttd/build/openttd.js ] || cp openttd/build/openttd.js dist/\\n')\n", 'JS copy mutation'),
    ):
        text = replace_once(text, old, '', label)

    text = replace_once(
        text,
        "test ! -e dist/openttd.wasm\\ntest ! -e dist/openttd.data",
        "test -s dist/openttd.js\\ntest -s dist/openttd.wasm\\ntest -s dist/openttd.data",
        'direct-file output assertions',
    )

    old_header = '# - all Emscripten resources are embedded, so index.html works via file://'
    if old_header in text:
        text = text.replace(
            old_header,
            '# - platform output keeps JS, WebAssembly and preload data as separate cacheable files',
            1,
        )

    for forbidden in (
        "s = s.replace('--preload-file', '--embed-file')",
        'SINGLE_FILE=1',
        "test ! -e dist/openttd.wasm",
        "test ! -e dist/openttd.data",
        "s = s.replace('cp openttd/build/openttd.wasm dist/",
        "s = s.replace('cp openttd/build/openttd.data dist/",
    ):
        if forbidden in text:
            raise SystemExit(f'Historical single-file behaviour remains: {forbidden}')

    path.write_text(text, encoding='utf-8')
    print('Platform streaming runtime enabled:', path)
    print('Separate openttd.js, openttd.wasm and openttd.data will be preserved.')


if __name__ == '__main__':
    main()
