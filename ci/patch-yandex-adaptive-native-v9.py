#!/usr/bin/env python3
"""V9: make the mobile native runtime safe for desktop + touch in one package.

Runs after patch-yandex-mobile-native.py. The earlier mobile patch suppresses
OpenTTD's software cursor unconditionally. V9 replaces that compile-time mobile
behaviour with a runtime flag controlled by the browser device profile.
"""
from pathlib import Path

p = Path('openttd/src/gfx.cpp')
if not p.is_file():
    raise SystemExit(f'Missing OpenTTD source: {p}')
text = p.read_text(encoding='utf-8')

old = '''#if defined(__EMSCRIPTEN__)\n\t/* Yandex mobile: touch-only build, never render the software mouse cursor. */\n\treturn;\n#endif\n'''
new = '''#if defined(__EMSCRIPTEN__)\n\t/* Yandex adaptive V9: touch devices hide OpenTTD's software cursor,\n\t * desktop keeps the original cursor. */\n\tif (_yandex_touch_ui_active) return;\n#endif\n'''
if new not in text:
    if text.count(old) != 1:
        raise SystemExit(f'Could not locate unconditional mobile cursor block: count={text.count(old)}')
    text = text.replace(old, new, 1)

marker = 'Yandex adaptive V9 native cursor mode.'
if marker not in text:
    safeguards = '#include "safeguards.h"\n'
    insert = '''#ifdef __EMSCRIPTEN__\n#include <emscripten/emscripten.h>\n\n/* Yandex adaptive V9 native cursor mode. False by default so desktop never\n * loses the original OpenTTD software cursor while device detection starts. */\nstatic bool _yandex_touch_ui_active = false;\nextern "C" EMSCRIPTEN_KEEPALIVE void em_openttd_set_touch_ui(int active)\n{\n\t_yandex_touch_ui_active = active != 0;\n}\n#endif\n\n#include "safeguards.h"\n'''
    if text.count(safeguards) != 1:
        raise SystemExit(f'Could not locate safeguards include: count={text.count(safeguards)}')
    text = text.replace(safeguards, insert, 1)

p.write_text(text, encoding='utf-8')
print('Yandex adaptive V9 native cursor mode applied')
