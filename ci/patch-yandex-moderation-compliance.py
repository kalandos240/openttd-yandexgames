#!/usr/bin/env python3
"""Apply Yandex Games moderation/compliance hardening to the vanilla package.

This patch is intentionally Yandex-only. It does not touch OpenTTD AI content.
It adds:
- a 2 minute fullscreen-ad eligibility cadence;
- a 2 second OpenTTD-styled, input-blocking ad warning while the game/audio are paused;
- timer-based ad breaks for long real-time sessions plus logical-pause opportunities;
- a 2:1 maximum active-field aspect ratio without stretching the SDL canvas;
- a small browser-hotkey guard so OpenTTD does not consume browser-reserved shortcuts.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

BRIDGE_MARKER = "const AD_WARNING_MS = 2 * 1000;"

VIEWPORT_JS = r'''/* Keep the OpenTTD SDL surface aligned with the Yandex Games viewport
 * while respecting the platform's maximum 2:1 active-field aspect ratio.
 * The backing canvas and its CSS size are changed together, so the game is
 * never stretched. On ultra-wide/tall viewports the remaining area shows the
 * existing OpenTTD background and the active field stays centred.
 */
(() => {
  'use strict';
  if (window.__openttdModerationViewportInstalled) return;
  window.__openttdModerationViewportInstalled = true;

  const MAX_ASPECT_RATIO = 2;

  const viewportSize = () => ({
    width: Math.max(64, Math.round(window.visualViewport?.width || window.innerWidth || document.documentElement.clientWidth || 1280)),
    height: Math.max(64, Math.round(window.visualViewport?.height || window.innerHeight || document.documentElement.clientHeight || 720)),
  });

  const gameSize = () => {
    const viewport = viewportSize();
    let width = viewport.width;
    let height = viewport.height;
    if (width / height > MAX_ASPECT_RATIO) width = Math.round(height * MAX_ASPECT_RATIO);
    if (height / width > MAX_ASPECT_RATIO) height = Math.round(width * MAX_ASPECT_RATIO);
    return { viewport, width: Math.max(64, width), height: Math.max(64, height) };
  };

  let raf = 0;
  let lastWidth = 0;
  let lastHeight = 0;
  let lastViewportWidth = 0;
  let lastViewportHeight = 0;

  const apply = () => {
    raf = 0;
    try {
      if (typeof Module === 'undefined' || Module.calledRun !== true || typeof Module.setCanvasSize !== 'function') return false;
      const canvas = Module.canvas || document.getElementById('canvas');
      if (!canvas) return false;
      const { viewport, width, height } = gameSize();
      if (width !== lastWidth || height !== lastHeight || canvas.width !== width || canvas.height !== height) {
        Module.setCanvasSize(width, height);
        lastWidth = width;
        lastHeight = height;
      }
      if (viewport.width !== lastViewportWidth || viewport.height !== lastViewportHeight || canvas.style.width !== `${width}px` || canvas.style.height !== `${height}px`) {
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        canvas.style.left = `${Math.round((viewport.width - width) / 2)}px`;
        canvas.style.top = `${Math.round((viewport.height - height) / 2)}px`;
        canvas.style.right = 'auto';
        canvas.style.bottom = 'auto';
        lastViewportWidth = viewport.width;
        lastViewportHeight = viewport.height;
      }
      return true;
    } catch (error) {
      console.warn('[OpenTTD] Moderation-safe viewport resize failed', error);
      return false;
    }
  };

  const schedule = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      if (!apply()) setTimeout(apply, 50);
    });
  };

  window.addEventListener('resize', schedule, { passive: true });
  window.visualViewport?.addEventListener('resize', schedule, { passive: true });
  document.addEventListener('fullscreenchange', schedule, { passive: true });

  let attempts = 0;
  const startup = setInterval(() => {
    attempts += 1;
    if (apply() || attempts >= 120) clearInterval(startup);
  }, 100);
})();
'''

HOTKEY_JS = r'''/* Do not let OpenTTD consume shortcuts reserved by the browser/OS.
 * We intentionally do not call preventDefault(): the browser keeps its normal
 * behaviour, while stopImmediatePropagation() prevents the game runtime from
 * treating the same keystroke as an OpenTTD command.
 */
(() => {
  'use strict';
  if (window.__openttdYandexReservedKeysInstalled) return;
  window.__openttdYandexReservedKeysInstalled = true;

  const isReserved = event => {
    const key = String(event.key || '');
    const lower = key.toLowerCase();
    if (key === 'F1' || key === 'F5') return true;
    const primary = event.ctrlKey || event.metaKey;
    if (!primary || event.altKey) return false;
    return lower === 's' || lower === 'w' || lower === 'q';
  };

  const guard = event => {
    if (!isReserved(event)) return;
    event.stopImmediatePropagation();
  };

  window.addEventListener('keydown', guard, true);
  window.addEventListener('keypress', guard, true);
  window.addEventListener('keyup', guard, true);
})();
'''

AD_HELPERS = r'''
  function currentGameplayElapsed(now = Date.now()) {
    let total = gameplayAccumulatedMs;
    if (gameplayActive && gameplayStartedAt) total += Math.max(0, now - gameplayStartedAt);
    return total;
  }

  function adLanguageIsRussian() {
    return String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase().startsWith('ru');
  }

  function ensureAdWarningOverlay() {
    let overlay = document.getElementById('openttd-yandex-ad-warning');
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = 'openttd-yandex-ad-warning';
    overlay.setAttribute('role', 'status');
    overlay.setAttribute('aria-live', 'assertive');
    Object.assign(overlay.style, {
      position: 'fixed', inset: '0', zIndex: '2147483646', display: 'none',
      alignItems: 'center', justifyContent: 'center', background: 'rgba(16,16,16,0.56)',
      pointerEvents: 'auto', cursor: 'default', fontFamily: 'Tahoma, Arial, Helvetica, sans-serif',
    });

    const panel = document.createElement('div');
    panel.id = 'openttd-yandex-ad-warning-panel';
    Object.assign(panel.style, {
      minWidth: '300px', maxWidth: 'min(560px, calc(100vw - 32px))',
      background: '#838383', border: '2px solid #a8a8a8', outline: '2px solid #404040',
      boxShadow: '0 0 0 1px #202020, 6px 6px 0 rgba(0,0,0,0.35)', color: '#101010',
      imageRendering: 'pixelated', userSelect: 'none',
    });

    const title = document.createElement('div');
    title.id = 'openttd-yandex-ad-warning-title';
    Object.assign(title.style, {
      background: '#305080', color: '#fcfcfc', minHeight: '22px', lineHeight: '22px',
      padding: '0 8px', fontWeight: '700', textShadow: '1px 1px #101010', borderBottom: '1px solid #a8a8a8',
    });

    const message = document.createElement('div');
    message.id = 'openttd-yandex-ad-warning-message';
    Object.assign(message.style, {
      padding: '18px 22px', textAlign: 'center', fontSize: '18px', lineHeight: '1.45',
      background: '#c0c0c0', borderTop: '1px solid #fcfcfc',
    });

    panel.append(title, message);
    overlay.append(panel);
    document.body.append(overlay);
    return overlay;
  }

  function updateAdWarning(seconds) {
    const overlay = ensureAdWarningOverlay();
    const title = overlay.querySelector('#openttd-yandex-ad-warning-title');
    const message = overlay.querySelector('#openttd-yandex-ad-warning-message');
    const ru = adLanguageIsRussian();
    if (title) title.textContent = ru ? 'Рекламная пауза' : 'Advertising break';
    if (message) {
      const main = ru
        ? `Реклама через ${seconds} ${seconds === 1 ? 'секунду' : 'секунды'}`
        : `Advertisement in ${seconds} second${seconds === 1 ? '' : 's'}`;
      const pause = ru ? 'Игра поставлена на паузу' : 'Game paused';
      message.innerHTML = `<strong>${main}</strong><br><span style="font-size:14px">${pause}</span>`;
    }
    overlay.style.display = 'flex';
  }

  function hideAdWarning() {
    const overlay = document.getElementById('openttd-yandex-ad-warning');
    if (overlay) overlay.style.display = 'none';
  }

  function clearAdDueTimer() {
    if (adDueTimer) clearTimeout(adDueTimer);
    adDueTimer = 0;
  }

  function scheduleAdDueTimer() {
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

NEW_AD_FUNCTION = r'''  async function maybeShowInterstitial(reason = 'logical-pause') {
    const now = Date.now();
    if (adOpen || adCountdownActive || !pageVisible || yandexPauseEventActive) return;
    if (currentGameplayElapsed(now) < AD_MIN_GAMEPLAY_MS) {
      scheduleAdDueTimer();
      return;
    }
    if (lastAdAt && now - lastAdAt < AD_MIN_INTERVAL_MS) {
      scheduleAdDueTimer();
      return;
    }

    const ysdk = await sdkReady;
    if (!ysdk || !ysdk.adv || typeof ysdk.adv.showFullscreenAdv !== 'function') {
      scheduleAdDueTimer();
      return;
    }
    if (adOpen || adCountdownActive || !pageVisible || yandexPauseEventActive) return;

    /* A timed interruption in a long real-time session must be announced while
       gameplay is already paused. Freeze the active-time accumulator before
       displaying the two-second warning. */
    const freezeAt = Date.now();
    if (gameplayActive && gameplayStartedAt) {
      gameplayAccumulatedMs += Math.max(0, freezeAt - gameplayStartedAt);
      gameplayStartedAt = 0;
    }
    adCountdownActive = true;
    clearAdDueTimer();
    updatePlatformPause();
    await setPlatformGameplay(false);
    suspendAudio();
    updateAdWarning(2);

    await new Promise(resolve => {
      adCountdownTimer = setTimeout(() => {
        updateAdWarning(1);
        adCountdownTimer = setTimeout(resolve, AD_WARNING_MS - AD_TICK_MS);
      }, AD_TICK_MS);
    });
    adCountdownTimer = 0;

    if (!pageVisible || yandexPauseEventActive) {
      adCountdownActive = false;
      hideAdWarning();
      updatePlatformPause();
      if (gameplayActive && !gameplayStartedAt) gameplayStartedAt = Date.now();
      resumeAudio();
      setPlatformGameplay(gameplayActive);
      scheduleAdDueTimer();
      return;
    }

    adCountdownActive = false;
    adOpen = true;
    gameplayAccumulatedMs = 0;
    lastAdAt = Date.now();
    hideAdWarning();
    updatePlatformPause();

    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      adOpen = false;
      updatePlatformPause();
      if (gameplayActive && !gameplayStartedAt) gameplayStartedAt = Date.now();
      resumeAudio();
      setPlatformGameplay(gameplayActive);
      scheduleAdDueTimer();
    };

    try {
      console.info('[Yandex/OpenTTD] Requesting fullscreen ad', reason);
      ysdk.adv.showFullscreenAdv({
        callbacks: {
          onOpen: () => {},
          onClose: () => finish(),
          onError: error => {
            console.warn('Yandex fullscreen ad failed', error);
            finish();
          },
        },
      });
    } catch (e) {
      console.warn('Yandex fullscreen ad exception', e);
      finish();
    }
  }
'''


def patch_bridge(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    if BRIDGE_MARKER in text:
        return
    text, n1 = re.subn(r"  const AD_MIN_GAMEPLAY_MS = 5 \* 60 \* 1000;\n  const AD_MIN_INTERVAL_MS = 5 \* 60 \* 1000;",
                       "  const AD_MIN_GAMEPLAY_MS = 2 * 60 * 1000;\n  const AD_MIN_INTERVAL_MS = 2 * 60 * 1000;\n  const AD_WARNING_MS = 2 * 1000;\n  const AD_TICK_MS = 1000;", text, count=1)
    if n1 != 1:
        raise SystemExit('Could not patch Yandex ad cadence constants')

    state_anchor = "  let adOpen = false;\n"
    state_add = "  let adOpen = false;\n  let adCountdownActive = false;\n  let adCountdownTimer = 0;\n  let adDueTimer = 0;\n"
    if text.count(state_anchor) != 1:
        raise SystemExit('Could not find Yandex ad state anchor')
    text = text.replace(state_anchor, state_add, 1)

    text = text.replace("    return adOpen || !pageVisible || yandexPauseEventActive;",
                        "    return adOpen || adCountdownActive || !pageVisible || yandexPauseEventActive;", 1)

    helper_anchor = "  async function setPlatformGameplay(active) {"
    if text.count(helper_anchor) != 1:
        raise SystemExit('Could not find GameplayAPI helper anchor')
    text = text.replace(helper_anchor, AD_HELPERS + "\n" + helper_anchor, 1)

    ad_pattern = re.compile(r"  async function maybeShowInterstitial\(\) \{.*?\n  \}\n\n  window\.yandexGameSetGameplay", re.S)
    text, n2 = ad_pattern.subn(NEW_AD_FUNCTION + "\n  window.yandexGameSetGameplay", text, count=1)
    if n2 != 1:
        raise SystemExit('Could not replace Yandex fullscreen ad function')

    old_active = """    if (active) {\n      gameplayStartedAt = now;\n      setPlatformGameplay(true);\n    } else {\n      setPlatformGameplay(false);\n      maybeShowInterstitial();\n    }\n"""
    new_active = """    if (active) {\n      gameplayStartedAt = now;\n      setPlatformGameplay(true);\n      scheduleAdDueTimer();\n    } else {\n      clearAdDueTimer();\n      setPlatformGameplay(false);\n      maybeShowInterstitial('logical-pause');\n    }\n"""
    if text.count(old_active) != 1:
        raise SystemExit('Could not patch gameplay ad scheduling')
    text = text.replace(old_active, new_active, 1)

    text = text.replace("  function platformPauseEvent() {\n    yandexPauseEventActive = true;",
                        "  function platformPauseEvent() {\n    yandexPauseEventActive = true;\n    clearAdDueTimer();", 1)
    text = text.replace("    setPlatformGameplay(gameplayActive);\n  }\n\n  sdkReady.then", 
                        "    setPlatformGameplay(gameplayActive);\n    scheduleAdDueTimer();\n  }\n\n  sdkReady.then", 1)
    text = text.replace("    if (!pageVisible) {\n", "    if (!pageVisible) {\n      clearAdDueTimer();\n", 1)
    text = text.replace("    } else {\n      resumeAudio();\n      setPlatformGameplay(gameplayActive);\n    }\n  });\n\n  window.addEventListener('blur'",
                        "    } else {\n      resumeAudio();\n      setPlatformGameplay(gameplayActive);\n      scheduleAdDueTimer();\n    }\n  });\n\n  window.addEventListener('blur'", 1)
    text = text.replace("  window.addEventListener('blur', () => {\n    pageVisible = false;",
                        "  window.addEventListener('blur', () => {\n    pageVisible = false;\n    clearAdDueTimer();", 1)
    text = text.replace("    if (pageVisible) setPlatformGameplay(gameplayActive);\n  });",
                        "    if (pageVisible) {\n      setPlatformGameplay(gameplayActive);\n      scheduleAdDueTimer();\n    }\n  });", 1)

    required = [
        BRIDGE_MARKER,
        "maybeShowInterstitial('gameplay-timer')",
        "maybeShowInterstitial('logical-pause')",
        "updateAdWarning(2)",
        "updateAdWarning(1)",
        "adCountdownActive",
        "scheduleAdDueTimer()",
        "GameplayAPI",
        "game_api_pause",
        "game_api_resume",
    ]
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f'Yandex bridge compliance markers missing: {missing}')
    path.write_text(text, encoding='utf-8')


def patch_index(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    tag = '<script src="openttd-yandex-web-keys.js"></script>'
    if tag not in text:
        anchor = '<script src="openttd-full-viewport.js"></script>'
        if text.count(anchor) != 1:
            raise SystemExit('Could not find viewport script tag in index.html')
        text = text.replace(anchor, anchor + tag, 1)
    path.write_text(text, encoding='utf-8')


def validate_names(root: Path) -> None:
    for path in root.rglob('*'):
        rel = path.relative_to(root).as_posix()
        if any(ord(ch) > 127 for ch in rel):
            raise SystemExit(f'Non-ASCII package path: {rel}')
        if ' ' in rel:
            raise SystemExit(f'Whitespace in package path: {rel}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    for required in ('index.html', 'yandex-bridge.js', 'openttd-full-viewport.js', 'openttd-runtime.js', 'openttd-classic-ai.js'):
        if not (dist / required).is_file():
            raise SystemExit(f'Missing Yandex package file: {required}')

    patch_bridge(dist / 'yandex-bridge.js')
    (dist / 'openttd-full-viewport.js').write_text(VIEWPORT_JS, encoding='utf-8')
    (dist / 'openttd-yandex-web-keys.js').write_text(HOTKEY_JS, encoding='utf-8')
    patch_index(dist / 'index.html')
    validate_names(dist)

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex unpacked package is too large: {unpacked} bytes')

    print(f'Yandex moderation compliance patch applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
