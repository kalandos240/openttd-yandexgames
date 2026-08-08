#!/usr/bin/env bash
set -euo pipefail

apt-get update
apt-get install -y --no-install-recommends curl unzip zip ca-certificates

rm -rf dist baseline-artifact baseline-inner.zip /tmp/ottd-assets /tmp/yandex-baseset
mkdir -p baseline-artifact dist /tmp/ottd-assets /tmp/yandex-baseset

curl -L --fail --retry 3 \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -o /tmp/baseline-artifact.zip \
  https://api.github.com/repos/kalandos240/openttd-yandexgames/actions/artifacts/9026488472/zip
unzip -q /tmp/baseline-artifact.zip -d baseline-artifact
unzip -q baseline-artifact/openttd-yandexgames.zip -d dist

curl -L --fail --retry 3 -o /tmp/opengfx.zip https://cdn.openttd.org/opengfx-releases/8.0/opengfx-8.0-all.zip
echo '43a0c1dabf39cb865394f3a6cc36d4da5c10ecfaaf55652043104806810903be  /tmp/opengfx.zip' | sha256sum -c -
curl -L --fail --retry 3 -o /tmp/opensfx.zip https://cdn.openttd.org/opensfx-releases/1.0.3/opensfx-1.0.3-all.zip
echo 'e0a218b7dd9438e701503b0f84c25a97c1c11b7c2f025323fb19d6db16ef3759  /tmp/opensfx.zip' | sha256sum -c -
curl -L --fail --retry 3 -o /tmp/openmsx.zip https://cdn.openttd.org/openmsx-releases/0.4.2/openmsx-0.4.2-all.zip
echo '5a4277a2e62d87f2952ea5020dc20fb2f6ffafdccf9913fbf35ad45ee30ec762  /tmp/openmsx.zip' | sha256sum -c -

unzip -q /tmp/opengfx.zip -d /tmp/ottd-assets/opengfx
unzip -q /tmp/opensfx.zip -d /tmp/ottd-assets/opensfx
unzip -q /tmp/openmsx.zip -d /tmp/ottd-assets/openmsx
find /tmp/ottd-assets -type f -name '*.tar' -exec cp -f '{}' /tmp/yandex-baseset/ \;

echo 'Extra base-set packages:'
ls -lah /tmp/yandex-baseset
test -n "$(find /tmp/yandex-baseset -type f -print -quit)"

python3 /emsdk/upstream/emscripten/tools/file_packager.py dist/yandex-basesets.data \
  --preload /tmp/yandex-baseset@/baseset \
  --js-output=dist/yandex-basesets.js

python3 - <<'PY'
from pathlib import Path
p = Path('dist/index.html')
s = p.read_text()

# Remove the too-early LoadingAPI.ready() call from the baseline wrapper.
s = s.replace("""          window.addEventListener('load', () => {
            setTimeout(() => {
              try { ysdk.features.LoadingAPI?.ready(); } catch (e) { console.warn('LoadingAPI.ready failed', e); }
            }, 500);
          }, { once: true });
""", "")

needle = '<script async src=openttd.js></script>'
bridge = r'''<script src="yandex-basesets.js"></script>
<script>
(function () {
  const originalPush = Module.preRun.push.bind(Module.preRun);
  let hooked = false;
  Module.preRun.push = function () {
    const result = originalPush.apply(null, arguments);
    if (!hooked) {
      hooked = true;
      originalPush(function () {
        Module.addRunDependency('yandex-locale');
        const finish = function () {
          setTimeout(function () {
            try {
              const personalDir = '/home/web_user/.openttd';
              const configPath = personalDir + '/openttd.cfg';
              let config = '';
              try { config = FS.readFile(configPath, {encoding: 'utf8'}); } catch (e) {}
              if (!/^language\s*=.*$/m.test(config)) {
                const locale = String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase();
                const language = locale.startsWith('ru') ? 'russian.lng' : 'english.lng';
                if (/^\[misc\]\s*$/m.test(config)) {
                  config = config.replace(/^\[misc\]\s*$/m, '[misc]\nlanguage = ' + language);
                } else {
                  config = '[misc]\nlanguage = ' + language + '\n\n' + config;
                }
                FS.writeFile(configPath, config);
              }
            } catch (e) {
              console.warn('Could not apply Yandex locale to OpenTTD', e);
            }
            Module.removeRunDependency('yandex-locale');
          }, 500);
        };
        if (window.yandexGamesSDKReady) {
          Promise.race([
            window.yandexGamesSDKReady,
            new Promise(resolve => setTimeout(() => resolve(null), 2500))
          ]).then(finish, finish);
        } else {
          finish();
        }
      });
    }
    return result;
  };

  Module.postRun.push(function () {
    if (!window.yandexGamesSDKReady) return;
    window.yandexGamesSDKReady.then(function (ysdk) {
      if (!ysdk) return;
      try {
        if (ysdk.features && ysdk.features.LoadingAPI) ysdk.features.LoadingAPI.ready();
      } catch (e) {
        console.warn('LoadingAPI.ready failed', e);
      }
    });
  });
})();
</script>
<script async src=openttd.js></script>'''
if needle not in s:
    raise SystemExit('Could not find OpenTTD script tag')
s = s.replace(needle, bridge, 1)
p.write_text(s)
PY

cat > dist/NOTICE.txt <<'EOF'
OpenTTD 15.3 WebAssembly port for Yandex Games.
OpenTTD is licensed under GNU GPL v2.
Bundled free base sets: OpenGFX 8.0, OpenSFX 1.0.3, OpenMSX 0.4.2.
Yandex Games integration/build automation: kalandos240/openttd-yandexgames.
EOF

uncompressed_bytes=$(du -sb dist | cut -f1)
echo "Uncompressed bytes: ${uncompressed_bytes}"
test "${uncompressed_bytes}" -lt 100000000
rm -f openttd-yandexgames-fast.zip
(cd dist && zip -9 -r ../openttd-yandexgames-fast.zip .)
ls -lah openttd-yandexgames-fast.zip dist
