#!/usr/bin/env python3
"""Apply semantics-preserving NewGRF resolver hot-path optimizations.

The production browser build does not run the native NewGRF profiler during
normal gameplay. OpenTTD 15.3 nevertheless performs a std::ranges::find over
_newgrf_profilers on every SpriteGroup::Resolve entry. NewGRF-heavy games call
this entry point extremely frequently. Bypass that diagnostic-only lookup when
no profiler exists, while preserving the exact resolver and profiling behaviour
when profiling is active.
"""
from __future__ import annotations

from pathlib import Path


PATH = Path("openttd/src/newgrf_spritegroup.cpp")
MARKER = "Browser edition fast path: NewGRF profiling is normally inactive."


def main() -> None:
    if not PATH.is_file():
        raise SystemExit(f"OpenTTD source is missing: {PATH}")

    text = PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("NewGRF resolver fast path already applied.")
        return

    old = """\tif (group == nullptr) return std::monostate{};\n\n\tconst GRFFile *grf = object.grffile;\n\tauto profiler = std::ranges::find(_newgrf_profilers, grf, &NewGRFProfiler::grffile);\n"""
    new = """\tif (group == nullptr) return std::monostate{};\n\n\t/* Browser edition fast path: NewGRF profiling is normally inactive.\n\t * Avoid the diagnostic profiler lookup on every Action 2 resolver entry.\n\t * This changes no game/NewGRF state and keeps the original profiling path\n\t * byte-for-byte reachable whenever at least one profiler is configured. */\n\tif (_newgrf_profilers.empty()) [[likely]] return group->Resolve(object);\n\n\tconst GRFFile *grf = object.grffile;\n\tauto profiler = std::ranges::find(_newgrf_profilers, grf, &NewGRFProfiler::grffile);\n"""

    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one OpenTTD 15.3 resolver anchor, found {count}")

    text = text.replace(old, new, 1)

    checks = (
        MARKER,
        "if (_newgrf_profilers.empty()) [[likely]] return group->Resolve(object);",
        "auto profiler = std::ranges::find(_newgrf_profilers, grf, &NewGRFProfiler::grffile);",
        "profiler->BeginResolve(object);",
        "profiler->RecursiveResolve();",
    )
    for check in checks:
        if check not in text:
            raise SystemExit(f"Post-patch NewGRF resolver check failed: {check!r}")

    PATH.write_text(text, encoding="utf-8")
    print("Applied NewGRF resolver fast path: inactive profiler lookup bypassed.")


if __name__ == "__main__":
    main()
