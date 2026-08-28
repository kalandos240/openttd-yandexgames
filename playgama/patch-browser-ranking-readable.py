#!/usr/bin/env python3
"""Replace the experimental packed 53-bit score with OpenTTD's 0..1000 rating."""
from pathlib import Path

path = Path('openttd/src/highscore_gui.cpp')
text = path.read_text(encoding='utf-8')

old_constants = '''static constexpr uint64_t BROWSER_RANKING_MAX_SCORE = (1ULL << 53) - 1;\nstatic constexpr uint64_t BROWSER_RANKING_VALUE_MASK = (1ULL << 43) - 1;'''
if old_constants in text:
    text = text.replace(old_constants, 'static constexpr uint64_t BROWSER_RANKING_MAX_SCORE = SCORE_MAX;', 1)
elif 'static constexpr uint64_t BROWSER_RANKING_MAX_SCORE = SCORE_MAX;' not in text:
    raise SystemExit('Could not locate browser ranking score constants')

start = text.find('/**\n * Browser ranking score layout (53 exact JavaScript integer bits):')
end = text.find('\nstatic std::string FormatBrowserRankingScore', start)
if start >= 0 and end >= 0:
    replacement = r'''/**
 * Browser ranking score is OpenTTD's native company performance rating.
 * Keeping the public value on the familiar 0..1000 scale makes both local and
 * platform leaderboards readable and prevents stale packed integers from
 * looking like impossible company scores.
 */
static uint64_t BrowserRankingScore(const Company *c)
{
	if (c == nullptr) return 0;
	const int32_t raw_performance = c->num_valid_stat_ent > 0 ? c->old_economy[0].performance_history : c->cur_economy.performance_history;
	return static_cast<uint64_t>(std::clamp<int32_t>(raw_performance, 0, SCORE_MAX));
}
'''
    text = text[:start] + replacement + text[end:]
elif 'return static_cast<uint64_t>(std::clamp<int32_t>(raw_performance, 0, SCORE_MAX));' not in text:
    raise SystemExit('Could not locate packed BrowserRankingScore implementation')

for forbidden in ('BROWSER_RANKING_VALUE_MASK', 'performance * 1023ULL / SCORE_MAX', 'CalculateCompanyValue(c, true).base()'):
    if forbidden in text:
        raise SystemExit(f'Packed ranking implementation survived: {forbidden}')
for required in ('BROWSER_RANKING_MAX_SCORE = SCORE_MAX', 'BrowserRankingCheatsUsed()', 'OpenTTDRankingCore?.submit?.'):
    if required not in text:
        raise SystemExit(f'Readable ranking marker missing: {required}')

path.write_text(text, encoding='utf-8')
print('Browser ranking now uses native 0..1000 OpenTTD performance scores.')
