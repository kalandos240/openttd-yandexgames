#!/usr/bin/env python3
"""Fix v14 A/B benchmark gates: baseline may use stock Canvas2D.

The optimized profile must prove the WebGL presenter is active. Requiring that
presenter on the baseline would invalidate the comparison because the presenter
is itself one of the optimizations under test.
"""
from pathlib import Path
import argparse

OLD = "  if (!result.renderer.active) throw new Error('WebGL framebuffer presenter did not activate');\n"
NEW = "  if (profile === 'optimized' && !result.renderer.active) throw new Error('WebGL framebuffer presenter did not activate');\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('harness', type=Path)
    args = ap.parse_args()
    path = args.harness
    text = path.read_text(encoding='utf-8')
    if NEW in text:
        print('A/B renderer gate already corrected')
        return
    if text.count(OLD) != 1:
        raise SystemExit(f'Expected one common WebGL gate, got {text.count(OLD)}')
    text = text.replace(OLD, NEW, 1)
    path.write_text(text, encoding='utf-8')
    print('A/B benchmark corrected: Canvas2D baseline allowed; optimized WebGL remains mandatory.')


if __name__ == '__main__':
    main()
