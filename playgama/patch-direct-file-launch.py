#!/usr/bin/env python3
"""Make final browser packages launch directly from file:// without network startup dependencies.

Hosted platform builds still use their SDKs. A local/direct-file launch deliberately
skips those SDK requests so the embedded OpenTTD runtime can boot immediately.
The same preparation step also installs the current AI preRun gate immediately
before openttd-runtime.js without changing the full tutorial/ranking package base.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PLAYGAMA_BRIDGE_URL = "https://bridge.playgama.com/v1/stable/playgama-bridge.js"
PLAYGAMA_BRIDGE_TAG = f'<script src="{PLAYGAMA_BRIDGE_URL}"></script>'
LOCAL_LOADER_NAME = "platform-bridge-loader.js"
LOCAL_LOADER_TAG = f'<script src="{LOCAL_LOADER_NAME}"></script>'
CONVERTER_MARKER = f'<!-- openttd-yandex-converter-marker: {PLAYGAMA_BRIDGE_TAG} -->'
AI_PRERUN_NAME = "openttd-ai-prerun.js"
AI_PRERUN_TAG = f'<script src="{AI_PRERUN_NAME}"></script>'
RUNTIME_TAG = '<script src="openttd-runtime.js"></script>'

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


def install_ai_prerun(dist: Path, html: str) -> str:
    source = Path(__file__).resolve().with_name(AI_PRERUN_NAME)
    if not source.is_file():
        raise SystemExit(f"Missing current AI preRun source: {source}")
    shutil.copy2(source, dist / AI_PRERUN_NAME)

    if AI_PRERUN_TAG not in html:
        if html.count(RUNTIME_TAG) != 1:
            raise SystemExit(f"Expected one openttd-runtime.js tag, found {html.count(RUNTIME_TAG)}")
        html = html.replace(RUNTIME_TAG, AI_PRERUN_TAG + RUNTIME_TAG, 1)
    if html.count(AI_PRERUN_TAG) != 1:
        raise SystemExit("AI preRun gate insertion is not unique")
    if html.index(AI_PRERUN_TAG) > html.index(RUNTIME_TAG):
        raise SystemExit("AI preRun gate must execute before openttd-runtime.js")
    return html


def prepare_playgama(dist: Path) -> None:
    index, html = read_index(dist)
    count = html.count(PLAYGAMA_BRIDGE_TAG)
    if count != 1:
        raise SystemExit(f"Expected one active Playgama Bridge tag, found {count}")

    # Keep the full-feature package intact; add only the current pre-main AI gate.
    html = install_ai_prerun(dist, html)
    html = html.replace(PLAYGAMA_BRIDGE_TAG, LOCAL_LOADER_TAG + "\n" + CONVERTER_MARKER, 1)
    index.write_text(html, encoding="utf-8")
    (dist / LOCAL_LOADER_NAME).write_text(LOADER_JS, encoding="utf-8")
    print("Prepared Playgama direct-file launch and pre-main SimpleAI gate")


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
    if AI_PRERUN_TAG not in html or not (dist / AI_PRERUN_NAME).is_file():
        raise SystemExit("AI preRun gate is missing from final Playgama package")
    if html.index(AI_PRERUN_TAG) > html.index(RUNTIME_TAG):
        raise SystemExit("AI preRun gate moved behind runtime in Playgama package")
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
    if AI_PRERUN_TAG not in final_html or not (dist / AI_PRERUN_NAME).is_file():
        raise SystemExit("AI preRun gate is missing from final Yandex package")
    if final_html.index(AI_PRERUN_TAG) > final_html.index(RUNTIME_TAG):
        raise SystemExit("AI preRun gate moved behind runtime in Yandex package")
    print("Finalized Yandex direct-file package: file:// skips /sdk.js; AI preRun retained")


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
