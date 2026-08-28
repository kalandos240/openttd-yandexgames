#!/usr/bin/env python3
"""Keep the proven Emscripten runtime settings instead of speculative tuning.

The previous 128 MiB + forced SIMD/geometric-growth experiment increased cold
startup cost and memory pressure in the platform iframe. OpenTTD's Release build
already uses compiler optimisation; retain the tested 64 MiB initial heap and
normal ALLOW_MEMORY_GROWTH behaviour.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('build_script', type=Path)
    args = ap.parse_args()

    path = args.build_script
    text = path.read_text(encoding='utf-8')

    # Support both a clean legacy checkout and a locally re-patched script, but
    # always leave the build on the known-good 64 MiB baseline.
    text = text.replace('INITIAL_MEMORY=134217728', 'INITIAL_MEMORY=67108864')
    if text.count('INITIAL_MEMORY=67108864') != 1:
        raise SystemExit(f'Expected one stable 64 MiB initial-memory setting, got {text.count("INITIAL_MEMORY=67108864")}')

    tuned = '''  emcmake cmake .. \\
    -DHOST_BINARY_DIR=../build-host \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DOPTION_USE_ASSERTS=OFF \\
    -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -msimd128" \\
    -DCMAKE_EXE_LINKER_FLAGS_RELEASE="-O3 -msimd128 -s MEMORY_GROWTH_GEOMETRIC_STEP=0.5 -s MEMORY_GROWTH_GEOMETRIC_CAP=268435456"
'''
    stable = '''  emcmake cmake .. \\
    -DHOST_BINARY_DIR=../build-host \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DOPTION_USE_ASSERTS=OFF
'''
    if tuned in text:
        text = text.replace(tuned, stable, 1)
    elif stable not in text:
        raise SystemExit('Could not find Emscripten Release configure block')

    for forbidden in ('-msimd128', 'MEMORY_GROWTH_GEOMETRIC_STEP', 'MEMORY_GROWTH_GEOMETRIC_CAP'):
        if forbidden in text:
            raise SystemExit(f'Unstable browser tuning remains in build script: {forbidden}')

    path.write_text(text, encoding='utf-8')
    print('Stable browser runtime restored: normal Release optimisation, 64 MiB initial heap, default memory growth.')


if __name__ == '__main__':
    main()
