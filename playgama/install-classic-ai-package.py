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
    if 'const COMPETITOR_INTERVAL = 1;' not in text:
        anchor = '  const COMPETITORS = 3;\n'
        if anchor not in text:
            raise SystemExit('Could not find COMPETITORS runtime anchor')
        text = text.replace(anchor, anchor + '  const COMPETITOR_INTERVAL = 1;\n', 1)

    marker = 'competitors_interval = \' + COMPETITOR_INTERVAL'
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

    if 'competitors_interval = ' not in text or 'COMPETITOR_INTERVAL = 1' not in text:
        raise SystemExit('Competitor interval patch did not apply')
    path.write_text(text, encoding='utf-8')



def patch_cloud_bridge(path: Path) -> None:
    """Stop cloud/config sanitisation from silently disabling free-play AIs."""
    text = path.read_text(encoding='utf-8')
    old = """  function sanitizeOfflineConfig(config) {
    config = String(config || '');
    if (/^max_no_competitors\\s*=.*$/m.test(config)) {
      return config.replace(/^max_no_competitors\\s*=.*$/m, 'max_no_competitors = 0');
    }
    if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      return config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\nmax_no_competitors = 0');
    }
    return config + (config.length === 0 || config.endsWith('\\n') ? '' : '\\n') + '[difficulty]\\nmax_no_competitors = 0\\n';
  }
"""
    new = """  function sanitizeOfflineConfig(config) {
    config = String(config || '');
    if (/^max_no_competitors\\s*=.*$/m.test(config)) {
      config = config.replace(/^max_no_competitors\\s*=.*$/m, 'max_no_competitors = 3');
    } else if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      config = config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\nmax_no_competitors = 3');
    } else {
      config += (config.length === 0 || config.endsWith('\\n') ? '' : '\\n') + '[difficulty]\\nmax_no_competitors = 3\\n';
    }
    if (/^competitors_interval\\s*=.*$/m.test(config)) {
      config = config.replace(/^competitors_interval\\s*=.*$/m, 'competitors_interval = 1');
    } else if (/^\\[difficulty\\]\\s*$/m.test(config)) {
      config = config.replace(/^\\[difficulty\\]\\s*$/m, '[difficulty]\\ncompetitors_interval = 1');
    } else {
      config += (config.length === 0 || config.endsWith('\\n') ? '' : '\\n') + '[difficulty]\\ncompetitors_interval = 1\\n';
    }
    return config;
  }
"""
    if old not in text:
        if 'max_no_competitors = 3' in text and 'competitors_interval = 1' in text:
            return
        raise SystemExit('Could not find legacy cloud AI-disable sanitizer')
    text = text.replace(old, new, 1)
    if 'max_no_competitors = 0' in text[text.find('function sanitizeOfflineConfig'):text.find('function readConfig')]:
        raise SystemExit('Cloud bridge still disables competitors')
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
    print('Bundled SimpleAI installed before OpenTTD runtime; free-play competitors are preserved and start every 1 minute.')


if __name__ == '__main__':
    main()
