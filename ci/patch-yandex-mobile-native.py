#!/usr/bin/env python3
"""Native source patch for the touch-only Yandex mobile build.

The desktop publication build is untouched. In the dedicated mobile runtime:
- OpenTTD never renders its software mouse cursor;
- JavaScript can enqueue tagged SDL mouse/wheel events for tap/right-click/zoom;
- one-finger panning calls the viewport's native OnScroll() path directly;
- a touch gesture lock suppresses browser/SDL compatibility mouse events while
  a finger gesture is being classified, preventing build tools firing on pan.
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
# 2. Add an Emscripten -> SDL event queue bridge plus gesture lock.
# ---------------------------------------------------------------------------
sdl = Path('openttd/src/video/sdl2_v.cpp')
if not sdl.is_file():
    raise SystemExit(f'Missing OpenTTD source: {sdl}')

text = sdl.read_text(encoding='utf-8')
bridge_marker = 'Yandex mobile native touch bridge: enqueue tagged SDL input events.'
if bridge_marker not in text:
    anchor = """bool VideoDriver_SDL_Base::PollEvent()\n{\n"""
    if text.count(anchor) != 1:
        raise SystemExit(f'Could not locate SDL PollEvent anchor: count={text.count(anchor)}')

    bridge = r'''#ifdef __EMSCRIPTEN__
/* Yandex mobile native touch bridge: enqueue tagged SDL input events.
 *
 * Continuous one-finger panning bypasses the mouse state machine. Discrete
 * tap/right-click/zoom events are tagged so PollEvent can distinguish them
 * from browser compatibility mouse events while a touch gesture is active.
 */
static constexpr uint32_t YANDEX_TOUCH_EVENT_ID = 0x59414E44u; // "YAND"
static bool _yandex_touch_gesture_active = false;

extern "C" EMSCRIPTEN_KEEPALIVE void em_openttd_touch_gesture_state(int active)
{
	_yandex_touch_gesture_active = active != 0;
	if (_yandex_touch_gesture_active) {
		_left_button_down = false;
		_left_button_clicked = false;
		_right_button_down = false;
		_right_button_clicked = false;
		_cursor.delta = {0, 0};
	}
}

extern "C" EMSCRIPTEN_KEEPALIVE void em_openttd_touch_mouse_event(int type, int x, int y)
{
	SDL_Event ev{};

	switch (type) {
		case 0:
			ev.type = SDL_MOUSEMOTION;
			ev.motion.type = SDL_MOUSEMOTION;
			ev.motion.which = YANDEX_TOUCH_EVENT_ID;
			ev.motion.x = x;
			ev.motion.y = y;
			break;

		case 1:
		case 2:
		case 3:
		case 4:
			ev.type = (type == 1 || type == 3) ? SDL_MOUSEBUTTONDOWN : SDL_MOUSEBUTTONUP;
			ev.button.type = ev.type;
			ev.button.which = YANDEX_TOUCH_EVENT_ID;
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
			ev.wheel.which = YANDEX_TOUCH_EVENT_ID;
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
    replacement = bridge + anchor + r'''#ifdef __EMSCRIPTEN__
	/* During a real touch gesture, browsers/Emscripten may also create
	 * compatibility mouse events. Ignore those completely. Only events tagged
	 * by em_openttd_touch_mouse_event() are allowed through the lock. */
	SDL_Event ev;
	if (!SDL_PollEvent(&ev)) return false;
	if (_yandex_touch_gesture_active) {
		bool blocked = false;
		switch (ev.type) {
			case SDL_MOUSEMOTION: blocked = ev.motion.which != YANDEX_TOUCH_EVENT_ID; break;
			case SDL_MOUSEBUTTONDOWN:
			case SDL_MOUSEBUTTONUP: blocked = ev.button.which != YANDEX_TOUCH_EVENT_ID; break;
			case SDL_MOUSEWHEEL: blocked = ev.wheel.which != YANDEX_TOUCH_EVENT_ID; break;
			default: break;
		}
		if (blocked) return true;
	}
'''
    # PollEvent already declares/polls SDL_Event immediately after the anchor.
    # Replace the first two lines too so there is only one declaration/poll.
    old_body = anchor + "\tSDL_Event ev;\n\n\tif (!SDL_PollEvent(&ev)) return false;\n"
    if text.count(old_body) != 1:
        raise SystemExit(f'Could not locate PollEvent prologue: count={text.count(old_body)}')
    text = text.replace(old_body, replacement, 1)
    sdl.write_text(text, encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Export a direct viewport-pan path from the native window system.
# ---------------------------------------------------------------------------
window = Path('openttd/src/window.cpp')
if not window.is_file():
    raise SystemExit(f'Missing OpenTTD source: {window}')

text = window.read_text(encoding='utf-8')
pan_marker = 'Yandex mobile direct touch pan: bypass desktop mouse-scroll state.'
if pan_marker not in text:
    safeguards = '#include "safeguards.h"\n'
    include_block = '#ifdef __EMSCRIPTEN__\n#include <emscripten/emscripten.h>\n#endif\n\n#include "safeguards.h"\n'
    if text.count(safeguards) != 1:
        raise SystemExit(f'Could not locate safeguards include: count={text.count(safeguards)}')
    text = text.replace(safeguards, include_block, 1)

    anchor = """\t_cursor.wheel_moved = false;\n\treturn ES_HANDLED;\n}\n\n/**\n * Check if a window can be made relative top-most window"""
    if text.count(anchor) != 1:
        raise SystemExit(f'Could not locate HandleViewportScroll tail: count={text.count(anchor)}')

    direct_pan = r'''
#ifdef __EMSCRIPTEN__
/* Yandex mobile direct touch pan: bypass desktop mouse-scroll state. */
extern "C" EMSCRIPTEN_KEEPALIVE int em_openttd_touch_pan(int x, int y, int dx, int dy)
{
	Window *w = FindWindowFromPt(x, y);
	if (w == nullptr || w->flags.Test(WindowFlag::DisableVpScroll)) return 0;

	Viewport *vp = IsPtInWindowViewport(w, x, y);
	if (vp == nullptr || _game_mode == GM_MENU || HasModalProgress()) return 0;

	if (w == GetMainWindow() && w->viewport->follow_vehicle != VehicleID::Invalid()) {
		const Vehicle *veh = Vehicle::Get(w->viewport->follow_vehicle);
		ScrollMainWindowTo(veh->x_pos, veh->y_pos, veh->z_pos, true);
	}

	if (dx != 0 || dy != 0) {
		Point delta{-dx, -dy};
		w->OnScroll(delta);
	}
	return 1;
}
#endif

'''
    text = text.replace(
        anchor,
        "\t_cursor.wheel_moved = false;\n\treturn ES_HANDLED;\n}\n" + direct_pan + "\n/**\n * Check if a window can be made relative top-most window",
        1,
    )
    window.write_text(text, encoding='utf-8')

print('Yandex mobile native cursor + tagged SDL input + gesture lock + direct viewport pan applied')
