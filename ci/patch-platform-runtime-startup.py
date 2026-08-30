#!/usr/bin/env python3
"""Harden an already-linked OpenTTD Emscripten runtime for hosted game platforms.

This is deliberately a deterministic post-link patch so the exact production
ZIP can be repaired and browser-smoke-tested without a second native rebuild.
The same changes are platform-agnostic and must be applied to both Yandex Games
and Playgama packages.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected exactly one {label}, got {count}')
    return text.replace(old, new, 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('runtime_js', type=Path)
    args = ap.parse_args()

    path = args.runtime_js
    if not path.is_file():
        raise SystemExit(f'Runtime is missing: {path}')
    text = path.read_text(encoding='utf-8')

    # Emscripten 3.1.57 normally waits for XMLHttpRequest.onload. We reproduced
    # a hosted Chromium cold start where the full 46 MB decoded body had arrived
    # but onload never completed, leaving OpenTTD at (2 / 42). Fetch streaming
    # lets us finish as soon as the exact decoded package byte count is present.
    xhr_marker = ';return}var xhr=new XMLHttpRequest;'
    fetch_loader = r""";return}if(typeof fetch==="function"){const fetchOnce=function(url,cacheMode){const options={credentials:"same-origin",cache:cacheMode||"default"};let controller=null;let timeout=null;if(typeof AbortController!=="undefined"){controller=new AbortController;options.signal=controller.signal;timeout=setTimeout(function(){try{controller.abort()}catch(e){}},90000)}const clearFetchTimeout=function(){if(timeout!==null){clearTimeout(timeout);timeout=null}};return fetch(url,options).then(function(response){if(!response.ok&&response.status!==0)throw new Error(response.status+" "+response.statusText+" : "+url);if(!response.body||typeof response.body.getReader!=="function"){return response.arrayBuffer().then(function(buffer){clearFetchTimeout();if(buffer.byteLength<packageSize)throw new Error("OpenTTD data package ended early: "+buffer.byteLength+" / "+packageSize);return buffer.byteLength===packageSize?buffer:buffer.slice(0,packageSize)})}const reader=response.body.getReader();const chunks=[];let received=0;const assemble=function(limit){const size=Math.min(limit,received);const out=new Uint8Array(size);let offset=0;for(const chunk of chunks){if(offset>=size)break;const length=Math.min(chunk.byteLength,size-offset);out.set(chunk.subarray(0,length),offset);offset+=length}return out.buffer};const read=function(){return reader.read().then(function(part){if(part.done){clearFetchTimeout();if(received<packageSize)throw new Error("OpenTTD data package ended early: "+received+" / "+packageSize);return assemble(packageSize)}const chunk=part.value;chunks.push(chunk);received+=chunk.byteLength;if(Module["setStatus"])Module["setStatus"](`Downloading data... (${Math.min(received,packageSize)}/${packageSize})`);if(received>=packageSize){clearFetchTimeout();try{reader.cancel()}catch(e){}return assemble(packageSize)}return read()})};return read()}).catch(function(error){clearFetchTimeout();throw error})};if(Module["setStatus"])Module["setStatus"]("Downloading data...");fetchOnce(packageName,"default").catch(function(firstError){console.warn("OpenTTD data stream retry after failure",firstError);const sep=packageName.indexOf("?")===-1?"?":"&";return fetchOnce(packageName+sep+"ottd_retry="+Date.now(),"reload")}).then(function(buffer){if(Module["setStatus"])Module["setStatus"]("Preparing game data...");callback(buffer)}).catch(errback);return}var xhr=new XMLHttpRequest;"""
    text = replace_once(text, xhr_marker, fetch_loader, 'Emscripten XHR package-loader marker')

    # Do not let storage support decide whether the game can boot. A platform
    # can restrict IndexedDB/private mode while still being perfectly capable of
    # running OpenTTD with its in-memory filesystem and platform cloud adapter.
    mkdir_old = 'FS.mkdir(personal_dir);'
    mkdir_new = 'try{FS.mkdirTree(personal_dir)}catch(e){console.warn("OpenTTD personal directory initialization failed; continuing.",e)}'
    text = replace_once(text, mkdir_old, mkdir_new, 'personal-directory creation')

    mount_old = '}else{FS.mount(IDBFS,{},personal_dir)}Module.addRunDependency("syncfs");'
    mount_new = '}else{try{FS.mount(IDBFS,{},personal_dir)}catch(e){console.warn("OpenTTD IndexedDB mount failed; continuing without persistent storage.",e)}}Module.addRunDependency("syncfs");'
    text = replace_once(text, mount_old, mount_new, 'IndexedDB mount')

    # The existing 8 second watchdog handles an async sync that never calls
    # back. Also catch a synchronous FS.syncfs exception, which otherwise exits
    # the preRun callback before OpenTTD can continue.
    sync_open_old = 'FS.syncfs(true,function(err){'
    sync_open_new = 'try{FS.syncfs(true,function(err){'
    text = replace_once(text, sync_open_old, sync_open_new, 'initial syncfs opening')

    sync_close_old = '}else{finish_startup()}});let openttd_syncfs_busy=false;'
    sync_close_new = '}else{finish_startup()}})}catch(e){console.warn("OpenTTD initial persistence sync failed synchronously; continuing.",e);clearTimeout(browser_startup_watchdog);browser_release_startup_dependency("initial filesystem sync threw")}let openttd_syncfs_busy=false;'
    text = replace_once(text, sync_close_old, sync_close_new, 'initial syncfs closing')

    # Track run dependency IDs. If a hosted smoke ever regresses, the browser
    # console will show the exact dependency instead of only '(2 / 42)'.
    add_marker = 'function addRunDependency(id){runDependencies++;Module["monitorRunDependencies"]?.(runDependencies)}function removeRunDependency(id){runDependencies--;Module["monitorRunDependencies"]?.(runDependencies);'
    tracked = 'var browserPendingRunDependencies=new Set;function addRunDependency(id){runDependencies++;if(id)browserPendingRunDependencies.add(id);Module["monitorRunDependencies"]?.(runDependencies)}function removeRunDependency(id){runDependencies--;if(id)browserPendingRunDependencies.delete(id);Module["monitorRunDependencies"]?.(runDependencies);'
    text = replace_once(text, add_marker, tracked, 'run-dependency tracker')

    diag_anchor = 'var dataURIPrefix="data:application/octet-stream;base64,";'
    diag = 'setTimeout(function(){if(typeof runDependencies!=="undefined"&&runDependencies>0&&typeof browserPendingRunDependencies!=="undefined")console.warn("OpenTTD startup still waiting for run dependencies:",runDependencies,Array.from(browserPendingRunDependencies))},15000);'
    text = replace_once(text, diag_anchor, diag + diag_anchor, 'startup dependency diagnostics anchor')

    # Firefox profiler data from the hosted game shows the SDL2 software
    # framebuffer spending a large fraction of CPU time in a full HEAP32 copy
    # plus Canvas2D alpha premultiplication for every presentation. Simulation
    # and presentation share the browser main thread, so rendering every frame
    # makes x4/x8 fast-forward CPU-bound. Keep x1 untouched, but cap presentation
    # while fast-forward is active. Native OpenTTD continues to execute all game
    # ticks and input events; only redundant visual uploads are skipped.
    framebuffer_marker = 'var w=$0;var h=$1;var pixels=$2;if(!Module["SDL2"])Module["SDL2"]={};var SDL2=Module["SDL2"];'
    framebuffer_throttle = framebuffer_marker + (
        'var openttdSpeed=typeof window!=="undefined"?Number(window.__openttdGameSpeed||100):100;'
        'if(openttdSpeed>100){'
        'var openttdNow=typeof performance!=="undefined"&&performance.now?performance.now():Date.now();'
        'var openttdInterval=openttdSpeed>=800?66.6667:openttdSpeed>=400?50:33.3333;'
        'if(SDL2.__openttdLastPresent&&openttdNow-SDL2.__openttdLastPresent<openttdInterval)return;'
        'SDL2.__openttdLastPresent=openttdNow;'
        '}'
    )
    text = replace_once(text, framebuffer_marker, framebuffer_throttle, 'SDL2 software framebuffer presenter')

    for required in (
        'Preparing game data...',
        'OpenTTD data stream retry after failure',
        'OpenTTD IndexedDB mount failed; continuing without persistent storage.',
        'initial filesystem sync threw',
        'browserPendingRunDependencies',
        'OpenTTD startup still waiting for run dependencies:',
        '__openttdGameSpeed',
        '__openttdLastPresent',
        'openttdSpeed>=800?66.6667:openttdSpeed>=400?50:33.3333',
    ):
        if required not in text:
            raise SystemExit(f'Runtime hardening marker is missing: {required}')

    path.write_text(text, encoding='utf-8')
    print('Hosted platform startup/performance hardened:', path)


if __name__ == '__main__':
    main()
