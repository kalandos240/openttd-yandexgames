#!/usr/bin/env python3
"""Build a complete Russian FIRS GRF language table for the pinned 5.2.x source.

The upstream 5.x tree intentionally removed translations.  We recover the
last maintained Russian table as a base, then fill newer FIRS strings from
curated terminology below.  The script is deliberately strict: an unknown
current English section is a build error instead of silently falling back to
English in the Russian UI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

RU_PRAGMA = {
    "grflangid": "0x07",
    "plural": "6",
    "gender": "m f n p",
    "case": "abl acc dat f gen m n nom p pre",
}

# nominative, genitive.  The genitive form is used by cargo-unit strings.
CARGOS = {
    "ACID": ("Кислота", "кислоты"),
    "ALUMINIA": ("Глинозём", "глинозёма"),
    "ALUMINIUM": ("Алюминий", "алюминия"),
    "AMMONIA": ("Аммиак", "аммиака"),
    "BEANS": ("Бобы", "бобов"),
    "CARBON_BLACK": ("Технический углерод", "технического углерода"),
    "CASSAVA": ("Маниок", "маниока"),
    "CAST_IRON": ("Чугун", "чугуна"),
    "CHLORINE": ("Хлор", "хлора"),
    "CHROMITE_ORE": ("Хромитовая руда", "хромитовой руды"),
    "CLEANING_AGENTS": ("Чистящие средства", "чистящих средств"),
    "COAL_TAR": ("Каменноугольная смола", "каменноугольной смолы"),
    "COKE": ("Кокс", "кокса"),
    "CONCRETE_PRODUCTS": ("Бетонные изделия", "бетонных изделий"),
    "COPPER": ("Медь", "меди"),
    "COPPER_CONCENTRATE": ("Медный концентрат", "медного концентрата"),
    "EDIBLE_OIL": ("Пищевое масло", "пищевого масла"),
    "ELECTRICAL_PARTS": ("Электрические компоненты", "электрических компонентов"),
    "EXPLOSIVES": ("Взрывчатые вещества", "взрывчатых веществ"),
    "FERROALLOYS": ("Ферросплавы", "ферросплавов"),
    "FERTILISER": ("Удобрения", "удобрений"),
    "FOOD_ADDITIVES": ("Пищевые добавки", "пищевых добавок"),
    "FORGINGS_AND_CASTINGS": ("Поковки и отливки", "поковок и отливок"),
    "GLASS": ("Стекло", "стекла"),
    "HARDWARE": ("Метизы", "метизов"),
    "KAOLIN": ("Каолин", "каолина"),
    "LIMESTONE": ("Известняк", "известняка"),
    "LOGS": ("Брёвна", "брёвен"),
    "LYE": ("Гидроксид натрия", "гидроксида натрия"),
    "MANGANESE": ("Марганец", "марганца"),
    "METHANOL": ("Метанол", "метанола"),
    "NAPHTHA": ("Нафта", "нафты"),
    "NICKEL": ("Никель", "никеля"),
    "NITRATES": ("Нитраты", "нитратов"),
    "NITROGEN": ("Азот", "азота"),
    "NUTS": ("Орехи", "орехов"),
    "OXYGEN": ("Кислород", "кислорода"),
    "PAINTS_AND_COATINGS": ("Краски и покрытия", "красок и покрытий"),
    "PEAT": ("Торф", "торфа"),
    "PHOSPHATE": ("Фосфаты", "фосфатов"),
    "PHOSPHORIC_ACID": ("Фосфорная кислота", "фосфорной кислоты"),
    "PIG_IRON": ("Передельный чугун", "передельного чугуна"),
    "PIPEWORK": ("Резервуары и трубопроводы", "резервуаров и трубопроводов"),
    "PLANT_AND_MACHINERY": ("Промышленное оборудование", "промышленного оборудования"),
    "PLASTICS": ("Пластмассы", "пластмасс"),
    "POTASH": ("Калийные соли", "калийных солей"),
    "PUMPS_AND_VALVES": ("Насосы и клапаны", "насосов и клапанов"),
    "PYRITE_ORE": ("Пиритная руда", "пиритной руды"),
    "QUICKLIME": ("Негашёная известь", "негашёной извести"),
    "RAW_LATEX": ("Сырой латекс", "сырого латекса"),
    "REBAR": ("Арматура", "арматуры"),
    "SALT": ("Соль", "соли"),
    "SEALS_HOSES_AND_BELTS": ("Уплотнения, шланги и ремни", "уплотнений, шлангов и ремней"),
    "SLAG": ("Шлак", "шлака"),
    "SODA_ASH": ("Кальцинированная сода", "кальцинированной соды"),
    "STEEL": ("Сталь", "стали"),
    "STEEL_BILLETS_AND_BLOOMS": ("Заготовки и блюмы", "заготовок и блюмов"),
    "STEEL_INGOTS": ("Стальные слитки", "стальных слитков"),
    "STEEL_MERCHANT_BAR": ("Сортовой прокат", "сортового проката"),
    "STEEL_PIPE": ("Стальные трубы", "стальных труб"),
    "STEEL_PLATE": ("Стальные плиты", "стальных плит"),
    "STEEL_SHEET": ("Листовая и полосовая сталь", "листовой и полосовой стали"),
    "STEEL_SLAB": ("Стальные слябы", "стальных слябов"),
    "STEEL_TUBE": ("Стальные трубки", "стальных трубок"),
    "STEEL_WIRE_ROD": ("Стальная катанка", "стальной катанки"),
    "STRUCTURAL_STEELWORK": ("Металлоконструкции", "металлоконструкций"),
    "SULPHUR": ("Сера", "серы"),
    "SULPHURIC_ACID": ("Серная кислота", "серной кислоты"),
    "TEXTILES": ("Текстиль", "текстиля"),
    "TIN": ("Олово", "олова"),
    "TINPLATE": ("Белая жесть", "белой жести"),
    "TYRE_CORD": ("Шинный корд", "шинного корда"),
    "TYRES": ("Шины", "шин"),
    "UREA": ("Мочевина", "мочевины"),
    "VEHICLE_BODIES": ("Кузова", "кузовов"),
    "VEHICLE_ENGINES": ("Двигатели и трансмиссии", "двигателей и трансмиссий"),
    "VEHICLE_PARTS": ("Автокомпоненты", "автокомпонентов"),
    "VEHICLES": ("Транспортные средства", "транспортных средств"),
    "WELDING_CONSUMABLES": ("Сварочные материалы", "сварочных материалов"),
    "YARN": ("Пряжа", "пряжи"),
    "ZINC": ("Цинк", "цинка"),
}

INDUSTRIES = {
    "AMMONIA_PLANT": "Аммиачный завод",
    "APPLIANCE_FACTORY": "Завод бытовой техники",
    "ASSEMBLY_PLANT": "Сборочный завод",
    "BASIC_OXYGEN_FURNACE": "Кислородный конвертер",
    "BLAST_FURNACE": "Доменная печь",
    "BODY_PLANT": "Кузовной завод",
    "CARBON_BLACK_PLANT": "Завод технического углерода",
    "CHEMICAL_PLANT": "Химический завод",
    "CHLOR_ALKALI_PLANT": "Хлор-щелочной завод",
    "CHROMITE_MINE": "Хромитовый рудник",
    "COKE_OVEN": "Коксовая печь",
    "CONCRETE_PLANT": "Бетонный завод",
    "COPPER_CONCENTRATOR": "Медная обогатительная фабрика",
    "COPPER_SMELTER": "Медеплавильный завод",
    "CRYO_PLANT": "Криогенный завод",
    "DAIRY_FARM": "Молочная ферма",
    "ELASTOMER_PRODUCTS_PLANT": "Завод эластомерных изделий",
    "ELECTRIC_ARC_FURNACE": "Электродуговая печь",
    "ENGINE_PLANT": "Двигателестроительный завод",
    "FACTORY_1": "Фабрика 1",
    "FACTORY_2": "Фабрика 2",
    "FACTORY_3": "Фабрика 3",
    "FARM": "Ферма",
    "FERROCHROME_SMELTER": "Феррохромовый завод",
    "FERTILISER_PLANT": "Завод удобрений",
    "FISH_FARM": "Рыбоводная ферма",
    "FLOUR_MILL": "Мукомольный завод",
    "FOOD_PROCESSOR": "Пищевой комбинат",
    "FORGE_AND_FOUNDRY": "Кузнечно-литейный завод",
    "HERDING_COOP": "Животноводческий кооператив",
    "INTEGRATED_STEEL_MILL": "Металлургический комбинат",
    "LATEX_PROCESSOR": "Завод переработки латекса",
    "LIMESTONE_MINE": "Известняковый карьер",
    "LIQUIDS_TERMINAL": "Терминал наливных грузов",
    "MANGANESE_MINE": "Марганцевый рудник",
    "METAL_WORKS": "Металлообрабатывающий завод",
    "NITRATE_MINE": "Нитратный рудник",
    "PEATLANDS": "Торфоразработки",
    "PHOSPHATE_MINE": "Фосфатный рудник",
    "PHOSPHORIC_ACID_PLANT": "Завод фосфорной кислоты",
    "PIPEWORK_FABRICATOR": "Трубный цех",
    "PLATE_MILL": "Листопрокатный завод",
    "POTASH_MINE": "Калийный рудник",
    "POWER_PLANT": "Электростанция",
    "POWER_SYSTEMS_FACTORY": "Завод энергетического оборудования",
    "PRECISION_PARTS_PLANT": "Завод точных деталей",
    "PYRITE_MINE": "Пиритный рудник",
    "PYRITE_SMELTER": "Пиритоплавильный завод",
    "SECTION_AND_BAR_MILL": "Сортопрокатный завод",
    "SLAG_GRINDING_PLANT": "Завод измельчения шлака",
    "SODA_ASH_MINE": "Рудник содового сырья",
    "SOLVAY_PLANT": "Содовый завод",
    "STRIP_MILL": "Завод полосового проката",
    "SULPHURIC_ACID_PLANT": "Завод серной кислоты",
    "SUPPLY_YARD": "Склад снабжения",
    "TINPLATE_WORKS": "Завод белой жести",
    "TUBE_AND_PIPE_MILL": "Трубопрокатный завод",
    "TYRE_PLANT": "Шинный завод",
    "VEHICLE_DISTRIBUTOR": "Центр дистрибуции транспорта",
    "VINEYARD": "Виноградник",
    "WHARF": "Грузовая пристань",
    "WIRE_ROD_MILL": "Завод катанки",
}

STATIONS = {
    "APPLIANCE_FACTORY": "Электротовары",
    "AUTOMOTIVE": "Автотранспорт",
    "BANK_TOP": "Бэнк-Топ",
    "BARNS": "Амбары",
    "BARREL_AND_KEG": "Бочки и кеги",
    "BAR_AND_SECTION_MILL": "Балки",
    "BAR_GRILL_AND_ROOMS": "Бар, гриль и комнаты",
    "BASE": "База",
    "BODY_PLANT": "Штамповочный цех",
    "BONEYARD": "Свалка",
    "BRINE_WORKS": "Соляной цех",
    "BUILDERS_YARD": "Строительный склад",
    "COLLIERY": "Угольная шахта",
    "COMPONENTS": "Компоненты",
    "CONCRETE_PLANT": "Железобетон",
    "COPPER_LODE": "Медная жила",
    "CREOSOTING": "Пропиточный цех",
    "CRYO_PLANT": "Криогенный завод",
    "DAIRY_LANE": "Молочная ферма",
    "ELASTOMER_PLANT": "Уплотнения и шланги",
    "ESTATE": "Поместье",
    "FARM_2": "Луга",
    "FARM_3": "Ранчо",
    "FOOD_CORPORATION": "Пищевая корпорация",
    "FOREST": "Лесной склад",
    "FORGE_AND_FOUNDRY": "Металлурги",
    "FURNACE": "Печь",
    "HEAVY_INDUSTRY_2": "Промзона",
    "HERDING_COOP": "Загоны для оленей",
    "INDUSTRY_HARBOUR_2": "Набережная",
    "INDUSTRY_HARBOUR_3": "Причал",
    "INDUSTRY_HARBOUR_4": "Береговая линия",
    "IRONSTONE": "Железняк",
    "KILNS": "Печи",
    "KIMBERLITE_DEPOSITS": "Кимберлитовые месторождения",
    "LIMESTONE_MINES": "Известняковые карьеры",
    "MANGANESE_MINES": "Марганцевые рудники",
    "METAL_WORKS": "Металлообработка",
    "MOULDINGS": "Фасонные изделия",
    "OIL_RIG": "Месторождение",
    "ORCHARDS": "Сады",
    "PIPEWORK_FABRICATOR": "Трубопроводы",
    "PLATE_MILL": "Слябовый склад",
    "POTASH_MINE": "Минералы",
    "POWERTRAIN": "Силовые агрегаты",
    "POWER_SYSTEMS_FACTORY": "Промышленное оборудование",
    "PUMPS": "Насосы",
    "PYRITES": "Пиритовые залежи",
    "ROD_MILL": "Прокатный стан",
    "RUBBER_COMPANY": "Каучуковая компания",
    "SALTPETER_WORKS": "Селитряный завод",
    "SEAFOOD": "Морепродукты",
    "SHARP_STREET": "Шарп-стрит",
    "SHEEP_FOLD": "Овечий загон",
    "SHOALS": "Отмели",
    "SILO": "Элеватор",
    "SMELTER": "Плавильный завод",
    "SOOT_FURNACE": "Сажевая печь",
    "STRIP_MILL": "Линия рулонного проката",
    "SUGAR_COMPANY": "Сахарная компания",
    "TANK_FARM": "Резервуарный парк",
    "TAPPERS_SHED": "Склад сборщиков латекса",
    "TOWN_3": "Магазины",
    "TRACKED_MACHINE_FACTORY": "Завод гусеничной техники",
    "TRONA_BEDS": "Залежи троны",
    "TUBE_MILL": "Трубный завод",
    "VEHICLE_DISTRIBUTOR": "Автоплощадка",
    "WELLS": "Скважины",
    "WINERY": "Винодельня",
}

STATIC = {
    "STR_GRF_NAME": "FIRS Industry Replacement Set",
    "STR_CARGO_SUBTYPE_DISPLAY_CARGO_OPTIONAL_FLAG": " {BLACK}(необязательно)",
    "STR_CARGO_SUBTYPE_DISPLAY_CARGO_SUPPLIED_FLAG": " {BLACK}(поставлено)",
    "STR_EXTRA_TEXT_SECONDARY_NON_COMBINATORY": "{BLACK}Для максимальной производительности поставляйте {WHITE}хотя бы один {BLACK}из требуемых грузов.",
    "STR_EXTRA_TEXT_SECONDARY_COMBINATORY_BOTH": "{BLACK}Для максимальной производительности поставляйте {WHITE}оба {BLACK}требуемых груза хотя бы раз в три минуты.",
    "STR_EXTRA_TEXT_SECONDARY_COMBINATORY_ALL": "{BLACK}Для максимальной производительности поставляйте {WHITE}все {BLACK}требуемые грузы хотя бы раз в три минуты.",
    "STR_EXTRA_TEXT_SECONDARY_COMBINATORY_ANY_TWO": "{BLACK}Для максимальной производительности поставляйте {WHITE}не менее двух {BLACK}требуемых грузов хотя бы раз в три минуты.",
    "STR_EXTRA_TEXT_SECONDARY_COMBINATORY_ANY_THREE": "{BLACK}Для максимальной производительности поставляйте {WHITE}не менее трёх {BLACK}требуемых грузов хотя бы раз в три минуты.",
    "STR_EXTRA_TEXT_TOWN_PRODUCER": "{BLACK}Производство пропорционально населению города. Каждую минуту будет произведено не менее {WHITE}{SIGNED_WORD} ед.{BLACK} и не более {WHITE}{SIGNED_WORD} ед.{BLACK} груза.",
    "STR_PARAM_NAME_PRIMARY_LEVEL1_REQUIREMENT": "Ящиков снабжения для повышенного уровня первичного производства (по умолчанию 16)",
    "STR_PARAM_NAME_PRIMARY_LEVEL2_REQUIREMENT": "Ящиков снабжения для максимального уровня первичного производства (по умолчанию 80)",
    "STR_PARAM_DESC_PRIMARY_LEVEL_REQUIREMENT": "Фермы, шахты и подобные предприятия увеличивают производство после доставки ящиков снабжения: сначала до {SILVER}повышенного{BLACK}, затем до {SILVER}максимального{BLACK} уровня.{}{}Значения по умолчанию подходят для обычной игры, но при необходимости их можно изменить.{}{}Для портовых предприятий требуется в 8 раз больше груза, чем указано здесь.",
    "STR_PARAM_NAME_PRIMARY_LEVEL1_BONUS": "Повышенный уровень первичного производства (%)",
    "STR_PARAM_NAME_PRIMARY_LEVEL2_BONUS": "Максимальный уровень первичного производства (%)",
    "STR_PARAM_DESC_PRIMARY_LEVEL_BONUS": "Производство ферм, шахт и подобных предприятий после выполнения требований снабжения (в процентах от {SILVER}обычного {BLACK}уровня производства).",
    "STR_PARAM_VALUE_ECONOMIES_STEELTOWN": "Steeltown",
    "STR_PARAM_NAME_OBJECTS": "Ландшафтные объекты FIRS",
    "STR_PARAM_DESC_OBJECTS": "FIRS включает набор декоративных ландшафтных объектов, которыми можно визуально расширять предприятия. На игровой процесс они не влияют. Объекты можно включить или отключить.",
    "STR_ERR_OPENTTD_VERSION": "{ORANGE}E00: для FIRS требуется OpenTTD 1.7.0 (или r27769 для trunk-сборок)",
    "STR_ERR_INCOMPATIBLE_SET": "{ORANGE}E01: {YELLOW}Несовместимый набор: {ORANGE}{STRING}",
    "STR_ERR_INCOMPATIBLE_PARAM_CANSET": "{ORANGE}E02: {YELLOW}Несовместимый параметр: {ORANGE}для работы с FIRS параметр 2 CanSet должен быть равен 0.",
    "STR_ERR_INCOMPATIBLE_PARAM_CITYSET": "{ORANGE}E02: {YELLOW}Несовместимый параметр: {ORANGE}для работы с FIRS параметр 2 NA City Set должен быть равен 0.",
    "STR_ERR_INCOMPATIBLE_SET_TTRS_VERSION": "{ORANGE}E04: {YELLOW}Несовместимая версия: {ORANGE}Total Town Replacement Set должен быть версии 3.11 или новее.",
}

FUND_TEXT = {
    "{}{BLACK}Location: {YELLOW}Cannot be funded on snow or in deserts.": "{}{BLACK}Расположение: {YELLOW}нельзя основать на снегу или в пустыне.",
    "{}{BLACK}Location: {YELLOW}Cannot be funded in deserts.": "{}{BLACK}Расположение: {YELLOW}нельзя основать в пустыне.",
    "{}{BLACK}Location: {YELLOW}Cannot be funded on snow.": "{}{BLACK}Расположение: {YELLOW}нельзя основать на снегу.",
    "{}{BLACK}Location: {YELLOW}Can only be funded on snow.": "{}{BLACK}Расположение: {YELLOW}можно основать только на снегу.",
    "{}{BLACK}Available from: {YELLOW}{COMMA}": "{}{BLACK}Доступно с: {YELLOW}{COMMA}",
    "{}{BLACK}Not available after: {YELLOW}{COMMA}": "{}{BLACK}Недоступно после: {YELLOW}{COMMA}",
}


def load(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def cargo_unit(section: str, english: str) -> str | None:
    suffix = section.removeprefix("STR_CARGO_UNIT_")
    if suffix not in CARGOS:
        return None
    gen = CARGOS[suffix][1]
    if english.startswith("{WEIGHT}"):
        return f"{{WEIGHT}} {gen}"
    if english.startswith("{VOLUME}"):
        return f"{{VOLUME}} {gen}"
    if "sack{P" in english:
        return f'{{SIGNED_WORD}} меш{{P 0 "" ка ков}} {gen}'
    if "crate{P" in english:
        return f'{{SIGNED_WORD}} ящик{{P 0 "" а ов}} {gen}'
    if "bale{P" in english:
        return f'{{SIGNED_WORD}} тюк{{P 0 "" а ов}} {gen}'
    return None


def generate_section(name: str, current: dict) -> dict | None:
    base = current.get("base") if isinstance(current, dict) else None
    if not isinstance(base, str):
        return None

    if name in STATIC:
        return {"base": STATIC[name]}
    if name.startswith("STR_CID_"):
        # Compact cargo identifiers are programmatic codes, not prose.
        return dict(current)
    if name.startswith("STR_CARGO_NAME_"):
        suffix = name.removeprefix("STR_CARGO_NAME_")
        value = CARGOS.get(suffix)
        return {"base": value[0]} if value else None
    if name.startswith("STR_CARGO_UNIT_"):
        value = cargo_unit(name, base)
        return {"base": value} if value else None
    if name.startswith("STR_IND_"):
        suffix = name.removeprefix("STR_IND_")
        value = INDUSTRIES.get(suffix)
        return {"base": value} if value else None
    if name.startswith("STR_STATION_"):
        suffix = name.removeprefix("STR_STATION_")
        value = STATIONS.get(suffix)
        return {"base": value} if value else None
    if name.startswith("STR_FUND_") and base in FUND_TEXT:
        return {"base": FUND_TEXT[base]}
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--english", type=Path, required=True)
    ap.add_argument("--historical-russian", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    english = load(args.english)
    historical = load(args.historical_russian)
    result: dict[str, dict] = {"GLOBAL_PRAGMA": RU_PRAGMA}
    unhandled: list[str] = []

    for name, current in english.items():
        if name == "GLOBAL_PRAGMA":
            continue
        old = historical.get(name)
        if isinstance(old, dict):
            # Emit only fields that still exist in current FIRS.  This drops
            # obsolete cases/variants without weakening current-key coverage.
            translated = {k: old[k] for k in current if k in old}
            if set(translated) == set(current):
                result[name] = translated
                continue
        generated = generate_section(name, current)
        if generated is None or set(generated) != set(current):
            unhandled.append(name)
            continue
        result[name] = generated

    if unhandled:
        print(f"Unhandled current FIRS sections: {len(unhandled)}")
        for name in unhandled:
            print("FIRS_RU_UNHANDLED", name)
        return 2

    lines: list[str] = []
    for name, values in result.items():
        lines.append(f"[{name}]" if name.replace("_", "").isalnum() else f"[{q(name)}]")
        for key, value in values.items():
            lines.append(f"{key} = {q(str(value))}")
        lines.append("")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")

    # Final structural proof: Russian output covers exactly every current
    # English section and every field in each section.
    written = load(args.output)
    if set(written) != set(english):
        raise SystemExit("Generated Russian FIRS section set differs from current English")
    for name, current in english.items():
        if set(written[name]) != set(current):
            raise SystemExit(f"Generated Russian FIRS field set differs for {name}")
    print(f"Generated complete Russian FIRS table: {len(english) - 1} strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
