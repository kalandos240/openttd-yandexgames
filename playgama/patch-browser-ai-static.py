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

# OpenTTD's company tick logic treats interval 0 as "start all configured
# competitors now", rather than waiting N minutes between AI starts.
settings = ROOT / 'src' / 'table' / 'settings' / 'difficulty_settings.ini'
s = settings.read_text(encoding='utf-8')
block_old = '''[SDT_VAR]\nvar      = difficulty.competitors_interval\ntype     = SLE_UINT16\nfrom     = SLV_AI_START_DATE\ndef      = 10\n'''
block_new = '''[SDT_VAR]\nvar      = difficulty.competitors_interval\ntype     = SLE_UINT16\nfrom     = SLV_AI_START_DATE\ndef      = 0\n'''
if block_old in s:
    s = s.replace(block_old, block_new, 1)
elif block_new not in s:
    raise SystemExit('Could not patch competitors_interval native default')
settings.write_text(s, encoding='utf-8')

print('Static AI filesystem staged before TarScanner/AI::Initialize:', manifest)
print(f'Copied {len(compat_files)} official OpenTTD AI compatibility scripts.')
