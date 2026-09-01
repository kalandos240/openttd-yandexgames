#!/usr/bin/env python3
"""Rebase the proven Playgama-only JS delta onto a freshly linked Yandex runtime.

Do NOT replace only the embedded WASM in an Emscripten SINGLE_FILE runtime:
ASM_CONSTS addresses in the generated JavaScript are tied to that exact link.
This helper proves the current Yandex->Playgama runtime delta is exactly the
startup-independent insertion, then applies that same insertion to the complete
fresh optimized runtime (WASM + matching generated JS/ASM_CONSTS as one unit).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import re
import zipfile
from pathlib import Path

RUNTIME = "openttd-runtime.js"
WASM_RE = re.compile(br'(wasmBinaryFile="data:application/octet-stream;base64,)([A-Za-z0-9+/=]+)(")')
OLD = (
    b'window.yandexGamesSDKReady?Promise.race([window.yandexGamesSDKReady,'
    b'new Promise((A=>setTimeout((()=>A(null)),3e3)))]).then(Q,Q):Q()}));'
)
NEW = b'window.__openttdPlatformStartupIndependent===true?Q():' + OLD


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_zip(path: Path):
    with zipfile.ZipFile(path, "r") as zf:
        infos = zf.infolist()
        files = {i.filename: zf.read(i.filename) for i in infos if not i.is_dir()}
    if RUNTIME not in files:
        raise SystemExit(f"{path}: missing {RUNTIME}")
    return infos, files


def wasm(runtime: bytes) -> bytes:
    matches = list(WASM_RE.finditer(runtime))
    if len(matches) != 1:
        raise SystemExit(f"Expected one embedded WASM payload, found {len(matches)}")
    data = base64.b64decode(matches[0].group(2), validate=True)
    if not data.startswith(b"\x00asm"):
        raise SystemExit("Embedded payload is not WebAssembly")
    return data


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-yandex", type=Path, required=True)
    ap.add_argument("--baseline-playgama", type=Path, required=True)
    ap.add_argument("--optimized-yandex", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    _, yfiles = load_zip(args.baseline_yandex)
    pinfos, pfiles = load_zip(args.baseline_playgama)
    _, ofiles = load_zip(args.optimized_yandex)

    yr = yfiles[RUNTIME]
    pr = pfiles[RUNTIME]
    opt = ofiles[RUNTIME]

    # Prove the platform delta on the exact current baselines first.
    if yr.count(OLD) != 1 or yr.count(NEW) != 0:
        raise SystemExit("Unexpected baseline Yandex startup wrapper")
    if yr.replace(OLD, NEW, 1) != pr:
        raise SystemExit("Baseline Playgama runtime has unproven differences from baseline Yandex runtime")

    # Keep the newly linked optimized runtime intact and apply only the proven
    # 54-byte Playgama startup delta. This preserves matching ASM_CONSTS offsets.
    if opt.count(OLD) != 1 or opt.count(NEW) != 0:
        raise SystemExit("Optimized Yandex runtime has no unique proven Playgama insertion point")
    final_runtime = opt.replace(OLD, NEW, 1)
    if wasm(final_runtime) != wasm(opt):
        raise SystemExit("Playgama transformation unexpectedly changed embedded WASM")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.baseline_playgama, "r") as src, zipfile.ZipFile(args.output, "w") as dst:
        for info in src.infolist():
            data = b"" if info.is_dir() else src.read(info.filename)
            if info.filename == RUNTIME:
                data = final_runtime
            dst.writestr(info, data)

    _, ffiles = load_zip(args.output)
    before = {k: sha256(v) for k, v in pfiles.items() if k != RUNTIME}
    after = {k: sha256(v) for k, v in ffiles.items() if k != RUNTIME}
    if before != after:
        raise SystemExit("A non-runtime Playgama file changed")

    print(f"platform_delta_bytes={len(pr) - len(yr)}")
    print("platform_delta_verified_exact=true")
    print(f"preserved_non_runtime_files={len(before)}")
    print(f"optimized_runtime_sha256={sha256(final_runtime)}")
    print(f"optimized_wasm_sha256={sha256(wasm(final_runtime))}")
    print(f"optimized_wasm_bytes={len(wasm(final_runtime))}")


if __name__ == "__main__":
    main()
