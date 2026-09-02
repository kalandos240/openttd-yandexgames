#!/usr/bin/env python3
"""Final Yandex publication hardening on top of the moderation package.

Keeps SimpleAI intact. This pass:
- changes ad request cadence to 150 seconds of active gameplay;
- makes the 2:1 viewport override win over legacy !important CSS;
- localizes the browser shell/error UI for RU/EN;
- blocks browser context menus/selection inside the game surface;
- leaves local saves intact and does not add external services.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import re

SHELL_I18N_JS = r'''(() => {
  'use strict';
  if (window.__openttdYandexShellI18nInstalled) return;
  window.__openttdYandexShellI18nInstalled = true;

  const isRu = () => String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase().startsWith('ru');
  const title = () => document.getElementById('title');
  const message = () => document.getElementById('message');

  const translateTitle = value => {
    if (!isRu()) return value;
    if (value === 'Loading ...') return 'Загрузка ...';
    if (value === 'Missing base graphics') return 'Отсутствует базовая графика';
    if (value === 'Thank you for playing!') return 'Спасибо за игру!';
    if (value === 'Crash :(') return 'Сбой :(';
    return value.replace(/^\((\d+) \/ (\d+)\) Loading \.\.\.$/, '($1 / $2) Загрузка ...');
  };

  const translateMessage = value => {
    if (!isRu()) return value;
    if (value === 'Preparing game ...') return 'Подготовка игры ...';
    if (value.startsWith('OpenTTD is downloading base graphics.')) {
      return value.replace('OpenTTD is downloading base graphics.', 'OpenTTD загружает базовую графику.');
    }
    if (value.startsWith('Failed to download base graphics.')) {
      return 'Не удалось загрузить базовую графику.<br/>Без неё игра не может запуститься.<br/><br/>Проверьте подключение и перезагрузите страницу.';
    }
    if (value.startsWith('Downloading base graphics done.')) {
      return 'Базовая графика загружена.<br/><br/>Страница будет перезагружена для запуска игры.';
    }
    if (value.startsWith('We hope you enjoyed OpenTTD!')) {
      return 'Спасибо, что играли в OpenTTD!<br/><br/>Перезагрузите страницу, чтобы запустить игру снова.';
    }
    if (value.startsWith('The game crashed!')) {
      return 'Игра аварийно завершилась.<br/><br/>Перезагрузите страницу, чтобы запустить её снова.';
    }
    return value;
  };

  let applying = false;
  const apply = () => {
    if (applying) return;
    applying = true;
    try {
      document.documentElement.lang = isRu() ? 'ru' : 'en';
      const t = title();
      const m = message();
      if (t) {
        const next = translateTitle(t.textContent || '');
        if (next !== t.textContent) t.textContent = next;
      }
      if (m) {
        const next = translateMessage(m.innerHTML || '');
        if (next !== m.innerHTML) m.innerHTML = next;
      }
    } finally {
      applying = false;
    }
  };

  const observer = new MutationObserver(apply);
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  window.addEventListener('openttd-yandex-language-ready', apply);
  setInterval(apply, 500);
  apply();
})();
'''

WEB_GUARD_JS = r'''(() => {
  'use strict';
  if (window.__openttdYandexWebGuardInstalled) return;
  window.__openttdYandexWebGuardInstalled = true;

  const isReserved = event => {
    const key = String(event.key || '');
    const lower = key.toLowerCase();
    if (key === 'F1' || key === 'F5') return true;
    const primary = event.ctrlKey || event.metaKey;
    if (!primary || event.altKey) return false;
    return lower === 's' || lower === 'w' || lower === 'q';
  };

  const keyGuard = event => {
    if (!isReserved(event)) return;
    event.stopImmediatePropagation();
  };

  window.addEventListener('keydown', keyGuard, true);
  window.addEventListener('keypress', keyGuard, true);
  window.addEventListener('keyup', keyGuard, true);

  const blockBrowserUi = event => event.preventDefault();
  document.addEventListener('contextmenu', blockBrowserUi, true);
  document.addEventListener('selectstart', blockBrowserUi, true);
  document.addEventListener('dragstart', blockBrowserUi, true);
})();
'''


def patch_ads(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    old_a = '  const AD_MIN_GAMEPLAY_MS = 2 * 60 * 1000;'
    old_b = '  const AD_MIN_INTERVAL_MS = 2 * 60 * 1000;'
    new_a = '  const AD_MIN_GAMEPLAY_MS = 150 * 1000;'
    new_b = '  const AD_MIN_INTERVAL_MS = 150 * 1000;'
    if text.count(old_a) != 1 or text.count(old_b) != 1:
        raise SystemExit('Expected installed two-minute moderation cadence before final adjustment')
    text = text.replace(old_a, new_a, 1).replace(old_b, new_b, 1)
    if 'const AD_WARNING_MS = 2 * 1000;' not in text or 'showFullscreenAdv' not in text:
        raise SystemExit('Fullscreen warning/ad integration missing')
    path.write_text(text, encoding='utf-8')


def patch_legacy_scale(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    pattern = re.compile(r'''    canvas\.emscripten \{\n      position: fixed !important;\n      inset: 0 !important;\n      left: 0 !important;\n      top: 0 !important;\n      transform: none !important;\n      width: 100vw !important;\n      height: 100vh !important;\n      max-width: none !important;\n      max-height: none !important;\n      aspect-ratio: auto !important;\n    \}''')
    replacement = '''    canvas.emscripten {\n      position: fixed !important;\n      transform: none !important;\n      max-width: none !important;\n      max-height: none !important;\n      aspect-ratio: auto !important;\n    }'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit('Could not neutralize legacy full-viewport canvas !important CSS')
    path.write_text(text, encoding='utf-8')


def patch_viewport(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    old = '''        canvas.style.width = `${width}px`;\n        canvas.style.height = `${height}px`;\n        canvas.style.left = `${Math.round((viewport.width - width) / 2)}px`;\n        canvas.style.top = `${Math.round((viewport.height - height) / 2)}px`;\n        canvas.style.right = 'auto';\n        canvas.style.bottom = 'auto';'''
    new = '''        canvas.style.setProperty('inset', 'auto', 'important');\n        canvas.style.setProperty('width', `${width}px`, 'important');\n        canvas.style.setProperty('height', `${height}px`, 'important');\n        canvas.style.setProperty('left', `${Math.round((viewport.width - width) / 2)}px`, 'important');\n        canvas.style.setProperty('top', `${Math.round((viewport.height - height) / 2)}px`, 'important');\n        canvas.style.setProperty('right', 'auto', 'important');\n        canvas.style.setProperty('bottom', 'auto', 'important');'''
    if text.count(old) != 1:
        raise SystemExit('Could not locate moderation viewport CSS assignment block')
    text = text.replace(old, new, 1)
    if "setProperty('width', `${width}px`, 'important')" not in text:
        raise SystemExit('Final 2:1 viewport important override missing')
    path.write_text(text, encoding='utf-8')


def patch_shell(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    old = 'alert("WebGL context lost. You will need to reload the page.")'
    new = "alert(String(window.yandexGameLanguage||navigator.language||'en').toLowerCase().startsWith('ru')?'Контекст WebGL потерян. Перезагрузите страницу.':'WebGL context lost. You will need to reload the page.')"
    if text.count(old) != 1:
        raise SystemExit('Could not locate WebGL context-lost alert')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')


def patch_index(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    shell_tag = '<script src="openttd-shell-2.js"></script>'
    i18n_tag = '<script src="openttd-yandex-shell-i18n.js"></script>'
    if i18n_tag not in text:
        if text.count(shell_tag) != 1:
            raise SystemExit('Could not find shell tag in index.html')
        text = text.replace(shell_tag, i18n_tag + shell_tag, 1)
    path.write_text(text, encoding='utf-8')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    args = ap.parse_args()
    dist = args.dist.resolve()

    required = (
        'index.html', 'yandex-bridge.js', 'openttd-yandex-fixes.js',
        'openttd-full-viewport.js', 'openttd-yandex-web-keys.js',
        'openttd-shell-2.js', 'openttd-runtime.js', 'openttd-classic-ai.js',
    )
    for name in required:
        if not (dist / name).is_file():
            raise SystemExit(f'Missing package file: {name}')

    patch_ads(dist / 'yandex-bridge.js')
    patch_legacy_scale(dist / 'openttd-yandex-fixes.js')
    patch_viewport(dist / 'openttd-full-viewport.js')
    patch_shell(dist / 'openttd-shell-2.js')
    (dist / 'openttd-yandex-web-keys.js').write_text(WEB_GUARD_JS, encoding='utf-8')
    (dist / 'openttd-yandex-shell-i18n.js').write_text(SHELL_I18N_JS, encoding='utf-8')
    patch_index(dist / 'index.html')

    unpacked = sum(p.stat().st_size for p in dist.rglob('*') if p.is_file())
    if unpacked >= 100_000_000:
        raise SystemExit(f'Yandex package too large: {unpacked}')

    print(f'Final Yandex publication patch applied: unpacked_bytes={unpacked}')


if __name__ == '__main__':
    main()
