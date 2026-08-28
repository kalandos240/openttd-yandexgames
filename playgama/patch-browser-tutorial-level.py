#!/usr/bin/env python3
"""Upgrade the browser tutorial into an interactive native training level.

Runs after patch-browser-tutorial.py and patch-browser-tutorial-toolbar.py. The
training UI uses OpenTTD's own widgets, sprites and translations: no HTML
coach-marks and no platform branding are exposed to the player.
"""
from pathlib import Path


def append_strings(path: Path, block: str, marker: str) -> None:
    text = path.read_text(encoding='utf-8')
    if marker in text:
        return
    if not text.endswith('\n'):
        text += '\n'
    text += '\n# Browser interactive training level and button guide\n' + block.strip() + '\n'
    path.write_text(text, encoding='utf-8')


append_strings(
    Path('openttd/src/lang/english.txt'),
    '''
STR_BROWSER_TUTORIAL_START_LEVEL                               :Start training level
STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP                       :Start a small dedicated practice game with step-by-step guidance
STR_BROWSER_BUTTON_GUIDE_MENU                                  :Button guide
STR_BROWSER_BUTTON_GUIDE_TOOLTIP                               :Open an illustrated guide to the main menu and in-game toolbar buttons
STR_BROWSER_TUTORIAL_COACH_CAPTION                             :Training level
STR_BROWSER_TUTORIAL_COACH_HINT                                :Follow the yellow highlight and the arrow. Perform the action in the real game, then press Next.
STR_BROWSER_TUTORIAL_FINISH                                    :Finish
STR_BROWSER_TUTORIAL_LEVEL_01                                  :1/16 — Camera and zoom{}This is a real practice map. Hold the right mouse button and drag to move the camera. Use the wheel or the highlighted zoom buttons to change scale. Look around before building.
STR_BROWSER_TUTORIAL_LEVEL_02                                  :2/16 — Pause and game speed{}Pause while planning expensive construction. Fast-forward is useful when you are waiting for vehicles, but return to normal speed before making precise changes.
STR_BROWSER_TUTORIAL_LEVEL_03                                  :3/16 — Map and towns{}Open the map and town tools. Towns generate passengers and mail. A station only serves buildings inside its catchment area, so location matters.
STR_BROWSER_TUTORIAL_LEVEL_04                                  :4/16 — Road construction{}Open the highlighted road construction button. Roads are the easiest first network: they are cheap, flexible and ideal for learning stations, depots and orders.
STR_BROWSER_TUTORIAL_LEVEL_05                                  :5/16 — Draw a road{}Use Autoroad in the road toolbar. Drag between two nearby towns. Build short clean connections first; bridges and tunnels can solve obstacles later.
STR_BROWSER_TUTORIAL_LEVEL_06                                  :6/16 — Bus stations{}Place a bus station in each town. Watch the station coverage highlight: town buildings inside that area can supply and accept passengers.
STR_BROWSER_TUTORIAL_LEVEL_07                                  :7/16 — Depot{}Build a road vehicle depot connected to your road. Depots are where road vehicles are purchased, replaced and serviced.
STR_BROWSER_TUTORIAL_LEVEL_08                                  :8/16 — Buy a vehicle{}Open the road-vehicle list or your depot and buy a bus. Vehicle windows show status, age, profit, reliability and controls for starting or stopping service.
STR_BROWSER_TUTORIAL_LEVEL_09                                  :9/16 — Orders{}Open the bus Orders window and add both stations. Orders define the route. Vehicles repeat the list automatically; full-load and transfer rules are optional advanced tools.
STR_BROWSER_TUTORIAL_LEVEL_10                                  :10/16 — Finances{}Open company finances. Income is earned when cargo reaches a useful destination. Track construction, running costs, loan interest and yearly profit before expanding.
STR_BROWSER_TUTORIAL_LEVEL_11                                  :11/16 — Railways and signals{}Trains carry large volumes efficiently. Build track, stations and a depot, then use signals to let several trains share a network safely. Start with a simple point-to-point line.
STR_BROWSER_TUTORIAL_LEVEL_12                                  :12/16 — Industries and cargo{}Industries produce and accept specific cargo. Use the industry directory and map to find useful chains, then connect producer to consumer with stations and suitable vehicles.
STR_BROWSER_TUTORIAL_LEVEL_13                                  :13/16 — Ships and aircraft{}Water and air transport cover long distances. Docks need water access; airports require large clear areas. These vehicles are expensive, so confirm demand before buying them.
STR_BROWSER_TUTORIAL_LEVEL_14                                  :14/16 — Terrain, bridges and tunnels{}Landscaping can level difficult ground, but it costs money and affects local authorities. Bridges and tunnels are often cheaper than reshaping a whole route.
STR_BROWSER_TUTORIAL_LEVEL_15                                  :15/16 — Company rating{}Graphs and company information help measure performance. The local and global company rankings use your best legitimate result. If any cheat is used, further score from that game is not counted.
STR_BROWSER_TUTORIAL_LEVEL_16                                  :16/16 — Save, settings and help{}Save important games, tune settings and use Help → Tutorial or Help → Button guide whenever you need a reminder. You now have the full core loop: demand → infrastructure → vehicles → orders → delivery → profit → expansion.
STR_BROWSER_MANUAL_CAPTION                                     :Illustrated button guide
STR_BROWSER_MANUAL_MAIN_MENU                                   :Main menu buttons
STR_BROWSER_MANUAL_TOOLBAR                                     :In-game toolbar buttons
''',
    'STR_BROWSER_TUTORIAL_START_LEVEL',
)

append_strings(
    Path('openttd/src/lang/russian.txt'),
    '''
STR_BROWSER_TUTORIAL_START_LEVEL                               :Начать обучающий уровень
STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP                       :Запустить небольшую учебную карту с пошаговыми подсказками
STR_BROWSER_BUTTON_GUIDE_MENU                                  :Справочник кнопок
STR_BROWSER_BUTTON_GUIDE_TOOLTIP                               :Открыть иллюстрированный справочник кнопок главного меню и игровой панели
STR_BROWSER_TUTORIAL_COACH_CAPTION                             :Обучающий уровень
STR_BROWSER_TUTORIAL_COACH_HINT                                :Следуйте жёлтой подсветке и стрелке. Выполните действие прямо в игре, затем нажмите «Далее».
STR_BROWSER_TUTORIAL_FINISH                                    :Завершить
STR_BROWSER_TUTORIAL_LEVEL_01                                  :1/16 — Камера и масштаб{}Это настоящая учебная карта. Зажмите правую кнопку мыши и двигайте карту. Колёсиком или подсвеченными кнопками меняйте масштаб. Перед строительством осмотритесь.
STR_BROWSER_TUTORIAL_LEVEL_02                                  :2/16 — Пауза и скорость{}Ставьте игру на паузу, когда планируете дорогое строительство. Ускорение удобно во время ожидания транспорта, но для точных действий лучше обычная скорость.
STR_BROWSER_TUTORIAL_LEVEL_03                                  :3/16 — Карта и города{}Откройте карту и инструменты городов. Города создают пассажиров и почту. Станция обслуживает только здания в своей зоне охвата, поэтому место строительства очень важно.
STR_BROWSER_TUTORIAL_LEVEL_04                                  :4/16 — Строительство дорог{}Нажмите подсвеченную кнопку строительства дорог. Дороги — лучший первый транспорт: они дешёвые, гибкие и позволяют освоить остановки, депо и задания.
STR_BROWSER_TUTORIAL_LEVEL_05                                  :5/16 — Прокладываем дорогу{}Выберите «Автодорога» на панели дорог и протяните дорогу между двумя близкими городами. Сначала стройте коротко и просто; препятствия позже можно пройти мостом или тоннелем.
STR_BROWSER_TUTORIAL_LEVEL_06                                  :6/16 — Автобусные остановки{}Поставьте по автобусной остановке в каждом городе. Следите за подсветкой зоны охвата: здания внутри неё создают и принимают пассажиров.
STR_BROWSER_TUTORIAL_LEVEL_07                                  :7/16 — Депо{}Постройте автомобильное депо и соедините его с дорогой. В депо покупают, заменяют и обслуживают дорожный транспорт.
STR_BROWSER_TUTORIAL_LEVEL_08                                  :8/16 — Покупаем транспорт{}Откройте список автотранспорта или депо и купите автобус. В окне машины видны состояние, возраст, прибыль, надёжность и кнопки запуска или остановки.
STR_BROWSER_TUTORIAL_LEVEL_09                                  :9/16 — Задания{}Откройте у автобуса окно «Задания» и добавьте обе остановки. Задания задают маршрут и повторяются автоматически. Полная загрузка и передача груза — дополнительные инструменты.
STR_BROWSER_TUTORIAL_LEVEL_10                                  :10/16 — Финансы{}Откройте финансы компании. Доход появляется после полезной доставки груза или пассажиров. Следите за строительством, эксплуатацией, кредитом и годовой прибылью.
STR_BROWSER_TUTORIAL_LEVEL_11                                  :11/16 — Железные дороги и сигналы{}Поезда эффективно перевозят большие объёмы. Постройте путь, станции и депо, а сигналами безопасно разделяйте общую сеть между несколькими поездами. Начните с простой линии между двумя точками.
STR_BROWSER_TUTORIAL_LEVEL_12                                  :12/16 — Промышленность и грузы{}Предприятия производят и принимают определённые грузы. Через список промышленности и карту найдите цепочку и соедините производителя с потребителем подходящим транспортом.
STR_BROWSER_TUTORIAL_LEVEL_13                                  :13/16 — Корабли и самолёты{}Водный и воздушный транспорт удобен на больших расстояниях. Причалу нужна вода, аэропорту — много свободного места. Такая техника дорогая, поэтому сначала проверьте спрос.
STR_BROWSER_TUTORIAL_LEVEL_14                                  :14/16 — Рельеф, мосты и тоннели{}Изменение рельефа помогает на сложной местности, но стоит денег и влияет на отношение местных властей. Часто мост или тоннель дешевле, чем перестраивать весь рельеф.
STR_BROWSER_TUTORIAL_LEVEL_15                                  :15/16 — Рейтинг компании{}Графики и сведения о компании показывают эффективность. Локальный и глобальный рейтинги учитывают лучший честный результат. Если использовать любой чит, дальнейшие очки этой партии в рейтинг не попадут.
STR_BROWSER_TUTORIAL_LEVEL_16                                  :16/16 — Сохранения, настройки и помощь{}Сохраняйте важные игры, настраивайте интерфейс и в любой момент открывайте «Помощь → Обучение» или «Помощь → Справочник кнопок». Основной цикл освоен: спрос → инфраструктура → транспорт → задания → доставка → прибыль → развитие.
STR_BROWSER_MANUAL_CAPTION                                     :Иллюстрированный справочник кнопок
STR_BROWSER_MANUAL_MAIN_MENU                                   :Кнопки главного меню
STR_BROWSER_MANUAL_TOOLBAR                                     :Кнопки игровой панели
''',
    'STR_BROWSER_TUTORIAL_START_LEVEL',
)

intro_path = Path('openttd/src/intro_gui.cpp')
intro = intro_path.read_text(encoding='utf-8')

# We need the public toolbar IDs for highlighting and the road toolbar IDs for
# the construction stages.
include_anchor = '#include "widgets/intro_widget.h"\n'
extra_includes = '#include "widgets/intro_widget.h"\n#include "widgets/toolbar_widget.h"\n#include "widgets/road_widget.h"\n'
if '#include "widgets/toolbar_widget.h"' not in intro:
    if include_anchor not in intro:
        raise SystemExit('Could not find intro widget include')
    intro = intro.replace(include_anchor, extra_includes, 1)

start = intro.find('enum BrowserTutorialWidgets : WidgetID {')
end = intro.find('struct SelectGameWindow : public Window {')
if start < 0 or end < 0 or end <= start:
    raise SystemExit('Could not find generated tutorial block to upgrade')

interactive_code = r'''
enum BrowserTutorialWidgets : WidgetID {
	WID_BT_START_LEVEL,
	WID_BT_BUTTON_GUIDE,
	WID_BT_TEXT,
	WID_BT_PREVIOUS,
	WID_BT_NEXT,
};

enum BrowserTutorialCoachWidgets : WidgetID {
	WID_BTC_CONTENT,
	WID_BTC_PREVIOUS,
	WID_BTC_NEXT,
};

enum BrowserButtonGuideWidgets : WidgetID {
	WID_BBG_CONTENT,
	WID_BBG_PREVIOUS,
	WID_BBG_NEXT,
};

void StartBrowserTutorialLevel();
void ShowBrowserButtonGuide();
void BrowserTutorialGameStarted();

static constexpr StringID _browser_tutorial_steps[] = {
	STR_BROWSER_TUTORIAL_STEP_1,
	STR_BROWSER_TUTORIAL_STEP_2,
	STR_BROWSER_TUTORIAL_STEP_3,
	STR_BROWSER_TUTORIAL_STEP_4,
	STR_BROWSER_TUTORIAL_STEP_5,
	STR_BROWSER_TUTORIAL_STEP_6,
	STR_BROWSER_TUTORIAL_STEP_7,
	STR_BROWSER_TUTORIAL_STEP_8,
};

static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_TUTORIAL_CAPTION),
	EndContainer(),
	/* Keep the footer compact enough for the 640x360 moderation viewport.
	   Separate navigation from the long Russian action labels so no widget can
	   overlap another row when GUI/font scaling changes. */
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BT_TEXT), SetMinimalSize(420, 100), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(140, 24), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(140, 24), SetFill(1, 0),
	EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
		NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BT_START_LEVEL), SetStringTip(STR_BROWSER_TUTORIAL_START_LEVEL, STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP), SetMinimalSize(190, 26), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_BUTTON_GUIDE), SetStringTip(STR_BROWSER_BUTTON_GUIDE_MENU, STR_BROWSER_BUTTON_GUIDE_TOOLTIP), SetMinimalSize(190, 26), SetFill(1, 0),
	EndContainer(),
};

static WindowDesc _browser_tutorial_desc(
	WDP_CENTER, {}, 0, 0,
	WC_HELPWIN, WC_NONE,
	{},
	_nested_browser_tutorial_widgets
);

struct BrowserTutorialWindow final : Window {
	size_t step = 0;

	BrowserTutorialWindow() : Window(_browser_tutorial_desc)
	{
		this->InitNested(0);
		this->UpdateButtons();
	}

	void UpdateButtons()
	{
		this->SetWidgetDisabledState(WID_BT_PREVIOUS, this->step == 0);
		this->SetWidgetDisabledState(WID_BT_NEXT, this->step + 1 >= std::size(_browser_tutorial_steps));
	}

	void DrawWidget(const Rect &r, WidgetID widget) const override
	{
		if (widget != WID_BT_TEXT) return;
		DrawStringMultiLine(r.Shrink(WidgetDimensions::scaled.sparse), _browser_tutorial_steps[this->step], TC_BLACK, SA_LEFT);
	}

	void OnClick([[maybe_unused]] Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
	{
		switch (widget) {
			case WID_BT_START_LEVEL: StartBrowserTutorialLevel(); return;
			case WID_BT_BUTTON_GUIDE: ShowBrowserButtonGuide(); return;
			case WID_BT_PREVIOUS:
				if (this->step > 0) --this->step;
				break;
			case WID_BT_NEXT:
				if (this->step + 1 < std::size(_browser_tutorial_steps)) ++this->step;
				break;
			default: return;
		}
		this->UpdateButtons();
		this->SetDirty();
	}
};

struct BrowserButtonGuideEntry {
	SpriteID sprite;
	StringID description;
};

static constexpr BrowserButtonGuideEntry _browser_main_menu_guide[] = {
	{SPR_IMG_LANDSCAPING, STR_INTRO_TOOLTIP_NEW_GAME},
	{SPR_IMG_SHOW_COUNTOURS, STR_INTRO_TOOLTIP_PLAY_HEIGHTMAP},
	{SPR_IMG_SUBSIDIES, STR_INTRO_TOOLTIP_PLAY_SCENARIO},
	{SPR_IMG_SAVE, STR_INTRO_TOOLTIP_LOAD_GAME},
	{SPR_IMG_COMPANY_LEAGUE, STR_INTRO_TOOLTIP_HIGHSCORE},
	{SPR_IMG_COMPANY_GENERAL, STR_INTRO_TOOLTIP_MULTIPLAYER},
	{SPR_IMG_SETTINGS, STR_INTRO_TOOLTIP_GAME_OPTIONS},
	{SPR_IMG_SHOW_VEHICLES, STR_INTRO_TOOLTIP_ONLINE_CONTENT},
	{SPR_IMG_SMALLMAP, STR_INTRO_TOOLTIP_SCENARIO_EDITOR},
	{SPR_IMG_QUERY, STR_INTRO_TOOLTIP_HELP},
	{SPR_IMG_QUERY, STR_BROWSER_TUTORIAL_TOOLTIP},
};

static constexpr BrowserButtonGuideEntry _browser_toolbar_guide[] = {
	{SPR_IMG_PAUSE, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_PAUSE},
	{SPR_IMG_FASTFORWARD, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_FAST_FORWARD},
	{SPR_IMG_SETTINGS, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_SETTINGS},
	{SPR_IMG_SAVE, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_SAVE},
	{SPR_IMG_SMALLMAP, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_SMALL_MAP},
	{SPR_IMG_TOWN, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_TOWNS},
	{SPR_IMG_SUBSIDIES, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_SUBSIDIES},
	{SPR_IMG_COMPANY_LIST, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_STATIONS},
	{SPR_IMG_COMPANY_FINANCE, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_FINANCES},
	{SPR_IMG_COMPANY_GENERAL, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_COMPANIES},
	{SPR_IMG_STORY_BOOK, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_STORY},
	{SPR_IMG_QUERY, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_GOAL},
	{SPR_IMG_GRAPHS, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_GRAPHS},
	{SPR_IMG_COMPANY_LEAGUE, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_LEAGUE},
	{SPR_IMG_INDUSTRY, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_INDUSTRIES},
	{SPR_IMG_TRAINLIST, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_TRAINS},
	{SPR_IMG_TRUCKLIST, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_ROADVEHS},
	{SPR_IMG_SHIPLIST, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_SHIPS},
	{SPR_IMG_AIRPLANESLIST, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_AIRCRAFT},
	{SPR_IMG_ZOOMIN, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_ZOOM_IN},
	{SPR_IMG_ZOOMOUT, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_ZOOM_OUT},
	{SPR_IMG_BUILDRAIL, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_RAILS},
	{SPR_IMG_BUILDROAD, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_ROADS},
	{SPR_IMG_BUILDTRAMS, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_TRAMS},
	{SPR_IMG_BUILDWATER, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_WATER},
	{SPR_IMG_BUILDAIR, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_AIR},
	{SPR_IMG_LANDSCAPING, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_LANDSCAPE},
	{SPR_IMG_MUSIC, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_MUSIC_SOUND},
	{SPR_IMG_MESSAGES, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_MESSAGES},
	{SPR_IMG_QUERY, STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_HELP},
};

static constexpr size_t BROWSER_GUIDE_ROWS = 3;
static constexpr size_t BROWSER_MAIN_PAGES = (std::size(_browser_main_menu_guide) + BROWSER_GUIDE_ROWS - 1) / BROWSER_GUIDE_ROWS;
static constexpr size_t BROWSER_TOOLBAR_PAGES = (std::size(_browser_toolbar_guide) + BROWSER_GUIDE_ROWS - 1) / BROWSER_GUIDE_ROWS;
static constexpr size_t BROWSER_GUIDE_PAGES = BROWSER_MAIN_PAGES + BROWSER_TOOLBAR_PAGES;

static constexpr std::initializer_list<NWidgetPart> _nested_browser_button_guide_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_MANUAL_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BBG_CONTENT), SetMinimalSize(420, 140), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(140, 24), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(140, 24), SetFill(1, 0),
	EndContainer(),
};

static WindowDesc _browser_button_guide_desc(
	WDP_CENTER, {}, 0, 0,
	WC_HELPWIN, WC_NONE,
	{},
	_nested_browser_button_guide_widgets
);

struct BrowserButtonGuideWindow final : Window {
	size_t page = 0;

	BrowserButtonGuideWindow() : Window(_browser_button_guide_desc)
	{
		this->InitNested(0);
		this->UpdateButtons();
	}

	void UpdateButtons()
	{
		this->SetWidgetDisabledState(WID_BBG_PREVIOUS, this->page == 0);
		this->SetWidgetDisabledState(WID_BBG_NEXT, this->page + 1 >= BROWSER_GUIDE_PAGES);
	}

	void DrawWidget(const Rect &r, WidgetID widget) const override
	{
		if (widget != WID_BBG_CONTENT) return;
		Rect body = r.Shrink(WidgetDimensions::scaled.sparse);
		const bool main_page = this->page < BROWSER_MAIN_PAGES;
		const auto &entries = main_page ? _browser_main_menu_guide : _browser_toolbar_guide;
		const size_t local_page = main_page ? this->page : this->page - BROWSER_MAIN_PAGES;
		const size_t start = local_page * BROWSER_GUIDE_ROWS;
		const size_t count = main_page ? std::size(_browser_main_menu_guide) : std::size(_browser_toolbar_guide);
		DrawString(body.left, body.right, body.top, main_page ? STR_BROWSER_MANUAL_MAIN_MENU : STR_BROWSER_MANUAL_TOOLBAR, TC_WHITE, SA_CENTER);
		int y = body.top + GetCharacterHeight(FS_NORMAL) + WidgetDimensions::scaled.vsep_wide;
		for (size_t row = 0; row < BROWSER_GUIDE_ROWS && start + row < count; ++row) {
			const BrowserButtonGuideEntry &entry = entries[start + row];
			DrawSprite(entry.sprite, PAL_NONE, body.left + 10, y + 6);
			Rect text_rect{body.left + 50, y, body.right, y + 35};
			DrawStringMultiLine(text_rect, entry.description, TC_BLACK, SA_LEFT);
			y += 38;
		}
	}

	void OnClick([[maybe_unused]] Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
	{
		if (widget == WID_BBG_PREVIOUS && this->page > 0) --this->page;
		if (widget == WID_BBG_NEXT && this->page + 1 < BROWSER_GUIDE_PAGES) ++this->page;
		this->UpdateButtons();
		this->SetDirty();
	}
};

void ShowBrowserButtonGuide()
{
	CloseWindowByClass(WC_HELPWIN);
	new BrowserButtonGuideWindow();
}

enum class BrowserTutorialTarget : uint8_t {
	None,
	MainToolbar,
	RoadToolbar,
};

struct BrowserTutorialCoachStep {
	StringID text;
	SpriteID icon;
	BrowserTutorialTarget target;
	WidgetID widget;
};

static constexpr BrowserTutorialCoachStep _browser_tutorial_level_steps[] = {
	{STR_BROWSER_TUTORIAL_LEVEL_01, SPR_IMG_ZOOMIN, BrowserTutorialTarget::MainToolbar, WID_TN_ZOOM_IN},
	{STR_BROWSER_TUTORIAL_LEVEL_02, SPR_IMG_PAUSE, BrowserTutorialTarget::MainToolbar, WID_TN_PAUSE},
	{STR_BROWSER_TUTORIAL_LEVEL_03, SPR_IMG_SMALLMAP, BrowserTutorialTarget::MainToolbar, WID_TN_SMALL_MAP},
	{STR_BROWSER_TUTORIAL_LEVEL_04, SPR_IMG_BUILDROAD, BrowserTutorialTarget::MainToolbar, WID_TN_ROADS},
	{STR_BROWSER_TUTORIAL_LEVEL_05, SPR_IMG_AUTOROAD, BrowserTutorialTarget::RoadToolbar, WID_ROT_AUTOROAD},
	{STR_BROWSER_TUTORIAL_LEVEL_06, SPR_IMG_BUS_STATION, BrowserTutorialTarget::RoadToolbar, WID_ROT_BUS_STATION},
	{STR_BROWSER_TUTORIAL_LEVEL_07, SPR_IMG_ROAD_DEPOT, BrowserTutorialTarget::RoadToolbar, WID_ROT_DEPOT},
	{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS},
	{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET},
	{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_COMPANY_FINANCE, BrowserTutorialTarget::MainToolbar, WID_TN_FINANCES},
	{STR_BROWSER_TUTORIAL_LEVEL_11, SPR_IMG_BUILDRAIL, BrowserTutorialTarget::MainToolbar, WID_TN_RAILS},
	{STR_BROWSER_TUTORIAL_LEVEL_12, SPR_IMG_INDUSTRY, BrowserTutorialTarget::MainToolbar, WID_TN_INDUSTRIES},
	{STR_BROWSER_TUTORIAL_LEVEL_13, SPR_IMG_BUILDWATER, BrowserTutorialTarget::MainToolbar, WID_TN_WATER},
	{STR_BROWSER_TUTORIAL_LEVEL_14, SPR_IMG_LANDSCAPING, BrowserTutorialTarget::MainToolbar, WID_TN_LANDSCAPE},
	{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_GRAPHS, BrowserTutorialTarget::MainToolbar, WID_TN_GRAPHS},
	{STR_BROWSER_TUTORIAL_LEVEL_16, SPR_IMG_SAVE, BrowserTutorialTarget::MainToolbar, WID_TN_SAVE},
};

static bool _browser_tutorial_pending = false;
static bool _browser_tutorial_active = false;

static Window *BrowserTutorialTargetWindow(BrowserTutorialTarget target)
{
	switch (target) {
		case BrowserTutorialTarget::MainToolbar: return FindWindowById(WC_MAIN_TOOLBAR, 0);
		case BrowserTutorialTarget::RoadToolbar: return FindWindowByClass(WC_BUILD_TOOLBAR);
		default: return nullptr;
	}
}

static void BrowserTutorialClearHighlights()
{
	if (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
	if (Window *w = FindWindowByClass(WC_BUILD_TOOLBAR); w != nullptr) w->DisableAllWidgetHighlight();
}

static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_coach_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_TUTORIAL_COACH_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BTC_CONTENT), SetMinimalSize(420, 105), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BTC_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(140, 24), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BTC_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(140, 24), SetFill(1, 0),
	EndContainer(),
};

static WindowDesc _browser_tutorial_coach_desc(
	WDP_CENTER, {}, 0, 0,
	WC_HELPWIN, WC_NONE,
	{},
	_nested_browser_tutorial_coach_widgets
);

struct BrowserTutorialCoachWindow final : Window {
	size_t step = 0;

	BrowserTutorialCoachWindow() : Window(_browser_tutorial_coach_desc)
	{
		this->InitNested(0);
		this->UpdateStep();
	}

	void Close([[maybe_unused]] int data = 0) override
	{
		BrowserTutorialClearHighlights();
		_browser_tutorial_active = false;
		this->Window::Close();
	}

	void UpdateStep()
	{
		BrowserTutorialClearHighlights();
		this->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);
		const auto &current = _browser_tutorial_level_steps[this->step];
		if (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
			target->SetWidgetHighlight(current.widget, TC_YELLOW);
		}
		this->SetDirty();
	}

	void OnRealtimeTick([[maybe_unused]] uint delta_ms) override
	{
		const auto &current = _browser_tutorial_level_steps[this->step];
		if (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
			if (!target->IsWidgetHighlighted(current.widget)) target->SetWidgetHighlight(current.widget, TC_YELLOW);
		}
		this->SetDirty();
	}

	void DrawWidget(const Rect &r, WidgetID widget) const override
	{
		if (widget != WID_BTC_CONTENT) return;
		const auto &current = _browser_tutorial_level_steps[this->step];
		Rect body = r.Shrink(WidgetDimensions::scaled.sparse);
		DrawSprite(current.icon, PAL_NONE, body.left + 12, body.top + 16);
		Rect text_rect{body.left + 58, body.top + 4, body.right, body.bottom - 35};
		DrawStringMultiLine(text_rect, current.text, TC_BLACK, SA_LEFT);
		Rect hint_rect{body.left + 58, body.bottom - 30, body.right, body.bottom};
		DrawStringMultiLine(hint_rect, STR_BROWSER_TUTORIAL_COACH_HINT, TC_YELLOW, SA_LEFT);

		if (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {
			const NWidgetBase *target_widget = target->GetWidget<NWidgetBase>(current.widget);
			if (target_widget != nullptr) {
				Rect target_rect = target_widget->GetCurrentRect();
				const int tx = target->left + (target_rect.left + target_rect.right) / 2;
				const int ty = target->top + (target_rect.top + target_rect.bottom) / 2;
				const int cx = this->left + (body.left + body.right) / 2;
				const int cy = this->top + (body.top + body.bottom) / 2;
				SpriteID arrow = SPR_ARROW_UP;
				int arrow_x = (body.left + body.right) / 2;
				int arrow_y = body.top + 3;
				if (std::abs(tx - cx) > std::abs(ty - cy)) {
					if (tx < cx) {
						arrow = SPR_ARROW_LEFT;
						arrow_x = body.left + 3;
						arrow_y = (body.top + body.bottom) / 2;
					} else {
						arrow = SPR_ARROW_RIGHT;
						arrow_x = body.right - 18;
						arrow_y = (body.top + body.bottom) / 2;
					}
				} else if (ty < cy) {
					arrow = SPR_ARROW_UP;
					arrow_x = (body.left + body.right) / 2;
					arrow_y = body.top + 3;
				} else {
					arrow = SPR_ARROW_DOWN;
					arrow_x = (body.left + body.right) / 2;
					arrow_y = body.bottom - 18;
				}
				DrawSprite(arrow, PAL_NONE, arrow_x, arrow_y);
			}
		}
	}

	void OnClick([[maybe_unused]] Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
	{
		if (widget == WID_BTC_PREVIOUS && this->step > 0) {
			--this->step;
			this->UpdateStep();
			return;
		}
		if (widget == WID_BTC_NEXT) {
			if (this->step + 1 < std::size(_browser_tutorial_level_steps)) {
				++this->step;
				this->UpdateStep();
			} else {
				this->Close();
			}
		}
	}
};

void StartBrowserTutorialLevel()
{
	/* Dedicated deterministic practice world. Keep it small and gentle so the
	   player reaches vehicles quickly instead of fighting map generation. */
	_is_network_server = false;
	_settings_newgame.game_creation.map_x = 7;
	_settings_newgame.game_creation.map_y = 7;
	_settings_newgame.game_creation.landscape = LandscapeType::Temperate;
	_settings_newgame.game_creation.amount_of_rivers = 0;
	_settings_newgame.difficulty.terrain_type = 0;
	_browser_tutorial_pending = true;
	_browser_tutorial_active = false;
	StartNewGameWithoutGUI(0x4F545444U);
}

void BrowserTutorialGameStarted()
{
	if (!_browser_tutorial_pending) return;
	_browser_tutorial_pending = false;
	_browser_tutorial_active = true;
	CloseWindowByClass(WC_HELPWIN);
	new BrowserTutorialCoachWindow();
}

void ShowBrowserTutorial()
{
	CloseWindowByClass(WC_HELPWIN);
	new BrowserTutorialWindow();
}

'''

intro = intro[:start] + interactive_code + intro[end:]
intro_path.write_text(intro, encoding='utf-8')

# Open the coach after SM_NEWGAME has finished creating the real world.
openttd_path = Path('openttd/src/openttd.cpp')
openttd = openttd_path.read_text(encoding='utf-8')
extern_anchor = 'extern void CheckCaches();\n'
extern_decl = 'extern void BrowserTutorialGameStarted();\n'
if extern_decl not in openttd:
    if extern_anchor not in openttd:
        raise SystemExit('Could not find openttd extern declaration anchor')
    openttd = openttd.replace(extern_anchor, extern_anchor + extern_decl, 1)

newgame_block = '''\t\tcase SM_RESTARTGAME: // Restart --> 'Random game' with current settings
\t\tcase SM_NEWGAME: // New Game --> 'Random game'
\t\t\tMakeNewGame(false, new_mode == SM_NEWGAME);
\t\t\tGenerateSavegameId();

\t\t\tUpdateSocialIntegration(GM_NORMAL);
\t\t\tbreak;
'''
patched_newgame = '''\t\tcase SM_RESTARTGAME: // Restart --> 'Random game' with current settings
\t\tcase SM_NEWGAME: // New Game --> 'Random game'
\t\t\tMakeNewGame(false, new_mode == SM_NEWGAME);
\t\t\tGenerateSavegameId();

\t\t\tUpdateSocialIntegration(GM_NORMAL);
\t\t\tif (new_mode == SM_NEWGAME) BrowserTutorialGameStarted();
\t\t\tbreak;
'''
if 'if (new_mode == SM_NEWGAME) BrowserTutorialGameStarted();' not in openttd:
    if openttd.count(newgame_block) != 1:
        raise SystemExit(f'Could not find unique SM_NEWGAME block ({openttd.count(newgame_block)})')
    openttd = openttd.replace(newgame_block, patched_newgame, 1)
openttd_path.write_text(openttd, encoding='utf-8')

# The existing toolbar patch already added Tutorial. Add the illustrated button
# guide beside it and shift the debug-only menu indices safely.
toolbar_path = Path('openttd/src/toolbar_gui.cpp')
toolbar = toolbar_path.read_text(encoding='utf-8')
if 'extern void ShowBrowserButtonGuide();' not in toolbar:
    decl = 'extern void ShowBrowserTutorial();\n'
    if decl not in toolbar:
        raise SystemExit('Could not find tutorial toolbar declaration')
    toolbar = toolbar.replace(decl, decl + 'extern void ShowBrowserButtonGuide();\n', 1)

old_pair = 'STR_ABOUT_MENU_HELP, STR_BROWSER_TUTORIAL_MENU, STR_NULL'
new_pair = 'STR_ABOUT_MENU_HELP, STR_BROWSER_TUTORIAL_MENU, STR_BROWSER_BUTTON_GUIDE_MENU, STR_NULL'
if new_pair not in toolbar:
    if toolbar.count(old_pair) != 2:
        raise SystemExit(f'Expected two tutorial Help menu lists, got {toolbar.count(old_pair)}')
    toolbar = toolbar.replace(old_pair, new_pair)

old_switch = '''\t\tcase  0: return PlaceLandBlockInfo();
\t\tcase  1: ShowHelpWindow();                 break;
\t\tcase  2: ShowBrowserTutorial();            break;
\t\tcase  3: IConsoleSwitch();                 break;
\t\tcase  4: ShowScriptDebugWindow(CompanyID::Invalid(), _ctrl_pressed); break;
\t\tcase  5: ShowScreenshotWindow();           break;
\t\tcase  6: ShowFramerateWindow();            break;
\t\tcase  7: ShowAboutWindow();                break;
\t\tcase  8: ShowSpriteAlignerWindow();        break;
\t\tcase  9: ToggleBoundingBoxes();            break;
\t\tcase 10: ToggleDirtyBlocks();              break;
\t\tcase 11: ToggleWidgetOutlines();           break;
'''
new_switch = '''\t\tcase  0: return PlaceLandBlockInfo();
\t\tcase  1: ShowHelpWindow();                 break;
\t\tcase  2: ShowBrowserTutorial();            break;
\t\tcase  3: ShowBrowserButtonGuide();         break;
\t\tcase  4: IConsoleSwitch();                 break;
\t\tcase  5: ShowScriptDebugWindow(CompanyID::Invalid(), _ctrl_pressed); break;
\t\tcase  6: ShowScreenshotWindow();           break;
\t\tcase  7: ShowFramerateWindow();            break;
\t\tcase  8: ShowAboutWindow();                break;
\t\tcase  9: ShowSpriteAlignerWindow();        break;
\t\tcase 10: ToggleBoundingBoxes();            break;
\t\tcase 11: ToggleDirtyBlocks();              break;
\t\tcase 12: ToggleWidgetOutlines();           break;
'''
if 'case  3: ShowBrowserButtonGuide();' not in toolbar:
    if toolbar.count(old_switch) != 1:
        raise SystemExit('Could not find post-tutorial Help callback switch')
    toolbar = toolbar.replace(old_switch, new_switch, 1)
toolbar_path.write_text(toolbar, encoding='utf-8')

for path, markers in {
    intro_path: (
        'StartBrowserTutorialLevel()',
        'struct BrowserTutorialCoachWindow final : Window',
        'SetWidgetHighlight(current.widget, TC_YELLOW)',
        'SPR_ARROW_LEFT',
        'struct BrowserButtonGuideWindow final : Window',
        'STR_TOOLBAR_TOOLTIP_PAUSE_GAME + WID_TN_HELP',
        'SetMinimalSize(420, 100)',
        'static constexpr size_t BROWSER_GUIDE_ROWS = 3;',
        '_browser_tutorial_coach_desc(\n\tWDP_CENTER',
    ),
    openttd_path: ('BrowserTutorialGameStarted();',),
    toolbar_path: ('ShowBrowserButtonGuide();', 'STR_BROWSER_BUTTON_GUIDE_MENU'),
}.items():
    data = path.read_text(encoding='utf-8')
    for marker in markers:
        if marker not in data:
            raise SystemExit(f'Missing interactive tutorial marker {marker!r} in {path}')

print('Interactive training level, yellow coach arrows and illustrated button guide patched.')
