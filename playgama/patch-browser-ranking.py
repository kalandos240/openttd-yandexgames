#!/usr/bin/env python3
"""Apply browser-edition native fixes as one deterministic source patch step.

The full tutorial/ranking/UI patch stack is retained. Legacy browser AI source
patches are intentionally excluded: the final build uses the newer native AI
gate/zero-interval fix plus the pre-main bundled SimpleAI installer instead.
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

# Root-cause repairs run last so compatibility/polish patches cannot restore
# permissive ranking parsing, proxy tutorial objectives, desktop font noise, or
# tutorial targets that point at the wrong construction toolbar.
runpy.run_path(str(locate("patch-browser-ranking-strict.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-font-web.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-real-objectives.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-clean-ui.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-tutorial-highlights.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-game-speed-selector.py")), run_name="__main__")
runpy.run_path(str(locate("patch-browser-startup-watchdog.py")), run_name="__main__")

# Do NOT run patch-browser-ai-static.py or patch-browser-ai-runtime-v2.py here.
# Those were the older browser-AI implementation. The current release enables
# the normal OpenTTD AI gate natively, patches competitors_interval=0 natively,
# and installs SimpleAI/dependencies before main() through openttd-ai-prerun.js.
print("Full browser feature stack applied: tutorial with complete native highlights, local/global ranking, vanilla fast-forward guard, NewGRF/UI compatibility, web fonts and startup watchdog; legacy AI source patches intentionally skipped.")
