#!/usr/bin/env python3
"""Expose native touch context for mobile gesture arbitration.

Runs after patch-yandex-mobile-native.py. The browser touch layer can ask
OpenTTD whether a point is UI, a normal viewport, or a viewport with an active
placement tool. This lets one-finger map panning coexist with original
click-and-drag construction semantics.
"""
from pathlib import Path

p = Path('openttd/src/window.cpp')
if not p.is_file():
    raise SystemExit(f'Missing OpenTTD source: {p}')

s = p.read_text(encoding='utf-8')
marker = 'Yandex mobile touch context: distinguish UI, pan and placement.'
if marker in s:
    print('Yandex mobile build-context patch already applied')
    raise SystemExit(0)

anchor = '''\treturn 1;\n}\n#endif\n\n/**\n * Check if a window can be made relative top-most window'''
if s.count(anchor) != 1:
    raise SystemExit(f'Could not locate direct-pan tail: count={s.count(anchor)}')

addition = r'''\treturn 1;
}

/* Yandex mobile touch context: distinguish UI, pan and placement.
 * Return values:
 *   0 = regular OpenTTD UI / no usable viewport
 *   1 = viewport with no active placement tool (one-finger pan)
 *   2 = viewport with an active placement tool (original LMB click/drag)
 */
extern "C" EMSCRIPTEN_KEEPALIVE int em_openttd_touch_context(int x, int y)
{
	Window *w = FindWindowFromPt(x, y);
	if (w == nullptr) return 0;

	Viewport *vp = IsPtInWindowViewport(w, x, y);
	if (vp == nullptr || _game_mode == GM_MENU || HasModalProgress()) return 0;

	return _thd.place_mode != HT_NONE ? 2 : 1;
}
#endif

/**
 * Check if a window can be made relative top-most window'''

s = s.replace(anchor, addition, 1)
p.write_text(s, encoding='utf-8')
print('Yandex mobile native build-context export applied')
