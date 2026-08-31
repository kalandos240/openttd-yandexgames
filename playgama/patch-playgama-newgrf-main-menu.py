#!/usr/bin/env python3
from pathlib import Path

intro_path = Path('openttd/src/intro_gui.cpp')
text = intro_path.read_text(encoding='utf-8')

include_anchor = '#include "highscore.h"\n'
include_line = '#include "newgrf_config.h"\n'
if include_line not in text:
    if include_anchor not in text:
        raise SystemExit(f'Could not find intro include anchor: {include_anchor!r}')
    text = text.replace(include_anchor, include_anchor + include_line, 1)

old_handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\tif (!_network_available) {\n\t\t\t\t\tShowErrorMessage(GetEncodedString(STR_NETWORK_ERROR_NOTAVAILABLE), {}, WL_ERROR);\n\t\t\t\t} else {\n\t\t\t\t\tShowNetworkContentListWindow();\n\t\t\t\t}\n\t\t\t\tbreak;'''
new_handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\t/* Browser edition: this slot opens the local bundled NewGRF list. */\n\t\t\t\t/* Avoid repeated scans: only scan when the native catalogue is empty. */\n\t\t\t\tif (_all_grfs.empty()) ScanNewGRFFiles(nullptr);\n\t\t\t\tShowNewGRFSettings(true, true, false, _grfconfig_newgame);\n\t\t\t\tbreak;'''
if 'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);' not in text:
    if old_handler not in text:
        raise SystemExit('Could not find the retained Online Content click handler')
    text = text.replace(old_handler, new_handler, 1)
else:
    old_v7 = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\t/* Playgama edition: this slot is a direct local NewGRF settings button. */\n\t\t\t\tShowNewGRFSettings(true, true, false, _grfconfig_newgame);\n\t\t\t\tbreak;'''
    if old_v7 in text:
        text = text.replace(old_v7, new_handler, 1)

options_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_OPTIONS), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SETTINGS, STR_INTRO_GAME_OPTIONS, STR_INTRO_TOOLTIP_GAME_OPTIONS), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
newgrf_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
if newgrf_widget not in text:
    if options_widget not in text:
        raise SystemExit('Could not find main-menu Game Options widget insertion point')
    text = text.replace(options_widget, options_widget + newgrf_widget, 1)

# Keep the normal Help action. Earlier builds replaced it with a custom license
# viewer, which added unrelated native UI/code and required a large document to
# be copied into the virtual filesystem. Legal notices stay as static package
# files and are never part of gameplay/runtime execution.
if 'ShowPlaygamaLicenses();' in text or 'PlaygamaLicensesWindow' in text or 'STR_PLAYGAMA_LICENSES' in text:
    raise SystemExit('Unexpected legacy in-game license UI remains in intro_gui.cpp')

checks = (
    '#include "newgrf_config.h"',
    'if (_all_grfs.empty()) ScanNewGRFFiles(nullptr);',
    'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);',
    'SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP)',
    'case WID_SGI_HELP:            ShowHelpWindow(); break;',
)
for check in checks:
    if text.count(check) != 1:
        raise SystemExit(f'Unexpected browser main-menu patch count for {check!r}: {text.count(check)}')

if 'ShowNetworkContentListWindow();' in text:
    raise SystemExit('Main-menu Online Content handler still reachable after browser patch')

intro_path.write_text(text, encoding='utf-8')

# Localize only descriptions of the bundled NewGRFs. License labels are not
# rendered in gameplay UI; the required legal texts remain static distribution
# files instead of being duplicated into native strings/windows.
newgrf_path = Path('openttd/src/newgrf_gui.cpp')
newgrf = newgrf_path.read_text(encoding='utf-8')
helper_marker = 'GetBundledGRFRussianDescription'
helper = r'''
/** Russian descriptions for the NewGRFs bundled with this browser edition. */
static std::optional<std::string_view> GetBundledGRFRussianDescription(const GRFConfig &c)
{
    if (!GetCurrentLanguageIsoCode().starts_with("ru")) return std::nullopt;

    switch (std::byteswap(c.ident.grfid)) {
        case 0x43411223: return "Комплексный набор поездов: паровые, дизельные и электрические составы с 1860 по 2020 год. Также включает скоростные, узкоколейные, метро- и пассажирские поезда. Набор вдохновлён железными дорогами Великобритании и Ирландии."; // Iron Horse 4
        case 0xF1250009: return "Расширенный набор промышленности и грузов для OpenTTD. Добавляет новые производственные цепочки, предприятия и варианты развития экономики. Не используйте одновременно с другим полным набором промышленности, например GIST."; // FIRS Industries 5
        case 0x9787EAFE: return "Набор дорожного транспорта: автобусы, грузовики и трамваи разных эпох. Предназначен для более разнообразных пассажирских и грузовых перевозок по дорогам."; // Road Hog
        case 0x55440100: return "Набор промышленности в немецком стиле с дополнительными предприятиями, грузами и производственными цепочками. Используйте как альтернативу другим полным наборам промышленности, например FIRS."; // GIST
        case 0x474C0501: return "Набор ранних транспортных средств, расширяющий выбор техники для начала игры в более ранние годы. Добавляет исторические варианты транспорта до появления стандартной техники поздних эпох."; // Early Vehicle Set
        case 0x4F475A01: return "Дополнительные настройки графического набора OpenGFX2. Позволяет менять визуальные параметры и варианты оформления OpenGFX2 без замены основной игровой механики."; // OpenGFX2 Settings
        default: return std::nullopt;
    }
}

'''
show_info_anchor = 'static void ShowNewGRFInfo(const GRFConfig &c, const Rect &r, bool show_params)\n'
if helper_marker not in newgrf:
    if show_info_anchor not in newgrf:
        raise SystemExit('Could not find ShowNewGRFInfo insertion point')
    newgrf = newgrf.replace(show_info_anchor, helper + show_info_anchor, 1)

old_description = '''\t/* Draw GRF info if it exists */\n\tif (auto desc = c.GetDescription(); desc.has_value() && !desc->empty()) {\n\t\ttr.top = DrawStringMultiLine(tr, GetString(STR_JUST_RAW_STRING, std::move(*desc)), TC_BLACK);\n\t} else {\n\t\ttr.top = DrawStringMultiLine(tr, STR_NEWGRF_SETTINGS_NO_INFO);\n\t}\n'''
new_description = '''\t/* Prefer our Russian description only for bundled GRFs and only while the\n\t * OpenTTD interface language is Russian. All other languages keep the exact\n\t * metadata supplied by the NewGRF itself. */\n\tif (auto localized = GetBundledGRFRussianDescription(c); localized.has_value()) {\n\t\ttr.top = DrawStringMultiLine(tr, GetString(STR_JUST_RAW_STRING, std::string(*localized)), TC_BLACK);\n\t} else if (auto desc = c.GetDescription(); desc.has_value() && !desc->empty()) {\n\t\ttr.top = DrawStringMultiLine(tr, GetString(STR_JUST_RAW_STRING, std::move(*desc)), TC_BLACK);\n\t} else {\n\t\ttr.top = DrawStringMultiLine(tr, STR_NEWGRF_SETTINGS_NO_INFO);\n\t}\n'''
if new_description not in newgrf:
    if old_description not in newgrf:
        raise SystemExit('Could not find NewGRF description rendering block')
    newgrf = newgrf.replace(old_description, new_description, 1)

for check in (
    'GetBundledGRFRussianDescription',
    'GetCurrentLanguageIsoCode().starts_with("ru")',
    'case 0x43411223',
    'case 0xF1250009',
    'case 0x9787EAFE',
    'case 0x55440100',
    'case 0x474C0501',
    'case 0x4F475A01',
    'Комплексный набор поездов',
    'Расширенный набор промышленности и грузов',
):
    if check not in newgrf:
        raise SystemExit(f'Missing bundled NewGRF localization patch marker: {check!r}')

for forbidden in ('Лицензия:', 'License: GPL', 'GPL v2.'):
    if forbidden in newgrf:
        raise SystemExit(f'Legacy license label remains in NewGRF gameplay description: {forbidden!r}')

newgrf_path.write_text(newgrf, encoding='utf-8')
print('Browser main menu patched: local NewGRF access retained; runtime license UI removed.')
