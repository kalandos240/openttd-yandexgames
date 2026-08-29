#!/usr/bin/env python3
"""Make OpenTTD's zero competitor interval mean immediate startup in the web port.

OpenTTD 15.3 normally treats difficulty.competitors_interval == 0 as an early
return in the competitor timeout callback. The surrounding scheduler already
contains the intended zero-interval fast path: while the number of AIs is below
max_no_competitors it rearms the timeout for the next tick, then backs off to a
10-minute replacement check once all requested AIs exist.

Removing only the contradictory early return therefore makes a user-selected
0-minute interval deterministic and immediate without touching non-zero values.
"""
from pathlib import Path

path = Path('openttd/src/company_cmd.cpp')
if not path.is_file():
    raise SystemExit(f'OpenTTD source file is missing: {path}')

text = path.read_text(encoding='utf-8')
needle = '\tif (_settings_game.difficulty.competitors_interval == 0) return;\n'
replacement = (
    '\t/* Web port: zero means start requested AI competitors immediately.\n'
    '\t * CompanyGameLoop already rearms this timeout every tick until the\n'
    '\t * requested competitor count is reached, then backs off. */\n'
)

count = text.count(needle)
if count != 1:
    raise SystemExit(
        'Expected exactly one OpenTTD zero-interval AI early-return, '
        f'found {count}; upstream source changed'
    )

text = text.replace(needle, replacement, 1)
path.write_text(text, encoding='utf-8')

verify = path.read_text(encoding='utf-8')
if needle in verify or 'zero means start requested AI competitors immediately' not in verify:
    raise SystemExit('Could not apply zero-interval AI startup patch deterministically')

print('Patched OpenTTD: competitors_interval=0 now starts requested AIs immediately.')
