#!/usr/bin/env python3
"""Finalize full-feature browser packages without regressing portal-specific behavior.

Playgama keeps its hosted Bridge while file:// startup stays offline. Yandex keeps
all native tutorial/ranking/full-viewport features, installs the current AI preRun
gate before openttd-runtime.js, and removes executable third-party network URLs.
"""
from __future__ import annotations

# Full-feature AI/Yandex integration revision; this file is also the v14 CI trigger.
import argparse
import re
import shutil
from pathlib import Path

PLAYGAMA_BRIDGE_URL = "https://bridge.playgama.com/v1/stable/playgama-bridge.js"
PLAYGAMA_BRIDGE_TAG = f'<script src="{PLAYGAMA_BRIDGE_URL}"></script>'
LOCAL_LOADER_NAME = "platform-bridge-loader.js"
LOCAL_LOADER_TAG = f'<script src="{LOCAL_LOADER_NAME}"></script>'
CONVERTER_MARKER = f'<!-- openttd-yandex-converter-marker: {PLAYGAMA_BRIDGE_TAG} -->'
AI_PRERUN_NAME = "openttd-ai-prerun.js"
AI_PRERUN_TAG = f'<script src="{AI_PRERUN_NAME}"></script>'
RUNTIME_TAG = '<script src="openttd-runtime.js"></script>'
EXECUTABLE_SUFFIXES = {'.html', '.js', '.css'}
EXTERNAL_URL_RE = re.compile(r'(?i)\b(?:https?|wss?)://[^\s"\'<>`)]*')
KNOWN_EXTERNAL_HOSTS = (
    'bananas-server.openttd.org',
    'content.openttd.org',
    'bridge.playgama.com',
)

LOADER_JS = r'''/* Hosted Playgama bridge loader; direct file:// launch stays completely offline. */
(() => {
  'use strict';
  if (location.protocol === 'file:') {
    window.__openttdDirectFileLaunch = true;
    return;
  }
  /* Parser-time insertion keeps the historical synchronous Bridge ordering for
     the hosted Playgama package without making the local package depend on CDN. */
  document.write('<script src="https://bridge.playgama.com/v1/stable/playgama-bridge.js"><\\/script>');
})();
'''


def read_index(dist: Path) -> tuple[Path, str]:
    index = dist / "index.html"
    if not index.is_file():
        raise SystemExit(f"Missing package index: {index}")
    return index, index.read_text(encoding="utf-8")


def install_ai_prerun(dist: Path, html: str) -> str:
    source = Path(__file__).resolve().with_name(AI_PRERUN_NAME)
    if not source.is_file():
        raise SystemExit(f"Missing current AI preRun source: {source}")
    shutil.copy2(source, dist / AI_PRERUN_NAME)

    if AI_PRERUN_TAG not in html:
        if html.count(RUNTIME_TAG) != 1:
            raise SystemExit(f"Expected one openttd-runtime.js tag, found {html.count(RUNTIME_TAG)}")
        html = html.replace(RUNTIME_TAG, AI_PRERUN_TAG + RUNTIME_TAG, 1)
    if html.count(AI_PRERUN_TAG) != 1:
        raise SystemExit("AI preRun gate insertion is not unique")
    if html.index(AI_PRERUN_TAG) > html.index(RUNTIME_TAG):
        raise SystemExit("AI preRun gate must execute before openttd-runtime.js")
    return html


def prepare_playgama(dist: Path) -> None:
    index, html = read_index(dist)
    count = html.count(PLAYGAMA_BRIDGE_TAG)
    if count != 1:
        raise SystemExit(f"Expected one active Playgama Bridge tag, found {count}")

    # Keep the full feature package intact; add only the current pre-main AI gate.
    html = install_ai_prerun(dist, html)
    html = html.replace(PLAYGAMA_BRIDGE_TAG, LOCAL_LOADER_TAG + "\n" + CONVERTER_MARKER, 1)
    index.write_text(html, encoding="utf-8")
    (dist / LOCAL_LOADER_NAME).write_text(LOADER_JS, encoding="utf-8")
    print("Prepared Playgama direct-file launch and pre-main SimpleAI gate")


def finalize_playgama(dist: Path) -> None:
    index, html = read_index(dist)
    if CONVERTER_MARKER not in html:
        raise SystemExit("Missing temporary Yandex converter marker")
    html = html.replace(CONVERTER_MARKER, "", 1)
    index.write_text(html, encoding="utf-8")
    if PLAYGAMA_BRIDGE_URL in html:
        raise SystemExit("Active/commented Playgama CDN URL remains in final Playgama index")
    if LOCAL_LOADER_TAG not in html or not (dist / LOCAL_LOADER_NAME).is_file():
        raise SystemExit("Local Playgama platform loader is missing")
    if AI_PRERUN_TAG not in html or not (dist / AI_PRERUN_NAME).is_file():
        raise SystemExit("AI preRun gate is missing from final Playgama package")
    if html.index(AI_PRERUN_TAG) > html.index(RUNTIME_TAG):
        raise SystemExit("AI preRun gate moved behind runtime in Playgama package")
    print("Finalized Playgama direct-file package")


def patch_yandex_addon_runtime(dist: Path) -> None:
    """Keep the shared local add-on installer feature-complete but platform-neutral."""
    path = dist / 'openttd-bundled-addons.js'
    if not path.is_file():
        return
    text = path.read_text(encoding='utf-8')
    replacements = {
        'Optional bundled OpenTTD add-ons for the Playgama build.':
            'Optional bundled OpenTTD add-ons for the Yandex Games build.',
        'PLAYGAMA-ALL-LICENSES.md': 'NOTICE.txt',
        'PLAYGAMA-LICENSES.md': 'YANDEX-LICENSES.md',
        '[Playgama/OpenTTD]': '[Yandex/OpenTTD]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if re.search(r'playgama', text, re.I):
        raise SystemExit('Playgama-specific reference remains in Yandex bundled-addons runtime')
    path.write_text(text, encoding='utf-8')


def make_yandex_runtime_autonomous(dist: Path) -> None:
    """Strip executable third-party endpoints after all feature conversion is complete."""
    rewrites: list[str] = []
    for path in sorted(dist.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXECUTABLE_SUFFIXES:
            continue
        rel = path.relative_to(dist).as_posix()
        text = path.read_text(encoding='utf-8', errors='ignore')
        original = text

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

        if "window.open(url_string, '_blank');" in text:
            text = text.replace(
                "window.open(url_string, '_blank');",
                "console.info('[OpenTTD] External URL opening disabled in autonomous Yandex build.');",
            )
            rewrites.append(f'{rel}: disabled window.open(url_string)')

        if text != original:
            path.write_text(text, encoding='utf-8')

    leftovers: list[str] = []
    playgama_hits: list[str] = []
    for path in sorted(dist.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXECUTABLE_SUFFIXES:
            continue
        rel = path.relative_to(dist).as_posix()
        text = path.read_text(encoding='utf-8', errors='ignore')
        for match in EXTERNAL_URL_RE.finditer(text):
            leftovers.append(f'{rel}: {match.group(0)}')
        if re.search(r'playgama', text, re.I):
            playgama_hits.append(rel)
        if re.search(r"return\s+['\"]wss?://['\"]\s*;", text, re.I):
            leftovers.append(f'{rel}: generic WebSocket fallback')

    (dist / 'YANDEX-URL-REWRITE.txt').write_text(
        '\n'.join(rewrites) + ('\n' if rewrites else ''), encoding='utf-8'
    )
    if leftovers:
        raise SystemExit('External runtime network references remain:\n' + '\n'.join(leftovers[:30]))
    if playgama_hits:
        raise SystemExit('Playgama residue remains in executable Yandex files: ' + ', '.join(playgama_hits[:30]))


def assert_full_feature_yandex(dist: Path) -> None:
    """Regression gate for the functionality that must never be lost again."""
    required = (
        'openttd-full-viewport.js',
        'openttd-ranking-core.js',
        'openttd-global-ranking.js',
        'openttd-classic-ai.js',
        'OPENTTD-CLASSIC-AI-MANIFEST.json',
        AI_PRERUN_NAME,
        'openttd-runtime.js',
        'openttd-yandex-fixes.js',
        'yandex-bridge.js',
        'yandex-bootstrap.js',
    )
    for name in required:
        path = dist / name
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f'Missing full-feature Yandex asset: {name}')

    html = (dist / 'index.html').read_text(encoding='utf-8')
    for tag in (
        '<script src="openttd-full-viewport.js"></script>',
        '<script src="openttd-ranking-core.js"></script>',
        '<script src="openttd-global-ranking.js"></script>',
        '<script src="openttd-classic-ai.js"></script>',
        AI_PRERUN_TAG,
    ):
        if tag not in html:
            raise SystemExit(f'Missing full-feature script tag: {tag}')
    if html.index(AI_PRERUN_TAG) > html.index(RUNTIME_TAG):
        raise SystemExit('AI preRun gate is not before runtime in final Yandex HTML')

    viewport = (dist / 'openttd-full-viewport.js').read_text(encoding='utf-8')
    fixes = (dist / 'openttd-yandex-fixes.js').read_text(encoding='utf-8')
    ranking = (dist / 'openttd-ranking-core.js').read_text(encoding='utf-8')
    global_ranking = (dist / 'openttd-global-ranking.js').read_text(encoding='utf-8')
    runtime = (dist / 'openttd-runtime.js').read_text(encoding='utf-8', errors='ignore')

    if 'Module.setCanvasSize(width, height)' not in viewport:
        raise SystemExit('Full viewport backing-canvas resize logic is missing')
    if 'width: 100vw !important' not in fixes or 'height: 100vh !important' not in fixes:
        raise SystemExit('Full viewport CSS did not survive Yandex conversion')
    if 'aspect-ratio: 16 / 9' in fixes:
        raise SystemExit('Legacy 16:9 letterbox returned in Yandex fixes')
    if 'const MAX_SCORE = 1000' not in ranking or 'openttd.localRanking.v3' not in ranking:
        raise SystemExit('Local ranking core is missing')
    if "LEADERBOARD_NAME = 'company_rating'" not in global_ranking:
        raise SystemExit('Yandex global leaderboard provider is missing')
    if 'wasmBinaryFile' not in runtime or 'data:application/octet-stream;base64,' not in runtime:
        raise SystemExit('Expected SINGLE_FILE WebAssembly payload in openttd-runtime.js')
    if (dist / 'openttd.wasm').exists() or (dist / 'openttd.data').exists():
        raise SystemExit('Unexpected split WASM/data files in SINGLE_FILE package')


def finalize_yandex(dist: Path) -> None:
    index, html = read_index(dist)
    if LOCAL_LOADER_TAG in html:
        html = html.replace(LOCAL_LOADER_TAG, "", 1)
        index.write_text(html, encoding="utf-8")
    loader = dist / LOCAL_LOADER_NAME
    if loader.exists():
        loader.unlink()

    bootstrap = dist / "yandex-bootstrap.js"
    if not bootstrap.is_file():
        raise SystemExit("Missing yandex-bootstrap.js")
    text = bootstrap.read_text(encoding="utf-8")
    guard = "if (location.protocol === 'file:')"
    if guard not in text:
        anchor = "window.yandexGamesSDKReady = (async () => {\n"
        if text.count(anchor) != 1:
            raise SystemExit(f"Could not locate Yandex SDK promise anchor ({text.count(anchor)})")
        addition = (
            anchor
            + "  if (location.protocol === 'file:') {\n"
            + "    window.__openttdDirectFileLaunch = true;\n"
            + "    return null;\n"
            + "  }\n"
        )
        text = text.replace(anchor, addition, 1)
    bootstrap.write_text(text, encoding="utf-8")

    final_html = index.read_text(encoding="utf-8")
    if LOCAL_LOADER_NAME in final_html or PLAYGAMA_BRIDGE_URL in final_html:
        raise SystemExit("Playgama platform loader remains in Yandex index")
    if "if (location.protocol === 'file:')" not in bootstrap.read_text(encoding="utf-8"):
        raise SystemExit("Yandex file:// SDK bypass is missing")
    if AI_PRERUN_TAG not in final_html or not (dist / AI_PRERUN_NAME).is_file():
        raise SystemExit("AI preRun gate is missing from final Yandex package")

    patch_yandex_addon_runtime(dist)
    make_yandex_runtime_autonomous(dist)
    assert_full_feature_yandex(dist)
    print("Finalized autonomous full-feature Yandex package: tutorial/ranking/viewport/AI retained")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare-playgama", "finalize-playgama", "finalize-yandex"))
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    if args.mode == "prepare-playgama":
        prepare_playgama(dist)
    elif args.mode == "finalize-playgama":
        finalize_playgama(dist)
    else:
        finalize_yandex(dist)


if __name__ == "__main__":
    main()
