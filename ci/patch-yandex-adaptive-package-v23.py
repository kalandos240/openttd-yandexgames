#!/usr/bin/env python3
"""V23: make adaptive viewport recovery robust after DevTools/iframe resizes.

Package-side only. Replaces the V21 viewport script with event-driven viewport
measurement using a fixed CSS viewport probe, ResizeObserver, visualViewport,
and short deferred resize bursts. No permanent polling is used.
"""
from __future__ import annotations

import argparse
from pathlib import Path

VIEWPORT_V23 = r'''/* Adaptive V23 resilient full-viewport desktop + touch layout.
 * Keeps CSS pixels and backing-store pixels 1:1, removes aspect clamping, and
 * recovers from delayed browser/Yandex iframe resizes (including DevTools
 * dock/undock/open/close) without a permanent polling loop.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV23Installed) return;
  window.__openttdAdaptiveViewportV23Installed = true;

  const root = document.documentElement;
  let probe = document.getElementById('openttd-viewport-probe');
  if (!probe) {
    probe = document.createElement('div');
    probe.id = 'openttd-viewport-probe';
    probe.setAttribute('aria-hidden', 'true');
    probe.style.setProperty('position', 'fixed', 'important');
    probe.style.setProperty('left', '0', 'important');
    probe.style.setProperty('top', '0', 'important');
    probe.style.setProperty('width', '100vw', 'important');
    probe.style.setProperty('height', '100vh', 'important');
    try {
      if (CSS?.supports?.('height', '100dvh')) probe.style.setProperty('height', '100dvh', 'important');
    } catch (_) {}
    probe.style.setProperty('visibility', 'hidden', 'important');
    probe.style.setProperty('pointer-events', 'none', 'important');
    probe.style.setProperty('contain', 'strict', 'important');
    probe.style.setProperty('z-index', '-2147483648', 'important');
    (document.body || root).appendChild(probe);
  }

  const normalizePage = () => {
    for (const node of [document.documentElement, document.body]) {
      if (!node) continue;
      node.style.setProperty('margin', '0', 'important');
      node.style.setProperty('padding', '0', 'important');
      node.style.setProperty('border', '0', 'important');
      node.style.setProperty('width', '100%', 'important');
      node.style.setProperty('height', '100%', 'important');
      node.style.setProperty('min-width', '0', 'important');
      node.style.setProperty('min-height', '0', 'important');
      node.style.setProperty('overflow', 'hidden', 'important');
    }
  };

  const readViewportBox = touchUi => {
    const vv = window.visualViewport;
    let probeRect = null;
    try { probeRect = probe?.getBoundingClientRect?.() || null; } catch (_) {}

    const fallbackWidth = innerWidth || root?.clientWidth || document.body?.clientWidth || 1280;
    const fallbackHeight = innerHeight || root?.clientHeight || document.body?.clientHeight || 720;

    if (touchUi && vv) {
      return {
        width: Math.max(64, Math.round(vv.width || probeRect?.width || fallbackWidth)),
        height: Math.max(64, Math.round(vv.height || probeRect?.height || fallbackHeight)),
        left: Math.max(0, Math.round(vv.offsetLeft || 0)),
        top: Math.max(0, Math.round(vv.offsetTop || 0)),
      };
    }

    /* The fixed 100vw/100dvh probe is authoritative here. It tracks the actual
       iframe viewport even when resize events arrive late or some DOM client
       dimensions still report the previous DevTools-docked size. */
    return {
      width: Math.max(64, Math.round(probeRect?.width || fallbackWidth)),
      height: Math.max(64, Math.round(probeRect?.height || fallbackHeight)),
      left: 0,
      top: 0,
    };
  };

  const layout = () => {
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;
    const viewport = readViewportBox(touchUi);
    return { viewport, touchUi, ...viewport };
  };

  window.openttdComputeAdaptiveLayout = layout;

  let raf = 0;
  let applying = false;
  let lastCssKey = '';
  let deferredTimers = [];

  const apply = () => {
    raf = 0;
    if (applying) return false;
    normalizePage();
    try {
      const module = window.Module || (typeof Module !== 'undefined' ? Module : null);
      if (!module || module.calledRun !== true || typeof module.setCanvasSize !== 'function') return false;
      const canvas = module.canvas || document.getElementById('canvas');
      if (!canvas) return false;

      const box = layout();
      applying = true;

      if (canvas.width !== box.width || canvas.height !== box.height) {
        module.setCanvasSize(box.width, box.height);
      }

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
      console.warn('[OpenTTD] Adaptive V23 viewport resize failed', error);
      return false;
    } finally {
      applying = false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      if (!apply()) setTimeout(apply, 50);
    });
  };

  const clearDeferred = () => {
    for (const id of deferredTimers) clearTimeout(id);
    deferredTimers = [];
  };

  const scheduleBurst = () => {
    schedule();
    clearDeferred();
    /* Yandex's outer resize manager and browser DevTools can settle in several
       layout phases. Recheck a few times, then stop completely. */
    for (const delay of [50, 150, 350, 800, 1500]) {
      deferredTimers.push(setTimeout(schedule, delay));
    }
  };

  for (const type of ['resize', 'orientationchange', 'openttd-mobile-profile', 'focus', 'pageshow']) {
    window.addEventListener(type, scheduleBurst, { passive: true });
  }
  window.visualViewport?.addEventListener('resize', scheduleBurst, { passive: true });
  window.visualViewport?.addEventListener('scroll', scheduleBurst, { passive: true });
  document.addEventListener('fullscreenchange', scheduleBurst, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) scheduleBurst();
  }, { passive: true });

  if (typeof ResizeObserver === 'function') {
    const ro = new ResizeObserver(() => scheduleBurst());
    ro.observe(probe);
    if (document.documentElement) ro.observe(document.documentElement);
    if (document.body) ro.observe(document.body);
    window.__openttdAdaptiveViewportResizeObserverV23 = ro;
  }

  /* Temporary startup readiness only; this is bounded and is not a runtime
     watchdog/polling loop. Once Emscripten is running, event-driven resize takes over. */
  let startupAttempts = 0;
  const waitForRuntime = () => {
    startupAttempts++;
    if (apply()) {
      scheduleBurst();
      return;
    }
    if (startupAttempts < 200) setTimeout(waitForRuntime, 50);
  };

  scheduleBurst();
  waitForRuntime();
})();
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()
    viewport = dist / 'openttd-full-viewport.js'
    if not viewport.is_file():
        raise SystemExit(f'Missing {viewport.name}')

    current = viewport.read_text(encoding='utf-8')
    if 'Adaptive V21 full-viewport desktop + touch layout.' not in current:
        raise SystemExit('V23 requires the verified V21 full-viewport baseline')
    if 'MAX_DESKTOP_ASPECT_RATIO' in current:
        raise SystemExit('Unexpected aspect-ratio clamp before V23')

    viewport.write_text(VIEWPORT_V23, encoding='utf-8')

    final = viewport.read_text(encoding='utf-8')
    required = (
        'Adaptive V23 resilient full-viewport desktop + touch layout.',
        "probe.id = 'openttd-viewport-probe'",
        "probe.style.setProperty('width', '100vw', 'important')",
        "CSS?.supports?.('height', '100dvh')",
        'const ro = new ResizeObserver(() => scheduleBurst());',
        "window.addEventListener(type, scheduleBurst, { passive: true });",
        "for (const delay of [50, 150, 350, 800, 1500])",
        'module.setCanvasSize(box.width, box.height)',
        'window.openttdComputeAdaptiveLayout = layout;',
        'window.visualViewport?.addEventListener(\'resize\', scheduleBurst',
    )
    for needle in required:
        if needle not in final:
            raise SystemExit(f'Missing V23 viewport invariant: {needle}')
    forbidden = (
        'MAX_DESKTOP_ASPECT_RATIO',
        'setInterval(apply, 250)',
    )
    for needle in forbidden:
        if needle in final:
            raise SystemExit(f'Forbidden V23 viewport pattern survived: {needle}')

    print('Adaptive V23 resilient viewport recovery applied')


if __name__ == '__main__':
    main()
