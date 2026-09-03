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
context_marker = 'Yandex mobile touch context: distinguish UI, pan and placement.'
if context_marker in s:
    print('Yandex mobile build-context patch already applied')
    raise SystemExit(0)

pan_marker = '/* Yandex mobile direct touch pan: bypass desktop mouse-scroll state. */'
start = s.find(pan_marker)
if start < 0:
    raise SystemExit('Could not locate direct-pan marker')

# Both direct-pan and touch-context exports belong to the same Emscripten block.
# Insert immediately before that block's first #endif after the unique pan marker;
# this is robust to whitespace/comment changes around the following function.
end = s.find('\n#endif', start)
if end < 0:
    raise SystemExit('Could not locate Emscripten #endif after direct-pan marker')

addition = r'''

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
'''

s = s[:end] + addition + s[end:]
p.write_text(s, encoding='utf-8')
print('Yandex mobile native build-context export applied')
