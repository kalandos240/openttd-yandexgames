#!/usr/bin/env python3
"""Turn the historical direct-file build into a platform-native split runtime.

The legacy pipeline intentionally used Emscripten SINGLE_FILE and --embed-file
so index.html could run from file:// with no server. Yandex Games and Playgama
serve ordinary same-origin files, so that mode is counterproductive: a ~57 MiB
Wasm binary becomes base64 inside a ~76 MiB JavaScript file, increasing parse,
decode and peak-memory cost on every cold browser profile.

Keep all gameplay/audio/source patches from the tested direct-file pipeline, but
leave Emscripten's normal JS + WASM + DATA output intact. The final packaging
step renames only the JS loader to openttd-runtime.js; Wasm/data remain separate
and cacheable/streamable by the browser.
"""
from pathlib import Path

path = Path('ci/build-direct-file.sh')
if not path.is_file():
    raise SystemExit('Legacy direct-file build script is missing')
text = path.read_text(encoding='utf-8')

single_old = r'''patch = r'''# Direct-file build: embed all files and the WebAssembly binary.
s = s.replace('--preload-file', '--embed-file')
wasm_marker = '    target_link_libraries(WASM::WASM INTERFACE "-s WASM_BIGINT")\n'
single_file = '    target_link_libraries(WASM::WASM INTERFACE "-s SINGLE_FILE=1")\n'
if single_file not in s:
    if wasm_marker not in s:
        raise SystemExit('Could not find WASM_BIGINT linker marker')
    s = s.replace(wasm_marker, wasm_marker + single_file, 1)
cmake.write_text(s)
'''
'''
single_new = r'''patch = r'''# Platform delivery: keep JS, Wasm and preloaded data as separate files.
# Do not convert --preload-file to --embed-file and do not enable SINGLE_FILE.
if '--embed-file' in s:
    raise SystemExit('Unexpected embedded-file flag before platform runtime patch')
if 'SINGLE_FILE=1' in s:
    raise SystemExit('Unexpected SINGLE_FILE flag before platform runtime patch')
cmake.write_text(s)
'''
'''
if text.count(single_old) != 1:
    raise SystemExit(f'Could not locate historical SINGLE_FILE mutation block ({text.count(single_old)})')
text = text.replace(single_old, single_new, 1)

copy_old = """s = s.replace('cp openttd/build/openttd.wasm dist/\\n', '')
s = s.replace('cp openttd/build/openttd.data dist/\\n', '')
s = s.replace('cp openttd/build/openttd.js dist/\\n', '[ ! -f openttd/build/openttd.js ] || cp openttd/build/openttd.js dist/\\n')
"""
copy_new = """# Platform packages keep the generated JS loader, Wasm binary and data archive.
# build-final.sh already copies all three files into dist/.
"""
if text.count(copy_old) != 1:
    raise SystemExit(f'Could not locate direct-file output stripping block ({text.count(copy_old)})')
text = text.replace(copy_old, copy_new, 1)

checks_old = """checks = '''test -f dist/index.html\\ntest ! -e dist/openttd.wasm\\ntest ! -e dist/openttd.data\\n\\n'''
"""
checks_new = """checks = '''test -f dist/index.html\\ntest -s dist/openttd.js\\ntest -s dist/openttd.wasm\\ntest -s dist/openttd.data\\n\\n'''
"""
if text.count(checks_old) != 1:
    raise SystemExit(f'Could not locate direct-file output assertions ({text.count(checks_old)})')
text = text.replace(checks_old, checks_new, 1)

text = text.replace(
    '# - all Emscripten resources are embedded, so index.html works via file://',
    '# - gameplay/audio patches come from the tested direct-file pipeline, but platform output stays split',
    1,
)

for forbidden in (
    "s.replace('--preload-file', '--embed-file')",
    'single_file =',
    "test ! -e dist/openttd.wasm",
    "test ! -e dist/openttd.data",
):
    if forbidden in text:
        raise SystemExit(f'Historical single-file behaviour remains: {forbidden}')

path.write_text(text, encoding='utf-8')
print('Platform streaming runtime enabled: separate openttd.js, openttd.wasm and openttd.data.')
