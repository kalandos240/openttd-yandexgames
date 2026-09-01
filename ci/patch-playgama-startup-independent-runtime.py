#!/usr/bin/env python3
from pathlib import Path
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('runtime', type=Path)
args = ap.parse_args()

p = args.runtime
raw = p.read_bytes()
old = b'window.yandexGamesSDKReady?Promise.race([window.yandexGamesSDKReady,new Promise((A=>setTimeout((()=>A(null)),3e3)))]).then(Q,Q):Q()}));'
new = b'window.__openttdPlatformStartupIndependent===true?Q():' + old

if raw.count(old) != 1:
    raise SystemExit(f'Expected exactly one Yandex startup gate, found {raw.count(old)}')
if b'__openttdPlatformStartupIndependent' in raw:
    raise SystemExit('Playgama startup-independent marker already exists')

before = len(raw)
raw = raw.replace(old, new, 1)
if len(raw) - before != 54:
    raise SystemExit(f'Unexpected Playgama runtime delta: {len(raw) - before}')
if raw.count(b'__openttdPlatformStartupIndependent') != 1:
    raise SystemExit('Could not add Playgama startup-independent marker exactly once')

p.write_bytes(raw)
print('Playgama startup-independent wrapper patch applied; native WASM remains untouched.')
