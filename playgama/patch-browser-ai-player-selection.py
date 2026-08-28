#!/usr/bin/env python3
"""Make an AI explicitly chosen by the player an active competitor slot.

OpenTTD keeps the AI script assigned to a slot separate from
`difficulty.max_no_competitors`. That makes it possible to select SimpleAI,
set the interval to 0, press Create, and still get no AI because the competitor
count stayed at 0. In the browser UI an explicit AI choice should activate that
slot, while all later count/interval changes remain fully player-controlled.
"""
from pathlib import Path

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
print('Player-selected AI slot now activates the matching competitor count; interval remains untouched.')
