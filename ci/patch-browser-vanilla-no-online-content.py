#!/usr/bin/env python3
from pathlib import Path

p = Path('openttd/src/intro_gui.cpp')
text = p.read_text(encoding='utf-8')

handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\tif (!_network_available) {\n\t\t\t\t\tShowErrorMessage(GetEncodedString(STR_NETWORK_ERROR_NOTAVAILABLE), {}, WL_ERROR);\n\t\t\t\t} else {\n\t\t\t\t\tShowNetworkContentListWindow();\n\t\t\t\t}\n\t\t\t\tbreak;\n'''
widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_INTRO_ONLINE_CONTENT, STR_INTRO_TOOLTIP_ONLINE_CONTENT), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''

handler_count = text.count(handler)
widget_count = text.count(widget)
if handler_count > 1:
    raise SystemExit(f'Unexpected duplicate Online Content handlers: {handler_count}')
if widget_count > 1:
    raise SystemExit(f'Unexpected duplicate Online Content widgets: {widget_count}')
if handler_count == 1:
    text = text.replace(handler, '', 1)
if widget_count == 1:
    text = text.replace(widget, '', 1)

# The stable browser pipeline already hides part of the upstream online UI in
# some patch stacks. Treat an already-removed button/handler as the desired
# state, while still failing if any reachable browser content entry remains.
for forbidden in (
    'ShowNetworkContentListWindow();',
    'WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_INTRO_ONLINE_CONTENT',
    'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);',
    'GetBundledGRFRussianDescription',
):
    if forbidden in text:
        raise SystemExit(f'Vanilla release still contains browser add-on UI marker: {forbidden!r}')

p.write_text(text, encoding='utf-8')
print(f'Vanilla release patch applied: removed handler={handler_count}, widget={widget_count}; no bundled NewGRF UI remains.')
