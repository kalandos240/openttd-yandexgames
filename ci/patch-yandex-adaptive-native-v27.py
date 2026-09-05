#!/usr/bin/env python3
"""V27: export a real SDL/OpenTTD window-resize bridge for Yandex host recovery.

JavaScript-only canvas resizing can change the HTML canvas without reallocating
OpenTTD's SDL software framebuffer. After DevTools closes this can either leave
a black strip (if the child viewport stays stale) or stretch a smaller native
framebuffer (if CSS/canvas is enlarged synthetically).

This patch exposes the existing VideoDriver::ChangeResolution() path to JS. That
path calls SDL_SetWindowSize(), reallocates the backing store and executes
GameSizeChanged(), keeping native framebuffer, canvas and GUI geometry in sync.
"""
from pathlib import Path

p = Path('openttd/src/video/sdl2_v.cpp')
if not p.is_file():
    raise SystemExit(f'Missing OpenTTD source: {p}')

text = p.read_text(encoding='utf-8')
marker = 'Yandex adaptive V27: native SDL resize bridge.'
if marker not in text:
    anchor = '#include "../safeguards.h"\n'
    block = r'''#ifdef __EMSCRIPTEN__
/* Yandex adaptive V27: native SDL resize bridge.
 * Use the normal OpenTTD video-driver resize path so SDL window size, software
 * framebuffer and _screen geometry change together. */
extern "C" EMSCRIPTEN_KEEPALIVE int em_openttd_force_window_resize(int width, int height)
{
	if (width < 64 || height < 64 || width > 16384 || height > 16384) return 0;
	VideoDriver *driver = VideoDriver::GetInstance();
	if (driver == nullptr) return 0;
	return driver->ChangeResolution(width, height) ? 1 : 0;
}

extern "C" EMSCRIPTEN_KEEPALIVE int em_openttd_screen_width()
{
	return _screen.width;
}

extern "C" EMSCRIPTEN_KEEPALIVE int em_openttd_screen_height()
{
	return _screen.height;
}
#endif

#include "../safeguards.h"
'''
    if text.count(anchor) != 1:
        raise SystemExit(f'Could not locate safeguards include in sdl2_v.cpp: count={text.count(anchor)}')
    text = text.replace(anchor, block, 1)

for needle in (
    marker,
    'em_openttd_force_window_resize',
    'driver->ChangeResolution(width, height)',
    'em_openttd_screen_width',
    'em_openttd_screen_height',
):
    if needle not in text:
        raise SystemExit(f'Missing V27 native resize invariant: {needle}')

p.write_text(text, encoding='utf-8')
print('Yandex adaptive V27 native SDL resize bridge applied')
