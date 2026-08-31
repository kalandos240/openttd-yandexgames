#!/usr/bin/env python3
"""Make OpenTTD's zero competitor interval start requested AIs in the web port.

OpenTTD 15.3 normally treats difficulty.competitors_interval == 0 as an early
return in the competitor timeout callback. The web edition intentionally uses
zero as "start requested competitors immediately" and its browser scheduler
then spreads AI creation over a few ticks to avoid a single-frame spike.

There is a second upstream behaviour that must also be handled: every new game
calls StartupCompanies(), which aborts _new_competitor_timeout. Merely removing
the zero-interval callback early-return therefore leaves the timer permanently
aborted after newgame and no AI is ever created. For Emscripten only, arm that
timer for the first game tick when interval=0 and competitors were requested.
Non-zero intervals and native desktop builds keep upstream behaviour.
"""
from pathlib import Path

path = Path('openttd/src/company_cmd.cpp')
if not path.is_file():
    raise SystemExit(f'OpenTTD source file is missing: {path}')

text = path.read_text(encoding='utf-8')

# 1. Allow the existing zero-interval path in OnTick_Companies() to run.
early_return = '\tif (_settings_game.difficulty.competitors_interval == 0) return;\n'
early_replacement = (
    '\t/* Web port: zero means start requested AI competitors immediately.\n'
    '\t * OnTick_Companies rearms the browser scheduler until the requested\n'
    '\t * competitor count is reached, then backs off. */\n'
)
count = text.count(early_return)
if count != 1:
    raise SystemExit(
        'Expected exactly one OpenTTD zero-interval AI early-return, '
        f'found {count}; upstream source changed'
    )
text = text.replace(early_return, early_replacement, 1)

# 2. StartupCompanies() aborts the timer on every new game. For a web game with
#    interval=0 this would make the fast path unreachable forever, so arm it for
#    the first game tick instead. Desktop/native OpenTTD is untouched.
startup_old = '''void StartupCompanies()\n{\n\t/* Ensure the timeout is aborted, so it doesn't fire based on information of the last game. */\n\t_new_competitor_timeout.Abort();\n}\n'''
startup_new = '''void StartupCompanies()\n{\n#ifdef __EMSCRIPTEN__\n\t/* Browser zero-interval AI bootstrap: StartupCompanies normally aborts the\n\t * competitor timer. With interval 0 the web fast path needs one initial\n\t * firing after newgame; subsequent firings are rearmed by OnTick_Companies. */\n\tif (_settings_game.difficulty.competitors_interval == 0 &&\n\t\t\t_settings_game.difficulty.max_no_competitors > 0) {\n\t\t_new_competitor_timeout.Reset({ TimerGameTick::Priority::COMPETITOR_TIMEOUT, 1 });\n\t\treturn;\n\t}\n#endif\n\n\t/* Ensure the timeout is aborted, so it doesn't fire based on information of the last game. */\n\t_new_competitor_timeout.Abort();\n}\n'''
count = text.count(startup_old)
if count != 1:
    raise SystemExit(
        'Expected exactly one StartupCompanies timer-abort block, '
        f'found {count}; upstream source changed'
    )
text = text.replace(startup_old, startup_new, 1)

path.write_text(text, encoding='utf-8')

verify = path.read_text(encoding='utf-8')
checks = (
    'zero means start requested AI competitors immediately',
    'Browser zero-interval AI bootstrap',
    '_new_competitor_timeout.Reset({ TimerGameTick::Priority::COMPETITOR_TIMEOUT, 1 });',
    '_settings_game.difficulty.max_no_competitors > 0',
)
if early_return in verify:
    raise SystemExit('Zero-interval AI early-return is still present')
for marker in checks:
    if marker not in verify:
        raise SystemExit(f'Could not apply zero-interval AI startup marker: {marker}')

print('Patched OpenTTD: interval=0 rearms competitor startup after newgame in Emscripten.')
