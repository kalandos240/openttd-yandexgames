#!/usr/bin/env python3
"""Second-pass mobile presentation fixes for the Yandex package.

Fixes three user-visible issues:
- no browser or native-style pointer presentation on touch devices;
- HiDPI backing resolution based on devicePixelRatio instead of CSS pixels;
- full visual-viewport coverage on mobile/tablet without safe-area letterboxing.
"""
from __future__ import annotations

import argparse
from pathlib import Path

VIEWPORT_V2 = r'''/* HiDPI adaptive OpenTTD canvas sizing for Yandex desktop + mobile.
 * Desktop retains the moderation-safe 2:1 maximum active-field ratio.
 * Touch devices fill the complete visual viewport. The canvas backing store is
 * rendered at devicePixelRatio (capped at 3x) while CSS keeps the physical
 * viewport size, eliminating the low-resolution blur of the first mobile pass.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV2Installed) return;
  window.__openttdAdaptiveViewportV2Installed = true;

  const MAX_DESKTOP_ASPECT_RATIO = 2;
  const MAX_TOUCH_DPR = 3;

  const viewportRect = () => {
    const vv = window.visualViewport;
    const width = Math.max(64, Math.round(vv?.width || innerWidth || document.documentElement.clientWidth || 1280));
    const height = Math.max(64, Math.round(vv?.height || innerHeight || document.documentElement.clientHeight || 720));
    const offsetLeft = Math.max(0, Math.round(vv?.offsetLeft || 0));
    const offsetTop = Math.max(0, Math.round(vv?.offsetTop || 0));
    return { width, height, offsetLeft, offsetTop };
  };

  const layout = () => {
    const viewport = viewportRect();
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;

    /* Mobile/tablet deliberately fills the whole visual viewport. Safe-area
       values remain available through the device profile, but are NOT used to
       shrink the game surface; this prevents visible background/letterboxing. */
    let cssWidth = viewport.width;
    let cssHeight = viewport.height;
    let left = viewport.offsetLeft;
    let top = viewport.offsetTop;

    if (!touchUi) {
      if (cssWidth / cssHeight > MAX_DESKTOP_ASPECT_RATIO) {
        const next = Math.round(cssHeight * MAX_DESKTOP_ASPECT_RATIO);
        left += Math.round((cssWidth - next) / 2);
        cssWidth = next;
      }
      if (cssHeight / cssWidth > MAX_DESKTOP_ASPECT_RATIO) {
        const next = Math.round(cssWidth * MAX_DESKTOP_ASPECT_RATIO);
        top += Math.round((cssHeight - next) / 2);
        cssHeight = next;
      }
    }

    const rawDpr = Number(window.devicePixelRatio || profile.dpr || 1);
    const renderScale = touchUi ? Math.max(1, Math.min(MAX_TOUCH_DPR, rawDpr || 1)) : 1;
    const backingWidth = Math.max(64, Math.round(cssWidth * renderScale));
    const backingHeight = Math.max(64, Math.round(cssHeight * renderScale));

    return {
      viewport, touchUi, renderScale,
      width: cssWidth, height: cssHeight, left, top,
      backingWidth, backingHeight,
    };
  };

  window.openttdComputeAdaptiveLayout = layout;
  let raf = 0;
  let last = '';

  const apply = () => {
    raf = 0;
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const canvas = Module.canvas || document.getElementById('canvas');
      if (!canvas) return false;
      const box = layout();
      const key = [box.width, box.height, box.left, box.top, box.backingWidth, box.backingHeight, box.touchUi].join(':');

      if (canvas.width !== box.backingWidth || canvas.height !== box.backingHeight) {
        Module.setCanvasSize(box.backingWidth, box.backingHeight);
      }

      if (key !== last) {
        canvas.style.setProperty('position', 'fixed', 'important');
        canvas.style.setProperty('inset', 'auto', 'important');
        canvas.style.setProperty('width', `${box.width}px`, 'important');
        canvas.style.setProperty('height', `${box.height}px`, 'important');
        canvas.style.setProperty('left', `${box.left}px`, 'important');
        canvas.style.setProperty('top', `${box.top}px`, 'important');
        canvas.style.setProperty('right', 'auto', 'important');
        canvas.style.setProperty('bottom', 'auto', 'important');
        canvas.style.setProperty('max-width', 'none', 'important');
        canvas.style.setProperty('max-height', 'none', 'important');
        canvas.style.setProperty('touch-action', box.touchUi ? 'none' : 'auto', 'important');
        canvas.style.setProperty('cursor', box.touchUi ? 'none' : 'auto', 'important');
        last = key;
      }

      const profile = window.openttdMobileProfile;
      if (profile && box.touchUi) {
        profile.renderScale = box.renderScale;
        profile.backingResolution = { width: box.backingWidth, height: box.backingHeight };
        profile.cssResolution = { width: box.width, height: box.height };
      }
      return true;
    } catch (error) {
      console.warn('[OpenTTD] HiDPI adaptive viewport resize failed', error);
      return false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => { if (!apply()) setTimeout(apply, 50); });
  };

  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('orientationchange', schedule, { passive: true });
  window.addEventListener('openttd-mobile-profile', schedule, { passive: true });
  window.visualViewport?.addEventListener('resize', schedule, { passive: true });
  window.visualViewport?.addEventListener('scroll', schedule, { passive: true });
  document.addEventListener('fullscreenchange', schedule, { passive: true });

  let attempts = 0;
  const startup = setInterval(() => {
    attempts += 1;
    if (apply() || attempts >= 160) clearInterval(startup);
  }, 100);
})();
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one occurrence, found {count}')
    return text.replace(old, new, 1)


def patch_mobile_js(path: Path) -> None:
    text = path.read_text(encoding='utf-8')

    old_scale = """    const shortSide = Math.min(window.visualViewport?.width || innerWidth || 0, window.visualViewport?.height || innerHeight || 0);\n    profile.guiScale = profile.touchUi ? (shortSide < 360 ? 150 : shortSide < 520 ? 175 : 200) : 100;\n    window.openttdRecommendedGuiScale = profile.guiScale;\n"""
    new_scale = """    const shortSide = Math.min(window.visualViewport?.width || innerWidth || 0, window.visualViewport?.height || innerHeight || 0);\n    const cssGuiScale = profile.touchUi ? (shortSide < 360 ? 150 : shortSide < 520 ? 175 : 200) : 100;\n    const renderScale = profile.touchUi ? Math.max(1, Math.min(3, Number(window.devicePixelRatio || profile.dpr || 1))) : 1;\n    profile.cssGuiScale = cssGuiScale;\n    profile.renderScale = renderScale;\n    profile.guiScale = profile.touchUi ? Math.max(100, Math.min(500, Math.round((cssGuiScale * renderScale) / 25) * 25)) : 100;\n    window.openttdRecommendedGuiScale = profile.guiScale;\n"""
    text = replace_once(text, old_scale, new_scale, 'HiDPI GUI scale')

    old_css = """      html, body { margin: 0 !important; padding: 0 !important; width: 100%; height: 100%; overflow: hidden !important; overscroll-behavior: none !important; }\n      html.openttd-touch-ui, html.openttd-touch-ui body { touch-action: none !important; -webkit-text-size-adjust: 100%; }\n      html.openttd-touch-ui canvas.emscripten { touch-action: none !important; -webkit-user-select: none !important; user-select: none !important; -webkit-touch-callout: none !important; }\n"""
    new_css = """      html, body { margin: 0 !important; padding: 0 !important; width: 100%; height: 100%; overflow: hidden !important; overscroll-behavior: none !important; background: #000 !important; }\n      html.openttd-touch-ui, html.openttd-touch-ui body { touch-action: none !important; -webkit-text-size-adjust: 100%; cursor: none !important; }\n      html.openttd-touch-ui *, html.openttd-touch-ui canvas.emscripten { cursor: none !important; }\n      html.openttd-touch-ui canvas.emscripten { touch-action: none !important; -webkit-user-select: none !important; user-select: none !important; -webkit-touch-callout: none !important; image-rendering: auto !important; }\n"""
    text = replace_once(text, old_css, new_css, 'touch cursor CSS')
    path.write_text(text, encoding='utf-8')


def patch_gui_scale_limit(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    old = "setGlobal('gui_scale', Math.max(100, Math.min(250, guiScale)));"
    new = "setGlobal('gui_scale', Math.max(100, Math.min(500, guiScale)));"
    text = replace_once(text, old, new, 'GUI scale upper bound')
    path.write_text(text, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    mobile = dist / 'openttd-yandex-mobile.js'
    viewport = dist / 'openttd-full-viewport.js'
    fixes = dist / 'openttd-yandex-fixes.js'
    for p in (mobile, viewport, fixes):
        if not p.is_file():
            raise SystemExit(f'Missing package file: {p.name}')

    patch_mobile_js(mobile)
    patch_gui_scale_limit(fixes)
    viewport.write_text(VIEWPORT_V2, encoding='utf-8')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Mobile HiDPI/fullscreen visual fixes applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
