#!/usr/bin/env python3
"""Normalize legacy tutorial dimensions before the final UX pass.

The quality patch intentionally supports re-runs, but its old `if new in text`
shortcut can leave the second occurrence untouched when two widget groups map
to the same target size. Normalize those remaining coach values explicitly.
"""
from pathlib import Path

path = Path("openttd/src/intro_gui.cpp")
text = path.read_text(encoding="utf-8")

normalizations = {
    "SetMinimalSize(600, 190)": "SetMinimalSize(520, 190)",
    "SetMinimalSize(140, 22)": "SetMinimalSize(120, 26)",
}
for old, new in normalizations.items():
    text = text.replace(old, new)

if "SetMinimalSize(600, 190)" in text or "SetMinimalSize(140, 22)" in text:
    raise SystemExit("Legacy tutorial coach dimensions survived normalization")
if "WID_BTC_CONTENT), SetMinimalSize(520, 190)" not in text:
    raise SystemExit("Normalized tutorial coach panel marker is missing")
if "WID_BTC_PREVIOUS" not in text or "SetMinimalSize(120, 26)" not in text:
    raise SystemExit("Normalized tutorial coach navigation marker is missing")

path.write_text(text, encoding="utf-8")
print("Tutorial coach legacy dimensions normalized for final UX pass.")
