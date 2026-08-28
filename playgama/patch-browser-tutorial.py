#!/usr/bin/env python3
"""Add the first native OpenTTD-styled tutorial layer to the browser edition.

This patch is intentionally platform-neutral. It creates a Tutorial button in
OpenTTD's main menu and a native multi-page guide using the regular OpenTTD
window/widget system. A later stage can attach objective detection to these
same steps without replacing the UI.
"""
from pathlib import Path


def append_language_strings(path: Path, block: str, marker: str) -> None:
    text = path.read_text(encoding='utf-8')
    if marker in text:
        return
    if not text.endswith('\n'):
        text += '\n'
    text += '\n# Browser edition tutorial UI\n' + block.strip() + '\n'
    path.write_text(text, encoding='utf-8')


append_language_strings(
    Path('openttd/src/lang/english.txt'),
    '''
STR_BROWSER_TUTORIAL_MENU                                      :Tutorial
STR_BROWSER_TUTORIAL_TOOLTIP                                   :Learn the basics of building and running a transport company
STR_BROWSER_TUTORIAL_CAPTION                                   :OpenTTD tutorial
STR_BROWSER_TUTORIAL_PREVIOUS                                  :Previous
STR_BROWSER_TUTORIAL_NEXT                                      :Next
STR_BROWSER_TUTORIAL_STEP_1                                    :1/8 — Camera and map{}Move around the map with the right mouse button. Use the mouse wheel to zoom. Find two nearby towns with enough room for stations and roads.
STR_BROWSER_TUTORIAL_STEP_2                                    :2/8 — First route{}Choose a simple passenger route between two nearby towns. Short routes are easier to build, cheaper to operate and ideal for learning the basic workflow.
STR_BROWSER_TUTORIAL_STEP_3                                    :3/8 — Build stations{}Open the road construction toolbar. Build one bus station in each town and connect them with a continuous road. Make sure the station catchment areas cover town buildings.
STR_BROWSER_TUTORIAL_STEP_4                                    :4/8 — Buy a vehicle{}Build a road vehicle depot connected to the route. Open the depot, buy a bus and keep its vehicle window open for the next step.
STR_BROWSER_TUTORIAL_STEP_5                                    :5/8 — Give orders{}Open the vehicle's Orders window. Add both stations in sequence. The vehicle will repeat these orders automatically until you change them.
STR_BROWSER_TUTORIAL_STEP_6                                    :6/8 — Start service{}Start the vehicle. Watch it reach both stations and carry passengers. Income appears when cargo or passengers are delivered to their destination.
STR_BROWSER_TUTORIAL_STEP_7                                    :7/8 — Money and profit{}Open the company finances window. Compare income, running costs, construction spending and loan interest. Expand only when existing routes can support the cost.
STR_BROWSER_TUTORIAL_STEP_8                                    :8/8 — Grow the network{}You now know the core loop: connect demand, build infrastructure, buy vehicles, create orders and reinvest profit. Try trains next, then experiment with industries and NewGRF content.
''',
    'STR_BROWSER_TUTORIAL_MENU',
)

append_language_strings(
    Path('openttd/src/lang/russian.txt'),
    '''
STR_BROWSER_TUTORIAL_MENU                                      :Обучение
STR_BROWSER_TUTORIAL_TOOLTIP                                   :Изучить основы строительства и управления транспортной компанией
STR_BROWSER_TUTORIAL_CAPTION                                   :Обучение OpenTTD
STR_BROWSER_TUTORIAL_PREVIOUS                                  :Назад
STR_BROWSER_TUTORIAL_NEXT                                      :Далее
STR_BROWSER_TUTORIAL_STEP_1                                    :1/8 — Камера и карта{}Перемещайтесь по карте правой кнопкой мыши. Колёсиком меняйте масштаб. Найдите два близких города, рядом с которыми достаточно места для остановок и дороги.
STR_BROWSER_TUTORIAL_STEP_2                                    :2/8 — Первый маршрут{}Для начала выберите простой пассажирский маршрут между двумя близкими городами. Короткий маршрут дешевле строить и обслуживать, поэтому на нём удобно освоить основной игровой цикл.
STR_BROWSER_TUTORIAL_STEP_3                                    :3/8 — Строим остановки{}Откройте панель строительства дорог. Поставьте по автобусной остановке в каждом городе и соедините их непрерывной дорогой. Зона охвата остановки должна захватывать городские здания.
STR_BROWSER_TUTORIAL_STEP_4                                    :4/8 — Покупаем транспорт{}Постройте автобусное депо, соединённое с маршрутом. Откройте депо, купите автобус и оставьте окно транспорта открытым для следующего шага.
STR_BROWSER_TUTORIAL_STEP_5                                    :5/8 — Задаём задания{}Откройте у автобуса окно «Задания». По очереди добавьте обе остановки. Транспорт будет повторять этот список автоматически, пока вы его не измените.
STR_BROWSER_TUTORIAL_STEP_6                                    :6/8 — Запускаем маршрут{}Запустите автобус. Проследите, как он посетит обе остановки и повезёт пассажиров. Доход появляется после доставки пассажиров или груза к месту назначения.
STR_BROWSER_TUTORIAL_STEP_7                                    :7/8 — Деньги и прибыль{}Откройте финансы компании. Сравните доходы, расходы на транспорт, строительство и проценты по кредиту. Расширяйтесь, когда действующие маршруты способны оплачивать дальнейший рост.
STR_BROWSER_TUTORIAL_STEP_8                                    :8/8 — Развиваем сеть{}Теперь вы знаете основной цикл: найти спрос, построить инфраструктуру, купить транспорт, задать маршрут и вложить прибыль в развитие. Следующим шагом попробуйте железную дорогу, затем промышленность и NewGRF.
''',
    'STR_BROWSER_TUTORIAL_MENU',
)

# Give the main menu its own widget ID rather than repurposing/removing an
# existing OpenTTD feature.
widgets_path = Path('openttd/src/widgets/intro_widget.h')
widgets = widgets_path.read_text(encoding='utf-8')
if 'WID_SGI_TUTORIAL' not in widgets:
    anchor = '\tWID_SGI_HIGHSCORE,             ///< Highscore button.\n'
    if anchor not in widgets:
        raise SystemExit('Could not find highscore widget enum anchor')
    widgets = widgets.replace(anchor, '\tWID_SGI_TUTORIAL,              ///< Browser-edition tutorial button.\n' + anchor, 1)
    widgets_path.write_text(widgets, encoding='utf-8')

intro_path = Path('openttd/src/intro_gui.cpp')
text = intro_path.read_text(encoding='utf-8')

window_marker = 'struct BrowserTutorialWindow final : Window'
window_code = r'''
enum BrowserTutorialWidgets : WidgetID {
	WID_BT_TEXT,
	WID_BT_PREVIOUS,
	WID_BT_NEXT,
};

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
	NWidget(WWT_PANEL, COLOUR_BROWN, WID_BT_TEXT), SetMinimalSize(500, 230), SetFill(1, 1), EndContainer(),
	NWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(150, 22), SetFill(1, 0),
		NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(150, 22), SetFill(1, 0),
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
		DrawStringMultiLine(r.Shrink(WidgetDimensions::scaled.sparse), _browser_tutorial_steps[this->step], TC_FROMSTRING, SA_LEFT);
	}

	void OnClick([[maybe_unused]] Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
	{
		switch (widget) {
			case WID_BT_PREVIOUS:
				if (this->step > 0) --this->step;
				break;
			case WID_BT_NEXT:
				if (this->step + 1 < std::size(_browser_tutorial_steps)) ++this->step;
				break;
			default:
				return;
		}
		this->UpdateButtons();
		this->SetDirty();
	}
};

static void ShowBrowserTutorial()
{
	CloseWindowByClass(WC_HELPWIN);
	new BrowserTutorialWindow();
}

'''
select_anchor = 'struct SelectGameWindow : public Window {'
if window_marker not in text:
    if select_anchor not in text:
        raise SystemExit('Could not find SelectGameWindow anchor')
    text = text.replace(select_anchor, window_code + select_anchor, 1)

click_anchor = '\t\t\tcase WID_SGI_HIGHSCORE:       ShowHighscoreTable(); break;\n'
click_line = '\t\t\tcase WID_SGI_TUTORIAL:        ShowBrowserTutorial(); break;\n'
if click_line not in text:
    if click_anchor not in text:
        raise SystemExit('Could not find main-menu highscore click anchor')
    text = text.replace(click_anchor, click_line + click_anchor, 1)

highscore_widget = '\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_HIGHSCORE), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_COMPANY_LEAGUE, STR_INTRO_HIGHSCORE, STR_INTRO_TOOLTIP_HIGHSCORE), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'
tutorial_widget = '\t\t\t\tNWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_TUTORIAL), SetToolbarMinimalSize(1), SetSpriteStringTip(SPR_IMG_QUERY, STR_BROWSER_TUTORIAL_MENU, STR_BROWSER_TUTORIAL_TOOLTIP), SetAlignment(SA_LEFT | SA_VERT_CENTER), SetFill(1, 0),\n'
if tutorial_widget not in text:
    if highscore_widget not in text:
        raise SystemExit('Could not find highscore widget insertion point')
    text = text.replace(highscore_widget, tutorial_widget + highscore_widget, 1)

for check in (
    'WID_SGI_TUTORIAL',
    'struct BrowserTutorialWindow final : Window',
    'ShowBrowserTutorial();',
    'STR_BROWSER_TUTORIAL_STEP_8',
):
    if check not in text:
        raise SystemExit(f'Missing tutorial patch marker: {check!r}')

intro_path.write_text(text, encoding='utf-8')
print('Native OpenTTD tutorial menu and guide window patched.')
