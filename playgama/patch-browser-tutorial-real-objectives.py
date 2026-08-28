#!/usr/bin/env python3
"""Replace tutorial proxy checks with actual OpenTTD state/facility checks."""
from __future__ import annotations

import re
from pathlib import Path


def set_string(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(rf'^({re.escape(key)}\s*:).*$', re.M)
    if not pattern.search(text):
        raise SystemExit(f'missing language key {key}')
    path.write_text(pattern.sub(lambda m: m.group(1) + value, text, count=1), encoding='utf-8')

ru = Path('openttd/src/lang/russian.txt')
en = Path('openttd/src/lang/english.txt')
set_string(ru, 'STR_BROWSER_TUTORIAL_COACH_CAPTION', 'Практическое обучение - реальные цели')
set_string(en, 'STR_BROWSER_TUTORIAL_COACH_CAPTION', 'Practical training - real objectives')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_15', '15/28 - Задания поезда{}Запустите поезд по настоящему маршруту. Далее откроется только после того, как поезд посетит минимум две ваши железнодорожные станции.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_15', '15/28 - Train service{}Run the train on a real route. Next unlocks only after the train has visited at least two of your rail stations.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_17', '17/28 - Грузовой маршрут{}Постройте минимум две грузовые станции у предприятий. Станции должны иметь железнодорожную или грузовую автомобильную инфраструктуру и находиться рядом с предприятиями.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_17', '17/28 - Cargo route{}Build at least two cargo stations by industries. They must have rail or truck facilities and be within reach of industries.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_20', '20/28 - Причалы{}Постройте два настоящих причала с доступом к воде - по одному на каждом конце будущего маршрута.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_20', '20/28 - Docks{}Build two real docks with water access, one at each end of the future route.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_21', '21/28 - Корабль{}Купите корабль, задайте маршрут и запустите его. Далее откроется только после посещения кораблём двух ваших причалов.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_21', '21/28 - Ship service{}Buy a ship, assign a route and start it. Next unlocks only after a ship has visited two of your docks.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_23', '23/28 - Аэропорты{}Постройте два аэропорта рядом с городами. Для реального воздушного маршрута нужны обе конечные точки.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_23', '23/28 - Airports{}Build two airports near towns. A real air route needs both endpoints.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_24', '24/28 - Самолёт{}Купите самолёт, задайте два аэропорта и запустите его. Далее откроется после посещения самолётом двух ваших аэропортов.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_24', '24/28 - Aircraft service{}Buy an aircraft, assign two airports and start it. Next unlocks after the aircraft has visited two of your airports.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_25', '25/28 - Рост городов{}Ваша сеть должна реально обслуживать минимум два города и иметь положительный транспортный доход.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_25', '25/28 - Town growth{}Your network must actually serve at least two towns and have positive transport income.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_26', '26/28 - Рельеф, мосты и тоннели{}Откройте инструменты изменения ландшафта. Далее станет доступно только после открытия панели инструментов рельефа.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_26', '26/28 - Terrain, bridges and tunnels{}Open the landscaping tools. Next unlocks only after the landscaping toolbar is open.')
set_string(ru, 'STR_BROWSER_TUTORIAL_LEVEL_27', '27/28 - Развитие компании{}Откройте любой график компании и оцените результат сети. Далее станет доступно после открытия графика.')
set_string(en, 'STR_BROWSER_TUTORIAL_LEVEL_27', '27/28 - Company progress{}Open any company graph and review your network. Next unlocks after a graph is open.')

p = Path('openttd/src/intro_gui.cpp')
s = p.read_text(encoding='utf-8')
include_anchor = '#include "company_base.h"\n'
extra = '#include "station_base.h"\n#include "station_type.h"\n#include "town.h"\n'
if '#include "station_base.h"' not in s:
    if include_anchor not in s:
        raise SystemExit('company include anchor missing')
    s = s.replace(include_anchor, include_anchor + extra, 1)

start = s.find('enum class BrowserTutorialObjective : uint8_t {')
if start < 0:
    raise SystemExit('tutorial objective enum missing')
table_start = s.find('static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps[] = {', start)
if table_start < 0:
    raise SystemExit('tutorial step table missing')
table_end = s.find('\n};', table_start)
if table_end < 0:
    raise SystemExit('tutorial step table end missing')
table_end += len('\n};')

logic_and_table = r'''enum class BrowserTutorialObjective : uint8_t {
	None,
	PauseUsed,
	TownDirectoryOpen,
	RoadToolbarOpen,
	RoadBuilt,
	BusStops2,
	RoadVehicle,
	FirstDelivery,
	FinancePositive,
	RailToolbarOpen,
	RailBuilt,
	RailStations2,
	SignalBuilt,
	Train,
	TrainService,
	IndustryDirectoryOpen,
	CargoInfrastructure,
	MultiCargo,
	WaterToolbarOpen,
	Docks2,
	ShipService,
	AirToolbarOpen,
	Airports2,
	AircraftService,
	TownNetwork,
	LandscapeToolbarOpen,
	GraphOpen,
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
static uint BrowserTutorialOwnedFacilityCount(const Company *c, StationFacility facility)
{
	if (c == nullptr) return 0;
	uint count = 0;
	for (const Station *st : Station::Iterate()) {
		if (st->owner == c->index && st->facilities.Test(facility)) ++count;
	}
	return count;
}
static uint BrowserTutorialVisitedFacilityCount(const Company *c, StationFacility facility, StationHadVehicleOfType vehicle)
{
	if (c == nullptr) return 0;
	uint count = 0;
	for (const Station *st : Station::Iterate()) {
		if (st->owner != c->index || !st->facilities.Test(facility)) continue;
		if ((st->had_vehicle_of_type & vehicle) != 0) ++count;
	}
	return count;
}
static uint BrowserTutorialCargoIndustryStationCount(const Company *c)
{
	if (c == nullptr) return 0;
	uint count = 0;
	for (const Station *st : Station::Iterate()) {
		if (st->owner != c->index || st->industries_near.empty()) continue;
		if (st->facilities.Test(StationFacility::Train) || st->facilities.Test(StationFacility::TruckStop)) ++count;
	}
	return count;
}
static uint BrowserTutorialServedTownCount(const Company *c)
{
	if (c == nullptr) return 0;
	uint count = 0;
	for (const Town *town : Town::Iterate()) {
		bool served = false;
		for (const Station *st : Station::Iterate()) {
			if (st->owner != c->index) continue;
			if (st->had_vehicle_of_type == HVOT_NONE) continue;
			if (st->CatchmentCoversTown(town->index)) { served = true; break; }
		}
		if (served) ++count;
	}
	return count;
}
static bool BrowserTutorialAnyGraphOpen()
{
	return FindWindowByClass(WC_INCOME_GRAPH) != nullptr ||
			FindWindowByClass(WC_OPERATING_PROFIT) != nullptr ||
			FindWindowByClass(WC_DELIVERED_CARGO) != nullptr ||
			FindWindowByClass(WC_PERFORMANCE_HISTORY) != nullptr ||
			FindWindowByClass(WC_COMPANY_VALUE) != nullptr ||
			FindWindowByClass(WC_PAYMENT_RATES) != nullptr;
}
static bool BrowserTutorialObjectiveComplete(BrowserTutorialObjective objective)
{
	const Company *c = BrowserTutorialCompany();
	switch (objective) {
		case BrowserTutorialObjective::None: return true;
		case BrowserTutorialObjective::PauseUsed: return _pause_mode.Any();
		case BrowserTutorialObjective::TownDirectoryOpen: return FindWindowByClass(WC_TOWN_DIRECTORY) != nullptr;
		case BrowserTutorialObjective::RoadToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD) != nullptr;
		case BrowserTutorialObjective::RoadBuilt: return c != nullptr && c->infrastructure.GetRoadTotal() >= 8;
		case BrowserTutorialObjective::BusStops2: return BrowserTutorialOwnedFacilityCount(c, StationFacility::BusStop) >= 2;
		case BrowserTutorialObjective::RoadVehicle: return c != nullptr && c->group_all[VEH_ROAD].num_vehicle >= 1;
		case BrowserTutorialObjective::FirstDelivery: return BrowserTutorialDeliveredCargo(c) >= 10;
		case BrowserTutorialObjective::FinancePositive: return FindWindowByClass(WC_FINANCES) != nullptr && BrowserTutorialHasPositiveIncome(c);
		case BrowserTutorialObjective::RailToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL) != nullptr;
		case BrowserTutorialObjective::RailBuilt: return c != nullptr && c->infrastructure.GetRailTotal() >= 8;
		case BrowserTutorialObjective::RailStations2: return BrowserTutorialOwnedFacilityCount(c, StationFacility::Train) >= 2;
		case BrowserTutorialObjective::SignalBuilt: return c != nullptr && c->infrastructure.signal >= 1;
		case BrowserTutorialObjective::Train: return c != nullptr && c->group_all[VEH_TRAIN].num_vehicle >= 1;
		case BrowserTutorialObjective::TrainService: return c != nullptr && c->group_all[VEH_TRAIN].num_vehicle >= 1 && BrowserTutorialVisitedFacilityCount(c, StationFacility::Train, HVOT_TRAIN) >= 2;
		case BrowserTutorialObjective::IndustryDirectoryOpen: return FindWindowByClass(WC_INDUSTRY_DIRECTORY) != nullptr;
		case BrowserTutorialObjective::CargoInfrastructure: return BrowserTutorialCargoIndustryStationCount(c) >= 2;
		case BrowserTutorialObjective::MultiCargo: return c != nullptr && BrowserTutorialDeliveredCargoKinds(c) >= 2 && BrowserTutorialDeliveredCargo(c) >= 50;
		case BrowserTutorialObjective::WaterToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_WATER) != nullptr;
		case BrowserTutorialObjective::Docks2: return BrowserTutorialOwnedFacilityCount(c, StationFacility::Dock) >= 2;
		case BrowserTutorialObjective::ShipService: return c != nullptr && c->group_all[VEH_SHIP].num_vehicle >= 1 && BrowserTutorialVisitedFacilityCount(c, StationFacility::Dock, HVOT_SHIP) >= 2;
		case BrowserTutorialObjective::AirToolbarOpen: return FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_AIR) != nullptr;
		case BrowserTutorialObjective::Airports2: return BrowserTutorialOwnedFacilityCount(c, StationFacility::Airport) >= 2;
		case BrowserTutorialObjective::AircraftService: return c != nullptr && c->group_all[VEH_AIRCRAFT].num_vehicle >= 1 && BrowserTutorialVisitedFacilityCount(c, StationFacility::Airport, HVOT_AIRCRAFT) >= 2;
		case BrowserTutorialObjective::TownNetwork: return BrowserTutorialHasPositiveIncome(c) && BrowserTutorialServedTownCount(c) >= 2;
		case BrowserTutorialObjective::LandscapeToolbarOpen: return FindWindowByClass(WC_SCEN_LAND_GEN) != nullptr;
		case BrowserTutorialObjective::GraphOpen: return BrowserTutorialAnyGraphOpen();
	}
	return false;
}
static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps[] = {
	{STR_BROWSER_TUTORIAL_LEVEL_01, SPR_IMG_ZOOMIN, BrowserTutorialTarget::MainToolbar, WID_TN_ZOOM_IN, BrowserTutorialObjective::None},
	{STR_BROWSER_TUTORIAL_LEVEL_02, SPR_IMG_PAUSE, BrowserTutorialTarget::MainToolbar, WID_TN_PAUSE, BrowserTutorialObjective::PauseUsed},
	{STR_BROWSER_TUTORIAL_LEVEL_03, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::TownDirectoryOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_04, SPR_IMG_BUILDROAD, BrowserTutorialTarget::MainToolbar, WID_TN_ROADS, BrowserTutorialObjective::RoadToolbarOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_05, SPR_IMG_AUTOROAD, BrowserTutorialTarget::RoadToolbar, WID_ROT_AUTOROAD, BrowserTutorialObjective::RoadBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_06, SPR_IMG_BUS_STATION, BrowserTutorialTarget::RoadToolbar, WID_ROT_BUS_STATION, BrowserTutorialObjective::BusStops2},
	{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicle},
	{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::FirstDelivery},
	{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_COMPANY_FINANCE, BrowserTutorialTarget::MainToolbar, WID_TN_FINANCES, BrowserTutorialObjective::FinancePositive},
	{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailToolbarOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::RailStations2},
	{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS, BrowserTutorialObjective::SignalBuilt},
	{STR_BROWSER_TUTORIAL_LEVEL_14, SPR_IMG_TRAINLIST, BrowserTutorialTarget::MainToolbar, WID_TN_TRAINS, BrowserTutorialObjective::Train},
	{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_TRAINLIST, BrowserTutorialTarget::MainToolbar, WID_TN_TRAINS, BrowserTutorialObjective::TrainService},
	{STR_BROWSER_TUTORIAL_LEVEL_16, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::IndustryDirectoryOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_17, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::CargoInfrastructure},
	{STR_BROWSER_TUTORIAL_LEVEL_18, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES, BrowserTutorialObjective::MultiCargo},
	{STR_BROWSER_TUTORIAL_LEVEL_19, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER, BrowserTutorialObjective::WaterToolbarOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER, BrowserTutorialObjective::Docks2},
	{STR_BROWSER_TUTORIAL_LEVEL_21, SPR_IMG_SHIPLIST, BrowserTutorialTarget::MainToolbar, WID_TN_SHIPS, BrowserTutorialObjective::ShipService},
	{STR_BROWSER_TUTORIAL_LEVEL_22, SPR_IMG_BUILDAIR, BrowserTutorialTarget::MainToolbar, WID_TN_AIR, BrowserTutorialObjective::AirToolbarOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_23, SPR_IMG_BUILDAIR, BrowserTutorialTarget::MainToolbar, WID_TN_AIR, BrowserTutorialObjective::Airports2},
	{STR_BROWSER_TUTORIAL_LEVEL_24, SPR_IMG_AIRPLANESLIST, BrowserTutorialTarget::MainToolbar, WID_TN_AIRCRAFT, BrowserTutorialObjective::AircraftService},
	{STR_BROWSER_TUTORIAL_LEVEL_25, SPR_IMG_TOWN, BrowserTutorialTarget::MainToolbar, WID_TN_TOWNS, BrowserTutorialObjective::TownNetwork},
	{STR_BROWSER_TUTORIAL_LEVEL_26, SPR_IMG_LANDSCAPING, BrowserTutorialTarget::MainToolbar, WID_TN_LANDSCAPE, BrowserTutorialObjective::LandscapeToolbarOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_27, SPR_IMG_GRAPHS, BrowserTutorialTarget::MainToolbar, WID_TN_GRAPHS, BrowserTutorialObjective::GraphOpen},
	{STR_BROWSER_TUTORIAL_LEVEL_28, SPR_IMG_SAVE, BrowserTutorialTarget::MainToolbar, WID_TN_SAVE, BrowserTutorialObjective::None},
};'''

s = s[:start] + logic_and_table + s[table_end:]
for marker in (
    'BrowserTutorialObjective::TrainService',
    'StationFacility::Dock) >= 2',
    'HVOT_SHIP',
    'HVOT_AIRCRAFT',
    'BrowserTutorialCargoIndustryStationCount',
    'BrowserTutorialServedTownCount',
):
    if marker not in s:
        raise SystemExit(f'missing deep tutorial marker {marker}')
p.write_text(s, encoding='utf-8')
print('Tutorial proxy objectives replaced with real OpenTTD station/service/window state checks.')
