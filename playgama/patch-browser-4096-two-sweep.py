#!/usr/bin/env python3
"""Experiment: reduce only 16M-tile browser world warmup from three sweeps to two.

The proven browser performance patch uses three complete RunTileLoop sweeps for
maps from 8M tiles. This experiment changes only 4096x4096 (16M tiles) to two
complete sweeps. Smaller maps retain the proven behaviour.
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
    if "Map::Size() >= 16u * 1024u * 1024u" in text and "browser_tile_warmup_loops = 0x200" in text:
        print("4096 two-sweep warmup experiment already enabled")
        return
    if text.count(OLD) != 1:
        raise SystemExit(f"Expected one proven 8M warmup anchor, got {text.count(OLD)}")
    text = text.replace(OLD, NEW, 1)
    for token in (
        "Map::Size() >= 16u * 1024u * 1024u",
        "browser_tile_warmup_loops = 0x200",
        "Map::Size() >= 8u * 1024u * 1024u",
        "browser_tile_warmup_loops = 0x300",
    ):
        if token not in text:
            raise SystemExit(f"Missing experiment invariant after patch: {token}")
    path.write_text(text, encoding="utf-8")
    print("4096 warmup experiment enabled: 16M tiles=2 sweeps, 8M+=3 sweeps, smaller maps=stock 5 sweeps.")


if __name__ == "__main__":
    main()
