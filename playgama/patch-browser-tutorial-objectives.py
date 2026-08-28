#!/usr/bin/env python3
"""Restore the full objective-gated tutorial and its dedicated practice world."""
from pathlib import Path
import re


def set_string(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    line = f"{key:<64}:{value}"
    pattern = re.compile(rf"^{re.escape(key)}\s*:.*$", re.M)
    if pattern.search(text):
        text = pattern.sub(line, text, count=1)
    else:
        text += ("" if text.endswith("\n") else "\n") + line + "\n"
    path.write_text(text, encoding="utf-8")


EN_OVERVIEW = [
    "Camera and map{}Move the map, zoom and inspect the area before building.",
    "Towns and cities{}Towns create passengers and mail inside station catchment areas and grow when well served.",
    "Roads and buses{}Connect two nearby towns with road, stops, a depot and a bus.",
    "Orders and delivery{}Give vehicles useful orders. Income appears after cargo or passengers are delivered.",
    "Railways and signals{}Build track, stations, a depot and signals, then run a train.",
    "Industries and resources{}Match a producing industry with a consumer and build a cargo route.",
    "Ships{}Build docks with water access, buy a ship and connect suitable ports.",
    "Aircraft{}Build airports near demand, buy an aircraft and create a long-distance route.",
    "Finances{}Compare income, construction, running costs and loan interest before expanding.",
    "Terrain, bridges and tunnels{}Use landscaping carefully and prefer direct bridges or tunnels when useful.",
    "Town and company growth{}Use town lists, graphs and company information to judge progress.",
    "Interactive level{}The dedicated training world checks real objectives and unlocks Next only after completion.",
]
RU_OVERVIEW = [
    "Камера и карта{}Перемещайте карту, меняйте масштаб и осматривайте местность до строительства.",
    "Города{}Города создают пассажиров и почту в зоне охвата станций и растут при хорошем обслуживании.",
    "Дороги и автобусы{}Соедините два близких города дорогой, остановками, депо и автобусом.",
    "Задания и доставка{}Задайте транспорту полезный маршрут. Доход появляется после доставки пассажиров или груза.",
    "Железные дороги и сигналы{}Постройте путь, станции, депо и сигналы, затем запустите поезд.",
    "Предприятия и ресурсы{}Свяжите производящее предприятие с подходящим потребителем грузовым маршрутом.",
    "Корабли{}Постройте причалы с доступом к воде, купите корабль и соедините подходящие порты.",
    "Самолёты{}Постройте аэропорты рядом со спросом, купите самолёт и создайте дальний маршрут.",
    "Финансы{}Сравнивайте доход, строительство, эксплуатационные расходы и проценты по кредиту.",
    "Рельеф, мосты и тоннели{}Меняйте рельеф аккуратно, используйте мосты и тоннели для прямых маршрутов.",
    "Рост городов и компании{}Используйте список городов, графики и сведения о компании для оценки прогресса.",
    "Интерактивный уровень{}Отдельная учебная карта проверяет реальные цели и открывает Далее только после выполнения.",
]

EN_LEVEL = [
    "Camera and zoom{}Inspect the small training world, nearby towns, industries and water. Continue: no construction required.",
    "Pause and speed{}Use pause for planning and fast-forward only while waiting. Continue: review these controls.",
    "Towns and catchment{}Open the town list and choose two nearby towns. Continue: choose the first passenger route.",
    "Road tools{}Open the highlighted road construction toolbar. Continue: the road toolbar must be open.",
    "First road{}Build a short continuous road. Continue: own at least 8 road pieces.",
    "Bus stops{}Place one stop in each town. Continue: own at least 2 station tiles.",
    "Depot and bus{}Build a connected road depot and buy a bus. Continue: own at least 1 road vehicle.",
    "Orders and first delivery{}Add both stops, start the bus and wait. Continue: deliver at least 10 cargo units or passengers.",
    "Finances{}Open company finances. Continue: record positive transport income.",
    "Rail tools{}Open railway construction and inspect track, station, depot and signal tools. Continue: choose a short rail route.",
    "Rail track{}Build a point-to-point railway. Continue: own at least 8 rail pieces.",
    "Rail stations{}Build a station at each end. Continue: own at least 4 station tiles in total.",
    "Signals{}Place a signal on the railway. Continue: own at least 1 signal.",
    "Train{}Build a depot and buy a train. Continue: own at least 1 train.",
    "Train orders{}Give the train useful orders and start it. Continue: watch the route operate.",
    "Industries and resources{}Open the industry list and find a producer plus matching consumer. Continue: choose a cargo chain.",
    "Cargo route{}Build stations and suitable transport for that resource chain. Continue: start the cargo service.",
    "Different cargo{}Run passenger and resource services. Continue: deliver at least 2 cargo types and 50 units total.",
    "Water transport{}Open water construction and find the easy coastline. Continue: choose a ship route.",
    "Dock{}Build a dock with water access. Continue: own at least 5 station tiles in total.",
    "Ship{}Buy a ship and give it useful orders. Continue: own at least 1 ship.",
    "Air transport{}Open airport construction and find clear land near a town. Continue: choose an airport site.",
    "Airport{}Build an airport near demand. Continue: own at least 1 airport.",
    "Aircraft{}Buy an aircraft and give it useful orders. Continue: own at least 1 aircraft.",
    "Town growth{}Compare the towns served by your network. Continue: keep positive transport income.",
    "Terrain, bridges and tunnels{}Inspect landscaping, bridges and tunnels. Continue: review these tools.",
    "Company progress{}Open graphs and company information. Continue: keep positive transport income.",
    "Finish{}Save the practice world if wanted. Training has covered towns, rail, resources, ships and aircraft.",
]
RU_LEVEL = [
    "Камера и масштаб{}Осмотрите небольшую учебную карту, города, предприятия и воду. Для продолжения: строительство пока не требуется.",
    "Пауза и скорость{}Используйте паузу для планирования, ускорение только для ожидания. Для продолжения: ознакомьтесь с кнопками.",
    "Города и зона охвата{}Откройте список городов и выберите два близких города. Для продолжения: выберите первый пассажирский маршрут.",
    "Строительство дорог{}Откройте подсвеченную панель дорог. Для продолжения: панель строительства дорог должна быть открыта.",
    "Первая дорога{}Постройте короткую непрерывную дорогу. Для продолжения: у компании должно быть не менее 8 участков дороги.",
    "Автобусные остановки{}Поставьте по остановке в каждом городе. Для продолжения: у компании должно быть не менее 2 станционных клеток.",
    "Депо и автобус{}Постройте соединённое с дорогой депо и купите автобус. Для продолжения: у компании должен быть хотя бы 1 автомобиль.",
    "Задания и первая доставка{}Добавьте обе остановки, запустите автобус и дождитесь рейса. Для продолжения: доставьте не менее 10 единиц груза или пассажиров.",
    "Финансы{}Откройте финансы компании. Для продолжения: получите положительный транспортный доход.",
    "Железнодорожные инструменты{}Откройте строительство железной дороги и изучите путь, станции, депо и сигналы. Для продолжения: выберите короткий маршрут.",
    "Железнодорожный путь{}Постройте линию между двумя точками. Для продолжения: у компании должно быть не менее 8 участков рельсов.",
    "Железнодорожные станции{}Постройте станции на концах линии. Для продолжения: у компании должно быть не менее 4 станционных клеток всего.",
    "Сигналы{}Поставьте сигнал на железной дороге. Для продолжения: у компании должен быть хотя бы 1 сигнал.",
    "Поезд{}Постройте депо и купите поезд. Для продолжения: у компании должен быть хотя бы 1 поезд.",
    "Задания поезда{}Добавьте полезные задания и запустите поезд. Для продолжения: проследите работу маршрута.",
    "Предприятия и ресурсы{}Откройте список предприятий, найдите производителя и подходящего потребителя. Для продолжения: выберите грузовую цепочку.",
    "Грузовой маршрут{}Постройте станции и подходящий транспорт для ресурсов. Для продолжения: запустите грузовой маршрут.",
    "Разные грузы{}Запустите пассажирский и ресурсный маршруты. Для продолжения: доставьте не менее 2 видов груза и 50 единиц всего.",
    "Водный транспорт{}Откройте инструменты водного транспорта и найдите удобный берег. Для продолжения: выберите маршрут корабля.",
    "Причал{}Постройте причал с доступом к воде. Для продолжения: у компании должно быть не менее 5 станционных клеток всего.",
    "Корабль{}Купите корабль и задайте полезный маршрут. Для продолжения: у компании должен быть хотя бы 1 корабль.",
    "Воздушный транспорт{}Откройте строительство аэропортов и найдите свободное место у города. Для продолжения: выберите площадку.",
    "Аэропорт{}Постройте аэропорт рядом со спросом. Для продолжения: у компании должен быть хотя бы 1 аэропорт.",
    "Самолёт{}Купите самолёт и задайте полезный маршрут. Для продолжения: у компании должен быть хотя бы 1 самолёт.",
    "Рост городов{}Сравните города, которые обслуживает сеть. Для продолжения: сохраняйте положительный транспортный доход.",
    "Рельеф, мосты и тоннели{}Изучите изменение рельефа, мосты и тоннели. Для продолжения: ознакомьтесь с инструментами.",
    "Развитие компании{}Откройте графики и сведения о компании. Для продолжения: сохраняйте положительный транспортный доход.",
    "Завершение{}При желании сохраните учебную карту. Обучение охватило города, железную дорогу, ресурсы, корабли и самолёты.",
]

english = Path("openttd/src/lang/english.txt")
russian = Path("openttd/src/lang/russian.txt")
for i, text in enumerate(EN_OVERVIEW, 1): set_string(english, f"STR_BROWSER_TUTORIAL_STEP_{i}", f"{i}/12 - {text}")
for i, text in enumerate(RU_OVERVIEW, 1): set_string(russian, f"STR_BROWSER_TUTORIAL_STEP_{i}", f"{i}/12 - {text}")
for i, text in enumerate(EN_LEVEL, 1): set_string(english, f"STR_BROWSER_TUTORIAL_LEVEL_{i:02d}", f"{i}/28 - {text}")
for i, text in enumerate(RU_LEVEL, 1): set_string(russian, f"STR_BROWSER_TUTORIAL_LEVEL_{i:02d}", f"{i}/28 - {text}")
set_string(english, "STR_BROWSER_TUTORIAL_COACH_HINT", "Complete the current requirement in the game. Next unlocks automatically when the objective is complete.")
set_string(russian, "STR_BROWSER_TUTORIAL_COACH_HINT", "Выполните требование текущего шага в игре. Кнопка Далее станет доступна автоматически после выполнения цели.")

intro_path = Path("openttd/src/intro_gui.cpp")
intro = intro_path.read_text(encoding="utf-8")
if '#include "company_base.h"' not in intro:
    anchor = '#include "vehicle_base.h"\n'
    if anchor not in intro: raise SystemExit("vehicle_base include anchor missing")
    intro = intro.replace(anchor, anchor + '#include "company_base.h"\n', 1)

start = intro.find("static constexpr StringID _browser_tutorial_steps[] = {")
end = intro.find("\n};", start)
if start < 0 or end < 0: raise SystemExit("tutorial overview array missing")
overview = "static constexpr StringID _browser_tutorial_steps[] = {\n" + "".join(f"\tSTR_BROWSER_TUTORIAL_STEP_{i},\n" for i in range(1, 13)) + "};"
intro = intro[:start] + overview + intro[end + 3:]

start = intro.find("enum class BrowserTutorialTarget : uint8_t {")
end = intro.find("static bool _browser_tutorial_pending = false;", start)
if start < 0 or end < 0: raise SystemExit("tutorial step definitions missing")
logic = r'''enum class BrowserTutorialTarget : uint8_t { None, MainToolbar, RoadToolbar };
enum class BrowserTutorialObjective : uint8_t {
	None, RoadToolbarOpen, RoadBuilt, Station2, RoadVehicle, FirstDelivery,
	PositiveIncome, RailBuilt, Station4, SignalBuilt, Train, MultiCargo,
	DockBuilt, Ship, Airport, Aircraft,
};
struct BrowserTutorialCoachStep {
	StringID text; SpriteID icon; BrowserTutorialTarget target; WidgetID widget; BrowserTutorialObjective objective;
};
static const Company *BrowserTutorialCompany() { return Company::GetIfValid(_local_company); }
static uint64_t BrowserTutorialDeliveredCargo(const Company *c)
{
	if (c == nullptr) return 0;
	uint64_t total = c->cur_economy.delivered_cargo.GetSum<uint64_t>();
	for (uint i = 0; i < c->num_valid_stat_ent; ++i) total += c->old_economy[i].delivered_cargo.GetSum<uint64_t>();
	return total;
}
static uint BrowserTutorialDeliveredCargoKinds(const Company *c)
{
	if (c == nullptr) return 0;
	uint count = 0;
	for (uint cargo = 0; cargo < NUM_CARGO; ++cargo) {
		uint64_t amount = c->cur_economy.delivered_cargo[cargo];
		for (uint i = 0; i < c->num_valid_stat_ent; ++i) amount += c->old_economy[i].delivered_cargo[cargo];
		if (amount > 0) ++count;
	}
	return count;
}
static bool BrowserTutorialHasPositiveIncome(const Company *c)
{
	if (c == nullptr) return false;
	if (c->cur_economy.income > 0) return true;
	for (uint i = 0; i < c->num_valid_stat_ent; ++i) if (c->old_economy[i].income > 0) return true;
	return false;
}
static bool BrowserTutorialObjectiveComplete(BrowserTutorialObjective objective)
{
	const Company *c = BrowserTutorialCompany();
	switch (objective) {
		case BrowserTutorialObjective::None: return true;
		case BrowserTutorialObjective::RoadToolbarOpen: return FindWindowByClass(WC_BUILD_TOOLBAR) != nullptr;
		case BrowserTutorialObjective::RoadBuilt: return c != nullptr && c->infrastructure.GetRoadTotal() >= 8;
		case BrowserTutorialObjective::Station2: return c != nullptr && c->infrastructure.station >= 2;
		case BrowserTutorialObjective::RoadVehicle: return c != nullptr && c->group_all[VEH_ROAD].num_vehicle >= 1;
		case BrowserTutorialObjective::FirstDelivery: return BrowserTutorialDeliveredCargo(c) >= 10;
		case BrowserTutorialObjective::PositiveIncome: return BrowserTutorialHasPositiveIncome(c);
		case BrowserTutorialObjective::RailBuilt: return c != nullptr && c->infrastructure.GetRailTotal() >= 8;
		case BrowserTutorialObjective::Station4: return c != nullptr && c->infrastructure.station >= 4;
		case BrowserTutorialObjective::SignalBuilt: return c != nullptr && c->infrastructure.signal >= 1;
		case BrowserTutorialObjective::Train: return c != nullptr && c->group_all[VEH_TRAIN].num_vehicle >= 1;
		case BrowserTutorialObjective::MultiCargo: return c != nullptr && BrowserTutorialDeliveredCargoKinds(c) >= 2 && BrowserTutorialDeliveredCargo(c) >= 50;
		case BrowserTutorialObjective::DockBuilt: return c != nullptr && c->infrastructure.station >= 5;
		case BrowserTutorialObjective::Ship: return c != nullptr && c->group_all[VEH_SHIP].num_vehicle >= 1;
		case BrowserTutorialObjective::Airport: return c != nullptr && c->infrastructure.airport >= 1;
		case BrowserTutorialObjective::Aircraft: return c != nullptr && c->group_all[VEH_AIRCRAFT].num_vehicle >= 1;
	}
	return false;
}
static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps[] = {
	{STR_BROWSER_TUTORIAL_LEVEL_01, SPR_IMG_ZOOMIN, BrowserTutorialTarget::MainToolbar, WID_TN_ZOOM_IN, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_02, SPR_IMG_PAUSE, BrowserTutorialTarget::MainToolbar, WID_TN_PAUSE, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_03, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_04, SPR_IMG_BUILDROAD, BrowserTutorialTarget::MainToolbar, WID_TN_ROADS, BrowserTutorialObjective::RoadToolbarOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_05, SPR_IMG_AUTOROAD, BrowserTutorialTarget::RoadToolbar, WID_ROT_AUTOROAD, BrowserTutorialObjective::RoadBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_06, SPR_IMG_BUS_STATION, BrowserTutorialTarget::RoadToolbar, WID_ROT_BUS_STATION, BrowserTutorialObjective::Station2},
	{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicle},
	{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::FirstDelivery},
	{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_COMPANY_FINANCE, BrowserTutorialTarget::MainToolbar, WID_TN_FINANCES, BrowserTutorialObjective::PositiveIncome},
	{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::Station4},
	{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::SignalBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_14, SPR_IMG_TRAINLIST, BrowserTutorialTarget::MainToolbar, WID_TN_TRAINS, BrowserTutorialObjective::Train},
	{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_TRAINLIST, BrowserTutorialTarget::MainToolbar, WID_TN_TRAINS, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_16, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_17, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_18, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::MultiCargo},
	{STR_BROWSER_TUTORIAL_LEVEL_19, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER, BrowserTutorialObjective::DockBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_21, SPR_IMG_SHIPLIST, BrowserTutorialTarget::MainToolbar, WID_TN_SHIPS, BrowserTutorialObjective::Ship},
	{STR_BROWSER_TUTORIAL_LEVEL_22, SPR_IMG_BUILDAIR, BrowserTutorialTarget::MainToolbar, WID_TN_AIR, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_23, SPR_IMG_BUILDAIR, BrowserTutorialTarget::MainToolbar, WID_TN_AIR, BrowserTutorialObjective::Airport},
	{STR_BROWSER_TUTORIAL_LEVEL_24, SPR_IMG_AIRPLANESLIST, BrowserTutorialTarget::MainToolbar, WID_TN_AIRCRAFT, BrowserTutorialObjective::Aircraft},
	{STR_BROWSER_TUTORIAL_LEVEL_25, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::PositiveIncome},
	{STR_BROWSER_TUTORIAL_LEVEL_26, SPR_IMG_LANDSCAPING, BrowserTutorialTarget::MainToolbar, WID_TN_LANDSCAPE, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_27, SPR_IMG_GRAPHS, BrowserTutorialTarget::MainToolbar, WID_TN_GRAPHS, BrowserTutorialObjective::PositiveIncome},
	{STR_BROWSER_TUTORIAL_LEVEL_28, SPR_IMG_SAVE, BrowserTutorialTarget::MainToolbar, WID_TN_SAVE, BrowserTutorialObjective::None},
};

'''
intro = intro[:start] + logic + intro[end:]

old = '''\tvoid UpdateStep()\n\t{\n\t\tBrowserTutorialClearHighlights();\n\t\tthis->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);\n\t\tconst auto &current = _browser_tutorial_level_steps[this->step];\n\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {\n\t\t\ttarget->SetWidgetHighlight(current.widget, TC_YELLOW);\n\t\t}\n\t\tthis->SetDirty();\n\t}\n'''
new = '''\tvoid UpdateStep()\n\t{\n\t\tBrowserTutorialClearHighlights();\n\t\tthis->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);\n\t\tconst auto &current = _browser_tutorial_level_steps[this->step];\n\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !BrowserTutorialObjectiveComplete(current.objective));\n\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) target->SetWidgetHighlight(current.widget, TC_YELLOW);\n\t\tthis->SetDirty();\n\t}\n'''
if old not in intro: raise SystemExit("coach UpdateStep missing")
intro = intro.replace(old, new, 1)
old = '''\tvoid OnRealtimeTick([[maybe_unused]] uint delta_ms) override\n\t{\n\t\tconst auto &current = _browser_tutorial_level_steps[this->step];\n\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {\n\t\t\tif (!target->IsWidgetHighlighted(current.widget)) target->SetWidgetHighlight(current.widget, TC_YELLOW);\n\t\t}\n\t\tthis->SetDirty();\n\t}\n'''
new = '''\tvoid OnRealtimeTick([[maybe_unused]] uint delta_ms) override\n\t{\n\t\tconst auto &current = _browser_tutorial_level_steps[this->step];\n\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !BrowserTutorialObjectiveComplete(current.objective));\n\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {\n\t\t\tif (!target->IsWidgetHighlighted(current.widget)) target->SetWidgetHighlight(current.widget, TC_YELLOW);\n\t\t}\n\t\tthis->SetDirty();\n\t}\n'''
if old not in intro: raise SystemExit("coach realtime tick missing")
intro = intro.replace(old, new, 1)
old = '''\t\tif (widget == WID_BTC_NEXT) {\n\t\t\tif (this->step + 1 < std::size(_browser_tutorial_level_steps)) {\n'''
new = '''\t\tif (widget == WID_BTC_NEXT) {\n\t\t\tif (!BrowserTutorialObjectiveComplete(_browser_tutorial_level_steps[this->step].objective)) return;\n\t\t\tif (this->step + 1 < std::size(_browser_tutorial_level_steps)) {\n'''
if old not in intro: raise SystemExit("coach Next handler missing")
intro = intro.replace(old, new, 1)

start = intro.find("void StartBrowserTutorialLevel()\n{")
end = intro.find("\nvoid ShowBrowserTutorial()", start)
if start < 0 or end < 0: raise SystemExit("tutorial world functions missing")
world = r'''struct BrowserTutorialSavedSettings {
	decltype(_settings_newgame.game_creation.map_x) map_x{};
	decltype(_settings_newgame.game_creation.map_y) map_y{};
	decltype(_settings_newgame.game_creation.landscape) landscape{};
	decltype(_settings_newgame.game_creation.amount_of_rivers) amount_of_rivers{};
	decltype(_settings_newgame.game_creation.water_border_presets) water_border_presets{};
	decltype(_settings_newgame.game_creation.custom_town_number) custom_town_number{};
	decltype(_settings_newgame.game_creation.custom_industry_number) custom_industry_number{};
	decltype(_settings_newgame.difficulty.terrain_type) terrain_type{};
	decltype(_settings_newgame.difficulty.quantity_sea_lakes) quantity_sea_lakes{};
	decltype(_settings_newgame.difficulty.number_towns) number_towns{};
	decltype(_settings_newgame.difficulty.industry_density) industry_density{};
	decltype(_settings_newgame.difficulty.max_loan) max_loan{};
	decltype(_settings_newgame.difficulty.vehicle_breakdowns) vehicle_breakdowns{};
	decltype(_settings_newgame.difficulty.construction_cost) construction_cost{};
	decltype(_settings_newgame.difficulty.vehicle_costs) vehicle_costs{};
	decltype(_settings_newgame.difficulty.town_council_tolerance) town_council_tolerance{};
	decltype(_settings_newgame.difficulty.disasters) disasters{};
};
static BrowserTutorialSavedSettings _browser_tutorial_saved_settings{};
static bool _browser_tutorial_settings_saved = false;
static void BrowserTutorialSaveNewGameSettings()
{
	if (_browser_tutorial_settings_saved) return;
	auto &s = _browser_tutorial_saved_settings;
	s.map_x = _settings_newgame.game_creation.map_x; s.map_y = _settings_newgame.game_creation.map_y;
	s.landscape = _settings_newgame.game_creation.landscape; s.amount_of_rivers = _settings_newgame.game_creation.amount_of_rivers;
	s.water_border_presets = _settings_newgame.game_creation.water_border_presets;
	s.custom_town_number = _settings_newgame.game_creation.custom_town_number; s.custom_industry_number = _settings_newgame.game_creation.custom_industry_number;
	s.terrain_type = _settings_newgame.difficulty.terrain_type; s.quantity_sea_lakes = _settings_newgame.difficulty.quantity_sea_lakes;
	s.number_towns = _settings_newgame.difficulty.number_towns; s.industry_density = _settings_newgame.difficulty.industry_density;
	s.max_loan = _settings_newgame.difficulty.max_loan; s.vehicle_breakdowns = _settings_newgame.difficulty.vehicle_breakdowns;
	s.construction_cost = _settings_newgame.difficulty.construction_cost; s.vehicle_costs = _settings_newgame.difficulty.vehicle_costs;
	s.town_council_tolerance = _settings_newgame.difficulty.town_council_tolerance; s.disasters = _settings_newgame.difficulty.disasters;
	_browser_tutorial_settings_saved = true;
}
static void BrowserTutorialRestoreNewGameSettings()
{
	if (!_browser_tutorial_settings_saved) return;
	const auto &s = _browser_tutorial_saved_settings;
	_settings_newgame.game_creation.map_x = s.map_x; _settings_newgame.game_creation.map_y = s.map_y;
	_settings_newgame.game_creation.landscape = s.landscape; _settings_newgame.game_creation.amount_of_rivers = s.amount_of_rivers;
	_settings_newgame.game_creation.water_border_presets = s.water_border_presets;
	_settings_newgame.game_creation.custom_town_number = s.custom_town_number; _settings_newgame.game_creation.custom_industry_number = s.custom_industry_number;
	_settings_newgame.difficulty.terrain_type = s.terrain_type; _settings_newgame.difficulty.quantity_sea_lakes = s.quantity_sea_lakes;
	_settings_newgame.difficulty.number_towns = s.number_towns; _settings_newgame.difficulty.industry_density = s.industry_density;
	_settings_newgame.difficulty.max_loan = s.max_loan; _settings_newgame.difficulty.vehicle_breakdowns = s.vehicle_breakdowns;
	_settings_newgame.difficulty.construction_cost = s.construction_cost; _settings_newgame.difficulty.vehicle_costs = s.vehicle_costs;
	_settings_newgame.difficulty.town_council_tolerance = s.town_council_tolerance; _settings_newgame.difficulty.disasters = s.disasters;
	_browser_tutorial_settings_saved = false;
}
void StartBrowserTutorialLevel()
{
	_is_network_server = false;
	BrowserTutorialSaveNewGameSettings();
	_settings_newgame.game_creation.map_x = 6; _settings_newgame.game_creation.map_y = 6;
	_settings_newgame.game_creation.landscape = LandscapeType::Temperate;
	_settings_newgame.game_creation.amount_of_rivers = 0; _settings_newgame.game_creation.water_border_presets = BFP_INFINITE_WATER;
	_settings_newgame.game_creation.custom_town_number = 8; _settings_newgame.game_creation.custom_industry_number = 16;
	_settings_newgame.difficulty.terrain_type = 0; _settings_newgame.difficulty.quantity_sea_lakes = 2;
	_settings_newgame.difficulty.number_towns = 4; _settings_newgame.difficulty.industry_density = ID_CUSTOM;
	_settings_newgame.difficulty.max_loan = 1000000; _settings_newgame.difficulty.vehicle_breakdowns = 0;
	_settings_newgame.difficulty.construction_cost = 0; _settings_newgame.difficulty.vehicle_costs = 0;
	_settings_newgame.difficulty.town_council_tolerance = 0; _settings_newgame.difficulty.disasters = false;
	_browser_tutorial_pending = true; _browser_tutorial_active = false;
	StartNewGameWithoutGUI(0x4F545444U);
}
void BrowserTutorialGameStarted()
{
	if (!_browser_tutorial_pending) return;
	_browser_tutorial_pending = false; _browser_tutorial_active = true;
	_settings_game.difficulty.max_no_competitors = 0;
	BrowserTutorialRestoreNewGameSettings();
	CloseWindowByClass(WC_HELPWIN);
	new BrowserTutorialCoachWindow();
}
'''
intro = intro[:start] + world + intro[end:]
intro_path.write_text(intro, encoding="utf-8")

for path in (english, russian):
    browser = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("STR_BROWSER_"))
    if "—" in browser or "→" in browser: raise SystemExit(f"font-unsafe browser punctuation in {path}")
for marker in ("STR_BROWSER_TUTORIAL_LEVEL_28", "BrowserTutorialObjective::Aircraft", "c->group_all[VEH_SHIP].num_vehicle", "custom_industry_number = 16", "BrowserTutorialRestoreNewGameSettings();"):
    if marker not in intro and marker not in english.read_text(encoding="utf-8") and marker not in russian.read_text(encoding="utf-8"):
        raise SystemExit(f"tutorial marker missing: {marker}")
print("Restored 28 objective-gated training steps, 12 overview pages and a temporary dedicated practice world.")
