#!/usr/bin/env python3
"""Extract one NewGRF from old/manual OpenTTD release archives.

Some historic NewGRF projects published ZIP files that contain a directory,
a nested TAR/ZIP, or metadata alongside the actual .grf. This helper walks
those layouts without relying on the OpenTTD BaNaNaS TCP content protocol.

Usage:
    python3 extract_newgrf_archive.py ARCHIVE OUTPUT_DIR [EXPECTED_MD5]

The selected .grf path is written to stdout. Diagnostics go to stderr so the
command is safe to use in shell command substitution.
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

MAX_DEPTH = 4
SUPPORTED_ARCHIVE_SUFFIXES = (
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.xz",
    ".txz",
    ".tar.bz2",
    ".tbz2",
)


def log(message: str) -> None:
    print(f"[newgrf-extract] {message}", file=sys.stderr)


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_archive(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in SUPPORTED_ARCHIVE_SUFFIXES)


def safe_destination(root: Path, member_name: str) -> Path:
    candidate = (root / member_name).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise RuntimeError(f"Archive member escapes destination: {member_name!r}") from exc
    return candidate


def extract_zip(path: Path, destination: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC failure in {path.name}: {bad}")
        for info in archive.infolist():
            target = safe_destination(destination, info.filename)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)


def extract_tar(path: Path, destination: Path) -> None:
    with tarfile.open(path, mode="r:*") as archive:
        for member in archive.getmembers():
            safe_destination(destination, member.name)
        archive.extractall(destination, filter="data")


def extract_archive(path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    lower = path.name.lower()
    if lower.endswith(".zip"):
        extract_zip(path, destination)
        return
    if tarfile.is_tarfile(path):
        extract_tar(path, destination)
        return
    raise RuntimeError(f"Unsupported or corrupt archive: {path}")


def find_grfs(root: Path) -> list[Path]:
    return sorted(
        (p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".grf"),
        key=lambda p: (len(p.parts), p.as_posix().lower()),
    )


def unpack_nested(root: Path, depth: int) -> None:
    """Walk nested archives once each, stopping as soon as a GRF is exposed."""
    if depth >= MAX_DEPTH or find_grfs(root):
        return

    archives = sorted(
        (p for p in root.iterdir() if p.is_file() and is_archive(p)),
        key=lambda p: p.name.lower(),
    )
    # Also support archives inside one or more ordinary wrapper directories.
    if not archives:
        archives = sorted(
            (p for p in root.rglob("*") if p.is_file() and is_archive(p)),
            key=lambda p: (len(p.parts), p.as_posix().lower()),
        )

    for index, archive in enumerate(archives):
        nested = root / f"__nested_{depth}_{index}_{archive.stem}"
        try:
            log(f"Extracting nested archive {archive.relative_to(root)}")
            extract_archive(archive, nested)
        except Exception as exc:  # Keep searching other nested payloads.
            log(f"Skipping unreadable nested archive {archive}: {exc}")
            continue

        if find_grfs(nested):
            return
        unpack_nested(nested, depth + 1)
        if find_grfs(nested):
            return


def select_grf(grfs: list[Path], expected_md5: str | None) -> Path:
    if expected_md5:
        needle = expected_md5.lower()
        for candidate in grfs:
            candidate_md5 = md5(candidate)
            log(f"Candidate {candidate}: MD5 {candidate_md5}")
            if candidate_md5 == needle or candidate_md5.startswith(needle):
                return candidate
        raise RuntimeError(
            f"No extracted GRF matches expected MD5 {expected_md5}; "
            f"found {len(grfs)} candidate(s)"
        )

    if len(grfs) == 1:
        log(f"Single GRF candidate: {grfs[0]}")
        return grfs[0]
    if not grfs:
        raise RuntimeError("Archive contains no .grf file")
    raise RuntimeError(
        "Archive contains multiple GRFs; provide EXPECTED_MD5 to select one: "
        + ", ".join(str(p) for p in grfs)
    )


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        print(__doc__.strip(), file=sys.stderr)
        return 2

    source = Path(argv[1]).resolve()
    destination = Path(argv[2]).resolve()
    expected_md5 = argv[3] if len(argv) == 4 else None

    if not source.is_file() or source.stat().st_size <= 0:
        raise RuntimeError(f"Missing/empty archive: {source}")

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)

    log(f"Opening {source.name} ({source.stat().st_size} bytes)")
    extract_archive(source, destination)
    grfs = find_grfs(destination)
    if not grfs:
        log("No direct GRF found; checking nested archives")
        unpack_nested(destination, 0)
        grfs = find_grfs(destination)

    selected = select_grf(grfs, expected_md5)
    log(f"Selected {selected} ({selected.stat().st_size} bytes, MD5 {md5(selected)})")
    print(selected)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        log(f"ERROR: {exc}")
        raise SystemExit(1)
