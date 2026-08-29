#!/usr/bin/env python3
"""Make final browser packages launch directly from file:// without network startup dependencies.

Hosted platform builds still use their SDKs. A local/direct-file launch deliberately
skips those SDK requests so the embedded OpenTTD runtime can boot immediately.
"""
from __future__ import annotations

import argparse
from pathlib import Path

PLAYGAMA_BRIDGE_URL = "https://bridge.playgama.com/v1/stable/playgama-bridge.js"
PLAYGAMA_BRIDGE_TAG = f'<script src="{PLAYGAMA_BRIDGE_URL}"></script>'
LOCAL_LOADER_NAME = "platform-bridge-loader.js"
LOCAL_LOADER_TAG = f'<script src="{LOCAL_LOADER_NAME}"></script>'
CONVERTER_MARKER = f'<!-- openttd-yandex-converter-marker: {PLAYGAMA_BRIDGE_TAG} -->'

LOADER_JS = r'''/* Hosted Playgama bridge loader; direct file:// launch stays completely offline. */
(() => {
  'use strict';
  if (location.protocol === 'file:') {
    window.__openttdDirectFileLaunch = true;
    return;
  }
  /* Parser-time insertion keeps the historical synchronous Bridge ordering for
     the hosted Playgama package without making the local package depend on CDN. */
  document.write('<script src="https://bridge.playgama.com/v1/stable/playgama-bridge.js"><\\/script>');
})();
'''


def read_index(dist: Path) -> tuple[Path, str]:
    index = dist / "index.html"
    if not index.is_file():
        raise SystemExit(f"Missing package index: {index}")
    return index, index.read_text(encoding="utf-8")


def prepare_playgama(dist: Path) -> None:
    index, html = read_index(dist)
    count = html.count(PLAYGAMA_BRIDGE_TAG)
    if count != 1:
        raise SystemExit(f"Expected one active Playgama Bridge tag, found {count}")
    html = html.replace(PLAYGAMA_BRIDGE_TAG, LOCAL_LOADER_TAG + "\n" + CONVERTER_MARKER, 1)
    index.write_text(html, encoding="utf-8")
    (dist / LOCAL_LOADER_NAME).write_text(LOADER_JS, encoding="utf-8")
    print("Prepared Playgama direct-file launch: hosted Bridge kept, file:// network dependency removed")


def finalize_playgama(dist: Path) -> None:
    index, html = read_index(dist)
    if CONVERTER_MARKER not in html:
        raise SystemExit("Missing temporary Yandex converter marker")
    html = html.replace(CONVERTER_MARKER, "", 1)
    index.write_text(html, encoding="utf-8")
    if PLAYGAMA_BRIDGE_URL in html:
        raise SystemExit("Active/commented Playgama CDN URL remains in final Playgama index")
    if LOCAL_LOADER_TAG not in html or not (dist / LOCAL_LOADER_NAME).is_file():
        raise SystemExit("Local Playgama platform loader is missing")
    print("Finalized Playgama direct-file package")


def finalize_yandex(dist: Path) -> None:
    index, html = read_index(dist)
    if LOCAL_LOADER_TAG in html:
        html = html.replace(LOCAL_LOADER_TAG, "", 1)
        index.write_text(html, encoding="utf-8")
    loader = dist / LOCAL_LOADER_NAME
    if loader.exists():
        loader.unlink()

    bootstrap = dist / "yandex-bootstrap.js"
    if not bootstrap.is_file():
        raise SystemExit("Missing yandex-bootstrap.js")
    text = bootstrap.read_text(encoding="utf-8")
    guard = "if (location.protocol === 'file:')"
    if guard not in text:
        anchor = "window.yandexGamesSDKReady = (async () => {\n"
        if text.count(anchor) != 1:
            raise SystemExit(f"Could not locate Yandex SDK promise anchor ({text.count(anchor)})")
        addition = (
            anchor
            + "  if (location.protocol === 'file:') {\n"
            + "    window.__openttdDirectFileLaunch = true;\n"
            + "    return null;\n"
            + "  }\n"
        )
        text = text.replace(anchor, addition, 1)
    bootstrap.write_text(text, encoding="utf-8")

    final_html = index.read_text(encoding="utf-8")
    if LOCAL_LOADER_NAME in final_html or PLAYGAMA_BRIDGE_URL in final_html:
        raise SystemExit("Playgama platform loader remains in Yandex index")
    if "if (location.protocol === 'file:')" not in bootstrap.read_text(encoding="utf-8"):
        raise SystemExit("Yandex file:// SDK bypass is missing")
    print("Finalized Yandex direct-file package: file:// skips /sdk.js")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare-playgama", "finalize-playgama", "finalize-yandex"))
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    if args.mode == "prepare-playgama":
        prepare_playgama(dist)
    elif args.mode == "finalize-playgama":
        finalize_playgama(dist)
    else:
        finalize_yandex(dist)


if __name__ == "__main__":
    main()
