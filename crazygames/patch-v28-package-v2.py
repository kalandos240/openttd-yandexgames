#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: patch-v28-package-v2.py <package-dir>')
root = Path(sys.argv[1])

def text(name):
    p = root / name
    if not p.is_file():
        raise SystemExit(f'missing {name}')
    return p.read_text(encoding='utf-8')

def write(name, value):
    (root / name).write_text(value, encoding='utf-8')

# V28 -> CrazyGames platform-neutral mobile layer.
s = text('openttd-yandex-mobile.js')
s = s.replace('__openttdYandexMobileInstalled', '__openttdCrazyGamesMobileInstalled')
s = s.replace('Yandex deviceInfo arrives later', 'CrazyGames systemInfo arrives later')
old = """  Promise.resolve(window.yandexGamesSDKReady).then(async ysdk => {
    try {
      const info = ysdk && ysdk.deviceInfo;
      if (info) {
        sdkDeviceType = String(info.type || '');
        if (!sdkDeviceType) {
          if (typeof info.isMobile === 'function' && info.isMobile()) sdkDeviceType = 'mobile';
          else if (typeof info.isTablet === 'function' && info.isTablet()) sdkDeviceType = 'tablet';
          else if (typeof info.isTV === 'function' && info.isTV()) sdkDeviceType = 'tv';
          else if (typeof info.isDesktop === 'function' && info.isDesktop()) sdkDeviceType = 'desktop';
        }
        sdkDeviceReady = true;
        publishProfile();
      }
    } catch (error) {
      console.warn('[OpenTTD mobile] Yandex deviceInfo unavailable', error);
    }
"""
new = """  Promise.resolve(window.crazyGamesSDKReady).then(async sdk => {
    try {
      const type = String(sdk?.user?.systemInfo?.device?.type || '');
      if (['mobile', 'tablet', 'desktop'].includes(type)) {
        sdkDeviceType = type;
        sdkDeviceReady = true;
        publishProfile();
      }
    } catch (error) {
      console.warn('[OpenTTD mobile] CrazyGames systemInfo unavailable', error);
    }
"""
if old not in s:
    raise SystemExit('mobile deviceInfo block not found')
s = s.replace(old, new, 1)
start = s.find('  /* Ask Yandex fullscreen on the first deliberate touch.')
end = s.find('  const mouseEvent = ', start)
if start < 0 or end < 0:
    raise SystemExit('mobile fullscreen block not found')
s = s[:start] + '  /* CrazyGames controls fullscreen at the platform level; the game never requests it. */\n\n' + s[end:]
write('openttd-crazygames-mobile.js', s)

s = text('openttd-yandex-fixes.js')
s = s.replace('Loaded after yandex-bridge.js and before openttd-runtime.js.', 'Loaded after crazygames-bridge.js and before openttd-runtime.js.')
s = s.replace("String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase()", "String(window.crazyGamesGameLanguage || window.yandexGameLanguage || navigator.language || 'en').toLowerCase()")
anchor = '  const applyHardPause = () => {'
addition = """  window.openttdSetPlatformAudioEnabled = function(enabled) {
    platformAudioEnabled = !!enabled;
    if (platformAudioEnabled) resumeAudio();
    else suspendAudio();
  };
  if (window.__crazyGamesMuteAudio === true) window.openttdSetPlatformAudioEnabled(false);

"""
if anchor not in s:
    raise SystemExit('platform fixes audio anchor not found')
s = s.replace(anchor, addition + anchor, 1)
write('openttd-platform-fixes.js', s)

s = text('openttd-yandex-shell-i18n.js')
s = s.replace('__openttdYandexShellI18nInstalled', '__openttdCrazyGamesShellI18nInstalled')
s = s.replace("String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase().startsWith('ru')", "String(window.crazyGamesGameLanguage || navigator.language || 'en').toLowerCase().startsWith('ru')")
s = s.replace("'openttd-yandex-language-ready'", "'openttd-crazygames-language-ready'")
write('openttd-crazygames-shell-i18n.js', s)

s = text('openttd-yandex-web-keys.js')
s = s.replace('__openttdYandexWebGuardInstalled', '__openttdCrazyGamesWebGuardInstalled')
write('openttd-crazygames-web-keys.js', s)

html = text('index.html')
old = '''    <!-- Yandex Games SDK -->
    <script src="yandex-bootstrap.js"></script><script src="openttd-yandex-mobile.js"></script>
  <script src="yandex-bridge.js"></script><script src="openttd-global-ranking.js"></script><script src="openttd-classic-ai.js"></script><script src="openttd-yandex-fixes.js"></script><script src="openttd-full-viewport.js"></script><script src="openttd-yandex-web-keys.js"></script><script src="openttd-ranking-core.js"></script><script src="openttd-vanilla-migration.js"></script>
  </head><body><div class=background><div id=box><div id=title>Loading ...</div><div id=message></div></div></div><div><canvas class=emscripten id=canvas tabindex=-1></canvas></div><script src="openttd-yandex-shell-i18n.js"></script><script src="openttd-shell-2.js"></script><script src="openttd-runtime.js"></script></body></html>'''
new = '''    <!-- CrazyGames HTML5 SDK v3 -->
    <script src="https://sdk.crazygames.com/crazygames-sdk-v3.js"></script>
    <script src="crazygames-bootstrap.js"></script><script src="openttd-crazygames-mobile.js"></script>
    <script src="crazygames-bridge.js"></script><script src="openttd-classic-ai.js"></script><script src="openttd-platform-fixes.js"></script><script src="openttd-full-viewport.js"></script><script src="openttd-crazygames-web-keys.js"></script><script src="openttd-vanilla-migration.js"></script>
  </head><body><div class=background><div id=box><div id=title>Loading ...</div><div id=message></div></div></div><div><canvas class=emscripten id=canvas tabindex=-1></canvas></div><script src="openttd-crazygames-shell-i18n.js"></script><script src="openttd-shell-2.js"></script><script src="openttd-runtime.js"></script></body></html>'''
if old not in html:
    raise SystemExit('index platform script block not found')
html = html.replace(old, new, 1)
write('index.html', html)

for name in [
    'yandex-bootstrap.js', 'yandex-bridge.js', 'openttd-yandex-mobile.js',
    'openttd-yandex-fixes.js', 'openttd-yandex-shell-i18n.js',
    'openttd-yandex-web-keys.js', 'openttd-global-ranking.js',
    'openttd-ranking-core.js', 'YANDEX-INTEGRATION.txt',
]:
    p = root / name
    if p.exists():
        p.unlink()

print('CrazyGames V2 package transform: PASS')
