#!/usr/bin/env bash
set -euo pipefail

# Extend the already-tested direct-file/audio build with:
# - a strictly single-player/offline OpenTTD UI/runtime
# - Yandex Games cloud saves, gameplay lifecycle and interstitial ads
# - CSP-safe external scripts while keeping embedded WASM/assets for file://
# - complete release licensing/source notices
#
# We patch the base build script rather than duplicating its large, tested body.
python3 - <<'PY'
from pathlib import Path

p = Path('ci/build-final.sh')
s = p.read_text()

clone_marker = 'cp openttd/os/emscripten/ports/liblzma.py /emsdk/upstream/emscripten/tools/ports/contrib/\n'
source_hook = (
    'python3 ci/patch-yandex-offline.py source\n'
    'python3 ci/patch-yandex-no-help.py\n'
    'python3 ci/patch-yandex-gameplay-state.py\n'
    'python3 ci/patch-ai-zero-interval.py\n'
    'python3 ci/patch-yandex-runtime-cleanup.py source\n'
    'python3 ci/patch-yandex-ai-offline.py\n'
)
if clone_marker not in s:
    raise SystemExit('Could not find OpenTTD clone/source patch marker')
s = s.replace(clone_marker, clone_marker + source_hook, 1)

host_marker = 'mkdir -p openttd/build-host\n'
pre_hook = (
    'python3 ci/patch-yandex-offline.py pre\n'
    'python3 ci/patch-yandex-runtime-cleanup.py pre\n\n'
)
if host_marker not in s:
    raise SystemExit('Could not find host build marker')
s = s.replace(host_marker, pre_hook + host_marker, 1)

notice_marker = "cat > dist/NOTICE.txt <<'EOF'\n"
bridge_hook = r"""python3 - <<'PY_YANDEX_BRIDGE'
from pathlib import Path
p = Path('dist/index.html')
html = p.read_text()
bridge = Path('ci/yandex-bridge.js').read_text()

# `build-final.sh` uses the normal synchronous SDK tag. Replace it only in the
# Yandex/direct-file edition with a dynamic loader so a local file:// launch
# does not try to fetch file:///sdk.js. The block is externalized later for CSP.
old_sdk = '''\
    <!-- Yandex Games SDK -->
    <script src="/sdk.js"></script>
    <script>
      window.yandexGameLanguage = navigator.language || 'en';
      window.yandexGamesSDKReady = (async () => {
        try {
          const ysdk = await YaGames.init();
          window.ysdk = ysdk;
          window.yandexGameLanguage = (ysdk.environment && ysdk.environment.i18n && ysdk.environment.i18n.lang) || window.yandexGameLanguage;
          return ysdk;
        } catch (e) {
          console.warn('Yandex Games SDK initialization failed', e);
          return null;
        }
      })();
    </script>
'''
new_sdk = '''\
    <!-- Yandex Games SDK -->
    <script>
      window.yandexGameLanguage = navigator.language || 'en';
      window.yandexGamesSDKReady = (async () => {
        if (location.protocol === 'file:') return null;
        try {
          if (typeof window.YaGames === 'undefined') {
            await new Promise((resolve, reject) => {
              const script = document.createElement('script');
              script.src = '/sdk.js';
              script.async = true;
              script.onload = resolve;
              script.onerror = () => reject(new Error('Could not load /sdk.js'));
              document.head.appendChild(script);
            });
          }
          const ysdk = await YaGames.init();
          window.ysdk = ysdk;
          window.yandexGameLanguage = (ysdk.environment && ysdk.environment.i18n && ysdk.environment.i18n.lang) || window.yandexGameLanguage;
          return ysdk;
        } catch (e) {
          console.warn('Yandex Games SDK initialization failed', e);
          return null;
        }
      })();
    </script>
'''
if old_sdk not in html:
    raise SystemExit('Could not find generated Yandex SDK block')
html = html.replace(old_sdk, new_sdk, 1)

if '</head>' not in html:
    raise SystemExit('No </head> found while injecting Yandex bridge')
html = html.replace('</head>', '<script>\n' + bridge + '\n</script>\n  </head>', 1)
p.write_text(html)
PY_YANDEX_BRIDGE

# Yandex uses nonce-based CSP. Move every inline script to same-origin files
# without changing DOM execution order. The huge runtime still contains the
# embedded WASM/assets, so local file:// launch remains serverless.
python3 ci/patch-yandex-runtime-cleanup.py dist

"""
if notice_marker not in s:
    raise SystemExit('Could not find final HTML/NOTICE marker')
s = s.replace(notice_marker, bridge_hook + notice_marker, 1)

# The base build writes a short NOTICE. Replace/augment it afterwards with the
# full legal/source bundle, once the official base-set release archives have
# already been downloaded and extracted.
size_marker = 'uncompressed_bytes=$(du -sb dist | cut -f1)\n'
if size_marker not in s:
    raise SystemExit('Could not find release size-check marker')
s = s.replace(size_marker, 'bash ci/package-release-licenses.sh\n\n' + size_marker, 1)

p.write_text(s)
PY

python3 -m py_compile \
  ci/patch-yandex-offline.py \
  ci/patch-yandex-no-help.py \
  ci/patch-yandex-gameplay-state.py \
  ci/patch-yandex-sdk-events.py \
  ci/patch-ai-zero-interval.py \
  ci/patch-yandex-runtime-cleanup.py \
  ci/patch-yandex-ai-offline.py
python3 ci/patch-yandex-sdk-events.py
python3 ci/patch-yandex-runtime-cleanup.py bridge
node --check ci/yandex-bridge.js
bash -n ci/package-release-licenses.sh
bash ci/build-direct-file.sh
