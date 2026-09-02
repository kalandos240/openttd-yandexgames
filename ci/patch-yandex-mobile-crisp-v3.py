#!/usr/bin/env python3
"""Fix mobile framebuffer/CSS desync introduced by DPR backing-store scaling.

Keeps the native cursorless runtime from the previous mobile build, but returns
OpenTTD to a 1:1 logical framebuffer that fills the complete visual viewport.
Pixel-art rendering is kept crisp with nearest-neighbour CSS sampling instead
of multiplying Module.setCanvasSize() by devicePixelRatio.
"""
from __future__ import annotations

import argparse
from pathlib import Path

VIEWPORT_V3 = r'''/* Mobile V3: one OpenTTD logical framebuffer == complete visual viewport.
 * Do not multiply Module.setCanvasSize() by DPR: SDL/OpenTTD owns the canvas
 * dimensions and doing so desynchronises its software framebuffer from CSS.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV3Installed) return;
  window.__openttdAdaptiveViewportV3Installed = true;

  const MAX_DESKTOP_ASPECT_RATIO = 2;

  const viewportRect = () => {
    const vv = window.visualViewport;
    return {
      width: Math.max(64, Math.round(vv?.width || innerWidth || document.documentElement.clientWidth || 1280)),
      height: Math.max(64, Math.round(vv?.height || innerHeight || document.documentElement.clientHeight || 720)),
      left: Math.max(0, Math.round(vv?.offsetLeft || 0)),
      top: Math.max(0, Math.round(vv?.offsetTop || 0)),
    };
  };

  const layout = () => {
    const viewport = viewportRect();
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;
    let width = viewport.width;
    let height = viewport.height;
    let left = viewport.left;
    let top = viewport.top;

    if (!touchUi) {
      if (width / height > MAX_DESKTOP_ASPECT_RATIO) {
        const next = Math.round(height * MAX_DESKTOP_ASPECT_RATIO);
        left += Math.round((width - next) / 2);
        width = next;
      }
      if (height / width > MAX_DESKTOP_ASPECT_RATIO) {
        const next = Math.round(width * MAX_DESKTOP_ASPECT_RATIO);
        top += Math.round((height - next) / 2);
        height = next;
      }
    }

    return { viewport, touchUi, width, height, left, top };
  };

  window.openttdComputeAdaptiveLayout = layout;
  let raf = 0;
  let lastKey = '';

  const apply = () => {
    raf = 0;
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const canvas = Module.canvas || document.getElementById('canvas');
      if (!canvas) return false;
      const box = layout();
      const key = [box.width, box.height, box.left, box.top, box.touchUi].join(':');

      if (canvas.width !== box.width || canvas.height !== box.height) {
        Module.setCanvasSize(box.width, box.height);
      }

      if (key !== lastKey) {
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
        canvas.style.setProperty('image-rendering', box.touchUi ? 'pixelated' : 'auto', 'important');
        lastKey = key;
      }

      if (window.openttdMobileProfile && box.touchUi) {
        window.openttdMobileProfile.renderScale = 1;
        window.openttdMobileProfile.backingResolution = { width: box.width, height: box.height };
        window.openttdMobileProfile.cssResolution = { width: box.width, height: box.height };
      }
      return true;
    } catch (error) {
      console.warn('[OpenTTD] Mobile V3 viewport resize failed', error);
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
    old = """    const shortSide = Math.min(window.visualViewport?.width || innerWidth || 0, window.visualViewport?.height || innerHeight || 0);\n    const cssGuiScale = profile.touchUi ? (shortSide < 360 ? 150 : shortSide < 520 ? 175 : 200) : 100;\n    const renderScale = profile.touchUi ? Math.max(1, Math.min(3, Number(window.devicePixelRatio || profile.dpr || 1))) : 1;\n    profile.cssGuiScale = cssGuiScale;\n    profile.renderScale = renderScale;\n    profile.guiScale = profile.touchUi ? Math.max(100, Math.min(500, Math.round((cssGuiScale * renderScale) / 25) * 25)) : 100;\n    window.openttdRecommendedGuiScale = profile.guiScale;\n"""
    new = """    const shortSide = Math.min(window.visualViewport?.width || innerWidth || 0, window.visualViewport?.height || innerHeight || 0);\n    profile.cssGuiScale = profile.touchUi ? (shortSide < 360 ? 150 : shortSide < 520 ? 175 : 200) : 100;\n    profile.renderScale = 1;\n    profile.guiScale = profile.cssGuiScale;\n    window.openttdRecommendedGuiScale = profile.guiScale;\n"""
    text = replace_once(text, old, new, 'remove DPR GUI compensation')
    text = text.replace('image-rendering: auto !important;', 'image-rendering: pixelated !important;', 1)
    path.write_text(text, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()
    mobile = dist / 'openttd-yandex-mobile.js'
    viewport = dist / 'openttd-full-viewport.js'
    for p in (mobile, viewport):
        if not p.is_file():
            raise SystemExit(f'Missing package file: {p.name}')

    patch_mobile_js(mobile)
    viewport.write_text(VIEWPORT_V3, encoding='utf-8')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Mobile V3 crisp framebuffer fix applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
