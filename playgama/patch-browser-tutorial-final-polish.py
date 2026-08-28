#!/usr/bin/env python3
from pathlib import Path
import re


def add_details(path, details, label):
    text = path.read_text(encoding='utf-8')
    for i, detail in enumerate(details, 1):
        key = f'STR_BROWSER_TUTORIAL_LEVEL_{i:02d}'
        m = re.search(rf'^({key}\s*:)(.*)$', text, re.M)
        if not m:
            raise SystemExit(f'missing {key}')
        if f'{{}}{label}:' not in m.group(2):
            value = m.group(2) + f'{{}}{{YELLOW}}{label}:{{BLACK}} {detail}'
            text = text[:m.start()] + m.group(1) + value + text[m.end():]
    path.write_text(text, encoding='utf-8')


def set_string(path, key, value):
    text = path.read_text(encoding='utf-8')
    p = re.compile(rf'^({key}\s*:).*$', re.M)
    if not p.search(text): raise SystemExit(f'missing {key}')
    path.write_text(p.sub(lambda m: m.group(1) + value, text, count=1), encoding='utf-8')


RU = [
'Найдите два близких города, предприятия и воду; они понадобятся дальше.',
'Пауза нужна перед строительством, ускорение - только для ожидания рейсов.',
'Выберите два близких города с домами, чтобы быстро появился спрос.',
'На панели дорог найдите дорогу, остановку и депо.',
'Соедините города непрерывной дорогой без разрывов.',
'Поставьте остановки у домов и соедините их с дорогой; нужны 2 станционные клетки.',
'Постройте депо с выездом на дорогу, купите и запустите автобус.',
'Добавьте обе остановки в задания автобуса и дождитесь реальной доставки.',
'Откройте финансы и дождитесь положительного транспортного дохода.',
'Для первого поезда выберите короткую прямую трассу.',
'Проложите непрерывные рельсы, проверьте повороты и доступ к депо.',
'Станции должны покрывать нужные здания или предприятия; нужны 4 станционные клетки.',
'Поставьте минимум один сигнал на железной дороге.',
'Купите поезд и убедитесь, что он может выехать из депо на линию.',
'Задайте поезду обе станции; если пути нет, проверьте рельсы и задания.',
'Найдите производителя груза и предприятие, которое этот груз принимает.',
'Зоны охвата грузовых станций должны включать производителя и потребителя.',
'Доставьте реально два разных типа грузов; наличие транспорта не засчитывается.',
'Найдите два берега с непрерывным водным путём между ними.',
'Причал должен касаться воды и иметь полезную зону охвата.',
'Купите корабль, задайте доступные причалы и запустите его.',
'Найдите достаточно большую ровную площадку возле города.',
'Постройте аэропорт так, чтобы зона охвата захватывала городские здания.',
'Купите самолёт, задайте аэропорты и убедитесь, что он вышел из ангара.',
'Регулярный транспорт и хороший рейтинг станции поддерживают рост города.',
'Меняйте рельеф экономно; мост или тоннель часто выгоднее большой выемки.',
'Сравните графики и прибыль транспорта, найдите слабые маршруты.',
'Готово: после выхода обычные настройки новой игры будут восстановлены.',
]
EN = [
'Locate two nearby towns, industries and water; later steps use them.',
'Pause before building; fast-forward only while waiting for trips.',
'Choose two nearby towns with buildings so demand appears quickly.',
'Find the road, bus-stop and depot tools.',
'Connect the towns with one continuous road.',
'Place stops by buildings and connect them to the road; two station tiles are required.',
'Build a depot with road access, buy a bus and start it.',
'Add both stops to the bus orders and wait for a real delivery.',
'Open finances and wait for positive transport income.',
'Use a short, straight route for the first train.',
'Build continuous rails and check curves and depot access.',
'Stations must cover the target buildings or industries; four station tiles are required.',
'Place at least one signal on the railway.',
'Buy a train and verify it can leave the depot.',
'Give the train both stations; if no path exists, inspect rails and orders.',
'Find a cargo producer and an industry that accepts that cargo.',
'Cargo-station catchment must cover both producer and consumer.',
'Deliver two different cargo types; merely owning cargo vehicles is not enough.',
'Find two shores connected by an uninterrupted water path.',
'A dock must touch water and have useful catchment.',
'Buy a ship, assign reachable docks and start it.',
'Find a large enough flat area near a town.',
'Build an airport whose catchment reaches town buildings.',
'Buy an aircraft, assign airports and verify it leaves the hangar.',
'Regular service and good station ratings help town growth.',
'Landscape sparingly; a bridge or tunnel is often cheaper than major terraforming.',
'Compare graphs and vehicle profit to find weak routes.',
'Done: leaving training restores normal new-game settings.',
]
if len(RU) != 28 or len(EN) != 28: raise SystemExit('need 28 tutorial details')

p = Path('openttd/src/intro_gui.cpp')
s = p.read_text(encoding='utf-8')
for old, new in [('SetMinimalSize(420, 100)','SetMinimalSize(600, 175)'),('SetMinimalSize(420, 140)','SetMinimalSize(600, 190)'),('SetMinimalSize(420, 105)','SetMinimalSize(640, 240)')]:
    if old not in s: raise SystemExit(f'missing layout {old}')
    s = s.replace(old, new, 1)
s = s.replace('target->SetWidgetHighlight(current.widget, TC_YELLOW);','target->SetWidgetHighlight(current.widget, TC_WHITE);',2)

if '#include "newgrf_config.h"' not in s:
    a = '#include "company_base.h"\n'
    if a not in s: raise SystemExit('missing include anchor')
    s = s.replace(a, a + '#include "newgrf_config.h"\n', 1)

a = '\tdecltype(_settings_newgame.game_creation.map_x) map_x{};\n'
if a not in s: raise SystemExit('missing saved settings anchor')
s = s.replace(a, a + '\tdecltype(_settings_newgame.game_creation.starting_year) starting_year{};\n\tdecltype(_settings_newgame.difficulty.max_no_competitors) max_no_competitors{};\n', 1)
a = 'static BrowserTutorialSavedSettings _browser_tutorial_saved_settings{};\nstatic bool _browser_tutorial_settings_saved = false;\n'
if a not in s: raise SystemExit('missing globals anchor')
s = s.replace(a, 'static BrowserTutorialSavedSettings _browser_tutorial_saved_settings{};\nstatic GRFConfigList _browser_tutorial_saved_newgrfs{};\nstatic bool _browser_tutorial_settings_saved = false;\n', 1)
a = '\ts.map_x = _settings_newgame.game_creation.map_x; s.map_y = _settings_newgame.game_creation.map_y;\n'
if a not in s: raise SystemExit('missing save anchor')
s = s.replace(a, a + '\ts.starting_year = _settings_newgame.game_creation.starting_year;\n\ts.max_no_competitors = _settings_newgame.difficulty.max_no_competitors;\n\tClearGRFConfigList(_browser_tutorial_saved_newgrfs);\n\tCopyGRFConfigList(_browser_tutorial_saved_newgrfs, _grfconfig_newgame, false);\n', 1)
a = '\t_settings_newgame.game_creation.map_x = s.map_x; _settings_newgame.game_creation.map_y = s.map_y;\n'
if a not in s: raise SystemExit('missing restore anchor')
s = s.replace(a, a + '\t_settings_newgame.game_creation.starting_year = s.starting_year;\n\t_settings_newgame.difficulty.max_no_competitors = s.max_no_competitors;\n', 1)
a = '\t_settings_newgame.difficulty.town_council_tolerance = s.town_council_tolerance; _settings_newgame.difficulty.disasters = s.disasters;\n\t_browser_tutorial_settings_saved = false;\n'
if a not in s: raise SystemExit('missing restore tail')
s = s.replace(a, '\t_settings_newgame.difficulty.town_council_tolerance = s.town_council_tolerance; _settings_newgame.difficulty.disasters = s.disasters;\n\tClearGRFConfigList(_grfconfig_newgame);\n\tCopyGRFConfigList(_grfconfig_newgame, _browser_tutorial_saved_newgrfs, false);\n\tClearGRFConfigList(_browser_tutorial_saved_newgrfs);\n\t_browser_tutorial_settings_saved = false;\n', 1)
a = '\tBrowserTutorialSaveNewGameSettings();\n\t_settings_newgame.game_creation.map_x = 6; _settings_newgame.game_creation.map_y = 6;\n'
if a not in s: raise SystemExit('missing tutorial start')
s = s.replace(a, '\tBrowserTutorialSaveNewGameSettings();\n\t_settings_newgame.game_creation.starting_year = TimerGameCalendar::Year{1950};\n\t_settings_newgame.difficulty.max_no_competitors = 0;\n\tClearGRFConfigList(_grfconfig_newgame);\n\t_settings_newgame.game_creation.map_x = 6; _settings_newgame.game_creation.map_y = 6;\n', 1)
a = '\t_settings_newgame.difficulty.max_loan = 1000000; _settings_newgame.difficulty.vehicle_breakdowns = 0;\n'
if a not in s: raise SystemExit('missing tutorial difficulty')
s = s.replace(a, '\t_settings_newgame.difficulty.max_loan = 300000; _settings_newgame.difficulty.vehicle_breakdowns = VehicleBreakdowns::Reduced;\n', 1)
for m in ['SetMinimalSize(640, 240)','starting_year = TimerGameCalendar::Year{1950}','ClearGRFConfigList(_grfconfig_newgame)','TC_WHITE']:
    if m not in s: raise SystemExit(f'missing marker {m}')
p.write_text(s, encoding='utf-8')

ru = Path('openttd/src/lang/russian.txt'); en = Path('openttd/src/lang/english.txt')
add_details(ru, RU, 'Подсказка'); add_details(en, EN, 'Tip')
set_string(ru, 'STR_BROWSER_TUTORIAL_COACH_HINT', '{YELLOW}Выполните условие шага и следуйте яркой подсветке. Далее включится автоматически.{BLACK}')
set_string(en, 'STR_BROWSER_TUTORIAL_COACH_HINT', '{YELLOW}Complete the objective and follow the bright highlight. Next unlocks automatically.{BLACK}')
print('Final tutorial polish applied.')
