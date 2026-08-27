#!/usr/bin/env python3
"""Apply browser-safe startup/audio policy to an assembled package.

This runs after upgrade_playgama_v10.py and before the shared Playgama package
is cloned into the Yandex edition. Keeping it on the shared package guarantees
identical native startup behaviour on both platforms.
"""
from pathlib import Path
import argparse


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Could not find unique {label}: {count}")
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    args = ap.parse_args()

    path = args.dist.resolve() / "openttd-playgama-fixes.js"
    if not path.is_file():
        raise SystemExit(f"Browser runtime fixes are missing: {path}")
    text = path.read_text(encoding="utf-8")

    # OpenTTD honours a persisted gui.pause_on_newgame setting. Browser/cloud
    # profiles can therefore start every new game with the native red PAUSED
    # indicator even though the platform never requested a pause. Web editions
    # always start playable; platform visibility/ad pause remains independent.
    write_anchor = """    try { FS.writeFile(path, config); } catch (error) {
      console.warn('[Playgama/OpenTTD] Could not apply platform language/AI config', error);
    }
"""
    pause_block = """    /* Browser editions must never inherit a stale pause-on-new-game flag. */
    if (/^pause_on_newgame\\s*=.*$/m.test(config)) {
      config = config.replace(/^pause_on_newgame\\s*=.*$/m, 'pause_on_newgame = false');
    } else if (/^\\[gui\\]\\s*$/m.test(config)) {
      config = config.replace(/^\\[gui\\]\\s*$/m, '[gui]\\npause_on_newgame = false');
    } else {
      config += (config && !config.endsWith('\\n') ? '\\n' : '') + '[gui]\\npause_on_newgame = false\\n';
    }

"""
    if "pause_on_newgame = false" not in text:
        if text.count(write_anchor) != 1:
            raise SystemExit(f"Could not find platform config write anchor: {text.count(write_anchor)}")
        text = text.replace(write_anchor, pause_block + write_anchor, 1)

    # The periodic music recovery loop used to call HTMLMediaElement.play()
    # every 1.5 s before the first gesture. Firefox correctly reports that as
    # an autoplay-policy violation. Gesture handlers still call this function,
    # so gating it on user activation preserves recovery without console spam.
    retry_old = """  const retryMusic = () => {
    if (shouldHardPause() || !platformAudioEnabled || document.hidden) return;
"""
    retry_new = """  const retryMusic = () => {
    if (shouldHardPause() || !platformAudioEnabled || document.hidden) return;
    if (!(navigator.userActivation?.hasBeenActive ?? true)) return;
"""
    text = replace_once(text, retry_old, retry_new, "pre-activation music retry")

    required = (
        "pause_on_newgame = false",
        "if (!(navigator.userActivation?.hasBeenActive ?? true)) return;",
        "Module.calledRun === true",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"Browser runtime policy marker missing: {marker}")

    path.write_text(text, encoding="utf-8")
    print("Browser runtime policy applied: no stale startup pause; no pre-activation music retry.")


if __name__ == "__main__":
    main()
