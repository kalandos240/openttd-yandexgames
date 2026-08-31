#!/usr/bin/env python3
from pathlib import Path
import re

path = Path('openttd/src/intro_gui.cpp')
text = path.read_text()

# The bundled upstream README/changelog/help documents contain legacy links and
# multiplayer/online references. Keep the local files in the GPL distribution,
# but remove the in-game Help entry point in the Yandex single-player edition.
text, count = re.subn(
    r'\n\t\t\t\tNWidget\(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_HELP\),[^\n]*\n',
    '\n',
    text,
    count=1,
)
if count != 1:
    raise SystemExit('Could not remove main-menu Help button')

needle = 'NWidget(WWT_PUSHIMGTEXTBTN, COLOUR_ORANGE, WID_SGI_HELP)'
if needle in text:
    raise SystemExit('Help entry point is still visible')

path.write_text(text)
print('Legacy help/online document entry point hidden in Yandex build.')
