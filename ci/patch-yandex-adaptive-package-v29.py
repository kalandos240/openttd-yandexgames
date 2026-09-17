#!/usr/bin/env python3
"""V29: preserve the desktop windowed baseline across Yandex fullscreen.

Yandex enters fullscreen from the parent shell, so the game iframe does not
always observe ``document.fullscreenElement``.  V27 could consequently learn
the fullscreen viewport (zero outer/inner delta) as a new healthy windowed
baseline.  After leaving fullscreen that stale baseline made the native SDL
framebuffer remain fullscreen-sized and cropped OpenTTD's bottom status bar.

V29 rejects fullscreen-like geometry and only refreshes an existing baseline
when the browser-frame deltas remain compatible with the previous windowed
sample.  Touch/mobile sizing and the V28 cursor fix are left unchanged.
"""
from __future__ import annotations

import argparse
from pathlib import Path


OLD_BLOCK = r"""  const considerHealthyBaseline = raw => {
    if (!raw || !document.hasFocus()) return;
    const outer = hostOuter();
    if (outer.width < raw.width || outer.height < raw.height || outer.width < 320 || outer.height < 240) return;
    const candidate = {
      deltaWidth: Math.max(0, outer.width - raw.width),
      deltaHeight: Math.max(0, outer.height - raw.height),
      rawWidth: raw.width,
      rawHeight: raw.height,
      outerWidth: outer.width,
      outerHeight: outer.height,
    };
    if (!host.baseline) {
      host.baseline = candidate;
      return;
    }
    const previousArea = host.baseline.rawWidth * host.baseline.rawHeight;
    const candidateArea = candidate.rawWidth * candidate.rawHeight;
    if (candidateArea > previousArea * 1.03 || candidate.deltaHeight + 24 < host.baseline.deltaHeight) {
      host.baseline = candidate;
    }
  };
"""

NEW_BLOCK = r"""  /* V29: Yandex can fullscreen the parent element without exposing a
     fullscreenElement inside this iframe. Geometry is therefore the primary
     signal; the document flags cover direct/native fullscreen as well. */
  const isFullscreenLike = (raw, outer) => {
    let documentFullscreen = false;
    try {
      documentFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
    } catch (_) {}
    const fillsHost = Math.abs(outer.width - raw.width) <= 16 &&
      Math.abs(outer.height - raw.height) <= 16;
    return documentFullscreen || fillsHost;
  };

  const considerHealthyBaseline = raw => {
    if (!raw || !document.hasFocus()) return;
    const outer = hostOuter();
    if (outer.width < raw.width || outer.height < raw.height || outer.width < 320 || outer.height < 240) return;
    if (isFullscreenLike(raw, outer)) return;
    const candidate = {
      deltaWidth: Math.max(0, outer.width - raw.width),
      deltaHeight: Math.max(0, outer.height - raw.height),
      rawWidth: raw.width,
      rawHeight: raw.height,
      outerWidth: outer.width,
      outerHeight: outer.height,
    };
    if (!host.baseline) {
      host.baseline = candidate;
      return;
    }

    /* A real browser-window resize preserves approximately the same browser
       chrome/host-shell deltas. Fullscreen removes those deltas abruptly; do
       not let that transient geometry poison the windowed recovery baseline. */
    const compatibleFrame =
      Math.abs(candidate.deltaWidth - host.baseline.deltaWidth) <= 48 &&
      Math.abs(candidate.deltaHeight - host.baseline.deltaHeight) <= 48;
    const previousArea = host.baseline.rawWidth * host.baseline.rawHeight;
    const candidateArea = candidate.rawWidth * candidate.rawHeight;
    if (compatibleFrame && candidateArea > previousArea * 1.03) {
      host.baseline = candidate;
    }
  };
"""


def patch_package(root: Path) -> None:
    viewport = root / 'openttd-full-viewport.js'
    if not viewport.is_file():
        raise SystemExit(f'missing {viewport}')

    text = viewport.read_text(encoding='utf-8')
    if NEW_BLOCK in text and OLD_BLOCK not in text:
        pass
    else:
        count = text.count(OLD_BLOCK)
        if count != 1:
            raise SystemExit(f'expected exactly one V27 baseline block, found {count}')
        text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
        viewport.write_text(text, encoding='utf-8')

    final = viewport.read_text(encoding='utf-8')
    required = (
        'V29: Yandex can fullscreen the parent element',
        'const isFullscreenLike = (raw, outer) => {',
        'if (isFullscreenLike(raw, outer)) return;',
        'const compatibleFrame =',
        "canvas.style.setProperty('cursor', 'none', 'important');",
    )
    for marker in required:
        if marker not in final:
            raise SystemExit(f'missing V29 invariant: {marker}')
    if 'candidate.deltaHeight + 24 < host.baseline.deltaHeight' in final:
        raise SystemExit('fullscreen-poisoning V27 baseline update is still present')

    print('Adaptive V29 fullscreen-exit windowed-baseline fix applied')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    patch_package(args.package.resolve())


if __name__ == '__main__':
    main()
