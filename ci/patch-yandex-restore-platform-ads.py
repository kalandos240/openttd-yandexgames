#!/usr/bin/env python3
"""Restore Yandex-owned sticky ad placement in adaptive V12 packages."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


SUPPRESSION = re.compile(
    r"  /\* V11: OpenTTD monetizes with fullscreen ads, so do not reserve a\n"
    r".*?document\.addEventListener\('fullscreenchange', hideStickyForViewport, \{ passive: true \}\);\n\n",
    re.S,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path)
    dist = parser.parse_args().dist.resolve()
    bridge = dist / "yandex-bridge.js"
    if not bridge.is_file():
        raise SystemExit("Missing yandex-bridge.js")

    text = bridge.read_text(encoding="utf-8")
    text, removed = SUPPRESSION.subn("", text, count=1)
    if removed != 1:
        raise SystemExit(f"Expected one V11 sticky suppression block, found {removed}")

    resume_call = "    hideStickyBanner('game-api-resume');\n"
    if text.count(resume_call) != 1:
        raise SystemExit("Expected one sticky hide call on game resume")
    text = text.replace(resume_call, "", 1)

    forbidden = ("hideBannerAdv", "__openttdStickySuppressionV11", "yandexHideStickyBanner")
    for marker in forbidden:
        if marker in text:
            raise SystemExit(f"Sticky suppression marker remains: {marker}")

    bridge.write_text(text, encoding="utf-8")
    unpacked = sum(p.stat().st_size for p in dist.rglob("*") if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f"Yandex package too large: {unpacked}")
    print(f"Yandex platform ad placement restored: unpacked_bytes={unpacked}")


if __name__ == "__main__":
    main()
