#!/usr/bin/env python3
"""Final browser tutorial v2: compact single-window UX and a full transport course.

This pass runs after all legacy tutorial patches. It deliberately replaces the
final generated lesson model instead of adding more incremental sizing hacks.
The practice course covers road, rail, freight/industry chains, ships,
aircraft and town growth on one deterministic, compact training world.
"""
from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Could not find unique {label}: {count}")
    return text.replace(old, new, 1)


def replace_lang_line(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    replacement = f"{key:<64}:{value}"
    pattern = re.compile(rf"^{re.escape(key)}\s*:.*$", re.M)
    text, count = pattern.subn(replacement, text, count=1)
    if count == 0:
        # New v2 lesson ids are appended immediately before the browser manual.
        marker = "STR_BROWSER_MANUAL_CAPTION"
        if marker not in text:
            raise SystemExit(f"Could not append {key} to {path}")
        text = text.replace(marker, replacement + "\n" + marker, 1)
    elif count != 1:
        raise SystemExit(f"Multiple language ids {key} in {path}")
    path.write_text(text, encoding="utf-8")


english_steps = {
    1: "1/32 — Camera and zoom{}Move the map with the right mouse button. Zoom with the wheel or the highlighted controls. This small map is your dedicated practice world.",
    2: "2/32 — Pause and speed{}Pause when planning and use fast-forward while waiting for vehicles. Learn these two controls before building anything.",
    3: "3/32 — Read the map{}Open the small map. Towns create passengers and mail; industries create and consume resources. Transport is about connecting those flows.",
    4: "4/32 — Open road construction{}Open the road toolbar. We will first build a complete passenger service from infrastructure to a running vehicle.",
    5: "5/32 — Build a road{}Use Autoroad and build at least six road pieces near two useful town areas.",
    6: "6/32 — Build two bus stops{}Place two bus stops in useful catchment areas. Stations collect and deliver cargo inside their coverage area.",
    7: "7/32 — Build a road depot{}Connect a road depot to your route. Vehicles are bought, serviced and replaced from depots.",
    8: "8/32 — Buy a bus{}Open your depot, open the vehicle catalogue and buy a bus.",
    9: "9/32 — Give the bus orders{}Open the bus Orders window and add both stops with Go To. Orders define the service route.",
    10: "10/32 — Start the bus{}Start the bus. Next unlocks only when a road vehicle has at least two manual orders and is running.",
    11: "11/32 — Open railway construction{}Open the railway toolbar. Trains carry much more cargo and signals let several trains share infrastructure safely.",
    12: "12/32 — Build railway track{}Use Autorail and build at least six pieces of useful track.",
    13: "13/32 — Build two rail stations{}Place two rail stations connected by your track. Station coverage determines which passengers or resources can use them.",
    14: "14/32 — Build a rail depot{}Place a rail depot connected to the line.",
    15: "15/32 — Buy a train{}Open the depot and buy a locomotive/train.",
    16: "16/32 — Train orders and signal{}Give the train at least two station orders and place at least one signal on your railway.",
    17: "17/32 — Find industries{}Open the Industry directory. Producers output raw materials; processing industries accept inputs and create another cargo.",
    18: "18/32 — Inspect a production chain{}Open an industry from the list and inspect what it produces and accepts. Use Display chain to understand where its cargo can go.",
    19: "19/32 — Deliver industrial cargo{}Build any sensible freight link from a producing industry to a consumer and complete one real freight delivery. Road or rail is fine.",
    20: "20/32 — Open water construction{}Open the water toolbar. The training map contains water and rivers so ships can be practised without searching a huge world.",
    21: "21/32 — Build two docks{}Build two docks on navigable water, preferably near towns or industries. The tutorial checks for two additional station facilities.",
    22: "22/32 — Build a ship depot{}Place a ship depot on navigable water.",
    23: "23/32 — Buy a ship{}Open the ship depot and buy a ship.",
    24: "24/32 — Ship orders and launch{}Give the ship at least two dock orders and start it. Buoys are useful waypoints on complicated waterways.",
    25: "25/32 — Open airport construction{}Open the airport toolbar. Aircraft are fast but expensive and airports need space and town-noise allowance.",
    26: "26/32 — Build two airports{}Place two airports near different towns. Each airport includes a hangar for buying aircraft.",
    27: "27/32 — Buy an aircraft{}Open an airport hangar and buy an aircraft.",
    28: "28/32 — Aircraft orders and launch{}Give the aircraft at least two airport orders and start it.",
    29: "29/32 — Open the town directory{}Open the Town directory. Regular successful services make towns grow; larger towns create more passengers and mail.",
    30: "30/32 — Open a town{}Open any town from the directory and inspect its population, transported cargo and local-authority controls.",
    31: "31/32 — Fund town growth{}Open Local Authority, select Fund new buildings and execute it. This directly accelerates building growth for several months.",
    32: "32/32 — Build a strong company{}You have used every major transport mode and an industry chain. Keep services profitable and reliable: the browser leaderboard now uses OpenTTD's company performance rating from 0 to 1000.",
}

russian_steps = {
    1: "1/32 — Камера и масштаб{}Перемещайте карту правой кнопкой мыши. Масштаб меняйте колёсиком или подсвеченными кнопками. Эта небольшая карта создана специально для обучения.",
    2: "2/32 — Пауза и скорость{}Ставьте игру на паузу при планировании и включайте ускорение, когда ждёте транспорт. Сначала освойте эти два элемента.",
    3: "3/32 — Читаем карту{}Откройте мини-карту. Города создают пассажиров и почту, а промышленность производит и потребляет ресурсы. Задача транспорта — соединять эти потоки.",
    4: "4/32 — Открываем дороги{}Откройте панель строительства дорог. Сначала построим полный пассажирский маршрут — от инфраструктуры до работающей машины.",
    5: "5/32 — Строим дорогу{}Выберите «Авторога» и постройте минимум шесть участков дороги рядом с двумя полезными частями города.",
    6: "6/32 — Две автобусные остановки{}Поставьте две остановки в хороших зонах охвата. Станции собирают и доставляют грузы внутри своей зоны.",
    7: "7/32 — Автодепо{}Подключите к маршруту автодепо. В депо транспорт покупают, обслуживают и заменяют.",
    8: "8/32 — Покупаем автобус{}Откройте депо, список доступного транспорта и купите автобус.",
    9: "9/32 — Задания автобуса{}Откройте «Задания» автобуса и через «Ехать к» добавьте обе остановки. Задания задают маршрут обслуживания.",
    10: "10/32 — Запускаем автобус{}Запустите автобус. «Далее» откроется только когда у машины есть минимум два ручных задания и она движется.",
    11: "11/32 — Открываем железные дороги{}Откройте панель железных дорог. Поезда перевозят большие объёмы, а сигналы позволяют безопасно делить путь между составами.",
    12: "12/32 — Строим путь{}Выберите «Авторельсы» и постройте минимум шесть участков полезного пути.",
    13: "13/32 — Две железнодорожные станции{}Поставьте две станции и соедините их путём. Зона охвата определяет, какие пассажиры и ресурсы попадут на станцию.",
    14: "14/32 — Железнодорожное депо{}Поставьте депо, подключённое к линии.",
    15: "15/32 — Покупаем поезд{}Откройте депо и купите локомотив или готовый поезд.",
    16: "16/32 — Задания и сигнал{}Добавьте поезду минимум две станции в задания и поставьте на линии хотя бы один сигнал.",
    17: "17/32 — Ищем промышленность{}Откройте список промышленности. Добывающие предприятия дают сырьё, а перерабатывающие принимают ресурсы и выпускают следующий груз.",
    18: "18/32 — Изучаем производственную цепочку{}Откройте предприятие из списка и посмотрите, что оно производит и принимает. «Показать цепочку» помогает понять направление груза.",
    19: "19/32 — Доставляем промышленный груз{}Постройте удобную грузовую связь от производителя к потребителю и выполните одну настоящую доставку ресурса. Подойдёт дорога или железная дорога.",
    20: "20/32 — Открываем водный транспорт{}Откройте панель водного строительства. На учебной карте специально есть вода и реки, чтобы корабли можно было освоить быстро.",
    21: "21/32 — Строим два причала{}Поставьте два причала на судоходной воде — например, рядом с городами или предприятиями. Обучение проверит появление двух новых станционных объектов.",
    22: "22/32 — Корабельное депо{}Поставьте корабельное депо на судоходной воде.",
    23: "23/32 — Покупаем корабль{}Откройте корабельное депо и купите судно.",
    24: "24/32 — Задания корабля и запуск{}Добавьте кораблю минимум два причала в задания и запустите его. На сложных водных путях используйте буи как точки маршрута.",
    25: "25/32 — Открываем аэропорты{}Откройте панель аэропортов. Самолёты быстрые, но дорогие; аэропортам нужны свободное место и допустимый уровень шума.",
    26: "26/32 — Строим два аэропорта{}Поставьте два аэропорта рядом с разными городами. В каждом аэропорту есть ангар для покупки самолётов.",
    27: "27/32 — Покупаем самолёт{}Откройте ангар аэропорта и купите самолёт.",
    28: "28/32 — Задания самолёта и запуск{}Добавьте самолёту минимум два аэропорта в задания и запустите его.",
    29: "29/32 — Список городов{}Откройте список городов. Регулярное успешное обслуживание ускоряет рост, а крупные города создают больше пассажиров и почты.",
    30: "30/32 — Открываем город{}Откройте любой город из списка и изучите население, объёмы перевозок и управление местной администрацией.",
    31: "31/32 — Ускоряем рост города{}Откройте «Местная администрация», выберите «Финансировать строительство зданий» и выполните действие. Оно ускоряет рост застройки на несколько месяцев.",
    32: "32/32 — Развиваем сильную компанию{}Вы освоили все основные виды транспорта и производственную цепочку. Поддерживайте прибыльные надёжные маршруты: рейтинг браузерной версии теперь равен штатной эффективности компании OpenTTD от 0 до 1000.",
}

for number, value in english_steps.items():
    replace_lang_line(Path("openttd/src/lang/english.txt"), f"STR_BROWSER_TUTORIAL_LEVEL_{number:02d}", value)
for number, value in russian_steps.items():
    replace_lang_line(Path("openttd/src/lang/russian.txt"), f"STR_BROWSER_TUTORIAL_LEVEL_{number:02d}", value)

path = Path("openttd/src/intro_gui.cpp")
text = path.read_text(encoding="utf-8")

# Headers used only by the final expanded lesson model.
include_anchor = '#include "widgets/order_widget.h"\n'
extra_headers = '''#include "widgets/order_widget.h"
#include "widgets/dock_widget.h"
#include "widgets/airport_widget.h"
#include "widgets/town_widget.h"
#include "widgets/industry_widget.h"
#include "water_map.h"
#include "town.h"
#include "cargotype.h"
'''
if '#include "widgets/dock_widget.h"' not in text:
    text = replace_once(text, include_anchor, extra_headers, "tutorial v2 headers")

# Replace all tutorial window geometry in one pass. Buttons have no horizontal
# fill: spacers absorb unused width, so GUI scaling cannot turn them into giant
# half-window slabs.
def replace_widget_block(name: str, body: str) -> None:
    global text
    pattern = re.compile(rf"static constexpr std::initializer_list<NWidgetPart> {re.escape(name)} = \{{.*?\n\}};", re.S)
    text, count = pattern.subn(body, text, count=1)
    if count != 1:
        raise SystemExit(f"Could not replace widget block {name}: {count}")

replace_widget_block("_nested_browser_tutorial_widgets", r'''static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_TUTORIAL_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BT_TEXT), SetMinimalSize(400, 132), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_normal, 0),
		NWidget(NWID_SPACER), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(74, 18),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(74, 18),
		NWidget(NWID_SPACER), SetFill(1, 0),
	EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_normal, 0),
		NWidget(NWID_SPACER), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BT_START_LEVEL), SetStringTip(STR_BROWSER_TUTORIAL_START_LEVEL, STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP), SetMinimalSize(126, 20),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_BUTTON_GUIDE), SetStringTip(STR_BROWSER_BUTTON_GUIDE_MENU, STR_BROWSER_BUTTON_GUIDE_TOOLTIP), SetMinimalSize(118, 20),
		NWidget(NWID_SPACER), SetFill(1, 0),
	EndContainer(),
};''')

replace_widget_block("_nested_browser_button_guide_widgets", r'''static constexpr std::initializer_list<NWidgetPart> _nested_browser_button_guide_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_MANUAL_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BBG_CONTENT), SetMinimalSize(420, 150), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_normal, 0),
		NWidget(NWID_SPACER), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(74, 18),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(74, 18),
		NWidget(NWID_SPACER), SetFill(1, 0),
	EndContainer(),
};''')

replace_widget_block("_nested_browser_tutorial_coach_widgets", r'''static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_coach_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_TUTORIAL_COACH_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BTC_CONTENT), SetMinimalSize(400, 122), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_normal, 0),
		NWidget(NWID_SPACER), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BTC_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(74, 18),
		NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BTC_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(74, 18),
		NWidget(NWID_SPACER), SetFill(1, 0),
	EndContainer(),
};''')

# Starting a practical lesson must destroy the overview before world creation;
# keeping it alive was the cause of the green/orange overview controls visibly
# poking out from underneath the coach on the generated map.
old_start_click = 'case WID_BT_START_LEVEL: StartBrowserTutorialLevel(); return;'
new_start_click = 'case WID_BT_START_LEVEL: this->Close(); StartBrowserTutorialLevel(); return;'
text = replace_once(text, old_start_click, new_start_click, "overview-to-coach transition")

# Full set of visual target types.
target_pattern = re.compile(r'enum class BrowserTutorialTarget : uint8_t \{.*?\n\};', re.S)
new_targets = '''enum class BrowserTutorialTarget : uint8_t {
\tNone,
\tMainToolbar,
\tRoadToolbar,
\tRailToolbar,
\tWaterToolbar,
\tAirToolbar,
};'''
text, count = target_pattern.subn(new_targets, text, count=1)
if count != 1:
    raise SystemExit(f"Could not replace tutorial target enum: {count}")

objective_pattern = re.compile(r'enum class BrowserTutorialObjective : uint8_t \{.*?\n\};', re.S)
new_objectives = '''enum class BrowserTutorialObjective : uint8_t {
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
\tIndustryDirectoryOpen,
\tIndustryViewOpen,
\tFreightDelivered,
\tWaterToolbarOpen,
\tDocksBuilt,
\tShipDepotBuilt,
\tShipBought,
\tShipOrdersRunning,
\tAirToolbarOpen,
\tAirportsBuilt,
\tAircraftBought,
\tAircraftOrdersRunning,
\tTownDirectoryOpen,
\tTownViewOpen,
\tTownGrowthFunded,
};'''
text, count = objective_pattern.subn(new_objectives, text, count=1)
if count != 1:
    raise SystemExit(f"Could not replace tutorial objective enum: {count}")

steps_pattern = re.compile(r'static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps\[\] = \{.*?\n\};', re.S)
new_steps = '''static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps[] = {
\t{STR_BROWSER_TUTORIAL_LEVEL_01, SPR_IMG_ZOOMIN, BrowserTutorialTarget::MainToolbar, WID_TN_ZOOM_IN, BrowserTutorialObjective::Informational},
\t{STR_BROWSER_TUTORIAL_LEVEL_02, SPR_IMG_PAUSE, BrowserTutorialTarget::MainToolbar, WID_TN_PAUSE, BrowserTutorialObjective::Informational},
\t{STR_BROWSER_TUTORIAL_LEVEL_03, SPR_IMG_SMALLMAP, BrowserTutorialTarget::MainToolbar, WID_TN_SMALL_MAP, BrowserTutorialObjective::SmallMapOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_04, SPR_IMG_BUILDROAD, BrowserTutorialTarget::MainToolbar, WID_TN_ROADS, BrowserTutorialObjective::RoadToolbarOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_05, SPR_IMG_AUTOROAD, BrowserTutorialTarget::RoadToolbar, WID_ROT_AUTOROAD, BrowserTutorialObjective::RoadBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_06, SPR_IMG_BUS_STATION, BrowserTutorialTarget::RoadToolbar, WID_ROT_BUS_STATION, BrowserTutorialObjective::BusStationsBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_ROAD_DEPOT, BrowserTutorialTarget::RoadToolbar, WID_ROT_DEPOT, BrowserTutorialObjective::RoadDepotBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicleBought},
\t{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadOrdersSet},
\t{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicleRunning},
\t{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailToolbarOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_AUTORAIL, BrowserTutorialObjective::RailBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_STATION, BrowserTutorialObjective::RailStationsBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_14, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_DEPOT, BrowserTutorialObjective::RailDepotBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_TRAINLIST, BrowserTutorialTarget::MainToolbar, WID_TN_TRAINS, BrowserTutorialObjective::TrainBought},
\t{STR_BROWSER_TUTORIAL_LEVEL_16, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::RailToolbar, WID_RAT_BUILD_SIGNALS, BrowserTutorialObjective::TrainOrdersAndSignal},
\t{STR_BROWSER_TUTORIAL_LEVEL_17, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::IndustryDirectoryOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_18, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::IndustryViewOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_19, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::FreightDelivered},
\t{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER, BrowserTutorialObjective::WaterToolbarOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_21, SPR_IMG_BUILDWATER, BrowserTutorialTarget::WaterToolbar, WID_DT_STATION, BrowserTutorialObjective::DocksBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_22, SPR_IMG_BUILDWATER, BrowserTutorialTarget::WaterToolbar, WID_DT_DEPOT, BrowserTutorialObjective::ShipDepotBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_23, SPR_IMG_SHIPLIST, BrowserTutorialTarget::MainToolbar, WID_TN_SHIPS, BrowserTutorialObjective::ShipBought},
\t{STR_BROWSER_TUTORIAL_LEVEL_24, SPR_IMG_SHIPLIST, BrowserTutorialTarget::MainToolbar, WID_TN_SHIPS, BrowserTutorialObjective::ShipOrdersRunning},
\t{STR_BROWSER_TUTORIAL_LEVEL_25, SPR_IMG_BUILDAIR, BrowserTutorialTarget::MainToolbar, WID_TN_AIR, BrowserTutorialObjective::AirToolbarOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_26, SPR_IMG_BUILDAIR, BrowserTutorialTarget::AirToolbar, WID_AT_AIRPORT, BrowserTutorialObjective::AirportsBuilt},
\t{STR_BROWSER_TUTORIAL_LEVEL_27, SPR_IMG_AIRPLANESLIST, BrowserTutorialTarget::MainToolbar, WID_TN_AIRCRAFT, BrowserTutorialObjective::AircraftBought},
\t{STR_BROWSER_TUTORIAL_LEVEL_28, SPR_IMG_AIRPLANESLIST, BrowserTutorialTarget::MainToolbar, WID_TN_AIRCRAFT, BrowserTutorialObjective::AircraftOrdersRunning},
\t{STR_BROWSER_TUTORIAL_LEVEL_29, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::TownDirectoryOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_30, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::TownViewOpen},
\t{STR_BROWSER_TUTORIAL_LEVEL_31, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::TownGrowthFunded},
\t{STR_BROWSER_TUTORIAL_LEVEL_32, SPR_IMG_COMPANY_LEAGUE, BrowserTutorialTarget::MainToolbar, WID_TN_LEAGUE, BrowserTutorialObjective::Informational},
};'''
text, count = steps_pattern.subn(new_steps, text, count=1)
if count != 1:
    raise SystemExit(f"Could not replace tutorial v2 step table: {count}")

# Upgrade the world-state snapshot to all major vehicle modes and water/air
# infrastructure. The tutorial world starts with an empty player company, so
# comparisons against the initial snapshot remain stable even when navigating
# backwards through the coach.
snapshot_pattern = re.compile(
    r'struct BrowserTutorialProgressSnapshot \{.*?\nstatic bool BrowserTutorialHasOrders\(VehicleType type, bool require_running\)',
    re.S,
)
new_snapshot = '''struct BrowserTutorialProgressSnapshot {
\tuint32_t road = 0;
\tuint32_t rail = 0;
\tuint32_t stations = 0;
\tuint32_t signals = 0;
\tuint32_t airports = 0;
\tuint32_t road_depots = 0;
\tuint32_t rail_depots = 0;
\tuint32_t ship_depots = 0;
\tuint32_t road_vehicles = 0;
\tuint32_t trains = 0;
\tuint32_t ships = 0;
\tuint32_t aircraft = 0;
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
\t\tresult.airports = company->infrastructure.airport;
\t}

\tfor (const Depot *depot : Depot::Iterate()) {
\t\tif (depot->xy == INVALID_TILE || GetTileOwner(depot->xy) != _local_company) continue;
\t\tif (IsRoadDepotTile(depot->xy)) ++result.road_depots;
\t\tif (IsRailDepotTile(depot->xy)) ++result.rail_depots;
\t\tif (IsShipDepotTile(depot->xy)) ++result.ship_depots;
\t}

\tfor (const Vehicle *vehicle : Vehicle::Iterate()) {
\t\tif (vehicle->owner != _local_company || !vehicle->IsPrimaryVehicle()) continue;
\t\tswitch (vehicle->type) {
\t\t\tcase VEH_ROAD: ++result.road_vehicles; break;
\t\t\tcase VEH_TRAIN: ++result.trains; break;
\t\t\tcase VEH_SHIP: ++result.ships; break;
\t\t\tcase VEH_AIRCRAFT: ++result.aircraft; break;
\t\t\tdefault: break;
\t\t}
\t}
\treturn result;
}

static bool BrowserTutorialHasOrders(VehicleType type, bool require_running)'''
text, count = snapshot_pattern.subn(new_snapshot, text, count=1)
if count != 1:
    raise SystemExit(f"Could not upgrade tutorial snapshot: {count}")

# Additional real objectives: at least one delivered freight unit, and the
# actual local-authority 'fund new buildings' effect for town growth.
objective_function_pattern = re.compile(
    r'static bool BrowserTutorialObjectiveComplete\(BrowserTutorialObjective objective\)\n\{.*?\n\}',
    re.S,
)
new_objective_function = '''static uint64_t BrowserTutorialDeliveredFreight()
{
\tconst Company *company = Company::GetIfValid(_local_company);
\tif (company == nullptr) return 0;
\tuint64_t total = 0;
\tauto add_entry = [&total](const CompanyEconomyEntry &entry) {
\t\tfor (CargoSpec *cargo : CargoSpec::Iterate()) {
\t\t\tif (!cargo->is_freight) continue;
\t\t\ttotal += entry.delivered_cargo[cargo->Index()];
\t\t}
\t};
\tadd_entry(company->cur_economy);
\tfor (uint i = 0; i < company->num_valid_stat_ent; ++i) add_entry(company->old_economy[i]);
\treturn total;
}

static bool BrowserTutorialTownGrowthFunded()
{
\tfor (const Town *town : Town::Iterate()) {
\t\tif (town->fund_buildings_months > 0) return true;
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
\t\tcase BrowserTutorialObjective::TrainOrdersAndSignal: return now.signals > _browser_tutorial_origin.signals && BrowserTutorialHasOrders(VEH_TRAIN, false);
\t\tcase BrowserTutorialObjective::IndustryDirectoryOpen: return FindWindowByClass(WC_INDUSTRY_DIRECTORY) != nullptr;
\t\tcase BrowserTutorialObjective::IndustryViewOpen: return FindWindowByClass(WC_INDUSTRY_VIEW) != nullptr;
\t\tcase BrowserTutorialObjective::FreightDelivered: return BrowserTutorialDeliveredFreight() > 0;
\t\tcase BrowserTutorialObjective::WaterToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_WATER) != nullptr;
\t\tcase BrowserTutorialObjective::DocksBuilt: return now.stations >= _browser_tutorial_origin.stations + 6;
\t\tcase BrowserTutorialObjective::ShipDepotBuilt: return now.ship_depots > _browser_tutorial_origin.ship_depots;
\t\tcase BrowserTutorialObjective::ShipBought: return now.ships > _browser_tutorial_origin.ships;
\t\tcase BrowserTutorialObjective::ShipOrdersRunning: return BrowserTutorialHasOrders(VEH_SHIP, true);
\t\tcase BrowserTutorialObjective::AirToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_AIR) != nullptr;
\t\tcase BrowserTutorialObjective::AirportsBuilt: return now.airports >= _browser_tutorial_origin.airports + 2;
\t\tcase BrowserTutorialObjective::AircraftBought: return now.aircraft > _browser_tutorial_origin.aircraft;
\t\tcase BrowserTutorialObjective::AircraftOrdersRunning: return BrowserTutorialHasOrders(VEH_AIRCRAFT, true);
\t\tcase BrowserTutorialObjective::TownDirectoryOpen: return FindWindowByClass(WC_TOWN_DIRECTORY) != nullptr;
\t\tcase BrowserTutorialObjective::TownViewOpen: return FindWindowByClass(WC_TOWN_VIEW) != nullptr;
\t\tcase BrowserTutorialObjective::TownGrowthFunded: return BrowserTutorialTownGrowthFunded();
\t}
\treturn false;
}'''
text, count = objective_function_pattern.subn(new_objective_function, text, count=1)
if count != 1:
    raise SystemExit(f"Could not replace expanded objective function: {count}")

# Deterministic toolbar resolution for every construction mode.
target_window_pattern = re.compile(r'static Window \*BrowserTutorialTargetWindow\(BrowserTutorialTarget target\)\n\{.*?\n\}', re.S)
new_target_window = '''static Window *BrowserTutorialTargetWindow(BrowserTutorialTarget target)
{
\tswitch (target) {
\t\tcase BrowserTutorialTarget::MainToolbar: return FindWindowById(WC_MAIN_TOOLBAR, 0);
\t\tcase BrowserTutorialTarget::RoadToolbar: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD);
\t\tcase BrowserTutorialTarget::RailToolbar: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL);
\t\tcase BrowserTutorialTarget::WaterToolbar: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_WATER);
\t\tcase BrowserTutorialTarget::AirToolbar: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_AIR);
\t\tdefault: return nullptr;
\t}
}'''
text, count = target_window_pattern.subn(new_target_window, text, count=1)
if count != 1:
    raise SystemExit(f"Could not replace target-window resolver: {count}")

# Replace the dynamic target resolver wholesale. It follows the active depot,
# catalogue, orders, industry and town windows, then falls back to the top
# toolbar if a transient construction toolbar was closed.
resolver_pattern = re.compile(
    r'static Window \*BrowserTutorialResolveTarget\(const BrowserTutorialCoachStep &step, WidgetID &widget\)\n\{.*?\n\}',
    re.S,
)
new_resolver = '''static Window *BrowserTutorialResolveTarget(const BrowserTutorialCoachStep &step, WidgetID &widget)
{
\tconst bool purchase = step.objective == BrowserTutorialObjective::RoadVehicleBought ||
\t\t\tstep.objective == BrowserTutorialObjective::TrainBought ||
\t\t\tstep.objective == BrowserTutorialObjective::ShipBought ||
\t\t\tstep.objective == BrowserTutorialObjective::AircraftBought;
\tif (purchase) {
\t\tif (Window *build = FindWindowByClass(WC_BUILD_VEHICLE); build != nullptr) {
\t\t\twidget = WID_BV_BUILD_SEL;
\t\t\treturn build;
\t\t}
\t\tif (Window *depot = FindWindowByClass(WC_VEHICLE_DEPOT); depot != nullptr) {
\t\t\twidget = WID_D_BUILD;
\t\t\treturn depot;
\t\t}
\t}

\tVehicleType order_type = VEH_INVALID;
\tbool require_running = false;
\tif (step.objective == BrowserTutorialObjective::RoadOrdersSet) order_type = VEH_ROAD;
\tif (step.objective == BrowserTutorialObjective::RoadVehicleRunning) { order_type = VEH_ROAD; require_running = true; }
\tif (step.objective == BrowserTutorialObjective::TrainOrdersAndSignal && !BrowserTutorialHasOrders(VEH_TRAIN, false)) order_type = VEH_TRAIN;
\tif (step.objective == BrowserTutorialObjective::ShipOrdersRunning) { order_type = VEH_SHIP; require_running = true; }
\tif (step.objective == BrowserTutorialObjective::AircraftOrdersRunning) { order_type = VEH_AIRCRAFT; require_running = true; }
\tif (order_type != VEH_INVALID) {
\t\tif (!BrowserTutorialHasOrders(order_type, false)) {
\t\t\tif (Window *orders = FindWindowByClass(WC_VEHICLE_ORDERS); orders != nullptr) { widget = WID_O_GOTO; return orders; }
\t\t\tif (Window *vehicle = FindWindowByClass(WC_VEHICLE_VIEW); vehicle != nullptr) { widget = WID_VV_SHOW_ORDERS; return vehicle; }
\t\t} else if (require_running && !BrowserTutorialHasOrders(order_type, true)) {
\t\t\tif (Window *vehicle = FindWindowByClass(WC_VEHICLE_VIEW); vehicle != nullptr) { widget = WID_VV_START_STOP; return vehicle; }
\t\t}
\t}

\tif (step.objective == BrowserTutorialObjective::IndustryViewOpen) {
\t\tif (Window *industry = FindWindowByClass(WC_INDUSTRY_DIRECTORY); industry != nullptr) { widget = WID_ID_INDUSTRY_LIST; return industry; }
\t}
\tif (step.objective == BrowserTutorialObjective::FreightDelivered) {
\t\tif (Window *industry = FindWindowByClass(WC_INDUSTRY_VIEW); industry != nullptr) { widget = WID_IV_DISPLAY; return industry; }
\t}
\tif (step.objective == BrowserTutorialObjective::TownViewOpen) {
\t\tif (Window *towns = FindWindowByClass(WC_TOWN_DIRECTORY); towns != nullptr) { widget = WID_TD_LIST; return towns; }
\t}
\tif (step.objective == BrowserTutorialObjective::TownGrowthFunded) {
\t\tif (Window *authority = FindWindowByClass(WC_TOWN_AUTHORITY); authority != nullptr) { widget = WID_TA_COMMAND_LIST; return authority; }
\t\tif (Window *town = FindWindowByClass(WC_TOWN_VIEW); town != nullptr) { widget = WID_TV_SHOW_AUTHORITY; return town; }
\t}

\twidget = step.widget;
\tif (Window *target = BrowserTutorialTargetWindow(step.target); target != nullptr && widget != INVALID_WIDGET) return target;

\tWindow *main = FindWindowById(WC_MAIN_TOOLBAR, 0);
\tif (main == nullptr) return nullptr;
\tif (step.target == BrowserTutorialTarget::RoadToolbar) { widget = WID_TN_ROADS; return main; }
\tif (step.target == BrowserTutorialTarget::RailToolbar) { widget = WID_TN_RAILS; return main; }
\tif (step.target == BrowserTutorialTarget::WaterToolbar) { widget = WID_TN_WATER; return main; }
\tif (step.target == BrowserTutorialTarget::AirToolbar) { widget = WID_TN_AIR; return main; }
\treturn nullptr;
}'''
text, count = resolver_pattern.subn(new_resolver, text, count=1)
if count != 1:
    raise SystemExit(f"Could not replace final dynamic resolver: {count}")

# Dedicated course world: compact, flat, enough towns/industry, and deliberately
# more water than the original tutorial so ships are always a first-class task.
old_map = '''\t_settings_newgame.game_creation.map_x = 7;
\t_settings_newgame.game_creation.map_y = 7;
\t_settings_newgame.game_creation.landscape = LandscapeType::Temperate;
\t_settings_newgame.game_creation.amount_of_rivers = 0;
\t_settings_newgame.difficulty.terrain_type = 0;
'''
new_map = '''\t_settings_newgame.game_creation.map_x = 7;
\t_settings_newgame.game_creation.map_y = 7;
\t_settings_newgame.game_creation.landscape = LandscapeType::Temperate;
\t_settings_newgame.game_creation.amount_of_rivers = 2;
\t_settings_newgame.game_creation.custom_town_number = 8;
\t_settings_newgame.difficulty.number_towns = CUSTOM_TOWN_NUMBER_DIFFICULTY;
\t_settings_newgame.difficulty.industry_density = ID_HIGH;
\t_settings_newgame.difficulty.terrain_type = 0;
\t_settings_newgame.difficulty.quantity_sea_lakes = 2;
\t_settings_newgame.difficulty.max_no_competitors = 0;
'''
text = replace_once(text, old_map, new_map, "dedicated multimodal practice map")

required = (
    "STR_BROWSER_TUTORIAL_LEVEL_32",
    "BrowserTutorialObjective::FreightDelivered",
    "BrowserTutorialObjective::ShipOrdersRunning",
    "BrowserTutorialObjective::AircraftOrdersRunning",
    "BrowserTutorialObjective::TownGrowthFunded",
    "BrowserTutorialDeliveredFreight()",
    "town->fund_buildings_months > 0",
    "IsShipDepotTile(depot->xy)",
    "WID_DT_STATION",
    "WID_AT_AIRPORT",
    "WID_TA_COMMAND_LIST",
    "SetMinimalSize(74, 18)",
    "this->Close(); StartBrowserTutorialLevel();",
    "custom_town_number = 8",
    "difficulty.industry_density = ID_HIGH",
    "difficulty.quantity_sea_lakes = 2",
)
for marker in required:
    if marker not in text:
        raise SystemExit(f"Missing tutorial v2 marker: {marker}")

path.write_text(text, encoding="utf-8")
print("Tutorial v2 applied: compact single-window UX + road/rail/freight/ship/air/town-growth course on a dedicated map.")
