#!/usr/bin/env python3
"""Make the browser tutorial reachable from the in-game Help menu."""
from pathlib import Path


intro_path = Path('openttd/src/intro_gui.cpp')
intro = intro_path.read_text(encoding='utf-8')
if 'static void ShowBrowserTutorial()' in intro:
    intro = intro.replace('static void ShowBrowserTutorial()', 'void ShowBrowserTutorial()', 1)
elif 'void ShowBrowserTutorial()' not in intro:
    raise SystemExit('Could not find browser tutorial entry point')
intro_path.write_text(intro, encoding='utf-8')


toolbar_path = Path('openttd/src/toolbar_gui.cpp')
toolbar = toolbar_path.read_text(encoding='utf-8')

help_anchor = '/* --- Help button menu --- */\n'
declaration = 'extern void ShowBrowserTutorial();\n\n'
if declaration not in toolbar:
    if help_anchor not in toolbar:
        raise SystemExit('Could not find toolbar Help menu anchor')
    toolbar = toolbar.replace(help_anchor, declaration + help_anchor, 1)

old_menu_pair = 'STR_ABOUT_MENU_HELP, STR_NULL'
new_menu_pair = 'STR_ABOUT_MENU_HELP, STR_BROWSER_TUTORIAL_MENU, STR_NULL'
if new_menu_pair not in toolbar:
    count = toolbar.count(old_menu_pair)
    if count != 2:
        raise SystemExit(f'Expected two Help menu lists, found {count}')
    toolbar = toolbar.replace(old_menu_pair, new_menu_pair)

old_switch = '''\t\tcase  0: return PlaceLandBlockInfo();
\t\tcase  1: ShowHelpWindow();                 break;
\t\tcase  2: IConsoleSwitch();                 break;
\t\tcase  3: ShowScriptDebugWindow(CompanyID::Invalid(), _ctrl_pressed); break;
\t\tcase  4: ShowScreenshotWindow();           break;
\t\tcase  5: ShowFramerateWindow();            break;
\t\tcase  6: ShowAboutWindow();                break;
\t\tcase  7: ShowSpriteAlignerWindow();        break;
\t\tcase  8: ToggleBoundingBoxes();            break;
\t\tcase  9: ToggleDirtyBlocks();              break;
\t\tcase 10: ToggleWidgetOutlines();           break;
'''
new_switch = '''\t\tcase  0: return PlaceLandBlockInfo();
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
if 'case  2: ShowBrowserTutorial();' not in toolbar:
    if toolbar.count(old_switch) != 1:
        raise SystemExit('Could not find Help menu callback switch')
    toolbar = toolbar.replace(old_switch, new_switch, 1)

for marker in (
    'extern void ShowBrowserTutorial();',
    'STR_ABOUT_MENU_HELP, STR_BROWSER_TUTORIAL_MENU, STR_NULL',
    'case  2: ShowBrowserTutorial();',
):
    if marker not in toolbar:
        raise SystemExit(f'Missing in-game tutorial toolbar marker: {marker!r}')

toolbar_path.write_text(toolbar, encoding='utf-8')
print('Browser tutorial added to the in-game Help menu.')
