#!/usr/bin/env python3
"""Make the Yandex V29 startup watchdog compatible with Playgama cloud restore.

Only TWO literal substitutions are permitted in the 73 MB Emscripten runtime.
Never regenerate, minify or otherwise alter the game runtime.
"""
from __future__ import annotations

import argparse
from pathlib import Path

WATCHDOG_BEFORE = b'setTimeout((function(){B("filesystem/cloud initialization exceeded 8000 ms")}),8e3)'
WATCHDOG_AFTER = b'setTimeout((function(){B("filesystem/cloud initialization exceeded 14000 ms")}),14e3)'
RESTORE_BEFORE = b'window.yandexRestoreOpenTTDCloud?Promise.race([window.yandexRestoreOpenTTDCloud(FS,personal_dir),new Promise((A=>setTimeout(A,2500)))]).then(A,A):A()'
RESTORE_AFTER = b'window.yandexRestoreOpenTTDCloud?Promise.race([window.yandexRestoreOpenTTDCloud(FS,personal_dir),new Promise((A=>setTimeout(A,8500)))]).then(A,A):A()'

# Cloud module's own deadline is 6500ms; it cannot write after the native
# restore's 8500ms outer limit. The 14000ms watchdog additionally includes
# the separate 3000ms SDK startup grace and IDBFS/compatibility hook work.
CLOUD_MODULE_BUDGET_MS = 6500
NATIVE_RESTORE_TIMEOUT_MS = 8500
NATIVE_STARTUP_WATCHDOG_MS = 14000
assert CLOUD_MODULE_BUDGET_MS < NATIVE_RESTORE_TIMEOUT_MS
assert NATIVE_RESTORE_TIMEOUT_MS + 3000 < NATIVE_STARTUP_WATCHDOG_MS


def replace_once(data: bytes, before: bytes, after: bytes) -> bytes:
    if data.count(before) != 1:
        raise SystemExit(f'Unexpected native runtime anchor: {before[:100]!r}; count={data.count(before)}')
    if data.count(after):
        raise SystemExit('Native runtime patch already present or duplicated')
    return data.replace(before, after, 1)


def expected_bytes(original: bytes) -> bytes:
    data = replace_once(original, WATCHDOG_BEFORE, WATCHDOG_AFTER)
    return replace_once(data, RESTORE_BEFORE, RESTORE_AFTER)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('dist', type=Path)
    ap.add_argument('--verify-original', type=Path, required=True)
    args = ap.parse_args()

    source_path = args.verify_original / 'openttd-runtime.js'
    target_path = args.dist / 'openttd-runtime.js'
    original = source_path.read_bytes()
    expected = expected_bytes(original)
    actual = target_path.read_bytes()
    if actual == original:
        target_path.write_bytes(expected)
        actual = target_path.read_bytes()
    if actual != expected:
        raise SystemExit('Unapproved change to native runtime: only two startup timeout changes are allowed')

    print('Exact V29 Emscripten startup patch PASS: restore 2500 -> 8500ms; watchdog 8000 -> 14000ms')


if __name__ == '__main__':
    main()
