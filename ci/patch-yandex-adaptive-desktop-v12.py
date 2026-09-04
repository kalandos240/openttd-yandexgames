#!/usr/bin/env python3
"""V12 desktop cursor polish for the adaptive Yandex package.

V11 keeps OpenTTD's software cursor on desktop, which is visually too large for
high-resolution/fullscreen browser play. V12 suppresses the OpenTTD software
cursor in the already-exported Emscripten cursor mode and uses the browser/OS
pointer at its native desktop size. Touch/mobile remains cursor-free.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one occurrence, found {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    mobile = dist / 'openttd-yandex-mobile.js'
    viewport = dist / 'openttd-full-viewport.js'
    for p in (mobile, viewport):
        if not p.is_file():
            raise SystemExit(f'Missing {p.name}')

    s = mobile.read_text(encoding='utf-8')
    s = replace_once(
        s,
        "try { nativeTouchSetter(profile.touchUi ? 1 : 0); } catch (error) {",
        "try { nativeTouchSetter(1); } catch (error) {",
        'publish cursor suppression',
    )
    s = replace_once(
        s,
        "      fn(profile.touchUi ? 1 : 0);\n      clearInterval(nativeModeSync);",
        "      /* V12: OpenTTD software cursor is suppressed in both modes. Touch has\n"
        "         no cursor; desktop uses the browser/OS cursor instead. */\n"
        "      fn(1);\n"
        "      window.__openttdDesktopSystemCursorV12 = true;\n"
        "      clearInterval(nativeModeSync);",
        'startup cursor suppression',
    )
    mobile.write_text(s, encoding='utf-8')

    v = viewport.read_text(encoding='utf-8')
    v = replace_once(
        v,
        "canvas.style.setProperty('cursor', 'none', 'important');",
        "canvas.style.setProperty('cursor', box.touchUi ? 'none' : 'default', 'important');",
        'desktop browser cursor',
    )
    if 'Adaptive V12 desktop + touch viewport.' not in v:
        v = v.replace(
            '/* Adaptive V9 desktop + touch viewport.',
            '/* Adaptive V12 desktop + touch viewport.\n'
            ' * Desktop uses the browser/OS pointer at native size; OpenTTD software cursor is suppressed.\n'
            ' *\n * Based on Adaptive V9 viewport.',
            1,
        )
    viewport.write_text(v, encoding='utf-8')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Adaptive V12 desktop system cursor applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
