#!/usr/bin/env python3
"""Make browser AI selection correct and keep many AIs responsive without frame spikes.

This patch keeps the player's AI count/interval authoritative, activates an
explicitly selected AI slot, and changes only the Emscripten runtime scheduling:
zero-minute startup is still immediate in game terms, but competitors are
created a few ticks apart and equal-speed AI work is phase-shifted across
frames. This prevents 5-15 Squirrel/pathfinder instances from all consuming
the same browser frame.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Explicitly choosing an AI slot must make that slot active for a new game.
# ---------------------------------------------------------------------------
path = Path('openttd/src/script/script_gui.cpp')
text = path.read_text(encoding='utf-8')

# IConsoleSetSetting is the normal settings mutation path and preserves all
# callbacks/validation. script_gui.cpp does not include its declaration upstream.
include_anchor = '#include "../settings_gui.h"\n'
include_line = '#include "../settings_func.h"\n'
if include_line not in text:
    if text.count(include_anchor) != 1:
        raise SystemExit('Could not find settings_gui include anchor')
    text = text.replace(include_anchor, include_anchor + include_line, 1)

old = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\t\tif (_game_mode == GM_EDITOR) {\n'''
new = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\n#ifdef __EMSCRIPTEN__\n\t\t/* Choosing an AI for a new game must also make that slot active. Upstream\n\t\t * OpenTTD deliberately keeps script selection and competitor count\n\t\t * separate, which is easy to miss in the browser UI. CompanyID is zero\n\t\t * based, while max_no_competitors is a count, hence slot + 1. Derive only\n\t\t * the minimum count from the slot the player accepted; never touch the\n\t\t * interval and never reduce an already larger player-selected count.\n\t\t * The old buggy form was: const int required_competitors = this->slot.base(); */\n\t\tif (this->slot != OWNER_DEITY && _game_mode != GM_NORMAL) {\n\t\t\tconst int required_competitors = this->slot.base() + 1;\n\t\t\tif (GetGameSettings().difficulty.max_no_competitors < required_competitors) {\n\t\t\t\tIConsoleSetSetting("difficulty.max_no_competitors", required_competitors);\n\t\t\t}\n\t\t}\n#endif\n\n\t\tif (_game_mode == GM_EDITOR) {\n'''

if text.count(old) != 1:
    raise SystemExit(f'Could not locate ScriptListWindow::ChangeScript block ({text.count(old)})')
text = text.replace(old, new, 1)

for marker in (
    '#include "../settings_func.h"',
    'const int required_competitors = this->slot.base() + 1;',
    'IConsoleSetSetting("difficulty.max_no_competitors", required_competitors);',
):
    if marker not in text:
        raise SystemExit(f'AI player-selection patch missing marker: {marker}')

path.write_text(text, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. A zero-minute interval must not instantiate every missing AI in one tick.
#    In browser builds one AI is posted every ~7-8 game ticks. Nine AIs still
#    appear in roughly two seconds, but their VM/pathfinder work is de-synced.
# ---------------------------------------------------------------------------
company_path = Path('openttd/src/company_cmd.cpp')
company_text = company_path.read_text(encoding='utf-8')

old_zero_interval = '''\t\tif (timeout == 0) {\n\t\t\t/* count number of competitors */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t}\n'''
new_zero_interval = '''\t\tif (timeout == 0) {\n\t\t\t/* count number of competitors */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\t/* A browser has one main JS/Wasm thread. Posting every missing AI here\n\t\t\t * makes all Squirrel VMs initialise in one tick and later wake in phase,\n\t\t\t * which produces severe frame spikes with several pathfinders. Keep the\n\t\t\t * user's zero-minute semantics, but spread creation over a handful of\n\t\t\t * ticks. The regular randomisation below turns 8 into roughly 7-8 ticks. */\n\t\t\tconst bool can_start = !_networking || Company::GetNumItems() < _settings_client.network.max_companies;\n\t\t\tif (num_ais < _settings_game.difficulty.max_no_competitors && can_start) {\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t\ttimeout = 8;\n\t\t\t} else {\n\t\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t\t}\n#else\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n#endif\n\t\t}\n'''

if company_text.count(old_zero_interval) != 1:
    raise SystemExit(f'Could not locate zero-interval competitor block ({company_text.count(old_zero_interval)})')
company_text = company_text.replace(old_zero_interval, new_zero_interval, 1)
company_path.write_text(company_text, encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Preserve each AI's configured speed, but distribute equal-speed AIs over
#    different browser frames instead of running every AI on the same frame.
# ---------------------------------------------------------------------------
ai_core_path = Path('openttd/src/ai/ai_core.cpp')
ai_core = ai_core_path.read_text(encoding='utf-8')

old_game_loop = '''/* static */ void AI::GameLoop()\n{\n\t/* If we are in networking, only servers run this function, and that only if it is allowed */\n\tif (_networking && (!_network_server || !_settings_game.ai.ai_in_multiplayer)) return;\n\n\t/* The speed with which AIs go, is limited by the 'competitor_speed' */\n\tAI::frame_counter++;\n\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tif ((AI::frame_counter & ((1 << (4 - _settings_game.difficulty.competitor_speed)) - 1)) != 0) return;\n\n\tBackup<CompanyID> cur_company(_current_company);\n\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\tcur_company.Change(c->index);\n\t\t\tc->ai_instance->GameLoop();\n\t\t\t/* Occasionally collect garbage; every 255 ticks do one company.\n\t\t\t * Effectively collecting garbage once every two months per AI. */\n\t\t\tif ((AI::frame_counter & 255) == 0 && (CompanyID)GB(AI::frame_counter, 8, 4) == c->index) {\n\t\t\t\tc->ai_instance->CollectGarbage();\n\t\t\t}\n\t\t} else {\n\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t}\n\t}\n\tcur_company.Restore();\n}\n'''
new_game_loop = '''/* static */ void AI::GameLoop()\n{\n\t/* If we are in networking, only servers run this function, and that only if it is allowed */\n\tif (_networking && (!_network_server || !_settings_game.ai.ai_in_multiplayer)) return;\n\n\t/* The speed with which AIs go, is limited by the 'competitor_speed'. */\n\tAI::frame_counter++;\n\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tconst uint run_mask = (1 << (4 - _settings_game.difficulty.competitor_speed)) - 1;\n#ifndef __EMSCRIPTEN__\n\tif ((AI::frame_counter & run_mask) != 0) return;\n#endif\n\n\tBackup<CompanyID> cur_company(_current_company);\n\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n\t\t\tconst bool collect_garbage = (AI::frame_counter & 255) == 0 && (CompanyID)GB(AI::frame_counter, 8, 4) == c->index;\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Keep exactly the same per-AI execution frequency as desktop, but give\n\t\t\t * each company a phase. At the default speed (mask 3), nine AIs become\n\t\t\t * roughly 2-3 AI VMs per frame instead of nine VMs every fourth frame. */\n\t\t\tif (((AI::frame_counter + c->index.base()) & run_mask) != 0) {\n\t\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\t\tif (collect_garbage) {\n\t\t\t\t\tcur_company.Change(c->index);\n\t\t\t\t\tc->ai_instance->CollectGarbage();\n\t\t\t\t}\n\t\t\t\tcontinue;\n\t\t\t}\n#endif\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\tcur_company.Change(c->index);\n\t\t\tc->ai_instance->GameLoop();\n\t\t\t/* Occasionally collect garbage; every 255 ticks do one company.\n\t\t\t * Effectively collecting garbage once every two months per AI. */\n\t\t\tif (collect_garbage) c->ai_instance->CollectGarbage();\n\t\t} else {\n\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t}\n\t}\n\tcur_company.Restore();\n}\n'''

if ai_core.count(old_game_loop) != 1:
    raise SystemExit(f'Could not locate AI::GameLoop block ({ai_core.count(old_game_loop)})')
ai_core = ai_core.replace(old_game_loop, new_game_loop, 1)

# Emit a level-0 line for every browser AI start. If an AI is alive but merely
# busy pathfinding, that is distinguishable from a VM that died during startup.
start_anchor = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n\n\tcur_company.Restore();\n'''
start_with_diag = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI start: company={}, script='{}', version={}, alive={}", company.base(), info->GetName(), info->GetVersion(), c->ai_instance->IsAlive());\n#endif\n\n\tcur_company.Restore();\n'''
if ai_core.count(start_anchor) != 1:
    raise SystemExit('Could not locate AI::StartNew diagnostic anchor')
ai_core = ai_core.replace(start_anchor, start_with_diag, 1)
ai_core_path.write_text(ai_core, encoding='utf-8')

# During a new-game switch upstream suppresses the normal script-debug popup.
# Keep that UX, but make a browser AI death visible in the developer console.
ai_instance_path = Path('openttd/src/ai/ai_instance.cpp')
ai_instance = ai_instance_path.read_text(encoding='utf-8')
died_anchor = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
died_with_diag = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI died: company={}, switch_mode={}", _current_company.base(), static_cast<int>(_switch_mode));\n#endif\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
if ai_instance.count(died_anchor) != 1:
    raise SystemExit('Could not locate AIInstance::Died diagnostic anchor')
ai_instance = ai_instance.replace(died_anchor, died_with_diag, 1)
ai_instance_path.write_text(ai_instance, encoding='utf-8')

# Fail the source-patch step rather than silently shipping a partially applied
# scheduler. These markers are also easy to assert in CI/artifacts.
checks = {
    company_path: (
        'timeout = 8;',
        'A browser has one main JS/Wasm thread.',
    ),
    ai_core_path: (
        'const uint run_mask = (1 << (4 - _settings_game.difficulty.competitor_speed)) - 1;',
        'AI::frame_counter + c->index.base()',
        'Browser AI start:',
    ),
    ai_instance_path: (
        'Browser AI died:',
    ),
}
for check_path, markers in checks.items():
    patched = check_path.read_text(encoding='utf-8')
    for marker in markers:
        if marker not in patched:
            raise SystemExit(f'Browser AI scheduler patch missing {marker!r} in {check_path}')

print('Browser AI fixed: selected slots activate, zero-minute startup is staggered, and AI VM work is phase-spread without reducing per-AI speed.')
