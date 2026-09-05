#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
LEGACY="$ROOT/legacy"
OUT=/tmp/out
PACKAGE=/tmp/package
V28=/tmp/v28

python3 -m pip install --disable-pip-version-check --no-cache-dir 'OpenTTDLab==0.0.75'

# Reuse the exact native/mobile/adaptive patch stack proven by V28.
cp playgama/patch-browser-ranking.py "$LEGACY/ci/patch-browser-ranking.py"
cp ci/patch-browser-vanilla-no-online-content.py "$LEGACY/ci/patch-browser-vanilla-no-online-content.py"
cp ci/patch-yandex-remove-external-ui.py "$LEGACY/ci/patch-yandex-remove-external-ui.py"
cp ci/patch-yandex-mobile-native.py "$LEGACY/ci/patch-yandex-mobile-native.py"
cp ci/patch-yandex-mobile-touch-behavior-v8.py "$LEGACY/ci/patch-yandex-mobile-touch-behavior-v8.py"
cp ci/patch-yandex-adaptive-native-v9.py "$LEGACY/ci/patch-yandex-adaptive-native-v9.py"
cp ci/patch-yandex-adaptive-native-v22.py "$LEGACY/ci/patch-yandex-adaptive-native-v22.py"
cp ci/patch-yandex-adaptive-native-v27.py "$LEGACY/ci/patch-yandex-adaptive-native-v27.py"

python3 - <<'PY'
from pathlib import Path

p = Path('legacy/ci/build-yandex-release.sh')
s = p.read_text(encoding='utf-8')

ai = "    'python3 ci/patch-yandex-ai-offline.py\\n'\n"
if s.count(ai) != 1:
    raise SystemExit(f'AI-disable hook count={s.count(ai)}')
s = s.replace(ai, '', 1)

help_anchor = "    'python3 ci/patch-yandex-no-help.py\\n'\n"
if s.count(help_anchor) != 1:
    raise SystemExit('Help patch anchor missing')
native_hooks = (
    help_anchor
    + "    'python3 ci/patch-yandex-remove-external-ui.py\\n'\n"
    + "    'python3 ci/patch-yandex-mobile-native.py\\n'\n"
    + "    'python3 ci/patch-yandex-mobile-touch-behavior-v8.py\\n'\n"
    + "    'python3 ci/patch-yandex-adaptive-native-v9.py\\n'\n"
    + "    'python3 ci/patch-yandex-adaptive-native-v22.py\\n'\n"
    + "    'python3 ci/patch-yandex-adaptive-native-v27.py\\n'\n"
)
s = s.replace(help_anchor, native_hooks, 1)

anchor = "    'python3 ci/patch-yandex-runtime-cleanup.py source\\n'\n"
if s.count(anchor) != 1:
    raise SystemExit('runtime cleanup anchor missing')
add = (
    "    'python3 ci/patch-browser-vanilla-no-online-content.py\\n'\n"
    "    'python3 ci/patch-browser-ranking.py\\n'\n"
)
s = s.replace(anchor, anchor + add, 1)
p.write_text(s, encoding='utf-8')

b = Path('legacy/ci/build-final.sh')
t = b.read_text(encoding='utf-8')
font_anchor = 'mkdir -p openttd/build/yandex_baseset /tmp/ottd-assets\n'
font_repl = (
    font_anchor
    + 'cp openttd/media/baseset/OpenTTD-Sans.ttf openttd/media/baseset/OpenTTD-Small.ttf '
    + 'openttd/media/baseset/OpenTTD-Serif.ttf openttd/media/baseset/OpenTTD-Mono.ttf '
    + 'openttd/build/yandex_baseset/\n'
)
if t.count(font_anchor) != 1:
    raise SystemExit('font staging anchor missing')
b.write_text(t.replace(font_anchor, font_repl, 1), encoding='utf-8')
PY

# Preserve the browser performance profile used by the tested production build.
python3 playgama/patch-browser-build-performance.py "$LEGACY/ci/build-final.sh"

# Convert the direct-file/SINGLE_FILE pipeline into normal split Emscripten
# JS + WASM + DATA delivery. OpenMSX tracks stay outside the preload package.
python3 - <<'PY'
from pathlib import Path
p = Path('legacy/ci/build-direct-file.sh')
s = p.read_text(encoding='utf-8')

old = "s = s.replace('--preload-file', '--embed-file')"
if old not in s:
    raise SystemExit('embed-file mutation missing')
s = s.replace(old, "pass  # CrazyGames V2 keeps --preload-file", 1)

old = "single_file = '    target_link_libraries(WASM::WASM INTERFACE \"-s SINGLE_FILE=1\")\\n'"
if old not in s:
    raise SystemExit('SINGLE_FILE mutation missing')
s = s.replace(old, "single_file = ''  # CrazyGames V2: split JS/WASM/DATA", 1)

for line in (
    "s = s.replace('cp openttd/build/openttd.wasm dist/\\n', '')\n",
    "s = s.replace('cp openttd/build/openttd.data dist/\\n', '')\n",
):
    if line not in s:
        raise SystemExit('split file removal mutation missing')
    s = s.replace(line, '', 1)

old_checks = """checks = '''test -f dist/index.html\ntest ! -e dist/openttd.wasm\ntest ! -e dist/openttd.data\n\n'''"""
new_checks = """checks = '''test -f dist/index.html\ntest -s dist/openttd.wasm\ntest -s dist/openttd.data\n\n'''"""
if old_checks not in s:
    raise SystemExit('direct-file artifact checks missing')
s = s.replace(old_checks, new_checks, 1)

old_path = '    return "/baseset/" + filename + ".mp3";'
new_path = '    return "music/" + filename + ".mp3";'
if old_path not in s:
    raise SystemExit('WebAudio music path missing')
s = s.replace(old_path, new_path, 1)

begin = s.find('        let data;\n')
end = s.find('        const audio = new Audio();\n', begin)
if begin < 0 or end < 0:
    raise SystemExit('embedded WebAudio file-read block missing')
s = s[:begin] + s[end:]
old_audio = '        audio.preload = "auto";\n        audio.src = state.url;'
new_audio = '        audio.preload = "none";\n        audio.src = path;'
if old_audio not in s:
    raise SystemExit('WebAudio blob source block missing')
s = s.replace(old_audio, new_audio, 1)

old_mkdir = 'mkdir -p /tmp/openmsx-render/src /tmp/openmsx-render/wav /tmp/fs-home'
new_mkdir = 'mkdir -p /tmp/openmsx-render/src /tmp/openmsx-render/wav /tmp/openmsx-render/mp3 /tmp/fs-home'
if old_mkdir not in s:
    raise SystemExit('OpenMSX render mkdir missing')
s = s.replace(old_mkdir, new_mkdir, 1)

old_mp3 = 'mp3="openttd/build/yandex_baseset/${stem}.mp3"'
new_mp3 = 'mp3="/tmp/openmsx-render/mp3/${stem}.mp3"'
if old_mp3 not in s:
    raise SystemExit('OpenMSX MP3 output missing')
s = s.replace(old_mp3, new_mp3, 1)

# The performance patch appended SINGLE_FILE-only assertions. Replace them
# with the names actually emitted by Emscripten before package assembly.
marker = '# Validate the effective SINGLE_FILE delivery, not an optional intermediate .js.'
pos = s.find(marker)
if pos >= 0:
    s = s[:pos] + '''# Validate CrazyGames V2 split delivery.\n\
test -s dist/openttd.js\n\
test -s dist/openttd.wasm\n\
test -s dist/openttd.data\n\
test -s openttd/build/openttd.wasm\n\
test -s openttd/build/openttd.data\n'''

p.write_text(s, encoding='utf-8')
PY

python3 -m py_compile \
  "$LEGACY/ci/patch-browser-vanilla-no-online-content.py" \
  "$LEGACY/ci/patch-yandex-remove-external-ui.py" \
  "$LEGACY/ci/patch-yandex-mobile-native.py" \
  "$LEGACY/ci/patch-yandex-mobile-touch-behavior-v8.py" \
  "$LEGACY/ci/patch-yandex-adaptive-native-v9.py" \
  "$LEGACY/ci/patch-yandex-adaptive-native-v22.py" \
  "$LEGACY/ci/patch-yandex-adaptive-native-v27.py" \
  crazygames/patch-v28-package-v2.py
bash -n "$LEGACY/ci/build-direct-file.sh"

# Compile OpenTTD 15.3 with split delivery.
(
  cd "$LEGACY"
  bash ci/build-yandex-release.sh

  test -s dist/openttd.js
  test -s dist/openttd.wasm
  test -s dist/openttd.data
  test "$(stat -c%s dist/openttd.js)" -lt 5000000
  test "$(stat -c%s dist/openttd.wasm)" -gt 1000000
  test "$(stat -c%s dist/openttd.data)" -gt 1000000
  ! grep -Fq 'data:application/octet-stream;base64,' dist/openttd.js
  ! grep -Fq 'SINGLE_FILE=1' openttd/CMakeLists.txt

  grep -Fq '_em_openttd_set_touch_ui' dist/openttd.js
  grep -Fq '_em_openttd_touch_context' dist/openttd.js
  grep -Fq '_em_openttd_touch_pan' dist/openttd.js
  grep -Fq '_em_openttd_touch_mouse_event' dist/openttd.js
  grep -Fq '_em_openttd_force_window_resize' dist/openttd.js
  grep -Fq '_em_openttd_screen_width' dist/openttd.js
  grep -Fq '_em_openttd_screen_height' dist/openttd.js

  node --check dist/openttd.js
  echo '--- split runtime sizes ---'
  ls -lh dist/openttd.js dist/openttd.wasm dist/openttd.data
  echo '--- lazy music size ---'
  du -ch /tmp/openmsx-render/mp3/*.mp3 | tail -1
)

# Download the exact verified V28 package shell so all non-runtime behavior
# remains based on the user's final Yandex build.
test -n "${GH_TOKEN:-}" || { echo 'GH_TOKEN is required'; exit 1; }
rm -rf "$V28" "$PACKAGE" "$OUT"
mkdir -p "$V28" "$PACKAGE" "$OUT"
curl -fL --retry 5 --retry-all-errors \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H 'Accept: application/vnd.github+json' \
  "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/artifacts/${V28_ARTIFACT_ID:-9960231016}/zip" \
  -o /tmp/v28-artifact.zip
unzip -q /tmp/v28-artifact.zip -d "$V28"
V28_ZIP="$(find "$V28" -type f -name 'OpenTTD-v14-Yandex-Adaptive-Desktop-Mobile-V28.zip' -print -quit)"
test -s "$V28_ZIP"
unzip -q "$V28_ZIP" -d "$PACKAGE"

# Replace only the runtime payload with split files, keep music lazy, then
# apply the CrazyGames platform shell.
cp "$LEGACY/dist/openttd.js" "$PACKAGE/openttd-runtime.js"
cp "$LEGACY/dist/openttd.wasm" "$PACKAGE/openttd.wasm"
cp "$LEGACY/dist/openttd.data" "$PACKAGE/openttd.data"

rm -rf "$PACKAGE/music"
mkdir -p "$PACKAGE/music"
cp /tmp/openmsx-render/mp3/*.mp3 "$PACKAGE/music/"
test "$(find "$PACKAGE/music" -type f -name '*.mp3' | wc -l)" -ge 31

python3 ci/patch-v14-webgl-runtime.py "$PACKAGE/openttd-runtime.js"
node --check "$PACKAGE/openttd-runtime.js"
python3 crazygames/patch-v28-package-v2.py "$PACKAGE"
cp crazygames/crazygames-bootstrap.js "$PACKAGE/crazygames-bootstrap.js"
cp crazygames/crazygames-bridge.js "$PACKAGE/crazygames-bridge.js"

cat > "$PACKAGE/CRAZYGAMES-INTEGRATION.txt" <<'EOF'
OpenTTD v14 / OpenTTD 15.3 WebAssembly - CrazyGames V2
Base package: verified Yandex Adaptive Desktop-Mobile V28.
Runtime: split Emscripten JS + WASM + DATA; SINGLE_FILE disabled.
OpenMSX rendered MP3 music: lazy-loaded as individual files on demand.
CrazyGames HTML5 SDK v3: init, loading/gameplay lifecycle, Data Module,
muteAudio, device systemInfo and ad-safe pause/resume bridge.
No Yandex SDK request, Yandex ads or Yandex leaderboard are included.
EOF

# Platform/runtime invariants.
test -s "$PACKAGE/index.html"
test -s "$PACKAGE/openttd-runtime.js"
test -s "$PACKAGE/openttd.wasm"
test -s "$PACKAGE/openttd.data"
test -s "$PACKAGE/crazygames-bootstrap.js"
test -s "$PACKAGE/crazygames-bridge.js"
test -s "$PACKAGE/openttd-crazygames-mobile.js"
test -s "$PACKAGE/openttd-platform-fixes.js"
test -s "$PACKAGE/openttd-full-viewport.js"
test -s "$PACKAGE/openttd-classic-ai.js"

grep -Fq 'https://sdk.crazygames.com/crazygames-sdk-v3.js' "$PACKAGE/index.html"
grep -Fq 'CrazyGames.SDK' "$PACKAGE/crazygames-bootstrap.js"
grep -Fq 'gameplayStart' "$PACKAGE/crazygames-bridge.js"
grep -Fq 'loadingStart' "$PACKAGE/crazygames-bootstrap.js"
grep -Fq 'loadingStop' "$PACKAGE/crazygames-bridge.js"
grep -Fq 'sdk.data.getItem' "$PACKAGE/crazygames-bridge.js"
grep -Fq 'muteAudio' "$PACKAGE/crazygames-bootstrap.js"

test ! -e "$PACKAGE/yandex-bootstrap.js"
test ! -e "$PACKAGE/yandex-bridge.js"
test ! -e "$PACKAGE/openttd-yandex-mobile.js"
test ! -e "$PACKAGE/openttd-global-ranking.js"
test ! -e "$PACKAGE/openttd-ranking-core.js"
! grep -RniF '/sdk.js' "$PACKAGE" --include='*.html' --include='*.js'
! grep -RniE 'playgama|playgamma' "$PACKAGE" --include='*.html' --include='*.js' --include='*.json'

! grep -Fq 'data:application/octet-stream;base64,' "$PACKAGE/openttd-runtime.js"
test "$(stat -c%s "$PACKAGE/openttd-runtime.js")" -lt 5000000
grep -Fq 'openttd.wasm' "$PACKAGE/openttd-runtime.js"
grep -Fq 'openttd.data' "$PACKAGE/openttd-runtime.js"
grep -Fq '_em_openttd_set_touch_ui' "$PACKAGE/openttd-runtime.js"
grep -Fq '_em_openttd_touch_context' "$PACKAGE/openttd-runtime.js"
grep -Fq '_em_openttd_force_window_resize' "$PACKAGE/openttd-runtime.js"
grep -Fq '__openttdWebGLPresenter' "$PACKAGE/openttd-runtime.js"
grep -Fq 'V8-deferred-fixed-placement' "$PACKAGE/openttd-crazygames-mobile.js"
grep -Fq 'Adaptive V27 host-aware native-framebuffer recovery.' "$PACKAGE/openttd-full-viewport.js"

node --check "$PACKAGE/crazygames-bootstrap.js"
node --check "$PACKAGE/crazygames-bridge.js"
node --check "$PACKAGE/openttd-crazygames-mobile.js"
node --check "$PACKAGE/openttd-platform-fixes.js"
node --check "$PACKAGE/openttd-full-viewport.js"
node --check "$PACKAGE/openttd-runtime.js"

# Estimate the transfer before the first real gameplayStart. Music is excluded
# because it is now fetched only on demand after runtime startup.
python3 - <<'PY'
from pathlib import Path
from html.parser import HTMLParser
import gzip

root = Path('/tmp/package')
html = (root / 'index.html').read_text(encoding='utf-8')

class Parser(HTMLParser):
    def __init__(self):
        super().__init__(); self.src = []
    def handle_starttag(self, tag, attrs):
        if tag != 'script': return
        src = dict(attrs).get('src')
        if src and not src.startswith(('http://', 'https://', '//')):
            self.src.append(src)

p = Parser(); p.feed(html)
initial_names = ['index.html'] + p.src + ['openttd.wasm', 'openttd.data']
seen = []
for name in initial_names:
    if name not in seen:
        seen.append(name)
missing = [name for name in seen if not (root / name).is_file()]
if missing:
    raise SystemExit(f'missing initial files: {missing}')
raw = sum((root / name).stat().st_size for name in seen)
gz = sum(len(gzip.compress((root / name).read_bytes(), compresslevel=9)) for name in seen)
total = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
music = sum(p.stat().st_size for p in (root / 'music').glob('*.mp3'))
count = sum(1 for p in root.rglob('*') if p.is_file())
print('initial_files=' + ','.join(seen))
print(f'initial_raw_bytes={raw}')
print(f'initial_gzip_estimate_bytes={gz}')
print(f'lazy_music_bytes={music}')
print(f'total_unpacked_bytes={total}')
print(f'total_file_count={count}')
if raw >= 50_000_000:
    raise SystemExit('raw initial payload exceeds CrazyGames 50 MB hard limit')
if count >= 1500:
    raise SystemExit('CrazyGames file-count limit exceeded')
Path('/tmp/crazygames-v2-size.txt').write_text(
    f'initial_raw_bytes={raw}\n'
    f'initial_gzip_estimate_bytes={gz}\n'
    f'lazy_music_bytes={music}\n'
    f'total_unpacked_bytes={total}\n'
    f'total_file_count={count}\n',
    encoding='utf-8')
PY

ZIP="$OUT/OpenTTD-v14-CrazyGames-Adaptive-Desktop-Mobile-V2.zip"
(cd "$PACKAGE" && zip -9 -r "$ZIP" .)
unzip -t "$ZIP" >/dev/null
sha256sum "$ZIP" | tee "$OUT/SHA256SUMS.txt"
cp /tmp/crazygames-v2-size.txt "$OUT/CRAZYGAMES-V2-SIZE.txt"

python3 - <<'PY'
from pathlib import Path
import hashlib
z = Path('/tmp/out/OpenTTD-v14-CrazyGames-Adaptive-Desktop-Mobile-V2.zip')
size = Path('/tmp/out/CRAZYGAMES-V2-SIZE.txt').read_text(encoding='utf-8')
report = (
    'OpenTTD v14 CrazyGames adaptive desktop-mobile V2\n'
    'base=verified_Yandex_V28\n'
    'runtime_delivery=split_js_wasm_data\n'
    'single_file=false\n'
    'music_delivery=lazy_individual_mp3\n'
    'crazygames_sdk_v3=true\n'
    'data_module=true\n'
    'mute_audio=true\n'
    'mobile_support=true\n'
    'multiplayer=false\n'
    + size
    + f'zip_bytes={z.stat().st_size}\n'
    + f'zip_sha256={hashlib.sha256(z.read_bytes()).hexdigest()}\n'
)
Path('/tmp/out/CRAZYGAMES-V2-RESULTS.txt').write_text(report, encoding='utf-8')
print(report)
PY

ls -lh "$ZIP"
