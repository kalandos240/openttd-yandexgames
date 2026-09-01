#!/usr/bin/env python3
from pathlib import Path

p = Path('openttd/src/intro_gui.cpp')
text = p.read_text(encoding='utf-8')

handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\tif (!_network_available) {\n\t\t\t\t\tShowErrorMessage(GetEncodedString(STR_NETWORK_ERROR_NOTAVAILABLE), {}, WL_ERROR);\n\t\t\t\t} else {\n\t\t\t\t\tShowNetworkContentListWindow();\n\t\t\t\t}\n\t\t\t\tbreak;\n'''
widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_INTRO_ONLINE_CONTENT, STR_INTRO_TOOLTIP_ONLINE_CONTENT), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''

if text.count(handler) != 1:
    raise SystemExit(f'Expected exactly one upstream Online Content handler, found {text.count(handler)}')
if text.count(widget) != 1:
    raise SystemExit(f'Expected exactly one upstream Online Content main-menu widget, found {text.count(widget)}')

text = text.replace(handler, '', 1)
text = text.replace(widget, '', 1)

# Release policy: the browser package contains no bundled NewGRFs and exposes no
# Online Content entry point. OpenTTD's native NewGRF subsystem remains intact
# for save compatibility and possible future use, but no content is shipped or
# downloaded by this release build.
for forbidden in (
    'ShowNetworkContentListWindow();',
    'WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_INTRO_ONLINE_CONTENT',
    'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);',
    'GetBundledGRFRussianDescription',
):
    if forbidden in text:
        raise SystemExit(f'Vanilla release still contains browser add-on UI marker: {forbidden!r}')

p.write_text(text, encoding='utf-8')
print('Vanilla release patch applied: Online Content main-menu entry removed; no bundled NewGRF UI added.')
