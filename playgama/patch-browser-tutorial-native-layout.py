#!/usr/bin/env python3
"""Polish browser tutorial UI with stock OpenTTD nested-widget patterns.

Runs after patch-browser-tutorial-level.py. The custom tutorial windows keep
their own content drawing, but their frame/padding/button layout follows native
OpenTTD dialogs such as GenerateLandscapeWindow: a brown panel with an inner
vertical stack, EqualSize button rows, SetMinimalTextLines(), and no hard-coded
button pixel sizes.

The patch also removes punctuation glyphs that are not used by stock Russian
OpenTTD strings (notably U+2014 and U+2192) from our custom STR_BROWSER_* text,
so the language glyph scan does not raise the red "current font is missing"
warning just because of tutorial copy.
"""

from pathlib import Path


def replace_block(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"Could not find start marker: {start_marker}")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"Could not find end marker after {start_marker}: {end_marker}")
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def normalise_browser_strings(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    lines = []
    changed = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("STR_BROWSER_"):
            new_line = line.replace("—", "-").replace("→", "->")
            if new_line != line:
                changed += 1
            line = new_line
        lines.append(line)
    result = "".join(lines)
    browser_lines = "\n".join(
        line for line in result.splitlines() if line.startswith("STR_BROWSER_")
    )
    for forbidden in ("—", "→"):
        if forbidden in browser_lines:
            raise SystemExit(f"Unsupported tutorial punctuation survived in {path}: {forbidden!r}")
    path.write_text(result, encoding="utf-8")
    print(f"Normalised browser tutorial punctuation in {path} ({changed} lines changed).")


intro_path = Path("openttd/src/intro_gui.cpp")
intro = intro_path.read_text(encoding="utf-8")

tutorial_widgets = r'''static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_TUTORIAL_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN),
		NWidget(NWID_VERTICAL), SetPIP(0, WidgetDimensions::unscaled.vsep_wide, 0), SetPadding(WidgetDimensions::unscaled.sparse),
			NWidget(WWT_EMPTY, INVALID_COLOUR, WID_BT_TEXT), SetMinimalSize(420, 100), SetFill(1, 1),

			/* Native OpenTTD equal-size navigation row; no fixed button pixels. */
			NWidget(NWID_HORIZONTAL, NWidContainerFlag::EqualSize),
				NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_PREVIOUS), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetFill(1, 0),
				NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_NEXT), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetFill(1, 0),
			EndContainer(),

			/* Same hierarchy as world creation: secondary action, then large green primary action. */
			NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_BUTTON_GUIDE), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_BUTTON_GUIDE_MENU, STR_BROWSER_BUTTON_GUIDE_TOOLTIP), SetFill(1, 0),
			NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BT_START_LEVEL), SetMinimalTextLines(3, 0), SetStringTip(STR_BROWSER_TUTORIAL_START_LEVEL, STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP), SetFill(1, 1),
		EndContainer(),
	EndContainer(),
};'''

guide_widgets = r'''static constexpr std::initializer_list<NWidgetPart> _nested_browser_button_guide_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_MANUAL_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN),
		NWidget(NWID_VERTICAL), SetPIP(0, WidgetDimensions::unscaled.vsep_wide, 0), SetPadding(WidgetDimensions::unscaled.sparse),
			NWidget(WWT_EMPTY, INVALID_COLOUR, WID_BBG_CONTENT), SetMinimalSize(420, 140), SetFill(1, 1),
			NWidget(NWID_HORIZONTAL, NWidContainerFlag::EqualSize),
				NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_PREVIOUS), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetFill(1, 0),
				NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_NEXT), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetFill(1, 0),
			EndContainer(),
		EndContainer(),
	EndContainer(),
};'''

coach_widgets = r'''static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_coach_widgets = {
	NWidget(NWID_HORIZONTAL),
		NWidget(WWT_CLOSEBOX, COLOUR_BROWN),
		NWidget(WWT_CAPTION, COLOUR_BROWN), SetStringTip(STR_BROWSER_TUTORIAL_COACH_CAPTION),
	EndContainer(),
	NWidget(WWT_PANEL, COLOUR_BROWN),
		NWidget(NWID_VERTICAL), SetPIP(0, WidgetDimensions::unscaled.vsep_wide, 0), SetPadding(WidgetDimensions::unscaled.sparse),
			NWidget(WWT_EMPTY, INVALID_COLOUR, WID_BTC_CONTENT), SetMinimalSize(420, 105), SetFill(1, 1),
			NWidget(NWID_HORIZONTAL, NWidContainerFlag::EqualSize),
				NWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BTC_PREVIOUS), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetFill(1, 0),
				NWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BTC_NEXT), SetMinimalTextLines(2, 0), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetFill(1, 0),
			EndContainer(),
		EndContainer(),
	EndContainer(),
};'''

intro = replace_block(
    intro,
    "static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_widgets = {",
    "static WindowDesc _browser_tutorial_desc(",
    tutorial_widgets,
)
intro = replace_block(
    intro,
    "static constexpr std::initializer_list<NWidgetPart> _nested_browser_button_guide_widgets = {",
    "static WindowDesc _browser_button_guide_desc(",
    guide_widgets,
)
intro = replace_block(
    intro,
    "static constexpr std::initializer_list<NWidgetPart> _nested_browser_tutorial_coach_widgets = {",
    "static WindowDesc _browser_tutorial_coach_desc(",
    coach_widgets,
)

for widget in (
    "WID_BT_PREVIOUS",
    "WID_BT_NEXT",
    "WID_BT_START_LEVEL",
    "WID_BT_BUTTON_GUIDE",
    "WID_BBG_PREVIOUS",
    "WID_BBG_NEXT",
    "WID_BTC_PREVIOUS",
    "WID_BTC_NEXT",
):
    for line in intro.splitlines():
        if widget in line and "NWidget(WWT_PUSHTXTBTN" in line and "SetMinimalSize(" in line:
            raise SystemExit(f"Fixed pixel size survived on tutorial button {widget}")

for marker in (
    "NWID_HORIZONTAL, NWidContainerFlag::EqualSize",
    "SetMinimalTextLines(3, 0)",
    "NWidget(WWT_EMPTY, INVALID_COLOUR, WID_BT_TEXT)",
    "NWidget(WWT_EMPTY, INVALID_COLOUR, WID_BBG_CONTENT)",
    "NWidget(WWT_EMPTY, INVALID_COLOUR, WID_BTC_CONTENT)",
):
    if marker not in intro:
        raise SystemExit(f"Native tutorial layout marker missing after polish: {marker}")

intro_path.write_text(intro, encoding="utf-8")

normalise_browser_strings(Path("openttd/src/lang/english.txt"))
normalise_browser_strings(Path("openttd/src/lang/russian.txt"))

print("Tutorial windows now use stock OpenTTD panel/button layout and font-safe punctuation.")
