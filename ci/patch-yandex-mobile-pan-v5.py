#!/usr/bin/env python3
"""V5 mobile touch bridge: pan viewports directly in native OpenTTD.

Unlike V4, one-finger dragging does not emulate a held mouse button at all.
The JS layer sends canvas-space position and delta to em_openttd_touch_pan(),
which hit-tests the OpenTTD window/viewport and calls Window::OnScroll().
Discrete tap/long-press/pinch actions still use the SDL bridge.
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
    const DRAG_THRESHOLD = 7;
    const LONG_PRESS_MS = 520;

    const stats = window.__openttdMobileTouchStats = {
      version: 'V5-direct-viewport-pan',
      panCalls: 0,
      panConsumed: 0,
      taps: 0,
      longPresses: 0,
      pinchSteps: 0,
    };

    const clearLongPress = () => {
      if (longPressTimer) clearTimeout(longPressTimer);
      longPressTimer = 0;
    };

    const point = e => ({ x: e.clientX, y: e.clientY, t: performance.now() });
    const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const center = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });

    const isTouchPointer = e => profile.touchUi && (e.pointerType === 'touch' || e.pointerType === 'pen');

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

    const getModule = () => window.Module || (typeof Module !== 'undefined' ? Module : null);

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

    const stopBrowserTouch = e => {
      if (!isTouchPointer(e)) return false;
      e.preventDefault();
      e.stopImmediatePropagation();
      return true;
    };

    canvas.addEventListener('pointerdown', e => {
      if (!stopBrowserTouch(e)) return;
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
      if (!stopBrowserTouch(e) || !pointers.has(e.pointerId)) return;
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
      if (!stopBrowserTouch(e)) return;
      const p = point(e);
      const wasPrimary = e.pointerId === primaryId;
      pointers.delete(e.pointerId);
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      clearLongPress();

      if (wasPrimary && down) {
        if (!dragging && !longPressFired && pointers.size === 0) {
          stats.taps++;
          nativeMouse(0, p);
          nativeMouse(1, p);
          nativeMouse(2, p);
        }
      }

      if (pointers.size === 0) {
        primaryId = null;
        down = null;
        last = null;
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
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

    const module = getModule();
    console.info('[OpenTTD mobile] V5 direct viewport touch bridge installed', {
      profile,
      nativeMouse: !!(module && module._em_openttd_touch_mouse_event),
      nativePan: !!(module && module._em_openttd_touch_pan),
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
    if '_em_openttd_touch_pan' not in runtime_text:
        raise SystemExit('Runtime does not export _em_openttd_touch_pan')
    if '_em_openttd_touch_mouse_event' not in runtime_text:
        raise SystemExit('Runtime does not export _em_openttd_touch_mouse_event')

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

    print(f'V5 direct native viewport pan applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
