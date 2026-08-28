#!/usr/bin/env python3
"""Replace the old 53-bit browser leaderboard score with OpenTTD's native rating.

The old score packed the 0..1000 performance rating into the high bits of a
53-bit integer and company value into the low bits. That produced huge opaque
numbers such as 2 000 000 000 000+ in the player-facing table. The leaderboard
now uses the same company performance rating OpenTTD already calculates:
strictly 0..1000, directly understandable and comparable.
"""
from pathlib import Path
import re


highscore = Path("openttd/src/highscore_gui.cpp")
text = highscore.read_text(encoding="utf-8")

old_constants = '''static constexpr uint64_t BROWSER_RANKING_MAX_SCORE = (1ULL << 53) - 1;
static constexpr uint64_t BROWSER_RANKING_VALUE_MASK = (1ULL << 43) - 1;
'''
new_constants = '''static constexpr uint64_t BROWSER_RANKING_MAX_SCORE = SCORE_MAX;
'''
if new_constants not in text:
    if text.count(old_constants) != 1:
        raise SystemExit(f"Could not find old 53-bit ranking constants: {text.count(old_constants)}")
    text = text.replace(old_constants, new_constants, 1)

score_pattern = re.compile(
    r'/\*\*\n \* Browser ranking score layout \(53 exact JavaScript integer bits\):.*?\nstatic uint64_t BrowserRankingScore\(const Company \*c\)\n\{.*?\n\}',
    re.S,
)
new_score = '''/**
 * Browser ranking score is OpenTTD's own company performance rating.
 *
 * OpenTTD already combines the important management dimensions into this
 * 0..1000 score. Keeping that value directly makes the leaderboard readable,
 * avoids artificial 53-bit numbers, and keeps the same metric in both browser
 * platforms and the native company-performance UI.
 */
static uint64_t BrowserRankingScore(const Company *c)
{
\tif (c == nullptr) return 0;
\tconst int32_t raw_performance = c->num_valid_stat_ent > 0 ? c->old_economy[0].performance_history : c->cur_economy.performance_history;
\treturn static_cast<uint64_t>(std::clamp<int32_t>(raw_performance, 0, SCORE_MAX));
}'''
text, count = score_pattern.subn(new_score, text, count=1)
if count != 1 and new_score not in text:
    raise SystemExit(f"Could not replace old 53-bit BrowserRankingScore: {count}")

for forbidden in (
    "BROWSER_RANKING_VALUE_MASK",
    "performance * 1023ULL / SCORE_MAX",
    "CalculateCompanyValue(c, true).base()",
):
    if forbidden in text:
        raise SystemExit(f"Legacy ranking formula survived: {forbidden}")
for required in (
    "BROWSER_RANKING_MAX_SCORE = SCORE_MAX",
    "std::clamp<int32_t>(raw_performance, 0, SCORE_MAX)",
):
    if required not in text:
        raise SystemExit(f"Missing bounded ranking marker: {required}")

highscore.write_text(text, encoding="utf-8")

for path, old, new in (
    (
        Path("openttd/src/lang/english.txt"),
        "STR_BROWSER_RANKING_CHEAT_NOTE                                 :Using cheats disables score tracking for the ranking",
        "STR_BROWSER_RANKING_CHEAT_NOTE                                 :Score = OpenTTD company performance rating (0-1000). Using cheats disables score tracking",
    ),
    (
        Path("openttd/src/lang/russian.txt"),
        "STR_BROWSER_RANKING_CHEAT_NOTE                                 :Использование читов отключает учёт очков в рейтинге",
        "STR_BROWSER_RANKING_CHEAT_NOTE                                 :Очки = рейтинг эффективности компании OpenTTD (0-1000). Читы отключают учёт результата",
    ),
):
    lang = path.read_text(encoding="utf-8")
    if new not in lang:
        if lang.count(old) != 1:
            raise SystemExit(f"Could not update ranking explanation in {path}")
        lang = lang.replace(old, new, 1)
        path.write_text(lang, encoding="utf-8")

print("Browser leaderboard score simplified to native OpenTTD performance rating 0..1000.")
