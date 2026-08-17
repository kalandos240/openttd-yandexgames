#!/usr/bin/env python3
"""Convert the pinned, tested OpenTTD browser build into a Playgama v2 package."""
from pathlib import Path
import argparse
import re
import shutil

BRIDGE_URL = "https://bridge.playgama.com/v2/stable/playgama-bridge.js"
BRIDGE = f'<script src="{BRIDGE_URL}"></script>'
ADAPTER = '<script src="playgama-yandex-compat.js"></script>'

NOTICE = f"""Playgama integration
====================

Active SDK: Playgama Bridge JS Core v2 stable
{BRIDGE_URL}

The OpenTTD runtime and Yandex-side game integration are kept byte-for-byte
unchanged. playgama-yandex-compat.js provides the small compatibility facade for
language, cloud saves, LoadingAPI/GameplayAPI, interstitial advertising,
pause/resume and platform mute events.

Rewarded ads are disabled because this OpenTTD port has no rewarded-ad mechanic.
Banner ads are disabled. Interstitial ads remain enabled and the game itself only
requests them at safe pauses. The existing OpenTTD canvas/background already fill
the browser viewport, so the package does not stretch or crop the game UI.
"""


def patch_html(html: str) -> str:
    html = re.sub(
        r'<script\s+src=["\']https://bridge\.playgama\.com/v1/(?:stable|latest)/playgama-bridge\.js["\']\s*></script>',
        BRIDGE,
        html,
        flags=re.I,
    )
    if BRIDGE_URL in html and 'playgama-yandex-compat.js' in html:
        return html

    yandex_bootstrap = '<script src="yandex-bootstrap.js"></script>'
    if yandex_bootstrap in html:
        return html.replace(yandex_bootstrap, BRIDGE + ADAPTER + yandex_bootstrap, 1)

    direct_sdk = re.compile(r'<script\s+src=(?:["\']?/sdk\.js["\']?|/sdk\.js)\s*></script>', re.I)
    if direct_sdk.search(html):
        return direct_sdk.sub(BRIDGE + ADAPTER, html, count=1)

    raise SystemExit('No supported Playgama SDK insertion point in index.html')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    ap.add_argument('--adapter', type=Path, required=True)
    ap.add_argument('--config', type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    index = dist / 'index.html'
    if not index.is_file():
        raise SystemExit('index.html must be in package root')

    html = patch_html(index.read_text(encoding='utf-8'))
    if 'bridge.playgama.com/v1/' in html:
        raise SystemExit('Legacy Playgama Bridge v1 reference remains')
    if BRIDGE not in html or ADAPTER not in html:
        raise SystemExit('Playgama Bridge v2 bootstrap missing')
    index.write_text(html, encoding='utf-8')

    shutil.copy2(args.adapter, dist / 'playgama-yandex-compat.js')
    shutil.copy2(args.config, dist / 'playgama-bridge-config.json')
    (dist / 'PLAYGAMA-INTEGRATION.txt').write_text(NOTICE, encoding='utf-8')

    bad = []
    total = 0
    for path in dist.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(dist).as_posix()
        total += path.stat().st_size
        if ' ' in rel or any(ord(ch) > 127 for ch in rel):
            bad.append(rel)
    if bad:
        raise SystemExit(f'Invalid archive paths: {bad}')
    if total >= 300_000_000:
        raise SystemExit(f'Playgama package exceeds 300 MB unpacked: {total}')

    print(f'Playgama Bridge v2 package ready: {dist}')
    print(f'Unpacked bytes: {total}')


if __name__ == '__main__':
    main()
