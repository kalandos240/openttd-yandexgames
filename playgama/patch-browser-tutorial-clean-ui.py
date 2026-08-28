#!/usr/bin/env python3
"""Final browser tutorial UI pass: no clipped 640px coach or detached arrow sprites."""
from pathlib import Path

p = Path('openttd/src/intro_gui.cpp')
s = p.read_text(encoding='utf-8')

# The previous polish made the coach 640px wide. On the moderation viewport
# (also 640px) window borders/padding make that physically impossible to fit,
# which is why controls could clip/overlap at scaled fonts. Keep generous text
# space but leave room for the native frame and desktop margins.
for old, new in (
    ('SetMinimalSize(600, 175)', 'SetMinimalSize(540, 160)'),
    ('SetMinimalSize(600, 190)', 'SetMinimalSize(540, 180)'),
    ('SetMinimalSize(640, 240)', 'SetMinimalSize(540, 205)'),
):
    if old in s:
        s = s.replace(old, new, 1)

# The old coach guessed the target direction and drew SPR_ARROW_* inside the
# coach window. Those sprites are tiny UI triangles, not callout arrows, and at
# some scales they render as the stray black triangle visible in screenshots.
# The actual target widget remains highlighted by OpenTTD itself, which is
# reliable at any scale and does not float over unrelated content.
start_marker = '\n\t\tif (Window *target = BrowserTutorialTargetWindow(current.target); target != nullptr && current.widget != INVALID_WIDGET) {\n\t\t\tconst NWidgetBase *target_widget = target->GetWidget<NWidgetBase>(current.widget);'
start = s.find(start_marker)
if start >= 0:
    end_marker = '\n\t}\n\n\tvoid OnClick'
    end = s.find(end_marker, start)
    if end < 0:
        raise SystemExit('Could not find coach DrawWidget end while removing detached arrow')
    s = s[:start] + s[end:]
elif 'const NWidgetBase *target_widget = target->GetWidget<NWidgetBase>(current.widget);' in s:
    raise SystemExit('Unexpected tutorial arrow layout')

# We intentionally keep widget highlighting as the callout mechanism.
if 'SetWidgetHighlight(current.widget, TC_WHITE)' not in s and 'SetWidgetHighlight(current.widget, TC_YELLOW)' not in s:
    raise SystemExit('Tutorial target highlighting is missing')
if 'SPR_ARROW_LEFT' in s[s.find('struct BrowserTutorialCoachWindow'):s.find('void StartBrowserTutorialLevel')]:
    raise SystemExit('Detached tutorial arrow survived')
if 'SetMinimalSize(640, 240)' in s:
    raise SystemExit('Clipped 640px coach minimum survived')

p.write_text(s, encoding='utf-8')
print('Tutorial coach now fits 640px viewports and uses native widget highlighting instead of broken arrow sprites.')
