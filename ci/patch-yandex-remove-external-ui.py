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

    # Remove external URL constants. Keep this deliberately tolerant of nearby
    # whitespace so it survives minor OpenTTD source formatting differences.
    url_pattern = re.compile(
        r'\n[ \t]*static const std::string WEBSITE_LINK = "https://www\.openttd\.org/";\n'
        r'[ \t]*static const std::string WIKI_LINK = "https://wiki\.openttd\.org/";\n'
        r'[ \t]*static const std::string BUGTRACKER_LINK = "https://bugs\.openttd\.org/";\n'
        r'[ \t]*static const std::string COMMUNITY_LINK = "https://community\.openttd\.org/";\n'
    )
    text, n_urls = url_pattern.subn('\n', text, count=1)
    if n_urls != 1:
        raise SystemExit('Could not remove Help external URL constants')

    # Remove the external-site click handlers while preserving local documents.
    click_pattern = re.compile(
        r'\n[ \t]*case WID_HW_WEBSITE:\n[ \t]*OpenBrowser\(WEBSITE_LINK\);\n[ \t]*break;'
        r'\n[ \t]*case WID_HW_WIKI:\n[ \t]*OpenBrowser\(WIKI_LINK\);\n[ \t]*break;'
        r'\n[ \t]*case WID_HW_BUGTRACKER:\n[ \t]*OpenBrowser\(BUGTRACKER_LINK\);\n[ \t]*break;'
        r'\n[ \t]*case WID_HW_COMMUNITY:\n[ \t]*OpenBrowser\(COMMUNITY_LINK\);\n[ \t]*break;'
    )
    text, n_clicks = click_pattern.subn('', text, count=1)
    if n_clicks != 1:
        raise SystemExit('Could not remove Help external-site click handlers')

    # Remove everything from the Websites frame up to (but not including) the
    # Documents frame. This is intentionally token-anchored rather than tied to
    # exact COLOUR_/Colours:: spelling or indentation.
    websites = re.search(
        r'^[ \t]*NWidget\(WWT_FRAME,[^\n]*SetStringTip\(STR_HELP_WINDOW_WEBSITES\),[ \t]*$',
        text,
        flags=re.M,
    )
    documents = re.search(
        r'^[ \t]*NWidget\(WWT_FRAME,[^\n]*SetStringTip\(STR_HELP_WINDOW_DOCUMENTS\),[ \t]*$',
        text,
        flags=re.M,
    )
    if websites is None or documents is None or documents.start() <= websites.start():
        raise SystemExit('Could not locate Help Websites/Documents widget boundary')
    text = text[:websites.start()] + text[documents.start():]

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

    # Remove the About-window website widget regardless of the colour enum
    # spelling used by the exact OpenTTD revision being built.
    text, n_widget = re.subn(
        r'^[ \t]*NWidget\(WWT_LABEL,[^\n]*WID_A_WEBSITE\),[ \t]*\n',
        '',
        text,
        count=1,
        flags=re.M,
    )
    if n_widget != 1:
        raise SystemExit('Could not remove About website label')

    text, n_string = re.subn(
        r'^[ \t]*if \(widget == WID_A_WEBSITE\) return "Website: https://www\.openttd\.org";[ \t]*\n',
        '',
        text,
        count=1,
        flags=re.M,
    )
    if n_string != 1:
        raise SystemExit('Could not remove About website text')

    if 'Website: https://www.openttd.org' in text or 'WID_A_WEBSITE),' in text:
        raise SystemExit('About external website UI remains')

    path.write_text(text, encoding='utf-8')


patch_help()
patch_about()
print('Yandex external website UI removed; local legal documents preserved.')
