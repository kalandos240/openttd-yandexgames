#!/usr/bin/env python3
"""Convert the verified browser base into the Yandex Games package.

The game/runtime/content base is preserved. Only the platform layer is swapped:
Playgama Bridge/adapter/cloud glue is removed, the Yandex bootstrap/bridge is
kept, and a platform-neutral global ranking provider is added.
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

PLAYGAMA_BRIDGE_RE = re.compile(
    r'<script\s+src=["\']https://bridge\.playgama\.com/[^"\']+/playgama-bridge\.js["\']\s*></script>',
    re.I,
)
PLAYGAMA_ADAPTER_RE = re.compile(
    r'<script\s+src=["\']playgama-yandex-compat\.js["\']\s*></script>', re.I
)
PLAYGAMA_CLOUD_RE = re.compile(
    r'<script\s+src=["\']openttd-playgama-cloud-saves\.js["\']\s*></script>', re.I
)
PLAYGAMA_FIXES_TAG = '<script src="openttd-playgama-fixes.js"></script>'
YANDEX_FIXES_TAG = '<script src="openttd-yandex-fixes.js"></script>'
YANDEX_BRIDGE_TAG = '<script src="yandex-bridge.js"></script>'
GLOBAL_RANKING_TAG = '<script src="openttd-global-ranking.js"></script>'

REMOVE_FILES = (
    'playgama-yandex-compat.js',
    'playgama-bridge-config.json',
    'openttd-playgama-cloud-saves.js',
    'openttd-playgama-fixes.js',
    'PLAYGAMA-INTEGRATION.txt',
    'PLAYGAMA-V10-CHANGES.txt',
    'PLAYGAMA-V8-CHANGES.txt',
    'PLAYGAMA-V7-CHANGES.txt',
)


def install_global_ranking(dist: Path) -> None:
    source = Path(__file__).resolve().with_name('openttd-global-ranking.js')
    if not source.is_file():
        raise SystemExit(f'Global ranking provider is missing: {source}')
    shutil.copy2(source, dist / 'openttd-global-ranking.js')


def patch_index(dist: Path) -> None:
    path = dist / 'index.html'
    html = path.read_text(encoding='utf-8')
    html, bridge_count = PLAYGAMA_BRIDGE_RE.subn('', html)
    html, adapter_count = PLAYGAMA_ADAPTER_RE.subn('', html)
    html, cloud_count = PLAYGAMA_CLOUD_RE.subn('', html)

    if bridge_count != 1:
        raise SystemExit(f'Expected one Playgama Bridge tag, found {bridge_count}')
    if adapter_count != 1:
        raise SystemExit(f'Expected one Playgama adapter tag, found {adapter_count}')
    if cloud_count != 1:
        raise SystemExit(f'Expected one Playgama cloud tag, found {cloud_count}')
    if PLAYGAMA_FIXES_TAG not in html:
        raise SystemExit('Playgama runtime-fixes script tag is missing')
    html = html.replace(PLAYGAMA_FIXES_TAG, YANDEX_FIXES_TAG, 1)

    for required in ('yandex-bootstrap.js', 'yandex-bridge.js', 'openttd-yandex-fixes.js', 'openttd-ranking-core.js'):
        if required not in html:
            raise SystemExit(f'Missing required platform script in index.html: {required}')

    html = html.replace(GLOBAL_RANKING_TAG, '')
    if YANDEX_BRIDGE_TAG not in html:
        raise SystemExit('Could not find platform bridge insertion point for global ranking')
    html = html.replace(YANDEX_BRIDGE_TAG, YANDEX_BRIDGE_TAG + GLOBAL_RANKING_TAG, 1)

    if re.search(r'playgama|bridge\.playgama\.com', html, re.I):
        raise SystemExit('Playgama reference remains in Yandex index.html')
    if html.count(GLOBAL_RANKING_TAG) != 1:
        raise SystemExit('Global ranking provider insertion is not unique')
    if not html.startswith('<!DOCTYPE html>'):
        raise SystemExit('Yandex index.html is not in standards mode')
    path.write_text(html, encoding='utf-8')


def patch_yandex_bootstrap(dist: Path) -> None:
    path = dist / 'yandex-bootstrap.js'
    text = path.read_text(encoding='utf-8')

    text, count = re.subn(
        r"^\s*if \(location\.protocol === 'file:'\) return null;\s*\n",
        '',
        text,
        count=1,
        flags=re.M,
    )
    if count not in (0, 1):
        raise SystemExit('Unexpected Yandex file-protocol guard count')

    if "script.src = '/sdk.js'" not in text:
        raise SystemExit('Yandex bootstrap does not use the required relative /sdk.js loader')
    if 'YaGames.init()' not in text:
        raise SystemExit('Yandex bootstrap does not initialize YaGames')
    if re.search(r'location\.(?:host|hostname|origin)|document\.domain', text):
        raise SystemExit('URL/domain restriction found in Yandex bootstrap')
    path.write_text(text, encoding='utf-8')


def patch_yandex_bridge(dist: Path) -> None:
    """Avoid calling lazy Emscripten exports before wasmExports is populated."""
    path = dist / 'yandex-bridge.js'
    text = path.read_text(encoding='utf-8')

    old_pause = '''  function setGamePlatformPaused(paused) {
    try {
      if (typeof Module !== 'undefined' && typeof Module._em_openttd_set_platform_pause === 'function') {
        Module._em_openttd_set_platform_pause(paused ? 1 : 0);
        return true;
      }
    } catch (e) {
      console.warn('OpenTTD platform pause bridge failed', e);
    }
    return false;
  }
'''
    new_pause = '''  function setGamePlatformPaused(paused) {
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true) return false;
      if (typeof Module._em_openttd_set_platform_pause !== 'function') return false;
      Module._em_openttd_set_platform_pause(paused ? 1 : 0);
      return true;
    } catch (e) {
      console.warn('OpenTTD platform pause bridge failed', e);
    }
    return false;
  }
'''
    if text.count(old_pause) != 1:
        raise SystemExit('Could not locate Yandex native pause bridge block')
    text = text.replace(old_pause, new_pause, 1)

    old_resume = "if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});"
    new_resume = (
        "if (ctx && ctx.state === 'suspended' && (navigator.userActivation?.hasBeenActive ?? true)) "
        "ctx.resume().catch(() => {});"
    )
    if text.count(old_resume) != 1:
        raise SystemExit('Could not locate Yandex AudioContext resume block')
    text = text.replace(old_resume, new_resume, 1)

    if 'Module.calledRun !== true' not in text:
        raise SystemExit('Yandex pause bridge runtime-ready guard is missing')
    path.write_text(text, encoding='utf-8')


def make_yandex_fixes(dist: Path) -> None:
    source = dist / 'openttd-playgama-fixes.js'
    if not source.is_file():
        raise SystemExit('openttd-playgama-fixes.js is missing')
    text = source.read_text(encoding='utf-8')

    pattern = re.compile(
        r"\n  const bindBridge = \(bridge\) => \{.*?\n  Promise\.resolve\(window\.playgamaBridgeReady\)\.then\(bindBridge\)\.catch\(\(\) => \{\}\);\n",
        re.S,
    )
    text, count = pattern.subn('\n', text, count=1)
    if count != 1:
        raise SystemExit('Could not remove direct Playgama Bridge binding from runtime fixes')

    replacements = {
        'OpenTTD-specific Playgama QA/runtime fixes.': 'OpenTTD-specific platform QA/runtime fixes.',
        '__openttdPlaygamaFixesInstalled': '__openttdPlatformFixesInstalled',
        'openttd-playgama-scale-fix': 'openttd-platform-scale-fix',
        '[Playgama/OpenTTD]': '[OpenTTD platform]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    if re.search(r'playgama', text, re.I):
        raise SystemExit('Playgama-specific reference remains in Yandex runtime fixes')
    if 'width: 100vw !important' not in text or 'height: 100vh !important' not in text:
        raise SystemExit('Full-viewport canvas fix did not survive Yandex conversion')
    if 'aspect-ratio: 16 / 9' in text:
        raise SystemExit('Legacy 16:9 letterbox remains in Yandex runtime fixes')
    target = dist / 'openttd-yandex-fixes.js'
    target.write_text(text, encoding='utf-8')


def write_platform_notice(dist: Path) -> None:
    (dist / 'YANDEX-INTEGRATION.txt').write_text(
        'OpenTTD 15.3 - platform integration build\n'
        '=========================================\n'
        '- Active SDK is loaded dynamically from /sdk.js.\n'
        '- There is no host/domain/protocol allow-list in the bootstrap.\n'
        '- Startup is not blocked indefinitely by SDK, cloud or optional add-on requests.\n'
        '- Native pause calls wait until Emscripten reports Module.calledRun.\n'
        '- The game canvas fills the complete platform viewport.\n'
        '- The page uses standards-mode HTML with a valid <!DOCTYPE html>.\n'
        '- A platform-neutral local/global ranking UI is backed by companyrating.\n',
        encoding='utf-8',
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    for required in (
        'index.html',
        'openttd-runtime.js',
        'yandex-bootstrap.js',
        'yandex-bridge.js',
        'openttd-playgama-fixes.js',
        'openttd-ranking-core.js',
    ):
        if not (dist / required).is_file():
            raise SystemExit(f'Required base file is missing: {required}')

    install_global_ranking(dist)
    patch_yandex_bootstrap(dist)
    patch_yandex_bridge(dist)
    make_yandex_fixes(dist)
    patch_index(dist)

    for name in REMOVE_FILES:
        path = dist / name
        if path.exists():
            path.unlink()

    write_platform_notice(dist)

    forbidden = (
        'playgama-yandex-compat.js',
        'playgama-bridge-config.json',
        'openttd-playgama-cloud-saves.js',
        'openttd-playgama-fixes.js',
    )
    for name in forbidden:
        if (dist / name).exists():
            raise SystemExit(f'Forbidden Playgama runtime file remains: {name}')

    print('Platform package with global ranking provider created:', dist)


if __name__ == '__main__':
    main()
