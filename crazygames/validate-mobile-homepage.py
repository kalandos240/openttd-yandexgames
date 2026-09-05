#!/usr/bin/env python3
"""Conservative CrazyGames mobile-homepage initial-transfer validator."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import PurePosixPath
from zipfile import ZipFile

LIMIT = 20_000_000


class Scripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        src = dict(attrs).get("src")
        if not src or src.startswith(("http://", "https://", "//")):
            return
        self.local.append(src.lstrip("./"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    args = parser.parse_args()

    with ZipFile(args.package) as zf:
        names = {PurePosixPath(i.filename).as_posix(): i for i in zf.infolist() if not i.is_dir()}
        html = zf.read("index.html").decode("utf-8")
        scripts = Scripts()
        scripts.feed(html)
        initial = ["index.html", *scripts.local, "openttd.wasm", "openttd.data"]
        initial = list(dict.fromkeys(initial))
        missing = [name for name in initial if name not in names]
        if missing:
            raise SystemExit(f"Missing initial files in package: {missing}")
        compressed = sum(names[name].compress_size for name in initial)
        raw = sum(names[name].file_size for name in initial)
        print("mobile_initial_files=" + ",".join(initial))
        print(f"mobile_initial_raw_bytes={raw}")
        print(f"mobile_initial_zip_deflate_bytes={compressed}")
        print(f"mobile_initial_headroom_bytes={LIMIT - compressed}")
        if compressed >= LIMIT:
            raise SystemExit(
                f"CrazyGames mobile-homepage conservative initial budget exceeded: "
                f"{compressed} >= {LIMIT} bytes"
            )


if __name__ == "__main__":
    main()
