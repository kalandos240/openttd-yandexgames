#!/usr/bin/env python3
"""Guide practical tutorial steps through the actual open OpenTTD windows.

Runs after the final UX pass. The coach first highlights the concrete action in
an open depot/build-vehicle/vehicle/orders window. If that window is not open,
the existing toolbar target remains the visible fallback.
"""
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Could not find unique {label}: {count}")
    return text.replace(old, new, 1)


path = Path("openttd/src/intro_gui.cpp")
text = path.read_text(encoding="utf-8")

include_anchor = '#include "widgets/rail_widget.h"\n'
extra_headers = '''#include "widgets/rail_widget.h"
#include "widgets/depot_widget.h"
#include "widgets/build_vehicle_widget.h"
#include "widgets/vehicle_widget.h"
#include "widgets/order_widget.h"
'''
if '#include "widgets/depot_widget.h"' not in text:
    text = replace_once(text, include_anchor, extra_headers, "tutorial action widget includes")

old_clear = '''static void BrowserTutorialClearHighlights()
{
\tif (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL); w != nullptr) w->DisableAllWidgetHighlight();
}
'''
new_clear = '''static void BrowserTutorialClearHighlights()
{
\tfor (Window *w : Window::Iterate()) {
\t\tswitch (w->window_class) {
\t\t\tcase WC_MAIN_TOOLBAR:
\t\t\tcase WC_BUILD_TOOLBAR:
\t\t\tcase WC_VEHICLE_DEPOT:
\t\t\tcase WC_BUILD_VEHICLE:
\t\t\tcase WC_VEHICLE_VIEW:
\t\t\tcase WC_VEHICLE_ORDERS:
\t\t\t\tw->DisableAllWidgetHighlight();
\t\t\t\tbreak;
\t\t\tdefault:
\t\t\t\tbreak;
\t\t}
\t}
}
'''
text = replace_once(text, old_clear, new_clear, "expanded tutorial highlight clearing")

old_resolver = '''static Window *BrowserTutorialResolveTarget(const BrowserTutorialCoachStep &step, WidgetID &widget)
{
\twidget = step.widget;
\tif (Window *target = BrowserTutorialTargetWindow(step.target); target != nullptr && widget != INVALID_WIDGET) return target;

\tWindow *main = FindWindowById(WC_MAIN_TOOLBAR, 0);
\tif (main == nullptr) return nullptr;
\tif (step.target == BrowserTutorialTarget::RoadToolbar) {
\t\twidget = WID_TN_ROADS;
\t\treturn main;
\t}
\tif (step.target == BrowserTutorialTarget::RailToolbar) {
\t\twidget = WID_TN_RAILS;
\t\treturn main;
\t}
\treturn nullptr;
}
'''
new_resolver = '''static Window *BrowserTutorialResolveTarget(const BrowserTutorialCoachStep &step, WidgetID &widget)
{
\t/* Purchase lessons: follow the player from depot -> vehicle catalogue -> Buy. */
\tif (step.objective == BrowserTutorialObjective::RoadVehicleBought ||
\t\t\tstep.objective == BrowserTutorialObjective::TrainBought) {
\t\tif (Window *build = FindWindowByClass(WC_BUILD_VEHICLE); build != nullptr) {
\t\t\twidget = WID_BV_BUILD_SEL;
\t\t\treturn build;
\t\t}
\t\tif (Window *depot = FindWindowByClass(WC_VEHICLE_DEPOT); depot != nullptr) {
\t\t\twidget = WID_D_BUILD;
\t\t\treturn depot;
\t\t}
\t}

\t/* Orders lessons: once a vehicle window is open, point at Orders; once the
\t   orders window is open, point at Go To so the stations can be selected. */
\tconst bool road_orders = step.objective == BrowserTutorialObjective::RoadOrdersSet;
\tconst bool train_orders = step.objective == BrowserTutorialObjective::TrainOrdersAndSignal &&
\t\t\t!BrowserTutorialHasOrders(VEH_TRAIN, false);
\tif (road_orders || train_orders) {
\t\tif (Window *orders = FindWindowByClass(WC_VEHICLE_ORDERS); orders != nullptr) {
\t\t\twidget = WID_O_GOTO;
\t\t\treturn orders;
\t\t}
\t\tif (Window *vehicle = FindWindowByClass(WC_VEHICLE_VIEW); vehicle != nullptr) {
\t\t\twidget = WID_VV_SHOW_ORDERS;
\t\t\treturn vehicle;
\t\t}
\t}

\t/* Starting the bus is a concrete button in the vehicle view. */
\tif (step.objective == BrowserTutorialObjective::RoadVehicleRunning) {
\t\tif (Window *vehicle = FindWindowByClass(WC_VEHICLE_VIEW); vehicle != nullptr) {
\t\t\twidget = WID_VV_START_STOP;
\t\t\treturn vehicle;
\t\t}
\t}

\twidget = step.widget;
\tif (Window *target = BrowserTutorialTargetWindow(step.target); target != nullptr && widget != INVALID_WIDGET) return target;

\t/* Construction toolbars are transient. If one was closed, blink the always
\t   visible top-toolbar button that reopens the required tool set. */
\tWindow *main = FindWindowById(WC_MAIN_TOOLBAR, 0);
\tif (main == nullptr) return nullptr;
\tif (step.target == BrowserTutorialTarget::RoadToolbar) {
\t\twidget = WID_TN_ROADS;
\t\treturn main;
\t}
\tif (step.target == BrowserTutorialTarget::RailToolbar) {
\t\twidget = WID_TN_RAILS;
\t\treturn main;
\t}
\treturn nullptr;
}
'''
text = replace_once(text, old_resolver, new_resolver, "dynamic tutorial target resolver")

required = (
    '#include "widgets/depot_widget.h"',
    'WID_BV_BUILD_SEL',
    'WID_D_BUILD',
    'WID_VV_SHOW_ORDERS',
    'WID_O_GOTO',
    'WID_VV_START_STOP',
    'BrowserTutorialHasOrders(VEH_TRAIN, false)',
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"Missing dynamic tutorial guidance marker: {marker}")

path.write_text(text, encoding="utf-8")
print("Tutorial action guidance patched: depot, buy, orders and start controls now follow the active window.")
