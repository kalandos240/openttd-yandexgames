#!/usr/bin/env python3
from pathlib import Path


def append_language_strings(path: Path, block: str, marker: str) -> None:
    text = path.read_text(encoding='utf-8')
    if marker in text:
        return
    if not text.endswith('\n'):
        text += '\n'
    text += '\n# Playgama local-content UI\n' + block.strip() + '\n'
    path.write_text(text, encoding='utf-8')


append_language_strings(
    Path('openttd/src/lang/english.txt'),
    '''
STR_PLAYGAMA_LICENSES                                           :Licenses
STR_PLAYGAMA_LICENSES_TOOLTIP                                   :View licenses and third-party notices for OpenTTD and all bundled content
''',
    'STR_PLAYGAMA_LICENSES',
)
append_language_strings(
    Path('openttd/src/lang/russian.txt'),
    '''
STR_PLAYGAMA_LICENSES                                           :Лицензии
STR_PLAYGAMA_LICENSES_TOOLTIP                                   :Посмотреть лицензии OpenTTD и всех встроенных компонентов и дополнений
''',
    'STR_PLAYGAMA_LICENSES',
)

intro_path = Path('openttd/src/intro_gui.cpp')
text = intro_path.read_text(encoding='utf-8')

for include_anchor, anchor in (
    ('#include "newgrf_config.h"\n', '#include "highscore.h"\n'),
    ('#include "textfile_gui.h"\n', '#include "newgrf_config.h"\n'),
):
    if include_anchor not in text:
        if anchor not in text:
            raise SystemExit(f'Could not find intro include anchor: {anchor!r}')
        text = text.replace(anchor, anchor + include_anchor, 1)

license_window = r'''
/** Native viewer for the complete Playgama distribution license bundle. */
struct PlaygamaLicensesWindow final : public TextfileWindow {
    PlaygamaLicensesWindow() : TextfileWindow(nullptr, TFT_LICENSE)
    {
        this->ConstructWindow();
        this->LoadTextfile("/home/web_user/.openttd/PLAYGAMA-LICENSES.md", NO_DIRECTORY);
    }
};

static void ShowPlaygamaLicenses()
{
    CloseWindowByClass(WC_TEXTFILE);
    new PlaygamaLicensesWindow();
}

'''
select_game_anchor = 'struct SelectGameWindow : public Window {'
if 'struct PlaygamaLicensesWindow final' not in text:
    if select_game_anchor not in text:
        raise SystemExit('Could not find SelectGameWindow declaration')
    text = text.replace(select_game_anchor, license_window + select_game_anchor, 1)

old_handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\tif (!_network_available) {\n\t\t\t\t\tShowErrorMessage(GetEncodedString(STR_NETWORK_ERROR_NOTAVAILABLE), {}, WL_ERROR);\n\t\t\t\t} else {\n\t\t\t\t\tShowNetworkContentListWindow();\n\t\t\t\t}\n\t\t\t\tbreak;'''
new_handler = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\t/* Playgama edition: this slot is a direct local NewGRF settings button. */\n\t\t\t\t/* The startup installer should have populated the catalogue already; */\n\t\t\t\t/* rescan defensively if the initial list is unexpectedly empty. */\n\t\t\t\tif (_all_grfs.empty()) ScanNewGRFFiles(nullptr);\n\t\t\t\tShowNewGRFSettings(true, true, false, _grfconfig_newgame);\n\t\t\t\tbreak;'''
if 'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);' not in text:
    if old_handler not in text:
        raise SystemExit('Could not find the retained Online Content click handler')
    text = text.replace(old_handler, new_handler, 1)
else:
    old_v7 = '''\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:\n\t\t\t\t/* Playgama edition: this slot is a direct local NewGRF settings button. */\n\t\t\t\tShowNewGRFSettings(true, true, false, _grfconfig_newgame);\n\t\t\t\tbreak;'''
    if old_v7 in text:
        text = text.replace(old_v7, new_handler, 1)

old_help = '\t\t\tcase WID_SGI_HELP:            ShowHelpWindow(); break;'
new_help = '\t\t\tcase WID_SGI_HELP:            ShowPlaygamaLicenses(); break;'
if new_help not in text:
    if old_help not in text:
        raise SystemExit('Could not find main-menu Help click handler for license repurpose')
    text = text.replace(old_help, new_help, 1)

options_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_OPTIONS), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SETTINGS, STR_INTRO_GAME_OPTIONS, STR_INTRO_TOOLTIP_GAME_OPTIONS), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
newgrf_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
license_widget = '''\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_HELP), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_QUERY, STR_PLAYGAMA_LICENSES, STR_PLAYGAMA_LICENSES_TOOLTIP), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'''
if newgrf_widget not in text:
    if options_widget not in text:
        raise SystemExit('Could not find main-menu Game Options widget insertion point')
    text = text.replace(options_widget, options_widget + newgrf_widget, 1)
if license_widget not in text:
    if newgrf_widget not in text:
        raise SystemExit('Could not find NewGRF widget insertion point for Licenses')
    text = text.replace(newgrf_widget, newgrf_widget + license_widget, 1)

checks = (
    '#include "newgrf_config.h"',
    '#include "textfile_gui.h"',
    'if (_all_grfs.empty()) ScanNewGRFFiles(nullptr);',
    'ShowNewGRFSettings(true, true, false, _grfconfig_newgame);',
    'SetSpriteStringTip(SPR_IMG_SHOW_VEHICLES, STR_MAPGEN_NEWGRF_SETTINGS, STR_MAPGEN_NEWGRF_SETTINGS_TOOLTIP)',
    'ShowPlaygamaLicenses();',
    'SetSpriteStringTip(SPR_IMG_QUERY, STR_PLAYGAMA_LICENSES, STR_PLAYGAMA_LICENSES_TOOLTIP)',
    'PLAYGAMA-LICENSES.md',
)
for check in checks:
    if text.count(check) != 1:
        raise SystemExit(f'Unexpected Playgama main-menu patch count for {check!r}: {text.count(check)}')

if 'ShowNetworkContentListWindow();' in text:
    raise SystemExit('Main-menu Online Content handler still reachable after Playgama patch')

intro_path.write_text(text, encoding='utf-8')

# Localize only the descriptions of the bundled NewGRFs. Their upstream names,
# parameters and English metadata remain untouched. OpenTTD itself decides the
# active language; when it is not Russian this helper returns nullopt and the
# original NewGRF-provided description is rendered exactly as before.
newgrf_path = Path('openttd/src/newgrf_gui.cpp')
newgrf = newgrf_path.read_text(encoding='utf-8')
helper_marker = 'GetBundledGRFRussianDescription'
helper = r'''
/** Russian descriptions for the NewGRFs bundled with this browser edition. */
static std::optional<std::string_view> GetBundledGRFRussianDescription(const GRFConfig &c)
{
    if (!GetCurrentLanguageIsoCode().starts_with("ru")) return std::nullopt;

    switch (std::byteswap(c.ident.grfid)) {
        case 0x43411223: return "Комплексный набор поездов: паровые, дизельные и электрические составы с 1860 по 2020 год. Также включает скоростные, узкоколейные, метро- и пассажирские поезда. Набор вдохновлён железными дорогами Великобритании и Ирландии. Лицензия: GPL v2."; // Iron Horse 4
        case 0xF1250009: return "Расширенный набор промышленности и грузов для OpenTTD. Добавляет новые производственные цепочки, предприятия и варианты развития экономики. Не используйте одновременно с другим полным набором промышленности, например GIST. Лицензия: GPL v2."; // FIRS Industries 5
        case 0x9787EAFE: return "Набор дорожного транспорта: автобусы, грузовики и трамваи разных эпох. Предназначен для более разнообразных пассажирских и грузовых перевозок по дорогам. Лицензия: GPL v2."; // Road Hog
        case 0x55440100: return "Набор промышленности в немецком стиле с дополнительными предприятиями, грузами и производственными цепочками. Используйте как альтернативу другим полным наборам промышленности, например FIRS. Лицензия: GPL v2."; // GIST
        case 0x474C0501: return "Набор ранних транспортных средств, расширяющий выбор техники для начала игры в более ранние годы. Добавляет исторические варианты транспорта до появления стандартной техники поздних эпох. Лицензия: GPL v2."; // Early Vehicle Set
        case 0x4F475A01: return "Дополнительные настройки графического набора OpenGFX2. Позволяет менять визуальные параметры и варианты оформления OpenGFX2 без замены основной игровой механики. Лицензия: GPL v2."; // OpenGFX2 Settings
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

newgrf_path.write_text(newgrf, encoding='utf-8')
print('Playgama/Yandex main menu patched; bundled NewGRF descriptions are localized for Russian UI.')
