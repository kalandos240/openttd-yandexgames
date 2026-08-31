#!/usr/bin/env python3
"""Experiment: reduce only 16M-tile browser world warmup from three sweeps to one.

The proven browser performance patch uses three complete RunTileLoop sweeps for
maps from 8M tiles. This experiment changes only 4096x4096 (16M tiles) to one
complete sweep (0x100 RunTileLoop calls). Smaller maps retain the proven behaviour.

This is intentionally experimental. One complete sweep still visits the full map
according to OpenTTD's TILE_UPDATE_FREQUENCY=256 schedule, but it changes the
amount of initial tile-loop ageing versus the validated two-sweep v7 release.
"""
from __future__ import annotations

import argparse
from pathlib import Path

NEEDLE = "if (Map::Size() >= 8u * 1024u * 1024u) browser_tile_warmup_loops = 0x300;"
FIRST = "if (Map::Size() >= 16u * 1024u * 1024u) browser_tile_warmup_loops = 0x100;"
SECOND = "else if (Map::Size() >= 8u * 1024u * 1024u) browser_tile_warmup_loops = 0x300;"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build_script", type=Path)
    args = parser.parse_args()

    path = args.build_script
    text = path.read_text(encoding="utf-8")
    if "Map::Size() >= 16u * 1024u * 1024u" in text and "browser_tile_warmup_loops = 0x100" in text:
        print("4096 one-sweep warmup experiment already enabled")
        return

    if text.count(NEEDLE) != 1:
        raise SystemExit(f"Expected one proven 8M warmup statement, got {text.count(NEEDLE)}")

    pos = text.index(NEEDLE)
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    if line_end < 0:
        line_end = len(text)
    prefix = text[line_start:pos]
    old_line = text[line_start:line_end]
    if old_line != prefix + NEEDLE:
        raise SystemExit(f"Unexpected text around warmup statement: {old_line!r}")

    replacement = prefix + FIRST + "\n" + prefix + SECOND
    text = text[:line_start] + replacement + text[line_end:]

    for token in (
        "Map::Size() >= 16u * 1024u * 1024u",
        "browser_tile_warmup_loops = 0x100",
        "Map::Size() >= 8u * 1024u * 1024u",
        "browser_tile_warmup_loops = 0x300",
    ):
        if token not in text:
            raise SystemExit(f"Missing experiment invariant after patch: {token}")
    if text.count(FIRST) != 1 or text.count(SECOND) != 1:
        raise SystemExit("4096 one-sweep statements are not unique after patch")

    path.write_text(text, encoding="utf-8")
    print(f"4096 one-sweep experiment enabled with preserved prefix {prefix!r}: 16M tiles=1 sweep, 8M+=3 sweeps, smaller maps=stock 5 sweeps.")


if __name__ == "__main__":
    main()
