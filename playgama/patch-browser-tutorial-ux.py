#!/usr/bin/env python3
"""Final UX pass for the native browser tutorial.

Runs after patch-browser-tutorial-quality.py. This pass is deliberately kept
separate from the objective logic: it makes the coach readable at large GUI
scales, guarantees a visible toolbar target for every practical lesson, makes
the yellow guidance pulse strongly, and avoids Unicode arrow glyphs that are
not present in every OpenTTD medium font.
"""
from pathlib import Path
import re


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Could not find unique {label}: {count}")
    return text.replace(old, new, 1)


def sanitize_browser_arrows(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        if line.startswith("STR_BROWSER_") and "→" in line:
            lines[i] = line.replace("→", "->")
            changed = True
    text = "".join(lines)
    if "→" in "\n".join(line for line in text.splitlines() if line.startswith("STR_BROWSER_")):
        raise SystemExit(f"Browser tutorial still contains unsupported arrow glyph in {path}")
    if changed:
        path.write_text(text, encoding="utf-8")


for lang in (Path("openttd/src/lang/english.txt"), Path("openttd/src/lang/russian.txt")):
    sanitize_browser_arrows(lang)

intro_path = Path("openttd/src/intro_gui.cpp")
text = intro_path.read_text(encoding="utf-8")

# Large OpenTTD interface scaling multiplies SetMinimalSize(), so the previous
# 520x190 coach became almost full-screen at 150-175% GUI scale. Keep the
# panels compact and let wrapped text use the available width instead.
layout_replacements = {
    "SetMinimalSize(500, 220)": "SetMinimalSize(450, 150)",
    "SetMinimalSize(520, 190)": "SetMinimalSize(450, 140)",
    "static constexpr size_t BROWSER_GUIDE_ROWS = 3;": "static constexpr size_t BROWSER_GUIDE_ROWS = 2;",
}
for old, new in layout_replacements.items():
    if old not in text and new not in text:
        raise SystemExit(f"Could not find tutorial UX layout marker: {old}")
    text = text.replace(old, new)

# Never let navigation buttons consume half the window. Side spacers absorb
# free width while the actual buttons remain fixed and centred.
nav_rows = [
    (
        "overview navigation",
        '''\tNWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(120, 26), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(120, 26), SetFill(1, 0),
\tEndContainer(),''',
        '''\tNWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_wide, 0),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(112, 24),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(112, 24),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\tEndContainer(),''',
    ),
    (
        "button guide navigation",
        '''\tNWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(120, 26), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(120, 26), SetFill(1, 0),
\tEndContainer(),''',
        '''\tNWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_wide, 0),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(112, 24),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BBG_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(112, 24),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\tEndContainer(),''',
    ),
    (
        "coach navigation",
        '''\tNWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BTC_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(120, 26), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BTC_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(120, 26), SetFill(1, 0),
\tEndContainer(),''',
        '''\tNWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_wide, 0),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BTC_PREVIOUS), SetStringTip(STR_BROWSER_TUTORIAL_PREVIOUS), SetMinimalSize(112, 24),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BTC_NEXT), SetStringTip(STR_BROWSER_TUTORIAL_NEXT), SetMinimalSize(112, 24),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\tEndContainer(),''',
    ),
]
for label, old, new in nav_rows:
    text = replace_once(text, old, new, label)

# The overview's two action buttons had the same stretching problem.
overview_actions_old = '''\tNWidget(NWID_HORIZONTAL), SetPIP(WidgetDimensions::unscaled.sparse.left, WidgetDimensions::unscaled.hsep_wide, WidgetDimensions::unscaled.sparse.right),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BT_START_LEVEL), SetStringTip(STR_BROWSER_TUTORIAL_START_LEVEL, STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP), SetMinimalSize(190, 26), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_BUTTON_GUIDE), SetStringTip(STR_BROWSER_BUTTON_GUIDE_MENU, STR_BROWSER_BUTTON_GUIDE_TOOLTIP), SetMinimalSize(180, 26), SetFill(1, 0),
\tEndContainer(),'''
overview_actions_new = '''\tNWidget(NWID_HORIZONTAL), SetPIP(0, WidgetDimensions::unscaled.hsep_wide, 0),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_BT_START_LEVEL), SetStringTip(STR_BROWSER_TUTORIAL_START_LEVEL, STR_BROWSER_TUTORIAL_START_LEVEL_TOOLTIP), SetMinimalSize(168, 24),
\t\tNWidget(WWT_PUSHTXTBTN, COLOUR_ORANGE, WID_BT_BUTTON_GUIDE), SetStringTip(STR_BROWSER_BUTTON_GUIDE_MENU, STR_BROWSER_BUTTON_GUIDE_TOOLTIP), SetMinimalSize(158, 24),
\t\tNWidget(NWID_SPACER), SetFill(1, 0),
\tEndContainer(),'''
text = replace_once(text, overview_actions_old, overview_actions_new, "overview action row")

# These lessons previously had target=None, so there was literally nothing to
# highlight. Point them at the matching vehicle-list button on the main toolbar.
target_replacements = {
    "{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::RoadVehicleBought}":
        "{STR_BROWSER_TUTORIAL_LEVEL_08, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicleBought}",
    "{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::RoadOrdersSet}":
        "{STR_BROWSER_TUTORIAL_LEVEL_09, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadOrdersSet}",
    "{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::RoadVehicleRunning}":
        "{STR_BROWSER_TUTORIAL_LEVEL_10, SPR_IMG_TRUCKLIST, BrowserTutorialTarget::MainToolbar, WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicleRunning}",
    "{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_TRAINLIST, BrowserTutorialTarget::None, INVALID_WIDGET, BrowserTutorialObjective::TrainBought}":
        "{STR_BROWSER_TUTORIAL_LEVEL_15, SPR_IMG_TRAINLIST, BrowserTutorialTarget::MainToolbar, WID_TN_TRAINS, BrowserTutorialObjective::TrainBought}",
}
for old, new in target_replacements.items():
    text = replace_once(text, old, new, "missing tutorial highlight target")

# Road/rail toolbars can be closed by the player. In that case the fallback is
# the always-visible top toolbar button that re-opens the required construction
# toolbar, so the tutorial never silently loses its visual target.
clear_marker = '''static void BrowserTutorialClearHighlights()
{
\tif (Window *w = FindWindowById(WC_MAIN_TOOLBAR, 0); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_ROAD); w != nullptr) w->DisableAllWidgetHighlight();
\tif (Window *w = FindWindowById(WC_BUILD_TOOLBAR, TRANSPORT_RAIL); w != nullptr) w->DisableAllWidgetHighlight();
}
'''
resolver_block = '''static Window *BrowserTutorialResolveTarget(const BrowserTutorialCoachStep &step, WidgetID &widget)
{
\twidget = step.widget;
\tif (Window *target = BrowserTutorialTargetWindow(step.target); target != nullptr && widget != INVALID_WIDGET) return target;

\tWindow *main = FindWindowById(WC_MAIN_TOOLBAR, 0);
\tif (main == nullptr) return nullptr;
\tif (step.target == BrowserTutorialTarget::RoadToolbar) {
\t\twidget = WID_TN_ROADS;
\t\treturn main;
\t}
\tif (step.target == BrowserTutorialTarget::RailToolbar) {
\t\twidget = WID_TN_RAILS;
\t\treturn main;
\t}
\treturn nullptr;
}

'''
if "BrowserTutorialResolveTarget" not in text:
    if text.count(clear_marker) != 1:
        raise SystemExit("Could not find tutorial highlight-clear block")
    text = text.replace(clear_marker, clear_marker + "\n" + resolver_block, 1)

coach_pattern = re.compile(
    r"struct BrowserTutorialCoachWindow final : Window \{.*?\n\};\n\nvoid StartBrowserTutorialLevel\(\)",
    re.S,
)
new_coach = r'''struct BrowserTutorialCoachWindow final : Window {
\tsize_t step = 0;
\tbool objective_complete = false;
\tbool highlight_visible = true;
\tuint highlight_elapsed_ms = 0;

\tBrowserTutorialCoachWindow() : Window(_browser_tutorial_coach_desc)
\t{
\t\tthis->InitNested(0);
\t\tthis->UpdateStep();
\t}

\tvoid Close([[maybe_unused]] int data = 0) override
\t{
\t\tBrowserTutorialClearHighlights();
\t\t_browser_tutorial_active = false;
\t\tthis->Window::Close();
\t}

\tvoid UpdateObjectiveState()
\t{
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tthis->objective_complete = BrowserTutorialObjectiveComplete(current.objective);
\t\tthis->SetWidgetDisabledState(WID_BTC_NEXT, !this->objective_complete);
\t}

\tvoid ApplyHighlight()
\t{
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tWidgetID target_widget = INVALID_WIDGET;
\t\tif (Window *target = BrowserTutorialResolveTarget(current, target_widget); target != nullptr && target_widget != INVALID_WIDGET) {
\t\t\ttarget->SetWidgetHighlight(target_widget, TC_YELLOW);
\t\t}
\t}

\tvoid UpdateStep()
\t{
\t\tBrowserTutorialClearHighlights();
\t\tthis->highlight_visible = true;
\t\tthis->highlight_elapsed_ms = 0;
\t\tthis->SetWidgetDisabledState(WID_BTC_PREVIOUS, this->step == 0);
\t\tthis->UpdateObjectiveState();
\t\tthis->ApplyHighlight();
\t\tthis->SetDirty();
\t}

\tvoid OnRealtimeTick(uint delta_ms) override
\t{
\t\tconst bool was_complete = this->objective_complete;
\t\tthis->UpdateObjectiveState();

\t\t/* Strong, deliberate pulse. The normal OpenTTD highlight also alternates
\t\t   white/yellow; this extra on/off phase makes the target unmistakable. */
\t\tthis->highlight_elapsed_ms += delta_ms;
\t\tif (this->highlight_elapsed_ms >= 260) {
\t\t\tthis->highlight_elapsed_ms %= 260;
\t\t\tthis->highlight_visible = !this->highlight_visible;
\t\t\tBrowserTutorialClearHighlights();
\t\t\tif (this->highlight_visible) this->ApplyHighlight();
\t\t\tthis->SetDirty();
\t\t} else if (this->highlight_visible) {
\t\t\t/* Windows/toolbars can be recreated while the step stays active. */
\t\t\tthis->ApplyHighlight();
\t\t}

\t\tif (was_complete != this->objective_complete) this->SetDirty();
\t}

\tvoid DrawWidget(const Rect &r, WidgetID widget) const override
\t{
\t\tif (widget != WID_BTC_CONTENT) return;
\t\tconst auto &current = _browser_tutorial_level_steps[this->step];
\t\tRect body = r.Shrink(WidgetDimensions::scaled.sparse);
\t\tDrawSprite(current.icon, PAL_NONE, body.left + 12, body.top + 12);
\t\tRect text_rect{body.left + 58, body.top + 3, body.right, body.bottom - 45};
\t\tDrawStringMultiLine(text_rect, current.text, TC_BLACK, SA_LEFT);

\t\tconst StringID status = current.objective == BrowserTutorialObjective::Informational
\t\t\t? STR_BROWSER_TUTORIAL_OBJECTIVE_INFO
\t\t\t: (this->objective_complete ? STR_BROWSER_TUTORIAL_OBJECTIVE_DONE : STR_BROWSER_TUTORIAL_OBJECTIVE_LOCKED);
\t\tRect hint_rect{body.left + 58, body.bottom - 41, body.right, body.bottom};
\t\tDrawStringMultiLine(hint_rect, status, this->objective_complete ? TC_WHITE : TC_YELLOW, SA_LEFT);

\t\tif (!this->highlight_visible) return;
\t\tWidgetID target_widget_id = INVALID_WIDGET;
\t\tif (Window *target = BrowserTutorialResolveTarget(current, target_widget_id); target != nullptr && target_widget_id != INVALID_WIDGET) {
\t\t\tconst NWidgetBase *target_widget = target->GetWidget<NWidgetBase>(target_widget_id);
\t\t\tif (target_widget != nullptr) {
\t\t\t\tRect target_rect = target_widget->GetCurrentRect();
\t\t\t\tconst int tx = target->left + (target_rect.left + target_rect.right) / 2;
\t\t\t\tconst int ty = target->top + (target_rect.top + target_rect.bottom) / 2;
\t\t\t\tconst int cx = this->left + (body.left + body.right) / 2;
\t\t\t\tconst int cy = this->top + (body.top + body.bottom) / 2;
\t\t\t\tSpriteID arrow = SPR_ARROW_UP;
\t\t\t\tif (std::abs(tx - cx) > std::abs(ty - cy)) arrow = tx < cx ? SPR_ARROW_LEFT : SPR_ARROW_RIGHT;
\t\t\t\telse arrow = ty < cy ? SPR_ARROW_UP : SPR_ARROW_DOWN;
\t\t\t\tDrawSprite(arrow, PAL_NONE, body.left + 20, body.bottom - 31);
\t\t\t}
\t\t}
\t}

\tvoid OnClick([[maybe_unused]] Point pt, WidgetID widget, [[maybe_unused]] int click_count) override
\t{
\t\tif (widget == WID_BTC_PREVIOUS && this->step > 0) {
\t\t\t--this->step;
\t\t\tthis->UpdateStep();
\t\t\treturn;
\t\t}
\t\tif (widget == WID_BTC_NEXT) {
\t\t\tthis->UpdateObjectiveState();
\t\t\tif (!this->objective_complete) return;
\t\t\tif (this->step + 1 < std::size(_browser_tutorial_level_steps)) {
\t\t\t\t++this->step;
\t\t\t\tthis->UpdateStep();
\t\t\t} else {
\t\t\t\tthis->Close();
\t\t\t}
\t\t}
\t}
};

void StartBrowserTutorialLevel()'''
text, coach_count = coach_pattern.subn(new_coach, text, count=1)
if coach_count != 1:
    raise SystemExit(f"Could not install pulsing tutorial coach: {coach_count}")

for marker in (
    "SetMinimalSize(450, 140)",
    "SetMinimalSize(112, 24)",
    "static constexpr size_t BROWSER_GUIDE_ROWS = 2;",
    "WID_TN_ROADVEHS, BrowserTutorialObjective::RoadVehicleBought",
    "WID_TN_TRAINS, BrowserTutorialObjective::TrainBought",
    "BrowserTutorialResolveTarget",
    "highlight_elapsed_ms >= 260",
    "this->highlight_visible = !this->highlight_visible",
):
    if marker not in text:
        raise SystemExit(f"Missing final tutorial UX marker: {marker}")

intro_path.write_text(text, encoding="utf-8")

# OpenTTD already blinks highlighted widgets between white and their configured
# colour. Make tutorial-yellow highlights substantially thicker so that pulse is
# visible even over busy toolbar sprites and at high-DPI scales.
widget_path = Path("openttd/src/widget.cpp")
widget = widget_path.read_text(encoding="utf-8")
needle = '''\t\t\tGfxFillRect(outer.left + 1, inner.bottom, outer.right - 1, outer.bottom, colour);
'''
strong = needle + '''
\t\t\t/* Browser tutorial emphasis: make yellow coach targets impossible to miss. */
\t\t\tif (widget->GetHighlightColour() == TC_YELLOW) {
\t\t\t\tconst int thickness = std::max(2, ScaleGUITrad(3));
\t\t\t\tGfxFillRect(outer.left, outer.top, outer.right, std::min(outer.bottom, outer.top + thickness - 1), colour);
\t\t\t\tGfxFillRect(outer.left, std::max(outer.top, outer.bottom - thickness + 1), outer.right, outer.bottom, colour);
\t\t\t\tGfxFillRect(outer.left, outer.top, std::min(outer.right, outer.left + thickness - 1), outer.bottom, colour);
\t\t\t\tGfxFillRect(std::max(outer.left, outer.right - thickness + 1), outer.top, outer.right, outer.bottom, colour);
\t\t\t}
'''
if "Browser tutorial emphasis" not in widget:
    if widget.count(needle) != 1:
        raise SystemExit(f"Could not find widget-highlight drawing anchor: {widget.count(needle)}")
    widget = widget.replace(needle, strong, 1)
widget_path.write_text(widget, encoding="utf-8")

print("Tutorial UX patched: compact centred controls, complete targets and strong pulsing yellow guidance.")
