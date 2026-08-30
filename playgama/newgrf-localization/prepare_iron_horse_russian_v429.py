#!/usr/bin/env python3
"""Pinned Iron Horse 4.29.0 Russian localization entry point.

This tiny pinned wrapper also acts as a release-path trigger when shared browser
regression infrastructure changes; it does not alter the generated GRF policy.
"""
from __future__ import annotations

import prepare_iron_horse_russian as base

# Project/proper role names.  Yandex localization guidance allows proper and
# programmatic names to remain original.  Keeping them explicit here ensures
# that ordinary English gameplay text can never use a broad fallback.
base.TEXT.update({
    "Gronk!": "Gronk!",
    "InterCity Express": "InterCity Express",
    "Lolz": "Lolz",
})

if __name__ == "__main__":
    raise SystemExit(base.main())
