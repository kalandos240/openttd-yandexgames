#!/usr/bin/env python3
"""Prepare the optional OpenTTD add-on payload for the Playgama build.

The script deliberately avoids the legacy BaNaNaS TCP metadata protocol.
Source-built GRFs must already exist in --work-dir; remaining pinned releases
are downloaded over HTTPS, verified, compressed, and described by a manifest.
Nothing produced by this script enables a NewGRF automatically.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tarfile
import time
import urllib.request
from pathlib import Path

from extract_newgrf_archive import md5 as file_md5
from extract_newgrf_archive import main as extract_main

ROAD_HOG_URL = "https://bundles.openttdcoop.org/road-hog/releases/LATEST/road-hog-1.4.1.zip"
ROAD_HOG_GRF_MD5 = "5b42f9b677d76724cf5265c3bb337ae1"
GIST_URL = "https://github.com/UweDomaratius/GermanIndustries/releases/download/v0.21.10/german_industries.zip"
OGFX2_SETTINGS_URL = "https://github.com/OpenTTD/OpenGFX2/releases/download/v0.7/ogfx2_settings.grf"
OGFX2_CLASSIC_URL = "https://github.com/OpenTTD/OpenGFX2/releases/download/0.8.1/OpenGFX2_Classic-0.8.1.tar"
OGFX2_LICENSE_URLS = (
    "https://raw.githubusercontent.com/OpenTTD/OpenGFX2/0.8.1/LICENSE",
    "https://raw.githubusercontent.com/OpenTTD/OpenGFX2/0.8.1/LICENSE.md",
    "https://raw.githubusercontent.com/OpenTTD/OpenGFX2/0.8.1/COPYING",
)
USER_AGENT = "openttd-yandexgames-playgama-v6-packager/1.1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, target: Path, attempts: int = 5) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            print(f"Downloading {url} -> {target} (attempt {attempt}/{attempts})")
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
            if partial.stat().st_size <= 0:
                raise RuntimeError(f"Downloaded empty file from {url}")
            partial.replace(target)
            print(
                f"Downloaded {target.name}: {target.stat().st_size} bytes, "
                f"SHA256 {sha256(target)}"
            )
            return target
        except Exception as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"Failed to download {url}: {last_error}")


def extract_one_grf(archive: Path, output_dir: Path, expected_md5: str | None = None) -> Path:
    argv = ["extract_newgrf_archive.py", str(archive), str(output_dir)]
    if expected_md5:
        argv.append(expected_md5)
    code = extract_main(argv)
    if code != 0:
        raise RuntimeError(f"Could not extract GRF from {archive}")

    candidates = sorted(output_dir.rglob("*.grf"))
    if expected_md5:
        candidates = [
            p for p in candidates
            if file_md5(p).lower().startswith(expected_md5.lower())
        ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one selected GRF in {archive}; got {candidates}"
        )
    return candidates[0]


def copy_notice(search_root: Path, target: Path) -> bool:
    names = ("license", "copying", "readme", "credits")
    candidates = []
    for path in search_root.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.name.lower()
        if any(lowered.startswith(prefix) for prefix in names):
            candidates.append(path)
    if not candidates:
        return False
    candidates.sort(
        key=lambda p: (
            0 if p.name.lower().startswith(("license", "copying")) else 1,
            len(p.parts),
            p.name.lower(),
        )
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidates[0], target)
    return True


def deterministic_gzip(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as src, target.open("wb") as raw_out:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw_out, compresslevel=9, mtime=0
        ) as gz:
            shutil.copyfileobj(src, gz, length=1024 * 1024)


def verify_classic_tar(path: Path) -> None:
    if not tarfile.is_tarfile(path):
        raise RuntimeError(f"OpenGFX2 Classic release is not a readable TAR: {path}")
    with tarfile.open(path, "r:*") as archive:
        names = [member.name.lower() for member in archive.getmembers() if member.isfile()]
    if not any(name.endswith(".obg") for name in names):
        raise RuntimeError("OpenGFX2 Classic TAR contains no .obg descriptor")
    if not any(name.endswith(".grf") for name in names):
        raise RuntimeError("OpenGFX2 Classic TAR contains no .grf data")


def prepare_prebuilt(work: Path, downloads: Path, licenses: Path) -> dict:
    provenance: dict[str, dict] = {}

    road_zip = download(ROAD_HOG_URL, downloads / "road-hog-1.4.1.zip")
    road_dir = downloads / "road-hog-extracted"
    road = extract_one_grf(road_zip, road_dir, ROAD_HOG_GRF_MD5)
    road_target = work / "road-hog-1.4.1.grf"
    shutil.copyfile(road, road_target)
    copy_notice(road_dir, licenses / "road-hog-release-notice.txt")
    provenance["road-hog-1.4.1.grf"] = {
        "download_url": ROAD_HOG_URL,
        "download_sha256": sha256(road_zip),
        "binary_md5": file_md5(road_target),
    }

    gist_zip = download(GIST_URL, downloads / "gist-0.21.10.zip")
    gist_dir = downloads / "gist-extracted"
    gist = extract_one_grf(gist_zip, gist_dir)
    gist_target = work / "gist-0.21.10.grf"
    shutil.copyfile(gist, gist_target)
    copy_notice(gist_dir, licenses / "gist-release-notice.txt")
    provenance["gist-0.21.10.grf"] = {
        "download_url": GIST_URL,
        "download_sha256": sha256(gist_zip),
        "binary_md5": file_md5(gist_target),
    }

    settings = download(OGFX2_SETTINGS_URL, work / "ogfx2-settings-0.7.grf")
    provenance["ogfx2-settings-0.7.grf"] = {
        "download_url": OGFX2_SETTINGS_URL,
        "download_sha256": sha256(settings),
        "binary_md5": file_md5(settings),
    }

    classic = download(OGFX2_CLASSIC_URL, work / "OpenGFX2_Classic-0.8.1.tar")
    verify_classic_tar(classic)
    provenance["OpenGFX2_Classic-0.8.1.tar"] = {
        "download_url": OGFX2_CLASSIC_URL,
        "download_sha256": sha256(classic),
        "binary_md5": file_md5(classic),
    }

    for url in OGFX2_LICENSE_URLS:
        try:
            download(url, licenses / "OpenGFX2-upstream-license.txt", attempts=2)
            break
        except Exception as exc:
            print(f"OpenGFX2 license URL failed, trying next: {exc}")

    return provenance


def build_manifest(work: Path, addon_dir: Path, provenance: dict[str, dict]) -> dict:
    specs = [
        {
            "content_id": "newgrf/43411223",
            "name": "Iron Horse 4 (Trains)",
            "version": "4.29.0",
            "source_file": "iron-horse-4.29.0.grf",
            "install_filename": "iron-horse-4.29.0.grf",
            "type": "newgrf",
            "category": "trains",
            "license": "GPL-2.0",
            "source": "https://github.com/andythenorth/iron-horse/tree/ec0523c6f80459ec40cb4488e9a23e5aaa3705c3",
            "source_commit": "ec0523c6f80459ec40cb4488e9a23e5aaa3705c3",
            "built_from_source": True,
        },
        {
            "content_id": "newgrf/f1250009",
            "name": "FIRS Industries 5",
            "version": "5.2.0",
            "source_file": "firs-5.2.0.grf",
            "install_filename": "firs-5.2.0.grf",
            "type": "newgrf",
            "category": "industry",
            "conflict_group": "industry-set",
            "license": "GPL-2.0",
            "source": "https://github.com/andythenorth/firs/tree/8844b7da36e919690322dcd69ffd9977e4e9a9c4",
            "source_commit": "8844b7da36e919690322dcd69ffd9977e4e9a9c4",
            "built_from_source": True,
        },
        {
            "content_id": "newgrf/9787eafe",
            "name": "Road Hog (Buses, Trucks, Trams)",
            "version": "1.4.1",
            "source_file": "road-hog-1.4.1.grf",
            "install_filename": "road-hog-1.4.1.grf",
            "type": "newgrf",
            "category": "road-vehicles",
            "license": "GPL-2.0",
            "source": "https://bundles.openttdcoop.org/road-hog/releases/LATEST/",
            "built_from_source": False,
        },
        {
            "content_id": "newgrf/55440100",
            "name": "GIST - German Industries Set",
            "version": "0.21.10",
            "source_file": "gist-0.21.10.grf",
            "install_filename": "gist-0.21.10.grf",
            "type": "newgrf",
            "category": "industry",
            "conflict_group": "industry-set",
            "license": "GPL-2.0",
            "source": "https://github.com/UweDomaratius/GermanIndustries/tree/v0.21.10",
            "built_from_source": False,
        },
        {
            "content_id": "newgrf/474c0501",
            "name": "Early Vehicle Set",
            "version": "0.0.2",
            "source_file": "early-vehicle-set-0.0.2.grf",
            "install_filename": "early-vehicle-set-0.0.2.grf",
            "type": "newgrf",
            "category": "vehicles",
            "license": "GPL-2.0",
            "source": "https://github.com/DonaldDuck313/OpenTTD-NewGRFs/tree/ae1a35b127cf089bce697afee1bc7cb6a0608b2a/EarlyVehicleSet",
            "source_commit": "ae1a35b127cf089bce697afee1bc7cb6a0608b2a",
            "built_from_source": True,
        },
        {
            "content_id": "newgrf/4f475a01",
            "name": "OpenGFX2 Settings",
            "version": "0.7",
            "source_file": "ogfx2-settings-0.7.grf",
            "install_filename": "ogfx2-settings-0.7.grf",
            "type": "newgrf",
            "category": "graphics-settings",
            "license": "GPL-2.0",
            "source": "https://github.com/OpenTTD/OpenGFX2/tree/v0.7",
            "built_from_source": False,
        },
        {
            "content_id": "base-graphics/6f676678",
            "name": "OpenGFX2 Classic",
            "version": "0.8.1",
            "source_file": "OpenGFX2_Classic-0.8.1.tar",
            "install_filename": "OpenGFX2_Classic-0.8.1.tar",
            "type": "base-graphics",
            "category": "base-graphics",
            "license": "GPL-2.0-upstream",
            "source": "https://github.com/OpenTTD/OpenGFX2/tree/0.8.1",
            "built_from_source": False,
            "native_tar_scan": True,
        },
    ]

    items: list[dict] = []
    for spec in specs:
        source_file = spec["source_file"]
        source = work / source_file
        if not source.is_file() or source.stat().st_size <= 0:
            raise RuntimeError(f"Missing prepared add-on payload: {source}")
        packed = addon_dir / f"{source.name}.gz"
        deterministic_gzip(source, packed)
        row = {key: value for key, value in spec.items() if key != "source_file"}
        row.update(
            {
                "asset": f"addons/{packed.name}",
                "compression": "gzip",
                "packaged_bytes": packed.stat().st_size,
                "installed_bytes": source.stat().st_size,
                "md5": file_md5(source),
                "sha256": sha256(source),
                "packaged_sha256": sha256(packed),
                "enabled_by_default": False,
            }
        )
        if source_file in provenance:
            row["upstream_release"] = provenance[source_file]
        items.append(row)

    return {
        "manifest_version": "2026-08-18-v6.1",
        "enabled_by_default": False,
        "notes": {
            "industry_conflict": "FIRS Industries 5 and GIST are alternatives; enable at most one in a new game.",
            "newgrf_ui": "Main menu -> NewGRF Settings",
            "base_graphics_ui": "Game Options -> Base graphics set",
            "startup": "Bundled content is available locally; no add-on is activated automatically.",
            "hashes": "Source builds record exact source commits and output hashes; HTTPS releases record download and installed binary hashes.",
        },
        "total_packaged_bytes": sum(row["packaged_bytes"] for row in items),
        "total_installed_bytes": sum(row["installed_bytes"] for row in items),
        "items": items,
    }


def write_notices(work: Path) -> None:
    notice = work / "THIRD-PARTY-ADDONS.md"
    notice.write_text(
        "# Bundled optional OpenTTD content\n\n"
        "All content below is shipped locally for player choice. Nothing is enabled automatically.\n\n"
        "- Iron Horse 4.29.0 — GPL-2.0 — source commit `ec0523c6f80459ec40cb4488e9a23e5aaa3705c3`.\n"
        "- FIRS Industries 5.2.0 — GPL-2.0 — source commit `8844b7da36e919690322dcd69ffd9977e4e9a9c4`.\n"
        "- Road Hog 1.4.1 — GPL-2.0 — official openttdcoop release bundle.\n"
        "- GIST 0.21.10 — GPL-2.0 — upstream release `v0.21.10`.\n"
        "- Early Vehicle Set 0.0.2 — GPL-2.0 — historical source commit `ae1a35b127cf089bce697afee1bc7cb6a0608b2a`.\n"
        "- OpenGFX2 Settings 0.7 — GPL-2.0 upstream.\n"
        "- OpenGFX2 Classic 0.8.1 — GPL-2.0 upstream source.\n\n"
        "FIRS and GIST are alternative industry sets and should not be enabled together in the same new game.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-dir", default="dist-addons")
    args = parser.parse_args()

    work = Path(args.work_dir).resolve()
    downloads = work / "downloads"
    addon_dir = work / "addons"
    licenses = work / "licenses"
    addon_dir.mkdir(parents=True, exist_ok=True)
    licenses.mkdir(parents=True, exist_ok=True)

    provenance = prepare_prebuilt(work, downloads, licenses)
    manifest = build_manifest(work, addon_dir, provenance)
    (work / "OPENTTD-BUNDLED-ADDONS.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    write_notices(work)

    checksum_lines = []
    for path in sorted(addon_dir.iterdir()):
        if path.is_file():
            checksum_lines.append(f"{sha256(path)}  addons/{path.name}")
    (work / "ADDON-PACKAGE-SHA256SUMS.txt").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )

    print(json.dumps(manifest, indent=2))
    print(f"Optional packaged bytes: {manifest['total_packaged_bytes']}")
    print(f"Optional installed bytes: {manifest['total_installed_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
