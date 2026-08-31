#!/usr/bin/env python3
"""Final browser AI runtime patch for OpenTTD 15.3.

This patch is intentionally compatible with the profiler-driven full-performance
patch which may already have inserted an aggregate Squirrel opcode budget into
AI::GameLoop(). It therefore does NOT replace AI::GameLoop() wholesale.

Goals:
- keep the player's AI count and interval authoritative;
- interval 0 starts requested AIs promptly, but only one new AI every few ticks;
- phase-spread equal-speed AI VMs across browser frames;
- preserve any aggregate opcode-budget block already present in AI::GameLoop();
- expose AI start/death diagnostics.
"""
from pathlib import Path

ROOT = Path("openttd")
if not ROOT.is_dir():
    raise SystemExit("OpenTTD source tree is missing")

# ---------------------------------------------------------------------------
# 1. Explicit AI slot selection activates at least that many competitors.
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
change_new = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\n#ifdef __EMSCRIPTEN__\n\t\t/* Selecting a concrete AI and competitor count are separate upstream\n\t\t * settings. Activating slot N therefore activates at least N + 1 slots. */\n\t\tif (this->slot != OWNER_DEITY && _game_mode != GM_NORMAL) {\n\t\t\tconst int required_competitors = this->slot.base() + 1;\n\t\t\tif (GetGameSettings().difficulty.max_no_competitors < required_competitors) {\n\t\t\t\tIConsoleSetSetting("difficulty.max_no_competitors", required_competitors);\n\t\t\t}\n\t\t}\n#endif\n\n\t\tif (_game_mode == GM_EDITOR) {\n'''
if 'const int required_competitors = this->slot.base() + 1;' not in text:
    if text.count(change_old) != 1:
        raise SystemExit(f"Could not locate ScriptListWindow::ChangeScript block ({text.count(change_old)})")
    text = text.replace(change_old, change_new, 1)
script_gui.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2. Zero-minute interval: one new AI every 8 ticks in browser builds.
# ---------------------------------------------------------------------------
company_cmd = ROOT / "src/company_cmd.cpp"
text = company_cmd.read_text(encoding="utf-8")
if 'browser-zero-ai-stagger-v3' not in text:
    start_anchor = "\t\tif (timeout == 0) {\n"
    end_anchor = "\t\t/* Randomize a bit when the AI is actually going to start;"
    if text.count(start_anchor) != 1:
        raise SystemExit(f"Could not locate zero-interval start anchor ({text.count(start_anchor)})")
    start = text.index(start_anchor)
    end = text.find(end_anchor, start)
    if end < 0:
        raise SystemExit("Could not locate zero-interval end anchor")
    replacement = '''\t\tif (timeout == 0) {\n\t\t\t/* browser-zero-ai-stagger-v3 */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Main-thread WebAssembly must not create all missing Squirrel VMs in\n\t\t\t * one game tick. Zero minutes remains effectively immediate in game\n\t\t\t * terms: one requested competitor is created every eight ticks. */\n\t\t\tconst bool can_start = !_networking || Company::GetNumItems() < _settings_client.network.max_companies;\n\t\t\tif (num_ais < _settings_game.difficulty.max_no_competitors && can_start) {\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t\ttimeout = 8;\n\t\t\t} else {\n\t\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t\t}\n#else\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n#endif\n\t\t}\n'''
    text = text[:start] + replacement + text[end:]
company_cmd.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3. Phase-spread AI VM work without deleting full-performance budget code.
# ---------------------------------------------------------------------------
ai_core = ROOT / "src/ai/ai_core.cpp"
text = ai_core.read_text(encoding="utf-8")

# Desktop retains the stock global cadence gate. Browser cadence is instead
# applied per company below, using company id as a phase.
old_gate = '''\tif ((AI::frame_counter & run_mask) != 0) return;\n'''
new_gate = '''#ifndef __EMSCRIPTEN__\n\tif ((AI::frame_counter & run_mask) != 0) return;\n#endif\n'''
if 'browser-ai-phase-spread-v3' not in text:
    if text.count(old_gate) != 1:
        raise SystemExit(f"Could not locate global AI cadence gate ({text.count(old_gate)})")
    text = text.replace(old_gate, new_gate, 1)

    loop_anchor = '''\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n'''
    loop_replacement = '''\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n#ifdef __EMSCRIPTEN__\n\t\t\t/* browser-ai-phase-spread-v3: preserve each AI's configured cadence,\n\t\t\t * but distribute equal-speed VMs over browser frames by company id. */\n\t\t\tif (((AI::frame_counter + c->index.base()) & run_mask) != 0) {\n\t\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\t\tcontinue;\n\t\t\t}\n#endif\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n'''
    if text.count(loop_anchor) != 1:
        raise SystemExit(f"Could not locate AI company loop anchor ({text.count(loop_anchor)})")
    text = text.replace(loop_anchor, loop_replacement, 1)

# The full-performance aggregate budget MUST survive this patch.
if 'browser_ai_opcode_budget' not in text or 'AutoRestoreBackup<uint32_t> browser_ai_budget' not in text:
    raise SystemExit("Aggregate browser AI opcode budget is missing before/after v3 phase patch")

start_old = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n\n\tcur_company.Restore();\n'''
start_new = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI start v3: company={}, script='{}', version={}, alive={}", company.base(), info->GetName(), info->GetVersion(), c->ai_instance->IsAlive());\n#endif\n\n\tcur_company.Restore();\n'''
if 'Browser AI start v3:' not in text:
    if text.count(start_old) != 1:
        raise SystemExit(f"Could not locate AI::StartNew diagnostic anchor ({text.count(start_old)})")
    text = text.replace(start_old, start_new, 1)
ai_core.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# 4. Emit browser diagnostics even when crash UI is suppressed during switch.
# ---------------------------------------------------------------------------
ai_instance = ROOT / "src/ai/ai_instance.cpp"
text = ai_instance.read_text(encoding="utf-8")
died_old = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
died_new = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI died v3: company={}, switch_mode={}", _current_company.base(), static_cast<int>(_switch_mode));\n#endif\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
if 'Browser AI died v3:' not in text:
    if text.count(died_old) != 1:
        raise SystemExit(f"Could not locate AIInstance::Died anchor ({text.count(died_old)})")
    text = text.replace(died_old, died_new, 1)
ai_instance.write_text(text, encoding="utf-8")

checks = {
    script_gui: ['const int required_competitors = this->slot.base() + 1;'],
    company_cmd: ['browser-zero-ai-stagger-v3', 'timeout = 8;'],
    ai_core: [
        'browser-ai-phase-spread-v3',
        'AI::frame_counter + c->index.base()',
        'browser_ai_opcode_budget',
        'AutoRestoreBackup<uint32_t> browser_ai_budget',
        'Browser AI start v3:',
    ],
    ai_instance: ['Browser AI died v3:'],
}
for path, markers in checks.items():
    patched = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in patched:
            raise SystemExit(f"Missing browser AI v3 marker {marker!r} in {path}")

print("Browser AI v3 applied: zero interval staggered, VM phases spread, aggregate opcode budget preserved, diagnostics enabled.")
