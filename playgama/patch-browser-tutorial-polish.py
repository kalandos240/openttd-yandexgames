#!/usr/bin/env python3
"""Polish the native browser training level after the base tutorial patches.

This stage keeps the tutorial entirely inside OpenTTD's normal window/sprite
system. It corrects browser-edition main-menu button descriptions and expands
the practice level beyond the first route into the remaining core management
mechanics.
"""
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if text.count(old) != 1:
        raise SystemExit(f"Could not find unique {label} in {path}: {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_before_marker(path: Path, marker: str, block: str, guard: str) -> None:
    text = path.read_text(encoding="utf-8")
    if guard in text:
        return
    if text.count(marker) != 1:
        raise SystemExit(f"Could not find unique insertion marker {marker!r} in {path}")
    text = text.replace(marker, block.rstrip() + "\n" + marker, 1)
    path.write_text(text, encoding="utf-8")


english = Path("openttd/src/lang/english.txt")
russian = Path("openttd/src/lang/russian.txt")

replace_once(
    english,
    "STR_BROWSER_TUTORIAL_COACH_HINT                                :Follow the yellow highlight and the arrow. Perform the action in the real game, then press Next.\n",
    "STR_BROWSER_TUTORIAL_COACH_HINT                                :The required control is outlined in yellow; the arrow in this window points toward it. Perform the action in the real game, then press Next.\n",
    "English coach hint",
)
replace_once(
    russian,
    "STR_BROWSER_TUTORIAL_COACH_HINT                                :Следуйте жёлтой подсветке и стрелке. Выполните действие прямо в игре, затем нажмите «Далее».\n",
    "STR_BROWSER_TUTORIAL_COACH_HINT                                :Нужная кнопка обведена жёлтым, а стрелка в этом окне показывает направление к ней. Выполните действие прямо в игре, затем нажмите «Далее».\n",
    "Russian coach hint",
)

replace_once(
    english,
    "STR_BROWSER_TUTORIAL_LEVEL_16                                  :16/16 — Save, settings and help{}Save important games, tune settings and use Help → Tutorial or Help → Button guide whenever you need a reminder. You now have the full core loop: demand → infrastructure → vehicles → orders → delivery → profit → expansion.\n",
    "STR_BROWSER_TUTORIAL_LEVEL_16                                  :16/20 — Save and settings{}Save important games before large rebuilds and tune interface, sound and gameplay settings to your preference. The Help menu always keeps Tutorial and Button guide available.\n",
    "English tutorial step 16",
)
replace_once(
    russian,
    "STR_BROWSER_TUTORIAL_LEVEL_16                                  :16/16 — Сохранения, настройки и помощь{}Сохраняйте важные игры, настраивайте интерфейс и в любой момент открывайте «Помощь → Обучение» или «Помощь → Справочник кнопок». Основной цикл освоен: спрос → инфраструктура → транспорт → задания → доставка → прибыль → развитие.\n",
    "STR_BROWSER_TUTORIAL_LEVEL_16                                  :16/20 — Сохранения и настройки{}Сохраняйте важные партии перед крупной перестройкой и настраивайте интерфейс, звук и правила игры под себя. В меню «Помощь» всегда доступны «Обучение» и «Справочник кнопок».\n",
    "Russian tutorial step 16",
)

append_before_marker(
    english,
    "STR_BROWSER_MANUAL_CAPTION                                     :Illustrated button guide\n",
    """STR_BROWSER_TUTORIAL_LEVEL_17                                  :17/20 — Stations and cargo rating{}Open the station list. Station ratings affect how much cargo chooses your service. Frequent reliable vehicles, enough capacity and short waiting times keep ratings healthy; overcrowding means the route needs more capacity.
STR_BROWSER_TUTORIAL_LEVEL_18                                  :18/20 — Subsidies and local authority{}Open Subsidies and Offers. Subsidies reward useful new links for a limited time. Towns also have a local-authority rating: excessive demolition can block construction, while useful service and careful building improve relations.
STR_BROWSER_TUTORIAL_LEVEL_19                                  :19/20 — Fleet management and replacement{}Open a vehicle list. Large companies should use groups, shared orders and automatic replacement instead of editing every vehicle separately. Watch age, reliability, yearly profit and capacity before expanding the fleet.
STR_BROWSER_TUTORIAL_LEVEL_20                                  :20/20 — Competitors, NewGRF and reference{}Company windows and graphs let you compare performance with competitors. NewGRF changes vehicles, industries and graphics for new games; AI competitors can be configured before starting. Use Help → Button guide for an illustrated explanation of every main-menu and top-toolbar control. The full loop is demand → infrastructure → vehicles → orders → delivery → profit → maintenance → expansion.
""",
    "STR_BROWSER_TUTORIAL_LEVEL_20",
)
append_before_marker(
    russian,
    "STR_BROWSER_MANUAL_CAPTION                                     :Иллюстрированный справочник кнопок\n",
    """STR_BROWSER_TUTORIAL_LEVEL_17                                  :17/20 — Станции и рейтинг груза{}Откройте список станций. Рейтинг станции влияет на то, сколько груза выберет вашу компанию. Частый и надёжный транспорт, достаточная вместимость и короткое ожидание поддерживают рейтинг; переполнение означает, что маршруту нужна дополнительная пропускная способность.
STR_BROWSER_TUTORIAL_LEVEL_18                                  :18/20 — Субсидии и местные власти{}Откройте «Субсидии и предложения». Субсидии временно повышают доход за полезные новые связи. У городов есть отношение местной администрации: массовый снос может запретить строительство, а полезное обслуживание и аккуратная застройка улучшают отношения.
STR_BROWSER_TUTORIAL_LEVEL_19                                  :19/20 — Управление парком и замена{}Откройте список транспорта. В большой компании используйте группы, общие задания и автозамену вместо ручной настройки каждой машины. Следите за возрастом, надёжностью, годовой прибылью и вместимостью перед расширением парка.
STR_BROWSER_TUTORIAL_LEVEL_20                                  :20/20 — Конкуренты, NewGRF и справка{}Окна компаний и графики позволяют сравнивать результаты с конкурентами. NewGRF меняют транспорт, промышленность и графику новой партии, а ИИ-соперников можно настроить перед запуском игры. В «Помощь → Справочник кнопок» есть иллюстрированное описание каждой кнопки главного меню и верхней игровой панели. Полный цикл: спрос → инфраструктура → транспорт → задания → доставка → прибыль → обслуживание → развитие.
""",
    "STR_BROWSER_TUTORIAL_LEVEL_20",
)

intro = Path("openttd/src/intro_gui.cpp")
text = intro.read_text(encoding="utf-8")

# The browser edition repurposes the old Online Content slot for local NewGRF
# settings and the old Help slot for the complete license viewer. Keep the
# illustrated guide aligned with what those buttons actually do.
replacements = {
    "\t{SPR_IMG_SHOW_VEHICLES, STR_INTRO_TOOLTIP_ONLINE_CONTENT},\n":
        "\t{SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP},\n",
    "\t{SPR_IMG_QUERY, STR_INTRO_TOOLTIP_HELP},\n":
        "\t{SPR_IMG_QUERY, STR_PLAYGAMA_LICENSES_TOOLTIP},\n",
}
for old, new in replacements.items():
    if new not in text:
        if text.count(old) != 1:
            raise SystemExit(f"Could not correct button-guide entry {old.strip()!r}: {text.count(old)}")
        text = text.replace(old, new, 1)

step_anchor = "\t{STR_BROWSER_TUTORIAL_LEVEL_16, SPR_IMG_SAVE, BrowserTutorialTarget::MainToolbar, WID_TN_SAVE},\n"
extra_steps = step_anchor + """\t{STR_BROWSER_TUTORIAL_LEVEL_17, SPR_IMG_COMPANY_LIST, BrowserTutorialTarget::MainToolbar, WID_TN_STATIONS},
\t{STR_BROWSER_TUTORIAL_LEVEL_18, SPR_IMG_SUBSIDIES, BrowserTutorialTarget::MainToolbar, WID_TN_SUBSIDIES},
\t{STR_BROWSER_TUTORIAL_LEVEL_19, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS},
\t{STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_QUERY, BrowserTutorialTarget::MainToolbar, WID_TN_HELP},
"""
if "STR_BROWSER_TUTORIAL_LEVEL_20, SPR_IMG_QUERY" not in text:
    if text.count(step_anchor) != 1:
        raise SystemExit(f"Could not find tutorial step-array anchor: {text.count(step_anchor)}")
    text = text.replace(step_anchor, extra_steps, 1)

for marker in (
    "STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP",
    "STR_PLAYGAMA_LICENSES_TOOLTIP",
    "STR_BROWSER_TUTORIAL_LEVEL_17",
    "STR_BROWSER_TUTORIAL_LEVEL_18",
    "STR_BROWSER_TUTORIAL_LEVEL_19",
    "STR_BROWSER_TUTORIAL_LEVEL_20",
    "WID_TN_STATIONS",
    "WID_TN_SUBSIDIES",
    "WID_TN_ROADVEHS",
    "WID_TN_HELP",
):
    if marker not in text:
        raise SystemExit(f"Missing polished tutorial marker {marker!r}")

intro.write_text(text, encoding="utf-8")
print("Browser tutorial polished to 20 steps; NewGRF/licenses button guide corrected.")
