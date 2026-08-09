#!/usr/bin/env python3
from pathlib import Path
import re

path = Path('openttd/src/newgrf_gui.cpp')
text = path.read_text()

# The offline patch removes the first CONTENT_DOWNLOAD switch branch from
# UpdateWidgetSize. That branch is a scoped `case ...: {}` in upstream 15.3,
# so remove the now-orphaned closing brace while keeping the switch/function
# closing braces intact.
old_tail = '\n\t\t\t}\n\t\t}\n\t}\n\n\tvoid OnResize() override'
new_tail = '\n\t\t}\n\t}\n\n\tvoid OnResize() override'
if old_tail not in text:
    raise SystemExit('Could not find orphaned NewGRF UpdateWidgetSize brace')
text = text.replace(old_tail, new_tail, 1)

# Remove the still-present click handler for the two Online Content buttons.
text, count = re.subn(
    r'\n\t\t\tcase WID_NS_CONTENT_DOWNLOAD:\n'
    r'\t\t\tcase WID_NS_CONTENT_DOWNLOAD2:\n'
    r'.*?\n\t\t\t\tbreak;\n',
    '\n',
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit('Could not remove NewGRF Online Content click handler')

# The old patch already removes the two SetStringTip calls. Remove the
# surrounding online-content label-selection code too, so no player-facing
# Online Content text remains in this window.
text, count = re.subn(
    r'\n\t\tStringID text;\n'
    r'\t\tStringID tool_tip;\n'
    r'\t\tif \(has_missing \|\| has_compatible\) \{.*?'
    r'\t\t\ttool_tip = STR_INTRO_TOOLTIP_ONLINE_CONTENT;\n'
    r'\t\t\}\n',
    '\n',
    text,
    count=1,
    flags=re.S,
)
if count != 1:
    raise SystemExit('Could not remove NewGRF Online Content label block')

# `has_compatible` existed only to choose the Online Content / missing-content
# label. Drop it and its update now that those buttons do not exist.
text = text.replace('\t\tbool has_compatible = false;\n', '')
text = text.replace('\t\t\thas_compatible |= c->flags.Test(GRFConfigFlag::Compatible);\n', '')

# Verify all user-facing routes/text for NewGRF online content are gone.
for needle in (
    'case WID_NS_CONTENT_DOWNLOAD:',
    'case WID_NS_CONTENT_DOWNLOAD2:',
    'NWidget(WWT_PUSHTXTBTN, COLOUR_YELLOW, WID_NS_CONTENT_DOWNLOAD',
    'GetWidget<NWidgetCore>(WID_NS_CONTENT_DOWNLOAD',
    'STR_INTRO_ONLINE_CONTENT',
    'STR_INTRO_TOOLTIP_ONLINE_CONTENT',
):
    if needle in text:
        raise SystemExit(f'NewGRF offline verification failed; still found: {needle}')

path.write_text(text)
print('Repaired and verified NewGRF offline UI patch.')
