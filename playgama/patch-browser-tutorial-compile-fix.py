#!/usr/bin/env python3
"""Compile-time includes required by the objective tutorial helpers."""
from pathlib import Path

path = Path('openttd/src/intro_gui.cpp')
text = path.read_text(encoding='utf-8')
anchor = '#include "company_base.h"\n'
include = '#include "company_func.h"\n'
if include not in text:
    if anchor not in text:
        raise SystemExit('company_base include anchor missing')
    text = text.replace(anchor, anchor + include, 1)
if include not in text:
    raise SystemExit('company_func include was not installed')
path.write_text(text, encoding='utf-8')
print('Objective tutorial company globals include installed.')
