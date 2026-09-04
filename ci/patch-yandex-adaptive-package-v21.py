#!/usr/bin/env python3
"""V21 prefinal package fixes on top of adaptive V9 + V20.

Scope is deliberately package-side only:
- remove the V20 false-negative runtime gate that can disable mobile building;
- make the OpenTTD canvas use the whole available viewport without aspect clamping;
- scrub stale NewGRF references from both desktop and mobile persistent configs.

Do not change native simulation/AI/performance code here.
"""
from __future__ import annotations

import argparse
from pathlib import Path


VIEWPORT_V21 = r'''/* Adaptive V21 full-viewport desktop + touch layout.
 * Keeps one CSS pixel per OpenTTD backing pixel for sharp rendering, while
 * filling all space exposed by the host iframe. No artificial aspect clamp.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV21Installed) return;
  window.__openttdAdaptiveViewportV21Installed = true;

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
      width: Math.max(64, Math.round(innerWidth || document.documentElement.clientWidth || document.body?.clientWidth || 1280)),
      height: Math.max(64, Math.round(innerHeight || document.documentElement.clientHeight || document.body?.clientHeight || 720)),
      left: 0,
      top: 0,
    };
  };

  const layout = () => {
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;
    const viewport = dimensions(touchUi);
    return { viewport, touchUi, ...viewport };
  };

  window.openttdComputeAdaptiveLayout = layout;
  let raf = 0;
  let applying = false;
  let lastCssKey = '';

  const normalizePage = () => {
    const html = document.documentElement;
    const body = document.body;
    for (const node of [html, body]) {
      if (!node) continue;
      node.style.setProperty('margin', '0', 'important');
      node.style.setProperty('padding', '0', 'important');
      node.style.setProperty('border', '0', 'important');
      node.style.setProperty('width', '100%', 'important');
      node.style.setProperty('height', '100%', 'important');
      node.style.setProperty('overflow', 'hidden', 'important');
      node.style.setProperty('background', '#000', 'important');
    }
  };

  const apply = () => {
    raf = 0;
    if (applying) return false;
    try {
      normalizePage();
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const canvas = Module.canvas || document.getElementById('canvas');
      if (!canvas) return false;
      const box = layout();
      applying = true;

      /* Backing resolution stays exactly equal to CSS resolution: no browser
         stretching, no hidden DPR multiplier and no additional blur. */
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
        canvas.style.setProperty('margin', '0', 'important');
        canvas.style.setProperty('padding', '0', 'important');
        canvas.style.setProperty('border', '0', 'important');
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
      console.warn('[OpenTTD] Adaptive V21 viewport resize failed', error);
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


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one match, found {count}')
    return text.replace(old, new, 1)


def patch_mobile(path: Path) -> None:
    s = path.read_text(encoding='utf-8')
    if 'V20 runtime-ready guard' not in s or 'V8-deferred-fixed-placement' not in s:
        raise SystemExit('V21 mobile fix requires verified V9 placement plus V20 guard')

    old = """  const getRuntimeModule = () => window.Module || (typeof Module !== 'undefined' ? Module : null);\n  const runtimeReady = () => {\n    const module = getRuntimeModule();\n    return !!(module && module.calledRun === true && module.HEAP8 && module.HEAP8.buffer);\n  };\n"""
    new = """  /* V21: calledRun is the Emscripten lifecycle signal we need here. HEAP8 is\n     not guaranteed to be published as Module.HEAP8, so using it as a readiness\n     requirement can leave every touch/build native call disabled forever. */\n  const getRuntimeModule = () => {\n    const globalModule = window.Module;\n    const lexicalModule = typeof Module !== 'undefined' ? Module : null;\n    if (globalModule?.calledRun === true) return globalModule;\n    if (lexicalModule?.calledRun === true) return lexicalModule;\n    return globalModule || lexicalModule;\n  };\n  const runtimeReady = () => {\n    const module = getRuntimeModule();\n    return !!(module && module.calledRun === true);\n  };\n"""
    s = replace_once(s, old, new, 'V20 runtime readiness block')

    if 'module.HEAP8 && module.HEAP8.buffer' in s:
        raise SystemExit('V21 still contains the invalid HEAP8 readiness requirement')
    for needle in (
        'V21: calledRun is the Emscripten lifecycle signal',
        'module.calledRun === true',
        "invokeNative('_em_openttd_touch_mouse_event'",
        "invokeNative('_em_openttd_touch_context'",
        "invokeNative('_em_openttd_touch_pan'",
        "if (gestureMode === 'place')",
        'stats.placementTaps++',
    ):
        if needle not in s:
            raise SystemExit(f'Missing mobile invariant after V21 patch: {needle}')
    path.write_text(s, encoding='utf-8')


def patch_migration(path: Path) -> None:
    s = path.read_text(encoding='utf-8')
    if 'Persistent NewGRF migration complete' not in s:
        raise SystemExit('Vanilla NewGRF migration script is not the expected package version')

    old_strip = """      if (!skip) out.push(line);\n    }\n    return out.join('\\n');\n"""
    new_strip = """      if (skip) continue;\n      /* Defensive cleanup for legacy one-line config variants too. */\n      if (/^\\s*newgrf(?:[-_]static)?\\s*=/.test(line.toLowerCase())) continue;\n      out.push(line);\n    }\n    return out.join('\\n');\n"""
    s = replace_once(s, old_strip, new_strip, 'NewGRF section stripper')

    old_config = """    const configPath = personalDir + '/openttd.cfg';\n    try {\n      const before = FS.readFile(configPath, { encoding: 'utf8' });\n      const after = stripNewGRFSections(before);\n      if (after !== before) {\n        FS.writeFile(configPath, after);\n        removed.push(configPath + ':[newgrf]');\n      }\n    } catch (_) {}\n"""
    new_config = """    /* Adaptive builds have separate desktop and mobile configs. Older\n       migration code cleaned only openttd.cfg, which allowed stale mobile\n       NewGRF references to survive cloud/IDBFS restore. Always clean both. */\n    for (const configName of ['openttd.cfg', 'openttd-mobile.cfg']) {\n      const configPath = personalDir + '/' + configName;\n      try {\n        const before = FS.readFile(configPath, { encoding: 'utf8' });\n        const after = stripNewGRFSections(before);\n        if (after !== before) {\n          FS.writeFile(configPath, after);\n          removed.push(configPath + ':[newgrf]');\n        }\n      } catch (_) {}\n    }\n"""
    s = replace_once(s, old_config, new_config, 'single desktop config migration')

    for needle in (
        "['openttd.cfg', 'openttd-mobile.cfg']",
        'newgrf(?:[-_]static)?',
        'window.yandexRestoreOpenTTDCloud = async function',
        'FS.syncfs(false',
    ):
        if needle not in s:
            raise SystemExit(f'Missing migration invariant after V21 patch: {needle}')
    path.write_text(s, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    mobile = dist / 'openttd-yandex-mobile.js'
    viewport = dist / 'openttd-full-viewport.js'
    migration = dist / 'openttd-vanilla-migration.js'
    for path in (mobile, viewport, migration):
        if not path.is_file():
            raise SystemExit(f'Missing {path.name}')

    patch_mobile(mobile)
    patch_migration(migration)
    viewport.write_text(VIEWPORT_V21, encoding='utf-8')

    print('Adaptive V21 prefinal package fixes applied')


if __name__ == '__main__':
    main()
