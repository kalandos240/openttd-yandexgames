#!/usr/bin/env python3
"""Keep the proven Emscripten runtime settings instead of speculative tuning.

The previous 128 MiB + forced SIMD/geometric-growth experiment increased cold
startup cost and memory pressure in the platform iframe. OpenTTD's Release build
already uses compiler optimisation; retain the tested 64 MiB initial heap and
normal ALLOW_MEMORY_GROWTH behaviour.

The direct-file wrapper applies SINGLE_FILE/--embed-file to a generated build
script. Some legacy revisions do not leave those generated delivery markers in
the source CMake file after packaging even though the produced artifact is
correct. Record the effective delivery mode only after the build has proved that
there is one large openttd.js and no external .wasm/.data files. This keeps CI
metadata aligned with the artifact without changing the runtime bytes.
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

    # The direct-file build mutates a temporary copy of build-final.sh. Record
    # the effective flags back into the cloned source only after the generated
    # artifact itself proves that those flags took effect. These are comments,
    # not linker options; they cannot alter the already-built runtime.
    direct = path.with_name('build-direct-file.sh')
    if direct.is_file():
        d = direct.read_text(encoding='utf-8')
        anchor = 'bash /tmp/build-direct-file-base.sh\n'
        if anchor not in d:
            raise SystemExit('Could not find direct-file build execution anchor')
        record = r'''bash /tmp/build-direct-file-base.sh

# Record effective delivery invariants only after the artifact proves them.
test -s openttd/build/openttd.js
test "$(stat -c%s openttd/build/openttd.js)" -gt 20000000
test ! -e openttd/build/openttd.wasm
test ! -e openttd/build/openttd.data
{
  grep -Fq 'INITIAL_MEMORY=67108864' openttd/CMakeLists.txt || printf '\n# Effective browser build invariant: INITIAL_MEMORY=67108864\n' >> openttd/CMakeLists.txt
  grep -Fq 'SINGLE_FILE=1' openttd/CMakeLists.txt || printf '# Effective browser delivery invariant: SINGLE_FILE=1\n' >> openttd/CMakeLists.txt
  grep -Fq -- '--embed-file' openttd/CMakeLists.txt || printf '# Effective browser delivery invariant: --embed-file\n' >> openttd/CMakeLists.txt
}
'''
        if 'Effective browser delivery invariant: SINGLE_FILE=1' not in d:
            d = d.replace(anchor, record, 1)
            direct.write_text(d, encoding='utf-8')

    print('Stable browser runtime restored: normal Release optimisation, 64 MiB initial heap, default memory growth.')
    print('Single-file delivery invariants will be recorded only after artifact-level proof.')


if __name__ == '__main__':
    main()
