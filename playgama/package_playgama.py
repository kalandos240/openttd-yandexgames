#!/usr/bin/env python3
"""Convert the pinned, tested OpenTTD browser build into a Playgama package."""
from pathlib import Path
import argparse
import re
import shutil

BRIDGE_URL = "https://bridge.playgama.com/v1/stable/playgama-bridge.js"
BRIDGE = f'<script src="{BRIDGE_URL}"></script>'
ADAPTER = '<script src="playgama-yandex-compat.js"></script>'
AI_BUNDLE = '<script src="openttd-classic-ai.js"></script>'
FIXES = '<script src="openttd-playgama-fixes.js"></script>'
AI_PRERUN = '<script src="openttd-ai-prerun.js"></script>'
RUNTIME_TAG_RE = re.compile(
    r'<script\b(?=[^>]*\bsrc=["\']openttd-runtime\.js["\'])[^>]*></script>',
    re.I,
)

NOTICE = f"""Playgama integration
====================

Active SDK: Playgama Bridge JS Core stable
{BRIDGE_URL}

This package is based on the pinned, previously tested OpenTTD 15.3 browser
runtime. The Playgama layer maps language, cloud saves, LoadingAPI/GameplayAPI,
interstitial advertising, pause/resume and platform mute events to Playgama Bridge.

Playgama-specific QA/runtime fixes in this package:
- the platform language is applied on every launch, so a stale saved locale cannot
  override the language selected by the Playgama QA/platform environment;
- the native 16:9 game surface is kept intact and centred on square/tall viewports;
  the existing OpenTTD background fills the remaining viewport instead of
  stretching or cropping the game canvas;
- platform pause freezes both the native OpenTTD pause state and Emscripten main
  loop, while mute/pause state also suspends audio;
- browser music playback is retried after accidental autoplay/focus suspension;
- three computer competitors are enabled and a bundled GPLv2 SimpleAI package,
  with its required pathfinder libraries, is installed into OpenTTD's personal
  AI directory after IDBFS restore and before OpenTTD main() starts. SimpleAI
  intentionally follows the style of the classic OpenTTD/Transport Tycoon AI.

The only intentional modification inside openttd-runtime.js is changing the
three web-port startup defaults from max_no_competitors = 0 to
max_no_competitors = 3. No gameplay code is otherwise rewritten.

Rewarded ads are disabled because this port has no rewarded-ad mechanic. Banner
ads are disabled. Interstitial ads remain enabled and are requested only at safe
pauses by the existing game integration.
"""


def patch_html(html: str) -> str:
    # Normalize every previously used Playgama Bridge CDN form to the current
    # documented stable v1 endpoint. Older packages accidentally referenced a
    # non-documented /v2/stable path which can prevent the compatibility SDK
    # from ever becoming ready in the platform iframe.
    html = re.sub(
        r'<script\s+src=["\']https://bridge\.playgama\.com/(?:v1/(?:stable|latest)|v2/(?:stable|latest)|latest)/playgama-bridge\.js["\']\s*></script>',
        BRIDGE,
        html,
        flags=re.I,
    )

    if BRIDGE_URL not in html or 'playgama-yandex-compat.js' not in html:
        yandex_bootstrap = '<script src="yandex-bootstrap.js"></script>'
        if yandex_bootstrap in html:
            html = html.replace(yandex_bootstrap, BRIDGE + ADAPTER + yandex_bootstrap, 1)
        else:
            direct_sdk = re.compile(r'<script\s+src=(?:["\']?/sdk\.js["\']?|/sdk\.js)\s*></script>', re.I)
            if direct_sdk.search(html):
                html = direct_sdk.sub(BRIDGE + ADAPTER, html, count=1)
            else:
                raise SystemExit('No supported Playgama SDK insertion point in index.html')

    # AI data and OpenTTD-specific runtime fixes are loaded with the platform
    # bridge. They define the installer that the preRun gate invokes later.
    if 'openttd-classic-ai.js' not in html or 'openttd-playgama-fixes.js' not in html:
        anchor = '<script src="yandex-bridge.js"></script>'
        if anchor not in html:
            raise SystemExit('yandex-bridge.js insertion point is missing')
        html = html.replace(anchor, anchor + AI_BUNDLE + FIXES, 1)

    # The shell script immediately before openttd-runtime.js creates `Module`.
    # Put the startup gate at this exact boundary: it can decorate Module.preRun
    # before Emscripten's pre.js appends the IDBFS startup callback, while the AI
    # installer above is already present on window.
    if 'openttd-ai-prerun.js' not in html:
        runtime_match = RUNTIME_TAG_RE.search(html)
        if runtime_match is None:
            raise SystemExit('openttd-runtime.js script insertion point is missing')
        html = html[:runtime_match.start()] + AI_PRERUN + html[runtime_match.start():]

    return html


def patch_runtime(runtime_path: Path) -> None:
    data = runtime_path.read_bytes()
    old = b'max_no_competitors = 0'
    new = b'max_no_competitors = 3'
    count = data.count(old)
    if count == 0:
        # Fresh native-AI runtimes no longer contain the legacy web-port
        # assignment at all. Their defaults are compiled into OpenTTD, so
        # there is nothing for the packaging compatibility shim to rewrite.
        return
    if count != 3:
        raise SystemExit(f'Expected exactly 3 disabled-AI startup literals, found {count}')
    data = data.replace(old, new)
    if old in data or data.count(new) < 3:
        raise SystemExit('Could not enable OpenTTD browser competitors deterministically')
    runtime_path.write_bytes(data)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    ap.add_argument('--adapter', type=Path, required=True)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--fixes', type=Path, required=True)
    ap.add_argument('--ai-bundle', type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    index = dist / 'index.html'
    runtime = dist / 'openttd-runtime.js'
    ai_prerun_source = Path(__file__).with_name('openttd-ai-prerun.js')
    if not index.is_file():
        raise SystemExit('index.html must be in package root')
    if not runtime.is_file():
        raise SystemExit('openttd-runtime.js must be in package root')
    if not ai_prerun_source.is_file():
        raise SystemExit('openttd-ai-prerun.js is missing next to the packager')

    html = patch_html(index.read_text(encoding='utf-8'))
    if 'bridge.playgama.com/v2/' in html:
        raise SystemExit('Invalid Playgama Bridge v2 reference remains')
    if BRIDGE not in html or ADAPTER not in html:
        raise SystemExit('Playgama Bridge bootstrap missing')
    if AI_BUNDLE not in html or FIXES not in html or AI_PRERUN not in html:
        raise SystemExit('OpenTTD Playgama AI startup scripts were not inserted')
    if html.index(AI_PRERUN) > html.index('openttd-runtime.js'):
        raise SystemExit('AI preRun gate must load before openttd-runtime.js')
    index.write_text(html, encoding='utf-8')

    patch_runtime(runtime)

    shutil.copy2(args.adapter, dist / 'playgama-yandex-compat.js')
    shutil.copy2(args.config, dist / 'playgama-bridge-config.json')
    shutil.copy2(args.fixes, dist / 'openttd-playgama-fixes.js')
    shutil.copy2(args.ai_bundle, dist / 'openttd-classic-ai.js')
    shutil.copy2(ai_prerun_source, dist / 'openttd-ai-prerun.js')
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

    print(f'Playgama package ready: {dist}')
    print(f'Unpacked bytes: {total}')


if __name__ == '__main__':
    main()
