#!/usr/bin/env python3
"""Apply browser-edition native fixes as one deterministic source patch step."""
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


# Base browser ranking and tutorial implementation.
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

# Root-cause repairs must run last so older compatibility/polish patches cannot
# restore proxy objectives, permissive legacy ranking parsing, or the desktop
# font warning. AI files are staged into Emscripten's /ai before AI::Initialize.
runpy.run_path(str(locate("patch-browser-ranking-strict.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-font-web.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-real-objectives.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-clean-ui.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-ai-static.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-ai-player-selection.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-startup-watchdog.py")), run_name="__main__")

print("Root-cause browser fixes applied: native AI preload, player-activated AI slots, cold-start watchdog, strict 0..1000 ranking, web font handling, real tutorial objectives, and viewport-safe tutorial UI.")
