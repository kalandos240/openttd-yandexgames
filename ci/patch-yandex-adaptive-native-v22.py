#!/usr/bin/env python3
"""V22: disable OpenTTD tooltips only while the adaptive touch UI is active.

Runs after patch-yandex-adaptive-native-v9.py. Desktop keeps original OpenTTD
hover/right-click tooltip behaviour. Touch/mobile mode suppresses tooltips at
the central GuiShowTooltips() entry point, so button descriptions and any other
native tooltip cannot appear after taps.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Give the adaptive touch-mode flag external linkage so GUI code can read it.
# ---------------------------------------------------------------------------
gfx = Path('openttd/src/gfx.cpp')
if not gfx.is_file():
    raise SystemExit(f'Missing OpenTTD source: {gfx}')

text = gfx.read_text(encoding='utf-8')
old_flag = 'static bool _yandex_touch_ui_active = false;\n'
new_flag = 'bool _yandex_touch_ui_active = false;\n'
# Check the exact old declaration first. The new declaration text is also a
# substring of the old "static bool ..." line, so a plain substring test for
# new_flag before this replacement would incorrectly treat the old line as done.
if old_flag in text:
    if text.count(old_flag) != 1:
        raise SystemExit(f'Could not uniquely locate adaptive touch flag: count={text.count(old_flag)}')
    text = text.replace(old_flag, new_flag, 1)
    gfx.write_text(text, encoding='utf-8')
elif new_flag not in text:
    raise SystemExit('Could not locate adaptive touch flag declaration')

# ---------------------------------------------------------------------------
# 2. Suppress every native tooltip in touch UI, at the central creation point.
# ---------------------------------------------------------------------------
misc = Path('openttd/src/misc_gui.cpp')
if not misc.is_file():
    raise SystemExit(f'Missing OpenTTD source: {misc}')

text = misc.read_text(encoding='utf-8')
marker = 'Yandex adaptive V22: disable native tooltips in touch UI.'
if marker not in text:
    safeguards = '#include "safeguards.h"\n'
    extern_block = '''#ifdef __EMSCRIPTEN__\n/* Yandex adaptive V22: disable native tooltips in touch UI. */\nextern bool _yandex_touch_ui_active;\n#endif\n\n#include "safeguards.h"\n'''
    if text.count(safeguards) != 1:
        raise SystemExit(f'Could not locate misc_gui safeguards include: count={text.count(safeguards)}')
    text = text.replace(safeguards, extern_block, 1)

    old = '''void GuiShowTooltips(Window *parent, EncodedString &&text, TooltipCloseCondition close_tooltip)\n{\n\tCloseWindowById(WC_TOOLTIPS, 0);\n\n\tif (text.empty() || !_cursor.in_window) return;\n'''
    new = '''void GuiShowTooltips(Window *parent, EncodedString &&text, TooltipCloseCondition close_tooltip)\n{\n\tCloseWindowById(WC_TOOLTIPS, 0);\n\n#ifdef __EMSCRIPTEN__\n\t/* Touch taps leave a synthetic mouse position over the pressed widget.\n\t * Without this guard OpenTTD interprets that as hover and immediately\n\t * opens the widget description. Desktop remains byte-for-byte equivalent\n\t * after this branch because the runtime flag is false there. */\n\tif (_yandex_touch_ui_active) return;\n#endif\n\n\tif (text.empty() || !_cursor.in_window) return;\n'''
    if text.count(old) != 1:
        raise SystemExit(f'Could not locate GuiShowTooltips prologue: count={text.count(old)}')
    text = text.replace(old, new, 1)
    misc.write_text(text, encoding='utf-8')

# Validation of source-side invariants.
gfx_text = gfx.read_text(encoding='utf-8')
misc_text = misc.read_text(encoding='utf-8')
for needle in (
    'bool _yandex_touch_ui_active = false;',
    'em_openttd_set_touch_ui',
):
    if needle not in gfx_text:
        raise SystemExit(f'Missing gfx invariant after V22 patch: {needle}')
if 'static bool _yandex_touch_ui_active = false;' in gfx_text:
    raise SystemExit('Touch UI flag still has internal linkage')
for needle in (
    'Yandex adaptive V22: disable native tooltips in touch UI.',
    'extern bool _yandex_touch_ui_active;',
    'void GuiShowTooltips(Window *parent, EncodedString &&text, TooltipCloseCondition close_tooltip)',
    'if (_yandex_touch_ui_active) return;',
    'if (text.empty() || !_cursor.in_window) return;',
):
    if needle not in misc_text:
        raise SystemExit(f'Missing misc_gui invariant after V22 patch: {needle}')

print('Yandex adaptive V22 mobile tooltip suppression applied')
