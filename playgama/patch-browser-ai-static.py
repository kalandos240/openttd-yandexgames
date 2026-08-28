#!/usr/bin/env python3
"""Make browser AIs available before OpenTTD scans scripts, without changing player settings."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path('openttd')
if not (ROOT / 'CMakeLists.txt').is_file():
    raise SystemExit('OpenTTD source tree is missing')

try:
    from openttdlab import download_from_bananas
except ImportError:
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-cache-dir',
        'OpenTTDLab==0.0.75',
    ])
    from openttdlab import download_from_bananas

stage = ROOT / 'browser_ai'
shutil.rmtree(stage, ignore_errors=True)
(stage / 'library').mkdir(parents=True, exist_ok=True)

manifest: list[tuple[str, str, int]] = []
with download_from_bananas('ai/534d504c') as files:
    for item in files:
        if len(item) == 5:
            content_id, filename, _license_name, _md5, get_data = item
        elif len(item) == 4:
            content_id, filename, _md5, get_data = item
        else:
            raise RuntimeError(f'Unexpected BaNaNaS item: {item!r}')
        content_id = str(content_id)
        filename = str(filename)
        with get_data() as chunks:
            data = b''.join(chunks)
        if not data:
            raise RuntimeError(f'Empty BaNaNaS payload: {content_id}')
        if content_id == 'ai/534d504c':
            target = stage / filename
        elif content_id.startswith(('ai-library/', 'ailibrary/')):
            target = stage / 'library' / filename
        elif content_id.startswith('ai/'):
            target = stage / filename
        else:
            raise RuntimeError(f'Unexpected AI dependency: {content_id}')
        target.write_bytes(data)
        manifest.append((content_id, target.relative_to(stage).as_posix(), len(data)))

if not any(cid == 'ai/534d504c' for cid, _, _ in manifest):
    raise SystemExit('SimpleAI was not staged')
if not any(cid.startswith(('ai-library/', 'ailibrary/')) for cid, _, _ in manifest):
    raise SystemExit('SimpleAI libraries were not staged')

# Old-API AIs need the official compatibility chain in the same native /ai path.
compat_src = ROOT / 'bin' / 'ai'
compat_files = sorted(compat_src.glob('compat_*.nut'))
if not compat_files:
    raise SystemExit('OpenTTD AI compatibility scripts are missing')
for source in compat_files:
    shutil.copy2(source, stage / source.name)

cmake = ROOT / 'CMakeLists.txt'
text = cmake.read_text(encoding='utf-8')
preload = '    target_link_libraries(WASM::WASM INTERFACE "--preload-file ${CMAKE_SOURCE_DIR}/browser_ai@/ai")\n'
if preload not in text:
    anchor = '    target_link_libraries(WASM::WASM INTERFACE "--preload-file ${CMAKE_BINARY_DIR}/lang/english.lng@/lang/english.lng")\n'
    if anchor not in text:
        raise SystemExit('Could not find Emscripten preload anchor')
    text = text.replace(anchor, anchor + preload, 1)
    cmake.write_text(text, encoding='utf-8')

# Keep OpenTTD's own defaults. More importantly, do not rewrite the settings
# selected by the player in New Game -> AI/Game Script Settings. The browser
# integration is responsible only for making the AI scripts available.
settings = ROOT / 'src' / 'table' / 'settings' / 'difficulty_settings.ini'
s = settings.read_text(encoding='utf-8')
max_block = s[s.index('var      = difficulty.max_no_competitors'):]
max_block = max_block[:max_block.index('[SDT_VAR]', 1)]
interval_block = s[s.index('var      = difficulty.competitors_interval'):]
interval_block = interval_block[:interval_block.index('[SDT_VAR]', 1)]
if 'def      = 0' not in max_block:
    raise SystemExit('Unexpected upstream max_no_competitors default')
if 'def      = 10' not in interval_block:
    raise SystemExit('Unexpected upstream competitors_interval default')

# The historical Yandex cleanup was written for an offline package without AI
# modules. It used to alter max_no_competitors during startup and cloud sync.
# Neutralize only those calls; the helper may remain in generated code unused.
legacy_cleanup = Path('ci/patch-yandex-runtime-cleanup.py')
if not legacy_cleanup.is_file():
    raise SystemExit('Legacy Yandex runtime-cleanup patch is missing')
cleanup = legacy_cleanup.read_text(encoding='utf-8')

startup_call = '                sanitizeYandexConfig();\n'
if cleanup.count(startup_call) != 1:
    raise SystemExit(f'Expected one startup AI sanitizer call, got {cleanup.count(startup_call)}')
cleanup = cleanup.replace(startup_call, '', 1)

read_wrapped = "return sanitizeOfflineConfig(FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' }));"
read_direct = "return FS.readFile(personalDir + '/openttd.cfg', { encoding: 'utf8' });"
if cleanup.count(read_wrapped) != 1:
    raise SystemExit('Could not find cloud config read sanitizer')
cleanup = cleanup.replace(read_wrapped, read_direct, 1)

empty_wrapped = "return sanitizeOfflineConfig('');"
if cleanup.count(empty_wrapped) != 1:
    raise SystemExit('Could not find empty cloud config sanitizer')
cleanup = cleanup.replace(empty_wrapped, "return '';", 1)

write_wrapped = 'FS.writeFile(configPath, sanitizeOfflineConfig(cloudConfig.config));'
write_direct = 'FS.writeFile(configPath, cloudConfig.config);'
if cleanup.count(write_wrapped) != 1:
    raise SystemExit('Could not find cloud config restore sanitizer')
cleanup = cleanup.replace(write_wrapped, write_direct, 1)

legacy_cleanup.write_text(cleanup, encoding='utf-8')

print('Static AI filesystem staged before TarScanner/AI::Initialize:', manifest)
print(f'Copied {len(compat_files)} official OpenTTD AI compatibility scripts.')
print('Player-selected AI count and competitors interval are preserved unchanged.')
