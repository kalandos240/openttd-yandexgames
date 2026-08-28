#!/usr/bin/env python3
"""Tune the tested Emscripten build for smoother large-map browser play."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('build_script', type=Path)
    args = ap.parse_args()

    path = args.build_script
    text = path.read_text(encoding='utf-8')

    # The tested legacy build first raises upstream OpenTTD's 32 MiB heap to
    # 64 MiB. Use 128 MiB instead so typical large-map sessions do not trigger
    # multiple expensive WebAssembly heap-growth copies near startup.
    old_memory = 'INITIAL_MEMORY=67108864'
    if text.count(old_memory) != 1:
        raise SystemExit(f'Expected one 64 MiB initial-memory setting, got {text.count(old_memory)}')
    text = text.replace(old_memory, 'INITIAL_MEMORY=134217728', 1)

    old_configure = '''  emcmake cmake .. \\
    -DHOST_BINARY_DIR=../build-host \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DOPTION_USE_ASSERTS=OFF
'''
    new_configure = '''  emcmake cmake .. \\
    -DHOST_BINARY_DIR=../build-host \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DOPTION_USE_ASSERTS=OFF \\
    -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -msimd128" \\
    -DCMAKE_EXE_LINKER_FLAGS_RELEASE="-O3 -msimd128 -s MEMORY_GROWTH_GEOMETRIC_STEP=0.5 -s MEMORY_GROWTH_GEOMETRIC_CAP=268435456"
'''
    if text.count(old_configure) != 1:
        raise SystemExit(f'Expected one Emscripten Release configure block, got {text.count(old_configure)}')
    text = text.replace(old_configure, new_configure, 1)

    path.write_text(text, encoding='utf-8')
    print('Browser performance build enabled: O3 + wasm SIMD, 128 MiB initial heap, geometric memory growth.')


if __name__ == '__main__':
    main()
