#!/usr/bin/env python3
"""V21 prefinal package fixes on top of adaptive V9 + V20.

Package-side only: fix mobile native-call readiness, remove the artificial
viewport aspect clamp, and purge stale NewGRF state from both adaptive configs.
Native simulation, AI and performance/optimization code are intentionally untouched.
"""
from __future__ import annotations

import argparse
from pathlib import Path


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
    new = """  /* V21: calledRun is the Emscripten lifecycle signal required here. HEAP8\n     is not guaranteed to be published as Module.HEAP8; requiring it can leave\n     every native touch/build call disabled even after the engine has started. */\n  const getRuntimeModule = () => {\n    const globalModule = window.Module;\n    const lexicalModule = typeof Module !== 'undefined' ? Module : null;\n    if (globalModule?.calledRun === true) return globalModule;\n    if (lexicalModule?.calledRun === true) return lexicalModule;\n    return globalModule || lexicalModule;\n  };\n  const runtimeReady = () => {\n    const module = getRuntimeModule();\n    return !!(module && module.calledRun === true);\n  };\n"""
    s = replace_once(s, old, new, 'V20 runtime readiness block')
    if 'module.HEAP8 && module.HEAP8.buffer' in s:
        raise SystemExit('V21 still contains invalid HEAP8 readiness gate')
    for needle in (
        'V21: calledRun is the Emscripten lifecycle signal',
        "invokeNative('_em_openttd_touch_mouse_event'",
        "invokeNative('_em_openttd_touch_context'",
        "invokeNative('_em_openttd_touch_pan'",
        "if (gestureMode === 'place')",
        'stats.placementTaps++',
    ):
        if needle not in s:
            raise SystemExit(f'Missing mobile invariant: {needle}')
    path.write_text(s, encoding='utf-8')


def patch_viewport(path: Path) -> None:
    s = path.read_text(encoding='utf-8')
    if 'Adaptive V9 desktop + touch viewport.' not in s:
        raise SystemExit('V21 viewport fix requires adaptive V9 viewport')

    s = replace_once(
        s,
        '/* Adaptive V9 desktop + touch viewport.',
        '/* Adaptive V21 full-viewport desktop + touch layout.',
        'viewport version marker',
    )
    s = replace_once(s, '  const MAX_DESKTOP_ASPECT_RATIO = 2;\n\n', '', 'desktop aspect constant')
    clamp = """    if (!touchUi) {\n      if (width / height > MAX_DESKTOP_ASPECT_RATIO) {\n        const next = Math.round(height * MAX_DESKTOP_ASPECT_RATIO);\n        left += Math.round((width - next) / 2);\n        width = next;\n      }\n      if (height / width > MAX_DESKTOP_ASPECT_RATIO) {\n        const next = Math.round(width * MAX_DESKTOP_ASPECT_RATIO);\n        top += Math.round((height - next) / 2);\n        height = next;\n      }\n    }\n"""
    s = replace_once(s, clamp, '', 'desktop aspect clamp')

    apply_anchor = """    try {\n      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;\n"""
    apply_repl = """    try {\n      for (const node of [document.documentElement, document.body]) {\n        if (!node) continue;\n        node.style.setProperty('margin', '0', 'important');\n        node.style.setProperty('padding', '0', 'important');\n        node.style.setProperty('border', '0', 'important');\n        node.style.setProperty('width', '100%', 'important');\n        node.style.setProperty('height', '100%', 'important');\n        node.style.setProperty('overflow', 'hidden', 'important');\n      }\n      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;\n"""
    s = replace_once(s, apply_anchor, apply_repl, 'page normalization anchor')

    style_anchor = """        canvas.style.setProperty('bottom', 'auto', 'important');\n        canvas.style.setProperty('max-width', 'none', 'important');\n"""
    style_repl = """        canvas.style.setProperty('bottom', 'auto', 'important');\n        canvas.style.setProperty('margin', '0', 'important');\n        canvas.style.setProperty('padding', '0', 'important');\n        canvas.style.setProperty('border', '0', 'important');\n        canvas.style.setProperty('max-width', 'none', 'important');\n"""
    s = replace_once(s, style_anchor, style_repl, 'canvas box reset')

    if 'MAX_DESKTOP_ASPECT_RATIO' in s:
        raise SystemExit('Desktop aspect clamp survived V21 viewport patch')
    for needle in (
        'Adaptive V21 full-viewport desktop + touch layout.',
        "node.style.setProperty('margin', '0', 'important')",
        'Module.setCanvasSize(box.width, box.height)',
        "bg.style.setProperty('display', 'none', 'important')",
    ):
        if needle not in s:
            raise SystemExit(f'Missing viewport invariant: {needle}')
    path.write_text(s, encoding='utf-8')


def patch_migration(path: Path) -> None:
    s = path.read_text(encoding='utf-8')
    if 'Persistent NewGRF migration complete' not in s:
        raise SystemExit('Unexpected vanilla migration script')

    old_strip = """      if (!skip) out.push(line);\n    }\n    return out.join('\\n');\n"""
    new_strip = """      if (skip) continue;\n      /* Defensive cleanup for legacy one-line config variants too. */\n      if (/^\\s*newgrf(?:[-_]static)?\\s*=/.test(line.toLowerCase())) continue;\n      out.push(line);\n    }\n    return out.join('\\n');\n"""
    s = replace_once(s, old_strip, new_strip, 'NewGRF stripper')

    dynamic = """    const configPath = personalDir + '/' + (window.openttdConfigFilename || 'openttd.cfg');\n    try {\n      const before = FS.readFile(configPath, { encoding: 'utf8' });\n      const after = stripNewGRFSections(before);\n      if (after !== before) {\n        FS.writeFile(configPath, after);\n        removed.push(configPath + ':[newgrf]');\n      }\n    } catch (_) {}\n"""
    desktop_only = """    const configPath = personalDir + '/openttd.cfg';\n    try {\n      const before = FS.readFile(configPath, { encoding: 'utf8' });\n      const after = stripNewGRFSections(before);\n      if (after !== before) {\n        FS.writeFile(configPath, after);\n        removed.push(configPath + ':[newgrf]');\n      }\n    } catch (_) {}\n"""
    both = """    /* Adaptive V21 always cleans both profiles. This also removes stale\n       references restored from older cloud/IDBFS builds before OpenTTD parses\n       either desktop or mobile configuration. */\n    for (const configName of ['openttd.cfg', 'openttd-mobile.cfg']) {\n      const configPath = personalDir + '/' + configName;\n      try {\n        const before = FS.readFile(configPath, { encoding: 'utf8' });\n        const after = stripNewGRFSections(before);\n        if (after !== before) {\n          FS.writeFile(configPath, after);\n          removed.push(configPath + ':[newgrf]');\n        }\n      } catch (_) {}\n    }\n"""
    matches = int(dynamic in s) + int(desktop_only in s)
    if matches != 1:
        raise SystemExit(f'config migration anchor: expected one supported form, found {matches}')
    s = s.replace(dynamic if dynamic in s else desktop_only, both, 1)

    for needle in (
        "['openttd.cfg', 'openttd-mobile.cfg']",
        'newgrf(?:[-_]static)?',
        'window.yandexRestoreOpenTTDCloud = async function',
        'FS.syncfs(false',
    ):
        if needle not in s:
            raise SystemExit(f'Missing migration invariant: {needle}')
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
    patch_viewport(viewport)
    patch_migration(migration)
    print('Adaptive V21 prefinal package fixes applied')


if __name__ == '__main__':
    main()
