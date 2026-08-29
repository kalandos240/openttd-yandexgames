#!/usr/bin/env python3
"""Turn the historical direct-file build into a platform-native split runtime.

The legacy pipeline intentionally used Emscripten SINGLE_FILE and --embed-file
so index.html could run from file:// with no server. Yandex Games and Playgama
serve ordinary same-origin files, so that mode is counterproductive: a large
Wasm binary becomes base64 inside JavaScript, increasing parse/decode and peak
memory cost on every cold browser profile.

In addition to preserving separate JS/Wasm/data files, install a small
post-link patch for Emscripten's preload-package transport. Some platform/CDN
responses can report the complete compressed transfer while keeping the XHR
request open. Emscripten waits for XHR.onload in that case and the game remains
stuck on "Downloading data" forever. The replacement uses Fetch streaming and
finishes as soon as the expected decoded package byte count has arrived.
"""
from __future__ import annotations

import argparse
from pathlib import Path


STREAM_HELPER = r'''#!/usr/bin/env python3
"""Harden Emscripten's external .data loader for game-platform CDNs."""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected one {label}, got {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('runtime_js', type=Path)
    args = ap.parse_args()

    path = args.runtime_js
    if not path.is_file():
        raise SystemExit(f'Generated Emscripten runtime is missing: {path}')
    text = path.read_text(encoding='utf-8')

    # Emscripten 3.1.57 emits an XHR preload-package loader. On game-platform
    # CDNs the compressed transfer can reach 100% while XHR.onload is delayed.
    # Fetch streams decoded bytes; once packageSize bytes have arrived the data
    # package is complete and we do not need to wait for the final close event.
    xhr_marker = ';return}var xhr=new XMLHttpRequest;'
    fetch_loader = r""";return}if(typeof fetch==="function"){const fetchOnce=function(url,cacheMode){const options={credentials:"same-origin",cache:cacheMode||"default"};let controller=null;let timeout=null;if(typeof AbortController!=="undefined"){controller=new AbortController;options.signal=controller.signal;timeout=setTimeout(function(){try{controller.abort()}catch(e){}},90000)}const clearFetchTimeout=function(){if(timeout!==null){clearTimeout(timeout);timeout=null}};return fetch(url,options).then(function(response){if(!response.ok&&response.status!==0)throw new Error(response.status+" "+response.statusText+" : "+url);if(!response.body||typeof response.body.getReader!=="function"){return response.arrayBuffer().then(function(buffer){clearFetchTimeout();if(buffer.byteLength<packageSize)throw new Error("OpenTTD data package ended early: "+buffer.byteLength+" / "+packageSize);return buffer.byteLength===packageSize?buffer:buffer.slice(0,packageSize)})}const reader=response.body.getReader();const chunks=[];let received=0;const assemble=function(limit){const size=Math.min(limit,received);const out=new Uint8Array(size);let offset=0;for(const chunk of chunks){if(offset>=size)break;const length=Math.min(chunk.byteLength,size-offset);out.set(chunk.subarray(0,length),offset);offset+=length}return out.buffer};const read=function(){return reader.read().then(function(part){if(part.done){clearFetchTimeout();if(received<packageSize)throw new Error("OpenTTD data package ended early: "+received+" / "+packageSize);return assemble(packageSize)}const chunk=part.value;chunks.push(chunk);received+=chunk.byteLength;if(Module["setStatus"])Module["setStatus"](`Downloading data... (${Math.min(received,packageSize)}/${packageSize})`);if(received>=packageSize){clearFetchTimeout();try{reader.cancel()}catch(e){}return assemble(packageSize)}return read()})};return read()}).catch(function(error){clearFetchTimeout();throw error})};if(Module["setStatus"])Module["setStatus"]("Downloading data...");fetchOnce(packageName,"default").catch(function(firstError){console.warn("OpenTTD data stream retry after failure",firstError);const sep=packageName.indexOf("?")===-1?"?":"&";return fetchOnce(packageName+sep+"ottd_retry="+Date.now(),"reload")}).then(function(buffer){if(Module["setStatus"])Module["setStatus"]("Preparing game data...");callback(buffer)}).catch(errback);return}var xhr=new XMLHttpRequest;"""
    text = replace_once(text, xhr_marker, fetch_loader, 'Emscripten XHR package-loader marker')

    # Keep exact dependency IDs for diagnostics. The stock monitor only exposes
    # a count, which made the observed "2 / 42" screen impossible to diagnose.
    add_marker = 'function addRunDependency(id){runDependencies++;Module["monitorRunDependencies"]?.(runDependencies)}function removeRunDependency(id){runDependencies--;Module["monitorRunDependencies"]?.(runDependencies);'
    tracked = 'var browserPendingRunDependencies=new Set;function addRunDependency(id){runDependencies++;if(id)browserPendingRunDependencies.add(id);Module["monitorRunDependencies"]?.(runDependencies)}function removeRunDependency(id){runDependencies--;if(id)browserPendingRunDependencies.delete(id);Module["monitorRunDependencies"]?.(runDependencies);'
    text = replace_once(text, add_marker, tracked, 'run-dependency tracker')

    diag_anchor = 'var dataURIPrefix="data:application/octet-stream;base64,";'
    diag = 'setTimeout(function(){if(typeof runDependencies!=="undefined"&&runDependencies>0&&typeof browserPendingRunDependencies!=="undefined")console.warn("OpenTTD startup still waiting for run dependencies:",runDependencies,Array.from(browserPendingRunDependencies))},15000);'
    text = replace_once(text, diag_anchor, diag + diag_anchor, 'startup dependency diagnostics anchor')

    for required in (
        'OpenTTD data stream retry after failure',
        'Preparing game data...',
        'OpenTTD startup still waiting for run dependencies:',
        'browserPendingRunDependencies',
    ):
        if required not in text:
            raise SystemExit(f'Generated runtime hardening marker is missing: {required}')

    path.write_text(text, encoding='utf-8')
    print('Hardened Emscripten .data streaming loader:', path)


if __name__ == '__main__':
    main()
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected one {label}, got {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('build_script', type=Path)
    args = ap.parse_args()

    path = args.build_script
    if not path.is_file():
        raise SystemExit(f'Legacy direct-file build script is missing: {path}')
    text = path.read_text(encoding='utf-8')

    text = replace_once(
        text,
        "s = s.replace('--preload-file', '--embed-file')\n",
        "# Platform delivery keeps --preload-file resources external.\n",
        'preload-to-embed mutation',
    )

    text = replace_once(
        text,
        "single_file = '    target_link_libraries(WASM::WASM INTERFACE \"-s SINGLE_FILE=1\")\\n'\n",
        "single_file = ''  # Platform build: never add SINGLE_FILE.\n",
        'SINGLE_FILE linker marker',
    )

    for old, label in (
        ("s = s.replace('cp openttd/build/openttd.wasm dist/\\n', '')\n", 'wasm output stripping'),
        ("s = s.replace('cp openttd/build/openttd.data dist/\\n', '')\n", 'data output stripping'),
        ("s = s.replace('cp openttd/build/openttd.js dist/\\n', '[ ! -f openttd/build/openttd.js ] || cp openttd/build/openttd.js dist/\\n')\n", 'JS copy mutation'),
    ):
        text = replace_once(text, old, '', label)

    text = replace_once(
        text,
        "test ! -e dist/openttd.wasm\\ntest ! -e dist/openttd.data",
        "test -s dist/openttd.js\\ntest -s dist/openttd.wasm\\ntest -s dist/openttd.data",
        'direct-file output assertions',
    )

    old_header = '# - all Emscripten resources are embedded, so index.html works via file://'
    if old_header in text:
        text = text.replace(
            old_header,
            '# - platform output keeps JS, WebAssembly and preload data as separate cacheable files',
            1,
        )

    # Have the generated build-final script patch openttd.js after linking and
    # before dist/ is staged.
    generator_anchor = "s = s.replace('openttd-yandexgames.zip', 'OpenTTD-YandexGames-Direct.zip')\np.write_text(s)\n"
    generator_injection = r'''runtime_dist_anchor = "mkdir -p dist\n"
runtime_patch_command = "python3 ci/patch-streaming-data-loader.py openttd/build/openttd.js\n"
if runtime_dist_anchor not in s:
    raise SystemExit('Could not find generated dist staging point')
s = s.replace(runtime_dist_anchor, runtime_patch_command + runtime_dist_anchor, 1)

'''
    text = replace_once(
        text,
        generator_anchor,
        generator_injection + generator_anchor,
        'generated runtime post-link insertion point',
    )

    for forbidden in (
        "s = s.replace('--preload-file', '--embed-file')",
        'SINGLE_FILE=1',
        "test ! -e dist/openttd.wasm",
        "test ! -e dist/openttd.data",
        "s = s.replace('cp openttd/build/openttd.wasm dist/",
        "s = s.replace('cp openttd/build/openttd.data dist/",
    ):
        if forbidden in text:
            raise SystemExit(f'Historical single-file behaviour remains: {forbidden}')

    helper = path.parent / 'patch-streaming-data-loader.py'
    compile(STREAM_HELPER, str(helper), 'exec')
    helper.write_text(STREAM_HELPER, encoding='utf-8')

    path.write_text(text, encoding='utf-8')
    print('Platform streaming runtime enabled:', path)
    print('Separate openttd.js, openttd.wasm and openttd.data will be preserved.')
    print('Fetch-stream .data completion patch installed:', helper)


if __name__ == '__main__':
    main()
