#!/usr/bin/env python3
"""Apply native browser ranking and tutorial patches as one build step."""
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
runpy.run_path(str(locate("patch-browser-ranking-readable.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-toolbar.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-level.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-native-layout.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-objectives.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-compile-fix.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-final-polish.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-v15-compat.py")), run_name="__main__")
print("Native readable ranking + full objective tutorial patches applied with final browser polish and OpenTTD 15.3 compatibility.")
