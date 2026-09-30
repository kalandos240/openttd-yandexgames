#!/usr/bin/env python3
"""Convert the verified Yandex V29 package into the independent Playgama build."""
from pathlib import Path
import argparse
import re
import shutil

BRIDGE_URL = "https://bridge.playgama.com/v2/stable/playgama-bridge.js"
BRIDGE_TAG = f'<script src="{BRIDGE_URL}"></script>'
ADAPTER_TAG = '<script src="playgama-yandex-compat.js"></script>'

NOTICE = """OpenTTD Playgama build
======================
Base: verified Yandex V29 package (commit 646b534248c8984c5cac97fbdf5c63f14e5d09ed).
Platform SDK: Playgama Bridge v2 stable.

The V29 OpenTTD runtime, adaptive viewport, mobile/touch behavior, AI bundle,
localization and gameplay are preserved. Only the platform bootstrap is
replaced with the Playgama Bridge compatibility layer.

Interstitial ads use the existing safe gameplay interval and pause/resume hooks.
Cloud data is mapped through Bridge v2 storage. Global ranking uses the
companyrating leaderboard through Bridge v2 leaderboards.
Rewarded and banner ads are disabled because this port has no matching mechanic.
"""


def patch_index(html: str) -> str:
    yandex = '<script src="yandex-bootstrap.js"></script>'
    replacement = BRIDGE_TAG + ADAPTER_TAG
    if yandex in html:
        html = html.replace(yandex, replacement, 1)
    elif BRIDGE_URL not in html or 'playgama-yandex-compat.js' not in html:
        raise SystemExit("yandex-bootstrap.js insertion point is missing")
    return html


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", type=Path)
    ap.add_argument("--adapter", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    args = ap.parse_args()

    dist = args.dist.resolve()
    index = dist / "index.html"
    if not index.is_file():
        raise SystemExit("index.html must be in package root")

    html = patch_index(index.read_text(encoding="utf-8"))
    index.write_text(html, encoding="utf-8")

    shutil.copy2(args.adapter, dist / "playgama-yandex-compat.js")
    shutil.copy2(args.config, dist / "playgama-bridge-config.json")

    for obsolete in ("yandex-bootstrap.js", "YANDEX-INTEGRATION.txt"):
        path = dist / obsolete
        if path.exists():
            path.unlink()

    (dist / "PLAYGAMA-INTEGRATION.txt").write_text(NOTICE, encoding="utf-8")

    if BRIDGE_URL not in html:
        raise SystemExit("Playgama Bridge v2 bootstrap missing")
    if "/sdk.js" in html:
        raise SystemExit("Yandex SDK reference remains in index.html")

    total = sum(p.stat().st_size for p in dist.rglob("*") if p.is_file())
    if total >= 300_000_000:
        raise SystemExit(f"Playgama package exceeds 300 MB unpacked: {total}")

    bad = []
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(dist).as_posix()
        if " " in rel or any(ord(ch) > 127 for ch in rel):
            bad.append(rel)
    if bad:
        raise SystemExit(f"Invalid archive paths: {bad}")

    print(f"Playgama V1 package ready: {dist}")
    print(f"Unpacked bytes: {total}")


if __name__ == "__main__":
    main()
