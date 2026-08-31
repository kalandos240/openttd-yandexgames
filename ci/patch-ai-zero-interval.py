#!/usr/bin/env python3
"""Make browser AI startup deterministic and keep many competitors responsive.

For the Emscripten edition only this patch:
- makes competitors_interval=0 mean "start requested competitors now";
- rearms the competitor timer after StartupCompanies() aborts old-game state;
- creates one missing AI every few game ticks instead of all AIs in one frame;
- phase-shifts equal-speed AI VMs across frames without reducing per-AI frequency;
- selecting an AI slot in the new-game UI raises max_no_competitors as needed.

Desktop/native OpenTTD behaviour and non-zero competitor intervals are unchanged.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Zero-minute interval: make the fast path reachable after every new game.
# ---------------------------------------------------------------------------
company_path = Path('openttd/src/company_cmd.cpp')
if not company_path.is_file():
    raise SystemExit(f'OpenTTD source file is missing: {company_path}')
company = company_path.read_text(encoding='utf-8')

early_return = '\tif (_settings_game.difficulty.competitors_interval == 0) return;\n'
early_replacement = (
    '\t/* Web port: zero means start requested AI competitors immediately.\n'
    '\t * The Emscripten path below rearms until the requested count exists. */\n'
)
if company.count(early_return) != 1:
    raise SystemExit(f'Expected one zero-interval AI early-return, found {company.count(early_return)}')
company = company.replace(early_return, early_replacement, 1)

startup_old = '''void StartupCompanies()\n{\n\t/* Ensure the timeout is aborted, so it doesn't fire based on information of the last game. */\n\t_new_competitor_timeout.Abort();\n}\n'''
startup_new = '''void StartupCompanies()\n{\n#ifdef __EMSCRIPTEN__\n\t/* Browser zero-interval AI bootstrap: StartupCompanies normally aborts the\n\t * competitor timer. With interval 0 the web fast path needs one initial\n\t * firing after newgame; subsequent firings are rearmed below. */\n\tif (_settings_game.difficulty.competitors_interval == 0 &&\n\t\t\t_settings_game.difficulty.max_no_competitors > 0) {\n\t\t_new_competitor_timeout.Reset({ TimerGameTick::Priority::COMPETITOR_TIMEOUT, 1 });\n\t\treturn;\n\t}\n#endif\n\n\t/* Ensure the timeout is aborted, so it doesn't fire based on information of the last game. */\n\t_new_competitor_timeout.Abort();\n}\n'''
if company.count(startup_old) != 1:
    raise SystemExit(f'Expected one StartupCompanies timer-abort block, found {company.count(startup_old)}')
company = company.replace(startup_old, startup_new, 1)

# Do not instantiate every requested Squirrel VM on one browser frame. The
# surrounding OpenTTD code adds its normal tiny random jitter and Reset()s this
# timeout after the block, so 8 means one new AI roughly every 7-8 game ticks.
zero_old = '''\t\tif (timeout == 0) {\n\t\t\t/* count number of competitors */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t}\n'''
zero_new = '''\t\tif (timeout == 0) {\n\t\t\t/* count number of competitors */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Browser AI startup staggering: keep zero-minute semantics but create\n\t\t\t * one missing AI every few ticks so VM/pathfinder initialization cannot\n\t\t\t * collapse into one enormous browser frame. */\n\t\t\tconst bool can_start = !_networking || Company::GetNumItems() < _settings_client.network.max_companies;\n\t\t\tif (num_ais < _settings_game.difficulty.max_no_competitors && can_start) {\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t\ttimeout = 8;\n\t\t\t} else {\n\t\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t\t}\n#else\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n#endif\n\t\t}\n'''
if company.count(zero_old) != 1:
    raise SystemExit(f'Expected one stock zero-interval creation block, found {company.count(zero_old)}')
company = company.replace(zero_old, zero_new, 1)
company_path.write_text(company, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. Keep each AI's configured speed but phase equal-speed AIs across frames.
#    The full-performance layer may already have inserted opcode-budget logic
#    before the Company loop; these smaller anchors deliberately remain valid.
# ---------------------------------------------------------------------------
ai_path = Path('openttd/src/ai/ai_core.cpp')
ai = ai_path.read_text(encoding='utf-8')

speed_old = '''\t/* The speed with which AIs go, is limited by the 'competitor_speed' */\n\tAI::frame_counter++;\n\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tif ((AI::frame_counter & ((1 << (4 - _settings_game.difficulty.competitor_speed)) - 1)) != 0) return;\n'''
speed_new = '''\t/* The speed with which AIs go, is limited by the 'competitor_speed'. */\n\tAI::frame_counter++;\n\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tconst uint run_mask = (1 << (4 - _settings_game.difficulty.competitor_speed)) - 1;\n#ifndef __EMSCRIPTEN__\n\tif ((AI::frame_counter & run_mask) != 0) return;\n#endif\n'''
if ai.count(speed_old) != 1:
    raise SystemExit(f'Expected one stock AI speed gate, found {ai.count(speed_old)}')
ai = ai.replace(speed_old, speed_new, 1)

loop_old = '''\t\tif (c->is_ai) {\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\tcur_company.Change(c->index);\n\t\t\tc->ai_instance->GameLoop();\n\t\t\t/* Occasionally collect garbage; every 255 ticks do one company.\n\t\t\t * Effectively collecting garbage once every two months per AI. */\n\t\t\tif ((AI::frame_counter & 255) == 0 && (CompanyID)GB(AI::frame_counter, 8, 4) == c->index) {\n\t\t\t\tc->ai_instance->CollectGarbage();\n\t\t\t}\n\t\t} else {\n'''
loop_new = '''\t\tif (c->is_ai) {\n\t\t\tconst bool collect_garbage = (AI::frame_counter & 255) == 0 && (CompanyID)GB(AI::frame_counter, 8, 4) == c->index;\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Browser AI frame staggering: preserve each company's execution\n\t\t\t * frequency, but distribute equal-speed AIs over different frames. */\n\t\t\tif (((AI::frame_counter + c->index.base()) & run_mask) != 0) {\n\t\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\t\tif (collect_garbage) {\n\t\t\t\t\tcur_company.Change(c->index);\n\t\t\t\t\tc->ai_instance->CollectGarbage();\n\t\t\t\t}\n\t\t\t\tcontinue;\n\t\t\t}\n#endif\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\tcur_company.Change(c->index);\n\t\t\tc->ai_instance->GameLoop();\n\t\t\t/* Occasionally collect garbage; every 255 ticks do one company.\n\t\t\t * Effectively collecting garbage once every two months per AI. */\n\t\t\tif (collect_garbage) c->ai_instance->CollectGarbage();\n\t\t} else {\n'''
if ai.count(loop_old) != 1:
    raise SystemExit(f'Expected one stock AI company-loop body, found {ai.count(loop_old)}')
ai = ai.replace(loop_old, loop_new, 1)
ai_path.write_text(ai, encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Selecting an AI slot in the new-game UI must make that slot active.
# ---------------------------------------------------------------------------
gui_path = Path('openttd/src/script/script_gui.cpp')
gui = gui_path.read_text(encoding='utf-8')
include_anchor = '#include "../settings_gui.h"\n'
include_line = '#include "../settings_func.h"\n'
if include_line not in gui:
    if gui.count(include_anchor) != 1:
        raise SystemExit('Could not find settings_gui include anchor')
    gui = gui.replace(include_anchor, include_anchor + include_line, 1)

select_old = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\t\tif (_game_mode == GM_EDITOR) {\n'''
select_new = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t/* Browser AI slot activation: CompanyID is zero-based while the\n\t\t * difficulty setting is a count. Never reduce a larger user choice. */\n\t\tif (this->slot != OWNER_DEITY && _game_mode != GM_NORMAL) {\n\t\t\tconst int required_competitors = this->slot.base() + 1;\n\t\t\tif (GetGameSettings().difficulty.max_no_competitors < required_competitors) {\n\t\t\t\tIConsoleSetSetting("difficulty.max_no_competitors", required_competitors);\n\t\t\t}\n\t\t}\n#endif\n\t\tif (_game_mode == GM_EDITOR) {\n'''
if gui.count(select_old) != 1:
    raise SystemExit(f'Expected one ScriptListWindow selection block, found {gui.count(select_old)}')
gui = gui.replace(select_old, select_new, 1)
gui_path.write_text(gui, encoding='utf-8')

# Deterministic source assertions: fail build early if any layer did not apply.
checks = {
    company_path: (
        'zero means start requested AI competitors immediately',
        'Browser zero-interval AI bootstrap',
        'Browser AI startup staggering',
        'timeout = 8;',
    ),
    ai_path: (
        'const uint run_mask =',
        'Browser AI frame staggering',
        'c->index.base()) & run_mask',
    ),
    gui_path: (
        'Browser AI slot activation',
        'const int required_competitors = this->slot.base() + 1;',
        'IConsoleSetSetting("difficulty.max_no_competitors", required_competitors);',
    ),
}
for p, markers in checks.items():
    body = p.read_text(encoding='utf-8')
    for marker in markers:
        if marker not in body:
            raise SystemExit(f'Missing browser AI patch marker in {p}: {marker}')

print('Patched browser AI: zero-interval bootstrap, staggered startup, staggered VM frames, slot activation.')
