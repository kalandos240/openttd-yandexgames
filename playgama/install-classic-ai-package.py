#!/usr/bin/env python3
"""Install bundled SimpleAI while preserving player AI settings and platform lifecycle state."""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

AI_TAG = '<script src="openttd-classic-ai.js"></script>'
FIXES_TAG = '<script src="openttd-playgama-fixes.js"></script>'


def patch_fixes(path: Path) -> None:
    text = path.read_text(encoding='utf-8')

    # Historical browser packages forced three competitors and interval zero at
    # every startup. That overrides the New Game AI window and can also create a
    # large CPU spike by starting several AIs at once. Keep only language setup.
    text, n_comp = re.subn(r'\n  const COMPETITORS = \d+;\n', '\n', text, count=1)
    text, n_int = re.subn(r'\n  const COMPETITOR_INTERVAL = \d+;\n', '\n', text, count=1)
    if n_comp not in (0, 1) or n_int not in (0, 1):
        raise SystemExit('Unexpected competitor constant count in runtime fixes')

    max_pattern = re.compile(
        r"\n    if \(/\^max_no_competitors\\s\*=\.\*\$/m\.test\(config\)\) \{.*?\n    \}\n",
        re.S,
    )
    interval_pattern = re.compile(
        r"\n\n    if \(/\^competitors_interval\\s\*=\.\*\$/m\.test\(config\)\) \{.*?\n    \}\n",
        re.S,
    )
    text, max_count = max_pattern.subn('\n', text, count=1)
    text, interval_count = interval_pattern.subn('\n', text, count=1)
    if max_count != 1:
        raise SystemExit(f'Could not remove forced max_no_competitors block ({max_count})')
    if interval_count not in (0, 1):
        raise SystemExit(f'Unexpected competitors_interval block count ({interval_count})')

    text = text.replace('platform language/AI config', 'platform language config')
    text = text.replace('platform settings. */', 'platform language settings. */')

    if 'max_no_competitors =' in text or 'competitors_interval =' in text:
        raise SystemExit('Runtime fixes still force player AI settings')
    path.write_text(text, encoding='utf-8')


def patch_bridge(path: Path) -> None:
    text = path.read_text(encoding='utf-8')

    # Cloud backup/restore must preserve exactly what the player selected.
    sanitize_pattern = re.compile(
        r"  function sanitizeOfflineConfig\(config\) \{.*?\n  \}\n\n",
        re.S,
    )
    if sanitize_pattern.search(text):
        text = sanitize_pattern.sub(
            "  function sanitizeOfflineConfig(config) {\n    return String(config || '');\n  }\n\n",
            text,
            count=1,
        )

    force_pattern = re.compile(
        r"  function forceBrowserAIConfig\(config\) \{.*?\n  \}\n\n",
        re.S,
    )
    if force_pattern.search(text):
        text = force_pattern.sub(
            "  function forceBrowserAIConfig(config) {\n    return String(config || '');\n  }\n\n",
            text,
            count=1,
        )

    text = text.replace(
        "return sanitizeOfflineConfig(FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' }));",
        "return FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' });",
    )
    text = text.replace("return sanitizeOfflineConfig('');", "return '';")
    text = text.replace(
        'FS.writeFile(configPath, forceBrowserAIConfig(cloudConfig.config));',
        'FS.writeFile(configPath, cloudConfig.config);',
    )
    text = text.replace(
        'FS.writeFile(configPath, sanitizeOfflineConfig(cloudConfig.config));',
        'FS.writeFile(configPath, cloudConfig.config);',
    )

    # Avoid stale async start/stop completions when visibility changes quickly.
    decl = '  let platformGameplayStarted = false;\n'
    if 'let gameplayStateRequest = 0;' not in text:
        if decl not in text:
            raise SystemExit('Could not find GameplayAPI state declaration')
        text = text.replace(decl, decl + '  let gameplayStateRequest = 0;\n', 1)

    old_set = '''  async function setPlatformGameplay(active) {
    const ysdk = await sdkReady;
    const api = ysdk && ysdk.features && ysdk.features.GameplayAPI;
    if (!api) return;
    const shouldStart = !!active && !shouldPlatformPause();
    if (shouldStart === platformGameplayStarted) return;

    try {
      if (shouldStart && typeof api.start === 'function') {
        api.start();
        platformGameplayStarted = true;
      } else if (!shouldStart && typeof api.stop === 'function') {
        api.stop();
        platformGameplayStarted = false;
      }
    } catch (e) {
      console.warn('Yandex GameplayAPI state change failed', e);
    }
  }
'''
    new_set = '''  async function setPlatformGameplay(active) {
    const request = ++gameplayStateRequest;
    const ysdk = await sdkReady;
    if (request !== gameplayStateRequest) return;
    const api = ysdk && ysdk.features && ysdk.features.GameplayAPI;
    if (!api) return;
    const shouldStart = !!active && !shouldPlatformPause();
    if (shouldStart === platformGameplayStarted) return;

    try {
      if (shouldStart && typeof api.start === 'function') {
        api.start();
        platformGameplayStarted = true;
      } else if (!shouldStart && typeof api.stop === 'function') {
        api.stop();
        platformGameplayStarted = false;
      }
    } catch (e) {
      console.warn('Yandex GameplayAPI state change failed', e);
    }
  }
'''
    if old_set in text:
        text = text.replace(old_set, new_set, 1)
    elif 'const request = ++gameplayStateRequest;' not in text:
        raise SystemExit('Could not patch GameplayAPI async state serialization')

    old_events = '''function platformPauseEvent() {
    yandexPauseEventActive = true;
    updatePlatformPause();
    suspendAudio();
    /* The Yandex platform itself temporarily applies GameplayAPI.stop() for
       game_api_pause and restores the previous markup state on resume. Do not
       send a duplicate stop/start pair here. */
  }

  function platformResumeEvent() {
    yandexPauseEventActive = false;
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    /* GameplayAPI state is restored by the platform for this event pair. */
  }
'''
    new_events = '''function platformPauseEvent() {
    yandexPauseEventActive = true;
    /* The platform has already stopped GameplayAPI for this event. Reflect
       that external state locally so resume is allowed to call start(). */
    platformGameplayStarted = false;
    ++gameplayStateRequest;
    updatePlatformPause();
    suspendAudio();
  }

  function platformResumeEvent() {
    yandexPauseEventActive = false;
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    setPlatformGameplay(gameplayActive);
  }
'''
    if old_events in text:
        text = text.replace(old_events, new_events, 1)
    elif 'platformGameplayStarted = false;\n    ++gameplayStateRequest;' not in text:
        raise SystemExit('Could not patch GameplayAPI pause/resume handlers')

    old_visibility = '''  document.addEventListener('visibilitychange', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    if (!pageVisible) {
      if (!yandexPauseEventsBound) setPlatformGameplay(false);
      suspendAudio();
    } else {
      resumeAudio();
      if (!yandexPauseEventsBound) setPlatformGameplay(gameplayActive);
    }
  });

  window.addEventListener('blur', () => {
    pageVisible = false;
    updatePlatformPause();
    if (!yandexPauseEventsBound) setPlatformGameplay(false);
    suspendAudio();
  });

  window.addEventListener('focus', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    if (!yandexPauseEventsBound) setPlatformGameplay(gameplayActive);
  });
'''
    new_visibility = '''  document.addEventListener('visibilitychange', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    if (!pageVisible) {
      if (yandexPauseEventsBound) {
        platformGameplayStarted = false;
        ++gameplayStateRequest;
      } else {
        setPlatformGameplay(false);
      }
      suspendAudio();
    } else {
      resumeAudio();
      setPlatformGameplay(gameplayActive);
    }
  });

  window.addEventListener('blur', () => {
    pageVisible = false;
    updatePlatformPause();
    if (yandexPauseEventsBound) {
      platformGameplayStarted = false;
      ++gameplayStateRequest;
    } else {
      setPlatformGameplay(false);
    }
    suspendAudio();
  });

  window.addEventListener('focus', () => {
    pageVisible = !document.hidden;
    updatePlatformPause();
    resumeAudio();
    if (pageVisible) setPlatformGameplay(gameplayActive);
  });
'''
    if old_visibility in text:
        text = text.replace(old_visibility, new_visibility, 1)
    elif "if (pageVisible) setPlatformGameplay(gameplayActive);" not in text:
        raise SystemExit('Could not patch GameplayAPI visibility/focus recovery')

    for forbidden in (
        "'max_no_competitors = 3'",
        "'competitors_interval = 0'",
        'forceBrowserAIConfig(cloudConfig.config)',
        'sanitizeOfflineConfig(cloudConfig.config)',
    ):
        if forbidden in text:
            raise SystemExit(f'Bridge still contains forced AI setting: {forbidden}')

    path.write_text(text, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    ap.add_argument('--bundle', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    index = dist / 'index.html'
    fixes = dist / 'openttd-playgama-fixes.js'
    bridge = dist / 'yandex-bridge.js'
    if not index.is_file() or not fixes.is_file() or not bridge.is_file():
        raise SystemExit('Production package is missing index.html, runtime fixes, or platform bridge')

    shutil.copy2(args.bundle, dist / 'openttd-classic-ai.js')
    shutil.copy2(args.manifest, dist / 'OPENTTD-CLASSIC-AI-MANIFEST.json')

    html = index.read_text(encoding='utf-8')
    if AI_TAG not in html:
        if FIXES_TAG not in html:
            raise SystemExit('Could not find runtime-fixes script tag for AI insertion')
        html = html.replace(FIXES_TAG, AI_TAG + FIXES_TAG, 1)
    if html.count(AI_TAG) != 1:
        raise SystemExit('SimpleAI script tag is not unique')
    index.write_text(html, encoding='utf-8')

    patch_fixes(fixes)
    patch_bridge(bridge)
    print('SimpleAI recovery bundle installed; AI count/interval remain player-controlled and GameplayAPI resumes after tab return.')


if __name__ == '__main__':
    main()
