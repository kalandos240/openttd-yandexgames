#!/usr/bin/env python3
"""Add a native OpenTTD game-speed selector to the existing fast-forward button.

OpenTTD 15.3 represents simulation speed as a percentage in `_game_speed`.
100 is normal speed, so 200/400/800 are exact x2/x4/x8 tick rates. The browser
build also publishes the selected native speed to JavaScript so the Emscripten
software-framebuffer presenter can reduce expensive full-canvas copies while
fast-forward is active. Both native diagnostics and the final release workflow
compile this patch before any Playgama/Yandex package can be published.
"""
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one {label} anchor, found {count}")
    return text.replace(old, new, 1)


src = Path("openttd/src/toolbar_gui.cpp")
text = src.read_text(encoding="utf-8")

include_anchor = '#include "safeguards.h"\n'
emscripten_include = '''#ifdef __EMSCRIPTEN__
#\tinclude <emscripten.h>
#endif

#include "safeguards.h"
'''
if '#\tinclude <emscripten.h>' not in text:
    text = replace_once(text, include_anchor, emscripten_include, "Emscripten include")

old_click = '''/**
 * Toggle fast forward mode.
 *
 * @return #CBF_NONE
 */
static CallBackFunction ToolbarFastForwardClick(Window *)
{
\tif (_networking) return CBF_NONE; // no fast forward in network game

\tChangeGameSpeed(_game_speed == 100);

\tSndClickBeep();
\treturn CBF_NONE;
}
'''
new_click = '''/** Available native simulation speeds for the fast-forward toolbar menu. */
enum GameSpeedMenuEntries : uint8_t {
\tGSME_NORMAL,
\tGSME_X2,
\tGSME_X4,
\tGSME_X8,
};

static int CurrentGameSpeedMenuEntry()
{
\tswitch (_game_speed) {
\t\tcase 200: return GSME_X2;
\t\tcase 400: return GSME_X4;
\t\tcase 800: return GSME_X8;
\t\tdefault:  return GSME_NORMAL;
\t}
}

/** Tell the browser presentation layer which native simulation speed is active. */
static void PublishBrowserGameSpeed()
{
#ifdef __EMSCRIPTEN__
\tEM_ASM({
\t\twindow.__openttdGameSpeed = $0;
\t}, _game_speed);
#endif
}

/**
 * Open the native simulation-speed selector.
 *
 * OpenTTD's video driver calculates the game-tick interval from `_game_speed`,
 * where 100 is normal speed. Using 200/400/800 therefore provides exact
 * x2/x4/x8 simulation targets. The browser presentation layer may render less
 * often at higher speeds, while simulation ticks and input remain native.
 *
 * @return #CBF_NONE
 */
static CallBackFunction ToolbarFastForwardClick(Window *w)
{
\tif (_networking) return CBF_NONE; // no fast forward in network game

\tDropDownList list;
\tlist.push_back(MakeDropDownListCheckedItem(_game_speed == 100, STR_GAME_SPEED_NORMAL, GSME_NORMAL));
\tlist.push_back(MakeDropDownListCheckedItem(_game_speed == 200, STR_GAME_SPEED_X2, GSME_X2));
\tlist.push_back(MakeDropDownListCheckedItem(_game_speed == 400, STR_GAME_SPEED_X4, GSME_X4));
\tlist.push_back(MakeDropDownListCheckedItem(_game_speed == 800, STR_GAME_SPEED_X8, GSME_X8));
\tShowDropDownList(w, std::move(list), CurrentGameSpeedMenuEntry(), WID_TN_FAST_FORWARD, 120, GetToolbarDropDownOptions());

\tSndClickBeep();
\treturn CBF_NONE;
}

/** Apply a speed chosen from the stock toolbar dropdown. */
static CallBackFunction MenuClickGameSpeed(int index)
{
\tif (_networking) return CBF_NONE;

\tswitch (index) {
\t\tcase GSME_NORMAL: _game_speed = 100; break;
\t\tcase GSME_X2:     _game_speed = 200; break;
\t\tcase GSME_X4:     _game_speed = 400; break;
\t\tcase GSME_X8:     _game_speed = 800; break;
\t\tdefault: return CBF_NONE;
\t}

\tPublishBrowserGameSpeed();
\tMarkWholeScreenDirty();
\tSndClickBeep();
\treturn CBF_NONE;
}
'''

if "enum GameSpeedMenuEntries" not in text:
    text = replace_once(text, old_click, new_click, "fast-forward click handler")

old_table = '''static MenuClickedProc * const _menu_clicked_procs[] = {
\tnullptr,                 // 0
\tnullptr,                 // 1
\tMenuClickSettings,    // 2
'''
new_table = '''static MenuClickedProc * const _menu_clicked_procs[] = {
\tnullptr,                 // 0
\tMenuClickGameSpeed,   // 1
\tMenuClickSettings,    // 2
'''
if "MenuClickGameSpeed,   // 1" not in text:
    text = replace_once(text, old_table, new_table, "toolbar dropdown callback table")

for marker in (
    "case 200: return GSME_X2;",
    "case 400: return GSME_X4;",
    "case 800: return GSME_X8;",
    "window.__openttdGameSpeed = $0;",
    "PublishBrowserGameSpeed();",
):
    if marker not in text:
        raise SystemExit(f"Native speed selector marker missing after patch: {marker}")

src.write_text(text, encoding="utf-8")

english = Path("openttd/src/lang/english.txt")
russian = Path("openttd/src/lang/russian.txt")
english_text = english.read_text(encoding="utf-8")
russian_text = russian.read_text(encoding="utf-8")

english_block = '''\n# Browser edition native simulation-speed selector\nSTR_GAME_SPEED_NORMAL                                           :Normal speed (x1)\nSTR_GAME_SPEED_X2                                               :Fast forward x2\nSTR_GAME_SPEED_X4                                               :Fast forward x4\nSTR_GAME_SPEED_X8                                               :Fast forward x8\n'''
russian_block = '''\n# Browser edition native simulation-speed selector\nSTR_GAME_SPEED_NORMAL                                           :Обычная скорость (×1)\nSTR_GAME_SPEED_X2                                               :Ускорение ×2\nSTR_GAME_SPEED_X4                                               :Ускорение ×4\nSTR_GAME_SPEED_X8                                               :Ускорение ×8\n'''

if "STR_GAME_SPEED_X2" not in english_text:
    english_text = english_text.rstrip() + "\n" + english_block
if "STR_GAME_SPEED_X2" not in russian_text:
    russian_text = russian_text.rstrip() + "\n" + russian_block

english.write_text(english_text, encoding="utf-8")
russian.write_text(russian_text, encoding="utf-8")

print("Native OpenTTD speed selector installed: x1, x2, x4, x8 with browser render-speed signal.")
