#!/usr/bin/env python3
"""Expose OpenTTD's native dirty rectangle to the generated browser presenter.

SDL2's Emscripten window-surface path eventually presents the whole software
framebuffer and drops the SDL_UpdateWindowSurfaceRects rectangle. OpenTTD has
already computed that rectangle, so retain it in Module.SDL2 immediately before
the SDL call. The post-link WebGL2 presenter consumes these four integers and
can upload only the changed rows without changing simulation or drawing logic.
"""
from __future__ import annotations

from pathlib import Path


MARKER = "__openttdDirtyValid"


def main() -> None:
    path = Path("openttd/src/video/sdl2_default_v.cpp")
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print("OpenTTD dirty-rect browser handoff already present")
        return

    old = "\tSDL_UpdateWindowSurfaceRects(this->sdl_window, &r, 1);\n"
    if text.count(old) != 1:
        raise SystemExit(f"Expected one SDL_UpdateWindowSurfaceRects call, found {text.count(old)}")

    new = r'''#ifdef __EMSCRIPTEN__
	/* Emscripten's SDL2 software-surface presenter receives the full framebuffer
	 * dimensions/pointer but not this update rectangle. Preserve the rectangle
	 * in the existing SDL2 JS state so the WebGL2 post-link presenter can use
	 * UNPACK_ROW_LENGTH/SKIP_* and upload only the changed pixels. Four scalar
	 * properties avoid allocating a JS array every paint. */
	EM_ASM({
		var s = Module.SDL2 || (Module.SDL2 = {});
		s.__openttdDirtyX = $0 | 0;
		s.__openttdDirtyY = $1 | 0;
		s.__openttdDirtyW = $2 | 0;
		s.__openttdDirtyH = $3 | 0;
		s.__openttdDirtyValid = 1;
	}, r.x, r.y, r.w, r.h);
#endif
	SDL_UpdateWindowSurfaceRects(this->sdl_window, &r, 1);
'''
    text = text.replace(old, new, 1)
    if text.count(MARKER) != 1 or "EM_ASM({" not in text:
        raise SystemExit("Dirty-rect browser handoff patch failed")
    path.write_text(text, encoding="utf-8")
    print("OpenTTD native dirty rectangle is now handed to the browser presenter")


if __name__ == "__main__":
    main()
