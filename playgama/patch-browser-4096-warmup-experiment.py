#!/usr/bin/env python3
"""Experiment: reduce only 16M-tile browser world warmup from three sweeps to two.

The normal OpenTTD 15.3 path remains five complete RunTileLoop sweeps. The
existing browser performance patch already uses three sweeps from 8M tiles.
This experiment narrows the additional reduction to maps of at least 16M tiles
(4096x4096) so smaller maps keep the proven behaviour.

Apply this to the already performance-patched build-final.sh before compilation.
"""
from __future__ import annotations

import argparse
from pathlib import Path

OLD = "\t\t\tif (Map::Size() >= 8u * 1024u * 1024u) browser_tile_warmup_loops = 0x300;\n"
NEW = (
    "\t\t\tif (Map::Size() >= 16u * 1024u * 1024u) browser_tile_warmup_loops = 0x200;\n"
    "\t\t\telse if (Map::Size() >= 8u * 1024u * 1024u) browser_tile_warmup_loops = 0x300;\n"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_script", type=Path)
    args = parser.parse_args()

    path = args.build_script
    text = path.read_text(encoding="utf-8")

    if "browser_tile_warmup_loops = 0x200" in text:
        print("4096-map two-sweep warmup experiment already enabled")
        return
    if text.count(OLD) != 1:
        raise SystemExit(f"Expected one browser 8M warmup anchor, got {text.count(OLD)}")

    text = text.replace(OLD, NEW, 1)
    if "Map::Size() >= 16u * 1024u * 1024u" not in text:
        raise SystemExit("16M-map warmup guard missing after patch")
    if "browser_tile_warmup_loops = 0x200" not in text:
        raise SystemExit("Two-sweep warmup invariant missing after patch")
    if "browser_tile_warmup_loops = 0x300" not in text:
        raise SystemExit("8M-map three-sweep fallback was lost")

    path.write_text(text, encoding="utf-8")
    print("4096-map warmup experiment enabled: 16M tiles=2 sweeps, 8M+=3 sweeps, smaller maps=stock 5 sweeps.")


if __name__ == "__main__":
    main()
