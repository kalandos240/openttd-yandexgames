#!/usr/bin/env python3
"""Do not block native OpenTTD startup on Playgama's optional network SDK.

Yandex V29 has a platform SDK startup gate, originally capped at 3 seconds.
The local Playgama loader sets a flag before the OpenTTD runtime is executed.
This JS-only patch lets the runtime skip SDK waits; Playgama's SDK still
initializes asynchronously and gets a late GAME_READY notification.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from patch_v29_startup_timeout import expected_bytes as expected_timeout
from patch_v29_frame_upload import expected_bytes as expected_presenter

OLD = b'window.yandexGamesSDKReady?Promise.race([window.yandexGamesSDKReady,new Promise((A=>setTimeout((()=>A(null)),3e3)))]).then(Q,Q):Q()}));'
NEW = b'window.__openttdPlatformStartupIndependent===true?Q():' + OLD

def expected_bytes(original: bytes) -> bytes:
    if original.count(OLD) != 1 or NEW in original:
        raise SystemExit('Unsupported SDK startup gate in verified Yandex V29 runtime')
    return original.replace(OLD, NEW, 1)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('dist',type=Path)
    p.add_argument('--verify-original',type=Path,required=True)
    a=p.parse_args()
    raw=(a.verify_original/'openttd-runtime.js').read_bytes()
    patched=expected_bytes(expected_presenter(expected_timeout(raw)))
    path=a.dist/'openttd-runtime.js'
    current=path.read_bytes()
    before=expected_presenter(expected_timeout(raw))
    if current==before:
        path.write_bytes(patched)
        current=path.read_bytes()
    if current!=patched:
        raise SystemExit('Runtime contains unapproved edits beyond exact SDK startup bypass, timeouts and upload cap')
    print('Playgama SDK-independent native startup: VERIFIED; Yandex V29 game simulation unchanged')

if __name__=='__main__':
    main()
