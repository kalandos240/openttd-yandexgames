#!/usr/bin/env python3
"""Apply the native browser ranking and tutorial patches as one build step.

The production workflow already invokes this filename. Keeping the ranking
implementation in a sibling core file lets the combined build reuse the
separately compile-tested tutorial patch without duplicating either patch.
"""
from pathlib import Path
import runpy


def locate(name: str) -> Path:
    here = Path(__file__).resolve().parent
    candidates = (
        here / name,
        here.parent.parent / "playgama" / name,
        Path.cwd().parent / "playgama" / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit(f"Could not locate combined browser patch dependency: {name}")


runpy.run_path(str(locate("patch-browser-ranking-core.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial.py")), run_name="__main__")
print("Native ranking + tutorial patches applied together.")
