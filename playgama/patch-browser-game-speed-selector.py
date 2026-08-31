#!/usr/bin/env python3
"""Keep OpenTTD 15.3's stock fast-forward behaviour in browser builds.

The browser edition must not replace the native fast-forward toggle with fixed
x2/x4/x8 choices. OpenTTD already implements the intended behaviour:
`ChangeGameSpeed(true)` switches to the unlimited game-tick mode (`_game_speed
== 0`) and `ChangeGameSpeed(false)` returns to normal speed. Rendering remains a
separate 60 Hz concern and is optimized after link without changing simulation
semantics.

This file is also a release-triggered native contract gate, so packaging/runtime
verification changes are rebuilt against the same stock-speed source baseline.
"""
from pathlib import Path


src = Path("openttd/src/toolbar_gui.cpp")
text = src.read_text(encoding="utf-8")

stock = '''/**
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

if stock not in text:
    raise SystemExit("Stock OpenTTD fast-forward handler is missing")

for forbidden in (
    "GameSpeedMenuEntries",
    "MenuClickGameSpeed",
    "_game_speed = 200",
    "_game_speed = 400",
    "_game_speed = 800",
    "STR_GAME_SPEED_X2",
    "STR_GAME_SPEED_X4",
    "STR_GAME_SPEED_X8",
):
    if forbidden in text:
        raise SystemExit(f"Non-vanilla browser speed selector remains: {forbidden}")

for lang_path in (Path("openttd/src/lang/english.txt"), Path("openttd/src/lang/russian.txt")):
    language = lang_path.read_text(encoding="utf-8")
    for forbidden in ("STR_GAME_SPEED_X2", "STR_GAME_SPEED_X4", "STR_GAME_SPEED_X8"):
        if forbidden in language:
            raise SystemExit(f"Non-vanilla speed string remains in {lang_path}: {forbidden}")

print("Vanilla OpenTTD fast-forward retained: normal speed <-> unlimited simulation speed.")
