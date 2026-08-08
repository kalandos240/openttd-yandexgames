#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path('openttd')


def edit(rel, transform):
    path = ROOT / rel
    text = path.read_text()
    new = transform(text)
    if new == text:
        raise SystemExit(f'Patch made no changes to {rel}')
    path.write_text(new)


def patch_source():
    def patch_cmake(text):
        old = '\\"_main\\", \\"_em_openttd_add_server\\"' 
        new = '\\"_main\\", \\"_em_openttd_add_server\\", \\"_em_openttd_set_platform_pause\\"' 
        if old not in text:
            raise SystemExit('Could not find Emscripten exported functions list')
        return text.replace(old, new, 1)

    edit('CMakeLists.txt', patch_cmake)

    def patch_network(text):
        pattern = re.compile(
            r'void NetworkStartUp\(\)\n\{\n.*?\n\}\n\n/\*\* This shuts the network down \*/',
            re.S,
        )
        replacement = '''void NetworkStartUp()
{
    Debug(net, 3, "OpenTTD networking disabled in Yandex Games build");
    _network_available = false;
    _networking = false;
    _network_server = false;
    _network_dedicated = false;
    _is_network_server = false;
    _network_game_info = {};
}

/** This shuts the network down */'''
        new, count = pattern.subn(replacement, text, count=1)
        if count != 1:
            raise SystemExit('Could not patch NetworkStartUp')
        shutdown_pattern = re.compile(
            r'void NetworkShutDown\(\)\n\{\n.*?\n\}',
            re.S,
        )
        shutdown_replacement = '''void NetworkShutDown()
{
    _network_available = false;
    _networking = false;
    _network_server = false;
    _network_dedicated = false;
    _is_network_server = false;
}'''
        new, shutdown_count = shutdown_pattern.subn(shutdown_replacement, new, count=1)
        if shutdown_count != 1:
            raise SystemExit('Could not patch NetworkShutDown')
        return new

    edit('src/network/network.cpp', patch_network)

    def patch_intro(text):
        text, c1 = re.subn(r'\n\t\t\tcase WID_SGI_PLAY_NETWORK:.*?\n\t\t\t\tbreak;\n', '\n', text, count=1, flags=re.S)
        text, c2 = re.subn(r'\n\t\t\tcase WID_SGI_CONTENT_DOWNLOAD:.*?\n\t\t\t\tbreak;\n', '\n', text, count=1, flags=re.S)
        text, c3 = re.subn(
            r'\n\t\t\t/\* Multi player \*/\n\t\t\tNWidget\(NWID_VERTICAL\).*?\n\t\t\tEndContainer\(\),\n',
            '\n', text, count=1, flags=re.S)
        text, c4 = re.subn(
            r'\n\t\t\t\tNWidget\(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD\),[^\n]*\n',
            '\n', text, count=1)
        text = text.replace('\t\t_survey.Transmit(NetworkSurveyHandler::Reason::EXIT, true);\n', '')
        if min(c1, c2, c3, c4) != 1:
            raise SystemExit(f'Could not fully patch intro GUI: {c1=} {c2=} {c3=} {c4=}')
        return text

    edit('src/intro_gui.cpp', patch_intro)

    def patch_help(text):
        text, count = re.subn(
            r'\n\t\t\tNWidget\(WWT_FRAME, COLOUR_DARK_GREEN\), SetStringTip\(STR_HELP_WINDOW_WEBSITES\),.*?\n\t\t\tEndContainer\(\),\n',
            '\n', text, count=1, flags=re.S)
        if count != 1:
            raise SystemExit('Could not remove Help websites frame')
        return text

    edit('src/help_gui.cpp', patch_help)

    def strip_script_online(text, prefix):
        text = re.sub(rf'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_{prefix}_CONTENT_DOWNLOAD\),[^\n]*', '', text)
        text = re.sub(rf'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_{prefix}_OPEN_URL\),[^\n]*', '', text)
        text = re.sub(rf'\n[ \t]*this->SetWidgetDisabledState\(WID_{prefix}_OPEN_URL,[^\n]*\);', '', text)
        text = re.sub(rf'\n\t\t\tcase WID_{prefix}_CONTENT_DOWNLOAD:.*?\n\t\t\t\tbreak;\n', '\n', text, count=1, flags=re.S)
        text = re.sub(rf'\n\t\t\tcase WID_{prefix}_OPEN_URL: \{{.*?\n\t\t\t\}}\n', '\n', text, count=1, flags=re.S)
        return text

    edit('src/ai/ai_gui.cpp', lambda t: strip_script_online(t, 'AIC'))
    edit('src/game/game_gui.cpp', lambda t: strip_script_online(t, 'GSC'))

    def patch_newgrf(text):
        text = re.sub(
            r'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_CONTENT_DOWNLOAD2?\),[^\n]*\n[ \t]*SetStringTip\([^\n]*\),',
            '', text)
        text = re.sub(
            r'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_OPEN_URL\),[^\n]*\n[ \t]*SetStringTip\([^\n]*\),',
            '', text)
        text = re.sub(r'\n[ \t]*this->GetWidget<NWidgetCore>\(WID_NS_CONTENT_DOWNLOAD2?\)->SetStringTip\([^\n]*\);', '', text)
        text = re.sub(r'\n[ \t]*this->SetWidgetDisabledState\(WID_NS_OPEN_URL,[^\n]*\);', '', text)
        text = re.sub(r'\n\t\t\tcase WID_NS_OPEN_URL: \{.*?\n\t\t\t\}\n', '\n', text, count=1, flags=re.S)
        text = re.sub(r'\n\t\t\tcase WID_NS_CONTENT_DOWNLOAD:\n\t\t\tcase WID_NS_CONTENT_DOWNLOAD2:.*?\n\t\t\t\tbreak;\n', '\n', text, count=1, flags=re.S)
        return text

    edit('src/newgrf_gui.cpp', patch_newgrf)

    def patch_fios(text):
        text, selector = re.subn(
            r'\n\t\t\t/\* Online Content button \*/\n\t\t\tNWidget\(NWID_SELECTION, INVALID_COLOUR, WID_SL_CONTENT_DOWNLOAD_SEL\),.*?\n\t\t\tEndContainer\(\),',
            '\n', text, count=1, flags=re.S)
        text = re.sub(
            r'\n\t/\* Online Content and Load button \*/\n\tNWidget\(NWID_HORIZONTAL, NWidContainerFlag::EqualSize\),\n\t\tNWidget\(WWT_PUSHTXTBTN, COLOUR_GREY, WID_SL_CONTENT_DOWNLOAD\),[^\n]*\n\t\t\t\tSetStringTip\([^\n]*\),',
            '\n\t/* Load button */\n\tNWidget(NWID_HORIZONTAL, NWidContainerFlag::EqualSize),', text, count=1)
        text = re.sub(r'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_GREY, WID_SL_MISSING_NEWGRFS\),[^\n]*', '', text)
        text = re.sub(
            r'\n\t\tif \(this->fop == SLO_LOAD && this->abstract_filetype == FT_SAVEGAME\) \{\n\t\t\tthis->GetWidget<NWidgetStacked>\(WID_SL_CONTENT_DOWNLOAD_SEL\)->SetDisplayedPlane\(SZSP_HORIZONTAL\);\n\t\t\}\n',
            '\n', text, count=1)
        text = re.sub(r'\n\t\t\tcase WID_SL_CONTENT_DOWNLOAD:.*?\n\t\t\t\tbreak;\n', '\n', text, count=1, flags=re.S)
        text = re.sub(r'\n\t\t\tcase WID_SL_MISSING_NEWGRFS:.*?\n\t\t\t\tbreak;\n', '\n', text, count=1, flags=re.S)
        text = re.sub(r'\n[ \t]*this->SetWidgetDisabledState\(WID_SL_MISSING_NEWGRFS,\n[ \t]*[^\n]*\);', '', text, count=1)
        if selector != 1:
            raise SystemExit('Could not remove save/load online-content selector')
        return text

    edit('src/fios_gui.cpp', patch_fios)

    def patch_settings(text):
        survey_old = 'if constexpr (!NetworkSurveyHandler::IsSurveyPossible()) this->GetWidget<NWidgetStacked>(WID_GO_SURVEY_SEL)->SetDisplayedPlane(SZSP_NONE);'
        survey_new = 'this->GetWidget<NWidgetStacked>(WID_GO_SURVEY_SEL)->SetDisplayedPlane(SZSP_NONE);'
        if survey_old not in text:
            raise SystemExit('Could not find survey visibility line in Game Options')
        text = text.replace(survey_old, survey_new, 1)

        text, social_tab = re.subn(r'\n[ \t]*NWidget\(WWT_TEXTBTN, GAME_OPTIONS_BUTTON, WID_GO_TAB_SOCIAL\),[^\n]*', '', text, count=1)
        if social_tab != 1:
            raise SystemExit('Could not remove Social tab button')
        text = text.replace(', WID_GO_TAB_SOCIAL);', ');')
        text = text.replace('\t\t\tcase WID_GO_TAB_SOCIAL: plane = 3; break;\n', '')
        text = text.replace('\t\t\tcase WID_GO_TAB_SOCIAL:\n', '')

        ids = [
            'WID_GO_BASE_GRF_CONTENT_DOWNLOAD', 'WID_GO_BASE_SFX_CONTENT_DOWNLOAD', 'WID_GO_BASE_MUSIC_CONTENT_DOWNLOAD',
            'WID_GO_BASE_GRF_OPEN_URL', 'WID_GO_BASE_SFX_OPEN_URL', 'WID_GO_BASE_MUSIC_OPEN_URL',
        ]
        removed = 0
        for wid in ids:
            text, count = re.subn(rf'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, GAME_OPTIONS_BUTTON, {wid}\),[^\n]*', '', text, count=1)
            removed += count
            text = re.sub(rf'\n[ \t]*this->SetWidgetDisabledState\({wid},[^\n]*\);', '', text)
        if removed != len(ids):
            raise SystemExit(f'Could not remove every base-set online button: removed={removed}')

        text = re.sub(r'\n\t\tthis->SetWidgetsDisabledState\(!_network_available, WID_GO_BASE_GRF_CONTENT_DOWNLOAD, WID_GO_BASE_SFX_CONTENT_DOWNLOAD, WID_GO_BASE_MUSIC_CONTENT_DOWNLOAD\);', '', text, count=1)
        return text

    edit('src/settings_gui.cpp', patch_settings)

    def patch_openttd(text):
        if '#include <emscripten.h>' not in text:
            anchor = '#include "safeguards.h"\n'
            text = text.replace(anchor, '#ifdef __EMSCRIPTEN__\n#include <emscripten.h>\n#endif\n\n' + anchor, 1)
        text = re.sub(
            r'static void UpdateSocialIntegration\(GameMode game_mode\)\n\{.*?\n\}\n\nvoid SwitchToMode',
            '''static void UpdateSocialIntegration([[maybe_unused]] GameMode game_mode)
{
}

#ifdef __EMSCRIPTEN__
static bool _yandex_platform_pause_applied = false;

extern "C" void em_openttd_set_platform_pause(int paused)
{
    if (_game_mode != GM_NORMAL) return;

    if (paused != 0) {
        if (!_pause_mode.Test(PauseMode::Normal)) {
            _yandex_platform_pause_applied = true;
            Command<CMD_PAUSE>::Post(PauseMode::Normal, true);
        }
    } else if (_yandex_platform_pause_applied) {
        _yandex_platform_pause_applied = false;
        Command<CMD_PAUSE>::Post(PauseMode::Normal, false);
    }
}
#endif

void SwitchToMode''',
            text, count=1, flags=re.S)
        text = text.replace('\tif (_game_mode == GM_NORMAL && new_mode != SM_SAVE_GAME) _survey.Transmit(NetworkSurveyHandler::Reason::LEAVE);\n', '')
        text = re.sub(
            r'\n\t\tcase SM_JOIN_GAME: // Join a multiplayer game\n.*?\n\t\t\tbreak;\n',
            '\n\t\tcase SM_JOIN_GAME: // Disabled in Yandex Games single-player build\n\t\t\tLoadIntroGame();\n\t\t\tbreak;\n',
            text, count=1, flags=re.S)
        text = re.sub(r'\n\t\t\tif \(_settings_client.network.participate_survey == PS_ASK\) \{.*?\n\t\t\t\}\n', '\n', text, count=1, flags=re.S)
        marker = '\t\tdefault: NOT_REACHED();\n\t}\n}\n\n\n\n/**\n * State controlling game loop.'
        lifecycle = '''\t\tdefault: NOT_REACHED();
\t}

#ifdef __EMSCRIPTEN__
    EM_ASM({
        if (window.yandexGameSetGameplay) window.yandexGameSetGameplay(!!$0);
    }, _game_mode == GM_NORMAL ? 1 : 0);
#endif
}



/**
 * State controlling game loop.'''
        if marker not in text:
            raise SystemExit('Could not find SwitchToMode end for lifecycle hook')
        text = text.replace(marker, lifecycle, 1)
        text = text.replace('\tSocialIntegration::RunCallbacks();\n', '')
        return text

    edit('src/openttd.cpp', patch_openttd)

    main = (ROOT / 'src/intro_gui.cpp').read_text()
    for needle in ['WID_SGI_PLAY_NETWORK', 'WID_SGI_CONTENT_DOWNLOAD', 'STR_INTRO_MULTIPLAYER', 'STR_INTRO_ONLINE_CONTENT']:
        if needle in main:
            raise SystemExit(f'Offline UI verification failed: {needle} remains in intro_gui.cpp')
    print('Offline/single-player source patch applied.')


def patch_pre():
    path = ROOT / 'os/emscripten/pre.js'
    text = path.read_text()
    dependency = "            Module.removeRunDependency('syncfs');"
    replacement = """            const releaseStartup = function() {
                Module.removeRunDependency('syncfs');
            };
            if (window.yandexRestoreOpenTTDCloud) {
                Promise.race([
                    window.yandexRestoreOpenTTDCloud(FS, personal_dir),
                    new Promise(resolve => setTimeout(resolve, 2500))
                ]).then(releaseStartup, releaseStartup);
            } else {
                releaseStartup();
            }"""
    if dependency not in text:
        raise SystemExit('Could not find startup dependency release in pre.js')
    text = text.replace(dependency, replacement, 1)

    anchor = """    window.openttd_exit = function() {
        window.openttd_syncfs(Module.onExit);
    }
"""
    cloud_hook = """    const openttd_local_syncfs = window.openttd_syncfs;
    window.openttd_syncfs = function(callback) {
        openttd_local_syncfs(function() {
            if (window.yandexBackupOpenTTDCloud) window.yandexBackupOpenTTDCloud(FS, personal_dir);
            if (callback) callback();
        });
    }

"""
    if anchor not in text:
        raise SystemExit('Could not find openttd_exit anchor in pre.js')
    text = text.replace(anchor, cloud_hook + anchor, 1)

    start_marker = "    window.openttd_open_url = function(url, url_len) {"
    start = text.find(start_marker)
    if start != -1:
        end_marker = "\n\n    /* https://github.com/emscripten-core/emscripten/pull/12995"
        end = text.find(end_marker, start)
        if end == -1:
            raise SystemExit('Could not find end of openttd_open_url')
        text = text[:start] + """    window.openttd_open_url = function(url, url_len) {
        console.warn('External URLs are disabled in the Yandex Games edition.');
    }
""" + text[end:]
    path.write_text(text)
    print('Yandex cloud/pre.js patch applied.')


if len(sys.argv) != 2 or sys.argv[1] not in {'source', 'pre'}:
    raise SystemExit('usage: patch-yandex-offline.py source|pre')
if sys.argv[1] == 'source':
    patch_source()
else:
    patch_pre()
