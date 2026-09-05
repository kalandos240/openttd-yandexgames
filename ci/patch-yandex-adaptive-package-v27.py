#!/usr/bin/env python3
"""V27: recover stale Yandex/DevTools height without stretching the framebuffer.

V26 fixed V25's image degradation by refusing synthetic host dimensions, but
that reintroduced the original failure: after closing docked DevTools the child
viewport can remain at the smaller console-open height, leaving a black strip.

V27 restores the measured V24 host-height recovery, but changes the critical
resize operation. Desktop resize is performed through the V27 native
VideoDriver::ChangeResolution bridge, so SDL window, OpenTTD backing store,
_screen and HTML canvas all move to the same resolution. The WebGL presenter is
also kept in exact-pixel mode and never stretches a smaller source framebuffer.
"""
from __future__ import annotations

import argparse
from pathlib import Path

VIEWPORT_V27 = r'''/* Adaptive V27 host-aware native-framebuffer recovery.
 * Desktop: infer a stale DevTools-closed child height from the previously healthy
 * outer/inner geometry, then resize OpenTTD through the native SDL bridge.
 * Touch/mobile: preserve the verified V26 1:1 visualViewport behavior.
 */
(() => {
  'use strict';
  if (window.__openttdAdaptiveViewportV27Installed) return;
  window.__openttdAdaptiveViewportV27Installed = true;

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
      node.style.setProperty('background', '#000', 'important');
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

  const host = {
    baseline: null,
    lastRaw: null,
    mismatch: false,
    nativeResizePending: false,
    lastTarget: null,
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

  const nativeScreen = module => {
    try {
      const getW = module?._em_openttd_screen_width;
      const getH = module?._em_openttd_screen_height;
      if (typeof getW !== 'function' || typeof getH !== 'function') return null;
      return { width: getW() | 0, height: getH() | 0 };
    } catch (_) {
      return null;
    }
  };

  const resizeDesktopNatively = (module, canvas, width, height) => {
    const fn = module?._em_openttd_force_window_resize;
    if (typeof fn !== 'function') return false;
    let screen = nativeScreen(module);
    if (screen?.width === width && screen?.height === height && canvas.width === width && canvas.height === height) return true;

    try {
      const ok = fn(width, height) | 0;
      if (ok !== 1) return false;
    } catch (error) {
      console.warn('[OpenTTD] V27 native resize call failed', error);
      return false;
    }

    screen = nativeScreen(module);
    if (!screen || screen.width !== width || screen.height !== height) return false;

    /* SDL resize should also update canvas dimensions. If Emscripten leaves the
       HTML attribute one step behind, it is safe to synchronize it only AFTER
       the native backing store already has exactly the target dimensions. */
    if (canvas.width !== width || canvas.height !== height) {
      module.setCanvasSize(width, height);
    }
    return canvas.width === width && canvas.height === height;
  };

  window.openttdComputeAdaptiveLayout = layout;
  window.openttdGetAdaptiveHostResizeState = () => ({
    baseline: host.baseline ? { ...host.baseline } : null,
    raw: host.lastRaw ? { ...host.lastRaw } : null,
    mismatch: host.mismatch,
    nativeResizePending: host.nativeResizePending,
    lastTarget: host.lastTarget ? { ...host.lastTarget } : null,
    nativeScreen: nativeScreen(window.Module || (typeof Module !== 'undefined' ? Module : null)),
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
      host.lastTarget = { width: box.width, height: box.height };

      if (box.touchUi) {
        host.nativeResizePending = false;
        if (canvas.width !== box.width || canvas.height !== box.height) {
          module.setCanvasSize(box.width, box.height);
        }
      } else {
        const exact = resizeDesktopNatively(module, canvas, box.width, box.height);
        host.nativeResizePending = !exact;
        if (!exact) return false;
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
        canvas.style.setProperty('cursor', box.touchUi ? 'none' : 'auto', 'important');
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
      console.warn('[OpenTTD] Adaptive V27 viewport resize failed', error);
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
    /* Dock/undock and the Yandex shell can settle in several phases. The burst
       is bounded; there is no permanent 250 ms watchdog. */
    for (const delay of [50, 120, 250, 500, 900, 1500, 2500, 4000]) {
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
    window.__openttdAdaptiveViewportResizeObserverV27 = ro;
  }

  /* Capture healthy desktop geometry before/after Yandex finishes its first
     layout pass. Do not learn a DevTools-shrunken frame while it lacks focus. */
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


def patch_exact_webgl_guard(runtime: Path) -> None:
    text = runtime.read_text(encoding='utf-8', errors='ignore')
    if '__openttdWebGLPresenter' not in text:
        raise SystemExit('V27 requires WebGL presenter before exact-pixel guard')
    if '__openttdPresenterMismatch' in text and '__otExactPixels' in text:
        return

    old = '__otGl.viewport(0,0,__otCanvas.width,__otCanvas.height);__otGl.useProgram(__otPresenter.program);'
    new = (
        'var __otCanvasW=__otCanvas.width|0,__otCanvasH=__otCanvas.height|0;'
        'var __otExactPixels=__otCanvasW===__otW&&__otCanvasH===__otH;'
        'if(!__otExactPixels){__otSDL.__openttdPresenterMismatch={sourceWidth:__otW,sourceHeight:__otH,canvasWidth:__otCanvasW,canvasHeight:__otCanvasH};'
        '__otGl.clearColor(0,0,0,1);__otGl.clear(__otGl.COLOR_BUFFER_BIT)}else{__otSDL.__openttdPresenterMismatch=null}'
        'var __otViewportY=Math.max(0,__otCanvasH-__otH);'
        '__otGl.viewport(0,__otViewportY,__otW,__otH);__otGl.useProgram(__otPresenter.program);'
    )
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'WebGL viewport anchor count={count}')
    runtime.write_text(text.replace(old, new, 1), encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()
    viewport = dist / 'openttd-full-viewport.js'
    runtime = dist / 'openttd-runtime.js'
    for path in (viewport, runtime):
        if not path.is_file():
            raise SystemExit(f'Missing {path.name}')

    current = viewport.read_text(encoding='utf-8')
    if 'Adaptive V26 exact child-viewport + native-pixel layout.' not in current:
        raise SystemExit('V27 requires verified V26 package baseline')

    viewport.write_text(VIEWPORT_V27, encoding='utf-8')
    patch_exact_webgl_guard(runtime)

    final = viewport.read_text(encoding='utf-8')
    for needle in (
        'Adaptive V27 host-aware native-framebuffer recovery.',
        'const recoverDesktopBox = raw => {',
        'raw.height < expectedHeight * 0.86',
        'const resizeDesktopNatively = (module, canvas, width, height) => {',
        "module?._em_openttd_force_window_resize",
        "module?._em_openttd_screen_width",
        "module?._em_openttd_screen_height",
        'host.nativeResizePending = !exact;',
        "bg.style.setProperty('display', 'none', 'important')",
    ):
        if needle not in final:
            raise SystemExit(f'Missing V27 invariant: {needle}')
    for forbidden in ('fullscreen.request()', 'fullscreen.exit()', 'setInterval(apply, 250)', 'MAX_DESKTOP_ASPECT_RATIO'):
        if forbidden in final:
            raise SystemExit(f'Forbidden V27 pattern survived: {forbidden}')

    runtime_text = runtime.read_text(encoding='utf-8', errors='ignore')
    for needle in ('__openttdWebGLPresenter', '__openttdPresenterMismatch', '__otExactPixels', 'texSubImage2D'):
        if needle not in runtime_text:
            raise SystemExit(f'Missing V27 WebGL invariant: {needle}')

    print('Adaptive V27 native framebuffer resize recovery applied')


if __name__ == '__main__':
    main()
