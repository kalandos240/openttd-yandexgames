#!/usr/bin/env python3
"""V20 cold-start hardening for the verified adaptive V9 package.

Apply only after ci/patch-yandex-adaptive-package-v9.py. V10-V19 are
intentionally not part of this build line.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one match, found {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    mobile = args.dist.resolve() / 'openttd-yandex-mobile.js'
    if not mobile.is_file():
        raise SystemExit(f'Missing {mobile.name}')

    s = mobile.read_text(encoding='utf-8')
    if 'const bootTouchHint' not in s or 'V8-deferred-fixed-placement' not in s:
        raise SystemExit('V20 must be applied to the verified adaptive V9 package')

    s = replace_once(
        s,
        "  window.openttdMobileProfile = profile;\n\n  const publishProfile = () => {\n",
        """  window.openttdMobileProfile = profile;\n\n  /* V20 runtime-ready guard. Emscripten exposes JS wrapper functions before the\n     WebAssembly instance is guaranteed to be initialized. A wrapper therefore\n     being present is not sufficient evidence that it is safe to call. */\n  const getRuntimeModule = () => window.Module || (typeof Module !== 'undefined' ? Module : null);\n  const runtimeReady = () => {\n    const module = getRuntimeModule();\n    return !!(module && module.calledRun === true && module.HEAP8 && module.HEAP8.buffer);\n  };\n  const invokeNative = (name, ...args) => {\n    const module = getRuntimeModule();\n    if (!runtimeReady()) return { called: false, value: undefined };\n    const fn = module?.[name];\n    if (typeof fn !== 'function') return { called: false, value: undefined };\n    try {\n      return { called: true, value: fn(...args) };\n    } catch (error) {\n      console.warn(`[OpenTTD mobile] Native call ${name} failed`, error);\n      return { called: false, value: undefined };\n    }\n  };\n  const syncNativeTouchMode = () => invokeNative('_em_openttd_set_touch_ui', profile.touchUi ? 1 : 0).called;\n  window.openttdMobileRuntimeReady = runtimeReady;\n\n  const publishProfile = () => {\n""",
        'runtime helper anchor',
    )

    s = replace_once(
        s,
        """    const nativeTouchSetter = window.Module?._em_openttd_set_touch_ui;\n    if (typeof nativeTouchSetter === 'function') nativeTouchSetter(profile.touchUi ? 1 : 0);\n""",
        "    syncNativeTouchMode();\n",
        'publishProfile native call',
    )

    s = replace_once(
        s,
        """    const getModule = () => window.Module || (typeof Module !== 'undefined' ? Module : null);\n\n    const gestureLock = active => {\n      const fn = getModule()?._em_openttd_touch_gesture_state;\n      if (typeof fn !== 'function') return false;\n      fn(active ? 1 : 0);\n      return true;\n    };\n""",
        "    const gestureLock = active => invokeNative('_em_openttd_touch_gesture_state', active ? 1 : 0).called;\n",
        'gesture lock native call',
    )

    s = replace_once(
        s,
        """    const nativeMouse = (type, p) => {\n      const fn = getModule()?._em_openttd_touch_mouse_event;\n      if (typeof fn !== 'function') return false;\n      const q = localPoint(p);\n      fn(type, q.x, q.y);\n      return true;\n    };\n\n    const nativeContext = p => {\n      const fn = getModule()?._em_openttd_touch_context;\n      if (typeof fn !== 'function') return 0;\n      const q = localPoint(p);\n      return Number(fn(q.x, q.y)) || 0;\n    };\n\n    const nativePan = (p, previous) => {\n      const fn = getModule()?._em_openttd_touch_pan;\n      if (typeof fn !== 'function' || !previous) return false;\n      const q = localPoint(p);\n      const prev = localPoint(previous);\n      const dx = q.x - prev.x;\n      const dy = q.y - prev.y;\n      if (dx === 0 && dy === 0) return true;\n      return !!fn(q.x, q.y, dx, dy);\n    };\n""",
        """    const nativeMouse = (type, p) => {\n      const q = localPoint(p);\n      return invokeNative('_em_openttd_touch_mouse_event', type, q.x, q.y).called;\n    };\n\n    const nativeContext = p => {\n      const q = localPoint(p);\n      const result = invokeNative('_em_openttd_touch_context', q.x, q.y);\n      return result.called ? (Number(result.value) || 0) : 0;\n    };\n\n    const nativePan = (p, previous) => {\n      if (!previous) return false;\n      const q = localPoint(p);\n      const prev = localPoint(previous);\n      const dx = q.x - prev.x;\n      const dy = q.y - prev.y;\n      if (dx === 0 && dy === 0) return true;\n      const result = invokeNative('_em_openttd_touch_pan', q.x, q.y, dx, dy);\n      return result.called && !!result.value;\n    };\n""",
        'touch native calls',
    )

    s = replace_once(
        s,
        """      const blockRawTouch = e => {\n        if (!profile.touchUi) return;\n        if (e.cancelable) e.preventDefault();\n        e.stopImmediatePropagation();\n      };\n""",
        """      const blockRawTouch = e => {\n        if (!profile.touchUi || !runtimeReady()) return;\n        if (e.cancelable) e.preventDefault();\n        e.stopImmediatePropagation();\n      };\n""",
        'raw touch readiness gate',
    )

    s = replace_once(
        s,
        """    const stopBrowserPointer = e => {\n      if (!profile.touchUi || !isTouchPointer(e)) return false;\n      if (e.cancelable) e.preventDefault();\n      e.stopImmediatePropagation();\n      return true;\n    };\n""",
        """    const stopBrowserPointer = e => {\n      if (!profile.touchUi || !isTouchPointer(e) || !runtimeReady()) return false;\n      if (e.cancelable) e.preventDefault();\n      e.stopImmediatePropagation();\n      return true;\n    };\n""",
        'pointer readiness gate',
    )

    s = replace_once(s, '    const module = getModule();\n', '    const module = getRuntimeModule();\n', 'diagnostic module getter')

    s = replace_once(
        s,
        """  const nativeModeSync = setInterval(() => {\n    const fn = window.Module?._em_openttd_set_touch_ui;\n    if (typeof fn !== 'function') return;\n    fn(profile.touchUi ? 1 : 0);\n    if (window.Module?.calledRun) clearInterval(nativeModeSync);\n  }, 50);\n""",
        """  const nativeModeSync = setInterval(() => {\n    if (syncNativeTouchMode()) clearInterval(nativeModeSync);\n  }, 50);\n""",
        'native mode sync loop',
    )

    for needle in (
        'V20 runtime-ready guard',
        'module.calledRun === true',
        'module.HEAP8 && module.HEAP8.buffer',
        "invokeNative('_em_openttd_set_touch_ui'",
        "invokeNative('_em_openttd_touch_gesture_state'",
        "invokeNative('_em_openttd_touch_mouse_event'",
        "invokeNative('_em_openttd_touch_context'",
        "invokeNative('_em_openttd_touch_pan'",
        '!profile.touchUi || !runtimeReady()',
        '!profile.touchUi || !isTouchPointer(e) || !runtimeReady()',
    ):
        if needle not in s:
            raise SystemExit(f'Missing V20 invariant: {needle}')

    mobile.write_text(s, encoding='utf-8')
    print('Adaptive V20 runtime-ready hardening applied')


if __name__ == '__main__':
    main()
