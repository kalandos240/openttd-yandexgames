#!/usr/bin/env python3
"""Make the native browser tutorial readable and objective-driven.

Runs after the base tutorial/toolbar/level/polish patches. This stage fixes the
scaled layout, removes the harsh inherited blue text colour, and turns the road
and rail lessons into real game-state objectives. It also keeps all visible
text in OpenTTD language resources so Russian/English follow the selected game
language automatically.
"""
from pathlib import Path
import re


def replace_lang_line(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}\s*:.*$", re.M)
    replacement = f"{key:<64}:{value}"
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Could not replace language string {key} in {path}")
    path.write_text(text, encoding="utf-8")


def append_before(path: Path, marker: str, block: str, guard: str) -> None:
    text = path.read_text(encoding="utf-8")
    if guard in text:
        return
    if text.count(marker) != 1:
        raise SystemExit(f"Could not find unique language insertion marker in {path}")
    path.write_text(text.replace(marker, block.rstrip() + "\n" + marker, 1), encoding="utf-8")


english = Path("openttd/src/lang/english.txt")
russian = Path("openttd/src/lang/russian.txt")

replace_lang_line(
    english,
    "STR_BROWSER_TUTORIAL_COACH_HINT",
    "Complete the objective in the real game. Next unlocks when it is complete.",
)
replace_lang_line(
    russian,
    "STR_BROWSER_TUTORIAL_COACH_HINT",
    "Выполните задание прямо в игре. Кнопка «Далее» станет доступна после выполнения.",
)

append_before(
    english,
    "STR_BROWSER_MANUAL_CAPTION",
    """STR_BROWSER_TUTORIAL_OBJECTIVE_INFO                              :Practice this control, then continue when ready.
STR_BROWSER_TUTORIAL_OBJECTIVE_LOCKED                            :Objective not complete yet. Perform the highlighted action in the game.
STR_BROWSER_TUTORIAL_OBJECTIVE_DONE                              :Objective complete. You can continue.
""",
    "STR_BROWSER_TUTORIAL_OBJECTIVE_LOCKED",
)
append_before(
    russian,
    "STR_BROWSER_MANUAL_CAPTION",
    """STR_BROWSER_TUTORIAL_OBJECTIVE_INFO                              :Попробуйте этот элемент управления и продолжайте, когда будете готовы.
STR_BROWSER_TUTORIAL_OBJECTIVE_LOCKED                            :Задание ещё не выполнено. Выполните указанное действие в игре.
STR_BROWSER_TUTORIAL_OBJECTIVE_DONE                              :Задание выполнено. Можно продолжать.
""",
    "STR_BROWSER_TUTORIAL_OBJECTIVE_LOCKED",
)

english_steps = {
    10: "10/20 — Start the bus service{}Start the bus after giving it at least two station orders. The lesson checks the real vehicle: Next unlocks only when a road vehicle has two manual orders and is running.",
    11: "11/20 — Open railway construction{}Open the railway construction toolbar. We will now repeat the complete transport loop with trains: track, stations, depot, train, orders and a signal.",
    12: "12/20 — Build railway track{}Choose Autorail and build a useful stretch of track. Next unlocks only after your company has actually built new rail infrastructure on the practice map.",
    13: "13/20 — Build two rail stations{}Place one rail station at each end of the line. Make sure both stations are connected by your track and cover useful buildings or cargo producers.",
    14: "14/20 — Build a rail depot{}Build a rail depot connected to the line. The tutorial checks the map and will not continue until your company owns a real rail depot.",
    15: "15/20 — Buy a train{}Open the depot you built and buy a locomotive/train. Next unlocks after a real train owned by your company exists.",
    16: "16/20 — Train orders and signal{}Give the train at least two station orders, then place at least one signal on your railway. This demonstrates both route programming and safe shared-track control.",
}
russian_steps = {
    10: "10/20 — Запускаем автобус{}После двух остановок в заданиях запустите автобус. Обучение проверяет настоящую машину: «Далее» откроется только когда у автотранспорта есть минимум два ручных задания и он запущен.",
    11: "11/20 — Открываем строительство железных дорог{}Откройте панель железных дорог. Теперь повторим полный транспортный цикл с поездом: путь, станции, депо, поезд, задания и сигнал.",
    12: "12/20 — Строим железнодорожный путь{}Выберите «Авторельсы» и проложите полезный участок пути. «Далее» откроется только после того, как ваша компания действительно построит новые рельсы на учебной карте.",
    13: "13/20 — Строим две железнодорожные станции{}Поставьте по железнодорожной станции на каждом конце линии. Соедините их путём и постарайтесь охватить полезные здания или производителей груза.",
    14: "14/20 — Строим железнодорожное депо{}Поставьте депо, соединённое с линией. Обучение проверяет карту и не продолжится, пока у вашей компании не появится настоящее железнодорожное депо.",
    15: "15/20 — Покупаем поезд{}Откройте построенное депо и купите локомотив или поезд. «Далее» откроется после появления настоящего поезда вашей компании.",
    16: "16/20 — Задания поезда и сигнал{}Добавьте поезду минимум две станции в задания, затем поставьте хотя бы один сигнал на своей железной дороге. Так вы освоите маршрут и безопасное управление общим путём.",
}
for number, value in english_steps.items():
    replace_lang_line(english, f"STR_BROWSER_TUTORIAL_LEVEL_{number:02d}", value)
for number, value in russian_steps.items():
    replace_lang_line(russian, f"STR_BROWSER_TUTORIAL_LEVEL_{number:02d}", value)

intro_path = Path("openttd/src/intro_gui.cpp")
text = intro_path.read_text(encoding="utf-8")

include_anchor = '#include "widgets/road_widget.h"\n'
extra_includes = '''#include "widgets/road_widget.h"
#include "widgets/rail_widget.h"
#include "company_base.h"
#include "company_func.h"
#include "depot_base.h"
#include "vehicle_base.h"
#include "road_map.h"
#include "rail_map.h"
'''
if '#include "widgets/rail_widget.h"' not in text:
    if text.count(include_anchor) != 1:
        raise SystemExit("Could not add tutorial objective includes")
    text = text.replace(include_anchor, extra_includes, 1)

layout_replacements = {
    'SetMinimalSize(240, 28)': 'SetMinimalSize(190, 26)',
    'SetMinimalSize(220, 28)': 'SetMinimalSize(180, 26)',
    'SetMinimalSize(560, 210)': 'SetMinimalSize(500, 220)',
    'SetMinimalSize(150, 22)': 'SetMinimalSize(120, 26)',
    'static constexpr size_t BROWSER_GUIDE_ROWS = 6;': 'static constexpr size_t BROWSER_GUIDE_ROWS = 3;',
    'SetMinimalSize(680, 350)': 'SetMinimalSize(520, 190)',
    'SetMinimalSize(600, 190)': 'SetMinimalSize(520, 190)',
    'SetMinimalSize(140, 22)': 'SetMinimalSize(120, 26)',
}
for old, new in layout_replacements.items():
    if new in text:
        continue
    if old not in text:
        raise SystemExit(f"Could not find tutorial layout marker: {old}")
    text = text.replace(old, new)

text = text.replace(
    'DrawStringMultiLine(r.Shrink(WidgetDimensions::scaled.sparse), _browser_tutorial_steps[this->step], TC_FROMSTRING, SA_LEFT);',
    'DrawStringMultiLine(r.Shrink(WidgetDimensions::scaled.sparse), _browser_tutorial_steps[this->step], TC_BLACK, SA_LEFT);',
)
text = text.replace(
    'DrawStringMultiLine(text_rect, entry.description, TC_FROMSTRING, SA_LEFT);',
    'DrawStringMultiLine(text_rect, entry.description, TC_BLACK, SA_LEFT);',
)
text = text.replace(
    'DrawStringMultiLine(text_rect, current.text, TC_FROMSTRING, SA_LEFT);',
    'DrawStringMultiLine(text_rect, current.text, TC_BLACK, SA_LEFT);',
)

old_target_enum = '''enum class BrowserTutorialTarget : uint8_t {
\tNone,
\tMainToolbar,
\tRoadToolbar,
};

struct BrowserTutorialCoachStep {
\tStringID text;
\tSpriteID icon;
\tBrowserTutorialTarget target;
\tWidgetID widget;
};
'''
new_target_enum = '''enum class BrowserTutorialTarget : uint8_t {
\tNone,
\tMainToolbar,
\tRoadToolbar,
\tRailToolbar,
};

enum class BrowserTutorialObjective : uint8_t {
\tInformational,
\tSmallMapOpen,
\tRoadToolbarOpen,
\tRoadBuilt,
\tBusStationsBuilt,
\tRoadDepotBuilt,
\tRoadVehicleBought,
\tRoadOrdersSet,
\tRoadVehicleRunning,
\tRailToolbarOpen,
\tRailBuilt,
\tRailStationsBuilt,
\tRailDepotBuilt,
\tTrainBought,
\tTrainOrdersAndSignal,
\tStationListOpen,
\tSubsidiesOpen,
\tVehicleListOpen,
};

struct BrowserTutorialCoachStep {
\tStringID text;
\tSpriteID icon;
\tBrowserTutorialTarget target;
\tWidgetID widget;
\tBrowserTutorialObjective objective;
};
'''
if new_target_enum not in text:
    if text.count(old_target_enum) != 1:
        raise SystemExit("Could not upgrade tutorial target/objective enum")
    text = text.replace(old_target_enum, new_target_enum, 1)

array_pattern = re.compile(
    r'static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps\[\] = \{.*?\n\};',
    re.S,
)
new_array = '''static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps[] = {
\t{STR_BROWSER_TUTORIAL_LEVEL_01, SPR_IMG_ZOOMIN, BrowserTutorialTarget::MainToolbar, WID_TN_ZOOM_IN, BrowserTutorialObjective::Informational},
\t{STR_BROWSER_TUTORIAL_LEVEL_02, SPR_IMG_PAUSE, BrowserTutorialTarget::MainToolbar, WID_TN_PAUSE, BrowserTutorialObjective::Informational},
\t{STR_BROWSER_TUTORIAL_LEVEL_03, SPR_IMG_SMALLMAP, BrowserTutorialTarget::MainToolbar, WID_TN_SMALL_MAP, BrowserTutorialObjective::SmallMapOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_04, SPR_IMG_BUILDROAD, BrowserTutorialTarget::MainToolbar, WID_TN_ROADS, BrowserTutorialObjective::RoadToolbarOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_05, SPR_IMG_AUTOROAD, BrowserTutorialTarget::RoadToolbar, WID_ROT_AUTOROAD, BrowserTutorialObjective::RoadBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_06, SPR_IMG_BUS_STATION, BrowserTutorialTarget::RoadToolbar, WID_ROT_BUS_STATION, BrowserTutorialObjective::BusStationsBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_ROAD_DEPOT, BrowserTutorialTarget::RoadToolbar, WID_ROT_DEPOT, BrowserTutorialObjective::RoadDepotBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::RoadVehicleBought},
\t{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::RoadOrdersSet},
\t{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::RoadVehicleRunning},
\t{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailToolbarOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_AUTORAIL, BrowserTutorialObjective::RailBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_STATION, BrowserTutorialObjective::RailStationsBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_14, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_DEPOT, BrowserTutorialObjective::RailDepotBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_TRAINLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::TrainBought},
\t{STR_BROWSER_TUTORIAL_LEVEL_16, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_SIGNALS, BrowserTutorialObjective::TrainOrdersAndSignal},
\t{STR_BROWSER_TUTORIAL_LEVEL_17, SPR_IMG_COMPANY_LIST, BrowserTutorialTarget::MainToolbar, WID_TN_STATIONS, BrowserTutorialObjective::StationListOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_18, SPR_IMG_SUBSIDIES, BrowserTutorialTarget::MainToolbar, WID_TN_SUBSIDIES, BrowserTutorialObjective::SubsidiesOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_19, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::VehicleListOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_QUERY, BrowserTutorialTarget::MainToolbar, WID_TN_HELP, BrowserTutorialObjective::Informational},
};'''
text, array_count = array_pattern.subn(new_array, text, count=1)
if array_count != 1:
    raise SystemExit(f"Could not replace tutorial step array: {array_count}")

old_active = '''static bool _browser_tutorial_pending = false;
static bool _browser_tutorial_active = false;
'''
new_active = '''struct BrowserTutorialProgressSnapshot {
\tuint32_t road = 0;
\tuint32_t rail = 0;
\tuint32_t stations = 0;
\tuint32_t signals = 0;
\tuint32_t road_depots = 0;
\tuint32_t rail_depots = 0;
\tuint32_t road_vehicles = 0;
\tuint32_t trains = 0;
};

static bool _browser_tutorial_pending = false;
static bool _browser_tutorial_active = false;
static BrowserTutorialProgressSnapshot _browser_tutorial_origin{};

static BrowserTutorialProgressSnapshot BrowserTutorialGetSnapshot()
{
\tBrowserTutorialProgressSnapshot result{};
\tif (const Company *company = Company::GetIfValid(_local_company); company != nullptr) {
\t\tresult.road = company->infrastructure.GetRoadTotal();
\t\tresult.rail = company->infrastructure.GetRailTotal();
\t\tresult.stations = company->infrastructure.station;
\t\tresult.signals = company->infrastructure.signal;
\t}

\tfor (const Depot *depot : Depot::Iterate()) {
\t\tif (depot->xy == INVALID_TILE || GetTileOwner(depot->xy) != _local_company) continue;
\t\tif (IsRoadDepotTile(depot->xy)) ++result.road_depots;
\t\tif (IsRailDepotTile(depot->xy)) ++result.rail_depots;
\t}

\tfor (const Vehicle *vehicle : Vehicle::Iterate()) {
\t\tif (vehicle->owner != _local_company || !vehicle->IsPrimaryVehicle()) continue;
\t\tif (vehicle->type == VEH_ROAD) ++result.road_vehicles;
\t\tif (vehicle->type == VEH_TRAIN) ++result.trains;
\t}
\treturn result;
}

static bool BrowserTutorialHasOrders(VehicleType type, bool require_running)
{
\tfor (const Vehicle *vehicle : Vehicle::Iterate()) {
\t\tif (vehicle->owner != _local_company || !vehicle->IsPrimaryVehicle() || vehicle->type != type) continue;
\t\tif (vehicle->GetNumManualOrders() < 2) continue;
\t\tif (require_running && vehicle->vehstatus.Test(VehState::Stopped)) continue;
\t\treturn true;
\t}
\treturn false;
}

static bool BrowserTutorialObjectiveComplete(BrowserTutorialObjective objective)
{
\tconst BrowserTutorialProgressSnapshot now = BrowserTutorialGetSnapshot();
\tswitch (objective) {
\t\tcase BrowserTutorialObjective::Informational: return true;
\t\tcase BrowserTutorialObjective::SmallMapOpen: return FindWindowByClass(WC_SMALLMAP) != nullptr;
\t\tcase BrowserTutorialObjective::RoadToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD) != nullptr;
\t\tcase BrowserTutorialObjective::RoadBuilt: return now.road >= _browser_tutorial_origin.road + 6;
\t\tcase BrowserTutorialObjective::BusStationsBuilt: return now.stations >= _browser_tutorial_origin.stations + 2;
\t\tcase BrowserTutorialObjective::RoadDepotBuilt: return now.road_depots > _browser_tutorial_origin.road_depots;
\t\tcase BrowserTutorialObjective::RoadVehicleBought: return now.road_vehicles > _browser_tutorial_origin.road_vehicles;
\t\tcase BrowserTutorialObjective::RoadOrdersSet: return BrowserTutorialHasOrders(VEH_ROAD, false);
\t\tcase BrowserTutorialObjective::RoadVehicleRunning: return BrowserTutorialHasOrders(VEH_ROAD, true);
\t\tcase BrowserTutorialObjective::RailToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL) != nullptr;
\t\tcase BrowserTutorialObjective::RailBuilt: return now.rail >= _browser_tutorial_origin.rail + 6;
\t\tcase BrowserTutorialObjective::RailStationsBuilt: return now.stations >= _browser_tutorial_origin.stations + 4;
\t\tcase BrowserTutorialObjective::RailDepotBuilt: return now.rail_depots > _browser_tutorial_origin.rail_depots;
\t\tcase BrowserTutorialObjective::TrainBought: return now.trains > _browser_tutorial_origin.trains;
\t\tcase BrowserTutorialObjective::TrainOrdersAndSignal:
\t\t\treturn now.signals > _browser_tutorial_origin.signals && BrowserTutorialHasOrders(VEH_TRAIN, false);
\t\tcase BrowserTutorialObjective::StationListOpen: return FindWindowByClass(WC_STATION_LIST) != nullptr;
\t\tcase BrowserTutorialObjective::SubsidiesOpen: return FindWindowByClass(WC_SUBSIDIES_LIST) != nullptr;
\t\tcase BrowserTutorialObjective::VehicleListOpen:
\t\t\treturn FindWindowByClass(WC_ROADVEH_LIST) != nullptr || FindWindowByClass(WC_TRAINS_LIST) != nullptr;
\t}
\treturn false;
}
'''
if new_active not in text:
    if text.count(old_active) != 1:
        raise SystemExit("Could not install tutorial game-state trackers")
    text = text.replace(old_active, new_active, 1)

old_target_window = '''static Window *BrowserTutorialTargetWindow(BrowserTutorialTarget target)
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
}
'''
new_target_window = '''static Window *BrowserTutorialTargetWindow(BrowserTutorialTarget target)
{
\tswitch (target) {
\t\tcase BrowserTutorialTarget::MainToolbar: return FindWindowById(WC_MAIN_TOOLBAR, 0);
\t\tcase BrowserTutorialTarget::RoadToolbar: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD);
\t\tcase BrowserTutorialTarget::RailToolbar: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL);
\t\tdefault: return nullptr;
\t}
}

static void BrowserTutorialClearHighlights()
{
\tif (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL); w != nullptr) w->DisableAllWidgetHighlight();
}
'''
if new_target_window not in text:
    if text.count(old_target_window) != 1:
        raise SystemExit("Could not make road/rail highlight targeting deterministic")
    text = text.replace(old_target_window, new_target_window, 1)

coach_pattern = re.compile(
    r'struct BrowserTutorialCoachWindow final : Window \{.*?\n\};\n\nvoid StartBrowserTutorialLevel\(\)',
    re.S,
)
new_coach = r'''struct BrowserTutorialCoachWindow final : Window {
\tsize_t step = 0;
\tbool objective_complete = false;

\tBrowserTutorialCoachWindow() : Window(_browser_tutorial_coach_desc)
\t{
\t\tthis->InitNested(0);
\t\tthis->UpdateStep();
\t}

\tvoid Close([[maybe_unused]] int data = 0) override
\t{
\t\tBrowserTutorialClearHighlights();
\t\t_browser_tutorial_active = false;
\t\tthis->Window::Close();
\t}

\tvoid UpdateObjectiveState()
\t{
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tthis->objective_complete = BrowserTutorialObjectiveComplete(current.objective);
\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !this->objective_complete);
\t}

\tvoid UpdateStep()
\t{
\t\tBrowserTutorialClearHighlights();
\t\tthis->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);
\t\tthis->UpdateObjectiveState();
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\ttarget->SetWidgetHighlight(current.widget, TC_YELLOW);
\t\t}
\t\tthis->SetDirty();
\t}

\tvoid OnRealtimeTick([[maybe_unused]] uint delta_ms) override
\t{
\t\tconst bool was_complete = this->objective_complete;
\t\tthis->UpdateObjectiveState();
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\tif (!target->IsWidgetHighlighted(current.widget)) target->SetWidgetHighlight(current.widget, TC_YELLOW);
\t\t}
\t\tif (was_complete != this->objective_complete) this->SetDirty();
\t}

\tvoid DrawWidget(const Rect &r, WidgetID widget) const override
\t{
\t\tif (widget != WID_BTC_CONTENT) return;
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tRect body = r.Shrink(WidgetDimensions::scaled.sparse);
\t\tDrawSprite(current.icon, PAL_NONE, body.left + 12, body.top + 16);
\t\tRect text_rect{body.left + 58, body.top + 4, body.right, body.bottom - 58};
\t\tDrawStringMultiLine(text_rect, current.text, TC_BLACK, SA_LEFT);

\t\tconst StringID status = current.objective == BrowserTutorialObjective::Informational
\t\t\t? STR_BROWSER_TUTORIAL_OBJECTIVE_INFO
\t\t\t: (this->objective_complete ? STR_BROWSER_TUTORIAL_OBJECTIVE_DONE : STR_BROWSER_TUTORIAL_OBJECTIVE_LOCKED);
\t\tRect hint_rect{body.left + 58, body.bottom - 52, body.right, body.bottom};
\t\tDrawStringMultiLine(hint_rect, status, TC_WHITE, SA_LEFT);

\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\tconst NWidgetBase *target_widget = target->GetWidget<NWidgetBase>(current.widget);
\t\t\tif (target_widget != nullptr) {
\t\t\t\tRect target_rect = target_widget->GetCurrentRect();
\t\t\t\tconst int tx = target->left + (target_rect.left + target_rect.right) / 2;
\t\t\t\tconst int ty = target->top + (target_rect.top + target_rect.bottom) / 2;
\t\t\t\tconst int cx = this->left + (body.left + body.right) / 2;
\t\t\t\tconst int cy = this->top + (body.top + body.bottom) / 2;
\t\t\t\tSpriteID arrow = SPR_ARROW_UP;
\t\t\t\tif (std::abs(tx - cx) > std::abs(ty - cy)) arrow = tx < cx ? SPR_ARROW_LEFT : SPR_ARROW_RIGHT;
\t\t\t\telse arrow = ty < cy ? SPR_ARROW_UP : SPR_ARROW_DOWN;
\t\t\t\tDrawSprite(arrow, PAL_NONE, body.left + 20, body.bottom - 35);
\t\t\t}
\t\t}
\t}

\tvoid OnClick([[maybe_unused]] Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
\t{
\t\tif (widget == WID_BTC_PREVIOUS && this->step > 0) {
\t\t\t--this->step;
\t\t\tthis->UpdateStep();
\t\t\treturn;
\t\t}
\t\tif (widget == WID_BTC_NEXT) {
\t\t\tthis->UpdateObjectiveState();
\t\t\tif (!this->objective_complete) return;
\t\t\tif (this->step + 1 < std::size(_browser_tutorial_level_steps)) {
\t\t\t\t++this->step;
\t\t\t\tthis->UpdateStep();
\t\t\t} else {
\t\t\t\tthis->Close();
\t\t\t}
\t\t}
\t}
};

void StartBrowserTutorialLevel()'''
text, coach_count = coach_pattern.subn(new_coach, text, count=1)
if coach_count != 1:
    raise SystemExit(f"Could not replace tutorial coach window: {coach_count}")

started_old = '''\t_browser_tutorial_pending = false;
\t_browser_tutorial_active = true;
\tCloseWindowByClass(WC_HELPWIN);
'''
started_new = '''\t_browser_tutorial_pending = false;
\t_browser_tutorial_active = true;
\t_browser_tutorial_origin = BrowserTutorialGetSnapshot();
\tCloseWindowByClass(WC_HELPWIN);
'''
if started_new not in text:
    if text.count(started_old) != 1:
        raise SystemExit("Could not capture tutorial origin state")
    text = text.replace(started_old, started_new, 1)

required_markers = (
    'BrowserTutorialObjective::RoadBuilt',
    'BrowserTutorialObjective::RailBuilt',
    'BrowserTutorialObjective::TrainOrdersAndSignal',
    'vehicle->GetNumManualOrders() < 2',
    'vehicle->vehstatus.Test(VehState::Stopped)',
    'IsRoadDepotTile(depot->xy)',
    'IsRailDepotTile(depot->xy)',
    'SetWidgetDisabledState(WID_BTC_NEXT, !this->objective_complete)',
    'DrawStringMultiLine(text_rect, current.text, TC_BLACK, SA_LEFT)',
    'DrawStringMultiLine(hint_rect, status, TC_WHITE, SA_LEFT)',
    'static constexpr size_t BROWSER_GUIDE_ROWS = 3;',
    'BrowserTutorialTarget::RailToolbar',
)
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"Missing tutorial-quality marker: {marker}")

intro_path.write_text(text, encoding="utf-8")
print("Tutorial quality patch applied: compact layout, readable colours, real road/rail objectives.")
