#!/usr/bin/env python3
"""Apply profiler-driven browser performance tuning to the tested v14 pipeline.

This patch deliberately keeps OpenTTD's proven Asyncify/JS exception model for
browser compatibility. Native Wasm exceptions are not mixed with ASYNCIFY.
The safe performance layer consists of:
  * -O3 + wasm SIMD + ThinLTO for C/C++ and the final link;
  * cooperative event-loop yields during synchronous world generation so very
    large maps no longer become one giant browser LongTask;
  * a fair aggregate Squirrel opcode budget when more than four AIs are active,
    preventing AI CPU cost from scaling linearly to 14 full VM slices per tick.
"""
from __future__ import annotations

import argparse
from pathlib import Path

SOURCE_PATCH_MARKER = "# V14_FULL_PERF_SOURCE_PATCH\n"


def inject_source_patch(text: str) -> str:
    if SOURCE_PATCH_MARKER.strip() in text:
        return text

    anchor = "git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd\n"
    if text.count(anchor) != 1:
        raise SystemExit(f"Expected one OpenTTD clone anchor, got {text.count(anchor)}")

    patch = r"""# V14_FULL_PERF_SOURCE_PATCH
python3 - <<'PY_FULL_PERF_SOURCE'
from pathlib import Path

# World generation is synchronous in this browser port. The stock progress
# code pumps OpenTTD's paused loop but does not return to the browser event loop,
# so a 4096x4096 generation can become one enormous LongTask. ASYNCIFY is part
# of the tested upstream Emscripten configuration; yield at most once every
# 32 ms from the progress path without changing generation semantics.
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

# With many competitors the stock AI scheduler gives every Squirrel VM a full
# script_max_opcode_till_suspend slice in the same tick. At 14 AIs this makes
# script work scale roughly 14x on one browser main thread. Keep every AI
# scheduled every eligible tick, but cap the aggregate browser VM work to the
# equivalent of four full configured slices. This only changes the amount of
# script computation per tick; companies, sleep counters and scheduling remain
# active and fair for every AI. The user's configured limit is never increased.
ai = Path('openttd/src/ai/ai_core.cpp')
a = ai.read_text(encoding='utf-8')
ai_anchor = '''\tBackup<CompanyID> cur_company(_current_company);
\tfor (const Company *c : Company::Iterate()) {
'''
ai_block = '''#ifdef __EMSCRIPTEN__
\tuint32_t browser_active_ai_count = 0;
\tfor (const Company *c : Company::Iterate()) {
\t\tif (c->is_ai && c->ai_instance != nullptr) browser_active_ai_count++;
\t}

\tconst uint32_t browser_configured_opcode_budget = _settings_game.script.script_max_opcode_till_suspend;
\tuint32_t browser_ai_opcode_budget = browser_configured_opcode_budget;
\tif (browser_active_ai_count > 4 && browser_configured_opcode_budget > 0) {
\t\tbrowser_ai_opcode_budget = static_cast<uint32_t>(
\t\t\t(static_cast<uint64_t>(browser_configured_opcode_budget) * 4u) / browser_active_ai_count);
\t\tif (browser_ai_opcode_budget == 0) browser_ai_opcode_budget = 1;
\t}
\tAutoRestoreBackup<uint32_t> browser_ai_budget(
\t\t_settings_game.script.script_max_opcode_till_suspend, browser_ai_opcode_budget);
#endif

\tBackup<CompanyID> cur_company(_current_company);
\tfor (const Company *c : Company::Iterate()) {
'''
if 'browser_ai_opcode_budget' not in a:
    if a.count(ai_anchor) != 1:
        raise SystemExit(f'Expected one AI scheduler anchor, got {a.count(ai_anchor)}')
    a = a.replace(ai_anchor, ai_block, 1)
ai.write_text(a, encoding='utf-8')
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
    -DCMAKE_C_FLAGS_RELEASE="-O3 -DNDEBUG -msimd128 -flto=thin" \\
    -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -msimd128 -flto=thin" \\
    -DCMAKE_EXE_LINKER_FLAGS_RELEASE="-O3 -msimd128 -flto=thin"
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

    for forbidden in ('-fwasm-exceptions', '-sSUPPORT_LONGJMP=wasm'):
        if forbidden in text:
            raise SystemExit(f'Incompatible native-EH tuning must not be present: {forbidden}')

    required = ('-msimd128', '-flto=thin', 'last_browser_yield_ms', 'browser_ai_opcode_budget')
    for token in required:
        if token not in text:
            raise SystemExit(f'Missing performance invariant in patched build: {token}')

    path.write_text(text, encoding='utf-8')
    print('Safe browser performance profile enabled: O3, wasm SIMD, ThinLTO, cooperative mapgen yields, fair aggregate AI VM budget; Asyncify compatibility retained.')


if __name__ == '__main__':
    main()
