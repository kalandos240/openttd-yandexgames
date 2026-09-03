#!/usr/bin/env python3
"""V6 mobile touch bridge: pan and construction are mutually exclusive.

A touch begins under a native gesture lock. Browser/Emscripten compatibility
mouse events are suppressed for the full gesture. Only our tagged native tap,
right-click and wheel events may pass. Once movement exceeds the pan threshold,
the gesture can only call em_openttd_touch_pan() until release, so active build
tools cannot place or drag-build while the camera is moving.
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
    let dragging = false;
    let longPressTimer = 0;
    let longPressFired = false;
    let pinchDistance = 0;
    let unlockTimer = 0;
    const DRAG_THRESHOLD = 7;
    const LONG_PRESS_MS = 520;
    const COMPAT_MOUSE_GUARD_MS = 220;

    const stats = window.__openttdMobileTouchStats = {
      version: 'V6-exclusive-pan-build-lock',
      panCalls: 0,
      panConsumed: 0,
      taps: 0,
      longPresses: 0,
      pinchSteps: 0,
      gestureLocks: 0,
    };

    const getModule = () => window.Module || (typeof Module !== 'undefined' ? Module : null);

    const gestureLock = active => {
      const module = getModule();
      const fn = module && module._em_openttd_touch_gesture_state;
      if (typeof fn !== 'function') return false;
      fn(active ? 1 : 0);
      if (active) stats.gestureLocks++;
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
    const center = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
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
      const module = getModule();
      const fn = module && module._em_openttd_touch_mouse_event;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      fn(type, q.x, q.y);
      return true;
    };

    const nativePan = (p, previous) => {
      const module = getModule();
      const fn = module && module._em_openttd_touch_pan;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      const prev = localPoint(previous);
      const dx = q.x - prev.x;
      const dy = q.y - prev.y;
      if (dx === 0 && dy === 0) return true;
      stats.panCalls++;
      const consumed = !!fn(q.x, q.y, dx, dy);
      if (consumed) stats.panConsumed++;
      return consumed;
    };

    /* Capture raw Touch Events before Emscripten/SDL sees them. Pointer Events
       below are the sole gesture source. This prevents the browser from
       generating a second compatibility mouse stream behind our classifier. */
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

    const beginLongPress = () => {
      clearLongPress();
      longPressTimer = setTimeout(() => {
        if (!down || dragging || pointers.size !== 1) return;
        longPressFired = true;
        stats.longPresses++;
        nativeMouse(0, down);
        nativeMouse(3, down);
        nativeMouse(4, down);
      }, LONG_PRESS_MS);
    };

    const stopBrowserPointer = e => {
      if (!isTouchPointer(e)) return false;
      if (e.cancelable) e.preventDefault();
      e.stopImmediatePropagation();
      return true;
    };

    canvas.addEventListener('pointerdown', e => {
      if (!stopBrowserPointer(e)) return;
      cancelUnlock();
      gestureLock(true);
      try { canvas.setPointerCapture(e.pointerId); } catch (_) {}
      const p = point(e);
      pointers.set(e.pointerId, p);

      if (pointers.size === 1) {
        primaryId = e.pointerId;
        down = p;
        last = p;
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        beginLongPress();
        return;
      }

      if (pointers.size === 2) {
        clearLongPress();
        dragging = false;
        const pts = [...pointers.values()];
        pinchDistance = distance(pts[0], pts[1]);
      }
    }, { capture: true, passive: false });

    canvas.addEventListener('pointermove', e => {
      if (!stopBrowserPointer(e) || !pointers.has(e.pointerId)) return;
      const p = point(e);
      pointers.set(e.pointerId, p);

      if (pointers.size >= 2) {
        clearLongPress();
        const pts = [...pointers.values()].slice(0, 2);
        const nextDistance = distance(pts[0], pts[1]);
        if (pinchDistance > 0 && Math.abs(nextDistance - pinchDistance) >= 12) {
          const c = center(pts[0], pts[1]);
          nativeMouse(0, c);
          nativeMouse(nextDistance > pinchDistance ? 5 : 6, c);
          stats.pinchSteps++;
          pinchDistance = nextDistance;
        }
        return;
      }

      if (e.pointerId !== primaryId || !down || !last || longPressFired) return;
      const moved = Math.hypot(p.x - down.x, p.y - down.y);
      if (!dragging && moved >= DRAG_THRESHOLD) {
        clearLongPress();
        dragging = true;
      }

      if (dragging) {
        nativePan(p, last);
        last = p;
      }
    }, { capture: true, passive: false });

    const finishPointer = e => {
      if (!stopBrowserPointer(e)) return;
      const p = point(e);
      const wasPrimary = e.pointerId === primaryId;
      pointers.delete(e.pointerId);
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      clearLongPress();

      if (wasPrimary && down && !dragging && !longPressFired && pointers.size === 0) {
        stats.taps++;
        /* Tagged events are explicitly allowed through the native lock. */
        nativeMouse(0, p);
        nativeMouse(1, p);
        nativeMouse(2, p);
      }

      if (pointers.size === 0) {
        primaryId = null;
        down = null;
        last = null;
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        /* Keep the lock briefly after touchend to swallow delayed compatibility
           mouse events produced by some Android browsers. */
        scheduleUnlock();
      } else if (pointers.size === 1) {
        const [id, remaining] = pointers.entries().next().value;
        primaryId = id;
        down = { ...remaining };
        last = { ...remaining };
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        beginLongPress();
      }
    };

    canvas.addEventListener('pointerup', finishPointer, { capture: true, passive: false });
    canvas.addEventListener('pointercancel', finishPointer, { capture: true, passive: false });
    canvas.addEventListener('contextmenu', e => e.preventDefault(), { capture: true });

    window.addEventListener('blur', () => {
      clearLongPress();
      pointers.clear();
      cancelUnlock();
      gestureLock(false);
    }, { passive: true });

    const module = getModule();
    console.info('[OpenTTD mobile] V6 exclusive pan/build lock installed', {
      profile,
      nativeMouse: !!(module && module._em_openttd_touch_mouse_event),
      nativePan: !!(module && module._em_openttd_touch_pan),
      gestureLock: !!(module && module._em_openttd_touch_gesture_state),
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
    for symbol in ('_em_openttd_touch_pan', '_em_openttd_touch_mouse_event', '_em_openttd_touch_gesture_state'):
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

    print(f'V6 exclusive pan/build gesture lock applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
