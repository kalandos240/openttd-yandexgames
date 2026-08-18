#!/usr/bin/env python3
from pathlib import Path

path = Path('openttd/src/intro_gui.cpp')
text = path.read_text(encoding='utf-8')

include_anchor = '#include "newgrf_config.h"\n'
if include_anchor not in text:
    anchor = '#include "highscore.h"\n'
    if anchor not in text:
        raise SystemExit('Could not find intro include anchor')
    text = text.replace(anchor, anchor + include_anchor, 1)

old_handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\tif (!_network_available) {\n\t\t\t\t\tShowErrorMessage(GetEncodedString(STR_NETWORK_ERROR_NOTAVAILABLE), {}, WL_ERROR);\n\t\t\t\t} else {\n\t\t\t\t\tShowNetworkContentListWindow();\n\t\t\t\t}\n\t\t\t\tbreak;'''
new_handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\t/* Playgama edition: this slot is a direct local NewGRF settings button. */\n\t\t\t\tShowNewGRFSettings(true, true, false, _grfconfig_newgame);\n\t\t\t\tbreak;'''
if old_handler not in text:
    raise SystemExit('Could not find the retained Online Content click handler')
text = text.replace(old_handler, new_handler, 1)

options_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_OPTIONS), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SETTINGS, STR_INTRO_GAME_OPTIONS, STR_INTRO_TOOLTIP_GAME_OPTIONS), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
newgrf_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
if newgrf_widget not in text:
    if options_widget not in text:
        raise SystemExit('Could not find main-menu Game Options widget insertion point')
    text = text.replace(options_widget, options_widget + newgrf_widget, 1)

checks = (
    '#include "newgrf_config.h"',
    'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);',
    'SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP)',
)
for check in checks:
    if text.count(check) != 1:
        raise SystemExit(f'Unexpected NewGRF main-menu patch count for {check!r}: {text.count(check)}')

if 'ShowNetworkContentListWindow();' in text:
    raise SystemExit('Main-menu Online Content handler still reachable after Playgama patch')

path.write_text(text, encoding='utf-8')
print('Playgama main menu now exposes local NewGRF Settings directly.')
