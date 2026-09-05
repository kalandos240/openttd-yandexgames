#!/usr/bin/env python3
"""V28: hide the host OS cursor while preserving OpenTTD's in-game cursor.

V27 already hides the cursor in the base stylesheet, but its adaptive viewport
runtime later overwrites the canvas inline style with cursor:auto on desktop.
Because the inline declaration is also !important, it wins and the browser/OS
pointer is rendered on top of OpenTTD's own software cursor.

V28 makes the adaptive runtime keep cursor:none on the game canvas for both
desktop and touch. OpenTTD continues to draw its own desktop cursor inside the
framebuffer, while touch/mobile remains cursorless as before.
"""
from __future__ import annotations

import argparse
from pathlib import Path

OLD_CURSOR = "canvas.style.setProperty('cursor', box.touchUi ? 'none' : 'auto', 'important');"
NEW_CURSOR = (
    "canvas.style.setProperty('cursor', 'none', 'important'); "
    "/* V28: OpenTTD renders its own cursor; suppress the host OS cursor. */"
)


def patch_package(root: Path) -> None:
    viewport = root / 'openttd-full-viewport.js'
    index = root / 'index.html'

    if not viewport.is_file():
        raise SystemExit(f'missing {viewport}')
    if not index.is_file():
        raise SystemExit(f'missing {index}')

    text = viewport.read_text(encoding='utf-8')
    if NEW_CURSOR in text and OLD_CURSOR not in text:
        pass
    else:
        count = text.count(OLD_CURSOR)
        if count != 1:
            raise SystemExit(f'expected exactly one V27 desktop cursor override, found {count}')
        text = text.replace(OLD_CURSOR, NEW_CURSOR, 1)
        viewport.write_text(text, encoding='utf-8')

    final = viewport.read_text(encoding='utf-8')
    if OLD_CURSOR in final:
        raise SystemExit('desktop cursor:auto override is still present')
    if NEW_CURSOR not in final:
        raise SystemExit('V28 cursor suppression marker missing')

    html = index.read_text(encoding='utf-8', errors='ignore')
    if 'canvas.emscripten' not in html:
        raise SystemExit('game canvas stylesheet rule missing')
    if 'cursor:none!important' not in html.replace(' ', ''):
        raise SystemExit('startup canvas cursor:none CSS missing')

    print('Adaptive V28 desktop system cursor suppression applied')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    patch_package(args.package.resolve())


if __name__ == '__main__':
    main()
