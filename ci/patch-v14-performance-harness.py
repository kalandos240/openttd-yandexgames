#!/usr/bin/env python3
"""Fix v14 A/B benchmark gates and CDP timeout for synchronous 4096 generation.

The optimized profile must prove the WebGL presenter is active. Requiring that
presenter on the baseline would invalidate the comparison because the presenter
is itself one of the optimizations under test.

OpenTTD's production Emscripten world generator is synchronous. On a slow CI
runner a real 4096x4096 baseline generation can block the browser main thread
for more than Puppeteer's default CDP protocol timeout (~180 seconds), even
though the benchmark's explicit world-generation timeout is 720 seconds. Raise
only the CDP transport timeout; do not relax any gameplay/pass criteria.
"""
from pathlib import Path
import argparse

OLD_GATE = "  if (!result.renderer.active) throw new Error('WebGL framebuffer presenter did not activate');\n"
NEW_GATE = "  if (profile === 'optimized' && !result.renderer.active) throw new Error('WebGL framebuffer presenter did not activate');\n"
LAUNCH = "const browser = await puppeteer.launch({\n"
LAUNCH_WITH_PROTOCOL = "const browser = await puppeteer.launch({\n  protocolTimeout: 900000,\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('harness', type=Path)
    args = ap.parse_args()
    path = args.harness
    text = path.read_text(encoding='utf-8')

    changed = False
    if NEW_GATE not in text:
        if text.count(OLD_GATE) != 1:
            raise SystemExit(f'Expected one common WebGL gate, got {text.count(OLD_GATE)}')
        text = text.replace(OLD_GATE, NEW_GATE, 1)
        changed = True

    if LAUNCH_WITH_PROTOCOL not in text:
        if text.count(LAUNCH) != 1:
            raise SystemExit(f'Expected one Puppeteer launch anchor, got {text.count(LAUNCH)}')
        text = text.replace(LAUNCH, LAUNCH_WITH_PROTOCOL, 1)
        changed = True

    path.write_text(text, encoding='utf-8')
    if changed:
        print('A/B harness corrected: Canvas2D baseline allowed and CDP protocol timeout raised to 900s.')
    else:
        print('A/B harness corrections already present.')


if __name__ == '__main__':
    main()
