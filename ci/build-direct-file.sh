#!/usr/bin/env bash
set -euo pipefail

# Direct-file variant of the proven final FreeType/Yandex build.
# All Emscripten resources are embedded, so index.html can be opened through
# file:// without a local HTTP server. Hosted/Yandex behaviour stays intact.
cp ci/build-final.sh /tmp/build-direct-file-base.sh

python3 - <<'PY'
from pathlib import Path
p = Path('/tmp/build-direct-file-base.sh')
s = p.read_text()

# Extend the Python patch that build-final.sh applies to OpenTTD's CMake.
needle = "cmake.write_text(s)\n"
patch = '''# Direct-file build: embed all files and the WebAssembly binary.
s = s.replace('--preload-file', '--embed-file')
wasm_marker = '    target_link_libraries(WASM::WASM INTERFACE "-s WASM_BIGINT")\\n'
single_file = '    target_link_libraries(WASM::WASM INTERFACE "-s SINGLE_FILE=1")\\n'
if single_file not in s:
    if wasm_marker not in s:
        raise SystemExit('Could not find WASM_BIGINT linker marker')
    s = s.replace(wasm_marker, wasm_marker + single_file, 1)
cmake.write_text(s)
'''
if needle not in s:
    raise SystemExit('Could not patch OpenTTD CMake mutation block')
s = s.replace(needle, patch, 1)

# Patch the generated OpenTTD Emscripten runtime before pre.js is written.
# Upstream WebAssembly starts with -snull, explicitly disabling OpenSFX.
# We switch to SDL audio and also pre-answer the OpenTTD survey prompt with No.
# On file://, skip only the persistent IDBFS mount; HTTPS/Yandex keeps IDBFS.
needle = "pre.write_text(s)\n"
patch = r'''args_old = "Module.arguments.push('-mnull', '-snull', '-vsdl');"
args_new = "Module.arguments.push('-mnull', '-ssdl', '-vsdl');"
if args_old not in s:
    raise SystemExit('Could not find Emscripten null sound arguments')
s = s.replace(args_old, args_new, 1)

survey_dependency = "            Module.removeRunDependency('syncfs');"
survey_patch = r'''            try {
                const private_path = personal_dir + '/private.cfg';
                let private_config = '';
                try {
                    private_config = FS.readFile(private_path, { encoding: 'utf8' });
                } catch (e) {}

                if (/^participate_survey\s*=.*$/m.test(private_config)) {
                    private_config = private_config.replace(/^participate_survey\s*=.*$/m, 'participate_survey = no');
                } else if (/^\[network\]\s*$/m.test(private_config)) {
                    private_config = private_config.replace(/^\[network\]\s*$/m, '[network]\nparticipate_survey = no');
                } else {
                    private_config += (private_config.length === 0 || private_config.endsWith('\n') ? '' : '\n') + '[network]\nparticipate_survey = no\n';
                }
                FS.writeFile(private_path, private_config);
            } catch (e) {
                console.warn('Could not disable OpenTTD survey prompt', e);
            }
'''
if survey_dependency not in s:
    raise SystemExit('Could not find startup dependency removal point')
s = s.replace(survey_dependency, survey_patch + survey_dependency, 1)

file_mount = "    FS.mount(IDBFS, {}, personal_dir);\n"
file_mount_replacement = """    if (typeof location !== 'undefined' && location.protocol === 'file:') {
        console.warn('OpenTTD direct-file mode: IndexedDB persistence is disabled for this local launch.');
    } else {
        FS.mount(IDBFS, {}, personal_dir);
    }
"""
if file_mount not in s:
    raise SystemExit('Could not find IDBFS mount line')
s = s.replace(file_mount, file_mount_replacement, 1)
pre.write_text(s)
'''
if needle not in s:
    raise SystemExit('Could not patch OpenTTD pre.js mutation block')
s = s.replace(needle, patch, 1)

# SINGLE_FILE + --embed-file intentionally produce no external .wasm/.data.
s = s.replace('cp openttd/build/openttd.wasm dist/\n', '')
s = s.replace('cp openttd/build/openttd.data dist/\n', '')
# Depending on Emscripten output mode, SINGLE_FILE may inline JS into the HTML
# or leave one JS file containing every subresource. Accept both layouts.
s = s.replace('cp openttd/build/openttd.js dist/\n', '[ ! -f openttd/build/openttd.js ] || cp openttd/build/openttd.js dist/\n')

marker = "cat > dist/NOTICE.txt <<'EOF'\n"
checks = '''test -f dist/index.html\ntest ! -e dist/openttd.wasm\ntest ! -e dist/openttd.data\n\n'''
if marker not in s:
    raise SystemExit('Could not find NOTICE marker')
s = s.replace(marker, checks + marker, 1)

s = s.replace('openttd-yandexgames.zip', 'OpenTTD-YandexGames-Direct.zip')
p.write_text(s)
PY

# Preserve the final build's Cyrillic/TrueType support.
echo 'Preparing Emscripten FreeType for Russian/Cyrillic text...'
embuilder build freetype

bash /tmp/build-direct-file-base.sh
