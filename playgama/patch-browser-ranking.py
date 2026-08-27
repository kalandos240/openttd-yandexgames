#!/usr/bin/env python3
from pathlib import Path
import re


def append_language_strings(path: Path, block: str, marker: str) -> None:
    text = path.read_text(encoding='utf-8')
    if marker in text:
        return
    if not text.endswith('\n'):
        text += '\n'
    text += '\n# Browser ranking UI\n' + block.strip() + '\n'
    path.write_text(text, encoding='utf-8')


append_language_strings(
    Path('openttd/src/lang/english.txt'),
    '''
STR_BROWSER_RANKING_TITLE                                      :Company rankings
STR_BROWSER_RANKING_LOCAL                                      :Local ranking
STR_BROWSER_RANKING_GLOBAL                                     :Global ranking
STR_BROWSER_RANKING_EMPTY                                      :No records yet
STR_BROWSER_RANKING_LOADING                                    :Loading ranking...
STR_BROWSER_RANKING_UNAVAILABLE                                :Global ranking is temporarily unavailable
STR_BROWSER_RANKING_REFRESH                                    :Refresh
STR_BROWSER_RANKING_SIGN_IN                                    :Sign in to participate
STR_BROWSER_RANKING_CHEAT_NOTE                                 :Using cheats disables score tracking for the ranking
STR_BROWSER_RANKING_CHEAT_USED                                 :Cheats were used in this game — further score is not counted
''',
    'STR_BROWSER_RANKING_TITLE',
)
append_language_strings(
    Path('openttd/src/lang/russian.txt'),
    '''
STR_BROWSER_RANKING_TITLE                                      :Рейтинг компаний
STR_BROWSER_RANKING_LOCAL                                      :Локальный рейтинг
STR_BROWSER_RANKING_GLOBAL                                     :Глобальный рейтинг
STR_BROWSER_RANKING_EMPTY                                      :Рекордов пока нет
STR_BROWSER_RANKING_LOADING                                    :Загрузка рейтинга...
STR_BROWSER_RANKING_UNAVAILABLE                                :Глобальный рейтинг временно недоступен
STR_BROWSER_RANKING_REFRESH                                    :Обновить
STR_BROWSER_RANKING_SIGN_IN                                    :Войти для участия
STR_BROWSER_RANKING_CHEAT_NOTE                                 :Использование читов отключает учёт очков в рейтинге
STR_BROWSER_RANKING_CHEAT_USED                                 :В этой партии использованы читы — дальнейшие очки не учитываются
''',
    'STR_BROWSER_RANKING_TITLE',
)

path = Path('openttd/src/highscore_gui.cpp')
text = path.read_text(encoding='utf-8')

include_anchor = '#include "timer/timer_game_calendar.h"\n'
extra_includes = '''#include "cheat_type.h"

#include <fstream>
#include <sstream>

#ifdef __EMSCRIPTEN__
#\tinclude <emscripten.h>
#endif
'''
if '#include "cheat_type.h"' not in text:
    if include_anchor not in text:
        raise SystemExit('Could not find highscore include anchor')
    text = text.replace(include_anchor, include_anchor + extra_includes, 1)

helper_marker = 'BROWSER_RANKING_MAX_SCORE'
helper = r'''
static constexpr uint64_t BROWSER_RANKING_MAX_SCORE = (1ULL << 53) - 1;
static constexpr uint64_t BROWSER_RANKING_VALUE_MASK = (1ULL << 43) - 1;
static constexpr const char *BROWSER_LOCAL_RANKING_FILE = "/home/web_user/.openttd/local-ranking.tsv";
static constexpr const char *BROWSER_GLOBAL_RANKING_FILE = "/home/web_user/.openttd/global-ranking.tsv";

struct BrowserRankingEntry {
	uint32_t rank = 0;
	uint64_t score = 0;
	bool is_user = false;
	std::string name{};
};

struct BrowserRankingSnapshot {
	std::string status = "offline";
	bool authorized = false;
	std::vector<BrowserRankingEntry> entries{};
};

static bool BrowserRankingCheatsUsed()
{
	return _cheats.magic_bulldozer.been_used ||
			_cheats.switch_company.been_used ||
			_cheats.money.been_used ||
			_cheats.crossing_tunnels.been_used ||
			_cheats.no_jetcrash.been_used ||
			_cheats.change_date.been_used ||
			_cheats.setup_prod.been_used ||
			_cheats.edit_max_hl.been_used ||
			_cheats.station_rating.been_used;
}

/**
 * Browser ranking score layout (53 exact JavaScript integer bits):
 *
 *   bits 52..43: OpenTTD performance rating mapped 0..1000 -> 0..1023
 *   bits 42.. 0: positive company value, saturated at 2^43 - 1
 *
 * Performance is the primary ordering key: no amount of company value can
 * overtake a company with a higher performance bucket. Company value then
 * breaks ties without leaving the exact integer range supported by JS SDKs.
 * A perfect 1000 rating plus saturated value reaches Number.MAX_SAFE_INTEGER.
 */
static uint64_t BrowserRankingScore(const Company *c)
{
	if (c == nullptr) return 0;
	const int32_t raw_performance = c->num_valid_stat_ent > 0 ? c->old_economy[0].performance_history : c->cur_economy.performance_history;
	const uint64_t performance = static_cast<uint64_t>(std::clamp<int32_t>(raw_performance, 0, SCORE_MAX));
	const uint64_t performance_bits = performance * 1023ULL / SCORE_MAX;

	const int64_t raw_value = CalculateCompanyValue(c, true).base();
	const uint64_t value_bits = raw_value <= 0 ? 0 : std::min<uint64_t>(static_cast<uint64_t>(raw_value), BROWSER_RANKING_VALUE_MASK);
	return std::min<uint64_t>((performance_bits << 43) | value_bits, BROWSER_RANKING_MAX_SCORE);
}

static std::string FormatBrowserRankingScore(uint64_t score)
{
	std::string value = std::to_string(score);
	for (int pos = static_cast<int>(value.size()) - 3; pos > 0; pos -= 3) value.insert(static_cast<size_t>(pos), " ");
	return value;
}

static std::vector<std::string> SplitBrowserRankingLine(const std::string &line)
{
	std::vector<std::string> fields;
	std::stringstream stream(line);
	std::string field;
	while (std::getline(stream, field, '\t')) fields.push_back(field);
	return fields;
}

static BrowserRankingSnapshot LoadBrowserRankingSnapshot(bool global)
{
	BrowserRankingSnapshot result;
	if (!global) result.status = "ready";
	std::ifstream input(global ? BROWSER_GLOBAL_RANKING_FILE : BROWSER_LOCAL_RANKING_FILE);
	if (!input.good()) return result;

	std::string line;
	while (std::getline(input, line)) {
		auto fields = SplitBrowserRankingLine(line);
		if (fields.empty()) continue;
		if (global && fields[0] == "status" && fields.size() >= 2) {
			result.status = fields[1];
			continue;
		}
		if (global && fields[0] == "authorized" && fields.size() >= 2) {
			result.authorized = fields[1] == "1";
			continue;
		}
		if (fields[0] != "entry") continue;
		try {
			BrowserRankingEntry entry;
			if (global) {
				if (fields.size() < 5) continue;
				entry.rank = static_cast<uint32_t>(std::stoul(fields[1]));
				entry.score = std::min<uint64_t>(std::stoull(fields[2]), BROWSER_RANKING_MAX_SCORE);
				entry.is_user = fields[3] == "1";
				entry.name = fields[4];
			} else {
				if (fields.size() < 4) continue;
				entry.rank = static_cast<uint32_t>(std::stoul(fields[1]));
				entry.score = std::min<uint64_t>(std::stoull(fields[2]), BROWSER_RANKING_MAX_SCORE);
				entry.name = fields[3];
			}
			result.entries.push_back(std::move(entry));
		} catch (...) {
			/* Ignore a partially written or malformed row and keep the UI alive. */
		}
	}
	return result;
}

static void RequestBrowserGlobalRanking()
{
#ifdef __EMSCRIPTEN__
	EM_ASM({ window.OpenTTDGlobalRanking?.requestEntries?.(); });
#endif
}

static void RequestBrowserGlobalRankingAuth()
{
#ifdef __EMSCRIPTEN__
	/* This is called only from a deliberate click in the ranking window. */
	EM_ASM({ window.OpenTTDGlobalRanking?.requestAuth?.(); });
#endif
}

static void SubmitBrowserRankingScore()
{
#ifdef __EMSCRIPTEN__
	if (_game_mode == GM_MENU || _networking || !Company::IsValidID(_local_company)) return;
	if (BrowserRankingCheatsUsed()) return;
	const Company *c = Company::Get(_local_company);
	const uint64_t score = BrowserRankingScore(c);
	if (score == 0) return;
	const std::string score_text = std::to_string(score);
	const std::string company_name = GetString(STR_HIGHSCORE_NAME, c->index, c->index);
	EM_ASM({
		const score = UTF8ToString($0);
		const name = UTF8ToString($1);
		window.OpenTTDRankingCore?.submit?.(score, name, true);
	}, score_text.c_str(), company_name.c_str());
#endif
}

static bool BrowserPointInRect(const Point &pt, const Rect &r)
{
	return pt.x >= r.left && pt.x <= r.right && pt.y >= r.top && pt.y <= r.bottom;
}

'''
base_anchor = 'struct EndGameHighScoreBaseWindow : Window {'
if helper_marker not in text:
    if base_anchor not in text:
        raise SystemExit('Could not find highscore base window anchor')
    text = text.replace(base_anchor, helper + base_anchor, 1)

start = text.find('struct HighScoreWindow : EndGameHighScoreBaseWindow {')
end_marker = '\n};\n\nstatic constexpr std::initializer_list<NWidgetPart> _nested_highscore_widgets'
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate HighScoreWindow block')

replacement = r'''struct HighScoreWindow : EndGameHighScoreBaseWindow {
	bool game_paused_by_player = false; ///< True if the game was paused by the player when the highscore window was opened.
	bool global_view = false;
	uint refresh_elapsed_ms = 0;
	BrowserRankingSnapshot local_snapshot{};
	BrowserRankingSnapshot global_snapshot{};

	HighScoreWindow(WindowDesc &desc, int difficulty, int8_t ranking) : EndGameHighScoreBaseWindow(desc)
	{
		/* pause game to show the chart */
		this->game_paused_by_player = _pause_mode == PauseMode::Normal;
		if (!_networking && !this->game_paused_by_player) Command<CMD_PAUSE>::Post(PauseMode::Normal, true);

		/* Close all always on-top windows to get a clean screen */
		if (_game_mode != GM_MENU) HideVitalWindows();

		this->window_number = difficulty;
		this->background_img = SPR_HIGHSCORE_CHART_BEGIN;
		this->rank = ranking;
		SubmitBrowserRankingScore();
#ifdef __EMSCRIPTEN__
		EM_ASM({ window.OpenTTDRankingCore?.requestLocalSnapshot?.(); });
#endif
		this->ReloadRankingSnapshots();
		MarkWholeScreenDirty();
	}

	void ReloadRankingSnapshots()
	{
		this->local_snapshot = LoadBrowserRankingSnapshot(false);
		this->global_snapshot = LoadBrowserRankingSnapshot(true);
	}

	Rect LocalTabRect() const
	{
		Point pt = this->GetTopLeft(ScaleSpriteTrad(640), ScaleSpriteTrad(480));
		return Rect{pt.x + ScaleSpriteTrad(105), pt.y + ScaleSpriteTrad(96), pt.x + ScaleSpriteTrad(315), pt.y + ScaleSpriteTrad(122)};
	}

	Rect GlobalTabRect() const
	{
		Point pt = this->GetTopLeft(ScaleSpriteTrad(640), ScaleSpriteTrad(480));
		return Rect{pt.x + ScaleSpriteTrad(325), pt.y + ScaleSpriteTrad(96), pt.x + ScaleSpriteTrad(535), pt.y + ScaleSpriteTrad(122)};
	}

	Rect RefreshRect() const
	{
		Point pt = this->GetTopLeft(ScaleSpriteTrad(640), ScaleSpriteTrad(480));
		return Rect{pt.x + ScaleSpriteTrad(355), pt.y + ScaleSpriteTrad(431), pt.x + ScaleSpriteTrad(535), pt.y + ScaleSpriteTrad(457)};
	}

	Rect SignInRect() const
	{
		Point pt = this->GetTopLeft(ScaleSpriteTrad(640), ScaleSpriteTrad(480));
		return Rect{pt.x + ScaleSpriteTrad(105), pt.y + ScaleSpriteTrad(431), pt.x + ScaleSpriteTrad(345), pt.y + ScaleSpriteTrad(457)};
	}

	void Close([[maybe_unused]] int data = 0) override
	{
		if (_game_mode != GM_MENU && !_exit_game) ShowVitalWindows();
		if (!_networking && !this->game_paused_by_player) Command<CMD_PAUSE>::Post(PauseMode::Normal, false);
		this->EndGameHighScoreBaseWindow::Close();
	}

	void OnRealtimeTick(uint delta_ms) override
	{
		this->refresh_elapsed_ms += delta_ms;
		if (this->refresh_elapsed_ms < 500) return;
		this->refresh_elapsed_ms = 0;
		this->ReloadRankingSnapshots();
		this->SetDirty();
	}

	void OnClick(Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
	{
		if (widget == WID_H_BACKGROUND) {
			if (BrowserPointInRect(pt, this->LocalTabRect())) {
				this->global_view = false;
#ifdef __EMSCRIPTEN__
				EM_ASM({ window.OpenTTDRankingCore?.requestLocalSnapshot?.(); });
#endif
				this->ReloadRankingSnapshots();
				this->SetDirty();
				return;
			}
			if (BrowserPointInRect(pt, this->GlobalTabRect())) {
				this->global_view = true;
				RequestBrowserGlobalRanking();
				this->ReloadRankingSnapshots();
				this->SetDirty();
				return;
			}
			if (this->global_view && BrowserPointInRect(pt, this->RefreshRect())) {
				RequestBrowserGlobalRanking();
				return;
			}
			if (this->global_view && !this->global_snapshot.authorized && BrowserPointInRect(pt, this->SignInRect())) {
				RequestBrowserGlobalRankingAuth();
				return;
			}
		}
		this->EndGameHighScoreBaseWindow::OnClick(pt, widget, click_count);
	}

	void DrawRankingButton(const Rect &r, StringID text, bool lowered) const
	{
		DrawFrameRect(r, COLOUR_ORANGE, lowered ? FrameFlags{FrameFlag::Lowered} : FrameFlags{});
		DrawString(r.left + WidgetDimensions::scaled.frametext.left, r.right - WidgetDimensions::scaled.frametext.right,
				r.top + std::max(0, (r.Height() - GetCharacterHeight(FS_NORMAL)) / 2), text, TC_WHITE, SA_CENTER);
	}

	void OnPaint() override
	{
		this->SetupHighScoreEndWindow();
		Point pt = this->GetTopLeft(ScaleSpriteTrad(640), ScaleSpriteTrad(480));

		DrawStringMultiLine(pt.x + ScaleSpriteTrad(70), pt.x + ScaleSpriteTrad(570), pt.y + ScaleSpriteTrad(24), pt.y + ScaleSpriteTrad(82),
				STR_BROWSER_RANKING_TITLE, TC_FROMSTRING, SA_CENTER);

		this->DrawRankingButton(this->LocalTabRect(), STR_BROWSER_RANKING_LOCAL, !this->global_view);
		this->DrawRankingButton(this->GlobalTabRect(), STR_BROWSER_RANKING_GLOBAL, this->global_view);

		const BrowserRankingSnapshot &snapshot = this->global_view ? this->global_snapshot : this->local_snapshot;
		const int top = pt.y + ScaleSpriteTrad(139);
		const int row_height = ScaleSpriteTrad(27);

		if (this->global_view && (snapshot.status == "loading")) {
			DrawString(pt.x + ScaleSpriteTrad(70), pt.x + ScaleSpriteTrad(570), top + ScaleSpriteTrad(40), STR_BROWSER_RANKING_LOADING, TC_BLACK, SA_CENTER);
		} else if (this->global_view && (snapshot.status == "offline" || snapshot.status == "error")) {
			DrawString(pt.x + ScaleSpriteTrad(70), pt.x + ScaleSpriteTrad(570), top + ScaleSpriteTrad(40), STR_BROWSER_RANKING_UNAVAILABLE, TC_RED, SA_CENTER);
		} else if (snapshot.entries.empty()) {
			DrawString(pt.x + ScaleSpriteTrad(70), pt.x + ScaleSpriteTrad(570), top + ScaleSpriteTrad(40), STR_BROWSER_RANKING_EMPTY, TC_BLACK, SA_CENTER);
		} else {
			for (size_t i = 0; i < snapshot.entries.size() && i < 10; ++i) {
				const BrowserRankingEntry &entry = snapshot.entries[i];
				const int y = top + static_cast<int>(i) * row_height;
				const TextColour colour = entry.is_user ? TC_RED : TC_BLACK;
				DrawString(pt.x + ScaleSpriteTrad(55), pt.x + ScaleSpriteTrad(93), y,
						GetString(STR_JUST_RAW_STRING, fmt::format("{}.", entry.rank)), colour, SA_RIGHT);
				DrawString(pt.x + ScaleSpriteTrad(103), pt.x + ScaleSpriteTrad(405), y,
						GetString(STR_JUST_RAW_STRING, entry.name), colour);
				DrawString(pt.x + ScaleSpriteTrad(415), pt.x + ScaleSpriteTrad(585), y,
						GetString(STR_JUST_RAW_STRING, FormatBrowserRankingScore(entry.score)), colour, SA_RIGHT);
			}
		}

		const bool cheated = _game_mode != GM_MENU && BrowserRankingCheatsUsed();
		DrawString(pt.x + ScaleSpriteTrad(70), pt.x + ScaleSpriteTrad(570), pt.y + ScaleSpriteTrad(402),
				cheated ? STR_BROWSER_RANKING_CHEAT_USED : STR_BROWSER_RANKING_CHEAT_NOTE,
				cheated ? TC_RED : TC_BLACK, SA_CENTER);

		if (this->global_view) {
			if (!snapshot.authorized) this->DrawRankingButton(this->SignInRect(), STR_BROWSER_RANKING_SIGN_IN, false);
			this->DrawRankingButton(this->RefreshRect(), STR_BROWSER_RANKING_REFRESH, false);
		}
	}
};'''

text = text[:start] + replacement + text[end + len('\n};'):]

# Record the best clean score periodically. Once any cheat has been used, no
# further score from that game is sent to either local or global ranking.
timer_anchor = 'static const IntervalTimer<TimerGameCalendar> _check_end_game'
timer = r'''
static const IntervalTimer<TimerGameCalendar> _browser_ranking_update({TimerGameCalendar::YEAR, TimerGameCalendar::Priority::NONE}, [](auto)
{
	SubmitBrowserRankingScore();
});

'''
if '_browser_ranking_update' not in text:
    if timer_anchor not in text:
        raise SystemExit('Could not find end-game timer anchor')
    text = text.replace(timer_anchor, timer + timer_anchor, 1)

checks = (
    'BROWSER_RANKING_MAX_SCORE = (1ULL << 53) - 1',
    'performance * 1023ULL / SCORE_MAX',
    'CalculateCompanyValue(c, true).base()',
    'BrowserRankingCheatsUsed()',
    'OpenTTDRankingCore?.submit?.',
    'OpenTTDGlobalRanking?.requestEntries?.',
    'STR_BROWSER_RANKING_LOCAL',
    'STR_BROWSER_RANKING_GLOBAL',
    '_browser_ranking_update',
)
for check in checks:
    if check not in text:
        raise SystemExit(f'Missing browser ranking patch marker: {check!r}')

path.write_text(text, encoding='utf-8')
print('Native local/global ranking UI and 53-bit clean-score tracking patched.')
