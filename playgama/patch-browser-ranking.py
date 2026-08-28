#!/usr/bin/env python3
"""Apply native browser ranking and tutorial patches as one build step.

The production workflow already invokes and watches this filename. Keeping the
feature implementation in sibling files lets the combined build reuse focused
probes without duplicating source transformations, while changes here trigger
the final Playgama + Yandex packaging workflow.
"""
from pathlib import Path
import re
import runpy
import shutil
import subprocess


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


def prepare_cyrillic_font_backend() -> None:
    """Make OpenTTD's bundled Cyrillic-capable TTF fonts usable in WebAssembly."""
    embuilder = shutil.which("embuilder")
    if embuilder is None:
        raise SystemExit("Emscripten embuilder is required for the browser OpenTTD build")
    subprocess.run([embuilder, "build", "freetype"], check=True)
    print("Prepared Emscripten FreeType for OpenTTD Latin/Cyrillic default fonts.")


def normalize_tutorial_language_alignment() -> None:
    """Keep generated tutorial language keys aligned like native OpenTTD strings."""
    pattern = re.compile(r"^(STR_BROWSER_TUTORIAL_LEVEL_\d{2})\s*:(.*)$", re.M)
    for filename in ("english.txt", "russian.txt"):
        path = Path("openttd/src/lang") / filename
        text = path.read_text(encoding="utf-8")
        text, count = pattern.subn(lambda match: f"{match.group(1):<63}:{match.group(2)}", text)
        if count != 32:
            raise SystemExit(f"Expected 32 tutorial language rows in {path}, got {count}")
        path.write_text(text, encoding="utf-8")
    print("Normalized all 32 EN/RU tutorial rows to native OpenTTD language alignment.")


prepare_cyrillic_font_backend()
runpy.run_path(str(locate("patch-browser-ranking-core.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-ranking-v2.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-toolbar.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-level.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-polish.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-quality.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-layout-normalize.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-ux.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-dynamic-targets.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-v2.py")), run_name="__main__")
normalize_tutorial_language_alignment()
print("Native 0-1000 ranking + objective-driven 32-step multimodal tutorial + compact dynamic guidance applied together.")
