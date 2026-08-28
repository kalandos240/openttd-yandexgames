#!/usr/bin/env python3
"""Final tutorial polish: readable coach, pulsing targets, canonical practice settings."""
from pathlib import Path
import re


def set_string(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    line = f"{key:<64}:{value}"
    pattern = re.compile(rf"^{re.escape(key)}\s*:.*$", re.M)
    if not pattern.search(text):
        raise SystemExit(f"Missing tutorial string {key} in {path}")
    path.write_text(pattern.sub(line, text, count=1), encoding="utf-8")


def append_step_details(path: Path, extras: list[str], label: str) -> None:
    text = path.read_text(encoding="utf-8")
    for i, extra in enumerate(extras, 1):
        key = f"STR_BROWSER_TUTORIAL_LEVEL_{i:02d}"
        pattern = re.compile(rf"^({re.escape(key)}\s*:)(.*)$", re.M)
        match = pattern.search(text)
        if not match:
            raise SystemExit(f"Missing {key} in {path}")
        value = match.group(2)
        if f"{{}}{label}:" not in value:
            value += f"{{}}{label}: {extra}"
            text = text[:match.start()] + match.group(1) + value + text[match.end():]
    path.write_text(text, encoding="utf-8")


RU_EXTRA = [
    "Проверьте, где находятся ближайшие города, предприятия и вода; это пригодится в следующих шагах.",
    "Для точного строительства используйте обычную скорость, а ускорение оставляйте для ожидания рейсов.",
    "Выбирайте два близких города с заметной жилой застройкой, чтобы первый маршрут быстро молучил пассажиров.",
    "На панели дорог заранее найдите инструменты дороги, депо и автобусной остановки.",
    "Стройте непрерывно: разрыв даже в одну клетку не позволит автобусу пройти маршрут.",
    "Ставьте остановки рядом с домами и обязательно соединяйте их с дорогой; смотрите на зону охвата.",
    "Депо должно иметь выезд на вашу дорогу; после покупки дитесь, что автобус не остановлен вручную.",
    "В заданиях должны быть обе остановки; если автобус не едет, проверьте доступность дороги и порядок заданий.",
    "Смотрите именно транспортный доход: единичная прибыль ещё не означает, что сеть окупает постоянные расходы.",
    "Для первого поезда выбирайте короткую прямую линию, чтобы проще проверить путь, станции сигналы.",
    "Проверьте непрерывность рельсов и правильное соединение всех поворотов до покупки поезда.",
    "Платформы должны быть соединены с рельсами, а зона охвата - захватывать нужные здания или предприятие.",
    "Для учебной линии достаточно одного сигнала; позже сигналами сеть делится на безопасные блоки.",
    "Покупайте состав под назначение маршрута и убедитесь, что локомотив может выйти из депо на линию.",
    "Если поезд пишет, что не может найти путь, проверьте соединение станций, депо, направление и задания.",
    "Сначала посмотрите, какой груз производит предприятие и какое предприятие именно этот груз принимает.",
    "Станции грузового маршрута должны покрывать производителя и потребителя, иначе груз не будет приниматься.",
    "Проверяйте значки грузов на станциях: нужны реальные доставки двух разных типов, а не только наличие транспорта.",
    "Между причалами должен существовать непрерывный водный путь без недоступных участков суши.",
    "Если причал не ставится, найдите другой участок берега; причал должен одновременно касаться воды и иметь полезную зону охвата.",
    "После покупки задайте кораблю доступные причалы и рбедитесь, что он может выйти из депо в открытый водный путь.",
    "Для аэропорта нужна большая ровная площадка; заранее оставьте достаточно свободного пространства возле города.",
    "Проверьте зону охвата аэропорта: она должна захватывать городские здания, иначе пассажиропоток будет слабым.",
    "Самолёту нужны корректные аэропорты в заданиях; после запуска проверьте, что он действительно покидает ангар.",
    "Высокий рейтинг станции и регулярный транспорт помогают удерживать спрос и развивать город.",
    "Изменяйте рельеф только при необходимости: мост или тоннель часто дешевле и сохраняет маршрут прямым.",
    "Сравнивайте прибыль отдельных машин и общие графики компании, чтобы находить слабые маршруты.",
    "После завершения вернитесь в главное меню: обычная свободная игра восстановит ваши настройки и снова разрешит ИИ.",
]

EN_EXTRA = [
    "Locate nearby towns, industries and water now; later steps use all of them.",
    "Use normal speed for precise building and fast-forward only while waiting for vehicles.",
    "Pick two close towns with visible buildings so the first passenger route gets demand quickly.",
    "Identify the road, depot and bus-stop tools before you start building.",
    "Keep the road continuous; a single missing tile can make the route unreachable.",
    "Place stops close to buildings, connect them to the road and watch the catchment highlight.",
    "The depot must exit onto your road; after purchase make sure the bus is not manually stopped.",
    "Both stops must be in Orders; if the bus does not move, check road access and order sequence.",
    "Watch transport income, not only one profitable trip; recurring costs matter.",
    "Use a short straight firsttom };\n"

new = "\t\trect text_rect{body.left + 58, body.top + 4, body.right, body.bottom - 46};\n\t\t\tDrawStringMultiLine(text_rect, current.text, TC_BLACK, SA_LEFT);\n\t\t\tRect hint_rect{body.left + 58, body.bottom - 40, body.right, body.bottom};\n"
if old not in intro:
    raise SystemExit("Tutorial coach text geometry anchor missing")
intro = intro.replace(old, new, 1)

member = "struct BrowserTutorialCoachWindow final : Window {\n\tsize_t step = 0;\n"
if member not in intro:
    raise SystemExit("Tutorial coach member anchor missing")
intro = intro.replace(member, member + "\tuint highlight_elapsed_ms = 0;\n\tbool highlight_bright = true;\n", 1)

old_update = """\tvoid UpdateStep()
\t{
\t\tBrowserTutorialClearHighlights();
\t\tthis->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !BrowserTutorialObjectiveComplete(current.objective));
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) target->SetWidgetHighlight(current.widget, TC_YELLOW);
\t\tthis->SetDirty();
\t}
"""
new_update = """\tvoid UpdateStep()
\t{
\t\tBrowserTutorialClearHighlights();
\t\tthis->highlight_elapsed_ms = 0;
\t\tthis->highlight_bright = true;
\t\tthis->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !BrowserTutorialObjectiveComplete(current.objective));
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) target->SetWidgetHighlight(current.widget, TC_WHITE);
\t\tthis->SetDirty();
\t}
"""
if old_update not in intro:
    raise SystemExit("Objective-aware UpdateStep anchor missing")
intro = intro.replace(old_update, new_update, 1)

old_tick = """\tvoid OnRealtimeTick([[maybe_unused]] uint delta_ms) override
\t{
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !BrowserTutorialObjectiveComplete(current.objective));
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\tif (!target->IsWidgetHighlighted(current.widget)) target->SetWidgetHighlight(current.widget, TC_YELLOW);
\t\t}
\t\tthis->SetDirty();
\t}
"""
new_tick = """\tvoid OnRealtimeTick(uint delta_ms) override
\t{
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !BrowserTutorialObjectiveComplete(current.objective));
\t\tthis->highlight_elapsed_ms += delta_ms;
\t\tif (this->highlight_elapsed_ms >= 320) {
\t\t\tthis->highlight_elapsed_ms %= 320;
\t\t\tthis->highlight_bright = !this->highlight_bright;
\t\t}
\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
\t\t\ttarget->SetWidgetHighlight(current.widget, this->highlight_bright ? TC_WHITE : TC_YELLOW);
\t\t}
\t\tthis->SetDirty();
\t}
"""
if old_tick not in intro:
    raise SystemExit("Objective-aware realtime tick anchor missing")
intro = intro.replace(old_tick, new_tick, 1)

if '#include "newgrf_config.h"' not in intro:
    anchor = '#include "company_base.h"\n'
    if anchor not in intro:
        raise SystemExit("company include anchor missing")
    intro = intro.replace(anchor, anchor + '#include "newgrf_config.h"\n', 1)

anchor = "\tdecltype(_settings_newgame.game_creation.map_x) map_x{};\n"
if anchor not in intro:
    raise SystemExit("saved-settings struct anchor missing")
intro = intro.replace(anchor, anchor + "\tdecltype(_settings_newgame.game_creation.starting_year) starting_year{};\n\tdecltype(_settings_newgame.difficulty.max_no_competitors) max_no_competitors{};\n", 1)

anchor = "static BrowserTutorialSavedSettings _browser_tutorial_saved_settings{};\nstatic bool _browser_tutorial_settings_saved = false;\n"
if anchor not in intro:
    raise SystemExit("saved-settings globals anchor missing")
intro = intro.replace(anchor, "static BrowserTutorialSavedSettings _browser_tutorial_saved_settings{};\nstatic GRFConfigList _browser_tutorial_saved_newgrfs{};\nstatic bool _browser_tutorial_settings_saved = false;\n", 1)

anchor = "\ts.map_x = _settings_newgame.game_creation.map_x; s.map_y = _settings_newgame.game_creation.map_y;\n"
if anchor not in intro:
    raise SystemExit("save function anchor missing")
intro = intro.replace(anchor, anchor + "\ts.starting_year = _settings_newgame.game_creation.starting_year;\n\ts.max_no_competitors = _settings_newgame.difficulty.max_no_competitors;\n\tClearGRFConfigList(_browser_tutorial_saved_newgrfs);\n\tCopyGRFConfigList(_browser_tutorial_saved_newgrfs, _grfconfig_newgame, false);\n", 1)

anchor = "\t_settings_newgame.game_creation.map_x = s.map_x; _settings_newgame.game_creation.map_y = s.map_y;\n"
if anchor not in intro:
    raise SystemExit("restore function anchor missing")
intro = intro.replace(anchor, anchor + "\t_settings_newgame.game_creation.starting_year = s.starting_year;\n\t_settings_newgame.difficulty.max_no_competitors = s.max_no_competitors;\n", 1)

anchor = "\t_settings_newgame.difficulty.town_council_tolerance = s.town_council_tolerance; _settings_newgame.difficulty.disasters = s.disasters;\n\t_browser_tutorial_settings_saved = false;\n"
if anchor not in intro:
    raise SystemExit("restore tail anchor missing")
intro = intro.replace(anchor, "\t_settings_newgame.difficulty.town_council_tolerance = s.town_council_tolerance; _settings_newgame.difficulty.disasters = s.disasters;\n\tClearGRFConfigList(_grfconfig_newgame);\n\tCopyGRFConfigList(_grfconfig_newgame, _browser_tutorial_saved_newgrfs, false);\n\tClearGRFConfigList(_browser_tutorial_saved_newgrfs);\n\t_browser_tutorial_settings_saved = false;\n", 1)

anchor = "\tBrowserTutorialSaveNewGameSettings();\n\t_settings_newgame.game_creation.map_x = 6; _settings_newgame.game_creation.map_y = 6;\n"
if anchor not in intro:
    raise SystemExit("tutorial start anchor missing")
intro = intro.replace(anchor, "\tBrowserTutorialSaveNewGameSettings();\n\t_settings_newgame.game_creation.starting_year = TimerGameCalendar::Year{1950};\n\t_settings_newgame.difficulty.max_no_competitors = 0;\n\tClearGRFConfigList(_grfconfig_newgame);\n\t_settings_newgame.game_creation.map_x = 6; _settings_newgame.game_creation.map_y = 6;\n", 1)

old = "\t_settings_newgame.difficulty.max_loan = 1000000; _settings_newgame.difficulty.vehicle_breakdowns = 0;\n"
new = "\t_settings_newgame.difficulty.max_loan = 300000; _settings_newgame.difficulty.vehicle_breakdowns = VehicleBreakdowns::Reduced;\n"
if old not in intro:
    raise SystemExit("tutorial easy-difficulty anchor missing")
intro = intro.replace(old, new, 1)

for marker in ("SetMinimalSize(600, 205)", "highlight_elapsed_ms", "TC_WHITE : TC_YELLOW", "starting_year = TimerGameCalendar::Year{1950}", "ClearGRFConfigList(_grfconfig_newgame)", "VehicleBreakdowns::Reduced"):
    if marker not in intro:
        raise SystemExit(f"Final tutorial marker missing: {marker}")

intro_path.write_text(intro, encoding="utf-8")
print("Tutorial final polish applied: larger text area, pulsing targets, detailed hints, 1950/no-AI/no-NewGRF practice settings.")
