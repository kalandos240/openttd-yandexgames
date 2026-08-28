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

old = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\t\tif (_game_mode == GM_EDITOR) {\n'''
new = '''\t\tif (this->selected == -1) {\n\t\t\tGetConfig(this->slot)->Change(std::nullopt);\n\t\t} else {\n\t\t\tScriptInfoList::const_iterator it = this->info_list->cbegin();\n\t\t\tstd::advance(it, this->selected);\n\t\t\tGetConfig(this->slot)->Change(it->second->GetName(), it->second->GetVersion());\n\t\t}\n\n#ifdef __EMSCRIPTEN__\n\t\t/* Choosing an AI for a new game must also make that slot active. Upstream\n\t\t * OpenTTD deliberately keeps script selection and competitor count\n\t\t * separate, which is easy to miss in the browser UI. Derive the minimum\n\t\t * count from the slot the player explicitly accepted; never touch the\n\t\t * interval and never re-apply this after the user changes the count. */\n\t\tif (this->slot != OWNER_DEITY && _game_mode != GM_NORMAL) {\n\t\t\tconst int required_competitors = this->slot.base();\n\t\t\tif (GetGameSettings().difficulty.max_no_competitors < required_competitors) {\n\t\t\t\tIConsoleSetSetting("difficulty.max_no_competitors", required_competitors);\n\t\t\t}\n\t\t}\n#endif\n\n\t\tif (_game_mode == GM_EDITOR) {\n'''

if text.count(old) != 1:
    raise SystemExit(f'Could not locate ScriptListWindow::ChangeScript block ({text.count(old)})')
text = text.replace(old, new, 1)

for marker in (
    'const int required_competitors = this->slot.base();',
    'IConsoleSetSetting("difficulty.max_no_competitors", required_competitors);',
):
    if marker not in text:
        raise SystemExit(f'AI player-selection patch missing marker: {marker}')

path.write_text(text, encoding='utf-8')
print('Player-selected AI slot now activates the matching competitor count; interval remains untouched.')
