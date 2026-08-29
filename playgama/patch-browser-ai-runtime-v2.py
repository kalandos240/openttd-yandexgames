#!/usr/bin/env python3
"""Browser-specific AI scheduling for OpenTTD 15.3.

Goals:
- keep the player's AI count and interval authoritative;
- selecting a concrete AI activates that slot for a new game;
- interval 0 stays effectively immediate, but missing AIs are not all created
  in the same browser frame;
- keep each AI's configured execution frequency unchanged while phase-spreading
  equal-speed AIs over browser frames;
- expose AI start/death diagnostics in the browser console.
"""
from pathlib import Path

ROOT = Path("openttd")
if not ROOT.is_dir():
    raise SystemExit("OpenTTD source tree is missing")


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Could not patch {label}: expected one anchor, got {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Explicitly selecting AI slot N must activate at least N + 1 competitors.
# ---------------------------------------------------------------------------
script_gui = ROOT / "src/script/script_gui.cpp"
text = script_gui.read_text(encoding="utf-8")

include_anchor = '#include "../settings_gui.h"\n'
include_line = '#include "../settings_func.h"\n'
if include_line not in text:
    if text.count(include_anchor) != 1:
        raise SystemExit("Could not locate settings_gui include anchor")
    text = text.replace(include_anchor, include_anchor + include_line, 1)

change_old = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\t\tif (_game_mode == GM_EDITOR) {\n'''
change_new = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\n#ifdef __EMSCRIPTEN__\n\t\t/* Script selection and competitor count are separate upstream settings.\n\t\t * If the player explicitly accepts an AI in slot N, activate at least\n\t\t * N + 1 competitors. Never reduce a larger count and never alter the\n\t\t * competitor interval selected by the player. */\n\t\tif (this->slot != OWNER_DEITY && _game_mode != GM_NORMAL) {\n\t\t\tconst int required_competitors = this->slot.base() + 1;\n\t\t\tif (GetGameSettings().difficulty.max_no_competitors < required_competitors) {\n\t\t\t\tIConsoleSetSetting("difficulty.max_no_competitors", required_competitors);\n\t\t\t}\n\t\t}\n#endif\n\n\t\tif (_game_mode == GM_EDITOR) {\n'''
if text.count(change_old) != 1:
    raise SystemExit(f"Could not locate ScriptListWindow::ChangeScript block ({text.count(change_old)})")
text = text.replace(change_old, change_new, 1)
script_gui.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 2. Interval 0: create one missing AI every ~7-8 ticks on Emscripten.
#
# Use stable structural anchors instead of reproducing the complete upstream
# block. Other browser patches may change comments/whitespace around this code.
# ---------------------------------------------------------------------------
company_cmd = ROOT / "src/company_cmd.cpp"
text = company_cmd.read_text(encoding="utf-8")
start_anchor = "\t\tif (timeout == 0) {\n"
end_anchor = "\t\t/* Randomize a bit when the AI is actually going to start;"
if text.count(start_anchor) != 1:
    raise SystemExit(f"Could not locate zero-interval start anchor ({text.count(start_anchor)})")
start = text.index(start_anchor)
end = text.find(end_anchor, start)
if end < 0:
    raise SystemExit("Could not locate zero-interval end anchor")

new_zero_interval = '''\t\tif (timeout == 0) {\n\t\t\t/* count number of competitors */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Browser OpenTTD runs game logic, Squirrel and pathfinders on the main\n\t\t\t * Wasm thread. Creating every missing AI in one tick synchronizes all\n\t\t\t * VMs and creates a large frame spike. Zero minutes still means start\n\t\t\t * immediately in game terms, but add one company every few ticks. */\n\t\t\tconst bool can_start = !_networking || Company::GetNumItems() < _settings_client.network.max_companies;\n\t\t\tif (num_ais < _settings_game.difficulty.max_no_competitors && can_start) {\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t\ttimeout = 8;\n\t\t\t} else {\n\t\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t\t}\n#else\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n#endif\n\t\t}\n'''
text = text[:start] + new_zero_interval + text[end:]
company_cmd.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 3. Phase-spread AI VM work across browser frames without lowering AI speed.
# ---------------------------------------------------------------------------
ai_core = ROOT / "src/ai/ai_core.cpp"
text = ai_core.read_text(encoding="utf-8")
loop_start_anchor = "/* static */ void AI::GameLoop()\n{\n"
loop_end_anchor = "/* static */ uint AI::GetTick()\n"
if text.count(loop_start_anchor) != 1:
    raise SystemExit(f"Could not locate AI::GameLoop start ({text.count(loop_start_anchor)})")
loop_start = text.index(loop_start_anchor)
loop_end = text.find(loop_end_anchor, loop_start)
if loop_end < 0:
    raise SystemExit("Could not locate AI::GameLoop end")

new_game_loop = '''/* static */ void AI::GameLoop()\n{\n\t/* If we are in networking, only servers run this function, and that only if it is allowed */\n\tif (_networking && (!_network_server || !_settings_game.ai.ai_in_multiplayer)) return;\n\n\t/* The speed with which AIs go, is limited by the 'competitor_speed'. */\n\tAI::frame_counter++;\n\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tconst uint run_mask = (1 << (4 - _settings_game.difficulty.competitor_speed)) - 1;\n#ifndef __EMSCRIPTEN__\n\tif ((AI::frame_counter & run_mask) != 0) return;\n#endif\n\n\tBackup<CompanyID> cur_company(_current_company);\n\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n\t\t\tconst bool collect_garbage = (AI::frame_counter & 255) == 0 && (CompanyID)GB(AI::frame_counter, 8, 4) == c->index;\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Each AI keeps the same 1/(mask+1) execution frequency as desktop,\n\t\t\t * but company index supplies a phase. With default speed, nine AIs are\n\t\t\t * distributed as roughly 2-3 VMs per frame instead of nine VMs in one. */\n\t\t\tif (((AI::frame_counter + c->index.base()) & run_mask) != 0) {\n\t\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\t\tif (collect_garbage) {\n\t\t\t\t\tcur_company.Change(c->index);\n\t\t\t\t\tc->ai_instance->CollectGarbage();\n\t\t\t\t}\n\t\t\t\tcontinue;\n\t\t\t}\n#endif\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\tcur_company.Change(c->index);\n\t\t\tc->ai_instance->GameLoop();\n\t\t\t/* Occasionally collect garbage; every 255 ticks do one company.\n\t\t\t * Effectively collecting garbage once every two months per AI. */\n\t\t\tif (collect_garbage) c->ai_instance->CollectGarbage();\n\t\t} else {\n\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t}\n\t}\n\tcur_company.Restore();\n}\n\n'''
text = text[:loop_start] + new_game_loop + text[loop_end:]

# Log whether each newly-created VM survived initialization.
start_old = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n\n\tcur_company.Restore();\n'''
start_new = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI start: company={}, script='{}', version={}, alive={}", company.base(), info->GetName(), info->GetVersion(), c->ai_instance->IsAlive());\n#endif\n\n\tcur_company.Restore();\n'''
if text.count(start_old) != 1:
    raise SystemExit(f"Could not locate AI::StartNew diagnostic anchor ({text.count(start_old)})")
text = text.replace(start_old, start_new, 1)
ai_core.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 4. AI crashes during SM_NEWGAME are normally hidden by upstream UI. Keep the
#    UI behaviour but emit one browser-console line before that early return.
# ---------------------------------------------------------------------------
ai_instance = ROOT / "src/ai/ai_instance.cpp"
text = ai_instance.read_text(encoding="utf-8")
died_old = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
died_new = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI died: company={}, switch_mode={}", _current_company.base(), static_cast<int>(_switch_mode));\n#endif\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
if text.count(died_old) != 1:
    raise SystemExit(f"Could not locate AIInstance::Died anchor ({text.count(died_old)})")
text = text.replace(died_old, died_new, 1)
ai_instance.write_text(text, encoding="utf-8")


# Strong postconditions: fail the source stage rather than ship a partial fix.
checks = {
    script_gui: [
        'const int required_competitors = this->slot.base() + 1;',
        'IConsoleSetSetting("difficulty.max_no_competitors", required_competitors);',
    ],
    company_cmd: [
        'timeout = 8;',
        'Browser OpenTTD runs game logic, Squirrel and pathfinders on the main',
    ],
    ai_core: [
        'const uint run_mask = (1 << (4 - _settings_game.difficulty.competitor_speed)) - 1;',
        'AI::frame_counter + c->index.base()',
        'Browser AI start:',
    ],
    ai_instance: [
        'Browser AI died:',
    ],
}
for path, markers in checks.items():
    patched = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in patched:
            raise SystemExit(f"Missing browser AI marker {marker!r} in {path}")

print("Browser AI v2 applied: player settings preserved, zero-minute creation staggered, AI VM work phase-spread, diagnostics enabled.")
