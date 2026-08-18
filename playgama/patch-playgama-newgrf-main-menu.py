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

path = Path('openttd/src/intro_gui.cpp')
text = path.read_text(encoding='utf-8')

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

path.write_text(text, encoding='utf-8')
print('Playgama main menu now exposes local NewGRF Settings and complete Licenses viewer.')
