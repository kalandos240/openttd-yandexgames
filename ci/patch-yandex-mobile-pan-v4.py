#!/usr/bin/env python3
"""Replace the DOM-synthetic touch bridge with a native SDL event bridge.

The V3 package has the correct crisp fullscreen framebuffer and cursorless
runtime. V4 keeps that presentation but sends tap/drag/long-press/pinch through
an EMSCRIPTEN_KEEPALIVE C++ function that queues real SDL events.
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
    let dragging = false;
    let longPressTimer = 0;
    let longPressFired = false;
    let pinchDistance = 0;
    const DRAG_THRESHOLD = 7;
    const LONG_PRESS_MS = 520;

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

    const nativeEvent = (type, p) => {
      const module = window.Module || (typeof Module !== 'undefined' ? Module : null);
      const fn = module && module._em_openttd_touch_mouse_event;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      fn(type, q.x, q.y);
      return true;
    };

    const beginLongPress = () => {
      clearLongPress();
      longPressTimer = setTimeout(() => {
        if (!down || dragging || pointers.size !== 1) return;
        longPressFired = true;
        nativeEvent(0, down);
        nativeEvent(3, down);
        nativeEvent(4, down);
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
      pointers.set(e.pointerId, point(e));

      if (pointers.size === 1) {
        primaryId = e.pointerId;
        down = point(e);
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        beginLongPress();
        return;
      }

      if (pointers.size === 2) {
        clearLongPress();
        if (dragging && down) nativeEvent(2, pointers.get(primaryId) || down);
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
          nativeEvent(0, c);
          nativeEvent(nextDistance > pinchDistance ? 5 : 6, c);
          pinchDistance = nextDistance;
        }
        return;
      }

      if (e.pointerId !== primaryId || !down || longPressFired) return;
      const moved = Math.hypot(p.x - down.x, p.y - down.y);
      if (!dragging && moved >= DRAG_THRESHOLD) {
        clearLongPress();
        dragging = true;
        nativeEvent(0, down);
        nativeEvent(1, down);
      }
      if (dragging) nativeEvent(0, p);
    }, { capture: true, passive: false });

    const finishPointer = e => {
      if (!stopBrowserTouch(e)) return;
      const p = point(e);
      const wasPrimary = e.pointerId === primaryId;
      pointers.delete(e.pointerId);
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      clearLongPress();

      if (wasPrimary && down) {
        if (dragging) {
          nativeEvent(0, p);
          nativeEvent(2, p);
        } else if (!longPressFired && pointers.size === 0) {
          nativeEvent(0, p);
          nativeEvent(1, p);
          nativeEvent(2, p);
        }
      }

      if (pointers.size === 0) {
        primaryId = null;
        down = null;
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
      } else if (pointers.size === 1) {
        const [id, remaining] = pointers.entries().next().value;
        primaryId = id;
        down = { ...remaining };
        dragging = false;
        longPressFired = false;
        pinchDistance = 0;
        beginLongPress();
      }
    };

    canvas.addEventListener('pointerup', finishPointer, { capture: true, passive: false });
    canvas.addEventListener('pointercancel', finishPointer, { capture: true, passive: false });
    canvas.addEventListener('contextmenu', e => e.preventDefault(), { capture: true });

    console.info('[OpenTTD mobile] Native SDL touch bridge installed', profile);
  };

'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    mobile = dist / 'openttd-yandex-mobile.js'
    fixes = dist / 'openttd-yandex-fixes.js'
    runtime = dist / 'openttd-runtime.js'
    for path in (mobile, fixes, runtime):
        if not path.is_file():
            raise SystemExit(f'Missing package file: {path.name}')

    text = mobile.read_text(encoding='utf-8')
    pattern = re.compile(
        r"  const installTouchBridge = \(\) => \{.*?(?=  if \(document\.readyState === 'loading'\))",
        re.S,
    )
    text, count = pattern.subn(TOUCH_BRIDGE, text, count=1)
    if count != 1:
        raise SystemExit(f'Could not replace touch bridge: count={count}')
    mobile.write_text(text, encoding='utf-8')

    config = fixes.read_text(encoding='utf-8')
    if "setGui('scroll_mode', '3')" not in config:
        raise SystemExit('Mobile MapLMB scroll_mode=3 is missing')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')

    print(f'Native SDL mobile pan/touch bridge applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
