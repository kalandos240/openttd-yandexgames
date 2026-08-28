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
    """Keep restored cloud configs from disabling the native browser AIs.

    Historical packages used several different sanitizeOfflineConfig bodies,
    including early-return variants. Matching/re-writing that function proved
    brittle. Patch the stable cloud-restore boundary instead: every config that
    is about to be restored is normalized through one small helper.
    """
    text = path.read_text(encoding='utf-8')

    helper_name = 'forceBrowserAIConfig'
    restore_anchor = '  function restoreCloudConfig(FS, personalDir, cloudConfig) {'
    if restore_anchor not in text:
        raise SystemExit('Could not find cloud restore boundary')

    helper = r'''  function forceBrowserAIConfig(config) {
    config = String(config || '');

    if (/^max_no_competitors\s*=.*$/m.test(config)) {
      config = config.replace(/^max_no_competitors\s*=.*$/m, 'max_no_competitors = 3');
    } else if (/^\[difficulty\]\s*$/m.test(config)) {
      config = config.replace(/^\[difficulty\]\s*$/m, '[difficulty]\nmax_no_competitors = 3');
    } else {
      config += (config && !config.endsWith('\n') ? '\n' : '') + '[difficulty]\nmax_no_competitors = 3\n';
    }

    if (/^competitors_interval\s*=.*$/m.test(config)) {
      config = config.replace(/^competitors_interval\s*=.*$/m, 'competitors_interval = 0');
    } else if (/^\[difficulty\]\s*$/m.test(config)) {
      config = config.replace(/^\[difficulty\]\s*$/m, '[difficulty]\ncompetitors_interval = 0');
    } else {
      config += (config && !config.endsWith('\n') ? '\n' : '') + '[difficulty]\ncompetitors_interval = 0\n';
    }
    return config;
  }

'''

    if f'function {helper_name}(config)' not in text:
        text = text.replace(restore_anchor, helper + restore_anchor, 1)

    # The legacy Yandex bridge writes the cloud string at this single boundary.
    # Handle both the direct form and historical sanitizer-wrapped form.
    direct = 'FS.writeFile(configPath, cloudConfig.config);'
    wrapped = 'FS.writeFile(configPath, sanitizeOfflineConfig(cloudConfig.config));'
    replacement = 'FS.writeFile(configPath, forceBrowserAIConfig(cloudConfig.config));'
    if replacement not in text:
        if direct in text:
            text = text.replace(direct, replacement, 1)
        elif wrapped in text:
            text = text.replace(wrapped, replacement, 1)
        else:
            raise SystemExit('Could not route cloud config restore through AI normalizer')

    # If an old sanitizer remains elsewhere, make its literal defaults safe too.
    text = text.replace('max_no_competitors = 0', 'max_no_competitors = 3')
    text = text.replace('competitors_interval = 1', 'competitors_interval = 0')

    if f'function {helper_name}(config)' not in text:
        raise SystemExit('Cloud AI normalizer was not installed')
    if replacement not in text:
        raise SystemExit('Cloud restore does not use AI normalizer')

    helper_start = text.find(f'function {helper_name}(config)')
    helper_end = text.find('function restoreCloudConfig', helper_start)
    patched = text[helper_start:helper_end]
    for marker in ('max_no_competitors = 3', 'competitors_interval = 0', 'return config;'):
        if marker not in patched:
            raise SystemExit(f'Cloud AI normalizer missing marker: {marker}')

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
    print('SimpleAI recovery bundle installed; native runtime preloads AI files and restored cloud configs preserve 3 immediate competitors.')


if __name__ == '__main__':
    main()
