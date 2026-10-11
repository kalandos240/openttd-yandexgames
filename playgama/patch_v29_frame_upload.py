#!/usr/bin/env python3
"""Apply a byte-exact frame-upload throttle to the Playgama OpenTTD JS presenter.

Firefox performance profile (2026-10-11): ~2.22s CPU under
WebGLRenderingContext.texSubImage2D -> memcpy within ~8.6s of main-thread
samples. On high-refresh screens, uploading every WASM render tick is wasteful.

Cap visual uploads to ~30 FPS while preserving ALL simulation/input ticks.
Resize, canvas/context recreation and first paint bypass the throttle.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ANCHOR = (
    b'47364289:(A,B,g)=>{var __otW=A,__otH=B,__otPixels=g;'
    b'Module.SDL2||(Module.SDL2={});var __otSDL=Module.SDL2,'
    b'__otCanvas=Module.canvas;'
)
FRAME_GUARD = (
    b'var __otFrameNow=performance.now();'
    b'if(__otSDL.__openttdPresenterCanvas===__otCanvas&&'
    b'__otSDL.__openttdLastPresentedAt!==void 0&&'
    b'__otFrameNow>=__otSDL.__openttdLastPresentedAt&&'
    b'__otFrameNow-__otSDL.__openttdLastPresentedAt<33.333&&'
    b'__otSDL.__openttdLastPresentedW===__otW&&'
    b'__otSDL.__openttdLastPresentedH===__otH&&'
    b'__otCanvas.width===__otW&&__otCanvas.height===__otH)return;'
    b'__otSDL.__openttdLastPresentedAt=__otFrameNow;'
    b'__otSDL.__openttdLastPresentedW=__otW;'
    b'__otSDL.__openttdLastPresentedH=__otH;'
)
AFTER_ANCHOR = b'if(__otSDL.__openttdPresenterCanvas!==__otCanvas)'


def expected_bytes(original: bytes) -> bytes:
    if original.count(ANCHOR + AFTER_ANCHOR) != 1:
        raise SystemExit('Unknown OpenTTD V29 presenter version or unexpected rendering edits')
    if FRAME_GUARD in original:
        raise SystemExit('Presenter already throttled')
    return original.replace(ANCHOR + AFTER_ANCHOR, ANCHOR + FRAME_GUARD + AFTER_ANCHOR, 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('dist', type=Path)
    p.add_argument('--verify-original', type=Path, required=True)
    args = p.parse_args()
    src = args.verify_original/'openttd-runtime.js'
    dst = args.dist/'openttd-runtime.js'
    pristine = src.read_bytes()
    from patch_v29_startup_timeout import expected_bytes as expected_startup
    expected = expected_bytes(expected_startup(pristine))
    actual = dst.read_bytes()
    if actual == expected_startup(pristine):
        dst.write_bytes(expected)
        actual = dst.read_bytes()
    if actual != expected:
        raise SystemExit('Unexpected runtime changes besides two startup timeouts and one render-upload throttle')
    print('OpenTTD V29 JS frame presenter cap verified: max ~30 FPS uploads; native simulation unchanged')


if __name__ == '__main__':
    main()
