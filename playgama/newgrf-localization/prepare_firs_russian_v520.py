#!/usr/bin/env python3
"""Pinned FIRS 5.2.0 Russian localization entry point.

Keeps version-specific terminology outside the generic strict generator.
"""
from __future__ import annotations

import prepare_firs_russian as base

# FIRS 5.2.0 still has a current cargo-unit string for cement while the
# historical Russian table does not carry that exact current section.
base.CARGOS["CEMENT"] = ("Цемент", "цемента")

if __name__ == "__main__":
    raise SystemExit(base.main())
