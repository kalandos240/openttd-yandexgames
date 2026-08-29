#!/usr/bin/env python3
"""Convert the verified Playgama OpenTTD package into an autonomous Yandex build."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

PLAYGAMA_BRIDGE_RE = re.compile(
    r'<script\s+src=["\']https://bridge\.playgama\.com/(?:v1|v2)/(?:stable|latest)/playgama-bridge\.js["\']\s*></script>',
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

# Executable Yandex-package files must not contain absolute network endpoints.
# JSON manifests are deliberately excluded: their source/license URLs are inert
# attribution metadata and are never fetched by the game runtime.
EXECUTABLE_SUFFIXES = {'.html', '.js', '.css'}
EXTERNAL_URL_RE = re.compile(r'(?i)\b(?:https?|wss?)://[^\s"\'<>`)]*')
KNOWN_EXTERNAL_HOSTS = (
    'bananas-server.openttd.org',
    'content.openttd.org',
    'bridge.playgama.com',
)


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
    if cloud_count not in (0, 1):
        raise SystemExit(f'Expected at most one legacy Playgama cloud tag, found {cloud_count}')
    if PLAYGAMA_FIXES_TAG not in html:
        raise SystemExit('Playgama runtime-fixes script tag is missing')
    html = html.replace(PLAYGAMA_FIXES_TAG, YANDEX_FIXES_TAG, 1)

    for required in ('yandex-bootstrap.js', 'yandex-bridge.js', 'openttd-yandex-fixes.js'):
        if required not in html:
            raise SystemExit(f'Missing required Yandex script in index.html: {required}')

    if re.search(r'playgama|bridge\.playgama\.com', html, re.I):
        raise SystemExit('Playgama reference remains in Yandex index.html')
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

    # /sdk.js is intentionally NOT a packaged file. On Yandex Games it is the
    # official same-origin platform endpoint supplied by the host environment.
    if "script.src = '/sdk.js'" not in text:
        raise SystemExit('Yandex bootstrap does not use the required relative /sdk.js loader')
    if 'YaGames.init()' not in text:
        raise SystemExit('Yandex bootstrap does not initialize YaGames')
    if re.search(r'location\.(?:host|hostname|origin)|document\.domain', text):
        raise SystemExit('URL/domain restriction found in Yandex bootstrap')
    path.write_text(text, encoding='utf-8')


def make_yandex_fixes(dist: Path) -> None:
    source = dist / 'openttd-playgama-fixes.js'
    if not source.is_file():
        raise SystemExit('openttd-playgama-fixes.js is missing')
    text = source.read_text(encoding='utf-8')

    # Remove the direct Playgama Bridge event binding. Yandex pause/resume,
    # GameplayAPI and advertising events are handled by yandex-bridge.js.
    start = text.find('\n  const bindBridge = (bridge) => {')
    end_marker = '\n  Promise.resolve(window.playgamaBridgeReady).then(bindBridge).catch(() => {});\n'
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit('Could not locate direct Playgama Bridge binding in runtime fixes')
    text = text[:start] + '\n' + text[end + len(end_marker):]

    replacements = {
        'OpenTTD-specific Playgama QA/runtime fixes.': 'OpenTTD-specific Yandex Games QA/runtime fixes.',
        '__openttdPlaygamaFixesInstalled': '__openttdYandexFixesInstalled',
        'openttd-playgama-scale-fix': 'openttd-yandex-scale-fix',
        '[Playgama/OpenTTD]': '[Yandex/OpenTTD]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    if re.search(r'playgama', text, re.I):
        raise SystemExit('Playgama-specific reference remains in Yandex runtime fixes')
    (dist / 'openttd-yandex-fixes.js').write_text(text, encoding='utf-8')


def make_runtime_autonomous(dist: Path) -> None:
    """Remove executable third-party network endpoints from the Yandex package.

    OpenTTD's Emscripten pre.js contains a BaNaNaS WebSocket proxy and even an
    inert GitHub URL in a compatibility comment. The old CI audit rejected the
    comment but missed the real wss:// endpoint. Strip both classes here and
    then perform a protocol+hostname rescan so the produced package, not merely
    the source tree, proves that it is autonomous.
    """
    rewrites: list[str] = []

    for path in sorted(dist.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXECUTABLE_SUFFIXES:
            continue
        rel = path.relative_to(dist).as_posix()
        text = path.read_text(encoding='utf-8', errors='ignore')
        original = text

        # Disable OpenTTD's generic HTTPS->WSS fallback as well as its explicit
        # BaNaNaS proxy URL. A relative /sdk.js remains untouched.
        for token in ("return 'wss://';", 'return "wss://";'):
            if token in text:
                text = text.replace(token, 'return null;')
                rewrites.append(f'{rel}: disabled generic WebSocket fallback')

        def replace_url(match: re.Match[str]) -> str:
            value = match.group(0)
            rewrites.append(f'{rel}: {value} -> about:blank')
            return 'about:blank'

        text = EXTERNAL_URL_RE.sub(replace_url, text)

        for host in KNOWN_EXTERNAL_HOSTS:
            if host in text:
                text = text.replace(host, 'offline.invalid')
                rewrites.append(f'{rel}: {host} -> offline.invalid')

        # The native browser glue can open URLs supplied by the game. The
        # autonomous portal build must not navigate to arbitrary third parties.
        if "window.open(url_string, '_blank');" in text:
            text = text.replace(
                "window.open(url_string, '_blank');",
                "console.info('[OpenTTD] External URL opening disabled in autonomous Yandex build.');",
            )
            rewrites.append(f'{rel}: disabled window.open(url_string)')

        if text != original:
            path.write_text(text, encoding='utf-8')

    leftovers: list[str] = []
    for path in sorted(dist.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXECUTABLE_SUFFIXES:
            continue
        rel = path.relative_to(dist).as_posix()
        text = path.read_text(encoding='utf-8', errors='ignore')
        for match in EXTERNAL_URL_RE.finditer(text):
            leftovers.append(f'{rel}: {match.group(0)}')
        for host in KNOWN_EXTERNAL_HOSTS:
            if host in text:
                leftovers.append(f'{rel}: hostname {host}')
        if re.search(r"return\s+['\"]wss?://['\"]\s*;", text, re.I):
            leftovers.append(f'{rel}: generic WebSocket fallback')

    (dist / 'YANDEX-URL-REWRITE.txt').write_text(
        '\n'.join(rewrites) + ('\n' if rewrites else ''), encoding='utf-8'
    )
    if leftovers:
        raise SystemExit(
            'External runtime network references remain in autonomous Yandex package:\n'
            + '\n'.join(leftovers)
        )


def write_platform_notice(dist: Path) -> None:
    (dist / 'YANDEX-INTEGRATION.txt').write_text(
        'OpenTTD 15.3 - Yandex Games autonomous edition\n'
        '==============================================\n'
        '- Active platform SDK: official same-origin /sdk.js endpoint supplied by Yandex Games.\n'
        '- YaGames.init() runs only after the SDK loader succeeds.\n'
        '- No Playgama runtime or third-party gameplay/content endpoint is executable.\n'
        '- OpenTTD startup is not blocked indefinitely by SDK, cloud or optional add-on requests.\n'
        '- LoadingAPI.ready() is sent after the WebAssembly runtime reaches postRun.\n'
        '- GameplayAPI, pause/resume, interstitial ads and Yandex player data are handled by yandex-bridge.js.\n'
        '- Optional local NewGRF packages remain opt-in and install in the background.\n',
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
    ):
        if not (dist / required).is_file():
            raise SystemExit(f'Required base file is missing: {required}')

    patch_yandex_bootstrap(dist)
    make_yandex_fixes(dist)
    patch_index(dist)

    for name in REMOVE_FILES:
        path = dist / name
        if path.exists():
            path.unlink()

    make_runtime_autonomous(dist)
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

    print('Autonomous Yandex Games package created:', dist)


if __name__ == '__main__':
    main()
