#!/usr/bin/env python3
"""Native source patch for the touch-only Yandex mobile build.

The desktop publication build is untouched. In the dedicated mobile runtime:
- OpenTTD never renders its software mouse cursor;
- JavaScript can enqueue real SDL mouse/wheel events for touch gestures.

The SDL bridge avoids relying on synthetic DOM MouseEvent objects, which are
not reliable enough for click-and-drag viewport scrolling in Emscripten/SDL2.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Hide the software cursor in the dedicated mobile runtime.
# ---------------------------------------------------------------------------
gfx = Path('openttd/src/gfx.cpp')
if not gfx.is_file():
    raise SystemExit(f'Missing OpenTTD source: {gfx}')

text = gfx.read_text(encoding='utf-8')
cursor_marker = '/* Yandex mobile: touch-only build, never render the software mouse cursor. */'
if cursor_marker not in text:
    old = """void DrawMouseCursor()\n{\n\t/* Don't draw mouse cursor if it is handled by the video driver. */\n"""
    new = """void DrawMouseCursor()\n{\n#if defined(__EMSCRIPTEN__)\n\t/* Yandex mobile: touch-only build, never render the software mouse cursor. */\n\treturn;\n#endif\n\n\t/* Don't draw mouse cursor if it is handled by the video driver. */\n"""
    if text.count(old) != 1:
        raise SystemExit(f'Could not locate DrawMouseCursor anchor: count={text.count(old)}')
    text = text.replace(old, new, 1)
    gfx.write_text(text, encoding='utf-8')

# ---------------------------------------------------------------------------
# 2. Add a small Emscripten -> SDL event queue bridge.
# ---------------------------------------------------------------------------
sdl = Path('openttd/src/video/sdl2_v.cpp')
if not sdl.is_file():
    raise SystemExit(f'Missing OpenTTD source: {sdl}')

text = sdl.read_text(encoding='utf-8')
bridge_marker = 'Yandex mobile native touch bridge: enqueue real SDL input events.'
if bridge_marker not in text:
    anchor = """bool VideoDriver_SDL_Base::PollEvent()\n{\n"""
    if text.count(anchor) != 1:
        raise SystemExit(f'Could not locate SDL PollEvent anchor: count={text.count(anchor)}')

    bridge = r'''#ifdef __EMSCRIPTEN__
/* Yandex mobile native touch bridge: enqueue real SDL input events.
 *
 * type:
 *   0 = mouse motion
 *   1 = left button down
 *   2 = left button up
 *   3 = right button down
 *   4 = right button up
 *   5 = wheel up / zoom in
 *   6 = wheel down / zoom out
 *
 * The events are intentionally inserted into SDL's own queue, so OpenTTD sees
 * exactly the same event stream as it would receive from a physical mouse.
 */
extern "C" EMSCRIPTEN_KEEPALIVE void em_openttd_touch_mouse_event(int type, int x, int y)
{
	SDL_Event ev{};

	switch (type) {
		case 0:
			ev.type = SDL_MOUSEMOTION;
			ev.motion.type = SDL_MOUSEMOTION;
			ev.motion.x = x;
			ev.motion.y = y;
			break;

		case 1:
		case 2:
		case 3:
		case 4:
			ev.type = (type == 1 || type == 3) ? SDL_MOUSEBUTTONDOWN : SDL_MOUSEBUTTONUP;
			ev.button.type = ev.type;
			ev.button.button = (type == 1 || type == 2) ? SDL_BUTTON_LEFT : SDL_BUTTON_RIGHT;
			ev.button.state = (type == 1 || type == 3) ? SDL_PRESSED : SDL_RELEASED;
			ev.button.clicks = 1;
			ev.button.x = x;
			ev.button.y = y;
			break;

		case 5:
		case 6:
			ev.type = SDL_MOUSEWHEEL;
			ev.wheel.type = SDL_MOUSEWHEEL;
			ev.wheel.y = type == 5 ? 1 : -1;
#if SDL_VERSION_ATLEAST(2, 18, 0)
			ev.wheel.preciseY = type == 5 ? 1.0f : -1.0f;
#endif
			break;

		default:
			return;
	}

	SDL_PushEvent(&ev);
}
#endif

'''
    text = text.replace(anchor, bridge + anchor, 1)
    sdl.write_text(text, encoding='utf-8')

print('Yandex mobile native cursor + SDL touch bridge patch applied')
