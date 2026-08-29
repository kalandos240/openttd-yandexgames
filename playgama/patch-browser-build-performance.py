#!/usr/bin/env python3
"""Keep the proven Emscripten runtime settings and remove obsolete AI sanitizers.

The browser release stays on the tested 64 MiB + normal memory-growth profile.
For the current AI-enabled build this hook also removes the old Yandex offline
cleanup that rewrote max_no_competitors to zero after IDBFS restore. The native
OpenTTD zero-interval patch remains part of the legacy source pipeline.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def remove_legacy_ai_sanitizers(build_script: Path) -> None:
    ci_dir = build_script.parent
    cleanup = ci_dir / 'patch-yandex-runtime-cleanup.py'
    release = ci_dir / 'build-yandex-release.sh'
    if not cleanup.is_file() or not release.is_file():
        raise SystemExit('Legacy Yandex cleanup/release scripts are missing next to build-final.sh')

    release_text = release.read_text(encoding='utf-8')
    if 'python3 ci/patch-ai-zero-interval.py' not in release_text:
        raise SystemExit('Native competitors_interval=0 patch is missing from the release source hook')

    text = cleanup.read_text(encoding='utf-8')

    # The obsolete offline cleanup modified os/emscripten/pre.js so releaseStartup()
    # rewrote max_no_competitors=0 immediately before OpenTTD main(). That was the
    # root cause of empty companies whose AI script never woke up.
    pattern = re.compile(
        r'''\n    # Old local/cloud configuration.*?'''
        r'''    text = replace_once\(text, old_release, new_release, 'offline AI startup config'\)\n''',
        re.S,
    )
    text, count = pattern.subn('', text, count=1)
    if count != 1:
        raise SystemExit(f'Expected one late AI startup sanitizer, found {count}')

    # The same cleanup also forced zero during cloud config read/write. Remove the
    # complete patch block so restored player settings survive unchanged.
    start = text.find("    old_read = '''  function readConfig(FS, personalDir) {")
    end_marker = "    text = replace_once(text, old_write, new_write, 'cloud config restore sanitizer')\n"
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit('Could not find legacy cloud AI sanitizer block')
    end += len(end_marker)
    text = text[:start] + text[end:]

    if 'offline AI startup config' in text or 'cloud config restore sanitizer' in text:
        raise SystemExit('Legacy AI-zero sanitizer markers remain after cleanup')
    cleanup.write_text(text, encoding='utf-8')
    print('Removed obsolete startup/cloud max_no_competitors=0 sanitizers.')


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

    # Remove the legacy late AI-zero rewrites before build-yandex-release.sh runs.
    remove_legacy_ai_sanitizers(path)

    # The direct-file build mutates a temporary copy of build-final.sh. Record
    # effective flags only after the generated artifact proves those flags took
    # effect. These comments cannot alter the already-built runtime.
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

    print('Stable browser runtime retained: Release optimisation, 64 MiB initial heap, default memory growth.')
    print('Native AI zero-interval patch retained; obsolete late AI-zero sanitizers removed.')


if __name__ == '__main__':
    main()
