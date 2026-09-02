#!/usr/bin/env python3
"""Remove user-facing external-site entry points from the Yandex OpenTTD build.

The legal/source documents remain packaged unchanged. This only removes buttons/
labels that recommend or open external websites from the in-game UI.
"""
from pathlib import Path
import re


def patch_help() -> None:
    path = Path('openttd/src/help_gui.cpp')
    text = path.read_text(encoding='utf-8')

    # Remove external URL constants.
    text, n_urls = re.subn(
        r'\nstatic const std::string WEBSITE_LINK = "https://www\.openttd\.org/";\n'
        r'static const std::string WIKI_LINK = "https://wiki\.openttd\.org/";\n'
        r'static const std::string BUGTRACKER_LINK = "https://bugs\.openttd\.org/";\n'
        r'static const std::string COMMUNITY_LINK = "https://community\.openttd\.org/";\n',
        '\n',
        text,
        count=1,
    )
    if n_urls != 1:
        raise SystemExit('Could not remove Help external URL constants')

    # Remove the external-site click handlers while preserving local documents.
    text, n_clicks = re.subn(
        r'\n\t\t\tcase WID_HW_WEBSITE:\n\t\t\t\tOpenBrowser\(WEBSITE_LINK\);\n\t\t\t\tbreak;'
        r'\n\t\t\tcase WID_HW_WIKI:\n\t\t\t\tOpenBrowser\(WIKI_LINK\);\n\t\t\t\tbreak;'
        r'\n\t\t\tcase WID_HW_BUGTRACKER:\n\t\t\t\tOpenBrowser\(BUGTRACKER_LINK\);\n\t\t\t\tbreak;'
        r'\n\t\t\tcase WID_HW_COMMUNITY:\n\t\t\t\tOpenBrowser\(COMMUNITY_LINK\);\n\t\t\t\tbreak;',
        '',
        text,
        count=1,
    )
    if n_clicks != 1:
        raise SystemExit('Could not remove Help external-site click handlers')

    # Remove the complete Websites frame from Help. Local README/changelog/license
    # buttons remain available if Help is ever opened programmatically.
    text, n_frame = re.subn(
        r'\n\t\t\tNWidget\(WWT_FRAME, COLOUR_DARK_GREEN\), SetStringTip\(STR_HELP_WINDOW_WEBSITES\),\n'
        r'\t\t\t\tNWidget\(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_HW_WEBSITE\),[^\n]*\n'
        r'\t\t\t\tNWidget\(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_HW_WIKI\),[^\n]*\n'
        r'\t\t\t\tNWidget\(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_HW_BUGTRACKER\),[^\n]*\n'
        r'\t\t\t\tNWidget\(WWT_PUSHTXTBTN, COLOUR_GREEN, WID_HW_COMMUNITY\),[^\n]*\n'
        r'\t\t\tEndContainer\(\),\n',
        '\n',
        text,
        count=1,
    )
    if n_frame != 1:
        raise SystemExit('Could not remove Help Websites widget frame')

    forbidden = (
        'WEBSITE_LINK', 'WIKI_LINK', 'BUGTRACKER_LINK', 'COMMUNITY_LINK',
        'WID_HW_WEBSITE)', 'WID_HW_WIKI)', 'WID_HW_BUGTRACKER)', 'WID_HW_COMMUNITY)',
        'STR_HELP_WINDOW_WEBSITES',
    )
    leftovers = [token for token in forbidden if token in text]
    if leftovers:
        raise SystemExit(f'External Help UI remains: {leftovers}')

    path.write_text(text, encoding='utf-8')


def patch_about() -> None:
    path = Path('openttd/src/misc_gui.cpp')
    text = path.read_text(encoding='utf-8')

    line = '\t\tNWidget(WWT_LABEL, INVALID_COLOUR, WID_A_WEBSITE),\n'
    if text.count(line) != 1:
        raise SystemExit('Could not find About website label')
    text = text.replace(line, '', 1)

    line = '\t\tif (widget == WID_A_WEBSITE) return "Website: https://www.openttd.org";\n'
    if text.count(line) != 1:
        raise SystemExit('Could not find About website text')
    text = text.replace(line, '', 1)

    if 'Website: https://www.openttd.org' in text or 'WID_A_WEBSITE),' in text:
        raise SystemExit('About external website UI remains')

    path.write_text(text, encoding='utf-8')


patch_help()
patch_about()
print('Yandex external website UI removed; local legal documents preserved.')
