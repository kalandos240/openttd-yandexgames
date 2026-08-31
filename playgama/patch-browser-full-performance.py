#!/usr/bin/env python3
"""Apply the v14 high-performance Emscripten profile to the tested build pipeline.

This is intentionally layered after patch-browser-build-performance.py so the
stable AI/startup fixes remain intact. The high-performance profile targets the
actual Firefox profiler hotspots:
  * native WebAssembly C++ exceptions instead of JS exception trampolines;
  * wasm SIMD + ThinLTO at -O3;
  * cooperative browser yields while synchronous world generation reports
    progress, preventing multi-second browser LongTasks on very large maps.
"""
from __future__ import annotations

import argparse
from pathlib import Path

SOURCE_PATCH_MARKER = "# V14_FULL_PERF_SOURCE_PATCH\n"


def inject_source_patch(text: str) -> str:
    if SOURCE_PATCH_MARKER.strip() in text:
        return text

    anchor = (
        "git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd\n"
    )
    if text.count(anchor) != 1:
        raise SystemExit(f"Expected one OpenTTD clone anchor, got {text.count(anchor)}")

    patch = r"""# V14_FULL_PERF_SOURCE_PATCH
python3 - <<'PY_FULL_PERF_SOURCE'
from pathlib import Path

# Native Wasm EH removes the JS exception bridge that dominated the Firefox
# profile. -fwasm-exceptions is supplied at compile/link time below; remove
# the legacy JS exception-catching switch from upstream's Emscripten block.
cmake = Path('openttd/CMakeLists.txt')
s = cmake.read_text(encoding='utf-8')
legacy_eh = '        -s DISABLE_EXCEPTION_CATCHING=0\n'
if s.count(legacy_eh) != 1:
    raise SystemExit(f'Expected one legacy Emscripten exception flag, got {s.count(legacy_eh)}')
s = s.replace(legacy_eh, '', 1)
cmake.write_text(s, encoding='utf-8')

# World generation is synchronous in this browser port. The stock progress
# code pumps OpenTTD's paused loop but does not return to the browser event loop,
# so a 4096x4096 generation can become one enormous LongTask. ASYNCIFY is
# already enabled upstream; yield at most once every 32 ms from the progress
# path so input/compositor work can run without changing generation semantics.
gui = Path('openttd/src/genworld_gui.cpp')
g = gui.read_text(encoding='utf-8')
include_anchor = '#include "video/video_driver.hpp"\n'
include_block = include_anchor + '#ifdef __EMSCRIPTEN__\n#include <emscripten.h>\n#endif\n'
if '#include <emscripten.h>' not in g:
    if g.count(include_anchor) != 1:
        raise SystemExit('Could not locate genworld Emscripten include anchor')
    g = g.replace(include_anchor, include_block, 1)

old_progress = '''void IncreaseGeneratingWorldProgress(GenWorldProgress cls)
{
\t/* In fact the param 'class' isn't needed.. but for some security reasons, we want it around */
\t_SetGeneratingWorldProgress(cls, 1, 0);
}
'''
new_progress = '''void IncreaseGeneratingWorldProgress(GenWorldProgress cls)
{
\t/* In fact the param 'class' isn't needed.. but for some security reasons, we want it around */
\t_SetGeneratingWorldProgress(cls, 1, 0);
#ifdef __EMSCRIPTEN__
\t/* Keep very large synchronous map generations responsive in the browser.
\t * ASYNCIFY already instruments emscripten_sleep(), so this returns to the
\t * event loop and resumes exactly where generation left off. */
\tstatic double last_browser_yield_ms = 0.0;
\tconst double now_ms = emscripten_get_now();
\tif (last_browser_yield_ms == 0.0 || now_ms - last_browser_yield_ms >= 32.0) {
\t\tlast_browser_yield_ms = now_ms;
\t\temscripten_sleep(0);
\t}
#endif
}
'''
if 'last_browser_yield_ms' not in g:
    if g.count(old_progress) != 1:
        raise SystemExit(f'Expected one world-progress function, got {g.count(old_progress)}')
    g = g.replace(old_progress, new_progress, 1)
gui.write_text(g, encoding='utf-8')
PY_FULL_PERF_SOURCE
"""
    return text.replace(anchor, anchor + patch, 1)


def tune_release_flags(text: str) -> str:
    stable = '''  emcmake cmake .. \\
    -DHOST_BINARY_DIR=../build-host \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DOPTION_USE_ASSERTS=OFF
'''
    tuned = '''  emcmake cmake .. \\
    -DHOST_BINARY_DIR=../build-host \\
    -DCMAKE_BUILD_TYPE=Release \\
    -DOPTION_USE_ASSERTS=OFF \\
    -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG -msimd128 -flto=thin -sSUPPORT_LONGJMP=wasm" \\
    -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -msimd128 -flto=thin -fwasm-exceptions" \\
    -DCMAKE_EXE_LINKER_FLAGS_RELEASE="-O3 -msimd128 -flto=thin -fwasm-exceptions -sSUPPORT_LONGJMP=wasm"
'''
    if tuned in text:
        return text
    if text.count(stable) != 1:
        raise SystemExit(f"Expected one stable Emscripten configure block, got {text.count(stable)}")
    return text.replace(stable, tuned, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('build_script', type=Path)
    args = ap.parse_args()

    path = args.build_script
    text = path.read_text(encoding='utf-8')
    text = inject_source_patch(text)
    text = tune_release_flags(text)

    required = (
        '-fwasm-exceptions',
        '-sSUPPORT_LONGJMP=wasm',
        '-msimd128',
        '-flto=thin',
        'last_browser_yield_ms',
    )
    for token in required:
        if token not in text:
            raise SystemExit(f'Missing performance invariant in patched build: {token}')

    path.write_text(text, encoding='utf-8')
    print('Full browser performance profile enabled: native Wasm EH, SIMD, ThinLTO, cooperative mapgen yields.')


if __name__ == '__main__':
    main()
