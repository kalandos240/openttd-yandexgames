#!/usr/bin/env bash
set -euo pipefail

# Reuse the proven final FreeType/Yandex build, but convert Emscripten's
# external .wasm/.data resources into embedded resources. This makes the
# package launchable by double-clicking index.html via file:// without a
# local HTTP server, while remaining usable when hosted by Yandex Games.
cp ci/build-final.sh /tmp/build-direct-file-base.sh

python3 - <<'PY'
from pathlib import Path
p = Path('/tmp/build-direct-file-base.sh')
s = p.read_text()

needle = "cmake.write_text(s)\n"
patch = r'''# Direct-file build: keep all generated/preloaded game data inside JS and
# embed the WebAssembly binary too, so the browser never fetches .data/.wasm
# over file:// (which Firefox/Chromium block for CORS/security reasons).
s = s.replace('--preload-file', '--embed-file')
wasm_marker = '    target_link_libraries(WASM::WASM INTERFACE \"-s WASM_BIGINT\")\\n'
single_file = '    target_link_libraries(WASM::WASM INTERFACE \"-s SINGLE_FILE=1\")\\n'
if single_file not in s:
    if wasm_marker not in s:
        raise SystemExit('Could not find WASM_BIGINT linker marker')
    s = s.replace(wasm_marker, wasm_marker + single_file, 1)
cmake.write_text(s)
'''
if needle not in s:
    raise SystemExit('Could not patch OpenTTD CMake mutation block')
s = s.replace(needle, patch, 1)

# SINGLE_FILE + --embed-file intentionally produce no external .wasm/.data.
s = s.replace('cp openttd/build/openttd.wasm dist/\n', '')
s = s.replace('cp openttd/build/openttd.data dist/\n', '')

# Add hard checks: the distributable must not depend on the two resources
# that cannot be fetched from file://.
marker = "cat > dist/NOTICE.txt <<'EOF'\n"
checks = r'''test -f dist/index.html
test -f dist/openttd.js
test ! -e dist/openttd.wasm
test ! -e dist/openttd.data
if grep -Eo '[A-Za-z0-9_.-]+\\.(wasm|data)' dist/index.html dist/openttd.js | grep -vE '^$'; then
    echo 'Found an external wasm/data filename in direct-file build' >&2
    exit 1
fi

'''
if marker not in s:
    raise SystemExit('Could not find NOTICE marker')
s = s.replace(marker, checks + marker, 1)

# Distinguish the output in CI/artifacts.
s = s.replace('openttd-yandexgames.zip', 'OpenTTD-YandexGames-Direct.zip')
p.write_text(s)
PY

bash /tmp/build-direct-file-base.sh
