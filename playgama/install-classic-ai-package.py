#!/usr/bin/env python3
"""Install the generated SimpleAI payload into a production browser package."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

AI_TAG = '<script src="openttd-classic-ai.js"></script>'
FIXES_TAG = '<script src="openttd-playgama-fixes.js"></script>'


def patch_fixes(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    # In OpenTTD, competitors_interval=0 is not "disabled": company_cmd.cpp
    # explicitly treats zero as "start as many competitors as needed now".
    if 'const COMPETITOR_INTERVAL = 0;' not in text:
        if 'const COMPETITOR_INTERVAL = 1;' in text:
            text = text.replace('const COMPETITOR_INTERVAL = 1;', 'const COMPETITOR_INTERVAL = 0;', 1)
        else:
            anchor = '  const COMPETITORS = 3;\n'
            if anchor not in text:
                raise SystemExit('Could not find COMPETITORS runtime anchor')
            text = text.replace(anchor, anchor + '  const COMPETITOR_INTERVAL = 0;\n', 1)

    marker = "competitors_interval = ' + COMPETITOR_INTERVAL"
    if marker not in text:
        max_block = """    if (/^max_no_competitors\\s*=.*$/m.test(config)) {
      config = config.replace(/^max_no_competitors\\s*=.*$/m, 'max_no_competitors = ' + COMPETITORS);
    } else if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      config = config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\nmax_no_competitors = ' + COMPETITORS);
    } else {
      config += (config && !config.endsWith('\\n') ? '\\n' : '') + '[difficulty]\\nmax_no_competitors = ' + COMPETITORS + '\\n';
    }
"""
        interval_block = """

    if (/^competitors_interval\\s*=.*$/m.test(config)) {
      config = config.replace(/^competitors_interval\\s*=.*$/m, 'competitors_interval = ' + COMPETITOR_INTERVAL);
    } else if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      config = config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\ncompetitors_interval = ' + COMPETITOR_INTERVAL);
    } else {
      config += (config && !config.endsWith('\\n') ? '\\n' : '') + '[difficulty]\\ncompetitors_interval = ' + COMPETITOR_INTERVAL + '\\n';
    }
"""
        if max_block not in text:
            raise SystemExit('Could not find forcePlatformConfig competitor block')
        text = text.replace(max_block, max_block + interval_block, 1)

    if 'COMPETITOR_INTERVAL = 0' not in text or marker not in text:
        raise SystemExit('Immediate competitor interval patch did not apply')
    path.write_text(text, encoding='utf-8')


def patch_cloud_bridge(path: Path) -> None:
    """Stop cloud/config sanitisation from silently disabling free-play AIs."""
    text = path.read_text(encoding='utf-8')
    start = text.find('function sanitizeOfflineConfig(config)')
    end = text.find('function readConfig', start)
    if start < 0 or end < 0:
        raise SystemExit('Could not find cloud config sanitizer')
    block = text[start:end]

    # Preserve three competitors and use OpenTTD's native immediate-start mode.
    block = block.replace('max_no_competitors = 0', 'max_no_competitors = 3')
    block = block.replace('competitors_interval = 1', 'competitors_interval = 0')

    # Old baselines may not have an interval line at all.
    if 'competitors_interval' not in block:
        return_anchor = '    return config;\n'
        addition = """    if (/^competitors_interval\\s*=.*$/m.test(config)) {
      config = config.replace(/^competitors_interval\\s*=.*$/m, 'competitors_interval = 0');
    } else if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      config = config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\ncompetitors_interval = 0');
    } else {
      config += (config.length === 0 || config.endsWith('\\n') ? '' : '\\n') + '[difficulty]\\ncompetitors_interval = 0\\n';
    }
"""
        if return_anchor not in block:
            raise SystemExit('Could not add immediate AI interval to cloud sanitizer')
        block = block.replace(return_anchor, addition + return_anchor, 1)

    text = text[:start] + block + text[end:]
    patched = text[start:text.find('function readConfig', start)]
    if 'max_no_competitors = 0' in patched:
        raise SystemExit('Cloud bridge still disables competitors')
    if 'competitors_interval = 1' in patched:
        raise SystemExit('Cloud bridge still delays competitors')
    if 'max_no_competitors = 3' not in patched or 'competitors_interval = 0' not in patched:
        raise SystemExit('Cloud bridge does not preserve immediate AI settings')
    path.write_text(text, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    ap.add_argument('--bundle', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    index = dist / 'index.html'
    fixes = dist / 'openttd-playgama-fixes.js'
    cloud_bridge = dist / 'yandex-bridge.js'
    if not index.is_file() or not fixes.is_file() or not cloud_bridge.is_file():
        raise SystemExit('Production package is missing index.html, runtime fixes, or cloud bridge')

    # Keep the JS bundle as a recovery path for old saves/packages, although the
    # rebuilt native runtime now also preloads these AIs before AI::Initialize().
    shutil.copy2(args.bundle, dist / 'openttd-classic-ai.js')
    shutil.copy2(args.manifest, dist / 'OPENTTD-CLASSIC-AI-MANIFEST.json')

    html = index.read_text(encoding='utf-8')
    if AI_TAG not in html:
        if FIXES_TAG not in html:
            raise SystemExit('Could not find runtime-fixes script tag for AI insertion')
        html = html.replace(FIXES_TAG, AI_TAG + FIXES_TAG, 1)
    if html.count(AI_TAG) != 1:
        raise SystemExit('SimpleAI script tag is not unique')
    index.write_text(html, encoding='utf-8')

    patch_fixes(fixes)
    patch_cloud_bridge(cloud_bridge)
    print('SimpleAI recovery bundle installed; native runtime also preloads AI files and configured competitors start immediately.')


if __name__ == '__main__':
    main()
