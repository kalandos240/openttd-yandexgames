#!/usr/bin/env python3
"""Make browser AIs part of the OpenTTD runtime filesystem before AI scanning."""
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

# These compatibility scripts are consumed by old-API AIs through the same
# native /ai search path. Copy the official OpenTTD 15.3 files, not a JS clone.
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

settings = ROOT / 'src' / 'table' / 'settings' / 'difficulty_settings.ini'
s = settings.read_text(encoding='utf-8')

# Fix the actual native new-game defaults instead of byte-replacing the built
# JavaScript afterwards. Three competitors are enabled in normal free play.
max_old = '''[SDT_VAR]\nvar      = difficulty.max_no_competitors\ntype     = SLE_UINT8\nfrom     = SLV_97\ndef      = 0\n'''
max_new = '''[SDT_VAR]\nvar      = difficulty.max_no_competitors\ntype     = SLE_UINT8\nfrom     = SLV_97\ndef      = 3\n'''
if max_old in s:
    s = s.replace(max_old, max_new, 1)
elif max_new not in s:
    raise SystemExit('Could not patch max_no_competitors native default')

# OpenTTD company_cmd.cpp treats interval 0 as a special immediate-fill mode:
# it posts CCA_NEW_AI until max_no_competitors has been reached.
interval_old = '''[SDT_VAR]\nvar      = difficulty.competitors_interval\ntype     = SLE_UINT16\nfrom     = SLV_AI_START_DATE\ndef      = 10\n'''
interval_new = '''[SDT_VAR]\nvar      = difficulty.competitors_interval\ntype     = SLE_UINT16\nfrom     = SLV_AI_START_DATE\ndef      = 0\n'''
if interval_old in s:
    s = s.replace(interval_old, interval_new, 1)
elif interval_new not in s:
    raise SystemExit('Could not patch competitors_interval native default')
settings.write_text(s, encoding='utf-8')

print('Static AI filesystem staged before TarScanner/AI::Initialize:', manifest)
print(f'Copied {len(compat_files)} official OpenTTD AI compatibility scripts.')
print('Native free-play defaults: 3 competitors, immediate-fill interval 0.')
