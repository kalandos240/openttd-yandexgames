#!/usr/bin/env python3
"""Ensure the bundled SimpleAI is actually selected for browser free play."""
from pathlib import Path

path = Path('openttd/src/misc.cpp')
text = path.read_text(encoding='utf-8')

if '#include "ai/ai_config.hpp"' not in text:
    anchor = '#include "ai/ai.hpp"\n'
    if anchor not in text:
        raise SystemExit('AI include anchor missing in misc.cpp')
    text = text.replace(anchor, anchor + '#include "ai/ai_config.hpp"\n', 1)

anchor = '\tInitializeCompanies();\n\tAI::Initialize();\n\tGame::Initialize();\n'
replacement = r'''	InitializeCompanies();
	AI::Initialize();

	/* Browser editions ship a known-good AI in the virtual filesystem before
	 * main() starts. Merely setting max_no_competitors is not sufficient when
	 * every AI slot is still empty, so explicitly select the bundled AI for
	 * empty slots. Respect user-selected AIs and keep tutorial games AI-free. */
	if (_settings_game.difficulty.max_no_competitors > 0) {
		for (CompanyID company = CompanyID::Begin(); company < MAX_COMPANIES; ++company) {
			AIConfig *current = AIConfig::GetConfig(company, ScriptConfig::ScriptSettingSource::ForceCurrentGame);
			if (!current->HasScript()) current->Change("SimpleAI", -1, false);

			AIConfig *next_game = AIConfig::GetConfig(company, ScriptConfig::ScriptSettingSource::ForceNewGame);
			if (!next_game->HasScript()) next_game->Change("SimpleAI", -1, false);
		}
	}

	Game::Initialize();
'''
if anchor not in text:
    raise SystemExit('AI initialization anchor missing in misc.cpp')
text = text.replace(anchor, replacement, 1)

for marker in (
    'AIConfig::GetConfig(company, ScriptConfig::ScriptSettingSource::ForceCurrentGame)',
    'current->Change("SimpleAI", -1, false)',
    '_settings_game.difficulty.max_no_competitors > 0',
):
    if marker not in text:
        raise SystemExit(f'Browser AI marker missing: {marker}')

path.write_text(text, encoding='utf-8')
print('Browser free play now assigns bundled SimpleAI to empty competitor slots after AI scanning.')
