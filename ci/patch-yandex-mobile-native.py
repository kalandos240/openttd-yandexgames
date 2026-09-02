#!/usr/bin/env python3
"""Native source patch for the touch-only Yandex mobile build.

The desktop publication build is untouched.  In the dedicated mobile runtime
OpenTTD must not render its software mouse cursor: all interaction is produced
by the touch bridge.
"""
from pathlib import Path

p = Path('openttd/src/gfx.cpp')
if not p.is_file():
    raise SystemExit(f'Missing OpenTTD source: {p}')

text = p.read_text(encoding='utf-8')
marker = '/* Yandex mobile: touch-only build, never render the software mouse cursor. */'
if marker in text:
    print('Mobile native cursor patch already applied')
    raise SystemExit(0)

old = """void DrawMouseCursor()\n{\n\t/* Don't draw mouse cursor if it is handled by the video driver. */\n"""
new = """void DrawMouseCursor()\n{\n#if defined(__EMSCRIPTEN__)\n\t/* Yandex mobile: touch-only build, never render the software mouse cursor. */\n\treturn;\n#endif\n\n\t/* Don't draw mouse cursor if it is handled by the video driver. */\n"""
if text.count(old) != 1:
    raise SystemExit(f'Could not locate DrawMouseCursor anchor: count={text.count(old)}')

p.write_text(text.replace(old, new, 1), encoding='utf-8')
print('Yandex mobile native cursor patch applied')
