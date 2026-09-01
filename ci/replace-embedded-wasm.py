#!/usr/bin/env python3
"""Replace only the embedded WebAssembly payload inside an OpenTTD SINGLE_FILE ZIP.

This preserves the platform-specific JavaScript wrapper and every other package file.
It is intended for applying a verified native runtime optimization to the matching
Yandex/Playgama browser package without rebuilding platform integration layers.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import zipfile
from pathlib import Path

WASM_RE = re.compile(br'(wasmBinaryFile="data:application/octet-stream;base64,)([A-Za-z0-9+/=]+)(")')
RUNTIME = 'openttd-runtime.js'


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_wasm(runtime: bytes) -> tuple[re.Match[bytes], bytes]:
    matches = list(WASM_RE.finditer(runtime))
    if len(matches) != 1:
        raise SystemExit(f'Expected exactly one embedded WASM payload, found {len(matches)}')
    match = matches[0]
    try:
        wasm = base64.b64decode(match.group(2), validate=True)
    except Exception as exc:
        raise SystemExit(f'Embedded WASM base64 is invalid: {exc}') from exc
    if not wasm.startswith(b'\x00asm'):
        raise SystemExit('Decoded embedded payload is not a WebAssembly module')
    return match, wasm


def load_zip(path: Path) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]]:
    with zipfile.ZipFile(path, 'r') as zf:
        infos = zf.infolist()
        files = {info.filename: zf.read(info.filename) for info in infos if not info.is_dir()}
    if RUNTIME not in files:
        raise SystemExit(f'{path}: {RUNTIME} is missing')
    return infos, files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', type=Path, required=True, help='Platform ZIP whose JS wrapper/files must be preserved')
    ap.add_argument('--optimized', type=Path, required=True, help='ZIP containing the optimized embedded WASM')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()

    base_infos, base_files = load_zip(args.baseline)
    _, opt_files = load_zip(args.optimized)

    base_runtime = base_files[RUNTIME]
    opt_runtime = opt_files[RUNTIME]
    base_match, base_wasm = find_wasm(base_runtime)
    opt_match, opt_wasm = find_wasm(opt_runtime)

    if base_wasm == opt_wasm:
        raise SystemExit('Baseline and optimized WASM are byte-identical; refusing a no-op package')

    # Preserve every byte of the platform-specific JS wrapper outside the data URI.
    replacement_b64 = opt_match.group(2)
    new_runtime = (
        base_runtime[:base_match.start(2)]
        + replacement_b64
        + base_runtime[base_match.end(2):]
    )
    new_match, new_wasm = find_wasm(new_runtime)
    if new_wasm != opt_wasm:
        raise SystemExit('Final runtime does not contain the optimized WASM exactly')
    if base_runtime[:base_match.start(2)] != new_runtime[:new_match.start(2)]:
        raise SystemExit('Runtime wrapper prefix changed unexpectedly')
    if base_runtime[base_match.end(2):] != new_runtime[new_match.end(2):]:
        raise SystemExit('Runtime wrapper suffix changed unexpectedly')

    final_files = dict(base_files)
    final_files[RUNTIME] = new_runtime
    before_non_runtime = {k: sha256(v) for k, v in base_files.items() if k != RUNTIME}
    after_non_runtime = {k: sha256(v) for k, v in final_files.items() if k != RUNTIME}
    if before_non_runtime != after_non_runtime:
        raise SystemExit('A non-runtime file changed unexpectedly')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.baseline, 'r') as src, zipfile.ZipFile(args.output, 'w') as dst:
        for info in src.infolist():
            data = src.read(info.filename) if not info.is_dir() else b''
            if info.filename == RUNTIME:
                data = new_runtime
            dst.writestr(info, data)

    print(f'baseline_zip={args.baseline}')
    print(f'optimized_zip={args.optimized}')
    print(f'output_zip={args.output}')
    print(f'preserved_non_runtime_files={len(before_non_runtime)}')
    print(f'baseline_runtime_sha256={sha256(base_runtime)}')
    print(f'final_runtime_sha256={sha256(new_runtime)}')
    print(f'baseline_wasm_sha256={sha256(base_wasm)}')
    print(f'optimized_wasm_sha256={sha256(opt_wasm)}')
    print(f'wasm_bytes={len(opt_wasm)}')
    print('platform_wrapper_changed=false')


if __name__ == '__main__':
    main()
