#!/usr/bin/env python3
"""Apply profiler-driven browser performance tuning to the tested v14 pipeline.

The release stays on OpenTTD's proven synchronous Emscripten runtime; we do not
turn on global Asyncify merely to make map generation yield, because that would
instrument a large part of the normal game hot path. The safe performance layer
consists of:
  * -O3 + wasm SIMD + ThinLTO for C/C++ and the final link;
  * a browser-only reduction of the *pre-game* tile-loop warmup on very large
    maps from five complete tile-update sweeps to three. Every tile is still
    warmed multiple times; normal simulation after game start is unchanged;
  * a fair aggregate Squirrel opcode budget when many AIs are active, preventing
    AI CPU cost from scaling linearly to 14 full VM slices per eligible tick;
  * change-only browser telemetry for active AI count / effective opcode budget,
    so the production benchmark can prove that all requested competitors run.
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

# OpenTTD warms a newly generated non-empty map with 0x500 (1280) calls to
# RunTileLoop(). RunTileLoop is guaranteed to visit every tile once per 256
# ticks, so stock performs five complete pre-game sweeps. On an 8M-16M tile web
# map that means tens of millions of synchronous tile callbacks before the first
# playable frame. For very large browser maps, three complete sweeps preserve
# multiple snow/ground/tree settling passes while cutting this warmup work by
# 40%. Normal post-start tile simulation is untouched.
genworld = Path('openttd/src/genworld.cpp')
g = genworld.read_text(encoding='utf-8')
old_warmup = '''\t\t\tSetGeneratingWorldProgress(GWP_RUNTILELOOP, 0x500);
\t\t\tfor (i = 0; i < 0x500; i++) {
\t\t\t\tRunTileLoop();
\t\t\t\tTimerGameTick::counter++;
\t\t\t\tIncreaseGeneratingWorldProgress(GWP_RUNTILELOOP);
\t\t\t}
'''
new_warmup = '''\t\t\tuint browser_tile_warmup_loops = 0x500;
#ifdef __EMSCRIPTEN__
\t\t\t/* 256 RunTileLoop calls are one complete tile-update sweep. Keep the
\t\t\t * stock five sweeps for normal maps and use three only from 8M tiles. */
\t\t\tif (Map::Size() >= 8u * 1024u * 1024u) browser_tile_warmup_loops = 0x300;
#endif
\t\t\tSetGeneratingWorldProgress(GWP_RUNTILELOOP, browser_tile_warmup_loops);
\t\t\tfor (i = 0; i < browser_tile_warmup_loops; i++) {
\t\t\t\tRunTileLoop();
\t\t\t\tTimerGameTick::counter++;
\t\t\t\tIncreaseGeneratingWorldProgress(GWP_RUNTILELOOP);
\t\t\t}
'''
if 'browser_tile_warmup_loops' not in g:
    if g.count(old_warmup) != 1:
        raise SystemExit(f'Expected one stock world warmup loop, got {g.count(old_warmup)}')
    g = g.replace(old_warmup, new_warmup, 1)
genworld.write_text(g, encoding='utf-8')

# With many competitors the stock AI scheduler gives every Squirrel VM a full
# script_max_opcode_till_suspend slice in the same eligible tick. On a browser
# main thread, 14 AIs therefore scale script work roughly 14x. Keep every AI
# scheduled every eligible tick, but cap aggregate VM work to the equivalent of
# six full configured slices. <= 6 active AIs are completely unchanged. At 14
# AIs, each still receives ~42.9% of a normal slice every eligible AI tick.
ai = Path('openttd/src/ai/ai_core.cpp')
a = ai.read_text(encoding='utf-8')
include_anchor = '#include "../framerate_type.h"\n'
include_block = '''#include "../framerate_type.h"
#ifdef __EMSCRIPTEN__
#\tinclude <emscripten.h>
#endif
'''
if '#\tinclude <emscripten.h>' not in a:
    if a.count(include_anchor) != 1:
        raise SystemExit(f'Expected one AI framerate include anchor, got {a.count(include_anchor)}')
    a = a.replace(include_anchor, include_block, 1)

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
\tif (browser_active_ai_count > 6 && browser_configured_opcode_budget > 0) {
\t\tbrowser_ai_opcode_budget = static_cast<uint32_t>(
\t\t\t(static_cast<uint64_t>(browser_configured_opcode_budget) * 6u) / browser_active_ai_count);
\t\tif (browser_ai_opcode_budget == 0) browser_ai_opcode_budget = 1;
\t}

\t/* Export benchmark evidence only when scheduler state changes, not every
\t * tick. Avoid a JavaScript object literal inside EM_ASM: the Emscripten
\t * variadic macro parser can interpret ':' tokens as C++ and fail compilation. */
\tstatic uint32_t browser_reported_ai_count = ~uint32_t{0};
\tstatic uint32_t browser_reported_ai_budget = ~uint32_t{0};
\tstatic uint32_t browser_reported_configured_budget = ~uint32_t{0};
\tif (browser_reported_ai_count != browser_active_ai_count ||
\t\t\tbrowser_reported_ai_budget != browser_ai_opcode_budget ||
\t\t\tbrowser_reported_configured_budget != browser_configured_opcode_budget) {
\t\tbrowser_reported_ai_count = browser_active_ai_count;
\t\tbrowser_reported_ai_budget = browser_ai_opcode_budget;
\t\tbrowser_reported_configured_budget = browser_configured_opcode_budget;
\t\tEM_ASM({
\t\t\tif (!Module.__openttdAIStats) Module.__openttdAIStats = {};
\t\t\tModule.__openttdAIStats.activeAI = $0;
\t\t\tModule.__openttdAIStats.configuredOpcodeBudget = $1;
\t\t\tModule.__openttdAIStats.effectiveOpcodeBudget = $2;
\t\t}, browser_active_ai_count, browser_configured_opcode_budget, browser_ai_opcode_budget);
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

    # Native Wasm EH is deliberately not mixed with the tested synchronous
    # browser runtime here; keep compatibility with the existing release.
    for forbidden in ('-fwasm-exceptions', '-sSUPPORT_LONGJMP=wasm', '-sASYNCIFY'):
        if forbidden in text:
            raise SystemExit(f'Unsupported experimental runtime flag must not be present: {forbidden}')

    required = ('-msimd128', '-flto=thin', 'browser_tile_warmup_loops', 'browser_ai_opcode_budget', '__openttdAIStats')
    for token in required:
        if token not in text:
            raise SystemExit(f'Missing performance invariant in patched build: {token}')

    path.write_text(text, encoding='utf-8')
    print('Safe browser performance profile enabled: O3, wasm SIMD, ThinLTO, large-map warmup reduction, fair aggregate AI VM budget, change-only AI telemetry.')


if __name__ == '__main__':
    main()
