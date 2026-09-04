#!/usr/bin/env python3
"""V11 desktop polish for the adaptive Yandex package.

Pin desktop OpenTTD GUI scale to 100% so fullscreen does not enlarge the UI.
Sticky banners remain owned by the Yandex page/SDK and are never suppressed.
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

    fixes = dist / 'openttd-yandex-fixes.js'
    bridge = dist / 'yandex-bridge.js'
    if not fixes.is_file() or not bridge.is_file():
        raise SystemExit('Missing adaptive V10 package files')

    f = fixes.read_text(encoding='utf-8')
    old = """    if (window.openttdMobileProfile?.touchUi) {
      setGlobal('gui_scale', Math.max(100, Math.min(500, guiScale)));
      setGui('osk_activation', 'immediately');
      setGui('scroll_mode', '3');
      setGui('scrollwheel_scrolling', '0');
      setGui('hover_delay_ms', '0');
      setGui('toolbar_pos', '1');
      setGui('statusbar_pos', '1');
    }
"""
    new = """    /* V11: touch keeps adaptive scaling; desktop is pinned to OpenTTD's
       native 100% minimum so fullscreen does not enlarge the toolbar. */
    if (window.openttdMobileProfile?.touchUi) {
      setGlobal('gui_scale', Math.max(100, Math.min(500, guiScale)));
      setGui('osk_activation', 'immediately');
      setGui('scroll_mode', '3');
      setGui('scrollwheel_scrolling', '0');
      setGui('hover_delay_ms', '0');
      setGui('toolbar_pos', '1');
      setGui('statusbar_pos', '1');
    } else {
      setGlobal('gui_scale', 100);
    }
"""
    f = replace_once(f, old, new, 'desktop gui scale block')
    fixes.write_text(f, encoding='utf-8')

    b = bridge.read_text(encoding='utf-8')
    if 'hideBannerAdv' in b or '__openttdStickySuppressionV11' in b:
        raise SystemExit('Unexpected sticky-banner suppression in base package')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Adaptive V11 desktop/sticky fixes applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
