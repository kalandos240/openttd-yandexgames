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


def sub_once(text, pattern, replacement, label, flags=0):
    new, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'Could not patch {label}')
    return new


def patch_source():
    def patch_cmake(text):
        old = '\\"_main\\", \\"_em_openttd_add_server\\"'
        new = '\\"_main\\", \\"_em_openttd_add_server\\", \\"_em_openttd_set_platform_pause\\"'
        if old not in text:
            raise SystemExit('Could not find Emscripten exported functions list')
        return text.replace(old, new, 1)

    edit('CMakeLists.txt', patch_cmake)

    def patch_network(text):
        text = sub_once(
            text,
            r'void NetworkStartUp\(\)\n\{\n.*?\n\}\n\n/\*\* This shuts the network down \*/',
            '''void NetworkStartUp()
{
    Debug(net, 3, "OpenTTD networking disabled in Yandex Games build");
    _network_available = false;
    _networking = false;
    _network_server = false;
    _network_dedicated = false;
    _is_network_server = false;
    _network_game_info = {};
}

/** This shuts the network down */''',
            'NetworkStartUp',
            re.S,
        )
        text = sub_once(
            text,
            r'void NetworkShutDown\(\)\n\{\n.*?\n\}',
            '''void NetworkShutDown()
{
    _network_available = false;
    _networking = false;
    _network_server = false;
    _network_dedicated = false;
    _is_network_server = false;
}''',
            'NetworkShutDown',
            re.S,
        )
        return text

    edit('src/network/network.cpp', patch_network)

    def patch_intro(text):
        # Remove the player-facing Multiplayer section and Online Content button.
        # Keep their click handlers compiled but unreachable; this is much safer
        # than deleting scoped switch branches and networking is hard-disabled.
        text = sub_once(
            text,
            r'\n\t\t\t/\* Multi player \*/\n\t\t\tNWidget\(NWID_VERTICAL\).*?\n\t\t\tEndContainer\(\),\n',
            '\n',
            'main-menu multiplayer widget block',
            re.S,
        )
        text = sub_once(
            text,
            r'\n\t\t\t\tNWidget\(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD\),[^\n]*\n',
            '\n',
            'main-menu Online Content button',
        )
        text = text.replace('\t\t_survey.Transmit(NetworkSurveyHandler::Reason::EXIT, true);\n', '')
        for needle in (
            'NWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_PLAY_NETWORK)',
            'NWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD)',
        ):
            if needle in text:
                raise SystemExit(f'Offline main-menu verification failed: {needle}')
        return text

    edit('src/intro_gui.cpp', patch_intro)

    def patch_help(text):
        # Remove the entire Websites frame. Local README/license/help remain.
        return sub_once(
            text,
            r'\n\t\t\tNWidget\(WWT_FRAME, COLOUR_DARK_GREEN\), SetStringTip\(STR_HELP_WINDOW_WEBSITES\),.*?\n\t\t\tEndContainer\(\),\n',
            '\n',
            'Help websites frame',
            re.S,
        )

    edit('src/help_gui.cpp', patch_help)

    def strip_script_online_widgets(text, prefix):
        before = text
        text = re.sub(
            rf'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_{prefix}_CONTENT_DOWNLOAD\),[^\n]*',
            '', text, count=1,
        )
        text = re.sub(
            rf'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_{prefix}_OPEN_URL\),[^\n]*',
            '', text, count=1,
        )
        text = re.sub(
            rf'\n[ \t]*this->SetWidgetDisabledState\(WID_{prefix}_OPEN_URL,[^\n]*\);',
            '', text,
        )
        if text == before:
            raise SystemExit(f'Could not remove {prefix} online widgets')
        for needle in (
            f'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_{prefix}_CONTENT_DOWNLOAD)',
            f'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_{prefix}_OPEN_URL)',
        ):
            if needle in text:
                raise SystemExit(f'{prefix} offline verification failed: {needle}')
        return text

    edit('src/ai/ai_gui.cpp', lambda t: strip_script_online_widgets(t, 'AIC'))
    edit('src/game/game_gui.cpp', lambda t: strip_script_online_widgets(t, 'GSC'))

    def patch_newgrf(text):
        # Only remove GUI nodes and direct GUI updates. Leave switch handlers and
        # UpdateWidgetSize cases intact and unreachable. This avoids unbalancing
        # scoped case blocks in upstream 15.3.
        original = text
        text = re.sub(
            r'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_CONTENT_DOWNLOAD2?\),[^\n]*\n[ \t]*SetStringTip\([^\n]*\),',
            '', text,
        )
        text = re.sub(
            r'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_OPEN_URL\),[^\n]*\n[ \t]*SetStringTip\([^\n]*\),',
            '', text,
        )
        text = re.sub(
            r'\n[ \t]*this->GetWidget<NWidgetCore>\(WID_NS_CONTENT_DOWNLOAD2?\)->SetStringTip\([^\n]*\);',
            '', text,
        )
        text = re.sub(
            r'\n[ \t]*this->SetWidgetDisabledState\(WID_NS_OPEN_URL,[^\n]*\);',
            '', text,
        )
        if text == original:
            raise SystemExit('Could not remove NewGRF online widgets')
        for needle in (
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_CONTENT_DOWNLOAD',
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_OPEN_URL)',
            'GetWidget<NWidgetCore>(WID_NS_CONTENT_DOWNLOAD',
        ):
            if needle in text:
                raise SystemExit(f'NewGRF offline verification failed: {needle}')
        return text

    edit('src/newgrf_gui.cpp', patch_newgrf)

    def patch_fios(text):
        # The savegame load dialog keeps its selection node but it is forced to
        # SZSP_NONE, so the Online Content child can never be displayed.
        text = sub_once(
            text,
            r'\n\t\tif \(this->fop == SLO_LOAD && this->abstract_filetype == FT_SAVEGAME\) \{\n'
            r'\t\t\tthis->GetWidget<NWidgetStacked>\(WID_SL_CONTENT_DOWNLOAD_SEL\)->SetDisplayedPlane\(SZSP_HORIZONTAL\);\n'
            r'\t\t\}\n',
            '\n\t\tthis->GetWidget<NWidgetStacked>(WID_SL_CONTENT_DOWNLOAD_SEL)->SetDisplayedPlane(SZSP_NONE);\n',
            'save/load Online Content visibility',
        )

        # Heightmap dialog has a direct Online Content button, remove just its
        # two widget-definition lines and keep the adjacent Load button.
        text = sub_once(
            text,
            r'\n\t\tNWidget\(WWT_PUSHTXTBTN, COLOUR_GREY, WID_SL_CONTENT_DOWNLOAD\),[^\n]*\n'
            r'\t\t\t\tSetStringTip\(STR_INTRO_ONLINE_CONTENT, STR_INTRO_TOOLTIP_ONLINE_CONTENT\),',
            '',
            'heightmap Online Content button',
        )

        text = sub_once(
            text,
            r'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, COLOUR_GREY, WID_SL_MISSING_NEWGRFS\),[^\n]*',
            '',
            'missing-content download button',
        )
        text = re.sub(
            r'\n[ \t]*this->SetWidgetDisabledState\(WID_SL_MISSING_NEWGRFS,\n[ \t]*[^\n]*\);',
            '', text, count=1,
        )
        return text

    edit('src/fios_gui.cpp', patch_fios)

    def patch_settings(text):
        survey_old = 'if constexpr (!NetworkSurveyHandler::IsSurveyPossible()) this->GetWidget<NWidgetStacked>(WID_GO_SURVEY_SEL)->SetDisplayedPlane(SZSP_NONE);'
        survey_new = 'this->GetWidget<NWidgetStacked>(WID_GO_SURVEY_SEL)->SetDisplayedPlane(SZSP_NONE);'
        if survey_old not in text:
            raise SystemExit('Could not find survey visibility line in Game Options')
        text = text.replace(survey_old, survey_new, 1)

        text, social_tab = re.subn(
            r'\n[ \t]*NWidget\(WWT_TEXTBTN, GAME_OPTIONS_BUTTON, WID_GO_TAB_SOCIAL\),[^\n]*',
            '', text, count=1,
        )
        if social_tab != 1:
            raise SystemExit('Could not remove Social tab button')
        text = text.replace(', WID_GO_TAB_SOCIAL);', ');')
        text = text.replace('\t\t\tcase WID_GO_TAB_SOCIAL: plane = 3; break;\n', '')
        text = text.replace('\t\t\tcase WID_GO_TAB_SOCIAL:\n', '')

        ids = [
            'WID_GO_BASE_GRF_CONTENT_DOWNLOAD',
            'WID_GO_BASE_SFX_CONTENT_DOWNLOAD',
            'WID_GO_BASE_MUSIC_CONTENT_DOWNLOAD',
            'WID_GO_BASE_GRF_OPEN_URL',
            'WID_GO_BASE_SFX_OPEN_URL',
            'WID_GO_BASE_MUSIC_OPEN_URL',
        ]
        for wid in ids:
            text, count = re.subn(
                rf'\n[ \t]*NWidget\(WWT_PUSHTXTBTN, GAME_OPTIONS_BUTTON, {wid}\),[^\n]*',
                '', text, count=1,
            )
            if count != 1:
                raise SystemExit(f'Could not remove game-options widget {wid}')
            text = re.sub(
                rf'\n[ \t]*this->SetWidgetDisabledState\({wid},[^\n]*\);',
                '', text,
            )

        text = re.sub(
            r'\n\t\tthis->SetWidgetsDisabledState\(!_network_available, WID_GO_BASE_GRF_CONTENT_DOWNLOAD, WID_GO_BASE_SFX_CONTENT_DOWNLOAD, WID_GO_BASE_MUSIC_CONTENT_DOWNLOAD\);',
            '', text, count=1,
        )
        return text

    edit('src/settings_gui.cpp', patch_settings)

    def patch_openttd(text):
        if '#include <emscripten.h>' not in text:
            anchor = '#include "safeguards.h"\n'
            if anchor not in text:
                raise SystemExit('Could not find safeguards include in openttd.cpp')
            text = text.replace(
                anchor,
                '#ifdef __EMSCRIPTEN__\n#include <emscripten.h>\n#endif\n\n' + anchor,
                1,
            )

        text, social_count = re.subn(
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
            text,
            count=1,
            flags=re.S,
        )
        if social_count != 1:
            raise SystemExit('Could not disable OpenTTD social integration')

        text = text.replace(
            '\tif (_game_mode == GM_NORMAL && new_mode != SM_SAVE_GAME) _survey.Transmit(NetworkSurveyHandler::Reason::LEAVE);\n',
            '',
        )
        text = sub_once(
            text,
            r'\n\t\tcase SM_JOIN_GAME: // Join a multiplayer game\n.*?\n\t\t\tbreak;\n',
            '\n\t\tcase SM_JOIN_GAME: // Disabled in Yandex Games single-player build\n\t\t\tLoadIntroGame();\n\t\t\tbreak;\n',
            'SM_JOIN_GAME',
            re.S,
        )
        text = re.sub(
            r'\n\t\t\tif \(_settings_client.network.participate_survey == PS_ASK\) \{.*?\n\t\t\t\}\n',
            '\n', text, count=1, flags=re.S,
        )
        text = text.replace('\tSocialIntegration::RunCallbacks();\n', '')
        return text

    edit('src/openttd.cpp', patch_openttd)

    # Verification is deliberately player-facing: hidden/unreachable switch
    # cases may stay compiled, but no online controls are constructed.
    checks = {
        'src/intro_gui.cpp': [
            'NWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_PLAY_NETWORK)',
            'NWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_CONTENT_DOWNLOAD)',
        ],
        'src/ai/ai_gui.cpp': [
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_AIC_CONTENT_DOWNLOAD)',
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_AIC_OPEN_URL)',
        ],
        'src/game/game_gui.cpp': [
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_GSC_CONTENT_DOWNLOAD)',
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_GSC_OPEN_URL)',
        ],
        'src/newgrf_gui.cpp': [
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_CONTENT_DOWNLOAD',
            'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_OPEN_URL)',
        ],
        'src/settings_gui.cpp': [
            'NWidget(WWT_TEXTBTN, GAME_OPTIONS_BUTTON, WID_GO_TAB_SOCIAL)',
            'NWidget(WWT_PUSHTXTBTN, GAME_OPTIONS_BUTTON, WID_GO_BASE_GRF_CONTENT_DOWNLOAD)',
            'NWidget(WWT_PUSHTXTBTN, GAME_OPTIONS_BUTTON, WID_GO_BASE_SFX_CONTENT_DOWNLOAD)',
            'NWidget(WWT_PUSHTXTBTN, GAME_OPTIONS_BUTTON, WID_GO_BASE_MUSIC_CONTENT_DOWNLOAD)',
        ],
    }
    for rel, needles in checks.items():
        data = (ROOT / rel).read_text()
        for needle in needles:
            if needle in data:
                raise SystemExit(f'Offline UI verification failed in {rel}: {needle}')

    print('Offline/single-player source patch applied and UI verified.')


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

    # Make all legacy OpenTTD web-network helpers inert. The Yandex SDK itself
    # remains available; only OpenTTD multiplayer/content networking is disabled.
    text = re.sub(
        r"Module\['websocket'\] = \{ url: function\(host, port, proto\) \{.*?\n\} \};",
        "Module['websocket'] = { url: function() { return null; } };",
        text,
        count=1,
        flags=re.S,
    )

    text = re.sub(
        r"    window\.openttd_server_list = function\(\) \{.*?\n    \}\n\n    var leftButtonDown",
        "    window.openttd_server_list = function() {};\n\n    var leftButtonDown",
        text,
        count=1,
        flags=re.S,
    )

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
    print('Yandex cloud/pre.js patch applied; legacy web networking disabled.')


if len(sys.argv) != 2 or sys.argv[1] not in {'source', 'pre'}:
    raise SystemExit('usage: patch-yandex-offline.py source|pre')
if sys.argv[1] == 'source':
    patch_source()
else:
    patch_pre()
