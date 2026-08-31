#!/usr/bin/env python3
"""Patch bundled SimpleAI-14 to cache bridge-type availability per game date.

The Firefox profile of the 4096x4096 / 14-AI web build shows
CheckBridgeAvailability as the dominant steady-state WASM hotspot. SimpleAI's
road pathfinder constructs AIBridgeList_Length(length) for every explored node
and every candidate bridge length. That list depends only on bridge availability
and globally configured min/max bridge length, not on the candidate tile.

Cache only the selected bridge type inside each MyRoadPF instance for the current
game date and length. The actual AIBridge.BuildBridge TestMode feasibility check
still runs for every candidate tile, so routing and gameplay semantics are kept.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

ARCHIVE_KEY = "ai/534d504c-SimpleAI-14.tar"
ARCHIVE_FILENAME = "534d504c-SimpleAI-14.tar"
AI_PATH = "SimpleAI-14/pathfinder.nut"
MARKER = "Web port modification 2026-08-31: cache bridge-type availability per game date."
UPSTREAM_MD5 = "b3137bbd0c73641cf510ead06e36dab6"

CLASS_OLD = '''class MyRoadPF extends RoadPathFinder
{
\t\t_cost_level_crossing = null;
\t\t_goals = null;
}
'''
CLASS_NEW = '''class MyRoadPF extends RoadPathFinder
{
\t\t_cost_level_crossing = null;
\t\t_goals = null;
\t\t// Web port modification 2026-08-31: cache bridge-type availability per game date.
\t\t_bridge_type_cache = null;
\t\t_bridge_type_cache_date = null;
}
'''

INIT_OLD = '''\t::RoadPathFinder.InitializePath(sources, goals);
\t_goals = AIList();
'''
INIT_NEW = '''\t::RoadPathFinder.InitializePath(sources, goals);
\t_goals = AIList();
\t_bridge_type_cache = {};
\t_bridge_type_cache_date = AIDate.GetCurrentDate();
'''

LOOP_OLD = '''\tfor (local i = 2; i < this._max_bridge_length; i++) {
\t\tlocal bridge_list = AIBridgeList_Length(i + 1);
\t\tlocal target = cur_node + i * (cur_node - last_node);
\t\tif (!bridge_list.IsEmpty() && !_goals.HasItem(target) &&
\t\t\t\tAIBridge.BuildBridge(AIVehicle.VT_ROAD, bridge_list.Begin(), cur_node, target)) {
\t\t\ttiles.push([target, bridge_dir]);
\t\t}
\t}
'''
LOOP_NEW = '''\tlocal current_date = AIDate.GetCurrentDate();
\tif (_bridge_type_cache == null || _bridge_type_cache_date != current_date) {
\t\t_bridge_type_cache = {};
\t\t_bridge_type_cache_date = current_date;
\t}
\tfor (local i = 2; i < this._max_bridge_length; i++) {
\t\tlocal bridge_length = i + 1;
\t\tlocal bridge_type = -1;
\t\tif (_bridge_type_cache.rawin(bridge_length)) {
\t\t\tbridge_type = _bridge_type_cache[bridge_length];
\t\t} else {
\t\t\tlocal bridge_list = AIBridgeList_Length(bridge_length);
\t\t\tif (!bridge_list.IsEmpty()) bridge_type = bridge_list.Begin();
\t\t\t_bridge_type_cache[bridge_length] <- bridge_type;
\t\t}

\t\tlocal target = cur_node + i * (cur_node - last_node);
\t\tif (bridge_type >= 0 && !_goals.HasItem(target) &&
\t\t\t\tAIBridge.BuildBridge(AIVehicle.VT_ROAD, bridge_type, cur_node, target)) {
\t\t\ttiles.push([target, bridge_dir]);
\t\t}
\t}
'''


def repack_with_patch(raw: bytes) -> bytes:
    members: list[tuple[tarfile.TarInfo, bytes | None]] = []
    found = False
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        for member in tf.getmembers():
            payload = tf.extractfile(member).read() if member.isfile() else None
            if member.name == AI_PATH:
                if payload is None:
                    raise SystemExit(f"{AI_PATH} unexpectedly is not a file")
                source = payload.decode("utf-8")
                if MARKER in source:
                    return raw
                for name, old in (("class fields", CLASS_OLD), ("initializer", INIT_OLD), ("bridge loop", LOOP_OLD)):
                    if source.count(old) != 1:
                        raise SystemExit(f"Expected one SimpleAI {name} anchor, got {source.count(old)}")
                source = source.replace(CLASS_OLD, CLASS_NEW, 1)
                source = source.replace(INIT_OLD, INIT_NEW, 1)
                source = source.replace(LOOP_OLD, LOOP_NEW, 1)
                payload = source.encode("utf-8")
                member.size = len(payload)
                found = True
            members.append((member, payload))
    if not found:
        raise SystemExit(f"Could not find {AI_PATH} in bundled archive")

    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for member, payload in members:
            tf.addfile(member, io.BytesIO(payload) if payload is not None else None)
    patched = out.getvalue()

    with tarfile.open(fileobj=io.BytesIO(patched), mode="r:") as tf:
        names = tf.getnames()
        if AI_PATH not in names or "SimpleAI-14/license.txt" not in names:
            raise SystemExit("Patched SimpleAI archive lost required source/license files")
        source = tf.extractfile(AI_PATH).read().decode("utf-8")
    if MARKER not in source:
        raise SystemExit("SimpleAI bridge-cache marker missing after repack")
    if source.count("AIBridgeList_Length(bridge_length)") != 1:
        raise SystemExit("Expected exactly one cached bridge-list construction path")
    if "AIBridge.BuildBridge(AIVehicle.VT_ROAD, bridge_type, cur_node, target)" not in source:
        raise SystemExit("Per-tile bridge TestMode feasibility check was lost")
    return patched


def patch_bundle(path: Path) -> None:
    js = path.read_text(encoding="utf-8")
    archives_prefix = "window.__openttdClassicAIArchives = "
    manifest_prefix = "window.__openttdClassicAIManifest = "
    if js.count(archives_prefix) != 1 or js.count(manifest_prefix) != 1:
        raise SystemExit("Unexpected classic-AI bundle assignment layout")

    a0 = js.index(archives_prefix) + len(archives_prefix)
    a1 = js.index(";\n", a0)
    m0 = js.index(manifest_prefix, a1) + len(manifest_prefix)
    m1 = js.index(";", m0)
    archives = json.loads(js[a0:a1])
    manifest = json.loads(js[m0:m1])

    if ARCHIVE_KEY not in archives:
        raise SystemExit(f"Missing bundled {ARCHIVE_KEY}")
    original = base64.b64decode(archives[ARCHIVE_KEY], validate=True)
    original_md5 = hashlib.md5(original).hexdigest()
    if original_md5 != UPSTREAM_MD5 and MARKER not in tar_source(original):
        raise SystemExit(f"Unexpected SimpleAI-14 input MD5: {original_md5}")

    patched = repack_with_patch(original)
    archives[ARCHIVE_KEY] = base64.b64encode(patched).decode("ascii")

    matches = [item for item in manifest if item.get("filename") == ARCHIVE_FILENAME]
    if len(matches) != 1:
        raise SystemExit(f"Expected one SimpleAI manifest row, got {len(matches)}")
    row = matches[0]
    row["md5"] = hashlib.md5(patched).hexdigest()
    row["bytes"] = len(patched)
    row["web_patch"] = "bridge-type-cache-per-game-date-2026-08-31"
    row["upstream_md5"] = UPSTREAM_MD5

    encoded_archives = json.dumps(archives, separators=(",", ":"), sort_keys=True)
    encoded_manifest = json.dumps(manifest, separators=(",", ":"), sort_keys=True)
    path.write_text(js[:a0] + encoded_archives + ";\n" + manifest_prefix + encoded_manifest + ";" + js[m1 + 1 :], encoding="utf-8")

    final = path.read_text(encoding="utf-8")
    fa0 = final.index(archives_prefix) + len(archives_prefix)
    fa1 = final.index(";\n", fa0)
    final_archives = json.loads(final[fa0:fa1])
    final_tar = base64.b64decode(final_archives[ARCHIVE_KEY], validate=True)
    if MARKER not in tar_source(final_tar):
        raise SystemExit("Final embedded SimpleAI source did not retain bridge cache")

    print(f"SimpleAI bridge availability cache applied: {len(original)} -> {len(patched)} bytes, md5={row['md5']}.")


def tar_source(raw: bytes) -> str:
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        member = tf.extractfile(AI_PATH)
        if member is None:
            raise SystemExit(f"Missing {AI_PATH}")
        return member.read().decode("utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_root", type=Path)
    args = ap.parse_args()
    bundle = args.package_root / "openttd-classic-ai.js"
    if not bundle.is_file():
        raise SystemExit(f"Missing {bundle}")
    patch_bundle(bundle)


if __name__ == "__main__":
    main()
