#!/usr/bin/env python3
"""Apply narrow, reversible Playgama-specific fixes to verified Yandex V29 shell."""
from __future__ import annotations
import argparse
from pathlib import Path

OLD_FREQUENCY = '  const AD_MIN_GAMEPLAY_MS = 150 * 1000;\n  const AD_MIN_INTERVAL_MS = 150 * 1000;'
NEW_FREQUENCY = '  const AD_MIN_GAMEPLAY_MS = 180 * 1000;\n  const AD_MIN_INTERVAL_MS = 180 * 1000;'

OLD_AD = '''  function scheduleAdDueTimer() {
    clearAdDueTimer();
    if (!gameplayActive || adOpen || adCountdownActive || !pageVisible || yandexPauseEventActive) return;
    const now = Date.now();
    const gameplayRemaining = Math.max(0, AD_MIN_GAMEPLAY_MS - currentGameplayElapsed(now));
    const intervalRemaining = lastAdAt ? Math.max(0, AD_MIN_INTERVAL_MS - (now - lastAdAt)) : 0;
    const delay = Math.max(gameplayRemaining, intervalRemaining);
    adDueTimer = setTimeout(() => {
      adDueTimer = 0;
      maybeShowInterstitial('gameplay-timer');
    }, Math.max(25, delay));
  }
'''
NEW_AD = '''  // Playgama requires interstitials at natural breaks, not during live play.
  // V29 invokes this function on game start, tab focus and ad completion.
  // Retain the original call sites, but never schedule a timed interruption.
  // On return to menu yandexGameSetGameplay(false) still calls
  // maybeShowInterstitial('logical-pause') after the safe gameplay interval.
  function scheduleAdDueTimer() {
    clearAdDueTimer();
  }
'''
OLD_RANK = """      if (!sdk?.leaderboards || typeof sdk.leaderboards.getEntries !== 'function') {
        status = 'offline';"""
NEW_RANK = """      if (!sdk?.leaderboards || typeof sdk.leaderboards.getEntries !== 'function' ||
          !(await methodAvailable(sdk, 'leaderboards.getEntries'))) {
        status = 'offline';"""
OLD_COMMENT = '    <!-- Yandex Games SDK -->'
NEW_COMMENT = '    <!-- Playgama Bridge SDK -->'


def replace_exact(path: Path, before: str, after: str) -> None:
    content = path.read_text(encoding='utf-8')
    if content.count(after) == 1 and before not in content:
        return
    if content.count(before) != 1:
        raise SystemExit(f'Expected exactly one V29 patch anchor in {path.name}; found {content.count(before)}')
    path.write_text(content.replace(before, after, 1), encoding='utf-8')


def patch(root: Path) -> None:
    replace_exact(root/'yandex-bridge.js', OLD_AD, NEW_AD)
    replace_exact(root/'yandex-bridge.js', OLD_FREQUENCY, NEW_FREQUENCY)
    replace_exact(root/'openttd-global-ranking.js', OLD_RANK, NEW_RANK)
    replace_exact(root/'index.html', OLD_COMMENT, NEW_COMMENT)
    assert_patched(root)


def assert_patched(root: Path) -> None:
    ad = (root/'yandex-bridge.js').read_text(encoding='utf-8')
    rank = (root/'openttd-global-ranking.js').read_text(encoding='utf-8')
    html = (root/'index.html').read_text(encoding='utf-8')
    if OLD_FREQUENCY in ad or ad.count(NEW_FREQUENCY) != 1:
        raise SystemExit('Playgama 180-second ad interval patch is missing')
    if OLD_AD in ad or ad.count(NEW_AD) != 1:
        raise SystemExit('Playgama natural-break ads patch is missing or incomplete')
    if "maybeShowInterstitial('logical-pause');" not in ad:
        raise SystemExit('Natural pause advertising has been lost')
    if "maybeShowInterstitial('gameplay-timer');" in ad:
        raise SystemExit('Unexpected timed gameplay advertisement remains')
    if OLD_RANK in rank or rank.count(NEW_RANK) != 1:
        raise SystemExit('Unsupported leaderboard fallback patch is missing')
    if html.count(NEW_COMMENT) != 1 or OLD_COMMENT in html:
        raise SystemExit('Playgama HTML header marker is missing')


def verify_exact_delta(pristine: Path, patched: Path) -> None:
    """Prove packaging touched only three declared text regions."""
    for name, before, after in (
        ('yandex-bridge.js', OLD_AD, NEW_AD),
        ('yandex-bridge.js', OLD_FREQUENCY, NEW_FREQUENCY),
        ('openttd-global-ranking.js', OLD_RANK, NEW_RANK),
    ):
        original = (pristine/name).read_text(encoding='utf-8')
        expected = original.replace(OLD_AD, NEW_AD, 1).replace(
            OLD_FREQUENCY, NEW_FREQUENCY, 1) if name == 'yandex-bridge.js' else original.replace(before, after, 1)
        actual = (patched/name).read_text(encoding='utf-8')
        if expected != actual:
            raise SystemExit(f'Unexpected Playgama customization outside approved patch: {name}')
    # HTML also contains the independently verified SDK bootstrap replacement.
    from package_from_yandex_v29 import patch_index
    original_html = (pristine/'index.html').read_text(encoding='utf-8')
    expected_html = patch_index(original_html).replace(OLD_COMMENT, NEW_COMMENT, 1)
    if (patched/'index.html').read_text(encoding='utf-8') != expected_html:
        raise SystemExit('Unexpected V29 HTML change beyond SDK/bootstrap/comment replacements')
    assert_patched(patched)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('dist', type=Path)
    parser.add_argument('--verify-original', type=Path)
    args = parser.parse_args()
    patch(args.dist)
    if args.verify_original:
        verify_exact_delta(args.verify_original, args.dist)
    print('Playgama V29 safe advertising / unavailable leaderboard changes verified')


if __name__ == '__main__':
    main()
