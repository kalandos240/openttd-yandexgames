#!/usr/bin/env python3
"""Make every actionable browser tutorial step keep a useful native highlight.

Runs after the real-objective/clean-UI tutorial patches. Construction steps use
transport-specific toolbars when they are open and fall back to the matching
main-toolbar button while the child toolbar is closed.
"""
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


p = Path("openttd/src/intro_gui.cpp")
s = p.read_text(encoding="utf-8")

include_anchor = '#include "widgets/road_widget.h"\n'
extra_includes = (
    '#include "widgets/road_widget.h"\n'
    '#include "widgets/rail_widget.h"\n'
    '#include "widgets/dock_widget.h"\n'
    '#include "widgets/airport_widget.h"\n'
)
if '#include "widgets/rail_widget.h"' not in s:
    s = replace_once(s, include_anchor, extra_includes, "tutorial transport widget includes")

old_enum = """enum class BrowserTutorialTarget : uint8_t {
\tNone,
\tMainToolbar,
\tRoadToolbar,
};"""
new_enum = """enum class BrowserTutorialTarget : uint8_t {
\tNone,
\tMainToolbar,
\tRoadToolbar,
\tRailToolbar,
\tWaterToolbar,
\tAirToolbar,
};"""
s = replace_once(s, old_enum, new_enum, "tutorial target enum")

old_target = """static Window *BrowserTutorialTargetWindow(BrowserTutorialTarget target)
{
\tswitch (target) {
\t\tcase BrowserTutorialTarget::MainToolbar: return FindWindowById(WC_MAIN_TOOLBAR, 0);
\t\tcase BrowserTutorialTarget::RoadToolbar: return FindWindowByClass(WC_BUILD_TOOLBAR);
\t\tdefault: return nullptr;
\t}
}

static void BrowserTutorialClearHighlights()
{
\tif (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowByClass(WC_BUILD_TOOLBAR); w != nullptr) w->DisableAllWidgetHighlight();
}"""
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
}

static void BrowserTutorialClearHighlights()
{
\tif (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_WATER); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_AIR); w != nullptr) w->DisableAllWidgetHighlight();
}"""
s = replace_once(s, old_target, new_target, "tutorial target resolver")

old_update = """\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\ttarget->SetWidgetHighlight(current.widget, TC_WHITE);
\t\t}
\t\tthis->SetDirty();"""
new_update = """\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tconst auto target = BrowserTutorialResolveTarget(current.target, current.widget);
\t\tif (target.window != nullptr && target.widget != INVALID_WIDGET) {
\t\t\ttarget.window->SetWidgetHighlight(target.widget, TC_WHITE);
\t\t}
\t\tthis->SetDirty();"""
s = replace_once(s, old_update, new_update, "tutorial UpdateStep highlight")

old_tick = """\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\tif (!target->IsWidgetHighlighted(current.widget)) target->SetWidgetHighlight(current.widget, TC_WHITE);
\t\t}
\t\tthis->SetDirty();"""
new_tick = """\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tconst auto target = BrowserTutorialResolveTarget(current.target, current.widget);
\t\tif (target.window != nullptr && target.widget != INVALID_WIDGET) {
\t\t\tif (!target.window->IsWidgetHighlighted(target.widget)) target.window->SetWidgetHighlight(target.widget, TC_WHITE);
\t\t}
\t\tthis->SetDirty();"""
s = replace_once(s, old_tick, new_tick, "tutorial realtime highlight")

old_draw = """\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\tconst NWidgetBase *target_widget = target->GetWidget<NWidgetBase>(current.widget);
\t\t\tif (target_widget != nullptr) {
\t\t\t\tRect target_rect = target_widget->GetCurrentRect();
\t\t\t\tconst int tx = target->left + (target_rect.left + target_rect.right) / 2;
\t\t\t\tconst int ty = target->top + (target_rect.top + target_rect.bottom) / 2;"""
new_draw = """\t\tconst auto target = BrowserTutorialResolveTarget(current.target, current.widget);
\t\tif (target.window != nullptr && target.widget != INVALID_WIDGET) {
\t\t\tconst NWidgetBase *target_widget = target.window->GetWidget<NWidgetBase>(target.widget);
\t\t\tif (target_widget != nullptr) {
\t\t\t\tRect target_rect = target_widget->GetCurrentRect();
\t\t\t\tconst int tx = target.window->left + (target_rect.left + target_rect.right) / 2;
\t\t\t\tconst int ty = target.window->top + (target_rect.top + target_rect.bottom) / 2;"""
s = replace_once(s, old_draw, new_draw, "tutorial coach arrow target")

replacements = {
    "\t{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicle},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_ROAD_DEPOT, BrowserTutorialTarget::RoadToolbar, WID_ROT_DEPOT, BrowserTutorialObjective::RoadVehicle},",

    "\t{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::FirstDelivery},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::FirstDelivery},",

    "\t{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailBuilt},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_AUTORAIL, BrowserTutorialObjective::RailBuilt},",

    "\t{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailStations2},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_STATION, BrowserTutorialObjective::RailStations2},",

    "\t{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::SignalBuilt},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_SIGNALS, BrowserTutorialObjective::SignalBuilt},",

    "\t{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER, BrowserTutorialObjective::Docks2},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_BUILDWATER, BrowserTutorialTarget::WaterToolbar, WID_DT_STATION, BrowserTutorialObjective::Docks2},",

    "\t{STR_BROWSER_TUTORIAL_LEVEL_23, SPR_IMG_BUILDAIR, BrowserTutorialTarget::MainToolbar, WID_TN_AIR, BrowserTutorialObjective::Airports2},":
    "\t{STR_BROWSER_TUTORIAL_LEVEL_23, SPR_IMG_BUILDAIR, BrowserTutorialTarget::AirToolbar, WID_AT_AIRPORT, BrowserTutorialObjective::Airports2},",
}
for old, new in replacements.items():
    s = replace_once(s, old, new, f"tutorial step mapping {old.split(',')[0].strip()}")

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
)
for marker in required:
    if marker not in s:
        raise SystemExit(f"tutorial highlight marker missing after patch: {marker}")

if "BrowserTutorialTargetWindow(" in s:
    raise SystemExit("legacy tutorial target resolver remains")

p.write_text(s, encoding="utf-8")
print("Tutorial highlights hardened: child toolbars + parent fallback + no empty actionable step.")
