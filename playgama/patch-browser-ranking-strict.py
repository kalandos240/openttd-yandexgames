#!/usr/bin/env python3
"""Reject stale/packed browser ranking snapshots instead of clamping them."""
from pathlib import Path

p = Path('openttd/src/highscore_gui.cpp')
s = p.read_text(encoding='utf-8')

old = '''\tBrowserRankingSnapshot result;\n\tif (!global) result.status = "ready";\n\tstd::ifstream input(global ? BROWSER_GLOBAL_RANKING_FILE : BROWSER_LOCAL_RANKING_FILE);\n'''
new = '''\tBrowserRankingSnapshot result;\n\tif (!global) result.status = "ready";\n\tbool local_version_ok = global;\n\tstd::ifstream input(global ? BROWSER_GLOBAL_RANKING_FILE : BROWSER_LOCAL_RANKING_FILE);\n'''
if old not in s:
    raise SystemExit('ranking snapshot header anchor missing')
s = s.replace(old, new, 1)

old = '''\t\tif (fields.empty()) continue;\n\t\tif (global && fields[0] == "status" && fields.size() >= 2) {\n'''
new = '''\t\tif (fields.empty()) continue;\n\t\tif (!global && fields[0] == "version") {\n\t\t\tlocal_version_ok = fields.size() >= 2 && fields[1] == "3";\n\t\t\tif (!local_version_ok) result.entries.clear();\n\t\t\tcontinue;\n\t\t}\n\t\tif (global && fields[0] == "status" && fields.size() >= 2) {\n'''
if old not in s:
    raise SystemExit('ranking snapshot loop anchor missing')
s = s.replace(old, new, 1)

old = '''\t\tif (fields[0] != "entry") continue;\n\n\t\tBrowserRankingEntry entry;\n'''
new = '''\t\tif (fields[0] != "entry") continue;\n\t\tif (!global && !local_version_ok) continue;\n\n\t\tBrowserRankingEntry entry;\n'''
if old not in s:
    raise SystemExit('ranking entry anchor missing')
s = s.replace(old, new, 1)

clamp = '\t\t\tentry.score = std::min<uint64_t>(parsed_score, BROWSER_RANKING_MAX_SCORE);\n'
strict = '\t\t\tif (parsed_score == 0 || parsed_score > BROWSER_RANKING_MAX_SCORE) continue;\n\t\t\tentry.score = parsed_score;\n'
count = s.count(clamp)
if count != 2:
    raise SystemExit(f'expected two score clamps, got {count}')
s = s.replace(clamp, strict)

old = '''\t}\n\treturn result;\n}\n\nstatic void RequestBrowserGlobalRanking()\n'''
new = '''\t}\n\tif (!global && !local_version_ok) result.entries.clear();\n\treturn result;\n}\n\nstatic void RequestBrowserGlobalRanking()\n'''
if old not in s:
    raise SystemExit('ranking snapshot return anchor missing')
s = s.replace(old, new, 1)

for marker in ('fields[1] == "3"', 'parsed_score > BROWSER_RANKING_MAX_SCORE', 'local_version_ok'):
    if marker not in s:
        raise SystemExit(f'missing strict ranking marker: {marker}')
p.write_text(s, encoding='utf-8')
print('Strict ranking snapshot v3 enabled; stale packed/oversized scores are discarded.')
