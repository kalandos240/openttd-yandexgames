#!/usr/bin/env python3
"""Final browser AI runtime patch for the OpenTTD 15.3 source used by v14.

Applied after the profiler-driven full-performance source patch. It deliberately
patches only stable OpenTTD 15.3 anchors, so the aggregate opcode-budget block
already inserted before the company loop remains untouched.
"""
from pathlib import Path

ROOT = Path("openttd")
if not ROOT.is_dir():
    raise SystemExit("OpenTTD source tree is missing")

# ---------------------------------------------------------------------------
# 1. Selecting AI slot N for a new game activates at least N+1 competitors.
# ---------------------------------------------------------------------------
script_gui = ROOT / "src/script/script_gui.cpp"
s = script_gui.read_text(encoding="utf-8")
include_anchor = '#include "../settings_gui.h"\n'
include_line = '#include "../settings_func.h"\n'
if include_line not in s:
    if s.count(include_anchor) != 1:
        raise SystemExit(f"settings include anchor mismatch: {s.count(include_anchor)}")
    s = s.replace(include_anchor, include_anchor + include_line, 1)

slot_old = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\t\tif (_game_mode == GM_EDITOR) {\n'''
slot_new = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t/* browser-ai-slot-v4 */\n\t\tif (this->slot != OWNER_DEITY && _game_mode != GM_NORMAL) {\n\t\t\tconst int required_competitors = this->slot.base() + 1;\n\t\t\tif (GetGameSettings().difficulty.max_no_competitors < required_competitors) {\n\t\t\t\tIConsoleSetSetting("difficulty.max_no_competitors", required_competitors);\n\t\t\t}\n\t\t}\n#endif\n\t\tif (_game_mode == GM_EDITOR) {\n'''
if 'browser-ai-slot-v4' not in s:
    if 'const int required_competitors = this->slot.base() + 1;' in s:
        # Equivalent proven patch already present; mark it without changing semantics.
        pos = s.find('const int required_competitors = this->slot.base() + 1;')
        line = s.rfind('\n', 0, pos) + 1
        s = s[:line] + '\t\t/* browser-ai-slot-v4: equivalent slot activation already installed. */\n' + s[line:]
    else:
        if s.count(slot_old) != 1:
            raise SystemExit(f"AI slot block mismatch: {s.count(slot_old)}")
        s = s.replace(slot_old, slot_new, 1)
script_gui.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------------------
# 2. interval=0: create one missing AI every eight ticks in Emscripten.
#    Bound replacement by the stable randomisation comment after the block.
# ---------------------------------------------------------------------------
company_cmd = ROOT / "src/company_cmd.cpp"
c = company_cmd.read_text(encoding="utf-8")
if 'browser-zero-ai-stagger-v4' not in c:
    start_anchor = "\t\tif (timeout == 0) {\n"
    end_anchor = "\t\t/* Randomize a bit when the AI is actually going to start;"
    if c.count(start_anchor) != 1:
        raise SystemExit(f"zero interval start anchor mismatch: {c.count(start_anchor)}")
    start = c.index(start_anchor)
    end = c.find(end_anchor, start)
    if end < 0:
        raise SystemExit("zero interval end anchor missing")
    replacement = '''\t\tif (timeout == 0) {\n\t\t\t/* browser-zero-ai-stagger-v4 */\n\t\t\tuint8_t num_ais = 0;\n\t\t\tfor (const Company *cc : Company::Iterate()) {\n\t\t\t\tif (cc->is_ai) num_ais++;\n\t\t\t}\n#ifdef __EMSCRIPTEN__\n\t\t\t/* Keep zero-minute semantics without constructing every Squirrel VM\n\t\t\t * on the same browser-main-thread tick. */\n\t\t\tconst bool can_start = !_networking || Company::GetNumItems() < _settings_client.network.max_companies;\n\t\t\tif (num_ais < _settings_game.difficulty.max_no_competitors && can_start) {\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t\ttimeout = 8;\n\t\t\t} else {\n\t\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n\t\t\t}\n#else\n\t\t\tsize_t num_companies = Company::GetNumItems();\n\t\t\tfor (auto i = 0; i < _settings_game.difficulty.max_no_competitors; i++) {\n\t\t\t\tif (_networking && num_companies++ >= _settings_client.network.max_companies) break;\n\t\t\t\tif (num_ais++ >= _settings_game.difficulty.max_no_competitors) break;\n\t\t\t\tCommand<CMD_COMPANY_CTRL>::Post(CCA_NEW_AI, CompanyID::Invalid(), CRR_NONE, INVALID_CLIENT_ID);\n\t\t\t}\n\t\t\ttimeout = 10 * 60 * Ticks::TICKS_PER_SECOND;\n#endif\n\t\t}\n'''
    c = c[:start] + replacement + c[end:]
company_cmd.write_text(c, encoding="utf-8")

# ---------------------------------------------------------------------------
# 3. Preserve exact competitor-speed frequency but phase browser companies.
#    Full-performance has already inserted its aggregate budget before
#    Backup<CompanyID>; these replacements intentionally do not touch it.
# ---------------------------------------------------------------------------
ai_core = ROOT / "src/ai/ai_core.cpp"
a = ai_core.read_text(encoding="utf-8")
for required in ('browser_ai_opcode_budget', 'AutoRestoreBackup<uint32_t> browser_ai_budget', 'Module.__openttdAIStats'):
    if required not in a:
        raise SystemExit(f"required aggregate AI budget marker missing before v4: {required}")

stock_cadence = '''\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tif ((AI::frame_counter & ((1 << (4 - _settings_game.difficulty.competitor_speed)) - 1)) != 0) return;\n'''
phased_cadence = '''\tassert(_settings_game.difficulty.competitor_speed <= 4);\n\tconst uint run_mask = (1 << (4 - _settings_game.difficulty.competitor_speed)) - 1;\n#ifndef __EMSCRIPTEN__\n\tif ((AI::frame_counter & run_mask) != 0) return;\n#endif\n\t/* browser-ai-phase-spread-v4 */\n'''
if 'browser-ai-phase-spread-v4' not in a:
    if a.count(stock_cadence) == 1:
        a = a.replace(stock_cadence, phased_cadence, 1)
    elif 'AI::frame_counter + c->index.base()' in a and 'const uint run_mask =' in a:
        pos = a.find('const uint run_mask =')
        line = a.rfind('\n', 0, pos) + 1
        a = a[:line] + '\t/* browser-ai-phase-spread-v4: equivalent phase scheduler already installed. */\n' + a[line:]
    else:
        raise SystemExit(f"exact OpenTTD 15.3 cadence anchor mismatch: {a.count(stock_cadence)}")

loop_anchor = '''\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n'''
loop_phased = '''\tfor (const Company *c : Company::Iterate()) {\n\t\tif (c->is_ai) {\n#ifdef __EMSCRIPTEN__\n\t\t\tif (((AI::frame_counter + c->index.base()) & run_mask) != 0) {\n\t\t\t\tPerformanceMeasurer::SetInactive((PerformanceElement)(PFE_AI0 + c->index));\n\t\t\t\tcontinue;\n\t\t\t}\n#endif\n\t\t\tPerformanceMeasurer framerate((PerformanceElement)(PFE_AI0 + c->index));\n'''
if 'AI::frame_counter + c->index.base()' not in a:
    if a.count(loop_anchor) != 1:
        raise SystemExit(f"AI company loop anchor mismatch: {a.count(loop_anchor)}")
    a = a.replace(loop_anchor, loop_phased, 1)

# Upgrade/add start diagnostics without changing AI initialization order.
if 'Browser AI start v4:' not in a:
    if 'Browser AI start v3:' in a:
        a = a.replace('Browser AI start v3:', 'Browser AI start v4:', 1)
    elif 'Browser AI start:' in a:
        a = a.replace('Browser AI start:', 'Browser AI start v4:', 1)
    else:
        start_old = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n\n\tcur_company.Restore();\n'''
        start_new = '''\tc->ai_instance->LoadOnStack(config->GetToLoadData());\n\tconfig->SetToLoadData(nullptr);\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI start v4: company={}, script='{}', version={}, alive={}", company.base(), info->GetName(), info->GetVersion(), c->ai_instance->IsAlive());\n#endif\n\n\tcur_company.Restore();\n'''
        if a.count(start_old) != 1:
            raise SystemExit(f"AI start diagnostic anchor mismatch: {a.count(start_old)}")
        a = a.replace(start_old, start_new, 1)
ai_core.write_text(a, encoding="utf-8")

# ---------------------------------------------------------------------------
# 4. Console diagnostic for AI VM death even when switch-mode UI suppresses it.
# ---------------------------------------------------------------------------
ai_instance = ROOT / "src/ai/ai_instance.cpp"
i = ai_instance.read_text(encoding="utf-8")
if 'Browser AI died v4:' not in i:
    if 'Browser AI died v3:' in i:
        i = i.replace('Browser AI died v3:', 'Browser AI died v4:', 1)
    elif 'Browser AI died:' in i:
        i = i.replace('Browser AI died:', 'Browser AI died v4:', 1)
    else:
        died_old = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
        died_new = '''\t/* Intro is not supposed to use AI, but it may have 'dummy' AI which instant dies. */\n\tif (_game_mode == GM_MENU) return;\n#ifdef __EMSCRIPTEN__\n\tDebug(script, 0, "Browser AI died v4: company={}, switch_mode={}", _current_company.base(), static_cast<int>(_switch_mode));\n#endif\n\n\t/* Don't show errors while loading savegame. They will be shown at end of loading anyway. */\n\tif (_switch_mode != SM_NONE) return;\n'''
        if i.count(died_old) != 1:
            raise SystemExit(f"AI death diagnostic anchor mismatch: {i.count(died_old)}")
        i = i.replace(died_old, died_new, 1)
ai_instance.write_text(i, encoding="utf-8")

checks = {
    script_gui: ('browser-ai-slot-v4', 'required_competitors'),
    company_cmd: ('browser-zero-ai-stagger-v4', 'timeout = 8;'),
    ai_core: (
        'browser-ai-phase-spread-v4',
        'const uint run_mask =',
        'AI::frame_counter + c->index.base()',
        'browser_ai_opcode_budget',
        'AutoRestoreBackup<uint32_t> browser_ai_budget',
        'Module.__openttdAIStats',
        'Browser AI start v4:',
    ),
    ai_instance: ('Browser AI died v4:',),
}
for path, markers in checks.items():
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            raise SystemExit(f"missing v4 marker {marker!r} in {path}")

print("Browser AI v4 applied: exact 15.3 cadence phased, interval-zero starts staggered, aggregate opcode budget preserved.")
