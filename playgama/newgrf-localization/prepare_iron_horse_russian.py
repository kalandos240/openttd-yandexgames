#!/usr/bin/env python3
"""Generate a strict native Russian language table for Iron Horse 4.29.0.

Proper/programmatic livery names are intentionally preserved.  Gameplay prose,
parameters, behaviours, roles, wagon classes, power and railtype UI are Russian.
Unknown upstream strings fail the build instead of silently falling back to
English in the Russian OpenTTD UI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

RU_PRAGMA = {"grflangid": 0x07, "plural": 6}

TEXT = {
    "Engines": "Локомотивы",
    "Wagons": "Вагоны",
    "All": "Все",
    "Simplified": "Упрощённый набор",
    "None": "Нет",
    "Train capacity": "Вместимость поездов",
    "Nanoscopic": "Минимальная",
    "Puny": "Малая",
    "Marvellous (default)": "Обычная (по умолчанию)",
    "Excessive": "Большая",
    "Outrageous": "Огромная",
    "Wagon colour fading": "Выцветание окраски вагонов",
    "Build some vehicles reversed": "Иногда строить транспорт развёрнутым",
    "Livery": "Окраска",
    "Company Colour": "Цвет компании",
    "Company Colour Adjacent": "Соседний оттенок цвета компании",
    "Company Colour Mix": "Смесь цветов компании",
    "Behaviour": "Особенность",
    "No gameplay effect": "Не влияет на игровой процесс",
    "Express haulable": "Подходит для экспресс-перевозок",
    "High speed capable": "Поддерживает высокую скорость",
    "Randomised choice of wagon": "Случайный вариант вагона",
    "Tilts for faster cornering": "Наклоняется для более быстрого прохождения поворотов",
    "Role": "Роль",
    "Driving Cab": "Вагон управления",
    "General Purpose": "Универсальный",
    "Express": "Экспресс",
    "Freight": "Грузовой",
    "Very High Capacity Urban": "Городской, особо высокой вместимости",
    "Urban Freight": "Городской грузовой",
    "High Capacity": "Высокая вместимость",
    "Gen": "Поколение",
    "Trailer": "Прицепной вагон",
    "(Cars)": "(Автомобили)",
    "(Trucks)": "(Грузовики)",
    "Power Source": "Источник тяги",
    "Electric": "Электрический",
    "Battery Hybrid": "Аккумуляторный гибрид",
    "Metro": "Метро",
    "Diesel": "Дизельный",
    "Steam": "Паровой",
    "{}Sprites Complete: {GOLD}Yup": "{}Спрайты готовы: {GOLD}Да",
    "{}Sprites Complete: {GOLD}Nope": "{}Спрайты готовы: {GOLD}Нет",
    "Dedicated High Speed Railway": "Выделенная высокоскоростная железная дорога",
    "[unused]": "[не используется]",
    "New Dedicated High Speed Vehicles": "Новый высокоскоростной железнодорожный транспорт",
    "Dedicated High Speed Vehicles": "Высокоскоростной железнодорожный транспорт",
    "high speed rail vehicle": "высокоскоростной железнодорожный транспорт",
    "Dedicated High Speed Railway Construction": "Строительство высокоскоростной железной дороги",
    "Dedicated high speed railway construction": "Строительство высокоскоростной железной дороги",
    "Metro Railway": "Железная дорога метро",
    "Metro Railway Construction": "Строительство метро",
    "Metro railway construction": "Строительство метро",
    "New Metro Vehicles": "Новый транспорт метро",
    "Metro Rail Vehicles": "Железнодорожный транспорт метро",
    "metro rail vehicle": "железнодорожный транспорт метро",
    "Narrow Gauge Railway": "Узкоколейная железная дорога",
    "Narrow Gauge Railway Construction": "Строительство узкоколейной железной дороги",
    "Narrow gauge railway construction": "Строительство узкоколейной железной дороги",
    "New Narrow Gauge Vehicles": "Новый узкоколейный транспорт",
    "Narrow Gauge Rail Vehicles": "Узкоколейный железнодорожный транспорт",
    "narrow gauge rail vehicle": "узкоколейный железнодорожный транспорт",
    "Electrified Narrow Gauge Railway": "Электрифицированная узкоколейная железная дорога",
    "Electrified Narrow Gauge Railway Construction": "Строительство электрифицированной узкоколейной железной дороги",
    "Electrified narrow gauge railway construction": "Строительство электрифицированной узкоколейной железной дороги",
    "New Electrified Narrow Gauge Vehicles": "Новый электрифицированный узкоколейный транспорт",
    "Electrified Narrow Gauge Vehicles": "Электрифицированный узкоколейный транспорт",
    "electrified narrow gauge rail vehicle": "электрифицированный узкоколейный железнодорожный транспорт",
}

PROSE = {
    "STR_GRF_DESCRIPTION": "{ORANGE}Iron Horse (Trains){}{BLACK}Полный набор поездов, ориентированный на игровой процесс: паровые, дизельные и электрические поезда периода 1860–2020 годов. Также включает высокоскоростные и узкоколейные поезда, а также поезда метро. В основном вдохновлён железными дорогами Великобритании и Ирландии.{SILVER}Дополнительная информация доступна на сайте проекта. {BLACK}Лицензия: GPL v2",
    "STR_PARAM_VEHICLE_AVAILABILITY_ENGINES_DESC": "Используйте все локомотивы, упрощённый набор или отключите их полностью. {}{}{SILVER}Все: {BLACK}доступен полный набор локомотивов Iron Horse. {}{}{SILVER}Упрощённый: {BLACK}доступно меньше локомотивов; декоративные поезда, снегоочистители, вагоны управления и очень медленные локомотивы исключены.{}{}{SILVER}Нет: {BLACK}локомотивы Iron Horse недоступны. Этот режим оставляет только вагоны Iron Horse и требует локомотивы из другого NewGRF.",
    "STR_PARAM_VEHICLE_AVAILABILITY_WAGONS_DESC": "Используйте все вагоны, упрощённый набор или отключите их полностью. {}{}{SILVER}Все: {BLACK}доступен полный набор вагонов Iron Horse. {}{}{SILVER}Упрощённый: {BLACK}доступно меньше вагонов. {}{}{SILVER}Нет: {BLACK}вагоны Iron Horse недоступны.",
    "STR_PARAM_ADJUST_VEHICLE_CAPACITY_DESC": "Настройте вместимость транспорта под выбранный стиль игры.{}{}{SILVER}Минимальная: {BLACK}на 77% меньше{SILVER}{}Малая: {BLACK}на 33% меньше{SILVER}{}Обычная: {BLACK}по умолчанию{SILVER}{}Большая: {BLACK}на 33% больше{SILVER}{}Огромная: {BLACK}на 77% больше{BLACK}",
    "STR_PARAM_WAGON_COLOUR_RANDOMISATION_STRATEGY_DESC": "Выцветшая окраска грузовых вагонов добавляет разнообразие составам; для каждого вагона вариант выбирается случайно.",
    "STR_PARAM_VEHICLE_RANDOM_REVERSE_ON_BUILD_DESC": "Iron Horse может случайно строить часть транспорта развёрнутой, например танк-паровозы или тепловозы с кабинами с обоих концов. Этот параметр позволяет отключить такое поведение.",
    "STR_BADGE_BEHAVIOUR_DRIVING_CAB": "Вагон управления{BLACK} — установите спереди или сзади состава вместе как минимум с одним локомотивом",
    "STR_BADGE_BEHAVIOUR_POST_OFFICE_CAR": "Убирает эксплуатационные расходы всех почтовых и высокоскоростных почтовых вагонов в составе",
    "STR_BADGE_BEHAVIOUR_RESTAURANT_CAR": "Убирает эксплуатационные расходы всех пассажирских и высокоскоростных пассажирских вагонов в составе",
    "STR_POWER_BY_POWER_SOURCE_TWO_SOURCES": "{BLACK}Мощность на {STRING}: {GOLD}{POWER} {}{BLACK}Мощность на {STRING}: {GOLD}{POWER}",
    "STR_SPEED_BY_RAILTYPE_LGV_CAPABLE": "{BLACK}Скорость (выделенная высокоскоростная линия): {GOLD}{VELOCITY} {}{BLACK}Скорость (обычная линия): {GOLD}{VELOCITY}",
    "STR_WAGONS_ADD_POWER_CAB": "{BLACK}Распределённая мощность: {GOLD}{POWER} за каждый присоединённый пассажирский или почтовый вагон {STRING}",
    "STR_WAGONS_ADD_POWER_CAB_CARGO_SPRINTER": "{BLACK}Распределённая мощность: {GOLD}{POWER} за каждый присоединённый моторный прицепной вагон {STRING}",
    "STR_WAGONS_ADD_POWER_MIDDLE": "{BLACK}Распределённая мощность: {GOLD}{POWER} при присоединении к локомотиву {STRING}",
}

WAGONS = {
    "Acid Tanker": "Цистерна для кислоты", "Stone Wagon": "Вагон для камня",
    "Aggregate Hopper": "Хоппер для заполнителя", "Alignment Van": "Путеизмерительный вагон",
    "Vehicle Transporter": "Вагон-автовоз", "Bolster Wagon": "Платформа со стойками",
    "Box Van": "Крытый вагон", "Mine Hopper": "Рудничный хоппер", "Mineral Wagon": "Вагон для минеральных грузов",
    "Quarry Open Wagon": "Открытый карьерный вагон", "Quarry Hopper": "Карьерный хоппер",
    "Bulkhead Flat Wagon": "Платформа с торцевыми стенками", "Brake Van": "Тормозной вагон",
    "Cane Bin": "Вагон для сахарного тростника", "Carbon Black Hopper": "Хоппер для технического углерода",
    "Cement Wagon": "Вагон для цемента", "Chemical Tanker": "Химическая цистерна", "Coal Hopper": "Угольный хоппер",
    "Coil Buggies": "Тележки для рулонов", "Coil Carrier": "Вагон для рулонов", "Covered Hopper": "Крытый хоппер",
    "Cryo Tanker": "Криогенная цистерна", "Curtain Side Van": "Крытый вагон со шторными бортами",
    "Car Transporter": "Вагон-автовоз", "Machinery Wagon": "Вагон для оборудования", "Motorail Van": "Вагон-автовоз Motorail",
    "Express Van": "Экспрессный крытый вагон", "Express Container Wagon": "Экспрессный контейнерный вагон",
    "Grain Hopper": "Зерновой хоппер", "Agricultural Wagon": "Сельскохозяйственный вагон",
    "Farm Product Van": "Крытый вагон для сельхозпродукции", "Farm Product Hopper": "Хоппер для сельхозпродукции",
    "General Flat Wagon": "Универсальная платформа", "Flat Wagon": "Платформа",
    "Express Food Van": "Экспрессный пищевой вагон", "Express Beverage Wagon": "Экспрессный вагон для напитков",
    "Express Food Tanker": "Экспрессная пищевая цистерна", "Food Product Hopper": "Хоппер для пищевых продуктов",
    "Food Ingredients Hopper": "Хоппер для пищевых ингредиентов", "Food Ingredients Wagon": "Вагон для пищевых ингредиентов",
    "Heavy Duty Bulk Wagon": "Тяжёлый вагон для навалочных грузов", "Heavy Duty Flat Wagon": "Тяжёлая платформа",
    "High Speed Mail Van": "Высокоскоростной почтовый вагон", "High Speed Coach": "Высокоскоростной пассажирский вагон",
    "Hood Open Wagon": "Открытый вагон с кожухом", "Mail Van": "Почтовый вагон", "Passenger Coach": "Пассажирский вагон",
    "Ingot Carriers": "Вагон для слитков", "Container Wagon": "Контейнерный вагон", "Lime Hopper": "Хоппер для извести",
    "Livestock Wagon": "Вагон для скота", "Livestock Express Van": "Экспрессный вагон для скота", "Log Carrier": "Вагон для брёвен",
    "Merchandise Van": "Крытый товарный вагон", "Covered Steel Wagon": "Крытый вагон для стали", "Steel Wagon": "Вагон для стали",
    "Metro Mail Van": "Почтовый вагон метро", "Metro Coach": "Пассажирский вагон метро", "Coal Wagon": "Угольный вагон",
    "Sand Wagon": "Вагон для песка", "Covered Mineral Hopper": "Крытый минеральный хоппер", "MGR Hopper": "Хоппер MGR",
    "Mill Flat Wagon": "Заводская платформа", "Mill Open Wagon": "Заводской открытый вагон", "General Open Wagon": "Универсальный открытый вагон",
    "Open Wagon": "Открытый вагон", "Ore Hopper": "Рудный хоппер", "Panoramic Coach": "Панорамный пассажирский вагон",
    "Peat Wagon": "Торфяной вагон", "Covered Goods Wagon": "Крытый грузовой вагон", "Easy-loading Covered Wagon": "Крытый вагон с облегчённой погрузкой",
    "Goods Wagon": "Грузовой вагон", "Manufacturing Parts Wagon": "Вагон для промышленных деталей", "Pipe Wagon": "Вагон для труб",
    "Travelling Post Office": "Почтовый вагон", "Pressure Tanker": "Цистерна высокого давления", "Product Tanker": "Продуктовая цистерна",
    "Refrigerated Van": "Рефрижераторный вагон", "Restaurant Car": "Вагон-ресторан", "Rock Hopper": "Каменный хоппер",
    "Roller Roof Hopper": "Хоппер с рулонной крышей", "Salt Hopper": "Соляной хоппер", "Scrap Wagon": "Вагон для металлолома",
    "Side Door Hopper": "Хоппер с боковой разгрузкой", "Silo Wagon": "Вагон-силос", "Skips": "Вагоны-скипы",
    "Slag Ladle Wagon": "Вагон со шлаковозным ковшом", "Sliding Roof Wagon": "Вагон со сдвижной крышей", "Cube Wagon": "Высококубатурный вагон",
    "Sliding Wall Van": "Крытый вагон со сдвижными стенами", "Spacer Wagon": "Вагон-прикрытие", "Suburban Coach": "Пригородный пассажирский вагон",
    "Swing Roof Hopper": "Хоппер с откидной крышей", "General Tanker": "Универсальная цистерна", "Tarpaulin Wagon": "Вагон с тентом",
    "Tippler Wagon": "Опрокидываемый вагон", "Torpedo Wagon": "Вагон-торпеда", "Volatiles Tanker": "Цистерна для летучих веществ",
}

LIVERY_DOCS = {
    "STR_EXTRA_TEXT_LIVERY_BANGER_BLUE": "Очень простая окраска: преимущественно первый цвет компании с небольшими элементами второго цвета.",
    "STR_EXTRA_TEXT_LIVERY_CLASSIC_LINES": "Окраска преимущественно первым цветом компании с одной или несколькими горизонтальными полосами второго цвета.",
    "STR_EXTRA_TEXT_LIVERY_CONVENTIONAL_WISDOM": "Окраска с чередующимися крупными блоками обоих цветов компании и минималистичными обозначениями либо без них.",
    "STR_EXTRA_TEXT_LIVERY_FREIGHT_BLACK": "Окраска грузовых поездов: преимущественно тёмные, загрязнённые цвета с логотипами или отметками в одном либо обоих цветах компании.",
    "STR_EXTRA_TEXT_LIVERY_FRUIT_RIPPLE": "Окраска пассажирских и почтовых поездов, вдохновлённая схемами British Rail InterCity 'Swallow' и 'Executive'.",
    "STR_EXTRA_TEXT_LIVERY_GREY_HORSE": "Окраска грузовых поездов на основе серого цвета с контрастными жёлтыми или иными панелями; вдохновлена схемами British Rail Railfreight.",
    "STR_EXTRA_TEXT_LIVERY_INDUSTRIAL_YELLOW": "Окраска поездов для промышленной эксплуатации, например на металлургических и литейных предприятиях.",
    "STR_EXTRA_TEXT_LIVERY_INVERSIONS": "Различные окраски преимущественно вторым цветом компании с логотипами или отметками первого цвета.",
    "STR_EXTRA_TEXT_LIVERY_LOWER_LINES": "Окраска преимущественно первым цветом компании с нижней частью кузова или полосой подножки второго цвета.",
    "STR_EXTRA_TEXT_LIVERY_MAIL_BY_RAIL": "Различные окраски почтовых поездов, вдохновлённые Royal Mail, Rail Express Systems, TGV La Poste и другими схемами; основной цвет всегда красный.",
    "STR_EXTRA_TEXT_LIVERY_MARGINAL_GAINS": "Универсальная окраска пассажирских и почтовых поездов, вдохновлённая бело-синей пригородной схемой British Rail 1970-х.",
    "STR_EXTRA_TEXT_LIVERY_METROLAND": "Различные окраски поездов метро, вдохновлённые London Underground и другими системами.",
    "STR_EXTRA_TEXT_LIVERY_RAIN_OR_SHINE": "Универсальная окраска пассажирских и почтовых поездов, вдохновлённая традиционными двухцветными схемами.",
    "STR_EXTRA_TEXT_LIVERY_RIDEWELL": "Универсальная окраска пассажирских и почтовых поездов; стиль меняется между поколениями транспорта.",
    "STR_EXTRA_TEXT_LIVERY_SHOW_PONY": "Уникальные окраски отдельных транспортных средств или варианты, не относящиеся к другим категориям.",
    "STR_EXTRA_TEXT_LIVERY_STOCK_STANDARD": "Простая окраска преимущественно первым цветом компании с логотипами или отметками второго цвета.",
    "STR_EXTRA_TEXT_LIVERY_SUPERGRAPHIC": "Яркая окраска с крупными блоками жёлтого и первого цвета компании, иногда с логотипами или отметками второго цвета.",
    "STR_EXTRA_TEXT_LIVERY_SURE_PACE": "Универсальная окраска пассажирских и почтовых поездов; стиль меняется между поколениями транспорта.",
    "STR_EXTRA_TEXT_LIVERY_VANILLA": "VANILLA",
    "STR_EXTRA_TEXT_LIVERY_VAPID_VOYAGER": "Окраска пассажирских и почтовых поездов, вдохновлённая Virgin Trains, Greater Anglia и похожими схемами.",
    "STR_EXTRA_TEXT_LIVERY_VINYL_VECTOR": "Универсальная окраска пассажирских и почтовых поездов, вдохновлённая динамичными схемами конца 1990-х–2020-х годов.",
    "STR_EXTRA_TEXT_LIVERY_HORNET": "Окраска поездов для промышленной эксплуатации, например на металлургических и литейных предприятиях и шахтах.",
    "STR_EXTRA_TEXT_LIVERY_WORKHORSE": "Окраска грузовых поездов, сочетающая сплошной чёрный цвет и оба цвета компании.",
}


def load(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def translate_section(name: str, values: dict) -> dict | None:
    # Livery labels are project/style names; Yandex support explicitly allows
    # programmatic/proper names to remain untranslated.
    if name.startswith("STR_BADGE_LIVERY_"):
        return dict(values)
    if name in LIVERY_DOCS:
        out = dict(values)
        out["base"] = LIVERY_DOCS[name]
        return out
    if name in PROSE:
        out = dict(values)
        out["base"] = PROSE[name]
        if name == "STR_ERROR_INFLATION_INCOMPATIBLE":
            out["ibex"] = "Iron Ibex несовместим с инфляцией OpenTTD. Отключите инфляцию в настройках OpenTTD."
            out["moose"] = "Iron Moose несовместим с инфляцией OpenTTD. Отключите инфляцию в настройках OpenTTD."
        if name == "STR_ERROR_TERMITE_DEPRECATED":
            out["ibex"] = "Iron Ibex уже включает типы путей Termite. Удалите Termite из списка NewGRF и начните новую игру."
            out["moose"] = "Iron Moose уже включает типы путей Termite. Удалите Termite из списка NewGRF и начните новую игру."
        return out
    if name == "STR_ERROR_INFLATION_INCOMPATIBLE":
        return {
            "base": "Iron Horse несовместим с инфляцией OpenTTD. Отключите инфляцию в настройках OpenTTD.",
            "ibex": "Iron Ibex несовместим с инфляцией OpenTTD. Отключите инфляцию в настройках OpenTTD.",
            "moose": "Iron Moose несовместим с инфляцией OpenTTD. Отключите инфляцию в настройках OpenTTD.",
        }
    if name == "STR_ERROR_TERMITE_DEPRECATED":
        return {
            "base": "Iron Horse уже включает типы путей Termite. Удалите Termite из списка NewGRF и начните новую игру.",
            "ibex": "Iron Ibex уже включает типы путей Termite. Удалите Termite из списка NewGRF и начните новую игру.",
            "moose": "Iron Moose уже включает типы путей Termite. Удалите Termite из списка NewGRF и начните новую игру.",
        }
    if name.startswith("STR_BADGE_GEN_") and values.get("base", "").isdigit():
        return dict(values)
    base = values.get("base")
    if isinstance(base, str) and base in WAGONS:
        out = dict(values); out["base"] = WAGONS[base]; return out
    if isinstance(base, str) and base in TEXT:
        out = dict(values); out["base"] = TEXT[base]; return out
    return None


def toml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--english", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    english = load(args.english)
    result = {"GLOBAL_PRAGMA": RU_PRAGMA}
    missing = []
    for name, values in english.items():
        if name == "GLOBAL_PRAGMA":
            continue
        translated = translate_section(name, values)
        if translated is None or set(translated) != set(values):
            missing.append(name)
        else:
            result[name] = translated
    if missing:
        print(f"Unhandled current Iron Horse sections: {len(missing)}")
        for name in missing:
            print("IRON_HORSE_RU_UNHANDLED", name)
        return 2
    lines = []
    for name, values in result.items():
        lines.append(f"[{name}]")
        for key, value in values.items():
            lines.append(f"{key} = {toml_value(value)}")
        lines.append("")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    written = load(args.output)
    if set(written) != set(english):
        raise SystemExit("Generated Iron Horse Russian section set differs from English")
    for name in english:
        if name == "GLOBAL_PRAGMA":
            continue
        if set(written[name]) != set(english[name]):
            raise SystemExit(f"Generated Iron Horse field set differs for {name}")
    print(f"Generated complete Russian Iron Horse table: {len(english) - 1} strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
