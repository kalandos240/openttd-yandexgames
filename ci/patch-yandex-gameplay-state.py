#!/usr/bin/env python3
from pathlib import Path

path = Path('openttd/src/openttd.cpp')
text = path.read_text()

# The first integration hook marked every GM_NORMAL state as gameplay, even
# while OpenTTD was paused. Yandex GameplayAPI requires stop() during pause and
# start() again immediately when gameplay resumes, so move the notification to
# the central game loop and emit it only when the effective state changes.
switch_hook = '''
#ifdef __EMSCRIPTEN__
    EM_ASM({
        if (window.yandexGameSetGameplay) window.yandexGameSetGameplay(!!$0);
    }, _game_mode == GM_NORMAL ? 1 : 0);
#endif
'''
if switch_hook not in text:
    raise SystemExit('Could not find old SwitchToMode Yandex gameplay hook')
text = text.replace(switch_hook, '\n', 1)

marker = '''void GameLoop()
{
'''
replacement = '''void GameLoop()
{
#ifdef __EMSCRIPTEN__
    static bool yandex_gameplay_state = false;
    const bool yandex_gameplay_now = _game_mode == GM_NORMAL && _pause_mode.None() && !HasModalProgress();
    if (yandex_gameplay_now != yandex_gameplay_state) {
        yandex_gameplay_state = yandex_gameplay_now;
        EM_ASM({
            if (window.yandexGameSetGameplay) window.yandexGameSetGameplay(!!$0);
        }, yandex_gameplay_now ? 1 : 0);
    }
#endif
'''
if marker not in text:
    raise SystemExit('Could not find GameLoop() for Yandex gameplay state hook')
text = text.replace(marker, replacement, 1)

path.write_text(text)
print('Yandex GameplayAPI state now follows OpenTTD play/pause state.')
