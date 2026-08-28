#!/usr/bin/env python3
"""OpenTTD 15.3 compatibility fixes for the final browser tutorial patch."""
from pathlib import Path

p = Path("openttd/src/intro_gui.cpp")
s = p.read_text(encoding="utf-8")
old = "\t_settings_newgame.difficulty.max_loan = 300000; _settings_newgame.difficulty.vehicle_breakdowns = VehicleBreakdowns::Reduced;\n"
new = "\t_settings_newgame.difficulty.max_loan = 300000; _settings_newgame.difficulty.vehicle_breakdowns = 1;\n"
if s.count(old) != 1:
    raise SystemExit(f"Expected exactly one OpenTTD 15.3 vehicle-breakdown compatibility anchor, got {s.count(old)}")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("OpenTTD 15.3 tutorial difficulty compatibility applied (vehicle_breakdowns=1 / reduced).")
