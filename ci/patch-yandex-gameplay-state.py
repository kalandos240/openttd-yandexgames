#!/usr/bin/env python3
from pathlib import Path

path = Path('openttd/src/openttd.cpp')
text = path.read_text()

# Older revisions of the Yandex patch emitted a coarse gameplay notification
# from SwitchToMode. Remove it when present, but do not require it: the current
# offline patch intentionally no longer inserts that intermediate hook.
switch_hook = '''
#ifdef __EMSCRIPTEN__
    EM_ASM({
        if (window.yandexGameSetGameplay) window.yandexGameSetGameplay(!!$0);
    }, _game_mode == GM_NORMAL ? 1 : 0);
#endif
'''
if switch_hook in text:
    text = text.replace(switch_hook, '\n', 1)

# Emit GameplayAPI state changes from the central game loop so Yandex sees
# gameplay only while the simulation is genuinely active (not paused and not
# blocked by modal progress windows).
if 'static bool yandex_gameplay_state = false;' not in text:
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
