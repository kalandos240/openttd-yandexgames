#!/usr/bin/env python3
"""Expose OpenTTD's SDL dirty rectangle to the generated browser presenter.

OpenTTD already tracks the minimal dirty rectangle in VideoDriver_SDL_Default::Paint,
but SDL2's Emscripten framebuffer backend ignores the rects and sends the entire
surface to JavaScript.  This browser-only source patch publishes the rectangle just
before SDL_UpdateWindowSurfaceRects(), allowing the later WebGL presenter patch to
upload only changed pixels while keeping SDL's stock call and fallback intact.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "# V14_DIRTY_RECT_SOURCE_PATCH\n"


def patch_build_script(text: str) -> str:
    if MARKER.strip() in text:
        return text

    anchor = "git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd\n"
    if text.count(anchor) != 1:
        raise SystemExit(f"Expected one OpenTTD clone anchor, got {text.count(anchor)}")

    source_patch = r'''# V14_DIRTY_RECT_SOURCE_PATCH
python3 - <<'PY_DIRTY_RECT_SOURCE'
from pathlib import Path

path = Path('openttd/src/video/sdl2_default_v.cpp')
text = path.read_text(encoding='utf-8')
anchor = '''\tSDL_UpdateWindowSurfaceRects(this->sdl_window, &r, 1);\n'''
replacement = '''#ifdef __EMSCRIPTEN__
\t/* SDL2's Emscripten software framebuffer ignores the rect list and normally
\t * copies the complete surface into JavaScript. Publish OpenTTD's already
\t * calculated dirty rectangle so our browser presenter can perform a partial
\t * texture upload. A zero-sized rectangle deliberately means "unknown/full". */
\tEM_ASM({
\t\tModule.__openttdDirtyRect = [$0, $1, $2, $3];
\t}, r.x, r.y, r.w, r.h);
#endif
\tSDL_UpdateWindowSurfaceRects(this->sdl_window, &r, 1);\n'''
if 'Module.__openttdDirtyRect' not in text:
    if text.count(anchor) != 1:
        raise SystemExit(f'Expected one SDL framebuffer update anchor, got {text.count(anchor)}')
    text = text.replace(anchor, replacement, 1)
path.write_text(text, encoding='utf-8')
PY_DIRTY_RECT_SOURCE
'''
    return text.replace(anchor, anchor + source_patch, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('build_script', type=Path)
    args = parser.parse_args()

    path = args.build_script
    text = path.read_text(encoding='utf-8')
    text = patch_build_script(text)
    if 'Module.__openttdDirtyRect' not in text:
        raise SystemExit('Dirty-rect source invariant missing after patch')
    path.write_text(text, encoding='utf-8')
    print('Browser dirty-rect bridge enabled for SDL2 framebuffer presentation.')


if __name__ == '__main__':
    main()
