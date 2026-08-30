#!/usr/bin/env python3
"""Pinned FIRS 5.2.0 Russian localization entry point.

Keeps version-specific terminology outside the generic strict generator.
"""
from __future__ import annotations

from pathlib import Path

import prepare_firs_russian as base

# FIRS 5.2.0 still has a current cargo-unit string for cement while the
# historical Russian table does not carry that exact current section.
base.CARGOS["CEMENT"] = ("Цемент", "цемента")

# The generic generator verifies field-for-field structure.  Russian NewGRF
# metadata legitimately adds gender/case grammar pragmas that English does not
# need.  Teach only the validation-side English schema about those legal
# metadata fields; keep the actual Russian pragmas intact in generated output.
_original_load = base.load


def _load_with_russian_grammar_schema(path: Path) -> dict:
    data = _original_load(path)
    if path.name == "english.toml" and "GLOBAL_PRAGMA" in data:
        data["GLOBAL_PRAGMA"] = dict(data["GLOBAL_PRAGMA"])
        data["GLOBAL_PRAGMA"]["gender"] = base.RU_PRAGMA["gender"]
        data["GLOBAL_PRAGMA"]["case"] = base.RU_PRAGMA["case"]
    return data


base.load = _load_with_russian_grammar_schema

if __name__ == "__main__":
    raise SystemExit(base.main())
