#!/usr/bin/env python3
"""V8 mobile gesture bridge: fixed placement commits only on touch release.

Native context codes from patch-yandex-mobile-touch-behavior-v8.py:
  0 = UI
  1 = normal map viewport (one-finger pan)
  2 = drag construction tool (roads/rails/area tools)
  3 = fixed placement tool (preview follows finger, build on release)

This prevents a depot/object/tunnel/etc. from being built at the initial finger
position merely because the user moved far enough to choose another location.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

TOUCH_BRIDGE = r'''  const installTouchBridge = () => {
    const canvas = document.getElementById('canvas');
    if (!canvas || canvas.__openttdTouchBridgeInstalled) return;
    canvas.__openttdTouchBridgeInstalled = true;

    const pointers = new Map();
    let primaryId = null;
    let down = null;
    let last = null;
    let gestureMode = 'none'; // map | build | place | ui | multi
    let dragging = false;
    let mouseDownSent = false;
    let longPressTimer = 0;
    let longPressFired = false;
    let pinchDistance = 0;
    let multiPanLast = null;
    let multiConsumedGesture = false;
    let unlockTimer = 0;

    const DRAG_THRESHOLD = 7;
    const LONG_PRESS_MS = 520;
    const PINCH_THRESHOLD = 12;
    const COMPAT_MOUSE_GUARD_MS = 220;

    const stats = window.__openttdMobileTouchStats = {
      version: 'V8-deferred-fixed-placement',
      mapPans: 0,
      twoFingerPans: 0,
      buildDrags: 0,
      uiDrags: 0,
      taps: 0,
      buildTaps: 0,
      placementMoves: 0,
      placementTaps: 0,
      longPresses: 0,
      pinchSteps: 0,
      contexts: { ui: 0, map: 0, build: 0, place: 0 },
    };

    const getModule = () => window.Module || (typeof Module !== 'undefined' ? Module : null);

    const gestureLock = active => {
      const fn = getModule()?._em_openttd_touch_gesture_state;
      if (typeof fn !== 'function') return false;
      fn(active ? 1 : 0);
      return true;
    };

    const cancelUnlock = () => {
      if (unlockTimer) clearTimeout(unlockTimer);
      unlockTimer = 0;
    };

    const scheduleUnlock = () => {
      cancelUnlock();
      unlockTimer = setTimeout(() => {
        gestureLock(false);
        unlockTimer = 0;
      }, COMPAT_MOUSE_GUARD_MS);
    };

    const clearLongPress = () => {
      if (longPressTimer) clearTimeout(longPressTimer);
      longPressTimer = 0;
    };

    const point = e => ({ x: e.clientX, y: e.clientY, t: performance.now() });
    const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const center = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, t: performance.now() });
    const isTouchPointer = e => e.pointerType === 'touch' || e.pointerType === 'pen';

    const localPoint = p => {
      const rect = canvas.getBoundingClientRect();
      const rw = Math.max(1, rect.width);
      const rh = Math.max(1, rect.height);
      const sx = canvas.width / rw;
      const sy = canvas.height / rh;
      return {
        x: Math.max(0, Math.min(canvas.width - 1, Math.round((p.x - rect.left) * sx))),
        y: Math.max(0, Math.min(canvas.height - 1, Math.round((p.y - rect.top) * sy))),
      };
    };

    const nativeMouse = (type, p) => {
      const fn = getModule()?._em_openttd_touch_mouse_event;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      fn(type, q.x, q.y);
      return true;
    };

    const nativeContext = p => {
      const fn = getModule()?._em_openttd_touch_context;
      if (typeof fn !== 'function') return 0;
      const q = localPoint(p);
      return Number(fn(q.x, q.y)) || 0;
    };

    const nativePan = (p, previous) => {
      const fn = getModule()?._em_openttd_touch_pan;
      if (typeof fn !== 'function' || !previous) return false;
      const q = localPoint(p);
      const prev = localPoint(previous);
      const dx = q.x - prev.x;
      const dy = q.y - prev.y;
      if (dx === 0 && dy === 0) return true;
      return !!fn(q.x, q.y, dx, dy);
    };

    if (!window.__openttdRawTouchBlocked) {
      window.__openttdRawTouchBlocked = true;
      const blockRawTouch = e => {
        if (e.cancelable) e.preventDefault();
        e.stopImmediatePropagation();
      };
      for (const type of ['touchstart', 'touchmove', 'touchend', 'touchcancel']) {
        window.addEventListener(type, blockRawTouch, { capture: true, passive: false });
      }
    }

    const stopBrowserPointer = e => {
      if (!isTouchPointer(e)) return false;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      return true;
    };

    const beginLongPress = () => {
      clearLongPress();
      if (gestureMode !== 'map') return;
      longPressTimer = setTimeout(() => {
        if (!down || dragging || pointers.size !== 1 || gestureMode !== 'map') return;
        longPressFired = true;
        stats.longPresses++;
        nativeMouse(0, down);
        nativeMouse(3, down);
        nativeMouse(4, down);
      }, LONG_PRESS_MS);
    };

    const startOriginalDrag = (kind, current) => {
      if (mouseDownSent || !down) return;
      clearLongPress();
      dragging = true;
      mouseDownSent = true;
      nativeMouse(0, down);
      nativeMouse(1, down);
      nativeMouse(0, current);
      if (kind === 'build') stats.buildDrags++;
      else stats.uiDrags++;
    };

    const chooseMode = p => {
      const ctx = nativeContext(p);
      if (ctx === 2) {
        stats.contexts.build++;
        return 'build';
      }
      if (ctx === 3) {
        stats.contexts.place++;
        return 'place';
      }
      if (ctx === 1) {
        stats.contexts.map++;
        return 'map';
      }
      stats.contexts.ui++;
      return 'ui';
    };

    canvas.addEventListener('pointerdown', e => {
      if (!stopBrowserPointer(e)) return;
      cancelUnlock();
      const first = pointers.size === 0;
      if (first) gestureLock(true);

      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}
      const p = point(e);
      pointers.set(e.pointerId, p);

      if (first) {
        primaryId = e.pointerId;
        down = p;
        last = p;
        gestureMode = chooseMode(p);
        dragging = false;
        mouseDownSent = false;
        longPressFired = false;
        pinchDistance = 0;
        multiPanLast = null;
        multiConsumedGesture = false;

        /* Move OpenTTD's highlight/cursor to the touched tile without pressing
           LMB. For fixed placement this is preview-only by construction. */
        if (gestureMode === 'build' || gestureMode === 'place') nativeMouse(0, p);
        beginLongPress();
        return;
      }

      if (pointers.size === 2 && !mouseDownSent) {
        clearLongPress();
        gestureMode = 'multi';
        dragging = true;
        multiConsumedGesture = true;
        const pts = [...pointers.values()].slice(0, 2);
        pinchDistance = distance(pts[0], pts[1]);
        multiPanLast = center(pts[0], pts[1]);
      }
    }, { capture: true, passive: false });

    canvas.addEventListener('pointermove', e => {
      if (!stopBrowserPointer(e) || !pointers.has(e.pointerId)) return;
      const p = point(e);
      pointers.set(e.pointerId, p);

      if (gestureMode === 'multi') {
        if (pointers.size < 2) return;
        clearLongPress();
        const pts = [...pointers.values()].slice(0, 2);
        const c = center(pts[0], pts[1]);
        if (multiPanLast && nativePan(c, multiPanLast)) stats.twoFingerPans++;
        multiPanLast = c;

        const nextDistance = distance(pts[0], pts[1]);
        if (pinchDistance > 0 && Math.abs(nextDistance - pinchDistance) >= PINCH_THRESHOLD) {
          nativeMouse(0, c);
          nativeMouse(nextDistance > pinchDistance ? 5 : 6, c);
          stats.pinchSteps++;
          pinchDistance = nextDistance;
        }
        return;
      }

      if (e.pointerId !== primaryId || !down || !last || longPressFired) return;
      const moved = Math.hypot(p.x - down.x, p.y - down.y);

      if (gestureMode === 'map') {
        if (!dragging && moved >= DRAG_THRESHOLD) {
          clearLongPress();
          dragging = true;
        }
        if (dragging) {
          if (nativePan(p, last)) stats.mapPans++;
          last = p;
        }
        return;
      }

      /* Fixed structures are NEVER given LMB-down while the finger is held.
         Motion only moves the native OpenTTD placement preview. */
      if (gestureMode === 'place') {
        nativeMouse(0, p);
        stats.placementMoves++;
        last = p;
        return;
      }

      if (gestureMode === 'build' || gestureMode === 'ui') {
        if (!dragging && moved >= DRAG_THRESHOLD) startOriginalDrag(gestureMode, p);
        else if (dragging && mouseDownSent) nativeMouse(0, p);
        last = p;
      }
    }, { capture: true, passive: false });

    const resetAll = () => {
      primaryId = null;
      down = null;
      last = null;
      gestureMode = 'none';
      dragging = false;
      mouseDownSent = false;
      longPressFired = false;
      pinchDistance = 0;
      multiPanLast = null;
      multiConsumedGesture = false;
      scheduleUnlock();
    };

    const finishPointer = (e, cancelled = false) => {
      if (!stopBrowserPointer(e)) return;
      const p = point(e);
      const wasPrimary = e.pointerId === primaryId;
      pointers.delete(e.pointerId);
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      clearLongPress();

      if (gestureMode === 'multi') {
        if (pointers.size === 0) resetAll();
        return;
      }

      if (wasPrimary && down) {
        if ((gestureMode === 'build' || gestureMode === 'ui') && mouseDownSent) {
          /* Always release a started native drag to avoid a stuck LMB state. */
          nativeMouse(0, p);
          nativeMouse(2, p);
        } else if (!cancelled && !dragging && !longPressFired && pointers.size === 0) {
          stats.taps++;
          if (gestureMode === 'build') stats.buildTaps++;
          if (gestureMode === 'place') stats.placementTaps++;

          /* This is the ONLY LMB-down for fixed placement: commit exactly at
             the final finger position after the user has chosen the location. */
          nativeMouse(0, p);
          nativeMouse(1, p);
          nativeMouse(2, p);
        }
      }

      if (pointers.size === 0) resetAll();
    };

    canvas.addEventListener('pointerup', e => finishPointer(e, false), { capture: true, passive: false });
    canvas.addEventListener('pointercancel', e => finishPointer(e, true), { capture: true, passive: false });
    canvas.addEventListener('contextmenu', e => e.preventDefault(), { capture: true });

    window.addEventListener('blur', () => {
      clearLongPress();
      if (mouseDownSent && last) nativeMouse(2, last);
      pointers.clear();
      cancelUnlock();
      gestureLock(false);
      primaryId = null;
      down = null;
      last = null;
      gestureMode = 'none';
      dragging = false;
      mouseDownSent = false;
    }, { passive: true });

    const module = getModule();
    console.info('[OpenTTD mobile] V8 deferred fixed-placement gestures installed', {
      profile,
      nativeMouse: !!module?._em_openttd_touch_mouse_event,
      nativePan: !!module?._em_openttd_touch_pan,
      nativeContext: !!module?._em_openttd_touch_context,
      gestureLock: !!module?._em_openttd_touch_gesture_state,
      stats,
    });
  };

'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    mobile = dist / 'openttd-yandex-mobile.js'
    runtime = dist / 'openttd-runtime.js'
    for path in (mobile, runtime):
        if not path.is_file():
            raise SystemExit(f'Missing package file: {path.name}')

    runtime_text = runtime.read_text(encoding='utf-8', errors='ignore')
    for symbol in (
        '_em_openttd_touch_pan',
        '_em_openttd_touch_mouse_event',
        '_em_openttd_touch_gesture_state',
        '_em_openttd_touch_context',
    ):
        if symbol not in runtime_text:
            raise SystemExit(f'Runtime does not export {symbol}')

    text = mobile.read_text(encoding='utf-8')
    pattern = re.compile(
        r"  const installTouchBridge = \(\) => \{.*?(?=  if \(document\.readyState === 'loading'\))",
        re.S,
    )
    text, count = pattern.subn(TOUCH_BRIDGE, text, count=1)
    if count != 1:
        raise SystemExit(f'Could not replace touch bridge: count={count}')
    mobile.write_text(text, encoding='utf-8')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')

    print(f'V8 deferred fixed-placement gesture bridge applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
