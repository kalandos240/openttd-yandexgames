#!/usr/bin/env python3
"""Add browser-only, behavior-neutral world-generation phase telemetry.

The patch records wall-clock time around the existing OpenTTD 15.3 generation
phases and publishes a single Module.__openttdGenerationStats object when world
generation finishes. It does not change loop counts, settings, RNG use, map data,
or progress updates.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "# V14_BROWSER_GENERATION_TELEMETRY_PATCH\n"


def patch_build_script(text: str) -> str:
    if MARKER.strip() in text:
        return text

    clone = "git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd\n"
    if text.count(clone) != 1:
        raise SystemExit(f"Expected one OpenTTD clone anchor, got {text.count(clone)}")

    source_patch = r'''# V14_BROWSER_GENERATION_TELEMETRY_PATCH
python3 - <<'PY_BROWSER_GENERATION_TELEMETRY'
from pathlib import Path

path = Path('openttd/src/genworld.cpp')
s = path.read_text(encoding='utf-8')

include_anchor = '''#include "safeguards.h"\n'''
include_replacement = '''#include "safeguards.h"\n\n#ifdef __EMSCRIPTEN__\n#\tinclude <emscripten.h>\n#endif\n'''
if 'include <emscripten.h>' not in s:
    if s.count(include_anchor) != 1:
        raise SystemExit(f'Expected one safeguards include anchor, got {s.count(include_anchor)}')
    s = s.replace(include_anchor, include_replacement, 1)

function_anchor = '''static void _GenerateWorld()\n{\n\t/* Make sure everything is done via OWNER_NONE. */\n'''
function_replacement = '''static void _GenerateWorld()\n{\n#ifdef __EMSCRIPTEN__\n\tconst double browser_generation_started = emscripten_get_now();\n\tdouble browser_startup_ms = 0.0;\n\tdouble browser_landscape_ms = 0.0;\n\tdouble browser_clear_ms = 0.0;\n\tdouble browser_towns_ms = 0.0;\n\tdouble browser_industries_ms = 0.0;\n\tdouble browser_objects_ms = 0.0;\n\tdouble browser_trees_ms = 0.0;\n\tdouble browser_game_init_ms = 0.0;\n\tdouble browser_tile_loop_ms = 0.0;\n\tdouble browser_script_ms = 0.0;\n#endif\n\t/* Make sure everything is done via OWNER_NONE. */\n'''
if 'browser_generation_started' not in s:
    if s.count(function_anchor) != 1:
        raise SystemExit(f'Expected one _GenerateWorld anchor, got {s.count(function_anchor)}')
    s = s.replace(function_anchor, function_replacement, 1)

startup_anchor = '''\t\tIncreaseGeneratingWorldProgress(GWP_MAP_INIT);\n\t\t/* Must start economy early because of the costs. */\n\t\tStartupEconomy();\n\t\tif (!CheckTownRoadTypes()) {\n'''
startup_replacement = '''\t\tIncreaseGeneratingWorldProgress(GWP_MAP_INIT);\n\t\t/* Must start economy early because of the costs. */\n#ifdef __EMSCRIPTEN__\n\t\tdouble browser_phase_started = emscripten_get_now();\n#endif\n\t\tStartupEconomy();\n#ifdef __EMSCRIPTEN__\n\t\tbrowser_startup_ms += emscripten_get_now() - browser_phase_started;\n#endif\n\t\tif (!CheckTownRoadTypes()) {\n'''
if 'browser_startup_ms +=' not in s:
    if s.count(startup_anchor) != 1:
        raise SystemExit(f'Expected one startup anchor, got {s.count(startup_anchor)}')
    s = s.replace(startup_anchor, startup_replacement, 1)

land_anchor = '''\t\tif (GenWorldInfo::mode != GWM_EMPTY) {\n\t\t\tlandscape_generated = GenerateLandscape(GenWorldInfo::mode);\n\t\t}\n'''
land_replacement = '''\t\tif (GenWorldInfo::mode != GWM_EMPTY) {\n#ifdef __EMSCRIPTEN__\n\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\tlandscape_generated = GenerateLandscape(GenWorldInfo::mode);\n#ifdef __EMSCRIPTEN__\n\t\t\tbrowser_landscape_ms += emscripten_get_now() - browser_phase_started;\n#endif\n\t\t}\n'''
if 'browser_landscape_ms +=' not in s:
    if s.count(land_anchor) != 1:
        raise SystemExit(f'Expected one landscape anchor, got {s.count(land_anchor)}')
    s = s.replace(land_anchor, land_replacement, 1)

clear_anchor = '''\t\t} else {\n\t\t\tGenerateClearTile();\n\t\t\tMap::CountLandTiles();\n'''
clear_replacement = '''\t\t} else {\n#ifdef __EMSCRIPTEN__\n\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\tGenerateClearTile();\n\t\t\tMap::CountLandTiles();\n#ifdef __EMSCRIPTEN__\n\t\t\tbrowser_clear_ms += emscripten_get_now() - browser_phase_started;\n#endif\n'''
if 'browser_clear_ms +=' not in s:
    if s.count(clear_anchor) != 1:
        raise SystemExit(f'Expected one generated-clear anchor, got {s.count(clear_anchor)}')
    s = s.replace(clear_anchor, clear_replacement, 1)

items_anchor = '''\t\t\tif (_game_mode != GM_EDITOR) {\n\t\t\t\tif (!GenerateTowns(_settings_game.economy.town_layout)) {\n\t\t\t\t\tHandleGeneratingWorldAbortion();\n\t\t\t\t\treturn;\n\t\t\t\t}\n\t\t\t\tGenerateIndustries();\n\t\t\t\tGenerateObjects();\n\t\t\t\tGenerateTrees();\n\t\t\t}\n'''
items_replacement = '''\t\t\tif (_game_mode != GM_EDITOR) {\n#ifdef __EMSCRIPTEN__\n\t\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\t\tif (!GenerateTowns(_settings_game.economy.town_layout)) {\n\t\t\t\t\tHandleGeneratingWorldAbortion();\n\t\t\t\t\treturn;\n\t\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\t\tbrowser_towns_ms += emscripten_get_now() - browser_phase_started;\n\t\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\t\tGenerateIndustries();\n#ifdef __EMSCRIPTEN__\n\t\t\t\tbrowser_industries_ms += emscripten_get_now() - browser_phase_started;\n\t\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\t\tGenerateObjects();\n#ifdef __EMSCRIPTEN__\n\t\t\t\tbrowser_objects_ms += emscripten_get_now() - browser_phase_started;\n\t\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\t\tGenerateTrees();\n#ifdef __EMSCRIPTEN__\n\t\t\t\tbrowser_trees_ms += emscripten_get_now() - browser_phase_started;\n#endif\n\t\t\t}\n'''
if 'browser_towns_ms +=' not in s:
    if s.count(items_anchor) != 1:
        raise SystemExit(f'Expected one world-items anchor, got {s.count(items_anchor)}')
    s = s.replace(items_anchor, items_replacement, 1)

game_init_anchor = '''\t\tSetGeneratingWorldProgress(GWP_GAME_INIT, 3);\n\t\tStartupCompanies();\n\t\tIncreaseGeneratingWorldProgress(GWP_GAME_INIT);\n\t\tStartupEngines();\n\t\tIncreaseGeneratingWorldProgress(GWP_GAME_INIT);\n\t\tStartupDisasters();\n'''
game_init_replacement = '''\t\tSetGeneratingWorldProgress(GWP_GAME_INIT, 3);\n#ifdef __EMSCRIPTEN__\n\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\tStartupCompanies();\n\t\tIncreaseGeneratingWorldProgress(GWP_GAME_INIT);\n\t\tStartupEngines();\n\t\tIncreaseGeneratingWorldProgress(GWP_GAME_INIT);\n\t\tStartupDisasters();\n#ifdef __EMSCRIPTEN__\n\t\tbrowser_game_init_ms += emscripten_get_now() - browser_phase_started;\n#endif\n'''
if 'browser_game_init_ms +=' not in s:
    if s.count(game_init_anchor) != 1:
        raise SystemExit(f'Expected one game-init anchor, got {s.count(game_init_anchor)}')
    s = s.replace(game_init_anchor, game_init_replacement, 1)

tile_anchor = '''\t\t\tSetGeneratingWorldProgress(GWP_RUNTILELOOP, 0x500);\n\t\t\tfor (i = 0; i < 0x500; i++) {\n'''
# The performance branch may already replace the literal loop count later in the
# source pipeline, so instrument immediately before the stock loop anchor.
tile_replacement = '''\t\t\tSetGeneratingWorldProgress(GWP_RUNTILELOOP, 0x500);\n#ifdef __EMSCRIPTEN__\n\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\tfor (i = 0; i < 0x500; i++) {\n'''
if 'browser_tile_loop_ms +=' not in s:
    if s.count(tile_anchor) != 1:
        raise SystemExit(f'Expected one RunTileLoop anchor, got {s.count(tile_anchor)}')
    s = s.replace(tile_anchor, tile_replacement, 1)
    tile_end = '''\t\t\t\tIncreaseGeneratingWorldProgress(GWP_RUNTILELOOP);\n\t\t\t}\n\n\t\t\tif (_game_mode != GM_EDITOR) {\n'''
    tile_end_repl = '''\t\t\t\tIncreaseGeneratingWorldProgress(GWP_RUNTILELOOP);\n\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\tbrowser_tile_loop_ms += emscripten_get_now() - browser_phase_started;\n#endif\n\n\t\t\tif (_game_mode != GM_EDITOR) {\n'''
    if s.count(tile_end) != 1:
        raise SystemExit(f'Expected one RunTileLoop end anchor, got {s.count(tile_end)}')
    s = s.replace(tile_end, tile_end_repl, 1)

script_anchor = '''\t\t\t\tif (Game::GetInstance() != nullptr) {\n\t\t\t\t\tSetGeneratingWorldProgress(GWP_RUNSCRIPT, 2500);\n\t\t\t\t\t_generating_world = true;\n'''
script_replacement = '''\t\t\t\tif (Game::GetInstance() != nullptr) {\n\t\t\t\t\tSetGeneratingWorldProgress(GWP_RUNSCRIPT, 2500);\n#ifdef __EMSCRIPTEN__\n\t\t\t\t\tbrowser_phase_started = emscripten_get_now();\n#endif\n\t\t\t\t\t_generating_world = true;\n'''
if 'browser_script_ms +=' not in s:
    if s.count(script_anchor) != 1:
        raise SystemExit(f'Expected one GameScript anchor, got {s.count(script_anchor)}')
    s = s.replace(script_anchor, script_replacement, 1)
    script_end = '''\t\t\t\t\t_generating_world = false;\n\t\t\t\t}\n'''
    script_end_repl = '''\t\t\t\t\t_generating_world = false;\n#ifdef __EMSCRIPTEN__\n\t\t\t\t\tbrowser_script_ms += emscripten_get_now() - browser_phase_started;\n#endif\n\t\t\t\t}\n'''
    if s.count(script_end) != 1:
        raise SystemExit(f'Expected one GameScript end anchor, got {s.count(script_end)}')
    s = s.replace(script_end, script_end_repl, 1)

publish_anchor = '''\t\tIncreaseGeneratingWorldProgress(GWP_GAME_START);\n\n\t\tCleanupGeneration();\n'''
publish_replacement = '''\t\tIncreaseGeneratingWorldProgress(GWP_GAME_START);\n\n#ifdef __EMSCRIPTEN__\n\t\tconst double browser_total_ms = emscripten_get_now() - browser_generation_started;\n\t\tEM_ASM({\n\t\t\tModule.__openttdGenerationStats = {\n\t\t\t\ttotalMs: $0, startupMs: $1, landscapeMs: $2, clearMs: $3,\n\t\t\t\ttownsMs: $4, industriesMs: $5, objectsMs: $6, treesMs: $7,\n\t\t\t\tgameInitMs: $8, tileLoopMs: $9, scriptMs: $10\n\t\t\t};\n\t\t}, browser_total_ms, browser_startup_ms, browser_landscape_ms, browser_clear_ms,\n\t\t\tbrowser_towns_ms, browser_industries_ms, browser_objects_ms, browser_trees_ms,\n\t\t\tbrowser_game_init_ms, browser_tile_loop_ms, browser_script_ms);\n#endif\n\n\t\tCleanupGeneration();\n'''
if 'Module.__openttdGenerationStats' not in s:
    if s.count(publish_anchor) != 1:
        raise SystemExit(f'Expected one generation publish anchor, got {s.count(publish_anchor)}')
    s = s.replace(publish_anchor, publish_replacement, 1)

path.write_text(s, encoding='utf-8')
PY_BROWSER_GENERATION_TELEMETRY
'''
    return text.replace(clone, clone + source_patch, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('build_script', type=Path)
    args = parser.parse_args()
    path = args.build_script
    text = patch_build_script(path.read_text(encoding='utf-8'))
    for token in (
        'V14_BROWSER_GENERATION_TELEMETRY_PATCH',
        'browser_landscape_ms', 'browser_towns_ms', 'browser_industries_ms',
        'browser_tile_loop_ms', 'Module.__openttdGenerationStats',
    ):
        if token not in text:
            raise SystemExit(f'Generation telemetry invariant missing: {token}')
    path.write_text(text, encoding='utf-8')
    print('Browser generation phase telemetry wired without changing generation behavior.')


if __name__ == '__main__':
    main()
