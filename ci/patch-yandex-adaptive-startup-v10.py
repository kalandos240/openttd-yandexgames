#!/usr/bin/env python3
"""V10 startup fix for adaptive desktop/mobile package.

V9 exposed native Emscripten wrappers on Module before wasmExports was ready.
Calling those wrappers during SDK/profile/ad startup could throw and leave a
black screen. V10 gates every native touch call on Module.calledRun === true.
"""
from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one occurrence, found {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()
    mobile = dist / 'openttd-yandex-mobile.js'
    runtime = dist / 'openttd-runtime.js'
    if not mobile.is_file() or not runtime.is_file():
        raise SystemExit('Missing adaptive package files')

    text = mobile.read_text(encoding='utf-8')

    text = replace_once(text,
"""    const nativeTouchSetter = window.Module?._em_openttd_set_touch_ui;
    if (typeof nativeTouchSetter === 'function') nativeTouchSetter(profile.touchUi ? 1 : 0);
""",
"""    const nativeModule = window.Module;
    const nativeTouchSetter = nativeModule?._em_openttd_set_touch_ui;
    if (nativeModule?.calledRun === true && typeof nativeTouchSetter === 'function') {
      try { nativeTouchSetter(profile.touchUi ? 1 : 0); } catch (error) {
        console.warn('[OpenTTD adaptive] native touch mode sync deferred', error);
      }
    }
""", 'publishProfile native setter')

    text = replace_once(text,
"""    const gestureLock = active => {
      const fn = getModule()?._em_openttd_touch_gesture_state;
      if (typeof fn !== 'function') return false;
      fn(active ? 1 : 0);
      return true;
    };
""",
"""    const gestureLock = active => {
      const module = getModule();
      if (module?.calledRun !== true) return false;
      const fn = module._em_openttd_touch_gesture_state;
      if (typeof fn !== 'function') return false;
      try { fn(active ? 1 : 0); return true; } catch (error) {
        console.warn('[OpenTTD adaptive] gesture lock call failed', error);
        return false;
      }
    };
""", 'gesture lock readiness')

    text = replace_once(text,
"""    const nativeMouse = (type, p) => {
      const fn = getModule()?._em_openttd_touch_mouse_event;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      fn(type, q.x, q.y);
      return true;
    };
""",
"""    const nativeMouse = (type, p) => {
      const module = getModule();
      if (module?.calledRun !== true) return false;
      const fn = module._em_openttd_touch_mouse_event;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      try { fn(type, q.x, q.y); return true; } catch (error) {
        console.warn('[OpenTTD adaptive] native mouse call failed', error);
        return false;
      }
    };
""", 'native mouse readiness')

    text = replace_once(text,
"""    const nativeContext = p => {
      const fn = getModule()?._em_openttd_touch_context;
      if (typeof fn !== 'function') return 0;
      const q = localPoint(p);
      return Number(fn(q.x, q.y)) || 0;
    };
""",
"""    const nativeContext = p => {
      const module = getModule();
      if (module?.calledRun !== true) return 0;
      const fn = module._em_openttd_touch_context;
      if (typeof fn !== 'function') return 0;
      const q = localPoint(p);
      try { return Number(fn(q.x, q.y)) || 0; } catch (error) {
        console.warn('[OpenTTD adaptive] native context call failed', error);
        return 0;
      }
    };
""", 'native context readiness')

    text = replace_once(text,
"""    const nativePan = (p, previous) => {
      const fn = getModule()?._em_openttd_touch_pan;
      if (typeof fn !== 'function' || !previous) return false;
      const q = localPoint(p);
      const prev = localPoint(previous);
      const dx = q.x - prev.x;
      const dy = q.y - prev.y;
      if (dx === 0 && dy === 0) return true;
      return !!fn(q.x, q.y, dx, dy);
    };
""",
"""    const nativePan = (p, previous) => {
      const module = getModule();
      if (module?.calledRun !== true || !previous) return false;
      const fn = module._em_openttd_touch_pan;
      if (typeof fn !== 'function') return false;
      const q = localPoint(p);
      const prev = localPoint(previous);
      const dx = q.x - prev.x;
      const dy = q.y - prev.y;
      if (dx === 0 && dy === 0) return true;
      try { return !!fn(q.x, q.y, dx, dy); } catch (error) {
        console.warn('[OpenTTD adaptive] native pan call failed', error);
        return false;
      }
    };
""", 'native pan readiness')

    text = replace_once(text,
"""  const nativeModeSync = setInterval(() => {
    const fn = window.Module?._em_openttd_set_touch_ui;
    if (typeof fn !== 'function') return;
    fn(profile.touchUi ? 1 : 0);
    if (window.Module?.calledRun) clearInterval(nativeModeSync);
  }, 50);
""",
"""  const nativeModeSync = setInterval(() => {
    const module = window.Module;
    if (module?.calledRun !== true) return;
    const fn = module._em_openttd_set_touch_ui;
    if (typeof fn !== 'function') return;
    try {
      fn(profile.touchUi ? 1 : 0);
      clearInterval(nativeModeSync);
    } catch (error) {
      console.warn('[OpenTTD adaptive] waiting for native touch mode export', error);
    }
  }, 50);
""", 'native mode sync readiness')

    # Positive marker for CI and diagnostics.
    text = text.replace("      version: 'V8-deferred-fixed-placement',",
                        "      version: 'V10-wasm-ready-deferred-placement',", 1)

    mobile.write_text(text, encoding='utf-8')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')
    print(f'Adaptive V10 WASM-ready startup guards applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
