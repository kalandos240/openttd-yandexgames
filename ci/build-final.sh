#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends git gcc-12 g++-12 zip unzip curl ca-certificates
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 100
update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 100

rm -rf openttd dist openttd-yandexgames.zip
git clone --depth 1 --branch 15.3 https://github.com/OpenTTD/OpenTTD.git openttd
cp openttd/os/emscripten/ports/liblzma.py /emsdk/upstream/emscripten/tools/ports/contrib/

python3 - <<'PY'
from pathlib import Path

cmake = Path('openttd/CMakeLists.txt')
s = cmake.read_text()
english = '    target_link_libraries(WASM::WASM INTERFACE "--preload-file ${CMAKE_BINARY_DIR}/lang/english.lng@/lang/english.lng")\n'
if english not in s:
    raise SystemExit('Could not find Emscripten language preload line')
if 'russian.lng@/lang/russian.lng' not in s:
    s = s.replace(
        english,
        english
        + '    target_link_libraries(WASM::WASM INTERFACE "--preload-file ${CMAKE_BINARY_DIR}/lang/russian.lng@/lang/russian.lng")\n'
        + '    target_link_libraries(WASM::WASM INTERFACE "--preload-file ${CMAKE_BINARY_DIR}/yandex_baseset@/baseset")\n',
        1,
    )
# The direct-file build embeds OpenGFX/OpenSFX/OpenMSX plus rendered browser
# audio into the module. OpenTTD's upstream 32 MiB initial heap is too small
# for the linker once those assets are embedded. Keep growth enabled, but start
# at 64 MiB so the module can link and boot reliably.
old_memory = '    target_link_libraries(WASM::WASM INTERFACE "-s INITIAL_MEMORY=33554432")\n'
new_memory = '    target_link_libraries(WASM::WASM INTERFACE "-s INITIAL_MEMORY=67108864")\n'
if old_memory not in s:
    raise SystemExit('Could not find Emscripten INITIAL_MEMORY setting')
s = s.replace(old_memory, new_memory, 1)
cmake.write_text(s)

pre = Path('openttd/os/emscripten/pre.js')
s = pre.read_text()
old = """    FS.syncfs(true, function (err) {
        Module.removeRunDependency('syncfs');
    });
"""
new = """    FS.syncfs(true, function (err) {
        const finish_startup = function() {
            try {
                const config_path = personal_dir + '/openttd.cfg';
                let config = '';
                try {
                    config = FS.readFile(config_path, { encoding: 'utf8' });
                } catch (e) {}

                if (!/^language\\s*=.*$/m.test(config)) {
                    const locale = String(window.yandexGameLanguage || navigator.language || 'en').toLowerCase();
                    const language = locale.startsWith('ru') ? 'russian.lng' : 'english.lng';
                    if (/^\\[misc\\]\\s*$/m.test(config)) {
                        config = config.replace(/^\\[misc\\]\\s*$/m, '[misc]\\nlanguage = ' + language);
                    } else {
                        config = '[misc]\\nlanguage = ' + language + '\\n\\n' + config;
                    }
                    FS.writeFile(config_path, config);
                }
            } catch (e) {
                console.warn('Could not apply Yandex locale to OpenTTD', e);
            }
            Module.removeRunDependency('syncfs');
        };

        if (window.yandexGamesSDKReady) {
            Promise.race([
                window.yandexGamesSDKReady,
                new Promise(resolve => setTimeout(() => resolve(null), 3000))
            ]).then(finish_startup, finish_startup);
        } else {
            finish_startup();
        }
    });
"""
if old not in s:
    raise SystemExit('Could not find initial IDBFS sync block')
s = s.replace(old, new, 1)
s += """

Module.postRun.push(function() {
    if (!window.yandexGamesSDKReady) return;
    window.yandexGamesSDKReady.then(function(ysdk) {
        if (!ysdk) return;
        try {
            if (ysdk.features && ysdk.features.LoadingAPI) ysdk.features.LoadingAPI.ready();
        } catch (e) {
            console.warn('LoadingAPI.ready failed', e);
        }
    });
});
"""
pre.write_text(s)
PY

mkdir -p openttd/build-host
(
  cd openttd/build-host
  cmake .. -DOPTION_TOOLS_ONLY=ON -DCMAKE_BUILD_TYPE=Release
  cmake --build . -j "$(nproc)" --target tools
)

mkdir -p openttd/build
(
  cd openttd/build
  emcmake cmake .. \
    -DHOST_BINARY_DIR=../build-host \
    -DCMAKE_BUILD_TYPE=Release \
    -DOPTION_USE_ASSERTS=OFF
)

mkdir -p openttd/build/yandex_baseset /tmp/ottd-assets
curl -L --fail --retry 3 -o /tmp/opengfx.zip https://cdn.openttd.org/opengfx-releases/8.0/opengfx-8.0-all.zip
echo '43a0c1dabf39cb865394f3a6cc36d4da5c10ecfaaf55652043104806810903be  /tmp/opengfx.zip' | sha256sum -c -
curl -L --fail --retry 3 -o /tmp/opensfx.zip https://cdn.openttd.org/opensfx-releases/1.0.3/opensfx-1.0.3-all.zip
echo 'e0a218b7dd9438e701503b0f84c25a97c1c11b7c2f025323fb19d6db16ef3759  /tmp/opensfx.zip' | sha256sum -c -
curl -L --fail --retry 3 -o /tmp/openmsx.zip https://cdn.openttd.org/openmsx-releases/0.4.2/openmsx-0.4.2-all.zip
echo '5a4277a2e62d87f2952ea5020dc20fb2f6ffafdccf9913fbf35ad45ee30ec762  /tmp/openmsx.zip' | sha256sum -c -

unzip -q /tmp/opengfx.zip -d /tmp/ottd-assets/opengfx
unzip -q /tmp/opensfx.zip -d /tmp/ottd-assets/opensfx
unzip -q /tmp/openmsx.zip -d /tmp/ottd-assets/openmsx
find /tmp/ottd-assets -type f \( \
  -name '*.tar' -o -name '*.grf' -o -name '*.obg' -o \
  -name '*.obs' -o -name '*.cat' -o -name '*.obm' -o -name '*.mid' \
\) -exec cp -f '{}' openttd/build/yandex_baseset/ \;

echo 'Bundled base-set files:'
ls -lah openttd/build/yandex_baseset
test -n "$(find openttd/build/yandex_baseset -type f -print -quit)"

(
  cd openttd/build
  cmake --build . -j "$(nproc)" --target openttd
)

mkdir -p dist
cp openttd/build/openttd.html dist/index.html
cp openttd/build/openttd.js dist/
cp openttd/build/openttd.wasm dist/
cp openttd/build/openttd.data dist/

python3 - <<'PY'
from pathlib import Path
p = Path('dist/index.html')
s = p.read_text()
sdk = '''
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
if '</head>' not in s:
    raise SystemExit('No </head> found in generated HTML')
s = s.replace('</head>', sdk + '  </head>', 1)
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
(cd dist && zip -9 -r ../openttd-yandexgames.zip .)
ls -lah openttd-yandexgames.zip dist
