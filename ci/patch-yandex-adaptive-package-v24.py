#!/usr/bin/env python3
"""V24: recover the OpenTTD surface when the Yandex host keeps a stale game size.

Package-side only. Builds on V23 and adds a desktop host-geometry fallback based
on the healthy relationship between the iframe viewport and browser outer size.
This specifically targets the DevTools close case where the child viewport can
remain stuck at the smaller docked-console height. It also performs one guarded
Yandex fullscreen request/exit pulse on the next trusted pointer gesture if the
host still reports a stale shrunken frame. Touch/mobile sizing remains V23-like.
"""
from __future__ import annotations

import argparse
from pathlib import Path

VIEWPORT_V24 = r'''/* Adaptive V24 host-aware full-viewport desktop + touch layout.
 * V23 handled child viewport events. V24 additionally remembers a healthy
 * desktop host geometry and can recover when the Yandex shell leaves the game
 * iframe at a stale DevTools-docked size after the console is closed.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV24Installed) return;
  window.__openttdAdaptiveViewportV24Installed = true;

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

  const rawViewport = touchUi => {
    const vv = window.visualViewport;
    let rect = null;
    try { rect = probe?.getBoundingClientRect?.() || null; } catch (_) {}
    const fallbackWidth = innerWidth || root?.clientWidth || document.body?.clientWidth || 1280;
    const fallbackHeight = innerHeight || root?.clientHeight || document.body?.clientHeight || 720;

    if (touchUi && vv) {
      return {
        width: Math.max(64, Math.round(vv.width || rect?.width || fallbackWidth)),
        height: Math.max(64, Math.round(vv.height || rect?.height || fallbackHeight)),
        left: Math.max(0, Math.round(vv.offsetLeft || 0)),
        top: Math.max(0, Math.round(vv.offsetTop || 0)),
      };
    }
    return {
      width: Math.max(64, Math.round(rect?.width || fallbackWidth)),
      height: Math.max(64, Math.round(rect?.height || fallbackHeight)),
      left: 0,
      top: 0,
    };
  };

  /* Desktop-only host baseline. In an iframe, outerWidth/outerHeight describe
     the browser host window while innerWidth/innerHeight describe the game
     frame. Their healthy delta is stable across ordinary window resizes. */
  const host = {
    baseline: null,
    lastRaw: null,
    mismatch: false,
    shellNudgeInFlight: false,
    shellNudgeDone: false,
  };

  const hostOuter = () => ({
    width: Math.max(0, Math.round(Number(window.outerWidth || 0))),
    height: Math.max(0, Math.round(Number(window.outerHeight || 0))),
  });

  const considerHealthyBaseline = raw => {
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
    /* Only learn a more expansive healthy frame automatically. Never teach the
       baseline a newly shrunken DevTools frame. */
    const previousArea = host.baseline.rawWidth * host.baseline.rawHeight;
    const candidateArea = candidate.rawWidth * candidate.rawHeight;
    if (candidateArea > previousArea * 1.03 || candidate.deltaHeight + 24 < host.baseline.deltaHeight) {
      host.baseline = candidate;
    }
  };

  const recoverDesktopBox = raw => {
    host.lastRaw = raw;
    if (!host.baseline) {
      host.mismatch = false;
      return raw;
    }
    const outer = hostOuter();
    if (outer.width < 320 || outer.height < 240) {
      host.mismatch = false;
      return raw;
    }

    const expectedWidth = Math.max(64, Math.round(outer.width - host.baseline.deltaWidth));
    const expectedHeight = Math.max(64, Math.round(outer.height - host.baseline.deltaHeight));
    const focused = document.hasFocus();
    const shortBy = expectedHeight - raw.height;
    const narrowBy = expectedWidth - raw.width;
    const heightMismatch = focused && shortBy >= 96 && raw.height < expectedHeight * 0.86;
    const widthMismatch = focused && narrowBy >= 128 && raw.width < expectedWidth * 0.84;
    host.mismatch = !!(heightMismatch || widthMismatch);

    return {
      width: widthMismatch ? expectedWidth : raw.width,
      height: heightMismatch ? expectedHeight : raw.height,
      left: 0,
      top: 0,
    };
  };

  const layout = () => {
    const profile = window.openttdMobileProfile || {};
    const touchUi = !!profile.touchUi;
    const raw = rawViewport(touchUi);
    if (touchUi) {
      host.mismatch = false;
      return { viewport: raw, rawViewport: raw, touchUi, ...raw };
    }
    const recovered = recoverDesktopBox(raw);
    return { viewport: recovered, rawViewport: raw, touchUi, ...recovered };
  };

  window.openttdComputeAdaptiveLayout = layout;
  window.openttdGetAdaptiveHostResizeState = () => ({
    baseline: host.baseline ? { ...host.baseline } : null,
    raw: host.lastRaw ? { ...host.lastRaw } : null,
    mismatch: host.mismatch,
  });

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

      if (!box.touchUi && !host.mismatch) considerHealthyBaseline(box.rawViewport);

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
      console.warn('[OpenTTD] Adaptive V24 viewport resize failed', error);
      return false;
    } finally {
      applying = false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => { if (!apply()) setTimeout(apply, 50); });
  };

  const clearDeferred = () => {
    for (const id of deferredTimers) clearTimeout(id);
    deferredTimers = [];
  };

  const scheduleBurst = () => {
    schedule();
    clearDeferred();
    for (const delay of [50, 150, 350, 800, 1500, 2500]) {
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
    window.__openttdAdaptiveViewportResizeObserverV24 = ro;
  }

  /* If the host frame itself is still stale, the child cannot resize the
     cross-origin parent directly. On the next deliberate desktop pointer-up,
     briefly toggle Yandex fullscreen through the documented SDK. This asks the
     platform's own resize manager to rebuild its game block, then immediately
     restores the user's previous non-fullscreen state. It runs at most once. */
  const nudgeYandexShellOnGesture = event => {
    if (!event.isTrusted || !host.mismatch || host.shellNudgeInFlight || host.shellNudgeDone) return;
    const profile = window.openttdMobileProfile || {};
    if (profile.touchUi) return;
    const ysdk = window.ysdk;
    const fullscreen = ysdk?.screen?.fullscreen;
    if (!fullscreen || fullscreen.status === fullscreen.STATUS_ON || typeof fullscreen.request !== 'function' || typeof fullscreen.exit !== 'function') return;

    host.shellNudgeInFlight = true;
    host.shellNudgeDone = true;
    try {
      const entered = fullscreen.request();
      Promise.resolve(entered).then(() => {
        scheduleBurst();
        setTimeout(() => {
          Promise.resolve(fullscreen.exit()).catch(() => {}).finally(() => {
            host.shellNudgeInFlight = false;
            scheduleBurst();
          });
        }, 180);
      }).catch(() => {
        host.shellNudgeInFlight = false;
      });
    } catch (_) {
      host.shellNudgeInFlight = false;
    }
  };
  window.addEventListener('pointerup', nudgeYandexShellOnGesture, { capture: true, passive: true });

  /* Capture several early healthy samples; retain the most expansive one. */
  for (const delay of [0, 150, 400, 900, 1800, 3000]) {
    setTimeout(() => {
      const profile = window.openttdMobileProfile || {};
      if (!profile.touchUi) considerHealthyBaseline(rawViewport(false));
      schedule();
    }, delay);
  }

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
    if 'Adaptive V23 resilient full-viewport desktop + touch layout.' not in current:
        raise SystemExit('V24 requires the verified V23 viewport baseline')
    if 'MAX_DESKTOP_ASPECT_RATIO' in current:
        raise SystemExit('Unexpected aspect-ratio clamp before V24')

    viewport.write_text(VIEWPORT_V24, encoding='utf-8')
    final = viewport.read_text(encoding='utf-8')
    required = (
        'Adaptive V24 host-aware full-viewport desktop + touch layout.',
        'const hostOuter = () => ({',
        'deltaHeight: Math.max(0, outer.height - raw.height)',
        'const recoverDesktopBox = raw => {',
        'raw.height < expectedHeight * 0.86',
        'window.openttdGetAdaptiveHostResizeState',
        'module.setCanvasSize(box.width, box.height)',
        'const nudgeYandexShellOnGesture = event => {',
        'fullscreen.request()',
        'fullscreen.exit()',
        "window.addEventListener('pointerup', nudgeYandexShellOnGesture",
        'for (const delay of [0, 150, 400, 900, 1800, 3000])',
    )
    for needle in required:
        if needle not in final:
            raise SystemExit(f'Missing V24 viewport invariant: {needle}')
    for needle in ('MAX_DESKTOP_ASPECT_RATIO', 'setInterval(apply, 250)'):
        if needle in final:
            raise SystemExit(f'Forbidden V24 viewport pattern survived: {needle}')

    print('Adaptive V24 host-aware resize recovery applied')


if __name__ == '__main__':
    main()
