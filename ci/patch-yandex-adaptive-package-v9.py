#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

VIEWPORT_V9 = r'''/* Adaptive V9 desktop + touch viewport.
 * One package serves both platforms. Desktop keeps the original OpenTTD cursor
 * and desktop config; touch/mobile gets touch-only input and cursor suppression.
 * A lightweight watchdog prevents late SDL/config resolution changes from
 * exposing the low-resolution loading background below/around the game.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV9Installed) return;
  window.__openttdAdaptiveViewportV9Installed = true;

  const MAX_DESKTOP_ASPECT_RATIO = 2;

  const dimensions = touchUi => {
    const vv = window.visualViewport;
    if (touchUi) {
      return {
        width: Math.max(64, Math.round(vv?.width || innerWidth || document.documentElement.clientWidth || 1280)),
        height: Math.max(64, Math.round(vv?.height || innerHeight || document.documentElement.clientHeight || 720)),
        left: Math.max(0, Math.round(vv?.offsetLeft || 0)),
        top: Math.max(0, Math.round(vv?.offsetTop || 0)),
      };
    }

    return {
      width: Math.max(64, Math.round(Math.max(innerWidth || 0, document.documentElement.clientWidth || 0, document.body?.clientWidth || 0))),
      height: Math.max(64, Math.round(Math.max(innerHeight || 0, document.documentElement.clientHeight || 0, document.body?.clientHeight || 0))),
      left: 0,
      top: 0,
    };
  };

  const layout = () => {
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;
    const viewport = dimensions(touchUi);
    let { width, height, left, top } = viewport;

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
  let applying = false;
  let lastCssKey = '';

  const apply = () => {
    raf = 0;
    if (applying) return false;
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const canvas = Module.canvas || document.getElementById('canvas');
      if (!canvas) return false;
      const box = layout();
      applying = true;

      if (canvas.width !== box.width || canvas.height !== box.height) Module.setCanvasSize(box.width, box.height);

      const cssKey = [box.width, box.height, box.left, box.top, box.touchUi].join(':');
      if (cssKey !== lastCssKey) {
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
        canvas.style.setProperty('cursor', 'none', 'important');
        canvas.style.setProperty('image-rendering', box.touchUi ? 'pixelated' : 'auto', 'important');
        lastCssKey = cssKey;
      }

      const bg = document.querySelector('div.background');
      if (bg) bg.style.setProperty('display', 'none', 'important');

      if (window.openttdMobileProfile) {
        window.openttdMobileProfile.renderScale = 1;
        window.openttdMobileProfile.backingResolution = { width: box.width, height: box.height };
        window.openttdMobileProfile.cssResolution = { width: box.width, height: box.height };
      }
      return true;
    } catch (error) {
      console.warn('[OpenTTD] Adaptive V9 viewport resize failed', error);
      return false;
    } finally {
      applying = false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => { if (!apply()) setTimeout(apply, 50); });
  };

  for (const type of ['resize', 'orientationchange', 'openttd-mobile-profile']) window.addEventListener(type, schedule, { passive: true });
  window.visualViewport?.addEventListener('resize', schedule, { passive: true });
  window.visualViewport?.addEventListener('scroll', schedule, { passive: true });
  document.addEventListener('fullscreenchange', schedule, { passive: true });

  setInterval(apply, 250);
  schedule();
})();
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    mobile = dist / 'openttd-yandex-mobile.js'
    viewport = dist / 'openttd-full-viewport.js'
    bridge = dist / 'yandex-bridge.js'
    runtime = dist / 'openttd-runtime.js'
    for p in (mobile, viewport, bridge, runtime):
        if not p.is_file():
            raise SystemExit(f'Missing {p.name}')

    rt = runtime.read_text(encoding='utf-8', errors='ignore')
    if '_em_openttd_set_touch_ui' not in rt:
        raise SystemExit('V9 native cursor setter missing')

    s = mobile.read_text(encoding='utf-8')
    old = """  const CONFIG_NAME = 'openttd-mobile.cfg';\n  const CONFIG_PATH = '/home/web_user/.openttd/' + CONFIG_NAME;\n  window.openttdConfigFilename = CONFIG_NAME;\n\n  /* Keep mobile presentation settings separate from the desktop profile while\n     sharing the same save directory. OpenTTD supports an explicit -c config. */\n  window.Module = window.Module || {};\n  window.Module.arguments = Array.isArray(window.Module.arguments) ? window.Module.arguments : [];\n  if (!window.Module.arguments.includes('-c')) window.Module.arguments.push('-c', CONFIG_PATH);\n\n"""
    new = """  /* Decide the boot config synchronously. Yandex deviceInfo arrives later, so\n     use capability hints only for this early config split. */\n  const bootTouchHint = (() => {\n    const uaMobile = navigator.userAgentData && typeof navigator.userAgentData.mobile === 'boolean' ? navigator.userAgentData.mobile : false;\n    const touch = Number(navigator.maxTouchPoints || 0) > 0;\n    let coarse = false, noHover = false;\n    try { coarse = matchMedia('(pointer: coarse)').matches || matchMedia('(any-pointer: coarse)').matches; } catch (_) {}\n    try { noHover = matchMedia('(hover: none)').matches; } catch (_) {}\n    return !!(uaMobile || (touch && coarse && noHover));\n  })();\n  window.openttdBootTouchUi = bootTouchHint;\n  window.Module = window.Module || {};\n  window.Module.arguments = Array.isArray(window.Module.arguments) ? window.Module.arguments : [];\n  if (bootTouchHint) {\n    const CONFIG_NAME = 'openttd-mobile.cfg';\n    const CONFIG_PATH = '/home/web_user/.openttd/' + CONFIG_NAME;\n    window.openttdConfigFilename = CONFIG_NAME;\n    if (!window.Module.arguments.includes('-c')) window.Module.arguments.push('-c', CONFIG_PATH);\n  } else {\n    window.openttdConfigFilename = 'openttd.cfg';\n  }\n\n"""
    if s.count(old) != 1:
        raise SystemExit(f'config block count={s.count(old)}')
    s = s.replace(old, new, 1)

    anchor = """    document.documentElement.classList.toggle('openttd-tablet', !!profile.isTablet);\n    window.dispatchEvent(new CustomEvent('openttd-mobile-profile', { detail: { ...profile } }));\n"""
    repl = """    document.documentElement.classList.toggle('openttd-tablet', !!profile.isTablet);\n    const nativeTouchSetter = window.Module?._em_openttd_set_touch_ui;\n    if (typeof nativeTouchSetter === 'function') nativeTouchSetter(profile.touchUi ? 1 : 0);\n    window.dispatchEvent(new CustomEvent('openttd-mobile-profile', { detail: { ...profile } }));\n"""
    if s.count(anchor) != 1:
        raise SystemExit('publishProfile anchor mismatch')
    s = s.replace(anchor, repl, 1)

    raw_old = """      const blockRawTouch = e => {\n        if (e.cancelable) e.preventDefault();\n        e.stopImmediatePropagation();\n      };\n"""
    raw_new = """      const blockRawTouch = e => {\n        if (!profile.touchUi) return;\n        if (e.cancelable) e.preventDefault();\n        e.stopImmediatePropagation();\n      };\n"""
    if s.count(raw_old) != 1:
        raise SystemExit('raw touch block anchor mismatch')
    s = s.replace(raw_old, raw_new, 1)

    pointer_old = """      if (!isTouchPointer(e)) return false;\n"""
    pointer_new = """      if (!profile.touchUi || !isTouchPointer(e)) return false;\n"""
    if s.count(pointer_old) != 1:
        raise SystemExit('pointer gate anchor mismatch')
    s = s.replace(pointer_old, pointer_new, 1)

    insert = """\n  const nativeModeSync = setInterval(() => {\n    const fn = window.Module?._em_openttd_set_touch_ui;\n    if (typeof fn !== 'function') return;\n    fn(profile.touchUi ? 1 : 0);\n    if (window.Module?.calledRun) clearInterval(nativeModeSync);\n  }, 50);\n\n"""
    marker = """  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', installTouchBridge, { once: true });\n"""
    if s.count(marker) != 1:
        raise SystemExit('touch install marker mismatch')
    s = s.replace(marker, insert + marker, 1)
    mobile.write_text(s, encoding='utf-8')

    b = bridge.read_text(encoding='utf-8')
    oldkey = "const CLOUD_CONFIG_KEY = 'openttdMobileConfigV1';"
    newkey = "const CLOUD_CONFIG_KEY = window.openttdBootTouchUi ? 'openttdMobileConfigV1' : 'openttdConfigV1';"
    if b.count(oldkey) != 1:
        raise SystemExit(f'cloud key count={b.count(oldkey)}')
    bridge.write_text(b.replace(oldkey, newkey, 1), encoding='utf-8')

    viewport.write_text(VIEWPORT_V9, encoding='utf-8')
    print('Adaptive desktop/mobile V9 package split applied')


if __name__ == '__main__':
    main()
