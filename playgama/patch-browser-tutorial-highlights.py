#!/usr/bin/env python3
"""Make every actionable browser tutorial step keep a useful native highlight.

Runs after the real-objective/clean-UI tutorial patches. Construction steps use
transport-specific toolbars when they are open and fall back to the matching
main-toolbar button while the child toolbar is closed.
"""
from pathlib import Path
import re


p = Path("openttd/src/intro_gui.cpp")
s = p.read_text(encoding="utf-8")

# Add public widget IDs for the child construction toolbars.
include_anchor = '#include "widgets/road_widget.h"\n'
if '#include "widgets/rail_widget.h"' not in s:
    if include_anchor not in s:
        raise SystemExit("tutorial road widget include anchor missing")
    s = s.replace(
        include_anchor,
        include_anchor
        + '#include "widgets/rail_widget.h"\n'
        + '#include "widgets/dock_widget.h"\n'
        + '#include "widgets/airport_widget.h"\n',
        1,
    )

# Earlier tutorial passes may format this enum on one line or many lines. Match
# the semantic block rather than one historical formatting variant.
enum_re = re.compile(r"enum class BrowserTutorialTarget\s*:\s*uint8_t\s*\{[^}]*\};", re.S)
m = enum_re.search(s)
if not m:
    raise SystemExit("tutorial target enum missing")
old_enum = m.group(0)
for required in ("None", "MainToolbar", "RoadToolbar"):
    if required not in old_enum:
        raise SystemExit(f"tutorial target enum lost required value: {required}")
new_enum = """enum class BrowserTutorialTarget : uint8_t {
\tNone,
\tMainToolbar,
\tRoadToolbar,
\tRailToolbar,
\tWaterToolbar,
\tAirToolbar,
};"""
s = s[:m.start()] + new_enum + s[m.end():]

# Replace the old generic WC_BUILD_TOOLBAR resolver. This fixes two problems at
# once: road highlighting can no longer land on another transport toolbar, and
# rail/water/air steps can point at their actual tool once the child toolbar is
# open. Until then the corresponding main-toolbar button remains highlighted.
target_re = re.compile(
    r"static Window \*BrowserTutorialTargetWindow\(BrowserTutorialTarget target\)\s*\{.*?\n\}",
    re.S,
)
m = target_re.search(s)
if not m:
    raise SystemExit("legacy tutorial target resolver missing")
new_target = """struct BrowserTutorialResolvedTarget {
\tWindow *window;
\tWidgetID widget;
};

static BrowserTutorialResolvedTarget BrowserTutorialResolveTarget(BrowserTutorialTarget target, WidgetID widget)
{
\tWindow *main = FindWindowById(WC_MAIN_TOOLBAR, 0);
\tswitch (target) {
\t\tcase BrowserTutorialTarget::MainToolbar:
\t\t\treturn {main, widget};
\t\tcase BrowserTutorialTarget::RoadToolbar:
\t\t\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD); w != nullptr) return {w, widget};
\t\t\treturn {main, WID_TN_ROADS};
\t\tcase BrowserTutorialTarget::RailToolbar:
\t\t\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL); w != nullptr) return {w, widget};
\t\t\treturn {main, WID_TN_RAILS};
\t\tcase BrowserTutorialTarget::WaterToolbar:
\t\t\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_WATER); w != nullptr) return {w, widget};
\t\t\treturn {main, WID_TN_WATER};
\t\tcase BrowserTutorialTarget::AirToolbar:
\t\t\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_AIR); w != nullptr) return {w, widget};
\t\t\treturn {main, WID_TN_AIR};
\t\tdefault:
\t\t\treturn {nullptr, INVALID_WIDGET};
\t}
}"""
s = s[:m.start()] + new_target + s[m.end():]

clear_re = re.compile(r"static void BrowserTutorialClearHighlights\(\)\s*\{.*?\n\}", re.S)
m = clear_re.search(s)
if not m:
    raise SystemExit("tutorial clear-highlights function missing")
new_clear = """static void BrowserTutorialClearHighlights()
{
\tif (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_WATER); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_AIR); w != nullptr) w->DisableAllWidgetHighlight();
}"""
s = s[:m.start()] + new_clear + s[m.end():]

# The final objective pass inserts Next-button gating between `current` and the
# highlight. Preserve that gating and replace only the highlight statement.
block_re = re.compile(
    r"(?P<indent>\t\t)if \(Window \*target = BrowserTutorialTargetWindow\(current\.target\); "
    r"target != nullptr && current\.widget != INVALID_WIDGET\) \{\s*"
    r"(?:if \(!target->IsWidgetHighlighted\(current\.widget\)\) )?"
    r"target->SetWidgetHighlight\(current\.widget, TC_(?:WHITE|YELLOW)\);\s*\}",
    re.S,
)
inline_re = re.compile(
    r"(?P<indent>\t\t)if \(Window \*target = BrowserTutorialTargetWindow\(current\.target\); "
    r"target != nullptr && current\.widget != INVALID_WIDGET\) "
    r"target->SetWidgetHighlight\(current\.widget, TC_(?:WHITE|YELLOW)\);"
)

replacement_update = """\t\tconst auto target = BrowserTutorialResolveTarget(current.target, current.widget);
\t\tif (target.window != nullptr && target.widget != INVALID_WIDGET) {
\t\t\ttarget.window->SetWidgetHighlight(target.widget, TC_WHITE);
\t\t}"""
replacement_tick = """\t\tconst auto target = BrowserTutorialResolveTarget(current.target, current.widget);
\t\tif (target.window != nullptr && target.widget != INVALID_WIDGET) {
\t\t\tif (!target.window->IsWidgetHighlighted(target.widget)) target.window->SetWidgetHighlight(target.widget, TC_WHITE);
\t\t}"""

# Work inside the two methods so we cannot accidentally alter unrelated code.
def replace_method_highlight(text: str, method: str, replacement: str) -> str:
    start = text.find(method)
    if start < 0:
        raise SystemExit(f"tutorial method missing: {method}")
    next_method = text.find("\n\tvoid ", start + len(method))
    if next_method < 0:
        next_method = text.find("\n};", start + len(method))
    if next_method < 0:
        raise SystemExit(f"tutorial method end missing: {method}")
    chunk = text[start:next_method]
    chunk2, n = block_re.subn(replacement, chunk, count=1)
    if n == 0:
        chunk2, n = inline_re.subn(replacement, chunk, count=1)
    if n != 1:
        raise SystemExit(f"tutorial highlight call missing/ambiguous in: {method}")
    return text[:start] + chunk2 + text[next_method:]

s = replace_method_highlight(s, "\tvoid UpdateStep()", replacement_update)
s = replace_method_highlight(s, "\tvoid OnRealtimeTick(", replacement_tick)

# Map objective steps to the concrete tool that performs the required action.
# Keep FirstDelivery on a useful, always-addressable main-toolbar control rather
# than the historical None/INVALID_WIDGET hole.
step_replacements = {
    r"(STR_BROWSER_TUTORIAL_LEVEL_07,\s*SPR_IMG_TRUCKLIST,\s*)BrowserTutorialTarget::MainToolbar,\s*WID_TN_ROADVEHS":
        r"\1BrowserTutorialTarget::RoadToolbar, WID_ROT_DEPOT",
    r"(STR_BROWSER_TUTORIAL_LEVEL_08,\s*SPR_IMG_TRUCKLIST,\s*)BrowserTutorialTarget::None,\s*INVALID_WIDGET":
        r"\1BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS",
    r"(STR_BROWSER_TUTORIAL_LEVEL_11,\s*SPR_IMG_BUILDRAIL,\s*)BrowserTutorialTarget::MainToolbar,\s*WID_TN_RAILS":
        r"\1BrowserTutorialTarget::RailToolbar, WID_RAT_AUTORAIL",
    r"(STR_BROWSER_TUTORIAL_LEVEL_12,\s*SPR_IMG_BUILDRAIL,\s*)BrowserTutorialTarget::MainToolbar,\s*WID_TN_RAILS":
        r"\1BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_STATION",
    r"(STR_BROWSER_TUTORIAL_LEVEL_13,\s*SPR_IMG_BUILDRAIL,\s*)BrowserTutorialTarget::MainToolbar,\s*WID_TN_RAILS":
        r"\1BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_SIGNALS",
    r"(STR_BROWSER_TUTORIAL_LEVEL_20,\s*SPR_IMG_BUILDWATER,\s*)BrowserTutorialTarget::MainToolbar,\s*WID_TN_WATER":
        r"\1BrowserTutorialTarget::WaterToolbar, WID_DT_STATION",
    r"(STR_BROWSER_TUTORIAL_LEVEL_23,\s*SPR_IMG_BUILDAIR,\s*)BrowserTutorialTarget::MainToolbar,\s*WID_TN_AIR":
        r"\1BrowserTutorialTarget::AirToolbar, WID_AT_AIRPORT",
}
for pattern, replacement in step_replacements.items():
    s2, n = re.subn(pattern, replacement, s, count=1)
    if n != 1:
        raise SystemExit(f"tutorial step mapping missing: {pattern}")
    s = s2

required = (
    "BrowserTutorialResolveTarget",
    "BrowserTutorialTarget::RailToolbar",
    "BrowserTutorialTarget::WaterToolbar",
    "BrowserTutorialTarget::AirToolbar",
    "WID_RAT_AUTORAIL",
    "WID_RAT_BUILD_STATION",
    "WID_RAT_BUILD_SIGNALS",
    "WID_DT_STATION",
    "WID_AT_AIRPORT",
    "BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::FirstDelivery",
)
for marker in required:
    if marker not in s:
        raise SystemExit(f"tutorial highlight marker missing after patch: {marker}")

if "BrowserTutorialTargetWindow(" in s:
    raise SystemExit("legacy tutorial target resolver remains")

p.write_text(s, encoding="utf-8")
print("Tutorial highlights hardened: child toolbars + parent fallback + no empty actionable step.")
