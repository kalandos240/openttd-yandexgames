#!/usr/bin/env python3
"""Remove remaining user-facing external-site entry points from Yandex OpenTTD.

`patch-yandex-offline.py` already removes the Websites widget frame. This pass
removes the now-unreachable URL constants/click handlers and the About website
label, so external recommendations are not retained in the compiled runtime.
Legal/source documents remain packaged unchanged.
"""
from pathlib import Path
import re


def patch_help() -> None:
    path = Path('openttd/src/help_gui.cpp')
    text = path.read_text(encoding='utf-8')

    url_pattern = re.compile(
        r'\n[ \t]*static const std::string WEBSITE_LINK = "https://www\.openttd\.org/";\n'
        r'[ \t]*static const std::string WIKI_LINK = "https://wiki\.openttd\.org/";\n'
        r'[ \t]*static const std::string BUGTRACKER_LINK = "https://bugs\.openttd\.org/";\n'
        r'[ \t]*static const std::string COMMUNITY_LINK = "https://community\.openttd\.org/";\n'
    )
    text, n_urls = url_pattern.subn('\n', text, count=1)
    if n_urls != 1:
        raise SystemExit('Could not remove Help external URL constants')

    click_pattern = re.compile(
        r'\n[ \t]*case WID_HW_WEBSITE:\n[ \t]*OpenBrowser\(WEBSITE_LINK\);\n[ \t]*break;'
        r'\n[ \t]*case WID_HW_WIKI:\n[ \t]*OpenBrowser\(WIKI_LINK\);\n[ \t]*break;'
        r'\n[ \t]*case WID_HW_BUGTRACKER:\n[ \t]*OpenBrowser\(BUGTRACKER_LINK\);\n[ \t]*break;'
        r'\n[ \t]*case WID_HW_COMMUNITY:\n[ \t]*OpenBrowser\(COMMUNITY_LINK\);\n[ \t]*break;'
    )
    text, n_clicks = click_pattern.subn('', text, count=1)
    if n_clicks != 1:
        raise SystemExit('Could not remove Help external-site click handlers')

    # The earlier offline patch must already have removed the visible Websites
    # frame. Enforce that invariant here rather than trying to remove it twice.
    forbidden = (
        'WEBSITE_LINK', 'WIKI_LINK', 'BUGTRACKER_LINK', 'COMMUNITY_LINK',
        'WID_HW_WEBSITE:', 'WID_HW_WIKI:', 'WID_HW_BUGTRACKER:', 'WID_HW_COMMUNITY:',
        'STR_HELP_WINDOW_WEBSITES',
    )
    leftovers = [token for token in forbidden if token in text]
    if leftovers:
        raise SystemExit(f'External Help UI/runtime reference remains: {leftovers}')

    path.write_text(text, encoding='utf-8')


def patch_about() -> None:
    path = Path('openttd/src/misc_gui.cpp')
    text = path.read_text(encoding='utf-8')

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
print('Yandex external website runtime/UI removed; local legal documents preserved.')
